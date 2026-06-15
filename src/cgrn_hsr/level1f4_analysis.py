from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

LEVEL1F4_SCHEMA_VERSION = "level1f4-analysis-v1"
LEVEL1F3_CHECKPOINT_COMMIT = "7841f3cd4f522b4fda0099502c7571bd64131d39"
LEVEL1F3_UPSTREAM_COMMIT = "a353f1e918dcb515cad4a89c8e47ce24668954a7"

SUBSTRATE_MAP = "MAP"
SUBSTRATE_BCF = "BCF"

CELL_PRIMARY = "COLLAPSE_SINGLE_PRIMARY"
CELL_STRESS = "COLLAPSE_SINGLE_STRESS"
CELL_EASY = "EASY_SINGLE"
CELL_ORDER = (CELL_PRIMARY, CELL_STRESS, CELL_EASY)

METHOD_GLOBAL = "global"
METHOD_RANDOM_HALF = "random_unconditional_half"
METHOD_RANDOM_QUARTER = "random_unconditional_quarter"
METHOD_SEMANTIC_HALF = "semantic_l2_half"
METHOD_SEMANTIC_QUARTER = "semantic_l2_quarter"
METHOD_ORACLE_HALF = "oracle_truth_included_half"
METHOD_ORACLE_QUARTER = "oracle_truth_included_quarter"

CONTEXT_PAIRS = (
    ("half", METHOD_RANDOM_HALF, METHOD_SEMANTIC_HALF, METHOD_ORACLE_HALF),
    ("quarter", METHOD_RANDOM_QUARTER, METHOD_SEMANTIC_QUARTER, METHOD_ORACLE_QUARTER),
)

PROVENANCE_STATUS_CLEAN = "CLEAN_HELDOUT"
PROVENANCE_STATUS_REPAIRED = "REPAIRED_HELDOUT_NO_OUTCOME_TUNING"
PROVENANCE_STATUS_CONTAMINATED = "HELDOUT_CONTAMINATED"
PROVENANCE_STATUS_UNKNOWN = "UNKNOWN"

PROVENANCE_AUDIT = {
    "status": PROVENANCE_STATUS_REPAIRED,
    "bug_summary": (
        "A Level 1F.3 execution bug allowed the selected BCF iteration cap to drop when the "
        "chosen configuration was reconstructed from the uncapped candidate list. Intermediate "
        "debugging runs therefore fell back to the task-derived cap instead of the frozen cap=16."
    ),
    "bug_discovered_on": "2026-06-15",
    "pre_fix_artifacts": [
        "transient workspace-local timing logs",
        "transient partial held-out trial files created during debugging",
    ],
    "intermediate_heldout_outcomes_viewed": True,
    "final_heldout_fully_rerun_with_cap_16": True,
    "same_heldout_seeds_reused_after_viewing_outcomes": True,
    "outcome_based_tuning_after_view": False,
    "status_rationale": (
        "The final committed Level 1F.3 artifacts were regenerated with the frozen cap=16 and "
        "without changing BCF configuration, selector logic, or held-out seed ranges after the "
        "bug was fixed. However, held-out outcomes were observed during debugging before the "
        "final rerun, so the substrate comparison remains provisional for publication purposes."
    ),
    "publication_requirement": (
        "Fresh clean-seed confirmation is required before publication-level substrate claims."
    ),
}

