from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cgrn_hsr.level3_5b_heldout_v2_confirmation import (
    EXPECTED_BCH_HASH,
    EXPECTED_MAP_HASHES,
    EXPECTED_PROTOCOL_V2_HASH,
    PROTOCOL_V2_PATH,
    execution_already_materialized,
)
from cgrn_hsr.level3_5b_protocol_repair import OLD_PROTOCOL_PATH

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_v2_hash_validation_passes() -> None:
    payload = _load("results/level3_5b_heldout_v2/protocol_integrity.json")
    assert payload["protocol_v2_hash_expected"] == EXPECTED_PROTOCOL_V2_HASH
    assert payload["protocol_v2_hash_observed"] == EXPECTED_PROTOCOL_V2_HASH
    assert payload["bch_hash_expected"] == EXPECTED_BCH_HASH
    assert payload["bch_hash_observed"] == EXPECTED_BCH_HASH
    assert payload["map_hashes_expected"] == EXPECTED_MAP_HASHES
    assert payload["map_hashes_observed"] == EXPECTED_MAP_HASHES


def test_old_v1_protocol_and_old_blocked_artifacts_remain_unchanged() -> None:
    payload = _load("results/level3_5b_heldout_v2/protocol_integrity.json")
    protocol_v2 = _load(PROTOCOL_V2_PATH)
    assert _sha256(ROOT / OLD_PROTOCOL_PATH) == protocol_v2["supersedes_protocol_hash"]
    assert payload["old_blocked_artifacts_unchanged"] is True


def test_protocol_repair_artifacts_remain_unchanged() -> None:
    payload = _load("results/level3_5b_heldout_v2/protocol_integrity.json")
    assert payload["repair_artifacts_unchanged"] is True
    assert payload["repair_validator_ready"] is True


def test_exact_seed_count_and_uniqueness_preserved() -> None:
    manifest = _load("results/level3_5b_heldout_v2/execution_manifest.json")
    all_seeds: list[int] = []
    for track_name in ("binary_track", "map_track"):
        for seeds in manifest["exact_concrete_seeds"][track_name].values():
            assert len(seeds) == 64
            assert len(set(seeds)) == 64
            all_seeds.extend(seeds)
    assert len(all_seeds) == len(set(all_seeds))


def test_zero_prior_seed_overlap_still_holds() -> None:
    seed_audit = _load("results/level3_5b_protocol_repair/seed_audit.json")
    assert seed_audit["audit_verdict"] == "PASS"
    for values in seed_audit["overlap_checks"].values():
        assert values == []


def test_execution_manifest_predates_trials_and_reports_block() -> None:
    manifest = _load("results/level3_5b_heldout_v2/execution_manifest.json")
    completion = _load("results/level3_5b_heldout_v2/completion_manifest.json")
    assert manifest["no_trial_had_yet_executed"] is True
    assert manifest["execution_authorized"] is False
    assert manifest["blocked_before_trials"] is True
    assert completion["executed_trials"] == 0
    assert completion["blocked_before_trials"] is True


def test_missing_gate_rules_causes_integrity_block() -> None:
    payload = _load("results/level3_5b_heldout_v2/protocol_integrity.json")
    assert payload["protocol_has_executable_gate_rules"] is False
    assert payload["blocked_because_missing_gate_rules"] is True
    assert payload["blocked"] is True
    assert any("lacks executable confirmatory gate semantics" in item for item in payload["integrity_failures"])


def test_no_trials_or_decoder_execution_occurred() -> None:
    analysis = _load("results/level3_5b_heldout_v2/analysis.json")
    for rel_path in (
        "results/level3_5b_heldout_v2/semantic_manifests.jsonl",
        "results/level3_5b_heldout_v2/binary_trials.jsonl",
        "results/level3_5b_heldout_v2/map_trials.jsonl",
    ):
        assert (ROOT / rel_path).read_text(encoding="utf-8") == ""
    assert analysis["benchmark_execution_invoked"] is False
    assert analysis["trials_executed"] == 0


def test_bcf_not_invoked_and_remains_blocked() -> None:
    payload = _load("results/level3_5b_heldout_v2/bcf_status.json")
    assert payload["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
    assert payload["executed"] is False


def test_only_frozen_metrics_and_gate_labels_are_loaded() -> None:
    protocol = _load(PROTOCOL_V2_PATH)
    integrity = _load("results/level3_5b_heldout_v2/protocol_integrity.json")
    verdicts = _load("results/level3_5b_heldout_v2/verdicts.json")
    analysis = _load("results/level3_5b_heldout_v2/analysis.json")
    assert integrity["frozen_metrics_loaded"] == protocol["metrics"]
    assert integrity["frozen_gates_loaded"] == protocol["gates"]
    assert verdicts["allowed_dispositions"] == protocol["gates"]
    assert analysis["frozen_metrics_and_gates_loaded_only"] is True


def test_rerun_after_completion_is_blocked() -> None:
    assert execution_already_materialized(ROOT / "results" / "level3_5b_heldout_v2") is True
