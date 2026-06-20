from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_MODULE_DIR = ROOT / "src" / "cgrn_hsr"
if str(SRC_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_MODULE_DIR))

from release_artifacts import (  # noqa: E402
    canonical_sha256,
    extract_abstract,
    extract_table_captions,
)


PAPER_DIR = ROOT / "paper"
FIGURE_DIR = PAPER_DIR / "figures"
RELEASE_DIR = PAPER_DIR / "release_candidate"
RELEASE_FIGURE_DIR = RELEASE_DIR / "figures"
ALLOWED_DIRTY_OUTPUTS = {
    "paper/RELEASE_CANDIDATE_MANIFEST.yaml",
    "paper/release_candidate/abstract.txt",
    "paper/release_candidate/figure_captions.md",
    "paper/release_candidate/manuscript_rc1.md",
    "paper/release_candidate/table_captions.md",
    "paper/release_candidate/references.bib",
    "paper/release_candidate/release_notes.md",
    "paper/release_candidate/title_and_metadata.md",
}


def is_release_output_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.startswith("paper/figures/")
        or normalized.startswith("paper/release_candidate/figures/")
        or normalized in ALLOWED_DIRTY_OUTPUTS
    )


def resolve_generated_from_commit() -> str:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    while True:
        changed = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if not changed:
            return commit
        if any(not is_release_output_path(path) for path in changed):
            return commit
        parent = subprocess.run(
            ["git", "rev-parse", f"{commit}^"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if parent.returncode != 0:
            return commit
        commit = parent.stdout.strip()


def require_clean_tree() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        raise RuntimeError("Could not determine git working tree status.")

    blocking_paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if is_release_output_path(path):
            continue
        if line.startswith("?? "):
            blocking_paths.append(path)
            continue
        worktree_diff = subprocess.run(
            ["git", "diff", "--quiet", "--ignore-cr-at-eol", "--", path],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        index_diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--ignore-cr-at-eol", "--", path],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if worktree_diff.returncode == 0 and index_diff.returncode == 0:
            continue
        blocking_paths.append(path)
    if blocking_paths:
        formatted = "\n".join(f"- {path}" for path in blocking_paths)
        raise RuntimeError(
            "build_release_candidate.py requires a clean working tree. "
            "Commit source changes first or use --allow-dirty only during local repair.\n"
            f"Blocking paths:\n{formatted}"
        )


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_title_and_metadata() -> str:
    return """# Release Candidate Metadata

## Title

Recoverability Has a Cost: An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures

## Repository identity

- Public project title: `VSA Recoverability Atlas`
- Legacy Python namespace: `cgrn_hsr`
- Release-candidate label: `external-review-rc1`
- Scientific status: development evidence atlas plus systematic mapping; no new experiments were run for this package

## Owner decisions still required

- Public author name: `<OWNER_DECISION_REQUIRED>`
- Research pseudonym, if used: `<OWNER_DECISION_REQUIRED>`
- Affiliation: `<OWNER_DECISION_REQUIRED>`
- Corresponding author: `<OWNER_DECISION_REQUIRED>`
- Contact email: `<OWNER_DECISION_REQUIRED>`
- ORCID: `<OWNER_DECISION_REQUIRED>`
- Public repository URL: `<OWNER_DECISION_REQUIRED>`
- Preprint platform: `<OWNER_DECISION_REQUIRED>`
- Target venue: `<OWNER_DECISION_REQUIRED>`

## Release boundaries

- No public upload was performed.
- No external outreach was sent automatically.
- No frozen experiment outputs, raw trial data, or held-out artifacts were modified.
- Official held-out execution count remains unchanged.

## Citation boundary

This package is suitable for technical external review of scope, evidence framing, manuscript clarity, and bibliography completeness. It is not yet the final submission package for a venue or preprint server.
"""


def build_release_notes() -> str:
    return """# Release Candidate Notes

## Package identity

- Package: `external-review-rc1`
- Source manuscript: `paper/manuscript.md`
- Branch intent: external technical review only

## What this package is for

- specialist section review
- bibliography and claim-scope review
- preprint-readiness editing
- venue-neutral technical feedback

## What this package is not for

- public repository launch
- automated outreach
- new experiments
- revised scientific claims beyond the current evidence atlas

## Known boundaries

- bibliography is substantially hardened but still needs final owner visual review
- the publication PDF pipeline now uses Pandoc, Tectonic, and deterministic qpdf normalization
- owner preprint-platform and venue decisions remain open
- dedicated history-aware secret scanning is still pending
- no public upload or outreach action was performed in this stage

## Recommended conversion path

The canonical reviewer PDF is built from `paper/manuscript.md` through the publication pipeline in `scripts/build_manuscript.py`. The release-candidate markdown bundle remains useful for technical review and source inspection before venue-specific packaging.
"""


def build_figure_captions() -> str:
    payload = load_json(PAPER_DIR / "FIGURE_MANIFEST.yaml")
    lines = ["# Figure Captions", ""]
    for figure in payload["figures"]:
        lines.append(f"## {figure['title']}")
        lines.append("")
        lines.append(str(figure["caption"]).strip())
        lines.append("")
    return "\n".join(lines)


def build_table_captions(manuscript_text: str) -> str:
    lines = ["# Table Captions", ""]
    for title, body in extract_table_captions(manuscript_text):
        lines.append(f"## {title}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def build_manifest(generated_from_commit: str) -> dict[str, object]:
    release_paths = [
        "paper/release_candidate/manuscript_rc1.md",
        "paper/release_candidate/abstract.txt",
        "paper/release_candidate/title_and_metadata.md",
        "paper/release_candidate/references.bib",
        "paper/release_candidate/figure_captions.md",
        "paper/release_candidate/table_captions.md",
        "paper/release_candidate/release_notes.md",
    ]
    release_hashes = {rel: canonical_sha256(ROOT / rel) for rel in release_paths}
    figure_hashes = {
        f"paper/release_candidate/figures/{path.name}": canonical_sha256(path)
        for path in sorted(RELEASE_FIGURE_DIR.iterdir())
        if path.is_file()
    }
    return {
        "schema_version": "vsa-recoverability-atlas-rc-manifest-v0.1",
        "generated_from_commit": generated_from_commit,
        "generated_from_commit_semantics": (
            "Ancestor commit whose clean tracked inputs were used to build the release candidate artifacts."
        ),
        "generation_date": "2026-06-19",
        "held_out_status": {
            "official_held_out_execution_count": 0,
            "note": "unchanged in this stage",
        },
        "release_candidate_hashes": release_hashes,
        "reference_hash": canonical_sha256(PAPER_DIR / "references.bib"),
        "claim_ledger_hash": canonical_sha256(PAPER_DIR / "claim_ledger.yaml"),
        "evidence_registry_hash": canonical_sha256(PAPER_DIR / "evidence_registry.yaml"),
        "supplement_hash": canonical_sha256(PAPER_DIR / "supplementary_evidence_atlas.md"),
        "figure_hashes": figure_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    if not args.allow_dirty:
        require_clean_tree()

    generated_from_commit = resolve_generated_from_commit()

    manuscript_text = (PAPER_DIR / "manuscript.md").read_text(encoding="utf-8")
    abstract_text = extract_abstract(manuscript_text)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(PAPER_DIR / "manuscript.md", RELEASE_DIR / "manuscript_rc1.md")
    write_text(RELEASE_DIR / "abstract.txt", abstract_text)
    write_text(RELEASE_DIR / "title_and_metadata.md", build_title_and_metadata())
    shutil.copyfile(PAPER_DIR / "references.bib", RELEASE_DIR / "references.bib")
    write_text(RELEASE_DIR / "figure_captions.md", build_figure_captions())
    write_text(RELEASE_DIR / "table_captions.md", build_table_captions(manuscript_text))
    write_text(RELEASE_DIR / "release_notes.md", build_release_notes())

    for path in RELEASE_FIGURE_DIR.iterdir():
        if path.is_file():
            path.unlink()
    for source in FIGURE_DIR.iterdir():
        if source.is_file() and source.suffix.lower() in {".pdf", ".png"}:
            shutil.copyfile(source, RELEASE_FIGURE_DIR / source.name)

    manifest = build_manifest(generated_from_commit)
    write_text(PAPER_DIR / "RELEASE_CANDIDATE_MANIFEST.yaml", json.dumps(manifest, indent=2))
    print("Built release candidate in", RELEASE_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
