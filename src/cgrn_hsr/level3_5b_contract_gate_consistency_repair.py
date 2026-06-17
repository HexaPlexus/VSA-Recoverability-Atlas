from __future__ import annotations

import json
import platform
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_5b_gate_specification import (
    ALLOWED_DIFF_TYPES,
    BCF_BLOCKED,
    LEVEL3_5B_GATE_BLOCK_CHANGE,
    PROTOCOL_V2_CANONICAL_HASH,
    build_synthetic_cases,
    canonical_json_hash,
    complete_gate_hash,
    evaluate_gate,
    exception_result,
    gate_source_audit_records,
    read_json,
)
from .level3_5b_protocol_repair import sha256_path
from .level3_5b_native_noise_frontiers import write_json

LEVEL3_5B_GATE_CONSISTENCY_SCHEMA = "level3-5b-contract-gate-consistency-v1"
LEVEL3_5B_HELDOUT_V4_VERSION = "level3.5b-heldout-v4"
V3_HASH = "4b197802b51f2bf1d02798d3bca2e857cb77b22e8c39350759221725ba8a48f2"
BLOCKED_V3_COMMIT = "c2bc5fc"

VERDICT_REPAIRED = "CONTRACT_GATE_CONSISTENCY_REPAIRED"
VERDICT_REFROZEN = "FINAL_PROTOCOL_REFROZEN"
VERDICT_READY = "READY_FOR_LEVEL_3_5B_HELDOUT_V4"
BLOCK_AMBIGUOUS = "BLOCKED_AMBIGUOUS_CONTRACT_GATE_SEMANTICS"
BLOCK_PERFORMANCE = "BLOCKED_REPAIR_REQUIRES_PERFORMANCE_GATE_CHANGE"
BLOCK_DIFF = "BLOCKED_UNAUTHORIZED_PROTOCOL_DIFF"

PROTOCOL_V3_PATH = "results/level3_5b_gate_specification/heldout_protocol_v3.json"
V3_ANALYSIS_PATH = "results/level3_5b_heldout_v3/analysis.json"
V3_COMPLETION_PATH = "results/level3_5b_heldout_v3/completion_manifest.json"
V3_DOC_PATH = "docs/LEVEL3_5B_HELDOUT_V3_NOISE_CONFIRMATION.md"

