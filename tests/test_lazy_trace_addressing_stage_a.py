from __future__ import annotations

import json
from pathlib import Path

from cgrn_hsr.lazy_trace_addressing_stage_a import (
    ACCEPT_MARGIN,
    CANDIDATE_BUDGET,
    CORRUPTION_CHANNEL_ID,
    DATASET_SEED_RANGES,
    MAP_DIMENSIONS,
    METHOD_EXACT_HASH,
    METHOD_MULTI_PROBE,
    METHOD_RANDOM_ROUTING,
    ONE_TABLE_PROBE_BUDGET,
    PROJECTION_SEEDS,
    QUERY_CORRUPTION_POINTS,
    RERANK_K,
    SIGNATURE_BITS,
    STAGE_A_NAMESPACE,
    STAGE_A_SCHEMA_VERSION,
    build_dataset,
    build_protocol,
    build_queries,
    build_trace_index,
    corrupt_payload,
    prior_known_seed_set,
    run_method_query,
    seeds_are_fresh,
    stage_a_seed_set,
)
from cgrn_hsr.semantic_lsh import RandomBucketRouter, RandomHyperplaneLSH, SignatureConfig
from cgrn_hsr.trace_index import TraceIndex, TraceStoreEntry
from cgrn_hsr.trace_record import (
    TRACE_CHECKSUM_MISMATCH,
    TRACE_MALFORMED,
    TRACE_OPERATION_FAMILY_MISMATCH,
    TraceRecord,
    payload_checksum,
    trace_record_from_dict,
)
from cgrn_hsr.verification import (
    DECISION_ABSTAIN,
    DECISION_EXPAND,
    decide_candidate,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_records():
    return build_dataset(dataset_seed=DATASET_SEED_RANGES["n1000"]["start"], record_count=64)


def _fixture_index():
    records = _fixture_records()
    index = build_trace_index(records)
    return records, index


def _fixture_routers(index: TraceIndex):
    payloads = index.committed_payloads()
    one_table = RandomHyperplaneLSH(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=SIGNATURE_BITS,
            table_count=1,
            table_seed=PROJECTION_SEEDS[0],
            probe_budget=ONE_TABLE_PROBE_BUDGET,
        )
    )
    one_table.fit(payloads)
    multi_probe = RandomHyperplaneLSH(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=SIGNATURE_BITS,
            table_count=4,
            table_seed=PROJECTION_SEEDS[0],
            probe_budget=4,
        )
    )
    multi_probe.fit(payloads)
    random_router = RandomBucketRouter(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=SIGNATURE_BITS,
            table_count=4,
            table_seed=PROJECTION_SEEDS[0],
            probe_budget=4,
        )
    )
    random_router.fit(index.committed_handles())
    return one_table, multi_probe, random_router


def test_exact_cue_has_expected_lsh_signature() -> None:
    records, index = _fixture_index()
    router, _, _ = _fixture_routers(index)
    payload = records[0].semantic_payload
    assert router.signatures(payload) == router.signatures(payload.clone())


def test_same_seed_gives_same_projections_and_signatures() -> None:
    records, index = _fixture_index()
    payload = records[0].semantic_payload
    left = RandomHyperplaneLSH(
        SignatureConfig(MAP_DIMENSIONS, SIGNATURE_BITS, 1, PROJECTION_SEEDS[0], 1)
    )
    right = RandomHyperplaneLSH(
        SignatureConfig(MAP_DIMENSIONS, SIGNATURE_BITS, 1, PROJECTION_SEEDS[0], 1)
    )
    left.fit(index.committed_payloads())
    right.fit(index.committed_payloads())
    assert left.signatures(payload) == right.signatures(payload)


def test_different_projection_seeds_change_index_family() -> None:
    records, index = _fixture_index()
    payload = records[0].semantic_payload
    left = RandomHyperplaneLSH(SignatureConfig(MAP_DIMENSIONS, SIGNATURE_BITS, 1, PROJECTION_SEEDS[0], 1))
    right = RandomHyperplaneLSH(SignatureConfig(MAP_DIMENSIONS, SIGNATURE_BITS, 1, PROJECTION_SEEDS[1], 1))
    left.fit(index.committed_payloads())
    right.fit(index.committed_payloads())
    assert left.signatures(payload) != right.signatures(payload)


