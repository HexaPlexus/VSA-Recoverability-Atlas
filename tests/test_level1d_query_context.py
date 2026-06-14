from __future__ import annotations

import json
from pathlib import Path

import torch
import torchhd

from cgrn_hsr.query_context import (
    CONTROL_SHUFFLED_QUERY_CONTEXT,
    LEVEL1D_CALIBRATION_MASTER_SEED,
    LEVEL1D_EVAL_MASTER_SEED,
    METHOD_GLOBAL_UNIFORM,
    METHOD_HARD_L1_STAGE,
    METHOD_HARD_L2_TOPK,
    METHOD_SOFT_L2_WEIGHTED_INIT,
    QUERY_OUTCOME_EQUIVALENT_VALID,
    QUERY_OUTCOME_HYBRID_SPURIOUS,
    QUERY_OUTCOME_IRRELEVANT_SOURCE_CAPTURE,
    QUERY_OUTCOME_TARGET_RECOVERY,
    QUERY_SCHEMA_VERSION,
    BaselineConfig,
    SyntheticContextConfig,
    build_prior_weights,
    build_query_trial_problem,
    build_stage_snapshots,
    build_weighted_initial_estimates,
    classify_query_outcome,
    degree_preserving_metadata_shuffle,
    full_candidate_indices,
    level1d_calibration_seed_set,
    level1d_evaluation_seed_set,
    non_overlapping_seed_sets,
    run_query_trial,
    save_json,
    save_summary_csv,
    save_trials_jsonl,
    select_l1_subset,
    select_l2_subset,
    shuffled_query_context_map,
    summarize_query_trials,
)


def build_problem(seed: int = 123, structured_distractor_count: int = 2):
    config = BaselineConfig(
        dimensions=256,
        num_factors=3,
        domain_size=6,
        structured_distractor_count=structured_distractor_count,
    )
    return build_query_trial_problem(
        config,
        seed=seed,
        anomaly_rate=0.1,
        seed_split="test",
        context_config=SyntheticContextConfig(multi_membership_rate=1.0, tertiary_membership_rate=0.3),
    )


def test_query_target_is_defined_by_query_metadata() -> None:
    problem = build_problem(seed=201)
    designated_sources = [source for source in problem.source_composites if source.is_designated_target]

    assert len(designated_sources) == 1
    assert designated_sources[0].tuple_indices.tolist() == problem.designated_target_tuple.tolist()
    assert problem.source_composites[0].tuple_indices.tolist() != problem.designated_target_tuple.tolist()


def test_equivalent_valid_source_classification() -> None:
    problem = build_problem(seed=202)
    equivalent = next(
        source for source in problem.source_composites if source.source_role == "QUERY_EQUIVALENT_VALID"
    )
    outcome = classify_query_outcome(problem, stable_prediction=True, predicted_indices=equivalent.tuple_indices)

    assert outcome == QUERY_OUTCOME_EQUIVALENT_VALID


def test_irrelevant_source_capture_classification() -> None:
    problem = build_problem(seed=203)
    irrelevant = next(
        source for source in problem.source_composites if not source.is_query_valid
    )
    outcome = classify_query_outcome(problem, stable_prediction=True, predicted_indices=irrelevant.tuple_indices)

    assert outcome == QUERY_OUTCOME_IRRELEVANT_SOURCE_CAPTURE


def test_hybrid_source_remains_spurious() -> None:
    problem = build_problem(seed=204)
    outcome = classify_query_outcome(
        problem,
        stable_prediction=True,
        predicted_indices=torch.tensor([5, 5, 5], dtype=torch.long),
    )

    assert outcome == QUERY_OUTCOME_HYBRID_SPURIOUS


def test_degree_preserving_metadata_shuffle() -> None:
    problem = build_problem(seed=205)
    shuffled = degree_preserving_metadata_shuffle(problem.context_hierarchy, seed=999)
    original_nonzero = (problem.context_hierarchy.factor_l2_weights > 0).sum(dim=-1)
    shuffled_nonzero = (shuffled.factor_l2_weights > 0).sum(dim=-1)
    original_sorted = torch.sort(problem.context_hierarchy.factor_l2_weights.flatten()).values
    shuffled_sorted = torch.sort(shuffled.factor_l2_weights.flatten()).values

    assert torch.equal(original_nonzero, shuffled_nonzero)
    assert torch.allclose(original_sorted, shuffled_sorted)


def test_shuffled_query_does_not_change_observation() -> None:
    problem_a = build_problem(seed=206)
    problem_b = build_problem(seed=207)
    shuffled_map = shuffled_query_context_map([problem_a, problem_b])

    assert shuffled_map[problem_a.seed] == problem_b.query_context
    assert shuffled_map[problem_b.seed] == problem_a.query_context
    assert torch.equal(problem_a.observation, problem_a.observation)


def test_shuffled_controls_have_no_target_access() -> None:
    problem_a = build_problem(seed=208)
    problem_b = build_problem(seed=209)
    shuffled_first = shuffled_query_context_map([problem_a, problem_b])
    mutated_problem_b = build_problem(seed=209)
    mutated_problem_b = mutated_problem_b.__class__(
        **{**mutated_problem_b.__dict__, "target_indices": (mutated_problem_b.target_indices + 1).remainder(mutated_problem_b.config.domain_size)}
    )
    shuffled_second = shuffled_query_context_map([problem_a, mutated_problem_b])

    assert shuffled_first[problem_a.seed] == shuffled_second[problem_a.seed]


def test_weighted_initialization_uses_full_domain_and_nonzero_weights() -> None:
    problem = build_problem(seed=210)
    weights = build_prior_weights(problem, problem.context_hierarchy, problem.query_context, prior_strength=1.0)
    estimates = build_weighted_initial_estimates(problem, weights)

    assert tuple(weights.shape) == (problem.config.num_factors, problem.config.domain_size)
    assert torch.all(weights > 0).item() is True
    assert tuple(estimates.shape) == (problem.config.num_factors, problem.config.dimensions)


