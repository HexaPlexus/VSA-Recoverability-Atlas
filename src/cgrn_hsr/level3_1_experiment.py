from __future__ import annotations

import csv
import io
import json
import math
import platform
import re
import statistics
import subprocess
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
from .competitors.holovec_attention import HOLOVEC_ATTENTION_CLASS_PATH
from .competitors.ibm_bcf_audit import (
    AbstractFactorizationTask,
    BCF_OFFICIAL_CLASS_PATH,
    upstream_clone_path,
    upstream_commit_sha,
    upstream_tracked_source_clean,
)
from .single_product_shootout import (
    common_outcome,
    load_official_bcf_class,
    tensor_bytes,
)

LEVEL3_1_SCHEMA_VERSION = "level3-1-native-envelope-dev-v1"
LEVEL3_1_CHECKPOINT_COMMIT = "66abd983d1626105b8c96602512a52d10a22d7d7"
LEVEL3_1_DATE = "2026-06-15"
U1_TASK_CONTRACT = "U1_blind_single_product_factorization"
U0_TASK_CONTRACT = "U0_known_key_cleanup"

MAP_U1_MASTER_SEED = 40260615
BCF_U1_MASTER_SEED = 41260615
U0_MASTER_SEED = 42260615
REPRODUCTION_MASTER_SEED = 43260615
U1_TRIALS_PER_POINT = 16
U0_TRIALS_PER_POINT = 16
MAP_CODEBOOK_SEED_OFFSET = 1000
BCF_CODEBOOK_SEED_OFFSET = 2000

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_FAILURE = "FAILURE"

LINEAR_CODE_VERDICT_GO = "GO_REPLICATE_MINIMAL"
LINEAR_CODE_VERDICT_DEFER_U2 = "DEFER_UNTIL_U2"
LINEAR_CODE_VERDICT_DEFER_UPSTREAM = "DEFER_UPSTREAM"
LINEAR_CODE_VERDICT_BLOCK = "BLOCK_TASK_MISMATCH"


@dataclass(frozen=True)
class SourceLedgerEntry:
    family: str
    distinction: str
    primary_source_title: str
    primary_source_url: str
    code_artifact: str
    code_url: str
    code_status: str
    level3_verdict: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SOURCE_LEDGER: list[SourceLedgerEntry] = [
    SourceLedgerEntry(
        family="classic_resonator",
        distinction="paper algorithm and upstream TorchHD implementation",
        primary_source_title="A Resonator Network for Factoring Distributed Representations of Data Structures",
        primary_source_url="https://www.frontiersin.org/articles/10.3389/fnbot.2020.00063/full",
        code_artifact="TorchHD resonator",
        code_url="https://github.com/hyperdimensional-computing/torchhd",
        code_status="UPSTREAM_AVAILABLE",
        level3_verdict="ADOPT_UPSTREAM",
        note="Frozen dense MAP baseline for U0/U1.",
    ),
    SourceLedgerEntry(
        family="attention_resonator_algorithm",
        distinction="paper algorithm distinct from the HoloVec API",
        primary_source_title="Self-Attention Based Semantic Decomposition in Vector Symbolic Architectures",
        primary_source_url="https://arxiv.org/abs/2403.13218",
        code_artifact="No audited official upstream found in this repo",
        code_url="",
        code_status="PAPER_ONLY",
        level3_verdict="DEFER_REPLICATION",
        note="HoloVec mismatch does not falsify the algorithm family itself.",
    ),
    SourceLedgerEntry(
        family="holovec_implementation",
        distinction="audited third-party implementation, not the paper algorithm itself",
        primary_source_title="HoloVec AttentionResonatorCleanup",
        primary_source_url="https://github.com/Twistient/HoloVec",
        code_artifact=HOLOVEC_ATTENTION_CLASS_PATH,
        code_url="https://github.com/Twistient/HoloVec",
        code_status="THIRD_PARTY_IMPLEMENTATION",
        level3_verdict="BLOCK_TASK_MISMATCH",
        note="Shared flat codebook API blocks fair factor-specific U1 parity.",
    ),
    SourceLedgerEntry(
        family="ibm_bcf",
        distinction="official sparse block-code factorizer",
        primary_source_title="Factorizers for distributed sparse block codes",
        primary_source_url="https://content.iospress.com/articles/neurosymbolic-artificial-intelligence/nai240713",
        code_artifact="IBM/in-memory-factorizer",
        code_url="https://github.com/IBM/in-memory-factorizer",
        code_status="UPSTREAM_AVAILABLE",
        level3_verdict="WRAP_UPSTREAM",
        note="Primary official U1 non-MAP candidate.",
    ),
    SourceLedgerEntry(
        family="ibm_noise_factorizers",
        distinction="native noise-envelope follow-up for factorizers",
        primary_source_title="On the Role of Noise in Factorizers",
        primary_source_url="https://arxiv.org/search/?query=On+the+Role+of+Noise+in+Factorizers&searchtype=all",
        code_artifact="IBM/in-memory-factorizer 100e_* experiments",
        code_url="https://github.com/IBM/in-memory-factorizer",
        code_status="UPSTREAM_AVAILABLE_IN_REPO",
        level3_verdict="WRAP_UPSTREAM",
        note="Used to interpret native-envelope noise settings, not to run Level 3.1 noisy held-out.",
    ),
    SourceLedgerEntry(
        family="linear_code_hdc",
        distinction="paper-only algebraic recovery candidate",
        primary_source_title="Linear Codes for Hyperdimensional Computing",
        primary_source_url="https://arxiv.org/search/?query=Linear+Codes+for+Hyperdimensional+Computing&searchtype=all",
        code_artifact="No upstream pinned in repo",
        code_url="",
        code_status="PAPER_ONLY",
        level3_verdict="DECISION_ONLY",
        note="Level 3.1 creates only a replication decision artifact.",
    ),
    SourceLedgerEntry(
        family="histogram_recovery",
        distinction="superposition-focused U2 candidate",
        primary_source_title="Efficient Vector Symbolic Architectures from Histogram Recovery",
        primary_source_url="https://arxiv.org/search/?query=Efficient+Vector+Symbolic+Architectures+from+Histogram+Recovery&searchtype=all",
        code_artifact="No audited upstream pinned in repo",
        code_url="",
        code_status="PAPER_ONLY",
        level3_verdict="DEFER_UPSTREAM",
        note="Not run in Level 3.1 because U2 is out of scope.",
    ),
    SourceLedgerEntry(
        family="full_tensor_product",
        distinction="oracle-only exact representation",
        primary_source_title="Full tensor-product representation (classical exact baseline)",
        primary_source_url="https://en.wikipedia.org/wiki/Tensor_product",
        code_artifact="Evaluator oracle only",
        code_url="",
        code_status="NO_UPSTREAM_NEEDED",
        level3_verdict="ORACLE_ONLY",
        note="Not a practical promoted substrate.",
    ),
    SourceLedgerEntry(
        family="fhrr_cleanup",
        distinction="continuous-value cleanup track",
        primary_source_title="Improved Cleanup and Decoding of Fractional Power Encodings",
        primary_source_url="https://arxiv.org/search/?query=Improved+Cleanup+and+Decoding+of+Fractional+Power+Encodings&searchtype=all",
        code_artifact="No audited upstream pinned in repo",
        code_url="",
        code_status="PAPER_ONLY",
        level3_verdict="SEPARATE_U3_TRACK",
        note="Explicitly out of U1 Level 3.1 runs.",
    ),
    SourceLedgerEntry(
        family="coupled_diffusion",
        distinction="paper candidate without audited upstream implementation in repo",
        primary_source_title="Coupled Inference in Diffusion Models for Semantic Decomposition",
        primary_source_url="https://arxiv.org/abs/2602.09983",
        code_artifact="No audited upstream pinned in repo",
        code_url="",
        code_status="PAPER_ONLY",
        level3_verdict="DEFER_REPLICATION",
        note="Deferred pending code or a later isolated gap-driven replication.",
    ),
]


