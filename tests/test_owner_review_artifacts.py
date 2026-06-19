from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cgrn_hsr.release_artifacts import extract_claim_ids


ROOT = Path(__file__).resolve().parents[1]


def test_owner_review_validator_warns_but_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_owner_review.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Pending owner review remains" in result.stdout


def test_owner_review_release_mode_fails_until_manual_signoff() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_owner_review.py", "--release"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Owner release gate is still pending" in result.stdout


def test_canonical_manuscript_hides_claim_metadata() -> None:
    manuscript = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    rc_manuscript = (ROOT / "paper" / "release_candidate" / "manuscript_rc1.md").read_text(encoding="utf-8")
    assert "[claim:" not in manuscript
    assert "[claim:" not in rc_manuscript
    assert "claim_recoverability_resource_accounting" in extract_claim_ids(manuscript)
    assert manuscript == rc_manuscript


def test_main_text_figures_embedded_and_supplement_only_figure_excluded() -> None:
    manifest = json.loads((ROOT / "paper" / "FIGURE_MANIFEST.yaml").read_text(encoding="utf-8-sig"))
    manuscript = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    for figure in manifest["figures"]:
        path = f"figures/{figure['figure_id']}.png"
        if figure["placement"] == "MAIN_TEXT":
            assert path in manuscript
        else:
            assert path not in manuscript


def test_annotated_manuscript_contains_owner_markers_only_in_review_copy() -> None:
    canonical = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    annotated = (ROOT / "paper" / "owner_review" / "manuscript_annotated.md").read_text(encoding="utf-8")
    assert "[OWNER-CHECK:" not in canonical
    assert "[OWNER-CHECK:" in annotated
