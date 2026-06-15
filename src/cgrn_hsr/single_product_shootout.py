from __future__ import annotations

import csv
import io
import importlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on Windows
    resource = None

import torch
import torchhd

from .baseline import (
    BaselineConfig,
    SyntheticContextHierarchy,
    bind_sequence,
    build_initial_estimates,
    build_synthetic_context_hierarchy,
    cosine_similarity_matrix,
    decode_top_candidates,
    factors_from_indices,
    generate_domains,
    l2_scores_for_factor,
    make_generator,
    normalized_similarity_pair,
    pilot_seed_set,
    predict_l2_context,
    sample_contextual_factor_index,
)
from .competitors.ibm_bcf_audit import (
    BCF_OFFICIAL_CLASS_PATH,
    IBM_BCF_AUDIT_SCHEMA_VERSION,
    AbstractFactorizationTask,
    upstream_clone_path,
    upstream_commit_sha,
    upstream_tracked_source_clean,
)
from .query_context import (
    level1d_calibration_seed_set,
    level1d_evaluation_seed_set,
)
from .selective_policy import (
    level1e_development_seed_set,
    level1e_calibration_seed_set,
    level1e_heldout_seed_set,
)
from .warm_start import (
    level1e1_calibration_seed_set,
    level1e1_development_seed_set,
    level1e1_heldout_seed_set,
)

LEVEL1F3_SCHEMA_VERSION = "level1f3-single-product-v1"
LEVEL1F3_METHOD_VERSION = "single-product-map-vs-ibm-bcf-v1"
LEVEL1F3_PROTOCOL_AMENDMENT = (
    "Held-out evaluation narrowed to 128 primary / 64 stress / 64 easy trials after observing "
    "that the official IBM BCF implementation incurred high end-to-end cost under repeated "
    "independently materialized contextual-subset benchmark calls. This amendment preserves the "
    "primary cell at full requested size while bounding overnight runtime."
)
LEVEL1F3_CONFIG_MASTER_SEED = 31260614
LEVEL1F3_DEVELOPMENT_MASTER_SEED = 32260614
LEVEL1F3_HELDOUT_MASTER_SEED = 33260614
LEVEL1F3_CONFIG_TRIALS_PER_CELL = 32
LEVEL1F3_DEVELOPMENT_TRIALS_PER_CELL = 32
LEVEL1F3_HELDOUT_PRIMARY_TRIALS = 128
LEVEL1F3_HELDOUT_STRESS_TRIALS = 64
LEVEL1F3_HELDOUT_EASY_TRIALS = 64
LEVEL1F3_CAP_SELECTION_TRIALS = 8
MAP_CODEBOOK_SEED_OFFSET = 10_000
BCF_CODEBOOK_SEED_OFFSET = 20_000
CONTEXT_PREDICTION_SEED_OFFSET = 30_000
TIMING_SAMPLE_TRIALS_PER_CELL = 4
TIMING_WARMUP_REPEATS = 1
TIMING_MEASURE_REPEATS = 3
BCF_ITERATION_CAP_CANDIDATES = (16, 32, 64)

SUBSTRATE_MAP = "MAP"
SUBSTRATE_BCF = "BCF"
OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_FAILURE = "FAILURE"

METHOD_GLOBAL = "global"
METHOD_RANDOM_HALF = "random_unconditional_half"
METHOD_RANDOM_QUARTER = "random_unconditional_quarter"
METHOD_SEMANTIC_HALF = "semantic_l2_half"
METHOD_SEMANTIC_QUARTER = "semantic_l2_quarter"
METHOD_ORACLE_HALF = "oracle_truth_included_half"
METHOD_ORACLE_QUARTER = "oracle_truth_included_quarter"
ALL_METHODS = (
    METHOD_GLOBAL,
    METHOD_RANDOM_HALF,
    METHOD_RANDOM_QUARTER,
    METHOD_SEMANTIC_HALF,
    METHOD_SEMANTIC_QUARTER,
    METHOD_ORACLE_HALF,
    METHOD_ORACLE_QUARTER,
)
DEVELOPMENT_METHODS = (
    METHOD_GLOBAL,
    METHOD_RANDOM_HALF,
    METHOD_SEMANTIC_HALF,
    METHOD_ORACLE_HALF,
)


@dataclass(frozen=True)
class ShootoutCell:
    label: str
    operating_point_label: str
    config: BaselineConfig
    anomaly_rate: float
    context_accuracy: float


@dataclass(frozen=True)
class BCFConfigCandidate:
    config_id: str
    dimension: int
    blocks: int
    a_value: int
    threshold: float
    source_path: str
    source_key: str
    source_note: str
    convergence_detection_threshold: float = 0.9
    similarity: str = "inf"
    decoding: str = "sequential"
    topa_pu: bool = True
    permutation: bool = False
    iteration_cap: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskBundle:
    task: AbstractFactorizationTask
    hierarchy: SyntheticContextHierarchy
    target_indices: torch.Tensor
    predicted_l2: str
    context_prediction_correct: bool
    anomaly_count: int


@dataclass
class PreparedBCFTrial:
    model: Any
    observation: torch.Tensor
    full_im_cpu: torch.Tensor
    shared_materialization_time_sec: float
    max_iterations_cap: int
    use_cuda: bool


@dataclass
class PreparedMAPTrial:
    domains: torch.Tensor
    observation: torch.Tensor
    target_indices: torch.Tensor
    shared_materialization_time_sec: float
    device: str


@dataclass(frozen=True)
class TrialRecord:
    schema_version: str
    method_version: str
    upstream_commit_sha: str
    seed_split: str
    cell_id: str
    operating_point_label: str
    substrate: str
    method_id: str
    subset_size_label: str
    task_seed: int
    context_accuracy: float
    anomaly_rate: float
    factor_count: int
    domain_size: int
    representation_dimension: int
    target_indices: list[int]
    active_l1: str
    active_l2: str
    predicted_l2: str
    context_prediction_correct: bool
    candidate_subset_indices: list[list[int]]
    candidate_count: int
    truth_included_per_factor: list[bool]
    all_truth_included: bool
    predicted_indices: list[int]
    outcome: str
    exact_recovery: bool
    per_factor_recovery: list[bool]
    iterations: int
    materialization_time_sec: float
    factorization_time_sec: float
    end_to_end_task_time_sec: float
    native_codebook_bytes: int
    native_observation_bytes: int
    runtime_state_bytes: int | None
    peak_cuda_memory_bytes: int | None
    peak_cpu_memory_bytes: int | None
    device: str
    same_device_timing_status: str
    uses_upstream_resonator: bool
    uses_official_bcf_class: bool
    official_bcf_class_path: str | None
    bcf_config_id: str | None
    max_iterations_cap: int
    no_query_aware_mixture_input: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EASY_CELL = ShootoutCell(
    label="EASY_SINGLE",
    operating_point_label="EASY_SINGLE",
    config=BaselineConfig(
        dimensions=256,
        num_factors=3,
        domain_size=5,
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=3,
    ),
    anomaly_rate=0.1,
    context_accuracy=0.9,
)
PRIMARY_CELL = ShootoutCell(
    label="COLLAPSE_SINGLE_PRIMARY",
    operating_point_label="COLLAPSE_SINGLE",
    config=BaselineConfig(
        dimensions=1024,
        num_factors=4,
        domain_size=10,
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=3,
    ),
    anomaly_rate=0.1,
    context_accuracy=0.9,
)
STRESS_CELL = ShootoutCell(
    label="COLLAPSE_SINGLE_STRESS",
    operating_point_label="COLLAPSE_SINGLE",
    config=BaselineConfig(
        dimensions=1024,
        num_factors=4,
        domain_size=10,
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=3,
    ),
    anomaly_rate=0.25,
    context_accuracy=0.7,
)
ALL_CELLS = (PRIMARY_CELL, STRESS_CELL, EASY_CELL)


