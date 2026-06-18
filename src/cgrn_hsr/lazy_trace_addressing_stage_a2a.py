from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional runtime
    faiss = None

from .lazy_trace_addressing_stage_a1 import (
    ACCEPT_MARGIN,
    ACCEPT_SIMILARITY_THRESHOLD,
    METHOD_A1_PRIMARY,
    METHOD_A1_SECONDARY_1,
    METHOD_A1_SECONDARY_2,
    METHOD_A1_MULTI_PROBE,
    METHOD_EXACT_HASH as METHOD_A1_EXACT_HASH,
    METHOD_GLOBAL_SCAN as METHOD_A1_GLOBAL_SCAN,
    METHOD_RANDOM_ROUTING as METHOD_A1_RANDOM_ROUTING,
    METHOD_STAGE_A_MULTI_TABLE,
    OUTCOME_ABSTAIN,
    OUTCOME_ACCEPT,
    OUTCOME_AMBIGUOUS_TRACE,
    OUTCOME_EXPAND,
    PRIMARY_CANDIDATE_BUDGET,
    PROJECTION_SEEDS as STAGE_A1_PROJECTION_SEEDS,
    QUERY_CORRUPTION_POINTS_A1,
    QUERY_KIND_CONTRACT_AMBIGUITY,
    QUERY_KIND_EXACT_AMBIGUITY,
    QUERY_KIND_NEAR_CONFLICT,
    QUERY_KIND_UNIQUE,
    RERANK_K,
    STAGE_A1_SCHEMA_VERSION,
    STAGE_A_PROTOCOL_HASH,
    StageA1Query,
    StageA1Record,
    _build_lsh_router,
    _build_random_router,
    _decoder_contract_decision,
    _exact_trace_decision,
    _global_scan,
    _stage_a_protocol_hash,
    build_dataset as build_stage_a1_dataset,
    build_queries as build_stage_a1_queries,
    build_trace_index,
    budget_matched_random_configs as stage_a1_random_configs,
    contract_key_from_candidate,
    contract_key_from_trace,
    expected_any_table_hit_probability,
    exact_key_from_candidate,
    exact_key_from_trace,
    method_configs as stage_a1_method_configs,
    prior_known_seed_set as stage_a1_prior_known_seed_set,
    seeds_are_fresh as stage_a1_seeds_are_fresh,
)
from .trace_index import TraceIndex, TraceStoreEntry
from .trace_record import TRACE_VALID, payload_checksum
from .verification import RerankedCandidate, rerank_candidates, validate_entry

STAGE_A2A_SCHEMA_VERSION = "lazy-semantic-trace-stage-a2a-dev-v1"
STAGE_A2A_TASK_NAME = "Lazy Semantic-to-Trace Addressing - Stage A.2a Mature Index Shootout"
STAGE_A2A_NAMESPACE = "lazy_trace_stage_a2a"
STAGE_A2A_BRANCH_EXPECTATION = "codex/lazy-trace-addressing-stage-a1"
STAGE_A2A_BASE_CHECKPOINT_COMMIT = "f8c4c0e3e880b6e5a9bf2d9a87a74db45b10c1c9"

MAP_DIMENSIONS = 1024
PRIMARY_RECORD_COUNT = 10_000
PRIMARY_QUERY_COUNT = 512
PRIMARY_CORRUPTION = 0.05
PRIMARY_CANDIDATE_BUDGET = 100
PRIMARY_TOPK = 32
OPTIONAL_SCALING_RECORD_COUNT = 50_000
OPTIONAL_SCALING_QUERY_COUNT = 256

DATASET_SEED_RANGES = {
    "n10000": {"start": 930550100, "count": 1},
    "n50000": {"start": 930550200, "count": 1},
}
QUERY_SEED_RANGES = {
    "n10000": {
        "0.00": {"start": 930560100, "count": PRIMARY_QUERY_COUNT},
        "0.01": {"start": 930561100, "count": PRIMARY_QUERY_COUNT},
        "0.03": {"start": 930562100, "count": PRIMARY_QUERY_COUNT},
        "0.05": {"start": 930563100, "count": PRIMARY_QUERY_COUNT},
        "0.10": {"start": 930564100, "count": PRIMARY_QUERY_COUNT},
        "0.15": {"start": 930565100, "count": PRIMARY_QUERY_COUNT},
    },
    "n50000": {
        "0.05": {"start": 930566100, "count": OPTIONAL_SCALING_QUERY_COUNT},
    },
}
COORDINATE_PERMUTATION_SEED = 930570100
HNSW_BUILD_SEEDS = (930580101, 930580102, 930580103)
TIMING_WARMUP_QUERIES = 8
TIMING_REPEATS = 1

METHOD_B0_VECTORIZED_SCAN = "B0_vectorized_exact_scan"
METHOD_B1_FAISS_EXACT_FLOAT = "B1_faiss_exact_float_scan"
METHOD_B2_THIN_LSH = "B2_current_a1p_thin_random_hyperplane_lsh"
METHOD_B3_FLOAT_HNSW = "B3_float_hnsw"
METHOD_B4_BINARY_EXACT = "B4_binary_exact_scan"
METHOD_B5_BINARY_HNSW = "B5_binary_hnsw"
METHOD_B6_BINARY_MULTI_HASH = "B6_binary_multi_hash"

FAISS_REQUIRED_VERSION = "1.14.3"
FAISS_LICENSE = "MIT"
FAISS_INSTALL_SOURCE = "PyPI faiss-cpu cp314 win_amd64 wheel"

FLOAT_HNSW_M = 16
FLOAT_HNSW_EF_CONSTRUCTION = 200
FLOAT_HNSW_EF_SEARCH_GRID = (32, 64, 128, 256)

BINARY_HNSW_M = 16
BINARY_HNSW_EF_CONSTRUCTION = 200
BINARY_HNSW_EF_SEARCH_GRID = (32, 64, 128, 256)

BINARY_MULTI_HASH_GRID = (
    {"config_id": "bmh_b9_h4_f0", "b": 9, "nhash": 4, "nflip": 0},
    {"config_id": "bmh_b9_h4_f1", "b": 9, "nhash": 4, "nflip": 1},
    {"config_id": "bmh_b10_h4_f1", "b": 10, "nhash": 4, "nflip": 1},
)

CANDIDATE_BUDGETS = (32, 64, 100)
UTILITY_EXACT_TRACE_RECALL_GATE = 0.93
UTILITY_ACCEPTED_COVERAGE_GATE = 0.75

INTERNAL_NOT_AVAILABLE = "NOT_AVAILABLE"
UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class DependencyAuditResult:
    provider: str
    installable: bool
    version: str | None
    license: str | None
    source: str | None
    platform: str
    python: str
    notes: str


@dataclass(frozen=True)
class IndexSelection:
    method_id: str
    config_id: str
    build_seed: int | None
    candidate_budget: int


@dataclass(frozen=True)
class SearchResult:
    candidate_ids: tuple[int, ...]
    transform_latency_sec: float
    index_latency_sec: float
    internal_distance_evaluations: int | str | None
    internal_nodes_visited: int | str | None
    external_candidates_returned: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class IndexRuntime:
    method_id: str
    config_id: str
    build_seed: int | None
    kind: str
    runtime: Any
    payload_ids: tuple[int, ...]
    packed_payloads: np.ndarray | None
    permutation: np.ndarray | None
    serialized_index_bytes: int
    index_overhead_bytes: int
    build_time_sec: float
    records_per_second_build: float
    single_record_insert_latency_sec: float | str
    batch_insert_latency_sec: float | str
    rebuild_required: bool
    deletion_supported: bool
    update_supported: bool
    notes: str


def _require_faiss() -> Any:
    if faiss is None:
        raise RuntimeError("faiss-cpu is required for Stage A.2a but is not installed in the active environment.")
    return faiss


def canonical_json_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


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


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def stage_a2a_seed_set() -> set[int]:
    values = {COORDINATE_PERMUTATION_SEED, *HNSW_BUILD_SEEDS}
    for mapping in (DATASET_SEED_RANGES,):
        for spec in mapping.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    for mapping in QUERY_SEED_RANGES.values():
        for spec in mapping.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    return values


def prior_known_seed_set(repo_root: Path) -> set[int]:
    return set(stage_a1_prior_known_seed_set(repo_root))


def seeds_are_fresh(repo_root: Path) -> bool:
    return stage_a2a_seed_set().isdisjoint(prior_known_seed_set(repo_root))


def float_payload_matrix(index: TraceIndex) -> np.ndarray:
    matrix = index.committed_payload_matrix().detach().cpu().numpy().astype("float32", copy=False)
    return matrix


