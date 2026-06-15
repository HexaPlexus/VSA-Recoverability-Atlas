from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_seam_l_is_decomposed() -> None:
    payload = _load("results/level2b0/final_verdicts.json")
    seam_ids = [row["id"] for row in payload["seam_L_decomposition"]]
    assert seam_ids == [f"L{i}" for i in range(1, 11)]


def test_broad_build_verdict_is_absent() -> None:
    payload = _load("results/level2b0/final_verdicts.json")
    assert payload["general_mechanism_routing"] != "BUILD"
    build_rows = [row for row in payload["seam_L_decomposition"] if row["verdict"] == "BUILD"]
    assert len(build_rows) == 1
    assert build_rows[0]["id"] == "L10"


def test_algorithm_selection_prior_art_recorded() -> None:
    payload = _load("results/level2b0/meta_control_overlap.json")
    assert payload["meta_control_prior_art"]["per_instance_algorithm_selection"]["recorded"] is True


def test_rational_metareasoning_prior_art_recorded() -> None:
    payload = _load("results/level2b0/meta_control_overlap.json")
    assert payload["meta_control_prior_art"]["rational_metareasoning"]["recorded"] is True


def test_adaptive_computation_prior_art_recorded() -> None:
    payload = _load("results/level2b0/meta_control_overlap.json")
    assert payload["meta_control_prior_art"]["anytime_and_adaptive_computation"]["recorded"] is True


def test_engineering_and_research_classifications_separated() -> None:
    payload = _load("results/level2b0/final_verdicts.json")
    classes = {row["classification"] for row in payload["engineering_vs_research"]}
    assert "ENGINEERING INTEGRATION" in classes
    assert "RESEARCH PROTOTYPE" in classes


def test_no_runtime_controller_added() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "meta_controller.py").exists()
    assert not (ROOT / "src" / "cgrn_hsr" / "entity_resolution.py").exists()


def test_cnm_marked_deferred() -> None:
    payload = _load("results/level2b0/final_verdicts.json")
    assert payload["cnm"] == "DEFERRED"
    closure = (ROOT / "docs" / "LEVEL2B_RESEARCH_CLOSURE.md").read_text(encoding="utf-8")
    assert "CNM: `DEFERRED`" in closure


def test_level1_and_level2a_artifacts_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level1a", "results/level1b", "results/level1c", "results/level1d", "results/level1e", "results/level1e1", "results/level1f", "results/level1f2_bcf_audit", "results/level1f3", "results/level1f4", "results/level2a"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_git_status_clean_after_commit_can_be_satisfied() -> None:
    result = subprocess.run(
        ["git", "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    assert "CGRN-HSR_CNM_research_spec.md" not in result