def level1f3_config_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        PRIMARY_CELL.label: {"start": LEVEL1F3_CONFIG_MASTER_SEED, "count": LEVEL1F3_CONFIG_TRIALS_PER_CELL},
        STRESS_CELL.label: {"start": LEVEL1F3_CONFIG_MASTER_SEED + 10_000, "count": LEVEL1F3_CONFIG_TRIALS_PER_CELL},
        EASY_CELL.label: {"start": LEVEL1F3_CONFIG_MASTER_SEED + 20_000, "count": LEVEL1F3_CONFIG_TRIALS_PER_CELL},
    }


def level1f3_development_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        PRIMARY_CELL.label: {"start": LEVEL1F3_DEVELOPMENT_MASTER_SEED, "count": LEVEL1F3_DEVELOPMENT_TRIALS_PER_CELL},
        STRESS_CELL.label: {"start": LEVEL1F3_DEVELOPMENT_MASTER_SEED + 10_000, "count": LEVEL1F3_DEVELOPMENT_TRIALS_PER_CELL},
        EASY_CELL.label: {"start": LEVEL1F3_DEVELOPMENT_MASTER_SEED + 20_000, "count": LEVEL1F3_DEVELOPMENT_TRIALS_PER_CELL},
    }


def level1f3_heldout_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        PRIMARY_CELL.label: {"start": LEVEL1F3_HELDOUT_MASTER_SEED, "count": LEVEL1F3_HELDOUT_PRIMARY_TRIALS},
        STRESS_CELL.label: {"start": LEVEL1F3_HELDOUT_MASTER_SEED + 10_000, "count": LEVEL1F3_HELDOUT_STRESS_TRIALS},
        EASY_CELL.label: {"start": LEVEL1F3_HELDOUT_MASTER_SEED + 20_000, "count": LEVEL1F3_HELDOUT_EASY_TRIALS},
    }


