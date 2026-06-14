from __future__ import annotations

import csv
import json
from pathlib import Path

from cgrn_hsr.query_context import BaselineConfig, SyntheticContextConfig, build_query_trial_problem
from cgrn_hsr.warm_start import (
    GLOBAL_GATE_VERSION,
    L2_GATE_VERSION,
    METHOD_ALWAYS_GLOBAL_COLD,
    METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
    METHOD_L2_THEN_COLD_GLOBAL,
    METHOD_L2_THEN_WARM_GLOBAL,
    METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED,
    WARM_START_METHOD_VERSION,
    WARM_START_SCHEMA_VERSION,
    WarmMethodTrialResult,
    build_paired_comparisons,
    choose_selected_method,
    compute_probe_separation,
    level1e1_calibration_seed_ranges,
    level1e1_development_seed_ranges,
    level1e1_heldout_seed_ranges,
    run_method_trial,
    save_csv,
    save_json,
    save_jsonl,
    summarize_method_trials,
    warm_start_seed_sets_non_overlapping,
)

CHECKPOINT_COMMIT = "6d885edb016bf6dcf2e4023f36e6232f21248d3b"
LEVEL1E1_RESULTS_DIR = Path("results") / "level1e1"

REGIMES: dict[str, BaselineConfig] = {
    "EASY_SINGLE": BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=0),
    "HARD_STRUCTURED_MIXTURE": BaselineConfig(dimensions=1024, num_factors=3, domain_size=5, structured_distractor_count=2),
    "COLLAPSE_SINGLE": BaselineConfig(dimensions=1024, num_factors=4, domain_size=10, structured_distractor_count=0),
}

CONTEXT_CONFIG = SyntheticContextConfig(
    num_l1_contexts=3,
    num_l2_per_l1=3,
    multi_membership_rate=0.5,
    tertiary_membership_rate=0.2,
)

CELL_ID_TO_SPEC = {
    "COLLAPSE_SINGLE_PRIMARY": {"label": "COLLAPSE_SINGLE", "anomaly_rate": 0.1, "context_accuracy": 0.9},
    "COLLAPSE_SINGLE_STRESS": {"label": "COLLAPSE_SINGLE", "anomaly_rate": 0.25, "context_accuracy": 0.7},
    "EASY_SINGLE": {"label": "EASY_SINGLE", "anomaly_rate": 0.1, "context_accuracy": 0.9},
    "HARD_STRUCTURED_MIXTURE": {"label": "HARD_STRUCTURED_MIXTURE", "anomaly_rate": 0.1, "context_accuracy": 0.9},
}

METHODS = (
    METHOD_ALWAYS_GLOBAL_COLD,
    METHOD_L2_THEN_COLD_GLOBAL,
    METHOD_L2_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE1_THEN_WARM_GLOBAL,
    METHOD_L2_PROBE2_THEN_WARM_GLOBAL,
    METHOD_L2_THEN_WARM_GLOBAL_UNCAPPED,
)


def build_problem_rows(seed_ranges: dict[str, dict[str, int]], seed_split: str) -> list[dict]:
    rows = []
    for cell_id, seed_spec in seed_ranges.items():
        cell = CELL_ID_TO_SPEC[cell_id]
        config = REGIMES[cell["label"]]
        for seed in range(seed_spec["start"], seed_spec["start"] + seed_spec["count"]):
            problem = build_query_trial_problem(
                config,
                seed=seed,
                anomaly_rate=cell["anomaly_rate"],
                seed_split=seed_split,
                context_config=CONTEXT_CONFIG,
            )
            rows.append(
                {
                    "cell_id": cell_id,
                    "operating_point_label": cell["label"],
                    "context_accuracy": cell["context_accuracy"],
                    "problem": problem,
                }
            )
    return rows


def run_split(problem_rows: list[dict], master_seed: int) -> list[WarmMethodTrialResult]:
    records: list[WarmMethodTrialResult] = []
    for row in problem_rows:
        for method_id in METHODS:
            records.append(
                run_method_trial(
                    problem=row["problem"],
                    cell_id=row["cell_id"],
                    operating_point_label=row["operating_point_label"],
                    method_id=method_id,
                    master_seed=master_seed,
                    context_accuracy=row["context_accuracy"],
                )
            )
    return records


