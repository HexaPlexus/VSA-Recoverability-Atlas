from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import inspect
import json
from pathlib import Path

import pytest
import torch
import torchhd

from cgrn_hsr.query_context import BaselineConfig, SyntheticContextConfig, build_query_trial_problem
from cgrn_hsr.selective_policy import (
    level1e_calibration_seed_set,
    level1e_development_seed_set,
    level1e_heldout_seed_set,
)
from cgrn_hsr.warm_start import (
    FROZEN_GLOBAL_GATE_THRESHOLDS,
    FROZEN_L2_GATE_THRESHOLDS,
    GLOBAL_GATE_VERSION,
    L2_GATE_VERSION,
    METHOD_ALWAYS_GLOBAL_COLD,
    METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
    METHOD_L2_THEN_COLD_GLOBAL,
    METHOD_L2_THEN_WARM_GLOBAL,
    POLICY_ABSTAIN_BUDGET_EXHAUSTED,
    RECOVERY_TOLERANCE,
    SelectedMethodRecord,
    StageExecution,
    WarmStartStage,
    build_contextual_candidate_indices,
    build_paired_comparisons,
    choose_selected_method,
    global_budget_candidate_evaluations,
    level1e1_calibration_seed_set,
    level1e1_development_seed_set,
    level1e1_heldout_seed_set,
    run_method_trial,
    warm_start_seed_sets_non_overlapping,
)
from cgrn_hsr import warm_start


def build_problem(seed: int = 401, max_iterations: int = 12):
    config = BaselineConfig(
        dimensions=64,
        num_factors=3,
        domain_size=6,
        structured_distractor_count=0,
        max_iterations=max_iterations,
        stable_patience=3,
    )
    return build_query_trial_problem(
        config,
        seed=seed,
        anomaly_rate=0.1,
        seed_split="test",
        context_config=SyntheticContextConfig(multi_membership_rate=1.0, tertiary_membership_rate=0.3),
    )


def make_stage(
    problem,
    stage_label: str,
    candidate_count: int,
    predicted_indices: list[int] | None = None,
    stable_prediction: bool = True,
    query_outcome_class: str = "QUERY_TARGET_RECOVERY",
    iterations_used: int = 1,
    min_margin: float = 0.2,
    reconstruction: float = 0.2,
) -> WarmStartStage:
    prediction = predicted_indices or problem.designated_target_tuple.tolist()
    margins = [min_margin] * problem.config.num_factors
    top1 = [0.4] * problem.config.num_factors
    top2 = [0.2] * problem.config.num_factors
    candidate_evaluations = iterations_used * problem.config.num_factors * candidate_count
    return WarmStartStage(
        stage_label=stage_label,
        candidate_count=candidate_count,
        iterations_used=iterations_used,
        stable_prediction=stable_prediction,
        stable_iterations=problem.config.stable_patience if stable_prediction else 1,
        predicted_indices=prediction,
        normalized_top1_scores=top1,
        normalized_top2_scores=top2,
        normalized_margins=margins,
        normalized_reconstruction_similarity=reconstruction,
        query_outcome_class=query_outcome_class,
        valid_recovery=query_outcome_class in ("QUERY_TARGET_RECOVERY", "QUERY_EQUIVALENT_VALID"),
        exact_recovery=query_outcome_class == "QUERY_TARGET_RECOVERY",
        factor_candidate_recall=[True] * problem.config.num_factors,
        all_truth_included=True,
        candidate_evaluations_proxy=candidate_evaluations,
        element_operations_proxy=candidate_evaluations * problem.config.dimensions,
        query_valid_source_included=True,
    )


def make_execution(problem, stage_label: str, candidate_count: int, fill: float) -> StageExecution:
    stage = make_stage(problem, stage_label, candidate_count)
    return StageExecution(
        stage=stage,
        final_estimates=torch.full((problem.config.num_factors, problem.config.dimensions), fill),
        final_similarities=torch.zeros((problem.config.num_factors, candidate_count)),
    )


