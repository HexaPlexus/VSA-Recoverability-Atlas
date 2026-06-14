from __future__ import annotations

import csv
import json
import math
import platform
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
import torchhd

from .baseline import (
    ANOMALY_RATE_GRID,
    CONTEXT_ACCURACY_GRID,
    METHOD_ORACLE_TRUTH_INCLUDED,
    METHOD_PREDICTED_L2_CONTEXT,
    METHOD_RANDOM_UNCONDITIONAL,
    METHOD_GLOBAL,
    OUTCOME_DISTRACTOR_CAPTURE,
    OUTCOME_HYBRID_SPURIOUS,
    OUTCOME_TARGET_RECOVERY,
    OUTCOME_UNSETTLED,
    BaselineConfig,
    SyntheticContextConfig,
    SyntheticContextHierarchy,
    bind_sequence,
    build_initial_estimates,
    build_synthetic_context_hierarchy,
    cosine_similarity_matrix,
    decode_top_candidates,
    factors_from_indices,
    level1c_seed_ranges,
    l2_index,
    l2_scores_for_factor,
    make_generator,
    method_selection_seed,
    normalized_similarity_pair,
    other_l2_labels,
    parent_scores_for_factor,
    pilot_seed_set,
    predict_l2_context,
    runtime_metadata,
    sample_index_from_scores,
    seed_everything,
    sibling_l2_labels,
    wilson_interval,
)

QUERY_SCHEMA_VERSION = "level1-query-v5"
LEVEL1D_CALIBRATION_MASTER_SEED = 23260614
LEVEL1D_EVAL_MASTER_SEED = 24260614
LEVEL1D_CALIBRATION_TRIALS_PER_REGIME = 24
LEVEL1D_EVAL_TRIALS_PER_REGIME = 64
LEVEL1D_PRIOR_STRENGTHS = (0.5, 1.0, 2.0)
CONTROL_NORMAL = "normal"
CONTROL_SHUFFLED_CONTEXT_METADATA = "shuffled_context_metadata"
CONTROL_SHUFFLED_QUERY_CONTEXT = "shuffled_query_context"

ROLE_DESIGNATED_TARGET = "DESIGNATED_TARGET"
ROLE_OUT_OF_QUERY_CONTEXT = "OUT_OF_QUERY_CONTEXT"
ROLE_SIBLING_QUERY_CONTEXT = "SIBLING_QUERY_CONTEXT"
ROLE_OVERLAPPING_CONTEXT = "OVERLAPPING_CONTEXT"
ROLE_QUERY_EQUIVALENT_VALID = "QUERY_EQUIVALENT_VALID"

QUERY_OUTCOME_TARGET_RECOVERY = "QUERY_TARGET_RECOVERY"
QUERY_OUTCOME_EQUIVALENT_VALID = "QUERY_EQUIVALENT_VALID"
QUERY_OUTCOME_IRRELEVANT_SOURCE_CAPTURE = "IRRELEVANT_SOURCE_CAPTURE"
QUERY_OUTCOME_HYBRID_SPURIOUS = "HYBRID_SPURIOUS"
QUERY_OUTCOME_UNSETTLED = "UNSETTLED"

METHOD_GLOBAL_UNIFORM = "global_uniform"
METHOD_HARD_L2_TOPK = "hard_l2_topk"
METHOD_SOFT_L2_WEIGHTED_INIT = "soft_l2_weighted_initialization"
METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT = "oracle_soft_l2_weighted_initialization"
METHOD_HARD_L2_STAGE = "hard_l2_stage"
METHOD_HARD_L1_STAGE = "hard_l1_stage"
METHOD_GLOBAL_STAGE = "global_stage"


@dataclass(frozen=True)
class QuerySourceComposite:
    source_id: str
    tuple_indices: torch.Tensor
    composite: torch.Tensor
    world_context: str
    query_relevance_context: str
    source_role: str
    is_designated_target: bool
    is_query_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "tuple_indices": [int(value) for value in self.tuple_indices.tolist()],
            "world_context": self.world_context,
            "query_relevance_context": self.query_relevance_context,
            "source_role": self.source_role,
            "is_designated_target": self.is_designated_target,
            "is_query_valid": self.is_query_valid,
        }


@dataclass(frozen=True)
class QueryTrialProblem:
    seed: int
    seed_split: str
    config: BaselineConfig
    domains: torch.Tensor
    observation: torch.Tensor
    context_hierarchy: SyntheticContextHierarchy
    shuffled_context_hierarchy: SyntheticContextHierarchy
    world_context: str
    query_context: str
    source_composites: tuple[QuerySourceComposite, ...]
    designated_target_tuple: torch.Tensor
    valid_source_tuples: torch.Tensor
    all_source_composite_indices: torch.Tensor
    target_indices: torch.Tensor
    structured_distractor_indices: torch.Tensor
    ground_truth_indices: torch.Tensor
    anomaly_rate: float
    anomaly_count: int


@dataclass(frozen=True)
class StageSnapshot:
    stage_label: str
    candidate_count: int
    truth_included_per_factor: list[bool]
    all_truth_included: bool
    predicted_tuple: list[int]
    query_outcome: str
    iterations: int
    normalized_top1: list[float]
    normalized_top2: list[float]
    normalized_margin: list[float]
    normalized_reconstruction_similarity: float
    stable_prediction: bool
    candidate_evaluations_proxy: int
    element_operations_proxy: int


