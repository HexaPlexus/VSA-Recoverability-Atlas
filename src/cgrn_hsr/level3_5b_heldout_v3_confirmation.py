from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_5b_gate_specification import (
    PROTOCOL_V2_CANONICAL_HASH,
    complete_gate_hash,
    evaluate_gate,
    load_csv_rows,
)
from .level3_5b_native_noise_frontiers import (
    BCF_TRACK_BLOCKED,
    CHANNEL_EXACT_WEIGHT,
    CHANNEL_MAP_SIGN_FLIP,
    LEVEL3_5B_DEV_SCHEMA_VERSION,
    MAP_EXTENDED_ARM_ID,
    MAP_FAST_ARM_ID,
    build_binary_method_rows,
    build_task,
    environment_snapshot,
    payload_bits_for_task,
    prepare_binary_representations,
    prepare_map_runs,
    run_map_arm,
    summarize_track,
    write_csv,
    write_json,
    write_jsonl,
)
from .level3_5b_protocol_repair import canonical_json_hash, read_json, sha256_path

LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION = "level3-5b-heldout-v3-confirmation-v1"
LEVEL3_5B_HELDOUT_V3_STAGE_COMPLETE = "LEVEL_3_5B_HELDOUT_V3_COMPLETE"
LEVEL3_5B_HELDOUT_V3_STAGE_INCOMPLETE = "LEVEL_3_5B_HELDOUT_V3_INCOMPLETE"
LEVEL3_5B_HELDOUT_V3_BLOCKED = "BLOCKED_BY_V3_PROTOCOL_INTEGRITY_FAILURE"
LEVEL3_5B_HELDOUT_V3_PROMOTION = "NO_PRODUCTION_PROMOTION"
LEVEL3_5B_HELDOUT_V3_NO_CLAIMS = "NO_CONFIRMATORY_CLAIMS"

LEVEL3_5B_GATE_CHECKPOINT = "8ed6113"
EXPECTED_PROTOCOL_V3_HASH = "4b197802b51f2bf1d02798d3bca2e857cb77b22e8c39350759221725ba8a48f2"
EXPECTED_BCH_HASH = "7974133f002cbba795ae4655f7ab8b75bc6621f86991c13bd1e4d97d3ba733f3"
EXPECTED_MAP_HASHES = {
    "map_d1024": "11fd00e0f0ed8bd4341e51169ca7bde135299d69e11798ad4a97b96ed96e5ff9",
    "map_d1024_step32_r4_best_native_reconstruction": "b32e989b0016c44e0d8cac61d0aead60edd43efc7ff686d1ff76e779c5747bff",
}

PROTOCOL_V3_PATH = "results/level3_5b_gate_specification/heldout_protocol_v3.json"
GATE_SPEC_ANALYSIS_PATH = "results/level3_5b_gate_specification/analysis.json"
GATE_SPEC_VALIDATOR_PATH = "results/level3_5b_gate_specification/validator_result.json"
GATE_SPEC_DRY_RUN_PATH = "results/level3_5b_gate_specification/synthetic_dry_run_results.json"
GATE_SPEC_DOC_PATH = "docs/LEVEL3_5B_PROSPECTIVE_GATE_SPECIFICATION.md"
PROTOCOL_V2_PATH = "results/level3_5b_protocol_repair/heldout_protocol_v2.json"
SEED_AUDIT_PATH = "results/level3_5b_protocol_repair/seed_audit.json"
V1_BLOCKED_DOC_PATH = "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md"
V2_REPAIR_DOC_PATH = "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md"
V2_BLOCKED_DOC_PATH = "docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md"
BCH_CONFIG_PATH = "results/level3_5b_dev/bch_configs.json"