def test_warm_start_uses_final_l2_estimates(monkeypatch) -> None:
    problem = build_problem(seed=501)
    l2_indices, _, full_indices = build_contextual_candidate_indices(problem, problem.query_context)
    seen_initials: list[torch.Tensor] = []

    def fake_run_iterative(problem_arg, candidate_indices, initial_estimates, max_iterations, stage_label):
        seen_initials.append(initial_estimates.clone())
        if stage_label == "L2_narrow":
            return make_execution(problem_arg, stage_label, candidate_indices.size(1), fill=7.0)
        return make_execution(problem_arg, stage_label, candidate_indices.size(1), fill=9.0)

    monkeypatch.setattr(warm_start, "run_iterative_stage", fake_run_iterative)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    monkeypatch.setattr(warm_start, "frozen_global_gate_accepts", lambda stage: True)

    _ = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert torch.allclose(seen_initials[1], torch.full_like(seen_initials[1], 7.0))
    assert full_indices.size(1) == seen_initials[1].size(0) * 0 + problem.config.domain_size


def test_cold_global_does_not_use_l2_estimates(monkeypatch) -> None:
    problem = build_problem(seed=502)
    seen_initials: list[torch.Tensor] = []

    def fake_run_iterative(problem_arg, candidate_indices, initial_estimates, max_iterations, stage_label):
        seen_initials.append(initial_estimates.clone())
        if stage_label == "L2_narrow":
            return make_execution(problem_arg, stage_label, candidate_indices.size(1), fill=7.0)
        return make_execution(problem_arg, stage_label, candidate_indices.size(1), fill=9.0)

    monkeypatch.setattr(warm_start, "run_iterative_stage", fake_run_iterative)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    monkeypatch.setattr(warm_start, "frozen_global_gate_accepts", lambda stage: True)

    _ = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_COLD_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert not torch.allclose(seen_initials[1], torch.full_like(seen_initials[1], 7.0))