def seed_ranges_to_set(seed_ranges: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in seed_ranges.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level1f3_config_seed_set() -> set[int]:
    return seed_ranges_to_set(level1f3_config_seed_ranges())


def level1f3_development_seed_set() -> set[int]:
    return seed_ranges_to_set(level1f3_development_seed_ranges())


def level1f3_heldout_seed_set() -> set[int]:
    return seed_ranges_to_set(level1f3_heldout_seed_ranges())


def level1f3_seed_sets_are_disjoint() -> bool:
    config_set = level1f3_config_seed_set()
    development_set = level1f3_development_seed_set()
    heldout_set = level1f3_heldout_seed_set()
    prior_sets = (
        pilot_seed_set(),
        level1d_calibration_seed_set(),
        level1d_evaluation_seed_set(),
        level1e_development_seed_set(),
        level1e_calibration_seed_set(),
        level1e_heldout_seed_set(),
        level1e1_development_seed_set(),
        level1e1_calibration_seed_set(),
        level1e1_heldout_seed_set(),
    )
    return (
        config_set.isdisjoint(development_set)
        and config_set.isdisjoint(heldout_set)
        and development_set.isdisjoint(heldout_set)
        and all(config_set.isdisjoint(seed_set) for seed_set in prior_sets)
        and all(development_set.isdisjoint(seed_set) for seed_set in prior_sets)
        and all(heldout_set.isdisjoint(seed_set) for seed_set in prior_sets)
    )


def method_subset_size_label(method_id: str) -> str:
    if method_id == METHOD_GLOBAL:
        return "full"
    if method_id.endswith("_half"):
        return "half"
    if method_id.endswith("_quarter"):
        return "quarter"
    raise ValueError(f"Unknown method_id: {method_id}")


def subset_size_for_label(domain_size: int, size_label: str) -> int:
    if size_label == "full":
        return domain_size
    if size_label == "half":
        return math.ceil(domain_size / 2)
    if size_label == "quarter":
        return max(2, math.ceil(domain_size / 4))
    raise ValueError(f"Unknown size_label: {size_label}")


def method_selection_seed(task_seed: int, method_id: str) -> int:
    offsets = {
        METHOD_GLOBAL: 0,
        METHOD_RANDOM_HALF: 100,
        METHOD_RANDOM_QUARTER: 200,
        METHOD_SEMANTIC_HALF: 300,
        METHOD_SEMANTIC_QUARTER: 400,
        METHOD_ORACLE_HALF: 500,
        METHOD_ORACLE_QUARTER: 600,
    }
    return task_seed + offsets[method_id]


def build_context_membership_payload(
    hierarchy: SyntheticContextHierarchy,
    config: BaselineConfig,
) -> dict[str, dict[str, float]]:
    payload: dict[str, dict[str, float]] = {}
    for factor_index in range(config.num_factors):
        for atom_index in range(config.domain_size):
            weights = hierarchy.factor_l2_weights[factor_index, atom_index]
            payload[f"f{factor_index}_i{atom_index}"] = {
                hierarchy.l2_labels[label_index]: float(weights[label_index].item())
                for label_index in range(len(hierarchy.l2_labels))
                if float(weights[label_index].item()) > 0.0
            }
    return payload


def build_single_product_task(cell: ShootoutCell, seed: int) -> TaskBundle:
    generator = make_generator(seed)
    hierarchy = build_synthetic_context_hierarchy(cell.config, generator)
    active_l2_index = int(torch.randint(0, len(hierarchy.l2_labels), (1,), generator=generator).item())
    active_l2 = hierarchy.l2_labels[active_l2_index]
    active_l1 = hierarchy.l2_to_l1[active_l2]
    rng = random.Random(seed + 73)

    sampled_indices: list[int] = []
    anomaly_sources: list[str] = []
    for factor_index in range(cell.config.num_factors):
        sampled_index, anomaly_source = sample_contextual_factor_index(
            hierarchy=hierarchy,
            factor_index=factor_index,
            active_l1=active_l1,
            active_l2=active_l2,
            anomaly_rate=cell.anomaly_rate,
            generator=generator,
            rng=rng,
        )
        sampled_indices.append(sampled_index)
        anomaly_sources.append(anomaly_source)

    target_indices = torch.tensor(sampled_indices, dtype=torch.long)
    predicted_l2, context_prediction_correct = predict_l2_context(
        hierarchy=hierarchy,
        active_l2=active_l2,
        context_accuracy=cell.context_accuracy,
        selection_seed=seed + CONTEXT_PREDICTION_SEED_OFFSET,
    )
    task = AbstractFactorizationTask(
        task_seed=seed,
        factor_count=cell.config.num_factors,
        domain_size_per_factor=[cell.config.domain_size] * cell.config.num_factors,
        target_indices=[int(value) for value in target_indices.tolist()],
        distractor_target_indices=[],
        context_membership=build_context_membership_payload(hierarchy, cell.config),
        active_context=active_l2,
        anomaly_rate=cell.anomaly_rate,
        query_valid_source_indices=[],
        active_l1=active_l1,
        active_l2=active_l2,
        context_prediction={
            "predicted_l2": predicted_l2,
            "context_prediction_correct": context_prediction_correct,
            "selection_seed": seed + CONTEXT_PREDICTION_SEED_OFFSET,
        },
    )
    return TaskBundle(
        task=task,
        hierarchy=hierarchy,
        target_indices=target_indices,
        predicted_l2=predicted_l2,
        context_prediction_correct=context_prediction_correct,
        anomaly_count=sum(source != "active_l2" for source in anomaly_sources),
    )


def topk_indices_from_scores(scores: torch.Tensor, subset_size: int) -> torch.Tensor:
    return torch.argsort(scores, descending=True, stable=True)[:subset_size].to(dtype=torch.long)


def select_shared_candidate_subset(bundle: TaskBundle, method_id: str) -> torch.Tensor:
    domain_size = bundle.task.domain_size_per_factor[0]
    factor_count = bundle.task.factor_count
    size_label = method_subset_size_label(method_id)
    subset_size = subset_size_for_label(domain_size, size_label)

    if method_id == METHOD_GLOBAL:
        return torch.stack(
            [torch.arange(domain_size, dtype=torch.long) for _ in range(factor_count)],
            dim=0,
        )

    rng = random.Random(method_selection_seed(bundle.task.task_seed, method_id))
    rows: list[torch.Tensor] = []

    for factor_index in range(factor_count):
        if method_id in (METHOD_RANDOM_HALF, METHOD_RANDOM_QUARTER):
            rows.append(
                torch.tensor(
                    sorted(rng.sample(range(domain_size), subset_size)),
                    dtype=torch.long,
                )
            )
            continue

        if method_id in (METHOD_SEMANTIC_HALF, METHOD_SEMANTIC_QUARTER):
            scores = l2_scores_for_factor(bundle.hierarchy, factor_index, bundle.predicted_l2)
            rows.append(topk_indices_from_scores(scores, subset_size))
            continue

        if method_id in (METHOD_ORACLE_HALF, METHOD_ORACLE_QUARTER):
            truth_index = int(bundle.target_indices[factor_index].item())
            remaining = [index for index in range(domain_size) if index != truth_index]
            picked = sorted([truth_index, *rng.sample(remaining, subset_size - 1)])
            rows.append(torch.tensor(picked, dtype=torch.long))
            continue

        raise ValueError(f"Unknown method_id: {method_id}")

    return torch.stack(rows, dim=0)


def common_outcome(predicted_indices: torch.Tensor, target_indices: torch.Tensor) -> tuple[str, list[bool], bool]:
    per_factor_recovery = predicted_indices.eq(target_indices).tolist()
    exact_recovery = bool(all(per_factor_recovery))
    if exact_recovery:
        return OUTCOME_EXACT, per_factor_recovery, True
    if any(per_factor_recovery):
        return OUTCOME_PARTIAL, per_factor_recovery, False
    return OUTCOME_FAILURE, per_factor_recovery, False


def tensor_bytes(tensor: torch.Tensor) -> int:
    return int(tensor.numel() * tensor.element_size())


def peak_cpu_memory_bytes() -> int | None:
    if resource is None:
        return None
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
    except Exception:
        return None
    return int(usage.ru_maxrss * 1024)


def synchronize_device(device: str) -> None:
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


def measure_decode_timing(
    run_once,
    *,
    device: str,
    warmup_repeats: int,
    measure_repeats: int,
) -> tuple[dict[str, Any], float, int | None, int | None]:
    for _ in range(warmup_repeats):
        run_once()

    elapsed: list[float] = []
    peak_cuda_memory = None
    peak_cpu_memory = None
    last_result: dict[str, Any] | None = None

    for _ in range(measure_repeats):
        synchronize_device(device)
        if device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(device=device)
        start = time.perf_counter()
        last_result = run_once()
        synchronize_device(device)
        elapsed.append(time.perf_counter() - start)
        if device.startswith("cuda") and torch.cuda.is_available():
            current_peak = int(torch.cuda.max_memory_allocated(device=device))
            peak_cuda_memory = current_peak if peak_cuda_memory is None else max(peak_cuda_memory, current_peak)
        current_cpu_peak = peak_cpu_memory_bytes()
        if current_cpu_peak is not None:
            peak_cpu_memory = current_cpu_peak if peak_cpu_memory is None else max(peak_cpu_memory, current_cpu_peak)

    if last_result is None:
        raise RuntimeError("Timing helper did not execute the decode function.")

    return last_result, statistics.median(elapsed), peak_cuda_memory, peak_cpu_memory


def map_runtime_state_bytes(estimates: torch.Tensor, similarities: torch.Tensor) -> int:
    return tensor_bytes(estimates) + tensor_bytes(similarities)


def map_device_for_runtime(prefer_cuda: bool = True) -> str:
    return "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"


def prepare_map_trial(
    bundle: TaskBundle,
    cell: ShootoutCell,
    *,
    device: str,
) -> PreparedMAPTrial:
    materialization_start = time.perf_counter()
    domains = generate_domains(
        cell.config,
        make_generator(bundle.task.task_seed + MAP_CODEBOOK_SEED_OFFSET),
    ).to(device)
    target_indices = bundle.target_indices.to(device)
    observation = bind_sequence(factors_from_indices(domains, target_indices))
    shared_materialization_time = time.perf_counter() - materialization_start
    return PreparedMAPTrial(
        domains=domains,
        observation=observation,
        target_indices=target_indices,
        shared_materialization_time_sec=shared_materialization_time,
        device=device,
    )


def evaluate_map_trial(
    bundle: TaskBundle,
    cell: ShootoutCell,
    method_id: str,
    candidate_indices: torch.Tensor,
    *,
    device: str,
    prepared: PreparedMAPTrial | None = None,
    timing_repeats: int = 1,
    timing_warmup: int = 0,
) -> TrialRecord:
    if bundle.task.distractor_target_indices:
        raise ValueError("Level 1F.3 MAP evaluation only supports single-product tasks.")

    prepared_trial = prepared or prepare_map_trial(bundle, cell, device=device)
    materialization_start = time.perf_counter()
    domains = prepared_trial.domains
    candidate_indices_device = candidate_indices.to(device=device, dtype=torch.long)
    candidate_domains = torch.stack(
        [
            domains[factor_index].index_select(0, candidate_indices_device[factor_index])
            for factor_index in range(cell.config.num_factors)
        ],
        dim=0,
    )
    initial_estimates = build_initial_estimates(candidate_domains)
    materialization_time = prepared_trial.shared_materialization_time_sec + (time.perf_counter() - materialization_start)

    def run_once() -> dict[str, Any]:
        current_estimates = initial_estimates.clone()
        previous_indices: torch.Tensor | None = None
        stable_iterations = 0
        stable_prediction = False
        decoded: dict[str, torch.Tensor] | None = None
        final_similarities: torch.Tensor | None = None

        for iteration in range(1, cell.config.max_iterations + 1):
            current_estimates = torchhd.resonator(prepared_trial.observation, current_estimates, candidate_domains)
            final_similarities = cosine_similarity_matrix(current_estimates, candidate_domains)
            decoded = decode_top_candidates(final_similarities)
            predicted_local_indices = decoded["top1_indices"]
            predicted_full_indices = candidate_indices_device.gather(
                1, predicted_local_indices.unsqueeze(-1)
            ).squeeze(-1)
            if previous_indices is not None and torch.equal(predicted_full_indices, previous_indices):
                stable_iterations += 1
            else:
                stable_iterations = 1
            previous_indices = predicted_full_indices.clone()
            if stable_iterations >= cell.config.stable_patience:
                stable_prediction = True
                break

        if decoded is None or final_similarities is None:
            raise RuntimeError("MAP factorization produced no decode output.")

        predicted_indices = candidate_indices_device.gather(
            1, decoded["top1_indices"].unsqueeze(-1)
        ).squeeze(-1)
        return {
            "predicted_indices": predicted_indices.detach().cpu(),
            "iterations": iteration,
            "stable_prediction": stable_prediction,
            "decoded": decoded,
            "estimates": current_estimates.detach(),
            "similarities": final_similarities.detach(),
        }

    run_result, factorization_time, peak_cuda_memory, peak_cpu = measure_decode_timing(
        run_once,
        device=device,
        warmup_repeats=timing_warmup,
        measure_repeats=timing_repeats,
    )
    predicted_indices = run_result["predicted_indices"]
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted_indices, bundle.target_indices.cpu())
    truth_included = candidate_indices.eq(bundle.target_indices.unsqueeze(-1)).any(dim=-1)

    return TrialRecord(
        schema_version=LEVEL1F3_SCHEMA_VERSION,
        method_version=LEVEL1F3_METHOD_VERSION,
        upstream_commit_sha="",
        seed_split="",
        cell_id=cell.label,
        operating_point_label=cell.operating_point_label,
        substrate=SUBSTRATE_MAP,
        method_id=method_id,
        subset_size_label=method_subset_size_label(method_id),
        task_seed=bundle.task.task_seed,
        context_accuracy=cell.context_accuracy,
        anomaly_rate=cell.anomaly_rate,
        factor_count=cell.config.num_factors,
        domain_size=cell.config.domain_size,
        representation_dimension=cell.config.dimensions,
        target_indices=bundle.task.target_indices,
        active_l1=bundle.task.active_l1 or "",
        active_l2=bundle.task.active_l2 or "",
        predicted_l2=bundle.predicted_l2,
        context_prediction_correct=bundle.context_prediction_correct,
        candidate_subset_indices=[row.tolist() for row in candidate_indices],
        candidate_count=int(candidate_indices.size(1)),
        truth_included_per_factor=truth_included.tolist(),
        all_truth_included=bool(truth_included.all().item()),
        predicted_indices=[int(value) for value in predicted_indices.tolist()],
        outcome=outcome,
        exact_recovery=exact_recovery,
        per_factor_recovery=[bool(value) for value in per_factor_recovery],
        iterations=int(run_result["iterations"]),
        materialization_time_sec=materialization_time,
        factorization_time_sec=factorization_time,
        end_to_end_task_time_sec=materialization_time + factorization_time,
        native_codebook_bytes=tensor_bytes(domains),
        native_observation_bytes=tensor_bytes(prepared_trial.observation),
        runtime_state_bytes=map_runtime_state_bytes(
            run_result["estimates"], run_result["similarities"]
        ),
        peak_cuda_memory_bytes=peak_cuda_memory,
        peak_cpu_memory_bytes=peak_cpu,
        device=device,
        same_device_timing_status="pending",
        uses_upstream_resonator=True,
        uses_official_bcf_class=False,
        official_bcf_class_path=None,
        bcf_config_id=None,
        max_iterations_cap=cell.config.max_iterations,
        no_query_aware_mixture_input=True,
    )


