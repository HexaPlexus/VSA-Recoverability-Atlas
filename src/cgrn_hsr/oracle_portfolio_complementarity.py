from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import platform
import random
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on Windows
    resource = None

import torch
import torchhd

from .baseline import bind_sequence, factors_from_indices, make_generator, normalized_similarity_pair
from .competitors.ibm_bcf_audit import AbstractFactorizationTask, upstream_clone_path
from .level3_2_confirmation import (
    FrozenBCFCellConfig,
    common_outcome,
    config_for_cell,
    peak_cpu_memory_bytes,
    synchronize_device,
    tensor_bytes,
    upstream_commit_sha,
    upstream_tracked_source_clean,
)
from .level3_2b_map_budget_robustness import (
    MAP_REPRESENTATION_SEED_OFFSETS,
    MapArmConfig,
    build_frozen_bcf_configs,
    build_map_arm_configs,
    evaluate_bcf_reference,
    evaluate_map_arm,
    factor_identity_tokens,
    instantiate_bcf_model,
    level3_2_seed_set,
    level3_2b_seed_set,
    prepare_map_task,
    prior_level3_1_seed_set,
)

SCHEMA_VERSION = "oracle-portfolio-v0.1"
CHECKPOINT_COMMIT = "538911d54f6f821c7cbb850731fb993f05097ba6"
TASK_CONTRACT = "clean_u1_f3_factor_specific_single_product"

METHOD_MAP_D512_FAST = "MAP_D512_FAST"
METHOD_MAP_D1024_FAST = "MAP_D1024_FAST"
METHOD_MAP_D1024_ROBUST = "MAP_D1024_ROBUST"
METHOD_BCF_NATIVE = "BCF_NATIVE"
METHOD_ABSTAIN = "ABSTAIN"

NON_ABSTAIN_METHODS = (
    METHOD_MAP_D512_FAST,
    METHOD_MAP_D1024_FAST,
    METHOD_MAP_D1024_ROBUST,
    METHOD_BCF_NATIVE,
)
ALL_METHODS = (*NON_ABSTAIN_METHODS, METHOD_ABSTAIN)

VERIFIED_ACCEPT = "VERIFIED_ACCEPT"
VERIFIED_REJECT = "VERIFIED_REJECT"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
METHOD_EXCEPTION = "METHOD_EXCEPTION"
BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"

PREMATERIALIZED_ALL_VIEWS = "PREMATERIALIZED_ALL_VIEWS"
LAZY_FALLBACK_VIEW = "LAZY_FALLBACK_VIEW"

RELEASE_BRANCH = "release/vsa-recoverability-atlas"
RESEARCH_BRANCH = "research/oracle-portfolio-v0.1"

COMMON_CELLS: tuple[dict[str, Any], ...] = (
    {"cell_id": "u1_easy_anchor", "classification": "EASY", "F": 3, "M": 10},
    {"cell_id": "u1_boundary_1", "classification": "TRANSITION", "F": 3, "M": 22},
    {"cell_id": "u1_boundary_2", "classification": "TRANSITION", "F": 3, "M": 31},
    {"cell_id": "u1_separation_anchor", "classification": "HARD", "F": 3, "M": 68},
)

SPLIT_SPECS: dict[str, dict[str, dict[str, int]]] = {
    "PILOT_RUNTIME": {
        "u1_easy_anchor": {"start": 970110100, "count": 16},
        "u1_boundary_1": {"start": 970120100, "count": 16},
        "u1_boundary_2": {"start": 970130100, "count": 16},
        "u1_separation_anchor": {"start": 970140100, "count": 16},
    },
    "PORTFOLIO_CALIBRATION": {
        "u1_easy_anchor": {"start": 970210100, "count": 32},
        "u1_boundary_1": {"start": 970220100, "count": 32},
        "u1_boundary_2": {"start": 970230100, "count": 32},
        "u1_separation_anchor": {"start": 970240100, "count": 32},
    },
    "FINAL_DEVELOPMENT_EVALUATION": {
        "u1_easy_anchor": {"start": 970310100, "count": 64},
        "u1_boundary_1": {"start": 970320100, "count": 64},
        "u1_boundary_2": {"start": 970330100, "count": 64},
        "u1_separation_anchor": {"start": 970340100, "count": 64},
    },
}

RANDOM_CONTROL_SEEDS = {
    "random_route": 970510100,
    "cost_matched_random_route": 970520100,
    "random_fixed_order_base": 970530100,
}

STATIC_THRESHOLDS = (10, 22, 31)
STATIC_ROUTE_GAIN_FRACTION_THRESHOLD = 0.90
STATIC_ROUTE_REGRET_ABS_THRESHOLD = 0.02
ORACLE_GAIN_ABS_THRESHOLD = 0.05
RESCUE_RATE_THRESHOLD = 0.10
RESCUE_COUNT_THRESHOLD = 4
DEPLOYABLE_ORACLE_GAIN_THRESHOLD = 0.03
PAIRWISE_CI_ALPHA = 0.05

UTILITY_PROFILES = {
    "SAFETY_CRITICAL": {
        "silent_error_penalty": 1_000_000.0,
        "abstention_penalty": 12.0,
        "latency_penalty": 1.0,
        "memory_penalty": 5e-8,
    },
    "LATENCY_CRITICAL": {
        "silent_error_penalty": 1_000_000.0,
        "abstention_penalty": 4.0,
        "latency_penalty": 8.0,
        "memory_penalty": 2e-8,
    },
    "BALANCED": {
        "silent_error_penalty": 1_000_000.0,
        "abstention_penalty": 8.0,
        "latency_penalty": 3.0,
        "memory_penalty": 4e-8,
    },
}

UTILITY_SENSITIVITY_GRID = {
    "silent_error_penalty": (100_000.0, 1_000_000.0),
    "abstention_penalty": (4.0, 8.0, 12.0),
    "latency_penalty": (1.0, 3.0, 8.0),
    "memory_penalty": (2e-8, 4e-8),
}

SEED_FILE_PATTERNS = ("*.json", "*.yaml", "*.yml")


@dataclass(frozen=True)
class FrozenMethod:
    method_id: str
    substrate: str
    source_artifact: str
    config_payload: dict[str, Any]
    config_hash: str
    representation_key: str | None
    dimensions: int | None
    role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrialSpec:
    split: str
    cell_id: str
    cell_classification: str
    factor_count: int
    domain_size: int
    trial_seed: int
    trial_id: str
    true_factor_indices: list[int]
    map_representation_seed_d512: int
    map_representation_seed_d1024: int
    bcf_representation_seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def trial_manifest(spec: TrialSpec) -> dict[str, Any]:
    return {
        "split": spec.split,
        "cell_id": spec.cell_id,
        "cell_classification": spec.cell_classification,
        "trial_id": spec.trial_id,
        "trial_seed": spec.trial_seed,
        "F": spec.factor_count,
        "M": spec.domain_size,
        "true_factor_indices": list(spec.true_factor_indices),
        "factor_identity_tokens": factor_identity_tokens(spec.factor_count, spec.domain_size),
        "map_representation_seed_d512": spec.map_representation_seed_d512,
        "map_representation_seed_d1024": spec.map_representation_seed_d1024,
        "bcf_representation_seed": spec.bcf_representation_seed,
        "task_contract": TASK_CONTRACT,
    }


def canonical_json_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo = math.floor(index)
    hi = math.ceil(index)
    if lo == hi:
        return ordered[lo]
    weight = index - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


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


def exact_mcnemar_p_value(b_only: int, a_only: int) -> float:
    total = b_only + a_only
    if total == 0:
        return 1.0
    tail = min(b_only, a_only)
    cdf = 0.0
    for k in range(0, tail + 1):
        cdf += math.comb(total, k) * (0.5 ** total)
    return min(1.0, 2.0 * cdf)


def pooled_non_easy(cell_id: str) -> bool:
    return cell_id != "u1_easy_anchor"


def cell_lookup(cell_id: str) -> dict[str, Any]:
    return next(cell for cell in COMMON_CELLS if cell["cell_id"] == cell_id)


def method_to_representation_key(method_id: str) -> str | None:
    return {
        METHOD_MAP_D512_FAST: "map_d512",
        METHOD_MAP_D1024_FAST: "map_d1024",
        METHOD_MAP_D1024_ROBUST: "map_d1024",
        METHOD_BCF_NATIVE: "bcf_d512",
        METHOD_ABSTAIN: None,
    }[method_id]