IMMUTABLE_PREVIOUS_PATHS = (
    "results/level3_5b_heldout",
    "results/level3_5b_protocol_repair",
    "results/level3_5b_heldout_v2",
    "results/level3_5b_gate_specification",
    V1_BLOCKED_DOC_PATH,
    V2_REPAIR_DOC_PATH,
    V2_BLOCKED_DOC_PATH,
    GATE_SPEC_DOC_PATH,
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
    "gate_inputs.json",
    "gate_results.json",
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


def execution_already_materialized(results_dir: Path) -> bool:
    completion = results_dir / "completion_manifest.json"
    if not completion.exists():
        return False
    payload = read_json(completion)
    return bool(payload.get("rerun_after_completion_forbidden", False))


def touch_empty(path: Path) -> None:
    path.write_text("", encoding="utf-8")


def range_to_seed_list(spec: dict[str, int]) -> list[int]:
    return list(range(int(spec["start"]), int(spec["end"]) + 1))


def build_execution_seed_lists(protocol: dict[str, Any]) -> dict[str, dict[str, list[int]]]:
    payload: dict[str, dict[str, list[int]]] = {}
    for track_name in ("binary_track", "map_track"):
        payload[track_name] = {}
        for cell_id, spec in protocol["fresh_seed_ranges"][track_name].items():
            payload[track_name][cell_id] = range_to_seed_list(spec)
    return payload


def git_changed_paths_since(repo_root: Path, checkpoint: str, paths: tuple[str, ...]) -> list[str]:
    _, stdout, _ = git_stdout(repo_root, "diff", "--name-only", checkpoint, "HEAD", "--", *paths)
    return [line for line in stdout.splitlines() if line]


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def ensure_synthetic_dry_run_passes(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    rows = payload.get("rows", {})
    for gate_id, cases in rows.items():
        expected_states = {
            "pass_case": "PASS",
            "fail_case": "FAIL",
            "boundary_case": "PASS",
            "missing_data_case": "INCOMPLETE_INPUT",
            "exceptional_trial_case": "INCOMPLETE_INPUT",
            "contradictory_metrics_case": "EXCEPTION",
        }
        for case_name, expected_state in expected_states.items():
            observed = cases.get(case_name, {}).get("state")
            if observed != expected_state:
                failures.append(
                    f"Synthetic dry-run {gate_id}/{case_name} expected {expected_state}, observed {observed}."
                )
        tie_state = cases.get("tie_case", {}).get("state")
        if tie_state not in {"PASS", "not applicable", None}:
            failures.append(f"Synthetic dry-run {gate_id}/tie_case has unexpected state {tie_state}.")
    return (not failures), failures


def cell_specs_from_protocol(protocol: dict[str, Any], track_name: str) -> list[dict[str, Any]]:
    payload = []
    semantic_payloads = protocol["preserved_scientific_fields"]["semantic_payloads"]
    for cell_id in protocol["preserved_scientific_fields"][track_name]["semantic_cells"]:
        spec = semantic_payloads[cell_id]
        payload.append({"cell_id": cell_id, "F": int(spec["factor_count"]), "M": int(spec["domain_size"])})
    return payload


def parse_exact_weight_label(label: str) -> int:
    return int(label.split("=", 1)[1])


def parse_probability_label(label: str) -> float:
    return float(label.split("=", 1)[1])


def point_seed_offset(arm_id: str, probability: float) -> int:
    initial_points = {0.0, 0.01, 0.02, 0.05, 0.1, 0.2}
    if arm_id == MAP_FAST_ARM_ID:
        return 4_000_000 if probability in initial_points else 6_000_000
    if arm_id == MAP_EXTENDED_ARM_ID:
        return 5_000_000 if probability in initial_points else 7_000_000
    raise KeyError(f"Unsupported MAP arm {arm_id}")


def normalize_row_schema(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["schema_version"] = LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION
        manifest = row.get("external_corruption_spec")
        if isinstance(manifest, dict):
            manifest["channel_application_stage"] = "post_clean_construction"


def append_map_summary_metrics(summary_rows: list[dict[str, Any]], raw_rows: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in raw_rows:
        key = (row["method_id"], row["cell_id"], row["corruption_label"])
        grouped.setdefault(key, []).append(row)
    for row in summary_rows:
        key = (row["method_id"], row["cell_id"], row["corruption_label"])
        batch = grouped[key]
        row["mean_native_reconstruction_score"] = statistics.fmean(
            float(item["native_reconstruction_score"]) for item in batch
        )
        row["mean_min_margin"] = statistics.fmean(float(item["min_margin"]) for item in batch)
        row["mean_mean_margin"] = statistics.fmean(float(item["mean_margin"]) for item in batch)
        row["mean_restart_agreement"] = statistics.fmean(float(item["restart_agreement"]) for item in batch)
        row["mean_unique_restart_proposals"] = statistics.fmean(
            float(item["unique_restart_proposals"]) for item in batch
        )
        row["mean_executed_restarts"] = statistics.fmean(float(item["executed_restarts"]) for item in batch)


def build_gate_inputs(
    protocol: dict[str, Any],
    *,
    binary_summary_rows: list[dict[str, Any]],
    map_summary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    binary_lookup = {
        (row["method_id"], row["cell_id"], row["channel_id"], row["corruption_label"]): row
        for row in binary_summary_rows
    }
    map_lookup = {
        (row["method_id"], row["cell_id"], row["channel_id"], row["corruption_label"]): row
        for row in map_summary_rows
    }
    outputs: list[dict[str, Any]] = []
    for gate in protocol["confirmatory_gates"]:
        used_rows: list[dict[str, Any]] = []
        if gate["id"] == "no_shared_noise_winner_contract_v1":
            outputs.append(
                {
                    "gate_id": gate["id"],
                    "rule_hash": gate["rule_hash"],
                    "inputs_used": {
                        "binary_channels": protocol["preserved_scientific_fields"]["binary_track"]["corruption_channels"],
                        "map_channels": protocol["preserved_scientific_fields"]["map_track"]["corruption_channels"],
                        "binary_claim_limits": protocol["preserved_scientific_fields"]["binary_track"]["claim_limits"],
                        "global_claim_limits": protocol["claim_limits"]["global"],
                        "bcf_status": protocol["preserved_scientific_fields"]["bcf_track"]["status"],
                    },
                }
            )
            continue

        if gate["id"].startswith("map_"):
            methods = gate["methods"].get("candidates", [gate["methods"].get("candidate")])
            channel_id = gate["corruption_points"]["channel_id"]
            for cell_id, labels in gate["required_points"].items():
                for method_id in methods:
                    for label in labels:
                        row = map_lookup[(method_id, cell_id, channel_id, label)]
                        used_rows.append(row)
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            channel_id = gate["corruption_points"]["channel_id"]
            for cell_id, labels in gate["required_points"].items():
                for label in labels:
                    for method_id in (
                        gate["methods"]["candidate"],
                        gate["methods"]["comparator"],
                    ):
                        row = binary_lookup[(method_id, cell_id, channel_id, label)]
                        used_rows.append(row)
        elif gate["id"] == "raw_neco_noise_gap_v1":
            channel_id = gate["corruption_points"]["channel_id"]
            method_id = gate["methods"]["candidate"]
            for cell_id in gate["required_cells"]:
                clean_label = gate["required_points"]["clean"][cell_id]
                nonzero_label = gate["required_points"]["nonzero"][cell_id]
                used_rows.append(binary_lookup[(method_id, cell_id, channel_id, clean_label)])
                used_rows.append(binary_lookup[(method_id, cell_id, channel_id, nonzero_label)])
        else:
            channel_id = gate["corruption_points"]["channel_id"]
            methods = [gate["methods"].get("candidate")] + gate["methods"].get("comparators", [])
            for cell_id, labels in gate["required_points"].items():
                for label in labels:
                    for method_id in methods:
                        if method_id is None:
                            continue
                        used_rows.append(binary_lookup[(method_id, cell_id, channel_id, label)])

        outputs.append(
            {
                "gate_id": gate["id"],
                "rule_hash": gate["rule_hash"],
                "inputs_used": used_rows,
            }
        )
    return outputs


def enrich_gate_result(gate: dict[str, Any], result: dict[str, Any], gate_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": gate["id"],
        "rule_hash": gate["rule_hash"],
        "inputs_used": gate_inputs["inputs_used"],
        "pass_or_fail": result["state"],
        "resulting_disposition": result["disposition"],
        "boundary_case_handling": {
            "tie_policy": gate["tie_policy"],
            "threshold_equality_policy": "threshold equality counts as pass"
            if "threshold equality counts as pass" in gate["tie_policy"]
            else "see gate thresholds and tie_policy",
        },
        "missing_or_exception_handling": {
            "missing_trial_policy": gate["missing_trial_policy"],
            "exceptional_trial_policy": gate["exceptional_trial_policy"],
        },
        "reasons": result["reasons"],
    }


def render_heldout_v3_doc(repo_root: Path, analysis: dict[str, Any], verdicts: dict[str, Any]) -> None:
    lines = [
        "# Level 3.5b Held-Out Native Noise Frontier Confirmation v3",
        "",
        f"- Schema: `{LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION}`",
        f"- Checkpoint: `{LEVEL3_5B_GATE_CHECKPOINT}`",
        f"- Stage status: `{analysis['final_stage_status']}`",
        f"- Promotion status: `{analysis['promotion_status']}`",
        f"- Overall verdict: `{verdicts['overall_verdict']}`",
        "",
        "## Guardrails",
        "",
        "- Protocol v3 only.",
        "- No v1/v2 execution, no rerun, no replacement seeds, no adaptive points.",
        "- BCF remains blocked by contract ambiguity.",
        "- No universal cross-track leaderboard.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_HELDOUT_V3_NOISE_CONFIRMATION.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def evaluate_protocol_v3_integrity(repo_root: Path, *, results_dir: Path) -> dict[str, Any]:
    protocol_path = repo_root / PROTOCOL_V3_PATH
    protocol = read_json(protocol_path)
    gate_analysis = read_json(repo_root / GATE_SPEC_ANALYSIS_PATH)
    gate_validator = read_json(repo_root / GATE_SPEC_VALIDATOR_PATH)
    gate_dry_run = read_json(repo_root / GATE_SPEC_DRY_RUN_PATH)
    seed_audit = read_json(repo_root / SEED_AUDIT_PATH)
    v2_protocol = read_json(repo_root / PROTOCOL_V2_PATH)
    v1_analysis = read_json(repo_root / "results" / "level3_5b_heldout" / "analysis.json")
    v2_analysis = read_json(repo_root / "results" / "level3_5b_heldout_v2" / "analysis.json")

    ancestry_rc, _, _ = git_stdout(
        repo_root,
        "merge-base",
        "--is-ancestor",
        LEVEL3_5B_GATE_CHECKPOINT,
        "HEAD",
        allow_failure=True,
    )
    ancestry_ok = ancestry_rc == 0
    protocol_hash = canonical_json_hash(protocol)
    protocol_file_hash = sha256_path(protocol_path)
    bch_hash = sha256_path(repo_root / BCH_CONFIG_PATH)
    map_hashes = protocol["config_hashes"]["map_arm_hashes"]

    immutable_changed = git_changed_paths_since(repo_root, LEVEL3_5B_GATE_CHECKPOINT, IMMUTABLE_PREVIOUS_PATHS)
    prior_trials_present = any(
        (results_dir / relative_path).exists() and (results_dir / relative_path).stat().st_size > 0
        for relative_path in ("binary_trials.jsonl", "map_trials.jsonl", "semantic_manifests.jsonl")
    )
    prior_execution_present = execution_already_materialized(results_dir)

    synthetic_pass, synthetic_failures = ensure_synthetic_dry_run_passes(gate_dry_run)

    gate_hash_failures: list[str] = []
    for gate in protocol["confirmatory_gates"]:
        observed = protocol["canonical_gate_hashes"].get(gate["id"])
        recomputed = complete_gate_hash(gate)
        if observed != recomputed:
            gate_hash_failures.append(f"{gate['id']} expected {observed}, recomputed {recomputed}")

    failures: list[str] = []
    if not ancestry_ok:
        failures.append(f"Current git ancestry does not include required checkpoint {LEVEL3_5B_GATE_CHECKPOINT}.")
    if protocol_hash != EXPECTED_PROTOCOL_V3_HASH:
        failures.append(f"Protocol v3 hash mismatch: expected {EXPECTED_PROTOCOL_V3_HASH}, observed {protocol_hash}.")
    if bch_hash != EXPECTED_BCH_HASH:
        failures.append(f"BCH config hash mismatch: expected {EXPECTED_BCH_HASH}, observed {bch_hash}.")
    if map_hashes != EXPECTED_MAP_HASHES:
        failures.append(f"MAP config hashes mismatch: expected {EXPECTED_MAP_HASHES}, observed {map_hashes}.")
    if protocol["supersedes_protocol_v2_hash"] != PROTOCOL_V2_CANONICAL_HASH:
        failures.append("Protocol v3 does not supersede the frozen v2 canonical hash.")
    if seed_audit.get("audit_verdict") != "PASS":
        failures.append(f"Seed audit is not PASS: observed {seed_audit.get('audit_verdict')}.")
    if gate_validator.get("validator_verdict") != "GATES_SPECIFIED_AND_FINAL_PROTOCOL_FROZEN":
        failures.append(
            f"Gate-spec validator verdict is not GATES_SPECIFIED_AND_FINAL_PROTOCOL_FROZEN: observed {gate_validator.get('validator_verdict')}."
        )
    if gate_analysis.get("heldout_trials_observed") != 0:
        failures.append("Gate-spec analysis no longer reports zero held-out trials observed.")
    if immutable_changed:
        failures.append(f"Previously frozen v1/v2/gate-spec artifacts changed since {LEVEL3_5B_GATE_CHECKPOINT}: {immutable_changed}.")
    if gate_hash_failures:
        failures.extend([f"Gate hash mismatch: {item}" for item in gate_hash_failures])
    if not synthetic_pass:
        failures.extend(synthetic_failures)
    if prior_trials_present:
        failures.append("Held-out v3 results directory already contains non-empty trial outcome files.")
    if prior_execution_present:
        failures.append("Held-out v3 completion manifest already exists; rerun is forbidden.")
    if v1_analysis.get("trials_executed", 0) != 0 or v2_analysis.get("trials_executed", 0) != 0:
        failures.append("Previous blocked held-out attempts no longer report zero executed trials.")

    return {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "required_checkpoint": LEVEL3_5B_GATE_CHECKPOINT,
        "current_git_commit": current_git_commit(repo_root),
        "ancestry_ok": ancestry_ok,
        "protocol_v3_path": PROTOCOL_V3_PATH,
        "protocol_v3_hash_expected": EXPECTED_PROTOCOL_V3_HASH,
        "protocol_v3_hash_observed": protocol_hash,
        "protocol_v3_file_hash_observed": protocol_file_hash,
        "bch_hash_expected": EXPECTED_BCH_HASH,
        "bch_hash_observed": bch_hash,
        "map_hashes_expected": EXPECTED_MAP_HASHES,
        "map_hashes_observed": map_hashes,
        "gate_hashes_expected": protocol["canonical_gate_hashes"],
        "gate_hashes_match": not gate_hash_failures,
        "gate_hash_failures": gate_hash_failures,
        "seed_audit_pass": seed_audit.get("audit_verdict") == "PASS",
        "old_protocols_unchanged": not immutable_changed,
        "changed_immutable_paths": immutable_changed,
        "synthetic_dry_run_pass": synthetic_pass,
        "synthetic_dry_run_failures": synthetic_failures,
        "gate_schema_complete": gate_validator.get("gate_schema_complete", False),
        "deterministic_gate_order": protocol["deterministic_verdict_evaluation_order"],
        "results_dir_preexisting": results_dir.exists(),
        "prior_trials_present": prior_trials_present,
        "prior_execution_present": prior_execution_present,
        "heldout_trials_observed_before_v3": 0,
        "blocked": bool(failures),
        "integrity_failures": failures,
    }


def run_level3_5b_heldout_v3(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_heldout_v3"
    if execution_already_materialized(results_dir):
        raise RuntimeError("Held-out v3 execution artifacts already exist; rerun is forbidden.")

    protocol = read_json(repo_root / PROTOCOL_V3_PATH)
    integrity = evaluate_protocol_v3_integrity(repo_root, results_dir=results_dir)
    env = environment_snapshot()
    environment = {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "python_version": env["python_version"],
        "platform": env["platform"],
        "galois_version": env["galois_version"],
        "torch_version": env["torch_version"],
        "cuda_available": env["cuda_available"],
        "git_commit": current_git_commit(repo_root),
        "timestamp_utc": utc_now_iso(),
        "protocol_version_required": protocol["protocol_version"],
    }

    results_dir.mkdir(parents=True, exist_ok=True)
    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "protocol_integrity.json", integrity)

    execution_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "protocol_path": PROTOCOL_V3_PATH,
        "protocol_version": protocol["protocol_version"],
        "protocol_hash": integrity["protocol_v3_hash_observed"],
        "git_commit": environment["git_commit"],
        "config_hashes": {
            "bch": integrity["bch_hash_observed"],
            "map": integrity["map_hashes_observed"],
            "gates": protocol["canonical_gate_hashes"],
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
        "device_information": {
            "binary_track_device": "cpu",
            "map_track_device": "\"cuda:0\" if available else cpu",
        },
        "start_timestamp": utc_now_iso(),
        "trials_executed_before_manifest": 0,
        "execution_authorized": not integrity["blocked"],
    }
    write_json(results_dir / "execution_manifest.json", execution_manifest)

    if integrity["blocked"]:
        for relative_path in PLACEHOLDER_RELATIVE_PATHS:
            touch_empty(results_dir / relative_path)
        bcf_status = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "status": BCF_TRACK_BLOCKED,
            "executed": False,
            "reason": protocol["preserved_scientific_fields"]["bcf_track"]["reason"],
        }
        write_json(results_dir / "bcf_status.json", bcf_status)
        completion_manifest = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "completed_at": utc_now_iso(),
            "trials_executed_binary": 0,
            "trials_executed_map": 0,
            "overall_verdict": LEVEL3_5B_HELDOUT_V3_BLOCKED,
            "rerun_after_completion_forbidden": True,
        }
        write_json(results_dir / "completion_manifest.json", completion_manifest)
        verdicts = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "overall_verdict": LEVEL3_5B_HELDOUT_V3_BLOCKED,
            "confirmatory_verdicts": {},
            "bcf_track": BCF_TRACK_BLOCKED,
            "blocked_reason": integrity["integrity_failures"],
        }
        write_json(results_dir / "verdicts.json", verdicts)
        claims = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "allowed_claims": [
                "Protocol integrity failed before the first held-out trial.",
                "No held-out v3 outcome was observed.",
            ],
            "forbidden_claims": [
                "Any substantive Level 3.5b held-out v3 noise-frontier claim.",
            ],
        }
        write_json(results_dir / "claims.json", claims)
        analysis = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "final_stage_status": LEVEL3_5B_HELDOUT_V3_BLOCKED,
            "promotion_status": LEVEL3_5B_HELDOUT_V3_PROMOTION,
            "benchmark_execution_invoked": False,
            "trials_executed": 0,
        }
        write_json(results_dir / "analysis.json", analysis)
        render_heldout_v3_doc(repo_root, analysis, verdicts)
        return analysis

    binary_methods = set(protocol["preserved_scientific_fields"]["binary_track"]["methods"])
    map_methods = set(protocol["preserved_scientific_fields"]["map_track"]["methods"])
    binary_cells = cell_specs_from_protocol(protocol, "binary_track")
    map_cells = cell_specs_from_protocol(protocol, "map_track")
    binary_points = protocol["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"]
    map_points = protocol["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]
    seed_lists = build_execution_seed_lists(protocol)

    manifests_rows: list[dict[str, Any]] = []
    binary_rows: list[dict[str, Any]] = []
    map_rows: list[dict[str, Any]] = []
    bcf_status = {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "status": BCF_TRACK_BLOCKED,
        "executed": False,
        "reason": protocol["preserved_scientific_fields"]["bcf_track"]["reason"],
    }
    write_json(results_dir / "bcf_status.json", bcf_status)

    completed_successfully = False
    incomplete_reason: str | None = None
    try:
        for cell in binary_cells:
            for seed in seed_lists["binary_track"][cell["cell_id"]]:
                manifest, task = build_task(seed, cell, "binary_exact_record")
                manifest = replace(manifest, split="heldout_noise_frontier_v3")
                manifests_rows.append(manifest.to_dict())
                representations = prepare_binary_representations(manifest, task)
                for label in binary_points[cell["cell_id"]]:
                    severity = float(parse_exact_weight_label(label))
                    batch = build_binary_method_rows(
                        manifest,
                        task,
                        representations,
                        channel_id=CHANNEL_EXACT_WEIGHT,
                        severity_value=severity,
                        corruption_label=label,
                        corruption_seed_offset=1_000_000 + int(severity * 100),
                    )
                    for row in batch:
                        if row["method_id"] in binary_methods:
                            row["split"] = manifest.split
                            binary_rows.append(row)

        device = "cuda:0" if env["cuda_available"] else "cpu"
        for cell in map_cells:
            for seed in seed_lists["map_track"][cell["cell_id"]]:
                manifest, task = build_task(seed, cell, "map_native_sign_flip")
                manifest = replace(manifest, split="heldout_noise_frontier_v3")
                manifests_rows.append(manifest.to_dict())
                prepared = prepare_map_runs(manifest, task, device=device)
                for label in map_points[cell["cell_id"]]:
                    probability = float(parse_probability_label(label))
                    for arm_id in protocol["preserved_scientific_fields"]["map_track"]["methods"]:
                        row, _ = run_map_arm(
                            prepared,
                            task,
                            manifest,
                            arm_id=arm_id,
                            probability=probability,
                            seed_offset=point_seed_offset(arm_id, probability) + int(probability * 1_000_000),
                        )
                        if row["method_id"] in map_methods:
                            row["split"] = manifest.split
                            map_rows.append(row)

        normalize_row_schema(binary_rows)
        normalize_row_schema(map_rows)
        write_jsonl(results_dir / "semantic_manifests.jsonl", manifests_rows)
        write_jsonl(results_dir / "binary_trials.jsonl", binary_rows)
        write_jsonl(results_dir / "map_trials.jsonl", map_rows)

        binary_summary = summarize_track(binary_rows, include_payload=True)
        map_summary = summarize_track(map_rows, include_payload=False)
        for row in binary_summary:
            row["schema_version"] = LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION
        for row in map_summary:
            row["schema_version"] = LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION
        append_map_summary_metrics(map_summary, map_rows)

        write_csv(results_dir / "binary_summary.csv", binary_summary)
        write_csv(results_dir / "map_summary.csv", map_summary)

        silent_error_summary = [
            {
                "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
                "track_id": row["track_id"],
                "method_id": row["method_id"],
                "cell_id": row["cell_id"],
                "channel_id": row["channel_id"],
                "corruption_label": row["corruption_label"],
                "silent_wrong_rate": row["silent_wrong_rate"],
                "detected_failure_rate": row["detected_failure_rate"],
                "conditional_wrong_given_nonfailure": row["conditional_wrong_given_nonfailure"],
            }
            for row in (binary_summary + map_summary)
        ]
        write_csv(results_dir / "silent_error_summary.csv", silent_error_summary)

        resource_summary = [
            {
                "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
                "track_id": row["track_id"],
                "method_id": row["method_id"],
                "cell_id": row["cell_id"],
                "channel_id": row["channel_id"],
                "corruption_label": row["corruption_label"],
                "mean_persistent_bytes": row["mean_persistent_bytes"],
                "mean_runtime_materialized_bytes": row["mean_runtime_materialized_bytes"],
                "mean_transmitted_or_observation_bits": row["mean_transmitted_or_observation_bits"],
                "mean_redundancy_ratio": row["mean_redundancy_ratio"],
            }
            for row in (binary_summary + map_summary)
        ]
        write_csv(results_dir / "resource_summary.csv", resource_summary)

        timing_summary = [
            {
                "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
                "track_id": row["track_id"],
                "method_id": row["method_id"],
                "cell_id": row["cell_id"],
                "channel_id": row["channel_id"],
                "corruption_label": row["corruption_label"],
                "median_decode_latency_sec": row["median_decode_latency_sec"],
                "p90_decode_latency_sec": row["p90_decode_latency_sec"],
                "p99_decode_latency_sec": row["p99_decode_latency_sec"],
                "median_end_to_end_latency_sec": row["median_end_to_end_latency_sec"],
            }
            for row in (binary_summary + map_summary)
        ]
        write_csv(results_dir / "timing_summary.csv", timing_summary)

        gate_inputs = build_gate_inputs(
            protocol,
            binary_summary_rows=binary_summary,
            map_summary_rows=map_summary,
        )
        write_json(results_dir / "gate_inputs.json", {"schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION, "rows": gate_inputs})

        loaded_binary_rows = load_csv_rows(results_dir / "binary_summary.csv")
        loaded_map_rows = load_csv_rows(results_dir / "map_summary.csv")
        gate_inputs_lookup = {row["gate_id"]: row for row in gate_inputs}
        gate_results: list[dict[str, Any]] = []
        confirmatory_verdicts: dict[str, str] = {}
        gate_incomplete = False
        for gate_id in protocol["deterministic_verdict_evaluation_order"]:
            gate = next(item for item in protocol["confirmatory_gates"] if item["id"] == gate_id)
            result = evaluate_gate(
                gate,
                binary_rows=loaded_binary_rows,
                map_rows=loaded_map_rows,
                protocol_v3=protocol,
            )
            enriched = enrich_gate_result(gate, result, gate_inputs_lookup[gate_id])
            gate_results.append(enriched)
            if result["state"] not in {"PASS", "FAIL"}:
                gate_incomplete = True
            if result["disposition"] is not None:
                confirmatory_verdicts[gate["disposition_if_pass"]] = (
                    result["disposition"] == gate["disposition_if_pass"]
                )
                confirmatory_verdicts[gate["disposition_if_fail"]] = (
                    result["disposition"] == gate["disposition_if_fail"]
                )
        confirmatory_verdicts[BCF_TRACK_BLOCKED] = True
        write_json(results_dir / "gate_results.json", {"schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION, "rows": gate_results})

        if gate_incomplete:
            completed_successfully = False
            incomplete_reason = "Gate evaluation returned INCOMPLETE_INPUT or EXCEPTION."
        else:
            completed_successfully = True
    except Exception as exc:  # pragma: no cover - infrastructure safeguard
        incomplete_reason = f"{type(exc).__name__}: {exc}"
        if manifests_rows:
            write_jsonl(results_dir / "semantic_manifests.jsonl", manifests_rows)
        if binary_rows:
            normalize_row_schema(binary_rows)
            write_jsonl(results_dir / "binary_trials.jsonl", binary_rows)
        if map_rows:
            normalize_row_schema(map_rows)
            write_jsonl(results_dir / "map_trials.jsonl", map_rows)

    binary_trial_count = len(binary_rows)
    map_trial_count = len(map_rows)

    if completed_successfully:
        verdict_rows = read_json(results_dir / "gate_results.json")["rows"]
        verdicts = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "overall_verdict": LEVEL3_5B_HELDOUT_V3_STAGE_COMPLETE,
            "confirmatory_gate_order": protocol["deterministic_verdict_evaluation_order"],
            "gate_dispositions": {
                row["gate_id"]: row["resulting_disposition"] for row in verdict_rows
            },
            "bcf_track": BCF_TRACK_BLOCKED,
        }
        claims = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "allowed_claims": [
                "Claims are limited to the frozen Level 3.5b v3 cells, channels, points and methods.",
                "Binary exact-record conclusions apply only to the exact-weight binary channel.",
                "MAP conclusions apply only to the frozen post-product sign-flip contract.",
                "BCF remains blocked by contract ambiguity and was not invoked.",
            ],
            "forbidden_claims": [
                "Any universal cross-track raw-p leaderboard.",
                "Any noisy BCF claim.",
                "Any production-promotion claim.",
                "Any U2, histogram or subject-memory claim.",
            ],
        }
        analysis = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "final_stage_status": LEVEL3_5B_HELDOUT_V3_STAGE_COMPLETE,
            "promotion_status": LEVEL3_5B_HELDOUT_V3_PROMOTION,
            "benchmark_execution_invoked": True,
            "trials_executed": binary_trial_count + map_trial_count,
            "binary_trial_rows": binary_trial_count,
            "map_trial_rows": map_trial_count,
            "bcf_invoked": False,
            "all_frozen_trials_executed_once": True,
            "no_manual_override": True,
            "development_conclusions_confirmed": [
                row["resulting_disposition"]
                for row in verdict_rows
                if row["resulting_disposition"] and row["resulting_disposition"].endswith("_CONFIRMED")
            ],
            "development_conclusions_not_confirmed": [
                row["resulting_disposition"]
                for row in verdict_rows
                if row["resulting_disposition"] and row["resulting_disposition"].endswith("_NOT_CONFIRMED")
            ],
            "contract_level_conclusions": [
                row["resulting_disposition"]
                for row in verdict_rows
                if row["resulting_disposition"] == "NO_SHARED_NOISE_WINNER"
            ],
        }
    else:
        verdicts = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "overall_verdict": LEVEL3_5B_HELDOUT_V3_STAGE_INCOMPLETE,
            "confirmatory_gate_order": protocol["deterministic_verdict_evaluation_order"],
            "bcf_track": BCF_TRACK_BLOCKED,
            "incomplete_reason": incomplete_reason,
        }
        claims = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "allowed_claims": [
                "Held-out v3 execution did not complete.",
                "Completed trial rows were preserved without replacement seeds.",
            ],
            "forbidden_claims": [
                "Any substantive confirmatory noise-frontier claim from incomplete execution.",
            ],
        }
        analysis = {
            "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
            "final_stage_status": LEVEL3_5B_HELDOUT_V3_STAGE_INCOMPLETE,
            "promotion_status": LEVEL3_5B_HELDOUT_V3_NO_CLAIMS,
            "benchmark_execution_invoked": True,
            "trials_executed": binary_trial_count + map_trial_count,
            "binary_trial_rows": binary_trial_count,
            "map_trial_rows": map_trial_count,
            "bcf_invoked": False,
            "incomplete_reason": incomplete_reason,
        }

    write_json(results_dir / "verdicts.json", verdicts)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    completion_manifest = {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "completed_at": utc_now_iso(),
        "trials_executed_binary": binary_trial_count,
        "trials_executed_map": map_trial_count,
        "all_trials_executed": completed_successfully,
        "overall_verdict": verdicts["overall_verdict"],
        "rerun_after_completion_forbidden": True,
    }
    write_json(results_dir / "completion_manifest.json", completion_manifest)
    render_heldout_v3_doc(repo_root, analysis, verdicts)

    return {
        "schema_version": LEVEL3_5B_HELDOUT_V3_SCHEMA_VERSION,
        "overall_verdict": verdicts["overall_verdict"],
        "binary_trial_rows": binary_trial_count,
        "map_trial_rows": map_trial_count,
        "bcf_status": BCF_TRACK_BLOCKED,
    }