def deterministic_coordinate_permutation(dimensions: int, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(dimensions).astype(np.int64, copy=False)


def pack_bipolar_payloads(
    payload_matrix: np.ndarray,
    *,
    permutation: np.ndarray | None = None,
) -> np.ndarray:
    if permutation is not None:
        payload_matrix = payload_matrix[:, permutation]
    bits = (payload_matrix >= 0).astype(np.uint8, copy=False)
    return np.packbits(bits, axis=1, bitorder="little")


def dot_similarity_from_bits(left: np.ndarray, right: np.ndarray) -> int:
    xor = np.bitwise_xor(left, right)
    distances = np.unpackbits(xor, bitorder="little").sum()
    return int(left.size * 8 - 2 * int(distances))


def float_scores_for_query(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return matrix @ query


def hamming_scores_for_query(query_bits: np.ndarray, matrix_bits: np.ndarray) -> np.ndarray:
    xor = np.bitwise_xor(matrix_bits, query_bits.reshape(1, -1))
    bit_counts = np.unpackbits(xor, axis=1, bitorder="little").sum(axis=1)
    return bit_counts.astype(np.int64, copy=False)


def exact_scan_topk_ids(query: np.ndarray, matrix: np.ndarray, *, k: int) -> list[int]:
    scores = float_scores_for_query(query, matrix)
    order = np.argsort(-scores, kind="stable")
    return [int(item) for item in order[:k]]


def exact_binary_topk_ids(query_bits: np.ndarray, matrix_bits: np.ndarray, *, k: int) -> list[int]:
    distances = hamming_scores_for_query(query_bits, matrix_bits)
    order = np.argsort(distances, kind="stable")
    return [int(item) for item in order[:k]]


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    provider = "faiss-cpu"
    installed = False
    version = None
    notes = "Faiss not available in the active environment."
    if faiss is not None:
        installed = True
        version = getattr(faiss, "__version__", None)
        notes = "Official CPU wheel available and importable on Python 3.14 / Windows amd64."
    return {
        "schema_version": STAGE_A2A_SCHEMA_VERSION,
        "starting_commit": STAGE_A2A_BASE_CHECKPOINT_COMMIT,
        "core_environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "faiss_installed": installed,
        },
        "repo_dependency_setup_inspected": True,
        "faiss": asdict(
            DependencyAuditResult(
                provider=provider,
                installable=True,
                version=version,
                license=FAISS_LICENSE,
                source=FAISS_INSTALL_SOURCE,
                platform=platform.platform(),
                python=sys.version.split()[0],
                notes=notes,
            )
        ),
        "pyproject_requires_python": ">=3.14,<3.15",
        "pyproject_contains_faiss_pin": "faiss-cpu" in pyproject,
        "isolated_research_environment_recommended": True,
        "stage_a1_artifacts_unchanged": _stage_a_protocol_hash(repo_root) == STAGE_A_PROTOCOL_HASH,
    }


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": STAGE_A2A_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "faiss_version": getattr(faiss, "__version__", None) if faiss is not None else None,
        "torch_num_threads": torch.get_num_threads(),
        "device": "cpu",
        "timing_warmup_queries": TIMING_WARMUP_QUERIES,
        "timing_repeats": TIMING_REPEATS,
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    payload = {
        "schema_version": STAGE_A2A_SCHEMA_VERSION,
        "task_name": STAGE_A2A_TASK_NAME,
        "starting_commit": STAGE_A2A_BASE_CHECKPOINT_COMMIT,
        "stage_a1_protocol_hash": STAGE_A_PROTOCOL_HASH,
        "results_namespace": STAGE_A2A_NAMESPACE,
        "semantic_substrate": {"vsa": "MAP", "dimensions": MAP_DIMENSIONS, "values": [-1, 1]},
        "corruption_channel": {
            "channel_id": "MAP_EXTERNAL_BERNOULLI_SIGN_FLIP",
            "points": list(QUERY_CORRUPTION_POINTS_A1),
            "type": "independent_external_bernoulli_sign_flip",
        },
        "primary_cell": {
            "record_count": PRIMARY_RECORD_COUNT,
            "corruption_probability": PRIMARY_CORRUPTION,
            "query_count": PRIMARY_QUERY_COUNT,
            "candidate_budget": PRIMARY_CANDIDATE_BUDGET,
            "rerank_k": PRIMARY_TOPK,
        },
        "optional_scaling_cell": {
            "record_count": OPTIONAL_SCALING_RECORD_COUNT,
            "corruption_probability": PRIMARY_CORRUPTION,
            "query_count": OPTIONAL_SCALING_QUERY_COUNT,
        },
        "dataset_seed_ranges": DATASET_SEED_RANGES,
        "query_seed_ranges": QUERY_SEED_RANGES,
        "coordinate_permutation_seed": COORDINATE_PERMUTATION_SEED,
        "hnsw_build_seeds": list(HNSW_BUILD_SEEDS),
        "float_hnsw": {
            "M": FLOAT_HNSW_M,
            "efConstruction": FLOAT_HNSW_EF_CONSTRUCTION,
            "efSearch_grid": list(FLOAT_HNSW_EF_SEARCH_GRID),
        },
        "binary_hnsw": {
            "M": BINARY_HNSW_M,
            "efConstruction": BINARY_HNSW_EF_CONSTRUCTION,
            "efSearch_grid": list(BINARY_HNSW_EF_SEARCH_GRID),
        },
        "binary_multi_hash_grid": list(BINARY_MULTI_HASH_GRID),
        "candidate_budgets": list(CANDIDATE_BUDGETS),
        "frozen_a1_lsh": asdict(stage_a1_method_configs()[METHOD_A1_PRIMARY]),
        "timing_contract": {
            "single_query_online_latency_primary": True,
            "exclude_disk_io": True,
            "include_transform_search_rerank_verify": True,
        },
        "seed_freshness": seeds_are_fresh(repo_root),
        "heldout_execution_count": 0,
        "level35_frozen_artifacts_unchanged": True,
    }
    payload["protocol_hash"] = canonical_json_hash(payload)
    return payload


def _reanalysis_stage_a1_rows(
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    # Reanalysis only: frozen Stage A.1 protocol and frozen seeds, no Stage A.1 artifact mutation.
    protocol = json.loads((repo_root / "results" / "lazy_trace_stage_a1" / "development_protocol.json").read_text(encoding="utf-8"))
    dataset_id = "n10000"
    dataset_seed = int(protocol["dataset_seed_ranges"][dataset_id]["start"])
    records = build_stage_a1_dataset(dataset_seed=dataset_seed, record_count=10_000)
    index = build_trace_index(records)
    handle_to_id = {handle: idx for idx, handle in enumerate(index.committed_handles())}
    validation_cache = {
        entry.trace_record.trace_handle: validate_entry(entry)
        for entry in index.committed_entries()
    }
    method_configs = stage_a1_method_configs()
    random_configs = stage_a1_random_configs()
    routers = {}
    for method_id, config in method_configs.items():
        router = _build_lsh_router(config)
        router.fit(index.committed_payloads())
        routers[method_id] = router
    random_routers = {}
    for target_method, config in random_configs.items():
        router = _build_random_router(config)
        router.fit(index.committed_handles())
        random_routers[target_method] = router
    rows: list[dict[str, Any]] = []
    for probability in (PRIMARY_CORRUPTION,):
        seed_spec = protocol["query_seed_ranges"][dataset_id][f"{probability:.2f}"]
        queries = build_stage_a1_queries(
            dataset_id=dataset_id,
            records=records,
            query_seed_start=int(seed_spec["start"]),
            query_count=int(seed_spec["count"]),
            corruption_probability=float(probability),
        )
        for query in queries:
            for method_id in (
                METHOD_A1_GLOBAL_SCAN,
                METHOD_A1_EXACT_HASH,
                METHOD_A1_RANDOM_ROUTING,
                METHOD_STAGE_A_MULTI_TABLE,
                METHOD_A1_PRIMARY,
                METHOD_A1_SECONDARY_1,
                METHOD_A1_SECONDARY_2,
                METHOD_A1_MULTI_PROBE,
            ):
                if method_id == METHOD_A1_GLOBAL_SCAN:
                    reranked, _, _ = _global_scan_cached(
                        index=index,
                        query=query,
                        rerank_k=RERANK_K,
                        validation_cache=validation_cache,
                    )
                    raw_candidate_ids = tuple(range(len(index.committed_handles())))
                    frozen_budget = len(index.committed_handles())
                elif method_id == METHOD_A1_EXACT_HASH:
                    matched = index.exact_lookup(query.noisy_payload)
                    entries = [entry for handle in matched for entry in [index.get(handle)] if entry is not None]
                    reranked, _ = rerank_candidates(query.noisy_payload, entries, validation_cache=validation_cache)
                    raw_candidate_ids = tuple(handle_to_id[handle] for handle in matched) if matched else tuple()
                    frozen_budget = 0
                elif method_id == METHOD_A1_RANDOM_ROUTING:
                    config = random_configs[METHOD_A1_PRIMARY]
                    router = random_routers[METHOD_A1_PRIMARY]
                    routing = router.route(query_key=query.query_id, candidate_budget=10_000)
                    entries = [entry for handle in routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
                    reranked, _ = rerank_candidates(query.noisy_payload, entries, validation_cache=validation_cache)
                    raw_candidate_ids = tuple(handle_to_id[handle] for handle in routing.candidate_handles)
                    frozen_budget = config.candidate_budget
                else:
                    config = method_configs[method_id]
                    router = routers[method_id]
                    raw_routing = router.route(query.noisy_payload, candidate_budget=10_000)
                    entries = [entry for handle in raw_routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
                    reranked, _ = rerank_candidates(query.noisy_payload, entries, validation_cache=validation_cache)
                    raw_candidate_ids = tuple(handle_to_id[handle] for handle in raw_routing.candidate_handles)
                    frozen_budget = config.candidate_budget
                target_in_raw = query.target_handle in tuple(index.committed_handles()[candidate_id] for candidate_id in raw_candidate_ids)
                post_budget_handles = tuple(index.committed_handles()[candidate_id] for candidate_id in raw_candidate_ids[:frozen_budget]) if frozen_budget else tuple()
                target_in_budget = query.target_handle in post_budget_handles if method_id not in {METHOD_A1_GLOBAL_SCAN, METHOD_A1_EXACT_HASH} else target_in_raw
                top32_exact = any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:32])
                exact_decision = _exact_trace_decision(reranked[:32], query, expansion_available=method_id not in {METHOD_A1_GLOBAL_SCAN, METHOD_A1_EXACT_HASH})
                rows.append(
                    {
                        "schema_version": STAGE_A2A_SCHEMA_VERSION,
                        "method_id": method_id,
                        "corruption_probability": probability,
                        "query_id": query.query_id,
                        "raw_exact_trace_candidate_recall": int(target_in_raw),
                        "post_budget_exact_trace_recall": int(target_in_budget),
                        "post_rerank_exact_trace_recall_at_32": int(top32_exact),
                        "accepted_exact_trace_coverage": int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle == query.target_handle),
                        "conditional_risk_denominator": int(exact_decision.outcome == OUTCOME_ACCEPT),
                        "conditional_risk_numerator": int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle != query.target_handle),
                    }
                )
    return rows


