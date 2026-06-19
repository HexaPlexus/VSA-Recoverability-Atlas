from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
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
    distractor_target_indices: list[list[int]] = field(default_factory=list)
    context_membership: dict[str, Any] = field(default_factory=dict)
    active_context: str = ""
    anomaly_rate: float = 0.0
    query_valid_source_indices: list[int] = field(default_factory=list)
    active_l1: str | None = None
    active_l2: str | None = None
    context_prediction: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def upstream_clone_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[3]
    return root / UPSTREAM_CLONE_RELATIVE_PATH


def _recorded_dependency_audit(root: Path) -> dict[str, Any]:
    path = root / "results" / "level1f2_bcf_audit" / "dependency_audit.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_root_from_clone(repo_path: Path) -> Path:
    return repo_path.parent.parent


def upstream_commit_sha(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    audit = _recorded_dependency_audit(_repo_root_from_clone(repo_path))
    return str(audit["upstream"]["pinned_commit_sha"])


def _windows_git_repo_path(repo_path: Path) -> str:
    path = str(repo_path)
    if path.startswith("/mnt/") and len(path) > 6 and path[5].isalpha():
        drive = path[5].upper()
        suffix = path[6:]
        return f"{drive}:{suffix}"
    return path


def upstream_tracked_source_clean(repo_path: Path) -> bool:
    if sys.platform != "win32":
        try:
            result = subprocess.run(
                [
                    "git.exe",
                    "-C",
                    _windows_git_repo_path(repo_path),
                    "status",
                    "--porcelain",
                    "--untracked-files=no",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == ""
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    result = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain", "--untracked-files=no"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip() == ""
    audit = _recorded_dependency_audit(_repo_root_from_clone(repo_path))
    return bool(audit.get("tracked_upstream_modifications") is False)


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