@dataclass(frozen=True)
class QueryTrialResult:
    schema_version: str
    master_seed: int
    seed: int
    seed_split: str
    operating_point_label: str
    method: str
    control_label: str
    context_accuracy: float | None
    anomaly_rate: float
    prior_strength: float | None
    query_context: str
    selector_query_context: str
    world_context: str
    D: int
    F: int
    M: int
    structured_distractor_count: int
    candidate_subset_size: int
    candidate_subset_indices: list[list[int]]
    factor_candidate_recall: list[bool]
    all_truth_included: bool
    query_valid_source_included: bool
    predicted_indices: list[int]
    stable_prediction: bool
    stable_iterations: int
    iterations_used: int
    query_outcome_class: str
    outcome_class: str
    exact_recovery: bool
    valid_recovery: bool
    per_factor_recovery: list[bool]
    normalized_top1_scores: list[float]
    normalized_top2_scores: list[float]
    normalized_margins: list[float]
    normalized_reconstruction_similarity: float
    candidate_evaluations_proxy: int
    element_operations_proxy: int
    false_consensus: bool
    unsettled_failure: bool
    source_composites: list[dict[str, Any]]
    valid_source_tuples: list[list[int]]
    designated_target_tuple: list[int]
    target_recovery_when_all_truth_included: bool | None
    valid_recovery_when_all_truth_included: bool | None
    target_recovery_when_truth_missing: bool | None
    context_prediction_correct: bool | None
    predicted_l2: str | None
    python_version: str
    torch_version: str
    torchhd_version: str
    platform: str
    config_id: str
    uses_upstream_resonator: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def query_runtime_metadata(master_seed: int) -> dict[str, Any]:
    meta = runtime_metadata(master_seed)
    meta["schema_version"] = QUERY_SCHEMA_VERSION
    return meta


def level1d_calibration_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "EASY_SINGLE": {
            "start": LEVEL1D_CALIBRATION_MASTER_SEED,
            "count": LEVEL1D_CALIBRATION_TRIALS_PER_REGIME,
        },
        "HARD_STRUCTURED_MIXTURE": {
            "start": LEVEL1D_CALIBRATION_MASTER_SEED + 10_000,
            "count": LEVEL1D_CALIBRATION_TRIALS_PER_REGIME,
        },
        "COLLAPSE_SINGLE": {
            "start": LEVEL1D_CALIBRATION_MASTER_SEED + 20_000,
            "count": LEVEL1D_CALIBRATION_TRIALS_PER_REGIME,
        },
    }


def level1d_evaluation_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "EASY_SINGLE": {
            "start": LEVEL1D_EVAL_MASTER_SEED,
            "count": LEVEL1D_EVAL_TRIALS_PER_REGIME,
        },
        "HARD_STRUCTURED_MIXTURE": {
            "start": LEVEL1D_EVAL_MASTER_SEED + 10_000,
            "count": LEVEL1D_EVAL_TRIALS_PER_REGIME,
        },
        "COLLAPSE_SINGLE": {
            "start": LEVEL1D_EVAL_MASTER_SEED + 20_000,
            "count": LEVEL1D_EVAL_TRIALS_PER_REGIME,
        },
    }


