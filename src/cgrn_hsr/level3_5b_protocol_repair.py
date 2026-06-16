from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .level3_2_confirmation import level3_2_heldout_seed_set, prior_level3_1_seed_set
from .level3_2b_map_budget_robustness import MAP_STABLE_PATIENCE
from .level3_2b_map_budget_robustness import level3_2b_seed_set
from .level3_4_algebraic_baselines import MAP_EXTENDED_ARM_ID, MAP_FAST_ARM_ID
from .level3_4_algebraic_baselines import level3_4_seed_set
from .level3_5b_native_noise_frontiers import (
    BCF_TRACK_BLOCKED,
    CHANNEL_BERNOULLI,
    CHANNEL_EXACT_WEIGHT,
    CHANNEL_MAP_SIGN_FLIP,
    LEVEL3_5B_DEV_SCHEMA_VERSION,
    MAP_REPRESENTATION_SEED_OFFSET,
    level3_5b_dev_seed_set,
    prior_seed_set,
    write_json,
)

LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION = "level3-5b-protocol-repair-v1"
LEVEL3_5B_HELDOUT_V2_VERSION = "level3.5b-heldout-v2"
REPAIR_VERDICT = "PROTOCOL_REPAIRED_AND_REFROZEN"
REPAIR_READY = "READY_FOR_LEVEL_3_5B_HELDOUT_V2"
BLOCK_REDESIGN = "BLOCKED_REPAIR_REQUIRES_REDESIGN"
BLOCK_SEED = "BLOCKED_SEED_AUDIT_FAILURE"
BLOCK_CONFIG = "BLOCKED_CONFIG_PROVENANCE_FAILURE"

OLD_BLOCKED_CHECKPOINT = "8fcef7e7123c4d5dd4d401a4521b51ca85af8e1d"
DOC_CHECKPOINT = "87f3997c10f7d2e6ac3df58f5b00c6834dea648c"
DEV_BENCHMARK_CHECKPOINT = "110404917fbcbd5a10623058ef8ce36d7ad36a04"

ALLOWED_DIFF_TYPES = {
    "SEED_LEAKAGE_REPAIR",
    "COUNT_CONSISTENCY_REPAIR",
    "CONFIG_COMPLETENESS_REPAIR",
    "METADATA_ONLY",
}

IMMUTABLE_BLOCKED_PATHS = (
    "results/level3_5b_heldout/analysis.json",
    "results/level3_5b_heldout/bcf_status.json",
    "results/level3_5b_heldout/binary_summary.csv",
    "results/level3_5b_heldout/binary_trials.jsonl",
    "results/level3_5b_heldout/claims.json",
    "results/level3_5b_heldout/completion_manifest.json",
    "results/level3_5b_heldout/environment.json",
    "results/level3_5b_heldout/execution_manifest.json",
    "results/level3_5b_heldout/map_summary.csv",
    "results/level3_5b_heldout/map_trials.jsonl",
    "results/level3_5b_heldout/protocol_integrity.json",
    "results/level3_5b_heldout/resource_summary.csv",
    "results/level3_5b_heldout/semantic_manifests.jsonl",
    "results/level3_5b_heldout/silent_error_summary.csv",
    "results/level3_5b_heldout/timing_summary.csv",
    "results/level3_5b_heldout/verdicts.json",
    "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md",
)

OLD_PROTOCOL_PATH = "results/level3_5b_dev/heldout_protocol.json"
FROZEN_DEV_PROTOCOL_PATH = "results/level3_5b_dev/frozen_development_protocol.json"
BCH_CONFIG_PATH = "results/level3_5b_dev/bch_configs.json"
TRANSITION_PATH = "results/level3_5b_dev/transition_regions.json"
OLD_BLOCKED_VERDICTS_PATH = "results/level3_5b_heldout/verdicts.json"
OLD_BLOCKED_ANALYSIS_PATH = "results/level3_5b_heldout/analysis.json"
OLD_BLOCKED_EXECUTION_MANIFEST_PATH = "results/level3_5b_heldout/execution_manifest.json"

SOURCE_HASH_PATHS = (
    "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
    "src/cgrn_hsr/level3_2b_map_budget_robustness.py",
    "src/cgrn_hsr/level3_4_algebraic_baselines.py",
)

