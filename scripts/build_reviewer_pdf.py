from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import markdown
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://github.com/HexaPlexus/VSA-Recoverability-Atlas"
DEFAULT_RENDER_SOURCE = ROOT / "paper" / "release_candidate" / "manuscript_rc1.md"
DEFAULT_LINK_SOURCE = ROOT / "paper" / "manuscript.md"
DEFAULT_OUTPUT = ROOT / "paper" / "release_candidate" / "VSA_Recoverability_Atlas_reviewer.pdf"
LINK_PATTERN = re.compile(
    r"(?P<prefix>!?)\[(?P<label>[^\]]+)\]\((?P<target><[^>]+>|[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)"
)
WINDOWS_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
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
REPO_TREE_OR_BLOB_PATTERN = re.compile(
    r"^/HexaPlexus/VSA-Recoverability-Atlas/(?P<kind>blob|tree)/(?P<commit>[0-9a-f]{40})/(?P<path>.+)$"
)
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def resolve_commit(ref: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", ref],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def find_browser_binary(explicit_path: str | None) -> Path:
    if explicit_path:
        browser = Path(explicit_path)
        if browser.is_file():
            return browser
        raise FileNotFoundError(f"Browser binary not found: {browser}")

    for candidate in EDGE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not find a supported Chromium-based browser binary.")


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def target_uses_preserved_scheme(target: str) -> bool:
    lowered = target.lower()
    if lowered.startswith("#"):
        return True
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https", "mailto"}


def target_is_disallowed_local_reference(target: str) -> bool:
    lowered = target.lower()
    if any(snippet in lowered for snippet in DISALLOWED_URI_SNIPPETS):
        return True
    if WINDOWS_PATH_PATTERN.match(target):
        return True
    return False


def resolve_repo_relative_target(target: str, link_source: Path) -> Path:
    clean_target = target.split("#", 1)[0]
    resolved = (link_source.parent / clean_target).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Relative link escapes repository root: {target}") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"Relative link target does not exist: {target} -> {resolved}")
    return resolved


def build_commit_pinned_url(
    target: str,
    *,
    commit_sha: str,
    base_url: str,
    link_source: Path,
) -> str:
    if target_uses_preserved_scheme(target):
        return target
    if target_is_disallowed_local_reference(target):
        raise ValueError(f"Local or private link is not allowed in reviewer PDF source: {target}")

    fragment = ""
    if "#" in target:
        _, fragment = target.split("#", 1)
    resolved = resolve_repo_relative_target(target, link_source)
    relpath = resolved.relative_to(ROOT).as_posix()
    kind = "tree" if resolved.is_dir() else "blob"
    url = f"{base_url}/{kind}/{commit_sha}/{relpath}"
    if fragment:
        url = f"{url}#{fragment}"
    return url


def rewrite_markdown_links(
    markdown_text: str,
    *,
    commit_sha: str,
    base_url: str,
    link_source: Path,
) -> tuple[str, int]:
    rewritten_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal rewritten_count
        if match.group("prefix") == "!":
            return match.group(0)

        original_target = match.group("target")
        title = match.group("title") or ""
        target = original_target[1:-1] if original_target.startswith("<") and original_target.endswith(">") else original_target
        rewritten_target = build_commit_pinned_url(
            target,
            commit_sha=commit_sha,
            base_url=base_url,
            link_source=link_source,
        )
        if rewritten_target != target:
            rewritten_count += 1
        label = match.group("label")
        return f"[{label}]({rewritten_target}{title})"

    return LINK_PATTERN.sub(replace, markdown_text), rewritten_count


def build_html(markdown_text: str, *, render_source: Path) -> str:
    body = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists", "tables", "toc"],
        output_format="html5",
    )
    base_href = render_source.parent.resolve().as_uri().rstrip("/") + "/"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VSA Recoverability Atlas Reviewer PDF</title>
  <base href="{base_href}">
  <style>
    body {{
      color: #111;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 11pt;
      line-height: 1.45;
      margin: 0 auto;
      max-width: 7.2in;
      padding: 0.45in 0.35in 0.6in;
    }}
    h1, h2, h3, h4 {{
      line-height: 1.2;
      margin: 1.2em 0 0.45em;
      page-break-after: avoid;
    }}
    h1 {{
      font-size: 22pt;
      margin-top: 0;
    }}
    h2 {{
      font-size: 16pt;
    }}
    h3 {{
      font-size: 13pt;
    }}
    p, li {{
      orphans: 3;
      widows: 3;
    }}
    img {{
      display: block;
      height: auto;
      margin: 0.8em auto;
      max-width: 100%;
      page-break-inside: avoid;
    }}
    table {{
      border-collapse: collapse;
      font-size: 10pt;
      margin: 1em 0;
      width: 100%;
    }}
    th, td {{
      border: 1px solid #888;
      padding: 0.35em 0.45em;
      vertical-align: top;
    }}
    code {{
      font-size: 0.92em;
    }}
    blockquote {{
      border-left: 3px solid #bbb;
      margin-left: 0;
      padding-left: 1em;
    }}
    a {{
      color: #0b57d0;
      text-decoration: underline;
      word-break: break-word;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def render_pdf(html_text: str, output_path: Path, *, browser_binary: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reviewer-pdf-", dir=str(ROOT)) as tmpdir:
        tmp_path = Path(tmpdir)
        html_path = tmp_path / "reviewer.html"
        html_path.write_text(html_text, encoding="utf-8", newline="\n")
        command = [
            str(browser_binary),
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=12000",
            f"--print-to-pdf={output_path}",
            html_path.as_uri(),
        ]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def extract_pdf_uris(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    uris: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        for annot_ref in page.get("/Annots") or []:
            annot = annot_ref.get_object()
            action = annot.get("/A")
            uri = action.get("/URI") if action else None
            if uri:
                uris.append((page_number, str(uri)))
    return uris


def validate_pdf_uris(
    pdf_path: Path,
    *,
    expected_commit: str,
    base_url: str,
    minimum_uri_count: int,
) -> list[tuple[int, str]]:
    uris = extract_pdf_uris(pdf_path)
    if len(uris) < minimum_uri_count:
        raise ValueError(
            f"Expected at least {minimum_uri_count} hyperlink annotations in {pdf_path.name}, found {len(uris)}."
        )

    for page_number, uri in uris:
        lowered = uri.lower()
        if any(snippet in lowered for snippet in DISALLOWED_URI_SNIPPETS):
            raise ValueError(f"Disallowed URI on page {page_number}: {uri}")

        if not uri.startswith(base_url):
            continue

        parsed = urlparse(uri)
        match = REPO_TREE_OR_BLOB_PATTERN.match(parsed.path)
        if not match:
            raise ValueError(f"Repository URI is not commit-pinned on page {page_number}: {uri}")

        commit = match.group("commit")
        if commit != expected_commit:
            raise ValueError(
                f"Repository URI uses commit {commit} instead of expected {expected_commit} on page {page_number}."
            )

        repo_path = match.group("path")
        local_path = ROOT / Path(repo_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Repository URI points to a missing path on page {page_number}: {uri}")

        kind = match.group("kind")
        if kind == "blob" and not local_path.is_file():
            raise ValueError(f"Blob URI does not point to a file on page {page_number}: {uri}")
        if kind == "tree" and not local_path.is_dir():
            raise ValueError(f"Tree URI does not point to a directory on page {page_number}: {uri}")

    return uris


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-source", default=str(DEFAULT_RENDER_SOURCE))
    parser.add_argument("--link-source", default=str(DEFAULT_LINK_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--browser-binary")
    args = parser.parse_args()

    render_source = normalize_path(args.render_source)
    link_source = normalize_path(args.link_source)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()

    commit_sha = resolve_commit(args.commit)
    browser_binary = find_browser_binary(args.browser_binary)
    markdown_text = render_source.read_text(encoding="utf-8")
    rewritten_markdown, rewritten_count = rewrite_markdown_links(
        markdown_text,
        commit_sha=commit_sha,
        base_url=args.base_url.rstrip("/"),
        link_source=link_source,
    )
    html_text = build_html(rewritten_markdown, render_source=render_source)
    render_pdf(html_text, output_path, browser_binary=browser_binary)
    uris = validate_pdf_uris(
        output_path,
        expected_commit=commit_sha,
        base_url=args.base_url.rstrip("/"),
        minimum_uri_count=rewritten_count,
    )

    print(f"Built reviewer PDF: {output_path}")
    print(f"Git commit: {commit_sha}")
    print(f"Rewritten repository-relative links: {rewritten_count}")
    print(f"Validated hyperlink annotations: {len(uris)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