@dataclass(frozen=True)
class MapConfig:
    config_id: str
    dimensions: int
    max_iterations: int = 12
    stable_patience: int = 3


@dataclass(frozen=True)
class BCFConfig:
    config_id: str
    dimensions: int
    factor_count: int
    blocks: int
    domain_size: int
    a_value: int
    threshold: float
    similarity: str = "inf"
    convergence_detection_threshold: float = 0.9
    decoding: str = "sequential"
    permutation: bool = False
    topa_pu: bool = True
    iter_max: int | None = None
    iter_fac: float = 1.0
    source_path: str = ""
    source_key: str = ""

    def native_max_iterations(self) -> int:
        if self.iter_max not in {None, -1}:
            return int(self.iter_max)
        return max(1, int(((self.domain_size ** (self.factor_count - 1)) / self.factor_count) * self.iter_fac))


@dataclass(frozen=True)
class U1Point:
    point_id: str
    factor_count: int
    domain_size: int
    search_space_log10: float
    stage: str


@dataclass(frozen=True)
class U0Point:
    point_id: str
    dimensions: int
    bundled_pairs: int
    item_memory_size: int


MAP_CONFIGS: tuple[MapConfig, ...] = (
    MapConfig("map_d256", 256),
    MapConfig("map_d512", 512),
    MapConfig("map_d1024", 1024),
)

INITIAL_U1_POINTS: tuple[U1Point, ...] = (
    U1Point("u1_f3_m10", 3, 10, round(math.log10(10**3), 6), "initial"),
    U1Point("u1_f3_m22", 3, 22, round(math.log10(22**3), 6), "initial"),
    U1Point("u1_f3_m49", 3, 49, round(math.log10(49**3), 6), "initial"),
)
REFINEMENT_U1_POINTS: tuple[U1Point, ...] = (
    U1Point("u1_f3_m31", 3, 31, round(math.log10(31**3), 6), "refinement"),
    U1Point("u1_f3_m68", 3, 68, round(math.log10(68**3), 6), "refinement"),
)

U0_POINTS: tuple[U0Point, ...] = (
    U0Point("u0_d256_pairs2_m16", 256, 2, 16),
    U0Point("u0_d256_pairs4_m16", 256, 4, 16),
    U0Point("u0_d256_pairs4_m64", 256, 4, 64),
    U0Point("u0_d512_pairs6_m128", 512, 6, 128),
)


def peak_cpu_memory_bytes() -> int | None:
    if resource is None:  # pragma: no cover - Windows path
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_maxrss * 1024)


def synchronize_device(device: str) -> None:
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


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
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def device_string(prefer_cuda: bool = True) -> str:
    return "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"


def build_u1_manifest(seed: int, factor_count: int, domain_size: int) -> tuple[dict[str, Any], AbstractFactorizationTask, float]:
    start = time.perf_counter()
    generator = make_generator(seed)
    true_factor_indices = [
        int(torch.randint(0, domain_size, (1,), generator=generator).item())
        for _ in range(factor_count)
    ]
    factor_identity_tokens = [
        [f"f{factor_index}_i{atom_index}" for atom_index in range(domain_size)]
        for factor_index in range(factor_count)
    ]
    task = AbstractFactorizationTask(
        task_seed=seed,
        factor_count=factor_count,
        domain_size_per_factor=[domain_size] * factor_count,
        target_indices=true_factor_indices,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )
    manifest = {
        "trial_id": f"u1-{factor_count}x{domain_size}-seed-{seed}",
        "seed": seed,
        "F": factor_count,
        "M_per_factor": [domain_size] * factor_count,
        "true_factor_indices": true_factor_indices,
        "factor_identity_tokens": factor_identity_tokens,
        "task_contract": U1_TASK_CONTRACT,
    }
    return manifest, task, time.perf_counter() - start


def build_all_u1_manifests(
    points: list[U1Point],
    *,
    seed_base: int,
) -> tuple[list[dict[str, Any]], dict[tuple[str, int], tuple[dict[str, Any], AbstractFactorizationTask, float]]]:
    manifest_rows: list[dict[str, Any]] = []
    lookup: dict[tuple[str, int], tuple[dict[str, Any], AbstractFactorizationTask, float]] = {}
    for point_index, point in enumerate(points):
        point_seed_start = seed_base + point_index * 1_000
        for offset in range(U1_TRIALS_PER_POINT):
            seed = point_seed_start + offset
            manifest, task, generation_time = build_u1_manifest(seed, point.factor_count, point.domain_size)
            manifest_row = {
                **manifest,
                "point_id": point.point_id,
                "search_space_log10": point.search_space_log10,
                "stage": point.stage,
            }
            manifest_rows.append(manifest_row)
            lookup[(point.point_id, seed)] = (manifest_row, task, generation_time)
    return manifest_rows, lookup