def test_domain_size_switch_uses_real_upstream_resonator(monkeypatch) -> None:
    problem = build_problem(seed=503)
    calls: list[int] = []
    original = torchhd.resonator

    def wrapped(*args, **kwargs):
        calls.append(int(args[2].size(1)))
        return original(*args, **kwargs)

    monkeypatch.setattr(torchhd, "resonator", wrapped)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    _ = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert any(size == max(2, -(-problem.config.domain_size // 4)) for size in calls)
    assert any(size == problem.config.domain_size for size in calls)
    assert len(calls) > 0


def test_one_step_probe_executes_exactly_one_step(monkeypatch) -> None:
    problem = build_problem(seed=504)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    result = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert result.probe_steps_executed == 1


def test_two_step_probe_executes_no_more_than_two_steps(monkeypatch) -> None:
    problem = build_problem(seed=505)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    result = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert result.probe_steps_executed == 2
    assert result.probe_steps_executed <= 2


def test_no_full_l1_iterative_convergence_is_run(monkeypatch) -> None:
    problem = build_problem(seed=506)
    _, l1_indices, _ = build_contextual_candidate_indices(problem, problem.query_context)
    l1_candidate_count = l1_indices.size(1)

    def guarded_run_iterative(problem_arg, candidate_indices, initial_estimates, max_iterations, stage_label):
        assert candidate_indices.size(1) != l1_candidate_count
        return make_execution(problem_arg, stage_label, candidate_indices.size(1), fill=1.0)

    monkeypatch.setattr(warm_start, "run_iterative_stage", guarded_run_iterative)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    monkeypatch.setattr(warm_start, "frozen_global_gate_accepts", lambda stage: True)

    _ = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )


@pytest.mark.parametrize(
    "method_id",
    [
        METHOD_L2_THEN_COLD_GLOBAL,
        METHOD_L2_THEN_WARM_GLOBAL,
        METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
        METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
    ],
)
def test_budget_never_exceeds_global_equivalent(method_id: str, monkeypatch) -> None:
    problem = build_problem(seed=507)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    result = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=method_id,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert result.candidate_evaluations <= global_budget_candidate_evaluations(problem)


def test_budget_exhaustion_abstains() -> None:
    problem = build_problem(seed=508, max_iterations=1)
    result = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_COLD_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert result.budget_exhausted is True
    assert result.policy_outcome == POLICY_ABSTAIN_BUDGET_EXHAUSTED


def test_compute_accounting_only_counts_executed_steps(monkeypatch) -> None:
    problem = build_problem(seed=509)
    monkeypatch.setattr(warm_start, "frozen_l2_gate_accepts", lambda stage: False)
    result = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    expected = (
        result.l2_stage["candidate_evaluations_proxy"]
        + result.probe_steps_executed * problem.config.num_factors * ((problem.config.domain_size + 1) // 2)
        + (0 if result.global_stage is None else result.global_stage["candidate_evaluations_proxy"])
    )
    assert result.candidate_evaluations == expected


def test_frozen_l2_gate_is_unchanged() -> None:
    payload = json.loads((Path("results") / "level1e" / "selected_policy.json").read_text(encoding="utf-8"))
    assert FROZEN_L2_GATE_THRESHOLDS.l2_min_margin == pytest.approx(0.05)
    assert FROZEN_L2_GATE_THRESHOLDS.l2_reconstruction == pytest.approx(0.15)
    assert payload["thresholds"]["l2_min_margin"] == pytest.approx(FROZEN_L2_GATE_THRESHOLDS.l2_min_margin)
    assert payload["thresholds"]["l2_reconstruction"] == pytest.approx(FROZEN_L2_GATE_THRESHOLDS.l2_reconstruction)
    assert L2_GATE_VERSION == "level1e-frozen-l2-v1"


def test_frozen_global_gate_is_unchanged() -> None:
    payload = json.loads((Path("results") / "level1e" / "selected_policy.json").read_text(encoding="utf-8"))
    assert FROZEN_GLOBAL_GATE_THRESHOLDS.global_min_margin == pytest.approx(0.05)
    assert FROZEN_GLOBAL_GATE_THRESHOLDS.global_reconstruction == pytest.approx(0.05)
    assert payload["thresholds"]["global_min_margin"] == pytest.approx(FROZEN_GLOBAL_GATE_THRESHOLDS.global_min_margin)
    assert payload["thresholds"]["global_reconstruction"] == pytest.approx(FROZEN_GLOBAL_GATE_THRESHOLDS.global_reconstruction)
    assert GLOBAL_GATE_VERSION == "level1e-frozen-global-v1"


def test_runtime_policy_code_avoids_ground_truth_fields() -> None:
    source = inspect.getsource(warm_start.frozen_l2_gate_accepts) + inspect.getsource(warm_start.frozen_global_gate_accepts)
    for forbidden in ("ground_truth", "designated_target_tuple", "target_indices", "context_accuracy"):
        assert forbidden not in source


def test_paired_methods_share_same_observation() -> None:
    problem = build_problem(seed=510)
    original = problem.observation.clone()
    warm = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )
    cold = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_COLD_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )

    assert torch.equal(problem.observation, original)
    assert warm.seed == cold.seed


def test_warm_cold_runs_are_deterministic() -> None:
    problem = build_problem(seed=511)
    warm_a = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )
    warm_b = run_method_trial(
        problem=problem,
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_WARM_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )
    assert warm_a.to_dict() == warm_b.to_dict()


def test_warm_helped_hurt_same_counts_are_correct() -> None:
    template = run_method_trial(
        problem=build_problem(seed=512),
        cell_id="COLLAPSE_SINGLE_PRIMARY",
        operating_point_label="TEST",
        method_id=METHOD_L2_THEN_COLD_GLOBAL,
        master_seed=0,
        context_accuracy=0.9,
    )
    cold_bad = replace(template, seed=1, method_id=METHOD_L2_THEN_COLD_GLOBAL, accepted_correct=False, accepted_stage=None)
    warm_good = replace(template, seed=1, method_id=METHOD_L2_THEN_WARM_GLOBAL, accepted_correct=True, accepted_stage="GLOBAL")
    cold_good = replace(template, seed=2, method_id=METHOD_L2_THEN_COLD_GLOBAL, accepted_correct=True, accepted_stage="GLOBAL")
    warm_bad = replace(template, seed=2, method_id=METHOD_L2_THEN_WARM_GLOBAL, accepted_correct=False, accepted_stage=None)
    cold_same = replace(template, seed=3, method_id=METHOD_L2_THEN_COLD_GLOBAL, accepted_correct=False, accepted_stage=None)
    warm_same = replace(template, seed=3, method_id=METHOD_L2_THEN_WARM_GLOBAL, accepted_correct=False, accepted_stage=None)

    rows = build_paired_comparisons([cold_bad, warm_good, cold_good, warm_bad, cold_same, warm_same])
    row = next(item for item in rows if item["warm_method"] == METHOD_L2_THEN_WARM_GLOBAL)

    assert row["warm_helped"] == 1
    assert row["warm_hurt"] == 1
    assert row["warm_same"] == 1


