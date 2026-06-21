from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
BUILD_DIR = PAPER_DIR / "build"
RELEASE_DIR = PAPER_DIR / "release_candidate"
SUBMISSION_DIR = PAPER_DIR / "submission_bundle"
MANUSCRIPT_PATH = PAPER_DIR / "manuscript.md"
METADATA_PATH = PAPER_DIR / "metadata.yaml"
TEMPLATE_PATH = PAPER_DIR / "latex" / "template.tex"
REFERENCES_PATH = PAPER_DIR / "references.bib"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR = PAPER_DIR / "tables"
BASE_URL = "https://github.com/HexaPlexus/VSA-Recoverability-Atlas"
DISALLOWED_URI_SNIPPETS = (
    "file:",
    "file:///",
    "c:\\",
    "c:/",
    "d:\\",
    "d:/",
    "/users/",
    "/home/",
    "/mnt/",
    "localhost",
    "127.0.0.1",
    "vscode:",
    "sandbox:",
)


def resolve_tool(explicit: str | None, *, env_var: str, executable: str) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"Tool not found: {path}")
    if env_value := os.environ.get(env_var):
        path = Path(env_value).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"{env_var} points to a missing tool: {path}")
    resolved = shutil.which(executable)
    if resolved:
        return Path(resolved).resolve()
    raise FileNotFoundError(
        f"Could not find '{executable}'. Pass --{executable}, set {env_var}, or install it on PATH. "
        "See paper/BUILDING.md for the publication toolchain requirements."
    )


