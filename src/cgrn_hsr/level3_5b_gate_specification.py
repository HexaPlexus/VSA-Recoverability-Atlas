from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_5b_protocol_repair import canonical_json_hash, read_json, sha256_path

LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION = "level3-5b-gate-specification-v1"
LEVEL3_5B_GATE_PROTOCOL_V3 = "level3.5b-heldout-v3"
LEVEL3_5B_GATE_COMPLETION_VERDICT = "GATES_SPECIFIED_AND_FINAL_PROTOCOL_FROZEN"
LEVEL3_5B_GATE_READY_VERDICT = "READY_FOR_LEVEL_3_5B_HELDOUT_V3"
LEVEL3_5B_GATE_BLOCK_OPERATIONALIZATION = "BLOCKED_GATE_CANNOT_BE_OPERATIONALIZED"
LEVEL3_5B_GATE_BLOCK_EVIDENCE = "BLOCKED_DEVELOPMENT_EVIDENCE_INSUFFICIENT"
LEVEL3_5B_GATE_BLOCK_CHANGE = "BLOCKED_BY_UNAUTHORIZED_PROTOCOL_CHANGE"
LEVEL3_5B_GATE_BLOCK_PROVENANCE = "BLOCKED_GATE_PROVENANCE_FAILURE"

PREVIOUS_BLOCKED_CHECKPOINT = "ae27c54"
PROTOCOL_V2_CANONICAL_HASH = "649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf"

DEV_PROTOCOL_PATH = "results/level3_5b_dev/heldout_protocol.json"
DEV_ANALYSIS_PATH = "results/level3_5b_dev/analysis.json"
DEV_BINARY_SUMMARY_PATH = "results/level3_5b_dev/binary_summary.csv"
DEV_MAP_SUMMARY_PATH = "results/level3_5b_dev/map_summary.csv"
DEV_TRANSITION_PATH = "results/level3_5b_dev/transition_regions.json"
DEV_DOC_PATH = "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md"
HELDOUT_PROTOCOL_DOC_PATH = "docs/LEVEL3_5B_HELDOUT_PROTOCOL.md"

V1_BLOCKED_DIR = "results/level3_5b_heldout"
V2_REPAIR_DIR = "results/level3_5b_protocol_repair"
V2_BLOCKED_DIR = "results/level3_5b_heldout_v2"
V1_BLOCKED_DOC = "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md"
V2_REPAIR_DOC = "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md"
V2_BLOCKED_DOC = "docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md"
V2_PROTOCOL_PATH = "results/level3_5b_protocol_repair/heldout_protocol_v2.json"
V2_ANALYSIS_PATH = "results/level3_5b_heldout_v2/analysis.json"
V2_COMPLETION_PATH = "results/level3_5b_heldout_v2/completion_manifest.json"
REPAIR_ANALYSIS_PATH = "results/level3_5b_protocol_repair/analysis.json"
REPAIR_VALIDATOR_PATH = "results/level3_5b_protocol_repair/validator_result.json"
SEED_AUDIT_PATH = "results/level3_5b_protocol_repair/seed_audit.json"

ALLOWED_DIFF_TYPES = {
    "CONFIRMATORY_GATE_SEMANTICS_ADDED",
    "STATISTICAL_POLICY_ADDED",
    "MISSING_OUTCOME_POLICY_ADDED",
    "METADATA_ONLY",
}

SOURCE_CLASS_EXPLICIT = "EXPLICIT_PREEXISTING_RULE"
SOURCE_CLASS_PARTIAL = "PARTIAL_PREEXISTING_RULE"
SOURCE_CLASS_LABEL = "LABEL_ONLY"
RULE_ORIGIN_NEW = "NEW_PROSPECTIVE_RULE_DEFINED_FROM_DEVELOPMENT_ONLY"
RULE_ORIGIN_RECOVERED = "RECOVERED_PREHELDOUT_RULE"

BCF_BLOCKED = "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"
NO_SHARED_NOISE_WINNER_NOT_CONFIRMED = "NO_SHARED_NOISE_WINNER_NOT_CONFIRMED"

IMMUTABLE_PREVIOUS_EVIDENCE_PATHS = (
    V1_BLOCKED_DIR,
    V2_REPAIR_DIR,
    V2_BLOCKED_DIR,
    V1_BLOCKED_DOC,
    V2_REPAIR_DOC,
    V2_BLOCKED_DOC,
)


@dataclass(frozen=True)
class SummaryRow:
    track_id: str
    method_id: str
    cell_id: str
    channel_id: str
    corruption_label: str
    trials: int
    exact_recovery_rate: float
    full_wrong_rate: float
    silent_wrong_rate: float
    detected_failure_rate: float
    partial_factor_recovery_rate: float
    mean_correct_factors: float
    conditional_wrong_given_nonfailure: float
    extra: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_csv_rows(path: Path) -> list[SummaryRow]:
    rows: list[SummaryRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            extra = {
                key: value
                for key, value in raw.items()
                if key
                not in {
                    "schema_version",
                    "track_id",
                    "method_id",
                    "cell_id",
                    "channel_id",
                    "corruption_label",
                    "trials",
                    "exact_recovery_rate",
                    "full_wrong_rate",
                    "silent_wrong_rate",
                    "detected_failure_rate",
                    "partial_factor_recovery_rate",
                    "mean_correct_factors",
                    "conditional_wrong_given_nonfailure",
                }
            }
            rows.append(
                SummaryRow(
                    track_id=raw["track_id"],
                    method_id=raw["method_id"],
                    cell_id=raw["cell_id"],
                    channel_id=raw["channel_id"],
                    corruption_label=raw["corruption_label"],
                    trials=int(raw["trials"]),
                    exact_recovery_rate=float(raw["exact_recovery_rate"]),
                    full_wrong_rate=float(raw["full_wrong_rate"]),
                    silent_wrong_rate=float(raw["silent_wrong_rate"]),
                    detected_failure_rate=float(raw["detected_failure_rate"]),
                    partial_factor_recovery_rate=float(raw["partial_factor_recovery_rate"]),
                    mean_correct_factors=float(raw["mean_correct_factors"]),
                    conditional_wrong_given_nonfailure=float(raw["conditional_wrong_given_nonfailure"]),
                    extra=extra,
                )
            )
    return rows


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


def unchanged_since_checkpoint(repo_root: Path, paths: tuple[str, ...]) -> tuple[bool, list[str]]:
    _, stdout, _ = git_stdout(repo_root, "diff", "--name-only", PREVIOUS_BLOCKED_CHECKPOINT, "HEAD", "--", *paths)
    changed = [line for line in stdout.splitlines() if line]
    return not changed, changed


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def row_key(row: SummaryRow) -> tuple[str, str, str, str, str]:
    return (row.track_id, row.method_id, row.cell_id, row.channel_id, row.corruption_label)


def build_row_lookup(rows: list[SummaryRow]) -> dict[tuple[str, str, str, str, str], SummaryRow]:
    return {row_key(row): row for row in rows}


def parse_numeric_label(label: str) -> float:
    return float(label.split("=", 1)[1])


def sorted_points(labels: list[str]) -> list[str]:
    return sorted(labels, key=parse_numeric_label)


def complete_gate_hash(gate: dict[str, Any]) -> str:
    payload = deepcopy(gate)
    payload.pop("rule_hash", None)
    return canonical_json_hash(payload)


def validate_rate(name: str, value: float) -> str | None:
    if value < -1e-9 or value > 1.0 + 1e-9:
        return f"{name}={value} is outside [0,1]"
    return None


def validate_summary_row(row: SummaryRow) -> list[str]:
    errors = []
    for key, value in (
        ("exact_recovery_rate", row.exact_recovery_rate),
        ("full_wrong_rate", row.full_wrong_rate),
        ("silent_wrong_rate", row.silent_wrong_rate),
        ("detected_failure_rate", row.detected_failure_rate),
        ("partial_factor_recovery_rate", row.partial_factor_recovery_rate),
        ("conditional_wrong_given_nonfailure", row.conditional_wrong_given_nonfailure),
    ):
        maybe = validate_rate(key, value)
        if maybe:
            errors.append(maybe)
    return errors


def get_row(
    lookup: dict[tuple[str, str, str, str, str], SummaryRow],
    *,
    track_id: str,
    method_id: str,
    cell_id: str,
    channel_id: str,
    corruption_label: str,
) -> SummaryRow | None:
    return lookup.get((track_id, method_id, cell_id, channel_id, corruption_label))


def gate_source_audit_records() -> list[dict[str, Any]]:
    return [
        {
            "disposition": "BCH_DOMINATES_BINARY_EXACT_RECORD_CONFIRMED",
            "explicit_rule_found": True,
            "source_files": [
                DEV_ANALYSIS_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
                DEV_DOC_PATH,
            ],
            "source_locations": [
                "results/level3_5b_dev/analysis.json:12",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1515",
                "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md:5",
            ],
            "original_rule_text": 'binary_verdict = "BCH_DOMINATES_BINARY_EXACT_RECORD_DEV" if has_method(binary_summary, "packed_tuple_bch_high_redundancy") else "BLOCK_BINARY_TRACK"',
            "executable_semantics_complete": False,
            "missing_fields": [
                "comparators",
                "cells",
                "corruption points",
                "dominance operator",
                "silent-wrong ceiling",
                "miscorrection handling",
                "tie policy",
            ],
            "source_class": SOURCE_CLASS_PARTIAL,
        },
        {
            "disposition": "BCH_DOMINANCE_NOT_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [V2_PROTOCOL_PATH],
            "source_locations": ["results/level3_5b_protocol_repair/heldout_protocol_v2.json:261-272"],
            "original_rule_text": "Disposition label present without executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": ["full pass/fail rule"],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "RAW_NECO_NOISE_GAP_CONFIRMED",
            "explicit_rule_found": True,
            "source_files": [
                DEV_ANALYSIS_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
            ],
            "source_locations": [
                "results/level3_5b_dev/analysis.json:67",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1516-1519,1538",
            ],
            "original_rule_text": 'raw_neco_gap = any(row["method_id"] == "raw_neco_algebraic_recovery" and (row["silent_wrong_rate"] > 0.0 or row["detected_failure_rate"] > 0.0) for row in binary_summary)',
            "executable_semantics_complete": False,
            "missing_fields": [
                "which cells",
                "which corruption points",
                "comparison against clean baseline",
                "quantitative threshold",
            ],
            "source_class": SOURCE_CLASS_PARTIAL,
        },
        {
            "disposition": "RAW_NECO_NOISE_GAP_NOT_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [V2_PROTOCOL_PATH],
            "source_locations": ["results/level3_5b_protocol_repair/heldout_protocol_v2.json:261-272"],
            "original_rule_text": "Disposition label present without executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": ["full pass/fail rule"],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "GENERIC_LINEAR_NOISE_EQUIVALENCE_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [
                DEV_ANALYSIS_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
            ],
            "source_locations": [
                "results/level3_5b_dev/analysis.json:60",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1539",
            ],
            "original_rule_text": '"generic_linear_noise_equivalence_verdict": "GENERIC_LINEAR_NOISE_EQUIVALENCE_DEV"',
            "executable_semantics_complete": False,
            "missing_fields": [
                "comparator",
                "equivalence interpretation",
                "margin",
                "cells",
                "corruption points",
            ],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "GENERIC_LINEAR_NOISE_EQUIVALENCE_NOT_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [V2_PROTOCOL_PATH],
            "source_locations": ["results/level3_5b_protocol_repair/heldout_protocol_v2.json:261-272"],
            "original_rule_text": "Disposition label present without executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": ["full pass/fail rule"],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "MAP_SILENT_COLLAPSE_CONFIRMED",
            "explicit_rule_found": True,
            "source_files": [
                DEV_ANALYSIS_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
                DEV_DOC_PATH,
            ],
            "source_locations": [
                "results/level3_5b_dev/analysis.json:63",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1521-1525",
                "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md:6",
            ],
            "original_rule_text": 'map_verdict = "MAP_GRACEFUL_REGION_DEV" if map_graceful else "MAP_SILENT_COLLAPSE_DEV"',
            "executable_semantics_complete": False,
            "missing_fields": [
                "direct collapse criterion",
                "cells",
                "points",
                "silent threshold",
                "detected-failure criterion",
            ],
            "source_class": SOURCE_CLASS_PARTIAL,
        },
        {
            "disposition": "MAP_SILENT_COLLAPSE_NOT_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [V2_PROTOCOL_PATH],
            "source_locations": ["results/level3_5b_protocol_repair/heldout_protocol_v2.json:261-272"],
            "original_rule_text": "Disposition label present without executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": ["full pass/fail rule"],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "MAP_GRACEFUL_REGION_CONFIRMED",
            "explicit_rule_found": True,
            "source_files": [
                DEV_ANALYSIS_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
            ],
            "source_locations": [
                "results/level3_5b_dev/analysis.json:63",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1521-1525",
            ],
            "original_rule_text": 'map_graceful = any(row["method_id"] == MAP_EXTENDED_ARM_ID and row["exact_recovery_rate"] < 0.90 and row["exact_recovery_rate"] > 0.10 and row["silent_wrong_rate"] <= 0.25 for row in map_summary)',
            "executable_semantics_complete": False,
            "missing_fields": [
                "which arm(s)",
                "which cells",
                "which corruption points",
                "partial-recovery interpretation",
                "region definition",
            ],
            "source_class": SOURCE_CLASS_PARTIAL,
        },
        {
            "disposition": "MAP_GRACEFUL_REGION_NOT_CONFIRMED",
            "explicit_rule_found": False,
            "source_files": [V2_PROTOCOL_PATH],
            "source_locations": ["results/level3_5b_protocol_repair/heldout_protocol_v2.json:261-272"],
            "original_rule_text": "Disposition label present without executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": ["full pass/fail rule"],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": "NO_SHARED_NOISE_WINNER",
            "explicit_rule_found": True,
            "source_files": [
                DEV_PROTOCOL_PATH,
                DEV_DOC_PATH,
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
            ],
            "source_locations": [
                "results/level3_5b_dev/heldout_protocol.json:156-157",
                "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md:24",
                "src/cgrn_hsr/level3_5b_native_noise_frontiers.py:1136,1215",
            ],
            "original_rule_text": 'claim_limits include "No cross-track universal winner" and guardrail text states that equal corruption percentages across incompatible channels are not interpreted as equal semantic damage.',
            "executable_semantics_complete": False,
            "missing_fields": ["machine-readable compatibility predicate"],
            "source_class": SOURCE_CLASS_PARTIAL,
        },
        {
            "disposition": NO_SHARED_NOISE_WINNER_NOT_CONFIRMED,
            "explicit_rule_found": False,
            "source_files": [],
            "source_locations": [],
            "original_rule_text": "Fail complement added in v3 for complete executable pass/fail semantics.",
            "executable_semantics_complete": False,
            "missing_fields": [],
            "source_class": SOURCE_CLASS_LABEL,
        },
        {
            "disposition": BCF_BLOCKED,
            "explicit_rule_found": True,
            "source_files": [
                DEV_PROTOCOL_PATH,
                DEV_DOC_PATH,
            ],
            "source_locations": [
                "results/level3_5b_dev/heldout_protocol.json:2-18",
                "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md:20",
            ],
            "original_rule_text": "BCF track blocked because no lawful external corruption contract was frozen.",
            "executable_semantics_complete": True,
            "missing_fields": [],
            "source_class": SOURCE_CLASS_EXPLICIT,
        },
    ]