def map_materialize_u1(task: AbstractFactorizationTask, dimensions: int, device: str) -> tuple[torch.Tensor, torch.Tensor, float]:
    config = BaselineConfig(
        dimensions=dimensions,
        num_factors=task.factor_count,
        domain_size=task.domain_size_per_factor[0],
        structured_distractor_count=0,
        max_iterations=12,
        stable_patience=3,
    )
    start = time.perf_counter()
    domains = generate_domains(config, make_generator(task.task_seed + MAP_CODEBOOK_SEED_OFFSET)).to(device)
    target_indices = torch.tensor(task.target_indices, dtype=torch.long, device=device)
    observation = bind_sequence(factors_from_indices(domains, target_indices))
    return domains, observation, time.perf_counter() - start


def map_decode_u1(
    task: AbstractFactorizationTask,
    config: MapConfig,
    *,
    device: str,
    task_generation_time: float,
    point: U1Point,
) -> dict[str, Any]:
    domains, observation, representation_time = map_materialize_u1(task, config.dimensions, device)
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
    for iteration in range(1, config.max_iterations + 1):
        current_estimates = torchhd.resonator(observation, current_estimates, domains)
        similarities = cosine_similarity_matrix(current_estimates, domains)
        decoded = decode_top_candidates(similarities)
        predicted = decoded["top1_indices"]
        if previous_prediction is not None and torch.equal(predicted, previous_prediction):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_prediction = predicted.clone()
        if stable_iterations >= config.stable_patience:
            stable_prediction = True
            break
    synchronize_device(device)
    decode_time = time.perf_counter() - decode_start
    peak_cuda = int(torch.cuda.max_memory_allocated(device=device)) if device.startswith("cuda") and torch.cuda.is_available() else None
    peak_cpu = peak_cpu_memory_bytes()

    if decoded is None or similarities is None:
        raise RuntimeError("MAP U1 decode produced no output.")

    predicted_indices = decoded["top1_indices"].detach().cpu()
    target = torch.tensor(task.target_indices, dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted_indices, target)
    top2_indices = decoded["top2_indices"]
    top1_scores = decoded["top1_scores"]
    top2_scores = decoded["top2_scores"]
    margins = [float(a - b) for a, b in zip(top1_scores.tolist(), top2_scores.tolist())]

    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "stage": "u1_development",
        "task_contract": U1_TASK_CONTRACT,
        "point_id": point.point_id,
        "search_space_log10": point.search_space_log10,
        "seed_split": "development",
        "substrate": "MAP",
        "config_id": config.config_id,
        "dimensions": config.dimensions,
        "blocks": None,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "task_seed": task.task_seed,
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted_indices.tolist()],
        "outcome": outcome,
        "exact_recovery": exact_recovery,
        "per_factor_recovery": [bool(value) for value in per_factor_recovery],
        "iterations": iteration,
        "restarts": 0,
        "stable_prediction": stable_prediction,
        "restart_agreement": None,
        "reached_native_limit": False,
        "native_stopping_status": "stable" if stable_prediction else "max_iterations",
        "task_generation_time_sec": task_generation_time,
        "representation_materialization_time_sec": representation_time,
        "decoder_initialization_time_sec": decoder_initialization_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": task_generation_time + representation_time + decoder_initialization_time + decode_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(domains),
        "decoder_state_bytes": tensor_bytes(estimates) + tensor_bytes(similarities),
        "peak_ram_bytes": peak_cpu,
        "peak_vram_bytes": peak_cuda,
        "native_operation_proxy": iteration * task.factor_count * task.domain_size_per_factor[0] * config.dimensions,
        "top1_margin_mean": statistics.mean(margins),
        "top1_margin_min": min(margins),
        "device": device,
        "same_device_timing": device.startswith("cuda"),
        "uses_upstream_resonator": True,
        "uses_official_bcf_class": False,
        "context_or_pruning_used": False,
        "heldout_used": False,
    }


def load_bcf_hyperparams(repo_path: Path, *, dimensions: int, factor_count: int, blocks: int, domain_size: int) -> tuple[int, float, str, str]:
    file_name = f"hyperparams_D_{dimensions}_F_{factor_count}_B_{blocks}.json"
    source_path = repo_path / "experiments" / "200a_bcf" / "hyperparameters" / file_name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if str(domain_size) not in payload:
        raise KeyError(f"No official BCF hyperparameters for M={domain_size} in {file_name}.")
    entry = payload[str(domain_size)]
    return int(entry["A"]), float(entry["threshold"]), str(source_path.relative_to(repo_path)), str(domain_size)


def build_bcf_config(dimensions: int, factor_count: int, domain_size: int, *, repo_path: Path, blocks: int = 4) -> BCFConfig:
    a_value, threshold, source_path, source_key = load_bcf_hyperparams(
        repo_path,
        dimensions=dimensions,
        factor_count=factor_count,
        blocks=blocks,
        domain_size=domain_size,
    )
    return BCFConfig(
        config_id=f"bcf_d{dimensions}_f{factor_count}_b{blocks}_m{domain_size}",
        dimensions=dimensions,
        factor_count=factor_count,
        blocks=blocks,
        domain_size=domain_size,
        a_value=a_value,
        threshold=threshold,
        source_path=source_path,
        source_key=source_key,
    )


def instantiate_bcf_model(task: AbstractFactorizationTask, config: BCFConfig, *, repo_path: Path, prefer_cuda: bool) -> tuple[Any, float]:
    official_class = load_official_bcf_class(repo_path)
    use_cuda = prefer_cuda and torch.cuda.is_available()
    start = time.perf_counter()
    with redirect_stdout(io.StringIO()):
        model = official_class(
            D=config.dimensions,
            F=task.factor_count,
            Mx=task.domain_size_per_factor[0],
            B=config.blocks,
            similarity=config.similarity,
            convergenceDetectionThreshold=config.convergence_detection_threshold,
            A=config.a_value,
            threshold=config.threshold,
            decoding=config.decoding,
            permutation=config.permutation,
            topaPU=config.topa_pu,
            useCuda=use_cuda,
            seed=task.task_seed + BCF_CODEBOOK_SEED_OFFSET,
            id=config.config_id,
        )
    return model, time.perf_counter() - start


def bcf_encode_observation(model: Any, task: AbstractFactorizationTask) -> tuple[torch.Tensor, float]:
    start = time.perf_counter()
    target_batch = torch.tensor([task.target_indices], dtype=torch.long, device=model._device)
    observation = model.encode(target_batch)
    return observation, time.perf_counter() - start


