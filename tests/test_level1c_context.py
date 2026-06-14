from __future__ import annotations

from dataclasses import replace

import torch

from cgrn_hsr.baseline import (
    BaselineConfig,
    SyntheticContextConfig,
    build_contextual_trial_problem,
    build_trial_problem,
    method_selection_seed,
    predict_l2_context,
    run_trial_on_problem,
    select_candidate_indices,
)


def test_context_metadata_does_not_change_hv_tensors() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=6, structured_distractor_count=0)
    plain_problem = build_trial_problem(config, seed=111)
    contextual_problem = build_contextual_trial_problem(config, seed=111, anomaly_rate=0.1)

    assert torch.equal(plain_problem.domains, contextual_problem.domains)


def test_atom_can_belong_to_multiple_contexts() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=8, structured_distractor_count=0)
    problem = build_contextual_trial_problem(
        config,
        seed=222,
        anomaly_rate=0.0,
        context_config=SyntheticContextConfig(multi_membership_rate=1.0, tertiary_membership_rate=0.0),
    )
    nonzero_counts = (problem.context_hierarchy.factor_l2_weights > 0).sum(dim=-1)

    assert torch.any(nonzero_counts >= 2).item() is True


def test_oracle_context_selector_does_not_read_target_indices() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=8, structured_distractor_count=0)
    problem = build_contextual_trial_problem(config, seed=333, anomaly_rate=0.1)
    subset_size = 4
    selection_seed = method_selection_seed(problem.seed, "oracle_l2_context", "half")
    baseline_indices, _, _ = select_candidate_indices(
        problem,
        "oracle_l2_context",
        subset_size,
        selection_seed,
    )
    shifted_target = (problem.target_indices + 1).remainder(config.domain_size)
    mutated_problem = replace(
        problem,
        target_indices=shifted_target,
        ground_truth_indices=shifted_target,
    )
    mutated_indices, _, _ = select_candidate_indices(
        mutated_problem,
        "oracle_l2_context",
        subset_size,
        selection_seed,
    )

    assert torch.equal(baseline_indices, mutated_indices)


def test_predicted_context_obeys_configured_accuracy_statistically() -> None:
    config = BaselineConfig(dimensions=256, num_factors=3, domain_size=6, structured_distractor_count=0)
    problem = build_contextual_trial_problem(config, seed=444, anomaly_rate=0.0)
    total = 400
    for expected_accuracy in (0.9, 0.7):
        correct = 0
        for offset in range(total):
            _, is_correct = predict_l2_context(
                hierarchy=problem.context_hierarchy,
                active_l2=problem.active_l2,
                context_accuracy=expected_accuracy,
                selection_seed=10_000 + offset,
            )
            correct += int(is_correct)
        observed = correct / total
        assert abs(observed - expected_accuracy) < 0.08


def test_context_subset_selection_exact_size_and_determinism() -> None:
    config = BaselineConfig(dimensions=256, num_factors=4, domain_size=10, structured_distractor_count=0)
    problem = build_contextual_trial_problem(config, seed=555, anomaly_rate=0.1)
    selection_seed = method_selection_seed(problem.seed, "predicted_l2_context", "quarter")
    first, predicted_l2_first, correct_first = select_candidate_indices(
        problem,
        "predicted_l2_context",
        3,
        selection_seed,
        context_accuracy=0.7,
    )
    second, predicted_l2_second, correct_second = select_candidate_indices(
        problem,
        "predicted_l2_context",
        3,
        selection_seed,
        context_accuracy=0.7,
    )

    assert tuple(first.shape) == (4, 3)
    assert torch.equal(first, second)
    assert predicted_l2_first == predicted_l2_second
    assert correct_first == correct_second


def test_context_paired_methods_share_same_problem_and_observation() -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, structured_distractor_count=2)
    problem = build_contextual_trial_problem(config, seed=666, anomaly_rate=0.25)
    oracle_result = run_trial_on_problem(
        problem,
        master_seed=1,
        operating_point_label="PAIR_CTX",
        method="oracle_l2_context",
        reduction_ratio_label="half",
        subset_size=3,
        selection_seed=method_selection_seed(problem.seed, "oracle_l2_context", "half"),
    )
    predicted_result = run_trial_on_problem(
        problem,
        master_seed=1,
        operating_point_label="PAIR_CTX",
        method="predicted_l2_context",
        reduction_ratio_label="half",
        subset_size=3,
        selection_seed=method_selection_seed(problem.seed, "predicted_l2_context", "half"),
        context_accuracy=0.9,
    )

    assert oracle_result.problem_id == predicted_result.problem_id
    assert oracle_result.target_indices == predicted_result.target_indices
    assert oracle_result.structured_distractor_indices == predicted_result.structured_distractor_indices
    assert oracle_result.active_l2 == predicted_result.active_l2


def test_anomaly_sampling_creates_context_violations() -> None:
    config = BaselineConfig(dimensions=256, num_factors=4, domain_size=6, structured_distractor_count=0)
    problem = build_contextual_trial_problem(config, seed=777, anomaly_rate=1.0)

    assert problem.anomaly_count == config.num_factors
    assert all(source != "active_l2" for source in problem.anomaly_sources)