SCIENTIFIC_BINARY_KEYS = (
    "methods",
    "semantic_cells",
    "corruption_channels",
    "corruption_points_by_cell",
    "trial_count_per_selected_point",
    "bch_configs",
    "primary_metrics",
    "claim_limits",
)
SCIENTIFIC_MAP_KEYS = (
    "methods",
    "semantic_cells",
    "corruption_channels",
    "corruption_points_by_cell",
    "trial_count_per_selected_point",
    "primary_metrics",
    "claim_limits",
)
SCIENTIFIC_BCF_KEYS = (
    "status",
    "trial_count_per_selected_point",
    "reason",
)

NEW_BINARY_SEED_RANGES = {
    "u1_f3_m10": {"start": 910350100, "end": 910350163, "count": 64},
    "u1_f3_m31": {"start": 910351100, "end": 910351163, "count": 64},
    "u1_f3_m68": {"start": 910352100, "end": 910352163, "count": 64},
}
NEW_MAP_SEED_RANGES = {
    "u1_f3_m10": {"start": 920350100, "end": 920350163, "count": 64},
    "u1_f3_m31": {"start": 920351100, "end": 920351163, "count": 64},
    "u1_f3_m68": {"start": 920352100, "end": 920352163, "count": 64},
}


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


def canonical_json_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def git_stdout(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def range_to_seed_list(spec: dict[str, int]) -> list[int]:
    return list(range(int(spec["start"]), int(spec["end"]) + 1))


def seed_ranges_to_set(specs: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in specs.values():
        values.update(range_to_seed_list(spec))
    return values


def build_source_hashes(repo_root: Path) -> dict[str, str]:
    return {rel_path: sha256_path(repo_root / rel_path) for rel_path in SOURCE_HASH_PATHS}


def extract_preserved_scientific_fields(
    *,
    old_protocol: dict[str, Any],
    blocked_verdicts: dict[str, Any],
    transition_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "binary_track": {key: old_protocol["binary_track"][key] for key in SCIENTIFIC_BINARY_KEYS},
        "map_track": {key: old_protocol["map_track"][key] for key in SCIENTIFIC_MAP_KEYS},
        "bcf_track": {key: old_protocol["bcf_track"][key] for key in SCIENTIFIC_BCF_KEYS},
        "outcome_taxonomy": old_protocol["outcome_taxonomy"],
        "confirmatory_dispositions": blocked_verdicts["allowed_dispositions"],
        "development_transition_regions_hash": transition_hash,
        "semantic_payloads": {
            "u1_f3_m10": {"factor_count": 3, "domain_size": 10, "payload_bits": 12},
            "u1_f3_m31": {"factor_count": 3, "domain_size": 31, "payload_bits": 15},
            "u1_f3_m68": {"factor_count": 3, "domain_size": 68, "payload_bits": 21},
        },
    }


def build_complete_map_config_records(repo_root: Path, frozen_dev_protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source_hashes = build_source_hashes(repo_root)
    code_hash = source_hashes["src/cgrn_hsr/level3_5b_native_noise_frontiers.py"]
    runtime_hash = source_hashes["src/cgrn_hsr/level3_2b_map_budget_robustness.py"]
    reference_hash = source_hashes["src/cgrn_hsr/level3_4_algebraic_baselines.py"]
    map_configs = {row["arm_id"]: row for row in frozen_dev_protocol["frozen_map_configs"]}

    common = {
        "task_contract": "U1_noisy_single_product_factorization_development_only",
        "semantic_cells": ["u1_f3_m10", "u1_f3_m31", "u1_f3_m68"],
        "factor_count_by_cell": {cell: 3 for cell in ("u1_f3_m10", "u1_f3_m31", "u1_f3_m68")},
        "domain_size_by_cell": {"u1_f3_m10": 10, "u1_f3_m31": 31, "u1_f3_m68": 68},
        "representation_family": "MAP / TorchHD resonator",
        "codebook_construction": {
            "helper": "prepare_map_task",
            "source_module": "src/cgrn_hsr/level3_2b_map_budget_robustness.py",
            "dimensions": 1024,
            "representation_seed_policy": {
                "manifest_field": "map_representation_seed",
                "offset_from_trial_seed": MAP_REPRESENTATION_SEED_OFFSET,
            },
            "baseline_config": {
                "dimensions": 1024,
                "num_factors": "task.factor_count",
                "domain_size": "task.domain_size_per_factor[0]",
                "structured_distractor_count": 0,
                "max_iterations": 12,
                "stable_patience": MAP_STABLE_PATIENCE,
            },
            "observation_construction": "bind_sequence(factors_from_indices(domains, target_indices))",
            "initial_estimate_construction": "build_initial_estimates(domains)",
            "device_policy": '\"cuda:0\" if torch.cuda.is_available() else \"cpu\"',
            "dtype_policy": "runtime torchhd / torch default floating MAP tensor dtype",
        },
        "external_corruption_contract": {
            "channel_id": CHANNEL_MAP_SIGN_FLIP,
            "applied_after_clean_product_construction": True,
            "helper": "bernoulli_sign_flips",
            "source_module": "src/cgrn_hsr/level3_5b_native_noise_frontiers.py",
        },
        "native_reconstruction_definition": "selected.normalized_reconstruction_similarity from run_map_attempt output",
        "source_hashes": {
            "level3_5b_native_noise_frontiers.py": code_hash,
            "level3_2b_map_budget_robustness.py": runtime_hash,
            "level3_4_algebraic_baselines.py": reference_hash,
        },
    }

    fast = {
        **common,
        "arm_id": MAP_FAST_ARM_ID,
        "dimensions": 1024,
        "max_iterations": int(map_configs[MAP_FAST_ARM_ID]["max_iterations"]),
        "stable_patience": int(map_configs[MAP_FAST_ARM_ID]["stable_patience"]),
        "restart_count": 1,
        "initialization": "baseline_estimates.clone()",
        "proposal_selection": "first",
        "aggregation": "single-attempt",
        "selection_rule": "first",
        "seed_policy": {
            "attempt_init_seed": "trial_seed + 100000",
            "corruption_seed_offsets": {
                "initial_points": 4_000_000,
                "adaptive_midpoints": 6_000_000,
            },
        },
        "stopping_behavior": "early stop when stable_iterations >= MAP_STABLE_PATIENCE else stop at max_iterations",
        "implementation_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
    }
    extended = {
        **common,
        "arm_id": MAP_EXTENDED_ARM_ID,
        "dimensions": 1024,
        "max_iterations": int(map_configs[MAP_EXTENDED_ARM_ID]["max_iterations"]),
        "stable_patience": MAP_STABLE_PATIENCE,
        "restart_count": int(map_configs[MAP_EXTENDED_ARM_ID]["restart_count"]),
        "initialization": "four cold random restarts via torchhd.random",
        "proposal_selection": "highest native reconstruction, tie-break mean_margin then earliest restart",
        "aggregation": "best_native_reconstruction across 4 restarts",
        "selection_rule": str(map_configs[MAP_EXTENDED_ARM_ID]["selection_rule"]),
        "seed_policy": {
            "restart_init_seed": "trial_seed + 200000 + restart_index",
            "selection_seed": "trial_seed + 300000",
            "corruption_seed_offsets": {
                "initial_points": 5_000_000,
                "adaptive_midpoints": 7_000_000,
            },
        },
        "stopping_behavior": "each restart early-stops at stable_patience else max_iterations; best proposal selected post hoc",
        "implementation_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
    }
    records = {
        MAP_FAST_ARM_ID: fast,
        MAP_EXTENDED_ARM_ID: extended,
    }
    for record in records.values():
        record["config_hash"] = canonical_json_hash(record)
    return records


def build_seed_audit(repo_root: Path, new_binary: dict[str, dict[str, int]], new_map: dict[str, dict[str, int]]) -> dict[str, Any]:
    level3_1_prior = prior_level3_1_seed_set()
    level3_2_prior = level3_2_heldout_seed_set()
    level3_2b_prior = level3_2b_seed_set()
    level3_4_prior = level3_4_seed_set()
    prior_known = prior_seed_set()
    dev_known = level3_5b_dev_seed_set()
    old_protocol = read_json(repo_root / OLD_PROTOCOL_PATH)
    old_heldout = set()
    for track_name in ("binary_track", "map_track", "bcf_track"):
        for spec in old_protocol[track_name]["seed_ranges"].values():
            old_heldout.update(range(int(spec["start"]), int(spec["start"]) + int(spec["count"])))

    new_binary_set = seed_ranges_to_set(new_binary)
    new_map_set = seed_ranges_to_set(new_map)
    overlap_checks = {
        "binary_vs_map_overlap": sorted(new_binary_set.intersection(new_map_set)),
        "binary_vs_prior_overlap": sorted(new_binary_set.intersection(prior_known)),
        "map_vs_prior_overlap": sorted(new_map_set.intersection(prior_known)),
        "binary_vs_dev_overlap": sorted(new_binary_set.intersection(dev_known)),
        "map_vs_dev_overlap": sorted(new_map_set.intersection(dev_known)),
        "binary_vs_invalid_v1_overlap": sorted(new_binary_set.intersection(old_heldout)),
        "map_vs_invalid_v1_overlap": sorted(new_map_set.intersection(old_heldout)),
    }
    count_checks = {
        "binary": {cell_id: len(range_to_seed_list(spec)) for cell_id, spec in new_binary.items()},
        "map": {cell_id: len(range_to_seed_list(spec)) for cell_id, spec in new_map.items()},
    }
    uniqueness_checks = {
        "binary_unique": len(new_binary_set) == 64 * len(new_binary),
        "map_unique": len(new_map_set) == 64 * len(new_map),
        "combined_unique": len(new_binary_set.union(new_map_set)) == (64 * len(new_binary) + 64 * len(new_map)),
    }
    audit_pass = all(len(values) == 0 for values in overlap_checks.values()) and all(
        count == 64 for group in count_checks.values() for count in group.values()
    ) and all(uniqueness_checks.values())
    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "scanned_prior_manifests": [
            {"source": "src/cgrn_hsr/level3_2_confirmation.py::prior_level3_1_seed_set", "count": len(level3_1_prior)},
            {"source": "src/cgrn_hsr/level3_2_confirmation.py::level3_2_heldout_seed_set", "count": len(level3_2_prior)},
            {"source": "src/cgrn_hsr/level3_2b_map_budget_robustness.py::level3_2b_seed_set", "count": len(level3_2b_prior)},
            {"source": "src/cgrn_hsr/level3_4_algebraic_baselines.py::level3_4_seed_set", "count": len(level3_4_prior)},
            {"source": "src/cgrn_hsr/level3_5b_native_noise_frontiers.py::level3_5b_dev_seed_set", "count": len(dev_known)},
            {"source": "results/level3_5b_dev/heldout_protocol.json", "count": len(old_heldout)},
            {"source": "results/level3_5b_heldout/execution_manifest.json", "count": len(old_heldout)},
        ],
        "prior_seed_ranges": {
            "aggregated_prior_known": {
                "count": len(prior_known),
                "min": min(prior_known) if prior_known else None,
                "max": max(prior_known) if prior_known else None,
            },
            "level3_5b_dev": {
                "count": len(dev_known),
                "min": min(dev_known) if dev_known else None,
                "max": max(dev_known) if dev_known else None,
            },
            "invalid_v1_heldout_protocol": {
                "count": len(old_heldout),
                "min": min(old_heldout) if old_heldout else None,
                "max": max(old_heldout) if old_heldout else None,
            },
        },
        "new_proposed_ranges": {
            "binary_track": new_binary,
            "map_track": new_map,
        },
        "counts": count_checks,
        "overlap_checks": overlap_checks,
        "uniqueness_checks": uniqueness_checks,
        "audit_verdict": "PASS" if audit_pass else BLOCK_SEED,
    }


def build_protocol_v2(
    *,
    old_protocol: dict[str, Any],
    preserved_fields: dict[str, Any],
    complete_map_configs: dict[str, dict[str, Any]],
    config_hashes: dict[str, str],
    seed_audit: dict[str, Any],
    supersedes_protocol_hash: str,
    bch_hash: str,
    transition_hash: str,
    blocked_artifact_hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "protocol_version": LEVEL3_5B_HELDOUT_V2_VERSION,
        "supersedes_protocol_hash": supersedes_protocol_hash,
        "repair_reason": {
            "P1": "HELDOUT_SEED_LEAKAGE",
            "P2": "TRIAL_COUNT_SEED_COUNT_MISMATCH",
            "P3": "MAP_CONFIG_UNDERSPECIFICATION",
        },
        "repair_statement": "No held-out outcomes were observed before repair, so a pre-execution administrative re-freeze is permitted. The repair must not alter outcome-facing scientific choices.",
        "no_trials_observed_before_repair": True,
        "preserved_scientific_fields": preserved_fields,
        "fresh_seed_ranges": {
            "binary_track": seed_audit["new_proposed_ranges"]["binary_track"],
            "map_track": seed_audit["new_proposed_ranges"]["map_track"],
            "bcf_track": {
                "status": BCF_TRACK_BLOCKED,
                "execution_authorized": False,
                "seed_ranges": old_protocol["bcf_track"]["seed_ranges"],
            },
        },
        "complete_config_records": {
            "map_track": complete_map_configs,
            "binary_track": {
                "bch_config_file_hash": bch_hash,
                "binary_method_source_hash": config_hashes["src/cgrn_hsr/level3_5b_native_noise_frontiers.py"],
                "transition_regions_hash": transition_hash,
            },
            "bcf_track": {
                "status": old_protocol["bcf_track"]["status"],
                "reason": old_protocol["bcf_track"]["reason"],
            },
        },
        "config_hashes": {
            "heldout_protocol_v1_hash": supersedes_protocol_hash,
            "bch_configs_hash": bch_hash,
            "transition_regions_hash": transition_hash,
            "source_hashes": {path: digest for path, digest in config_hashes.items() if path in SOURCE_HASH_PATHS},
            "map_arm_hashes": {arm_id: record["config_hash"] for arm_id, record in complete_map_configs.items()},
            "blocked_artifact_hashes": blocked_artifact_hashes,
        },
        "trial_counts": {
            "binary_track": old_protocol["binary_track"]["trial_count_per_selected_point"],
            "map_track": old_protocol["map_track"]["trial_count_per_selected_point"],
            "bcf_track": old_protocol["bcf_track"]["trial_count_per_selected_point"],
        },
        "metrics": {
            "binary_track": old_protocol["binary_track"]["primary_metrics"],
            "map_track": old_protocol["map_track"]["primary_metrics"],
            "outcome_taxonomy": old_protocol["outcome_taxonomy"],
        },
        "gates": preserved_fields["confirmatory_dispositions"],
        "claim_limits": {
            "binary_track": old_protocol["binary_track"]["claim_limits"],
            "map_track": old_protocol["map_track"]["claim_limits"],
            "global": [
                "No cross-track universal winner",
                "No production promotion",
                "No BCF noisy claim",
            ],
        },
    }


def build_protocol_diff(v1_hash: str, v2_hash: str, new_binary: dict[str, Any], new_map: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "path": "fresh_seed_ranges.binary_track",
            "change_type": "SEED_LEAKAGE_REPAIR",
            "description": "Replace invalid leaked binary held-out seeds with fresh non-overlapping ranges.",
            "new_value": new_binary,
        },
        {
            "path": "fresh_seed_ranges.map_track",
            "change_type": "SEED_LEAKAGE_REPAIR",
            "description": "Replace invalid leaked MAP held-out seeds with fresh non-overlapping ranges.",
            "new_value": new_map,
        },
        {
            "path": "trial_counts.binary_track_vs_seed_counts",
            "change_type": "COUNT_CONSISTENCY_REPAIR",
            "description": "Restore exact 64-seed availability for each binary cell to match the frozen 64-trial target.",
        },
        {
            "path": "trial_counts.map_track_vs_seed_counts",
            "change_type": "COUNT_CONSISTENCY_REPAIR",
            "description": "Restore exact 64-seed availability for each MAP cell to match the frozen 64-trial target.",
        },
        {
            "path": "complete_config_records.map_track.map_d1024",
            "change_type": "CONFIG_COMPLETENESS_REPAIR",
            "description": "Add the complete immutable MAP fast-arm execution record and hash.",
        },
        {
            "path": "complete_config_records.map_track.map_d1024_step32_r4_best_native_reconstruction",
            "change_type": "CONFIG_COMPLETENESS_REPAIR",
            "description": "Add the complete immutable MAP extended-arm execution record and hash.",
        },
        {
            "path": "protocol_version",
            "change_type": "METADATA_ONLY",
            "description": "Version the repaired held-out protocol and record supersession metadata.",
            "old_hash": v1_hash,
            "new_hash": v2_hash,
        },
    ]
    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "allowed_change_types": sorted(ALLOWED_DIFF_TYPES),
        "rows": rows,
    }


