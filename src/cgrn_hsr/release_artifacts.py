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


def extract_abstract(markdown: str) -> str:
    match = re.search(r"^## Abstract\s+(.*?)\s+^## 1\.", markdown, re.S | re.M)
    if not match:
        raise ValueError("Could not locate canonical abstract in manuscript.")
    return match.group(1).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def extract_markdown_headings(markdown: str) -> list[str]:
    return re.findall(r"^#+\s+(.+?)\s*$", markdown, re.M)


def extract_table_captions(markdown: str) -> list[tuple[str, str]]:
    matches = re.finditer(r"^### (Table \d+\..+?)\n\n(.*?)(?=\n## |\n### |\Z)", markdown, re.S | re.M)
    captions: list[tuple[str, str]] = []
    for match in matches:
        title = match.group(1).strip()
        body = " ".join(line.strip() for line in match.group(2).strip().splitlines() if line.strip())
        captions.append((title, body))
    return captions