def seed_ranges_to_set(seed_ranges: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in seed_ranges.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level1d_calibration_seed_set() -> set[int]:
    return seed_ranges_to_set(level1d_calibration_seed_ranges())


def level1d_evaluation_seed_set() -> set[int]:
    return seed_ranges_to_set(level1d_evaluation_seed_ranges())


def non_overlapping_seed_sets() -> bool:
    return (
        level1d_calibration_seed_set().isdisjoint(level1d_evaluation_seed_set())
        and level1d_calibration_seed_set().isdisjoint(pilot_seed_set())
        and level1d_calibration_seed_set().isdisjoint(seed_ranges_to_set(level1c_seed_ranges()))
        and level1d_evaluation_seed_set().isdisjoint(pilot_seed_set())
        and level1d_evaluation_seed_set().isdisjoint(seed_ranges_to_set(level1c_seed_ranges()))
    )


def source_role_templates(structured_distractor_count: int, seed: int) -> tuple[str, ...]:
    if structured_distractor_count == 0:
        return (ROLE_DESIGNATED_TARGET,)

    templates = (
        (
            ROLE_SIBLING_QUERY_CONTEXT,
            ROLE_DESIGNATED_TARGET,
            ROLE_QUERY_EQUIVALENT_VALID,
        ),
        (
            ROLE_OVERLAPPING_CONTEXT,
            ROLE_DESIGNATED_TARGET,
            ROLE_OUT_OF_QUERY_CONTEXT,
        ),
        (
            ROLE_QUERY_EQUIVALENT_VALID,
            ROLE_OUT_OF_QUERY_CONTEXT,
            ROLE_DESIGNATED_TARGET,
        ),
        (
            ROLE_SIBLING_QUERY_CONTEXT,
            ROLE_OVERLAPPING_CONTEXT,
            ROLE_DESIGNATED_TARGET,
        ),
    )
    template = list(templates[seed % len(templates)])
    while len(template) < structured_distractor_count + 1:
        template.append(
            (
                ROLE_QUERY_EQUIVALENT_VALID,
                ROLE_OUT_OF_QUERY_CONTEXT,
                ROLE_SIBLING_QUERY_CONTEXT,
                ROLE_OVERLAPPING_CONTEXT,
            )[(seed + len(template)) % 4]
        )
    return tuple(template[: structured_distractor_count + 1])


def choose_cross_l1_context(hierarchy: SyntheticContextHierarchy, query_context: str) -> str:
    query_l1 = hierarchy.l2_to_l1[query_context]
    alternatives = other_l2_labels(hierarchy, query_l1)
    return alternatives[0] if alternatives else query_context


def sample_role_scores(
    hierarchy: SyntheticContextHierarchy,
    factor_index: int,
    query_context: str,
    role: str,
    anomaly_mode: str | None = None,
) -> tuple[torch.Tensor, str, str]:
    query_l1 = hierarchy.l2_to_l1[query_context]
    sibling_contexts = sibling_l2_labels(hierarchy, query_context)
    sibling_context = sibling_contexts[0] if sibling_contexts else query_context
    cross_context = choose_cross_l1_context(hierarchy, query_context)

    query_scores = l2_scores_for_factor(hierarchy, factor_index, query_context)
    sibling_scores = l2_scores_for_factor(hierarchy, factor_index, sibling_context)
    cross_scores = l2_scores_for_factor(hierarchy, factor_index, cross_context)
    parent_scores = parent_scores_for_factor(hierarchy, factor_index, query_l1)

    if anomaly_mode == "parent":
        anomaly_scores = (parent_scores - query_scores).clamp_min(0.0)
        if float(anomaly_scores.sum().item()) <= 0.0:
            anomaly_scores = parent_scores
        return anomaly_scores + 0.01, query_l1, query_context
    if anomaly_mode == "sibling":
        return sibling_scores + 0.01, hierarchy.l2_to_l1[sibling_context], query_context
    if anomaly_mode == "global":
        return torch.ones_like(query_scores), "GLOBAL", query_context

    if role == ROLE_DESIGNATED_TARGET:
        return query_scores + 0.01, query_l1, query_context
    if role == ROLE_QUERY_EQUIVALENT_VALID:
        return query_scores + 0.01, query_l1, query_context
    if role == ROLE_SIBLING_QUERY_CONTEXT:
        return sibling_scores + 0.01, hierarchy.l2_to_l1[sibling_context], sibling_context
    if role == ROLE_OUT_OF_QUERY_CONTEXT:
        return cross_scores + 0.01, hierarchy.l2_to_l1[cross_context], cross_context
    if role == ROLE_OVERLAPPING_CONTEXT:
        overlap_scores = 0.65 * sibling_scores + 0.35 * query_scores
        return overlap_scores + 0.01, hierarchy.l2_to_l1[sibling_context], query_context
    raise ValueError(f"Unsupported source role: {role}")


def sample_source_tuple(
    config: BaselineConfig,
    hierarchy: SyntheticContextHierarchy,
    query_context: str,
    role: str,
    generator: torch.Generator,
    anomaly_rate: float,
    rng: random.Random,
) -> tuple[torch.Tensor, str, str, int]:
    indices = []
    world_context = query_context
    relevance_context = query_context
    anomaly_events = 0
    for factor_index in range(config.num_factors):
        anomaly_mode = None
        if role in (ROLE_DESIGNATED_TARGET, ROLE_QUERY_EQUIVALENT_VALID) and rng.random() < anomaly_rate:
            anomaly_mode = rng.choices(
                population=["parent", "sibling", "global"],
                weights=[0.5, 0.35, 0.15],
                k=1,
            )[0]
            anomaly_events += 1
        scores, sampled_world_context, sampled_relevance_context = sample_role_scores(
            hierarchy,
            factor_index,
            query_context,
            role,
            anomaly_mode=anomaly_mode,
        )
        world_context = sampled_world_context
        relevance_context = sampled_relevance_context
        indices.append(sample_index_from_scores(scores, generator))
    return torch.tensor(indices, dtype=torch.long), world_context, relevance_context, anomaly_events


def degree_preserving_metadata_shuffle(
    hierarchy: SyntheticContextHierarchy,
    seed: int,
) -> SyntheticContextHierarchy:
    rng = random.Random(seed)
    factor_l2_weights = torch.zeros_like(hierarchy.factor_l2_weights)
    for factor_index in range(hierarchy.factor_l2_weights.size(0)):
        for atom_index in range(hierarchy.factor_l2_weights.size(1)):
            row = hierarchy.factor_l2_weights[factor_index, atom_index]
            nonzero_indices = row.nonzero(as_tuple=False).flatten().tolist()
            nonzero_weights = [float(row[index].item()) for index in nonzero_indices]
            chosen = rng.sample(range(row.numel()), len(nonzero_indices))
            shuffled_row = torch.zeros_like(row)
            for target_index, weight in zip(chosen, nonzero_weights, strict=False):
                shuffled_row[target_index] = float(weight)
            factor_l2_weights[factor_index, atom_index] = shuffled_row

    return SyntheticContextHierarchy(
        config=hierarchy.config,
        l1_labels=hierarchy.l1_labels,
        l2_labels=hierarchy.l2_labels,
        l2_to_l1=hierarchy.l2_to_l1,
        l1_to_l2=hierarchy.l1_to_l2,
        factor_l2_weights=factor_l2_weights,
    )


def build_query_trial_problem(
    config: BaselineConfig,
    seed: int,
    anomaly_rate: float,
    seed_split: str,
    context_config: SyntheticContextConfig | None = None,
) -> QueryTrialProblem:
    generator = make_generator(seed)
    domains = torch.stack(
        [
            torchhd.random(config.domain_size, config.dimensions, "MAP", generator=generator)
            for _ in range(config.num_factors)
        ],
        dim=0,
    )
    hierarchy = build_synthetic_context_hierarchy(config, generator, context_config)
    query_context = hierarchy.l2_labels[
        int(torch.randint(0, len(hierarchy.l2_labels), (1,), generator=generator).item())
    ]
    world_context = hierarchy.l2_to_l1[query_context]
    roles = source_role_templates(config.structured_distractor_count, seed)
    source_rows: list[QuerySourceComposite] = []
    all_indices: list[torch.Tensor] = []
    valid_indices: list[torch.Tensor] = []
    designated_target_tuple: torch.Tensor | None = None
    seen: set[tuple[int, ...]] = set()
    rng = random.Random(seed + 1234)
    anomaly_count = 0

    for source_index, role in enumerate(roles):
        for _ in range(512):
            tuple_indices, source_world_context, relevance_context, source_anomalies = sample_source_tuple(
                config,
                hierarchy,
                query_context,
                role,
                generator,
                anomaly_rate=anomaly_rate,
                rng=rng,
            )
            key = tuple(int(value) for value in tuple_indices.tolist())
            if key in seen:
                continue
            seen.add(key)
            all_indices.append(tuple_indices)
            composite = bind_sequence(factors_from_indices(domains, tuple_indices))
            is_designated_target = role == ROLE_DESIGNATED_TARGET
            is_query_valid = role in (ROLE_DESIGNATED_TARGET, ROLE_QUERY_EQUIVALENT_VALID)
            source_rows.append(
                QuerySourceComposite(
                    source_id=f"S{source_index}",
                    tuple_indices=tuple_indices,
                    composite=composite,
                    world_context=source_world_context,
                    query_relevance_context=relevance_context,
                    source_role=role,
                    is_designated_target=is_designated_target,
                    is_query_valid=is_query_valid,
                )
            )
            if is_designated_target:
                designated_target_tuple = tuple_indices
            if is_query_valid:
                valid_indices.append(tuple_indices)
            anomaly_count += source_anomalies
            break
        else:
            raise RuntimeError("Could not sample a unique query-aware source tuple.")

    if designated_target_tuple is None:
        raise RuntimeError("Query trial problem did not generate a designated target.")

    observation = torchhd.multiset(torch.stack([source.composite for source in source_rows], dim=0))
    all_source_indices = torch.stack(all_indices, dim=0)
    valid_source_tuples = torch.stack(valid_indices, dim=0)
    structured_distractor_indices = torch.stack(
        [source.tuple_indices for source in source_rows if not source.is_designated_target],
        dim=0,
    ) if len(source_rows) > 1 else torch.empty((0, config.num_factors), dtype=torch.long)
    shuffled_context_hierarchy = degree_preserving_metadata_shuffle(hierarchy, seed + 7000)

    return QueryTrialProblem(
        seed=seed,
        seed_split=seed_split,
        config=config,
        domains=domains,
        observation=observation,
        context_hierarchy=hierarchy,
        shuffled_context_hierarchy=shuffled_context_hierarchy,
        world_context=world_context,
        query_context=query_context,
        source_composites=tuple(source_rows),
        designated_target_tuple=designated_target_tuple,
        valid_source_tuples=valid_source_tuples,
        all_source_composite_indices=all_source_indices,
        target_indices=designated_target_tuple,
        structured_distractor_indices=structured_distractor_indices,
        ground_truth_indices=designated_target_tuple,
        anomaly_rate=anomaly_rate,
        anomaly_count=anomaly_count,
    )


def shuffled_query_context_map(problems: list[QueryTrialProblem]) -> dict[int, str]:
    if len(problems) <= 1:
        return {problem.seed: problem.query_context for problem in problems}
    ordered = sorted(problems, key=lambda item: item.seed)
    contexts = [problem.query_context for problem in ordered]
    rotated = contexts[1:] + contexts[:1]
    return {problem.seed: rotated[index] for index, problem in enumerate(ordered)}


def full_candidate_indices(problem: QueryTrialProblem) -> torch.Tensor:
    return torch.stack(
        [torch.arange(problem.config.domain_size, dtype=torch.long) for _ in range(problem.config.num_factors)],
        dim=0,
    )


def stage_subset_sizes(domain_size: int) -> tuple[int, int]:
    return max(2, math.ceil(domain_size / 4)), math.ceil(domain_size / 2)


def topk_indices_from_scores(scores: torch.Tensor, subset_size: int) -> torch.Tensor:
    ranked = torch.argsort(scores, descending=True, stable=True)
    return ranked[:subset_size].to(dtype=torch.long)


def select_l2_subset(
    problem: QueryTrialProblem,
    hierarchy: SyntheticContextHierarchy,
    query_context: str,
    subset_size: int,
) -> torch.Tensor:
    rows = []
    for factor_index in range(problem.config.num_factors):
        rows.append(topk_indices_from_scores(l2_scores_for_factor(hierarchy, factor_index, query_context), subset_size))
    return torch.stack(rows, dim=0)


def select_l1_subset(
    problem: QueryTrialProblem,
    hierarchy: SyntheticContextHierarchy,
    query_context: str,
    l2_subset: torch.Tensor,
    subset_size: int,
) -> torch.Tensor:
    l1_context = hierarchy.l2_to_l1[query_context]
    rows = []
    for factor_index in range(problem.config.num_factors):
        parent_scores = parent_scores_for_factor(hierarchy, factor_index, l1_context)
        ranked = torch.argsort(parent_scores, descending=True, stable=True).tolist()
        chosen = [int(value) for value in l2_subset[factor_index].tolist()]
        for candidate in ranked:
            if candidate not in chosen:
                chosen.append(candidate)
            if len(chosen) >= subset_size:
                break
        rows.append(torch.tensor(chosen[:subset_size], dtype=torch.long))
    return torch.stack(rows, dim=0)


def select_random_unconditional_subset(
    problem: QueryTrialProblem,
    subset_size: int,
    selection_seed: int,
) -> torch.Tensor:
    rng = random.Random(selection_seed)
    rows = []
    for _ in range(problem.config.num_factors):
        rows.append(torch.tensor(sorted(rng.sample(range(problem.config.domain_size), subset_size)), dtype=torch.long))
    return torch.stack(rows, dim=0)


def select_oracle_truth_included_subset(
    problem: QueryTrialProblem,
    subset_size: int,
    selection_seed: int,
) -> torch.Tensor:
    rng = random.Random(selection_seed)
    rows = []
    for factor_index in range(problem.config.num_factors):
        truth_index = int(problem.designated_target_tuple[factor_index].item())
        remaining = [index for index in range(problem.config.domain_size) if index != truth_index]
        picks = sorted([truth_index, *rng.sample(remaining, subset_size - 1)])
        rows.append(torch.tensor(picks, dtype=torch.long))
    return torch.stack(rows, dim=0)


def slice_candidate_domains(problem: QueryTrialProblem, candidate_indices: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [problem.domains[factor_index].index_select(0, candidate_indices[factor_index]) for factor_index in range(problem.config.num_factors)],
        dim=0,
    )


def build_prior_weights(
    problem: QueryTrialProblem,
    hierarchy: SyntheticContextHierarchy,
    query_context: str,
    prior_strength: float,
    floor_mass: float = 0.05,
) -> torch.Tensor:
    if prior_strength <= 0.0:
        raise ValueError("prior_strength must be positive.")
    weights = []
    uniform = 1.0 / problem.config.domain_size
    for factor_index in range(problem.config.num_factors):
        scores = l2_scores_for_factor(hierarchy, factor_index, query_context)
        logits = prior_strength * scores
        normalized = torch.softmax(logits, dim=0)
        mixed = floor_mass * uniform + (1.0 - floor_mass) * normalized
        mixed = mixed / mixed.sum()
        weights.append(mixed)
    return torch.stack(weights, dim=0)


def build_weighted_initial_estimates(
    problem: QueryTrialProblem,
    prior_weights: torch.Tensor,
) -> torch.Tensor:
    return torch.einsum("fm,fmd->fd", prior_weights, problem.domains)


def tuple_matches_row(tuple_indices: torch.Tensor, rows: torch.Tensor) -> bool:
    if rows.numel() == 0:
        return False
    return bool(rows.eq(tuple_indices.unsqueeze(0)).all(dim=1).any().item())


def classify_query_outcome(problem: QueryTrialProblem, stable_prediction: bool, predicted_indices: torch.Tensor) -> str:
    if not stable_prediction:
        return QUERY_OUTCOME_UNSETTLED
    if torch.equal(predicted_indices, problem.designated_target_tuple):
        return QUERY_OUTCOME_TARGET_RECOVERY
    other_valid = problem.valid_source_tuples
    if tuple_matches_row(predicted_indices, other_valid) and not torch.equal(predicted_indices, problem.designated_target_tuple):
        return QUERY_OUTCOME_EQUIVALENT_VALID
    if tuple_matches_row(predicted_indices, problem.all_source_composite_indices):
        return QUERY_OUTCOME_IRRELEVANT_SOURCE_CAPTURE
    return QUERY_OUTCOME_HYBRID_SPURIOUS


def classify_source_outcome(problem: QueryTrialProblem, stable_prediction: bool, predicted_indices: torch.Tensor) -> str:
    if not stable_prediction:
        return OUTCOME_UNSETTLED
    if torch.equal(predicted_indices, problem.target_indices):
        return OUTCOME_TARGET_RECOVERY
    if tuple_matches_row(predicted_indices, problem.structured_distractor_indices):
        return OUTCOME_DISTRACTOR_CAPTURE
    return OUTCOME_HYBRID_SPURIOUS


def query_valid_source_included(problem: QueryTrialProblem, candidate_indices: torch.Tensor) -> bool:
    for valid_tuple in problem.valid_source_tuples:
        included = candidate_indices.eq(valid_tuple.unsqueeze(-1)).any(dim=-1)
        if bool(included.all().item()):
            return True
    return False


def reference_tuple_mean_rank(
    candidate_indices: torch.Tensor,
    final_similarities: torch.Tensor,
    reference_indices: torch.Tensor,
) -> float:
    ranks = []
    for factor_index in range(candidate_indices.size(0)):
        reference_value = int(reference_indices[factor_index].item())
        row_candidates = candidate_indices[factor_index].tolist()
        if reference_value not in row_candidates:
            ranks.append(float(candidate_indices.size(1) + 1))
            continue
        order = torch.argsort(final_similarities[factor_index], descending=True, stable=True).tolist()
        sorted_candidates = [row_candidates[index] for index in order]
        ranks.append(float(sorted_candidates.index(reference_value) + 1))
    return sum(ranks) / len(ranks)


def run_query_trial(
    problem: QueryTrialProblem,
    operating_point_label: str,
    master_seed: int,
    method: str,
    control_label: str = CONTROL_NORMAL,
    context_accuracy: float | None = None,
    prior_strength: float | None = None,
    shuffled_query_context: str | None = None,
    reference_indices: torch.Tensor | None = None,
) -> tuple[QueryTrialResult, torch.Tensor]:
    seed_everything(problem.seed)
    l2_subset_size, l1_subset_size = stage_subset_sizes(problem.config.domain_size)
    selector_query_context = problem.query_context if control_label != CONTROL_SHUFFLED_QUERY_CONTEXT else (shuffled_query_context or problem.query_context)
    selector_hierarchy = problem.context_hierarchy if control_label != CONTROL_SHUFFLED_CONTEXT_METADATA else problem.shuffled_context_hierarchy

    predicted_l2: str | None = None
    context_prediction_correct: bool | None = None
    if method in (
        METHOD_HARD_L2_TOPK,
        METHOD_HARD_L2_STAGE,
        METHOD_HARD_L1_STAGE,
        METHOD_SOFT_L2_WEIGHTED_INIT,
        METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT,
    ):
        if method == METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT:
            predicted_l2 = selector_query_context
            context_prediction_correct = selector_query_context == problem.query_context
        elif method in (METHOD_SOFT_L2_WEIGHTED_INIT, METHOD_HARD_L2_TOPK, METHOD_HARD_L2_STAGE, METHOD_HARD_L1_STAGE):
            if context_accuracy is None:
                raise ValueError(f"{method} requires context_accuracy.")
            predicted_l2, context_prediction_correct = predict_l2_context(
                hierarchy=selector_hierarchy,
                active_l2=selector_query_context,
                context_accuracy=context_accuracy,
                selection_seed=method_selection_seed(problem.seed, METHOD_PREDICTED_L2_CONTEXT, "quarter"),
            )
        else:
            predicted_l2 = selector_query_context
            context_prediction_correct = selector_query_context == problem.query_context

    if method == METHOD_GLOBAL_UNIFORM or method == METHOD_GLOBAL_STAGE:
        candidate_indices = full_candidate_indices(problem)
        initial_estimates = build_initial_estimates(problem.domains)
    elif method == METHOD_RANDOM_UNCONDITIONAL:
        candidate_indices = select_random_unconditional_subset(
            problem,
            subset_size=l2_subset_size,
            selection_seed=method_selection_seed(problem.seed, METHOD_RANDOM_UNCONDITIONAL, "quarter"),
        )
        initial_estimates = build_initial_estimates(slice_candidate_domains(problem, candidate_indices))
    elif method == METHOD_ORACLE_TRUTH_INCLUDED:
        candidate_indices = select_oracle_truth_included_subset(
            problem,
            subset_size=l2_subset_size,
            selection_seed=method_selection_seed(problem.seed, METHOD_ORACLE_TRUTH_INCLUDED, "quarter"),
        )
        initial_estimates = build_initial_estimates(slice_candidate_domains(problem, candidate_indices))
    elif method in (METHOD_HARD_L2_TOPK, METHOD_HARD_L2_STAGE):
        candidate_indices = select_l2_subset(problem, selector_hierarchy, predicted_l2, l2_subset_size)
        initial_estimates = build_initial_estimates(slice_candidate_domains(problem, candidate_indices))
    elif method == METHOD_HARD_L1_STAGE:
        l2_candidate_indices = select_l2_subset(problem, selector_hierarchy, predicted_l2, l2_subset_size)
        candidate_indices = select_l1_subset(problem, selector_hierarchy, predicted_l2, l2_candidate_indices, l1_subset_size)
        initial_estimates = build_initial_estimates(slice_candidate_domains(problem, candidate_indices))
    elif method in (METHOD_SOFT_L2_WEIGHTED_INIT, METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT):
        if prior_strength is None:
            raise ValueError(f"{method} requires prior_strength.")
        candidate_indices = full_candidate_indices(problem)
        prior_weights = build_prior_weights(problem, selector_hierarchy, predicted_l2, prior_strength)
        initial_estimates = build_weighted_initial_estimates(problem, prior_weights)
    else:
        raise ValueError(f"Unsupported method: {method}")

    candidate_domains = slice_candidate_domains(problem, candidate_indices)
    current_estimates = initial_estimates
    previous_indices: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    decoded: dict[str, torch.Tensor] | None = None
    final_similarities: torch.Tensor | None = None

    for iteration in range(1, problem.config.max_iterations + 1):
        current_estimates = torchhd.resonator(problem.observation, current_estimates, candidate_domains)
        final_similarities = cosine_similarity_matrix(current_estimates, candidate_domains)
        decoded = decode_top_candidates(final_similarities)
        predicted_local = decoded["top1_indices"]
        predicted_full = candidate_indices.gather(1, predicted_local.unsqueeze(-1)).squeeze(-1)
        if previous_indices is not None and torch.equal(predicted_full, previous_indices):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_indices = predicted_full.clone()
        if stable_iterations >= problem.config.stable_patience:
            stable_prediction = True
            break

    if decoded is None or final_similarities is None:
        raise RuntimeError("Query trial did not decode resonator outputs.")

    predicted_full = candidate_indices.gather(1, decoded["top1_indices"].unsqueeze(-1)).squeeze(-1)
    predicted_factors = factors_from_indices(problem.domains, predicted_full)
    reconstruction = bind_sequence(predicted_factors)
    truth_included_per_factor = candidate_indices.eq(problem.designated_target_tuple.unsqueeze(-1)).any(dim=-1)
    all_truth_included = bool(truth_included_per_factor.all().item())
    valid_source_reachable = query_valid_source_included(problem, candidate_indices)
    per_factor_recovery = predicted_full.eq(problem.designated_target_tuple)
    exact_recovery = bool(per_factor_recovery.all().item())
    query_outcome = classify_query_outcome(problem, stable_prediction, predicted_full)
    source_outcome = classify_source_outcome(problem, stable_prediction, predicted_full)
    valid_recovery = query_outcome in (QUERY_OUTCOME_TARGET_RECOVERY, QUERY_OUTCOME_EQUIVALENT_VALID)
    candidate_subset_size = candidate_indices.size(1)
    candidate_evaluations_proxy = iteration * problem.config.num_factors * candidate_subset_size
    element_operations_proxy = candidate_evaluations_proxy * problem.config.dimensions

    meta = query_runtime_metadata(master_seed)
    result = QueryTrialResult(
        schema_version=meta["schema_version"],
        master_seed=master_seed,
        seed=problem.seed,
        seed_split=problem.seed_split,
        operating_point_label=operating_point_label,
        method=method,
        control_label=control_label,
        context_accuracy=context_accuracy,
        anomaly_rate=problem.anomaly_rate,
        prior_strength=prior_strength,
        query_context=problem.query_context,
        selector_query_context=selector_query_context,
        world_context=problem.world_context,
        D=problem.config.dimensions,
        F=problem.config.num_factors,
        M=problem.config.domain_size,
        structured_distractor_count=problem.config.structured_distractor_count,
        candidate_subset_size=candidate_subset_size,
        candidate_subset_indices=[row.tolist() for row in candidate_indices],
        factor_candidate_recall=truth_included_per_factor.tolist(),
        all_truth_included=all_truth_included,
        query_valid_source_included=valid_source_reachable,
        predicted_indices=predicted_full.tolist(),
        stable_prediction=stable_prediction,
        stable_iterations=stable_iterations,
        iterations_used=iteration,
        query_outcome_class=query_outcome,
        outcome_class=source_outcome,
        exact_recovery=exact_recovery,
        valid_recovery=valid_recovery,
        per_factor_recovery=per_factor_recovery.tolist(),
        normalized_top1_scores=[float(value) for value in decoded["top1_scores"].tolist()],
        normalized_top2_scores=[float(value) for value in decoded["top2_scores"].tolist()],
        normalized_margins=[float(value) for value in decoded["margins"].tolist()],
        normalized_reconstruction_similarity=normalized_similarity_pair(reconstruction, problem.observation),
        candidate_evaluations_proxy=candidate_evaluations_proxy,
        element_operations_proxy=element_operations_proxy,
        false_consensus=stable_prediction and not exact_recovery,
        unsettled_failure=(not stable_prediction) and (not exact_recovery),
        source_composites=[source.to_dict() for source in problem.source_composites],
        valid_source_tuples=[row.tolist() for row in problem.valid_source_tuples],
        designated_target_tuple=problem.designated_target_tuple.tolist(),
        target_recovery_when_all_truth_included=(exact_recovery if all_truth_included else None),
        valid_recovery_when_all_truth_included=(valid_recovery if all_truth_included else None),
        target_recovery_when_truth_missing=(exact_recovery if not all_truth_included else None),
        context_prediction_correct=context_prediction_correct,
        predicted_l2=predicted_l2,
        python_version=meta["python_version"],
        torch_version=meta["torch_version"],
        torchhd_version=meta["torchhd_version"],
        platform=meta["platform"],
        config_id=problem.config.config_id(),
        uses_upstream_resonator=True,
    )
    return result, final_similarities


def build_stage_snapshots(
    problem: QueryTrialProblem,
    operating_point_label: str,
    master_seed: int,
    context_accuracy: float,
    shuffled_query_context: str,
) -> tuple[dict[str, StageSnapshot], dict[str, Any]]:
    l2_result, l2_similarities = run_query_trial(
        problem,
        operating_point_label,
        master_seed,
        method=METHOD_HARD_L2_STAGE,
        context_accuracy=context_accuracy,
    )
    l2_predicted = torch.tensor(l2_result.predicted_indices, dtype=torch.long)
    l1_result, l1_similarities = run_query_trial(
        problem,
        operating_point_label,
        master_seed,
        method=METHOD_HARD_L1_STAGE,
        context_accuracy=context_accuracy,
    )
    global_result, global_similarities = run_query_trial(
        problem,
        operating_point_label,
        master_seed,
        method=METHOD_GLOBAL_STAGE,
    )

    snapshots = {
        "L2_narrow": StageSnapshot(
            stage_label="L2_narrow",
            candidate_count=l2_result.candidate_subset_size,
            truth_included_per_factor=l2_result.factor_candidate_recall,
            all_truth_included=l2_result.all_truth_included,
            predicted_tuple=l2_result.predicted_indices,
            query_outcome=l2_result.query_outcome_class,
            iterations=l2_result.iterations_used,
            normalized_top1=l2_result.normalized_top1_scores,
            normalized_top2=l2_result.normalized_top2_scores,
            normalized_margin=l2_result.normalized_margins,
            normalized_reconstruction_similarity=l2_result.normalized_reconstruction_similarity,
            stable_prediction=l2_result.stable_prediction,
            candidate_evaluations_proxy=l2_result.candidate_evaluations_proxy,
            element_operations_proxy=l2_result.element_operations_proxy,
        ),
        "L1_parent": StageSnapshot(
            stage_label="L1_parent",
            candidate_count=l1_result.candidate_subset_size,
            truth_included_per_factor=l1_result.factor_candidate_recall,
            all_truth_included=l1_result.all_truth_included,
            predicted_tuple=l1_result.predicted_indices,
            query_outcome=l1_result.query_outcome_class,
            iterations=l1_result.iterations_used,
            normalized_top1=l1_result.normalized_top1_scores,
            normalized_top2=l1_result.normalized_top2_scores,
            normalized_margin=l1_result.normalized_margins,
            normalized_reconstruction_similarity=l1_result.normalized_reconstruction_similarity,
            stable_prediction=l1_result.stable_prediction,
            candidate_evaluations_proxy=l1_result.candidate_evaluations_proxy,
            element_operations_proxy=l1_result.element_operations_proxy,
        ),
        "global": StageSnapshot(
            stage_label="global",
            candidate_count=global_result.candidate_subset_size,
            truth_included_per_factor=global_result.factor_candidate_recall,
            all_truth_included=global_result.all_truth_included,
            predicted_tuple=global_result.predicted_indices,
            query_outcome=global_result.query_outcome_class,
            iterations=global_result.iterations_used,
            normalized_top1=global_result.normalized_top1_scores,
            normalized_top2=global_result.normalized_top2_scores,
            normalized_margin=global_result.normalized_margins,
            normalized_reconstruction_similarity=global_result.normalized_reconstruction_similarity,
            stable_prediction=global_result.stable_prediction,
            candidate_evaluations_proxy=global_result.candidate_evaluations_proxy,
            element_operations_proxy=global_result.element_operations_proxy,
        ),
    }

    def stage_rank(similarities: torch.Tensor, result: QueryTrialResult, reference_tuple: torch.Tensor) -> float:
        return reference_tuple_mean_rank(
            candidate_indices=torch.tensor(result.candidate_subset_indices, dtype=torch.long),
            final_similarities=similarities,
            reference_indices=reference_tuple,
        )

    l2_margin = statistics.fmean(l2_result.normalized_margins)
    l1_margin = statistics.fmean(l1_result.normalized_margins)
    global_margin = statistics.fmean(global_result.normalized_margins)

    stage_order = [snapshots["L2_narrow"], snapshots["L1_parent"], snapshots["global"]]
    earliest_valid = next(
        (snapshot.stage_label for snapshot in stage_order if snapshot.query_outcome in (QUERY_OUTCOME_TARGET_RECOVERY, QUERY_OUTCOME_EQUIVALENT_VALID)),
        None,
    )
    earliest_target = next(
        (snapshot.stage_label for snapshot in stage_order if snapshot.query_outcome == QUERY_OUTCOME_TARGET_RECOVERY),
        None,
    )
    cumulative_compute = 0
    progressive_stage_label = earliest_valid or "global"
    for snapshot in stage_order:
        cumulative_compute += snapshot.element_operations_proxy
        if snapshot.stage_label == progressive_stage_label:
            break

    stability = {
        "l2_prediction_survives_l1": l1_result.predicted_indices == l2_result.predicted_indices,
        "l2_prediction_survives_global": global_result.predicted_indices == l2_result.predicted_indices,
        "l2_rank_at_l1": stage_rank(l1_similarities, l1_result, l2_predicted),
        "l2_rank_at_global": stage_rank(global_similarities, global_result, l2_predicted),
        "l1_rank_at_global": stage_rank(
            global_similarities,
            global_result,
            torch.tensor(l1_result.predicted_indices, dtype=torch.long),
        ),
        "l2_margin_delta_at_l1": l1_margin - l2_margin,
        "l2_margin_delta_at_global": global_margin - l2_margin,
        "oracle_earliest_valid_stage": earliest_valid,
        "oracle_earliest_target_stage": earliest_target,
        "oracle_progressive_compute": cumulative_compute,
    }
    return snapshots, stability


def choose_prior_strength(calibration_trials: list[QueryTrialResult]) -> float:
    grouped: dict[float, list[QueryTrialResult]] = {}
    for trial in calibration_trials:
        grouped.setdefault(float(trial.prior_strength), []).append(trial)
    ranked = sorted(
        grouped.items(),
        key=lambda item: (
            -sum(trial.valid_recovery for trial in item[1]) / len(item[1]),
            -sum(trial.exact_recovery for trial in item[1]) / len(item[1]),
            item[0],
        ),
    )
    return ranked[0][0]


def summarize_query_trials(trials: list[QueryTrialResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, float | None, float, float | None], list[QueryTrialResult]] = {}
    for trial in trials:
        key = (
            trial.seed_split,
            trial.operating_point_label,
            trial.method,
            trial.control_label,
            trial.anomaly_rate,
            trial.context_accuracy,
            trial.prior_strength,
        )
        grouped.setdefault(key, []).append(trial)

    rows = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        total = len(batch)
        target_hits = sum(trial.query_outcome_class == QUERY_OUTCOME_TARGET_RECOVERY for trial in batch)
        valid_hits = sum(trial.valid_recovery for trial in batch)
        equivalent_hits = sum(trial.query_outcome_class == QUERY_OUTCOME_EQUIVALENT_VALID for trial in batch)
        irrelevant_hits = sum(trial.query_outcome_class == QUERY_OUTCOME_IRRELEVANT_SOURCE_CAPTURE for trial in batch)
        hybrid_hits = sum(trial.query_outcome_class == QUERY_OUTCOME_HYBRID_SPURIOUS for trial in batch)
        unsettled_hits = sum(trial.query_outcome_class == QUERY_OUTCOME_UNSETTLED for trial in batch)
        all_truth_hits = sum(trial.all_truth_included for trial in batch)
        valid_source_included_hits = sum(trial.query_valid_source_included for trial in batch)
        conditioned_truth = [trial for trial in batch if trial.all_truth_included]
        missing_truth = [trial for trial in batch if not trial.all_truth_included]
        target_low, target_high = wilson_interval(target_hits, total)
        valid_low, valid_high = wilson_interval(valid_hits, total)
        hybrid_low, hybrid_high = wilson_interval(hybrid_hits, total)

        rows.append(
            {
                "schema_version": QUERY_SCHEMA_VERSION,
                "seed_split": first.seed_split,
                "operating_point_label": first.operating_point_label,
                "method": first.method,
                "control_label": first.control_label,
                "anomaly_rate": first.anomaly_rate,
                "context_accuracy": first.context_accuracy,
                "prior_strength": first.prior_strength,
                "candidate_subset_size": first.candidate_subset_size,
                "trials": total,
                "designated_target_recovery_rate": target_hits / total,
                "designated_target_recovery_ci_low": target_low,
                "designated_target_recovery_ci_high": target_high,
                "query_valid_recovery_rate": valid_hits / total,
                "query_valid_recovery_ci_low": valid_low,
                "query_valid_recovery_ci_high": valid_high,
                "query_equivalent_valid_rate": equivalent_hits / total,
                "irrelevant_source_capture_rate": irrelevant_hits / total,
                "hybrid_spurious_rate": hybrid_hits / total,
                "hybrid_spurious_ci_low": hybrid_low,
                "hybrid_spurious_ci_high": hybrid_high,
                "unsettled_rate": unsettled_hits / total,
                "all_truth_included_rate": all_truth_hits / total,
                "query_valid_source_included_rate": valid_source_included_hits / total,
                "factor_candidate_recall_rate": (
                    sum(sum(trial.factor_candidate_recall) for trial in batch) / (total * first.F)
                ),
                "target_recovery_given_all_truth_included": (
                    sum(trial.exact_recovery for trial in conditioned_truth) / len(conditioned_truth)
                    if conditioned_truth
                    else None
                ),
                "valid_recovery_given_all_truth_included": (
                    sum(trial.valid_recovery for trial in conditioned_truth) / len(conditioned_truth)
                    if conditioned_truth
                    else None
                ),
                "target_recovery_given_truth_missing": (
                    sum(trial.exact_recovery for trial in missing_truth) / len(missing_truth)
                    if missing_truth
                    else None
                ),
                "mean_iterations_used": sum(trial.iterations_used for trial in batch) / total,
                "mean_candidate_evaluations_proxy": sum(trial.candidate_evaluations_proxy for trial in batch) / total,
                "mean_element_operations_proxy": sum(trial.element_operations_proxy for trial in batch) / total,
                "mean_normalized_margin": sum(statistics.fmean(trial.normalized_margins) for trial in batch) / total,
                "mean_normalized_reconstruction_similarity": sum(trial.normalized_reconstruction_similarity for trial in batch) / total,
                "context_prediction_correct_rate": (
                    sum(trial.context_prediction_correct for trial in batch if trial.context_prediction_correct is not None)
                    / len([trial for trial in batch if trial.context_prediction_correct is not None])
                    if any(trial.context_prediction_correct is not None for trial in batch)
                    else None
                ),
                "python_version": first.python_version,
                "torch_version": first.torch_version,
                "torchhd_version": first.torchhd_version,
                "platform": first.platform,
            }
        )
    return rows


def save_trials_jsonl(path: Path, trials: list[QueryTrialResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for trial in trials:
            handle.write(json.dumps(trial.to_dict(), ensure_ascii=True) + "\n")


def save_summary_csv(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not summary_rows:
        raise ValueError("Cannot write an empty summary.")
    fieldnames = list(summary_rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_evidence_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