def load_official_bcf_class(repo_path: Path):
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    module = importlib.import_module("models.blockcodefactorizer")
    return getattr(module, "blockcodefactorizer")


def official_bcf_max_iterations(task: AbstractFactorizationTask, configured_cap: int | None = None) -> int:
    default_cap = max(1, int((task.domain_size_per_factor[0] ** (task.factor_count - 1)) / task.factor_count))
    if configured_cap is None:
        return default_cap
    return min(default_cap, max(1, configured_cap))


def prepare_bcf_trial(
    bundle: TaskBundle,
    config: BCFConfigCandidate,
    *,
    repo_path: Path,
    prefer_cuda: bool,
) -> PreparedBCFTrial:
    official_class = load_official_bcf_class(repo_path)
    use_cuda = prefer_cuda and torch.cuda.is_available()
    target_batch = torch.tensor([bundle.task.target_indices], dtype=torch.long)
    max_iterations_cap = official_bcf_max_iterations(bundle.task, config.iteration_cap)

    materialization_start = time.perf_counter()
    with redirect_stdout(io.StringIO()):
        model = official_class(
            D=config.dimension,
            F=bundle.task.factor_count,
            Mx=bundle.task.domain_size_per_factor[0],
            B=config.blocks,
            similarity=config.similarity,
            convergenceDetectionThreshold=config.convergence_detection_threshold,
            A=config.a_value,
            threshold=config.threshold,
            decoding=config.decoding,
            permutation=config.permutation,
            topaPU=config.topa_pu,
            useCuda=use_cuda,
            seed=bundle.task.task_seed + BCF_CODEBOOK_SEED_OFFSET,
            id=config.config_id,
        )
    target_device = target_batch.to(model._device)
    observation = model.encode(target_device)
    shared_materialization_time = time.perf_counter() - materialization_start
    return PreparedBCFTrial(
        model=model,
        observation=observation,
        full_im_cpu=model._IM.detach().cpu(),
        shared_materialization_time_sec=shared_materialization_time,
        max_iterations_cap=max_iterations_cap,
        use_cuda=use_cuda,
    )


def build_bcf_config_candidates() -> list[BCFConfigCandidate]:
    return [
        BCFConfigCandidate(
            config_id="official_hp_d256_b4_m10",
            dimension=256,
            blocks=4,
            a_value=40,
            threshold=0.0031,
            source_path="experiments/200a_bcf/hyperparameters/hyperparams_D_256_F_3_B_4.json",
            source_key="10",
            source_note="Official F=3, B=4, D=256 hyperparameter table at codebook size 10. Reused as the nearest official single-product prior for M=5 and M=10.",
        ),
        BCFConfigCandidate(
            config_id="official_hp_d512_b4_m10",
            dimension=512,
            blocks=4,
            a_value=46,
            threshold=0.0094,
            source_path="experiments/200a_bcf/hyperparameters/hyperparams_D_512_F_3_B_4.json",
            source_key="10",
            source_note="Official F=3, B=4, D=512 hyperparameter table at codebook size 10. Reused as the nearest official single-product prior for M=5 and M=10.",
        ),
        BCFConfigCandidate(
            config_id="official_hp_d1024_b4_m10",
            dimension=1024,
            blocks=4,
            a_value=40,
            threshold=0.0065,
            source_path="experiments/200a_bcf/hyperparameters/hyperparams_D_1024_F_3_B_4.json",
            source_key="10",
            source_note="Official F=3, B=4, D=1024 hyperparameter table at codebook size 10. Reused as the nearest official single-product prior for M=5 and M=10.",
        ),
    ]


def choose_bcf_iteration_cap(
    repo_path: Path,
    same_device_timing_status: str,
    *,
    prefer_cuda: bool,
) -> tuple[int, dict[str, Any]]:
    reference_candidate = build_bcf_config_candidates()[1]
    cap_rows: list[dict[str, Any]] = []
    upstream_sha = upstream_commit_sha(repo_path)
    spec = level1f3_config_seed_ranges()[PRIMARY_CELL.label]

    for cap in BCF_ITERATION_CAP_CANDIDATES:
        print(f"[level1f3] cap sweep cap={cap}", flush=True)
        capped_candidate = replace(reference_candidate, iteration_cap=cap)
        cap_trials: list[TrialRecord] = []
        for seed in range(spec["start"], spec["start"] + LEVEL1F3_CAP_SELECTION_TRIALS):
            bundle = build_single_product_task(PRIMARY_CELL, seed)
            subset = select_shared_candidate_subset(bundle, METHOD_GLOBAL)
            trial = evaluate_bcf_trial(
                bundle,
                PRIMARY_CELL,
                METHOD_GLOBAL,
                subset,
                config=capped_candidate,
                repo_path=repo_path,
                prefer_cuda=prefer_cuda,
            )
            trial = set_trial_metadata(
                trial,
                seed_split="cap_selection",
                upstream_sha=upstream_sha,
                same_device_timing_status=same_device_timing_status,
            )
            cap_trials.append(trial)
        cap_rows.append(
            {
                "iteration_cap": cap,
                "exact_recovery_rate": sum(trial.exact_recovery for trial in cap_trials) / len(cap_trials),
                "mean_iterations": sum(trial.iterations for trial in cap_trials) / len(cap_trials),
                "mean_factorization_time_sec": (
                    sum(trial.factorization_time_sec for trial in cap_trials) / len(cap_trials)
                ),
                "selection_trials": LEVEL1F3_CAP_SELECTION_TRIALS,
                "reference_config_id": reference_candidate.config_id,
            }
        )

    chosen_row = max(
        cap_rows,
        key=lambda row: (
            row["exact_recovery_rate"],
            -row["mean_iterations"],
            -row["mean_factorization_time_sec"],
        ),
    )
    payload = {
        "reference_config_id": reference_candidate.config_id,
        "selection_cell": PRIMARY_CELL.label,
        "selection_trials": LEVEL1F3_CAP_SELECTION_TRIALS,
        "candidates": cap_rows,
        "selected_iteration_cap": chosen_row["iteration_cap"],
        "selection_objective": "max exact_recovery, then min iterations, then min factorization time",
    }
    return int(chosen_row["iteration_cap"]), payload


