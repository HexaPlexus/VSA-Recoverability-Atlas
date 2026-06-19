from __future__ import annotations

import hashlib
import re
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".csv",
    ".json",
    ".jsonl",
    ".bib",
    ".svg",
    ".py",
}


def normalize_text_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    text = data.decode("utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def canonical_sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_EXTENSIONS:
        data = normalize_text_bytes(path)
    return hashlib.sha256(data).hexdigest()


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def extract_abstract(markdown: str) -> str:
    match = re.search(r"^## Abstract\s+(.*?)\s+^## 1\.", markdown, re.S | re.M)
    if not match:
        raise ValueError("Could not locate canonical abstract in manuscript.")
    return strip_html_comments(match.group(1)).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", strip_html_comments(text)))


def extract_markdown_headings(markdown: str) -> list[str]:
    return re.findall(r"^#+\s+(.+?)\s*$", markdown, re.M)


def extract_claim_ids(markdown: str) -> list[str]:
    claim_ids = set(re.findall(r"\[claim:(claim_[A-Za-z0-9_]+)\]", markdown))
    for chunk in re.findall(r"<!--\s*CLAIMS:\s*(.*?)\s*-->", markdown, re.S | re.I):
        for part in chunk.split(","):
            claim_id = part.strip()
            if claim_id.startswith("claim_"):
                claim_ids.add(claim_id)
    return sorted(claim_ids)


def extract_table_captions(markdown: str) -> list[tuple[str, str]]:
    matches = re.finditer(r"^### (Table \d+\..+?)\n\n(.*?)(?=\n## |\n### |\Z)", markdown, re.S | re.M)
    captions: list[tuple[str, str]] = []
    for match in matches:
        title = strip_html_comments(match.group(1)).strip()
        body = " ".join(
            line.strip()
            for line in strip_html_comments(match.group(2)).strip().splitlines()
            if line.strip()
        )
        captions.append((title, body))
    return captions
