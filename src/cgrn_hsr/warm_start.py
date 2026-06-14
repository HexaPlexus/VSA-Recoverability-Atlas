from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
import torchhd

from .baseline import (
    METHOD_PREDICTED_L2_CONTEXT,
    bind_sequence,
    build_initial_estimates,
    cosine_similarity_matrix,
    decode_top_candidates,
    factors_from_indices,
    method_selection_seed,
    normalized_similarity_pair,
    pilot_seed_set,
    predict_l2_context,
    seed_everything,
    wilson_interval,
)
from .query_context import (
    QUERY_OUTCOME_EQUIVALENT_VALID,
    QUERY_OUTCOME_TARGET_RECOVERY,
    QueryTrialProblem,
    classify_query_outcome,
    full_candidate_indices,
    level1d_calibration_seed_set,
    level1d_evaluation_seed_set,
    query_valid_source_included,
    reference_tuple_mean_rank,
    select_l1_subset,
    select_l2_subset,
    slice_candidate_domains,
    stage_subset_sizes,
)
from .selective_policy import (
    GlobalRuntimeEvidence,
    L2RuntimeEvidence,
    PolicyThresholds,
    global_accepts,
    l2_accepts,
    level1e_calibration_seed_set,
    level1e_development_seed_set,
    level1e_heldout_seed_set,
)

WARM_START_SCHEMA_VERSION = "level1-warm-start-v1"
WARM_START_METHOD_VERSION = "budget-matched-warm-start-v1"
L2_GATE_VERSION = "level1e-frozen-l2-v1"
GLOBAL_GATE_VERSION = "level1e-frozen-global-v1"

LEVEL1E1_DEVELOPMENT_MASTER_SEED = 28260614
LEVEL1E1_CALIBRATION_MASTER_SEED = 29260614
LEVEL1E1_HELDOUT_MASTER_SEED = 30260614
LEVEL1E1_DEVELOPMENT_TRIALS_PER_CELL = 24
LEVEL1E1_CALIBRATION_TRIALS_PER_CELL = 24
LEVEL1E1_HELDOUT_TRIALS_PER_CELL = 64

RECOVERY_TOLERANCE = 0.05
MEANINGFUL_COVERAGE_FLOOR = 0.05

METHOD_ALWAYS_GLOBAL_COLD = "always_global_cold"
METHOD_L2_THEN_COLD_GLOBAL = "l2_then_cold_global"
METHOD_L2_THEN_WARM_GLOBAL = "l2_then_warm_global"
METHOD_L2_PROBE1_THEN_WARM_GLOBAL = "l2_probe1_then_warm_global"
METHOD_L2_PROBE2_THEN_WARM_GLOBAL = "l2_probe2_then_warm_global"
METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED = "l2_then_warm_global_uncapped"

POLICY_ACCEPT_CORRECT_L2 = "ACCEPT_CORRECT_L2"
POLICY_ACCEPT_WRONG_L2 = "ACCEPT_WRONG_L2"
POLICY_ACCEPT_CORRECT_GLOBAL = "ACCEPT_CORRECT_GLOBAL"
POLICY_ACCEPT_WRONG_GLOBAL = "ACCEPT_WRONG_GLOBAL"
POLICY_ABSTAIN = "ABSTAIN"
POLICY_ABSTAIN_BUDGET_EXHAUSTED = "ABSTAIN_BUDGET_EXHAUSTED"

PREFERRED_WARM_METHOD_ORDER = (
    METHOD_L2_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
)

FROZEN_L2_GATE_THRESHOLDS = PolicyThresholds(
    l2_min_margin=0.05,
    l2_reconstruction=0.15,
    l1_rank_max=1.0,
    l1_min_margin=0.05,
    global_min_margin=0.05,
    global_reconstruction=0.05,
)
FROZEN_GLOBAL_GATE_THRESHOLDS = FROZEN_L2_GATE_THRESHOLDS


@dataclass(frozen=True)
class WarmStartStage:
    stage_label: str
    candidate_count: int
    iterations_used: int
    stable_prediction: bool
    stable_iterations: int
    predicted_indices: list[int]
    normalized_top1_scores: list[float]
    normalized_top2_scores: list[float]
    normalized_margins: list[float]
    normalized_reconstruction_similarity: float
    query_outcome_class: str
    valid_recovery: bool
    exact_recovery: bool
    factor_candidate_recall: list[bool]
    all_truth_included: bool
    candidate_evaluations_proxy: int
    element_operations_proxy: int
    query_valid_source_included: bool


@dataclass(frozen=True)
class ProbeEvidence:
    steps_requested: int
    steps_executed: int
    predicted_indices: list[int]
    l2_tuple_survives_probe: bool
    factor_survival_fraction: float
    prediction_agreement: float
    probe_min_margin: float
    probe_mean_margin: float
    probe_reconstruction: float
    probe_rank: float


