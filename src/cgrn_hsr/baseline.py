from __future__ import annotations

import csv
import json
import math
import platform
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from functools import reduce
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torchhd

BENCHMARK_SCHEMA_VERSION = "level1-baseline-v3"
SIMILARITY_METRIC = "cosine"
PILOT_MASTER_SEED = 20260614
PILOT_TRIALS_PER_CONFIG = 12
PILOT_CONFIG_COUNT = 18
CONFIRMATION_TRIALS_PER_POINT = 128
CONFIRMATION_SEED_START = PILOT_MASTER_SEED + 1_000_000
LEVEL1C_MASTER_SEED = 22260614
LEVEL1C_TRIALS_PER_REGIME = 64
CONTEXT_ACCURACY_GRID = (1.0, 0.9, 0.7)
ANOMALY_RATE_GRID = (0.0, 0.1, 0.25)

OUTCOME_TARGET_RECOVERY = "TARGET_RECOVERY"
OUTCOME_DISTRACTOR_CAPTURE = "DISTRACTOR_CAPTURE"
OUTCOME_HYBRID_SPURIOUS = "HYBRID_SPURIOUS"
OUTCOME_UNSETTLED = "UNSETTLED"
OUTCOME_CLASSES = (
    OUTCOME_TARGET_RECOVERY,
    OUTCOME_DISTRACTOR_CAPTURE,
    OUTCOME_HYBRID_SPURIOUS,
    OUTCOME_UNSETTLED,
)

METHOD_GLOBAL = "global"
METHOD_RANDOM_UNCONDITIONAL = "random_unconditional"
METHOD_ORACLE_TRUTH_INCLUDED = "oracle_truth_included"
METHOD_ORACLE_L2_CONTEXT = "oracle_l2_context"
METHOD_PREDICTED_L2_CONTEXT = "predicted_l2_context"
METHOD_ALIASES = {
    "random_truth_included": METHOD_ORACLE_TRUTH_INCLUDED,
}


@dataclass(frozen=True)
class BaselineConfig:
    dimensions: int
    num_factors: int
    domain_size: int
    structured_distractor_count: int
    component_flip_rate: float = 0.0
    max_iterations: int = 12
    stable_patience: int = 3

    def config_id(self) -> str:
        return (
            f"D{self.dimensions}_F{self.num_factors}_"
            f"M{self.domain_size}_SD{self.structured_distractor_count}"
        )


@dataclass(frozen=True)
class SyntheticContextConfig:
    num_l1_contexts: int = 3
    num_l2_per_l1: int = 3
    multi_membership_rate: float = 0.45
    tertiary_membership_rate: float = 0.15

    def num_l2_contexts(self) -> int:
        return self.num_l1_contexts * self.num_l2_per_l1


@dataclass(frozen=True)
class SyntheticContextHierarchy:
    config: SyntheticContextConfig
    l1_labels: tuple[str, ...]
    l2_labels: tuple[str, ...]
    l2_to_l1: dict[str, str]
    l1_to_l2: dict[str, tuple[str, ...]]
    factor_l2_weights: torch.Tensor


@dataclass(frozen=True)
class TrialProblem:
    seed: int
    config: BaselineConfig
    domains: torch.Tensor
    target_indices: torch.Tensor
    ground_truth_indices: torch.Tensor
    ground_truth_factors: torch.Tensor
    clean_composite: torch.Tensor
    structured_distractor_indices: torch.Tensor
    structured_distractors: torch.Tensor
    all_source_composite_indices: torch.Tensor
    observation: torch.Tensor
    context_hierarchy: SyntheticContextHierarchy | None = None
    active_l1: str | None = None
    active_l2: str | None = None
    anomaly_rate: float = 0.0
    anomaly_count: int = 0
    anomaly_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrialResult:
    schema_version: str
    similarity_metric: str
    master_seed: int
    seed: int
    problem_id: str
    operating_point_label: str
    method: str
    reduction_ratio_label: str
    D: int
    F: int
    M: int
    structured_distractor_count: int
    component_flip_rate: float
    max_iterations: int
    stable_patience: int
    candidate_subset_size: int
    candidate_evaluations_proxy: int
    element_operations_proxy: int
    ground_truth_indices: list[int]
    target_indices: list[int]
    structured_distractor_indices: list[list[int]]
    all_source_composite_indices: list[list[int]]
    candidate_subset_indices: list[list[int]]
    truth_included_per_factor: list[bool]
    all_truth_included: bool
    candidate_recall: float
    candidate_precision_proxy: float
    predicted_indices: list[int]
    exact_recovery: bool
    per_factor_recovery: list[bool]
    iterations_used: int
    stable_prediction: bool
    stable_iterations: int
    stop_reason: str
    outcome_class: str
    normalized_top1_scores: list[float]
    normalized_top2_scores: list[float]
    normalized_margins: list[float]
    normalized_reconstruction_similarity: float
    false_consensus: bool
    unsettled_failure: bool
    context_accuracy: float | None
    context_prediction_correct: bool | None
    active_l1: str | None
    active_l2: str | None
    predicted_l2: str | None
    anomaly_rate: float
    anomaly_count: int
    python_version: str
    torch_version: str
    torchhd_version: str
    platform: str
    config_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def runtime_metadata(master_seed: int) -> dict[str, Any]:
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "similarity_metric": SIMILARITY_METRIC,
        "master_seed": master_seed,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "platform": platform.platform(),
    }


def bind_sequence(vectors: torch.Tensor) -> torch.Tensor:
    return reduce(torchhd.bind, vectors)


def make_generator(seed: int) -> torch.Generator:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return generator


def canonical_method(method: str) -> str:
    return METHOD_ALIASES.get(method, method)