def resolve_commit(ref: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", ref],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def resolve_commit_timestamp(ref: str) -> str:
    return subprocess.run(
        ["git", "show", "-s", "--format=%ct", ref],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def require_clean_tree() -> None:
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("build_manuscript.py requires a clean working tree unless --allow-dirty is set.")


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_uses_preserved_scheme(target: str) -> bool:
    if target.startswith("#"):
        return True
    scheme = urlparse(target).scheme
    return scheme in {"http", "https", "mailto"}


def target_is_disallowed_local_reference(target: str) -> bool:
    lowered = target.lower()
    return any(snippet in lowered for snippet in DISALLOWED_URI_SNIPPETS)


def build_commit_pinned_url(target: str, *, commit_sha: str, link_source: Path) -> str:
    if target_uses_preserved_scheme(target):
        return target
    if target_is_disallowed_local_reference(target):
        raise ValueError(f"Local or private link is not allowed in manuscript output: {target}")
    fragment = ""
    if "#" in target:
        target, fragment = target.split("#", 1)
    resolved = (link_source.parent / target).resolve()
    resolved.relative_to(ROOT)
    if not resolved.exists():
        raise FileNotFoundError(f"Relative link target does not exist: {target}")
    relpath = resolved.relative_to(ROOT).as_posix()
    kind = "tree" if resolved.is_dir() else "blob"
    url = f"{BASE_URL}/{kind}/{commit_sha}/{relpath}"
    if fragment:
        url = f"{url}#{fragment}"
    return url


def rewrite_links(markdown_text: str, *, commit_sha: str, link_source: Path) -> str:
    import re

    pattern = re.compile(r"(?P<prefix>!?)\[(?P<label>[^\]]+)\]\((?P<target><[^>]+>|[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)")

    def replace(match: re.Match[str]) -> str:
        if match.group("prefix") == "!":
            return match.group(0)
        target = match.group("target")
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        rewritten = build_commit_pinned_url(target, commit_sha=commit_sha, link_source=link_source)
        title = match.group("title") or ""
        return f"[{match.group('label')}]({rewritten}{title})"

    return pattern.sub(replace, markdown_text)


def strip_front_matter_headings(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    start = 0
    for index, line in enumerate(lines):
        if line.strip() == "## 1. Introduction":
            start = index
            break
    return "\n".join(lines[start:]).lstrip() + "\n"


def copy_tree_contents(source: Path, target: Path, suffixes: set[str] | None = None) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir()):
        if item.is_file():
            if suffixes is None or item.suffix.lower() in suffixes:
                shutil.copy2(item, target / item.name)
        elif item.is_dir():
            shutil.copytree(item, target / item.name)


def sync_build_assets() -> None:
    copy_tree_contents(FIGURES_DIR, BUILD_DIR / "figures", suffixes={".pdf", ".png"})
    if TABLES_DIR.exists():
        copy_tree_contents(TABLES_DIR, BUILD_DIR / "tables", suffixes={".tex"})


def render_publication_figures() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_manuscript_figures.py")],
        cwd=ROOT,
        check=True,
    )


def build_runtime_metadata(*, commit_sha: str) -> Path:
    payload = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("paper/metadata.yaml must deserialize to a mapping.")
    payload["build_commit"] = commit_sha
    payload["repository_commit_url"] = f"{BASE_URL}/tree/{commit_sha}"
    runtime_metadata_path = BUILD_DIR / "metadata.runtime.yaml"
    runtime_metadata_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    return runtime_metadata_path


def collect_figure_hashes() -> dict[str, str]:
    figure_hashes: dict[str, str] = {}
    for figure in sorted(FIGURES_DIR.iterdir()):
        if figure.is_file() and figure.suffix.lower() == ".pdf":
            figure_hashes[figure.name] = canonical_sha256(figure)
    return figure_hashes


def tool_version(binary: Path) -> str:
    result = subprocess.run(
        [str(binary), "--version"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().splitlines()[0]


def write_build_manifest(
    *,
    commit_sha: str,
    metadata_path: Path,
    pdf_path: Path,
    pandoc: Path,
    tectonic: Path,
    qpdf: Path,
) -> None:
    manifest = {
        "commit": commit_sha,
        "manuscript_hash": canonical_sha256(MANUSCRIPT_PATH),
        "references_hash": canonical_sha256(REFERENCES_PATH),
        "metadata_hash": canonical_sha256(metadata_path),
        "figure_hashes": collect_figure_hashes(),
        "pdf_hash": canonical_sha256(pdf_path),
        "pandoc_version": tool_version(pandoc),
        "tectonic_version": tool_version(tectonic),
        "qpdf_version": tool_version(qpdf),
    }
    (BUILD_DIR / "publication_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_submission_bundle(tex_path: Path, pdf_path: Path, metadata_path: Path) -> None:
    figures_dir = SUBMISSION_DIR / "figures"
    tables_dir = SUBMISSION_DIR / "tables"
    if SUBMISSION_DIR.exists():
        shutil.rmtree(SUBMISSION_DIR)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tex_path, SUBMISSION_DIR / "manuscript.tex")
    shutil.copy2(REFERENCES_PATH, SUBMISSION_DIR / "references.bib")
    shutil.copy2(metadata_path, SUBMISSION_DIR / "metadata.yaml")
    shutil.copy2(PAPER_DIR / "BUILDING.md", SUBMISSION_DIR / "BUILDING.md")
    for figure in sorted(FIGURES_DIR.iterdir()):
        if figure.is_file() and figure.suffix.lower() == ".pdf":
            shutil.copy2(figure, figures_dir / figure.name)
    if TABLES_DIR.exists():
        for table in sorted(TABLES_DIR.iterdir()):
            if table.is_file() and table.suffix.lower() == ".tex":
                shutil.copy2(table, tables_dir / table.name)
    checksums = {
        "manuscript.tex": canonical_sha256(SUBMISSION_DIR / "manuscript.tex"),
        "references.bib": canonical_sha256(SUBMISSION_DIR / "references.bib"),
        "metadata.yaml": canonical_sha256(SUBMISSION_DIR / "metadata.yaml"),
        pdf_path.name: canonical_sha256(pdf_path),
    }
    sha_lines = [f"{digest}  {name}" for name, digest in sorted(checksums.items())]
    (SUBMISSION_DIR / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="reviewer-preprint")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--pandoc")
    parser.add_argument("--tectonic")
    parser.add_argument("--qpdf")
    args = parser.parse_args()

    if args.profile != "reviewer-preprint":
        raise ValueError("Only reviewer-preprint is currently supported.")
    if not args.allow_dirty:
        require_clean_tree()

    pandoc = resolve_tool(args.pandoc, env_var="PANDOC", executable="pandoc")
    tectonic = resolve_tool(args.tectonic, env_var="TECTONIC", executable="tectonic")
    qpdf = resolve_tool(args.qpdf, env_var="QPDF", executable="qpdf")

    commit_sha = resolve_commit(args.commit)
    short_sha = commit_sha[:8]
    source_date_epoch = resolve_commit_timestamp(args.commit)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    render_publication_figures()
    sync_build_assets()
    runtime_metadata_path = build_runtime_metadata(commit_sha=commit_sha)

    manuscript_text = MANUSCRIPT_PATH.read_text(encoding="utf-8-sig")
    rewritten_markdown = rewrite_links(manuscript_text, commit_sha=commit_sha, link_source=MANUSCRIPT_PATH)
    publication_markdown = strip_front_matter_headings(rewritten_markdown)

    work_markdown = BUILD_DIR / "manuscript_work.md"
    tex_path = BUILD_DIR / "manuscript.tex"
    raw_pdf_path = BUILD_DIR / "manuscript.pdf"
    final_pdf_path = RELEASE_DIR / f"VSA_Recoverability_Atlas_{short_sha}.pdf"
    work_markdown.write_text(publication_markdown, encoding="utf-8", newline="\n")

    pandoc_command = [
        str(pandoc),
        str(work_markdown),
        "--from=markdown+raw_tex+tex_math_dollars+smart",
        "--standalone",
        "--citeproc",
        "--bibliography",
        str(REFERENCES_PATH),
        "--shift-heading-level-by=-1",
        "--metadata-file",
        str(runtime_metadata_path),
        "--template",
        str(TEMPLATE_PATH),
        "--resource-path",
        str(PAPER_DIR),
        "--resource-path",
        str(BUILD_DIR),
        "--wrap=none",
        "--output",
        str(tex_path),
    ]
    subprocess.run(pandoc_command, cwd=ROOT, check=True)

    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = source_date_epoch
    subprocess.run(
        [
            str(tectonic),
            "--keep-intermediates",
            "--keep-logs",
            "--outdir",
            str(BUILD_DIR),
            str(tex_path),
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )

    if not raw_pdf_path.exists():
        raise FileNotFoundError("Tectonic did not produce paper/build/manuscript.pdf.")

    subprocess.run(
        [str(qpdf), "--deterministic-id", str(raw_pdf_path), str(final_pdf_path)],
        cwd=ROOT,
        check=True,
    )

    build_submission_bundle(tex_path=tex_path, pdf_path=final_pdf_path, metadata_path=runtime_metadata_path)
    write_build_manifest(
        commit_sha=commit_sha,
        metadata_path=runtime_metadata_path,
        pdf_path=final_pdf_path,
        pandoc=pandoc,
        tectonic=tectonic,
        qpdf=qpdf,
    )

    print(f"Built reviewer preprint: {final_pdf_path}")
    print(f"Commit: {commit_sha}")
    print(f"PDF SHA256: {canonical_sha256(final_pdf_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
