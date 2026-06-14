from __future__ import annotations

import csv
import json
import platform
import random
import sys
from dataclasses import asdict, dataclass
from functools import reduce
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torchhd

BENCHMARK_SCHEMA_VERSION = "level1a-global-resonator-v1"


@dataclass(frozen=True)
class BaselineConfig:
    dimensions: int
    num_factors: int
    domain_size: int
    external_noise: int
    max_iterations: int = 12
    stable_patience: int = 3

    def config_id(self) -> str:
        return (
            f"D{self.dimensions}_F{self.num_factors}_"
            f"M{self.domain_size}_N{self.external_noise}"
        )


@dataclass(frozen=True)
class TrialProblem:
    seed: int
    config: BaselineConfig
    domains: torch.Tensor
    ground_truth_indices: torch.Tensor
    ground_truth_factors: torch.Tensor
    clean_composite: torch.Tensor
    observation: torch.Tensor
    initial_estimates: torch.Tensor


@dataclass(frozen=True)
class TrialResult:
    schema_version: str
    master_seed: int
    seed: int
    D: int
    F: int
    M: int
    external_noise: int
    max_iterations: int
    stable_patience: int
    ground_truth_indices: list[int]
    predicted_indices: list[int]
    exact_recovery: bool
    per_factor_recovery: list[bool]
    iterations_used: int
    converged: bool
    stable_iterations: int
    top1_scores: list[float]
    top2_scores: list[float]
    margins: list[float]
    reconstruction_similarity: float
    false_consensus: bool
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


def build_trial_problem(config: BaselineConfig, seed: int) -> TrialProblem:
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

    observation_terms = [clean_composite]
    for _ in range(config.external_noise):
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
        observation_terms.append(bind_sequence(distractor_factors))

    observation = (
        clean_composite
        if len(observation_terms) == 1
        else torchhd.multiset(torch.stack(observation_terms, dim=0))
    )
    initial_estimates = torch.stack(
        [torchhd.multiset(domains[i]) for i in range(config.num_factors)],
        dim=0,
    )

    return TrialProblem(
        seed=seed,
        config=config,
        domains=domains,
        ground_truth_indices=ground_truth_indices,
        ground_truth_factors=ground_truth_factors,
        clean_composite=clean_composite,
        observation=observation,
        initial_estimates=initial_estimates,
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


def classify_false_consensus(converged: bool, exact_recovery: bool) -> bool:
    return converged and not exact_recovery


def run_trial(config: BaselineConfig, seed: int, master_seed: int) -> TrialResult:
    seed_everything(seed)
    problem = build_trial_problem(config, seed)
    current_estimates = problem.initial_estimates
    previous_indices: torch.Tensor | None = None
    stable_iterations = 0
    converged = False
    decoded: dict[str, torch.Tensor] | None = None

    for iteration in range(1, config.max_iterations + 1):
        current_estimates = torchhd.resonator(
            problem.observation,
            current_estimates,
            problem.domains,
        )
        similarities = torchhd.dot_similarity(
            current_estimates.unsqueeze(-2), problem.domains
        ).squeeze(-2)
        decoded = decode_top_candidates(similarities)
        predicted_indices = decoded["top1_indices"]

        if previous_indices is not None and torch.equal(predicted_indices, previous_indices):
            stable_iterations += 1
        else:
            stable_iterations = 1

        previous_indices = predicted_indices.clone()
        if stable_iterations >= config.stable_patience:
            converged = True
            break

    if decoded is None:
        raise RuntimeError("Resonator trial produced no decoded candidates.")

    predicted_factors = torch.stack(
        [problem.domains[i, decoded["top1_indices"][i]] for i in range(config.num_factors)],
        dim=0,
    )
    reconstruction = bind_sequence(predicted_factors)
    reconstruction_similarity = float(
        torchhd.dot_similarity(reconstruction, problem.observation).item()
    )
    per_factor_recovery = decoded["top1_indices"].eq(problem.ground_truth_indices)
    exact_recovery = bool(per_factor_recovery.all().item())

    meta = runtime_metadata(master_seed)
    return TrialResult(
        schema_version=meta["schema_version"],
        master_seed=meta["master_seed"],
        seed=seed,
        D=config.dimensions,
        F=config.num_factors,
        M=config.domain_size,
        external_noise=config.external_noise,
        max_iterations=config.max_iterations,
        stable_patience=config.stable_patience,
        ground_truth_indices=problem.ground_truth_indices.tolist(),
        predicted_indices=decoded["top1_indices"].tolist(),
        exact_recovery=exact_recovery,
        per_factor_recovery=per_factor_recovery.tolist(),
        iterations_used=iteration,
        converged=converged,
        stable_iterations=stable_iterations,
        top1_scores=[float(x) for x in decoded["top1_scores"].tolist()],
        top2_scores=[float(x) for x in decoded["top2_scores"].tolist()],
        margins=[float(x) for x in decoded["margins"].tolist()],
        reconstruction_similarity=reconstruction_similarity,
        false_consensus=classify_false_consensus(converged, exact_recovery),
        python_version=meta["python_version"],
        torch_version=meta["torch_version"],
        torchhd_version=meta["torchhd_version"],
        platform=meta["platform"],
        config_id=config.config_id(),
    )


def summarize_trials(trials: list[TrialResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[TrialResult]] = {}
    for trial in trials:
        grouped.setdefault(trial.config_id, []).append(trial)

    summary_rows: list[dict[str, Any]] = []
    for config_id in sorted(grouped):
        batch = grouped[config_id]
        first = batch[0]
        total = len(batch)
        exact_rate = sum(t.exact_recovery for t in batch) / total
        false_consensus_rate = sum(t.false_consensus for t in batch) / total
        converged_rate = sum(t.converged for t in batch) / total
        mean_iterations = sum(t.iterations_used for t in batch) / total
        mean_margin = sum(sum(t.margins) / len(t.margins) for t in batch) / total
        mean_reconstruction = sum(t.reconstruction_similarity for t in batch) / total
        summary_rows.append(
            {
                "config_id": config_id,
                "D": first.D,
                "F": first.F,
                "M": first.M,
                "external_noise": first.external_noise,
                "max_iterations": first.max_iterations,
                "stable_patience": first.stable_patience,
                "trials": total,
                "exact_recovery_rate": exact_rate,
                "false_consensus_rate": false_consensus_rate,
                "converged_rate": converged_rate,
                "mean_iterations_used": mean_iterations,
                "mean_margin": mean_margin,
                "mean_reconstruction_similarity": mean_reconstruction,
                "schema_version": first.schema_version,
                "master_seed": first.master_seed,
                "python_version": first.python_version,
                "torch_version": first.torch_version,
                "torchhd_version": first.torchhd_version,
                "platform": first.platform,
            }
        )
    return summary_rows


def choose_summary_row(
    summary_rows: list[dict[str, Any]],
    predicate,
    target_rate: float,
) -> dict[str, Any] | None:
    candidates = [row for row in summary_rows if predicate(row)]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda row: (
            abs(row["exact_recovery_rate"] - target_rate),
            row["external_noise"],
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