def cosine_similarity_matrix(estimates: torch.Tensor, domains: torch.Tensor) -> torch.Tensor:
    expanded_estimates = estimates.unsqueeze(-2).expand_as(domains)
    return F.cosine_similarity(expanded_estimates, domains, dim=-1)


def normalized_similarity_pair(lhs: torch.Tensor, rhs: torch.Tensor) -> float:
    return float(F.cosine_similarity(lhs.unsqueeze(0), rhs.unsqueeze(0), dim=-1).item())


def build_initial_estimates(candidate_domains: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [torchhd.multiset(candidate_domains[i]) for i in range(candidate_domains.size(0))],
        dim=0,
    )


def generate_domains(config: BaselineConfig, generator: torch.Generator) -> torch.Tensor:
    return torch.stack(
        [
            torchhd.random(config.domain_size, config.dimensions, "MAP", generator=generator)
            for _ in range(config.num_factors)
        ],
        dim=0,
    )


def sample_index_from_scores(scores: torch.Tensor, generator: torch.Generator) -> int:
    weights = scores.float().clamp_min(0.0)
    if float(weights.sum().item()) <= 0.0:
        weights = torch.ones_like(weights, dtype=torch.float32)
    probabilities = weights / weights.sum()
    return int(torch.multinomial(probabilities, 1, generator=generator).item())


def build_synthetic_context_hierarchy(
    config: BaselineConfig,
    generator: torch.Generator,
    context_config: SyntheticContextConfig | None = None,
) -> SyntheticContextHierarchy:
    context_config = context_config or SyntheticContextConfig()
    l1_labels = tuple(f"L1_{index}" for index in range(context_config.num_l1_contexts))
    l2_labels = tuple(
        f"{l1_labels[l1_index]}__L2_{l2_index}"
        for l1_index in range(context_config.num_l1_contexts)
        for l2_index in range(context_config.num_l2_per_l1)
    )
    l2_to_l1 = {
        label: label.split("__", maxsplit=1)[0]
        for label in l2_labels
    }
    l1_to_l2 = {
        l1_label: tuple(
            label for label in l2_labels if l2_to_l1[label] == l1_label
        )
        for l1_label in l1_labels
    }

    weights = torch.zeros(
        (config.num_factors, config.domain_size, len(l2_labels)),
        dtype=torch.float32,
    )
    for factor_index in range(config.num_factors):
        for atom_index in range(config.domain_size):
            primary_index = int(torch.randint(0, len(l2_labels), (1,), generator=generator).item())
            membership = torch.zeros(len(l2_labels), dtype=torch.float32)
            membership[primary_index] = 0.65 + 0.25 * torch.rand(1, generator=generator).item()

            available = [idx for idx in range(len(l2_labels)) if idx != primary_index]
            if available and torch.rand(1, generator=generator).item() < context_config.multi_membership_rate:
                secondary_pool = torch.tensor(available, dtype=torch.long)
                secondary_choice = int(
                    secondary_pool[
                        torch.randint(0, secondary_pool.numel(), (1,), generator=generator).item()
                    ].item()
                )
                membership[secondary_choice] = 0.15 + 0.25 * torch.rand(1, generator=generator).item()

            remaining = [
                idx
                for idx in range(len(l2_labels))
                if membership[idx].item() == 0.0
            ]
            if remaining and torch.rand(1, generator=generator).item() < context_config.tertiary_membership_rate:
                tertiary_pool = torch.tensor(remaining, dtype=torch.long)
                tertiary_choice = int(
                    tertiary_pool[
                        torch.randint(0, tertiary_pool.numel(), (1,), generator=generator).item()
                    ].item()
                )
                membership[tertiary_choice] = 0.05 + 0.10 * torch.rand(1, generator=generator).item()

            membership = membership / membership.sum()
            weights[factor_index, atom_index] = membership

    return SyntheticContextHierarchy(
        config=context_config,
        l1_labels=l1_labels,
        l2_labels=l2_labels,
        l2_to_l1=l2_to_l1,
        l1_to_l2=l1_to_l2,
        factor_l2_weights=weights,
    )


def l2_index(hierarchy: SyntheticContextHierarchy, label: str) -> int:
    return hierarchy.l2_labels.index(label)


def l2_scores_for_factor(
    hierarchy: SyntheticContextHierarchy,
    factor_index: int,
    l2_label: str,
) -> torch.Tensor:
    return hierarchy.factor_l2_weights[factor_index, :, l2_index(hierarchy, l2_label)]


def parent_scores_for_factor(
    hierarchy: SyntheticContextHierarchy,
    factor_index: int,
    l1_label: str,
) -> torch.Tensor:
    child_indices = torch.tensor(
        [l2_index(hierarchy, child) for child in hierarchy.l1_to_l2[l1_label]],
        dtype=torch.long,
    )
    return hierarchy.factor_l2_weights[factor_index].index_select(1, child_indices).sum(dim=1)


def sibling_l2_labels(hierarchy: SyntheticContextHierarchy, active_l2: str) -> tuple[str, ...]:
    active_l1 = hierarchy.l2_to_l1[active_l2]
    return tuple(label for label in hierarchy.l1_to_l2[active_l1] if label != active_l2)


def other_l2_labels(hierarchy: SyntheticContextHierarchy, active_l1: str) -> tuple[str, ...]:
    return tuple(label for label in hierarchy.l2_labels if hierarchy.l2_to_l1[label] != active_l1)


def predict_l2_context(
    hierarchy: SyntheticContextHierarchy,
    active_l2: str,
    context_accuracy: float,
    selection_seed: int,
) -> tuple[str, bool]:
    if not 0.0 <= context_accuracy <= 1.0:
        raise ValueError("context_accuracy must be between 0.0 and 1.0.")

    rng = random.Random(selection_seed)
    if rng.random() < context_accuracy:
        return active_l2, True

    siblings = sibling_l2_labels(hierarchy, active_l2)
    active_l1 = hierarchy.l2_to_l1[active_l2]
    cross_l1 = other_l2_labels(hierarchy, active_l1)

    if siblings and (not cross_l1 or rng.random() < 0.8):
        return siblings[rng.randrange(len(siblings))], False
    if cross_l1:
        return cross_l1[rng.randrange(len(cross_l1))], False
    if siblings:
        return siblings[rng.randrange(len(siblings))], False
    return active_l2, True