def bcf_model_codebook_bytes(model) -> int:
    return tensor_bytes(model._IM) + tensor_bytes(model._matIM)


def bcf_runtime_state_bytes(model) -> int:
    return tensor_bytes(model._init_guess)


def slice_bcf_codebook(im_tensor: torch.Tensor, candidate_indices: torch.Tensor) -> torch.Tensor:
    rows = []
    for factor_index in range(candidate_indices.size(0)):
        rows.append(im_tensor[factor_index].index_select(0, candidate_indices[factor_index].cpu()))
    return torch.stack(rows, dim=0)


def evaluate_bcf_trial(
    bundle: TaskBundle,
    cell: ShootoutCell,
    method_id: str,
    candidate_indices: torch.Tensor,
    *,
    config: BCFConfigCandidate,
    repo_path: Path,
    prefer_cuda: bool,
    prepared: PreparedBCFTrial | None = None,
    timing_repeats: int = 1,
    timing_warmup: int = 0,
) -> TrialRecord:
    if bundle.task.distractor_target_indices:
        raise ValueError("Level 1F.3 BCF evaluation only supports single-product tasks.")

    prepared_trial = prepared or prepare_bcf_trial(
        bundle,
        config,
        repo_path=repo_path,
        prefer_cuda=prefer_cuda,
    )
    official_class = load_official_bcf_class(repo_path)
    candidate_count = int(candidate_indices.size(1))
    materialization_time = prepared_trial.shared_materialization_time_sec
    if method_id == METHOD_GLOBAL:
        active_model = prepared_trial.model
    else:
        subset_materialization_start = time.perf_counter()
        subset_im = slice_bcf_codebook(prepared_trial.full_im_cpu, candidate_indices)
        with redirect_stdout(io.StringIO()):
            active_model = official_class(
                D=config.dimension,
                F=bundle.task.factor_count,
                Mx=candidate_count,
                B=config.blocks,
                similarity=config.similarity,
                convergenceDetectionThreshold=config.convergence_detection_threshold,
                A=config.a_value,
                threshold=config.threshold,
                decoding=config.decoding,
                IM=subset_im,
                permutation=config.permutation,
                topaPU=config.topa_pu,
                useCuda=prepared_trial.use_cuda,
                seed=bundle.task.task_seed + BCF_CODEBOOK_SEED_OFFSET,
                id=config.config_id,
            )
        materialization_time += time.perf_counter() - subset_materialization_start

    def run_once() -> dict[str, Any]:
        prediction_local = active_model.decode(
            prepared_trial.observation,
            prepared_trial.max_iterations_cap,
        ).detach().cpu()
        if method_id == METHOD_GLOBAL:
            prediction_full = prediction_local
        else:
            prediction_full = torch.stack(
                [
                    candidate_indices[factor_index].index_select(0, prediction_local[0, factor_index].view(1)).squeeze(0)
                    for factor_index in range(candidate_indices.size(0))
                ],
                dim=0,
            ).view(1, -1)
        return {
            "predicted_indices": prediction_full.squeeze(0).to(dtype=torch.long),
            "iterations": int(active_model._get_number_iter().max().item()),
        }

    run_result, factorization_time, peak_cuda_memory, peak_cpu = measure_decode_timing(
        run_once,
        device=active_model._device,
        warmup_repeats=timing_warmup,
        measure_repeats=timing_repeats,
    )
    predicted_indices = run_result["predicted_indices"]
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted_indices, bundle.target_indices.cpu())
    truth_included = candidate_indices.eq(bundle.target_indices.unsqueeze(-1)).any(dim=-1)

    return TrialRecord(
        schema_version=LEVEL1F3_SCHEMA_VERSION,
        method_version=LEVEL1F3_METHOD_VERSION,
        upstream_commit_sha=upstream_commit_sha(repo_path),
        seed_split="",
        cell_id=cell.label,
        operating_point_label=cell.operating_point_label,
        substrate=SUBSTRATE_BCF,
        method_id=method_id,
        subset_size_label=method_subset_size_label(method_id),
        task_seed=bundle.task.task_seed,
        context_accuracy=cell.context_accuracy,
        anomaly_rate=cell.anomaly_rate,
        factor_count=cell.config.num_factors,
        domain_size=cell.config.domain_size,
        representation_dimension=config.dimension,
        target_indices=bundle.task.target_indices,
        active_l1=bundle.task.active_l1 or "",
        active_l2=bundle.task.active_l2 or "",
        predicted_l2=bundle.predicted_l2,
        context_prediction_correct=bundle.context_prediction_correct,
        candidate_subset_indices=[row.tolist() for row in candidate_indices],
        candidate_count=candidate_count,
        truth_included_per_factor=truth_included.tolist(),
        all_truth_included=bool(truth_included.all().item()),
        predicted_indices=[int(value) for value in predicted_indices.tolist()],
        outcome=outcome,
        exact_recovery=exact_recovery,
        per_factor_recovery=[bool(value) for value in per_factor_recovery],
        iterations=int(run_result["iterations"]),
        materialization_time_sec=materialization_time,
        factorization_time_sec=factorization_time,
        end_to_end_task_time_sec=materialization_time + factorization_time,
        native_codebook_bytes=bcf_model_codebook_bytes(active_model),
        native_observation_bytes=tensor_bytes(prepared_trial.observation),
        runtime_state_bytes=bcf_runtime_state_bytes(active_model),
        peak_cuda_memory_bytes=peak_cuda_memory,
        peak_cpu_memory_bytes=peak_cpu,
        device=active_model._device,
        same_device_timing_status="pending",
        uses_upstream_resonator=False,
        uses_official_bcf_class=True,
        official_bcf_class_path=BCF_OFFICIAL_CLASS_PATH,
        bcf_config_id=config.config_id,
        max_iterations_cap=prepared_trial.max_iterations_cap,
        no_query_aware_mixture_input=True,
    )


def set_trial_metadata(
    record: TrialRecord,
    *,
    seed_split: str,
    upstream_sha: str,
    same_device_timing_status: str,
) -> TrialRecord:
    payload = record.to_dict()
    payload["seed_split"] = seed_split
    payload["upstream_commit_sha"] = upstream_sha
    payload["same_device_timing_status"] = same_device_timing_status
    return TrialRecord(**payload)


def summarize_trials(trials: list[TrialRecord]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[TrialRecord]] = {}
    for trial in trials:
        key = (trial.seed_split, trial.cell_id, trial.substrate, trial.method_id)
        grouped.setdefault(key, []).append(trial)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        total = len(batch)
        exact_count = sum(trial.outcome == OUTCOME_EXACT for trial in batch)
        partial_count = sum(trial.outcome == OUTCOME_PARTIAL for trial in batch)
        failure_count = sum(trial.outcome == OUTCOME_FAILURE for trial in batch)
        rows.append(
            {
                "schema_version": LEVEL1F3_SCHEMA_VERSION,
                "seed_split": first.seed_split,
                "cell_id": first.cell_id,
                "operating_point_label": first.operating_point_label,
                "substrate": first.substrate,
                "method_id": first.method_id,
                "subset_size_label": first.subset_size_label,
                "context_accuracy": first.context_accuracy,
                "anomaly_rate": first.anomaly_rate,
                "representation_dimension": first.representation_dimension,
                "trials": total,
                "exact_recovery_rate": exact_count / total,
                "partial_recovery_rate": partial_count / total,
                "failure_rate": failure_count / total,
                "per_factor_recovery_rate": sum(sum(trial.per_factor_recovery) for trial in batch) / (total * first.factor_count),
                "truth_inclusion_rate": sum(trial.all_truth_included for trial in batch) / total,
                "mean_iterations": sum(trial.iterations for trial in batch) / total,
                "mean_materialization_time_sec": sum(trial.materialization_time_sec for trial in batch) / total,
                "mean_factorization_time_sec": sum(trial.factorization_time_sec for trial in batch) / total,
                "mean_end_to_end_task_time_sec": sum(trial.end_to_end_task_time_sec for trial in batch) / total,
                "mean_native_codebook_bytes": sum(trial.native_codebook_bytes for trial in batch) / total,
                "mean_native_observation_bytes": sum(trial.native_observation_bytes for trial in batch) / total,
                "mean_runtime_state_bytes": sum((trial.runtime_state_bytes or 0) for trial in batch) / total,
                "mean_peak_cuda_memory_bytes": (
                    sum((trial.peak_cuda_memory_bytes or 0) for trial in batch) / total
                    if any(trial.peak_cuda_memory_bytes is not None for trial in batch)
                    else None
                ),
                "mean_peak_cpu_memory_bytes": (
                    sum((trial.peak_cpu_memory_bytes or 0) for trial in batch) / total
                    if any(trial.peak_cpu_memory_bytes is not None for trial in batch)
                    else None
                ),
                "same_device_timing_status": first.same_device_timing_status,
                "bcf_config_id": first.bcf_config_id,
                "upstream_commit_sha": first.upstream_commit_sha,
            }
        )
    return rows


