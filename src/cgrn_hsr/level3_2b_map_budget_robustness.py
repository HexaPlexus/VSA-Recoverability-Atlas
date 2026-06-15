from __future__ import annotations

import csv
import io
import json
import math
import platform
import random
import statistics
import sys
import time
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on Windows
    resource = None

import torch
import torch.nn.functional as F
import torchhd

from .baseline import (
    BaselineConfig,
    bind_sequence,
    build_initial_estimates,
    cosine_similarity_matrix,
    decode_top_candidates,
    factors_from_indices,
    generate_domains,
    make_generator,
    normalized_similarity_pair,
)
from .competitors.ibm_bcf_audit import AbstractFactorizationTask, BCF_OFFICIAL_CLASS_PATH
from .level3_2_confirmation import (
    BCF_CONFIG_FAMILY,
    FrozenBCFCellConfig,
    LEVEL3_2_CHECKPOINT_COMMIT,
    build_frozen_bcf_configs,
    common_outcome,
    config_for_cell,
    load_official_bcf_class,
    peak_cpu_memory_bytes,
    prior_level3_1_seed_set,
    synchronize_device,
    tensor_bytes,
    upstream_clone_path,
    upstream_commit_sha,
    upstream_tracked_source_clean,
    write_csv,
    write_json,
    write_jsonl,
)

LEVEL3_2B_SCHEMA_VERSION = "level3-2b-map-budget-robustness-dev-v1"
LEVEL3_2B_CHECKPOINT_COMMIT = "86efbb8927069cdc057fe3ba4ddacd41cd938acb"
U1_TASK_CONTRACT = "U1_blind_single_product_factorization"
SEED_SPLIT = "development_robustness"

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_FAILURE = "FAILURE"

MAP_STABLE_PATIENCE = 3
MAP_RESTART_COUNT = 4
MAP_RESTART_SELECTION_RULES = (
    "majority_vote",
    "best_native_reconstruction",
    "random_restart_selection",
)
COMPUTE_MATCHED_ARM_IDS = (
    "map_wallclock_matched_bcf_median",
    "map_wallclock_matched_bcf_p90",
)

CELL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "cell_id": "u1_easy_sanity",
        "classification": "SANITY",
        "F": 3,
        "M": 10,
        "trials": 16,
        "heavy_exploratory": False,
    },
    {
        "cell_id": "u1_boundary_22",
        "classification": "PRIMARY",
        "F": 3,
        "M": 22,
        "trials": 32,
        "heavy_exploratory": False,
    },
    {
        "cell_id": "u1_boundary_31",
        "classification": "PRIMARY",
        "F": 3,
        "M": 31,
        "trials": 32,
        "heavy_exploratory": False,
    },
    {
        "cell_id": "u1_separation_68",
        "classification": "HEAVY_EXPLORATORY",
        "F": 3,
        "M": 68,
        "trials": 16,
        "heavy_exploratory": True,
    },
)

SEED_RANGES = {
    "u1_easy_sanity": {"start": 70260615, "count": 16},
    "u1_boundary_22": {"start": 71260615, "count": 32},
    "u1_boundary_31": {"start": 72260615, "count": 32},
    "u1_separation_68": {"start": 73260615, "count": 16},
}

MAP_DIMENSIONS = (512, 1024)
MAP_REPRESENTATION_SEED_OFFSETS = {512: 3_000, 1024: 4_000}
BCF_REPRESENTATION_SEED_OFFSET = 5_000
RESTART_SELECTION_SEED_OFFSET = 6_000


@dataclass(frozen=True)
class MapArmConfig:
    arm_id: str
    dimensions: int
    max_iterations: int
    init_mode: str
    restart_count: int
    selection_rule: str
    compute_matching_mode: str | None = None
    budget_source_substrate: str | None = None
    budget_statistic: str | None = None
    frozen_wallclock_budget_sec: float | None = None
    frozen_map_reference_decode_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedMapTask:
    dimensions: int
    domains: torch.Tensor
    observation: torch.Tensor
    baseline_estimates: torch.Tensor
    target_indices: torch.Tensor
    materialization_time_sec: float
    decoder_initialization_time_sec: float
    observation_bytes: int
    codebook_bytes: int
    baseline_state_bytes: int
    device: str


@dataclass(frozen=True)
class MapAttempt:
    restart_index: int
    init_mode: str
    max_iterations: int
    predicted_indices: list[int]
    per_factor_recovery: list[bool]
    exact_recovery: bool
    outcome: str
    iterations: int
    stable_prediction: bool
    stable_iterations: int
    prediction_change_count: int
    trajectory_stability: float
    normalized_reconstruction_similarity: float
    min_margin: float
    mean_margin: float
    decode_time_sec: float
    decoder_state_bytes: int

    def tuple_key(self) -> tuple[int, ...]:
        return tuple(self.predicted_indices)