def resolve_frozen_methods(root: Path) -> dict[str, FrozenMethod]:
    level3_2 = json.loads((root / "results" / "level3_2" / "frozen_configs.json").read_text(encoding="utf-8"))
    level3_2b = json.loads((root / "results" / "level3_2b" / "map_arm_configs.json").read_text(encoding="utf-8"))
    map_d512 = next(row for row in level3_2["map_configs"] if row["config_id"] == "map_d512")
    map_d1024 = next(row for row in level3_2["map_configs"] if row["config_id"] == "map_d1024")
    map_robust = next(
        row
        for row in level3_2b["map_arms"]
        if row["arm_id"] == "map_1024_step32_r4_best_native_reconstruction"
    )
    bcf_rows = [
        row
        for row in level3_2["bcf_per_cell_official_lookup"]
        if row["domain_size"] in {10, 22, 31, 68}
    ]
    bcf_payload = {
        "bcf_config_family": level3_2["bcf_config_family"],
        "bcf_per_cell_official_lookup": bcf_rows,
        "ibm_upstream_commit": level3_2["ibm_upstream_commit"],
    }
    return {
        METHOD_MAP_D512_FAST: FrozenMethod(
            method_id=METHOD_MAP_D512_FAST,
            substrate="MAP",
            source_artifact="results/level3_2/frozen_configs.json",
            config_payload=map_d512,
            config_hash=canonical_json_hash(map_d512),
            representation_key="map_d512",
            dimensions=512,
            role="lowest-cost MAP baseline",
        ),
        METHOD_MAP_D1024_FAST: FrozenMethod(
            method_id=METHOD_MAP_D1024_FAST,
            substrate="MAP",
            source_artifact="results/level3_2/frozen_configs.json",
            config_payload=map_d1024,
            config_hash=canonical_json_hash(map_d1024),
            representation_key="map_d1024",
            dimensions=1024,
            role="stronger ordinary MAP baseline",
        ),
        METHOD_MAP_D1024_ROBUST: FrozenMethod(
            method_id=METHOD_MAP_D1024_ROBUST,
            substrate="MAP",
            source_artifact="results/level3_2b/map_arm_configs.json",
            config_payload=map_robust,
            config_hash=canonical_json_hash(map_robust),
            representation_key="map_d1024",
            dimensions=1024,
            role="higher-compute restarted MAP path",
        ),
        METHOD_BCF_NATIVE: FrozenMethod(
            method_id=METHOD_BCF_NATIVE,
            substrate="BCF",
            source_artifact="results/level3_2/frozen_configs.json",
            config_payload=bcf_payload,
            config_hash=canonical_json_hash(bcf_payload),
            representation_key="bcf_d512",
            dimensions=512,
            role="official native IBM BCF path",
        ),
        METHOD_ABSTAIN: FrozenMethod(
            method_id=METHOD_ABSTAIN,
            substrate="ABSTAIN",
            source_artifact="inline",
            config_payload={"method_id": METHOD_ABSTAIN, "typed_outcome": INSUFFICIENT_EVIDENCE},
            config_hash=canonical_json_hash({"method_id": METHOD_ABSTAIN}),
            representation_key=None,
            dimensions=None,
            role="typed no-answer control",
        ),
    }


def build_trial_spec(split: str, cell: dict[str, Any], trial_seed: int) -> TrialSpec:
    generator = make_generator(trial_seed)
    true_indices = [
        int(torch.randint(0, cell["M"], (1,), generator=generator).item())
        for _ in range(cell["F"])
    ]
    return TrialSpec(
        split=split,
        cell_id=cell["cell_id"],
        cell_classification=cell["classification"],
        factor_count=cell["F"],
        domain_size=cell["M"],
        trial_seed=trial_seed,
        trial_id=f"{split.lower()}-{cell['cell_id']}-seed-{trial_seed}",
        true_factor_indices=true_indices,
        map_representation_seed_d512=trial_seed + MAP_REPRESENTATION_SEED_OFFSETS[512],
        map_representation_seed_d1024=trial_seed + MAP_REPRESENTATION_SEED_OFFSETS[1024],
        bcf_representation_seed=trial_seed + 5_000,
    )


def spec_to_task(spec: TrialSpec) -> AbstractFactorizationTask:
    return AbstractFactorizationTask(
        task_seed=spec.trial_seed,
        factor_count=spec.factor_count,
        domain_size_per_factor=[spec.domain_size] * spec.factor_count,
        target_indices=spec.true_factor_indices,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )


