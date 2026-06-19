from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from cgrn_hsr.release_artifacts import canonical_sha256, extract_abstract, extract_markdown_headings, word_count


ROOT = Path(__file__).resolve().parents[1]


def _with_temp_worktree(callback) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        worktree = Path(temp_dir) / "artifact-worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), "HEAD"], cwd=ROOT, check=True)
        try:
            env = os.environ.copy()
            existing = env.get("PYTHONPATH", "")
            worktree_src = str(worktree / "src")
            env["PYTHONPATH"] = worktree_src if not existing else worktree_src + os.pathsep + existing
            callback(worktree, env)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


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
    def _check(worktree: Path, env: dict[str, str]) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/build_manuscript_figures.py"],
            cwd=worktree,
            env=env,
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
            assert (worktree / "paper" / "figures" / name).exists(), name

    _with_temp_worktree(_check)


def test_manuscript_figures_are_byte_deterministic() -> None:
    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _check(worktree: Path, env: dict[str, str]) -> None:
        subprocess.run(
            [sys.executable, "scripts/build_manuscript_figures.py"],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        targets = [
            worktree / "paper" / "figures" / "figure1_budget_map.png",
            worktree / "paper" / "figures" / "figure1_budget_map.svg",
            worktree / "paper" / "figures" / "figure6_architecture_flow.png",
            worktree / "paper" / "figures" / "figure6_architecture_flow.svg",
        ]
        first_hashes = {path.name: _digest(path) for path in targets}
        subprocess.run(
            [sys.executable, "scripts/build_manuscript_figures.py"],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        second_hashes = {path.name: _digest(path) for path in targets}
        assert second_hashes == first_hashes

    _with_temp_worktree(_check)


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


def test_workflow_uses_full_history_checkout() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in workflow
    assert "python scripts/build_release_candidate.py" in workflow
    assert "git diff --exit-code" in workflow
    assert workflow.index("python -m pytest -q") < workflow.index("python scripts/build_manuscript_figures.py")
    assert workflow.index("python scripts/build_manuscript_figures.py") < workflow.index(
        "python scripts/build_release_candidate.py"
    )
    assert workflow.index("python scripts/build_release_candidate.py") < workflow.index("git diff --exit-code")


def test_canonical_hash_is_line_ending_independent(tmp_path: Path) -> None:
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_text("alpha\nbeta\ngamma\n", encoding="utf-8", newline="\n")
    crlf.write_text("alpha\r\nbeta\r\ngamma\r\n", encoding="utf-8", newline="")
    assert canonical_sha256(lf) == canonical_sha256(crlf)


def test_release_candidate_rebuild_and_manifest() -> None:
    def _check(worktree: Path, env: dict[str, str]) -> None:
        subprocess.run(
            [sys.executable, "scripts/build_release_candidate.py"],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        manuscript = (worktree / "paper" / "manuscript.md").read_text(encoding="utf-8")
        rc_manuscript = (worktree / "paper" / "release_candidate" / "manuscript_rc1.md").read_text(encoding="utf-8")
        rc_abstract = (worktree / "paper" / "release_candidate" / "abstract.txt").read_text(encoding="utf-8").strip()
        assert rc_manuscript == manuscript
        assert rc_abstract == extract_abstract(manuscript)

        manifest = json.loads((worktree / "paper" / "RELEASE_CANDIDATE_MANIFEST.yaml").read_text(encoding="utf-8-sig"))
        generated_from_commit = manifest["generated_from_commit"]
        subprocess.run(
            ["git", "cat-file", "-e", f"{generated_from_commit}^{{commit}}"],
            cwd=worktree,
            check=True,
        )
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", generated_from_commit, "HEAD"],
            cwd=worktree,
            check=True,
        )

    _with_temp_worktree(_check)


def test_release_candidate_rebuild_allows_generated_figure_drift() -> None:
    def _check(worktree: Path, env: dict[str, str]) -> None:
        subprocess.run(
            [sys.executable, "scripts/build_manuscript_figures.py"],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, "scripts/build_release_candidate.py"],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    _with_temp_worktree(_check)


def test_review_packet_sections_resolve() -> None:
    manuscript = (ROOT / "paper" / "release_candidate" / "manuscript_rc1.md").read_text(encoding="utf-8")
    headings = set(extract_markdown_headings(manuscript))
    for packet in [
        ROOT / "paper" / "review_packets" / "00_PLAIN_LANGUAGE_SYNOPSIS.md",
        ROOT / "paper" / "review_packets" / "01_TECHNICAL_ONE_PAGER.md",
        ROOT / "paper" / "review_packets" / "A_MAP_RESONATOR_REVIEW.md",
        ROOT / "paper" / "review_packets" / "B_BCF_GSBC_REVIEW.md",
        ROOT / "paper" / "review_packets" / "C_EXPERIMENTAL_METHODS_REVIEW.md",
        ROOT / "paper" / "review_packets" / "D_SYSTEMATIC_MAPPING_REVIEW.md",
        ROOT / "paper" / "review_packets" / "E_HARDWARE_REVIEW.md",
        ROOT / "paper" / "review_packets" / "F_GENERAL_READER_REVIEW.md",
    ]:
        text = packet.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        assert match is not None, packet
        sections = re.findall(r'- "([^"]+)"', match.group(1))
        for section in sections:
            assert section in headings, (packet.name, section)


def test_hardware_scope_markers_present() -> None:
    manuscript = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8").lower()
    assert "literature-only" in manuscript
    assert "not measured in this repository" in manuscript


def test_word_counts_use_full_manuscript() -> None:
    manuscript = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    rc_manuscript = (ROOT / "paper" / "release_candidate" / "manuscript_rc1.md").read_text(encoding="utf-8")
    abstract = extract_abstract(manuscript)
    assert 200 <= word_count(abstract) <= 300
    assert word_count(manuscript) >= 7000
    assert word_count(rc_manuscript) == word_count(manuscript)


def test_build_evidence_tables_does_not_mutate_canonical_manuscript() -> None:
    manuscript_before = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, "scripts/build_evidence_tables.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    manuscript_after = (ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8")
    assert manuscript_after == manuscript_before


def test_historical_commit_references_are_public_ancestors() -> None:
    for sha in [
        "dea30d8",
        "5d54748",
        "8b7b24a",
        "86efbb8",
        "a3ca3b3",
        "2b8d6f9",
        "d6f222f",
        "8fcef7e",
        "1104049",
        "ccf3730",
        "f8c4c0e",
        "52060ef",
        "c6a24d7",
        "19bcb16",
        "85b5334",
        "3914e7264fd6a5ee41fe2d99001b0b4c766ce7d2",
    ]:
        subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT, check=True)
        subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT, check=True)


def test_validator_passes_in_fresh_worktree() -> None:
    if os.environ.get("CGRN_HSR_SKIP_NESTED_WORKTREE_TEST") == "1":
        return
    with tempfile.TemporaryDirectory() as temp_dir:
        worktree = Path(temp_dir) / "clean-checkout"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), "HEAD"], cwd=ROOT, check=True)
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(worktree / "src")
            env["CGRN_HSR_SKIP_NESTED_WORKTREE_TEST"] = "1"
            result = subprocess.run(
                [sys.executable, "scripts/validate_evidence_registry.py"],
                cwd=worktree,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "tests/test_manuscript_artifacts.py"],
                cwd=worktree,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)