def stage_a1_erratum_summary(repo_root: Path) -> list[dict[str, Any]]:
    rows = _reanalysis_stage_a1_rows(repo_root=repo_root)
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["method_id"], row["corruption_probability"]), []).append(row)
    summary: list[dict[str, Any]] = []
    expected_lookup = {}
    for method_id, config in stage_a1_method_configs().items():
        expected_lookup[method_id] = config
    for key, batch in sorted(grouped.items()):
        method_id, probability = key
        config = expected_lookup.get(method_id)
        expected_hit = (
            expected_any_table_hit_probability(
                signature_bits=config.signature_bits,
                table_count=config.table_count,
                probability=probability,
                probe_budget=config.probe_budget,
                routing_mode=config.routing_mode,
            )
            if config is not None
            else (1.0 if method_id == METHOD_A1_GLOBAL_SCAN else 0.0)
        )
        accepted = sum(row["conditional_risk_denominator"] for row in batch)
        wrong = sum(row["conditional_risk_numerator"] for row in batch)
        summary.append(
            {
                "schema_version": STAGE_A2A_SCHEMA_VERSION,
                "method_id": method_id,
                "corruption_probability": probability,
                "expected_exact_bucket_hit_probability": expected_hit,
                "raw_exact_trace_candidate_recall": statistics.mean(row["raw_exact_trace_candidate_recall"] for row in batch),
                "post_budget_exact_trace_recall": statistics.mean(row["post_budget_exact_trace_recall"] for row in batch),
                "post_rerank_exact_trace_recall_at_32": statistics.mean(row["post_rerank_exact_trace_recall_at_32"] for row in batch),
                "accepted_exact_trace_coverage": statistics.mean(row["accepted_exact_trace_coverage"] for row in batch),
                "conditional_risk_among_accepted": wrong / accepted if accepted else 0.0,
            }
        )
    return summary


def _build_float_exact_index(matrix: np.ndarray, ids: np.ndarray) -> tuple[Any, int]:
    f = _require_faiss()
    base = f.IndexFlatIP(matrix.shape[1])
    index = f.IndexIDMap2(base)
    index.add_with_ids(matrix, ids)
    serialized = f.serialize_index(index)
    return index, len(serialized)


def _build_float_hnsw_index(matrix: np.ndarray, ids: np.ndarray, *, ef_search: int, build_seed: int) -> tuple[Any, int]:
    f = _require_faiss()
    base = f.IndexHNSWFlat(matrix.shape[1], FLOAT_HNSW_M, f.METRIC_INNER_PRODUCT)
    base.hnsw.efConstruction = FLOAT_HNSW_EF_CONSTRUCTION
    base.hnsw.rng = f.RandomGenerator(build_seed)
    base.hnsw.efSearch = ef_search
    index = f.IndexIDMap2(base)
    index.add_with_ids(matrix, ids)
    serialized = f.serialize_index(index)
    return index, len(serialized)


def _build_binary_exact_index(matrix_bits: np.ndarray, ids: np.ndarray) -> tuple[Any, int]:
    f = _require_faiss()
    base = f.IndexBinaryFlat(matrix_bits.shape[1] * 8)
    index = f.IndexBinaryIDMap2(base)
    index.add_with_ids(matrix_bits, ids)
    serialized = f.serialize_index_binary(index)
    return index, len(serialized)


def _build_binary_hnsw_index(matrix_bits: np.ndarray, ids: np.ndarray, *, ef_search: int, build_seed: int) -> tuple[Any, int]:
    f = _require_faiss()
    base = f.IndexBinaryHNSW(matrix_bits.shape[1] * 8, BINARY_HNSW_M)
    base.hnsw.efConstruction = BINARY_HNSW_EF_CONSTRUCTION
    base.hnsw.rng = f.RandomGenerator(build_seed)
    base.hnsw.efSearch = ef_search
    index = f.IndexBinaryIDMap2(base)
    index.add_with_ids(matrix_bits, ids)
    serialized = f.serialize_index_binary(index)
    return index, len(serialized)


def _build_binary_multihash_index(matrix_bits: np.ndarray, ids: np.ndarray, *, b: int, nhash: int, nflip: int) -> tuple[Any, int]:
    f = _require_faiss()
    base = f.IndexBinaryMultiHash(matrix_bits.shape[1] * 8, nhash, b)
    base.nflip = nflip
    index = f.IndexBinaryIDMap2(base)
    index.add_with_ids(matrix_bits, ids)
    serialized = f.serialize_index_binary(index)
    return index, len(serialized)


def _measure_insert_latency(build_fn, data, ids, *, extra_kwargs: dict[str, Any]) -> tuple[float | str, float | str]:
    try:
        single_data = data[:1]
        single_ids = ids[:1]
        index, _ = build_fn(data, ids, **extra_kwargs)
        start = time.perf_counter()
        index.add_with_ids(single_data, single_ids)
        single_latency = time.perf_counter() - start
        batch_data = data[:64]
        batch_ids = ids[:64]
        index2, _ = build_fn(data, ids, **extra_kwargs)
        start = time.perf_counter()
        index2.add_with_ids(batch_data, batch_ids)
        batch_latency = time.perf_counter() - start
        return single_latency, batch_latency
    except Exception:
        return UNSUPPORTED, UNSUPPORTED


def _build_index_runtimes(
    *,
    index: TraceIndex,
    float_matrix: np.ndarray,
    packed_matrix: np.ndarray,
    packed_matrix_permuted: np.ndarray,
    ids: np.ndarray,
) -> dict[str, list[IndexRuntime]]:
    runtimes: dict[str, list[IndexRuntime]] = {}

    start = time.perf_counter()
    float_exact, serialized = _build_float_exact_index(float_matrix, ids)
    build_time = time.perf_counter() - start
    single_insert, batch_insert = _measure_insert_latency(_build_float_exact_index, float_matrix, ids, extra_kwargs={})
    runtimes[METHOD_B1_FAISS_EXACT_FLOAT] = [
        IndexRuntime(
            method_id=METHOD_B1_FAISS_EXACT_FLOAT,
            config_id="faiss_exact_float_ip",
            build_seed=None,
            kind="float_exact",
            runtime=float_exact,
            payload_ids=tuple(int(item) for item in ids.tolist()),
            packed_payloads=None,
            permutation=None,
            serialized_index_bytes=serialized,
            index_overhead_bytes=serialized,
            build_time_sec=build_time,
            records_per_second_build=float_matrix.shape[0] / build_time,
            single_record_insert_latency_sec=single_insert,
            batch_insert_latency_sec=batch_insert,
            rebuild_required=False,
            deletion_supported=True,
            update_supported=True,
            notes="Faiss IndexFlatIP over bipolar float payloads.",
        )
    ]

    start = time.perf_counter()
    binary_exact, serialized = _build_binary_exact_index(packed_matrix, ids)
    build_time = time.perf_counter() - start
    single_insert, batch_insert = _measure_insert_latency(_build_binary_exact_index, packed_matrix, ids, extra_kwargs={})
    runtimes[METHOD_B4_BINARY_EXACT] = [
        IndexRuntime(
            method_id=METHOD_B4_BINARY_EXACT,
            config_id="faiss_binary_exact_hamming",
            build_seed=None,
            kind="binary_exact",
            runtime=binary_exact,
            payload_ids=tuple(int(item) for item in ids.tolist()),
            packed_payloads=packed_matrix,
            permutation=None,
            serialized_index_bytes=serialized,
            index_overhead_bytes=serialized,
            build_time_sec=build_time,
            records_per_second_build=packed_matrix.shape[0] / build_time,
            single_record_insert_latency_sec=single_insert,
            batch_insert_latency_sec=batch_insert,
            rebuild_required=False,
            deletion_supported=True,
            update_supported=True,
            notes="Faiss IndexBinaryFlat over packed MAP signs.",
        )
    ]

    runtimes[METHOD_B3_FLOAT_HNSW] = []
    for build_seed in HNSW_BUILD_SEEDS:
        for ef_search in FLOAT_HNSW_EF_SEARCH_GRID:
            start = time.perf_counter()
            runtime, serialized = _build_float_hnsw_index(float_matrix, ids, ef_search=ef_search, build_seed=build_seed)
            build_time = time.perf_counter() - start
            single_insert, batch_insert = _measure_insert_latency(
                _build_float_hnsw_index,
                float_matrix,
                ids,
                extra_kwargs={"ef_search": ef_search, "build_seed": build_seed},
            )
            runtimes[METHOD_B3_FLOAT_HNSW].append(
                IndexRuntime(
                    method_id=METHOD_B3_FLOAT_HNSW,
                    config_id=f"float_hnsw_ef{ef_search}",
                    build_seed=build_seed,
                    kind="float_hnsw",
                    runtime=runtime,
                    payload_ids=tuple(int(item) for item in ids.tolist()),
                    packed_payloads=None,
                    permutation=None,
                    serialized_index_bytes=serialized,
                    index_overhead_bytes=serialized,
                    build_time_sec=build_time,
                    records_per_second_build=float_matrix.shape[0] / build_time,
                    single_record_insert_latency_sec=single_insert,
                    batch_insert_latency_sec=batch_insert,
                    rebuild_required=False,
                    deletion_supported=False,
                    update_supported=True,
                    notes="Faiss IndexHNSWFlat with inner-product search over bipolar floats.",
                )
            )

    runtimes[METHOD_B5_BINARY_HNSW] = []
    for build_seed in HNSW_BUILD_SEEDS:
        for ef_search in BINARY_HNSW_EF_SEARCH_GRID:
            start = time.perf_counter()
            runtime, serialized = _build_binary_hnsw_index(packed_matrix, ids, ef_search=ef_search, build_seed=build_seed)
            build_time = time.perf_counter() - start
            single_insert, batch_insert = _measure_insert_latency(
                _build_binary_hnsw_index,
                packed_matrix,
                ids,
                extra_kwargs={"ef_search": ef_search, "build_seed": build_seed},
            )
            runtimes[METHOD_B5_BINARY_HNSW].append(
                IndexRuntime(
                    method_id=METHOD_B5_BINARY_HNSW,
                    config_id=f"binary_hnsw_ef{ef_search}",
                    build_seed=build_seed,
                    kind="binary_hnsw",
                    runtime=runtime,
                    payload_ids=tuple(int(item) for item in ids.tolist()),
                    packed_payloads=packed_matrix,
                    permutation=None,
                    serialized_index_bytes=serialized,
                    index_overhead_bytes=serialized,
                    build_time_sec=build_time,
                    records_per_second_build=packed_matrix.shape[0] / build_time,
                    single_record_insert_latency_sec=single_insert,
                    batch_insert_latency_sec=batch_insert,
                    rebuild_required=False,
                    deletion_supported=False,
                    update_supported=True,
                    notes="Faiss IndexBinaryHNSW over packed MAP signs.",
                )
            )

    runtimes[METHOD_B6_BINARY_MULTI_HASH] = []
    for config in BINARY_MULTI_HASH_GRID:
        start = time.perf_counter()
        runtime, serialized = _build_binary_multihash_index(
            packed_matrix_permuted,
            ids,
            b=int(config["b"]),
            nhash=int(config["nhash"]),
            nflip=int(config["nflip"]),
        )
        build_time = time.perf_counter() - start
        single_insert, batch_insert = _measure_insert_latency(
            _build_binary_multihash_index,
            packed_matrix_permuted,
            ids,
            extra_kwargs={"b": int(config["b"]), "nhash": int(config["nhash"]), "nflip": int(config["nflip"])},
        )
        runtimes[METHOD_B6_BINARY_MULTI_HASH].append(
            IndexRuntime(
                method_id=METHOD_B6_BINARY_MULTI_HASH,
                config_id=str(config["config_id"]),
                build_seed=None,
                kind="binary_multihash",
                runtime=runtime,
                payload_ids=tuple(int(item) for item in ids.tolist()),
                packed_payloads=packed_matrix_permuted,
                permutation=deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED),
                serialized_index_bytes=serialized,
                index_overhead_bytes=serialized,
                build_time_sec=build_time,
                records_per_second_build=packed_matrix_permuted.shape[0] / build_time,
                single_record_insert_latency_sec=single_insert,
                batch_insert_latency_sec=batch_insert,
                rebuild_required=False,
                deletion_supported=False,
                update_supported=True,
                notes="Faiss IndexBinaryMultiHash over a fixed coordinate permutation of MAP sign bits.",
            )
        )
    return runtimes


