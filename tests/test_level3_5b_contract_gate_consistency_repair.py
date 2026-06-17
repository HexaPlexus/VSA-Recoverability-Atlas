from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_zero_heldout_trials_and_blocked_v3_immutable() -> None:
    payload = _load("results/level3_5b_gate_consistency_repair/validator_result.json")
    assert payload["zero_heldout_trials"] is True
    assert payload["blocked_v3_attempt_committed_and_immutable"] is True
    assert payload["v1_v2_v3_unchanged"] is True


def test_root_cause_audit_and_repaired_side() -> None:
    audit = _load("results/level3_5b_gate_consistency_repair/contract_gate_consistency_audit.json")
    analysis = _load("results/level3_5b_gate_consistency_repair/analysis.json")
    assert audit["root_cause"] == "AMBIGUOUS_RULE_SEMANTICS"
    assert audit["fixture_input_validity"] == "VALID_FAIL_CASE"
    assert "serialized contract-gate rule" in analysis["repaired_side"]


def test_only_contract_gate_consistency_diff_exists() -> None:
    diff = _load("results/level3_5b_gate_consistency_repair/protocol_v3_to_v4_diff.json")
    assert all(
        row["change_type"] in {"CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR", "METADATA_ONLY"}
        for row in diff["rows"]
    )


def test_performance_gates_and_hashes_unchanged() -> None:
    v3 = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    v4 = _load("results/level3_5b_gate_consistency_repair/heldout_protocol_v4.json")
    for gate_id, gate_hash in v3["canonical_gate_hashes"].items():
        if gate_id == "no_shared_noise_winner_contract_v1":
            assert v4["canonical_gate_hashes"][gate_id] != gate_hash
        else:
            assert v4["canonical_gate_hashes"][gate_id] == gate_hash
    assert v4["preserved_scientific_fields"] == v3["preserved_scientific_fields"]
    assert v4["fresh_seed_ranges"] == v3["fresh_seed_ranges"]
    assert v4["trial_counts"] == v3["trial_counts"]
    assert v4["complete_config_records"] == v3["complete_config_records"]
    assert v4["metrics"] == v3["metrics"]


def test_pass_fail_exception_are_distinguishable() -> None:
    dry = _load("results/level3_5b_gate_consistency_repair/synthetic_dry_run_results.json")
    gate = dry["rows"]["no_shared_noise_winner_contract_v1"]
    assert gate["pass_case"]["state"] == "PASS"
    assert gate["fail_case"]["state"] == "FAIL"
    assert gate["exceptional_trial_case"]["state"] == "EXCEPTION"
    assert gate["missing_data_case"]["state"] == "EXCEPTION"
    assert gate["contradictory_metrics_case"]["state"] == "EXCEPTION"


def test_all_synthetic_dry_runs_pass_and_no_benchmark_execution() -> None:
    validator = _load("results/level3_5b_gate_consistency_repair/validator_result.json")
    analysis = _load("results/level3_5b_gate_consistency_repair/analysis.json")
    assert validator["synthetic_dry_runs_pass"] is True
    assert validator["pass_fail_exception_distinguishable"] is True
    assert validator["benchmark_execution_invoked"] is False
    assert analysis["benchmark_execution_invoked"] is False