def sample_contextual_factor_index(
    hierarchy: SyntheticContextHierarchy,
    factor_index: int,
    active_l1: str,
    active_l2: str,
    anomaly_rate: float,
    generator: torch.Generator,
    rng: random.Random,
) -> tuple[int, str]:
    if rng.random() < anomaly_rate:
        anomaly_mode = rng.choices(
            population=["parent", "sibling", "global"],
            weights=[0.5, 0.35, 0.15],
            k=1,
        )[0]
    else:
        anomaly_mode = "active_l2"

    if anomaly_mode == "active_l2":
        scores = l2_scores_for_factor(hierarchy, factor_index, active_l2)
    elif anomaly_mode == "parent":
        parent_scores = parent_scores_for_factor(hierarchy, factor_index, active_l1)
        active_scores = l2_scores_for_factor(hierarchy, factor_index, active_l2)
        scores = (parent_scores - active_scores).clamp_min(0.0)
        if float(scores.sum().item()) <= 0.0:
            scores = parent_scores
    elif anomaly_mode == "sibling":
        siblings = sibling_l2_labels(hierarchy, active_l2)
        if siblings:
            sibling_label = siblings[rng.randrange(len(siblings))]
            scores = l2_scores_for_factor(hierarchy, factor_index, sibling_label)
        else:
            scores = parent_scores_for_factor(hierarchy, factor_index, active_l1)
    elif anomaly_mode == "global":
        scores = torch.ones(hierarchy.factor_l2_weights.size(1), dtype=torch.float32)
    else:
        raise ValueError(f"Unsupported anomaly mode: {anomaly_mode}")

    if anomaly_mode != "global":
        # Keep sampling support broad enough to generate multiple real source tuples
        # without changing the hypervector geometry or selector logic.
        scores = scores + 0.01

    return sample_index_from_scores(scores, generator), anomaly_mode


def sample_composite_indices(
    config: BaselineConfig,
    generator: torch.Generator,
    hierarchy: SyntheticContextHierarchy,
    active_l1: str,
    active_l2: str,
    anomaly_rate: float,
    rng: random.Random,
) -> tuple[torch.Tensor, tuple[str, ...]]:
    sampled_indices: list[int] = []
    anomaly_sources: list[str] = []
    for factor_index in range(config.num_factors):
        sampled_index, anomaly_source = sample_contextual_factor_index(
            hierarchy=hierarchy,
            factor_index=factor_index,
            active_l1=active_l1,
            active_l2=active_l2,
            anomaly_rate=anomaly_rate,
            generator=generator,
            rng=rng,
        )
        sampled_indices.append(sampled_index)
        anomaly_sources.append(anomaly_source)

    return torch.tensor(sampled_indices, dtype=torch.long), tuple(anomaly_sources)


def unique_contextual_source_tuples(
    config: BaselineConfig,
    generator: torch.Generator,
    hierarchy: SyntheticContextHierarchy,
    active_l1: str,
    active_l2: str,
    anomaly_rate: float,
    seed: int,
) -> tuple[torch.Tensor, tuple[str, ...], torch.Tensor]:
    source_count = 1 + config.structured_distractor_count
    source_tuples: list[torch.Tensor] = []
    target_anomaly_sources: tuple[str, ...] = ()
    seen: set[tuple[int, ...]] = set()
    rng = random.Random(seed + 73)

    for source_index in range(source_count):
        for _ in range(512):
            sampled_indices, anomaly_sources = sample_composite_indices(
                config=config,
                generator=generator,
                hierarchy=hierarchy,
                active_l1=active_l1,
                active_l2=active_l2,
                anomaly_rate=anomaly_rate,
                rng=rng,
            )
            key = tuple(int(value) for value in sampled_indices.tolist())
            if key not in seen:
                seen.add(key)
                source_tuples.append(sampled_indices)
                if source_index == 0:
                    target_anomaly_sources = anomaly_sources
                break
        else:
            raise RuntimeError("Could not sample a unique contextual source tuple.")

    stacked = torch.stack(source_tuples, dim=0)
    return stacked[0], target_anomaly_sources, stacked[1:]


def factors_from_indices(domains: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [domains[factor_index, indices[factor_index]] for factor_index in range(indices.numel())],
        dim=0,
    )


