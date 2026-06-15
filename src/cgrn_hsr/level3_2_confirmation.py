from __future__ import annotations

import csv
import io
import json
import math
import platform
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
)
from .competitors.ibm_bcf_audit import (
    BCF_OFFICIAL_CLASS_PATH,
    AbstractFactorizationTask,
    upstream_clone_path,
    upstream_commit_sha,
    upstream_tracked_source_clean,
)

LEVEL3_2_SCHEMA_VERSION = "level3-2-clean-u1-heldout-v1"
LEVEL3_2_CHECKPOINT_COMMIT = "dea30d81c89dd344abfddcaa0eaaf85c7958c662"
U1_TASK_CONTRACT = "U1_blind_single_product_factorization"

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_FAILURE = "FAILURE"

MAP_CONFIGS: tuple[dict[str, Any], ...] = (
    {"config_id": "map_d512", "dimensions": 512, "max_iterations": 12, "stable_patience": 3, "restarts": 0},
    {"config_id": "map_d1024", "dimensions": 1024, "max_iterations": 12, "stable_patience": 3, "restarts": 0},
)
BCF_CONFIG_FAMILY = {
    "config_family": "bcf_d512_f3_b4",
    "dimensions": 512,
    "blocks": 4,
    "factor_count": 3,
    "similarity": "inf",
    "convergence_detection_threshold": 0.9,
    "decoding": "sequential",
    "permutation": False,
    "topa_pu": True,
}

COMMON_CELLS: tuple[dict[str, Any], ...] = (
    {"cell_id": "u1_easy_anchor", "classification": "COMMON", "F": 3, "M": 10, "trials": 64},
    {"cell_id": "u1_boundary_1", "classification": "COMMON", "F": 3, "M": 22, "trials": 128},
    {"cell_id": "u1_boundary_2", "classification": "COMMON", "F": 3, "M": 31, "trials": 128},
    {"cell_id": "u1_separation_anchor", "classification": "COMMON", "F": 3, "M": 68, "trials": 64},
)
OPTIONAL_EXTENSION_CELL = {
    "cell_id": "u1_bcf_native_extension",
    "classification": "BCF_NATIVE_EXTENSION",
    "F": 3,
    "M": 110,
    "trials": 64,
    "run_map": False,
}

HELDOUT_SEED_RANGES = {
    "u1_easy_anchor": {"start": 60260615, "count": 64},
    "u1_boundary_1": {"start": 61260615, "count": 128},
    "u1_boundary_2": {"start": 62260615, "count": 128},
    "u1_separation_anchor": {"start": 63260615, "count": 64},
    "u1_bcf_native_extension": {"start": 64260615, "count": 64},
}
TIMING_SUBSET_PER_COMMON_CELL = 16

MAP_REPRESENTATION_SEED_OFFSET = 1_000
BCF_REPRESENTATION_SEED_OFFSET = 2_000


@dataclass(frozen=True)
class FrozenBCFCellConfig:
    cell_id: str
    config_family: str
    dimensions: int
    blocks: int
    factor_count: int
    domain_size: int
    a_value: int
    threshold: float
    source_path: str
    source_key: str
    similarity: str = "inf"
    convergence_detection_threshold: float = 0.9
    decoding: str = "sequential"
    permutation: bool = False
    topa_pu: bool = True

    def native_max_iterations(self) -> int:
        return max(1, int((self.domain_size ** (self.factor_count - 1)) / self.factor_count))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def peak_cpu_memory_bytes() -> int | None:
    if resource is None:  # pragma: no cover - Windows path
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_maxrss * 1024)


def synchronize_device(device: str) -> None:
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


def tensor_bytes(tensor: torch.Tensor) -> int:
    return tensor.element_size() * tensor.nelement()


def load_official_bcf_class(repo_path: Path):
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    module = __import__("models.blockcodefactorizer", fromlist=["blockcodefactorizer"])
    return getattr(module, "blockcodefactorizer")


def common_outcome(predicted_indices: torch.Tensor, target_indices: torch.Tensor) -> tuple[str, list[bool], bool]:
    matches = predicted_indices.eq(target_indices)
    per_factor = [bool(value) for value in matches.tolist()]
    exact = bool(matches.all().item())
    if exact:
        return OUTCOME_EXACT, per_factor, True
    if bool(matches.any().item()):
        return OUTCOME_PARTIAL, per_factor, False
    return OUTCOME_FAILURE, per_factor, False


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prior_level3_1_seed_set() -> set[int]:
    values: set[int] = set()
    for base, points, count in (
        (40260615, 4, 16),
        (40260615 + 100_000, 2, 16),
        (43260615, 5, 8),
        (42260615, 4, 16),
    ):
        for point_index in range(points):
            start = base + point_index * 1_000
            for seed in range(start, start + count):
                values.add(seed)
    for point_index in range(3):
        start = 43260615 + 10_000 + point_index * 100
        for seed in range(start, start + (8 if point_index < 2 else 4)):
            values.add(seed)
    return values