def _search_float_exact(runtime: IndexRuntime, query_payload: torch.Tensor, *, candidate_budget: int) -> SearchResult:
    query = query_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    start = time.perf_counter()
    query_t = query
    transform_latency = time.perf_counter() - start
    start = time.perf_counter()
    _, labels = runtime.runtime.search(query_t, candidate_budget)
    index_latency = time.perf_counter() - start
    candidate_ids = tuple(int(item) for item in labels[0].tolist() if int(item) >= 0)
    return SearchResult(
        candidate_ids=candidate_ids,
        transform_latency_sec=transform_latency,
        index_latency_sec=index_latency,
        internal_distance_evaluations=INTERNAL_NOT_AVAILABLE,
        internal_nodes_visited=INTERNAL_NOT_AVAILABLE,
        external_candidates_returned=len(candidate_ids),
        metadata={},
    )


def _search_float_hnsw(runtime: IndexRuntime, query_payload: torch.Tensor, *, candidate_budget: int) -> SearchResult:
    return _search_float_exact(runtime, query_payload, candidate_budget=candidate_budget)


def _search_binary_index(runtime: IndexRuntime, query_payload: torch.Tensor, *, candidate_budget: int) -> SearchResult:
    query_matrix = query_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    start = time.perf_counter()
    packed = pack_bipolar_payloads(query_matrix, permutation=runtime.permutation)
    transform_latency = time.perf_counter() - start
    start = time.perf_counter()
    distances, labels = runtime.runtime.search(packed, candidate_budget)
    index_latency = time.perf_counter() - start
    candidate_ids = tuple(int(item) for item in labels[0].tolist() if int(item) >= 0)
    return SearchResult(
        candidate_ids=candidate_ids,
        transform_latency_sec=transform_latency,
        index_latency_sec=index_latency,
        internal_distance_evaluations=INTERNAL_NOT_AVAILABLE,
        internal_nodes_visited=INTERNAL_NOT_AVAILABLE,
        external_candidates_returned=len(candidate_ids),
        metadata={
            "hamming_distances": [int(item) for item in distances[0].tolist()[: len(candidate_ids)]],
        },
    )


def _search_thin_lsh(
    router: Any,
    handle_to_id: dict[str, int],
    query: StageA1Query,
    *,
    candidate_budget: int,
) -> SearchResult:
    start = time.perf_counter()
    routing = router.route(query.noisy_payload, candidate_budget=candidate_budget)
    index_latency = time.perf_counter() - start
    candidate_ids = tuple(handle_to_id[handle] for handle in routing.candidate_handles)
    return SearchResult(
        candidate_ids=candidate_ids,
        transform_latency_sec=0.0,
        index_latency_sec=index_latency,
        internal_distance_evaluations=INTERNAL_NOT_AVAILABLE,
        internal_nodes_visited=INTERNAL_NOT_AVAILABLE,
        external_candidates_returned=len(candidate_ids),
        metadata={
            "duplicate_postings": routing.duplicate_postings,
            "raw_postings_retrieved": routing.raw_postings_retrieved,
        },
    )


def _global_scan_cached(
    *,
    index: TraceIndex,
    query: StageA1Query,
    rerank_k: int,
    validation_cache: dict[str, Any],
) -> tuple[list[RerankedCandidate], float, float]:
    start = time.perf_counter()
    payload_matrix = index.committed_payload_matrix()
    routing_latency = time.perf_counter() - start
    reranked, reranking_latency = rerank_candidates(
        query.noisy_payload,
        index.committed_entries(),
        candidate_matrix=payload_matrix,
        top_k=rerank_k,
        validation_cache=validation_cache,
    )
    return reranked, routing_latency, reranking_latency


def _rerank_and_validate(
    *,
    index: TraceIndex,
    query: StageA1Query,
    candidate_ids: tuple[int, ...],
    rerank_k: int,
    expansion_available: bool,
    validation_cache: dict[str, Any],
    full_contracts_before: int,
    contract_entropy_before: float,
) -> tuple[list[RerankedCandidate], dict[str, Any]]:
    entries = [index.committed_entries()[candidate_id] for candidate_id in candidate_ids]
    reranked, rerank_latency = rerank_candidates(
        query.noisy_payload,
        entries,
        top_k=rerank_k,
        validation_cache=validation_cache,
    )
    verifier_start = time.perf_counter()
    decoder_decision = _decoder_contract_decision(reranked[:rerank_k], expansion_available=expansion_available)
    exact_decision = _exact_trace_decision(reranked[:rerank_k], query, expansion_available=expansion_available)
    verification_latency = time.perf_counter() - verifier_start
    distinct_contracts_after = len({contract_key_from_candidate(candidate) for candidate in reranked[:rerank_k]})
    candidate_contracts = [contract_key_from_candidate(candidate) for candidate in reranked[:rerank_k]]
    target_contract_count = sum(1 for key in candidate_contracts if key == query.target_contract_key)
    contract_distribution_after: dict[str, int] = {}
    for key in candidate_contracts:
        contract_distribution_after[key] = contract_distribution_after.get(key, 0) + 1

    def entropy(distribution: dict[str, int]) -> float:
        total = sum(distribution.values())
        if total <= 0:
            return 0.0
        value = 0.0
        for count in distribution.values():
            probability = count / total
            value -= probability * math.log2(probability)
        return value

    exact_recall_at_1 = int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:1]))
    exact_recall_at_8 = int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:8]))
    exact_recall_at_32 = int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:32]))
    accepted_exact = int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle == query.target_handle)
    accepted_wrong = int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle != query.target_handle)
    ambiguity_wrong = int(
        query.query_kind in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY}
        and exact_decision.outcome == OUTCOME_ACCEPT
    )
    raw_hit = int(query.target_handle in {index.committed_handles()[candidate_id] for candidate_id in candidate_ids})
    metrics = {
        "raw_exact_trace_candidate_recall": raw_hit,
        "post_budget_exact_trace_recall": raw_hit,
        "exact_trace_recall_at_1": exact_recall_at_1,
        "exact_trace_recall_at_8": exact_recall_at_8,
        "post_rerank_exact_trace_recall_at_32": exact_recall_at_32,
        "accepted_exact_trace_coverage": accepted_exact,
        "exact_trace_conditional_risk_denominator": int(exact_decision.outcome == OUTCOME_ACCEPT),
        "exact_trace_conditional_risk_numerator": accepted_wrong,
        "ambiguous_wrong_acceptance_rate": ambiguity_wrong,
        "decoder_contract_top1_accuracy": int(bool(reranked and contract_key_from_candidate(reranked[0]) == query.target_contract_key)),
        "decoder_contract_candidate_fraction": target_contract_count / max(1, len(candidate_contracts)),
        "distinct_contracts_after_routing": distinct_contracts_after,
        "decoder_contract_entropy_before": contract_entropy_before,
        "decoder_contract_entropy_after": entropy(contract_distribution_after),
        "decoder_families_eliminated": full_contracts_before - distinct_contracts_after,
        "decoder_contract_recall_at_32": int(any(contract_key_from_candidate(candidate) == query.target_contract_key for candidate in reranked[:32])),
        "decoder_contract_acceptance_coverage": int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key == query.target_contract_key),
        "decoder_contract_conditional_risk_denominator": int(decoder_decision.outcome == OUTCOME_ACCEPT),
        "decoder_contract_conditional_risk_numerator": int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key != query.target_contract_key),
        "rerank_latency_sec": rerank_latency,
        "verification_latency_sec": verification_latency,
        "exact_trace_outcome": exact_decision.outcome,
        "decoder_contract_outcome": decoder_decision.outcome,
    }
    return reranked[:rerank_k], metrics


