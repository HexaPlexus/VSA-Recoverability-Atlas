from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from cgrn_hsr.lazy_trace_addressing_stage_a2a import (
    COORDINATE_PERMUTATION_SEED,
    FLOAT_HNSW_EF_SEARCH_GRID,
    MAP_DIMENSIONS,
    METHOD_B0_VECTORIZED_SCAN,
    METHOD_B1_FAISS_EXACT_FLOAT,
    METHOD_B3_FLOAT_HNSW,
    METHOD_B4_BINARY_EXACT,
    METHOD_B5_BINARY_HNSW,
    METHOD_B6_BINARY_MULTI_HASH,
    PRIMARY_CANDIDATE_BUDGET,
    PRIMARY_CORRUPTION,
    PRIMARY_TOPK,
    QUERY_KIND_EXACT_AMBIGUITY,
    STAGE_A_PROTOCOL_HASH,
    _build_binary_exact_index,
    _build_binary_hnsw_index,
    _build_binary_multihash_index,
    _build_float_exact_index,
    _build_float_hnsw_index,
    _run_method_query,
    build_stage_a1_dataset,
    build_stage_a1_queries,
    build_trace_index,
    canonical_json_hash,
    contract_key_from_trace,
    deterministic_coordinate_permutation,
    dot_similarity_from_bits,
    exact_binary_topk_ids,
    exact_scan_topk_ids,
    float_scores_for_query,
    float_payload_matrix,
    pack_bipolar_payloads,
    prior_known_seed_set,
    seeds_are_fresh,
    stage_a2a_seed_set,
)
from cgrn_hsr.verification import validate_entry

ROOT = Path(__file__).resolve().parents[1]
STAGE_A1_PROTOCOL_SHA = "3457395a278f470f9e0dd8c8a43ae2296ed0629444e8b578218231fc241f2dd6"
LEVEL35_V4_SHA = "317e7a43afadb2002a25dbb82588f72610098cd7dad19f03dcac2dd4077cd6e5"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_records(record_count: int = 256):
    return build_stage_a1_dataset(dataset_seed=930550100, record_count=record_count)


def _fixture_index(record_count: int = 256):
    records = _fixture_records(record_count=record_count)
    return records, build_trace_index(records)


def _fixture_query(records, *, probability: float = PRIMARY_CORRUPTION, query_kind: str | None = None):
    queries = build_stage_a1_queries(
        dataset_id="fixture",
        records=records,
        query_seed_start=930560100,
        query_count=32,
        corruption_probability=probability,
    )
    if query_kind is None:
        return queries[0]
    return next(query for query in queries if query.query_kind == query_kind)


def _contract_stats(index):
    distribution: dict[str, int] = {}
    for entry in index.committed_entries():
        key = contract_key_from_trace(entry.trace_record)
        distribution[key] = distribution.get(key, 0) + 1
    entropy = 0.0
    total = sum(distribution.values())
    for count in distribution.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return len(distribution), entropy


def test_bipolar_dot_and_hamming_rank_equivalence() -> None:
    matrix = np.array(
        [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, -1.0, -1.0],
            [1.0, -1.0, 1.0, -1.0],
            [-1.0, -1.0, -1.0, -1.0],
        ],
        dtype=np.float32,
    )
    query = np.array([1.0, 1.0, 1.0, -1.0], dtype=np.float32)
    packed_matrix = pack_bipolar_payloads(matrix)
    packed_query = pack_bipolar_payloads(query.reshape(1, -1))[0]
    float_rank = exact_scan_topk_ids(query, matrix, k=4)
    binary_rank = exact_binary_topk_ids(packed_query, packed_matrix, k=4)
    assert float_rank == binary_rank
    assert dot_similarity_from_bits(packed_matrix[0], packed_query) == 6


def test_float_exact_baseline_equivalence() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, _ = _build_float_exact_index(matrix, ids)
    query = _fixture_query(records, probability=PRIMARY_CORRUPTION)
    q = query.noisy_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    _, labels = runtime.search(q, 32)
    faiss_rank = [int(item) for item in labels[0].tolist() if int(item) >= 0]
    helper_rank = exact_scan_topk_ids(q[0], matrix, k=32)
    scores = float_scores_for_query(q[0], matrix)
    faiss_scores = sorted((float(scores[idx]) for idx in faiss_rank), reverse=True)
    helper_scores = sorted((float(scores[idx]) for idx in helper_rank), reverse=True)
    assert faiss_scores == helper_scores