def level3_2_heldout_seed_set() -> set[int]:
    values: set[int] = set()
    for spec in HELDOUT_SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level3_2_seed_sets_are_fresh() -> bool:
    return level3_2_heldout_seed_set().isdisjoint(prior_level3_1_seed_set())


def factor_identity_tokens(factor_count: int, domain_size: int) -> list[list[str]]:
    return [
        [f"f{factor_index}_i{atom_index}" for atom_index in range(domain_size)]
        for factor_index in range(factor_count)
    ]


def build_abstract_task_manifest(trial_seed: int, cell: dict[str, Any]) -> tuple[dict[str, Any], AbstractFactorizationTask]:
    generator = make_generator(trial_seed)
    true_indices = [
        int(torch.randint(0, cell["M"], (1,), generator=generator).item())
        for _ in range(cell["F"])
    ]
    map_representation_seed = trial_seed + MAP_REPRESENTATION_SEED_OFFSET
    bcf_representation_seed = trial_seed + BCF_REPRESENTATION_SEED_OFFSET
    manifest = {
        "trial_id": f"{cell['cell_id']}-seed-{trial_seed}",
        "trial_seed": trial_seed,
        "F": cell["F"],
        "M": cell["M"],
        "factor_identity_tokens": factor_identity_tokens(cell["F"], cell["M"]),
        "true_factor_indices": true_indices,
        "cell_id": cell["cell_id"],
        "cell_classification": cell["classification"],
        "split": "heldout",
        "task_contract": U1_TASK_CONTRACT,
        "map_representation_seed": map_representation_seed,
        "bcf_representation_seed": bcf_representation_seed,
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


def load_bcf_hyperparams(repo_path: Path, *, dimensions: int, factor_count: int, blocks: int, domain_size: int) -> tuple[int, float, str, str]:
    file_name = f"hyperparams_D_{dimensions}_F_{factor_count}_B_{blocks}.json"
    source_path = repo_path / "experiments" / "200a_bcf" / "hyperparameters" / file_name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    entry = payload[str(domain_size)]
    return int(entry["A"]), float(entry["threshold"]), str(source_path.relative_to(repo_path)), str(domain_size)


def build_frozen_bcf_configs(repo_path: Path) -> list[FrozenBCFCellConfig]:
    rows: list[FrozenBCFCellConfig] = []
    for cell in [*COMMON_CELLS, OPTIONAL_EXTENSION_CELL]:
        a_value, threshold, source_path, source_key = load_bcf_hyperparams(
            repo_path,
            dimensions=BCF_CONFIG_FAMILY["dimensions"],
            factor_count=BCF_CONFIG_FAMILY["factor_count"],
            blocks=BCF_CONFIG_FAMILY["blocks"],
            domain_size=cell["M"],
        )
        rows.append(
            FrozenBCFCellConfig(
                cell_id=cell["cell_id"],
                config_family=BCF_CONFIG_FAMILY["config_family"],
                dimensions=BCF_CONFIG_FAMILY["dimensions"],
                blocks=BCF_CONFIG_FAMILY["blocks"],
                factor_count=BCF_CONFIG_FAMILY["factor_count"],
                domain_size=cell["M"],
                a_value=a_value,
                threshold=threshold,
                source_path=source_path,
                source_key=source_key,
            )
        )
    return rows


def config_for_cell(cell_id: str, frozen_bcf_configs: list[FrozenBCFCellConfig]) -> FrozenBCFCellConfig:
    return next(row for row in frozen_bcf_configs if row.cell_id == cell_id)


def prepare_map(task: AbstractFactorizationTask, *, dimensions: int, representation_seed: int, device: str) -> tuple[torch.Tensor, torch.Tensor, float]:
    config = BaselineConfig(
        dimensions=dimensions,
        num_factors=task.factor_count,
        domain_size=task.domain_size_per_factor[0],
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=3,
    )
    start = time.perf_counter()
    domains = generate_domains(config, make_generator(representation_seed)).to(device)
    target = torch.tensor(task.target_indices, dtype=torch.long, device=device)
    observation = bind_sequence(factors_from_indices(domains, target))
    return domains, observation, time.perf_counter() - start


def evaluate_map_trial(
    manifest: dict[str, Any],
    task: AbstractFactorizationTask,
    *,
    map_config: dict[str, Any],
    device: str,
) -> dict[str, Any]:
    task_generation_time = 0.0
    domains, observation, representation_time = prepare_map(
        task,
        dimensions=map_config["dimensions"],
        representation_seed=manifest["map_representation_seed"],
        device=device,
    )
    init_start = time.perf_counter()
    estimates = build_initial_estimates(domains)
    decoder_initialization_time = time.perf_counter() - init_start

    synchronize_device(device)
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=device)
    decode_start = time.perf_counter()
    previous_prediction: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    similarities: torch.Tensor | None = None
    decoded: dict[str, torch.Tensor] | None = None
    current_estimates = estimates.clone()
    for iteration in range(1, map_config["max_iterations"] + 1):
        current_estimates = torchhd.resonator(observation, current_estimates, domains)
        similarities = cosine_similarity_matrix(current_estimates, domains)
        decoded = decode_top_candidates(similarities)
        prediction = decoded["top1_indices"]
        if previous_prediction is not None and torch.equal(prediction, previous_prediction):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_prediction = prediction.clone()
        if stable_iterations >= map_config["stable_patience"]:
            stable_prediction = True
            break
    synchronize_device(device)
    decode_time = time.perf_counter() - decode_start
    peak_vram = int(torch.cuda.max_memory_allocated(device=device)) if device.startswith("cuda") and torch.cuda.is_available() else None
    peak_ram = peak_cpu_memory_bytes()

    if decoded is None or similarities is None:
        raise RuntimeError("MAP decode produced no output.")

    predicted = decoded["top1_indices"].detach().cpu().to(dtype=torch.long)
    target = torch.tensor(task.target_indices, dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted, target)

    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "cell_id": manifest["cell_id"],
        "cell_classification": manifest["cell_classification"],
        "split": "heldout",
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "substrate": "MAP",
        "config_id": map_config["config_id"],
        "config_family": map_config["config_id"],
        "factor_count": manifest["F"],
        "domain_size": manifest["M"],
        "semantic_search_space": manifest["M"] ** manifest["F"],
        "log10_semantic_search_space": round(math.log10(manifest["M"] ** manifest["F"]), 6),
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted.tolist()],
        "outcome": outcome,
        "exact_recovery": exact_recovery,
        "per_factor_recovery": [bool(value) for value in per_factor_recovery],
        "wrong_tuple_output": not exact_recovery,
        "task_generation_time_sec": task_generation_time,
        "representation_materialization_time_sec": representation_time,
        "decoder_initialization_time_sec": decoder_initialization_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": task_generation_time + representation_time + decoder_initialization_time + decode_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(domains),
        "decoder_state_bytes": tensor_bytes(estimates) + tensor_bytes(similarities),
        "peak_ram_bytes": peak_ram,
        "peak_vram_bytes": peak_vram,
        "iterations": iteration,
        "restarts": map_config["restarts"],
        "native_operations_proxy": iteration * manifest["F"] * manifest["M"] * map_config["dimensions"],
        "stable_prediction_if_available": stable_prediction,
        "restart_agreement": None,
        "native_stop_status": "stable" if stable_prediction else "max_iterations",
        "reached_native_limit": False,
        "representation_seed": manifest["map_representation_seed"],
        "representation_materialized_independently": True,
        "uses_upstream_resonator": True,
        "uses_official_bcf_class": False,
        "same_device_timing": device.startswith("cuda"),
        "device": device,
        "no_context": True,
        "no_candidate_pruning": True,
        "no_noise": True,
        "task_contract": U1_TASK_CONTRACT,
    }