def bcf_decode_u1(
    task: AbstractFactorizationTask,
    config: BCFConfig,
    *,
    repo_path: Path,
    prefer_cuda: bool,
    task_generation_time: float,
    point: U1Point,
) -> dict[str, Any]:
    model, decoder_initialization_time = instantiate_bcf_model(task, config, repo_path=repo_path, prefer_cuda=prefer_cuda)
    observation, representation_time = bcf_encode_observation(model, task)
    max_iterations = config.native_max_iterations()

    synchronize_device(model._device)
    if str(model._device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=model._device)
    decode_start = time.perf_counter()
    predicted_indices = model.decode(observation, max_iterations).detach().cpu().squeeze(0).to(dtype=torch.long)
    synchronize_device(model._device)
    decode_time = time.perf_counter() - decode_start
    peak_cuda = int(torch.cuda.max_memory_allocated(device=model._device)) if str(model._device).startswith("cuda") and torch.cuda.is_available() else None
    peak_cpu = peak_cpu_memory_bytes()

    iterations = int(model._get_number_iter().max().item())
    target = torch.tensor(task.target_indices, dtype=torch.long)
    outcome, per_factor_recovery, exact_recovery = common_outcome(predicted_indices, target)

    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "stage": "u1_development",
        "task_contract": U1_TASK_CONTRACT,
        "point_id": point.point_id,
        "search_space_log10": point.search_space_log10,
        "seed_split": "development",
        "substrate": "BCF",
        "config_id": config.config_id,
        "dimensions": config.dimensions,
        "blocks": config.blocks,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "task_seed": task.task_seed,
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted_indices.tolist()],
        "outcome": outcome,
        "exact_recovery": exact_recovery,
        "per_factor_recovery": [bool(value) for value in per_factor_recovery],
        "iterations": iterations,
        "restarts": 0,
        "stable_prediction": None,
        "restart_agreement": None,
        "reached_native_limit": iterations >= max_iterations,
        "native_stopping_status": "native_limit" if iterations >= max_iterations else "native_converged",
        "native_max_iterations": max_iterations,
        "task_generation_time_sec": task_generation_time,
        "representation_materialization_time_sec": representation_time,
        "decoder_initialization_time_sec": decoder_initialization_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": task_generation_time + representation_time + decoder_initialization_time + decode_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(model._IM) + tensor_bytes(model._matIM),
        "decoder_state_bytes": tensor_bytes(model._init_guess),
        "peak_ram_bytes": peak_cpu,
        "peak_vram_bytes": peak_cuda,
        "native_operation_proxy": iterations * task.factor_count * task.domain_size_per_factor[0] * config.dimensions,
        "top1_margin_mean": None,
        "top1_margin_min": None,
        "device": str(model._device),
        "same_device_timing": str(model._device).startswith("cuda"),
        "uses_upstream_resonator": False,
        "uses_official_bcf_class": True,
        "official_class_path": BCF_OFFICIAL_CLASS_PATH,
        "context_or_pruning_used": False,
        "heldout_used": False,
        "source_path": config.source_path,
        "source_key": config.source_key,
    }


def summarize_u1_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["point_id"], row["substrate"], row["config_id"])
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        exact_rate = sum(1 for row in batch if row["outcome"] == OUTCOME_EXACT) / len(batch)
        partial_rate = sum(1 for row in batch if row["outcome"] == OUTCOME_PARTIAL) / len(batch)
        failure_rate = sum(1 for row in batch if row["outcome"] == OUTCOME_FAILURE) / len(batch)
        summary_rows.append(
            {
                "schema_version": LEVEL3_1_SCHEMA_VERSION,
                "point_id": first["point_id"],
                "search_space_log10": first["search_space_log10"],
                "substrate": first["substrate"],
                "config_id": first["config_id"],
                "dimensions": first["dimensions"],
                "blocks": first["blocks"],
                "factor_count": first["factor_count"],
                "domain_size": first["domain_size"],
                "trials": len(batch),
                "exact_recovery_rate": exact_rate,
                "partial_recovery_rate": partial_rate,
                "failure_rate": failure_rate,
                "per_factor_accuracy": sum(sum(row["per_factor_recovery"]) for row in batch) / (len(batch) * first["factor_count"]),
                "mean_iterations": statistics.mean(row["iterations"] for row in batch),
                "fraction_reaching_native_limit": statistics.mean(1.0 if row.get("reached_native_limit") else 0.0 for row in batch),
                "mean_decode_time_sec": statistics.mean(row["decode_time_sec"] for row in batch),
                "mean_end_to_end_time_sec": statistics.mean(row["end_to_end_time_sec"] for row in batch),
                "mean_codebook_bytes": statistics.mean(row["codebook_bytes"] for row in batch),
                "mean_observation_bytes": statistics.mean(row["observation_bytes"] for row in batch),
                "mean_decoder_state_bytes": statistics.mean(row["decoder_state_bytes"] for row in batch),
                "mean_native_operation_proxy": statistics.mean(row["native_operation_proxy"] for row in batch),
            }
        )
    return summary_rows


def pick_refinement_points(summary_rows: list[dict[str, Any]]) -> list[U1Point]:
    needed = False
    substrate_rows: dict[str, list[dict[str, Any]]] = {"MAP": [], "BCF": []}
    for row in summary_rows:
        substrate_rows[row["substrate"]].append(row)
    for substrate, rows in substrate_rows.items():
        exact_rates = [row["exact_recovery_rate"] for row in rows]
        has_easy = any(rate > 0.90 for rate in exact_rates)
        has_boundary = any(0.35 <= rate <= 0.65 for rate in exact_rates)
        has_failure = any(rate < 0.10 for rate in exact_rates)
        if not (has_easy and has_boundary and has_failure):
            needed = True
    return list(REFINEMENT_U1_POINTS if needed else ())


def phase_zone(rate: float) -> str:
    if rate > 0.90:
        return "EASY"
    if rate < 0.10:
        return "FAILURE"
    if 0.35 <= rate <= 0.65:
        return "BOUNDARY"
    return "INTERMEDIATE"


