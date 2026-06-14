from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

import pytest

from cgrn_hsr.query_context import (
    METHOD_GLOBAL_UNIFORM,
    QUERY_OUTCOME_EQUIVALENT_VALID,
    QUERY_OUTCOME_HYBRID_SPURIOUS,
    QUERY_OUTCOME_TARGET_RECOVERY,
    BaselineConfig,
    SyntheticContextConfig,
    build_query_trial_problem,
    run_query_trial,
)
from cgrn_hsr.selective_policy import (
    POLICY_ABSTAIN,
    POLICY_ACCEPT_CORRECT_L1,
    POLICY_ACCEPT_CORRECT_L2,
    POLICY_ACCEPT_WRONG_GLOBAL,
    POLICY_VERSION,
    SELECTIVE_POLICY_FEATURES,
    SELECTIVE_SCHEMA_VERSION,
    GlobalRuntimeEvidence,
    L1RuntimeEvidence,
    L2RuntimeEvidence,
    PolicyInput,
    PolicyThresholds,
    SelectedPolicy,
    StageCompute,
    compute_coverage,
    compute_selective_risk,
    compute_stage_hit_rates_among_all_trials,
    decision_outcome_label,
    level1e_calibration_seed_set,
    level1e_development_seed_set,
    level1e_heldout_seed_set,
    run_adaptive_policy,
    save_json,
    selective_seed_sets_non_overlapping,
)


def build_problem(seed: int = 301):
    config = BaselineConfig(
        dimensions=256,
        num_factors=3,
        domain_size=6,
        structured_distractor_count=2,
    )
    return build_query_trial_problem(
        config,
        seed=seed,
        anomaly_rate=0.1,
        seed_split="test",
        context_config=SyntheticContextConfig(multi_membership_rate=1.0, tertiary_membership_rate=0.3),
    )


def build_policy_input() -> PolicyInput:
    return PolicyInput(
        l2=L2RuntimeEvidence(
            stable_prediction_l2=True,
            iterations_l2=2,
            min_normalized_margin_l2=0.20,
            mean_normalized_margin_l2=0.25,
            normalized_reconstruction_l2=0.30,
            context_confidence=0.0,
        ),
        l1=L1RuntimeEvidence(
            stable_prediction_l1=True,
            iterations_l1=3,
            l2_tuple_survives_l1=True,
            l2_factor_survival_fraction_at_l1=1.0,
            l2_tuple_rank_at_l1=1.0,
            prediction_agreement_l2_l1=1.0,
            min_normalized_margin_l1=0.25,
            mean_normalized_margin_l1=0.30,
            normalized_reconstruction_l1=0.35,
            reconstruction_delta_l1_minus_l2=0.05,
            margin_delta_l1_minus_l2=0.05,
        ),
        global_stage=GlobalRuntimeEvidence(
            stable_prediction_global=True,
            iterations_global=4,
            prediction_agreement_l1_global=1.0,
            l1_tuple_rank_at_global=1.0,
            normalized_reconstruction_global=0.40,
            min_normalized_margin_global=0.30,
            mean_normalized_margin_global=0.35,
        ),
        l2_compute=StageCompute("L2_narrow", 2, 2, 12, 1200),
        l1_compute=StageCompute("L1_parent", 3, 4, 36, 3600),
        global_compute=StageCompute("global", 4, 6, 72, 7200),
    )


def build_policy(thresholds: PolicyThresholds | None = None) -> SelectedPolicy:
    return SelectedPolicy(
        policy_version=POLICY_VERSION,
        schema_version=SELECTIVE_SCHEMA_VERSION,
        features=SELECTIVE_POLICY_FEATURES,
        thresholds=thresholds
        or PolicyThresholds(
            l2_min_margin=0.10,
            l2_reconstruction=0.10,
            l1_rank_max=1.0,
            l1_min_margin=0.10,
            global_min_margin=0.10,
            global_reconstruction=0.10,
        ),
        calibration_seed_range={"PRIMARY": {"start": 1, "count": 2}},
        target_risk=0.05,
        achieved_calibration_risk=0.04,
        calibration_coverage=0.50,
        selection_rule="test",
        fallback_risk_target_used=False,
    )


def test_target_recovery_le_valid_recovery_on_same_denominator() -> None:
    audit = compute_stage_hit_rates_among_all_trials(
        {
            "oracle_earliest_valid_stage_counts": {"L2_narrow": 7, "L1_parent": 4, "global": 5},
            "oracle_earliest_target_stage_counts": {"L2_narrow": 5, "L1_parent": 3, "global": 4},
        },
        total_trials=20,
    )

    assert audit["oracle_earliest_target_before_global_hit_rate_among_all_trials"] <= audit[
        "oracle_earliest_valid_before_global_hit_rate_among_all_trials"
    ]
    assert audit["invariant_target_le_valid_same_denominator"] is True


def test_level1e_seed_splits_do_not_overlap() -> None:
    assert level1e_development_seed_set().isdisjoint(level1e_calibration_seed_set())
    assert level1e_development_seed_set().isdisjoint(level1e_heldout_seed_set())
    assert level1e_calibration_seed_set().isdisjoint(level1e_heldout_seed_set())
    assert selective_seed_sets_non_overlapping() is True


def test_runtime_policy_surface_excludes_ground_truth_and_context_accuracy() -> None:
    policy_input_fields = set(PolicyInput.__dataclass_fields__)
    l2_fields = set(L2RuntimeEvidence.__dataclass_fields__)
    l1_fields = set(L1RuntimeEvidence.__dataclass_fields__)
    global_fields = set(GlobalRuntimeEvidence.__dataclass_fields__)
    all_fields = policy_input_fields | l2_fields | l1_fields | global_fields | set(SELECTIVE_POLICY_FEATURES)

    forbidden = {
        "ground_truth_indices",
        "designated_target_tuple",
        "target_indices",
        "valid_source_tuples",
        "query_outcome_class",
        "outcome_class",
        "context_accuracy",
    }
    assert forbidden.isdisjoint(all_fields)


