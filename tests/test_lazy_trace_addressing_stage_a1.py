from __future__ import annotations

import json
from pathlib import Path

from cgrn_hsr.release_artifacts import canonical_sha256
from cgrn_hsr.lazy_trace_addressing_stage_a1 import (
    ACCEPT_SIMILARITY_THRESHOLD,
    AMBIGUITY_SIMILARITY_EPSILON,
    METHOD_A1_MULTI_PROBE,
    METHOD_A1_PRIMARY,
    METHOD_EXACT_HASH,
    METHOD_GLOBAL_SCAN,
    OUTCOME_AMBIGUOUS_TRACE,
    PRIMARY_CANDIDATE_BUDGET,
    PROJECTION_SEEDS,
    QUERY_KIND_CONTRACT_AMBIGUITY,
    QUERY_KIND_EXACT_AMBIGUITY,
    QUERY_KIND_UNIQUE,
    RERANK_K,
    STAGE_A_PROTOCOL_HASH,
    _build_lsh_router,
    _decoder_contract_decision,
    _exact_trace_decision,
    _global_scan,
    _mutate_records_for_contract_shuffle,
    _mutate_records_for_exact_trace_shuffle,
    _mutate_records_for_parent_shuffle,
    _stage_a_protocol_hash,
    build_dataset,
    build_protocol,
    build_queries,
    build_trace_index,
    budget_matched_random_configs,
    contract_key_from_candidate,
    expected_any_table_hit_probability,
    expected_query_similarity,
    expected_single_bit_collision_probability,
    expected_single_table_hit_probability,
    method_configs,
    run_query,
    seeds_are_fresh,
    stage_a1_seed_set,
)
from cgrn_hsr.verification import rerank_candidates

ROOT = Path(__file__).resolve().parents[1]
STAGE_A_PROTOCOL_HASH_CANONICAL = "7dc4904a0029c258b101d645e1e62b2eaa59dec2f81209a8a1490a30e6aadde1"


def _fixture_records(record_count: int = 256):
    return build_dataset(dataset_seed=930450100, record_count=record_count)


def _fixture_index(record_count: int = 256):
    records = _fixture_records(record_count=record_count)
    return records, build_trace_index(records)


def _first_query(records, *, probability: float = 0.05, query_kind: str | None = None):
    queries = build_queries(
        dataset_id="fixture",
        records=records,
        query_seed_start=930499100,
        query_count=32,
        corruption_probability=probability,
    )
    if query_kind is None:
        return queries[0]
    return next(query for query in queries if query.query_kind == query_kind)


def test_analytical_probability_calculations_match_stage_a1_expectation() -> None:
    rho = expected_query_similarity(0.05)
    q = expected_single_bit_collision_probability(0.05)
    hit = expected_any_table_hit_probability(
        signature_bits=12,
        table_count=18,
        probability=0.05,
        probe_budget=1,
        routing_mode="primary_only",
    )
    assert abs(rho - 0.9) < 1e-9
    assert abs(q - 0.85643370687) < 1e-6
    assert abs(hit - 0.9524860264) < 1e-6


def test_frozen_configuration_serialization_includes_repaired_grid() -> None:
    protocol = build_protocol(ROOT)
    methods = protocol["methods"]
    assert methods[METHOD_A1_PRIMARY]["signature_bits"] == 12
    assert methods[METHOD_A1_PRIMARY]["table_count"] == 18
    assert methods[METHOD_A1_MULTI_PROBE]["routing_mode"] == "margin_probe"
    assert protocol["changed_fields"]["query_trials_per_primary_point"] == 512


def test_multi_table_determinism_and_projection_seed_change() -> None:
    records, index = _fixture_index()
    payload = records[0].semantic_payload
    config = method_configs()[METHOD_A1_PRIMARY]
    left = _build_lsh_router(config)
    right = _build_lsh_router(config)
    left.fit(index.committed_payloads())
    right.fit(index.committed_payloads())
    assert left.signatures(payload) == right.signatures(payload)
    changed = _build_lsh_router(type(config)(**{**config.__dict__, "projection_seed": PROJECTION_SEEDS[1]}))
    changed.fit(index.committed_payloads())
    assert left.signatures(payload) != changed.signatures(payload)


def test_margin_aware_probe_ordering_and_budget_are_deterministic() -> None:
    records, index = _fixture_index()
    config = method_configs()[METHOD_A1_MULTI_PROBE]
    router = _build_lsh_router(config)
    router.fit(index.committed_payloads())
    routing = router.route(records[0].semantic_payload, candidate_budget=PRIMARY_CANDIDATE_BUDGET)
    assert len(routing.probed_signatures) <= config.table_count * config.probe_budget
    secondary_margins = list(routing.probe_margins[config.table_count :])
    assert secondary_margins == sorted(secondary_margins)


def test_candidate_budget_and_raw_posting_accounting_are_strict() -> None:
    records, index = _fixture_index()
    config = method_configs()[METHOD_A1_PRIMARY]
    router = _build_lsh_router(config)
    router.fit(index.committed_payloads())
    routing = router.route(records[0].semantic_payload, candidate_budget=10)
    assert len(routing.candidate_handles) <= 10
    assert routing.raw_postings_retrieved >= len(routing.candidate_handles)


def test_vectorized_global_scan_matches_full_similarity_semantics() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.05)
    reranked_full, _ = rerank_candidates(
        query.noisy_payload,
        index.committed_entries(),
        candidate_matrix=index.committed_payload_matrix(),
    )
    _, reranked_topk, _, _ = _global_scan(index, query, rerank_k=RERANK_K)
    assert [candidate.handle for candidate in reranked_topk[:RERANK_K]] == [
        candidate.handle for candidate in reranked_full[:RERANK_K]
    ]