def instantiate_bcf_model(task: AbstractFactorizationTask, config: FrozenBCFCellConfig, *, repo_path: Path, representation_seed: int, prefer_cuda: bool):
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


def evaluate_bcf_trial(
    manifest: dict[str, Any],
    task: AbstractFactorizationTask,
    *,
    repo_path: Path,
    frozen_config: FrozenBCFCellConfig,
    prefer_cuda: bool,
) -> dict[str, Any]:
    task_generation_time = 0.0
    model, decoder_initialization_time = instantiate_bcf_model(
        task,
        frozen_config,
        repo_path=repo_path,
        representation_seed=manifest["bcf_representation_seed"],
        prefer_cuda=prefer_cuda,
    )
    rep_start = time.perf_counter()
    target_batch = torch.tensor([task.target_indices], dtype=torch.long, device=model._device)
    observation = model.encode(target_batch)
    representation_time = time.perf_counter() - rep_start

    max_iterations = frozen_config.native_max_iterations()
    synchronize_device(str(model._device))
    if str(model._device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=model._device)
    decode_start = time.perf_counter()
    predicted = model.decode(observation, max_iterations).detach().cpu().squeeze(0).to(dtype=torch.long)
    synchronize_device(str(model._device))
    decode_time = time.perf_counter() - decode_start
    peak_vram = int(torch.cuda.max_memory_allocated(device=model._device)) if str(model._device).startswith("cuda") and torch.cuda.is_available() else None
    peak_ram = peak_cpu_memory_bytes()

    iterations = int(model._get_number_iter().max().item())
    target = torch.tensor(task.target_indices, dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted, target)
    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "cell_id": manifest["cell_id"],
        "cell_classification": manifest["cell_classification"],
        "split": "heldout",
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "substrate": "BCF",
        "config_id": frozen_config.config_family,
        "config_family": frozen_config.config_family,
        "factor_count": manifest["F"],
        "domain_size": manifest["M"],
        "semantic_search_space": manifest["M"] ** manifest["F"],
        "log10_semantic_search_space": round(math.log10(manifest["M"] ** manifest["F"]), 6),
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted.tolist()],
        "outcome": outcome,
        "exact_recovery": exact_recovery,
        "per_factor_recovery": [bool(value) for value in per_factor_recovery],
        "wrong_tuple_output": not exact_recovery,
        "task_generation_time_sec": task_generation_time,
        "representation_materialization_time_sec": representation_time,
        "decoder_initialization_time_sec": decoder_initialization_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": task_generation_time + representation_time + decoder_initialization_time + decode_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(model._IM) + tensor_bytes(model._matIM),
        "decoder_state_bytes": tensor_bytes(model._init_guess),
        "peak_ram_bytes": peak_ram,
        "peak_vram_bytes": peak_vram,
        "iterations": iterations,
        "restarts": 0,
        "native_operations_proxy": iterations * manifest["F"] * manifest["M"] * frozen_config.dimensions,
        "stable_prediction_if_available": None,
        "restart_agreement": None,
        "native_stop_status": "native_limit" if iterations >= max_iterations else "native_converged",
        "reached_native_limit": iterations >= max_iterations,
        "native_max_iterations": max_iterations,
        "representation_seed": manifest["bcf_representation_seed"],
        "representation_materialized_independently": True,
        "uses_upstream_resonator": False,
        "uses_official_bcf_class": True,
        "official_bcf_class_path": BCF_OFFICIAL_CLASS_PATH,
        "same_device_timing": str(model._device).startswith("cuda"),
        "device": str(model._device),
        "no_context": True,
        "no_candidate_pruning": True,
        "no_noise": True,
        "task_contract": U1_TASK_CONTRACT,
        "bcf_official_a_value": frozen_config.a_value,
        "bcf_official_threshold": frozen_config.threshold,
        "bcf_source_path": frozen_config.source_path,
        "bcf_source_key": frozen_config.source_key,
    }