def timing_summary_rows(trials: list[TrialRecord]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[TrialRecord]] = {}
    for trial in trials:
        key = (trial.cell_id, trial.substrate, trial.method_id)
        grouped.setdefault(key, []).append(trial)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        rows.append(
            {
                "schema_version": LEVEL1F3_SCHEMA_VERSION,
                "cell_id": first.cell_id,
                "substrate": first.substrate,
                "method_id": first.method_id,
                "timed_trials": len(batch),
                "median_materialization_time_sec": statistics.median(trial.materialization_time_sec for trial in batch),
                "median_factorization_time_sec": statistics.median(trial.factorization_time_sec for trial in batch),
                "median_end_to_end_task_time_sec": statistics.median(trial.end_to_end_task_time_sec for trial in batch),
                "same_device_timing_status": first.same_device_timing_status,
                "device": first.device,
            }
        )
    return rows


def memory_summary_rows(trials: list[TrialRecord]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[TrialRecord]] = {}
    for trial in trials:
        key = (trial.cell_id, trial.substrate, trial.method_id)
        grouped.setdefault(key, []).append(trial)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        rows.append(
            {
                "schema_version": LEVEL1F3_SCHEMA_VERSION,
                "cell_id": first.cell_id,
                "substrate": first.substrate,
                "method_id": first.method_id,
                "mean_native_codebook_bytes": sum(trial.native_codebook_bytes for trial in batch) / len(batch),
                "mean_native_observation_bytes": sum(trial.native_observation_bytes for trial in batch) / len(batch),
                "mean_runtime_state_bytes": sum((trial.runtime_state_bytes or 0) for trial in batch) / len(batch),
                "mean_peak_cuda_memory_bytes": (
                    sum((trial.peak_cuda_memory_bytes or 0) for trial in batch) / len(batch)
                    if any(trial.peak_cuda_memory_bytes is not None for trial in batch)
                    else None
                ),
                "mean_peak_cpu_memory_bytes": (
                    sum((trial.peak_cpu_memory_bytes or 0) for trial in batch) / len(batch)
                    if any(trial.peak_cpu_memory_bytes is not None for trial in batch)
                    else None
                ),
            }
        )
    return rows


def factorizer_comparison_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["cell_id"], row["substrate"], row["method_id"]): row
        for row in summary_rows
        if row["seed_split"] == "heldout"
    }
    rows = []
    for cell in ALL_CELLS:
        map_row = lookup[(cell.label, SUBSTRATE_MAP, METHOD_GLOBAL)]
        bcf_row = lookup[(cell.label, SUBSTRATE_BCF, METHOD_GLOBAL)]
        rows.append(
            {
                "schema_version": LEVEL1F3_SCHEMA_VERSION,
                "cell_id": cell.label,
                "map_exact_recovery_rate": map_row["exact_recovery_rate"],
                "bcf_exact_recovery_rate": bcf_row["exact_recovery_rate"],
                "bcf_minus_map_exact_recovery": bcf_row["exact_recovery_rate"] - map_row["exact_recovery_rate"],
                "map_mean_iterations": map_row["mean_iterations"],
                "bcf_mean_iterations": bcf_row["mean_iterations"],
                "map_mean_factorization_time_sec": map_row["mean_factorization_time_sec"],
                "bcf_mean_factorization_time_sec": bcf_row["mean_factorization_time_sec"],
                "map_mean_native_codebook_bytes": map_row["mean_native_codebook_bytes"],
                "bcf_mean_native_codebook_bytes": bcf_row["mean_native_codebook_bytes"],
                "same_device_timing_status": map_row["same_device_timing_status"],
            }
        )
    return rows


def context_transfer_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["cell_id"], row["substrate"], row["method_id"]): row
        for row in summary_rows
        if row["seed_split"] == "heldout"
    }
    rows = []
    method_pairs = (
        (METHOD_SEMANTIC_HALF, METHOD_RANDOM_HALF, METHOD_ORACLE_HALF),
        (METHOD_SEMANTIC_QUARTER, METHOD_RANDOM_QUARTER, METHOD_ORACLE_QUARTER),
    )
    for cell in ALL_CELLS:
        for substrate in (SUBSTRATE_MAP, SUBSTRATE_BCF):
            global_row = lookup[(cell.label, substrate, METHOD_GLOBAL)]
            for semantic_method, random_method, oracle_method in method_pairs:
                semantic_row = lookup[(cell.label, substrate, semantic_method)]
                random_row = lookup[(cell.label, substrate, random_method)]
                oracle_row = lookup[(cell.label, substrate, oracle_method)]
                rows.append(
                    {
                        "schema_version": LEVEL1F3_SCHEMA_VERSION,
                        "cell_id": cell.label,
                        "substrate": substrate,
                        "semantic_method": semantic_method,
                        "random_method": random_method,
                        "oracle_method": oracle_method,
                        "semantic_exact_recovery_rate": semantic_row["exact_recovery_rate"],
                        "random_exact_recovery_rate": random_row["exact_recovery_rate"],
                        "global_exact_recovery_rate": global_row["exact_recovery_rate"],
                        "oracle_exact_recovery_rate": oracle_row["exact_recovery_rate"],
                        "semantic_truth_inclusion_rate": semantic_row["truth_inclusion_rate"],
                        "random_truth_inclusion_rate": random_row["truth_inclusion_rate"],
                        "oracle_truth_inclusion_rate": oracle_row["truth_inclusion_rate"],
                        "semantic_minus_random_exact_recovery": semantic_row["exact_recovery_rate"] - random_row["exact_recovery_rate"],
                        "semantic_minus_random_truth_inclusion": semantic_row["truth_inclusion_rate"] - random_row["truth_inclusion_rate"],
                        "semantic_regret_vs_oracle": oracle_row["exact_recovery_rate"] - semantic_row["exact_recovery_rate"],
                        "semantic_vs_global_time_delta_sec": semantic_row["mean_factorization_time_sec"] - global_row["mean_factorization_time_sec"],
                    }
                )
    return rows


