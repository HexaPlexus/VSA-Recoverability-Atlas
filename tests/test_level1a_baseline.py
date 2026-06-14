from __future__ import annotations

import json
from pathlib import Path

import torch

from cgrn_hsr.baseline import (
    BENCHMARK_SCHEMA_VERSION,
    BaselineConfig,
    build_initial_estimates,
    build_trial_problem,
    classify_false_consensus,
    classify_unsettled_failure,
    confirmation_seed_set,
    cosine_similarity_matrix,
    decode_top_candidates,
    method_selection_seed,
    normalized_similarity_pair,
    pilot_seed_set,
    run_trial,
    run_trial_on_problem,
    save_confirmation_payload,
    save_summary_csv,
    save_trials_jsonl,
    select_candidate_indices,
    summarize_trials,
)


def test_schema_version_and_structured_distractor_field() -> None:
    assert BENCHMARK_SCHEMA_VERSION == "level1a-baseline-v2"
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=2)
    assert config.structured_distractor_count == 2
    assert "SD2" in config.config_id()


def test_trial_is_deterministic_for_same_seed() -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, structured_distractor_count=0)
    first = run_trial(config, seed=12345, master_seed=20260614, operating_point_label="TEST")
    second = run_trial(config, seed=12345, master_seed=20260614, operating_point_label="TEST")

    assert first.to_dict() == second.to_dict()


def test_problem_generation_shapes_and_ground_truth() -> None:
    config = BaselineConfig(dimensions=256, num_factors=4, domain_size=7, structured_distractor_count=1)
    problem = build_trial_problem(config, seed=55)

    assert tuple(problem.domains.shape) == (4, 7, 256)
    assert tuple(problem.ground_truth_indices.shape) == (4,)
    assert tuple(problem.ground_truth_factors.shape) == (4, 256)
    assert tuple(problem.clean_composite.shape) == (256,)
    assert tuple(problem.observation.shape) == (256,)
    assert tuple(problem.structured_distractors.shape) == (1, 256)
    assert torch.all(problem.ground_truth_indices.ge(0)).item()
    assert torch.all(problem.ground_truth_indices.lt(config.domain_size)).item()


def test_easy_configuration_exact_recovery() -> None:
    config = BaselineConfig(dimensions=1000, num_factors=3, domain_size=5, structured_distractor_count=0)
    result = run_trial(config, seed=7, master_seed=20260614, operating_point_label="EASY")

    assert result.exact_recovery is True
    assert result.false_consensus is False
    assert result.unsettled_failure is False
    assert result.predicted_indices == result.ground_truth_indices


def test_false_consensus_and_unsettled_failure_classification() -> None:
    assert classify_false_consensus(stable_prediction=True, exact_recovery=False) is True
    assert classify_false_consensus(stable_prediction=False, exact_recovery=False) is False
    assert classify_unsettled_failure(stable_prediction=False, exact_recovery=False) is True
    assert classify_unsettled_failure(stable_prediction=True, exact_recovery=False) is False


def test_normalized_similarity_range() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=0)
    problem = build_trial_problem(config, seed=101)
    estimates = build_initial_estimates(problem.domains)
    similarities = cosine_similarity_matrix(estimates, problem.domains)
    decoded = decode_top_candidates(similarities)
    reconstruction_similarity = normalized_similarity_pair(problem.clean_composite, problem.observation)

    assert torch.all(similarities.le(1.0 + 1e-6)).item()
    assert torch.all(similarities.ge(-1.0 - 1e-6)).item()
    assert torch.all(decoded["margins"].le(2.0 + 1e-6)).item()
    assert torch.all(decoded["margins"].ge(-2.0 - 1e-6)).item()
    assert -1.0 - 1e-6 <= reconstruction_similarity <= 1.0 + 1e-6


def test_deterministic_random_subset_selection_and_exact_size() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=8, structured_distractor_count=0)
    problem = build_trial_problem(config, seed=202)
    seed = method_selection_seed(problem.seed, "random_unconditional", "half")
    first = select_candidate_indices(problem, "random_unconditional", 4, seed)
    second = select_candidate_indices(problem, "random_unconditional", 4, seed)

    assert torch.equal(first, second)
    assert tuple(first.shape) == (3, 4)


def test_random_truth_included_always_contains_ground_truth() -> None:
    config = BaselineConfig(dimensions=256, num_factors=4, domain_size=10, structured_distractor_count=0)
    problem = build_trial_problem(config, seed=303)
    indices = select_candidate_indices(
        problem,
        "random_truth_included",
        5,
        method_selection_seed(problem.seed, "random_truth_included", "half"),
    )

    for factor_index in range(config.num_factors):
        assert int(problem.ground_truth_indices[factor_index].item()) in indices[factor_index].tolist()


def test_random_unconditional_has_no_hidden_truth_access() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=12, structured_distractor_count=0)
    problem = build_trial_problem(config, seed=404)
    subset_size = 3
    saw_missing_truth = False
    for offset in range(20):
        indices = select_candidate_indices(problem, "random_unconditional", subset_size, problem.seed + offset)
        inclusion = indices.eq(problem.ground_truth_indices.unsqueeze(-1)).any(dim=-1)
        if not bool(inclusion.all().item()):
            saw_missing_truth = True
            break

    assert saw_missing_truth is True


def test_paired_trials_share_same_observation() -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, structured_distractor_count=2)
    problem = build_trial_problem(config, seed=505)
    global_result = run_trial_on_problem(problem, master_seed=1, operating_point_label="PAIR")
    pruned_result = run_trial_on_problem(
        problem,
        master_seed=1,
        operating_point_label="PAIR",
        method="random_truth_included",
        reduction_ratio_label="half",
        subset_size=3,
        selection_seed=method_selection_seed(problem.seed, "random_truth_included", "half"),
    )

    assert global_result.problem_id == pruned_result.problem_id
    assert global_result.ground_truth_indices == pruned_result.ground_truth_indices


def test_result_serialization_roundtrip(tmp_path: Path) -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, structured_distractor_count=0)
    result = run_trial(config, seed=123, master_seed=20260614, operating_point_label="SERIALIZE")
    summary_rows = summarize_trials([result])

    trials_path = tmp_path / "trials.jsonl"
    summary_path = tmp_path / "summary.csv"
    confirmation_path = tmp_path / "confirmation.json"

    save_trials_jsonl(trials_path, [result])
    save_summary_csv(summary_path, summary_rows)
    save_confirmation_payload(
        confirmation_path,
        confirmation_rows=summary_rows,
        seed_ranges={"SERIALIZE": {"start": 1, "count": 1}},
        level1a_commit="deadbeef",
    )

    trial_lines = trials_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(trial_lines) == 1
    assert json.loads(trial_lines[0])["config_id"] == config.config_id()

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "exact_recovery_rate" in summary_text
    assert config.config_id() in summary_text

    payload = json.loads(confirmation_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == BENCHMARK_SCHEMA_VERSION
    assert payload["level1a_commit"] == "deadbeef"


def test_confirmation_seed_ranges_do_not_overlap_pilot() -> None:
    assert pilot_seed_set().isdisjoint(confirmation_seed_set())