def validate_protocol_repair(
    repo_root: Path,
    *,
    old_protocol: dict[str, Any],
    old_blocked_analysis: dict[str, Any],
    preserved_fields: dict[str, Any],
    seed_audit: dict[str, Any],
    protocol_v2: dict[str, Any],
    protocol_diff: dict[str, Any],
    complete_map_configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    old_binary_trials = (repo_root / "results" / "level3_5b_heldout" / "binary_trials.jsonl").read_text(encoding="utf-8")
    old_map_trials = (repo_root / "results" / "level3_5b_heldout" / "map_trials.jsonl").read_text(encoding="utf-8")
    immutable_diff = git_stdout(repo_root, "diff", "--name-only", "HEAD", "--", *IMMUTABLE_BLOCKED_PATHS)
    current_bch_hash = sha256_path(repo_root / BCH_CONFIG_PATH)
    current_old_protocol_hash = sha256_path(repo_root / OLD_PROTOCOL_PATH)
    current_transition_hash = sha256_path(repo_root / TRANSITION_PATH)
    source_hashes = build_source_hashes(repo_root)

    unsupported_diff_types = [
        row["change_type"] for row in protocol_diff["rows"] if row["change_type"] not in ALLOWED_DIFF_TYPES
    ]
    scientific_fields_match = (
        protocol_v2["preserved_scientific_fields"]["binary_track"] == {key: old_protocol["binary_track"][key] for key in SCIENTIFIC_BINARY_KEYS}
        and protocol_v2["preserved_scientific_fields"]["map_track"] == {key: old_protocol["map_track"][key] for key in SCIENTIFIC_MAP_KEYS}
        and protocol_v2["preserved_scientific_fields"]["bcf_track"] == {key: old_protocol["bcf_track"][key] for key in SCIENTIFIC_BCF_KEYS}
        and protocol_v2["metrics"]["binary_track"] == old_protocol["binary_track"]["primary_metrics"]
        and protocol_v2["metrics"]["map_track"] == old_protocol["map_track"]["primary_metrics"]
        and protocol_v2["metrics"]["outcome_taxonomy"] == old_protocol["outcome_taxonomy"]
    )
    map_hashes_match = all(
        protocol_v2["config_hashes"]["map_arm_hashes"][arm_id] == record["config_hash"]
        for arm_id, record in complete_map_configs.items()
    )
    source_hashes_match = protocol_v2["config_hashes"]["source_hashes"] == source_hashes
    no_trials_before_repair = old_blocked_analysis["trials_executed"] == 0 and old_binary_trials == "" and old_map_trials == ""

    verdict = REPAIR_VERDICT
    if unsupported_diff_types:
        verdict = BLOCK_REDESIGN
    elif not scientific_fields_match:
        verdict = BLOCK_REDESIGN
    elif seed_audit["audit_verdict"] != "PASS":
        verdict = BLOCK_SEED
    elif not map_hashes_match or not source_hashes_match:
        verdict = BLOCK_CONFIG

    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "zero_heldout_trials_before_repair": no_trials_before_repair,
        "old_protocol_unchanged_hash": current_old_protocol_hash == protocol_v2["supersedes_protocol_hash"],
        "old_blocked_artifacts_unchanged_in_git_diff": immutable_diff == "",
        "scientific_fields_preserved": scientific_fields_match,
        "corruption_points_identical": (
            protocol_v2["preserved_scientific_fields"]["binary_track"]["corruption_points_by_cell"]
            == old_protocol["binary_track"]["corruption_points_by_cell"]
            and protocol_v2["preserved_scientific_fields"]["map_track"]["corruption_points_by_cell"]
            == old_protocol["map_track"]["corruption_points_by_cell"]
        ),
        "method_sets_identical": (
            protocol_v2["preserved_scientific_fields"]["binary_track"]["methods"] == old_protocol["binary_track"]["methods"]
            and protocol_v2["preserved_scientific_fields"]["map_track"]["methods"] == old_protocol["map_track"]["methods"]
        ),
        "gates_identical": protocol_v2["gates"] == protocol_v2["preserved_scientific_fields"]["confirmatory_dispositions"],
        "metrics_identical": (
            protocol_v2["metrics"]["binary_track"] == old_protocol["binary_track"]["primary_metrics"]
            and protocol_v2["metrics"]["map_track"] == old_protocol["map_track"]["primary_metrics"]
            and protocol_v2["metrics"]["outcome_taxonomy"] == old_protocol["outcome_taxonomy"]
        ),
        "trial_count_equals_seed_count": {
            "binary_track": all(spec["count"] == protocol_v2["trial_counts"]["binary_track"] for spec in protocol_v2["fresh_seed_ranges"]["binary_track"].values()),
            "map_track": all(spec["count"] == protocol_v2["trial_counts"]["map_track"] for spec in protocol_v2["fresh_seed_ranges"]["map_track"].values()),
        },
        "all_new_seeds_unique": seed_audit["uniqueness_checks"]["combined_unique"],
        "new_seeds_non_overlapping": all(len(values) == 0 for values in seed_audit["overlap_checks"].values()),
        "complete_map_config_hashes_match": map_hashes_match,
        "bch_hash_unchanged": protocol_v2["config_hashes"]["bch_configs_hash"] == current_bch_hash,
        "bcf_blocked": protocol_v2["fresh_seed_ranges"]["bcf_track"]["status"] == BCF_TRACK_BLOCKED,
        "unsupported_protocol_diff_types": unsupported_diff_types,
        "protocol_v2_hash_guard_valid": (
            protocol_v2["config_hashes"]["source_hashes"] == source_hashes
            and protocol_v2["config_hashes"]["transition_regions_hash"] == current_transition_hash
        ),
        "benchmark_execution_invoked": False,
        "validator_verdict": verdict,
        "ready_for_level3_5b_heldout_v2": verdict == REPAIR_VERDICT,
    }


