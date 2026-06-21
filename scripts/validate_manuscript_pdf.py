from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
BUILD_DIR = PAPER_DIR / "build"
DISALLOWED_TEXT_SNIPPETS = (
    "[@",
    "OWNER-CHECK",
    "[claim:",
    "TODO",
    "FIXME",
    "localhost",
    "C:\\",
    "/home/",
    "/Users/",
    "/mnt/",
    "sandbox:",
)
DISALLOWED_URI_SNIPPETS = (
    "file:",
    "localhost",
    "127.0.0.1",
    "c:\\",
    "/home/",
    "/users/",
    "/mnt/",
    "sandbox:",
)
PLACEHOLDER_BIB_PATTERNS = (
    re.compile(r"\bauthors\b", re.I),
    re.compile(r"\bunknown\b", re.I),
    re.compile(r"\btbd\b", re.I),
    re.compile(r"\bvarious\b", re.I),
)
SYNTHETIC_FIELD_PATTERNS = (
    re.compile(r"/\s*preprint lineage", re.I),
    re.compile(r"/\s*device venue", re.I),
    re.compile(r"/\s*hardware venue", re.I),
    re.compile(r"/\s*official platform source", re.I),
)
PROHIBITED_MAIN_PAPER_IDS = (
    "level3_2_map_budget_robustness",
    "oracle_portfolio_complementarity_v0_1",
    "self_describing_record_sidecar_closure",
    "decoder_certified_codebook",
    "decoder_guided_tag_repair",
    "codebook_residue_block_lut",
)
OVERFULL_RE = re.compile(r"Overfull \\hbox \(([0-9.]+)pt too wide\)")
UNDERFULL_RE = re.compile(r"Underfull \\hbox")
EXPECTED_TITLE = "Recoverability Has a Cost: An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures"
EXPECTED_AUTHOR = "Gamzat Ibragimovich"
MAX_OVERFULL_PT = 1.0


def resolve_qpdf(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"Tool not found: {path}")
    if env_value := os.environ.get("QPDF"):
        path = Path(env_value).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"QPDF points to a missing tool: {path}")
    resolved = shutil.which("qpdf")
    if resolved:
        return Path(resolved).resolve()
    raise FileNotFoundError(
        "Could not find 'qpdf'. Pass --qpdf, set QPDF, or install qpdf on PATH. "
        "See paper/BUILDING.md for the publication toolchain requirements."
    )


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def extract_cited_keys(markdown: str) -> set[str]:
    keys = set(re.findall(r"\[@([^;\]]+)", markdown))
    keys.update(re.findall(r"(?<![\w-])@([A-Za-z0-9_:-]+)", markdown))
    return {key.strip() for key in keys if key.strip()}


def parse_bib_entries(text: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"@(?P<kind>\w+)\{(?P<key>[^,]+),(?P<body>[\s\S]*?)\n\}", text):
        body = match.group("body")
        fields: dict[str, str] = {"ENTRYTYPE": match.group("kind")}
        for field_match in re.finditer(r"(?im)^\s*(\w+)\s*=\s*\{([\s\S]*?)\}\s*,?\s*$", body):
            fields[field_match.group(1).lower()] = field_match.group(2).strip()
        entries[match.group("key")] = fields
    return entries


def collect_bibliography_failures(*, cited_keys: set[str], entries: dict[str, dict[str, str]]) -> list[str]:
    failures: list[str] = []
    for key in sorted(cited_keys):
        if key not in entries:
            failures.append(f"Missing bibliography entry for cited key: {key}")
            continue
        fields = entries[key]
        author = fields.get("author", "")
        title = fields.get("title", "")
        journalish = " ".join(fields.get(name, "") for name in ("journal", "booktitle", "note"))
        if not author:
            failures.append(f"{key}: missing author field.")
        elif any(pattern.search(author) for pattern in PLACEHOLDER_BIB_PATTERNS):
            failures.append(f"{key}: placeholder bibliography author detected: {author}")
        if not title:
            failures.append(f"{key}: missing title field.")
        if any(pattern.search(journalish) for pattern in SYNTHETIC_FIELD_PATTERNS):
            failures.append(f"{key}: synthetic venue metadata detected: {journalish}")
    return failures


