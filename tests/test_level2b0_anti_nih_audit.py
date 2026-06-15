from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cgrn_hsr.level2b0_audit import (
    LEVEL2B0_SCHEMA_VERSION,
    REQUIREMENT_MATRIX,
    build_architecture_overlap_markdown,
    build_prior_art_matrix_markdown,
    build_research_seam_markdown,
    write_level2b0_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_requirement_has_a_verdict() -> None:
    assert REQUIREMENT_MATRIX
    assert all(row["verdict"] for row in REQUIREMENT_MATRIX)


def test_every_build_verdict_has_documented_mismatch() -> None:
    build_rows = [row for row in REQUIREMENT_MATRIX if row["verdict"] == "BUILD"]
    assert build_rows
    assert all(row["mismatch"] for row in build_rows)


def test_no_custom_resolver_implementation_added() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "entity_resolution.py").exists()


def test_smoke_adapters_are_minimal() -> None:
    experiment_source = (ROOT / "experiments" / "level2b0_prior_art_audit.py").read_text(encoding="utf-8")
    assert "write_level2b0_artifacts" in experiment_source
    assert "torchhd" not in experiment_source
    assert "stonesoup" not in experiment_source


def test_no_level2a_artifacts_changed() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level2a", "docs/LEVEL2A*"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_no_bcf_invocation() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level2b0_audit.py").read_text(encoding="utf-8").lower()
    assert "ibm_bcf" not in source
    assert "single_product_shootout" not in source


def test_hypothesis_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_aborted_pre_audit_code_is_not_active_mainline() -> None:
    analysis = _load(ROOT / "results" / "level2b0" / "analysis.json")
    aborted = analysis["aborted_pre_audit_level2b"]
    assert aborted["active_mainline_detected"] is False
    assert aborted["patch_saved"] is False


def test_artifacts_can_be_regenerated() -> None:
    payloads = write_level2b0_artifacts(ROOT)
    assert payloads["analysis.json"]["schema_version"] == LEVEL2B0_SCHEMA_VERSION


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL2B0_PRIOR_ART_MATRIX.md",
        "docs/LEVEL2B0_ARCHITECTURE_OVERLAP.md",
        "docs/LEVEL2B0_RESEARCH_SEAM.md",
        "results/level2b0/dependency_audit.json",
        "results/level2b0/capability_matrix.json",
        "results/level2b0/smoke_results.json",
        "results/level2b0/verdicts.json",
        "results/level2b0/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_markdown_outputs_include_core_sections() -> None:
    assert "Requirement" in build_prior_art_matrix_markdown()
    assert "Overlap map" in build_architecture_overlap_markdown()
    assert "Candidate seam" in build_research_seam_markdown()