def detect_seed_numbers_from_text(path: Path) -> set[int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits: set[int] = set()
    for line in text.splitlines():
        lower = line.lower()
        if "seed" not in lower and "start" not in lower:
            continue
        for match in re.finditer(r"\b([0-9]{6,})\b", line):
            hits.add(int(match.group(1)))
    return hits


def discover_historical_seed_markers(root: Path) -> dict[str, list[int]]:
    discovered: dict[str, list[int]] = {}
    current_namespace = Path("results") / "oracle_portfolio_v0_1"
    for pattern in SEED_FILE_PATTERNS:
        for path in sorted((root / "results").rglob(pattern)):
            try:
                relative = path.relative_to(root)
            except ValueError:
                relative = path
            if current_namespace in relative.parents:
                continue
            numbers = sorted(detect_seed_numbers_from_text(path))
            if numbers:
                discovered[str(relative)] = numbers
    return discovered


def explicit_historical_seed_set() -> set[int]:
    historical = set()
    historical.update(prior_level3_1_seed_set())
    historical.update(level3_2_seed_set())
    historical.update(level3_2b_seed_set())
    return historical


def current_stage_seed_set() -> set[int]:
    values: set[int] = set()
    for split in SPLIT_SPECS.values():
        for spec in split.values():
            values.update(range(spec["start"], spec["start"] + spec["count"]))
    return values


def seeds_are_fresh(root: Path) -> tuple[bool, dict[str, Any]]:
    historical_markers = discover_historical_seed_markers(root)
    exact_historical = explicit_historical_seed_set()
    current = current_stage_seed_set()
    overlapping_explicit = sorted(current.intersection(exact_historical))
    overlapping_markers = {
        path: sorted(current.intersection(numbers))
        for path, numbers in historical_markers.items()
        if current.intersection(numbers)
    }
    return (
        not overlapping_explicit and not overlapping_markers,
        {
            "current_stage_seed_count": len(current),
            "explicit_historical_seed_count": len(exact_historical),
            "historical_marker_files": len(historical_markers),
            "overlapping_explicit_seeds": overlapping_explicit,
            "overlapping_marker_files": overlapping_markers,
        },
    )


def device_name(prefer_cuda: bool) -> str:
    return "cuda:0" if prefer_cuda and torch.cuda.is_available() else "cpu"


def map_fast_arm(root: Path, dimensions: int) -> MapArmConfig:
    arms = build_map_arm_configs(Path(__file__).resolve().parents[2])
    arm_id = f"map_{dimensions}_step12"
    return next(arm for arm in arms if arm.arm_id == arm_id)


def map_robust_arm(root: Path) -> MapArmConfig:
    arms = build_map_arm_configs(root)
    return next(arm for arm in arms if arm.arm_id == "map_1024_step32_r4_best_native_reconstruction")


def bcf_config_by_cell(root: Path) -> dict[str, FrozenBCFCellConfig]:
    repo_path = upstream_clone_path(root)
    rows = build_frozen_bcf_configs(repo_path)
    return {
        "u1_easy_anchor": config_for_cell("u1_easy_anchor", rows),
        "u1_boundary_1": config_for_cell("u1_boundary_1", rows),
        "u1_boundary_2": config_for_cell("u1_boundary_2", rows),
        "u1_separation_anchor": config_for_cell("u1_separation_anchor", rows),
    }


def verify_map_prediction(prepared: Any, predicted_indices: list[int]) -> dict[str, Any]:
    predicted = torch.tensor(predicted_indices, dtype=torch.long)
    predicted_factors = factors_from_indices(prepared.domains.detach().cpu(), predicted)
    reconstruction = bind_sequence(predicted_factors)
    observed = prepared.observation.detach().cpu()
    exact_match = bool(torch.equal(reconstruction, observed))
    return {
        "verification_exact_match": exact_match,
        "verification_similarity": normalized_similarity_pair(reconstruction, observed),
    }


def verify_bcf_prediction(
    spec: TrialSpec,
    predicted_indices: list[int],
    *,
    root: Path,
    frozen_config: FrozenBCFCellConfig,
    prefer_cuda: bool,
) -> dict[str, Any]:
    task = spec_to_task(spec)
    model, init_time = instantiate_bcf_model(
        task,
        frozen_config,
        repo_path=upstream_clone_path(root),
        representation_seed=spec.bcf_representation_seed,
        prefer_cuda=prefer_cuda,
    )
    observed_batch = torch.tensor([task.target_indices], dtype=torch.long, device=model._device)
    predicted_batch = torch.tensor([predicted_indices], dtype=torch.long, device=model._device)
    start = time.perf_counter()
    observed = model.encode(observed_batch)
    predicted_observation = model.encode(predicted_batch)
    synchronize_device(str(model._device))
    elapsed = time.perf_counter() - start
    exact_match = bool(torch.equal(observed.detach().cpu(), predicted_observation.detach().cpu()))
    return {
        "verification_exact_match": exact_match,
        "verification_similarity": 1.0 if exact_match else 0.0,
        "verification_init_time_sec": init_time,
        "verification_encode_time_sec": elapsed,
        "verification_peak_ram_bytes": peak_cpu_memory_bytes(),
        "verification_peak_vram_bytes": (
            int(torch.cuda.max_memory_allocated(device=model._device))
            if str(model._device).startswith("cuda") and torch.cuda.is_available()
            else None
        ),
    }


def verifier_disposition(result: dict[str, Any], verification: dict[str, Any]) -> str:
    if result.get("typed_failure") == METHOD_EXCEPTION:
        return METHOD_EXCEPTION
    if verification.get("verification_exact_match"):
        return VERIFIED_ACCEPT
    if result.get("reached_native_limit"):
        return BUDGET_EXHAUSTED
    if result.get("predicted_indices") is None:
        return INSUFFICIENT_EVIDENCE
    return VERIFIED_REJECT


def abstain_result(spec: TrialSpec) -> dict[str, Any]:
    return {
        "method_id": METHOD_ABSTAIN,
        "method_hash": canonical_json_hash({"method_id": METHOD_ABSTAIN}),
        "predicted_indices": None,
        "ground_truth_correct": False,
        "verifier_disposition": INSUFFICIENT_EVIDENCE,
        "verifier_accepted": False,
        "correct_and_accepted": False,
        "wrong_and_accepted": False,
        "correct_but_rejected": False,
        "typed_failure": INSUFFICIENT_EVIDENCE,
        "latency_decode_sec": 0.0,
        "latency_verify_sec": 0.0,
        "latency_total_query_sec": 0.0,
        "latency_cold_query_sec": 0.0,
        "persistent_bytes": 0,
        "transient_bytes": 0,
        "materialization_time_sec": 0.0,
        "native_metrics": {},
        "common_typed_checks": {},
        "reached_native_limit": False,
        "representation_key": None,
        "silent_wrong_accepted": False,
    }


def evaluate_method(
    spec: TrialSpec,
    task: AbstractFactorizationTask,
    *,
    root: Path,
    method: FrozenMethod,
    prefer_cuda: bool,
    prepared_cache: dict[int, Any],
    bcf_configs: dict[str, FrozenBCFCellConfig],
) -> dict[str, Any]:
    if method.method_id == METHOD_ABSTAIN:
        return abstain_result(spec)
    manifest = trial_manifest(spec)

    try:
        if method.method_id == METHOD_MAP_D512_FAST:
            arm = map_fast_arm(root, 512)
            prepared = prepared_cache[512]
            raw = evaluate_map_arm(manifest, task, prepared, arm=arm, root=root)
            verify_start = time.perf_counter()
            verification = verify_map_prediction(prepared, raw["predicted_indices"])
            verify_elapsed = time.perf_counter() - verify_start
        elif method.method_id == METHOD_MAP_D1024_FAST:
            arm = map_fast_arm(root, 1024)
            prepared = prepared_cache[1024]
            raw = evaluate_map_arm(manifest, task, prepared, arm=arm, root=root)
            verify_start = time.perf_counter()
            verification = verify_map_prediction(prepared, raw["predicted_indices"])
            verify_elapsed = time.perf_counter() - verify_start
        elif method.method_id == METHOD_MAP_D1024_ROBUST:
            arm = map_robust_arm(root)
            prepared = prepared_cache[1024]
            raw = evaluate_map_arm(manifest, task, prepared, arm=arm, root=root)
            verify_start = time.perf_counter()
            verification = verify_map_prediction(prepared, raw["predicted_indices"])
            verify_elapsed = time.perf_counter() - verify_start
        elif method.method_id == METHOD_BCF_NATIVE:
            frozen_config = bcf_configs[spec.cell_id]
            raw = evaluate_bcf_reference(
                manifest,
                task,
                repo_path=upstream_clone_path(root),
                frozen_config=frozen_config,
                prefer_cuda=prefer_cuda,
            )
            verify_start = time.perf_counter()
            verification = verify_bcf_prediction(
                spec,
                raw["predicted_indices"],
                root=root,
                frozen_config=frozen_config,
                prefer_cuda=prefer_cuda,
            )
            verify_elapsed = time.perf_counter() - verify_start
        else:  # pragma: no cover - guarded by frozen methods
            raise ValueError(f"Unsupported method: {method.method_id}")
    except Exception as exc:  # pragma: no cover - exercised by failure tests
        return {
            "method_id": method.method_id,
            "method_hash": method.config_hash,
            "predicted_indices": None,
            "ground_truth_correct": False,
            "verifier_disposition": METHOD_EXCEPTION,
            "verifier_accepted": False,
            "correct_and_accepted": False,
            "wrong_and_accepted": False,
            "correct_but_rejected": False,
            "typed_failure": METHOD_EXCEPTION,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "latency_decode_sec": 0.0,
            "latency_verify_sec": 0.0,
            "latency_total_query_sec": 0.0,
            "latency_cold_query_sec": 0.0,
            "persistent_bytes": 0,
            "transient_bytes": 0,
            "materialization_time_sec": 0.0,
            "native_metrics": {},
            "common_typed_checks": {},
            "reached_native_limit": False,
            "representation_key": method.representation_key,
            "silent_wrong_accepted": False,
        }

    disposition = verifier_disposition(raw, verification)
    accepted = disposition == VERIFIED_ACCEPT
    exact = bool(raw["exact_recovery"])
    materialization_time = float(raw["representation_materialization_time_sec"]) + float(raw["decoder_initialization_time_sec"])
    query_latency = float(raw["decode_time_sec"]) + float(verify_elapsed)
    cold_latency = materialization_time + query_latency
    return {
        "method_id": method.method_id,
        "method_hash": method.config_hash,
        "predicted_indices": raw["predicted_indices"],
        "ground_truth_correct": exact,
        "verifier_disposition": disposition,
        "verifier_accepted": accepted,
        "correct_and_accepted": exact and accepted,
        "wrong_and_accepted": (not exact) and accepted,
        "correct_but_rejected": exact and (not accepted),
        "typed_failure": disposition if disposition != VERIFIED_ACCEPT else None,
        "latency_decode_sec": float(raw["decode_time_sec"]),
        "latency_verify_sec": float(verify_elapsed),
        "latency_total_query_sec": query_latency,
        "latency_cold_query_sec": cold_latency,
        "persistent_bytes": int(raw["codebook_bytes"]),
        "transient_bytes": int(raw["decoder_state_bytes"]),
        "materialization_time_sec": materialization_time,
        "native_metrics": {
            "iterations": raw["executed_steps"],
            "restarts": raw["restart_count"],
            "native_stop_status": raw["native_stopping_status"],
            "selected_mean_margin": raw.get("selected_mean_margin"),
            "selected_native_reconstruction": raw.get("selected_native_reconstruction"),
            "restart_agreement": raw.get("restart_agreement"),
            "native_operation_proxy": raw.get("native_operation_proxy"),
        },
        "common_typed_checks": verification,
        "reached_native_limit": bool(raw["reached_native_limit"]),
        "representation_key": method.representation_key,
        "silent_wrong_accepted": (not exact) and accepted,
    }


def run_split(
    root: Path,
    *,
    split: str,
    prefer_cuda: bool,
    methods: dict[str, FrozenMethod],
    bcf_configs: dict[str, FrozenBCFCellConfig],
) -> list[dict[str, Any]]:
    device = device_name(prefer_cuda)
    rows: list[dict[str, Any]] = []
    for cell in COMMON_CELLS:
        seed_spec = SPLIT_SPECS[split][cell["cell_id"]]
        print(f"[{split}] {cell['cell_id']} trials={seed_spec['count']} device={device}", flush=True)
        for offset, seed in enumerate(range(seed_spec["start"], seed_spec["start"] + seed_spec["count"]), start=1):
            spec = build_trial_spec(split, cell, seed)
            task = spec_to_task(spec)
            prepared_cache = {
                512: prepare_map_task(task, dimensions=512, representation_seed=spec.map_representation_seed_d512, device=device),
                1024: prepare_map_task(task, dimensions=1024, representation_seed=spec.map_representation_seed_d1024, device=device),
            }
            method_results = {
                method_id: evaluate_method(
                    spec,
                    task,
                    root=root,
                    method=methods[method_id],
                    prefer_cuda=prefer_cuda,
                    prepared_cache=prepared_cache,
                    bcf_configs=bcf_configs,
                )
                for method_id in ALL_METHODS
            }
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "split": split,
                    "cell_id": spec.cell_id,
                    "classification": spec.cell_classification,
                    "trial_id": spec.trial_id,
                    "trial_seed": spec.trial_seed,
                    "F": spec.factor_count,
                    "M": spec.domain_size,
                    "true_factor_indices": spec.true_factor_indices,
                    "map_representation_seed_d512": spec.map_representation_seed_d512,
                    "map_representation_seed_d1024": spec.map_representation_seed_d1024,
                    "bcf_representation_seed": spec.bcf_representation_seed,
                    "semantic_search_space": spec.domain_size ** spec.factor_count,
                    "method_results": method_results,
                }
            )
            if offset % 8 == 0 or offset == seed_spec["count"]:
                print(f"  completed {offset}/{seed_spec['count']} for {cell['cell_id']}", flush=True)
    return rows