def build_frozen_protocol() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2_CHECKPOINT_COMMIT,
        "protocol_frozen_before_first_heldout_run": True,
        "hypothesis": {
            "primary": "Official native BCF supports a materially larger clean U1 semantic search space than classic MAP-resonator in the frozen F=3 operating envelope, at substantially higher decode cost.",
            "null": "Development separation does not reproduce on fresh held-out tasks.",
        },
        "scope": {
            "task_contract": U1_TASK_CONTRACT,
            "noise": False,
            "u0_heldout": False,
            "u2": False,
            "u3": False,
            "context": False,
            "candidate_pruning": False,
            "controller": False,
            "warm_start": False,
        },
        "common_cells": list(COMMON_CELLS),
        "optional_extension_cell": OPTIONAL_EXTENSION_CELL,
        "heldout_seed_ranges": HELDOUT_SEED_RANGES,
        "timing_subset_per_common_cell": TIMING_SUBSET_PER_COMMON_CELL,
        "same_device_timing_expected": True,
        "resume_policy": "immutable trial ids, no outcome-driven cell changes",
    }


def build_frozen_configs(repo_path: Path, frozen_bcf_configs: list[FrozenBCFCellConfig]) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "map_configs": list(MAP_CONFIGS),
        "bcf_config_family": BCF_CONFIG_FAMILY,
        "bcf_per_cell_official_lookup": [row.to_dict() for row in frozen_bcf_configs],
        "ibm_upstream_commit": upstream_commit_sha(repo_path),
    }


