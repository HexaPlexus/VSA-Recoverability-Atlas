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

BENCHMARK_SCHEMA_VERSION = "level1a-baseline-v2"
SIMILARITY_METRIC = "cosine"
PILOT_MASTER_SEED = 20260614
PILOT_TRIALS_PER_CONFIG = 12
PILOT_CONFIG_COUNT = 18
CONFIRMATION_TRIALS_PER_POINT = 128
CONFIRMATION_SEED_START = PILOT_MASTER_SEED + 1_000_000


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
class TrialProblem:
    seed: int
    config: BaselineConfig
    domains: torch.Tensor
    ground_truth_indices: torch.Tensor
    ground_truth_factors: torch.Tensor
    clean_composite: torch.Tensor
    structured_distractors: torch.Tensor
    observation: torch.Tensor


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
    ground_truth_indices: list[int]
    candidate_subset_indices: list[list[int]]
    truth_included_per_factor: list[bool]
    all_truth_included: bool
    predicted_indices: list[int]
    exact_recovery: bool
    per_factor_recovery: list[bool]
    iterations_used: int
    stable_prediction: bool
    stable_iterations: int
    stop_reason: str
    normalized_top1_scores: list[float]
    normalized_top2_scores: list[float]
    normalized_margins: list[float]
    normalized_reconstruction_similarity: float
    false_consensus: bool
    unsettled_failure: bool
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


def build_trial_problem(config: BaselineConfig, seed: int) -> TrialProblem:
    if config.component_flip_rate != 0.0:
        raise ValueError("component_flip_rate is reserved for future work and must stay 0.0 here.")

    generator = make_generator(seed)
    domains = torch.stack(
        [
            torchhd.random(config.domain_size, config.dimensions, "MAP", generator=generator)
            for _ in range(config.num_factors)
        ],
        dim=0,
    )
    ground_truth_indices = torch.randint(
        low=0,
        high=config.domain_size,
        size=(config.num_factors,),
        generator=generator,
    )
    ground_truth_factors = torch.stack(
        [domains[i, ground_truth_indices[i]] for i in range(config.num_factors)],
        dim=0,
    )
    clean_composite = bind_sequence(ground_truth_factors)

    distractors: list[torch.Tensor] = []
    for _ in range(config.structured_distractor_count):
        distractor_indices = torch.randint(
            low=0,
            high=config.domain_size,
            size=(config.num_factors,),
            generator=generator,
        )
        distractor_factors = torch.stack(
            [domains[i, distractor_indices[i]] for i in range(config.num_factors)],
            dim=0,
        )
        distractors.append(bind_sequence(distractor_factors))

    structured_distractors = (
        torch.stack(distractors, dim=0)
        if distractors
        else torch.empty((0, config.dimensions), dtype=clean_composite.dtype)
    )
    observation_terms = [clean_composite] + distractors
    observation = (
        clean_composite
        if len(observation_terms) == 1
        else torchhd.multiset(torch.stack(observation_terms, dim=0))
    )

    return TrialProblem(
        seed=seed,
        config=config,
        domains=domains,
        ground_truth_indices=ground_truth_indices,
        ground_truth_factors=ground_truth_factors,
        clean_composite=clean_composite,
        structured_distractors=structured_distractors,
        observation=observation,
    )


def decode_top_candidates(similarities: torch.Tensor) -> dict[str, torch.Tensor]:
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


def classify_false_consensus(stable_prediction: bool, exact_recovery: bool) -> bool:
    return stable_prediction and not exact_recovery


def classify_unsettled_failure(stable_prediction: bool, exact_recovery: bool) -> bool:
    return (not stable_prediction) and (not exact_recovery)


