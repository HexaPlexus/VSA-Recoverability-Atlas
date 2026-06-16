from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_5b_native_noise_frontiers import write_json
from .level3_5b_protocol_repair import (
    BCH_CONFIG_PATH,
    IMMUTABLE_BLOCKED_PATHS,
    LEVEL3_5B_HELDOUT_V2_VERSION,
    LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
    OLD_PROTOCOL_PATH,
    TRANSITION_PATH,
    canonical_json_hash,
    read_json,
    sha256_path,
)

LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION = "level3-5b-heldout-v2-confirmation-v1"
LEVEL3_5B_HELDOUT_V2_STAGE_STATUS = "LEVEL_3_5B_HELDOUT_V2_COMPLETE"
LEVEL3_5B_HELDOUT_V2_BLOCKED = "BLOCKED_BY_V2_PROTOCOL_INTEGRITY_FAILURE"
LEVEL3_5B_HELDOUT_V2_PROMOTION_STATUS = "NO_PRODUCTION_PROMOTION"

LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT = "6aeafedb0b4025afbf9cbce9ff02e4b9aa10a32e"
EXPECTED_PROTOCOL_V2_HASH = "649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf"
EXPECTED_BCH_HASH = "7974133f002cbba795ae4655f7ab8b75bc6621f86991c13bd1e4d97d3ba733f3"
EXPECTED_MAP_HASHES = {
    "map_d1024": "11fd00e0f0ed8bd4341e51169ca7bde135299d69e11798ad4a97b96ed96e5ff9",
    "map_d1024_step32_r4_best_native_reconstruction": "b32e989b0016c44e0d8cac61d0aead60edd43efc7ff686d1ff76e779c5747bff",
}

PROTOCOL_V2_PATH = "results/level3_5b_protocol_repair/heldout_protocol_v2.json"
SEED_AUDIT_PATH = "results/level3_5b_protocol_repair/seed_audit.json"
REPAIR_VALIDATOR_PATH = "results/level3_5b_protocol_repair/validator_result.json"
REPAIR_ANALYSIS_PATH = "results/level3_5b_protocol_repair/analysis.json"
REPAIR_DOC_PATH = "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md"

REPAIR_IMMUTABLE_PATHS = (
    "results/level3_5b_protocol_repair/analysis.json",
    "results/level3_5b_protocol_repair/environment.json",
    "results/level3_5b_protocol_repair/heldout_protocol_v2.json",
    "results/level3_5b_protocol_repair/protocol_diff.json",
    "results/level3_5b_protocol_repair/seed_audit.json",
    "results/level3_5b_protocol_repair/validator_result.json",
    REPAIR_DOC_PATH,
)