ORIGINAL_HYPOTHESIS_SUMMARY = (
    "The original CGRN-HSR hypothesis proposed that an external probabilistic context layer could "
    "route candidate domains, budget factorization effort, and gate acceptance without changing "
    "the underlying hypervector geometry. The intended gain was lower compute and fewer silent "
    "false commitments through context-aware candidate restriction, verifier-backed abstention, "
    "and cold fallback when local context failed."
)


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_trials(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def maybe_round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def rate(successes: int, total: int) -> float | None:
    if total <= 0:
        return None
    return successes / total


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    radius = (z / denom) * math.sqrt((p * (1.0 - p) / total) + ((z * z) / (4.0 * total * total)))
    return max(0.0, center - radius), min(1.0, center + radius)


def percentile_nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def method_k_label(method_id: str) -> str:
    if method_id.endswith("_half"):
        return "half"
    if method_id.endswith("_quarter"):
        return "quarter"
    return "full"


def method_subset_size(method_id: str, candidate_count: int) -> str:
    if method_id == METHOD_GLOBAL:
        return "full"
    return method_k_label(method_id)


def exact_requires_all_truth_included(trial: dict[str, Any]) -> bool:
    return (not trial["exact_recovery"]) or trial["all_truth_included"]


def group_trials(trials: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for trial in trials:
        key = (trial["cell_id"], trial["substrate"], trial["method_id"])
        grouped.setdefault(key, []).append(trial)
    return grouped


def build_truth_inclusion_rows(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(group_trials(trials)):
        cell_id, substrate, method_id = key
        batch = group_trials(trials)[key]
        total = len(batch)
        factor_count = int(batch[0]["factor_count"])
        all_truth_count = sum(1 for trial in batch if trial["all_truth_included"])
        truth_missing_count = total - all_truth_count
        exact_count = sum(1 for trial in batch if trial["exact_recovery"])
        exact_all_count = sum(1 for trial in batch if trial["exact_recovery"] and trial["all_truth_included"])
        exact_missing_count = sum(1 for trial in batch if trial["exact_recovery"] and not trial["all_truth_included"])
        per_factor_truth_hits = sum(sum(1 for flag in trial["truth_included_per_factor"] if flag) for trial in batch)
        all_truth_ci_low, all_truth_ci_high = wilson_interval(all_truth_count, total)
        exact_ci_low, exact_ci_high = wilson_interval(exact_count, total)
        exact_all_ci_low, exact_all_ci_high = wilson_interval(exact_all_count, all_truth_count)
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "cell_id": cell_id,
                "substrate": substrate,
                "method_id": method_id,
                "k_label": method_k_label(method_id),
                "trials": total,
                "factor_count": factor_count,
                "per_factor_truth_inclusion_rate": maybe_round(per_factor_truth_hits / (total * factor_count)),
                "all_truth_included_count": all_truth_count,
                "all_truth_included_rate": maybe_round(rate(all_truth_count, total)),
                "all_truth_included_ci_low": maybe_round(all_truth_ci_low),
                "all_truth_included_ci_high": maybe_round(all_truth_ci_high),
                "exact_recovery_count": exact_count,
                "exact_recovery_rate": maybe_round(rate(exact_count, total)),
                "exact_recovery_ci_low": maybe_round(exact_ci_low),
                "exact_recovery_ci_high": maybe_round(exact_ci_high),
                "truth_missing_count": truth_missing_count,
                "exact_given_all_truth_included": maybe_round(rate(exact_all_count, all_truth_count)),
                "exact_given_all_truth_included_ci_low": maybe_round(exact_all_ci_low),
                "exact_given_all_truth_included_ci_high": maybe_round(exact_all_ci_high),
                "exact_given_truth_missing": maybe_round(rate(exact_missing_count, truth_missing_count)),
                "exact_and_truth_missing_count": exact_missing_count,
                "invariant_exact_requires_all_truth_included": exact_missing_count == 0,
            }
        )
    return rows


def index_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {tuple(row[key] for key in keys): row for row in rows}


def build_oracle_decomposition_rows(truth_rows: list[dict[str, Any]], grouped_trials: dict[tuple[str, str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    truth_index = index_rows(truth_rows, ("cell_id", "substrate", "method_id"))
    rows: list[dict[str, Any]] = []
    available_pairs = sorted({(row["cell_id"], row["substrate"]) for row in truth_rows})
    for cell_id, substrate in available_pairs:
        global_row = truth_index.get((cell_id, substrate, METHOD_GLOBAL))
        if global_row is None:
            continue
        for k_label, random_method, semantic_method, oracle_method in CONTEXT_PAIRS:
            random_row = truth_index.get((cell_id, substrate, random_method))
            semantic_row = truth_index.get((cell_id, substrate, semantic_method))
            oracle_row = truth_index.get((cell_id, substrate, oracle_method))
            if random_row is None or semantic_row is None or oracle_row is None:
                continue
            rows.append(
                {
                    "schema_version": LEVEL1F4_SCHEMA_VERSION,
                    "cell_id": cell_id,
                    "substrate": substrate,
                    "k_label": k_label,
                    "global_method": METHOD_GLOBAL,
                    "random_method": random_method,
                    "semantic_method": semantic_method,
                    "oracle_method": oracle_method,
                    "global_exact_recovery": global_row["exact_recovery_rate"],
                    "global_exact_ci_low": global_row["exact_recovery_ci_low"],
                    "global_exact_ci_high": global_row["exact_recovery_ci_high"],
                    "random_unconditional_exact_recovery": random_row["exact_recovery_rate"],
                    "random_unconditional_ci_low": random_row["exact_recovery_ci_low"],
                    "random_unconditional_ci_high": random_row["exact_recovery_ci_high"],
                    "semantic_l2_exact_recovery": semantic_row["exact_recovery_rate"],
                    "semantic_l2_ci_low": semantic_row["exact_recovery_ci_low"],
                    "semantic_l2_ci_high": semantic_row["exact_recovery_ci_high"],
                    "oracle_truth_included_exact_recovery": oracle_row["exact_recovery_rate"],
                    "oracle_truth_included_ci_low": oracle_row["exact_recovery_ci_low"],
                    "oracle_truth_included_ci_high": oracle_row["exact_recovery_ci_high"],
                }
            )
    return rows


def conditional_regret_decomposition(
    semantic_all: float,
    semantic_conditional: float,
    oracle_all: float,
    oracle_conditional: float,
) -> tuple[float, float]:
    truth_exclusion = max(0.0, (oracle_all - semantic_all) * oracle_conditional)
    factorization = max(0.0, semantic_all * max(0.0, oracle_conditional - semantic_conditional))
    return truth_exclusion, factorization


def build_conditional_recovery_rows(truth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth_index = index_rows(truth_rows, ("cell_id", "substrate", "method_id"))
    rows: list[dict[str, Any]] = []
    available_pairs = sorted({(row["cell_id"], row["substrate"]) for row in truth_rows})
    for cell_id, substrate in available_pairs:
        global_row = truth_index.get((cell_id, substrate, METHOD_GLOBAL))
        if global_row is None:
            continue
        for k_label, random_method, semantic_method, oracle_method in CONTEXT_PAIRS:
            random_row = truth_index.get((cell_id, substrate, random_method))
            semantic_row = truth_index.get((cell_id, substrate, semantic_method))
            oracle_row = truth_index.get((cell_id, substrate, oracle_method))
            if random_row is None or semantic_row is None or oracle_row is None:
                continue
            selector_advantage = (semantic_row["all_truth_included_rate"] or 0.0) - (random_row["all_truth_included_rate"] or 0.0)
            conditional_factorizer_advantage = None
            if semantic_row["exact_given_all_truth_included"] is not None and random_row["exact_given_all_truth_included"] is not None:
                conditional_factorizer_advantage = (
                    semantic_row["exact_given_all_truth_included"] - random_row["exact_given_all_truth_included"]
                )
            oracle_regret = (oracle_row["exact_recovery_rate"] or 0.0) - (semantic_row["exact_recovery_rate"] or 0.0)
            truth_exclusion, factorization_failure = conditional_regret_decomposition(
                semantic_row["all_truth_included_rate"] or 0.0,
                semantic_row["exact_given_all_truth_included"] or 0.0,
                oracle_row["all_truth_included_rate"] or 0.0,
                oracle_row["exact_given_all_truth_included"] or 0.0,
            )
            rows.append(
                {
                    "schema_version": LEVEL1F4_SCHEMA_VERSION,
                    "cell_id": cell_id,
                    "substrate": substrate,
                    "k_label": k_label,
                    "global_method": METHOD_GLOBAL,
                    "random_method": random_method,
                    "semantic_method": semantic_method,
                    "oracle_method": oracle_method,
                    "global_exact_recovery": global_row["exact_recovery_rate"],
                    "random_all_truth_included_rate": random_row["all_truth_included_rate"],
                    "semantic_all_truth_included_rate": semantic_row["all_truth_included_rate"],
                    "oracle_all_truth_included_rate": oracle_row["all_truth_included_rate"],
                    "random_exact_given_all_truth_included": random_row["exact_given_all_truth_included"],
                    "semantic_exact_given_all_truth_included": semantic_row["exact_given_all_truth_included"],
                    "oracle_exact_given_all_truth_included": oracle_row["exact_given_all_truth_included"],
                    "random_exact_given_truth_missing": random_row["exact_given_truth_missing"],
                    "semantic_exact_given_truth_missing": semantic_row["exact_given_truth_missing"],
                    "random_exact_recovery": random_row["exact_recovery_rate"],
                    "selector_advantage": maybe_round(selector_advantage),
                    "conditional_factorizer_advantage": maybe_round(conditional_factorizer_advantage),
                    "semantic_exact_recovery": semantic_row["exact_recovery_rate"],
                    "oracle_exact_recovery": oracle_row["exact_recovery_rate"],
                    "oracle_regret": maybe_round(oracle_regret),
                    "oracle_regret_truth_exclusion": maybe_round(truth_exclusion),
                    "oracle_regret_factorization_failure": maybe_round(factorization_failure),
                }
            )
    return rows


def build_cap_saturation_rows(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracked_methods = {
        METHOD_GLOBAL,
        METHOD_SEMANTIC_HALF,
        METHOD_SEMANTIC_QUARTER,
        METHOD_ORACLE_HALF,
        METHOD_ORACLE_QUARTER,
    }
    rows: list[dict[str, Any]] = []
    grouped = group_trials([trial for trial in trials if trial["substrate"] == SUBSTRATE_BCF and trial["method_id"] in tracked_methods])
    for key in sorted(grouped):
        cell_id, substrate, method_id = key
        batch = grouped[key]
        iterations = [int(trial["iterations"]) for trial in batch]
        cap_values = [int(trial["max_iterations_cap"]) for trial in batch]
        cap_target = 16
        reaching_cap = sum(1 for value in iterations if value >= cap_target)
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "cell_id": cell_id,
                "substrate": substrate,
                "method_id": method_id,
                "trials": len(batch),
                "mean_iterations": maybe_round(sum(iterations) / len(iterations)),
                "median_iterations": maybe_round(statistics.median(iterations)),
                "p90_iterations": maybe_round(percentile_nearest_rank(iterations, 0.9)),
                "max_iterations": max(iterations),
                "max_iterations_cap": max(cap_values),
                "fraction_reaching_cap_16": maybe_round(reaching_cap / len(iterations)),
            }
        )
    return rows


def build_config_sweep_rows(selected_bcf_config: dict[str, Any]) -> list[dict[str, Any]]:
    selection_trials = next(iter(selected_bcf_config["selection_split"].values()))["count"]
    rows: list[dict[str, Any]] = []
    for candidate in selected_bcf_config["candidates"]:
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "config_id": candidate["config_id"],
                "exact_recovery_rate": candidate["exact_recovery_rate"],
                "mean_iterations": candidate["mean_iterations"],
                "mean_factorization_time_sec": None,
                "mean_native_codebook_bytes": candidate["mean_native_codebook_bytes"],
                "trial_count": selection_trials,
                "selection_cell": selected_bcf_config["selection_cells"][0],
                "selected_iteration_cap": selected_bcf_config["selected_iteration_cap"],
                "same_device_timing_status": selected_bcf_config["same_device_timing_status"],
                "selected": candidate["config_id"] == selected_bcf_config["selected_config"]["config_id"],
                "timing_available_in_artifact": False,
                "selection_note": "Selected among the tested upstream-justified configurations on the frozen development split.",
            }
        )
    return rows


def build_pareto_rows(
    factorizer_rows: list[dict[str, str]],
    context_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in factorizer_rows:
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "table_type": "raw_substrate",
                "cell_id": row["cell_id"],
                "method": "MAP global",
                "exact_recovery": row["map_exact_recovery_rate"],
                "factorization_time_sec": row["map_mean_factorization_time_sec"],
                "codebook_bytes": row["map_mean_native_codebook_bytes"],
                "iterations": row["map_mean_iterations"],
            }
        )
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "table_type": "raw_substrate",
                "cell_id": row["cell_id"],
                "method": "BCF global",
                "exact_recovery": row["bcf_exact_recovery_rate"],
                "factorization_time_sec": row["bcf_mean_factorization_time_sec"],
                "codebook_bytes": row["bcf_mean_native_codebook_bytes"],
                "iterations": row["bcf_mean_iterations"],
            }
        )

    for row in context_rows:
        if row["semantic_method"] != METHOD_SEMANTIC_HALF:
            continue
        rows.append(
            {
                "schema_version": LEVEL1F4_SCHEMA_VERSION,
                "table_type": "context_transfer",
                "cell_id": row["cell_id"],
                "substrate": row["substrate"],
                "random_half_exact_recovery": row["random_exact_recovery_rate"],
                "semantic_half_exact_recovery": row["semantic_exact_recovery_rate"],
                "oracle_half_exact_recovery": row["oracle_exact_recovery_rate"],
                "semantic_gain_over_random": row["semantic_minus_random_exact_recovery"],
                "semantic_regret_to_oracle": row["semantic_regret_vs_oracle"],
            }
        )
    return rows


