from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from cgrn_hsr.level3_5b_protocol_repair import (
    ALLOWED_DIFF_TYPES,
    BCH_CONFIG_PATH,
    OLD_PROTOCOL_PATH,
    TRANSITION_PATH,
    build_complete_map_config_records,
    build_protocol_diff,
    canonical_json_hash,
    read_json,
    validate_protocol_repair,
)

ROOT = Path(__file__).resolve().parents[1]
REPAIR_DIR = ROOT / "results" / "level3_5b_protocol_repair"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_old_protocol_unchanged() -> None:
    validator = _load("results/level3_5b_protocol_repair/validator_result.json")
    assert validator["old_protocol_unchanged_hash"] is True


def test_blocked_heldout_artifacts_unchanged() -> None:
    validator = _load("results/level3_5b_protocol_repair/validator_result.json")
    assert validator["old_blocked_artifacts_unchanged_in_git_diff"] is True


def test_no_heldout_trial_rows_exist_before_repair() -> None:
    validator = _load("results/level3_5b_protocol_repair/validator_result.json")
    assert validator["zero_heldout_trials_before_repair"] is True


def test_v2_corruption_points_equal_v1() -> None:
    v1 = _load(OLD_PROTOCOL_PATH)
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    assert v2["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"] == v1["binary_track"]["corruption_points_by_cell"]
    assert v2["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"] == v1["map_track"]["corruption_points_by_cell"]


def test_v2_methods_equal_v1() -> None:
    v1 = _load(OLD_PROTOCOL_PATH)
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    assert v2["preserved_scientific_fields"]["binary_track"]["methods"] == v1["binary_track"]["methods"]
    assert v2["preserved_scientific_fields"]["map_track"]["methods"] == v1["map_track"]["methods"]


def test_v2_gates_and_metrics_equal_frozen() -> None:
    v1 = _load(OLD_PROTOCOL_PATH)
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    blocked_verdicts = _load("results/level3_5b_heldout/verdicts.json")
    assert v2["gates"] == blocked_verdicts["allowed_dispositions"]
    assert v2["metrics"]["binary_track"] == v1["binary_track"]["primary_metrics"]
    assert v2["metrics"]["map_track"] == v1["map_track"]["primary_metrics"]
    assert v2["metrics"]["outcome_taxonomy"] == v1["outcome_taxonomy"]


def test_trial_count_equals_seed_count() -> None:
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    for spec in v2["fresh_seed_ranges"]["binary_track"].values():
        assert spec["count"] == v2["trial_counts"]["binary_track"] == 64
    for spec in v2["fresh_seed_ranges"]["map_track"].values():
        assert spec["count"] == v2["trial_counts"]["map_track"] == 64


def test_64_unique_binary_and_map_seeds_per_cell() -> None:
    audit = _load("results/level3_5b_protocol_repair/seed_audit.json")
    assert all(count == 64 for count in audit["counts"]["binary"].values())
    assert all(count == 64 for count in audit["counts"]["map"].values())
    assert audit["uniqueness_checks"]["binary_unique"] is True
    assert audit["uniqueness_checks"]["map_unique"] is True
    assert audit["uniqueness_checks"]["combined_unique"] is True


def test_zero_overlap_with_development_and_prior() -> None:
    audit = _load("results/level3_5b_protocol_repair/seed_audit.json")
    for values in audit["overlap_checks"].values():
        assert values == []


def test_exact_map_config_hashes() -> None:
    frozen_dev = _load("results/level3_5b_dev/frozen_development_protocol.json")
    expected = build_complete_map_config_records(ROOT, frozen_dev)
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    assert v2["config_hashes"]["map_arm_hashes"] == {arm_id: row["config_hash"] for arm_id, row in expected.items()}


def test_unchanged_bch_hashes() -> None:
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    validator = _load("results/level3_5b_protocol_repair/validator_result.json")
    assert (ROOT / BCH_CONFIG_PATH).exists()
    assert isinstance(v2["config_hashes"]["bch_configs_hash"], str)
    assert len(v2["config_hashes"]["bch_configs_hash"]) == 64
    assert validator["bch_hash_unchanged"] is True


def test_bcf_remains_blocked() -> None:
    v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    assert v2["fresh_seed_ranges"]["bcf_track"]["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
    assert v2["fresh_seed_ranges"]["bcf_track"]["execution_authorized"] is False


def test_unsupported_protocol_diff_classification_fails() -> None:
    old_protocol = _load(OLD_PROTOCOL_PATH)
    old_analysis = _load("results/level3_5b_heldout/analysis.json")
    preserved_fields = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")["preserved_scientific_fields"]
    seed_audit = _load("results/level3_5b_protocol_repair/seed_audit.json")
    protocol_v2 = _load("results/level3_5b_protocol_repair/heldout_protocol_v2.json")
    complete_map_configs = protocol_v2["complete_config_records"]["map_track"]
    protocol_diff = build_protocol_diff(
        protocol_v2["supersedes_protocol_hash"],
        canonical_json_hash(protocol_v2),
        protocol_v2["fresh_seed_ranges"]["binary_track"],
        protocol_v2["fresh_seed_ranges"]["map_track"],
    )
    protocol_diff["rows"][0]["change_type"] = "ILLEGAL_CHANGE"
    validator = validate_protocol_repair(
        ROOT,
        old_protocol=old_protocol,
        old_blocked_analysis=old_analysis,
        preserved_fields=preserved_fields,
        seed_audit=seed_audit,
        protocol_v2=protocol_v2,
        protocol_diff=protocol_diff,
        complete_map_configs=complete_map_configs,
    )
    assert validator["validator_verdict"] == "BLOCKED_REPAIR_REQUIRES_REDESIGN"
    assert validator["unsupported_protocol_diff_types"] == ["ILLEGAL_CHANGE"]


def test_benchmark_execution_not_invoked() -> None:
    analysis = _load("results/level3_5b_protocol_repair/analysis.json")
    validator = _load("results/level3_5b_protocol_repair/validator_result.json")
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_protocol_repair.py").read_text(encoding="utf-8")
    assert analysis["benchmark_execution_invoked"] is False
    assert validator["benchmark_execution_invoked"] is False
    assert "run_level3_5b_dev(" not in source
    assert "run_level3_5b_heldout(" not in source


def test_protocol_diff_classifications_allowed() -> None:
    payload = _load("results/level3_5b_protocol_repair/protocol_diff.json")
    assert set(payload["allowed_change_types"]) == ALLOWED_DIFF_TYPES
    assert all(row["change_type"] in ALLOWED_DIFF_TYPES for row in payload["rows"])


def test_old_blocked_artifacts_and_doc_not_modified_in_git() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level3_5b_heldout", "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""