def flatten_method_rows(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trial in trials:
        for method_id, result in trial["method_results"].items():
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "split": trial["split"],
                    "cell_id": trial["cell_id"],
                    "classification": trial["classification"],
                    "trial_id": trial["trial_id"],
                    "trial_seed": trial["trial_seed"],
                    "F": trial["F"],
                    "M": trial["M"],
                    "semantic_search_space": trial["semantic_search_space"],
                    "true_factor_indices": trial["true_factor_indices"],
                    **result,
                }
            )
    return rows


def subset_label(row: dict[str, Any]) -> list[str]:
    labels = [row["cell_id"], "ALL_FINAL" if row["split"] == "FINAL_DEVELOPMENT_EVALUATION" else row["split"]]
    if row["split"] == "FINAL_DEVELOPMENT_EVALUATION":
        labels.append("FINAL_NON_EASY" if pooled_non_easy(row["cell_id"]) else "FINAL_EASY_ONLY")
    return labels


def method_summary(flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in flat_rows:
        for label in subset_label(row):
            groups.setdefault((label, row["method_id"]), []).append(row)
    summary: list[dict[str, Any]] = []
    for (label, method_id), batch in sorted(groups.items()):
        trials = len(batch)
        correct = sum(1 for row in batch if row["ground_truth_correct"])
        accepted = sum(1 for row in batch if row["verifier_accepted"])
        correct_accepted = sum(1 for row in batch if row["correct_and_accepted"])
        wrong_accepted = sum(1 for row in batch if row["wrong_and_accepted"])
        ci_low, ci_high = wilson_interval(correct_accepted, trials)
        acceptance_coverage = correct_accepted / trials if trials else 0.0
        conditional_risk = wrong_accepted / accepted if accepted else 0.0
        summary.append(
            {
                "schema_version": SCHEMA_VERSION,
                "subset": label,
                "method_id": method_id,
                "trials": trials,
                "exact_recovery_rate": correct / trials if trials else 0.0,
                "accepted_exact_coverage": acceptance_coverage,
                "accepted_exact_ci_low": ci_low,
                "accepted_exact_ci_high": ci_high,
                "coverage": accepted / trials if trials else 0.0,
                "conditional_risk": conditional_risk,
                "silent_wrong_rate": wrong_accepted / trials if trials else 0.0,
                "correct_but_rejected_rate": sum(1 for row in batch if row["correct_but_rejected"]) / trials if trials else 0.0,
                "median_latency_sec": statistics.median(row["latency_total_query_sec"] for row in batch) if batch else 0.0,
                "p95_latency_sec": quantile([row["latency_total_query_sec"] for row in batch], 0.95),
                "p99_latency_sec": quantile([row["latency_total_query_sec"] for row in batch], 0.99),
                "mean_persistent_bytes": statistics.mean(row["persistent_bytes"] for row in batch) if batch else 0.0,
                "mean_transient_bytes": statistics.mean(row["transient_bytes"] for row in batch) if batch else 0.0,
                "mean_materialization_sec": statistics.mean(row["materialization_time_sec"] for row in batch) if batch else 0.0,
                "mean_iterations": statistics.mean(float(row["native_metrics"].get("iterations", 0.0)) for row in batch) if batch else 0.0,
                "mean_restarts": statistics.mean(float(row["native_metrics"].get("restarts", 0.0)) for row in batch) if batch else 0.0,
            }
        )
    return summary


def pairwise_rows(flat_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_trial = {(row["subset_label"] if "subset_label" in row else "", row["trial_id"], row["method_id"]): row for row in []}
    del by_trial
    overlap_rows: list[dict[str, Any]] = []
    rescue_rows: list[dict[str, Any]] = []
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION" and row["method_id"] in NON_ABSTAIN_METHODS]
    subsets = {
        "FINAL_ALL": finals,
        "FINAL_NON_EASY": [row for row in finals if pooled_non_easy(row["cell_id"])],
        **{cell["cell_id"]: [row for row in finals if row["cell_id"] == cell["cell_id"]] for cell in COMMON_CELLS},
    }
    for subset_name, subset_rows in subsets.items():
        index = {(row["trial_id"], row["method_id"]): row for row in subset_rows}
        trial_ids = sorted({row["trial_id"] for row in subset_rows})
        for left, right in itertools.permutations(NON_ABSTAIN_METHODS, 2):
            both_correct = left_only = right_only = both_wrong = 0
            left_fail_right_rescue = 0
            right_fail_left_rescue = 0
            accepted_rescue = 0
            for trial_id in trial_ids:
                left_row = index[(trial_id, left)]
                right_row = index[(trial_id, right)]
                left_ok = bool(left_row["ground_truth_correct"])
                right_ok = bool(right_row["ground_truth_correct"])
                if left_ok and right_ok:
                    both_correct += 1
                elif left_ok and not right_ok:
                    left_only += 1
                elif right_ok and not left_ok:
                    right_only += 1
                else:
                    both_wrong += 1
                if (not left_ok) and right_ok:
                    left_fail_right_rescue += 1
                if (not right_ok) and left_ok:
                    right_fail_left_rescue += 1
                if (not left_row["verifier_accepted"]) and right_row["correct_and_accepted"]:
                    accepted_rescue += 1
            left_failures = left_only + both_wrong
            right_failures = right_only + both_wrong
            correct_sets = both_correct + left_only + right_only
            failure_sets = both_wrong + left_only + right_only
            overlap_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "subset": subset_name,
                    "left_method": left,
                    "right_method": right,
                    "both_correct": both_correct,
                    "left_correct_right_wrong": left_only,
                    "left_wrong_right_correct": right_only,
                    "both_wrong": both_wrong,
                    "correct_set_jaccard": both_correct / correct_sets if correct_sets else 0.0,
                    "failure_set_jaccard": both_wrong / failure_sets if failure_sets else 0.0,
                    "error_correlation_proxy": both_wrong / max(1, left_failures + right_failures - both_wrong),
                    "mcnemar_exact_p": exact_mcnemar_p_value(right_only, left_only),
                }
            )
            rescue_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "subset": subset_name,
                    "failed_method": left,
                    "rescue_method": right,
                    "rescued_trial_count": left_fail_right_rescue,
                    "rescue_rate_given_failure": left_fail_right_rescue / left_failures if left_failures else 0.0,
                    "verifier_accepted_rescue_count": accepted_rescue,
                    "verifier_accepted_rescue_rate_given_failure": accepted_rescue / left_failures if left_failures else 0.0,
                    "reverse_rescue_count": right_fail_left_rescue,
                }
            )
    return overlap_rows, rescue_rows


def unique_representation_bytes(rows: list[dict[str, Any]], methods: tuple[str, ...]) -> int:
    by_key: dict[str, int] = {}
    for row in rows:
        if row["method_id"] not in methods:
            continue
        key = row["representation_key"]
        if key is None:
            continue
        by_key[key] = max(by_key.get(key, 0), int(row["persistent_bytes"]))
    return sum(by_key.values())


def strategy_trial_result(
    trial_rows: dict[str, dict[str, Any]],
    order: tuple[str, ...],
    *,
    cost_mode: str,
) -> dict[str, Any]:
    invoked = 0
    latency = 0.0
    cold_latency = 0.0
    accepted_method = None
    enabled_rows = [trial_rows[method] for method in order]
    persistent = unique_representation_bytes(enabled_rows, order)
    materialized: set[str] = set()
    for method in order:
        row = trial_rows[method]
        invoked += 1
        latency += row["latency_total_query_sec"]
        if cost_mode == LAZY_FALLBACK_VIEW:
            rep_key = row["representation_key"]
            if rep_key is not None and rep_key not in materialized:
                cold_latency += row["materialization_time_sec"]
                materialized.add(rep_key)
        if row["verifier_accepted"]:
            accepted_method = method
            break
    cold_latency += latency
    if accepted_method is None:
        accepted_method = METHOD_ABSTAIN
    accepted_row = trial_rows.get(accepted_method) if accepted_method != METHOD_ABSTAIN else None
    return {
        "accepted_method": accepted_method,
        "ground_truth_correct": bool(accepted_row["ground_truth_correct"]) if accepted_row else False,
        "verifier_accepted": bool(accepted_row["verifier_accepted"]) if accepted_row else False,
        "wrong_and_accepted": bool(accepted_row["wrong_and_accepted"]) if accepted_row else False,
        "coverage": 1.0 if accepted_row and accepted_row["verifier_accepted"] else 0.0,
        "latency_sec": latency,
        "cold_latency_sec": cold_latency,
        "methods_invoked": invoked if accepted_method != METHOD_ABSTAIN else len(order),
        "persistent_bytes": persistent,
        "transient_bytes": max((int(trial_rows[method]["transient_bytes"]) for method in order), default=0),
        "materialization_time_sec": cold_latency - latency,
    }