def paired_comparison_rows(context_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["cell_id"], row["substrate"], row["semantic_method"]): row
        for row in context_rows
    }
    rows = []
    for cell in ALL_CELLS:
        for semantic_method in (METHOD_SEMANTIC_HALF, METHOD_SEMANTIC_QUARTER):
            map_row = lookup[(cell.label, SUBSTRATE_MAP, semantic_method)]
            bcf_row = lookup[(cell.label, SUBSTRATE_BCF, semantic_method)]
            rows.append(
                {
                    "schema_version": LEVEL1F3_SCHEMA_VERSION,
                    "cell_id": cell.label,
                    "semantic_method": semantic_method,
                    "map_semantic_gain_over_random": map_row["semantic_minus_random_exact_recovery"],
                    "bcf_semantic_gain_over_random": bcf_row["semantic_minus_random_exact_recovery"],
                    "map_truth_inclusion_gain_over_random": map_row["semantic_minus_random_truth_inclusion"],
                    "bcf_truth_inclusion_gain_over_random": bcf_row["semantic_minus_random_truth_inclusion"],
                    "bcf_minus_map_semantic_gain": bcf_row["semantic_minus_random_exact_recovery"] - map_row["semantic_minus_random_exact_recovery"],
                }
            )
    return rows


def save_trials_jsonl(path: Path, trials: list[TrialRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for trial in trials:
            handle.write(json.dumps(trial.to_dict(), ensure_ascii=True) + "\n")


def save_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot save an empty CSV.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def current_repo_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def choose_bcf_config(
    repo_path: Path,
    same_device_timing_status: str,
    *,
    selected_iteration_cap: int,
    prefer_cuda: bool,
) -> tuple[BCFConfigCandidate, dict[str, Any]]:
    candidates = build_bcf_config_candidates()
    candidate_rows: list[dict[str, Any]] = []
    trials: list[TrialRecord] = []
    upstream_sha = upstream_commit_sha(repo_path)
    selection_cells = (PRIMARY_CELL,)

    for candidate in candidates:
        candidate = replace(candidate, iteration_cap=selected_iteration_cap)
        print(f"[level1f3] configuration sweep candidate={candidate.config_id}", flush=True)
        per_candidate_trials: list[TrialRecord] = []
        for cell in selection_cells:
            spec = level1f3_config_seed_ranges()[cell.label]
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                bundle = build_single_product_task(cell, seed)
                subset = select_shared_candidate_subset(bundle, METHOD_GLOBAL)
                trial = evaluate_bcf_trial(
                    bundle,
                    cell,
                    METHOD_GLOBAL,
                    subset,
                    config=candidate,
                    repo_path=repo_path,
                    prefer_cuda=prefer_cuda,
                )
                trial = set_trial_metadata(
                    trial,
                    seed_split="configuration",
                    upstream_sha=upstream_sha,
                    same_device_timing_status=same_device_timing_status,
                )
                per_candidate_trials.append(trial)
                trials.append(trial)
        exact_rate = sum(trial.exact_recovery for trial in per_candidate_trials) / len(per_candidate_trials)
        mean_iterations = sum(trial.iterations for trial in per_candidate_trials) / len(per_candidate_trials)
        mean_codebook_bytes = sum(trial.native_codebook_bytes for trial in per_candidate_trials) / len(per_candidate_trials)
        candidate_rows.append(
            {
                "config_id": candidate.config_id,
                "exact_recovery_rate": exact_rate,
                "mean_iterations": mean_iterations,
                "mean_native_codebook_bytes": mean_codebook_bytes,
                "dimension": candidate.dimension,
                "blocks": candidate.blocks,
                "A": candidate.a_value,
                "threshold": candidate.threshold,
                "source_path": candidate.source_path,
                "source_key": candidate.source_key,
                "source_note": candidate.source_note,
            }
        )

    chosen_row = max(
        candidate_rows,
        key=lambda row: (
            row["exact_recovery_rate"],
            -row["mean_iterations"],
            -row["mean_native_codebook_bytes"],
        ),
    )
    chosen = replace(
        next(candidate for candidate in candidates if candidate.config_id == chosen_row["config_id"]),
        iteration_cap=selected_iteration_cap,
    )
    payload = {
        "schema_version": LEVEL1F3_SCHEMA_VERSION,
        "method_version": LEVEL1F3_METHOD_VERSION,
        "upstream_commit_sha": upstream_sha,
        "selection_split": {cell.label: level1f3_config_seed_ranges()[cell.label] for cell in selection_cells},
        "selection_cells": [cell.label for cell in selection_cells],
        "selection_objective": "max exact_recovery, then min iterations, then min memory",
        "same_device_timing_status": same_device_timing_status,
        "selected_iteration_cap": selected_iteration_cap,
        "protocol_amendment": LEVEL1F3_PROTOCOL_AMENDMENT,
        "candidates": candidate_rows,
        "selected_config": chosen.to_dict(),
        "selection_locked_before_heldout": True,
        "limitations": [
            "Official BCF hyperparameter tables do not cover M=5 or F=4 directly.",
            "The frozen candidates reuse official single-product priors from nearby published tables rather than inventing custom equations or kernels.",
            "Configuration selection is intentionally scoped to the primary single-product cell to keep the pre-heldout search narrow.",
        ],
    }
    return chosen, payload


def run_trials_for_split(
    seed_split: str,
    seed_ranges: dict[str, dict[str, int]],
    *,
    cells: tuple[ShootoutCell, ...] = ALL_CELLS,
    methods: tuple[str, ...] = ALL_METHODS,
    bcf_config: BCFConfigCandidate,
    repo_path: Path,
    prefer_cuda: bool,
    same_device_timing_status: str,
) -> list[TrialRecord]:
    trials: list[TrialRecord] = []
    upstream_sha = upstream_commit_sha(repo_path)
    map_device = map_device_for_runtime(prefer_cuda=prefer_cuda)

    for cell in cells:
        spec = seed_ranges[cell.label]
        print(
            f"[level1f3] split={seed_split} cell={cell.label} trials={spec['count']} methods={len(methods)}",
            flush=True,
        )
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            bundle = build_single_product_task(cell, seed)
            prepared_map = prepare_map_trial(bundle, cell, device=map_device)
            prepared_bcf = prepare_bcf_trial(
                bundle,
                bcf_config,
                repo_path=repo_path,
                prefer_cuda=prefer_cuda,
            )
            for method_id in methods:
                subset = select_shared_candidate_subset(bundle, method_id)
                map_trial = evaluate_map_trial(
                    bundle,
                    cell,
                    method_id,
                    subset,
                    device=map_device,
                    prepared=prepared_map,
                )
                map_trial = set_trial_metadata(
                    map_trial,
                    seed_split=seed_split,
                    upstream_sha=upstream_sha,
                    same_device_timing_status=same_device_timing_status,
                )
                bcf_trial = evaluate_bcf_trial(
                    bundle,
                    cell,
                    method_id,
                    subset,
                    config=bcf_config,
                    repo_path=repo_path,
                    prefer_cuda=prefer_cuda,
                    prepared=prepared_bcf,
                )
                bcf_trial = set_trial_metadata(
                    bcf_trial,
                    seed_split=seed_split,
                    upstream_sha=upstream_sha,
                    same_device_timing_status=same_device_timing_status,
                )
                trials.extend((map_trial, bcf_trial))

    return trials


def timed_subset_sample(trials: list[TrialRecord]) -> dict[str, set[int]]:
    sample: dict[str, set[int]] = {}
    for cell in ALL_CELLS:
        seeds = [
            trial.task_seed
            for trial in trials
            if trial.seed_split == "heldout" and trial.cell_id == cell.label and trial.substrate == SUBSTRATE_MAP and trial.method_id == METHOD_GLOBAL
        ]
        sample[cell.label] = set(sorted(seeds)[:TIMING_SAMPLE_TRIALS_PER_CELL])
    return sample


def rerun_timing_sample(
    heldout_trials: list[TrialRecord],
    *,
    cells: tuple[ShootoutCell, ...] = ALL_CELLS,
    bcf_config: BCFConfigCandidate,
    repo_path: Path,
    prefer_cuda: bool,
    same_device_timing_status: str,
) -> list[TrialRecord]:
    sampled_seeds = timed_subset_sample(heldout_trials)
    timed_trials: list[TrialRecord] = []
    upstream_sha = upstream_commit_sha(repo_path)
    map_device = map_device_for_runtime(prefer_cuda=prefer_cuda)

    for cell in cells:
        print(
            f"[level1f3] timing sample cell={cell.label} trials={len(sampled_seeds[cell.label])} methods={len(ALL_METHODS)} repeats={TIMING_MEASURE_REPEATS}",
            flush=True,
        )
        for seed in sorted(sampled_seeds[cell.label]):
            bundle = build_single_product_task(cell, seed)
            prepared_map = prepare_map_trial(bundle, cell, device=map_device)
            prepared_bcf = prepare_bcf_trial(
                bundle,
                bcf_config,
                repo_path=repo_path,
                prefer_cuda=prefer_cuda,
            )
            for method_id in ALL_METHODS:
                subset = select_shared_candidate_subset(bundle, method_id)
                map_trial = evaluate_map_trial(
                    bundle,
                    cell,
                    method_id,
                    subset,
                    device=map_device,
                    prepared=prepared_map,
                    timing_repeats=TIMING_MEASURE_REPEATS,
                    timing_warmup=TIMING_WARMUP_REPEATS,
                )
                map_trial = set_trial_metadata(
                    map_trial,
                    seed_split="timing",
                    upstream_sha=upstream_sha,
                    same_device_timing_status=same_device_timing_status,
                )
                bcf_trial = evaluate_bcf_trial(
                    bundle,
                    cell,
                    method_id,
                    subset,
                    config=bcf_config,
                    repo_path=repo_path,
                    prefer_cuda=prefer_cuda,
                    prepared=prepared_bcf,
                    timing_repeats=TIMING_MEASURE_REPEATS,
                    timing_warmup=TIMING_WARMUP_REPEATS,
                )
                bcf_trial = set_trial_metadata(
                    bcf_trial,
                    seed_split="timing",
                    upstream_sha=upstream_sha,
                    same_device_timing_status=same_device_timing_status,
                )
                timed_trials.extend((map_trial, bcf_trial))
    return timed_trials


def detect_same_device_timing_status(map_cuda_available: bool) -> str:
    return "same_wsl_gpu" if map_cuda_available and torch.cuda.is_available() else "no_same_device_gpu"


def pareto_analysis(
    factorizer_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    primary_factorizer = next(row for row in factorizer_rows if row["cell_id"] == PRIMARY_CELL.label)
    primary_bcf_context = [
        row for row in context_rows
        if row["cell_id"] == PRIMARY_CELL.label and row["substrate"] == SUBSTRATE_BCF
    ]
    bcf_context_helped = any(
        row["semantic_minus_random_exact_recovery"] > 0.0 or row["semantic_minus_random_truth_inclusion"] > 0.0
        for row in primary_bcf_context
    )
    if primary_factorizer["bcf_minus_map_exact_recovery"] > 0.0 and bcf_context_helped:
        decision = "PIVOT_SUBSTRATE"
    elif bcf_context_helped:
        decision = "COMPOSE"
    else:
        decision = "MAP_REMAINS_PARETO"
    return {
        "schema_version": LEVEL1F3_SCHEMA_VERSION,
        "decision": decision,
        "primary_global_comparison": primary_factorizer,
        "primary_bcf_context_helped": bcf_context_helped,
    }


def historical_level1e_reference() -> dict[str, Any]:
    summary_path = Path(__file__).resolve().parents[2] / "results" / "level1e" / "summary.csv"
    rows: dict[str, Any] = {}
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["policy_id"] == "adaptive_calibrated_policy" and row["cell_id"] in {PRIMARY_CELL.label, STRESS_CELL.label, EASY_CELL.label}:
                rows[row["cell_id"]] = row
    return rows


def run_level1f3(output_dir: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    repo_path = upstream_clone_path()
    root = Path(__file__).resolve().parents[2]
    if not upstream_tracked_source_clean(repo_path):
        raise RuntimeError("Official IBM upstream checkout must remain unchanged during Level 1F.3.")

    same_device_timing_status = detect_same_device_timing_status(map_cuda_available=torch.cuda.is_available())
    print(f"[level1f3] same_device_timing_status={same_device_timing_status}", flush=True)
    selected_iteration_cap, cap_payload = choose_bcf_iteration_cap(
        repo_path,
        same_device_timing_status,
        prefer_cuda=prefer_cuda,
    )
    print(f"[level1f3] selected_iteration_cap={selected_iteration_cap}", flush=True)
    selected_bcf_config, selected_payload = choose_bcf_config(
        repo_path,
        same_device_timing_status,
        selected_iteration_cap=selected_iteration_cap,
        prefer_cuda=prefer_cuda,
    )
    print(f"[level1f3] selected_bcf_config={selected_payload['selected_config']['config_id']}", flush=True)
    development_trials = run_trials_for_split(
        "development",
        level1f3_development_seed_ranges(),
        methods=DEVELOPMENT_METHODS,
        bcf_config=selected_bcf_config,
        repo_path=repo_path,
        prefer_cuda=prefer_cuda,
        same_device_timing_status=same_device_timing_status,
    )
    heldout_trials = run_trials_for_split(
        "heldout",
        level1f3_heldout_seed_ranges(),
        bcf_config=selected_bcf_config,
        repo_path=repo_path,
        prefer_cuda=prefer_cuda,
        same_device_timing_status=same_device_timing_status,
    )
    timing_trials = rerun_timing_sample(
        heldout_trials,
        bcf_config=selected_bcf_config,
        repo_path=repo_path,
        prefer_cuda=prefer_cuda,
        same_device_timing_status=same_device_timing_status,
    )

    all_trials = development_trials + heldout_trials
    summary_rows = summarize_trials(all_trials)
    factorizer_rows = factorizer_comparison_rows(summary_rows)
    context_rows = context_transfer_rows(summary_rows)
    paired_rows = paired_comparison_rows(context_rows)
    timing_rows = timing_summary_rows(timing_trials)
    memory_rows = memory_summary_rows(heldout_trials)
    pareto = pareto_analysis(factorizer_rows, context_rows)

    save_json(output_dir / "selected_bcf_config.json", selected_payload)
    save_trials_jsonl(output_dir / "heldout_trials.jsonl", heldout_trials)
    save_summary_csv(output_dir / "summary.csv", summary_rows)
    save_summary_csv(output_dir / "factorizer_comparison.csv", factorizer_rows)
    save_summary_csv(output_dir / "context_transfer.csv", context_rows)
    save_summary_csv(output_dir / "timing_summary.csv", timing_rows)
    save_summary_csv(output_dir / "memory_summary.csv", memory_rows)
    save_summary_csv(output_dir / "paired_comparisons.csv", paired_rows)
    save_json(output_dir / "pareto_analysis.json", pareto)
    save_json(
        output_dir / "analysis.json",
        {
            "schema_version": LEVEL1F3_SCHEMA_VERSION,
            "method_version": LEVEL1F3_METHOD_VERSION,
            "checkpoint_commit": current_repo_head(root),
            "upstream_commit_sha": upstream_commit_sha(repo_path),
            "seed_ranges": {
                "configuration": level1f3_config_seed_ranges(),
                "development": level1f3_development_seed_ranges(),
                "heldout": level1f3_heldout_seed_ranges(),
            },
            "protocol_amendment": LEVEL1F3_PROTOCOL_AMENDMENT,
            "same_device_timing_status": same_device_timing_status,
            "selected_iteration_cap": selected_iteration_cap,
            "iteration_cap_selection": cap_payload,
            "selected_bcf_config": selected_payload["selected_config"],
            "historical_level1e_reference": historical_level1e_reference(),
            "pareto_analysis": pareto,
        },
    )
    return {
        "summary_rows": summary_rows,
        "factorizer_rows": factorizer_rows,
        "context_rows": context_rows,
        "timing_rows": timing_rows,
        "memory_rows": memory_rows,
        "paired_rows": paired_rows,
        "pareto": pareto,
        "iteration_cap_selection": cap_payload,
        "selected_bcf_config": selected_payload,
    }
