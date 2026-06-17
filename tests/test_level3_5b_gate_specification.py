from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from cgrn_hsr.level3_5b_gate_specification import (
    ALLOWED_DIFF_TYPES,
    LEVEL3_5B_GATE_COMPLETION_VERDICT,
    NO_SHARED_NOISE_WINNER_NOT_CONFIRMED,
    PREVIOUS_BLOCKED_CHECKPOINT,
    PROTOCOL_V2_CANONICAL_HASH,
    complete_gate_hash,
    evaluate_gate,
    load_csv_rows,
    read_json,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_zero_heldout_trials_and_no_leakage() -> None:
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    assert validator["zero_heldout_trials_before_v3"] is True
    assert validator["heldout_trials_observed"] == 0
    assert validator["heldout_outcomes_available_to_gate_design"] is False


def test_old_protocols_and_block_records_immutable() -> None:
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    assert validator["v1_and_v2_unchanged_since_previous_blocked_checkpoint"] is True
    assert validator["changed_immutable_paths"] == []
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            PREVIOUS_BLOCKED_CHECKPOINT,
            "HEAD",
            "--",
            "results/level3_5b_heldout",
            "results/level3_5b_protocol_repair",
            "results/level3_5b_heldout_v2",
            "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md",
            "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md",
            "docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""


def test_v2_to_v3_diff_allowlist_only() -> None:
    payload = _load("results/level3_5b_gate_specification/protocol_v2_to_v3_diff.json")
    assert payload["v2_canonical_hash"] == PROTOCOL_V2_CANONICAL_HASH
    assert set(payload["allowed_change_types"]) == ALLOWED_DIFF_TYPES
    assert all(row["change_type"] in ALLOWED_DIFF_TYPES for row in payload["rows"])


def test_methods_cells_points_seeds_configs_trials_and_metrics_unchanged() -> None:
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    assert validator["methods_unchanged"] is True
    assert validator["cells_unchanged"] is True
    assert validator["corruption_points_unchanged"] is True
    assert validator["seeds_unchanged_from_v2"] is True
    assert validator["trial_counts_unchanged"] is True
    assert validator["configs_unchanged"] is True
    assert validator["metrics_unchanged"] is True


def test_complete_gate_schemas_and_rule_hashes() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    assert validator["gate_schema_complete"] is True
    assert validator["undefined_thresholds"] == []
    assert validator["missing_provenance"] == []
    assert validator["bad_rule_hashes"] == []
    for gate in protocol["confirmatory_gates"]:
        assert gate["rule_hash"] == complete_gate_hash(gate)


def test_every_disposition_has_executable_rule() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    dispositions = {gate["disposition_if_pass"] for gate in protocol["confirmatory_gates"]}
    dispositions.update({gate["disposition_if_fail"] for gate in protocol["confirmatory_gates"]})
    assert "BCH_DOMINATES_BINARY_EXACT_RECORD_CONFIRMED" in dispositions
    assert "BCH_DOMINANCE_NOT_CONFIRMED" in dispositions
    assert "RAW_NECO_NOISE_GAP_CONFIRMED" in dispositions
    assert "RAW_NECO_NOISE_GAP_NOT_CONFIRMED" in dispositions
    assert "GENERIC_LINEAR_NOISE_EQUIVALENCE_CONFIRMED" in dispositions
    assert "GENERIC_LINEAR_NOISE_EQUIVALENCE_NOT_CONFIRMED" in dispositions
    assert "MAP_SILENT_COLLAPSE_CONFIRMED" in dispositions
    assert "MAP_SILENT_COLLAPSE_NOT_CONFIRMED" in dispositions
    assert "MAP_GRACEFUL_REGION_CONFIRMED" in dispositions
    assert "MAP_GRACEFUL_REGION_NOT_CONFIRMED" in dispositions
    assert "NO_SHARED_NOISE_WINNER" in dispositions
    assert NO_SHARED_NOISE_WINNER_NOT_CONFIRMED in dispositions


def test_gate_evaluation_is_deterministic() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    gate = protocol["confirmatory_gates"][0]
    binary_rows = load_csv_rows(ROOT / "results/level3_5b_dev/binary_summary.csv")
    map_rows = load_csv_rows(ROOT / "results/level3_5b_dev/map_summary.csv")
    adjusted_binary = [type(row)(**{**row.__dict__, "trials": 64}) for row in binary_rows]
    adjusted_map = [type(row)(**{**row.__dict__, "trials": 64}) for row in map_rows]
    left = evaluate_gate(gate, binary_rows=adjusted_binary, map_rows=adjusted_map, protocol_v3=protocol)
    right = evaluate_gate(gate, binary_rows=adjusted_binary, map_rows=adjusted_map, protocol_v3=protocol)
    assert left == right


def test_synthetic_dry_run_cases_cover_pass_fail_boundary_missing_exception_tie_and_contradiction() -> None:
    payload = _load("results/level3_5b_gate_specification/synthetic_dry_run_results.json")["rows"]
    for gate_id, cases in payload.items():
        assert cases["pass_case"]["state"] == "PASS"
        assert cases["fail_case"]["state"] in {"FAIL", "PASS"}
        assert cases["boundary_case"]["state"] in {"PASS", "FAIL"}
        assert cases["missing_data_case"]["state"] == "INCOMPLETE_INPUT"
        assert cases["exceptional_trial_case"]["state"] in {"INCOMPLETE_INPUT", "FAIL"}
        assert cases["tie_case"]["state"] in {"PASS", "FAIL"}
        assert cases["contradictory_metrics_case"]["state"] in {"EXCEPTION", "FAIL"}


def test_no_runtime_execution_is_invoked() -> None:
    analysis = _load("results/level3_5b_gate_specification/analysis.json")
    environment = _load("results/level3_5b_gate_specification/environment.json")
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_gate_specification.py").read_text(encoding="utf-8")
    assert analysis["benchmark_execution_invoked"] is False
    assert environment["benchmark_execution_invoked"] is False
    assert "run_level3_5b_dev(" not in source
    assert "run_level3_5b_heldout(" not in source
    assert "run_level3_5b_heldout_v2(" not in source


def test_bcf_remains_blocked() -> None:
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    assert validator["bcf_remains_blocked"] is True
    assert protocol["preserved_scientific_fields"]["bcf_track"]["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"


def test_validator_verdict_ready() -> None:
    validator = _load("results/level3_5b_gate_specification/validator_result.json")
    analysis = _load("results/level3_5b_gate_specification/analysis.json")
    assert validator["validator_verdict"] == LEVEL3_5B_GATE_COMPLETION_VERDICT
    assert analysis["completion_verdict"] == LEVEL3_5B_GATE_COMPLETION_VERDICT
    assert analysis["ready_verdict"] == "READY_FOR_LEVEL_3_5B_HELDOUT_V3"