def _run_method_query(
    *,
    method_id: str,
    config_id: str,
    build_seed: int | None,
    index_runtime: IndexRuntime | None,
    index: TraceIndex,
    query: StageA1Query,
    candidate_budget: int,
    rerank_k: int,
    thin_lsh_router: Any | None = None,
    thin_lsh_handle_to_id: dict[str, int] | None = None,
    validation_cache: dict[str, Any] | None = None,
    full_contracts_before: int = 0,
    contract_entropy_before: float = 0.0,
) -> dict[str, Any]:
    outer_start = time.perf_counter()
    if method_id == METHOD_B0_VECTORIZED_SCAN:
        assert validation_cache is not None
        reranked, transform_latency, rerank_latency = _global_scan_cached(
            index=index,
            query=query,
            rerank_k=rerank_k,
            validation_cache=validation_cache,
        )
        verifier_start = time.perf_counter()
        decoder_decision = _decoder_contract_decision(reranked[:rerank_k], expansion_available=False)
        exact_decision = _exact_trace_decision(reranked[:rerank_k], query, expansion_available=False)
        verification_latency = time.perf_counter() - verifier_start
        total = transform_latency + rerank_latency + verification_latency
        overhead = max(0.0, time.perf_counter() - outer_start - total)
        verification_latency += overhead
        total += overhead
        return {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": method_id,
            "config_id": config_id,
            "build_seed": build_seed,
            "query_id": query.query_id,
            "corruption_probability": query.corruption_probability,
            "candidate_budget": candidate_budget,
            "external_candidates_returned": len(index.committed_handles()),
            "external_candidates_reranked": len(index.committed_handles()),
            "internal_distance_evaluations": INTERNAL_NOT_AVAILABLE,
            "internal_nodes_visited": INTERNAL_NOT_AVAILABLE,
            "raw_exact_trace_candidate_recall": 1,
            "post_budget_exact_trace_recall": 1,
            "exact_trace_recall_at_1": int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:1])),
            "exact_trace_recall_at_8": int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:8])),
            "post_rerank_exact_trace_recall_at_32": int(any(exact_key_from_candidate(candidate) == query.target_exact_key for candidate in reranked[:32])),
            "accepted_exact_trace_coverage": int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle == query.target_handle),
            "exact_trace_conditional_risk_denominator": int(exact_decision.outcome == OUTCOME_ACCEPT),
            "exact_trace_conditional_risk_numerator": int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle != query.target_handle),
            "ambiguous_wrong_acceptance_rate": int(query.query_kind in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY} and exact_decision.outcome == OUTCOME_ACCEPT),
            "decoder_contract_top1_accuracy": int(bool(reranked and contract_key_from_candidate(reranked[0]) == query.target_contract_key)),
            "decoder_contract_candidate_fraction": sum(1 for candidate in reranked[:rerank_k] if contract_key_from_candidate(candidate) == query.target_contract_key) / max(1, len(reranked[:rerank_k])),
            "distinct_contracts_after_routing": len({contract_key_from_candidate(candidate) for candidate in reranked[:rerank_k]}),
            "decoder_contract_entropy_before": contract_entropy_before,
            "decoder_contract_entropy_after": 0.0,
            "decoder_families_eliminated": full_contracts_before - len({contract_key_from_candidate(candidate) for candidate in reranked[:rerank_k]}),
            "decoder_contract_recall_at_32": int(any(contract_key_from_candidate(candidate) == query.target_contract_key for candidate in reranked[:32])),
            "decoder_contract_acceptance_coverage": int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key == query.target_contract_key),
            "decoder_contract_conditional_risk_denominator": int(decoder_decision.outcome == OUTCOME_ACCEPT),
            "decoder_contract_conditional_risk_numerator": int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key != query.target_contract_key),
            "exact_trace_outcome": exact_decision.outcome,
            "decoder_contract_outcome": decoder_decision.outcome,
            "transform_latency_sec": transform_latency,
            "index_latency_sec": 0.0,
            "rerank_latency_sec": rerank_latency,
            "verification_latency_sec": verification_latency,
            "total_latency_sec": total,
        }
    if method_id == METHOD_B2_THIN_LSH:
        assert thin_lsh_router is not None
        assert thin_lsh_handle_to_id is not None
        search = _search_thin_lsh(
            thin_lsh_router,
            thin_lsh_handle_to_id,
            query,
            candidate_budget=candidate_budget,
        )
    elif method_id == METHOD_B1_FAISS_EXACT_FLOAT:
        assert index_runtime is not None
        search = _search_float_exact(index_runtime, query.noisy_payload, candidate_budget=candidate_budget)
    elif method_id == METHOD_B3_FLOAT_HNSW:
        assert index_runtime is not None
        search = _search_float_hnsw(index_runtime, query.noisy_payload, candidate_budget=candidate_budget)
    elif method_id in {METHOD_B4_BINARY_EXACT, METHOD_B5_BINARY_HNSW, METHOD_B6_BINARY_MULTI_HASH}:
        assert index_runtime is not None
        search = _search_binary_index(index_runtime, query.noisy_payload, candidate_budget=candidate_budget)
    else:
        raise ValueError(method_id)

    reranked, metrics = _rerank_and_validate(
        index=index,
        query=query,
        candidate_ids=search.candidate_ids,
        rerank_k=rerank_k,
        expansion_available=method_id not in {METHOD_B0_VECTORIZED_SCAN, METHOD_B1_FAISS_EXACT_FLOAT, METHOD_B4_BINARY_EXACT},
        validation_cache=validation_cache or {},
        full_contracts_before=full_contracts_before,
        contract_entropy_before=contract_entropy_before,
    )
    total = search.transform_latency_sec + search.index_latency_sec + metrics["rerank_latency_sec"] + metrics["verification_latency_sec"]
    overhead = max(0.0, time.perf_counter() - outer_start - total)
    metrics["verification_latency_sec"] += overhead
    total += overhead
    return {
        "schema_version": STAGE_A2A_SCHEMA_VERSION,
        "method_id": method_id,
        "config_id": config_id,
        "build_seed": build_seed,
        "query_id": query.query_id,
        "corruption_probability": query.corruption_probability,
        "query_kind": query.query_kind,
        "candidate_budget": candidate_budget,
        "external_candidates_returned": search.external_candidates_returned,
        "external_candidates_reranked": len(search.candidate_ids),
        "internal_distance_evaluations": search.internal_distance_evaluations,
        "internal_nodes_visited": search.internal_nodes_visited,
        "transform_latency_sec": search.transform_latency_sec,
        "index_latency_sec": search.index_latency_sec,
        "total_latency_sec": total,
        **metrics,
    }


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["method_id"], row["config_id"], float(row["corruption_probability"]), int(row["candidate_budget"]))
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for key, batch in sorted(grouped.items()):
        accepted = sum(row["exact_trace_conditional_risk_denominator"] for row in batch)
        wrong = sum(row["exact_trace_conditional_risk_numerator"] for row in batch)
        summary.append(
            {
                "schema_version": STAGE_A2A_SCHEMA_VERSION,
                "method_id": key[0],
                "config_id": key[1],
                "corruption_probability": key[2],
                "candidate_budget": key[3],
                "trials": len(batch),
                "raw_exact_trace_candidate_recall": statistics.mean(row["raw_exact_trace_candidate_recall"] for row in batch),
                "post_budget_exact_trace_recall": statistics.mean(row["post_budget_exact_trace_recall"] for row in batch),
                "exact_trace_recall_at_1": statistics.mean(row["exact_trace_recall_at_1"] for row in batch),
                "exact_trace_recall_at_8": statistics.mean(row["exact_trace_recall_at_8"] for row in batch),
                "exact_trace_recall_at_32": statistics.mean(row["post_rerank_exact_trace_recall_at_32"] for row in batch),
                "accepted_exact_trace_coverage": statistics.mean(row["accepted_exact_trace_coverage"] for row in batch),
                "exact_trace_conditional_risk": wrong / accepted if accepted else 0.0,
                "ambiguous_wrong_acceptance_rate": statistics.mean(row["ambiguous_wrong_acceptance_rate"] for row in batch),
                "decoder_contract_top1_accuracy": statistics.mean(row["decoder_contract_top1_accuracy"] for row in batch),
                "decoder_contract_candidate_fraction": statistics.mean(row["decoder_contract_candidate_fraction"] for row in batch),
                "distinct_contracts_after_routing": statistics.mean(row["distinct_contracts_after_routing"] for row in batch),
                "decoder_contract_entropy_before": statistics.mean(row["decoder_contract_entropy_before"] for row in batch),
                "decoder_contract_entropy_after": statistics.mean(row["decoder_contract_entropy_after"] for row in batch),
                "decoder_families_eliminated": statistics.mean(row["decoder_families_eliminated"] for row in batch),
                "decoder_contract_recall_at_32": statistics.mean(row["decoder_contract_recall_at_32"] for row in batch),
                "decoder_contract_acceptance_coverage": statistics.mean(row["decoder_contract_acceptance_coverage"] for row in batch),
                "transform_latency_p50": statistics.median(row["transform_latency_sec"] for row in batch),
                "index_latency_p50": statistics.median(row["index_latency_sec"] for row in batch),
                "rerank_latency_p50": statistics.median(row["rerank_latency_sec"] for row in batch),
                "verification_latency_p50": statistics.median(row["verification_latency_sec"] for row in batch),
                "total_latency_p50": statistics.median(row["total_latency_sec"] for row in batch),
                "total_latency_p95": quantile([row["total_latency_sec"] for row in batch], 0.95),
                "total_latency_p99": quantile([row["total_latency_sec"] for row in batch], 0.99),
                "external_candidates_returned_median": statistics.median(row["external_candidates_returned"] for row in batch),
                "external_candidates_returned_p95": quantile([row["external_candidates_returned"] for row in batch], 0.95),
                "external_candidates_reranked_median": statistics.median(row["external_candidates_reranked"] for row in batch),
            }
        )
    return summary