@dataclass(frozen=True)
class StageExecution:
    stage: WarmStartStage
    final_estimates: torch.Tensor
    final_similarities: torch.Tensor


@dataclass(frozen=True)
class ProbeExecution:
    evidence: ProbeEvidence
    final_estimates: torch.Tensor
    final_similarities: torch.Tensor


@dataclass(frozen=True)
class WarmMethodTrialResult:
    schema_version: str
    method_version: str
    seed_split: str
    cell_id: str
    operating_point_label: str
    method_id: str
    seed: int
    anomaly_rate: float
    context_accuracy: float
    D: int
    F: int
    M: int
    structured_distractor_count: int
    budget_mode: str
    global_budget_candidate_evaluations: int
    global_budget_element_operations: int
    candidate_evaluations: int
    element_operations_proxy: int
    total_iterations: int
    l2_iterations: int
    probe_steps_requested: int
    probe_steps_executed: int
    global_iterations: int
    cold_global_iterations: int
    warm_global_iterations: int
    iterations_saved_vs_cold: int | None
    accepted_stage: str | None
    accepted_correct: bool
    policy_outcome: str
    abstain_reason: str | None
    l2_accepted: bool
    ran_l2: bool
    ran_probe: bool
    ran_global: bool
    budget_exhausted: bool
    warm_start_used: bool
    warm_start_initial_prediction: list[int] | None
    final_prediction: list[int]
    prediction_changed_after_expansion: bool | None
    warm_start_initial_query_outcome: str | None
    final_query_outcome: str
    final_valid_recovery: bool
    final_exact_recovery: bool
    l2_prediction_correct: bool
    l2_predicted_indices: list[int]
    predicted_l2_context: str
    context_prediction_correct: bool
    l2_stage: dict[str, Any]
    probe_evidence: dict[str, Any] | None
    global_stage: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelectedMethodRecord:
    schema_version: str
    method_version: str
    selected_method: str
    l2_gate_version: str
    global_gate_version: str
    budget_definition: dict[str, str]
    probe_steps: int
    seed_ranges: dict[str, dict[str, dict[str, int]]]
    selection_rule: str
    gate_result: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def level1e1_development_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E1_DEVELOPMENT_MASTER_SEED, "count": LEVEL1E1_DEVELOPMENT_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E1_DEVELOPMENT_MASTER_SEED + 10_000, "count": LEVEL1E1_DEVELOPMENT_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E1_DEVELOPMENT_MASTER_SEED + 20_000, "count": LEVEL1E1_DEVELOPMENT_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E1_DEVELOPMENT_MASTER_SEED + 30_000, "count": LEVEL1E1_DEVELOPMENT_TRIALS_PER_CELL},
    }


def level1e1_calibration_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E1_CALIBRATION_MASTER_SEED, "count": LEVEL1E1_CALIBRATION_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E1_CALIBRATION_MASTER_SEED + 10_000, "count": LEVEL1E1_CALIBRATION_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E1_CALIBRATION_MASTER_SEED + 20_000, "count": LEVEL1E1_CALIBRATION_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E1_CALIBRATION_MASTER_SEED + 30_000, "count": LEVEL1E1_CALIBRATION_TRIALS_PER_CELL},
    }


def level1e1_heldout_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E1_HELDOUT_MASTER_SEED, "count": LEVEL1E1_HELDOUT_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E1_HELDOUT_MASTER_SEED + 10_000, "count": LEVEL1E1_HELDOUT_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E1_HELDOUT_MASTER_SEED + 20_000, "count": LEVEL1E1_HELDOUT_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E1_HELDOUT_MASTER_SEED + 30_000, "count": LEVEL1E1_HELDOUT_TRIALS_PER_CELL},
    }


def seed_ranges_to_set(seed_ranges: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in seed_ranges.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level1e1_development_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e1_development_seed_ranges())


def level1e1_calibration_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e1_calibration_seed_ranges())


def level1e1_heldout_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e1_heldout_seed_ranges())


def warm_start_seed_sets_non_overlapping() -> bool:
    current_sets = (
        level1e1_development_seed_set(),
        level1e1_calibration_seed_set(),
        level1e1_heldout_seed_set(),
    )
    prior_sets = (
        level1d_calibration_seed_set(),
        level1d_evaluation_seed_set(),
        level1e_development_seed_set(),
        level1e_calibration_seed_set(),
        level1e_heldout_seed_set(),
        pilot_seed_set(),
    )
    return (
        current_sets[0].isdisjoint(current_sets[1])
        and current_sets[0].isdisjoint(current_sets[2])
        and current_sets[1].isdisjoint(current_sets[2])
        and all(current.isdisjoint(prior) for current in current_sets for prior in prior_sets)
    )


def correct_query_outcome(query_outcome: str) -> bool:
    return query_outcome in (QUERY_OUTCOME_TARGET_RECOVERY, QUERY_OUTCOME_EQUIVALENT_VALID)