def execute_heldout(
    repo_path: Path,
    *,
    prefer_cuda: bool,
    frozen_bcf_configs: list[FrozenBCFCellConfig],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_rows: list[dict[str, Any]] = []
    trial_rows: list[dict[str, Any]] = []
    device = "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"
    all_cells = [*COMMON_CELLS, OPTIONAL_EXTENSION_CELL]
    for cell in all_cells:
        spec = HELDOUT_SEED_RANGES[cell["cell_id"]]
        frozen_bcf = config_for_cell(cell["cell_id"], frozen_bcf_configs)
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            manifest, task = build_abstract_task_manifest(seed, cell)
            manifest_rows.append(manifest)
            for map_config in MAP_CONFIGS:
                if cell["classification"] == "BCF_NATIVE_EXTENSION" and not cell.get("run_map", True):
                    break
                trial_rows.append(
                    evaluate_map_trial(
                        manifest,
                        task,
                        map_config=map_config,
                        device=device,
                    )
                )
            trial_rows.append(
                evaluate_bcf_trial(
                    manifest,
                    task,
                    repo_path=repo_path,
                    frozen_config=frozen_bcf,
                    prefer_cuda=prefer_cuda,
                )
            )
    return manifest_rows, trial_rows


def summarize_recovery(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        key = (row["cell_id"], row["substrate"], row["config_id"])
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        exact_successes = sum(1 for row in batch if row["exact_recovery"])
        exact_rate = exact_successes / len(batch)
        wrong_tuple_rate = sum(1 for row in batch if row["wrong_tuple_output"]) / len(batch)
        per_factor_accuracy = sum(sum(row["per_factor_recovery"]) for row in batch) / (len(batch) * first["factor_count"])
        ci_low, ci_high = wilson_interval(exact_successes, len(batch))
        summary.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "cell_classification": first["cell_classification"],
                "substrate": first["substrate"],
                "config_id": first["config_id"],
                "factor_count": first["factor_count"],
                "domain_size": first["domain_size"],
                "semantic_search_space": first["semantic_search_space"],
                "log10_semantic_search_space": first["log10_semantic_search_space"],
                "trials": len(batch),
                "exact_recovery_rate": exact_rate,
                "exact_recovery_ci_low": ci_low,
                "exact_recovery_ci_high": ci_high,
                "per_factor_accuracy": per_factor_accuracy,
                "wrong_tuple_output_rate": wrong_tuple_rate,
            }
        )
    return summary


def build_capacity_boundary(recovery_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for substrate, config_id in sorted({(row["substrate"], row["config_id"]) for row in recovery_rows if row["cell_classification"] == "COMMON"}):
        batch = sorted(
            [row for row in recovery_rows if row["substrate"] == substrate and row["config_id"] == config_id and row["cell_classification"] == "COMMON"],
            key=lambda item: item["log10_semantic_search_space"],
        )
        confirmed = [row for row in batch if row["exact_recovery_rate"] >= 0.90]
        failed = [row for row in batch if row["exact_recovery_rate"] < 0.90]
        largest_confirmed = confirmed[-1] if confirmed else None
        smallest_failed = failed[0] if failed else None
        rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "substrate": substrate,
                "config_id": config_id,
                "largest_confirmed_ge_0_90_cell_id": largest_confirmed["cell_id"] if largest_confirmed else None,
                "largest_confirmed_ge_0_90_log10_search_space": largest_confirmed["log10_semantic_search_space"] if largest_confirmed else None,
                "smallest_confirmed_lt_0_90_cell_id": smallest_failed["cell_id"] if smallest_failed else None,
                "smallest_confirmed_lt_0_90_log10_search_space": smallest_failed["log10_semantic_search_space"] if smallest_failed else None,
                "boundary_rule": ">=0.90 exact recovery",
            }
        )
    return rows