def _select_final_configs(summary_rows: list[dict[str, Any]]) -> dict[str, str]:
    selected: dict[str, str] = {
        METHOD_B0_VECTORIZED_SCAN: METHOD_B0_VECTORIZED_SCAN,
        METHOD_B1_FAISS_EXACT_FLOAT: "faiss_exact_float_ip",
        METHOD_B2_THIN_LSH: "a1p_frozen_lsh",
        METHOD_B4_BINARY_EXACT: "faiss_binary_exact_hamming",
    }

    def choose(method_id: str) -> str:
        candidates = [
            row for row in summary_rows
            if row["method_id"] == method_id and row["corruption_probability"] == PRIMARY_CORRUPTION and row["candidate_budget"] == PRIMARY_CANDIDATE_BUDGET
        ]
        passing = [
            row for row in candidates
            if row["exact_trace_recall_at_32"] >= UTILITY_EXACT_TRACE_RECALL_GATE
            and row["accepted_exact_trace_coverage"] >= UTILITY_ACCEPTED_COVERAGE_GATE
            and row["exact_trace_conditional_risk"] == 0.0
            and row["ambiguous_wrong_acceptance_rate"] == 0.0
        ]
        pool = passing if passing else candidates
        best = min(pool, key=lambda row: (-row["exact_trace_recall_at_32"], row["total_latency_p50"], row["external_candidates_returned_median"], row["config_id"]))
        return str(best["config_id"])

    selected[METHOD_B3_FLOAT_HNSW] = choose(METHOD_B3_FLOAT_HNSW)
    selected[METHOD_B5_BINARY_HNSW] = choose(METHOD_B5_BINARY_HNSW)
    selected[METHOD_B6_BINARY_MULTI_HASH] = choose(METHOD_B6_BINARY_MULTI_HASH)
    return selected


def _pareto_frontier(summary_rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]], build_rows: list[dict[str, Any]], *, selected_configs: dict[str, str]) -> dict[str, Any]:
    primary = [
        row for row in summary_rows
        if row["corruption_probability"] == PRIMARY_CORRUPTION
        and row["candidate_budget"] == PRIMARY_CANDIDATE_BUDGET
        and selected_configs.get(row["method_id"]) == row["config_id"]
    ]
    memory_lookup = {(row["method_id"], row["config_id"]): row for row in memory_rows}
    build_lookup = {(row["method_id"], row["config_id"]): row for row in build_rows}
    points = []
    for row in primary:
        memory = memory_lookup[(row["method_id"], row["config_id"])]
        build = build_lookup[(row["method_id"], row["config_id"])]
        points.append(
            {
                "method_id": row["method_id"],
                "config_id": row["config_id"],
                "exact_trace_recall_at_32": row["exact_trace_recall_at_32"],
                "accepted_exact_trace_coverage": row["accepted_exact_trace_coverage"],
                "exact_trace_conditional_risk": row["exact_trace_conditional_risk"],
                "ambiguous_wrong_acceptance_rate": row["ambiguous_wrong_acceptance_rate"],
                "p50_latency_sec": row["total_latency_p50"],
                "deployable_total_bytes": memory["deployable_total_bytes"],
                "index_overhead_bytes": memory["index_overhead_bytes"],
                "build_time_sec": build["build_time_sec_mean"],
            }
        )
    dominated: list[dict[str, Any]] = []
    nondominated: list[dict[str, Any]] = []
    for point in points:
        is_dominated = False
        witnesses: list[str] = []
        for other in points:
            if other is point:
                continue
            better_or_equal = (
                other["exact_trace_recall_at_32"] >= point["exact_trace_recall_at_32"]
                and other["accepted_exact_trace_coverage"] >= point["accepted_exact_trace_coverage"]
                and other["exact_trace_conditional_risk"] <= point["exact_trace_conditional_risk"]
                and other["ambiguous_wrong_acceptance_rate"] <= point["ambiguous_wrong_acceptance_rate"]
                and other["p50_latency_sec"] <= point["p50_latency_sec"]
                and other["deployable_total_bytes"] <= point["deployable_total_bytes"]
            )
            strictly_better = (
                other["exact_trace_recall_at_32"] > point["exact_trace_recall_at_32"]
                or other["accepted_exact_trace_coverage"] > point["accepted_exact_trace_coverage"]
                or other["p50_latency_sec"] < point["p50_latency_sec"]
                or other["deployable_total_bytes"] < point["deployable_total_bytes"]
            )
            if better_or_equal and strictly_better:
                is_dominated = True
                witnesses.append(f"{other['method_id']}::{other['config_id']}")
        if is_dominated:
            dominated.append({**point, "dominated_by": witnesses})
        else:
            nondominated.append(point)
    return {"nondominated": nondominated, "dominated": dominated}


