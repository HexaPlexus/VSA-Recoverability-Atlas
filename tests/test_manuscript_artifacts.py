from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_evidence_registry.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_manuscript_figures_regenerate() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_manuscript_figures.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in [
        "figure1_budget_map.svg",
        "figure1_budget_map.png",
        "figure3_clean_f3_frontier.svg",
        "figure3_clean_f3_frontier.png",
        "figure5_escalation.svg",
        "figure5_escalation.png",
    ]:
        assert (ROOT / "paper" / "figures" / name).exists(), name


def test_release_candidate_bundle_exists() -> None:
    required = [
        ROOT / "paper" / "release_candidate" / "manuscript_rc1.md",
        ROOT / "paper" / "release_candidate" / "abstract.txt",
        ROOT / "paper" / "release_candidate" / "title_and_metadata.md",
        ROOT / "paper" / "release_candidate" / "references.bib",
        ROOT / "paper" / "review_packets" / "00_PLAIN_LANGUAGE_SYNOPSIS.md",
        ROOT / "paper" / "review_packets" / "01_TECHNICAL_ONE_PAGER.md",
        ROOT / "paper" / "review_packets" / "REVIEW_RESPONSE_FORM.md",
        ROOT / "paper" / "EXTERNAL_REVIEW_BUNDLE.md",
        ROOT / "paper" / "RELEASE_CANDIDATE_MANIFEST.yaml",
    ]
    for path in required:
        assert path.exists(), path