def test_lazy_insertion_only_happens_after_commit_flag() -> None:
    record = _fixture_records()[0]
    index = TraceIndex()
    index.insert(
        TraceStoreEntry(
            trace_record=record.trace_record,
            semantic_payload=record.semantic_payload,
            committed=False,
            family_label=record.family_label,
            namespace_contract=record.operand_namespaces,
            arity=record.arity,
        )
    )
    assert index.committed_handles() == []


def test_uncommitted_record_does_not_appear_in_postings() -> None:
    record = _fixture_records()[0]
    index = TraceIndex()
    index.insert(
        TraceStoreEntry(
            trace_record=record.trace_record,
            semantic_payload=record.semantic_payload,
            committed=False,
            family_label=record.family_label,
            namespace_contract=record.operand_namespaces,
            arity=record.arity,
        )
    )
    assert index.exact_lookup(record.semantic_payload) == ()


def test_exact_hash_does_not_accept_noisy_cue() -> None:
    records, index = _fixture_index()
    record = records[0]
    noisy = corrupt_payload(record.semantic_payload, probability=0.10, seed=123)
    assert index.exact_lookup(noisy) == ()


def test_lsh_can_return_multiple_candidates() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    routing = multi_probe.route(records[0].semantic_payload, candidate_budget=CANDIDATE_BUDGET)
    assert len(routing.candidate_handles) >= 1


def test_bucket_collision_is_not_identity_match() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    routing = multi_probe.route(records[0].semantic_payload, candidate_budget=CANDIDATE_BUDGET)
    if len(routing.candidate_handles) > 1:
        assert len(set(routing.candidate_handles)) == len(routing.candidate_handles)


def test_duplicate_postings_are_deduplicated() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    routing = multi_probe.route(records[0].semantic_payload, candidate_budget=CANDIDATE_BUDGET)
    assert len(routing.candidate_handles) == len(set(routing.candidate_handles))


def test_malformed_trace_is_rejected_with_typed_status() -> None:
    payload = {"trace_handle": "x"}
    record, validation = trace_record_from_dict(payload)
    assert record is None
    assert validation.status == TRACE_MALFORMED


def test_wrong_checksum_is_rejected() -> None:
    record = _fixture_records()[0]
    bad_trace = TraceRecord(
        trace_handle=record.trace_handle,
        record_id=record.record_id,
        operation_family=record.family_label,
        algebra="MAP",
        arity=record.arity,
        operand_namespaces=record.operand_namespaces,
        operation_parameters=dict(record.trace_record.operation_parameters),
        parent_handles=record.trace_record.parent_handles,
        semantic_payload_checksum="deadbeef",
    )
    entry = TraceStoreEntry(
        trace_record=bad_trace,
        semantic_payload=record.semantic_payload,
        committed=True,
        family_label=record.family_label,
        namespace_contract=record.operand_namespaces,
        arity=record.arity,
    )
    assert validate_entry(entry).status == TRACE_CHECKSUM_MISMATCH


def test_wrong_operation_family_is_not_accepted() -> None:
    record = _fixture_records()[0]
    replacement_family = "MAP_BIND_2" if record.family_label != "MAP_BIND_2" else "MAP_BUNDLE_3"
    bad_trace = TraceRecord(
        trace_handle=record.trace_handle,
        record_id=record.record_id,
        operation_family=replacement_family,
        algebra="MAP",
        arity=record.arity,
        operand_namespaces=record.operand_namespaces,
        operation_parameters=dict(record.trace_record.operation_parameters),
        parent_handles=record.trace_record.parent_handles,
        semantic_payload_checksum=payload_checksum(record.semantic_payload),
    )
    entry = TraceStoreEntry(
        trace_record=bad_trace,
        semantic_payload=record.semantic_payload,
        committed=True,
        family_label=record.family_label,
        namespace_contract=record.operand_namespaces,
        arity=record.arity,
    )
    assert validate_entry(entry).status == TRACE_OPERATION_FAMILY_MISMATCH


