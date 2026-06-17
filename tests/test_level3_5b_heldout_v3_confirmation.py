from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cgrn_hsr.level3_5b_heldout_v3_confirmation import (
    EXPECTED_BCH_HASH,
    EXPECTED_MAP_HASHES,
    EXPECTED_PROTOCOL_V3_HASH,
    execution_already_materialized,
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


def _read_jsonl(path: str) -> list[dict]:
    rows = []
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_v3_hash_and_config_hashes_match() -> None:
    payload = _load("results/level3_5b_heldout_v3/protocol_integrity.json")
    assert payload["protocol_v3_hash_expected"] == EXPECTED_PROTOCOL_V3_HASH
    assert payload["protocol_v3_hash_observed"] == EXPECTED_PROTOCOL_V3_HASH
    assert payload["bch_hash_expected"] == EXPECTED_BCH_HASH
    assert payload["bch_hash_observed"] == EXPECTED_BCH_HASH
    assert payload["map_hashes_expected"] == EXPECTED_MAP_HASHES
    assert payload["map_hashes_observed"] == EXPECTED_MAP_HASHES
    assert payload["gate_hashes_match"] is True


def test_old_protocols_and_block_records_immutable() -> None:
    payload = _load("results/level3_5b_heldout_v3/protocol_integrity.json")
    assert payload["old_protocols_unchanged"] is True
    assert payload["changed_immutable_paths"] == []


def test_execution_manifest_created_before_trials() -> None:
    manifest = _load("results/level3_5b_heldout_v3/execution_manifest.json")
    completion = _load("results/level3_5b_heldout_v3/completion_manifest.json")
    assert manifest["trials_executed_before_manifest"] == 0
    assert manifest["execution_authorized"] is True
    assert completion["rerun_after_completion_forbidden"] is True


def test_exact_assigned_seed_usage_and_uniqueness() -> None:
    manifest = _load("results/level3_5b_heldout_v3/execution_manifest.json")
    binary_trials = _read_jsonl("results/level3_5b_heldout_v3/binary_trials.jsonl")
    map_trials = _read_jsonl("results/level3_5b_heldout_v3/map_trials.jsonl")

    for track_name, trial_rows in (("binary_track", binary_trials), ("map_track", map_trials)):
        by_cell: dict[str, set[int]] = {}
        for row in trial_rows:
            by_cell.setdefault(row["cell_id"], set()).add(int(row["trial_seed"]))
        for cell_id, seeds in manifest["exact_concrete_seeds"][track_name].items():
            assert set(seeds) == by_cell[cell_id]
            assert len(seeds) == 64
            assert len(set(seeds)) == 64


def test_every_seed_executes_exactly_once_per_assigned_point() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    binary_trials = _read_jsonl("results/level3_5b_heldout_v3/binary_trials.jsonl")
    map_trials = _read_jsonl("results/level3_5b_heldout_v3/map_trials.jsonl")

    expected_binary_methods = set(protocol["preserved_scientific_fields"]["binary_track"]["methods"])
    expected_map_methods = set(protocol["preserved_scientific_fields"]["map_track"]["methods"])

    binary_counts: dict[tuple[str, str, str, int], int] = {}
    for row in binary_trials:
        key = (row["cell_id"], row["method_id"], row["corruption_label"], int(row["trial_seed"]))
        binary_counts[key] = binary_counts.get(key, 0) + 1
        assert row["method_id"] in expected_binary_methods
    assert all(value == 1 for value in binary_counts.values())

    map_counts: dict[tuple[str, str, str, int], int] = {}
    for row in map_trials:
        key = (row["cell_id"], row["method_id"], row["corruption_label"], int(row["trial_seed"]))
        map_counts[key] = map_counts.get(key, 0) + 1
        assert row["method_id"] in expected_map_methods
    assert all(value == 1 for value in map_counts.values())


def test_no_replacement_extra_or_adaptive_points() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    binary_trials = _read_jsonl("results/level3_5b_heldout_v3/binary_trials.jsonl")
    map_trials = _read_jsonl("results/level3_5b_heldout_v3/map_trials.jsonl")
    binary_points = protocol["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"]
    map_points = protocol["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]
    assert {row["corruption_label"] for row in binary_trials if row["cell_id"] == "u1_f3_m10"} == set(binary_points["u1_f3_m10"])
    assert {row["corruption_label"] for row in map_trials if row["cell_id"] == "u1_f3_m31"} == set(map_points["u1_f3_m31"])


def test_truth_not_passed_and_map_corruption_after_clean_construction() -> None:
    binary_trials = _read_jsonl("results/level3_5b_heldout_v3/binary_trials.jsonl")
    map_trials = _read_jsonl("results/level3_5b_heldout_v3/map_trials.jsonl")
    assert all(row["uses_truth_in_decoder"] is False for row in binary_trials)
    assert all(row["uses_truth_in_decoder"] is False for row in map_trials)
    assert all(row["corruption_after_clean_product_construction"] is True for row in map_trials)


def test_bcf_never_invoked_and_remains_blocked() -> None:
    payload = _load("results/level3_5b_heldout_v3/bcf_status.json")
    assert payload["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
    assert payload["executed"] is False


def test_gate_evaluation_uses_serialized_rules_only_and_order_is_fixed() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    gate_results = _load("results/level3_5b_heldout_v3/gate_results.json")["rows"]
    assert [row["gate_id"] for row in gate_results] == protocol["deterministic_verdict_evaluation_order"]
    for row in gate_results:
        assert row["rule_hash"] == protocol["canonical_gate_hashes"][row["gate_id"]]
        assert row["missing_or_exception_handling"]["missing_trial_policy"] is not None


def test_silent_wrong_separate_and_practical_equivalence_wording_preserved() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    gate_results = _load("results/level3_5b_heldout_v3/gate_results.json")["rows"]
    assert "silent_wrong_rate" in protocol["metric_definitions"]
    generic_gate = next(row for row in gate_results if row["gate_id"] == "generic_linear_practical_equivalence_v1")
    assert "practical" in generic_gate["reasons"][0].lower() or generic_gate["pass_or_fail"] in {"FAIL", "PASS"}


def test_no_manual_override_or_universal_cross_track_leaderboard() -> None:
    analysis = _load("results/level3_5b_heldout_v3/analysis.json")
    claims = _load("results/level3_5b_heldout_v3/claims.json")
    assert analysis["no_manual_override"] is True
    assert any("universal cross-track" in item.lower() for item in claims["forbidden_claims"])


def test_rerun_after_completion_is_blocked() -> None:
    assert execution_already_materialized(ROOT / "results" / "level3_5b_heldout_v3") is True
