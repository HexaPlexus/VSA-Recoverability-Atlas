from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from cgrn_hsr.exact_capsule_contract_closure import (
    BUDGET_M0,
    CORRUPTION_C0,
    CORRUPTION_C10,
    CORRUPTION_C4,
    CORRUPTION_C6,
    CORRUPTION_C7,
    CORRUPTION_C8,
    CORRUPTION_C9,
    LEVEL35_V4_SHA256,
    METHOD_E2,
    METHOD_E3,
    METHOD_E6,
    RAW_CAPSULE_BITS,
    SCHEMA_VERSION,
    STAGE_A1_PROTOCOL_SHA256,
    STAGE_A2A_PROTOCOL_SHA256,
    STAGE_A_PROTOCOL_SHA256,
    build_queries,
    build_state,
    parse_capsule,
    prior_known_seed_set,
    protocol_payload,
    seeds_are_fresh,
    stage_seed_set,
    token_schemas,
    _run_trial,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "exact_capsule_contract"
FIRST_ORDER_DOC_SHA256 = "C66FE1EEE89F079A2BB551EF7FD26CB13EF173F21871406A38E5FF8E6766341D"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_protocol_serialization_is_deterministic_and_seed_ranges_are_fresh() -> None:
    left = protocol_payload(ROOT)
    right = protocol_payload(ROOT)
    assert left["protocol_hash"] == right["protocol_hash"]
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_token_schema_matches_frozen_capsule_payload_and_bch_contract() -> None:
    schemas = token_schemas()
    assert schemas["raw_capsule"]["total_bits"] == RAW_CAPSULE_BITS == 21
    assert schemas["ecc"]["shortened_k"] == RAW_CAPSULE_BITS
    assert schemas["ecc"]["shortened_n"] > schemas["ecc"]["shortened_k"]


def test_plain_field_and_isolated_capsule_share_same_bits_on_clean_query() -> None:
    state = build_state(budget_contract=BUDGET_M0)
    query = build_queries(state, corruption_cell=CORRUPTION_C0)[0]
    assert query.carried_field_bits == query.carried_capsule_bits
    plain = _run_trial(state=state, query=query, method_id=METHOD_E2)
    capsule = _run_trial(state=state, query=query, method_id=METHOD_E3)
    assert plain["accepted_trace_id"] == capsule["accepted_trace_id"]
    assert plain["final_outcome"] == capsule["final_outcome"] == "ACCEPT"


def test_parse_rejects_malformed_and_integrity_corrupted_capsules() -> None:
    state = build_state(budget_contract=BUDGET_M0)
    malformed = build_queries(state, corruption_cell=CORRUPTION_C8)[0]
    corrupted = build_queries(state, corruption_cell=CORRUPTION_C9)[0]
    _, malformed_status = parse_capsule(malformed.carried_capsule_bits)
    _, corrupted_status = parse_capsule(corrupted.carried_capsule_bits)
    assert malformed_status == "CAPSULE_PARSE_FAILURE"
    assert corrupted_status == "CAPSULE_INTEGRITY_FAILURE"


def test_erased_stale_and_uncommitted_capsules_return_typed_failures() -> None:
    state = build_state(budget_contract=BUDGET_M0)
    erased = _run_trial(state=state, query=build_queries(state, corruption_cell=CORRUPTION_C4)[0], method_id=METHOD_E3)
    stale = _run_trial(state=state, query=build_queries(state, corruption_cell=CORRUPTION_C7)[0], method_id=METHOD_E3)
    uncommitted = _run_trial(state=state, query=build_queries(state, corruption_cell=CORRUPTION_C10)[0], method_id=METHOD_E3)
    assert erased["retrieval_outcome"] == "NO_TRACE"
    assert stale["retrieval_outcome"] == "STALE_TRACE"
    assert uncommitted["retrieval_outcome"] == "UNCOMMITTED_TRACE"
    assert erased["accepted_trace_id"] is None
    assert stale["accepted_trace_id"] is None
    assert uncommitted["accepted_trace_id"] is None


def test_wrong_valid_capsule_does_not_silently_accept_wrong_trace() -> None:
    state = build_state(budget_contract=BUDGET_M0)
    row = _run_trial(state=state, query=build_queries(state, corruption_cell=CORRUPTION_C6)[0], method_id=METHOD_E3)
    assert row["accepted_trace_id"] is None
    assert row["silent_wrong_provenance"] == 0
    assert row["silent_wrong_decoder"] == 0


def test_ecc_arm_improves_corrupted_capsule_coverage_over_raw_capsule() -> None:
    summary = _load_csv(RESULTS / "retrieval_summary.csv")
    def coverage(method: str, cell: str) -> float:
        row = next(
            item for item in summary
            if item["method_id"] == method
            and item["budget_contract"] == BUDGET_M0
            and item["corruption_cell"] == cell
        )
        return float(row["accepted_exact_trace_coverage"])
    assert coverage(METHOD_E6, "C2_SEMANTIC_CLEAN_CAPSULE_NOISY") > coverage(METHOD_E3, "C2_SEMANTIC_CLEAN_CAPSULE_NOISY")


def test_stage_artifacts_exist_and_analysis_reports_no_heldout_execution() -> None:
    required = [
        "dependency_audit.json",
        "development_protocol.json",
        "information_contracts.json",
        "token_schemas.json",
        "environment.json",
        "trial_results.jsonl",
        "retrieval_summary.csv",
        "replay_summary.csv",
        "corruption_summary.csv",
        "lifecycle_summary.csv",
        "memory_summary.csv",
        "latency_summary.csv",
        "ablation_summary.csv",
        "analysis.json",
    ]
    for name in required:
        assert (RESULTS / name).exists(), name
    analysis = _load(RESULTS / "analysis.json")
    assert analysis["schema_version"] == SCHEMA_VERSION
    assert analysis["heldout_execution_count"] == 0


def test_previous_stage_and_level35_artifacts_remain_immutable() -> None:
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a" / "development_protocol.json") == STAGE_A_PROTOCOL_SHA256
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a1" / "development_protocol.json") == STAGE_A1_PROTOCOL_SHA256
    assert _sha256(ROOT / "results" / "lazy_trace_stage_a2a" / "development_protocol.json") == STAGE_A2A_PROTOCOL_SHA256
    assert _sha256(ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256
    assert _sha256(ROOT / "docs" / "LEVEL3_FIRST_ORDER_TRACE_COACTIVATION.md") == FIRST_ORDER_DOC_SHA256


def test_exact_resolution_gate_now_tracks_only_resolvable_clean_records() -> None:
    analysis = _load(RESULTS / "analysis.json")
    assert analysis["gates"]["exact_resolution_gate"] == "PASS"


def test_retrieval_and_replay_failures_are_separated_in_trial_rows() -> None:
    trial_path = RESULTS / "trial_results.jsonl"
    rows = [json.loads(line) for line in trial_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    mismatch = [
        row for row in rows
        if row["retrieval_outcome"] != row["replay_outcome"]
    ]
    assert mismatch