def oracle_trial_result(
    trial_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
    cost_mode: str,
) -> dict[str, Any]:
    candidates = [trial_rows[method] for method in NON_ABSTAIN_METHODS]
    if mode == "ORACLE_DIRECT_MIN_COST_CORRECT":
        eligible = [row for row in candidates if row["ground_truth_correct"]]
    elif mode == "ORACLE_VERIFIER_CONSTRAINED":
        eligible = [row for row in candidates if row["correct_and_accepted"]]
    elif mode == "ORACLE_COVERAGE_AT_ZERO_SILENT_ERROR":
        eligible = [row for row in candidates if row["correct_and_accepted"]]
    else:
        raise ValueError(mode)
    if not eligible:
        return strategy_trial_result(trial_rows, tuple(), cost_mode=cost_mode) | {"accepted_method": METHOD_ABSTAIN}
    chosen = min(eligible, key=lambda row: (row["latency_total_query_sec"], row["method_id"]))
    persistent = unique_representation_bytes(candidates, NON_ABSTAIN_METHODS)
    cold_latency = chosen["latency_total_query_sec"]
    if cost_mode == LAZY_FALLBACK_VIEW and chosen["representation_key"] is not None:
        cold_latency += chosen["materialization_time_sec"]
    return {
        "accepted_method": chosen["method_id"],
        "ground_truth_correct": True,
        "verifier_accepted": bool(chosen["verifier_accepted"]),
        "wrong_and_accepted": False,
        "coverage": 1.0 if chosen["verifier_accepted"] else 0.0,
        "latency_sec": float(chosen["latency_total_query_sec"]),
        "cold_latency_sec": cold_latency,
        "methods_invoked": 1,
        "persistent_bytes": persistent,
        "transient_bytes": int(chosen["transient_bytes"]),
        "materialization_time_sec": cold_latency - float(chosen["latency_total_query_sec"]),
    }


def best_single_method(flat_rows: list[dict[str, Any]], subset: str = "FINAL_ALL") -> str:
    summaries = method_summary(flat_rows)
    candidates = [row for row in summaries if row["subset"] == subset and row["method_id"] in NON_ABSTAIN_METHODS]
    best = max(
        candidates,
        key=lambda row: (
            row["accepted_exact_coverage"],
            -row["conditional_risk"],
            -row["median_latency_sec"],
            -row["mean_persistent_bytes"],
        ),
    )
    return str(best["method_id"])


def evaluate_single_method_strategies(flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION"]
    by_trial: dict[str, dict[str, dict[str, Any]]] = {}
    for row in finals:
        by_trial.setdefault(row["trial_id"], {})[row["method_id"]] = row
    strategy_rows: list[dict[str, Any]] = []
    for method_id in ALL_METHODS:
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            trial_results = []
            for method_map in by_trial.values():
                if method_id == METHOD_ABSTAIN:
                    trial_results.append(
                        {
                            "accepted_method": METHOD_ABSTAIN,
                            "ground_truth_correct": False,
                            "verifier_accepted": False,
                            "wrong_and_accepted": False,
                            "coverage": 0.0,
                            "latency_sec": 0.0,
                            "cold_latency_sec": 0.0,
                            "methods_invoked": 0,
                            "persistent_bytes": 0,
                            "transient_bytes": 0,
                            "materialization_time_sec": 0.0,
                        }
                    )
                else:
                    row = method_map[method_id]
                    cold_latency = row["latency_total_query_sec"]
                    if cost_mode == LAZY_FALLBACK_VIEW and row["representation_key"] is not None:
                        cold_latency += row["materialization_time_sec"]
                    trial_results.append(
                        {
                            "accepted_method": method_id if row["verifier_accepted"] else METHOD_ABSTAIN,
                            "ground_truth_correct": row["ground_truth_correct"],
                            "verifier_accepted": row["verifier_accepted"],
                            "wrong_and_accepted": row["wrong_and_accepted"],
                            "coverage": 1.0 if row["verifier_accepted"] else 0.0,
                            "latency_sec": row["latency_total_query_sec"],
                            "cold_latency_sec": cold_latency,
                            "methods_invoked": 1,
                            "persistent_bytes": row["persistent_bytes"],
                            "transient_bytes": row["transient_bytes"],
                            "materialization_time_sec": cold_latency - row["latency_total_query_sec"],
                        }
                    )
            strategy_rows.extend(
                summarize_strategy_trials(
                    trial_results,
                    strategy_id=f"ALWAYS_{method_id}",
                    cost_mode=cost_mode,
                    trial_metadata={trial_id: by_trial[trial_id][next(iter(by_trial[trial_id]))] for trial_id in by_trial},
                )
            )
    return strategy_rows


def summarize_strategy_trials(
    trial_results: list[dict[str, Any]],
    *,
    strategy_id: str,
    cost_mode: str,
    trial_metadata: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered_metadata = list(trial_metadata.items())
    grouped: dict[str, list[dict[str, Any]]] = {
        "FINAL_ALL": trial_results,
        "FINAL_NON_EASY": [row for (trial_id, meta), row in zip(ordered_metadata, trial_results) if pooled_non_easy(meta["cell_id"])],
    }
    for cell in COMMON_CELLS:
        grouped[cell["cell_id"]] = [
            row for (_, meta), row in zip(ordered_metadata, trial_results) if meta["cell_id"] == cell["cell_id"]
        ]
    for subset, batch in grouped.items():
        trials = len(batch)
        accepted = sum(1 for row in batch if row["verifier_accepted"])
        correct_accepted = sum(1 for row in batch if row["ground_truth_correct"] and row["verifier_accepted"])
        wrong_accepted = sum(1 for row in batch if row["wrong_and_accepted"])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "strategy_id": strategy_id,
                "cost_mode": cost_mode,
                "subset": subset,
                "trials": trials,
                "accepted_exact_coverage": correct_accepted / trials if trials else 0.0,
                "coverage": accepted / trials if trials else 0.0,
                "conditional_risk": wrong_accepted / accepted if accepted else 0.0,
                "silent_wrong_rate": wrong_accepted / trials if trials else 0.0,
                "median_latency_sec": statistics.median(row["latency_sec"] for row in batch) if batch else 0.0,
                "p95_latency_sec": quantile([row["latency_sec"] for row in batch], 0.95),
                "p99_latency_sec": quantile([row["latency_sec"] for row in batch], 0.99),
                "median_cold_latency_sec": statistics.median(row["cold_latency_sec"] for row in batch) if batch else 0.0,
                "mean_methods_invoked": statistics.mean(row["methods_invoked"] for row in batch) if batch else 0.0,
                "mean_persistent_bytes": statistics.mean(row["persistent_bytes"] for row in batch) if batch else 0.0,
                "mean_transient_bytes": statistics.mean(row["transient_bytes"] for row in batch) if batch else 0.0,
                "mean_materialization_time_sec": statistics.mean(row["materialization_time_sec"] for row in batch) if batch else 0.0,
            }
        )
    return rows


def evaluate_fixed_order_cascades(flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION"]
    by_trial: dict[str, dict[str, dict[str, Any]]] = {}
    for row in finals:
        by_trial.setdefault(row["trial_id"], {})[row["method_id"]] = row
    rows: list[dict[str, Any]] = []
    for order in itertools.permutations(NON_ABSTAIN_METHODS):
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            trial_results = [strategy_trial_result(method_map, order, cost_mode=cost_mode) for method_map in by_trial.values()]
            rows.extend(
                summarize_strategy_trials(
                    trial_results,
                    strategy_id="CASCADE:" + "->".join(order),
                    cost_mode=cost_mode,
                    trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in by_trial.items()},
                )
            )
    return rows


def generate_random_distribution(
    calibration_rows: list[dict[str, Any]],
    *,
    target_latency: float,
) -> dict[str, float]:
    method_means = {
        method: statistics.mean(
            row["latency_total_query_sec"] for row in calibration_rows if row["method_id"] == method
        )
        for method in NON_ABSTAIN_METHODS
    }
    best_gap = float("inf")
    best_dist: dict[str, float] | None = None
    steps = range(0, 21)
    for a in steps:
        for b in steps:
            for c in steps:
                d = 20 - a - b - c
                if d < 0:
                    continue
                probs = {
                    NON_ABSTAIN_METHODS[0]: a / 20.0,
                    NON_ABSTAIN_METHODS[1]: b / 20.0,
                    NON_ABSTAIN_METHODS[2]: c / 20.0,
                    NON_ABSTAIN_METHODS[3]: d / 20.0,
                }
                if sum(probs.values()) == 0.0:
                    continue
                expected = sum(probs[method] * method_means[method] for method in NON_ABSTAIN_METHODS)
                gap = abs(expected - target_latency)
                if gap < best_gap:
                    best_gap = gap
                    best_dist = probs
    assert best_dist is not None
    return best_dist


def sample_method(distribution: dict[str, float], rng: random.Random) -> str:
    threshold = rng.random()
    running = 0.0
    for method in NON_ABSTAIN_METHODS:
        running += distribution[method]
        if threshold <= running:
            return method
    return NON_ABSTAIN_METHODS[-1]