def tuple_agreement_fraction(lhs: list[int], rhs: list[int]) -> float:
    return sum(int(left == right) for left, right in zip(lhs, rhs, strict=False)) / len(lhs)


def stage_min_margin(stage: WarmStartStage) -> float:
    return float(min(stage.normalized_margins))


def stage_mean_margin(stage: WarmStartStage) -> float:
    return float(statistics.fmean(stage.normalized_margins))


def predict_l2_for_problem(problem: QueryTrialProblem, context_accuracy: float) -> tuple[str, bool]:
    return predict_l2_context(
        hierarchy=problem.context_hierarchy,
        active_l2=problem.query_context,
        context_accuracy=context_accuracy,
        selection_seed=method_selection_seed(problem.seed, METHOD_PREDICTED_L2_CONTEXT, "quarter"),
    )


def build_contextual_candidate_indices(
    problem: QueryTrialProblem,
    predicted_l2_context: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    l2_subset_size, l1_subset_size = stage_subset_sizes(problem.config.domain_size)
    l2_indices = select_l2_subset(problem, problem.context_hierarchy, predicted_l2_context, l2_subset_size)
    l1_indices = select_l1_subset(problem, problem.context_hierarchy, predicted_l2_context, l2_indices, l1_subset_size)
    return l2_indices, l1_indices, full_candidate_indices(problem)


def decode_estimates(
    problem: QueryTrialProblem,
    candidate_indices: torch.Tensor,
    estimates: torch.Tensor,
) -> tuple[list[int], str]:
    candidate_domains = slice_candidate_domains(problem, candidate_indices)
    similarities = cosine_similarity_matrix(estimates, candidate_domains)
    decoded = decode_top_candidates(similarities)
    predicted_full = candidate_indices.gather(1, decoded["top1_indices"].unsqueeze(-1)).squeeze(-1)
    return [int(value) for value in predicted_full.tolist()], classify_query_outcome(problem, False, predicted_full)


def summarize_stage(
    problem: QueryTrialProblem,
    candidate_indices: torch.Tensor,
    current_estimates: torch.Tensor,
    final_similarities: torch.Tensor,
    decoded: dict[str, torch.Tensor],
    stable_prediction: bool,
    stable_iterations: int,
    iterations_used: int,
    stage_label: str,
) -> WarmStartStage:
    predicted_full = candidate_indices.gather(1, decoded["top1_indices"].unsqueeze(-1)).squeeze(-1)
    predicted_factors = factors_from_indices(problem.domains, predicted_full)
    reconstruction = bind_sequence(predicted_factors)
    truth_included_per_factor = candidate_indices.eq(problem.designated_target_tuple.unsqueeze(-1)).any(dim=-1)
    exact_recovery = bool(predicted_full.eq(problem.designated_target_tuple).all().item())
    query_outcome = classify_query_outcome(problem, stable_prediction, predicted_full)
    candidate_count = candidate_indices.size(1)
    candidate_evaluations = iterations_used * problem.config.num_factors * candidate_count
    return WarmStartStage(
        stage_label=stage_label,
        candidate_count=candidate_count,
        iterations_used=iterations_used,
        stable_prediction=stable_prediction,
        stable_iterations=stable_iterations,
        predicted_indices=[int(value) for value in predicted_full.tolist()],
        normalized_top1_scores=[float(value) for value in decoded["top1_scores"].tolist()],
        normalized_top2_scores=[float(value) for value in decoded["top2_scores"].tolist()],
        normalized_margins=[float(value) for value in decoded["margins"].tolist()],
        normalized_reconstruction_similarity=normalized_similarity_pair(reconstruction, problem.observation),
        query_outcome_class=query_outcome,
        valid_recovery=correct_query_outcome(query_outcome),
        exact_recovery=exact_recovery,
        factor_candidate_recall=truth_included_per_factor.tolist(),
        all_truth_included=bool(truth_included_per_factor.all().item()),
        candidate_evaluations_proxy=candidate_evaluations,
        element_operations_proxy=candidate_evaluations * problem.config.dimensions,
        query_valid_source_included=query_valid_source_included(problem, candidate_indices),
    )


def run_iterative_stage(
    problem: QueryTrialProblem,
    candidate_indices: torch.Tensor,
    initial_estimates: torch.Tensor,
    max_iterations: int,
    stage_label: str,
) -> StageExecution:
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive.")

    candidate_domains = slice_candidate_domains(problem, candidate_indices)
    current_estimates = initial_estimates.clone()
    previous_indices: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    decoded: dict[str, torch.Tensor] | None = None
    final_similarities: torch.Tensor | None = None

    for iteration in range(1, max_iterations + 1):
        current_estimates = torchhd.resonator(problem.observation, current_estimates, candidate_domains)
        final_similarities = cosine_similarity_matrix(current_estimates, candidate_domains)
        decoded = decode_top_candidates(final_similarities)
        predicted_full = candidate_indices.gather(1, decoded["top1_indices"].unsqueeze(-1)).squeeze(-1)
        if previous_indices is not None and torch.equal(predicted_full, previous_indices):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_indices = predicted_full.clone()
        if stable_iterations >= problem.config.stable_patience:
            stable_prediction = True
            break

    if decoded is None or final_similarities is None:
        raise RuntimeError("Iterative stage did not execute resonator.")

    return StageExecution(
        stage=summarize_stage(
            problem,
            candidate_indices,
            current_estimates,
            final_similarities,
            decoded,
            stable_prediction=stable_prediction,
            stable_iterations=stable_iterations,
            iterations_used=iteration,
            stage_label=stage_label,
        ),
        final_estimates=current_estimates,
        final_similarities=final_similarities,
    )


def run_probe_stage(
    problem: QueryTrialProblem,
    candidate_indices: torch.Tensor,
    initial_estimates: torch.Tensor,
    steps: int,
    reference_indices: list[int],
) -> ProbeExecution:
    if steps <= 0:
        raise ValueError("Probe steps must be positive.")

    candidate_domains = slice_candidate_domains(problem, candidate_indices)
    current_estimates = initial_estimates.clone()
    for _ in range(steps):
        current_estimates = torchhd.resonator(problem.observation, current_estimates, candidate_domains)

    final_similarities = cosine_similarity_matrix(current_estimates, candidate_domains)
    decoded = decode_top_candidates(final_similarities)
    predicted_full = candidate_indices.gather(1, decoded["top1_indices"].unsqueeze(-1)).squeeze(-1)
    reference_tensor = torch.tensor(reference_indices, dtype=torch.long)
    predicted_list = [int(value) for value in predicted_full.tolist()]
    evidence = ProbeEvidence(
        steps_requested=steps,
        steps_executed=steps,
        predicted_indices=predicted_list,
        l2_tuple_survives_probe=predicted_list == reference_indices,
        factor_survival_fraction=tuple_agreement_fraction(reference_indices, predicted_list),
        prediction_agreement=tuple_agreement_fraction(reference_indices, predicted_list),
        probe_min_margin=float(min(float(value) for value in decoded["margins"].tolist())),
        probe_mean_margin=float(statistics.fmean(float(value) for value in decoded["margins"].tolist())),
        probe_reconstruction=normalized_similarity_pair(
            bind_sequence(factors_from_indices(problem.domains, predicted_full)),
            problem.observation,
        ),
        probe_rank=reference_tuple_mean_rank(candidate_indices, final_similarities, reference_tensor),
    )
    return ProbeExecution(evidence=evidence, final_estimates=current_estimates, final_similarities=final_similarities)


def make_l2_runtime_evidence(stage: WarmStartStage) -> L2RuntimeEvidence:
    return L2RuntimeEvidence(
        stable_prediction_l2=stage.stable_prediction,
        iterations_l2=stage.iterations_used,
        min_normalized_margin_l2=stage_min_margin(stage),
        mean_normalized_margin_l2=stage_mean_margin(stage),
        normalized_reconstruction_l2=stage.normalized_reconstruction_similarity,
        context_confidence=0.0,
    )


def make_global_runtime_evidence(stage: WarmStartStage) -> GlobalRuntimeEvidence:
    return GlobalRuntimeEvidence(
        stable_prediction_global=stage.stable_prediction,
        iterations_global=stage.iterations_used,
        prediction_agreement_l1_global=0.0,
        l1_tuple_rank_at_global=0.0,
        normalized_reconstruction_global=stage.normalized_reconstruction_similarity,
        min_normalized_margin_global=stage_min_margin(stage),
        mean_normalized_margin_global=stage_mean_margin(stage),
    )


def frozen_l2_gate_accepts(stage: WarmStartStage) -> bool:
    return l2_accepts(make_l2_runtime_evidence(stage), FROZEN_L2_GATE_THRESHOLDS)


def frozen_global_gate_accepts(stage: WarmStartStage) -> bool:
    return global_accepts(make_global_runtime_evidence(stage), FROZEN_GLOBAL_GATE_THRESHOLDS)


def global_budget_candidate_evaluations(problem: QueryTrialProblem) -> int:
    return problem.config.max_iterations * problem.config.num_factors * problem.config.domain_size


def global_budget_element_operations(problem: QueryTrialProblem) -> int:
    return global_budget_candidate_evaluations(problem) * problem.config.dimensions


def remaining_global_iterations(problem: QueryTrialProblem, used_candidate_evaluations: int) -> int:
    remaining_candidate_budget = global_budget_candidate_evaluations(problem) - used_candidate_evaluations
    return max(0, remaining_candidate_budget // (problem.config.num_factors * problem.config.domain_size))


def compute_policy_outcome(accepted_stage: str | None, accepted_correct: bool, budget_exhausted: bool) -> str:
    if budget_exhausted:
        return POLICY_ABSTAIN_BUDGET_EXHAUSTED
    if accepted_stage is None:
        return POLICY_ABSTAIN
    if accepted_stage == "L2":
        return POLICY_ACCEPT_CORRECT_L2 if accepted_correct else POLICY_ACCEPT_WRONG_L2
    if accepted_stage == "GLOBAL":
        return POLICY_ACCEPT_CORRECT_GLOBAL if accepted_correct else POLICY_ACCEPT_WRONG_GLOBAL
    raise ValueError(f"Unsupported accepted stage: {accepted_stage}")


def run_method_trial(
    problem: QueryTrialProblem,
    cell_id: str,
    operating_point_label: str,
    method_id: str,
    master_seed: int,
    context_accuracy: float,
) -> WarmMethodTrialResult:
    seed_everything(problem.seed)
    predicted_l2_context, context_prediction_correct = predict_l2_for_problem(problem, context_accuracy)
    l2_indices, l1_indices, full_indices = build_contextual_candidate_indices(problem, predicted_l2_context)
    l2_initial_estimates = build_initial_estimates(slice_candidate_domains(problem, l2_indices))
    l2_execution = run_iterative_stage(problem, l2_indices, l2_initial_estimates, problem.config.max_iterations, "L2_narrow")
    l2_stage = l2_execution.stage
    l2_prediction_correct = correct_query_outcome(l2_stage.query_outcome_class)

    total_candidate_evaluations = 0
    total_element_operations = 0
    total_iterations = 0
    probe_steps_requested = 0
    probe_steps_executed = 0
    probe_evidence: ProbeEvidence | None = None
    global_stage: WarmStartStage | None = None
    accepted_stage: str | None = None
    accepted_correct = False
    abstain_reason: str | None = None
    budget_exhausted = False
    ran_l2 = method_id != METHOD_ALWAYS_GLOBAL_COLD
    ran_probe = False
    ran_global = False
    warm_start_used = False
    warm_start_initial_prediction: list[int] | None = None
    warm_start_initial_query_outcome: str | None = None
    final_prediction: list[int]
    final_query_outcome: str
    final_valid_recovery: bool
    final_exact_recovery: bool
    cold_global_iterations = 0
    warm_global_iterations = 0
    budget_mode = "uncapped_diagnostic" if method_id == METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED else "budget_matched"
    global_budget_candidates = global_budget_candidate_evaluations(problem)
    global_budget_ops = global_budget_element_operations(problem)

    if method_id == METHOD_ALWAYS_GLOBAL_COLD:
        global_initial_estimates = build_initial_estimates(problem.domains)
        initial_prediction, initial_outcome = decode_estimates(problem, full_indices, global_initial_estimates)
        global_execution = run_iterative_stage(problem, full_indices, global_initial_estimates, problem.config.max_iterations, "global")
        global_stage = global_execution.stage
        ran_global = True
        cold_global_iterations = global_stage.iterations_used
        total_candidate_evaluations = global_stage.candidate_evaluations_proxy
        total_element_operations = global_stage.element_operations_proxy
        total_iterations = global_stage.iterations_used
        warm_start_initial_prediction = initial_prediction
        warm_start_initial_query_outcome = initial_outcome
        if frozen_global_gate_accepts(global_stage):
            accepted_stage = "GLOBAL"
            accepted_correct = correct_query_outcome(global_stage.query_outcome_class)
        final_prediction = global_stage.predicted_indices
        final_query_outcome = global_stage.query_outcome_class
        final_valid_recovery = global_stage.valid_recovery
        final_exact_recovery = global_stage.exact_recovery
    else:
        total_candidate_evaluations += l2_stage.candidate_evaluations_proxy
        total_element_operations += l2_stage.element_operations_proxy
        total_iterations += l2_stage.iterations_used

        if frozen_l2_gate_accepts(l2_stage):
            accepted_stage = "L2"
            accepted_correct = l2_prediction_correct
            final_prediction = l2_stage.predicted_indices
            final_query_outcome = l2_stage.query_outcome_class
            final_valid_recovery = l2_stage.valid_recovery
            final_exact_recovery = l2_stage.exact_recovery
        else:
            current_estimates = l2_execution.final_estimates
            final_prediction = l2_stage.predicted_indices
            final_query_outcome = l2_stage.query_outcome_class
            final_valid_recovery = l2_stage.valid_recovery
            final_exact_recovery = l2_stage.exact_recovery

            if method_id == METHOD_L2_PROBE1_THEN_WARM_GLOBAL:
                probe_steps_requested = 1
            elif method_id == METHOD_L2_PROBE2_THEN_WARM_GLOBAL:
                probe_steps_requested = 2

            if probe_steps_requested > 0:
                probe_execution = run_probe_stage(
                    problem,
                    l1_indices,
                    current_estimates,
                    steps=probe_steps_requested,
                    reference_indices=l2_stage.predicted_indices,
                )
                probe_evidence = probe_execution.evidence
                current_estimates = probe_execution.final_estimates
                probe_steps_executed = probe_evidence.steps_executed
                ran_probe = True
                total_candidate_evaluations += probe_steps_executed * problem.config.num_factors * l1_indices.size(1)
                total_element_operations += probe_steps_executed * problem.config.num_factors * l1_indices.size(1) * problem.config.dimensions
                total_iterations += probe_steps_executed
                final_prediction = probe_evidence.predicted_indices
                final_query_outcome = classify_query_outcome(problem, False, torch.tensor(final_prediction, dtype=torch.long))

            if method_id == METHOD_L2_THEN_COLD_GLOBAL:
                current_estimates = build_initial_estimates(problem.domains)
                warm_start_used = False
            else:
                warm_start_used = True

            if method_id == METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED:
                max_global_iterations = problem.config.max_iterations
            else:
                max_global_iterations = remaining_global_iterations(problem, total_candidate_evaluations)

            if max_global_iterations <= 0:
                budget_exhausted = method_id != METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED
                abstain_reason = "BUDGET_EXHAUSTED" if budget_exhausted else None
                final_valid_recovery = correct_query_outcome(final_query_outcome)
                final_exact_recovery = final_prediction == problem.designated_target_tuple.tolist()
            else:
                warm_start_initial_prediction, warm_start_initial_query_outcome = decode_estimates(problem, full_indices, current_estimates)
                global_execution = run_iterative_stage(problem, full_indices, current_estimates, max_global_iterations, "global")
                global_stage = global_execution.stage
                ran_global = True
                total_candidate_evaluations += global_stage.candidate_evaluations_proxy
                total_element_operations += global_stage.element_operations_proxy
                total_iterations += global_stage.iterations_used
                final_prediction = global_stage.predicted_indices
                final_query_outcome = global_stage.query_outcome_class
                final_valid_recovery = global_stage.valid_recovery
                final_exact_recovery = global_stage.exact_recovery
                if method_id == METHOD_L2_THEN_COLD_GLOBAL:
                    cold_global_iterations = global_stage.iterations_used
                else:
                    warm_global_iterations = global_stage.iterations_used
                if frozen_global_gate_accepts(global_stage):
                    accepted_stage = "GLOBAL"
                    accepted_correct = correct_query_outcome(global_stage.query_outcome_class)
                else:
                    abstain_reason = "GLOBAL_GATE_REJECTED"

    if accepted_stage is None and abstain_reason is None:
        abstain_reason = "GLOBAL_GATE_REJECTED" if ran_global else None

    prediction_changed_after_expansion = (
        None
        if warm_start_initial_prediction is None
        else final_prediction != warm_start_initial_prediction
    )
    policy_outcome = compute_policy_outcome(accepted_stage, accepted_correct, budget_exhausted)
    return WarmMethodTrialResult(
        schema_version=WARM_START_SCHEMA_VERSION,
        method_version=WARM_START_METHOD_VERSION,
        seed_split=problem.seed_split,
        cell_id=cell_id,
        operating_point_label=operating_point_label,
        method_id=method_id,
        seed=problem.seed,
        anomaly_rate=problem.anomaly_rate,
        context_accuracy=context_accuracy,
        D=problem.config.dimensions,
        F=problem.config.num_factors,
        M=problem.config.domain_size,
        structured_distractor_count=problem.config.structured_distractor_count,
        budget_mode=budget_mode,
        global_budget_candidate_evaluations=global_budget_candidates,
        global_budget_element_operations=global_budget_ops,
        candidate_evaluations=total_candidate_evaluations,
        element_operations_proxy=total_element_operations,
        total_iterations=total_iterations,
        l2_iterations=l2_stage.iterations_used,
        probe_steps_requested=probe_steps_requested,
        probe_steps_executed=probe_steps_executed,
        global_iterations=(global_stage.iterations_used if global_stage is not None else 0),
        cold_global_iterations=cold_global_iterations,
        warm_global_iterations=warm_global_iterations,
        iterations_saved_vs_cold=None,
        accepted_stage=accepted_stage,
        accepted_correct=accepted_correct,
        policy_outcome=policy_outcome,
        abstain_reason=abstain_reason,
        l2_accepted=accepted_stage == "L2",
        ran_l2=ran_l2,
        ran_probe=ran_probe,
        ran_global=ran_global,
        budget_exhausted=budget_exhausted,
        warm_start_used=warm_start_used,
        warm_start_initial_prediction=warm_start_initial_prediction,
        final_prediction=final_prediction,
        prediction_changed_after_expansion=prediction_changed_after_expansion,
        warm_start_initial_query_outcome=warm_start_initial_query_outcome,
        final_query_outcome=final_query_outcome,
        final_valid_recovery=final_valid_recovery,
        final_exact_recovery=final_exact_recovery,
        l2_prediction_correct=l2_prediction_correct,
        l2_predicted_indices=l2_stage.predicted_indices,
        predicted_l2_context=predicted_l2_context,
        context_prediction_correct=context_prediction_correct,
        l2_stage=asdict(l2_stage),
        probe_evidence=(asdict(probe_evidence) if probe_evidence is not None else None),
        global_stage=(asdict(global_stage) if global_stage is not None else None),
    )


def summarize_method_trials(records: list[WarmMethodTrialResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[WarmMethodTrialResult]] = {}
    for record in records:
        grouped.setdefault((record.cell_id, record.method_id), []).append(record)

    rows = []
    for (cell_id, method_id), batch in sorted(grouped.items()):
        total = len(batch)
        accepted = [row for row in batch if row.accepted_stage is not None]
        correct = [row for row in accepted if row.accepted_correct]
        false_accept = [row for row in accepted if not row.accepted_correct]
        coverage = len(accepted) / total
        selective_risk = 0.0 if not accepted else 1.0 - (len(correct) / len(accepted))
        coverage_low, coverage_high = wilson_interval(len(accepted), total)
        if accepted:
            false_low, false_high = wilson_interval(len(false_accept), len(accepted))
        else:
            false_low, false_high = (0.0, 0.0)
        rows.append(
            {
                "schema_version": WARM_START_SCHEMA_VERSION,
                "cell_id": cell_id,
                "method_id": method_id,
                "trials": total,
                "coverage": coverage,
                "coverage_ci_low": coverage_low,
                "coverage_ci_high": coverage_high,
                "selective_risk": selective_risk,
                "selective_risk_ci_low": false_low,
                "selective_risk_ci_high": false_high,
                "false_accept_rate": len(false_accept) / total,
                "abstention_rate": sum(row.accepted_stage is None for row in batch) / total,
                "l2_accept_rate": sum(row.accepted_stage == "L2" for row in batch) / total,
                "global_escalation_rate": sum(row.ran_global for row in batch) / total,
                "budget_exhaustion_rate": sum(row.budget_exhausted for row in batch) / total,
                "exact_or_valid_recovery_rate": sum(row.final_valid_recovery for row in batch) / total,
                "overall_correct_accept_rate": len(correct) / total,
                "mean_compute": sum(row.element_operations_proxy for row in batch) / total,
                "median_compute": statistics.median(row.element_operations_proxy for row in batch),
                "p90_compute": sorted(row.element_operations_proxy for row in batch)[math.ceil(0.9 * total) - 1],
                "mean_total_iterations": sum(row.total_iterations for row in batch) / total,
                "mean_global_iterations": sum(row.global_iterations for row in batch) / total,
            }
        )
    return rows


def build_paired_comparisons(records: list[WarmMethodTrialResult]) -> list[dict[str, Any]]:
    by_key = {(record.cell_id, record.seed, record.method_id): record for record in records}
    rows = []
    for cell_id in sorted({record.cell_id for record in records}):
        for warm_method in (
            METHOD_L2_THEN_WARM_GLOBAL,
            METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
            METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
        ):
            seeds = sorted({
                record.seed
                for record in records
                if record.cell_id == cell_id and record.method_id == METHOD_L2_THEN_COLD_GLOBAL
            })
            warm_helped = 0
            warm_hurt = 0
            warm_same = 0
            recovery_deltas = []
            risk_flags = []
            compute_deltas = []
            global_iteration_deltas = []
            iteration_savings = []
            for seed in seeds:
                cold = by_key[(cell_id, seed, METHOD_L2_THEN_COLD_GLOBAL)]
                warm = by_key.get((cell_id, seed, warm_method))
                if warm is None:
                    continue
                cold_correct = cold.accepted_correct
                warm_correct = warm.accepted_correct
                if (not cold_correct) and warm_correct:
                    warm_helped += 1
                elif cold_correct and (not warm_correct):
                    warm_hurt += 1
                else:
                    warm_same += 1
                recovery_deltas.append(int(warm.final_valid_recovery) - int(cold.final_valid_recovery))
                risk_flags.append(int(warm.accepted_stage is not None and not warm.accepted_correct) - int(cold.accepted_stage is not None and not cold.accepted_correct))
                compute_deltas.append(warm.element_operations_proxy - cold.element_operations_proxy)
                global_iteration_deltas.append(warm.global_iterations - cold.global_iterations)
                iteration_savings.append(cold.global_iterations - warm.global_iterations)
            total = len(recovery_deltas)
            if total == 0:
                continue
            rows.append(
                {
                    "schema_version": WARM_START_SCHEMA_VERSION,
                    "cell_id": cell_id,
                    "warm_method": warm_method,
                    "cold_method": METHOD_L2_THEN_COLD_GLOBAL,
                    "trials": total,
                    "warm_vs_cold_recovery_delta": sum(recovery_deltas) / total,
                    "warm_vs_cold_selective_risk_delta": sum(risk_flags) / total,
                    "warm_vs_cold_compute_delta": sum(compute_deltas) / total,
                    "warm_vs_cold_global_iterations_delta": sum(global_iteration_deltas) / total,
                    "mean_iterations_saved_vs_cold": sum(iteration_savings) / total,
                    "warm_helped": warm_helped,
                    "warm_hurt": warm_hurt,
                    "warm_same": warm_same,
                }
            )
    return rows


def compute_probe_separation(records: list[WarmMethodTrialResult]) -> dict[str, Any]:
    payload: dict[str, Any] = {"schema_version": WARM_START_SCHEMA_VERSION, "methods": {}}
    for method_id in (METHOD_L2_PROBE1_THEN_WARM_GLOBAL, METHOD_L2_PROBE2_THEN_WARM_GLOBAL):
        method_rows = [record for record in records if record.method_id == method_id and record.probe_evidence is not None]
        by_cell: dict[str, Any] = {}
        for cell_id in sorted({record.cell_id for record in method_rows}):
            cell_rows = [record for record in method_rows if record.cell_id == cell_id]
            survives = [record for record in cell_rows if record.probe_evidence["l2_tuple_survives_probe"]]
            fails = [record for record in cell_rows if not record.probe_evidence["l2_tuple_survives_probe"]]

            def summarize(rows: list[WarmMethodTrialResult]) -> dict[str, Any]:
                total = len(rows)
                correct = sum(record.l2_prediction_correct for record in rows)
                if total == 0:
                    return {"rate": None, "ci_low": None, "ci_high": None, "total": 0}
                low, high = wilson_interval(correct, total)
                return {"rate": correct / total, "ci_low": low, "ci_high": high, "total": total}

            by_cell[cell_id] = {
                "P(correct | survives_probe)": summarize(survives),
                "P(correct | fails_probe)": summarize(fails),
            }
        payload["methods"][method_id] = by_cell
    return payload


def summary_lookup(summary_rows: list[dict[str, Any]], cell_id: str, method_id: str) -> dict[str, Any]:
    return next(row for row in summary_rows if row["cell_id"] == cell_id and row["method_id"] == method_id)


def method_probe_steps(method_id: str) -> int:
    if method_id == METHOD_L2_PROBE1_THEN_WARM_GLOBAL:
        return 1
    if method_id == METHOD_L2_PROBE2_THEN_WARM_GLOBAL:
        return 2
    return 0


def choose_selected_method(summary_rows: list[dict[str, Any]]) -> SelectedMethodRecord:
    primary_global = summary_lookup(summary_rows, "COLLAPSE_SINGLE_PRIMARY", METHOD_ALWAYS_GLOBAL_COLD)
    primary_cold = summary_lookup(summary_rows, "COLLAPSE_SINGLE_PRIMARY", METHOD_L2_THEN_COLD_GLOBAL)
    selection_rule = (
        "Prefer the simplest warm continuation in order "
        "[l2_then_warm_global, l2_probe1_then_warm_global, l2_probe2_then_warm_global] "
        "that satisfies the primary held-out gate."
    )

    selected_method = METHOD_L2_THEN_WARM_GLOBAL
    gate_result = "NOT_CONFIRMED"
    for method_id in PREFERRED_WARM_METHOD_ORDER:
        row = summary_lookup(summary_rows, "COLLAPSE_SINGLE_PRIMARY", method_id)
        passes = (
            row["selective_risk"] <= 0.05
            and row["coverage"] >= MEANINGFUL_COVERAGE_FLOOR
            and row["mean_compute"] < primary_global["mean_compute"]
            and row["false_accept_rate"] <= primary_global["false_accept_rate"] + 1e-12
            and row["exact_or_valid_recovery_rate"] >= primary_cold["exact_or_valid_recovery_rate"] - RECOVERY_TOLERANCE
        )
        if passes:
            selected_method = method_id
            gate_result = "CONFIRMED"
            break

    return SelectedMethodRecord(
        schema_version=WARM_START_SCHEMA_VERSION,
        method_version=WARM_START_METHOD_VERSION,
        selected_method=selected_method,
        l2_gate_version=L2_GATE_VERSION,
        global_gate_version=GLOBAL_GATE_VERSION,
        budget_definition={
            "global_budget_candidate_evaluations": "max_iterations * F * M",
            "global_budget_element_operations": "max_iterations * F * M * D",
            "remaining_global_iterations": "floor((remaining_candidate_budget) / (F * M))",
        },
        probe_steps=method_probe_steps(selected_method),
        seed_ranges={
            "development": level1e1_development_seed_ranges(),
            "calibration": level1e1_calibration_seed_ranges(),
            "heldout": level1e1_heldout_seed_ranges(),
        },
        selection_rule=selection_rule,
        gate_result=gate_result,
    )


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def save_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write empty CSV.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