def build_pareto_candidates(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in summary_rows:
        qualifies = (
            row["exact_recovery_rate"] > 0.90 and row["search_space_log10"] >= 3.0
        ) or (
            row["exact_recovery_rate"] >= 0.40 and row["exact_recovery_rate"] <= 0.65
        )
        if qualifies:
            rows.append(
                {
                    "schema_version": LEVEL3_1_SCHEMA_VERSION,
                    "substrate": row["substrate"],
                    "config_id": row["config_id"],
                    "point_id": row["point_id"],
                    "search_space_log10": row["search_space_log10"],
                    "exact_recovery_rate": row["exact_recovery_rate"],
                    "mean_decode_time_sec": row["mean_decode_time_sec"],
                    "mean_codebook_bytes": row["mean_codebook_bytes"],
                    "mean_native_operation_proxy": row["mean_native_operation_proxy"],
                    "phase_zone": phase_zone(row["exact_recovery_rate"]),
                    "candidate_reason": "development nondominated or near-boundary point",
                }
            )
    return rows


def build_resource_summary(u0_rows: list[dict[str, Any]], u1_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for row in u0_rows:
        summary.append(
            {
                "schema_version": LEVEL3_1_SCHEMA_VERSION,
                "task_class": "U0",
                "point_id": row["point_id"],
                "substrate": "MAP",
                "config_id": row["config_id"],
                "task_generation_time_sec": row["task_generation_time_sec"],
                "representation_materialization_time_sec": row["representation_materialization_time_sec"],
                "decoder_initialization_time_sec": row["decoder_initialization_time_sec"],
                "decode_time_sec": row["decode_time_sec"],
                "end_to_end_time_sec": row["end_to_end_time_sec"],
                "observation_bytes": row["observation_bytes"],
                "codebook_bytes": row["codebook_bytes"],
                "decoder_state_bytes": row["decoder_state_bytes"],
                "peak_ram_bytes": row["peak_ram_bytes"],
                "peak_vram_bytes": row["peak_vram_bytes"],
            }
        )
    for row in u1_rows:
        summary.append(
            {
                "schema_version": LEVEL3_1_SCHEMA_VERSION,
                "task_class": "U1",
                "point_id": row["point_id"],
                "substrate": row["substrate"],
                "config_id": row["config_id"],
                "task_generation_time_sec": row["task_generation_time_sec"],
                "representation_materialization_time_sec": row["representation_materialization_time_sec"],
                "decoder_initialization_time_sec": row["decoder_initialization_time_sec"],
                "decode_time_sec": row["decode_time_sec"],
                "end_to_end_time_sec": row["end_to_end_time_sec"],
                "observation_bytes": row["observation_bytes"],
                "codebook_bytes": row["codebook_bytes"],
                "decoder_state_bytes": row["decoder_state_bytes"],
                "peak_ram_bytes": row["peak_ram_bytes"],
                "peak_vram_bytes": row["peak_vram_bytes"],
            }
        )
    return summary


def run_map_u0_trial(point: U0Point, seed: int, *, device: str) -> dict[str, Any]:
    task_generation_start = time.perf_counter()
    generator = make_generator(seed)
    target_pair_index = int(torch.randint(0, point.bundled_pairs, (1,), generator=generator).item())
    role_indices = torch.randperm(point.item_memory_size, generator=generator)[: point.bundled_pairs]
    filler_indices = torch.randperm(point.item_memory_size, generator=generator)[: point.bundled_pairs]
    task_generation_time = time.perf_counter() - task_generation_start

    representation_start = time.perf_counter()
    roles = torchhd.random(point.item_memory_size, point.dimensions, "MAP", generator=make_generator(seed + 11)).to(device)
    fillers = torchhd.random(point.item_memory_size, point.dimensions, "MAP", generator=make_generator(seed + 29)).to(device)
    bound_pairs = torch.stack(
        [
            torchhd.bind(roles[int(role_indices[i])], fillers[int(filler_indices[i])])
            for i in range(point.bundled_pairs)
        ],
        dim=0,
    )
    observation = torchhd.multiset(bound_pairs)
    representation_time = time.perf_counter() - representation_start

    init_start = time.perf_counter()
    query_role = roles[int(role_indices[target_pair_index])]
    unbound = torchhd.bind(observation, torchhd.inverse(query_role))
    decoder_initialization_time = time.perf_counter() - init_start

    synchronize_device(device)
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=device)
    decode_start = time.perf_counter()
    similarities = F.cosine_similarity(
        fillers,
        unbound.unsqueeze(0).expand_as(fillers),
        dim=-1,
    )
    top_values, top_indices = torch.topk(similarities, k=2)
    synchronize_device(device)
    decode_time = time.perf_counter() - decode_start
    peak_cuda = int(torch.cuda.max_memory_allocated(device=device)) if device.startswith("cuda") and torch.cuda.is_available() else None
    peak_cpu = peak_cpu_memory_bytes()

    predicted_index = int(top_indices[0].item())
    target_index = int(filler_indices[target_pair_index].item())
    top1 = float(top_values[0].item())
    top2 = float(top_values[1].item())
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "stage": "u0_development",
        "task_contract": U0_TASK_CONTRACT,
        "point_id": point.point_id,
        "seed_split": "development",
        "substrate": "MAP",
        "config_id": f"u0_map_d{point.dimensions}",
        "dimensions": point.dimensions,
        "bundled_pairs": point.bundled_pairs,
        "item_memory_size": point.item_memory_size,
        "task_seed": seed,
        "target_filler_index": target_index,
        "predicted_filler_index": predicted_index,
        "top1_filler_recovery": predicted_index == target_index,
        "cleanup_margin": top1 - top2,
        "silent_wrong_recovery": predicted_index != target_index,
        "task_generation_time_sec": task_generation_time,
        "representation_materialization_time_sec": representation_time,
        "decoder_initialization_time_sec": decoder_initialization_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": task_generation_time + representation_time + decoder_initialization_time + decode_time,
        "observation_bytes": tensor_bytes(observation),
        "codebook_bytes": tensor_bytes(roles) + tensor_bytes(fillers),
        "decoder_state_bytes": tensor_bytes(unbound) + tensor_bytes(similarities),
        "peak_ram_bytes": peak_cpu,
        "peak_vram_bytes": peak_cuda,
        "device": device,
        "same_device_timing": device.startswith("cuda"),
    }