def test_heldout_seeds_do_not_overlap_previous_runs() -> None:
    assert warm_start_seed_sets_non_overlapping() is True
    assert level1e1_development_seed_set().isdisjoint(level1e1_calibration_seed_set())
    assert level1e1_development_seed_set().isdisjoint(level1e1_heldout_seed_set())
    assert level1e1_heldout_seed_set().isdisjoint(level1e_development_seed_set())
    assert level1e1_heldout_seed_set().isdisjoint(level1e_calibration_seed_set())
    assert level1e1_heldout_seed_set().isdisjoint(level1e_heldout_seed_set())


def test_selected_method_is_immutable_after_heldout() -> None:
    record = choose_selected_method(
        [
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_ALWAYS_GLOBAL_COLD, "selective_risk": 0.5, "coverage": 1.0, "mean_compute": 100.0, "false_accept_rate": 0.5, "exact_or_valid_recovery_rate": 0.6},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_THEN_COLD_GLOBAL, "selective_risk": 0.1, "coverage": 0.5, "mean_compute": 90.0, "false_accept_rate": 0.1, "exact_or_valid_recovery_rate": 0.6},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_THEN_WARM_GLOBAL, "selective_risk": 0.04, "coverage": 0.2, "mean_compute": 80.0, "false_accept_rate": 0.05, "exact_or_valid_recovery_rate": 0.56},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_PROBE1_THEN_WARM_GLOBAL, "selective_risk": 0.06, "coverage": 0.3, "mean_compute": 70.0, "false_accept_rate": 0.05, "exact_or_valid_recovery_rate": 0.59},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_PROBE2_THEN_WARM_GLOBAL, "selective_risk": 0.07, "coverage": 0.3, "mean_compute": 70.0, "false_accept_rate": 0.05, "exact_or_valid_recovery_rate": 0.59},
        ]
    )

    assert isinstance(record, SelectedMethodRecord)
    assert record.selected_method == METHOD_L2_THEN_WARM_GLOBAL
    with pytest.raises(FrozenInstanceError):
        record.gate_result = "MUTATED"  # type: ignore[misc]


def test_choose_selected_method_uses_declared_tolerance() -> None:
    record = choose_selected_method(
        [
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_ALWAYS_GLOBAL_COLD, "selective_risk": 0.4, "coverage": 1.0, "mean_compute": 100.0, "false_accept_rate": 0.4, "exact_or_valid_recovery_rate": 0.7},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_THEN_COLD_GLOBAL, "selective_risk": 0.1, "coverage": 0.5, "mean_compute": 90.0, "false_accept_rate": 0.1, "exact_or_valid_recovery_rate": 0.7},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_THEN_WARM_GLOBAL, "selective_risk": 0.04, "coverage": 0.2, "mean_compute": 80.0, "false_accept_rate": 0.05, "exact_or_valid_recovery_rate": 0.7 - RECOVERY_TOLERANCE + 0.01},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_PROBE1_THEN_WARM_GLOBAL, "selective_risk": 0.2, "coverage": 0.2, "mean_compute": 70.0, "false_accept_rate": 0.2, "exact_or_valid_recovery_rate": 0.7},
            {"cell_id": "COLLAPSE_SINGLE_PRIMARY", "method_id": METHOD_L2_PROBE2_THEN_WARM_GLOBAL, "selective_risk": 0.2, "coverage": 0.2, "mean_compute": 70.0, "false_accept_rate": 0.2, "exact_or_valid_recovery_rate": 0.7},
        ]
    )
    assert record.gate_result == "CONFIRMED"