def build_global_statistical_policy() -> dict[str, Any]:
    return {
        "point_estimates": "observed summary rates from frozen held-out summaries",
        "confidence_intervals": {
            "enabled": True,
            "method": "Wilson 95%",
            "used_for_verdicts": False,
            "purpose": "descriptive reporting only",
        },
        "paired_structure": "not used; confirmatory rules operate on per-method frozen summary rows",
        "hypothesis_tests": {
            "enabled": False,
            "alpha": None,
            "multiple_comparison_correction": None,
        },
        "minimum_sample_validity": {
            "binary_track": 64,
            "map_track": 64,
        },
        "zero_count_policy": "rate comparisons use observed 0.0 directly; no continuity correction in pass/fail logic",
        "missing_outcome_policy": "missing required summary row or trials < minimum sample validity => INCOMPLETE_INPUT and no substantive disposition",
        "exceptional_trial_policy": "typed exceptional outcomes remain in observed summary; if summary integrity is broken, gate returns INCOMPLETE_INPUT",
        "deterministic_threshold_decision": True,
        "raw_p_cross_track_policy": "forbidden; incompatible channel severities are not ranked on equal raw p",
    }


def build_confirmatory_gates(protocol_v2: dict[str, Any]) -> list[dict[str, Any]]:
    binary_points = protocol_v2["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"]
    map_points = protocol_v2["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]

    first_nonzero_binary = {
        cell_id: sorted_points([label for label in labels if label != "e=0"])[0]
        for cell_id, labels in binary_points.items()
    }
    bch_nonzero_points = {
        cell_id: [label for label in sorted_points(labels) if label != "e=0"]
        for cell_id, labels in binary_points.items()
    }
    map_graceful_points = {
        "u1_f3_m31": ["p=0.0", "p=0.01", "p=0.02", "p=0.05"],
    }

    gates = [
        {
            "id": "bch_binary_exact_record_dominance_v1",
            "disposition_if_pass": "BCH_DOMINATES_BINARY_EXACT_RECORD_CONFIRMED",
            "disposition_if_fail": "BCH_DOMINANCE_NOT_CONFIRMED",
            "scientific_question": "Does frozen high-redundancy BCH remain the preferred exact-record binary control on the frozen exact-weight U1 cells and points?",
            "source_class": SOURCE_CLASS_PARTIAL,
            "source_provenance": {
                "audit_disposition": "BCH_DOMINATES_BINARY_EXACT_RECORD_CONFIRMED",
                "rule_origin": RULE_ORIGIN_NEW,
                "development_sources": [
                    DEV_BINARY_SUMMARY_PATH,
                    DEV_PROTOCOL_PATH,
                ],
            },
            "methods": {
                "candidate": "packed_tuple_bch_high_redundancy",
                "comparators": [
                    "uncoded_packed_tuple",
                    "packed_tuple_bch_low_redundancy",
                    "generic_full_rank_linear_mix",
                    "raw_neco_algebraic_recovery",
                ],
            },
            "semantic_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "corruption_points": {
                "channel_id": "EXACT_WEIGHT_BIT_FLIPS",
                "required_points": bch_nonzero_points,
            },
            "included_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "detected_failure_rate",
                "miscorrection_rate",
            ],
            "excluded_metrics": [
                "latency",
                "resource bytes",
                "bernoulli points",
            ],
            "aggregation_unit": "summary row (method x cell x channel x corruption point)",
            "comparison_operator": "candidate exact must be >= every comparator exact on every required row; ties allowed",
            "thresholds": {
                "silent_wrong_rate_max": 0.125,
                "miscorrection_rate_max": 0.375,
                "per_row_exact_margin_min": 0.0,
            },
            "required_points": bch_nonzero_points,
            "required_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "missing_trial_policy": "INCOMPLETE_INPUT",
            "exceptional_trial_policy": "INCOMPLETE_INPUT if any required summary row is absent or has trials != 64",
            "tie_policy": "ties on exact_recovery_rate are allowed; candidate still must satisfy silent and miscorrection ceilings",
            "multiplicity_policy": "none; all rows are fixed ex ante and evaluated conjunctively",
            "confidence_interval_policy": "Wilson 95% reported descriptively only; not used in pass/fail",
            "minimum_effect_requirement": {
                "per_cell_required": True,
                "target_methods": [
                    "uncoded_packed_tuple",
                    "generic_full_rank_linear_mix",
                    "raw_neco_algebraic_recovery",
                ],
                "minimum_exact_advantage": 0.50,
                "description": "At least one nonzero required point per cell must show >=0.50 exact-rate advantage over the strongest non-BCH comparator.",
            },
            "silent_error_constraint": {
                "metric": "silent_wrong_rate",
                "operator": "<=",
                "value": 0.125,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "descriptive only",
            },
            "deterministic_evaluation_order": [
                "u1_f3_m10:e=1,e=2,e=3,e=4,e=6",
                "u1_f3_m31:e=1,e=2,e=3,e=4,e=6",
                "u1_f3_m68:e=2,e=3,e=4,e=5,e=8",
            ],
            "rule_version": "v1",
        },
        {
            "id": "raw_neco_noise_gap_v1",
            "disposition_if_pass": "RAW_NECO_NOISE_GAP_CONFIRMED",
            "disposition_if_fail": "RAW_NECO_NOISE_GAP_NOT_CONFIRMED",
            "scientific_question": "Does raw NeCo clean algebraic recovery lose exact noisy decoding immediately after the first nonzero exact-weight corruption point?",
            "source_class": SOURCE_CLASS_PARTIAL,
            "source_provenance": {
                "audit_disposition": "RAW_NECO_NOISE_GAP_CONFIRMED",
                "rule_origin": RULE_ORIGIN_NEW,
                "development_sources": [DEV_BINARY_SUMMARY_PATH],
            },
            "methods": {
                "candidate": "raw_neco_algebraic_recovery",
            },
            "semantic_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "corruption_points": {
                "channel_id": "EXACT_WEIGHT_BIT_FLIPS",
                "clean_point": {"u1_f3_m10": "e=0", "u1_f3_m31": "e=0", "u1_f3_m68": "e=0"},
                "required_points": first_nonzero_binary,
            },
            "included_metrics": [
                "exact_recovery_rate",
                "detected_failure_rate",
                "silent_wrong_rate",
            ],
            "excluded_metrics": [
                "latency",
                "bernoulli points",
                "cross-method ranking",
            ],
            "aggregation_unit": "summary row per cell at clean and first nonzero exact-weight point",
            "comparison_operator": "all required cells must satisfy clean exact threshold and first-nonzero failure thresholds",
            "thresholds": {
                "clean_exact_min": 0.95,
                "clean_silent_wrong_max": 0.05,
                "nonzero_exact_max": 0.10,
                "nonzero_detected_failure_min": 0.90,
            },
            "required_points": {
                "clean": {"u1_f3_m10": "e=0", "u1_f3_m31": "e=0", "u1_f3_m68": "e=0"},
                "nonzero": first_nonzero_binary,
            },
            "required_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "missing_trial_policy": "INCOMPLETE_INPUT",
            "exceptional_trial_policy": "INCOMPLETE_INPUT if any required row is absent or has trials != 64",
            "tie_policy": "not applicable",
            "multiplicity_policy": "none; all required cells must satisfy the same thresholds",
            "confidence_interval_policy": "Wilson 95% descriptive only",
            "minimum_effect_requirement": {
                "description": "Immediate post-clean degradation is required at the first nonzero exact-weight point in every cell.",
            },
            "silent_error_constraint": {
                "metric": "clean silent_wrong_rate",
                "operator": "<=",
                "value": 0.05,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "descriptive only",
            },
            "deterministic_evaluation_order": [
                "u1_f3_m10:e=0 then e=1",
                "u1_f3_m31:e=0 then e=1",
                "u1_f3_m68:e=0 then e=2",
            ],
            "rule_version": "v1",
        },
        {
            "id": "generic_linear_practical_equivalence_v1",
            "disposition_if_pass": "GENERIC_LINEAR_NOISE_EQUIVALENCE_CONFIRMED",
            "disposition_if_fail": "GENERIC_LINEAR_NOISE_EQUIVALENCE_NOT_CONFIRMED",
            "scientific_question": "Is no material separation detected between raw NeCo and the same-length generic full-rank linear control on the frozen exact-weight binary points?",
            "source_class": SOURCE_CLASS_LABEL,
            "source_provenance": {
                "audit_disposition": "GENERIC_LINEAR_NOISE_EQUIVALENCE_CONFIRMED",
                "rule_origin": RULE_ORIGIN_NEW,
                "development_sources": [DEV_BINARY_SUMMARY_PATH],
                "interpretation_mode": "PRACTICAL_EQUIVALENCE_WITH_MARGIN",
            },
            "methods": {
                "candidate": "raw_neco_algebraic_recovery",
                "comparator": "generic_full_rank_linear_mix",
            },
            "semantic_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "corruption_points": {
                "channel_id": "EXACT_WEIGHT_BIT_FLIPS",
                "required_points": binary_points,
            },
            "included_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "detected_failure_rate",
            ],
            "excluded_metrics": [
                "latency",
                "resource bytes",
                "bernoulli points",
            ],
            "aggregation_unit": "summary row pair (raw NeCo vs generic linear) at each frozen exact-weight point",
            "comparison_operator": "maximum absolute metric difference across required rows must stay within frozen practical margins",
            "thresholds": {
                "exact_recovery_rate_abs_margin_max": 0.10,
                "silent_wrong_rate_abs_margin_max": 0.05,
                "detected_failure_rate_abs_margin_max": 0.10,
            },
            "required_points": binary_points,
            "required_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
            "missing_trial_policy": "INCOMPLETE_INPUT",
            "exceptional_trial_policy": "INCOMPLETE_INPUT if any paired row is absent or has trials != 64",
            "tie_policy": "exact equality is allowed and sufficient",
            "multiplicity_policy": "none; all paired rows must satisfy the same margins",
            "confidence_interval_policy": "Wilson 95% descriptive only; no formal statistical equivalence claim",
            "minimum_effect_requirement": {
                "description": "No row may exceed the practical separation margins.",
            },
            "silent_error_constraint": {
                "metric": "absolute silent_wrong_rate difference",
                "operator": "<=",
                "value": 0.05,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "descriptive only",
            },
            "deterministic_evaluation_order": [
                "u1_f3_m10:e=0,e=1,e=2,e=3,e=4,e=6",
                "u1_f3_m31:e=0,e=1,e=2,e=3,e=4,e=6",
                "u1_f3_m68:e=0,e=2,e=3,e=4,e=5,e=8",
            ],
            "rule_version": "v1",
        },
        {
            "id": "map_silent_collapse_v1",
            "disposition_if_pass": "MAP_SILENT_COLLAPSE_CONFIRMED",
            "disposition_if_fail": "MAP_SILENT_COLLAPSE_NOT_CONFIRMED",
            "scientific_question": "In the frozen high-capacity MAP cell, do both frozen MAP arms continue returning full tuples after semantic correctness has collapsed, without detected failure?",
            "source_class": SOURCE_CLASS_PARTIAL,
            "source_provenance": {
                "audit_disposition": "MAP_SILENT_COLLAPSE_CONFIRMED",
                "rule_origin": RULE_ORIGIN_NEW,
                "development_sources": [DEV_MAP_SUMMARY_PATH],
            },
            "methods": {
                "candidates": [
                    "map_d1024",
                    "map_d1024_step32_r4_best_native_reconstruction",
                ],
            },
            "semantic_cells": ["u1_f3_m68"],
            "corruption_points": {
                "channel_id": "MAP_SIGN_FLIP",
                "required_points": {"u1_f3_m68": map_points["u1_f3_m68"]},
            },
            "included_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "detected_failure_rate",
            ],
            "excluded_metrics": [
                "native reconstruction score as abstention surrogate",
                "latency",
            ],
            "aggregation_unit": "summary row per MAP arm and frozen point in u1_f3_m68",
            "comparison_operator": "all required rows must satisfy collapse thresholds",
            "thresholds": {
                "exact_recovery_rate_max": 0.10,
                "silent_wrong_rate_min": 0.90,
                "detected_failure_rate_max": 0.05,
            },
            "required_points": {"u1_f3_m68": map_points["u1_f3_m68"]},
            "required_cells": ["u1_f3_m68"],
            "missing_trial_policy": "INCOMPLETE_INPUT",
            "exceptional_trial_policy": "INCOMPLETE_INPUT if any required row is absent or has trials != 64",
            "tie_policy": "not applicable",
            "multiplicity_policy": "none; both frozen arms and all frozen points must satisfy the same thresholds",
            "confidence_interval_policy": "Wilson 95% descriptive only",
            "minimum_effect_requirement": {
                "description": "Collapse must persist throughout the entire frozen u1_f3_m68 point set for both arms.",
            },
            "silent_error_constraint": {
                "metric": "silent_wrong_rate",
                "operator": ">=",
                "value": 0.90,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "descriptive only",
            },
            "deterministic_evaluation_order": [
                "map_d1024:u1_f3_m68:p=0.0,p=0.01,p=0.02,p=0.05,p=0.1",
                "map_d1024_step32_r4_best_native_reconstruction:u1_f3_m68:p=0.0,p=0.01,p=0.02,p=0.05,p=0.1",
            ],
            "rule_version": "v1",
        },
        {
            "id": "map_graceful_region_v1",
            "disposition_if_pass": "MAP_GRACEFUL_REGION_CONFIRMED",
            "disposition_if_fail": "MAP_GRACEFUL_REGION_NOT_CONFIRMED",
            "scientific_question": "Does the extended frozen MAP arm retain an intermediate exact/partial region with bounded silent-wrong behavior on the selected frozen u1_f3_m31 points?",
            "source_class": SOURCE_CLASS_PARTIAL,
            "source_provenance": {
                "audit_disposition": "MAP_GRACEFUL_REGION_CONFIRMED",
                "rule_origin": RULE_ORIGIN_NEW,
                "development_sources": [DEV_MAP_SUMMARY_PATH],
            },
            "methods": {
                "candidate": "map_d1024_step32_r4_best_native_reconstruction",
            },
            "semantic_cells": ["u1_f3_m31"],
            "corruption_points": {
                "channel_id": "MAP_SIGN_FLIP",
                "required_points": map_graceful_points,
            },
            "included_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "mean_correct_factors",
            ],
            "excluded_metrics": [
                "detected_failure_rate as primary",
                "latency",
            ],
            "aggregation_unit": "summary row per selected graceful-region point",
            "comparison_operator": "all selected points must satisfy the same region thresholds",
            "thresholds": {
                "exact_recovery_rate_min": 0.25,
                "exact_recovery_rate_max": 0.75,
                "silent_wrong_rate_max": 0.50,
                "mean_correct_factors_min": 1.50,
            },
            "required_points": map_graceful_points,
            "required_cells": ["u1_f3_m31"],
            "missing_trial_policy": "INCOMPLETE_INPUT",
            "exceptional_trial_policy": "INCOMPLETE_INPUT if any required row is absent or has trials != 64",
            "tie_policy": "threshold equality counts as pass",
            "multiplicity_policy": "none; all selected points are fixed ex ante and evaluated conjunctively",
            "confidence_interval_policy": "Wilson 95% descriptive only",
            "minimum_effect_requirement": {
                "description": "The selected region must maintain intermediate exact recovery and bounded silent-wrong on every required point.",
            },
            "silent_error_constraint": {
                "metric": "silent_wrong_rate",
                "operator": "<=",
                "value": 0.50,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "descriptive only",
            },
            "deterministic_evaluation_order": [
                "map_d1024_step32_r4_best_native_reconstruction:u1_f3_m31:p=0.0,p=0.01,p=0.02,p=0.05",
            ],
            "rule_version": "v1",
        },
        {
            "id": "no_shared_noise_winner_contract_v1",
            "disposition_if_pass": "NO_SHARED_NOISE_WINNER",
            "disposition_if_fail": NO_SHARED_NOISE_WINNER_NOT_CONFIRMED,
            "scientific_question": "Does the frozen protocol still forbid a shared cross-track noise winner because the binary and MAP tracks use incompatible native corruption channels with no calibrated common severity mapping?",
            "source_class": SOURCE_CLASS_PARTIAL,
            "source_provenance": {
                "audit_disposition": "NO_SHARED_NOISE_WINNER",
                "rule_origin": RULE_ORIGIN_RECOVERED,
                "development_sources": [
                    DEV_PROTOCOL_PATH,
                    DEV_DOC_PATH,
                ],
            },
            "methods": {
                "binary_track_methods": protocol_v2["preserved_scientific_fields"]["binary_track"]["methods"],
                "map_track_methods": protocol_v2["preserved_scientific_fields"]["map_track"]["methods"],
            },
            "semantic_cells": [],
            "corruption_points": {
                "track_compatibility_only": True,
            },
            "included_metrics": [],
            "excluded_metrics": [
                "all held-out outcome metrics",
            ],
            "aggregation_unit": "protocol contract only",
            "comparison_operator": "binary and MAP channel sets must differ and claim limits must forbid cross-track winner claims",
            "thresholds": {
                "requires_distinct_channel_sets": True,
                "requires_cross_track_claim_forbidden": True,
            },
            "required_points": {},
            "required_cells": [],
            "missing_trial_policy": "not applicable",
            "exceptional_trial_policy": "not applicable",
            "tie_policy": "not applicable",
            "multiplicity_policy": "not applicable",
            "confidence_interval_policy": "not applicable",
            "minimum_effect_requirement": {
                "description": "No common calibrated severity mapping may be available across binary exact-weight and MAP sign-flip channels.",
            },
            "silent_error_constraint": {
                "metric": None,
                "operator": None,
                "value": None,
            },
            "resource_constraint": {
                "primary_confirmatory_role": False,
                "policy": "not applicable",
            },
            "deterministic_evaluation_order": [
                "protocol binary channels",
                "protocol map channels",
                "protocol claim limits",
            ],
            "rule_version": "v1",
        },
    ]
    for gate in gates:
        gate["rule_hash"] = complete_gate_hash(gate)
    return gates