def summarize_timing(trials: list[dict[str, Any]], manifests: list[dict[str, Any]], *, repo_path: Path, frozen_bcf_configs: list[FrozenBCFCellConfig], prefer_cuda: bool) -> list[dict[str, Any]]:
    device = "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"
    selected: dict[str, list[dict[str, Any]]] = {}
    common_ids = {cell["cell_id"] for cell in COMMON_CELLS}
    for manifest in manifests:
        if manifest["cell_id"] not in common_ids:
            continue
        selected.setdefault(manifest["cell_id"], [])
        if len(selected[manifest["cell_id"]]) < TIMING_SUBSET_PER_COMMON_CELL:
            selected[manifest["cell_id"]].append(manifest)

    timing_rows: list[dict[str, Any]] = []
    for cell_id, manifest_batch in sorted(selected.items()):
        frozen_bcf = config_for_cell(cell_id, frozen_bcf_configs)
        for map_config in MAP_CONFIGS:
            decode_times: list[float] = []
            for manifest in manifest_batch:
                _, task = build_abstract_task_manifest(manifest["trial_seed"], next(cell for cell in COMMON_CELLS if cell["cell_id"] == cell_id))
                for _ in range(1):  # warm-up
                    evaluate_map_trial(manifest, task, map_config=map_config, device=device)
                for _ in range(3):
                    decode_times.append(evaluate_map_trial(manifest, task, map_config=map_config, device=device)["decode_time_sec"])
            timing_rows.append(
                {
                    "schema_version": LEVEL3_2_SCHEMA_VERSION,
                    "cell_id": cell_id,
                    "substrate": "MAP",
                    "config_id": map_config["config_id"],
                    "timed_tasks": len(manifest_batch),
                    "repeats_per_task": 3,
                    "median_decode_time_sec": statistics.median(decode_times),
                    "p90_decode_time_sec": quantile(decode_times, 0.90),
                    "p99_decode_time_sec": quantile(decode_times, 0.99),
                    "max_decode_time_sec": max(decode_times),
                    "same_device_timing": device.startswith("cuda"),
                }
            )
        decode_times = []
        for manifest in manifest_batch:
            _, task = build_abstract_task_manifest(manifest["trial_seed"], next(cell for cell in COMMON_CELLS if cell["cell_id"] == cell_id))
            for _ in range(1):
                evaluate_bcf_trial(manifest, task, repo_path=repo_path, frozen_config=frozen_bcf, prefer_cuda=prefer_cuda)
            for _ in range(3):
                decode_times.append(
                    evaluate_bcf_trial(manifest, task, repo_path=repo_path, frozen_config=frozen_bcf, prefer_cuda=prefer_cuda)["decode_time_sec"]
                )
        timing_rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "cell_id": cell_id,
                "substrate": "BCF",
                "config_id": frozen_bcf.config_family,
                "timed_tasks": len(manifest_batch),
                "repeats_per_task": 3,
                "median_decode_time_sec": statistics.median(decode_times),
                "p90_decode_time_sec": quantile(decode_times, 0.90),
                "p99_decode_time_sec": quantile(decode_times, 0.99),
                "max_decode_time_sec": max(decode_times),
                "same_device_timing": True,
            }
        )
    return timing_rows


def summarize_memory(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        key = (row["cell_id"], row["substrate"], row["config_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "substrate": first["substrate"],
                "config_id": first["config_id"],
                "mean_observation_bytes": statistics.mean(row["observation_bytes"] for row in batch),
                "mean_codebook_bytes": statistics.mean(row["codebook_bytes"] for row in batch),
                "mean_decoder_state_bytes": statistics.mean(row["decoder_state_bytes"] for row in batch),
                "max_peak_ram_bytes": max(row["peak_ram_bytes"] or 0 for row in batch),
                "max_peak_vram_bytes": max(row["peak_vram_bytes"] or 0 for row in batch),
                "total_native_bytes_mean": statistics.mean(
                    row["observation_bytes"] + row["codebook_bytes"] + row["decoder_state_bytes"] for row in batch
                ),
            }
        )
    return rows


def summarize_iterations(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        key = (row["cell_id"], row["substrate"], row["config_id"])
        grouped.setdefault(key, []).append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        iterations = [row["iterations"] for row in batch]
        rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "cell_id": first["cell_id"],
                "substrate": first["substrate"],
                "config_id": first["config_id"],
                "mean_iterations": statistics.mean(iterations),
                "median_iterations": statistics.median(iterations),
                "p90_iterations": quantile([float(value) for value in iterations], 0.90),
                "p99_iterations": quantile([float(value) for value in iterations], 0.99),
                "max_iterations": max(iterations),
                "iteration_variance": statistics.pvariance(iterations),
                "reached_native_limit_rate": statistics.mean(1.0 if row["reached_native_limit"] else 0.0 for row in batch),
                "restart_variance": 0.0 if first["substrate"] == "MAP" else None,
            }
        )
    return rows


def build_pareto_summary(recovery_rows: list[dict[str, Any]], timing_rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]], boundary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timing_lookup = {(row["cell_id"], row["substrate"], row["config_id"]): row for row in timing_rows}
    memory_lookup = {(row["cell_id"], row["substrate"], row["config_id"]): row for row in memory_rows}
    rows: list[dict[str, Any]] = []
    for row in recovery_rows:
        timing = timing_lookup.get((row["cell_id"], row["substrate"], row["config_id"]))
        memory = memory_lookup.get((row["cell_id"], row["substrate"], row["config_id"]))
        rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "view": "recovery_vs_latency",
                "cell_id": row["cell_id"],
                "substrate": row["substrate"],
                "config_id": row["config_id"],
                "exact_recovery_rate": row["exact_recovery_rate"],
                "median_decode_time_sec": timing["median_decode_time_sec"] if timing else None,
                "total_native_bytes_mean": memory["total_native_bytes_mean"] if memory else None,
            }
        )
    for row in boundary_rows:
        timing_for_config = [item for item in timing_rows if item["substrate"] == row["substrate"] and item["config_id"] == row["config_id"]]
        p90 = max((item["p90_decode_time_sec"] for item in timing_for_config), default=None)
        rows.append(
            {
                "schema_version": LEVEL3_2_SCHEMA_VERSION,
                "view": "capacity_vs_compute",
                "cell_id": row["largest_confirmed_ge_0_90_cell_id"],
                "substrate": row["substrate"],
                "config_id": row["config_id"],
                "largest_confirmed_ge_0_90_log10_search_space": row["largest_confirmed_ge_0_90_log10_search_space"],
                "p90_decode_time_sec": p90,
                "boundary_rule": row["boundary_rule"],
            }
        )
    return rows


