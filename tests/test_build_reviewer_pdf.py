from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_reviewer_pdf.py"
SPEC = importlib.util.spec_from_file_location("build_reviewer_pdf", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_rewrite_markdown_links_commit_pins_repo_targets() -> None:
    text = (
        "[protocol](SYSTEMATIC_REVIEW_PROTOCOL.md)\n"
        "[results](../results/level3_2/)\n"
        "[doi](https://doi.org/10.1000/example)\n"
        "[mail](mailto:test@example.com)\n"
        "[anchor](#scope)\n"
        "![figure](figures/figure1_budget_map.png)\n"
    )

    rewritten, count = MODULE.rewrite_markdown_links(
        text,
        commit_sha="1234567890abcdef1234567890abcdef12345678",
        base_url="https://github.com/HexaPlexus/VSA-Recoverability-Atlas",
        link_source=ROOT / "paper" / "manuscript.md",
    )

    assert count == 2
    assert (
        "[protocol](https://github.com/HexaPlexus/VSA-Recoverability-Atlas/blob/"
        "1234567890abcdef1234567890abcdef12345678/paper/SYSTEMATIC_REVIEW_PROTOCOL.md)"
    ) in rewritten
    assert (
        "[results](https://github.com/HexaPlexus/VSA-Recoverability-Atlas/tree/"
        "1234567890abcdef1234567890abcdef12345678/results/level3_2)"
    ) in rewritten
    assert "[doi](https://doi.org/10.1000/example)" in rewritten
    assert "[mail](mailto:test@example.com)" in rewritten
    assert "[anchor](#scope)" in rewritten
    assert "![figure](figures/figure1_budget_map.png)" in rewritten


def test_local_source_paths_are_rejected() -> None:
    text = "[bad](file:///C:/Users/Thanatos/Desktop/CGRN-HSR/paper/manuscript.md)"

    try:
        MODULE.rewrite_markdown_links(
            text,
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            base_url="https://github.com/HexaPlexus/VSA-Recoverability-Atlas",
            link_source=ROOT / "paper" / "manuscript.md",
        )
    except ValueError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("Expected local reviewer-source path to be rejected.")