def test_l2_decision_uses_only_pre_l1_features() -> None:
    policy_input = build_policy_input()
    policy = build_policy()
    mutated = replace(
        policy_input,
        l1=replace(
            policy_input.l1,
            stable_prediction_l1=False,
            l2_tuple_survives_l1=False,
            l2_tuple_rank_at_l1=99.0,
            min_normalized_margin_l1=-1.0,
        ),
        global_stage=replace(
            policy_input.global_stage,
            stable_prediction_global=False,
            min_normalized_margin_global=-1.0,
            normalized_reconstruction_global=-1.0,
        ),
    )

    assert run_adaptive_policy(policy_input, policy).accepted_stage == "L2"
    assert run_adaptive_policy(mutated, policy).accepted_stage == "L2"


def test_l1_decision_uses_only_post_l1_features() -> None:
    policy_input = replace(
        build_policy_input(),
        l2=replace(
            build_policy_input().l2,
            min_normalized_margin_l2=0.01,
            normalized_reconstruction_l2=0.01,
        ),
    )
    policy = build_policy()
    mutated = replace(
        policy_input,
        global_stage=replace(
            policy_input.global_stage,
            stable_prediction_global=False,
            min_normalized_margin_global=-1.0,
            normalized_reconstruction_global=-1.0,
        ),
    )

    assert run_adaptive_policy(policy_input, policy).accepted_stage == "L1"
    assert run_adaptive_policy(mutated, policy).accepted_stage == "L1"


@pytest.mark.parametrize(
    ("thresholds", "expected_stage", "expected_compute"),
    [
        (
            PolicyThresholds(0.10, 0.10, 1.0, 0.10, 0.10, 0.10),
            "L2",
            (12, 1200),
        ),
        (
            PolicyThresholds(0.30, 0.30, 1.0, 0.10, 0.10, 0.10),
            "L1",
            (48, 4800),
        ),
        (
            PolicyThresholds(0.30, 0.30, 0.0, 0.50, 0.10, 0.10),
            "GLOBAL",
            (120, 12000),
        ),
        (
            PolicyThresholds(0.30, 0.30, 0.0, 0.50, 0.50, 0.50),
            None,
            (120, 12000),
        ),
    ],
)
def test_compute_accounting_sums_only_executed_stages(
    thresholds: PolicyThresholds,
    expected_stage: str | None,
    expected_compute: tuple[int, int],
) -> None:
    decision = run_adaptive_policy(build_policy_input(), build_policy(thresholds))

    assert decision.accepted_stage == expected_stage
    assert decision.candidate_evaluations == expected_compute[0]
    assert decision.element_operations_proxy == expected_compute[1]


def test_abstention_is_not_false_accept_and_metrics_are_correct() -> None:
    accepted_correct = 2
    accepted_total = 3
    total_trials = 5

    assert decision_outcome_label(None, QUERY_OUTCOME_HYBRID_SPURIOUS) == POLICY_ABSTAIN
    assert compute_selective_risk(accepted_correct, accepted_total) == pytest.approx(1.0 / 3.0)
    assert compute_coverage(accepted_total, total_trials) == pytest.approx(0.6)


def test_threshold_policy_is_deterministic() -> None:
    policy_input = build_policy_input()
    policy = build_policy()
    first = run_adaptive_policy(policy_input, policy)
    second = run_adaptive_policy(policy_input, policy)

    assert first == second


def test_policy_serialization_and_frozen_selected_policy(tmp_path: Path) -> None:
    policy = build_policy()
    path = tmp_path / "selected_policy.json"
    save_json(path, policy.to_dict())
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == SELECTIVE_SCHEMA_VERSION
    assert payload["policy_version"] == POLICY_VERSION
    assert payload["thresholds"]["l2_min_margin"] == pytest.approx(0.10)
    with pytest.raises(FrozenInstanceError):
        policy.target_risk = 0.10  # type: ignore[misc]


def test_selected_policy_is_not_mutated_during_execution() -> None:
    policy = build_policy()
    before = policy.to_dict()
    _ = run_adaptive_policy(build_policy_input(), policy)

    assert policy.to_dict() == before


def test_paired_baselines_use_same_observation() -> None:
    problem = build_problem(seed=302)
    original_observation = problem.observation.clone()
    global_result, _ = run_query_trial(
        problem,
        operating_point_label="TEST",
        master_seed=1234,
        method=METHOD_GLOBAL_UNIFORM,
    )
    l2_result, _ = run_query_trial(
        problem,
        operating_point_label="TEST",
        master_seed=1234,
        method="hard_l2_stage",
        context_accuracy=0.9,
    )

    assert problem.observation.equal(original_observation)
    assert global_result.seed == l2_result.seed
    assert global_result.designated_target_tuple == l2_result.designated_target_tuple


def test_query_valid_outcomes_are_marked_correct_and_global_error_is_wrong() -> None:
    assert decision_outcome_label("L2", QUERY_OUTCOME_TARGET_RECOVERY) == POLICY_ACCEPT_CORRECT_L2
    assert decision_outcome_label("L1", QUERY_OUTCOME_EQUIVALENT_VALID) == POLICY_ACCEPT_CORRECT_L1
    assert decision_outcome_label("GLOBAL", QUERY_OUTCOME_HYBRID_SPURIOUS) == POLICY_ACCEPT_WRONG_GLOBAL