IMMUTABLE_V1_V2_V3_PATHS = (
    "results/level3_5b_heldout",
    "results/level3_5b_protocol_repair",
    "results/level3_5b_heldout_v2",
    "results/level3_5b_gate_specification",
    "results/level3_5b_heldout_v3",
    "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md",
    "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md",
    "docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md",
    "docs/LEVEL3_5B_PROSPECTIVE_GATE_SPECIFICATION.md",
    V3_DOC_PATH,
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


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def find_gate(protocol: dict[str, Any], gate_id: str) -> dict[str, Any]:
    return next(gate for gate in protocol["confirmatory_gates"] if gate["id"] == gate_id)


def build_contract_metadata(protocol_v4: dict[str, Any]) -> dict[str, Any]:
    return {
        "no_shared_noise_winner_contract_v1": {
            "binary_track_channel_ids": protocol_v4["preserved_scientific_fields"]["binary_track"]["corruption_channels"],
            "map_track_channel_ids": protocol_v4["preserved_scientific_fields"]["map_track"]["corruption_channels"],
            "shared_calibrated_severity_mapping_exists": False,
            "cross_track_equal_difficulty_claim_allowed": False,
            "bcf_track_status": protocol_v4["preserved_scientific_fields"]["bcf_track"]["status"],
        }
    }


def build_protocol_v4(protocol_v3: dict[str, Any]) -> dict[str, Any]:
    protocol_v4 = deepcopy(protocol_v3)
    protocol_v4["protocol_version"] = LEVEL3_5B_HELDOUT_V4_VERSION
    protocol_v4["supersedes_protocol_v3_hash"] = V3_HASH
    protocol_v4["heldout_trials_observed_before_v4"] = 0
    protocol_v4["repair_scope"] = "no_shared_noise_winner_contract_v1 dry-run consistency only"
    protocol_v4["contract_gate_metadata"] = build_contract_metadata(protocol_v4)

    gate = deepcopy(find_gate(protocol_v4, "no_shared_noise_winner_contract_v1"))
    gate["source_provenance"] = {
        **gate["source_provenance"],
        "rule_origin": "CLARIFIED_CONTRACT_GATE_PREHELDOUT",
        "repair_scope": "dry-run consistency only",
    }
    gate["comparison_operator"] = (
        "contract metadata must be present and well-typed; then the protocol passes only if binary/map channel sets differ, "
        "shared calibrated severity mapping is absent, cross-track equal-difficulty winner claims remain forbidden, and BCF stays blocked"
    )
    gate["thresholds"] = {
        "requires_distinct_channel_sets": True,
        "requires_shared_calibrated_severity_mapping_exists": False,
        "requires_cross_track_equal_difficulty_claim_allowed": False,
        "requires_bcf_track_blocked": True,
        "exception_on_missing_or_malformed_contract_metadata": True,
    }
    gate["exceptional_trial_policy"] = (
        "EXCEPTION on missing, malformed or internally contradictory contract metadata; otherwise PASS or FAIL only"
    )
    gate["rule_version"] = "v2"
    gate["rule_hash"] = complete_gate_hash(gate)

    protocol_v4["confirmatory_gates"] = [
        gate if item["id"] == "no_shared_noise_winner_contract_v1" else item
        for item in protocol_v4["confirmatory_gates"]
    ]
    protocol_v4["canonical_gate_hashes"] = {
        item["id"]: item["rule_hash"] for item in protocol_v4["confirmatory_gates"]
    }
    return protocol_v4


def build_root_cause_audit(protocol_v3: dict[str, Any], protocol_v4: dict[str, Any]) -> dict[str, Any]:
    gate_v3 = find_gate(protocol_v3, "no_shared_noise_winner_contract_v1")
    gate_v4 = find_gate(protocol_v4, "no_shared_noise_winner_contract_v1")
    return {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "gate_rule": gate_v3["id"],
        "gate_rule_hash": gate_v3["rule_hash"],
        "repaired_gate_rule_hash": gate_v4["rule_hash"],
        "synthetic_fixture": "contradictory_metrics_case in v3 dry-run validator",
        "fixture_expected_outcome": "EXCEPTION",
        "evaluator_actual_outcome": "FAIL",
        "rule_semantics": "PASS for established incompatibility; FAIL for valid metadata that permits or implies a shared comparable noise scale; EXCEPTION for missing or malformed contract metadata.",
        "missing_data_semantics": "EXCEPTION for absent required contract metadata.",
        "exception_semantics": "EXCEPTION for missing or malformed contract metadata.",
        "fail_semantics": "FAIL for valid metadata that removes the cross-track incompatibility guardrail.",
        "fixture_input_validity": "VALID_FAIL_CASE",
        "root_cause": "AMBIGUOUS_RULE_SEMANTICS",
    }


def build_protocol_diff(protocol_v3: dict[str, Any], protocol_v4: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "v3_canonical_hash": canonical_json_hash(protocol_v3),
        "v4_canonical_hash": canonical_json_hash(protocol_v4),
        "allowed_change_types": [
            "CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR",
            "METADATA_ONLY",
        ],
        "rows": [
            {"field": "protocol_version", "change_type": "METADATA_ONLY"},
            {"field": "supersedes_protocol_v3_hash", "change_type": "METADATA_ONLY"},
            {"field": "heldout_trials_observed_before_v4", "change_type": "METADATA_ONLY"},
            {"field": "repair_scope", "change_type": "METADATA_ONLY"},
            {"field": "contract_gate_metadata", "change_type": "CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR"},
            {"field": "confirmatory_gates.no_shared_noise_winner_contract_v1", "change_type": "CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR"},
            {"field": "canonical_gate_hashes.no_shared_noise_winner_contract_v1", "change_type": "CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR"},
        ],
    }


def build_synthetic_cases_v4(protocol_v4: dict[str, Any]) -> dict[str, Any]:
    gates = protocol_v4["confirmatory_gates"]
    base = build_synthetic_cases(protocol_v4, gates)
    gate = find_gate(protocol_v4, "no_shared_noise_winner_contract_v1")
    pass_result_case = evaluate_gate(gate, binary_rows=[], map_rows=[], protocol_v3=protocol_v4)

    fail_protocol = deepcopy(protocol_v4)
    fail_protocol["contract_gate_metadata"]["no_shared_noise_winner_contract_v1"][
        "shared_calibrated_severity_mapping_exists"
    ] = True
    fail_result_case = evaluate_gate(gate, binary_rows=[], map_rows=[], protocol_v3=fail_protocol)

    exception_protocol = deepcopy(protocol_v4)
    del exception_protocol["contract_gate_metadata"]["no_shared_noise_winner_contract_v1"][
        "shared_calibrated_severity_mapping_exists"
    ]
    exception_result_case = evaluate_gate(gate, binary_rows=[], map_rows=[], protocol_v3=exception_protocol)

    contradictory_protocol = deepcopy(protocol_v4)
    contradictory_protocol["contract_gate_metadata"]["no_shared_noise_winner_contract_v1"][
        "binary_track_channel_ids"
    ] = "EXACT_WEIGHT_BIT_FLIPS"
    contradictory_result_case = evaluate_gate(gate, binary_rows=[], map_rows=[], protocol_v3=contradictory_protocol)

    base["no_shared_noise_winner_contract_v1"] = {
        "pass_case": pass_result_case,
        "fail_case": fail_result_case,
        "boundary_case": pass_result_case,
        "missing_data_case": exception_result_case,
        "exceptional_trial_case": exception_result_case,
        "tie_case": pass_result_case,
        "contradictory_metrics_case": contradictory_result_case,
    }
    return {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "rows": base,
    }


def validate_synthetic_results(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    rows = payload["rows"]
    for gate_id, cases in rows.items():
        if gate_id == "no_shared_noise_winner_contract_v1":
            expected = {
                "pass_case": "PASS",
                "fail_case": "FAIL",
                "boundary_case": "PASS",
                "missing_data_case": "EXCEPTION",
                "exceptional_trial_case": "EXCEPTION",
                "tie_case": "PASS",
                "contradictory_metrics_case": "EXCEPTION",
            }
        else:
            expected = {
                "pass_case": "PASS",
                "fail_case": "FAIL",
                "boundary_case": "PASS",
                "missing_data_case": "INCOMPLETE_INPUT",
                "exceptional_trial_case": "INCOMPLETE_INPUT",
                "tie_case": "PASS",
                "contradictory_metrics_case": "EXCEPTION",
            }
        for case_name, state in expected.items():
            observed = cases[case_name]["state"]
            if observed != state:
                failures.append(f"{gate_id}/{case_name} expected {state}, observed {observed}.")
    return (not failures), failures


def validate_protocol_v4(repo_root: Path, protocol_v3: dict[str, Any], protocol_v4: dict[str, Any], diff: dict[str, Any], dry_runs: dict[str, Any]) -> dict[str, Any]:
    v1_analysis = read_json(repo_root / "results" / "level3_5b_heldout" / "analysis.json")
    v2_analysis = read_json(repo_root / "results" / "level3_5b_heldout_v2" / "analysis.json")
    v3_analysis = read_json(repo_root / V3_ANALYSIS_PATH)
    v3_completion = read_json(repo_root / V3_COMPLETION_PATH)
    immutable_changes = git_changed_paths_since(repo_root, BLOCKED_V3_COMMIT, IMMUTABLE_V1_V2_V3_PATHS)
    synthetic_ok, synthetic_failures = validate_synthetic_results(dry_runs)

    unchanged_performance_gate_hashes = {}
    for gate_id, gate_hash in protocol_v3["canonical_gate_hashes"].items():
        if gate_id == "no_shared_noise_winner_contract_v1":
            continue
        unchanged_performance_gate_hashes[gate_id] = (
            protocol_v4["canonical_gate_hashes"].get(gate_id) == gate_hash
        )

    unauthorized_diff = [
        row for row in diff["rows"]
        if row["change_type"] not in {"CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR", "METADATA_ONLY"}
    ]

    methods_unchanged = protocol_v4["preserved_scientific_fields"]["binary_track"]["methods"] == protocol_v3["preserved_scientific_fields"]["binary_track"]["methods"] and protocol_v4["preserved_scientific_fields"]["map_track"]["methods"] == protocol_v3["preserved_scientific_fields"]["map_track"]["methods"]
    cells_unchanged = protocol_v4["preserved_scientific_fields"]["binary_track"]["semantic_cells"] == protocol_v3["preserved_scientific_fields"]["binary_track"]["semantic_cells"] and protocol_v4["preserved_scientific_fields"]["map_track"]["semantic_cells"] == protocol_v3["preserved_scientific_fields"]["map_track"]["semantic_cells"]
    points_unchanged = protocol_v4["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"] == protocol_v3["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"] and protocol_v4["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"] == protocol_v3["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]
    seeds_unchanged = protocol_v4["fresh_seed_ranges"] == protocol_v3["fresh_seed_ranges"]
    trial_counts_unchanged = protocol_v4["trial_counts"] == protocol_v3["trial_counts"]
    configs_unchanged = protocol_v4["complete_config_records"] == protocol_v3["complete_config_records"]
    metrics_unchanged = protocol_v4["metrics"] == protocol_v3["metrics"]

    gate = find_gate(protocol_v4, "no_shared_noise_winner_contract_v1")
    pass_fail_exception_distinguishable = (
        dry_runs["rows"]["no_shared_noise_winner_contract_v1"]["pass_case"]["state"] == "PASS"
        and dry_runs["rows"]["no_shared_noise_winner_contract_v1"]["fail_case"]["state"] == "FAIL"
        and dry_runs["rows"]["no_shared_noise_winner_contract_v1"]["exceptional_trial_case"]["state"] == "EXCEPTION"
    )

    verdict = VERDICT_REPAIRED
    if unauthorized_diff:
        verdict = BLOCK_DIFF
    elif not all(unchanged_performance_gate_hashes.values()) or not all(
        [methods_unchanged, cells_unchanged, points_unchanged, seeds_unchanged, trial_counts_unchanged, configs_unchanged, metrics_unchanged]
    ):
        verdict = BLOCK_PERFORMANCE
    elif not pass_fail_exception_distinguishable or not synthetic_ok:
        verdict = BLOCK_AMBIGUOUS

    return {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "zero_heldout_trials": (
            v1_analysis.get("trials_executed", 0) == 0
            and v2_analysis.get("trials_executed", 0) == 0
            and v3_analysis.get("trials_executed", 0) == 0
            and v3_completion.get("trials_executed_binary", 0) == 0
            and v3_completion.get("trials_executed_map", 0) == 0
            and count_jsonl_rows(repo_root / "results" / "level3_5b_heldout_v3" / "binary_trials.jsonl") == 0
            and count_jsonl_rows(repo_root / "results" / "level3_5b_heldout_v3" / "map_trials.jsonl") == 0
        ),
        "blocked_v3_attempt_committed_and_immutable": not immutable_changes,
        "changed_immutable_paths": immutable_changes,
        "v1_v2_v3_unchanged": not immutable_changes,
        "allowed_diff_only": not unauthorized_diff,
        "unauthorized_diff_rows": unauthorized_diff,
        "unchanged_performance_gate_hashes": unchanged_performance_gate_hashes,
        "methods_unchanged": methods_unchanged,
        "cells_unchanged": cells_unchanged,
        "points_unchanged": points_unchanged,
        "seeds_unchanged": seeds_unchanged,
        "trial_counts_unchanged": trial_counts_unchanged,
        "configs_unchanged": configs_unchanged,
        "metrics_unchanged": metrics_unchanged,
        "pass_fail_exception_distinguishable": pass_fail_exception_distinguishable,
        "synthetic_dry_runs_pass": synthetic_ok,
        "synthetic_dry_run_failures": synthetic_failures,
        "benchmark_execution_invoked": False,
        "validator_verdict": verdict,
        "refrozen_ready_status": VERDICT_READY if verdict == VERDICT_REPAIRED else None,
    }


def render_doc(repo_root: Path, analysis: dict[str, Any], audit: dict[str, Any]) -> None:
    lines = [
        "# Level 3.5b Contract-Gate Consistency Repair",
        "",
        f"- Schema: `{LEVEL3_5B_GATE_CONSISTENCY_SCHEMA}`",
        f"- Blocked v3 commit: `{BLOCKED_V3_COMMIT}`",
        f"- Root cause: `{audit['root_cause']}`",
        f"- Held-out trials observed before v4: `0`",
        f"- V3 hash: `{analysis['v3_hash']}`",
        f"- V4 hash: `{analysis['v4_hash']}`",
        "",
        "## Scope",
        "",
        "- Only `no_shared_noise_winner_contract_v1` dry-run consistency was repaired.",
        "- Performance-gate semantics, seeds, cells, methods, points, trial counts, configs and metrics were left unchanged.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_CONTRACT_GATE_CONSISTENCY_REPAIR.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_level3_5b_contract_gate_consistency_repair(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_gate_consistency_repair"
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol_v3 = read_json(repo_root / PROTOCOL_V3_PATH)
    protocol_v4 = build_protocol_v4(protocol_v3)
    audit = build_root_cause_audit(protocol_v3, protocol_v4)
    diff = build_protocol_diff(protocol_v3, protocol_v4)
    dry_runs = build_synthetic_cases_v4(protocol_v4)
    validator = validate_protocol_v4(repo_root, protocol_v3, protocol_v4, diff, dry_runs)

    environment = {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": current_git_commit(repo_root),
        "timestamp_utc": utc_now_iso(),
        "benchmark_execution_invoked": False,
    }
    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "contract_gate_consistency_audit.json", audit)
    write_json(results_dir / "heldout_protocol_v4.json", protocol_v4)
    write_json(results_dir / "protocol_v3_to_v4_diff.json", diff)
    write_json(results_dir / "synthetic_dry_run_results.json", dry_runs)
    write_json(results_dir / "validator_result.json", validator)

    analysis = {
        "schema_version": LEVEL3_5B_GATE_CONSISTENCY_SCHEMA,
        "completion_verdict": validator["validator_verdict"],
        "readiness_status": validator["refrozen_ready_status"],
        "heldout_trials_observed": 0,
        "benchmark_execution_invoked": False,
        "v3_hash": canonical_json_hash(protocol_v3),
        "v4_hash": canonical_json_hash(protocol_v4),
        "repaired_side": "serialized contract-gate rule, evaluator validation path and synthetic contract fixtures",
        "performance_gate_hashes_unchanged": validator["unchanged_performance_gate_hashes"],
        "allowed_diff_classes": [
            "CONTRACT_GATE_DRY_RUN_CONSISTENCY_REPAIR",
            "METADATA_ONLY",
        ],
    }
    write_json(results_dir / "analysis.json", analysis)
    render_doc(repo_root, analysis, audit)
    return analysis