def rows_to_index(rows: list[SummaryRow]) -> dict[tuple[str, str, str, str, str], SummaryRow]:
    return build_row_lookup(rows)


def incomplete_result(gate: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "gate_id": gate["id"],
        "state": "INCOMPLETE_INPUT",
        "disposition": None,
        "reasons": reasons,
    }


def fail_result(gate: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "gate_id": gate["id"],
        "state": "FAIL",
        "disposition": gate["disposition_if_fail"],
        "reasons": reasons,
    }


def pass_result(gate: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "gate_id": gate["id"],
        "state": "PASS",
        "disposition": gate["disposition_if_pass"],
        "reasons": reasons,
    }


def exception_result(gate: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "gate_id": gate["id"],
        "state": "EXCEPTION",
        "disposition": None,
        "reasons": reasons,
    }


def evaluate_bch_gate(gate: dict[str, Any], binary_lookup: dict[tuple[str, str, str, str, str], SummaryRow]) -> dict[str, Any]:
    reasons: list[str] = []
    candidate = gate["methods"]["candidate"]
    comparators = gate["methods"]["comparators"]
    channel = gate["corruption_points"]["channel_id"]
    effect_per_cell: dict[str, bool] = {}
    for cell_id, labels in gate["required_points"].items():
        effect_per_cell[cell_id] = False
        for label in labels:
            candidate_row = get_row(
                binary_lookup,
                track_id="binary_exact_record",
                method_id=candidate,
                cell_id=cell_id,
                channel_id=channel,
                corruption_label=label,
            )
            if candidate_row is None:
                return incomplete_result(gate, [f"Missing candidate row for {cell_id}/{label}."])
            if candidate_row.trials != 64:
                return incomplete_result(gate, [f"Candidate row for {cell_id}/{label} has trials={candidate_row.trials}, expected 64."])
            row_errors = validate_summary_row(candidate_row)
            if row_errors:
                return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": row_errors}
            if candidate_row.silent_wrong_rate > gate["thresholds"]["silent_wrong_rate_max"]:
                reasons.append(f"{cell_id}/{label} silent_wrong_rate={candidate_row.silent_wrong_rate} exceeds ceiling.")
            miscorrection_rate = float(candidate_row.extra.get("miscorrection_rate") or 0.0)
            if miscorrection_rate > gate["thresholds"]["miscorrection_rate_max"]:
                reasons.append(f"{cell_id}/{label} miscorrection_rate={miscorrection_rate} exceeds ceiling.")
            best_non_bch_exact = 0.0
            for comparator in comparators:
                comp_row = get_row(
                    binary_lookup,
                    track_id="binary_exact_record",
                    method_id=comparator,
                    cell_id=cell_id,
                    channel_id=channel,
                    corruption_label=label,
                )
                if comp_row is None:
                    return incomplete_result(gate, [f"Missing comparator row for {comparator} {cell_id}/{label}."])
                if comp_row.trials != 64:
                    return incomplete_result(gate, [f"Comparator row {comparator} {cell_id}/{label} has trials={comp_row.trials}, expected 64."])
                comp_errors = validate_summary_row(comp_row)
                if comp_errors:
                    return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": comp_errors}
                if candidate_row.exact_recovery_rate < comp_row.exact_recovery_rate:
                    reasons.append(
                        f"{cell_id}/{label} candidate exact {candidate_row.exact_recovery_rate} is below comparator {comparator} exact {comp_row.exact_recovery_rate}."
                    )
                if comparator in gate["minimum_effect_requirement"]["target_methods"]:
                    best_non_bch_exact = max(best_non_bch_exact, comp_row.exact_recovery_rate)
            if candidate_row.exact_recovery_rate - best_non_bch_exact >= gate["minimum_effect_requirement"]["minimum_exact_advantage"]:
                effect_per_cell[cell_id] = True
    for cell_id, has_effect in effect_per_cell.items():
        if not has_effect:
            reasons.append(f"{cell_id} lacks the minimum exact-rate advantage over the strongest non-BCH comparator.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["All required rows satisfied BCH dominance semantics."])


def evaluate_raw_neco_gap_gate(gate: dict[str, Any], binary_lookup: dict[tuple[str, str, str, str, str], SummaryRow]) -> dict[str, Any]:
    reasons: list[str] = []
    method_id = gate["methods"]["candidate"]
    channel = gate["corruption_points"]["channel_id"]
    for cell_id in gate["required_cells"]:
        clean_label = gate["required_points"]["clean"][cell_id]
        nonzero_label = gate["required_points"]["nonzero"][cell_id]
        clean_row = get_row(binary_lookup, track_id="binary_exact_record", method_id=method_id, cell_id=cell_id, channel_id=channel, corruption_label=clean_label)
        nonzero_row = get_row(binary_lookup, track_id="binary_exact_record", method_id=method_id, cell_id=cell_id, channel_id=channel, corruption_label=nonzero_label)
        if clean_row is None or nonzero_row is None:
            return incomplete_result(gate, [f"Missing raw NeCo row(s) for {cell_id}."])
        if clean_row.trials != 64 or nonzero_row.trials != 64:
            return incomplete_result(gate, [f"Unexpected trial count for {cell_id}."])
        for row in (clean_row, nonzero_row):
            errs = validate_summary_row(row)
            if errs:
                return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": errs}
        if clean_row.exact_recovery_rate < gate["thresholds"]["clean_exact_min"]:
            reasons.append(f"{cell_id} clean exact {clean_row.exact_recovery_rate} below minimum.")
        if clean_row.silent_wrong_rate > gate["thresholds"]["clean_silent_wrong_max"]:
            reasons.append(f"{cell_id} clean silent {clean_row.silent_wrong_rate} above maximum.")
        if nonzero_row.exact_recovery_rate > gate["thresholds"]["nonzero_exact_max"]:
            reasons.append(f"{cell_id} first nonzero exact {nonzero_row.exact_recovery_rate} above maximum.")
        if nonzero_row.detected_failure_rate < gate["thresholds"]["nonzero_detected_failure_min"]:
            reasons.append(f"{cell_id} first nonzero detected_failure {nonzero_row.detected_failure_rate} below minimum.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["Raw NeCo clean-to-noisy gap satisfied in every required cell."])


def evaluate_generic_equivalence_gate(gate: dict[str, Any], binary_lookup: dict[tuple[str, str, str, str, str], SummaryRow]) -> dict[str, Any]:
    reasons: list[str] = []
    candidate = gate["methods"]["candidate"]
    comparator = gate["methods"]["comparator"]
    channel = gate["corruption_points"]["channel_id"]
    for cell_id, labels in gate["required_points"].items():
        for label in labels:
            cand = get_row(binary_lookup, track_id="binary_exact_record", method_id=candidate, cell_id=cell_id, channel_id=channel, corruption_label=label)
            comp = get_row(binary_lookup, track_id="binary_exact_record", method_id=comparator, cell_id=cell_id, channel_id=channel, corruption_label=label)
            if cand is None or comp is None:
                return incomplete_result(gate, [f"Missing paired rows for {cell_id}/{label}."])
            if cand.trials != 64 or comp.trials != 64:
                return incomplete_result(gate, [f"Unexpected trial count for {cell_id}/{label}."])
            for row in (cand, comp):
                errs = validate_summary_row(row)
                if errs:
                    return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": errs}
            exact_delta = abs(cand.exact_recovery_rate - comp.exact_recovery_rate)
            silent_delta = abs(cand.silent_wrong_rate - comp.silent_wrong_rate)
            detected_delta = abs(cand.detected_failure_rate - comp.detected_failure_rate)
            if exact_delta > gate["thresholds"]["exact_recovery_rate_abs_margin_max"]:
                reasons.append(f"{cell_id}/{label} exact delta {exact_delta} exceeds margin.")
            if silent_delta > gate["thresholds"]["silent_wrong_rate_abs_margin_max"]:
                reasons.append(f"{cell_id}/{label} silent delta {silent_delta} exceeds margin.")
            if detected_delta > gate["thresholds"]["detected_failure_rate_abs_margin_max"]:
                reasons.append(f"{cell_id}/{label} detected delta {detected_delta} exceeds margin.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["Raw NeCo and generic linear stay within all practical margins."])


def evaluate_map_silent_collapse_gate(gate: dict[str, Any], map_lookup: dict[tuple[str, str, str, str, str], SummaryRow]) -> dict[str, Any]:
    reasons: list[str] = []
    channel = gate["corruption_points"]["channel_id"]
    for method_id in gate["methods"]["candidates"]:
        for label in gate["required_points"]["u1_f3_m68"]:
            row = get_row(map_lookup, track_id="map_native_sign_flip", method_id=method_id, cell_id="u1_f3_m68", channel_id=channel, corruption_label=label)
            if row is None:
                return incomplete_result(gate, [f"Missing MAP row for {method_id} {label}."])
            if row.trials != 64:
                return incomplete_result(gate, [f"Unexpected trials for {method_id} {label}: {row.trials}."])
            errs = validate_summary_row(row)
            if errs:
                return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": errs}
            if row.exact_recovery_rate > gate["thresholds"]["exact_recovery_rate_max"]:
                reasons.append(f"{method_id}/{label} exact {row.exact_recovery_rate} exceeds collapse max.")
            if row.silent_wrong_rate < gate["thresholds"]["silent_wrong_rate_min"]:
                reasons.append(f"{method_id}/{label} silent {row.silent_wrong_rate} below collapse min.")
            if row.detected_failure_rate > gate["thresholds"]["detected_failure_rate_max"]:
                reasons.append(f"{method_id}/{label} detected {row.detected_failure_rate} exceeds collapse max.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["Both MAP arms satisfy the frozen high-capacity silent-collapse rule."])


def evaluate_map_graceful_gate(gate: dict[str, Any], map_lookup: dict[tuple[str, str, str, str, str], SummaryRow]) -> dict[str, Any]:
    reasons: list[str] = []
    method_id = gate["methods"]["candidate"]
    channel = gate["corruption_points"]["channel_id"]
    for label in gate["required_points"]["u1_f3_m31"]:
        row = get_row(map_lookup, track_id="map_native_sign_flip", method_id=method_id, cell_id="u1_f3_m31", channel_id=channel, corruption_label=label)
        if row is None:
            return incomplete_result(gate, [f"Missing graceful-region row for {label}."])
        if row.trials != 64:
            return incomplete_result(gate, [f"Unexpected trials for graceful-region row {label}: {row.trials}."])
        errs = validate_summary_row(row)
        if errs:
            return {"gate_id": gate["id"], "state": "EXCEPTION", "disposition": None, "reasons": errs}
        if row.exact_recovery_rate < gate["thresholds"]["exact_recovery_rate_min"]:
            reasons.append(f"{label} exact {row.exact_recovery_rate} below minimum.")
        if row.exact_recovery_rate > gate["thresholds"]["exact_recovery_rate_max"]:
            reasons.append(f"{label} exact {row.exact_recovery_rate} above maximum.")
        if row.silent_wrong_rate > gate["thresholds"]["silent_wrong_rate_max"]:
            reasons.append(f"{label} silent {row.silent_wrong_rate} above maximum.")
        if row.mean_correct_factors < gate["thresholds"]["mean_correct_factors_min"]:
            reasons.append(f"{label} mean_correct {row.mean_correct_factors} below minimum.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["Extended MAP satisfies the frozen graceful-region rule on all selected points."])


def evaluate_no_shared_winner_gate(gate: dict[str, Any], protocol_v3: dict[str, Any]) -> dict[str, Any]:
    metadata = protocol_v3.get("contract_gate_metadata", {}).get("no_shared_noise_winner_contract_v1")
    if metadata is not None:
        required_keys = {
            "binary_track_channel_ids",
            "map_track_channel_ids",
            "shared_calibrated_severity_mapping_exists",
            "cross_track_equal_difficulty_claim_allowed",
            "bcf_track_status",
        }
        missing = sorted(required_keys.difference(metadata))
        if missing:
            return exception_result(
                gate,
                [f"Missing required contract metadata keys: {', '.join(missing)}."],
            )
        if not isinstance(metadata["binary_track_channel_ids"], list) or not all(
            isinstance(item, str) for item in metadata["binary_track_channel_ids"]
        ):
            return exception_result(gate, ["binary_track_channel_ids must be a list of strings."])
        if not isinstance(metadata["map_track_channel_ids"], list) or not all(
            isinstance(item, str) for item in metadata["map_track_channel_ids"]
        ):
            return exception_result(gate, ["map_track_channel_ids must be a list of strings."])
        if not isinstance(metadata["shared_calibrated_severity_mapping_exists"], bool):
            return exception_result(
                gate,
                ["shared_calibrated_severity_mapping_exists must be a boolean."],
            )
        if not isinstance(metadata["cross_track_equal_difficulty_claim_allowed"], bool):
            return exception_result(
                gate,
                ["cross_track_equal_difficulty_claim_allowed must be a boolean."],
            )
        if not isinstance(metadata["bcf_track_status"], str):
            return exception_result(gate, ["bcf_track_status must be a string."])

        reasons: list[str] = []
        binary_channels = set(metadata["binary_track_channel_ids"])
        map_channels = set(metadata["map_track_channel_ids"])
        if binary_channels == map_channels:
            reasons.append("Binary and MAP channel sets are identical, so incompatibility is not established.")
        if metadata["shared_calibrated_severity_mapping_exists"]:
            reasons.append("Protocol metadata claims a shared calibrated severity mapping exists.")
        if metadata["cross_track_equal_difficulty_claim_allowed"]:
            reasons.append("Protocol metadata allows a cross-track equal-difficulty winner claim.")
        if metadata["bcf_track_status"] != BCF_BLOCKED:
            reasons.append("BCF track is no longer blocked.")
        return fail_result(gate, reasons) if reasons else pass_result(
            gate,
            ["Protocol contract still forbids a shared cross-track noise winner."],
        )

    reasons: list[str] = []
    binary_channels = set(protocol_v3["preserved_scientific_fields"]["binary_track"]["corruption_channels"])
    map_channels = set(protocol_v3["preserved_scientific_fields"]["map_track"]["corruption_channels"])
    binary_claims = set(protocol_v3["claim_limits"]["binary_track"])
    global_claims = set(protocol_v3["claim_limits"]["global"])
    if binary_channels == map_channels:
        reasons.append("Binary and MAP channel sets are identical, so incompatibility is not established.")
    if "No cross-track universal winner" not in binary_claims or "No cross-track universal winner" not in global_claims:
        reasons.append("Cross-track universal-winner claim limit is absent.")
    if protocol_v3["preserved_scientific_fields"]["bcf_track"]["status"] != BCF_BLOCKED:
        reasons.append("BCF track is no longer blocked.")
    return fail_result(gate, reasons) if reasons else pass_result(gate, ["Protocol contract still forbids a shared cross-track noise winner."])


def evaluate_gate(
    gate: dict[str, Any],
    *,
    binary_rows: list[SummaryRow],
    map_rows: list[SummaryRow],
    protocol_v3: dict[str, Any],
) -> dict[str, Any]:
    binary_lookup = rows_to_index(binary_rows)
    map_lookup = rows_to_index(map_rows)
    if gate["id"] == "bch_binary_exact_record_dominance_v1":
        return evaluate_bch_gate(gate, binary_lookup)
    if gate["id"] == "raw_neco_noise_gap_v1":
        return evaluate_raw_neco_gap_gate(gate, binary_lookup)
    if gate["id"] == "generic_linear_practical_equivalence_v1":
        return evaluate_generic_equivalence_gate(gate, binary_lookup)
    if gate["id"] == "map_silent_collapse_v1":
        return evaluate_map_silent_collapse_gate(gate, map_lookup)
    if gate["id"] == "map_graceful_region_v1":
        return evaluate_map_graceful_gate(gate, map_lookup)
    if gate["id"] == "no_shared_noise_winner_contract_v1":
        return evaluate_no_shared_winner_gate(gate, protocol_v3)
    raise KeyError(f"Unknown gate id: {gate['id']}")


def build_metric_definitions() -> dict[str, str]:
    return {
        "exact_recovery_rate": "fraction of trials whose decoded tuple exactly matches the true factor indices",
        "full_wrong_rate": "fraction of trials returning a full but incorrect tuple",
        "silent_wrong_rate": "fraction of trials returning a wrong tuple without detected failure",
        "detected_failure_rate": "fraction of trials returning typed detected failure instead of a valid semantic tuple",
        "partial_factor_recovery_rate": "fraction of trials with nonzero but incomplete factor recovery",
        "mean_correct_factors": "mean number of correctly recovered factors per trial",
        "conditional_wrong_given_nonfailure": "wrong full-tuple rate among trials that did not produce detected failure",
        "miscorrection_rate": "BCH-only fraction of trials that decode to the wrong valid or unassigned payload",
    }


def build_protocol_v3(protocol_v2: dict[str, Any], gates: list[dict[str, Any]], source_audit_hash: str) -> dict[str, Any]:
    protocol_v3 = deepcopy(protocol_v2)
    protocol_v3["protocol_version"] = LEVEL3_5B_GATE_PROTOCOL_V3
    protocol_v3["supersedes_protocol_v2_hash"] = PROTOCOL_V2_CANONICAL_HASH
    protocol_v3["heldout_trials_observed_before_v3"] = 0
    protocol_v3["heldout_outcomes_available_to_gate_design"] = False
    protocol_v3["gate_semantics_newly_specified"] = True
    protocol_v3["stage_classification"] = [
        "PRE_EXECUTION_PROTOCOL_COMPLETION",
        "PROSPECTIVE_GATE_SPECIFICATION",
        "NO_HELDOUT_LEAKAGE",
    ]
    protocol_v3["correct_classification_statement"] = (
        "This stage is not an administrative repair of existing executable gates, because executable quantitative gate semantics did not previously exist."
    )
    protocol_v3["statistics_policy"] = build_global_statistical_policy()
    protocol_v3["metric_definitions"] = build_metric_definitions()
    protocol_v3["confirmatory_dispositions"] = [
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
        BCF_BLOCKED,
        "NO_SHARED_NOISE_WINNER",
        NO_SHARED_NOISE_WINNER_NOT_CONFIRMED,
    ]
    protocol_v3["confirmatory_gates"] = gates
    protocol_v3["canonical_gate_hashes"] = {gate["id"]: gate["rule_hash"] for gate in gates}
    protocol_v3["deterministic_verdict_evaluation_order"] = [gate["id"] for gate in gates]
    protocol_v3["missing_outcome_policy"] = {
        "summary_row_missing": "INCOMPLETE_INPUT",
        "trial_count_mismatch": "INCOMPLETE_INPUT",
        "exceptional_summary_metrics": "EXCEPTION",
        "no_substantive_verdict_without_complete_inputs": True,
    }
    protocol_v3["gate_source_audit_hash"] = source_audit_hash
    return protocol_v3


def build_protocol_diff(protocol_v2: dict[str, Any], protocol_v3: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "v2_canonical_hash": PROTOCOL_V2_CANONICAL_HASH,
        "v3_canonical_hash": canonical_json_hash(protocol_v3),
        "allowed_change_types": sorted(ALLOWED_DIFF_TYPES),
        "rows": [
            {"field": "protocol_version", "change_type": "METADATA_ONLY"},
            {"field": "supersedes_protocol_v2_hash", "change_type": "METADATA_ONLY"},
            {"field": "heldout_trials_observed_before_v3", "change_type": "METADATA_ONLY"},
            {"field": "heldout_outcomes_available_to_gate_design", "change_type": "METADATA_ONLY"},
            {"field": "stage_classification", "change_type": "METADATA_ONLY"},
            {"field": "correct_classification_statement", "change_type": "METADATA_ONLY"},
            {"field": "statistics_policy", "change_type": "STATISTICAL_POLICY_ADDED"},
            {"field": "metric_definitions", "change_type": "METADATA_ONLY"},
            {"field": "confirmatory_dispositions", "change_type": "CONFIRMATORY_GATE_SEMANTICS_ADDED"},
            {"field": "confirmatory_gates", "change_type": "CONFIRMATORY_GATE_SEMANTICS_ADDED"},
            {"field": "canonical_gate_hashes", "change_type": "CONFIRMATORY_GATE_SEMANTICS_ADDED"},
            {"field": "deterministic_verdict_evaluation_order", "change_type": "CONFIRMATORY_GATE_SEMANTICS_ADDED"},
            {"field": "missing_outcome_policy", "change_type": "MISSING_OUTCOME_POLICY_ADDED"},
            {"field": "gate_source_audit_hash", "change_type": "METADATA_ONLY"},
        ],
    }


def validate_protocol_v3(
    repo_root: Path,
    *,
    protocol_v2: dict[str, Any],
    protocol_v3: dict[str, Any],
    gates: list[dict[str, Any]],
    protocol_diff: dict[str, Any],
) -> dict[str, Any]:
    old_heldout_analysis = read_json(repo_root / V1_BLOCKED_DIR / "analysis.json")
    v2_heldout_analysis = read_json(repo_root / V2_ANALYSIS_PATH)
    repair_analysis = read_json(repo_root / REPAIR_ANALYSIS_PATH)
    seed_audit = read_json(repo_root / SEED_AUDIT_PATH)
    repair_validator = read_json(repo_root / REPAIR_VALIDATOR_PATH)
    immutable_ok, changed = unchanged_since_checkpoint(repo_root, IMMUTABLE_PREVIOUS_EVIDENCE_PATHS)
    v1_trial_rows = count_jsonl_rows(repo_root / V1_BLOCKED_DIR / "binary_trials.jsonl") + count_jsonl_rows(repo_root / V1_BLOCKED_DIR / "map_trials.jsonl")
    v2_trial_rows = count_jsonl_rows(repo_root / V2_BLOCKED_DIR / "binary_trials.jsonl") + count_jsonl_rows(repo_root / V2_BLOCKED_DIR / "map_trials.jsonl")

    methods_unchanged = (
        protocol_v3["preserved_scientific_fields"]["binary_track"]["methods"] == protocol_v2["preserved_scientific_fields"]["binary_track"]["methods"]
        and protocol_v3["preserved_scientific_fields"]["map_track"]["methods"] == protocol_v2["preserved_scientific_fields"]["map_track"]["methods"]
    )
    cells_unchanged = (
        protocol_v3["preserved_scientific_fields"]["binary_track"]["semantic_cells"] == protocol_v2["preserved_scientific_fields"]["binary_track"]["semantic_cells"]
        and protocol_v3["preserved_scientific_fields"]["map_track"]["semantic_cells"] == protocol_v2["preserved_scientific_fields"]["map_track"]["semantic_cells"]
    )
    points_unchanged = (
        protocol_v3["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"] == protocol_v2["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"]
        and protocol_v3["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"] == protocol_v2["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]
    )
    seeds_unchanged = protocol_v3["fresh_seed_ranges"] == protocol_v2["fresh_seed_ranges"]
    trial_counts_unchanged = protocol_v3["trial_counts"] == protocol_v2["trial_counts"]
    configs_unchanged = protocol_v3["complete_config_records"] == protocol_v2["complete_config_records"]
    metrics_unchanged = protocol_v3["metrics"] == protocol_v2["metrics"]

    gate_schema_complete = True
    undefined_thresholds: list[str] = []
    missing_provenance: list[str] = []
    bad_hashes: list[str] = []
    for gate in gates:
        for field in (
            "id",
            "disposition_if_pass",
            "disposition_if_fail",
            "scientific_question",
            "source_class",
            "source_provenance",
            "methods",
            "semantic_cells",
            "corruption_points",
            "included_metrics",
            "excluded_metrics",
            "aggregation_unit",
            "comparison_operator",
            "thresholds",
            "required_points",
            "required_cells",
            "missing_trial_policy",
            "exceptional_trial_policy",
            "tie_policy",
            "multiplicity_policy",
            "confidence_interval_policy",
            "minimum_effect_requirement",
            "silent_error_constraint",
            "resource_constraint",
            "deterministic_evaluation_order",
            "rule_version",
            "rule_hash",
        ):
            if field not in gate:
                gate_schema_complete = False
        if gate["source_provenance"] in ({}, None):
            missing_provenance.append(gate["id"])
        if any(value is None for value in gate["thresholds"].values()):
            undefined_thresholds.append(gate["id"])
        if gate["rule_hash"] != complete_gate_hash(gate):
            bad_hashes.append(gate["id"])
    unsupported_diff = [row["change_type"] for row in protocol_diff["rows"] if row["change_type"] not in ALLOWED_DIFF_TYPES]

    verdict = LEVEL3_5B_GATE_COMPLETION_VERDICT
    if unsupported_diff or not all((methods_unchanged, cells_unchanged, points_unchanged, seeds_unchanged, trial_counts_unchanged, configs_unchanged, metrics_unchanged)):
        verdict = LEVEL3_5B_GATE_BLOCK_CHANGE
    elif not immutable_ok:
        verdict = LEVEL3_5B_GATE_BLOCK_CHANGE
    elif missing_provenance:
        verdict = LEVEL3_5B_GATE_BLOCK_PROVENANCE
    elif undefined_thresholds or not gate_schema_complete or bad_hashes:
        verdict = LEVEL3_5B_GATE_BLOCK_OPERATIONALIZATION
    elif not seed_audit["audit_verdict"] == "PASS":
        verdict = LEVEL3_5B_GATE_BLOCK_EVIDENCE

    return {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "heldout_trials_observed": 0,
        "heldout_outcomes_available_to_gate_design": False,
        "zero_heldout_trials_before_v3": (
            old_heldout_analysis.get("trials_executed", 0) == 0
            and v2_heldout_analysis.get("trials_executed", 0) == 0
            and repair_analysis.get("heldout_trials_executed", 0) == 0
            and v1_trial_rows == 0
            and v2_trial_rows == 0
        ),
        "v1_and_v2_unchanged_since_previous_blocked_checkpoint": immutable_ok,
        "changed_immutable_paths": changed,
        "methods_unchanged": methods_unchanged,
        "cells_unchanged": cells_unchanged,
        "corruption_points_unchanged": points_unchanged,
        "seeds_unchanged_from_v2": seeds_unchanged,
        "trial_counts_unchanged": trial_counts_unchanged,
        "configs_unchanged": configs_unchanged,
        "metrics_unchanged": metrics_unchanged,
        "bcf_remains_blocked": protocol_v3["preserved_scientific_fields"]["bcf_track"]["status"] == BCF_BLOCKED,
        "gate_schema_complete": gate_schema_complete,
        "undefined_thresholds": undefined_thresholds,
        "missing_provenance": missing_provenance,
        "bad_rule_hashes": bad_hashes,
        "unsupported_protocol_diff_types": unsupported_diff,
        "deterministic_gate_order": protocol_v3["deterministic_verdict_evaluation_order"],
        "repair_seed_audit_pass": seed_audit["audit_verdict"] == "PASS",
        "repair_validator_ready": repair_validator.get("ready_for_level3_5b_heldout_v2", False),
        "benchmark_execution_invoked": False,
        "validator_verdict": verdict,
    }


def make_binary_row(method: str, cell: str, label: str, *, exact: float, silent: float, detected: float, trials: int = 64, miscorrection: float | None = None) -> SummaryRow:
    return SummaryRow(
        track_id="binary_exact_record",
        method_id=method,
        cell_id=cell,
        channel_id="EXACT_WEIGHT_BIT_FLIPS",
        corruption_label=label,
        trials=trials,
        exact_recovery_rate=exact,
        full_wrong_rate=silent,
        silent_wrong_rate=silent,
        detected_failure_rate=detected,
        partial_factor_recovery_rate=max(0.0, 1.0 - exact - silent - detected),
        mean_correct_factors=3.0 * exact,
        conditional_wrong_given_nonfailure=(silent / (1.0 - detected)) if detected < 1.0 else 0.0,
        extra={"miscorrection_rate": miscorrection if miscorrection is not None else ""},
    )


def make_map_row(method: str, cell: str, label: str, *, exact: float, silent: float, mean_correct: float, detected: float = 0.0, trials: int = 64) -> SummaryRow:
    return SummaryRow(
        track_id="map_native_sign_flip",
        method_id=method,
        cell_id=cell,
        channel_id="MAP_SIGN_FLIP",
        corruption_label=label,
        trials=trials,
        exact_recovery_rate=exact,
        full_wrong_rate=silent,
        silent_wrong_rate=silent,
        detected_failure_rate=detected,
        partial_factor_recovery_rate=max(0.0, 1.0 - exact - silent - detected),
        mean_correct_factors=mean_correct,
        conditional_wrong_given_nonfailure=(silent / (1.0 - detected)) if detected < 1.0 else 0.0,
        extra={},
    )


def build_synthetic_cases(protocol_v3: dict[str, Any], gates: list[dict[str, Any]]) -> dict[str, Any]:
    gate_map = {gate["id"]: gate for gate in gates}

    binary_base: list[SummaryRow] = []
    for cell, labels in protocol_v3["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"].items():
        for label in labels:
            if label == "e=0":
                binary_base.extend(
                    [
                        make_binary_row("packed_tuple_bch_high_redundancy", cell, label, exact=1.0, silent=0.0, detected=0.0, miscorrection=0.0),
                        make_binary_row("packed_tuple_bch_low_redundancy", cell, label, exact=1.0, silent=0.0, detected=0.0, miscorrection=0.0),
                        make_binary_row("uncoded_packed_tuple", cell, label, exact=1.0, silent=0.0, detected=0.0),
                        make_binary_row("generic_full_rank_linear_mix", cell, label, exact=1.0, silent=0.0, detected=0.0),
                        make_binary_row("raw_neco_algebraic_recovery", cell, label, exact=1.0, silent=0.0, detected=0.0),
                    ]
                )
            else:
                binary_base.extend(
                    [
                        make_binary_row("packed_tuple_bch_high_redundancy", cell, label, exact=1.0, silent=0.0, detected=0.0, miscorrection=0.0),
                        make_binary_row("packed_tuple_bch_low_redundancy", cell, label, exact=0.5, silent=0.25, detected=0.25, miscorrection=0.25),
                        make_binary_row("uncoded_packed_tuple", cell, label, exact=0.0, silent=0.75, detected=0.25),
                        make_binary_row("generic_full_rank_linear_mix", cell, label, exact=0.0, silent=0.0, detected=1.0),
                        make_binary_row("raw_neco_algebraic_recovery", cell, label, exact=0.0, silent=0.0, detected=1.0),
                    ]
                )

    map_base: list[SummaryRow] = []
    for label in protocol_v3["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]["u1_f3_m68"]:
        map_base.extend(
            [
                make_map_row("map_d1024", "u1_f3_m68", label, exact=0.0, silent=1.0, mean_correct=0.0),
                make_map_row("map_d1024_step32_r4_best_native_reconstruction", "u1_f3_m68", label, exact=0.0, silent=1.0, mean_correct=0.0),
            ]
        )
    for label in protocol_v3["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]["u1_f3_m31"]:
        if label in {"p=0.0", "p=0.01", "p=0.02", "p=0.05"}:
            map_base.append(
                make_map_row("map_d1024_step32_r4_best_native_reconstruction", "u1_f3_m31", label, exact=0.5, silent=0.4, mean_correct=1.8)
            )
        else:
            map_base.append(
                make_map_row("map_d1024_step32_r4_best_native_reconstruction", "u1_f3_m31", label, exact=0.1, silent=0.8, mean_correct=0.5)
            )
    cases: dict[str, Any] = {}
    for gate in gates:
        pass_binary = deepcopy(binary_base)
        pass_map = deepcopy(map_base)
        pass_result_case = evaluate_gate(gate, binary_rows=pass_binary, map_rows=pass_map, protocol_v3=protocol_v3)

        fail_binary = deepcopy(binary_base)
        fail_map = deepcopy(map_base)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            fail_binary = [row if not (row.method_id == "packed_tuple_bch_high_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.0, silent=0.2, detected=0.8, miscorrection=0.3) for row in fail_binary]
        elif gate["id"] == "raw_neco_noise_gap_v1":
            fail_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.5, silent=0.0, detected=0.5) for row in fail_binary]
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            fail_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.5, silent=0.0, detected=0.5) for row in fail_binary]
        elif gate["id"] == "map_silent_collapse_v1":
            fail_map = [row if not (row.method_id == "map_d1024" and row.cell_id == "u1_f3_m68" and row.corruption_label == "p=0.0") else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.4, silent=0.6, mean_correct=1.0) for row in fail_map]
        elif gate["id"] == "map_graceful_region_v1":
            fail_map = [row if not (row.method_id == "map_d1024_step32_r4_best_native_reconstruction" and row.cell_id == "u1_f3_m31" and row.corruption_label == "p=0.02") else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.2, silent=0.6, mean_correct=1.0) for row in fail_map]
        else:
            mutated = deepcopy(protocol_v3)
            mutated["claim_limits"]["global"] = []
            fail_result_case = evaluate_gate(gate, binary_rows=fail_binary, map_rows=fail_map, protocol_v3=mutated)
            boundary_result_case = evaluate_gate(gate, binary_rows=pass_binary, map_rows=pass_map, protocol_v3=protocol_v3)
            cases[gate["id"]] = {
                "pass_case": pass_result_case,
                "fail_case": fail_result_case,
                "boundary_case": boundary_result_case,
                "missing_data_case": incomplete_result(gate, ["Synthetic protocol-contract fixture omitted required compatibility evidence."]),
                "exceptional_trial_case": incomplete_result(gate, ["Protocol-only gate has no trial rows; synthetic exceptional input blocks evaluation."]),
                "tie_case": pass_result_case,
                "contradictory_metrics_case": fail_result(gate, ["Synthetic protocol-contract fixture contradicts the frozen compatibility guardrail."]),
            }
            continue

        fail_result_case = evaluate_gate(gate, binary_rows=fail_binary, map_rows=fail_map, protocol_v3=protocol_v3)

        boundary_binary = deepcopy(binary_base)
        boundary_map = deepcopy(map_base)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            boundary_binary = [row if not (row.method_id == "packed_tuple_bch_high_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.5, silent=0.125, detected=0.375, miscorrection=0.2) for row in boundary_binary]
        elif gate["id"] == "raw_neco_noise_gap_v1":
            boundary_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.1, silent=0.0, detected=0.9) for row in boundary_binary]
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            boundary_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.1, silent=0.05, detected=0.9) for row in boundary_binary]
        elif gate["id"] == "map_silent_collapse_v1":
            boundary_map = [row if not (row.method_id == "map_d1024" and row.cell_id == "u1_f3_m68" and row.corruption_label == "p=0.0") else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.1, silent=0.9, mean_correct=0.3, detected=0.05) for row in boundary_map]
        elif gate["id"] == "map_graceful_region_v1":
            boundary_map = [row if not (row.method_id == "map_d1024_step32_r4_best_native_reconstruction" and row.cell_id == "u1_f3_m31" and row.corruption_label == "p=0.02") else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.25, silent=0.5, mean_correct=1.5) for row in boundary_map]
        boundary_result_case = evaluate_gate(gate, binary_rows=boundary_binary, map_rows=boundary_map, protocol_v3=protocol_v3)

        missing_binary = deepcopy(pass_binary)
        missing_map = deepcopy(pass_map)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            missing_binary = [row for row in missing_binary if not (row.method_id == "packed_tuple_bch_high_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")]
            missing_result_case = evaluate_gate(gate, binary_rows=missing_binary, map_rows=missing_map, protocol_v3=protocol_v3)
        elif gate["id"] == "raw_neco_noise_gap_v1":
            missing_binary = [row for row in missing_binary if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")]
            missing_result_case = evaluate_gate(gate, binary_rows=missing_binary, map_rows=missing_map, protocol_v3=protocol_v3)
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            missing_binary = [row for row in missing_binary if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")]
            missing_result_case = evaluate_gate(gate, binary_rows=missing_binary, map_rows=missing_map, protocol_v3=protocol_v3)
        elif gate["id"] == "map_silent_collapse_v1":
            missing_map = [row for row in missing_map if not (row.method_id == "map_d1024" and row.cell_id == "u1_f3_m68" and row.corruption_label == "p=0.0")]
            missing_result_case = evaluate_gate(gate, binary_rows=missing_binary, map_rows=missing_map, protocol_v3=protocol_v3)
        elif gate["id"] == "map_graceful_region_v1":
            missing_map = [row for row in missing_map if not (row.method_id == "map_d1024_step32_r4_best_native_reconstruction" and row.cell_id == "u1_f3_m31" and row.corruption_label == "p=0.02")]
            missing_result_case = evaluate_gate(gate, binary_rows=missing_binary, map_rows=missing_map, protocol_v3=protocol_v3)
        else:
            missing_result_case = incomplete_result(gate, ["Synthetic protocol-contract fixture omitted required compatibility evidence."])

        exceptional_binary = deepcopy(pass_binary)
        exceptional_map = deepcopy(pass_map)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            exceptional_binary = [
                row if not (row.method_id == "packed_tuple_bch_high_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")
                else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=1.0, silent=0.0, detected=0.0, trials=63, miscorrection=0.0)
                for row in exceptional_binary
            ]
        elif gate["id"] == "raw_neco_noise_gap_v1":
            exceptional_binary = [
                row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")
                else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.0, silent=0.0, detected=1.0, trials=63)
                for row in exceptional_binary
            ]
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            exceptional_binary = [
                row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1")
                else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=0.0, silent=0.0, detected=1.0, trials=63)
                for row in exceptional_binary
            ]
        elif gate["id"] == "map_silent_collapse_v1":
            exceptional_map = [
                row if not (row.method_id == "map_d1024" and row.cell_id == "u1_f3_m68" and row.corruption_label == "p=0.0")
                else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.0, silent=1.0, mean_correct=0.0, trials=63)
                for row in exceptional_map
            ]
        elif gate["id"] == "map_graceful_region_v1":
            exceptional_map = [
                row if not (row.method_id == "map_d1024_step32_r4_best_native_reconstruction" and row.cell_id == "u1_f3_m31" and row.corruption_label == "p=0.02")
                else make_map_row(row.method_id, row.cell_id, row.corruption_label, exact=0.5, silent=0.4, mean_correct=1.8, trials=63)
                for row in exceptional_map
            ]
        exceptional_result_case = evaluate_gate(gate, binary_rows=exceptional_binary, map_rows=exceptional_map, protocol_v3=protocol_v3)

        tie_binary = deepcopy(pass_binary)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            tie_binary = [row if not (row.method_id == "packed_tuple_bch_low_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else make_binary_row(row.method_id, row.cell_id, row.corruption_label, exact=1.0, silent=0.0, detected=0.0, miscorrection=0.0) for row in tie_binary]
        tie_result_case = evaluate_gate(gate, binary_rows=tie_binary, map_rows=pass_map, protocol_v3=protocol_v3)

        contradictory_binary = deepcopy(pass_binary)
        contradictory_map = deepcopy(pass_map)
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            contradictory_binary = [row if not (row.method_id == "packed_tuple_bch_high_redundancy" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else SummaryRow(**{**row.__dict__, "silent_wrong_rate": 1.5}) for row in contradictory_binary]
        elif gate["id"] == "raw_neco_noise_gap_v1":
            contradictory_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else SummaryRow(**{**row.__dict__, "detected_failure_rate": 1.5}) for row in contradictory_binary]
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            contradictory_binary = [row if not (row.method_id == "raw_neco_algebraic_recovery" and row.cell_id == "u1_f3_m10" and row.corruption_label == "e=1") else SummaryRow(**{**row.__dict__, "detected_failure_rate": 1.5}) for row in contradictory_binary]
        elif gate["id"] == "map_silent_collapse_v1":
            contradictory_map = [row if not (row.method_id == "map_d1024" and row.cell_id == "u1_f3_m68" and row.corruption_label == "p=0.0") else SummaryRow(**{**row.__dict__, "silent_wrong_rate": 1.5}) for row in contradictory_map]
        elif gate["id"] == "map_graceful_region_v1":
            contradictory_map = [row if not (row.method_id == "map_d1024_step32_r4_best_native_reconstruction" and row.cell_id == "u1_f3_m31" and row.corruption_label == "p=0.02") else SummaryRow(**{**row.__dict__, "silent_wrong_rate": 1.5}) for row in contradictory_map]
        contradictory_result_case = evaluate_gate(gate, binary_rows=contradictory_binary, map_rows=contradictory_map, protocol_v3=protocol_v3)

        cases[gate["id"]] = {
            "pass_case": pass_result_case,
            "fail_case": fail_result_case,
            "boundary_case": boundary_result_case,
            "missing_data_case": missing_result_case,
            "exceptional_trial_case": exceptional_result_case,
            "tie_case": tie_result_case,
            "contradictory_metrics_case": contradictory_result_case,
        }
    return cases


def build_development_gate_calibration(
    protocol_v3: dict[str, Any],
    gates: list[dict[str, Any]],
    binary_rows: list[SummaryRow],
    map_rows: list[SummaryRow],
) -> dict[str, Any]:
    dev_binary_rows = [SummaryRow(**{**row.__dict__, "trials": 64}) for row in binary_rows]
    dev_map_rows = [SummaryRow(**{**row.__dict__, "trials": 64}) for row in map_rows]
    calibration_rows = []
    for gate in gates:
        dev_result = evaluate_gate(gate, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
        sensitivity: list[dict[str, Any]] = []
        if gate["id"] == "bch_binary_exact_record_dominance_v1":
            for miscorrection_ceiling in (0.20, 0.375, 0.50):
                probe = deepcopy(gate)
                probe["thresholds"]["miscorrection_rate_max"] = miscorrection_ceiling
                result = evaluate_gate(probe, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
                sensitivity.append({"parameter": "miscorrection_rate_max", "value": miscorrection_ceiling, "state": result["state"], "disposition": result["disposition"]})
        elif gate["id"] == "raw_neco_noise_gap_v1":
            for detected_min in (1.0, 0.9, 0.8):
                probe = deepcopy(gate)
                probe["thresholds"]["nonzero_detected_failure_min"] = detected_min
                result = evaluate_gate(probe, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
                sensitivity.append({"parameter": "nonzero_detected_failure_min", "value": detected_min, "state": result["state"], "disposition": result["disposition"]})
        elif gate["id"] == "generic_linear_practical_equivalence_v1":
            for margin in (0.05, 0.10, 0.20):
                probe = deepcopy(gate)
                probe["thresholds"]["exact_recovery_rate_abs_margin_max"] = margin
                probe["thresholds"]["detected_failure_rate_abs_margin_max"] = margin
                result = evaluate_gate(probe, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
                sensitivity.append({"parameter": "paired_rate_margin", "value": margin, "state": result["state"], "disposition": result["disposition"]})
        elif gate["id"] == "map_silent_collapse_v1":
            for silent_min in (0.75, 0.90, 0.95):
                probe = deepcopy(gate)
                probe["thresholds"]["silent_wrong_rate_min"] = silent_min
                result = evaluate_gate(probe, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
                sensitivity.append({"parameter": "silent_wrong_rate_min", "value": silent_min, "state": result["state"], "disposition": result["disposition"]})
        elif gate["id"] == "map_graceful_region_v1":
            for silent_max in (0.40, 0.50, 0.60):
                probe = deepcopy(gate)
                probe["thresholds"]["silent_wrong_rate_max"] = silent_max
                result = evaluate_gate(probe, binary_rows=dev_binary_rows, map_rows=dev_map_rows, protocol_v3=protocol_v3)
                sensitivity.append({"parameter": "silent_wrong_rate_max", "value": silent_max, "state": result["state"], "disposition": result["disposition"]})
        else:
            sensitivity.append({"parameter": "contract", "value": "fixed", "state": dev_result["state"], "disposition": dev_result["disposition"]})

        calibration_rows.append(
            {
                "gate_id": gate["id"],
                "disposition_if_pass": gate["disposition_if_pass"],
                "development_result": dev_result,
                "development_observed_trials_per_point": 16,
                "development_rate_only_evaluation": True,
                "development_metrics_used": gate["included_metrics"],
                "candidate_threshold_rationale": gate["thresholds"],
                "sensitivity_to_nearby_thresholds": sensitivity,
                "why_not_uniquely_optimized": "Selected margins are coarse, interpretable guardrails from existing development summaries, not a search over held-out outcomes.",
                "expected_interpretation": gate["scientific_question"],
                "known_weakness": "Development sample size is 16 per point; confirmatory rules are intentionally simple and may fail to generalize on held-out.",
            }
        )
    return {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "heldout_trials_observed": 0,
        "rows": calibration_rows,
    }


def render_gate_spec_doc(repo_root: Path, analysis: dict[str, Any], protocol_v3_hash: str, source_audit: list[dict[str, Any]]) -> None:
    recovered = analysis["recovered_gate_ids"]
    new_rules = analysis["newly_defined_gate_ids"]
    lines = [
        "# Level 3.5b Prospective Gate Specification",
        "",
        f"- Schema: `{LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION}`",
        f"- Completion verdict: `{analysis['completion_verdict']}`",
        f"- Ready verdict: `{analysis['ready_verdict']}`",
        f"- heldout_trials_observed: `{analysis['heldout_trials_observed']}`",
        f"- heldout_outcomes_available_to_gate_design: `{analysis['heldout_outcomes_available_to_gate_design']}`",
        f"- Protocol v2 hash: `{PROTOCOL_V2_CANONICAL_HASH}`",
        f"- Protocol v3 hash: `{protocol_v3_hash}`",
        "",
        "## Classification",
        "",
        "- PRE_EXECUTION_PROTOCOL_COMPLETION",
        "- PROSPECTIVE_GATE_SPECIFICATION",
        "- NO_HELDOUT_LEAKAGE",
        "",
        "## Why v2 Was Incomplete",
        "",
        "- v2 froze methods, cells, points, seeds, configs and metrics.",
        "- v2 serialized disposition labels in `gates`, but not executable quantitative decision rules.",
        "- The v2 runner therefore blocked execution before first trial.",
        "",
        "## Recovered vs Newly Defined",
        "",
        f"- Recovered pre-heldout contract rules: `{', '.join(recovered)}`",
        f"- Newly defined prospective rules from development-only evidence: `{', '.join(new_rules)}`",
        "",
        "## Claim Limits",
        "",
        "- No binary, BCH, NeCo, generic-linear, MAP or BCF held-out outcome has been observed.",
        "- v3 is the first final executable confirmatory protocol for Level 3.5b.",
        "- All gate thresholds remain development-calibrated and held-out-unseen.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_PROSPECTIVE_GATE_SPECIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_level3_5b_gate_specification(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_gate_specification"
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol_v2 = read_json(repo_root / V2_PROTOCOL_PATH)
    binary_rows = load_csv_rows(repo_root / DEV_BINARY_SUMMARY_PATH)
    map_rows = load_csv_rows(repo_root / DEV_MAP_SUMMARY_PATH)
    source_audit = gate_source_audit_records()
    write_json(results_dir / "gate_source_audit.json", {"schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION, "rows": source_audit})
    source_audit_hash = canonical_json_hash({"rows": source_audit})

    gates = build_confirmatory_gates(protocol_v2)
    protocol_v3 = build_protocol_v3(protocol_v2, gates, source_audit_hash)
    protocol_v3_hash = canonical_json_hash(protocol_v3)
    protocol_diff = build_protocol_diff(protocol_v2, protocol_v3)
    calibration = build_development_gate_calibration(protocol_v3, gates, binary_rows, map_rows)
    dry_runs = build_synthetic_cases(protocol_v3, gates)
    validator = validate_protocol_v3(repo_root, protocol_v2=protocol_v2, protocol_v3=protocol_v3, gates=gates, protocol_diff=protocol_diff)

    environment = {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": current_git_commit(repo_root),
        "timestamp_utc": utc_now_iso(),
        "benchmark_execution_invoked": False,
    }
    analysis = {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "completion_verdict": validator["validator_verdict"],
        "ready_verdict": LEVEL3_5B_GATE_READY_VERDICT if validator["validator_verdict"] == LEVEL3_5B_GATE_COMPLETION_VERDICT else None,
        "heldout_trials_observed": 0,
        "heldout_outcomes_available_to_gate_design": False,
        "v2_protocol_hash": PROTOCOL_V2_CANONICAL_HASH,
        "v3_protocol_hash": protocol_v3_hash,
        "benchmark_execution_invoked": False,
        "gate_ids": [gate["id"] for gate in gates],
        "newly_defined_gate_ids": [
            gate["id"]
            for gate in gates
            if gate["source_provenance"]["rule_origin"] == RULE_ORIGIN_NEW
        ],
        "recovered_gate_ids": [
            gate["id"]
            for gate in gates
            if gate["source_provenance"]["rule_origin"] == RULE_ORIGIN_RECOVERED
        ],
    }

    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "development_gate_calibration.json", calibration)
    write_json(results_dir / "heldout_protocol_v3.json", protocol_v3)
    write_json(results_dir / "protocol_v2_to_v3_diff.json", protocol_diff)
    write_json(results_dir / "validator_result.json", validator)
    write_json(results_dir / "synthetic_dry_run_results.json", {"schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION, "rows": dry_runs})
    write_json(results_dir / "analysis.json", analysis)

    render_gate_spec_doc(repo_root, analysis, protocol_v3_hash, source_audit)

    return {
        "schema_version": LEVEL3_5B_GATE_SPEC_SCHEMA_VERSION,
        "completion_verdict": validator["validator_verdict"],
        "ready_verdict": analysis["ready_verdict"],
        "protocol_v3_hash": protocol_v3_hash,
    }