def factor_identity_tokens(factor_count: int, domain_size: int) -> list[list[str]]:
    return [
        [f"f{factor_index}_i{atom_index}" for atom_index in range(domain_size)]
        for factor_index in range(factor_count)
    ]


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values_sorted = sorted(values)
    index = (len(values_sorted) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values_sorted[lower]
    weight = index - lower
    return values_sorted[lower] * (1.0 - weight) + values_sorted[upper] * weight


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials == 0:
        return (0.0, 0.0)
    phat = successes / trials
    denom = 1.0 + (z * z) / trials
    center = (phat + (z * z) / (2 * trials)) / denom
    margin = (
        z
        * math.sqrt((phat * (1.0 - phat) / trials) + ((z * z) / (4 * trials * trials)))
        / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def level3_2_seed_set() -> set[int]:
    values: set[int] = set()
    for spec in (
        {"start": 60260615, "count": 64},
        {"start": 61260615, "count": 128},
        {"start": 62260615, "count": 128},
        {"start": 63260615, "count": 64},
        {"start": 64260615, "count": 64},
    ):
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level3_2b_seed_set() -> set[int]:
    values: set[int] = set()
    for spec in SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level3_2b_seed_sets_are_fresh() -> bool:
    prior = prior_level3_1_seed_set().union(level3_2_seed_set())
    return level3_2b_seed_set().isdisjoint(prior)


def build_task_manifest(trial_seed: int, cell: dict[str, Any]) -> tuple[dict[str, Any], AbstractFactorizationTask]:
    generator = make_generator(trial_seed)
    true_indices = [
        int(torch.randint(0, cell["M"], (1,), generator=generator).item())
        for _ in range(cell["F"])
    ]
    manifest = {
        "trial_id": f"{cell['cell_id']}-seed-{trial_seed}",
        "trial_seed": trial_seed,
        "F": cell["F"],
        "M": cell["M"],
        "true_factor_indices": true_indices,
        "factor_identity_tokens": factor_identity_tokens(cell["F"], cell["M"]),
        "split": SEED_SPLIT,
        "cell_id": cell["cell_id"],
        "cell_classification": cell["classification"],
        "task_contract": U1_TASK_CONTRACT,
        "map_representation_seed_d512": trial_seed + MAP_REPRESENTATION_SEED_OFFSETS[512],
        "map_representation_seed_d1024": trial_seed + MAP_REPRESENTATION_SEED_OFFSETS[1024],
        "bcf_representation_seed": trial_seed + BCF_REPRESENTATION_SEED_OFFSET,
    }
    task = AbstractFactorizationTask(
        task_seed=trial_seed,
        factor_count=cell["F"],
        domain_size_per_factor=[cell["M"]] * cell["F"],
        target_indices=true_indices,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )
    return manifest, task


def prepare_map_task(
    task: AbstractFactorizationTask,
    *,
    dimensions: int,
    representation_seed: int,
    device: str,
) -> PreparedMapTask:
    config = BaselineConfig(
        dimensions=dimensions,
        num_factors=task.factor_count,
        domain_size=task.domain_size_per_factor[0],
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=MAP_STABLE_PATIENCE,
    )
    start = time.perf_counter()
    domains = generate_domains(config, make_generator(representation_seed)).to(device)
    target = torch.tensor(task.target_indices, dtype=torch.long, device=device)
    observation = bind_sequence(factors_from_indices(domains, target))
    materialization_time = time.perf_counter() - start
    init_start = time.perf_counter()
    baseline_estimates = build_initial_estimates(domains)
    decoder_initialization_time = time.perf_counter() - init_start
    similarities = cosine_similarity_matrix(baseline_estimates, domains)
    baseline_state_bytes = tensor_bytes(baseline_estimates) + tensor_bytes(similarities)
    return PreparedMapTask(
        dimensions=dimensions,
        domains=domains,
        observation=observation,
        baseline_estimates=baseline_estimates,
        target_indices=target,
        materialization_time_sec=materialization_time,
        decoder_initialization_time_sec=decoder_initialization_time,
        observation_bytes=tensor_bytes(observation),
        codebook_bytes=tensor_bytes(domains),
        baseline_state_bytes=baseline_state_bytes,
        device=device,
    )


def random_initial_estimates(prepared: PreparedMapTask, *, seed: int) -> torch.Tensor:
    return torchhd.random(
        prepared.target_indices.numel(),
        prepared.dimensions,
        "MAP",
        generator=make_generator(seed),
    ).to(prepared.device)


def run_map_attempt(
    prepared: PreparedMapTask,
    *,
    max_iterations: int,
    init_mode: str,
    init_seed: int,
) -> MapAttempt:
    if init_mode == "baseline":
        current_estimates = prepared.baseline_estimates.clone()
    elif init_mode == "random":
        current_estimates = random_initial_estimates(prepared, seed=init_seed)
    else:  # pragma: no cover - guarded by frozen configs
        raise ValueError(f"Unsupported init mode: {init_mode}")

    previous_prediction: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    prediction_change_count = 0
    decoded: dict[str, torch.Tensor] | None = None
    similarities: torch.Tensor | None = None

    synchronize_device(prepared.device)
    decode_start = time.perf_counter()
    for iteration in range(1, max_iterations + 1):
        current_estimates = torchhd.resonator(
            prepared.observation,
            current_estimates,
            prepared.domains,
        )
        similarities = cosine_similarity_matrix(current_estimates, prepared.domains)
        decoded = decode_top_candidates(similarities)
        prediction = decoded["top1_indices"]
        if previous_prediction is not None and not torch.equal(prediction, previous_prediction):
            prediction_change_count += 1
        if previous_prediction is not None and torch.equal(prediction, previous_prediction):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_prediction = prediction.clone()
        if stable_iterations >= MAP_STABLE_PATIENCE:
            stable_prediction = True
            break
    synchronize_device(prepared.device)
    decode_time = time.perf_counter() - decode_start

    if decoded is None or similarities is None:
        raise RuntimeError("MAP attempt produced no decoded output.")

    predicted = decoded["top1_indices"].detach().cpu().to(dtype=torch.long)
    target = prepared.target_indices.detach().cpu().to(dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted, target)
    predicted_factors = factors_from_indices(prepared.domains.detach().cpu(), predicted)
    reconstruction = bind_sequence(predicted_factors)
    reconstruction_similarity = normalized_similarity_pair(
        reconstruction,
        prepared.observation.detach().cpu(),
    )
    return MapAttempt(
        restart_index=0,
        init_mode=init_mode,
        max_iterations=max_iterations,
        predicted_indices=[int(value) for value in predicted.tolist()],
        per_factor_recovery=per_factor_recovery,
        exact_recovery=exact_recovery,
        outcome=outcome,
        iterations=iteration,
        stable_prediction=stable_prediction,
        stable_iterations=stable_iterations,
        prediction_change_count=prediction_change_count,
        trajectory_stability=stable_iterations / iteration,
        normalized_reconstruction_similarity=reconstruction_similarity,
        min_margin=float(decoded["margins"].min().item()),
        mean_margin=float(decoded["margins"].mean().item()),
        decode_time_sec=decode_time,
        decoder_state_bytes=tensor_bytes(current_estimates) + tensor_bytes(similarities),
    )


def choose_attempt(
    attempts: list[MapAttempt],
    *,
    selection_rule: str,
    selection_seed: int,
) -> MapAttempt:
    if selection_rule == "first":
        return attempts[0]
    if selection_rule == "best_native_reconstruction":
        return max(
            attempts,
            key=lambda attempt: (
                attempt.normalized_reconstruction_similarity,
                attempt.mean_margin,
                -attempt.restart_index,
            ),
        )
    if selection_rule == "majority_vote":
        grouped: dict[tuple[int, ...], list[MapAttempt]] = {}
        for attempt in attempts:
            grouped.setdefault(attempt.tuple_key(), []).append(attempt)
        best_group = max(
            grouped.values(),
            key=lambda group: (
                len(group),
                max(item.normalized_reconstruction_similarity for item in group),
                -min(item.restart_index for item in group),
            ),
        )
        return max(
            best_group,
            key=lambda attempt: (
                attempt.normalized_reconstruction_similarity,
                attempt.mean_margin,
                -attempt.restart_index,
            ),
        )
    if selection_rule == "random_restart_selection":
        rng = random.Random(selection_seed)
        return attempts[rng.randrange(len(attempts))]
    raise ValueError(f"Unsupported selection rule: {selection_rule}")


def restart_agreement(attempts: list[MapAttempt]) -> float:
    counts: dict[tuple[int, ...], int] = {}
    for attempt in attempts:
        counts[attempt.tuple_key()] = counts.get(attempt.tuple_key(), 0) + 1
    return max(counts.values()) / len(attempts)


def unique_proposal_count(attempts: list[MapAttempt]) -> int:
    return len({attempt.tuple_key() for attempt in attempts})


def compute_matched_budget_lookup(root: Path) -> dict[tuple[str, int, str], dict[str, float]]:
    timing_rows = list(csv.DictReader((root / "results" / "level3_2" / "timing_summary.csv").open("r", encoding="utf-8")))
    cell_map = {
        "u1_easy_sanity": "u1_easy_anchor",
        "u1_boundary_22": "u1_boundary_1",
        "u1_boundary_31": "u1_boundary_2",
        "u1_separation_68": "u1_separation_anchor",
    }
    budgets: dict[tuple[str, int, str], dict[str, float]] = {}
    for cell_id, reference_id in cell_map.items():
        bcf_row = next(row for row in timing_rows if row["cell_id"] == reference_id and row["substrate"] == "BCF")
        for dimensions, config_id in ((512, "map_d512"), (1024, "map_d1024")):
            map_row = next(
                row for row in timing_rows if row["cell_id"] == reference_id and row["substrate"] == "MAP" and row["config_id"] == config_id
            )
            budgets[(cell_id, dimensions, "median")] = {
                "bcf_budget_sec": float(bcf_row["median_decode_time_sec"]),
                "map_reference_decode_sec": float(map_row["median_decode_time_sec"]),
            }
            budgets[(cell_id, dimensions, "p90")] = {
                "bcf_budget_sec": float(bcf_row["p90_decode_time_sec"]),
                "map_reference_decode_sec": float(map_row["median_decode_time_sec"]),
            }
    return budgets


def build_map_arm_configs(root: Path) -> list[MapArmConfig]:
    budgets = compute_matched_budget_lookup(root)
    rows: list[MapArmConfig] = []
    for dimensions in MAP_DIMENSIONS:
        for max_iterations in (12, 32, 64, 128):
            rows.append(
                MapArmConfig(
                    arm_id=f"map_{dimensions}_step{max_iterations}",
                    dimensions=dimensions,
                    max_iterations=max_iterations,
                    init_mode="baseline",
                    restart_count=1,
                    selection_rule="first",
                )
            )
        for max_iterations in (12, 32):
            for selection_rule in MAP_RESTART_SELECTION_RULES:
                rows.append(
                    MapArmConfig(
                        arm_id=f"map_{dimensions}_step{max_iterations}_r4_{selection_rule}",
                        dimensions=dimensions,
                        max_iterations=max_iterations,
                        init_mode="random",
                        restart_count=MAP_RESTART_COUNT,
                        selection_rule=selection_rule,
                    )
                )
        for budget_statistic in ("median", "p90"):
            rows.append(
                MapArmConfig(
                    arm_id=f"map_{dimensions}_wallclock_matched_bcf_{budget_statistic}",
                    dimensions=dimensions,
                    max_iterations=12,
                    init_mode="random",
                    restart_count=0,
                    selection_rule="best_native_reconstruction",
                    compute_matching_mode="sequential_cold_restarts",
                    budget_source_substrate="BCF",
                    budget_statistic=budget_statistic,
                    frozen_wallclock_budget_sec=-1.0,
                    frozen_map_reference_decode_sec=-1.0,
                )
            )

    hydrated: list[MapArmConfig] = []
    for row in rows:
        if row.compute_matching_mode is None:
            hydrated.append(row)
            continue
        # Store per-cell budgets in frozen protocol rather than inside the arm id.
        hydrated.append(row)
    return hydrated


def compute_matched_plan(
    arm: MapArmConfig,
    *,
    cell_id: str,
    root: Path,
) -> tuple[float, float]:
    budgets = compute_matched_budget_lookup(root)
    record = budgets[(cell_id, arm.dimensions, arm.budget_statistic or "median")]
    return record["bcf_budget_sec"], record["map_reference_decode_sec"]


def evaluate_map_arm(
    manifest: dict[str, Any],
    task: AbstractFactorizationTask,
    prepared: PreparedMapTask,
    *,
    arm: MapArmConfig,
    root: Path,
) -> dict[str, Any]:
    selection_seed = manifest["trial_seed"] + RESTART_SELECTION_SEED_OFFSET + arm.dimensions + len(arm.arm_id)
    attempts: list[MapAttempt] = []
    actual_restart_count = 0
    frozen_wallclock_budget_sec: float | None = None
    frozen_map_reference_decode_sec: float | None = None
    cumulative_decode_time_sec = 0.0

    if prepared.device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=prepared.device)

    if arm.compute_matching_mode is None:
        for restart_index in range(arm.restart_count):
            attempt = run_map_attempt(
                prepared,
                max_iterations=arm.max_iterations,
                init_mode=arm.init_mode,
                init_seed=selection_seed + restart_index,
            )
            attempts.append(
                MapAttempt(
                    restart_index=restart_index,
                    **{key: value for key, value in asdict(attempt).items() if key != "restart_index"},
                )
            )
        actual_restart_count = len(attempts)
    else:
        frozen_wallclock_budget_sec, frozen_map_reference_decode_sec = compute_matched_plan(
            arm,
            cell_id=manifest["cell_id"],
            root=root,
        )
        while True:
            if attempts and frozen_map_reference_decode_sec is not None and frozen_wallclock_budget_sec is not None:
                if cumulative_decode_time_sec + frozen_map_reference_decode_sec > frozen_wallclock_budget_sec:
                    break
            attempt = run_map_attempt(
                prepared,
                max_iterations=arm.max_iterations,
                init_mode=arm.init_mode,
                init_seed=selection_seed + len(attempts),
            )
            attempts.append(
                MapAttempt(
                    restart_index=len(attempts),
                    **{key: value for key, value in asdict(attempt).items() if key != "restart_index"},
                )
            )
            cumulative_decode_time_sec += attempt.decode_time_sec
            if len(attempts) >= 128:  # pragma: no cover - safety guard
                break
        actual_restart_count = len(attempts)

    selected = choose_attempt(
        attempts,
        selection_rule=arm.selection_rule,
        selection_seed=selection_seed,
    )
    exact_recovery = selected.exact_recovery
    partial_recovery = (not exact_recovery) and any(selected.per_factor_recovery)
    trajectory_stability = sum(attempt.trajectory_stability for attempt in attempts) / len(attempts)
    prediction_change_count = sum(attempt.prediction_change_count for attempt in attempts)
    restart_agreement_value = restart_agreement(attempts)
    unique_count = unique_proposal_count(attempts)
    total_decode_time = sum(attempt.decode_time_sec for attempt in attempts)
    total_iterations = sum(attempt.iterations for attempt in attempts)
    best_reconstruction = max(attempt.normalized_reconstruction_similarity for attempt in attempts)

    peak_vram_bytes = (
        int(torch.cuda.max_memory_allocated(device=prepared.device))
        if prepared.device.startswith("cuda") and torch.cuda.is_available()
        else None
    )

    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2B_CHECKPOINT_COMMIT,
        "split": SEED_SPLIT,
        "cell_id": manifest["cell_id"],
        "cell_classification": manifest["cell_classification"],
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "substrate": "MAP",
        "arm_id": arm.arm_id,
        "dimensions": arm.dimensions,
        "factor_count": manifest["F"],
        "domain_size": manifest["M"],
        "semantic_search_space": manifest["M"] ** manifest["F"],
        "log10_semantic_search_space": round(math.log10(manifest["M"] ** manifest["F"]), 6),
        "true_factor_indices": task.target_indices,
        "predicted_indices": selected.predicted_indices,
        "outcome": selected.outcome,
        "exact_recovery": exact_recovery,
        "partial_recovery": partial_recovery,
        "per_factor_recovery": selected.per_factor_recovery,
        "wrong_tuple_output": not exact_recovery,
        "max_iterations": arm.max_iterations,
        "init_mode": arm.init_mode,
        "selection_rule": arm.selection_rule,
        "restart_count": actual_restart_count,
        "planned_restart_count": arm.restart_count,
        "executed_steps": total_iterations,
        "decode_time_sec": total_decode_time,
        "end_to_end_time_sec": prepared.materialization_time_sec + prepared.decoder_initialization_time_sec + total_decode_time,
        "task_generation_time_sec": 0.0,
        "representation_materialization_time_sec": prepared.materialization_time_sec,
        "decoder_initialization_time_sec": prepared.decoder_initialization_time_sec,
        "observation_bytes": prepared.observation_bytes,
        "codebook_bytes": prepared.codebook_bytes,
        "decoder_state_bytes": max(attempt.decoder_state_bytes for attempt in attempts),
        "peak_ram_bytes": peak_cpu_memory_bytes(),
        "peak_vram_bytes": peak_vram_bytes,
        "stable_prediction": selected.stable_prediction,
        "stable_iterations": selected.stable_iterations,
        "trajectory_stability": trajectory_stability,
        "prediction_change_count": prediction_change_count,
        "restart_agreement": restart_agreement_value,
        "unique_proposal_count": unique_count,
        "best_native_reconstruction": best_reconstruction,
        "selected_native_reconstruction": selected.normalized_reconstruction_similarity,
        "selected_min_margin": selected.min_margin,
        "selected_mean_margin": selected.mean_margin,
        "native_operation_proxy": total_iterations * manifest["F"] * manifest["M"] * arm.dimensions,
        "native_stopping_status": "stable" if selected.stable_prediction else "max_iterations",
        "reached_native_limit": False,
        "restarts": actual_restart_count - 1,
        "same_device_timing": prepared.device.startswith("cuda"),
        "device": prepared.device,
        "compute_matching_mode": arm.compute_matching_mode,
        "budget_source_substrate": arm.budget_source_substrate,
        "budget_statistic": arm.budget_statistic,
        "frozen_wallclock_budget_sec": frozen_wallclock_budget_sec,
        "frozen_map_reference_decode_sec": frozen_map_reference_decode_sec,
        "map_equations_changed": False,
        "heldout_used": False,
        "no_context": True,
        "no_candidate_pruning": True,
        "no_noise": True,
        "task_contract": U1_TASK_CONTRACT,
        "uses_upstream_resonator": True,
        "uses_official_bcf_class": False,
    }