def evaluate_random_controls(flat_rows: list[dict[str, Any]], static_route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION"]
    calibration = [row for row in flat_rows if row["split"] == "PORTFOLIO_CALIBRATION"]
    by_trial: dict[str, dict[str, dict[str, Any]]] = {}
    for row in finals:
        by_trial.setdefault(row["trial_id"], {})[row["method_id"]] = row
    calibration_static = next(
        row for row in static_route_rows if row["profile"] == "BALANCED" and row["subset"] == "FINAL_ALL"
    )
    target_latency = calibration_static["median_latency_sec"]
    matched_distribution = generate_random_distribution(calibration, target_latency=target_latency)
    rows: list[dict[str, Any]] = []
    for control_name, distribution in (
        ("RANDOM_ROUTE", {method: 0.25 for method in NON_ABSTAIN_METHODS}),
        ("COST_MATCHED_RANDOM_ROUTE", matched_distribution),
    ):
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            rng = random.Random(RANDOM_CONTROL_SEEDS["random_route"] if control_name == "RANDOM_ROUTE" else RANDOM_CONTROL_SEEDS["cost_matched_random_route"])
            trial_results = []
            for method_map in by_trial.values():
                method = sample_method(distribution, rng)
                row = method_map[method]
                cold_latency = row["latency_total_query_sec"]
                if cost_mode == LAZY_FALLBACK_VIEW and row["representation_key"] is not None:
                    cold_latency += row["materialization_time_sec"]
                trial_results.append(
                    {
                        "accepted_method": method if row["verifier_accepted"] else METHOD_ABSTAIN,
                        "ground_truth_correct": row["ground_truth_correct"],
                        "verifier_accepted": row["verifier_accepted"],
                        "wrong_and_accepted": row["wrong_and_accepted"],
                        "coverage": 1.0 if row["verifier_accepted"] else 0.0,
                        "latency_sec": row["latency_total_query_sec"],
                        "cold_latency_sec": cold_latency,
                        "methods_invoked": 1,
                        "persistent_bytes": row["persistent_bytes"],
                        "transient_bytes": row["transient_bytes"],
                        "materialization_time_sec": cold_latency - row["latency_total_query_sec"],
                    }
                )
            rows.extend(
                summarize_strategy_trials(
                    trial_results,
                    strategy_id=control_name,
                    cost_mode=cost_mode,
                    trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in by_trial.items()},
                )
            )
    for order_seed in range(5):
        rng = random.Random(RANDOM_CONTROL_SEEDS["random_fixed_order_base"] + order_seed)
        order = list(NON_ABSTAIN_METHODS)
        rng.shuffle(order)
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            trial_results = [strategy_trial_result(method_map, tuple(order), cost_mode=cost_mode) for method_map in by_trial.values()]
            rows.extend(
                summarize_strategy_trials(
                    trial_results,
                    strategy_id=f"RANDOM_FIXED_ORDER:{order_seed}:" + "->".join(order),
                    cost_mode=cost_mode,
                    trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in by_trial.items()},
                )
            )
    return rows


def evaluate_oracles(flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION"]
    by_trial: dict[str, dict[str, dict[str, Any]]] = {}
    for row in finals:
        by_trial.setdefault(row["trial_id"], {})[row["method_id"]] = row
    rows: list[dict[str, Any]] = []
    for oracle_mode in (
        "ORACLE_DIRECT_MIN_COST_CORRECT",
        "ORACLE_VERIFIER_CONSTRAINED",
        "ORACLE_COVERAGE_AT_ZERO_SILENT_ERROR",
    ):
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            trial_results = [oracle_trial_result(method_map, mode=oracle_mode, cost_mode=cost_mode) for method_map in by_trial.values()]
            rows.extend(
                summarize_strategy_trials(
                    trial_results,
                    strategy_id=oracle_mode,
                    cost_mode=cost_mode,
                    trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in by_trial.items()},
                )
            )
    return rows


def static_policy_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for method in NON_ABSTAIN_METHODS:
        candidates.append({"policy_id": f"ALWAYS:{method}", "threshold": None, "low_method": method, "high_method": method})
    for threshold in STATIC_THRESHOLDS:
        for low_method, high_method in itertools.product(NON_ABSTAIN_METHODS, repeat=2):
            candidates.append(
                {
                    "policy_id": f"THRESHOLD:{threshold}:{low_method}:{high_method}",
                    "threshold": threshold,
                    "low_method": low_method,
                    "high_method": high_method,
                }
            )
    return candidates


def apply_static_policy(policy: dict[str, Any], row: dict[str, Any]) -> str:
    threshold = policy["threshold"]
    if threshold is None:
        return str(policy["low_method"])
    return str(policy["low_method"] if row["M"] <= threshold else policy["high_method"])


def utility_value(summary_row: dict[str, Any], profile: dict[str, float]) -> float:
    return (
        summary_row["accepted_exact_coverage"]
        - profile["silent_error_penalty"] * summary_row["silent_wrong_rate"]
        - profile["abstention_penalty"] * (1.0 - summary_row["coverage"])
        - profile["latency_penalty"] * summary_row["median_latency_sec"]
        - profile["memory_penalty"] * summary_row["mean_persistent_bytes"]
    )


def fit_static_routes(flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calibration = [row for row in flat_rows if row["split"] == "PORTFOLIO_CALIBRATION"]
    finals = [row for row in flat_rows if row["split"] == "FINAL_DEVELOPMENT_EVALUATION"]
    calibration_trials: dict[str, dict[str, dict[str, Any]]] = {}
    final_trials: dict[str, dict[str, dict[str, Any]]] = {}
    for row in calibration:
        calibration_trials.setdefault(row["trial_id"], {})[row["method_id"]] = row
    for row in finals:
        final_trials.setdefault(row["trial_id"], {})[row["method_id"]] = row
    results: list[dict[str, Any]] = []
    for profile_name, profile in UTILITY_PROFILES.items():
        best_policy = None
        best_utility = -float("inf")
        for policy in static_policy_candidates():
            trial_results = []
            for method_map in calibration_trials.values():
                any_row = next(iter(method_map.values()))
                method = apply_static_policy(policy, any_row)
                row = method_map[method]
                trial_results.append(
                    {
                        "accepted_method": method if row["verifier_accepted"] else METHOD_ABSTAIN,
                        "ground_truth_correct": row["ground_truth_correct"],
                        "verifier_accepted": row["verifier_accepted"],
                        "wrong_and_accepted": row["wrong_and_accepted"],
                        "coverage": 1.0 if row["verifier_accepted"] else 0.0,
                        "latency_sec": row["latency_total_query_sec"],
                        "cold_latency_sec": row["latency_total_query_sec"] + row["materialization_time_sec"],
                        "methods_invoked": 1,
                        "persistent_bytes": row["persistent_bytes"],
                        "transient_bytes": row["transient_bytes"],
                        "materialization_time_sec": row["materialization_time_sec"],
                    }
                )
            summaries = summarize_strategy_trials(
                trial_results,
                strategy_id=policy["policy_id"],
                cost_mode=PREMATERIALIZED_ALL_VIEWS,
                trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in calibration_trials.items()},
            )
            summary = next(row for row in summaries if row["subset"] == "FINAL_ALL")
            utility = utility_value(summary, profile)
            if utility > best_utility:
                best_utility = utility
                best_policy = policy
        assert best_policy is not None
        for cost_mode in (PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW):
            trial_results = []
            for method_map in final_trials.values():
                any_row = next(iter(method_map.values()))
                method = apply_static_policy(best_policy, any_row)
                row = method_map[method]
                cold_latency = row["latency_total_query_sec"]
                if cost_mode == LAZY_FALLBACK_VIEW and row["representation_key"] is not None:
                    cold_latency += row["materialization_time_sec"]
                trial_results.append(
                    {
                        "accepted_method": method if row["verifier_accepted"] else METHOD_ABSTAIN,
                        "ground_truth_correct": row["ground_truth_correct"],
                        "verifier_accepted": row["verifier_accepted"],
                        "wrong_and_accepted": row["wrong_and_accepted"],
                        "coverage": 1.0 if row["verifier_accepted"] else 0.0,
                        "latency_sec": row["latency_total_query_sec"],
                        "cold_latency_sec": cold_latency,
                        "methods_invoked": 1,
                        "persistent_bytes": row["persistent_bytes"],
                        "transient_bytes": row["transient_bytes"],
                        "materialization_time_sec": cold_latency - row["latency_total_query_sec"],
                    }
                )
            summaries = summarize_strategy_trials(
                trial_results,
                strategy_id=best_policy["policy_id"],
                cost_mode=cost_mode,
                trial_metadata={trial_id: method_map[next(iter(method_map))] for trial_id, method_map in final_trials.items()},
            )
            for row in summaries:
                row["profile"] = profile_name
                row["calibration_policy_id"] = best_policy["policy_id"]
                row["threshold"] = best_policy["threshold"]
                row["low_method"] = best_policy["low_method"]
                row["high_method"] = best_policy["high_method"]
                row["calibration_utility"] = best_utility
                results.append(row)
    return results