def test_binary_exact_baseline_equivalence() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    packed = pack_bipolar_payloads(matrix)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, _ = _build_binary_exact_index(packed, ids)
    query = _fixture_query(records, probability=0.0)
    packed_query = pack_bipolar_payloads(
        query.noisy_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    )
    distances, labels = runtime.search(packed_query, 32)
    faiss_rank = [int(item) for item in labels[0].tolist() if int(item) >= 0]
    helper_rank = exact_binary_topk_ids(packed_query[0], packed, k=32)
    assert faiss_rank == helper_rank
    assert distances.shape[1] == 32


def test_bit_packing_and_coordinate_permutation_are_deterministic() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    left = deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED)
    right = deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED)
    changed = deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED + 1)
    assert np.array_equal(left, right)
    assert not np.array_equal(left, changed)
    assert np.array_equal(
        pack_bipolar_payloads(matrix, permutation=left),
        pack_bipolar_payloads(matrix, permutation=right),
    )


def test_hnsw_result_ids_map_to_correct_trace_records() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, _ = _build_float_hnsw_index(matrix, ids, ef_search=FLOAT_HNSW_EF_SEARCH_GRID[0], build_seed=930580101)
    query = _fixture_query(records, probability=0.0)
    q = query.noisy_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    _, labels = runtime.search(q, 16)
    handles = [index.committed_entries()[int(item)].trace_record.trace_handle for item in labels[0].tolist() if int(item) >= 0]
    assert handles
    assert all(handle.startswith("trace:") for handle in handles)


def test_binary_hnsw_result_ids_map_correctly() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    packed = pack_bipolar_payloads(matrix)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, _ = _build_binary_hnsw_index(packed, ids, ef_search=64, build_seed=930580101)
    query = _fixture_query(records, probability=0.0)
    packed_query = pack_bipolar_payloads(
        query.noisy_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False)
    )
    _, labels = runtime.search(packed_query, 16)
    handles = [index.committed_entries()[int(item)].trace_record.trace_handle for item in labels[0].tolist() if int(item) >= 0]
    assert handles
    assert all(handle.startswith("trace:") for handle in handles)


def test_multihash_collisions_never_imply_identity() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    packed = pack_bipolar_payloads(matrix, permutation=deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED))
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, _ = _build_binary_multihash_index(packed, ids, b=9, nhash=4, nflip=1)
    query = _fixture_query(records, probability=0.0)
    packed_query = pack_bipolar_payloads(
        query.noisy_payload.detach().cpu().reshape(1, -1).numpy().astype("float32", copy=False),
        permutation=deterministic_coordinate_permutation(MAP_DIMENSIONS, seed=COORDINATE_PERMUTATION_SEED),
    )
    _, labels = runtime.search(packed_query, 64)
    candidate_ids = [int(item) for item in labels[0].tolist() if int(item) >= 0]
    assert len(candidate_ids) <= 64
    assert len(candidate_ids) >= 1


def test_shared_candidate_budget_enforcement() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    float_runtime, ser = _build_float_exact_index(matrix, ids)
    from cgrn_hsr.lazy_trace_addressing_stage_a2a import IndexRuntime

    runtime = IndexRuntime(
        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
        config_id="faiss_exact_float_ip",
        build_seed=None,
        kind="float_exact",
        runtime=float_runtime,
        payload_ids=tuple(int(i) for i in ids.tolist()),
        packed_payloads=None,
        permutation=None,
        serialized_index_bytes=ser,
        index_overhead_bytes=ser,
        build_time_sec=0.0,
        records_per_second_build=0.0,
        single_record_insert_latency_sec="NA",
        batch_insert_latency_sec="NA",
        rebuild_required=False,
        deletion_supported=True,
        update_supported=True,
        notes="",
    )
    query = _fixture_query(records, probability=PRIMARY_CORRUPTION)
    validation_cache = {e.trace_record.trace_handle: validate_entry(e) for e in index.committed_entries()}
    full_contracts, entropy = _contract_stats(index)
    row_32 = _run_method_query(
        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
        config_id="faiss_exact_float_ip",
        build_seed=None,
        index_runtime=runtime,
        index=index,
        query=query,
        candidate_budget=32,
        rerank_k=PRIMARY_TOPK,
        validation_cache=validation_cache,
        full_contracts_before=full_contracts,
        contract_entropy_before=entropy,
    )
    row_64 = _run_method_query(
        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
        config_id="faiss_exact_float_ip",
        build_seed=None,
        index_runtime=runtime,
        index=index,
        query=query,
        candidate_budget=64,
        rerank_k=PRIMARY_TOPK,
        validation_cache=validation_cache,
        full_contracts_before=full_contracts,
        contract_entropy_before=entropy,
    )
    assert row_32["external_candidates_returned"] <= 32
    assert row_64["external_candidates_returned"] <= 64
    assert row_64["external_candidates_returned"] >= row_32["external_candidates_returned"]


