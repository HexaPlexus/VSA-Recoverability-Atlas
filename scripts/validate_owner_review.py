from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_MODULE_DIR = ROOT / "src" / "cgrn_hsr"
if str(SRC_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_MODULE_DIR))

from release_artifacts import extract_markdown_headings  # noqa: E402


PAPER_DIR = ROOT / "paper"
OWNER_REVIEW_DIR = PAPER_DIR / "owner_review"
MAIN_FIGURE_PATH_PATTERN = re.compile(r"!\[[^\]]*\]\((figures/[^)]+)\)")

OWNER_STATUSES = {
    "PENDING_OWNER_REVIEW",
    "OWNER_APPROVED",
    "VISUAL_BLOCKER",
    "NON_BLOCKING_NOTE",
}


def load_json_yaml(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def embedded_figure_paths(markdown: str) -> set[str]:
    return set(MAIN_FIGURE_PATH_PATTERN.findall(markdown))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true", help="Fail if any manual owner review remains pending.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    required_paths = [
        PAPER_DIR / "manuscript.md",
        PAPER_DIR / "release_candidate" / "manuscript_rc1.md",
        PAPER_DIR / "FIGURE_MANIFEST.yaml",
        OWNER_REVIEW_DIR / "manuscript_annotated.md",
        OWNER_REVIEW_DIR / "OWNER_REVIEW_REGISTER.yaml",
        OWNER_REVIEW_DIR / "OWNER_VISUAL_SIGNOFF.md",
        OWNER_REVIEW_DIR / "REVIEWER_CRITIQUE_ACTIONS.md",
        OWNER_REVIEW_DIR / "FIGURE_INTEGRATION_AUDIT.md",
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing owner-review artifact: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    manifest = load_json_yaml(PAPER_DIR / "FIGURE_MANIFEST.yaml")
    register = load_json_yaml(OWNER_REVIEW_DIR / "OWNER_REVIEW_REGISTER.yaml")
    manuscript = (PAPER_DIR / "manuscript.md").read_text(encoding="utf-8")
    rc_manuscript = (PAPER_DIR / "release_candidate" / "manuscript_rc1.md").read_text(encoding="utf-8")
    annotated = (OWNER_REVIEW_DIR / "manuscript_annotated.md").read_text(encoding="utf-8")

    if manuscript != rc_manuscript:
        errors.append("Canonical and release-candidate manuscripts diverge.")
    if "[OWNER-CHECK:" in manuscript:
        errors.append("Canonical manuscript contains owner-review markers.")
    if "[OWNER-CHECK:" not in annotated:
        errors.append("Annotated manuscript is missing owner-review markers.")

    headings = set(extract_markdown_headings(manuscript))
    embedded = embedded_figure_paths(manuscript)
    figures = manifest.get("figures", [])
    main_text_figure_ids: list[str] = []
    for figure in figures:
        placement = figure.get("placement")
        figure_id = figure.get("figure_id", "<unknown>")
        section = figure.get("manuscript_section", "")
        if placement == "MAIN_TEXT":
            main_text_figure_ids.append(figure_id)
            if section not in headings:
                errors.append(f"Main-text figure {figure_id} references missing section {section!r}.")
            expected_path = f"figures/{figure_id}.png"
            if expected_path not in embedded:
                errors.append(f"Main-text figure {figure_id} is not embedded in manuscript.")
        elif placement == "SUPPLEMENT_ONLY":
            unexpected_path = f"figures/{figure_id}.png"
            if unexpected_path in embedded:
                errors.append(f"Supplement-only figure {figure_id} is embedded in main manuscript.")

    entries = register.get("entries", [])
    seen_ids: set[str] = set()
    pending_entries: list[str] = []
    figure_entries: set[str] = set()
    for entry in entries:
        review_id = entry.get("review_id")
        if review_id in seen_ids:
            errors.append(f"Duplicate owner review id: {review_id}")
        seen_ids.add(review_id)
        for field in {
            "review_id",
            "target",
            "section_or_figure",
            "category",
            "severity",
            "reason",
            "source_of_truth",
            "required_manual_action",
            "status",
            "owner_checked",
            "date",
            "notes",
        }:
            if field not in entry:
                errors.append(f"Owner review entry {review_id} missing field {field}.")
        status = entry.get("status")
        if status not in OWNER_STATUSES:
            errors.append(f"Unsupported owner-review status for {review_id}: {status}")
        if status == "PENDING_OWNER_REVIEW":
            pending_entries.append(review_id)
        if status == "VISUAL_BLOCKER":
            errors.append(f"Visual blocker remains open: {review_id}")
        if entry.get("category") == "FIGURE":
            section_or_figure = str(entry.get("section_or_figure", ""))
            match = re.search(r"Figure\s+(\d+)", section_or_figure)
            if match:
                figure_entries.add(f"figure{match.group(1)}")

    for figure_id in main_text_figure_ids:
        short_id = figure_id.split("_", 1)[0]
        if short_id not in figure_entries:
            errors.append(f"No owner-review FIGURE entry found for main-text figure {figure_id}.")

    if args.release and pending_entries:
        errors.append(
            "Owner release gate is still pending for: " + ", ".join(sorted(pending_entries))
        )
    elif pending_entries:
        warnings.append(
            "Pending owner review remains for: " + ", ".join(sorted(pending_entries))
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}")
    print(
        "Owner-review artifacts validated. "
        f"Main-text figures: {len(main_text_figure_ids)}. Pending owner checks: {len(pending_entries)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