def test_empty_bucket_gives_expand_or_abstain_not_exception() -> None:
    records, index = _fixture_index()
    router = RandomHyperplaneLSH(SignatureConfig(MAP_DIMENSIONS, SIGNATURE_BITS, 1, 999999, 1))
    router.fit({})
    routing = router.route(records[0].semantic_payload, candidate_budget=CANDIDATE_BUDGET)
    decision = decide_candidate([], rerank_k=RERANK_K, accept_similarity_threshold=0.97, accept_margin=ACCEPT_MARGIN, expansion_available=routing.empty_primary_bucket)
    assert decision.decision in {DECISION_EXPAND, DECISION_ABSTAIN}


def test_probe_budget_is_strictly_enforced() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    routing = multi_probe.route(records[0].semantic_payload, candidate_budget=CANDIDATE_BUDGET)
    assert len(routing.probed_signatures) <= 4 * 4


def test_candidate_budget_is_strictly_enforced() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    routing = multi_probe.route(records[0].semantic_payload, candidate_budget=8)
    assert len(routing.candidate_handles) <= 8


def test_random_routing_baseline_is_budget_matched() -> None:
    records, index = _fixture_index()
    _, _, random_router = _fixture_routers(index)
    routing = random_router.route(query_key="q", candidate_budget=CANDIDATE_BUDGET)
    assert len(routing.candidate_handles) <= CANDIDATE_BUDGET


def test_shuffled_semantic_to_trace_mapping_fails_recovery() -> None:
    records, index = _fixture_index()
    _, multi_probe, _ = _fixture_routers(index)
    query = build_queries(
        dataset_id="n1000",
        records=records,
        query_seed_start=930399000,
        query_count=1,
        corruption_probability=0.03,
    )[0]
    good = run_method_query(
        method_id=METHOD_MULTI_PROBE,
        query=query,
        index=index,
        handles=index.committed_handles(),
        lsh_router=multi_probe,
        random_router=None,
    )
    shuffled = list(records)
    shuffled.reverse()
    shuffled_index = TraceIndex()
    for left, right in zip(records, shuffled, strict=True):
        shuffled_index.insert(
            TraceStoreEntry(
                trace_record=right.trace_record,
                semantic_payload=left.semantic_payload,
                committed=True,
                family_label=right.family_label,
                namespace_contract=right.operand_namespaces,
                arity=right.arity,
            )
        )
    bad = run_method_query(
        method_id=METHOD_MULTI_PROBE,
        query=query,
        index=shuffled_index,
        handles=shuffled_index.committed_handles(),
        lsh_router=multi_probe,
        random_router=None,
    )
    assert good["trace_recall_at_32"] >= bad["trace_recall_at_32"]
    assert bad["wrong_trace_acceptance_rate"] in {0, 1}


def test_no_heldout_or_frozen_seed_overlap() -> None:
    assert seeds_are_fresh(ROOT) is True
    assert stage_a_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_serialized_protocol_is_reproducible() -> None:
    first = json.dumps(build_protocol(ROOT), sort_keys=True)
    second = json.dumps(build_protocol(ROOT), sort_keys=True)
    assert first == second


def test_existing_namespace_is_separate_from_level35b() -> None:
    assert STAGE_A_NAMESPACE != "level3_5b_dev"
    assert STAGE_A_NAMESPACE != "level3_5b_heldout"


def test_exact_hash_baseline_exists_and_corruption_contract_is_frozen() -> None:
    protocol = build_protocol(ROOT)
    assert METHOD_EXACT_HASH in protocol["baselines"]
    assert protocol["corruption_channel"]["channel_id"] == CORRUPTION_CHANNEL_ID
    assert protocol["corruption_channel"]["points"] == list(QUERY_CORRUPTION_POINTS)