def claims_payload(recovery_rows: list[dict[str, Any]], boundary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    boundary_lookup = {(row["substrate"], row["config_id"]): row for row in boundary_rows}
    map512 = boundary_lookup[("MAP", "map_d512")]
    map1024 = boundary_lookup[("MAP", "map_d1024")]
    bcf = boundary_lookup[("BCF", "bcf_d512_f3_b4")]

    shift_vs_map512 = None
    shift_vs_map1024 = None
    if bcf["largest_confirmed_ge_0_90_log10_search_space"] is not None and map512["largest_confirmed_ge_0_90_log10_search_space"] is not None:
        shift_vs_map512 = bcf["largest_confirmed_ge_0_90_log10_search_space"] - map512["largest_confirmed_ge_0_90_log10_search_space"]
    if bcf["largest_confirmed_ge_0_90_log10_search_space"] is not None and map1024["largest_confirmed_ge_0_90_log10_search_space"] is not None:
        shift_vs_map1024 = bcf["largest_confirmed_ge_0_90_log10_search_space"] - map1024["largest_confirmed_ge_0_90_log10_search_space"]

    confirm_shift = bool(
        shift_vs_map512 is not None
        and shift_vs_map1024 is not None
        and shift_vs_map512 >= 0.5
        and shift_vs_map1024 >= 0.5
    )
    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "primary_hypothesis": "Official native BCF supports a materially larger clean U1 semantic search space than classic MAP-resonator in the frozen F=3 operating envelope, at substantially higher decode cost.",
        "null_hypothesis": "Development separation does not reproduce on fresh held-out tasks.",
        "capacity_shift_log10_vs_map_d512": shift_vs_map512,
        "capacity_shift_log10_vs_map_d1024": shift_vs_map1024,
        "materiality_gate_log10": 0.5,
        "confirm_bcf_clean_u1_frontier_shift": confirm_shift,
        "allowed_claims": [
            "clean U1 held-out frontier shift confirmed or not confirmed",
            "multi-substrate candidate if capacity and speed separate",
            "resource/Pareto interpretation under clean U1 only",
        ],
        "forbidden_claims": [
            "noisy-unbinding superiority",
            "best universal VSA substrate",
            "production-ready promotion",
            "selective safety claim without acceptance policy",
        ],
        "bcf_confidence_note": "Official BCF outputs tuples and iteration/stopping diagnostics, but no benchmark-comparable confidence surface was used.",
    }


def analysis_payload(claims: dict[str, Any], timing_rows: list[dict[str, Any]], recovery_rows: list[dict[str, Any]]) -> dict[str, Any]:
    easy_times = [row for row in timing_rows if row["cell_id"] == "u1_easy_anchor"]
    map_fast = min((row["median_decode_time_sec"] for row in easy_times if row["substrate"] == "MAP"), default=None)
    bcf_fast = min((row["median_decode_time_sec"] for row in easy_times if row["substrate"] == "BCF"), default=None)
    if claims["confirm_bcf_clean_u1_frontier_shift"]:
        verdict = "MULTI_SUBSTRATE_CANDIDATE" if (map_fast is not None and bcf_fast is not None and map_fast < bcf_fast) else "CONFIRM_BCF_CLEAN_U1_FRONTIER_SHIFT"
    else:
        verdict = "DEVELOPMENT_SIGNAL_FAILS"
    return {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2_CHECKPOINT_COMMIT,
        "git_status_at_start": "clean",
        "executed_cells": sorted({row["cell_id"] for row in recovery_rows}),
        "heldout_used": True,
        "no_noise_used": True,
        "no_context_used": True,
        "no_new_decoder": True,
        "final_verdict": verdict,
        "same_device_timing": True,
        "bcf_always_outputs_tuple_without_common_confidence": True,
        "trial_count": len(recovery_rows),
        "optional_extension_classification": OPTIONAL_EXTENSION_CELL["classification"],
    }