def utility_sensitivity(strategy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row for row in strategy_rows
        if row["subset"] == "FINAL_ALL" and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS
    ]
    results: list[dict[str, Any]] = []
    for silent_penalty, abstention_penalty, latency_penalty, memory_penalty in itertools.product(
        UTILITY_SENSITIVITY_GRID["silent_error_penalty"],
        UTILITY_SENSITIVITY_GRID["abstention_penalty"],
        UTILITY_SENSITIVITY_GRID["latency_penalty"],
        UTILITY_SENSITIVITY_GRID["memory_penalty"],
    ):
        best = max(
            candidates,
            key=lambda row: (
                row["accepted_exact_coverage"]
                - silent_penalty * row["silent_wrong_rate"]
                - abstention_penalty * (1.0 - row["coverage"])
                - latency_penalty * row["median_latency_sec"]
                - memory_penalty * row["mean_persistent_bytes"]
            )
        )
        results.append(
            {
                "schema_version": SCHEMA_VERSION,
                "silent_error_penalty": silent_penalty,
                "abstention_penalty": abstention_penalty,
                "latency_penalty": latency_penalty,
                "memory_penalty": memory_penalty,
                "winning_strategy": best["strategy_id"],
                "subset": best["subset"],
                "cost_mode": best["cost_mode"],
                "accepted_exact_coverage": best["accepted_exact_coverage"],
                "median_latency_sec": best["median_latency_sec"],
            }
        )
    return results


def evaluate_gates(
    method_rows: list[dict[str, Any]],
    rescue_rows: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    static_rows: list[dict[str, Any]],
    strategy_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    final_all_methods = [row for row in method_rows if row["subset"] == "ALL_FINAL" and row["method_id"] in NON_ABSTAIN_METHODS]
    best_single = max(final_all_methods, key=lambda row: row["accepted_exact_coverage"])
    oracle_direct = next(
        row
        for row in oracle_rows
        if row["strategy_id"] == "ORACLE_DIRECT_MIN_COST_CORRECT"
        and row["subset"] == "FINAL_NON_EASY"
        and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS
    )
    oracle_verifier = next(
        row
        for row in oracle_rows
        if row["strategy_id"] == "ORACLE_VERIFIER_CONSTRAINED"
        and row["subset"] == "FINAL_NON_EASY"
        and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS
    )
    best_single_non_easy = max(
        [row for row in method_rows if row["subset"] == "FINAL_NON_EASY" and row["method_id"] in NON_ABSTAIN_METHODS],
        key=lambda row: row["accepted_exact_coverage"],
    )
    oracle_gain = oracle_direct["accepted_exact_coverage"] - best_single_non_easy["accepted_exact_coverage"]
    meaningful_rescue = max(
        (
            row
            for row in rescue_rows
            if row["subset"] == "FINAL_NON_EASY"
        ),
        key=lambda row: (row["rescue_rate_given_failure"], row["rescued_trial_count"]),
    )
    best_static = max(
        [row for row in static_rows if row["subset"] == "FINAL_NON_EASY" and row["profile"] == "BALANCED" and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS],
        key=lambda row: row["accepted_exact_coverage"],
    )
    oracle_gain_all = next(
        row for row in oracle_rows
        if row["strategy_id"] == "ORACLE_DIRECT_MIN_COST_CORRECT" and row["subset"] == "FINAL_ALL" and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS
    )["accepted_exact_coverage"] - best_single["accepted_exact_coverage"]
    static_gain_all = best_static["accepted_exact_coverage"] - best_single_non_easy["accepted_exact_coverage"]
    gain_fraction = 1.0 if oracle_gain <= 0.0 else max(0.0, static_gain_all / oracle_gain)
    nondominated_portfolios = [
        row
        for row in strategy_rows
        if row["subset"] == "FINAL_ALL"
        and row["cost_mode"] == PREMATERIALIZED_ALL_VIEWS
        and row["strategy_id"].startswith(("CASCADE:", "ORACLE_", "THRESHOLD:"))
        and row["accepted_exact_coverage"] >= best_single["accepted_exact_coverage"]
        and row.get("silent_wrong_rate", 0.0) <= best_single.get("silent_wrong_rate", 0.0)
        and (
            row["median_latency_sec"] < best_single["median_latency_sec"]
            or row["mean_persistent_bytes"] < best_single["mean_persistent_bytes"]
            or row["accepted_exact_coverage"] > best_single["accepted_exact_coverage"]
        )
    ]
    return {
        "gate_contract_parity": True,
        "gate_oracle_gain": oracle_gain >= ORACLE_GAIN_ABS_THRESHOLD and oracle_gain_all >= ORACLE_GAIN_ABS_THRESHOLD,
        "gate_oracle_gain_value": oracle_gain,
        "gate_rescue_asymmetry": meaningful_rescue["rescue_rate_given_failure"] >= RESCUE_RATE_THRESHOLD and meaningful_rescue["rescued_trial_count"] >= RESCUE_COUNT_THRESHOLD,
        "gate_rescue_row": meaningful_rescue,
        "gate_verifier_viability": (oracle_verifier["accepted_exact_coverage"] - best_single_non_easy["accepted_exact_coverage"]) >= DEPLOYABLE_ORACLE_GAIN_THRESHOLD,
        "gate_verifier_gain_value": oracle_verifier["accepted_exact_coverage"] - best_single_non_easy["accepted_exact_coverage"],
        "gate_cost_aware_value": bool(nondominated_portfolios),
        "gate_static_route_sufficiency": gain_fraction >= STATIC_ROUTE_GAIN_FRACTION_THRESHOLD or (oracle_gain - static_gain_all) <= STATIC_ROUTE_REGRET_ABS_THRESHOLD,
        "gate_static_gain_fraction": gain_fraction,
        "gate_static_residual_regret": oracle_gain - static_gain_all,
        "best_single_method": best_single["method_id"],
    }


def build_protocol(root: Path, methods: dict[str, FrozenMethod], seed_report: dict[str, Any]) -> dict[str, Any]:
    protocol = {
        "schema_version": SCHEMA_VERSION,
        "checkpoint_commit": CHECKPOINT_COMMIT,
        "branch_target": RESEARCH_BRANCH,
        "source_release_branch": RELEASE_BRANCH,
        "task_contract": {
            "semantic_task": "clean single-product factorization",
            "factor_count": 3,
            "ordered_designated_target_tuple": True,
            "factor_specific_domains": True,
            "noise": False,
            "nested_structures": False,
            "ground_truth_during_inference": False,
        },
        "cells": list(COMMON_CELLS),
        "splits": SPLIT_SPECS,
        "frozen_methods": {method_id: methods[method_id].to_dict() for method_id in ALL_METHODS},
        "cost_modes": [PREMATERIALIZED_ALL_VIEWS, LAZY_FALLBACK_VIEW],
        "static_route_candidates": static_policy_candidates(),
        "random_control_seeds": RANDOM_CONTROL_SEEDS,
        "utility_profiles": UTILITY_PROFILES,
        "utility_sensitivity_grid": UTILITY_SENSITIVITY_GRID,
        "prospective_gates": {
            "oracle_gain_abs_threshold": ORACLE_GAIN_ABS_THRESHOLD,
            "rescue_rate_threshold": RESCUE_RATE_THRESHOLD,
            "rescue_count_threshold": RESCUE_COUNT_THRESHOLD,
            "deployable_oracle_gain_threshold": DEPLOYABLE_ORACLE_GAIN_THRESHOLD,
            "static_route_gain_fraction_threshold": STATIC_ROUTE_GAIN_FRACTION_THRESHOLD,
            "static_route_regret_abs_threshold": STATIC_ROUTE_REGRET_ABS_THRESHOLD,
        },
        "seed_integrity": seed_report,
        "official_heldout_execution_count": 0,
        "allowed_change_scope": [
            "new paired development evaluation only",
            "no router",
            "no hardware model",
            "no new VSA method",
        ],
        "forbidden_claims": [
            "learned router justified before oracle complementarity",
            "cross-substrate hidden-state handoff",
            "new general cascade principle",
            "held-out confirmation",
        ],
    }
    protocol["protocol_hash"] = canonical_json_hash(protocol)
    return protocol


def execution_plan(protocol: dict[str, Any]) -> str:
    paired_trials = sum(spec["count"] for split in SPLIT_SPECS.values() for spec in split.values())
    method_calls = paired_trials * len(NON_ABSTAIN_METHODS)
    cascade_orders = math.factorial(len(NON_ABSTAIN_METHODS))
    return "\n".join(
        [
            "# Oracle Portfolio Execution Plan",
            "",
            f"- Protocol hash: `{protocol['protocol_hash']}`",
            f"- Cells: `{', '.join(cell['cell_id'] for cell in COMMON_CELLS)}`",
            f"- Split sizes: pilot=16, calibration=32, final=64 per cell",
            f"- Total paired semantic trials: `{paired_trials}`",
            f"- Non-abstain method executions: `{method_calls}`",
            f"- Fixed-order cascades: `{cascade_orders}`",
            f"- Utility profiles: `{', '.join(UTILITY_PROFILES.keys())}`",
            f"- Cost modes: `{PREMATERIALIZED_ALL_VIEWS}`, `{LAZY_FALLBACK_VIEW}`",
            "- No held-out execution",
        ]
    ) + "\n"


def build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Oracle Portfolio Complementarity Report",
        "",
        f"- Build verdict: `{summary['build_verdict']}`",
        f"- Scientific verdict: `{summary['scientific_verdict']}`",
        f"- Portfolio verdict: `{summary['portfolio_verdict']}`",
        f"- Protocol hash: `{summary['protocol_hash']}`",
        f"- Best fixed single method: `{summary['best_single_method']}`",
        f"- Gate outcomes: `{json.dumps(summary['gate_outcomes'], sort_keys=True)}`",
        "",
        "## Constraints",
        "",
        "- No router, no hardware model, no new substrate implementation.",
        "- Common clean-U1 F=3 semantic contract only.",
        "- Dual-representation costs counted explicitly.",
        "",
        "## Main interpretation",
        "",
        summary["interpretation"],
        "",
    ]
    return "\n".join(lines) + "\n"