def select_candidate_indices(
    problem: TrialProblem,
    method: str,
    subset_size: int | None,
    selection_seed: int,
) -> torch.Tensor:
    if method == "global":
        return torch.stack(
            [torch.arange(problem.config.domain_size, dtype=torch.long) for _ in range(problem.config.num_factors)],
            dim=0,
        )

    if subset_size is None:
        raise ValueError("subset_size must be provided for pruning controls.")

    rng = random.Random(selection_seed)
    candidate_rows: list[torch.Tensor] = []
    for factor_index in range(problem.config.num_factors):
        population = list(range(problem.config.domain_size))
        truth_index = int(problem.ground_truth_indices[factor_index].item())

        if method == "random_unconditional":
            picked = sorted(rng.sample(population, subset_size))
        elif method == "random_truth_included":
            remaining = [idx for idx in population if idx != truth_index]
            picked = sorted([truth_index, *rng.sample(remaining, subset_size - 1)])
        else:
            raise ValueError(f"Unknown method: {method}")

        candidate_rows.append(torch.tensor(picked, dtype=torch.long))

    return torch.stack(candidate_rows, dim=0)


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
    method: str = "global",
    reduction_ratio_label: str = "full",
    subset_size: int | None = None,
    selection_seed: int | None = None,
) -> TrialResult:
    seed_everything(problem.seed)

    if method == "global":
        candidate_indices = select_candidate_indices(problem, method, None, selection_seed or problem.seed)
    else:
        if subset_size is None or selection_seed is None:
            raise ValueError("Pruning methods require subset_size and selection_seed.")
        candidate_indices = select_candidate_indices(problem, method, subset_size, selection_seed)

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
    predicted_factors = torch.stack(
        [problem.domains[i, predicted_full_indices[i]] for i in range(problem.config.num_factors)],
        dim=0,
    )
    reconstruction = bind_sequence(predicted_factors)
    normalized_reconstruction_similarity = normalized_similarity_pair(reconstruction, problem.observation)
    per_factor_recovery = predicted_full_indices.eq(problem.ground_truth_indices)
    exact_recovery = bool(per_factor_recovery.all().item())
    truth_included_per_factor = candidate_indices.eq(problem.ground_truth_indices.unsqueeze(-1)).any(dim=-1)
    all_truth_included = bool(truth_included_per_factor.all().item())
    candidate_subset_size = candidate_domains.size(1)
    candidate_evaluations_proxy = iteration * problem.config.num_factors * candidate_subset_size

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
        ground_truth_indices=problem.ground_truth_indices.tolist(),
        candidate_subset_indices=[row.tolist() for row in candidate_indices],
        truth_included_per_factor=truth_included_per_factor.tolist(),
        all_truth_included=all_truth_included,
        predicted_indices=predicted_full_indices.tolist(),
        exact_recovery=exact_recovery,
        per_factor_recovery=per_factor_recovery.tolist(),
        iterations_used=iteration,
        stable_prediction=stable_prediction,
        stable_iterations=stable_iterations,
        stop_reason="stable_prediction" if stable_prediction else "max_iterations",
        normalized_top1_scores=[float(x) for x in decoded["top1_scores"].tolist()],
        normalized_top2_scores=[float(x) for x in decoded["top2_scores"].tolist()],
        normalized_margins=[float(x) for x in decoded["margins"].tolist()],
        normalized_reconstruction_similarity=normalized_reconstruction_similarity,
        false_consensus=classify_false_consensus(stable_prediction, exact_recovery),
        unsettled_failure=classify_unsettled_failure(stable_prediction, exact_recovery),
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
    method_offsets = {
        "global": 0,
        "random_unconditional": 10_000,
        "random_truth_included": 20_000,
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
    grouped: dict[tuple[str, str, str], list[TrialResult]] = {}
    for trial in trials:
        key = (trial.operating_point_label, trial.method, trial.reduction_ratio_label)
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
        exact_low, exact_high = wilson_interval(exact_successes, total)
        false_low, false_high = wilson_interval(false_consensus_count, total)
        unsettled_low, unsettled_high = wilson_interval(unsettled_failure_count, total)

        summary_rows.append(
            {
                "operating_point_label": first.operating_point_label,
                "config_id": first.config_id,
                "method": first.method,
                "reduction_ratio_label": first.reduction_ratio_label,
                "D": first.D,
                "F": first.F,
                "M": first.M,
                "structured_distractor_count": first.structured_distractor_count,
                "component_flip_rate": first.component_flip_rate,
                "candidate_subset_size": first.candidate_subset_size,
                "trials": total,
                "exact_recovery_rate": exact_successes / total,
                "exact_recovery_ci_low": exact_low,
                "exact_recovery_ci_high": exact_high,
                "per_factor_recovery_rate": per_factor_successes / per_factor_total,
                "false_consensus_rate": false_consensus_count / total,
                "false_consensus_ci_low": false_low,
                "false_consensus_ci_high": false_high,
                "unsettled_failure_rate": unsettled_failure_count / total,
                "unsettled_failure_ci_low": unsettled_low,
                "unsettled_failure_ci_high": unsettled_high,
                "stable_prediction_rate": stable_prediction_count / total,
                "truth_inclusion_probability": all_truth_included_count / total,
                "conditional_accuracy_given_all_truth_included": conditional_accuracy,
                "truth_absent_failure_rate": len(truth_absent_failures) / total,
                "truth_present_failure_rate": len(truth_present_failures) / total,
                "mean_iterations_used": sum(iterations_values) / total,
                "median_iterations_used": statistics.median(iterations_values),
                "mean_normalized_margin": sum(margin_values) / total,
                "mean_normalized_reconstruction_similarity": sum(reconstruction_values) / total,
                "mean_candidate_evaluations_proxy": sum(t.candidate_evaluations_proxy for t in batch) / total,
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
        row["operating_point_label"]: row
        for row in summary_rows
        if row["method"] == "global" and row["reduction_ratio_label"] == "full"
    }
    oracle_rows = {
        (row["operating_point_label"], row["reduction_ratio_label"]): row
        for row in summary_rows
        if row["method"] == "random_truth_included"
    }
    for row in summary_rows:
        global_row = global_rows[row["operating_point_label"]]
        oracle_row = oracle_rows.get((row["operating_point_label"], row["reduction_ratio_label"]))
        row["paired_exact_recovery_delta_vs_global"] = (
            row["exact_recovery_rate"] - global_row["exact_recovery_rate"]
        )
        row["paired_false_consensus_delta_vs_global"] = (
            row["false_consensus_rate"] - global_row["false_consensus_rate"]
        )
        if oracle_row is not None:
            row["paired_exact_recovery_delta_vs_random_truth_included"] = (
                row["exact_recovery_rate"] - oracle_row["exact_recovery_rate"]
            )
            row["paired_false_consensus_delta_vs_random_truth_included"] = (
                row["false_consensus_rate"] - oracle_row["false_consensus_rate"]
            )
        else:
            row["paired_exact_recovery_delta_vs_random_truth_included"] = None
            row["paired_false_consensus_delta_vs_random_truth_included"] = None

    return summary_rows


def choose_summary_row(
    summary_rows: list[dict[str, Any]],
    predicate,
    target_rate: float,
) -> dict[str, Any] | None:
    candidates = [
        row
        for row in summary_rows
        if row["method"] == "global" and row["reduction_ratio_label"] == "full" and predicate(row)
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
