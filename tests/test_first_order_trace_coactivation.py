from __future__ import annotations

import hashlib
from pathlib import Path

from cgrn_hsr.release_artifacts import canonical_sha256
from cgrn_hsr.first_order_trace_coactivation import (
    BUDGET_FIXED_SEMANTIC,
    DECISION_ABSTAIN,
    DECISION_AMBIGUOUS,
    DECISION_NO_TRACE,
    LEVEL35_V4_SHA256,
    METHOD_B0_KNOWN_HANDLE,
    METHOD_B2_BRIDGE,
    METHOD_B3_EXACT_CAPSULE,
    METHOD_B7_TRACE_FREE,
    PRIMARY_CANDIDATE_BUDGET,
    QUERY_CLASS_U3,
    QUERY_CLASS_U4,
    SCHEMA_VERSION,
    STAGE_A1_PROTOCOL_SHA256,
    STAGE_A2A_PROTOCOL_SHA256,
    STAGE_A_PROTOCOL_SHA256,
    TRACE_INVALID_COMMIT_STATE,
    TRACE_INVALID_PARENT_HANDLE,
    TRACE_VALID,
    build_query_set,
    build_replay_bank,
    build_store_state,
    build_trace_atom,
    dependency_audit,
    operation_contract_key,
    prior_known_seed_set,
    protocol_payload,
    run_first_order_trace_coactivation,
    seeds_are_fresh,
    stage_seed_set,
    validate_trace_atom,
    _run_trial,
)

ROOT = Path(__file__).resolve().parents[1]
STAGE_A_PROTOCOL_SHA256_CANONICAL = "7DC4904A0029C258B101D645E1E62B2EAA59DEC2F81209A8A1490A30E6AADDE1"
STAGE_A1_PROTOCOL_SHA256_CANONICAL = "49AC82ECF69DAF269DC014ED77B62E0809B46C81E9AFD171EE5DFF6BC36152E3"
STAGE_A2A_PROTOCOL_SHA256_CANONICAL = "25DAFF8D448F2B5102184FA74EC5D4A3CD05F14A6AC050C2DD3926C2A4A1E1C8"


def _sha256(path: Path) -> str:
    return canonical_sha256(path).upper()


def _fixture_state(record_count: int = 128, trace_dimensions: int = 16):
    return build_store_state(
        dimensions=128,
        trace_dimensions=trace_dimensions,
        budget_contract=BUDGET_FIXED_SEMANTIC,
        record_count=record_count,
        seed=123,
    )


def _fixture_queries(corruption_cell: str = "C0_CLEAN", *, count: int = 16, trace_dimensions: int = 16):
    state, remaining = _fixture_state(trace_dimensions=trace_dimensions)
    queries = build_query_set(
        records=state.records,
        remaining_candidates=remaining,
        corruption_cell=corruption_cell,
        budget_contract=BUDGET_FIXED_SEMANTIC,
        trace_dimensions=trace_dimensions,
        query_seed_start=999,
        query_count=count,
    )
    return state, remaining, queries


def test_replay_bank_covers_all_required_operation_families() -> None:
    replay_bank, atomic = build_replay_bank(dimensions=64, seed=1)
    families = {candidate.operation_family for candidate in replay_bank}
    assert families == {
        "MAP_BIND_2",
        "MAP_BIND_3",
        "MAP_BUNDLE_3",
        "MAP_BUNDLE_5",
        "MAP_PERMUTE_K",
        "MAP_BIND_THEN_BUNDLE",
    }
    assert atomic


def test_trace_atom_validation_rejects_uncommitted_and_unknown_parent() -> None:
    replay_bank, atomic = build_replay_bank(dimensions=64, seed=1)
    candidate = replay_bank[0]
    atom = build_trace_atom(
        trace_id="trace:test",
        result_record_id="record:test",
        replay_candidate=candidate,
        provenance="ACTUAL_EXECUTED_OPERATION",
        commit_state="UNCOMMITTED",
    )
    validation = validate_trace_atom(atom, result_record_id="record:test", known_parent_handles=set(atomic))
    assert validation.status == TRACE_INVALID_COMMIT_STATE
    committed = build_trace_atom(
        trace_id="trace:test:2",
        result_record_id="record:test",
        replay_candidate=candidate,
        provenance="ACTUAL_EXECUTED_OPERATION",
        commit_state="COMMITTED",
    )
    validation_bad_parent = validate_trace_atom(
        committed,
        result_record_id="record:test",
        known_parent_handles={"bad:parent"},
    )
    assert validation_bad_parent.status == TRACE_INVALID_PARENT_HANDLE