PLACEHOLDER_RELATIVE_PATHS = (
    "semantic_manifests.jsonl",
    "binary_trials.jsonl",
    "map_trials.jsonl",
    "binary_summary.csv",
    "map_summary.csv",
    "silent_error_summary.csv",
    "resource_summary.csv",
    "timing_summary.csv",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def git_changed_paths_since(repo_root: Path, checkpoint: str, paths: tuple[str, ...]) -> list[str]:
    _, stdout, _ = git_stdout(repo_root, "diff", "--name-only", checkpoint, "HEAD", "--", *paths)
    return [line for line in stdout.splitlines() if line]


def touch_empty(path: Path) -> None:
    path.write_text("", encoding="utf-8")


def execution_already_materialized(results_dir: Path) -> bool:
    completion = results_dir / "completion_manifest.json"
    if not completion.exists():
        return False
    payload = read_json(completion)
    return bool(payload.get("execution_manifest_written", False))


def protocol_contains_executable_gate_rules(protocol: dict[str, Any]) -> bool:
    if isinstance(protocol.get("gates"), dict):
        return True
    for key in ("gate_rules", "confirmatory_gate_rules", "decision_rules", "verdict_rules"):
        if key in protocol and isinstance(protocol[key], dict) and protocol[key]:
            return True
    return False


def expected_seed_ranges(protocol: dict[str, Any]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        "binary_track": protocol["fresh_seed_ranges"]["binary_track"],
        "map_track": protocol["fresh_seed_ranges"]["map_track"],
    }


def build_execution_seed_lists(protocol: dict[str, Any]) -> dict[str, dict[str, list[int]]]:
    payload: dict[str, dict[str, list[int]]] = {}
    for track_name, ranges in expected_seed_ranges(protocol).items():
        payload[track_name] = {}
        for cell_id, spec in ranges.items():
            payload[track_name][cell_id] = list(range(int(spec["start"]), int(spec["end"]) + 1))
    return payload


def evaluate_protocol_v2_integrity(repo_root: Path, *, results_dir: Path) -> dict[str, Any]:
    protocol_path = repo_root / PROTOCOL_V2_PATH
    bch_path = repo_root / BCH_CONFIG_PATH
    old_protocol_path = repo_root / OLD_PROTOCOL_PATH
    transition_path = repo_root / TRANSITION_PATH
    seed_audit_path = repo_root / SEED_AUDIT_PATH
    repair_validator_path = repo_root / REPAIR_VALIDATOR_PATH
    repair_analysis_path = repo_root / REPAIR_ANALYSIS_PATH

    protocol = read_json(protocol_path)
    old_protocol = read_json(old_protocol_path)
    seed_audit = read_json(seed_audit_path)
    repair_validator = read_json(repair_validator_path)
    repair_analysis = read_json(repair_analysis_path)

    ancestry_rc, _, _ = git_stdout(
        repo_root,
        "merge-base",
        "--is-ancestor",
        LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT,
        "HEAD",
        allow_failure=True,
    )
    ancestry_ok = ancestry_rc == 0
    protocol_hash = canonical_json_hash(protocol)
    protocol_file_hash = sha256_path(protocol_path)
    bch_hash = sha256_path(bch_path)
    map_hashes = protocol["config_hashes"]["map_arm_hashes"]

    old_blocked_changed = git_changed_paths_since(repo_root, LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT, IMMUTABLE_BLOCKED_PATHS)
    repair_changed = git_changed_paths_since(repo_root, LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT, REPAIR_IMMUTABLE_PATHS)

    prior_trials_present = any(
        (results_dir / relative_path).exists() and (results_dir / relative_path).stat().st_size > 0
        for relative_path in ("binary_trials.jsonl", "map_trials.jsonl", "semantic_manifests.jsonl")
    )
    results_dir_preexisting = results_dir.exists()
    prior_execution_present = execution_already_materialized(results_dir)

    preserved_fields = protocol["preserved_scientific_fields"]
    scientific_fields_preserved = (
        preserved_fields["binary_track"]["methods"] == old_protocol["binary_track"]["methods"]
        and preserved_fields["binary_track"]["corruption_points_by_cell"] == old_protocol["binary_track"]["corruption_points_by_cell"]
        and preserved_fields["map_track"]["methods"] == old_protocol["map_track"]["methods"]
        and preserved_fields["map_track"]["corruption_points_by_cell"] == old_protocol["map_track"]["corruption_points_by_cell"]
        and preserved_fields["outcome_taxonomy"] == old_protocol["outcome_taxonomy"]
    )

    failures: list[str] = []
    if not ancestry_ok:
        failures.append(
            f"Current git ancestry does not include required checkpoint {LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT}."
        )
    if protocol_hash != EXPECTED_PROTOCOL_V2_HASH:
        failures.append(
            f"Protocol v2 hash mismatch: expected {EXPECTED_PROTOCOL_V2_HASH}, observed {protocol_hash}."
        )
    if bch_hash != EXPECTED_BCH_HASH:
        failures.append(f"BCH config hash mismatch: expected {EXPECTED_BCH_HASH}, observed {bch_hash}.")
    if map_hashes != EXPECTED_MAP_HASHES:
        failures.append(f"MAP config hashes mismatch: expected {EXPECTED_MAP_HASHES}, observed {map_hashes}.")
    if seed_audit.get("audit_verdict") != "PASS":
        failures.append(f"Seed audit is not PASS: observed {seed_audit.get('audit_verdict')}.")
    if repair_validator.get("validator_verdict") != "PROTOCOL_REPAIRED_AND_REFROZEN":
        failures.append(
            f"Protocol-repair validator verdict is not PROTOCOL_REPAIRED_AND_REFROZEN: observed {repair_validator.get('validator_verdict')}."
        )
    if not repair_validator.get("ready_for_level3_5b_heldout_v2", False):
        failures.append("Protocol-repair validator does not authorize held-out v2 readiness.")
    if old_blocked_changed:
        failures.append(f"Old blocked artifacts changed after repair checkpoint: {old_blocked_changed}.")
    if repair_changed:
        failures.append(f"Protocol-repair artifacts changed after repair checkpoint: {repair_changed}.")
    if prior_trials_present:
        failures.append("Held-out v2 results directory already contains non-empty trial outcome files.")
    if prior_execution_present:
        failures.append("Held-out v2 completion manifest already exists; rerun is forbidden.")
    if not scientific_fields_preserved:
        failures.append("Protocol v2 preserved scientific fields no longer match frozen v1 semantics.")
    if not protocol_contains_executable_gate_rules(protocol):
        failures.append(
            "Protocol v2 lacks executable confirmatory gate semantics: `gates` contains only disposition labels and no serialized decision rules."
        )

    return {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "checkpoint_commit_required": LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT,
        "current_git_commit": current_git_commit(repo_root),
        "ancestry_ok": ancestry_ok,
        "protocol_v2_path": PROTOCOL_V2_PATH,
        "protocol_v2_hash_expected": EXPECTED_PROTOCOL_V2_HASH,
        "protocol_v2_hash_observed": protocol_hash,
        "protocol_v2_file_hash_observed": protocol_file_hash,
        "bch_hash_expected": EXPECTED_BCH_HASH,
        "bch_hash_observed": bch_hash,
        "map_hashes_expected": EXPECTED_MAP_HASHES,
        "map_hashes_observed": map_hashes,
        "seed_audit_pass": seed_audit.get("audit_verdict") == "PASS",
        "repair_validator_ready": repair_validator.get("ready_for_level3_5b_heldout_v2", False),
        "repair_analysis_no_trials": repair_analysis.get("heldout_trials_executed", 0) == 0,
        "old_blocked_artifacts_unchanged": not old_blocked_changed,
        "repair_artifacts_unchanged": not repair_changed,
        "old_blocked_changed_paths": old_blocked_changed,
        "repair_changed_paths": repair_changed,
        "results_dir_preexisting": results_dir_preexisting,
        "prior_trials_present": prior_trials_present,
        "prior_execution_present": prior_execution_present,
        "scientific_fields_preserved": scientific_fields_preserved,
        "frozen_metrics_loaded": protocol["metrics"],
        "frozen_gates_loaded": protocol["gates"],
        "protocol_has_executable_gate_rules": protocol_contains_executable_gate_rules(protocol),
        "blocked_because_missing_gate_rules": not protocol_contains_executable_gate_rules(protocol),
        "blocked": bool(failures),
        "integrity_failures": failures,
    }


def render_heldout_v2_doc(repo_root: Path, integrity: dict[str, Any]) -> None:
    lines = [
        "# Level 3.5b Held-Out Native Noise Frontier Confirmation v2",
        "",
        f"- Schema: `{LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION}`",
        f"- Required checkpoint: `{LEVEL3_5B_PROTOCOL_REPAIR_CHECKPOINT}`",
        f"- Current commit at execution attempt: `{integrity['current_git_commit']}`",
        f"- Overall verdict: `{LEVEL3_5B_HELDOUT_V2_BLOCKED}`",
        "",
        "## Pre-Execution Integrity",
        "",
        f"- Protocol v2 hash expected: `{integrity['protocol_v2_hash_expected']}`",
        f"- Protocol v2 canonical hash observed: `{integrity['protocol_v2_hash_observed']}`",
        f"- Protocol v2 file SHA-256 observed: `{integrity['protocol_v2_file_hash_observed']}`",
        f"- BCH hash observed: `{integrity['bch_hash_observed']}`",
        f"- MAP hashes observed: `{json.dumps(integrity['map_hashes_observed'], sort_keys=True)}`",
        f"- Seed audit PASS: `{integrity['seed_audit_pass']}`",
        f"- Old blocked artifacts unchanged: `{integrity['old_blocked_artifacts_unchanged']}`",
        f"- Repair artifacts unchanged: `{integrity['repair_artifacts_unchanged']}`",
        "",
        "## Blocking Reason",
        "",
        "- No held-out trials were executed.",
        "- The repaired v2 protocol preserves frozen methods, cells, points, seeds and hashes.",
        "- However, the confirmatory gate layer remains underspecified for execution.",
        "- `gates` serializes only allowed disposition labels, not executable decision rules.",
        "- Under the frozen-protocol contract, the runner cannot invent confirmatory thresholds or verdict logic.",
        "",
        "## Claim Boundary",
        "",
        "- This is a pre-trial integrity block, not a scientific outcome.",
        "- No binary, BCH, NeCo, generic-linear, MAP or BCF held-out result was observed in this v2 attempt.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_level3_5b_heldout_v2(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_heldout_v2"
    if execution_already_materialized(results_dir):
        raise RuntimeError("Held-out v2 execution artifacts already exist; rerun is forbidden.")

    environment = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": current_git_commit(repo_root),
        "timestamp_utc": utc_now_iso(),
        "protocol_version_required": LEVEL3_5B_HELDOUT_V2_VERSION,
    }

    protocol = read_json(repo_root / PROTOCOL_V2_PATH)
    integrity = evaluate_protocol_v2_integrity(repo_root, results_dir=results_dir)

    results_dir.mkdir(parents=True, exist_ok=True)
    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "protocol_integrity.json", integrity)

    execution_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "protocol_path": PROTOCOL_V2_PATH,
        "protocol_hash": integrity["protocol_v2_hash_observed"],
        "git_commit": environment["git_commit"],
        "config_hashes": {
            "bch": integrity["bch_hash_observed"],
            "map": integrity["map_hashes_observed"],
        },
        "exact_concrete_seeds": build_execution_seed_lists(protocol),
        "methods": {
            "binary_track": protocol["preserved_scientific_fields"]["binary_track"]["methods"],
            "map_track": protocol["preserved_scientific_fields"]["map_track"]["methods"],
            "bcf_track": protocol["preserved_scientific_fields"]["bcf_track"]["status"],
        },
        "cells": {
            "binary_track": protocol["preserved_scientific_fields"]["binary_track"]["semantic_cells"],
            "map_track": protocol["preserved_scientific_fields"]["map_track"]["semantic_cells"],
        },
        "points": {
            "binary_track": protocol["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"],
            "map_track": protocol["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"],
        },
        "trial_counts": protocol["trial_counts"],
        "environment": environment,
        "start_timestamp": utc_now_iso(),
        "no_trial_had_yet_executed": True,
        "execution_authorized": not integrity["blocked"],
        "blocked_before_trials": integrity["blocked"],
    }
    write_json(results_dir / "execution_manifest.json", execution_manifest)

    for relative_path in PLACEHOLDER_RELATIVE_PATHS:
        touch_empty(results_dir / relative_path)

    bcf_status = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "status": "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY",
        "executed": False,
        "reason": protocol["preserved_scientific_fields"]["bcf_track"]["reason"],
    }
    write_json(results_dir / "bcf_status.json", bcf_status)

    overall_verdict = LEVEL3_5B_HELDOUT_V2_BLOCKED
    completion_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "completed_at": utc_now_iso(),
        "execution_manifest_written": True,
        "blocked_before_trials": True,
        "executed_trials": 0,
        "overall_verdict": overall_verdict,
        "rerun_after_completion_forbidden": True,
    }
    write_json(results_dir / "completion_manifest.json", completion_manifest)

    verdicts = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "overall_verdict": overall_verdict,
        "confirmatory_verdicts": {
            "binary_track": "NOT_EXECUTED",
            "map_track": "NOT_EXECUTED",
            "bcf_track": "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY",
        },
        "allowed_dispositions": protocol["gates"],
        "blocked_reason": integrity["integrity_failures"],
    }
    write_json(results_dir / "verdicts.json", verdicts)

    claims = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "allowed_claims": [
            "Protocol v2 preserved the frozen scientific choices but remained non-executable due to missing serialized confirmatory gate semantics.",
            "No held-out trial outcome was observed before this block.",
            "BCF remains blocked by contract ambiguity and was not invoked.",
        ],
        "forbidden_claims": [
            "Any confirmatory noise-frontier claim for binary, BCH, raw NeCo, generic linear or MAP.",
            "Any improvised gate logic derived outside heldout_protocol_v2.json.",
            "Any statement that Level 3.5b held-out v2 completed successfully.",
        ],
    }
    write_json(results_dir / "claims.json", claims)

    analysis = {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "final_stage_status": LEVEL3_5B_HELDOUT_V2_STAGE_STATUS,
        "promotion_status": LEVEL3_5B_HELDOUT_V2_PROMOTION_STATUS,
        "overall_verdict": overall_verdict,
        "executed": False,
        "trials_executed": 0,
        "benchmark_execution_invoked": False,
        "bcf_invoked": False,
        "frozen_metrics_and_gates_loaded_only": True,
        "integrity_failures": integrity["integrity_failures"],
        "blocked_because_missing_gate_rules": integrity["blocked_because_missing_gate_rules"],
        "no_trials_observed": True,
    }
    write_json(results_dir / "analysis.json", analysis)

    render_heldout_v2_doc(repo_root, integrity)

    return {
        "schema_version": LEVEL3_5B_HELDOUT_V2_SCHEMA_VERSION,
        "overall_verdict": overall_verdict,
        "executed_trials": 0,
        "integrity_failures": len(integrity["integrity_failures"]),
    }