def composite_from_indices(domains: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    return bind_sequence(factors_from_indices(domains, indices))


def build_trial_problem(config: BaselineConfig, seed: int) -> TrialProblem:
    if config.component_flip_rate != 0.0:
        raise ValueError("component_flip_rate is reserved for future work and must stay 0.0 here.")

    generator = make_generator(seed)
    domains = generate_domains(config, generator)
    target_indices = torch.randint(
        low=0,
        high=config.domain_size,
        size=(config.num_factors,),
        generator=generator,
    )
    ground_truth_factors = factors_from_indices(domains, target_indices)
    clean_composite = bind_sequence(ground_truth_factors)

    distractor_indices_rows: list[torch.Tensor] = []
    distractor_vectors: list[torch.Tensor] = []
    seen = {tuple(int(value) for value in target_indices.tolist())}
    for _ in range(config.structured_distractor_count):
        for _ in range(128):
            distractor_indices = torch.randint(
                low=0,
                high=config.domain_size,
                size=(config.num_factors,),
                generator=generator,
            )
            distractor_key = tuple(int(value) for value in distractor_indices.tolist())
            if distractor_key not in seen:
                seen.add(distractor_key)
                distractor_indices_rows.append(distractor_indices)
                distractor_vectors.append(composite_from_indices(domains, distractor_indices))
                break
        else:
            raise RuntimeError("Could not sample a unique structured distractor tuple.")

    structured_distractor_indices = (
        torch.stack(distractor_indices_rows, dim=0)
        if distractor_indices_rows
        else torch.empty((0, config.num_factors), dtype=torch.long)
    )
    structured_distractors = (
        torch.stack(distractor_vectors, dim=0)
        if distractor_vectors
        else torch.empty((0, config.dimensions), dtype=clean_composite.dtype)
    )
    all_source_composite_indices = (
        torch.cat([target_indices.unsqueeze(0), structured_distractor_indices], dim=0)
        if structured_distractor_indices.numel() > 0
        else target_indices.unsqueeze(0)
    )
    observation_terms = [clean_composite, *distractor_vectors]
    observation = (
        clean_composite
        if len(observation_terms) == 1
        else torchhd.multiset(torch.stack(observation_terms, dim=0))
    )

    return TrialProblem(
        seed=seed,
        config=config,
        domains=domains,
        target_indices=target_indices,
        ground_truth_indices=target_indices,
        ground_truth_factors=ground_truth_factors,
        clean_composite=clean_composite,
        structured_distractor_indices=structured_distractor_indices,
        structured_distractors=structured_distractors,
        all_source_composite_indices=all_source_composite_indices,
        observation=observation,
    )


def build_contextual_trial_problem(
    config: BaselineConfig,
    seed: int,
    anomaly_rate: float,
    context_config: SyntheticContextConfig | None = None,
) -> TrialProblem:
    if config.component_flip_rate != 0.0:
        raise ValueError("component_flip_rate is reserved for future work and must stay 0.0 here.")

    generator = make_generator(seed)
    domains = generate_domains(config, generator)
    hierarchy = build_synthetic_context_hierarchy(config, generator, context_config)

    active_l2_index = int(torch.randint(0, len(hierarchy.l2_labels), (1,), generator=generator).item())
    active_l2 = hierarchy.l2_labels[active_l2_index]
    active_l1 = hierarchy.l2_to_l1[active_l2]

    target_indices, target_anomaly_sources, distractor_indices = unique_contextual_source_tuples(
        config=config,
        generator=generator,
        hierarchy=hierarchy,
        active_l1=active_l1,
        active_l2=active_l2,
        anomaly_rate=anomaly_rate,
        seed=seed,
    )
    ground_truth_factors = factors_from_indices(domains, target_indices)
    clean_composite = bind_sequence(ground_truth_factors)

    distractor_vectors = [
        composite_from_indices(domains, distractor_indices[index])
        for index in range(distractor_indices.size(0))
    ]
    structured_distractors = (
        torch.stack(distractor_vectors, dim=0)
        if distractor_vectors
        else torch.empty((0, config.dimensions), dtype=clean_composite.dtype)
    )
    all_source_composite_indices = (
        torch.cat([target_indices.unsqueeze(0), distractor_indices], dim=0)
        if distractor_indices.numel() > 0
        else target_indices.unsqueeze(0)
    )
    observation_terms = [clean_composite, *distractor_vectors]
    observation = (
        clean_composite
        if len(observation_terms) == 1
        else torchhd.multiset(torch.stack(observation_terms, dim=0))
    )

    return TrialProblem(
        seed=seed,
        config=config,
        domains=domains,
        target_indices=target_indices,
        ground_truth_indices=target_indices,
        ground_truth_factors=ground_truth_factors,
        clean_composite=clean_composite,
        structured_distractor_indices=distractor_indices,
        structured_distractors=structured_distractors,
        all_source_composite_indices=all_source_composite_indices,
        observation=observation,
        context_hierarchy=hierarchy,
        active_l1=active_l1,
        active_l2=active_l2,
        anomaly_rate=anomaly_rate,
        anomaly_count=sum(source != "active_l2" for source in target_anomaly_sources),
        anomaly_sources=target_anomaly_sources,
    )


def decode_top_candidates(similarities: torch.Tensor) -> dict[str, torch.Tensor]:
    if similarities.size(-1) < 2:
        raise ValueError("Need at least two candidates per factor to decode top-1/top-2 margins.")
    topk = torch.topk(similarities, k=2, dim=-1)
    top1_indices = topk.indices[:, 0]
    top2_indices = topk.indices[:, 1]
    top1_scores = topk.values[:, 0]
    top2_scores = topk.values[:, 1]
    margins = top1_scores - top2_scores
    return {
        "top1_indices": top1_indices,
        "top2_indices": top2_indices,
        "top1_scores": top1_scores,
        "top2_scores": top2_scores,
        "margins": margins,
    }


def predicted_matches_any_source(
    predicted_indices: torch.Tensor,
    source_indices: torch.Tensor,
) -> bool:
    if source_indices.numel() == 0:
        return False
    expanded = predicted_indices.unsqueeze(0).expand_as(source_indices)
    return bool(source_indices.eq(expanded).all(dim=1).any().item())


def classify_outcome(
    stable_prediction: bool,
    predicted_indices: torch.Tensor,
    target_indices: torch.Tensor,
    structured_distractor_indices: torch.Tensor,
) -> str:
    if not stable_prediction:
        return OUTCOME_UNSETTLED
    if torch.equal(predicted_indices, target_indices):
        return OUTCOME_TARGET_RECOVERY
    if predicted_matches_any_source(predicted_indices, structured_distractor_indices):
        return OUTCOME_DISTRACTOR_CAPTURE
    return OUTCOME_HYBRID_SPURIOUS


def classify_false_consensus(stable_prediction: bool, exact_recovery: bool) -> bool:
    return stable_prediction and not exact_recovery


def classify_unsettled_failure(stable_prediction: bool, exact_recovery: bool) -> bool:
    return (not stable_prediction) and (not exact_recovery)


def topk_context_indices(
    scores: torch.Tensor,
    subset_size: int,
) -> torch.Tensor:
    ranked_indices = torch.argsort(scores, descending=True, stable=True)
    return ranked_indices[:subset_size].to(dtype=torch.long)


def select_candidate_indices(
    problem: TrialProblem,
    method: str,
    subset_size: int | None,
    selection_seed: int,
    context_accuracy: float | None = None,
) -> tuple[torch.Tensor, str | None, bool | None]:
    method = canonical_method(method)

    if method == METHOD_GLOBAL:
        return (
            torch.stack(
                [
                    torch.arange(problem.config.domain_size, dtype=torch.long)
                    for _ in range(problem.config.num_factors)
                ],
                dim=0,
            ),
            None,
            None,
        )

    if subset_size is None:
        raise ValueError("subset_size must be provided for non-global methods.")

    if not 2 <= subset_size <= problem.config.domain_size:
        raise ValueError("subset_size must be between 2 and domain_size inclusive.")

    rng = random.Random(selection_seed)
    candidate_rows: list[torch.Tensor] = []
    predicted_l2: str | None = None
    context_prediction_correct: bool | None = None

    if method in (METHOD_ORACLE_L2_CONTEXT, METHOD_PREDICTED_L2_CONTEXT) and problem.context_hierarchy is None:
        raise ValueError("Context-aware methods require contextual trial metadata.")

    if method == METHOD_PREDICTED_L2_CONTEXT:
        if context_accuracy is None:
            raise ValueError("predicted_l2_context requires context_accuracy.")
        predicted_l2, context_prediction_correct = predict_l2_context(
            hierarchy=problem.context_hierarchy,
            active_l2=problem.active_l2,
            context_accuracy=context_accuracy,
            selection_seed=selection_seed,
        )

    for factor_index in range(problem.config.num_factors):
        population = list(range(problem.config.domain_size))
        truth_index = int(problem.ground_truth_indices[factor_index].item())

        if method == METHOD_RANDOM_UNCONDITIONAL:
            picked = sorted(rng.sample(population, subset_size))
            candidate_rows.append(torch.tensor(picked, dtype=torch.long))
            continue

        if method == METHOD_ORACLE_TRUTH_INCLUDED:
            remaining = [index for index in population if index != truth_index]
            picked = sorted([truth_index, *rng.sample(remaining, subset_size - 1)])
            candidate_rows.append(torch.tensor(picked, dtype=torch.long))
            continue

        if method == METHOD_ORACLE_L2_CONTEXT:
            scores = l2_scores_for_factor(problem.context_hierarchy, factor_index, problem.active_l2)
            candidate_rows.append(topk_context_indices(scores, subset_size))
            continue

        if method == METHOD_PREDICTED_L2_CONTEXT:
            scores = l2_scores_for_factor(problem.context_hierarchy, factor_index, predicted_l2)
            candidate_rows.append(topk_context_indices(scores, subset_size))
            continue

        raise ValueError(f"Unknown method: {method}")

    return torch.stack(candidate_rows, dim=0), predicted_l2, context_prediction_correct


def slice_candidate_domains(problem: TrialProblem, candidate_indices: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [problem.domains[i].index_select(0, candidate_indices[i]) for i in range(problem.config.num_factors)],
        dim=0,
    )


def make_problem_id(config: BaselineConfig, seed: int, label: str) -> str:
    return f"{label}:{config.config_id()}:seed{seed}"


def run_trial_on_problem(
    problem: TrialProblem,
    master_seed: int,
    operating_point_label: str,
    method: str = METHOD_GLOBAL,
    reduction_ratio_label: str = "full",
    subset_size: int | None = None,
    selection_seed: int | None = None,
    context_accuracy: float | None = None,
) -> TrialResult:
    seed_everything(problem.seed)

    method = canonical_method(method)
    effective_selection_seed = selection_seed if selection_seed is not None else problem.seed
    candidate_indices, predicted_l2, context_prediction_correct = select_candidate_indices(
        problem=problem,
        method=method,
        subset_size=None if method == METHOD_GLOBAL else subset_size,
        selection_seed=effective_selection_seed,
        context_accuracy=context_accuracy,
    )

    candidate_domains = slice_candidate_domains(problem, candidate_indices)
    initial_estimates = build_initial_estimates(candidate_domains)
    current_estimates = initial_estimates
    previous_indices: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    decoded: dict[str, torch.Tensor] | None = None

    for iteration in range(1, problem.config.max_iterations + 1):
        current_estimates = torchhd.resonator(
            problem.observation,
            current_estimates,
            candidate_domains,
        )
        similarities = cosine_similarity_matrix(current_estimates, candidate_domains)
        decoded = decode_top_candidates(similarities)
        predicted_local_indices = decoded["top1_indices"]
        predicted_full_indices = candidate_indices.gather(1, predicted_local_indices.unsqueeze(-1)).squeeze(-1)

        if previous_indices is not None and torch.equal(predicted_full_indices, previous_indices):
            stable_iterations += 1
        else:
            stable_iterations = 1

        previous_indices = predicted_full_indices.clone()
        if stable_iterations >= problem.config.stable_patience:
            stable_prediction = True
            break

    if decoded is None:
        raise RuntimeError("Resonator trial produced no decoded candidates.")

    predicted_full_indices = candidate_indices.gather(
        1, decoded["top1_indices"].unsqueeze(-1)
    ).squeeze(-1)
    predicted_factors = factors_from_indices(problem.domains, predicted_full_indices)
    reconstruction = bind_sequence(predicted_factors)
    normalized_reconstruction_similarity = normalized_similarity_pair(reconstruction, problem.observation)
    per_factor_recovery = predicted_full_indices.eq(problem.ground_truth_indices)
    exact_recovery = bool(per_factor_recovery.all().item())
    truth_included_per_factor = candidate_indices.eq(problem.ground_truth_indices.unsqueeze(-1)).any(dim=-1)
    all_truth_included = bool(truth_included_per_factor.all().item())
    candidate_subset_size = candidate_domains.size(1)
    candidate_hits = int(truth_included_per_factor.sum().item())
    candidate_recall = candidate_hits / problem.config.num_factors
    candidate_precision_proxy = candidate_hits / (problem.config.num_factors * candidate_subset_size)
    candidate_evaluations_proxy = iteration * problem.config.num_factors * candidate_subset_size
    element_operations_proxy = iteration * problem.config.num_factors * candidate_subset_size * problem.config.dimensions
    outcome_class = classify_outcome(
        stable_prediction=stable_prediction,
        predicted_indices=predicted_full_indices,
        target_indices=problem.target_indices,
        structured_distractor_indices=problem.structured_distractor_indices,
    )

    meta = runtime_metadata(master_seed)
    return TrialResult(
        schema_version=meta["schema_version"],
        similarity_metric=meta["similarity_metric"],
        master_seed=meta["master_seed"],
        seed=problem.seed,
        problem_id=make_problem_id(problem.config, problem.seed, operating_point_label),
        operating_point_label=operating_point_label,
        method=method,
        reduction_ratio_label=reduction_ratio_label,
        D=problem.config.dimensions,
        F=problem.config.num_factors,
        M=problem.config.domain_size,
        structured_distractor_count=problem.config.structured_distractor_count,
        component_flip_rate=problem.config.component_flip_rate,
        max_iterations=problem.config.max_iterations,
        stable_patience=problem.config.stable_patience,
        candidate_subset_size=candidate_subset_size,
        candidate_evaluations_proxy=candidate_evaluations_proxy,
        element_operations_proxy=element_operations_proxy,
        ground_truth_indices=problem.ground_truth_indices.tolist(),
        target_indices=problem.target_indices.tolist(),
        structured_distractor_indices=[row.tolist() for row in problem.structured_distractor_indices],
        all_source_composite_indices=[row.tolist() for row in problem.all_source_composite_indices],
        candidate_subset_indices=[row.tolist() for row in candidate_indices],
        truth_included_per_factor=truth_included_per_factor.tolist(),
        all_truth_included=all_truth_included,
        candidate_recall=candidate_recall,
        candidate_precision_proxy=candidate_precision_proxy,
        predicted_indices=predicted_full_indices.tolist(),
        exact_recovery=exact_recovery,
        per_factor_recovery=per_factor_recovery.tolist(),
        iterations_used=iteration,
        stable_prediction=stable_prediction,
        stable_iterations=stable_iterations,
        stop_reason="stable_prediction" if stable_prediction else "max_iterations",
        outcome_class=outcome_class,
        normalized_top1_scores=[float(x) for x in decoded["top1_scores"].tolist()],
        normalized_top2_scores=[float(x) for x in decoded["top2_scores"].tolist()],
        normalized_margins=[float(x) for x in decoded["margins"].tolist()],
        normalized_reconstruction_similarity=normalized_reconstruction_similarity,
        false_consensus=classify_false_consensus(stable_prediction, exact_recovery),
        unsettled_failure=classify_unsettled_failure(stable_prediction, exact_recovery),
        context_accuracy=context_accuracy,
        context_prediction_correct=context_prediction_correct,
        active_l1=problem.active_l1,
        active_l2=problem.active_l2,
        predicted_l2=predicted_l2,
        anomaly_rate=problem.anomaly_rate,
        anomaly_count=problem.anomaly_count,
        python_version=meta["python_version"],
        torch_version=meta["torch_version"],
        torchhd_version=meta["torchhd_version"],
        platform=meta["platform"],
        config_id=problem.config.config_id(),
    )


def run_trial(
    config: BaselineConfig,
    seed: int,
    master_seed: int,
    operating_point_label: str = "UNLABELED",
) -> TrialResult:
    problem = build_trial_problem(config, seed)
    return run_trial_on_problem(
        problem,
        master_seed=master_seed,
        operating_point_label=operating_point_label,
    )


def method_selection_seed(problem_seed: int, method: str, reduction_ratio_label: str) -> int:
    method = canonical_method(method)
    method_offsets = {
        METHOD_GLOBAL: 0,
        METHOD_RANDOM_UNCONDITIONAL: 10_000,
        METHOD_ORACLE_TRUTH_INCLUDED: 20_000,
        METHOD_ORACLE_L2_CONTEXT: 30_000,
        METHOD_PREDICTED_L2_CONTEXT: 40_000,
    }
    ratio_offsets = {
        "full": 0,
        "half": 100,
        "quarter": 200,
    }
    return problem_seed + method_offsets[method] + ratio_offsets[reduction_ratio_label]


def wilson_interval(successes: int, total: int, confidence_z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")

    p = successes / total
    z2 = confidence_z**2
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    radius = (confidence_z / denom) * math.sqrt((p * (1.0 - p) / total) + (z2 / (4.0 * total**2)))
    return max(0.0, center - radius), min(1.0, center + radius)


def summarize_trials(trials: list[TrialResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, float | None, float], list[TrialResult]] = {}
    for trial in trials:
        key = (
            trial.operating_point_label,
            trial.method,
            trial.reduction_ratio_label,
            trial.context_accuracy,
            trial.anomaly_rate,
        )
        grouped.setdefault(key, []).append(trial)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        total = len(batch)
        exact_successes = sum(t.exact_recovery for t in batch)
        false_consensus_count = sum(t.false_consensus for t in batch)
        unsettled_failure_count = sum(t.unsettled_failure for t in batch)
        stable_prediction_count = sum(t.stable_prediction for t in batch)
        all_truth_included_count = sum(t.all_truth_included for t in batch)
        per_factor_total = total * first.F
        per_factor_successes = sum(sum(t.per_factor_recovery) for t in batch)
        iterations_values = [t.iterations_used for t in batch]
        margin_values = [sum(t.normalized_margins) / len(t.normalized_margins) for t in batch]
        reconstruction_values = [t.normalized_reconstruction_similarity for t in batch]
        target_recovery_count = sum(t.outcome_class == OUTCOME_TARGET_RECOVERY for t in batch)
        distractor_capture_count = sum(t.outcome_class == OUTCOME_DISTRACTOR_CAPTURE for t in batch)
        hybrid_spurious_count = sum(t.outcome_class == OUTCOME_HYBRID_SPURIOUS for t in batch)
        unsettled_count = sum(t.outcome_class == OUTCOME_UNSETTLED for t in batch)
        conditional_trials = [t for t in batch if t.all_truth_included]
        conditional_accuracy = (
            sum(t.exact_recovery for t in conditional_trials) / len(conditional_trials)
            if conditional_trials
            else None
        )
        truth_absent_failures = [
            t for t in batch if (not t.all_truth_included) and (not t.exact_recovery)
        ]
        truth_present_failures = [
            t for t in batch if t.all_truth_included and (not t.exact_recovery)
        ]
        context_predictions = [t.context_prediction_correct for t in batch if t.context_prediction_correct is not None]
        exact_low, exact_high = wilson_interval(exact_successes, total)
        false_low, false_high = wilson_interval(false_consensus_count, total)
        unsettled_low, unsettled_high = wilson_interval(unsettled_failure_count, total)

        summary_rows.append(
            {
                "operating_point_label": first.operating_point_label,
                "config_id": first.config_id,
                "method": first.method,
                "reduction_ratio_label": first.reduction_ratio_label,
                "context_accuracy": first.context_accuracy,
                "anomaly_rate": first.anomaly_rate,
                "D": first.D,
                "F": first.F,
                "M": first.M,
                "structured_distractor_count": first.structured_distractor_count,
                "component_flip_rate": first.component_flip_rate,
                "candidate_subset_size": first.candidate_subset_size,
                "trials": total,
                "target_recovery_rate": target_recovery_count / total,
                "distractor_capture_rate": distractor_capture_count / total,
                "hybrid_spurious_rate": hybrid_spurious_count / total,
                "unsettled_rate": unsettled_count / total,
                "exact_recovery_rate": exact_successes / total,
                "exact_recovery_ci_low": exact_low,
                "exact_recovery_ci_high": exact_high,
                "per_factor_recovery_rate": per_factor_successes / per_factor_total,
                "false_consensus_rate": false_consensus_count / total,
                "false_consensus_ci_low": false_low,
                "false_consensus_ci_high": false_high,
                "false_consensus_distractor_capture_share": (
                    distractor_capture_count / false_consensus_count
                    if false_consensus_count
                    else None
                ),
                "false_consensus_hybrid_spurious_share": (
                    hybrid_spurious_count / false_consensus_count
                    if false_consensus_count
                    else None
                ),
                "unsettled_failure_rate": unsettled_failure_count / total,
                "unsettled_failure_ci_low": unsettled_low,
                "unsettled_failure_ci_high": unsettled_high,
                "stable_prediction_rate": stable_prediction_count / total,
                "truth_inclusion_probability": all_truth_included_count / total,
                "mean_candidate_recall": sum(t.candidate_recall for t in batch) / total,
                "mean_candidate_precision_proxy": sum(t.candidate_precision_proxy for t in batch) / total,
                "conditional_accuracy_given_all_truth_included": conditional_accuracy,
                "truth_absent_failure_rate": len(truth_absent_failures) / total,
                "truth_present_failure_rate": len(truth_present_failures) / total,
                "mean_iterations_used": sum(iterations_values) / total,
                "median_iterations_used": statistics.median(iterations_values),
                "mean_normalized_margin": sum(margin_values) / total,
                "mean_normalized_reconstruction_similarity": sum(reconstruction_values) / total,
                "mean_candidate_evaluations_proxy": sum(t.candidate_evaluations_proxy for t in batch) / total,
                "mean_element_operations_proxy": sum(t.element_operations_proxy for t in batch) / total,
                "mean_anomaly_count": sum(t.anomaly_count for t in batch) / total,
                "context_prediction_correct_rate": (
                    sum(context_predictions) / len(context_predictions)
                    if context_predictions
                    else None
                ),
                "schema_version": first.schema_version,
                "similarity_metric": first.similarity_metric,
                "master_seed": first.master_seed,
                "python_version": first.python_version,
                "torch_version": first.torch_version,
                "torchhd_version": first.torchhd_version,
                "platform": first.platform,
            }
        )

    global_rows = {
        (row["operating_point_label"], row["anomaly_rate"]): row
        for row in summary_rows
        if row["method"] == METHOD_GLOBAL and row["reduction_ratio_label"] == "full"
    }
    oracle_rows = {
        (row["operating_point_label"], row["reduction_ratio_label"], row["anomaly_rate"]): row
        for row in summary_rows
        if row["method"] == METHOD_ORACLE_TRUTH_INCLUDED
    }
    random_rows = {
        (row["operating_point_label"], row["reduction_ratio_label"], row["anomaly_rate"]): row
        for row in summary_rows
        if row["method"] == METHOD_RANDOM_UNCONDITIONAL
    }

    for row in summary_rows:
        global_row = global_rows[(row["operating_point_label"], row["anomaly_rate"])]
        oracle_row = oracle_rows.get(
            (row["operating_point_label"], row["reduction_ratio_label"], row["anomaly_rate"])
        )
        random_row = random_rows.get(
            (row["operating_point_label"], row["reduction_ratio_label"], row["anomaly_rate"])
        )
        row["paired_exact_recovery_delta_vs_global"] = (
            row["exact_recovery_rate"] - global_row["exact_recovery_rate"]
        )
        row["paired_false_consensus_delta_vs_global"] = (
            row["false_consensus_rate"] - global_row["false_consensus_rate"]
        )
        row["paired_target_recovery_delta_vs_global"] = (
            row["target_recovery_rate"] - global_row["target_recovery_rate"]
        )
        if oracle_row is not None:
            row["paired_exact_recovery_regret_vs_oracle_truth_included"] = (
                oracle_row["exact_recovery_rate"] - row["exact_recovery_rate"]
            )
            row["paired_candidate_recall_regret_vs_oracle_truth_included"] = (
                oracle_row["mean_candidate_recall"] - row["mean_candidate_recall"]
            )
        else:
            row["paired_exact_recovery_regret_vs_oracle_truth_included"] = None
            row["paired_candidate_recall_regret_vs_oracle_truth_included"] = None
        if random_row is not None:
            row["paired_candidate_recall_delta_vs_random_unconditional"] = (
                row["mean_candidate_recall"] - random_row["mean_candidate_recall"]
            )
            row["paired_exact_recovery_delta_vs_random_unconditional"] = (
                row["exact_recovery_rate"] - random_row["exact_recovery_rate"]
            )
        else:
            row["paired_candidate_recall_delta_vs_random_unconditional"] = None
            row["paired_exact_recovery_delta_vs_random_unconditional"] = None

    return summary_rows


def choose_summary_row(
    summary_rows: list[dict[str, Any]],
    predicate,
    target_rate: float,
) -> dict[str, Any] | None:
    candidates = [
        row
        for row in summary_rows
        if row["method"] == METHOD_GLOBAL
        and row["reduction_ratio_label"] == "full"
        and row["anomaly_rate"] == 0.0
        and predicate(row)
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda row: (
            abs(row["exact_recovery_rate"] - target_rate),
            row["structured_distractor_count"],
            row["F"],
            row["M"],
            -row["D"],
        ),
    )


def select_operating_points(summary_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    return {
        "EASY": choose_summary_row(summary_rows, lambda row: row["exact_recovery_rate"] >= 0.90, 0.95),
        "BORDERLINE": choose_summary_row(
            summary_rows,
            lambda row: 0.40 <= row["exact_recovery_rate"] <= 0.70,
            0.55,
        ),
        "COLLAPSE": choose_summary_row(summary_rows, lambda row: row["exact_recovery_rate"] <= 0.20, 0.10),
    }


def confirm_operating_point(label: str, exact_recovery_rate: float) -> str:
    if label == "EASY":
        return "CONFIRMED" if exact_recovery_rate >= 0.90 else "NOT_CONFIRMED"
    if label == "BORDERLINE":
        return "CONFIRMED" if 0.40 <= exact_recovery_rate <= 0.70 else "NOT_CONFIRMED"
    if label == "COLLAPSE":
        return "CONFIRMED" if exact_recovery_rate <= 0.20 else "NOT_CONFIRMED"
    raise ValueError(f"Unknown operating point label: {label}")


def save_trials_jsonl(path: Path, trials: list[TrialResult]) -> None:
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


def save_operating_points(
    path: Path,
    operating_points: dict[str, dict[str, Any] | None],
    master_seed: int,
    pilot_grid: list[BaselineConfig],
) -> None:
    payload = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "similarity_metric": SIMILARITY_METRIC,
        "master_seed": master_seed,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "platform": platform.platform(),
        "seed_policy": {
            "description": "trial_seed = master_seed + config_index * 1000 + trial_index",
        },
        "pilot_grid": [asdict(config) | {"config_id": config.config_id()} for config in pilot_grid],
        "operating_points": operating_points,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_confirmation_payload(
    path: Path,
    confirmation_rows: list[dict[str, Any]],
    seed_ranges: dict[str, dict[str, int]],
    level1a_commit: str,
) -> None:
    payload = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "similarity_metric": SIMILARITY_METRIC,
        "level1a_commit": level1a_commit,
        "seed_policy": seed_ranges,
        "operating_points_confirmation": confirmation_rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def pilot_seed_set() -> set[int]:
    return {
        PILOT_MASTER_SEED + config_index * 1000 + trial_index
        for config_index in range(PILOT_CONFIG_COUNT)
        for trial_index in range(PILOT_TRIALS_PER_CONFIG)
    }


def confirmation_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "EASY": {"start": CONFIRMATION_SEED_START, "count": CONFIRMATION_TRIALS_PER_POINT},
        "BORDERLINE": {
            "start": CONFIRMATION_SEED_START + 1_000,
            "count": CONFIRMATION_TRIALS_PER_POINT,
        },
        "COLLAPSE": {
            "start": CONFIRMATION_SEED_START + 2_000,
            "count": CONFIRMATION_TRIALS_PER_POINT,
        },
    }


def confirmation_seed_set() -> set[int]:
    seeds: set[int] = set()
    for spec in confirmation_seed_ranges().values():
        start = spec["start"]
        count = spec["count"]
        for seed in range(start, start + count):
            seeds.add(seed)
    return seeds


def level1c_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "EASY_SINGLE": {"start": LEVEL1C_MASTER_SEED, "count": LEVEL1C_TRIALS_PER_REGIME},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1C_MASTER_SEED + 10_000, "count": LEVEL1C_TRIALS_PER_REGIME},
        "COLLAPSE_SINGLE": {"start": LEVEL1C_MASTER_SEED + 20_000, "count": LEVEL1C_TRIALS_PER_REGIME},
    }