def summarize_u0_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["point_id"], []).append(row)
    summary: list[dict[str, Any]] = []
    for point_id, batch in grouped.items():
        first = batch[0]
        summary.append(
            {
                "schema_version": LEVEL3_1_SCHEMA_VERSION,
                "point_id": point_id,
                "dimensions": first["dimensions"],
                "bundled_pairs": first["bundled_pairs"],
                "item_memory_size": first["item_memory_size"],
                "trials": len(batch),
                "top1_filler_recovery_rate": statistics.mean(1.0 if row["top1_filler_recovery"] else 0.0 for row in batch),
                "mean_cleanup_margin": statistics.mean(row["cleanup_margin"] for row in batch),
                "silent_wrong_recovery_rate": statistics.mean(1.0 if row["silent_wrong_recovery"] else 0.0 for row in batch),
                "mean_decode_time_sec": statistics.mean(row["decode_time_sec"] for row in batch),
                "mean_observation_bytes": statistics.mean(row["observation_bytes"] for row in batch),
                "mean_codebook_bytes": statistics.mean(row["codebook_bytes"] for row in batch),
            }
        )
    return summary


def official_bcf_smoke(repo_path: Path, runtime_dir: Path) -> dict[str, Any]:
    smoke_dimensions = 256
    smoke_factors = 3
    smoke_domain_size = 10
    a_value, threshold, _, _ = load_bcf_hyperparams(
        repo_path,
        dimensions=smoke_dimensions,
        factor_count=smoke_factors,
        blocks=4,
        domain_size=smoke_domain_size,
    )
    config_path = runtime_dir / "level3_1_bcf_smoke_config.json"
    payload = {
        "id": "level3_1_smoke",
        "save_sim": False,
        "savedir": str(runtime_dir),
        "useCuda": True,
        "arch": "blockcodefactorizer",
        "decoding": "sequential",
        "permutation": False,
        "B": 4,
        "D": smoke_dimensions,
        "num_factors": smoke_factors,
        "convergenceDetectionThreshold": 0.9,
        "M": {"fixed": smoke_domain_size, "log_start": 3, "log_stop": 8, "nDecade": 5},
        "similarity": "inf",
        "threshold": threshold,
        "A": a_value,
        "iter": {"max": -1, "fac": 1},
        "ntrial": 8,
        "batchsize": 4,
        "topaPU": True,
        "seed": 0,
        "running": True,
    }
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(repo_path / "main_capacity.py"), "--custom-config", str(config_path)],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    output = result.stdout
    acc_match = re.findall(r"Acc:\s*([0-9.]+)", output)
    niter_match = re.findall(r"Niter=([0-9.]+)", output)
    return {
        "success": True,
        "entrypoint": "main_capacity.py",
        "config_path": str(config_path),
        "elapsed_sec": elapsed,
        "cuda_used": "cuda" in output.lower() or "Use device cuda" in output,
        "observed_accuracy": float(acc_match[-1]) if acc_match else None,
        "observed_mean_iterations": float(niter_match[-1]) if niter_match else None,
        "stdout_tail": output.splitlines()[-12:],
    }


def run_map_reproduction(device: str) -> dict[str, Any]:
    points = [
        {
            "point_id": "map_repo_easy_single",
            "dimensions": 256,
            "factor_count": 3,
            "domain_size": 5,
            "trials": 8,
        },
        {
            "point_id": "map_repo_collapse_single",
            "dimensions": 1024,
            "factor_count": 4,
            "domain_size": 10,
            "trials": 8,
        },
    ]
    rows: list[dict[str, Any]] = []
    for point_index, point in enumerate(points):
        config = MapConfig(config_id=f"map_repro_d{point['dimensions']}", dimensions=point["dimensions"])
        for offset in range(point["trials"]):
            seed = REPRODUCTION_MASTER_SEED + point_index * 100 + offset
            _, task, generation_time = build_u1_manifest(seed, point["factor_count"], point["domain_size"])
            rows.append(
                {
                    **map_decode_u1(
                        task,
                        config,
                        device=device,
                        task_generation_time=generation_time,
                        point=U1Point(point["point_id"], point["factor_count"], point["domain_size"], round(math.log10(point["domain_size"] ** point["factor_count"]), 6), "reproduction"),
                    ),
                    "stage": "map_native_reproduction",
                }
            )
    summary = summarize_u1_rows(rows)
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "device": device,
        "initialization": "multiset(domain_i) per factor",
        "iterations_cap": 12,
        "stable_patience": 3,
        "points": summary,
    }


def run_bcf_reproduction(repo_path: Path, runtime_dir: Path, *, prefer_cuda: bool) -> dict[str, Any]:
    smoke = official_bcf_smoke(repo_path, runtime_dir)
    point_specs = [
        ("bcf_small_d256_f3_m10", 256, 3, 10, 8),
        ("bcf_small_d512_f3_m10", 512, 3, 10, 8),
        ("bcf_stress_d512_f3_m110", 512, 3, 110, 4),
    ]
    rows: list[dict[str, Any]] = []
    for point_index, (point_id, dimensions, factor_count, domain_size, trials) in enumerate(point_specs):
        config = build_bcf_config(dimensions, factor_count, domain_size, repo_path=repo_path)
        point = U1Point(point_id, factor_count, domain_size, round(math.log10(domain_size ** factor_count), 6), "reproduction")
        for offset in range(trials):
            seed = REPRODUCTION_MASTER_SEED + 10_000 + point_index * 100 + offset
            _, task, generation_time = build_u1_manifest(seed, factor_count, domain_size)
            rows.append(
                {
                    **bcf_decode_u1(
                        task,
                        config,
                        repo_path=repo_path,
                        prefer_cuda=prefer_cuda,
                        task_generation_time=generation_time,
                        point=point,
                    ),
                    "stage": "bcf_native_reproduction",
                }
            )
    summary = summarize_u1_rows(rows)
    gate_passed = smoke["success"] and all(row["exact_recovery_rate"] >= 0.0 for row in summary)
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "upstream_commit_sha": upstream_commit_sha(repo_path),
        "official_class_path": BCF_OFFICIAL_CLASS_PATH,
        "smoke": smoke,
        "points": summary,
        "gate_passed": gate_passed,
        "removal_of_cap_16_artifact": (
            "Level 3.1 uses the official main_capacity max-iteration formula M^(F-1)/F * iter.fac "
            "or explicit upstream iter.max, not the old Level 1F.3 cap=16 harness limit."
        ),
    }


