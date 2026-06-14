from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

IBM_BCF_AUDIT_SCHEMA_VERSION = "level1f2-bcf-audit-v1"
BCF_OFFICIAL_CLASS_PATH = "models.blockcodefactorizer.blockcodefactorizer"
UPSTREAM_CLONE_RELATIVE_PATH = Path("competitors") / "ibm_in_memory_factorizer"

STATUS_SUPPORTED = "SUPPORTED"
STATUS_WRAPPABLE = "WRAPPABLE"
STATUS_TASK_MISMATCH = "TASK_MISMATCH"
STATUS_UPSTREAM_MODIFICATION_REQUIRED = "UPSTREAM_MODIFICATION_REQUIRED"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AbstractFactorizationTask:
    task_seed: int
    factor_count: int
    domain_size_per_factor: list[int]
    target_indices: list[int]
    distractor_target_indices: list[list[int]]
    context_membership: dict[str, list[str]]
    active_context: str
    anomaly_rate: float
    query_valid_source_indices: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def upstream_clone_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[3]
    return root / UPSTREAM_CLONE_RELATIVE_PATH


def upstream_commit_sha(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def upstream_tracked_source_clean(repo_path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "diff", "--name-only", "HEAD", "--", "."],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == ""


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_json_roundtrippable(value: Any) -> bool:
    try:
        json.loads(json.dumps(value, ensure_ascii=True))
    except (TypeError, ValueError):
        return False
    return True


def load_recorded_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
