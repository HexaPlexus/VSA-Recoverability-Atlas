from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_5b_native_noise_frontiers import (
    BCF_TRACK_BLOCKED,
    level3_5b_dev_seed_set,
    prior_seed_set,
    write_json,
)

LEVEL3_5B_HELDOUT_SCHEMA_VERSION = "level3-5b-heldout-native-noise-frontiers-v1"
LEVEL3_5B_HELDOUT_STAGE_STATUS = "LEVEL_3_5B_HELDOUT_COMPLETE"
LEVEL3_5B_HELDOUT_BLOCKED = "BLOCKED_BY_PROTOCOL_INTEGRITY_FAILURE"
LEVEL3_5B_HELDOUT_PROMOTION_STATUS = "NO_PRODUCTION_PROMOTION"

BENCHMARK_DEVELOPMENT_CHECKPOINT = "110404917fbcbd5a10623058ef8ce36d7ad36a04"
DOCUMENTATION_CHECKPOINT = "87f3997c10f7d2e6ac3df58f5b00c6834dea648c"

FROZEN_INTEGRITY_PATHS = (
    "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
    "experiments/level3_5b_native_noise_frontiers.py",
    "results/level3_5b_dev/heldout_protocol.json",
    "results/level3_5b_dev/bch_configs.json",
    "results/level3_5b_dev/frozen_development_protocol.json",
    "results/level3_5b_dev/transition_regions.json",
    "results/level3_5b_dev/binary_summary.csv",
    "results/level3_5b_dev/map_summary.csv",
    "results/level3_5b_dev/bcf_summary.csv",
)