def test_increasing_prior_strength_boosts_context_candidates() -> None:
    problem = build_problem(seed=211)
    context_mass = problem.context_hierarchy.factor_l2_weights.sum(dim=(0, 1))
    query_context_index = int(torch.argmax(context_mass).item())
    query_context = problem.context_hierarchy.l2_labels[query_context_index]
    weak = build_prior_weights(problem, problem.context_hierarchy, query_context, prior_strength=0.5)
    strong = build_prior_weights(problem, problem.context_hierarchy, query_context, prior_strength=2.0)
    query_scores = problem.context_hierarchy.factor_l2_weights[:, :, query_context_index]
    factor_index = int(torch.argmax(query_scores.max(dim=-1).values - query_scores.min(dim=-1).values).item())
    top_index = int(torch.argmax(query_scores[factor_index]).item())
    weak_ratio = weak[factor_index, top_index].item() / weak[factor_index].min().item()
    strong_ratio = strong[factor_index, top_index].item() / strong[factor_index].min().item()

    assert strong_ratio > weak_ratio


def test_atomic_hv_not_changed_by_metadata_or_prior() -> None:
    problem = build_problem(seed=212)
    original_domains = problem.domains.clone()
    _ = degree_preserving_metadata_shuffle(problem.context_hierarchy, seed=1)
    weights = build_prior_weights(problem, problem.context_hierarchy, problem.query_context, prior_strength=1.0)
    _ = build_weighted_initial_estimates(problem, weights)

    assert torch.equal(problem.domains, original_domains)


def test_query_problem_anomaly_rate_creates_violations() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=6, structured_distractor_count=2)
    problem = build_query_trial_problem(
        config,
        seed=999,
        anomaly_rate=1.0,
        seed_split="test",
        context_config=SyntheticContextConfig(multi_membership_rate=1.0, tertiary_membership_rate=0.3),
    )

    assert problem.anomaly_count > 0


def test_l1_subset_is_superset_of_l2_and_global_contains_l1() -> None:
    problem = build_problem(seed=213)
    l2_size = max(2, (problem.config.domain_size + 3) // 4)
    l1_size = (problem.config.domain_size + 1) // 2
    l2_subset = select_l2_subset(problem, problem.context_hierarchy, problem.query_context, l2_size)
    l1_subset = select_l1_subset(problem, problem.context_hierarchy, problem.query_context, l2_subset, l1_size)
    global_subset = full_candidate_indices(problem)

    for factor_index in range(problem.config.num_factors):
        assert set(l2_subset[factor_index].tolist()).issubset(set(l1_subset[factor_index].tolist()))
        assert set(l1_subset[factor_index].tolist()).issubset(set(global_subset[factor_index].tolist()))


def test_stage_observations_identical_and_stability_consistent() -> None:
    problem = build_problem(seed=214)
    original_observation = problem.observation.clone()
    snapshots, stability = build_stage_snapshots(
        problem,
        operating_point_label="TEST",
        master_seed=LEVEL1D_EVAL_MASTER_SEED,
        context_accuracy=0.9,
        shuffled_query_context=problem.query_context,
    )

    assert torch.equal(problem.observation, original_observation)
    assert stability["l2_prediction_survives_l1"] == (
        snapshots["L2_narrow"].predicted_tuple == snapshots["L1_parent"].predicted_tuple
    )
    assert stability["l2_prediction_survives_global"] == (
        snapshots["L2_narrow"].predicted_tuple == snapshots["global"].predicted_tuple
    )


def test_calibration_and_evaluation_seeds_do_not_overlap() -> None:
    assert level1d_calibration_seed_set().isdisjoint(level1d_evaluation_seed_set())
    assert non_overlapping_seed_sets() is True
    assert LEVEL1D_CALIBRATION_MASTER_SEED != LEVEL1D_EVAL_MASTER_SEED


def test_serialization_and_schema_version(tmp_path: Path) -> None:
    problem = build_problem(seed=215)
    result, _ = run_query_trial(
        problem,
        operating_point_label="TEST",
        master_seed=LEVEL1D_EVAL_MASTER_SEED,
        method=METHOD_GLOBAL_UNIFORM,
    )
    summary = summarize_query_trials([result])
    trials_path = tmp_path / "trials.jsonl"
    summary_path = tmp_path / "summary.csv"
    payload_path = tmp_path / "payload.json"

    save_trials_jsonl(trials_path, [result])
    save_summary_csv(summary_path, summary)
    save_json(payload_path, {"schema_version": QUERY_SCHEMA_VERSION})

    trial_payload = json.loads(trials_path.read_text(encoding="utf-8").strip())
    assert trial_payload["schema_version"] == QUERY_SCHEMA_VERSION
    assert "query_valid_recovery_rate" in summary_path.read_text(encoding="utf-8")
    assert json.loads(payload_path.read_text(encoding="utf-8"))["schema_version"] == QUERY_SCHEMA_VERSION


def test_upstream_torchhd_resonator_is_used(monkeypatch) -> None:
    problem = build_problem(seed=216)
    call_counter = {"count": 0}
    original = torchhd.resonator

    def wrapped(*args, **kwargs):
        call_counter["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(torchhd, "resonator", wrapped)
    result, _ = run_query_trial(
        problem,
        operating_point_label="TEST",
        master_seed=LEVEL1D_EVAL_MASTER_SEED,
        method=METHOD_HARD_L2_TOPK,
        context_accuracy=0.9,
    )

    assert call_counter["count"] > 0
    assert result.uses_upstream_resonator is True