def collect_duplicate_dois(entries: dict[str, dict[str, str]]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for key, fields in entries.items():
        doi = fields.get("doi", "").strip().lower()
        if not doi:
            continue
        if doi in seen:
            duplicates.append(f"Duplicate DOI {doi} appears in both {seen[doi]} and {key}")
        else:
            seen[doi] = key
    return duplicates


def collect_font_embedding_failures(reader: PdfReader) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for page_index, page in enumerate(reader.pages, start=1):
        resources = page.get("/Resources") or {}
        font_dict = resources.get("/Font") if hasattr(resources, "get") else None
        if not font_dict:
            continue
        for font_name, ref in font_dict.items():
            font = ref.get_object()
            base_name = str(font.get("/BaseFont", font_name))
            if base_name in seen:
                continue
            seen.add(base_name)
            descriptor = font.get("/FontDescriptor")
            if descriptor is None and font.get("/DescendantFonts"):
                descendants = font["/DescendantFonts"]
                if descendants:
                    descriptor = descendants[0].get_object().get("/FontDescriptor")
            if descriptor is None:
                failures.append(f"Missing descriptor for {base_name}")
                continue
            descriptor = descriptor.get_object()
            if not any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
                failures.append(f"Unembedded font detected: {base_name}")
    return failures


def collect_uris(reader: PdfReader) -> list[str]:
    uris: list[str] = []
    for page in reader.pages:
        for annot_ref in page.get("/Annots") or []:
            annot = annot_ref.get_object()
            action = annot.get("/A")
            uri = action.get("/URI") if action else None
            if uri:
                uris.append(str(uri))
    return uris


def flatten_outline_count(outline: object) -> int:
    count = 0
    stack = [outline]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif item:
            count += 1
    return count


def parse_layout_warnings(log_text: str) -> tuple[float, int]:
    worst_overfull = 0.0
    for match in OVERFULL_RE.finditer(log_text):
        worst_overfull = max(worst_overfull, float(match.group(1)))
    return worst_overfull, len(UNDERFULL_RE.findall(log_text))


def load_build_manifest() -> dict[str, object]:
    path = BUILD_DIR / "publication_manifest.json"
    if not path.exists():
        return {}
    return json.loads(load_text(path))


def canonical_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_hash_manifest(manifest: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if not manifest:
        return ["Build manifest is missing."]
    expected_manuscript = manifest.get("manuscript_hash")
    expected_refs = manifest.get("references_hash")
    expected_figures = manifest.get("figure_hashes", {})
    if expected_manuscript and canonical_sha256(PAPER_DIR / "manuscript.md") != expected_manuscript:
        failures.append("Build manifest manuscript hash is stale.")
    if expected_refs and canonical_sha256(PAPER_DIR / "references.bib") != expected_refs:
        failures.append("Build manifest references hash is stale.")
    if isinstance(expected_figures, dict):
        for name, digest in expected_figures.items():
            figure_path = PAPER_DIR / "figures" / name
            if not figure_path.exists():
                failures.append(f"Figure missing since build manifest generation: {name}")
            elif canonical_sha256(figure_path) != digest:
                failures.append(f"Build manifest figure hash is stale for {name}")
    return failures


def validate_figure_audit(mode: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    audit_path = PAPER_DIR / "figure_audit.yaml"
    if not audit_path.exists():
        message = "paper/figure_audit.yaml is missing."
        if mode == "release":
            errors.append(message)
        else:
            warnings.append(message)
        return errors, warnings
    payload = yaml.safe_load(load_text(audit_path)) or {}
    figures = payload.get("figures", {})
    for figure_name, checks in figures.items():
        if not isinstance(checks, dict):
            errors.append(f"{figure_name}: figure audit entry must be a mapping.")
            continue
        for field in (
            "vector_output",
            "caption_parity_checked",
            "data_parity_checked",
            "axis_labels_present",
            "visible_numeric_labels",
            "grayscale_checked",
            "colorblind_checked",
            "manual_render_checked",
        ):
            value = checks.get(field)
            if value is True:
                continue
            message = f"{figure_name}: audit field '{field}' is not confirmed."
            if mode == "release":
                errors.append(message)
            else:
                warnings.append(message)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--development", action="store_true")
    mode.add_argument("--release", action="store_true")
    parser.add_argument("--qpdf")
    parser.add_argument("pdf")
    args = parser.parse_args()
    validation_mode = "release" if args.release else "development"

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    qpdf = resolve_qpdf(args.qpdf)
    subprocess.run([str(qpdf), "--check", str(pdf_path)], cwd=ROOT, check=True)

    reader = PdfReader(str(pdf_path))
    metadata = reader.metadata or {}
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    outline_count = 0
    try:
        outline_count = flatten_outline_count(reader.outline)
    except Exception:
        outline_count = 0
    uri_list = collect_uris(reader)
    font_failures = collect_font_embedding_failures(reader)

    manuscript_text = load_text(PAPER_DIR / "manuscript.md")
    references_text = load_text(PAPER_DIR / "references.bib")
    cited_keys = extract_cited_keys(manuscript_text)
    bib_entries = parse_bib_entries(references_text)
    build_log = load_text(BUILD_DIR / "manuscript.log") if (BUILD_DIR / "manuscript.log").exists() else ""
    build_tex = load_text(BUILD_DIR / "manuscript.tex") if (BUILD_DIR / "manuscript.tex").exists() else ""
    build_manifest = load_build_manifest()

    errors: list[str] = []
    warnings: list[str] = []

    bibliography_failures = collect_bibliography_failures(cited_keys=cited_keys, entries=bib_entries)
    duplicate_dois = collect_duplicate_dois(bib_entries)
    errors.extend(bibliography_failures)
    errors.extend(duplicate_dois)

    if metadata.get("/Title") != EXPECTED_TITLE:
        errors.append("PDF title metadata is missing or incorrect.")
    if metadata.get("/Author") != EXPECTED_AUTHOR:
        errors.append("PDF author metadata is missing or incorrect.")
    if outline_count == 0:
        errors.append("PDF outline/bookmarks are absent.")
    if not uri_list:
        errors.append("No hyperlink annotations found in PDF.")
    errors.extend(font_failures)
    if "References" not in text:
        errors.append("Rendered References section not found in extracted text.")
    for snippet in DISALLOWED_TEXT_SNIPPETS:
        if snippet in text:
            errors.append(f"Disallowed text snippet found in extracted PDF text: {snippet}")
    for uri in uri_list:
        lowered = uri.lower()
        if any(snippet in lowered for snippet in DISALLOWED_URI_SNIPPETS):
            errors.append(f"Disallowed hyperlink target found: {uri}")

    worst_overfull, underfull_count = parse_layout_warnings(build_log)
    if worst_overfull > MAX_OVERFULL_PT:
        errors.append(f"Overfull boxes exceed threshold: worst is {worst_overfull:.3f}pt.")
    if validation_mode == "release" and underfull_count > 0:
        warnings.append(f"Underfull box warnings remain: {underfull_count}")

    if ".png}" in build_tex or ".jpg}" in build_tex or ".jpeg}" in build_tex:
        errors.append("Raster figure embedding detected in manuscript.tex.")
    for marker in PROHIBITED_MAIN_PAPER_IDS:
        if marker in manuscript_text:
            errors.append(f"Reader-facing repository identifier remains in main manuscript: {marker}")

    errors.extend(validate_hash_manifest(build_manifest))
    figure_audit_errors, figure_audit_warnings = validate_figure_audit(validation_mode)
    errors.extend(figure_audit_errors)
    warnings.extend(figure_audit_warnings)

    if validation_mode == "release":
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status:
            errors.append("Release validation requires a clean working tree.")

    print(f"Mode: {validation_mode}")
    print(f"Pages: {len(reader.pages)}")
    print(f"Outline entries: {outline_count}")
    print(f"Hyperlinks: {len(uri_list)}")
    print(f"Title metadata: {metadata.get('/Title', '')}")
    print(f"Author metadata: {metadata.get('/Author', '')}")
    print(f"Worst overfull: {worst_overfull:.3f}pt")
    print(f"Underfull warnings: {underfull_count}")
    print(f"Cited keys: {len(cited_keys)}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("PDF validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