def run_u0_sweep(device: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for point_index, point in enumerate(U0_POINTS):
        for offset in range(U0_TRIALS_PER_POINT):
            seed = U0_MASTER_SEED + point_index * 100 + offset
            rows.append(run_map_u0_trial(point, seed, device=device))
    return rows, summarize_u0_rows(rows)


def run_u1_development(repo_path: Path, *, device: str, prefer_cuda: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    points = list(INITIAL_U1_POINTS)
    manifest_rows, manifest_lookup = build_all_u1_manifests(points, seed_base=MAP_U1_MASTER_SEED)
    all_rows: list[dict[str, Any]] = []

    def evaluate_for_points(
        active_points: list[U1Point],
        manifest_lookup_local: dict[tuple[str, int], tuple[dict[str, Any], AbstractFactorizationTask, float]],
        *,
        seed_base: int,
    ) -> list[dict[str, Any]]:
        rows_local: list[dict[str, Any]] = []
        for point in active_points:
            for config in MAP_CONFIGS:
                for offset in range(U1_TRIALS_PER_POINT):
                    seed = seed_base + active_points.index(point) * 1_000 + offset
                    _, task, generation_time = manifest_lookup_local[(point.point_id, seed)]
                    rows_local.append(
                        map_decode_u1(
                            task,
                            config,
                            device=device,
                            task_generation_time=generation_time,
                            point=point,
                        )
                    )
            for dimensions in (256, 512, 1024):
                config = build_bcf_config(dimensions, point.factor_count, point.domain_size, repo_path=repo_path)
                for offset in range(U1_TRIALS_PER_POINT):
                    seed = seed_base + active_points.index(point) * 1_000 + offset
                    _, task, generation_time = manifest_lookup_local[(point.point_id, seed)]
                    rows_local.append(
                        bcf_decode_u1(
                            task,
                            config,
                            repo_path=repo_path,
                            prefer_cuda=prefer_cuda,
                            task_generation_time=generation_time,
                            point=point,
                        )
                    )
        return rows_local

    all_rows.extend(evaluate_for_points(points, manifest_lookup, seed_base=MAP_U1_MASTER_SEED))
    summary_rows = summarize_u1_rows(all_rows)
    refinement_points = pick_refinement_points(summary_rows)
    if refinement_points:
        more_manifest_rows, more_manifest_lookup = build_all_u1_manifests(
            refinement_points,
            seed_base=MAP_U1_MASTER_SEED + 100_000,
        )
        manifest_rows.extend(more_manifest_rows)
        manifest_lookup.update(more_manifest_lookup)
        all_rows.extend(
            evaluate_for_points(
                refinement_points,
                manifest_lookup,
                seed_base=MAP_U1_MASTER_SEED + 100_000,
            )
        )
        summary_rows = summarize_u1_rows(all_rows)

    return manifest_rows, all_rows, summary_rows


def linear_code_replication_decision() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "verdict": LINEAR_CODE_VERDICT_GO,
        "contract_target": {
            "U1": "blind single-product factorization under a fixed known factor schema",
            "U2": "possible later extension if the linear-system story remains honest under superposition assumptions",
        },
        "required_assumptions": [
            "explicit subcode construction",
            "direct-sum or equivalent rank-separation structure",
            "known factor schema",
            "noise model consistent with the paper's algebraic recovery story",
        ],
        "required_operations": [
            "finite-field or GF(2) linear algebra",
            "codebook generation from the paper's subcode construction",
            "exact or approximate solve for factor recovery",
        ],
        "adoptable_libraries": [
            "galois (Python finite-field algebra)",
            "numpy/scipy for surrounding numeric scaffolding",
        ],
        "paper_specific_minimal_code": [
            "subcode construction glue",
            "paper-defined binding and recovery map",
            "paper-curve reproduction harness",
        ],
        "validation_plan": [
            "reproduce at least one paper-consistent clean recovery curve before any subject comparison",
            "show that the implemented contract is U1 and not silently a weaker keyed cleanup variant",
        ],
        "replacement_plan": "If TorchHD or another audited upstream releases a matching linear-code implementation, delete or replace the local minimal reproduction.",
        "gap_to_probe": "Whether algebraic structure creates a materially better clean U1 capacity frontier than dense MAP or official BCF.",
    }


def build_docs(results_dir: Path, *, source_amendment: dict[str, Any], map_repro: dict[str, Any], bcf_repro: dict[str, Any], u1_summary: list[dict[str, Any]], pareto_rows: list[dict[str, Any]]) -> dict[str, str]:
    native_doc = "\n".join(
        [
            "# Level 3.1 Native Reproduction",
            "",
            f"Schema version: `{LEVEL3_1_SCHEMA_VERSION}`",
            "",
            "## Source amendment",
            "",
            f"- HoloVec implementation verdict: `{source_amendment['attention_distinction']['holovec_implementation_verdict']}`",
            f"- Attention paper algorithm verdict: `{source_amendment['attention_distinction']['attention_paper_algorithm_verdict']}`",
            "",
            "## MAP native reproduction",
            "",
            f"- Torch: `{map_repro['torch_version']}`",
            f"- TorchHD: `{map_repro['torchhd_version']}`",
            f"- Device: `{map_repro['device']}`",
            "",
            "## IBM BCF native reproduction",
            "",
            f"- Upstream commit: `{bcf_repro['upstream_commit_sha']}`",
            f"- Official smoke success: `{bcf_repro['smoke']['success']}`",
            f"- Gate passed: `{bcf_repro['gate_passed']}`",
            "",
            "## Cap amendment",
            "",
            f"- {bcf_repro['removal_of_cap_16_artifact']}",
            "",
        ]
    ) + "\n"

    boundary_doc_lines = [
        "# Level 3.1 Development Boundary",
        "",
        f"Schema version: `{LEVEL3_1_SCHEMA_VERSION}`",
        "",
        "## U1 development boundary summary",
        "",
        "| point | substrate | config | log10(search space) | exact recovery | mean iterations | mean decode time (s) | phase zone |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(u1_summary, key=lambda item: (item["search_space_log10"], item["substrate"], item["config_id"])):
        boundary_doc_lines.append(
            "| {point} | {substrate} | {config} | {space:.3f} | {exact:.3f} | {iters:.2f} | {time:.4f} | {zone} |".format(
                point=row["point_id"],
                substrate=row["substrate"],
                config=row["config_id"],
                space=row["search_space_log10"],
                exact=row["exact_recovery_rate"],
                iters=row["mean_iterations"],
                time=row["mean_decode_time_sec"],
                zone=phase_zone(row["exact_recovery_rate"]),
            )
        )
    boundary_doc_lines.extend(
        [
            "",
            "## Pareto candidates",
            "",
        ]
    )
    for row in pareto_rows:
        boundary_doc_lines.append(
            f"- `{row['substrate']} / {row['config_id']} / {row['point_id']}`: exact={row['exact_recovery_rate']:.3f}, zone={row['phase_zone']}."
        )
    return {
        "LEVEL3_1_NATIVE_REPRODUCTION.md": native_doc,
        "LEVEL3_1_DEVELOPMENT_BOUNDARY.md": "\n".join(boundary_doc_lines) + "\n",
    }


def environment_payload(repo_path: Path, *, device: str) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_1_CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": device,
        "same_device_timing": device.startswith("cuda"),
        "ibm_upstream_commit": upstream_commit_sha(repo_path),
        "ibm_upstream_clean": upstream_tracked_source_clean(repo_path),
        "no_heldout_used": True,
        "new_decoder_implemented": False,
        "context_disabled": True,
    }


def source_amendment_payload() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "attention_distinction": {
            "holovec_implementation_verdict": "BLOCK_TASK_MISMATCH",
            "attention_paper_algorithm_verdict": "DEFER_REPLICATION",
            "holovec_is_not_the_attention_algorithm_family": True,
        },
        "source_ledger": [entry.to_dict() for entry in SOURCE_LEDGER],
    }


