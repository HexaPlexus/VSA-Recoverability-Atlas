from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from cgrn_hsr.release_artifacts import canonical_sha256
from cgrn_hsr.level3_5b_heldout_confirmation import (
    LEVEL3_5B_HELDOUT_BLOCKED,
    evaluate_protocol_integrity,
)

ROOT = Path(__file__).resolve().parents[1]
HELDOUT_DIR = ROOT / "results" / "level3_5b_heldout"
DEV_DIR = ROOT / "results" / "level3_5b_dev"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_protocol_hashes_match_frozen_artifacts() -> None:
    payload = _load("results/level3_5b_heldout/protocol_integrity.json")
    for rel_path, item in payload["frozen_file_hashes"].items():
        assert item["exists"] is True
        assert isinstance(item["sha256"], str)
        assert len(item["sha256"]) == 64
        assert canonical_sha256(ROOT / rel_path)


def test_benchmark_blocks_on_mutated_protocol(tmp_path: Path) -> None:
    protocol = _load("results/level3_5b_dev/heldout_protocol.json")
    protocol["binary_track"]["methods"] = protocol["binary_track"]["methods"][:-1]
    mutated = tmp_path / "heldout_protocol.json"
    mutated.write_text(json.dumps(protocol, indent=2, sort_keys=True), encoding="utf-8")
    integrity = evaluate_protocol_integrity(ROOT, heldout_protocol_path=mutated)
    assert integrity["blocked"] is True
    assert integrity["override_hash_checks"]["heldout_protocol_hash_matches_canonical"] is False


def test_heldout_seeds_overlap_development_and_prior_and_block() -> None:
    payload = _load("results/level3_5b_heldout/analysis.json")
    assert payload["overall_verdict"] == LEVEL3_5B_HELDOUT_BLOCKED
    assert payload["blocked_because_protocol_internal_counts_mismatch"] is True
    assert payload["blocked_because_map_config_protocol_mismatch"] is True
    assert payload["blocked_because_heldout_overlaps_development"] is True
    assert payload["blocked_because_heldout_overlaps_prior"] is False
    assert payload["trials_executed"] == 0


def test_execution_manifest_created_before_trials() -> None:
    payload = _load("results/level3_5b_heldout/execution_manifest.json")
    assert payload["execution_authorized"] is False
    assert payload["blocked_before_trials"] is True
    assert payload["start_time"]


def test_methods_and_configs_loaded_only_from_frozen_protocol() -> None:
    manifest = _load("results/level3_5b_heldout/execution_manifest.json")
    protocol = _load("results/level3_5b_dev/heldout_protocol.json")
    assert manifest["methods"]["binary_track"] == protocol["binary_track"]["methods"]
    assert manifest["methods"]["map_track"] == protocol["map_track"]["methods"]
    assert manifest["trial_counts"]["binary_track"] == protocol["binary_track"]["trial_count_per_selected_point"]
    assert manifest["trial_counts"]["map_track"] == protocol["map_track"]["trial_count_per_selected_point"]


def test_adaptive_corruption_points_absent() -> None:
    manifest = _load("results/level3_5b_heldout/execution_manifest.json")
    protocol = _load("results/level3_5b_dev/heldout_protocol.json")
    assert manifest["corruption_points"] == {
        "binary_track": protocol["binary_track"]["corruption_points_by_cell"],
        "map_track": protocol["map_track"]["corruption_points_by_cell"],
    }


def test_bch_wrapper_and_configs_unchanged() -> None:
    payload = _load("results/level3_5b_heldout/protocol_integrity.json")
    assert payload["bch_configs_match"] is True
    assert payload["override_hash_checks"]["bch_configs_hash_matches_canonical"] is True


def test_raw_neco_and_generic_linear_decoders_unchanged() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_heldout_confirmation.py").read_text(encoding="utf-8")
    assert "def decode_neco(" not in source
    assert "def decode_generic(" not in source
    assert "noisy NeCo decoder" not in source


def test_map_configs_fully_match_frozen_protocol() -> None:
    payload = _load("results/level3_5b_heldout/protocol_integrity.json")
    assert payload["map_configs_match"] is False
    assert payload["seed_range_checks"]["map_seed_ranges_match"] is True


def test_bcf_blocked_track_not_run() -> None:
    payload = _load("results/level3_5b_heldout/bcf_status.json")
    assert payload["status"] == "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
    assert payload["executed"] is False


def test_outcome_taxonomy_preserves_silent_wrong_separately() -> None:
    protocol = _load("results/level3_5b_dev/heldout_protocol.json")
    assert "SILENT_WRONG" in protocol["outcome_taxonomy"]


def test_not_confirmed_is_not_upgraded_to_positive_claim() -> None:
    claims = _load("results/level3_5b_heldout/claims.json")
    joined = " ".join(claims["allowed_claims"] + claims["forbidden_claims"])
    assert "confirmed" not in joined.lower() or "No confirmatory native-noise claims were authorized from this stage." in claims["allowed_claims"]


def test_no_additional_seeds_or_trials_executed() -> None:
    assert (HELDOUT_DIR / "semantic_manifests.jsonl").read_text(encoding="utf-8") == ""
    assert (HELDOUT_DIR / "binary_trials.jsonl").read_text(encoding="utf-8") == ""
    assert (HELDOUT_DIR / "map_trials.jsonl").read_text(encoding="utf-8") == ""


def test_no_universal_raw_p_leaderboard() -> None:
    analysis = _load("results/level3_5b_heldout/analysis.json")
    claims = _load("results/level3_5b_heldout/claims.json")
    text = json.dumps(analysis) + json.dumps(claims)
    assert "leaderboard" not in text.lower()
    assert "No cross-track universal winner" not in claims["allowed_claims"]


def test_no_lcr_focus_cnm_u2_or_histogram_imports() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_heldout_confirmation.py").read_text(encoding="utf-8").lower()
    forbidden = ["lcr", "focus", "cnm", "u2", "histogram"]
    assert all(token not in source for token in forbidden)


def test_prior_development_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level3_5b_dev/*",
            "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
            "experiments/level3_5b_native_noise_frontiers.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""


def test_lcr_research_document_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "docs/research/LAZY_COMPOSITE_REIFICATION_HYPOTHESIS.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""