def test_decoder_contract_can_be_correct_when_exact_trace_is_ambiguous() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_EXACT_AMBIGUITY)
    _, reranked, _, _ = _global_scan(index, query, rerank_k=RERANK_K)
    decoder = _decoder_contract_decision(reranked, expansion_available=True)
    exact = _exact_trace_decision(reranked, query, expansion_available=True)
    assert any(contract_key_from_candidate(candidate) == query.target_contract_key for candidate in reranked[:RERANK_K])
    assert exact.outcome == OUTCOME_AMBIGUOUS_TRACE
    assert decoder.outcome in {"ACCEPT", "EXPAND", "ABSTAIN"}


def test_exact_trace_correctness_holds_for_unique_exact_query() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_UNIQUE)
    row = run_query(
        method_id=METHOD_GLOBAL_SCAN,
        config_id=METHOD_GLOBAL_SCAN,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=len(index.committed_handles()),
        rerank_k=RERANK_K,
    )
    assert row["decoder_contract_recall_at_1"] == 1
    assert row["exact_trace_recall_at_1"] == 1
    assert row["exact_trace_top1_accuracy"] == 1


def test_identical_semantic_payloads_never_silently_accept_one_exact_trace() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_EXACT_AMBIGUITY)
    row = run_query(
        method_id=METHOD_EXACT_HASH,
        config_id=METHOD_EXACT_HASH,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=0,
        rerank_k=RERANK_K,
    )
    assert row["exact_trace_outcome"] == OUTCOME_AMBIGUOUS_TRACE
    assert row["exact_trace_accepted_wrong"] == 0
    assert row["ambiguous_wrong_acceptance"] == 0


def test_contract_shuffle_collapses_decoder_contract_retrieval() -> None:
    records = _fixture_records()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_UNIQUE)
    shuffled_records = _mutate_records_for_contract_shuffle(records)
    index = build_trace_index(shuffled_records)
    row = run_query(
        method_id=METHOD_GLOBAL_SCAN,
        config_id=METHOD_GLOBAL_SCAN,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=len(index.committed_handles()),
        rerank_k=RERANK_K,
    )
    assert row["decoder_contract_recall_at_1"] == 0


def test_exact_trace_shuffle_preserves_contract_but_breaks_exact_identity() -> None:
    records = _fixture_records()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_UNIQUE)
    shuffled_records = _mutate_records_for_exact_trace_shuffle(records)
    index = build_trace_index(shuffled_records)
    row = run_query(
        method_id=METHOD_GLOBAL_SCAN,
        config_id=METHOD_GLOBAL_SCAN,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=len(index.committed_handles()),
        rerank_k=RERANK_K,
    )
    assert row["decoder_contract_recall_at_1"] == 1
    assert row["exact_trace_recall_at_1"] == 0


def test_parent_shuffle_preserves_contract_but_fails_provenance_validation() -> None:
    records = _fixture_records()
    query = _first_query(records, probability=0.0, query_kind=QUERY_KIND_UNIQUE)
    shuffled_records = _mutate_records_for_parent_shuffle(records)
    index = build_trace_index(shuffled_records)
    row = run_query(
        method_id=METHOD_GLOBAL_SCAN,
        config_id=METHOD_GLOBAL_SCAN,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=len(index.committed_handles()),
        rerank_k=RERANK_K,
    )
    assert row["decoder_contract_recall_at_1"] == 1
    assert row["exact_trace_recall_at_1"] == 0


def test_acceptance_coverage_and_conditional_risk_are_explicit() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.05, query_kind=QUERY_KIND_UNIQUE)
    config = method_configs()[METHOD_A1_PRIMARY]
    router = _build_lsh_router(config)
    router.fit(index.committed_payloads())
    row = run_query(
        method_id=config.method_id,
        config_id=config.method_id,
        query=query,
        index=index,
        router=router,
        random_router=None,
        candidate_budget=config.candidate_budget,
        rerank_k=config.rerank_k,
    )
    assert row["decoder_contract_acceptance_coverage"] in {0, 1}
    assert row["exact_trace_acceptance_coverage"] in {0, 1}
    assert row["decoder_contract_conditional_risk_denominator"] in {0, 1}
    assert row["exact_trace_conditional_risk_denominator"] in {0, 1}


def test_exact_hash_baseline_remains_exact_only() -> None:
    records, index = _fixture_index()
    query = _first_query(records, probability=0.10, query_kind=QUERY_KIND_UNIQUE)
    row = run_query(
        method_id=METHOD_EXACT_HASH,
        config_id=METHOD_EXACT_HASH,
        query=query,
        index=index,
        router=None,
        random_router=None,
        candidate_budget=0,
        rerank_k=RERANK_K,
    )
    assert row["candidate_set_size"] == 0
    assert row["exact_hash_hit"] == 0


def test_stage_a_artifact_hash_and_seed_freshness_are_preserved() -> None:
    raw_hash = _stage_a_protocol_hash(ROOT)
    canonical_hash = canonical_sha256(ROOT / "results" / "lazy_trace_stage_a" / "development_protocol.json")
    assert raw_hash == STAGE_A_PROTOCOL_HASH or canonical_hash == STAGE_A_PROTOCOL_HASH_CANONICAL
    assert seeds_are_fresh(ROOT) is True
    assert stage_a1_seed_set().isdisjoint({910350100, 920350100})


def test_random_budget_matching_is_serialized_and_capped() -> None:
    configs = budget_matched_random_configs()
    assert configs[METHOD_A1_PRIMARY].candidate_budget <= PRIMARY_CANDIDATE_BUDGET
    assert configs[METHOD_A1_MULTI_PROBE].candidate_budget <= PRIMARY_CANDIDATE_BUDGET