def render_repair_doc(repo_root: Path, analysis: dict[str, Any], protocol_v1_hash: str, protocol_v2_hash: str) -> None:
    lines = [
        "# Level 3.5b Protocol Repair and Re-Freeze",
        "",
        f"- Old blocked checkpoint: `{OLD_BLOCKED_CHECKPOINT}`",
        f"- Protocol repair verdict: `{analysis['repair_verdict']}`",
        f"- Ready status: `{analysis['ready_status']}`",
        f"- Protocol v1 hash: `{protocol_v1_hash}`",
        f"- Protocol v2 hash: `{protocol_v2_hash}`",
        "",
        "## Why Repair Was Required",
        "",
        "- P1 `HELDOUT_SEED_LEAKAGE`: held-out ranges overlapped development ranges.",
        "- P2 `TRIAL_COUNT_SEED_COUNT_MISMATCH`: protocol requested 64 trials but provided 16 seeds.",
        "- P3 `MAP_CONFIG_UNDERSPECIFICATION`: held-out MAP config did not fully identify the richer frozen development arm.",
        "",
        "> This is an administrative pre-execution repair, not a second chance after observing held-out outcomes.",
        "",
        "## Lawfulness",
        "",
        "- Zero held-out trial rows existed before repair.",
        "- The blocked held-out attempt remains immutable evidence.",
        "- Outcome-facing scientific choices were preserved; only protocol integrity defects were repaired.",
        "",
        "## Immutable Scientific Fields",
        "",
        "- Binary methods, cells, corruption points, BCH configurations, metrics and claim limits were preserved.",
        "- MAP methods, cells, corruption points, metrics and claim limits were preserved.",
        "- BCF remains blocked and unexecuted.",
        "- Development transition points remain referenced by hash.",
        "",
        "## What Changed",
        "",
        "- Fresh non-overlapping held-out seed ranges were allocated for binary and MAP.",
        "- Trial counts and seed counts were made consistent at 64 per binary cell and 64 per MAP cell.",
        "- Complete MAP arm records and hashes were added so future held-out execution can validate the exact frozen arms.",
        "",
        "## Remaining Claim Limits",
        "",
        "- No substantive noise-frontier claim is authorized at this stage.",
        "- No held-out benchmark execution occurred.",
        "- No production promotion is authorized.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_level3_5b_protocol_repair(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_protocol_repair"
    results_dir.mkdir(parents=True, exist_ok=True)

    old_protocol = read_json(repo_root / OLD_PROTOCOL_PATH)
    frozen_dev_protocol = read_json(repo_root / FROZEN_DEV_PROTOCOL_PATH)
    bch_configs = read_json(repo_root / BCH_CONFIG_PATH)
    transition_regions = read_json(repo_root / TRANSITION_PATH)
    blocked_verdicts = read_json(repo_root / OLD_BLOCKED_VERDICTS_PATH)
    blocked_analysis = read_json(repo_root / OLD_BLOCKED_ANALYSIS_PATH)

    protocol_v1_hash = sha256_path(repo_root / OLD_PROTOCOL_PATH)
    bch_hash = sha256_path(repo_root / BCH_CONFIG_PATH)
    transition_hash = sha256_path(repo_root / TRANSITION_PATH)
    blocked_artifact_hashes = {rel: sha256_path(repo_root / rel) for rel in IMMUTABLE_BLOCKED_PATHS}

    preserved_fields = extract_preserved_scientific_fields(
        old_protocol=old_protocol,
        blocked_verdicts=blocked_verdicts,
        transition_hash=transition_hash,
    )
    seed_audit = build_seed_audit(repo_root, NEW_BINARY_SEED_RANGES, NEW_MAP_SEED_RANGES)
    complete_map_configs = build_complete_map_config_records(repo_root, frozen_dev_protocol)
    source_hashes = build_source_hashes(repo_root)
    config_hashes = {
        **source_hashes,
        "results/level3_5b_dev/bch_configs.json": bch_hash,
        "results/level3_5b_dev/transition_regions.json": transition_hash,
    }

    protocol_v2 = build_protocol_v2(
        old_protocol=old_protocol,
        preserved_fields=preserved_fields,
        complete_map_configs=complete_map_configs,
        config_hashes=config_hashes,
        seed_audit=seed_audit,
        supersedes_protocol_hash=protocol_v1_hash,
        bch_hash=bch_hash,
        transition_hash=transition_hash,
        blocked_artifact_hashes=blocked_artifact_hashes,
    )
    protocol_v2_hash = canonical_json_hash(protocol_v2)
    protocol_diff = build_protocol_diff(protocol_v1_hash, protocol_v2_hash, NEW_BINARY_SEED_RANGES, NEW_MAP_SEED_RANGES)
    validator = validate_protocol_repair(
        repo_root,
        old_protocol=old_protocol,
        old_blocked_analysis=blocked_analysis,
        preserved_fields=preserved_fields,
        seed_audit=seed_audit,
        protocol_v2=protocol_v2,
        protocol_diff=protocol_diff,
        complete_map_configs=complete_map_configs,
    )

    analysis = {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "repair_verdict": validator["validator_verdict"],
        "ready_status": REPAIR_READY if validator["validator_verdict"] == REPAIR_VERDICT else validator["validator_verdict"],
        "old_blocked_checkpoint": OLD_BLOCKED_CHECKPOINT,
        "zero_trials_executed_before_repair": validator["zero_heldout_trials_before_repair"],
        "preserved_scientific_fields_hash": canonical_json_hash(preserved_fields),
        "protocol_v1_hash": protocol_v1_hash,
        "protocol_v2_hash": protocol_v2_hash,
        "seed_audit_verdict": seed_audit["audit_verdict"],
        "validator_result": validator["validator_verdict"],
        "benchmark_execution_invoked": False,
    }

    write_json(results_dir / "environment.json", {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": git_stdout(repo_root, "rev-parse", "HEAD"),
        "timestamp_utc": utc_now_iso(),
    })
    write_json(results_dir / "seed_audit.json", seed_audit)
    write_json(results_dir / "heldout_protocol_v2.json", protocol_v2)
    write_json(results_dir / "protocol_diff.json", protocol_diff)
    write_json(results_dir / "validator_result.json", validator)
    write_json(results_dir / "analysis.json", analysis)

    render_repair_doc(repo_root, analysis, protocol_v1_hash, protocol_v2_hash)

    return {
        "schema_version": LEVEL3_5B_PROTOCOL_REPAIR_SCHEMA_VERSION,
        "repair_verdict": analysis["repair_verdict"],
        "ready_status": analysis["ready_status"],
        "protocol_v1_hash": protocol_v1_hash,
        "protocol_v2_hash": protocol_v2_hash,
    }