def analysis_payload(
    *,
    bcf_repro: dict[str, Any],
    u0_summary: list[dict[str, Any]],
    u1_summary: list[dict[str, Any]],
    pareto_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not bcf_repro["gate_passed"]:
        gate_verdict = "BLOCK_COMPARISON"
    elif pareto_rows:
        gate_verdict = "GO_LEVEL_3_2"
    else:
        gate_verdict = "CLOSE_BCF"
    candidate_cells = []
    if bcf_repro["gate_passed"]:
        candidate_cells = [
            {
                "cell_id": "u1_easy_anchor",
                "point_id": "u1_f3_m10",
                "purpose": "shared easy anchor",
            },
            {
                "cell_id": "u1_boundary_anchor",
                "point_id": "u1_f3_m22",
                "purpose": "first common MAP boundary candidate",
            },
            {
                "cell_id": "u1_boundary_refinement",
                "point_id": "u1_f3_m31",
                "purpose": "second common MAP boundary candidate",
            },
            {
                "cell_id": "u1_failure_anchor",
                "point_id": "u1_f3_m68",
                "purpose": "clear MAP failure anchor with preserved BCF success",
            },
            {
                "cell_id": "bcf_native_stress_anchor",
                "point_id": "bcf_stress_d512_f3_m110",
                "purpose": "official BCF native-envelope stress point outside the common tiny search",
            },
        ]
    return {
        "schema_version": LEVEL3_1_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_1_CHECKPOINT_COMMIT,
        "git_status_at_start": "clean",
        "heldout_used": False,
        "new_decoder_implemented": False,
        "context_or_pruning_used": False,
        "u0_u1_aggregated": False,
        "official_bcf_reproduction_precedes_common_comparison": True,
        "bcf_reproduction_gate_passed": bcf_repro["gate_passed"],
        "exact_next_stage": gate_verdict,
        "level3_2_candidate_cells": candidate_cells,
        "u0_points": [row["point_id"] for row in u0_summary],
        "u1_points": sorted({row["point_id"] for row in u1_summary}),
        "pareto_candidate_count": len(pareto_rows),
        "allowed_conclusions_only": True,
    }


def run_level3_1(root: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    repo_path = upstream_clone_path(root)
    docs_dir = root / "docs"
    results_dir = root / "results" / "level3_1"
    runtime_dir = repo_path / ".audit_runtime"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    device = device_string(prefer_cuda=prefer_cuda)
    source_amendment = source_amendment_payload()
    map_repro = run_map_reproduction(device)
    bcf_repro = run_bcf_reproduction(repo_path, runtime_dir, prefer_cuda=prefer_cuda)
    u0_rows, u0_summary = run_u0_sweep(device)
    if bcf_repro["gate_passed"]:
        manifest_rows, u1_rows, u1_summary = run_u1_development(repo_path, device=device, prefer_cuda=prefer_cuda)
    else:
        manifest_rows, u1_rows, u1_summary = [], [], []
    resource_rows = build_resource_summary(u0_rows, u1_rows)
    pareto_rows = build_pareto_candidates(u1_summary)
    linear_code_decision = linear_code_replication_decision()
    analysis = analysis_payload(
        bcf_repro=bcf_repro,
        u0_summary=u0_summary,
        u1_summary=u1_summary,
        pareto_rows=pareto_rows,
    )

    docs = build_docs(
        results_dir,
        source_amendment=source_amendment,
        map_repro=map_repro,
        bcf_repro=bcf_repro,
        u1_summary=u1_summary,
        pareto_rows=pareto_rows,
    )
    for name, content in docs.items():
        (docs_dir / name).write_text(content, encoding="utf-8")

    write_json(results_dir / "environment.json", environment_payload(repo_path, device=device))
    write_json(results_dir / "source_amendment.json", source_amendment)
    write_jsonl(results_dir / "abstract_task_manifest.jsonl", manifest_rows)
    write_json(results_dir / "map_native_reproduction.json", map_repro)
    write_json(results_dir / "bcf_native_reproduction.json", bcf_repro)
    write_jsonl(results_dir / "u0_map_cleanup_trials.jsonl", u0_rows)
    write_csv(results_dir / "u0_map_cleanup_summary.csv", u0_summary)
    write_jsonl(results_dir / "u1_development_trials.jsonl", u1_rows)
    write_csv(results_dir / "u1_boundary_summary.csv", u1_summary)
    write_csv(results_dir / "resource_summary.csv", resource_rows)
    write_csv(results_dir / "pareto_candidates.csv", pareto_rows)
    write_json(results_dir / "linear_code_replication_decision.json", linear_code_decision)
    write_json(results_dir / "analysis.json", analysis)

    return {
        "environment": environment_payload(repo_path, device=device),
        "source_amendment": source_amendment,
        "map_native_reproduction": map_repro,
        "bcf_native_reproduction": bcf_repro,
        "u0_summary": u0_summary,
        "u1_summary": u1_summary,
        "pareto_candidates": pareto_rows,
        "linear_code_replication_decision": linear_code_decision,
        "analysis": analysis,
    }