def test_lazy_uncommitted_queries_have_no_authoritative_trace() -> None:
    state, remaining, queries = _fixture_queries(corruption_cell="C0_CLEAN")
    unknown = next(query for query in queries if query.query_class == QUERY_CLASS_U4)
    assert unknown.target_trace_ids == tuple()
    row = _run_trial(method_id=METHOD_B2_BRIDGE, state=state, query=unknown)
    assert row["decision"] in {DECISION_NO_TRACE, DECISION_ABSTAIN, "EXPAND"}
    assert row["accepted_trace_id"] is None


def test_known_handle_oracle_accepts_true_trace() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C0_CLEAN")
    query = next(query for query in queries if query.query_class != QUERY_CLASS_U4)
    row = _run_trial(method_id=METHOD_B0_KNOWN_HANDLE, state=state, query=query)
    assert row["decision"] == "ACCEPT"
    assert row["accepted_trace_id"] in set(query.target_trace_ids)
    assert row["trace_spike_recall_at_1"] == 1


def test_semantic_bridge_can_return_multiple_candidates() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C1_SEMANTIC_ONLY")
    query = next(query for query in queries if query.query_class != QUERY_CLASS_U4)
    row = _run_trial(method_id=METHOD_B2_BRIDGE, state=state, query=query)
    assert row["trace_spike_candidate_count"] >= 1
    assert len(row["candidate_trace_ids"]) == row["trace_spike_candidate_count"]
    assert row["trace_spike_candidate_count"] <= PRIMARY_CANDIDATE_BUDGET


def test_identical_semantics_semantic_only_arm_does_not_silently_accept_exact_trace() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C0_CLEAN")
    query = next(query for query in queries if query.query_class == QUERY_CLASS_U3)
    row = _run_trial(method_id=METHOD_B2_BRIDGE, state=state, query=query)
    assert row["decision"] in {DECISION_AMBIGUOUS, DECISION_ABSTAIN, "EXPAND"}
    assert row["silent_wrong_trace_rate"] == 0


def test_identical_semantics_exact_capsule_never_silently_accepts_wrong_trace() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C0_CLEAN")
    query = next(query for query in queries if query.query_class == QUERY_CLASS_U3)
    row = _run_trial(method_id=METHOD_B3_EXACT_CAPSULE, state=state, query=query)
    assert row["silent_wrong_trace_rate"] == 0
    if row["accepted_trace_id"] is not None:
        assert row["accepted_trace_id"] in set(query.target_trace_ids)


def test_trace_free_portfolio_attempts_more_decoders_than_trace_configured_arm() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C1_SEMANTIC_ONLY")
    query = next(query for query in queries if query.query_class != QUERY_CLASS_U4)
    trace_free = _run_trial(method_id=METHOD_B7_TRACE_FREE, state=state, query=query)
    bridged = _run_trial(method_id=METHOD_B2_BRIDGE, state=state, query=query)
    assert trace_free["decoder_invocations"] > bridged["decoder_invocations"]
    assert trace_free["decoder_families_attempted"] >= bridged["decoder_families_attempted"]


def test_parent_handle_removal_preserves_contract_but_reduces_exact_parent_recovery() -> None:
    state, _, queries = _fixture_queries(corruption_cell="C0_CLEAN")
    query = next(query for query in queries if query.query_class != QUERY_CLASS_U4)
    with_handles = _run_trial(method_id=METHOD_B2_BRIDGE, state=state, query=query)
    without_handles = _run_trial(
        method_id=METHOD_B2_BRIDGE,
        state=state,
        query=query,
        remove_exact_parent_handles=True,
    )
    assert without_handles["operation_family_recovery"] == with_handles["operation_family_recovery"]
    assert without_handles["exact_parent_handle_recovery"] <= with_handles["exact_parent_handle_recovery"]


def test_protocol_serialization_is_deterministic_and_seed_fresh() -> None:
    left = protocol_payload(ROOT)
    right = protocol_payload(ROOT)
    assert left["protocol_hash"] == right["protocol_hash"]
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_dependency_audit_and_prior_stage_artifacts_unchanged() -> None:
    audit = dependency_audit(ROOT)
    assert audit["verdict"] == "COMPOSE"
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a" / "development_protocol.json") in {STAGE_A_PROTOCOL_SHA256, STAGE_A_PROTOCOL_SHA256_CANONICAL}
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a1" / "development_protocol.json") in {STAGE_A1_PROTOCOL_SHA256, STAGE_A1_PROTOCOL_SHA256_CANONICAL}
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a2a" / "development_protocol.json") in {STAGE_A2A_PROTOCOL_SHA256, STAGE_A2A_PROTOCOL_SHA256_CANONICAL}
    assert canonical_sha256(ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper() == LEVEL35_V4_SHA256