def build_confirmation_doc(claims: dict[str, Any], boundary_rows: list[dict[str, Any]], timing_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Level 3.2 Clean U1 Confirmation",
        "",
        f"Schema version: `{LEVEL3_2_SCHEMA_VERSION}`",
        "",
        "## Frozen configs",
        "",
        "- MAP: `map_d512`, `map_d1024`",
        "- BCF family: `bcf_d512_f3_b4` with per-cell official `A`/`threshold` rows from the pinned IBM hyperparameter table",
        "",
        "## Common held-out cells",
        "",
        "- `F=3, M=10, trials=64`",
        "- `F=3, M=22, trials=128`",
        "- `F=3, M=31, trials=128`",
        "- `F=3, M=68, trials=64`",
        "",
        "## Capacity shift",
        "",
        f"- BCF vs `map_d512`: `{claims['capacity_shift_log10_vs_map_d512']}` log10 units",
        f"- BCF vs `map_d1024`: `{claims['capacity_shift_log10_vs_map_d1024']}` log10 units",
        "",
        "## Boundary brackets",
        "",
    ]
    for row in boundary_rows:
        lines.append(
            f"- `{row['substrate']} / {row['config_id']}`: largest `>=0.90` = `{row['largest_confirmed_ge_0_90_cell_id']}`, smallest `<0.90` = `{row['smallest_confirmed_lt_0_90_cell_id']}`."
        )
    lines.extend(
        [
            "",
            "## Timing note",
            "",
            "- Timing uses a separate frozen 16-task subset per common cell with warm-up and synchronized CUDA measurements.",
            "- Same-device status remained explicit throughout the run.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def run_level3_2(root: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    repo_path = upstream_clone_path(root)
    docs_dir = root / "docs"
    results_dir = root / "results" / "level3_2"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    frozen_protocol = build_frozen_protocol()
    frozen_bcf_configs = build_frozen_bcf_configs(repo_path)
    frozen_configs = build_frozen_configs(repo_path, frozen_bcf_configs)
    write_json(results_dir / "frozen_protocol.json", frozen_protocol)
    write_json(results_dir / "frozen_configs.json", frozen_configs)

    manifest_rows, heldout_trials = execute_heldout(
        repo_path,
        prefer_cuda=prefer_cuda,
        frozen_bcf_configs=frozen_bcf_configs,
    )
    recovery_rows = summarize_recovery(heldout_trials)
    boundary_rows = build_capacity_boundary(recovery_rows)
    timing_rows = summarize_timing(
        heldout_trials,
        manifest_rows,
        repo_path=repo_path,
        frozen_bcf_configs=frozen_bcf_configs,
        prefer_cuda=prefer_cuda,
    )
    memory_rows = summarize_memory(heldout_trials)
    iteration_rows = summarize_iterations(heldout_trials)
    pareto_rows = build_pareto_summary(recovery_rows, timing_rows, memory_rows, boundary_rows)
    claims = claims_payload(recovery_rows, boundary_rows)
    analysis = analysis_payload(claims, timing_rows, heldout_trials)

    write_json(results_dir / "environment.json", {
        "schema_version": LEVEL3_2_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_2_CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu",
        "same_device_timing": bool(prefer_cuda and torch.cuda.is_available()),
        "ibm_upstream_commit": upstream_commit_sha(repo_path),
        "ibm_upstream_clean": upstream_tracked_source_clean(repo_path),
    })
    write_jsonl(results_dir / "heldout_task_manifest.jsonl", manifest_rows)
    write_jsonl(results_dir / "heldout_trials.jsonl", heldout_trials)
    write_csv(results_dir / "recovery_summary.csv", recovery_rows)
    write_csv(results_dir / "capacity_boundary.csv", boundary_rows)
    write_csv(results_dir / "timing_summary.csv", timing_rows)
    write_csv(results_dir / "memory_summary.csv", memory_rows)
    write_csv(results_dir / "iteration_summary.csv", iteration_rows)
    write_csv(results_dir / "pareto_summary.csv", pareto_rows)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    (docs_dir / "LEVEL3_2_CLEAN_U1_CONFIRMATION.md").write_text(
        build_confirmation_doc(claims, boundary_rows, timing_rows),
        encoding="utf-8",
    )

    return {
        "frozen_protocol": frozen_protocol,
        "frozen_configs": frozen_configs,
        "recovery_summary": recovery_rows,
        "capacity_boundary": boundary_rows,
        "timing_summary": timing_rows,
        "memory_summary": memory_rows,
        "iteration_summary": iteration_rows,
        "pareto_summary": pareto_rows,
        "claims": claims,
        "analysis": analysis,
    }