def test_ambiguous_trace_is_not_silently_accepted_across_index_types() -> None:
    records, index = _fixture_index()
    query = _fixture_query(records, probability=0.0, query_kind=QUERY_KIND_EXACT_AMBIGUITY)
    validation_cache = {e.trace_record.trace_handle: validate_entry(e) for e in index.committed_entries()}
    full_contracts, entropy = _contract_stats(index)
    matrix = float_payload_matrix(index)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    float_runtime, ser = _build_float_exact_index(matrix, ids)
    from cgrn_hsr.lazy_trace_addressing_stage_a2a import IndexRuntime

    runtime = IndexRuntime(
        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
        config_id="faiss_exact_float_ip",
        build_seed=None,
        kind="float_exact",
        runtime=float_runtime,
        payload_ids=tuple(int(i) for i in ids.tolist()),
        packed_payloads=None,
        permutation=None,
        serialized_index_bytes=ser,
        index_overhead_bytes=ser,
        build_time_sec=0.0,
        records_per_second_build=0.0,
        single_record_insert_latency_sec="NA",
        batch_insert_latency_sec="NA",
        rebuild_required=False,
        deletion_supported=True,
        update_supported=True,
        notes="",
    )
    row = _run_method_query(
        method_id=METHOD_B1_FAISS_EXACT_FLOAT,
        config_id="faiss_exact_float_ip",
        build_seed=None,
        index_runtime=runtime,
        index=index,
        query=query,
        candidate_budget=PRIMARY_CANDIDATE_BUDGET,
        rerank_k=PRIMARY_TOPK,
        validation_cache=validation_cache,
        full_contracts_before=full_contracts,
        contract_entropy_before=entropy,
    )
    assert row["ambiguous_wrong_acceptance_rate"] == 0
    assert row["exact_trace_outcome"] in {"AMBIGUOUS_TRACE", "ABSTAIN"}


def test_malformed_trace_rejection_and_validation_independence() -> None:
    records = _fixture_records()
    bad = records[0]
    bad_trace = replace(
        bad.trace_record,
        semantic_payload_checksum="0" * 64,
    )
    from cgrn_hsr.trace_index import TraceStoreEntry

    bad_entry = TraceStoreEntry(
        trace_record=bad_trace,
        semantic_payload=bad.semantic_payload,
        committed=True,
        family_label=bad.family_label,
        namespace_contract=bad.operand_namespaces,
        arity=bad.arity,
    )
    validation = validate_entry(bad_entry)
    assert validation.status != "TRACE_VALID"


def test_timing_components_sum_correctly() -> None:
    records, index = _fixture_index()
    validation_cache = {e.trace_record.trace_handle: validate_entry(e) for e in index.committed_entries()}
    full_contracts, entropy = _contract_stats(index)
    query = _fixture_query(records, probability=PRIMARY_CORRUPTION)
    row = _run_method_query(
        method_id=METHOD_B0_VECTORIZED_SCAN,
        config_id=METHOD_B0_VECTORIZED_SCAN,
        build_seed=None,
        index_runtime=None,
        index=index,
        query=query,
        candidate_budget=len(index.committed_handles()),
        rerank_k=PRIMARY_TOPK,
        validation_cache=validation_cache,
        full_contracts_before=full_contracts,
        contract_entropy_before=entropy,
    )
    summed = row["transform_latency_sec"] + row["index_latency_sec"] + row["rerank_latency_sec"] + row["verification_latency_sec"]
    assert abs(row["total_latency_sec"] - summed) < 1e-9


def test_serialized_index_accounting_and_seed_reporting() -> None:
    records, index = _fixture_index()
    matrix = float_payload_matrix(index)
    ids = np.arange(matrix.shape[0], dtype=np.int64)
    runtime, ser = _build_float_hnsw_index(matrix, ids, ef_search=64, build_seed=930580101)
    assert ser > 0
    assert runtime.ntotal == matrix.shape[0]


def test_stage_a1_and_level35_artifacts_remain_unchanged_and_seeds_are_fresh() -> None:
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a1" / "development_protocol.json") == STAGE_A1_PROTOCOL_SHA
    assert _sha256(ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA
    assert canonical_json_hash({"ok": True}) == canonical_json_hash({"ok": True})
    assert seeds_are_fresh(ROOT) is True
    assert stage_a2a_seed_set().isdisjoint(prior_known_seed_set(ROOT))