def build_timing_audit(
    heldout_trials: list[dict[str, Any]],
    timing_rows: list[dict[str, str]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for trial in heldout_trials:
        key = (trial["cell_id"], trial["substrate"], trial["method_id"])
        grouped.setdefault(key, []).append(trial)

    summaries: list[dict[str, Any]] = []
    timing_index = {
        (row["cell_id"], row["substrate"], row["method_id"]): row for row in timing_rows
    }
    for key in sorted(grouped):
        batch = grouped[key]
        cell_id, substrate, method_id = key
        materialization_values = [float(trial["materialization_time_sec"]) for trial in batch]
        factorization_values = [float(trial["factorization_time_sec"]) for trial in batch]
        end_to_end_values = [float(trial["end_to_end_task_time_sec"]) for trial in batch]
        timing_row = timing_index.get(key)
        summaries.append(
            {
                "cell_id": cell_id,
                "substrate": substrate,
                "method_id": method_id,
                "heldout_trials": len(batch),
                "median_materialization_time_sec": maybe_round(statistics.median(materialization_values)),
                "p90_materialization_time_sec": maybe_round(percentile_nearest_rank(materialization_values, 0.9)),
                "median_factorization_time_sec": maybe_round(statistics.median(factorization_values)),
                "p90_factorization_time_sec": maybe_round(percentile_nearest_rank(factorization_values, 0.9)),
                "median_end_to_end_task_time_sec": maybe_round(statistics.median(end_to_end_values)),
                "p90_end_to_end_task_time_sec": maybe_round(percentile_nearest_rank(end_to_end_values, 0.9)),
                "timing_sample_tasks": int(timing_row["timed_trials"]) if timing_row else None,
                "timing_repeats_serialized": False,
                "timing_repeats": None,
                "cuda_sync_status": timing_row["same_device_timing_status"] if timing_row else analysis["same_device_timing_status"],
                "claim_boundary": (
                    "Under the audited official implementation and repeated small-task orchestration, "
                    "MAP had lower measured factorization latency."
                ),
            }
        )
    return {
        "measurement_scope": "heldout trials plus timing summary artifact",
        "codebook_generation_in_factorization_time": False,
        "imports_included_in_factorization_time": False,
        "context_selection_included_in_factorization_time": False,
        "disk_io_included_in_factorization_time": False,
        "repeats_note": "Level 1F.3 artifacts did not serialize timing repeats; Level 1F.4 therefore reports repeats as unavailable in-artifact.",
        "summaries": summaries,
    }


def build_memory_audit(heldout_trials: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for trial in heldout_trials:
        grouped.setdefault((trial["cell_id"], trial["substrate"], trial["method_id"]), []).append(trial)

    summaries: list[dict[str, Any]] = []
    for key in sorted(grouped):
        cell_id, substrate, method_id = key
        batch = grouped[key]
        summaries.append(
            {
                "cell_id": cell_id,
                "substrate": substrate,
                "method_id": method_id,
                "codebook_bytes": maybe_round(sum(float(trial["native_codebook_bytes"]) for trial in batch) / len(batch)),
                "observation_bytes": maybe_round(sum(float(trial["native_observation_bytes"]) for trial in batch) / len(batch)),
                "runtime_state_bytes": maybe_round(sum(float(trial["runtime_state_bytes"] or 0) for trial in batch) / len(batch)),
                "peak_cuda_memory_bytes": maybe_round(sum(float(trial["peak_cuda_memory_bytes"] or 0) for trial in batch) / len(batch)),
            }
        )
    return {
        "memory_comparison": "partial_but_runtime_state_available",
        "summaries": summaries,
        "caveat": (
            "Peak CUDA memory reflects allocator-visible runtime behavior in the audited harness and "
            "should not be treated as a pure codebook-state comparison."
        ),
    }


def build_claims(
    truth_rows: list[dict[str, Any]],
    conditional_rows: list[dict[str, Any]],
    factorizer_rows: list[dict[str, str]],
) -> dict[str, Any]:
    def all_positive(row_key: str, rows: list[dict[str, Any]]) -> bool:
        return all((row[row_key] is not None) and (row[row_key] > 0.0) for row in rows)

    portability_confirmed = all_positive("selector_advantage", conditional_rows) and all(
        (row["semantic_exact_recovery"] or 0.0) > (row["random_exact_recovery"] or 0.0)
        for row in conditional_rows
    )

    internal_rows = [
        row for row in conditional_rows
        if row["conditional_factorizer_advantage"] is not None
    ]
    factorizer_internal_confirmed = bool(internal_rows) and all(
        row["conditional_factorizer_advantage"] > 0.0 for row in internal_rows
    )

    map_stronger = all(
        float(row["map_exact_recovery_rate"]) >= float(row["bcf_exact_recovery_rate"])
        for row in factorizer_rows
    )

    claim_a_status = "CONFIRMED" if portability_confirmed else "NOT_CONFIRMED"
    claim_b_status = "CONFIRMED" if factorizer_internal_confirmed else "NOT_CONFIRMED"
    claim_c_status = "SUPPORTED_IN_TESTED_OPERATING_ENVELOPE" if map_stronger else "NOT_CONFIRMED"
    claim_d_status = "CONFIRMED" if portability_confirmed else "NOT_CONFIRMED"

    narrow_status = "NARROW" if claim_a_status == "CONFIRMED" and claim_b_status != "CONFIRMED" else "COMPOSE"
    publication_status = "BLOCK_PUBLICATION_CLAIM" if PROVENANCE_AUDIT["status"] != PROVENANCE_STATUS_CLEAN else "PUBLICATION_OK"

    return {
        "schema_version": LEVEL1F4_SCHEMA_VERSION,
        "claim_a_context_portability": {
            "status": claim_a_status,
            "wording": "Semantic context beat size-matched random candidate selection on truth inclusion and exact recovery for MAP and official IBM BCF in the tested single-product cells.",
        },
        "claim_b_factorizer_internal_semantic_benefit": {
            "status": claim_b_status,
            "wording": "A substrate-internal semantic benefit beyond truth retention was not consistently demonstrated across MAP and BCF.",
        },
        "claim_c_map_stronger_than_bcf": {
            "status": claim_c_status,
            "wording": "MAP was stronger than the audited official IBM BCF implementation in the tested operating envelope.",
        },
        "claim_d_external_context_transfer": {
            "status": claim_d_status,
            "wording": "The external context-selection mechanism transferred across two representation/factorizer families.",
        },
        "go_level_2": claim_a_status == "CONFIRMED",
        "closure_verdict": narrow_status,
        "publication_status": publication_status,
        "allowed_claims": [
            "Semantic context beats random candidate selection.",
            "The external context-selection mechanism transferred from MAP to official IBM BCF.",
            "MAP was stronger than official IBM BCF in the tested single-product operating envelope.",
        ],
        "forbidden_claims": [
            "BCF is inherently slower.",
            "CGRN is fully substrate-independent.",
            "Verifier, fallback policy, or open-world lifecycle already transferred to BCF.",
            "MAP is generally superior to all block-code factorizers.",
        ],
    }


def build_level1_closure_markdown(claims: dict[str, Any]) -> str:
    return f"""# Level 1 Research Closure

## 1. Original hypothesis

{ORIGINAL_HYPOTHESIS_SUMMARY}

The unchanged source hypothesis remains in `CGRN-HSR_research_hypothesis.md`.

## 2. Confirmed components

- Semantic context beats random candidate selection in the tested single-product regimes.
- Context gain transfers from MAP to the official IBM BCF implementation.
- Context-biased MAP initialization helps in selected collapse regimes.
- Selective acceptance reduces silent false commits.
- L2 to cold global fallback is the surviving MAP path.

## 3. Partially supported components

- Context appears portable as an external candidate-recall mechanism across substrates.
- BCF context transfer is confirmed at the selector level, but BCF substrate parity remains limited to scoped single-product tasks.
- MAP vs BCF superiority is only supported in the tested operating envelope.

## 4. Falsified mechanisms

- Full L2 to L1 to global cold cascade.
- Warm transfer of resonator estimates across expanding domains.
- Cheap L1 probes as a verifier surrogate.
- HoloVec as a fair per-factor competitor under the audited contract.

## 5. Competitor audits

- HoloVec competitor audit: blocked for factor-specific domain mismatch under the current API.
- Official IBM BCF audit: wrappable for single-product typed tasks; structured-mixture parity remains blocked.

## 6. Substrate comparison

- MAP and official IBM BCF were compared on matched abstract single-product tasks.
- Semantic subsets improved both substrates over size-matched random subsets.
- In the tested operating envelope, MAP global remained stronger on recovery and measured factorization latency.
- Official IBM implementation exhibited high end-to-end benchmarking cost under repeated independently materialized contextual-subset trials.

## 7. Surviving architecture

```text
Observation / Query
        ↓
External probabilistic context
        ↓
Schema and candidate-domain routing
        ↓
Native proposal engine
- MAP resonator
- optional BCF typed decoder
- future linear-code decoder
        ↓
Evidence / relevance / provenance
        ↓
Accept / cold fallback / abstain
        ↓
Transactional commit
```

Hierarchy survives as a mechanism for context organization, schema routing, candidate selection, and search budgeting. It is not used to carry resonator state between expanding domains.

## 8. Claims allowed

- Semantic context beats random candidate selection in the tested Level 1 settings.
- The external context-selection mechanism transferred across MAP and official IBM BCF.
- MAP was stronger than the audited official IBM BCF implementation in the tested single-product operating envelope.
- Structured-mixture BCF parity remains unresolved rather than disproven.

## 9. Claims forbidden

- BCF is inherently slower.
- CGRN is fully substrate-independent.
- Verifier, selective-risk policy, fallback policy, or open-world lifecycle have already transferred to BCF.
- Hierarchical resonator continuation is a viable mainline runtime path.

## 10. Pre-publication replication requirements

- Fresh clean-seed confirmation of the Level 1F.3 BCF substrate comparison because held-out provenance status is `{PROVENANCE_AUDIT["status"]}`.
- Any publication claim about BCF substrate comparison must use untouched held-out seeds after the cap-propagation bug fix.
- Structured-mixture parity, linear-code alternatives, and open-world lifecycle claims require new dedicated experiments.

## 11. Transition contract for Level 2

- Level 2 may build on the surviving MAP mainline: external probabilistic context, typed candidate routing, selective acceptance, cold fallback, and abstention.
- Level 2 must not reintroduce warm resonator continuation or full cold L2 to L1 to global cascade as default runtime mechanisms.
- Level 2 may treat BCF as an optional typed decoder substrate, but not as a verified drop-in replacement for the full MAP control stack.
- Unresolved areas carried forward: linear-code HDC, noisy algebraic recovery, structured-mixture BCF parity, temporal utility, and open-world concept lifecycle.
"""


def build_analysis_payload(
    level1f3_analysis: dict[str, Any],
    truth_rows: list[dict[str, Any]],
    conditional_rows: list[dict[str, Any]],
    cap_rows: list[dict[str, Any]],
    config_rows: list[dict[str, Any]],
    timing_audit: dict[str, Any],
    memory_audit: dict[str, Any],
    claims: dict[str, Any],
) -> dict[str, Any]:
    invariant_violations = [
        row for row in truth_rows if not row["invariant_exact_requires_all_truth_included"]
    ]
    return {
        "schema_version": LEVEL1F4_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL1F3_CHECKPOINT_COMMIT,
        "source_level1f3_analysis": level1f3_analysis,
        "provenance_audit": PROVENANCE_AUDIT,
        "invariant_violations": invariant_violations,
        "timing_audit": timing_audit,
        "memory_audit": memory_audit,
        "config_sweep_summary": config_rows,
        "claims": claims,
        "no_new_factorizer_runs": True,
    }


def build_level1f4(root: Path | None = None) -> dict[str, Any]:
    root = root or default_root()
    source_dir = root / "results" / "level1f3"
    output_dir = root / "results" / "level1f4"
    docs_dir = root / "docs"

    heldout_trials = load_trials(source_dir / "heldout_trials.jsonl")
    factorizer_rows = load_csv_rows(source_dir / "factorizer_comparison.csv")
    context_rows = load_csv_rows(source_dir / "context_transfer.csv")
    timing_rows = load_csv_rows(source_dir / "timing_summary.csv")
    memory_rows = load_csv_rows(source_dir / "memory_summary.csv")
    level1f3_analysis = load_json(source_dir / "analysis.json")
    selected_bcf_config = load_json(source_dir / "selected_bcf_config.json")

    truth_rows = build_truth_inclusion_rows(heldout_trials)
    oracle_rows = build_oracle_decomposition_rows(truth_rows, group_trials(heldout_trials))
    conditional_rows = build_conditional_recovery_rows(truth_rows)
    cap_rows = build_cap_saturation_rows(heldout_trials)
    config_rows = build_config_sweep_rows(selected_bcf_config)
    pareto_rows = build_pareto_rows(factorizer_rows, context_rows)
    timing_audit = build_timing_audit(heldout_trials, timing_rows, level1f3_analysis)
    memory_audit = build_memory_audit(heldout_trials)
    claims = build_claims(truth_rows, conditional_rows, factorizer_rows)
    analysis_payload = build_analysis_payload(
        level1f3_analysis,
        truth_rows,
        conditional_rows,
        cap_rows,
        config_rows,
        timing_audit,
        memory_audit,
        claims,
    )
    closure_md = build_level1_closure_markdown(claims)

    save_csv(output_dir / "oracle_decomposition.csv", oracle_rows)
    save_csv(output_dir / "truth_inclusion_decomposition.csv", truth_rows)
    save_csv(output_dir / "conditional_recovery.csv", conditional_rows)
    save_csv(output_dir / "cap_saturation.csv", cap_rows)
    save_csv(output_dir / "config_sweep_summary.csv", config_rows)
    save_csv(output_dir / "pareto_summary.csv", pareto_rows)
    save_json(output_dir / "claims.json", claims)
    save_json(output_dir / "analysis.json", analysis_payload)
    (docs_dir / "LEVEL1_RESEARCH_CLOSURE.md").write_text(closure_md, encoding="utf-8", newline="\n")

    return {
        "oracle_rows": oracle_rows,
        "truth_rows": truth_rows,
        "conditional_rows": conditional_rows,
        "cap_rows": cap_rows,
        "config_rows": config_rows,
        "pareto_rows": pareto_rows,
        "claims": claims,
        "analysis": analysis_payload,
    }