def decorate_record(
    record: WarmMethodTrialResult,
    by_key: dict[tuple[str, int, str], WarmMethodTrialResult],
) -> dict:
    payload = record.to_dict()
    if record.method_id == METHOD_ALWAYS_GLOBAL_COLD:
        payload["cold_control_global_iterations"] = record.global_iterations
        payload["iterations_saved_vs_cold"] = 0
        return payload

    cold = by_key[(record.cell_id, record.seed, METHOD_L2_THEN_COLD_GLOBAL)]
    payload["cold_control_global_iterations"] = cold.global_iterations
    payload["iterations_saved_vs_cold"] = cold.global_iterations - record.global_iterations
    payload["cold_control_policy_outcome"] = cold.policy_outcome
    payload["cold_control_accepted_correct"] = cold.accepted_correct
    return payload


def load_level1e_reference() -> dict[str, dict[str, str]]:
    rows = list(csv.DictReader((Path("results") / "level1e" / "summary.csv").open(encoding="utf-8")))
    references = {}
    for cell_id in ("COLLAPSE_SINGLE_PRIMARY", "COLLAPSE_SINGLE_STRESS", "EASY_SINGLE"):
        references[cell_id] = next(
            row
            for row in rows
            if row["cell_id"] == cell_id and row["policy_id"] == "adaptive_calibrated_policy"
        )
    return references


def main() -> None:
    if not warm_start_seed_sets_non_overlapping():
        raise RuntimeError("Level 1E.1 seed ranges overlap with prior runs.")

    development_rows = build_problem_rows(level1e1_development_seed_ranges(), "development")
    calibration_rows = build_problem_rows(level1e1_calibration_seed_ranges(), "calibration")
    heldout_rows = build_problem_rows(level1e1_heldout_seed_ranges(), "heldout")

    development_records = run_split(development_rows, master_seed=0)
    calibration_records = run_split(calibration_rows, master_seed=1)
    heldout_records = run_split(heldout_rows, master_seed=2)

    heldout_summary = summarize_method_trials(heldout_records)
    heldout_pairs = build_paired_comparisons(heldout_records)
    heldout_probe = compute_probe_separation(heldout_records)
    selected_method = choose_selected_method(heldout_summary)

    heldout_by_key = {
        (record.cell_id, record.seed, record.method_id): record
        for record in heldout_records
    }
    heldout_trial_rows = [decorate_record(record, heldout_by_key) for record in heldout_records]

    save_jsonl(LEVEL1E1_RESULTS_DIR / "heldout_trials.jsonl", heldout_trial_rows)
    save_csv(LEVEL1E1_RESULTS_DIR / "summary.csv", heldout_summary)
    save_csv(LEVEL1E1_RESULTS_DIR / "paired_comparisons.csv", heldout_pairs)
    save_json(LEVEL1E1_RESULTS_DIR / "probe_evidence.json", heldout_probe)
    save_json(LEVEL1E1_RESULTS_DIR / "selected_method.json", selected_method.to_dict())
    save_json(
        LEVEL1E1_RESULTS_DIR / "analysis.json",
        {
            "schema_version": WARM_START_SCHEMA_VERSION,
            "method_version": WARM_START_METHOD_VERSION,
            "checkpoint_commit": CHECKPOINT_COMMIT,
            "l2_gate_version": L2_GATE_VERSION,
            "global_gate_version": GLOBAL_GATE_VERSION,
            "seed_ranges": {
                "development": level1e1_development_seed_ranges(),
                "calibration": level1e1_calibration_seed_ranges(),
                "heldout": level1e1_heldout_seed_ranges(),
            },
            "development_summary": summarize_method_trials(development_records),
            "calibration_summary": summarize_method_trials(calibration_records),
            "heldout_summary": heldout_summary,
            "heldout_paired_comparisons": heldout_pairs,
            "heldout_probe_evidence": heldout_probe,
            "historical_level1e_reference": load_level1e_reference(),
            "selected_method": selected_method.to_dict(),
        },
    )

    print(f"development_trials={len(development_records)}")
    print(f"calibration_trials={len(calibration_records)}")
    print(f"heldout_trials={len(heldout_records)}")
    print(json.dumps(selected_method.to_dict(), ensure_ascii=True))


if __name__ == "__main__":
    main()