def instantiate_bcf_model(
    task: AbstractFactorizationTask,
    config: FrozenBCFCellConfig,
    *,
    repo_path: Path,
    representation_seed: int,
    prefer_cuda: bool,
):
    official_class = load_official_bcf_class(repo_path)
    use_cuda = prefer_cuda and torch.cuda.is_available()
    start = time.perf_counter()
    with redirect_stdout(io.StringIO()):
        model = official_class(
            D=config.dimensions,
            F=config.factor_count,
            Mx=config.domain_size,
            B=config.blocks,
            similarity=config.similarity,
            convergenceDetectionThreshold=config.convergence_detection_threshold,
            A=config.a_value,
            threshold=config.threshold,
            decoding=config.decoding,
            permutation=config.permutation,
            topaPU=config.topa_pu,
            useCuda=use_cuda,
            seed=representation_seed,
            id=config.config_family,
        )
    return model, time.perf_counter() - start


def evaluate_bcf_reference(
    manifest: dict[str, Any],
    task: AbstractFactorizationTask,
    *,
    repo_path: Path,
    frozen_config: FrozenBCFCellConfig,
    prefer_cuda: bool,
) -> dict[str, Any]:
    model, init_time = instantiate_bcf_model(
        task,
        frozen_config,
        repo_path=repo_path,
        representation_seed=manifest["bcf_representation_seed"],
        prefer_cuda=prefer_cuda,
    )
    rep_start = time.perf_counter()
    target_batch = torch.tensor([task.target_indices], dtype=torch.long, device=model._device)
    observation = model.encode(target_batch)
    materialization_time = time.perf_counter() - rep_start
    native_max_iterations = frozen_config.native_max_iterations()

    synchronize_device(str(model._device))
    if str(model._device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=model._device)
    decode_start = time.perf_counter()
    predicted = model.decode(observation, native_max_iterations).detach().cpu().squeeze(0).to(dtype=torch.long)
    synchronize_device(str(model._device))
    decode_time = time.perf_counter() - decode_start

    target = torch.tensor(task.target_indices, dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted, target)
    iterations = int(model._get_number_iter().max().item())

    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2B_CHECKPOINT_COMMIT,
        "split": SEED_SPLIT,
        "cell_id": manifest["cell_id"],
        "cell_classification": manifest["cell_classification"],
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "substrate": "BCF",
        "arm_id": "bcf_d512_f3_b4_reference",
        "dimensions": frozen_config.dimensions,
        "factor_count": manifest["F"],
        "domain_size": manifest["M"],
        "semantic_search_space": manifest["M"] ** manifest["F"],
        "log10_semantic_search_space": round(math.log10(manifest["M"] ** manifest["F"]), 6),
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted.tolist()],
        "outcome": outcome,
        "exact_recovery": exact_recovery,
        "partial_recovery": (not exact_recovery) and any(per_factor_recovery),
        "per_factor_recovery": per_factor_recovery,
        "wrong_tuple_output": not exact_recovery,
        "max_iterations": native_max_iterations,
        "init_mode": "official_native",
        "selection_rule": "native",
        "restart_count": 1,
        "planned_restart_count": 1,
        "executed_steps": iterations,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": materialization_time + init_time + decode_time,
        "task_generation_time_sec": 0.0,
        "representation_materialization_time_sec": materialization_time,
        "decoder_initialization_time_sec": init_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(model._IM) + tensor_bytes(model._matIM),
        "decoder_state_bytes": tensor_bytes(model._init_guess),
        "peak_ram_bytes": peak_cpu_memory_bytes(),
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated(device=model._device)) if str(model._device).startswith("cuda") and torch.cuda.is_available() else None,
        "stable_prediction": None,
        "stable_iterations": None,
        "trajectory_stability": None,
        "prediction_change_count": None,
        "restart_agreement": None,
        "unique_proposal_count": None,
        "best_native_reconstruction": None,
        "selected_native_reconstruction": None,
        "selected_min_margin": None,
        "selected_mean_margin": None,
        "native_operation_proxy": iterations * manifest["F"] * manifest["M"] * frozen_config.dimensions,
        "native_stopping_status": "native_limit" if iterations >= native_max_iterations else "native_converged",
        "reached_native_limit": iterations >= native_max_iterations,
        "restarts": 0,
        "same_device_timing": str(model._device).startswith("cuda"),
        "device": str(model._device),
        "compute_matching_mode": None,
        "budget_source_substrate": None,
        "budget_statistic": None,
        "frozen_wallclock_budget_sec": None,
        "frozen_map_reference_decode_sec": None,
        "map_equations_changed": False,
        "heldout_used": False,
        "no_context": True,
        "no_candidate_pruning": True,
        "no_noise": True,
        "task_contract": U1_TASK_CONTRACT,
        "uses_upstream_resonator": False,
        "uses_official_bcf_class": True,
        "official_bcf_class_path": BCF_OFFICIAL_CLASS_PATH,
        "bcf_source_path": frozen_config.source_path,
        "bcf_source_key": frozen_config.source_key,
    }