def summarize_results(
    protocol: dict[str, Any],
    method_rows: list[dict[str, Any]],
    overlap_rows: list[dict[str, Any]],
    rescue_rows: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    cascade_rows: list[dict[str, Any]],
    static_rows: list[dict[str, Any]],
    random_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    all_strategy_rows = [*cascade_rows, *oracle_rows, *static_rows, *random_rows]
    gates = evaluate_gates(method_rows, rescue_rows, oracle_rows, static_rows, all_strategy_rows)
    best_single_method_id = gates["best_single_method"]
    if not gates["gate_oracle_gain"]:
        build_verdict = "STOP_PORTFOLIO_LINE"
        scientific_verdict = "ORACLE_COMPLEMENTARITY_NOT_SUPPORTED"
        portfolio_verdict = "DOMINANT_SINGLE_METHOD"
        next_stage = "NO_FURTHER_PORTFOLIO_WORK"
        interpretation = (
            "The direct oracle did not achieve the prospectively meaningful recovery improvement over the best fixed method on hard or pooled non-easy cells. "
            "This does not justify a practical router, FPGA model, or Lava seam."
        )
    elif gates["gate_static_route_sufficiency"]:
        build_verdict = "ADOPT_STATIC_ROUTE"
        scientific_verdict = "ORACLE_COMPLEMENTARITY_PRESENT"
        portfolio_verdict = "ADOPT_STATIC_ROUTE"
        next_stage = "STATIC_CASCADE_CONFIRMATION"
        interpretation = (
            "Complementarity exists, but calibration-level difficulty already captures almost all deployable oracle value. "
            "A trivial static route is sufficient and a learned instance router remains blocked."
        )
    elif gates["gate_verifier_viability"] and gates["gate_cost_aware_value"]:
        build_verdict = "INSTANCE_LEVEL_ROUTER_JUSTIFIED"
        scientific_verdict = "VERIFIER_CONSTRAINED_COMPLEMENTARITY_PRESENT"
        portfolio_verdict = "COST_AWARE_PORTFOLIO_VALUE_PRESENT"
        next_stage = "PRACTICAL_ROUTER_V0_1"
        interpretation = (
            "Residual verified oracle value remains after static routing and cost accounting, so an evidence-based practical router would be lawful as the next seam."
        )
    else:
        build_verdict = "COMPLEMENTARITY_NOT_DEPLOYABLE"
        scientific_verdict = "COMPLEMENTARITY_NOT_DEPLOYABLE"
        portfolio_verdict = "COST_ERASES_COMPLEMENTARITY"
        next_stage = "NO_FURTHER_PORTFOLIO_WORK"
        interpretation = (
            "Any residual complementarity was erased by verifier constraints, dual-encoding cost, or cumulative cascade latency, so no practical router is justified."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_hash": protocol["protocol_hash"],
        "build_verdict": build_verdict,
        "scientific_verdict": scientific_verdict,
        "portfolio_verdict": portfolio_verdict,
        "next_stage": next_stage,
        "best_single_method": best_single_method_id,
        "gate_outcomes": gates,
        "interpretation": interpretation,
    }


def environment_payload(root: Path, *, prefer_cuda: bool, methods: dict[str, FrozenMethod]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "checkpoint_commit": CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": device_name(prefer_cuda),
        "resource_module_available": resource is not None,
        "ibm_upstream_commit": upstream_commit_sha(upstream_clone_path(root)),
        "ibm_upstream_clean": upstream_tracked_source_clean(upstream_clone_path(root)),
        "frozen_method_hashes": {method_id: method.config_hash for method_id, method in methods.items()},
    }


def run_oracle_portfolio(root: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    methods = resolve_frozen_methods(root)
    seed_ok, seed_report = seeds_are_fresh(root)
    if not seed_ok:
        raise RuntimeError(f"Seed overlap detected: {seed_report}")

    results_dir = root / "results" / "oracle_portfolio_v0_1"
    results_dir.mkdir(parents=True, exist_ok=True)
    bcf_configs = bcf_config_by_cell(root)
    protocol = build_protocol(root, methods, seed_report)
    write_json(results_dir / "method_configs.json", {
        "schema_version": SCHEMA_VERSION,
        "methods": {method_id: method.to_dict() for method_id, method in methods.items()},
        "bcf_upstream_commit": upstream_commit_sha(upstream_clone_path(root)),
        "source_hashes": {
            "results/level3_2/frozen_configs.json": sha256_path(root / "results" / "level3_2" / "frozen_configs.json"),
            "results/level3_2b/map_arm_configs.json": sha256_path(root / "results" / "level3_2b" / "map_arm_configs.json"),
            "src/cgrn_hsr/level3_2_confirmation.py": sha256_path(root / "src" / "cgrn_hsr" / "level3_2_confirmation.py"),
            "src/cgrn_hsr/level3_2b_map_budget_robustness.py": sha256_path(root / "src" / "cgrn_hsr" / "level3_2b_map_budget_robustness.py"),
            "src/cgrn_hsr/competitors/ibm_bcf_audit.py": sha256_path(root / "src" / "cgrn_hsr" / "competitors" / "ibm_bcf_audit.py"),
        },
    })
    (results_dir / "frozen_protocol.yaml").write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (results_dir / "execution_plan.md").write_text(execution_plan(protocol), encoding="utf-8")
    write_json(results_dir / "environment.json", environment_payload(root, prefer_cuda=prefer_cuda, methods=methods))

    trials = []
    for split in ("PILOT_RUNTIME", "PORTFOLIO_CALIBRATION", "FINAL_DEVELOPMENT_EVALUATION"):
        trials.extend(run_split(root, split=split, prefer_cuda=prefer_cuda, methods=methods, bcf_configs=bcf_configs))
    write_jsonl(results_dir / "paired_trials.jsonl", trials)

    flat_rows = flatten_method_rows(trials)
    summary_rows = method_summary(flat_rows)
    overlap_rows, rescue_rows = pairwise_rows(flat_rows)
    single_strategy_rows = evaluate_single_method_strategies(flat_rows)
    cascade_rows = evaluate_fixed_order_cascades(flat_rows)
    oracle_rows = evaluate_oracles(flat_rows)
    static_rows = fit_static_routes(flat_rows)
    random_rows = evaluate_random_controls(flat_rows, static_rows)
    all_strategy_rows = [*single_strategy_rows, *cascade_rows, *oracle_rows, *static_rows, *random_rows]
    utility_rows = utility_sensitivity(all_strategy_rows)
    summary = summarize_results(protocol, summary_rows, overlap_rows, rescue_rows, oracle_rows, cascade_rows, static_rows, random_rows)

    write_csv(results_dir / "method_summary.csv", summary_rows)
    write_csv(results_dir / "pairwise_overlap.csv", overlap_rows)
    write_csv(results_dir / "rescue_matrix.csv", rescue_rows)
    write_csv(results_dir / "fixed_order_cascades.csv", cascade_rows)
    write_csv(results_dir / "oracle_frontiers.csv", oracle_rows)
    write_csv(results_dir / "static_route_results.csv", static_rows)
    write_csv(results_dir / "utility_sensitivity.csv", utility_rows)
    write_json(results_dir / "summary.json", summary)
    (results_dir / "report.md").write_text(build_report(summary), encoding="utf-8")
    return {
        "protocol": protocol,
        "method_summary": summary_rows,
        "single_method_strategies": single_strategy_rows,
        "pairwise_overlap": overlap_rows,
        "rescue_matrix": rescue_rows,
        "fixed_order_cascades": cascade_rows,
        "oracle_frontiers": oracle_rows,
        "static_route_results": static_rows,
        "utility_sensitivity": utility_rows,
        "summary": summary,
    }