HASHED_FROZEN_FILES = (
    "results/level3_5b_dev/heldout_protocol.json",
    "results/level3_5b_dev/bch_configs.json",
    "results/level3_5b_dev/frozen_development_protocol.json",
    "results/level3_5b_dev/transition_regions.json",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_stdout(repo_root: Path, *args: str, allow_failure: bool = False) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def current_git_commit(repo_root: Path) -> str:
    _, stdout, _ = git_stdout(repo_root, "rev-parse", "HEAD")
    return stdout


def frozen_file_diff(repo_root: Path) -> list[str]:
    _, stdout, _ = git_stdout(
        repo_root,
        "diff",
        "--name-only",
        BENCHMARK_DEVELOPMENT_CHECKPOINT,
        "HEAD",
        "--",
        *FROZEN_INTEGRITY_PATHS,
    )
    return [line for line in stdout.splitlines() if line]


def protocol_seed_set(protocol: dict[str, Any]) -> set[int]:
    values: set[int] = set()
    for track_name in ("binary_track", "map_track", "bcf_track"):
        track = protocol.get(track_name, {})
        for spec in track.get("seed_ranges", {}).values():
            start = int(spec["start"])
            count = int(spec["count"])
            for seed in range(start, start + count):
                values.add(seed)
    return values


def build_file_hashes(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for rel_path in HASHED_FROZEN_FILES:
        path = repo_root / rel_path
        payload[rel_path] = {
            "exists": path.exists(),
            "sha256": sha256_path(path) if path.exists() else None,
        }
    return payload


def canonical_frozen_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "heldout_protocol.json": repo_root / "results" / "level3_5b_dev" / "heldout_protocol.json",
        "bch_configs.json": repo_root / "results" / "level3_5b_dev" / "bch_configs.json",
        "frozen_development_protocol.json": repo_root / "results" / "level3_5b_dev" / "frozen_development_protocol.json",
        "transition_regions.json": repo_root / "results" / "level3_5b_dev" / "transition_regions.json",
    }


def compare_bch_configs(protocol: dict[str, Any], bch_configs: dict[str, Any]) -> bool:
    return protocol["binary_track"]["bch_configs"] == bch_configs["rows"]


def compare_seed_ranges(protocol: dict[str, Any], frozen_protocol: dict[str, Any]) -> dict[str, bool]:
    return {
        "binary_seed_ranges_match": protocol["binary_track"]["seed_ranges"] == frozen_protocol["binary_seed_ranges"],
        "map_seed_ranges_match": protocol["map_track"]["seed_ranges"] == frozen_protocol["map_seed_ranges"],
        "bcf_seed_ranges_match": protocol["bcf_track"]["seed_ranges"] == frozen_protocol["bcf_seed_ranges"],
    }


def normalize_map_configs_from_protocol(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in protocol["map_track"]["map_configs"]:
        normalized = {
            "arm_id": item["arm_id"],
            "dimensions": item["dimensions"],
            "max_iterations": item["max_iterations"],
        }
        if "restarts" in item:
            normalized["restart_count"] = item["restarts"]
        if "selection_rule" in item:
            normalized["selection_rule"] = item["selection_rule"]
        rows.append(normalized)
    return rows


def compare_map_configs(protocol: dict[str, Any], frozen_protocol: dict[str, Any]) -> bool:
    expected = []
    for item in frozen_protocol["frozen_map_configs"]:
        normalized = {
            "arm_id": item["arm_id"],
            "dimensions": item["dimensions"],
            "max_iterations": item["max_iterations"],
        }
        if "restart_count" in item:
            normalized["restart_count"] = item["restart_count"]
        if "selection_rule" in item:
            normalized["selection_rule"] = item["selection_rule"]
        expected.append(normalized)
    return normalize_map_configs_from_protocol(protocol) == expected


def protocol_contradictions(protocol: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for track_name in ("binary_track", "map_track"):
        track = protocol[track_name]
        expected_trials = int(track["trial_count_per_selected_point"])
        for cell_id, spec in track["seed_ranges"].items():
            if int(spec["count"]) != expected_trials:
                failures.append(
                    f"{track_name}:{cell_id} seed_range.count={spec['count']} != trial_count_per_selected_point={expected_trials}"
                )
    return failures


def seed_overlap_failures(protocol: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    heldout = protocol_seed_set(protocol)
    overlap_dev = heldout.intersection(level3_5b_dev_seed_set())
    overlap_prior = heldout.intersection(prior_seed_set())
    if overlap_dev:
        failures.append(
            f"heldout seeds overlap development seeds ({len(overlap_dev)} overlaps; sample={sorted(overlap_dev)[:5]})"
        )
    if overlap_prior:
        failures.append(
            f"heldout seeds overlap prior Level 3.1-3.4/3.2b seeds ({len(overlap_prior)} overlaps; sample={sorted(overlap_prior)[:5]})"
        )
    return failures


def evaluate_protocol_integrity(
    repo_root: Path,
    *,
    heldout_protocol_path: Path | None = None,
    bch_config_path: Path | None = None,
    frozen_development_protocol_path: Path | None = None,
    transition_regions_path: Path | None = None,
) -> dict[str, Any]:
    heldout_protocol_path = heldout_protocol_path or (repo_root / "results" / "level3_5b_dev" / "heldout_protocol.json")
    bch_config_path = bch_config_path or (repo_root / "results" / "level3_5b_dev" / "bch_configs.json")
    frozen_development_protocol_path = frozen_development_protocol_path or (
        repo_root / "results" / "level3_5b_dev" / "frozen_development_protocol.json"
    )
    transition_regions_path = transition_regions_path or (repo_root / "results" / "level3_5b_dev" / "transition_regions.json")

    protocol = read_json(heldout_protocol_path)
    bch_configs = read_json(bch_config_path)
    frozen_protocol = read_json(frozen_development_protocol_path)
    transition_regions = read_json(transition_regions_path)
    canonical_paths = canonical_frozen_paths(repo_root)

    ancestry_rc, _, _ = git_stdout(
        repo_root,
        "merge-base",
        "--is-ancestor",
        BENCHMARK_DEVELOPMENT_CHECKPOINT,
        DOCUMENTATION_CHECKPOINT,
        allow_failure=True,
    )
    ancestry_ok = ancestry_rc == 0
    changed_paths = frozen_file_diff(repo_root)
    file_hashes = build_file_hashes(repo_root)
    seed_range_checks = compare_seed_ranges(protocol, frozen_protocol)
    map_configs_match = compare_map_configs(protocol, frozen_protocol)
    bch_configs_match = compare_bch_configs(protocol, bch_configs)
    transition_rows_present = bool(transition_regions.get("rows"))
    override_hash_checks = {
        "heldout_protocol_hash_matches_canonical": sha256_path(heldout_protocol_path) == sha256_path(canonical_paths["heldout_protocol.json"]),
        "bch_configs_hash_matches_canonical": sha256_path(bch_config_path) == sha256_path(canonical_paths["bch_configs.json"]),
        "frozen_development_protocol_hash_matches_canonical": sha256_path(frozen_development_protocol_path)
        == sha256_path(canonical_paths["frozen_development_protocol.json"]),
        "transition_regions_hash_matches_canonical": sha256_path(transition_regions_path) == sha256_path(canonical_paths["transition_regions.json"]),
    }

    failures: list[str] = []
    if not ancestry_ok:
        failures.append(
            f"git ancestry check failed: {BENCHMARK_DEVELOPMENT_CHECKPOINT} is not an ancestor of {DOCUMENTATION_CHECKPOINT}"
        )
    if changed_paths:
        failures.append(f"frozen benchmark files changed after development checkpoint: {changed_paths}")
    if not bch_configs_match:
        failures.append("heldout protocol BCH configs do not match frozen bch_configs.json")
    if not map_configs_match:
        failures.append("heldout protocol MAP configs do not match frozen_development_protocol.json")
    for check_name, matches in seed_range_checks.items():
        if not matches:
            failures.append(f"{check_name} is false")
    for check_name, matches in override_hash_checks.items():
        if not matches:
            failures.append(f"{check_name} is false")
    if not transition_rows_present:
        failures.append("transition_regions.json has no rows")
    failures.extend(protocol_contradictions(protocol))
    failures.extend(seed_overlap_failures(protocol))

    return {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "benchmark_development_checkpoint": BENCHMARK_DEVELOPMENT_CHECKPOINT,
        "documentation_checkpoint": DOCUMENTATION_CHECKPOINT,
        "ancestry_ok": ancestry_ok,
        "frozen_file_hashes": file_hashes,
        "changed_frozen_paths_after_development_checkpoint": changed_paths,
        "bch_configs_match": bch_configs_match,
        "map_configs_match": map_configs_match,
        "seed_range_checks": seed_range_checks,
        "override_hash_checks": override_hash_checks,
        "transition_rows_present": transition_rows_present,
        "integrity_failures": failures,
        "blocked": bool(failures),
        "blocked_verdict": LEVEL3_5B_HELDOUT_BLOCKED if failures else None,
    }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def touch_empty(path: Path) -> None:
    ensure_parent(path)
    path.write_text("", encoding="utf-8")


def render_heldout_confirmation_doc(repo_root: Path, analysis: dict[str, Any], protocol_integrity: dict[str, Any]) -> None:
    lines = [
        "# Level 3.5b Held-Out Native Noise Frontier Confirmation",
        "",
        f"- Schema: `{LEVEL3_5B_HELDOUT_SCHEMA_VERSION}`",
        f"- Stage status: `{analysis['final_stage_status']}`",
        f"- Promotion status: `{analysis['promotion_status']}`",
        f"- Overall verdict: `{analysis['overall_verdict']}`",
        "",
        "## Integrity Gate",
        "",
        f"- Ancestry OK: `{protocol_integrity['ancestry_ok']}`",
        f"- Frozen file changes after development checkpoint: `{bool(protocol_integrity['changed_frozen_paths_after_development_checkpoint'])}`",
        f"- Integrity failures: `{len(protocol_integrity['integrity_failures'])}`",
        "",
        "## Outcome",
        "",
        "- No held-out trials were executed.",
        "- The run was blocked before first trial because the frozen held-out protocol is internally inconsistent.",
        "- Development seed ranges were reused as held-out seed ranges, which violates confirmatory seed discipline.",
        "- Binary and MAP trial counts in the frozen protocol do not match the declared seed-range counts.",
        "- The frozen held-out MAP config subset does not exactly match the richer frozen development MAP config record.",
        "",
        "## BCF Track",
        "",
        "- BCF remains blocked by native corruption-contract ambiguity.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_level3_5b_heldout(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_heldout"
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol_path = repo_root / "results" / "level3_5b_dev" / "heldout_protocol.json"
    bch_path = repo_root / "results" / "level3_5b_dev" / "bch_configs.json"
    frozen_dev_path = repo_root / "results" / "level3_5b_dev" / "frozen_development_protocol.json"
    transition_path = repo_root / "results" / "level3_5b_dev" / "transition_regions.json"

    protocol = read_json(protocol_path)
    protocol_hash = sha256_path(protocol_path)
    config_hashes = {
        "heldout_protocol.json": sha256_path(protocol_path),
        "bch_configs.json": sha256_path(bch_path),
        "frozen_development_protocol.json": sha256_path(frozen_dev_path),
        "transition_regions.json": sha256_path(transition_path),
    }

    environment = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": current_git_commit(repo_root),
        "timestamp_utc": utc_now_iso(),
    }
    write_json(results_dir / "environment.json", environment)

    protocol_integrity = evaluate_protocol_integrity(repo_root)
    write_json(results_dir / "protocol_integrity.json", protocol_integrity)

    execution_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "protocol_hash": protocol_hash,
        "git_commit": environment["git_commit"],
        "environment": environment,
        "methods": {
            "binary_track": protocol["binary_track"]["methods"],
            "map_track": protocol["map_track"]["methods"],
            "bcf_track": protocol["bcf_track"]["status"],
        },
        "cells": {
            "binary_track": protocol["binary_track"]["semantic_cells"],
            "map_track": protocol["map_track"]["semantic_cells"],
        },
        "corruption_points": {
            "binary_track": protocol["binary_track"]["corruption_points_by_cell"],
            "map_track": protocol["map_track"]["corruption_points_by_cell"],
        },
        "trial_counts": {
            "binary_track": protocol["binary_track"]["trial_count_per_selected_point"],
            "map_track": protocol["map_track"]["trial_count_per_selected_point"],
            "bcf_track": protocol["bcf_track"]["trial_count_per_selected_point"],
        },
        "seed_ranges": {
            "binary_track": protocol["binary_track"]["seed_ranges"],
            "map_track": protocol["map_track"]["seed_ranges"],
            "bcf_track": protocol["bcf_track"]["seed_ranges"],
        },
        "config_hashes": config_hashes,
        "start_time": utc_now_iso(),
        "execution_authorized": not protocol_integrity["blocked"],
        "blocked_before_trials": protocol_integrity["blocked"],
    }
    write_json(results_dir / "execution_manifest.json", execution_manifest)

    touch_empty(results_dir / "semantic_manifests.jsonl")
    touch_empty(results_dir / "binary_trials.jsonl")
    touch_empty(results_dir / "map_trials.jsonl")
    touch_empty(results_dir / "binary_summary.csv")
    touch_empty(results_dir / "map_summary.csv")
    touch_empty(results_dir / "silent_error_summary.csv")
    touch_empty(results_dir / "resource_summary.csv")
    touch_empty(results_dir / "timing_summary.csv")

    bcf_status = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "status": protocol["bcf_track"]["status"],
        "reason": protocol["bcf_track"]["reason"],
        "executed": False,
        "blocked_by_protocol_integrity_failure": protocol_integrity["blocked"],
    }
    write_json(results_dir / "bcf_status.json", bcf_status)

    if protocol_integrity["blocked"]:
        overall_verdict = LEVEL3_5B_HELDOUT_BLOCKED
        confirmatory_verdicts = {
            "binary_track": "NOT_EXECUTED",
            "map_track": "NOT_EXECUTED",
            "bcf_track": BCF_TRACK_BLOCKED,
        }
    else:  # pragma: no cover - future activation only
        raise NotImplementedError("Held-out execution path is intentionally unavailable until protocol integrity passes.")

    completion_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "completed_at": utc_now_iso(),
        "executed_trials": 0,
        "overall_verdict": overall_verdict,
        "blocked_before_trials": protocol_integrity["blocked"],
    }
    write_json(results_dir / "completion_manifest.json", completion_manifest)

    verdicts = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "overall_verdict": overall_verdict,
        "confirmatory_verdicts": confirmatory_verdicts,
        "allowed_dispositions": [
            "BCH_DOMINATES_BINARY_EXACT_RECORD_CONFIRMED",
            "BCH_DOMINANCE_NOT_CONFIRMED",
            "RAW_NECO_NOISE_GAP_CONFIRMED",
            "RAW_NECO_NOISE_GAP_NOT_CONFIRMED",
            "GENERIC_LINEAR_NOISE_EQUIVALENCE_CONFIRMED",
            "GENERIC_LINEAR_NOISE_EQUIVALENCE_NOT_CONFIRMED",
            "MAP_SILENT_COLLAPSE_CONFIRMED",
            "MAP_SILENT_COLLAPSE_NOT_CONFIRMED",
            "MAP_GRACEFUL_REGION_CONFIRMED",
            "MAP_GRACEFUL_REGION_NOT_CONFIRMED",
            "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY",
            "NO_SHARED_NOISE_WINNER",
        ],
        "blocked_reason": protocol_integrity["integrity_failures"],
    }
    write_json(results_dir / "verdicts.json", verdicts)

    claims = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "allowed_claims": [
            "Held-out execution was blocked by protocol integrity failure before first trial.",
            "No confirmatory native-noise claims were authorized from this stage.",
            "BCF noisy-track status remains blocked by contract ambiguity.",
        ],
        "forbidden_claims": [
            "Any held-out confirmation claim for BCH, raw NeCo, generic linear mix, or MAP.",
            "Any repaired or inferred held-out seed schedule.",
            "Any claim based on rerunning or silently fixing the frozen protocol.",
        ],
    }
    write_json(results_dir / "claims.json", claims)

    analysis = {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "final_stage_status": LEVEL3_5B_HELDOUT_STAGE_STATUS,
        "promotion_status": LEVEL3_5B_HELDOUT_PROMOTION_STATUS,
        "overall_verdict": overall_verdict,
        "executed": False,
        "trials_executed": 0,
        "confirmatory_verdicts": confirmatory_verdicts,
        "integrity_failures": protocol_integrity["integrity_failures"],
        "blocked_because_protocol_internal_counts_mismatch": any(
            "trial_count_per_selected_point" in item for item in protocol_integrity["integrity_failures"]
        ),
        "blocked_because_map_config_protocol_mismatch": any(
            "MAP configs do not match" in item for item in protocol_integrity["integrity_failures"]
        ),
        "blocked_because_heldout_overlaps_development": any(
            "overlap development seeds" in item for item in protocol_integrity["integrity_failures"]
        ),
        "blocked_because_heldout_overlaps_prior": any(
            "overlap prior" in item for item in protocol_integrity["integrity_failures"]
        ),
        "bcf_status": protocol["bcf_track"]["status"],
        "tuning_performed": False,
    }
    write_json(results_dir / "analysis.json", analysis)

    render_heldout_confirmation_doc(repo_root, analysis, protocol_integrity)

    return {
        "schema_version": LEVEL3_5B_HELDOUT_SCHEMA_VERSION,
        "overall_verdict": overall_verdict,
        "integrity_failures": len(protocol_integrity["integrity_failures"]),
        "executed_trials": 0,
        "bcf_status": protocol["bcf_track"]["status"],
    }