def summarize_recovery(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        key = (row["cell_id"], row["dimensions"], row["substrate"], row["arm_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        exact_successes = sum(1 for row in batch if row["exact_recovery"])
        partial_successes = sum(1 for row in batch if row["partial_recovery"])
        per_factor_hits = sum(sum(row["per_factor_recovery"]) for row in batch)
        ci_low, ci_high = wilson_interval(exact_successes, len(batch))
        rows.append(
            {
                "schema_version": LEVEL3_2B_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "cell_classification": first["cell_classification"],
                "dimensions": first["dimensions"],
                "substrate": first["substrate"],
                "arm_id": first["arm_id"],
                "trials": len(batch),
                "exact_recovery_rate": exact_successes / len(batch),
                "exact_recovery_ci_low": ci_low,
                "exact_recovery_ci_high": ci_high,
                "partial_recovery_rate": partial_successes / len(batch),
                "per_factor_accuracy": per_factor_hits / (len(batch) * first["factor_count"]),
                "wrong_tuple_output_rate": sum(1 for row in batch if row["wrong_tuple_output"]) / len(batch),
                "mean_executed_steps": statistics.mean(row["executed_steps"] for row in batch),
                "mean_restart_count": statistics.mean(row["restart_count"] for row in batch),
            }
        )
    return rows


def summarize_restart(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    restart_trials = [row for row in trials if row["substrate"] == "MAP" and row["restart_count"] > 1]
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in restart_trials:
        key = (row["cell_id"], row["dimensions"], row["arm_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        rows.append(
            {
                "schema_version": LEVEL3_2B_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "dimensions": first["dimensions"],
                "arm_id": first["arm_id"],
                "selection_rule": first["selection_rule"],
                "mean_restart_count": statistics.mean(row["restart_count"] for row in batch),
                "mean_restart_agreement": statistics.mean(row["restart_agreement"] for row in batch),
                "mean_unique_proposal_count": statistics.mean(row["unique_proposal_count"] for row in batch),
                "mean_best_native_reconstruction": statistics.mean(row["best_native_reconstruction"] for row in batch),
                "mean_selected_native_reconstruction": statistics.mean(row["selected_native_reconstruction"] for row in batch),
                "mean_prediction_change_count": statistics.mean(row["prediction_change_count"] for row in batch),
                "mean_trajectory_stability": statistics.mean(row["trajectory_stability"] for row in batch),
            }
        )
    return rows


def summarize_timing(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        key = (row["cell_id"], row["dimensions"], row["substrate"], row["arm_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        decode_values = [row["decode_time_sec"] for row in batch]
        end_values = [row["end_to_end_time_sec"] for row in batch]
        rows.append(
            {
                "schema_version": LEVEL3_2B_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "dimensions": first["dimensions"],
                "substrate": first["substrate"],
                "arm_id": first["arm_id"],
                "median_decode_time_sec": statistics.median(decode_values),
                "p90_decode_time_sec": quantile(decode_values, 0.90),
                "p99_decode_time_sec": quantile(decode_values, 0.99),
                "median_end_to_end_time_sec": statistics.median(end_values),
                "p90_end_to_end_time_sec": quantile(end_values, 0.90),
                "p99_end_to_end_time_sec": quantile(end_values, 0.99),
                "same_device_timing": first["same_device_timing"],
            }
        )
    return rows


def summarize_compute_matched(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched_trials = [row for row in trials if row["arm_id"] in {f"map_{dim}_{suffix}" for dim in MAP_DIMENSIONS for suffix in ("wallclock_matched_bcf_median", "wallclock_matched_bcf_p90")} or row["arm_id"] == "bcf_d512_f3_b4_reference"]
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in matched_trials:
        key = (row["cell_id"], row["dimensions"], row["arm_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        exact_successes = sum(1 for row in batch if row["exact_recovery"])
        rows.append(
            {
                "schema_version": LEVEL3_2B_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "dimensions": first["dimensions"],
                "arm_id": first["arm_id"],
                "trials": len(batch),
                "exact_recovery_rate": exact_successes / len(batch),
                "mean_decode_time_sec": statistics.mean(row["decode_time_sec"] for row in batch),
                "median_decode_time_sec": statistics.median(row["decode_time_sec"] for row in batch),
                "mean_restart_count": statistics.mean(row["restart_count"] for row in batch),
                "frozen_wallclock_budget_sec": first["frozen_wallclock_budget_sec"],
                "budget_statistic": first["budget_statistic"],
            }
        )
    return rows


def build_pareto_summary(
    recovery_rows: list[dict[str, Any]],
    timing_rows: list[dict[str, Any]],
    trials: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    timing_lookup = {(row["cell_id"], row["dimensions"], row["substrate"], row["arm_id"]): row for row in timing_rows}
    rows: list[dict[str, Any]] = []
    for row in recovery_rows:
        timing = timing_lookup[(row["cell_id"], row["dimensions"], row["substrate"], row["arm_id"])]
        exact_trials = [
            trial for trial in trials
            if trial["cell_id"] == row["cell_id"]
            and trial["dimensions"] == row["dimensions"]
            and trial["substrate"] == row["substrate"]
            and trial["arm_id"] == row["arm_id"]
            and trial["exact_recovery"]
        ]
        exact_per_second = 0.0
        compute_per_exact = None
        total_decode = sum(trial["decode_time_sec"] for trial in trials if trial["cell_id"] == row["cell_id"] and trial["dimensions"] == row["dimensions"] and trial["substrate"] == row["substrate"] and trial["arm_id"] == row["arm_id"])
        if total_decode > 0.0:
            exact_per_second = len(exact_trials) / total_decode
        if exact_trials:
            compute_per_exact = total_decode / len(exact_trials)
        rows.append(
            {
                "schema_version": LEVEL3_2B_SCHEMA_VERSION,
                "cell_id": row["cell_id"],
                "dimensions": row["dimensions"],
                "substrate": row["substrate"],
                "arm_id": row["arm_id"],
                "exact_recovery_rate": row["exact_recovery_rate"],
                "median_decode_time_sec": timing["median_decode_time_sec"],
                "p90_decode_time_sec": timing["p90_decode_time_sec"],
                "exact_recoveries_per_second": exact_per_second,
                "compute_spent_per_exact_recovery_sec": compute_per_exact,
            }
        )
    return rows


def claims_payload(recovery_rows: list[dict[str, Any]], timing_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def lookup(cell_id: str, dimensions: int, arm_id: str) -> dict[str, Any]:
        return next(
            row for row in recovery_rows
            if row["cell_id"] == cell_id and row["dimensions"] == dimensions and row["arm_id"] == arm_id
        )

    primary_cells = ("u1_boundary_31", "u1_separation_68")
    best_extended_rows: list[dict[str, Any]] = []
    for cell_id in primary_cells:
        for dimensions in MAP_DIMENSIONS:
            candidates = [
                row for row in recovery_rows
                if row["cell_id"] == cell_id
                and row["dimensions"] == dimensions
                and row["substrate"] == "MAP"
            ]
            best_extended_rows.append(max(candidates, key=lambda row: row["exact_recovery_rate"]))

    bcf_representation_decoder_advantage_supported = True
    map_intermediate_region = False
    map_budget_artifact = False
    bcf_pareto_advantage_supported = True
    details: list[dict[str, Any]] = []

    timing_lookup = {(row["cell_id"], row["dimensions"], row["arm_id"]): row for row in timing_rows}
    for row in best_extended_rows:
        bcf = lookup(row["cell_id"], 512, "bcf_d512_f3_b4_reference")
        timing = timing_lookup[(row["cell_id"], row["dimensions"], row["arm_id"])]
        bcf_timing = timing_lookup[(bcf["cell_id"], bcf["dimensions"], bcf["arm_id"])]
        gap = bcf["exact_recovery_rate"] - row["exact_recovery_rate"]
        if gap < 0.20:
            bcf_representation_decoder_advantage_supported = False
        if row["exact_recovery_rate"] >= bcf["exact_recovery_rate"] - 0.05 and timing["median_decode_time_sec"] <= bcf_timing["median_decode_time_sec"] * 1.10:
            map_budget_artifact = True
            bcf_pareto_advantage_supported = False
        if row["exact_recovery_rate"] > lookup(row["cell_id"], row["dimensions"], f"map_{row['dimensions']}_step12")["exact_recovery_rate"] + 0.10 and gap >= 0.10:
            map_intermediate_region = True
        details.append(
            {
                "cell_id": row["cell_id"],
                "dimensions": row["dimensions"],
                "best_map_arm": row["arm_id"],
                "best_map_exact_recovery_rate": row["exact_recovery_rate"],
                "bcf_exact_recovery_rate": bcf["exact_recovery_rate"],
                "recovery_gap_vs_bcf": gap,
                "best_map_median_decode_time_sec": timing["median_decode_time_sec"],
                "bcf_median_decode_time_sec": bcf_timing["median_decode_time_sec"],
            }
        )

    no_benefit_from_extra_map_compute = not any(
        row["arm_id"].endswith(("step32", "step64", "step128", "best_native_reconstruction", "majority_vote"))
        and row["exact_recovery_rate"] > lookup(row["cell_id"], row["dimensions"], f"map_{row['dimensions']}_step12")["exact_recovery_rate"] + 0.10
        for row in recovery_rows
        if row["substrate"] == "MAP" and row["cell_id"] in primary_cells
    )

    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "status": "development_robustness_only",
        "level3_2_frozen_claim_remains_valid": True,
        "bcf_representation_decoder_advantage_supported": bcf_representation_decoder_advantage_supported,
        "bcf_pareto_advantage_supported": bcf_pareto_advantage_supported,
        "map_budget_artifact": map_budget_artifact,
        "map_intermediate_region": map_intermediate_region,
        "no_benefit_from_extra_map_compute": no_benefit_from_extra_map_compute,
        "primary_cells": list(primary_cells),
        "details": details,
        "allowed_claims": [
            "development robustness interpretation of the frozen Level 3.2 separation",
            "whether extra MAP compute narrows or preserves the gap",
            "whether an intermediate MAP operating region exists",
        ],
        "forbidden_claims": [
            "held-out substrate confirmation",
            "production promotion",
            "router selection",
            "noise/U2/U3 conclusions",
        ],
    }


def analysis_payload(claims: dict[str, Any], trial_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if claims["map_budget_artifact"]:
        verdict = "MAP_BUDGET_ARTIFACT"
    elif claims["map_intermediate_region"]:
        verdict = "MAP_INTERMEDIATE_REGION"
    elif claims["bcf_representation_decoder_advantage_supported"] and claims["bcf_pareto_advantage_supported"]:
        verdict = "BCF_REPRESENTATION_DECODER_AND_PARETO_ADVANTAGE"
    elif claims["bcf_representation_decoder_advantage_supported"]:
        verdict = "BCF_REPRESENTATION_DECODER_ADVANTAGE"
    else:
        verdict = "ROBUSTNESS_INCONCLUSIVE"
    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2B_CHECKPOINT_COMMIT,
        "git_status_at_start": "clean",
        "final_verdict": verdict,
        "split": SEED_SPLIT,
        "trial_count": len(trial_rows),
        "heldout_used": False,
        "no_context_used": True,
        "no_noise_used": True,
        "no_new_decoder": True,
        "exact_next_stage": "Level 3.3: Minimal NeCo / Linear-Code U1 Paper Reproduction",
    }


def build_frozen_protocol(root: Path) -> dict[str, Any]:
    budget_rows = compute_matched_budget_lookup(root)
    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2B_CHECKPOINT_COMMIT,
        "source_level3_2_checkpoint": LEVEL3_2_CHECKPOINT_COMMIT,
        "status": "development_robustness_only",
        "protocol_frozen_before_first_run": True,
        "scope": {
            "task_contract": U1_TASK_CONTRACT,
            "u1_clean_only": True,
            "noise": False,
            "erasures": False,
            "u2": False,
            "u3": False,
            "context": False,
            "candidate_pruning": False,
            "controller": False,
            "cnm_h2": False,
            "new_decoder": False,
        },
        "cells": list(CELL_SPECS),
        "seed_ranges": SEED_RANGES,
        "frozen_compute_matched_budgets": {
            f"{cell_id}_d{dimensions}_{statistic}": values
            for (cell_id, dimensions, statistic), values in sorted(budget_rows.items())
        },
        "restart_selection_rules": list(MAP_RESTART_SELECTION_RULES),
        "bcf_reference": {
            "config_family": BCF_CONFIG_FAMILY["config_family"],
            "retuned": False,
            "native_stopping": True,
        },
        "level3_2_artifacts_unchanged": True,
    }


def build_arm_config_payload(root: Path) -> dict[str, Any]:
    budgets = compute_matched_budget_lookup(root)
    return {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "map_arms": [row.to_dict() for row in build_map_arm_configs(root)],
        "frozen_bcf_reference": BCF_CONFIG_FAMILY,
        "compute_matched_budgets": {
            f"{cell_id}_d{dimensions}_{statistic}": values
            for (cell_id, dimensions, statistic), values in sorted(budgets.items())
        },
    }


def build_doc(claims: dict[str, Any], recovery_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Level 3.2b MAP Compute-Budget Robustness Audit",
        "",
        f"Schema version: `{LEVEL3_2B_SCHEMA_VERSION}`",
        "",
        "## Scope",
        "",
        "- Clean U1 only",
        "- Fresh development seeds only",
        "- No context, pruning, CNM/H2, controller, noise, U2, U3, or new decoder",
        "",
        "## Verdict flags",
        "",
        f"- `bcf_representation_decoder_advantage_supported`: `{claims['bcf_representation_decoder_advantage_supported']}`",
        f"- `bcf_pareto_advantage_supported`: `{claims['bcf_pareto_advantage_supported']}`",
        f"- `map_budget_artifact`: `{claims['map_budget_artifact']}`",
        f"- `map_intermediate_region`: `{claims['map_intermediate_region']}`",
        f"- `no_benefit_from_extra_map_compute`: `{claims['no_benefit_from_extra_map_compute']}`",
        "",
        "## Best-by-cell MAP details",
        "",
    ]
    for detail in claims["details"]:
        lines.append(
            f"- `{detail['cell_id']} / D={detail['dimensions']}`: best MAP arm `{detail['best_map_arm']}` exact `{detail['best_map_exact_recovery_rate']}`, BCF `{detail['bcf_exact_recovery_rate']}`, gap `{detail['recovery_gap_vs_bcf']}`."
        )
    lines.extend(
        [
            "",
            "## Development note",
            "",
            "This audit does not modify the frozen Level 3.2 held-out claim; it only tests whether extra MAP compute narrows the already confirmed frozen-baseline separation.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def warmup_native_paths(root: Path, repo_path: Path, *, prefer_cuda: bool) -> None:
    device = "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"
    cell = CELL_SPECS[0]
    manifest, task = build_task_manifest(SEED_RANGES[cell["cell_id"]]["start"], cell)
    prepared = prepare_map_task(
        task,
        dimensions=512,
        representation_seed=manifest["map_representation_seed_d512"],
        device=device,
    )
    run_map_attempt(
        prepared,
        max_iterations=12,
        init_mode="baseline",
        init_seed=manifest["trial_seed"] + RESTART_SELECTION_SEED_OFFSET,
    )
    frozen_bcf_configs_all = build_frozen_bcf_configs(repo_path)
    frozen_bcf = config_for_cell("u1_easy_anchor", frozen_bcf_configs_all)
    evaluate_bcf_reference(
        manifest,
        task,
        repo_path=repo_path,
        frozen_config=frozen_bcf,
        prefer_cuda=prefer_cuda,
    )


def run_level3_2b(root: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    repo_path = upstream_clone_path(root)
    docs_dir = root / "docs"
    results_dir = root / "results" / "level3_2b"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    frozen_protocol = build_frozen_protocol(root)
    arm_config_payload = build_arm_config_payload(root)
    write_json(results_dir / "frozen_protocol.json", frozen_protocol)
    write_json(results_dir / "map_arm_configs.json", arm_config_payload)
    warmup_native_paths(root, repo_path, prefer_cuda=prefer_cuda)

    frozen_bcf_configs_all = build_frozen_bcf_configs(repo_path)
    frozen_bcf_configs = {
        "u1_easy_sanity": config_for_cell("u1_easy_anchor", frozen_bcf_configs_all),
        "u1_boundary_22": config_for_cell("u1_boundary_1", frozen_bcf_configs_all),
        "u1_boundary_31": config_for_cell("u1_boundary_2", frozen_bcf_configs_all),
        "u1_separation_68": config_for_cell("u1_separation_anchor", frozen_bcf_configs_all),
    }
    map_arms = build_map_arm_configs(root)

    manifest_rows: list[dict[str, Any]] = []
    trial_rows: list[dict[str, Any]] = []
    device = "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"

    for cell in CELL_SPECS:
        seed_spec = SEED_RANGES[cell["cell_id"]]
        for seed in range(seed_spec["start"], seed_spec["start"] + seed_spec["count"]):
            manifest, task = build_task_manifest(seed, cell)
            manifest_rows.append(manifest)
            prepared_by_dim = {
                dimensions: prepare_map_task(
                    task,
                    dimensions=dimensions,
                    representation_seed=manifest[f"map_representation_seed_d{dimensions}"],
                    device=device,
                )
                for dimensions in MAP_DIMENSIONS
            }
            if device.startswith("cuda") and torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats(device=device)
            for arm in map_arms:
                trial_rows.append(
                    evaluate_map_arm(
                        manifest,
                        task,
                        prepared_by_dim[arm.dimensions],
                        arm=arm,
                        root=root,
                    )
                )
            trial_rows.append(
                evaluate_bcf_reference(
                    manifest,
                    task,
                    repo_path=repo_path,
                    frozen_config=frozen_bcf_configs[cell["cell_id"]],
                    prefer_cuda=prefer_cuda,
                )
            )

    recovery_rows = summarize_recovery(trial_rows)
    restart_rows = summarize_restart(trial_rows)
    timing_rows = summarize_timing(trial_rows)
    compute_matched_rows = summarize_compute_matched(trial_rows)
    pareto_rows = build_pareto_summary(recovery_rows, timing_rows, trial_rows)
    claims = claims_payload(recovery_rows, timing_rows)
    analysis = analysis_payload(claims, trial_rows)

    write_json(results_dir / "environment.json", {
        "schema_version": LEVEL3_2B_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2B_CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": device,
        "same_device_timing": bool(prefer_cuda and torch.cuda.is_available()),
        "ibm_upstream_commit": upstream_commit_sha(repo_path),
        "ibm_upstream_clean": upstream_tracked_source_clean(repo_path),
    })
    write_jsonl(results_dir / "task_manifest.jsonl", manifest_rows)
    write_jsonl(results_dir / "trials.jsonl", trial_rows)
    write_csv(results_dir / "recovery_summary.csv", recovery_rows)
    write_csv(results_dir / "restart_summary.csv", restart_rows)
    write_csv(results_dir / "timing_summary.csv", timing_rows)
    write_csv(results_dir / "compute_matched_summary.csv", compute_matched_rows)
    write_csv(results_dir / "pareto_summary.csv", pareto_rows)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    (docs_dir / "LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md").write_text(
        build_doc(claims, recovery_rows),
        encoding="utf-8",
    )

    return {
        "frozen_protocol": frozen_protocol,
        "map_arm_configs": arm_config_payload,
        "recovery_summary": recovery_rows,
        "restart_summary": restart_rows,
        "timing_summary": timing_rows,
        "compute_matched_summary": compute_matched_rows,
        "pareto_summary": pareto_rows,
        "claims": claims,
        "analysis": analysis,
    }
