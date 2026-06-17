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
    assert manifest["execution_authorized"] is False
    assert completion["rerun_after_completion_forbidden"] is True
    assert completion["trials_executed_binary"] == 0
    assert completion["trials_executed_map"] == 0


def test_assigned_seed_lists_are_frozen_and_unique_even_though_no_trials_ran() -> None:
    manifest = _load("results/level3_5b_heldout_v3/execution_manifest.json")
    for track_name in ("binary_track", "map_track"):
        for cell_id, seeds in manifest["exact_concrete_seeds"][track_name].items():
            assert len(seeds) == 64
            assert len(set(seeds)) == 64


def test_no_trials_were_executed_and_no_replacement_or_extra_seeds_exist() -> None:
    binary_trials = _read_jsonl("results/level3_5b_heldout_v3/binary_trials.jsonl")
    map_trials = _read_jsonl("results/level3_5b_heldout_v3/map_trials.jsonl")
    assert binary_trials == []
    assert map_trials == []


def test_block_reason_is_the_contract_gate_dry_run_mismatch() -> None:
    verdicts = _load("results/level3_5b_heldout_v3/verdicts.json")
    assert verdicts["overall_verdict"] == "BLOCKED_BY_V3_PROTOCOL_INTEGRITY_FAILURE"
    assert any(
        "no_shared_noise_winner_contract_v1/contradictory_metrics_case" in item
        for item in verdicts["blocked_reason"]
    )


def test_truth_never_reached_decoders_because_runner_blocked_pretrial() -> None:
    analysis = _load("results/level3_5b_heldout_v3/analysis.json")
    assert analysis["benchmark_execution_invoked"] is False
    assert analysis["trials_executed"] == 0


def test_bcf_never_invoked_and_remains_blocked() -> None:
    payload = _load("results/level3_5b_heldout_v3/bcf_status.json")
    assert payload["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
    assert payload["executed"] is False


def test_gate_evaluation_was_not_invoked_after_integrity_block() -> None:
    assert (ROOT / "results" / "level3_5b_heldout_v3" / "gate_results.json").read_text(encoding="utf-8") == ""
    assert (ROOT / "results" / "level3_5b_heldout_v3" / "gate_inputs.json").read_text(encoding="utf-8") == ""


def test_silent_wrong_metric_still_exists_in_frozen_protocol() -> None:
    protocol = _load("results/level3_5b_gate_specification/heldout_protocol_v3.json")
    assert "silent_wrong_rate" in protocol["metric_definitions"]


def test_no_manual_override_and_no_confirmatory_claims_after_block() -> None:
    analysis = _load("results/level3_5b_heldout_v3/analysis.json")
    claims = _load("results/level3_5b_heldout_v3/claims.json")
    assert analysis["final_stage_status"] == "BLOCKED_BY_V3_PROTOCOL_INTEGRITY_FAILURE"
    assert any("no held-out v3 outcome was observed" in item.lower() for item in claims["allowed_claims"])


def test_rerun_after_completion_is_blocked() -> None:
    assert execution_already_materialized(ROOT / "results" / "level3_5b_heldout_v3") is True