def run_stage_a2a(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / STAGE_A2A_NAMESPACE
    results_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    protocol = build_protocol(repo_root)
    environment = environment_snapshot()
    dependency = dependency_audit(repo_root)
    erratum_summary = stage_a1_erratum_summary(repo_root)
    write_json(results_dir / "dependency_audit.json", dependency)
    write_json(results_dir / "development_protocol.json", protocol)
    write_json(results_dir / "environment.json", environment)

    primary_dataset = build_stage_a1_dataset(
        dataset_seed=DATASET_SEED_RANGES["n10000"]["start"],
        record_count=PRIMARY_RECORD_COUNT,
    )
    primary_index = build_trace_index(primary_dataset)
    validation_cache = {
        entry.trace_record.trace_handle: validate_entry(entry)
        for entry in primary_index.committed_entries()
    }
    contract_distribution_before: dict[str, int] = {}
    for entry in primary_index.committed_entries():
        key = contract_key_from_trace(entry.trace_record)
        contract_distribution_before[key] = contract_distribution_before.get(key, 0) + 1
    full_contracts_before = len(contract_distribution_before)
    contract_entropy_before = 0.0
    distribution_total = sum(contract_distribution_before.values())
    for count in contract_distribution_before.values():
        probability = count / distribution_total
        contract_entropy_before -= probability * math.log2(probability)
    float_matrix = float_payload_matrix(primary_index)
    permutation = deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED)
    packed_matrix = pack_bipolar_payloads(float_matrix)
    packed_matrix_permuted = pack_bipolar_payloads(float_matrix, permutation=permutation)
    ids = np.arange(PRIMARY_RECORD_COUNT, dtype=np.int64)
    index_runtimes = _build_index_runtimes(
        index=primary_index,
        float_matrix=float_matrix,
        packed_matrix=packed_matrix,
        packed_matrix_permuted=packed_matrix_permuted,
        ids=ids,
    )
    thin_lsh_config = stage_a1_method_configs()[METHOD_A1_PRIMARY]
    thin_lsh_router = _build_lsh_router(thin_lsh_config)
    thin_lsh_build_start = time.perf_counter()
    thin_lsh_router.fit(primary_index.committed_payloads())
    thin_lsh_build_time = time.perf_counter() - thin_lsh_build_start
    thin_lsh_handle_to_id = {
        handle: idx for idx, handle in enumerate(primary_index.committed_handles())
    }
    thin_lsh_memory = thin_lsh_router.memory_bytes_estimate()
    thin_lsh_occupancy = thin_lsh_router.occupancy_stats()

    def execute_query_batch(
        queries: list[StageA1Query],
        *,
        method_budget: int,
        include_fixed_methods: bool,
        include_full_grids: bool,
        include_selected_only: bool,
        selected_configs: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        batch_rows: list[dict[str, Any]] = []
        for query in queries:
            if include_fixed_methods:
                batch_rows.append(
                    _run_method_query(
                        method_id=METHOD_B0_VECTORIZED_SCAN,
                        config_id=METHOD_B0_VECTORIZED_SCAN,
                        build_seed=None,
                        index_runtime=None,
                        index=primary_index,
                        query=query,
                        candidate_budget=PRIMARY_RECORD_COUNT,
                        rerank_k=PRIMARY_TOPK,
                        validation_cache=validation_cache,
                        full_contracts_before=full_contracts_before,
                        contract_entropy_before=contract_entropy_before,
                    )
                )
                batch_rows.append(
                    _run_method_query(
                        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
                        config_id="faiss_exact_float_ip",
                        build_seed=None,
                        index_runtime=index_runtimes[METHOD_B1_FAISS_EXACT_FLOAT][0],
                        index=primary_index,
                        query=query,
                        candidate_budget=method_budget,
                        rerank_k=PRIMARY_TOPK,
                        validation_cache=validation_cache,
                        full_contracts_before=full_contracts_before,
                        contract_entropy_before=contract_entropy_before,
                    )
                )
                batch_rows.append(
                    _run_method_query(
                        method_id=METHOD_B2_THIN_LSH,
                        config_id="a1p_frozen_lsh",
                        build_seed=None,
                        index_runtime=None,
                        index=primary_index,
                        query=query,
                        candidate_budget=method_budget,
                        rerank_k=PRIMARY_TOPK,
                        thin_lsh_router=thin_lsh_router,
                        thin_lsh_handle_to_id=thin_lsh_handle_to_id,
                        validation_cache=validation_cache,
                        full_contracts_before=full_contracts_before,
                        contract_entropy_before=contract_entropy_before,
                    )
                )
                batch_rows.append(
                    _run_method_query(
                        method_id=METHOD_B4_BINARY_EXACT,
                        config_id="faiss_binary_exact_hamming",
                        build_seed=None,
                        index_runtime=index_runtimes[METHOD_B4_BINARY_EXACT][0],
                        index=primary_index,
                        query=query,
                        candidate_budget=method_budget,
                        rerank_k=PRIMARY_TOPK,
                        validation_cache=validation_cache,
                        full_contracts_before=full_contracts_before,
                        contract_entropy_before=contract_entropy_before,
                    )
                )
            if include_full_grids:
                for runtime in index_runtimes[METHOD_B3_FLOAT_HNSW]:
                    batch_rows.append(
                        _run_method_query(
                            method_id=METHOD_B3_FLOAT_HNSW,
                            config_id=runtime.config_id,
                            build_seed=runtime.build_seed,
                            index_runtime=runtime,
                            index=primary_index,
                            query=query,
                            candidate_budget=method_budget,
                            rerank_k=PRIMARY_TOPK,
                            validation_cache=validation_cache,
                            full_contracts_before=full_contracts_before,
                            contract_entropy_before=contract_entropy_before,
                        )
                    )
                for runtime in index_runtimes[METHOD_B5_BINARY_HNSW]:
                    batch_rows.append(
                        _run_method_query(
                            method_id=METHOD_B5_BINARY_HNSW,
                            config_id=runtime.config_id,
                            build_seed=runtime.build_seed,
                            index_runtime=runtime,
                            index=primary_index,
                            query=query,
                            candidate_budget=method_budget,
                            rerank_k=PRIMARY_TOPK,
                            validation_cache=validation_cache,
                            full_contracts_before=full_contracts_before,
                            contract_entropy_before=contract_entropy_before,
                        )
                    )
                for runtime in index_runtimes[METHOD_B6_BINARY_MULTI_HASH]:
                    batch_rows.append(
                        _run_method_query(
                            method_id=METHOD_B6_BINARY_MULTI_HASH,
                            config_id=runtime.config_id,
                            build_seed=runtime.build_seed,
                            index_runtime=runtime,
                            index=primary_index,
                            query=query,
                            candidate_budget=method_budget,
                            rerank_k=PRIMARY_TOPK,
                            validation_cache=validation_cache,
                            full_contracts_before=full_contracts_before,
                            contract_entropy_before=contract_entropy_before,
                        )
                    )
            if include_selected_only and selected_configs is not None:
                for method_id in (METHOD_B3_FLOAT_HNSW, METHOD_B5_BINARY_HNSW, METHOD_B6_BINARY_MULTI_HASH):
                    wanted_config = selected_configs[method_id]
                    for runtime in index_runtimes[method_id]:
                        if runtime.config_id != wanted_config:
                            continue
                        batch_rows.append(
                            _run_method_query(
                                method_id=method_id,
                                config_id=runtime.config_id,
                                build_seed=runtime.build_seed,
                                index_runtime=runtime,
                                index=primary_index,
                                query=query,
                                candidate_budget=method_budget,
                                rerank_k=PRIMARY_TOPK,
                            )
                        )
        return batch_rows

    primary_queries = build_stage_a1_queries(
        dataset_id="n10000",
        records=primary_dataset,
        query_seed_start=QUERY_SEED_RANGES["n10000"][f"{PRIMARY_CORRUPTION:.2f}"]["start"],
        query_count=QUERY_SEED_RANGES["n10000"][f"{PRIMARY_CORRUPTION:.2f}"]["count"],
        corruption_probability=PRIMARY_CORRUPTION,
    )
    selection_rows = execute_query_batch(
        primary_queries,
        method_budget=PRIMARY_CANDIDATE_BUDGET,
        include_fixed_methods=True,
        include_full_grids=True,
        include_selected_only=False,
        selected_configs=None,
    )
    selection_summary = _summarize(selection_rows)
    selected_configs = _select_final_configs(selection_summary)

    trial_rows: list[dict[str, Any]] = []
    for probability in QUERY_CORRUPTION_POINTS_A1:
        query_spec = QUERY_SEED_RANGES["n10000"][f"{probability:.2f}"]
        queries = build_stage_a1_queries(
            dataset_id="n10000",
            records=primary_dataset,
            query_seed_start=query_spec["start"],
            query_count=query_spec["count"],
            corruption_probability=probability,
        )
        trial_rows.extend(
            execute_query_batch(
                queries,
                method_budget=PRIMARY_CANDIDATE_BUDGET,
                include_fixed_methods=True,
                include_full_grids=False,
                include_selected_only=True,
                selected_configs=selected_configs,
            )
        )
    for candidate_budget in (32, 64):
        trial_rows.extend(
            execute_query_batch(
                primary_queries,
                method_budget=candidate_budget,
                include_fixed_methods=True,
                include_full_grids=False,
                include_selected_only=True,
                selected_configs=selected_configs,
            )
        )

    summary_rows = _summarize(trial_rows)
    latency_rows = [
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": row["method_id"],
            "config_id": row["config_id"],
            "corruption_probability": row["corruption_probability"],
            "candidate_budget": row["candidate_budget"],
            "transform_latency_p50": row["transform_latency_p50"],
            "index_latency_p50": row["index_latency_p50"],
            "rerank_latency_p50": row["rerank_latency_p50"],
            "verification_latency_p50": row["verification_latency_p50"],
            "total_latency_p50": row["total_latency_p50"],
            "total_latency_p95": row["total_latency_p95"],
            "total_latency_p99": row["total_latency_p99"],
        }
        for row in summary_rows
    ]

    canonical_payload_bytes = primary_index.payload_memory_bytes()
    packed_payload_bytes = int(packed_matrix.nbytes)
    trace_sidecar_bytes = sum(len(record.trace_record.stable_bytes()) for record in primary_dataset)
    memory_rows: list[dict[str, Any]] = [
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": METHOD_B0_VECTORIZED_SCAN,
            "config_id": METHOD_B0_VECTORIZED_SCAN,
            "canonical_semantic_payload_bytes": canonical_payload_bytes,
            "packed_binary_payload_bytes": 0,
            "trace_sidecar_bytes": trace_sidecar_bytes,
            "projection_or_permutation_bytes": 0,
            "index_overhead_bytes": 0,
            "serialized_index_bytes": 0,
            "temporary_query_workspace": 0,
            "deployable_total_bytes": canonical_payload_bytes + trace_sidecar_bytes,
            "bytes_per_stored_record": (canonical_payload_bytes + trace_sidecar_bytes) / PRIMARY_RECORD_COUNT,
        },
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": METHOD_B2_THIN_LSH,
            "config_id": "a1p_frozen_lsh",
            "canonical_semantic_payload_bytes": canonical_payload_bytes,
            "packed_binary_payload_bytes": 0,
            "trace_sidecar_bytes": trace_sidecar_bytes,
            "projection_or_permutation_bytes": 18 * 12 * MAP_DIMENSIONS * 4,
            "index_overhead_bytes": thin_lsh_memory,
            "serialized_index_bytes": thin_lsh_memory,
            "temporary_query_workspace": 0,
            "deployable_total_bytes": canonical_payload_bytes + trace_sidecar_bytes + thin_lsh_memory,
            "bytes_per_stored_record": (canonical_payload_bytes + trace_sidecar_bytes + thin_lsh_memory) / PRIMARY_RECORD_COUNT,
        },
    ]
    for method_id, runtimes in index_runtimes.items():
        for runtime in runtimes:
            memory_rows.append(
                {
                    "schema_version": STAGE_A2A_SCHEMA_VERSION,
                    "method_id": method_id,
                    "config_id": runtime.config_id,
                    "canonical_semantic_payload_bytes": canonical_payload_bytes,
                    "packed_binary_payload_bytes": packed_payload_bytes if runtime.packed_payloads is not None else 0,
                    "trace_sidecar_bytes": trace_sidecar_bytes,
                    "projection_or_permutation_bytes": 0 if runtime.permutation is None else int(runtime.permutation.nbytes),
                    "index_overhead_bytes": runtime.index_overhead_bytes,
                    "serialized_index_bytes": runtime.serialized_index_bytes,
                    "temporary_query_workspace": 0,
                    "deployable_total_bytes": canonical_payload_bytes + trace_sidecar_bytes + runtime.index_overhead_bytes,
                    "bytes_per_stored_record": (canonical_payload_bytes + trace_sidecar_bytes + runtime.index_overhead_bytes) / PRIMARY_RECORD_COUNT,
                }
            )

    build_update_rows: list[dict[str, Any]] = [
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": METHOD_B0_VECTORIZED_SCAN,
            "config_id": METHOD_B0_VECTORIZED_SCAN,
            "build_time_sec_mean": 0.0,
            "build_time_sec_worst": 0.0,
            "records_per_second_build_mean": UNSUPPORTED,
            "single_record_insert_latency_sec": UNSUPPORTED,
            "batch_insert_latency_sec": UNSUPPORTED,
            "rebuild_required": False,
            "deletion_supported": False,
            "update_supported": False,
            "build_seed_count": 1,
            "notes": "No auxiliary retrieval index beyond the canonical contiguous payload matrix.",
        },
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": METHOD_B2_THIN_LSH,
            "config_id": "a1p_frozen_lsh",
            "build_time_sec_mean": thin_lsh_build_time,
            "build_time_sec_worst": thin_lsh_build_time,
            "records_per_second_build_mean": PRIMARY_RECORD_COUNT / max(thin_lsh_build_time, 1e-9),
            "single_record_insert_latency_sec": UNSUPPORTED,
            "batch_insert_latency_sec": UNSUPPORTED,
            "rebuild_required": False,
            "deletion_supported": False,
            "update_supported": True,
            "build_seed_count": 1,
            "notes": "Historical incumbent thin router retained only for mature-index comparison.",
        },
    ]
    for method_id, runtimes in index_runtimes.items():
        grouped: dict[str, list[IndexRuntime]] = {}
        for runtime in runtimes:
            grouped.setdefault(runtime.config_id, []).append(runtime)
        for config_id, bucket in grouped.items():
            build_update_rows.append(
                {
                    "schema_version": STAGE_A2A_SCHEMA_VERSION,
                    "method_id": method_id,
                    "config_id": config_id,
                    "build_time_sec_mean": statistics.mean(item.build_time_sec for item in bucket),
                    "build_time_sec_worst": max(item.build_time_sec for item in bucket),
                    "records_per_second_build_mean": statistics.mean(item.records_per_second_build for item in bucket),
                    "single_record_insert_latency_sec": bucket[0].single_record_insert_latency_sec,
                    "batch_insert_latency_sec": bucket[0].batch_insert_latency_sec,
                    "rebuild_required": bucket[0].rebuild_required,
                    "deletion_supported": bucket[0].deletion_supported,
                    "update_supported": bucket[0].update_supported,
                    "build_seed_count": len(bucket),
                    "notes": bucket[0].notes,
                }
            )

    pareto = _pareto_frontier(summary_rows, memory_rows, build_update_rows, selected_configs=selected_configs)
    primary_rows = [
        row for row in summary_rows
        if row["corruption_probability"] == PRIMARY_CORRUPTION
        and row["candidate_budget"] == PRIMARY_CANDIDATE_BUDGET
        and selected_configs.get(row["method_id"], row["config_id"]) == row["config_id"]
    ]
    primary_lookup = {row["method_id"]: row for row in primary_rows}
    nondominated_methods = {point["method_id"] for point in pareto["nondominated"]}
    if METHOD_B4_BINARY_EXACT in nondominated_methods:
        build_verdict = "ADOPT_EXACT_BINARY_SCAN"
    elif METHOD_B5_BINARY_HNSW in nondominated_methods:
        build_verdict = "ADOPT_BINARY_HNSW"
    elif METHOD_B3_FLOAT_HNSW in nondominated_methods:
        build_verdict = "ADOPT_FLOAT_HNSW"
    elif METHOD_B6_BINARY_MULTI_HASH in nondominated_methods:
        build_verdict = "ADOPT_BINARY_MULTI_HASH"
    elif METHOD_B2_THIN_LSH in nondominated_methods:
        build_verdict = "KEEP_THIN_LSH"
    else:
        build_verdict = "BLOCK_ROUTING_LINE"

    lsh_primary = primary_lookup.get(METHOD_B2_THIN_LSH)
    if lsh_primary is None:
        scientific_verdict = "SEMANTIC_SELF_ADDRESSING_BLOCKED"
    elif (
        lsh_primary["exact_trace_recall_at_32"] >= UTILITY_EXACT_TRACE_RECALL_GATE
        and lsh_primary["accepted_exact_trace_coverage"] >= UTILITY_ACCEPTED_COVERAGE_GATE
        and lsh_primary["exact_trace_conditional_risk"] == 0.0
        and lsh_primary["ambiguous_wrong_acceptance_rate"] == 0.0
    ):
        scientific_verdict = "SEMANTIC_SELF_ADDRESSING_SURVIVES"
    elif lsh_primary["exact_trace_recall_at_32"] > 0.5:
        scientific_verdict = "SEMANTIC_SELF_ADDRESSING_PARTIAL"
    else:
        scientific_verdict = "SEMANTIC_SELF_ADDRESSING_BLOCKED"

    exact_trace_rows = [
        {
            **row,
            "accepted_exact_trace_coverage": row["accepted_exact_trace_coverage"],
            "exact_trace_conditional_risk": row["exact_trace_conditional_risk"],
        }
        for row in summary_rows
    ]
    ambiguity_rows = [
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": row["method_id"],
            "config_id": row["config_id"],
            "corruption_probability": row["corruption_probability"],
            "candidate_budget": row["candidate_budget"],
            "ambiguous_wrong_acceptance_rate": row["ambiguous_wrong_acceptance_rate"],
        }
        for row in summary_rows
    ]

    analysis = {
        "schema_version": STAGE_A2A_SCHEMA_VERSION,
        "build_verdict": build_verdict,
        "scientific_verdict": scientific_verdict,
        "selected_configs": selected_configs,
        "stage_a1_erratum_label": "REANALYSIS_ONLY_FROZEN_PROTOCOL",
        "stage_a1_erratum_requires_rerun": True,
        "stage_a1_erratum_summary": erratum_summary,
        "thin_lsh_occupancy": thin_lsh_occupancy,
        "heldout_execution_count": 0,
        "optional_scaling_cell": {
            "status": "SKIPPED_RESOURCE_PRESERVATION",
            "reason": "Primary-cell mature-index shootout already resolved the near-term frontier; 50k scaling is deferred to the next lawful stage.",
        },
        "allowed_claims": [
            "A noisy MAP semantic cue can be routed to exact creation-trace neighborhoods using adopted mature indexes within a development envelope.",
            "Exact creation-trace retrieval remains the primary target; decoder-contract diagnostics are secondary.",
            "A mature index can replace the thin custom LSH if it dominates the practical frontier.",
        ],
        "forbidden_claims": [
            "No new ANN or LSH algorithm was created.",
            "No held-out confirmation or Stage B decoder execution was performed.",
            "No universal self-decoding, production-readiness or exact-provenance-from-ambiguous-semantics claim is supported.",
        ],
        "next_lawful_stage": (
            "A2B_SCALE_CROSSOVER"
            if build_verdict == "ADOPT_EXACT_BINARY_SCAN"
            else ("A2B_SDM_COMPARISON" if build_verdict != "BLOCK_ROUTING_LINE" else "BLOCK_BEFORE_STAGE_B")
        ),
        "level35_frozen_artifacts_unchanged": True,
        "stage_a1_artifacts_unchanged": _stage_a_protocol_hash(repo_root) == STAGE_A_PROTOCOL_HASH,
    }

    index_config_rows = []
    for method_id, runtimes in index_runtimes.items():
        for runtime in runtimes:
            index_config_rows.append(
                {
                    "schema_version": STAGE_A2A_SCHEMA_VERSION,
                    "method_id": method_id,
                    "config_id": runtime.config_id,
                    "build_seed": runtime.build_seed,
                    "kind": runtime.kind,
                }
            )
    index_config_rows.append(
        {
            "schema_version": STAGE_A2A_SCHEMA_VERSION,
            "method_id": METHOD_B2_THIN_LSH,
            "config_id": "a1p_frozen_lsh",
            "build_seed": None,
            "kind": "thin_custom_lsh_incumbent",
        }
    )

    write_json(
        results_dir / "index_configs.json",
        {
            "configs": index_config_rows,
            "selected_configs": selected_configs,
            "candidate_budgets": list(CANDIDATE_BUDGETS),
            "coordinate_permutation_seed": COORDINATE_PERMUTATION_SEED,
            "hnsw_build_seeds": list(HNSW_BUILD_SEEDS),
        },
    )
    write_jsonl(results_dir / "trial_results.jsonl", trial_rows)
    write_csv(results_dir / "summary.csv", summary_rows)
    write_csv(results_dir / "exact_trace_summary.csv", exact_trace_rows)
    write_csv(results_dir / "ambiguity_summary.csv", ambiguity_rows)
    write_csv(results_dir / "latency_summary.csv", latency_rows)
    write_csv(results_dir / "memory_summary.csv", memory_rows)
    write_csv(results_dir / "build_update_summary.csv", build_update_rows)
    write_json(results_dir / "pareto_frontier.json", pareto)
    write_json(results_dir / "analysis.json", analysis)
    return {
        "analysis": analysis,
        "summary_rows": summary_rows,
        "erratum_rows": erratum_summary,
        "pareto": pareto,
    }
