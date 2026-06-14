from __future__ import annotations

import json
import math
from pathlib import Path

from cgrn_hsr.baseline import (
    ANOMALY_RATE_GRID,
    BENCHMARK_SCHEMA_VERSION,
    CONTEXT_ACCURACY_GRID,
    LEVEL1C_MASTER_SEED,
    LEVEL1C_TRIALS_PER_REGIME,
    METHOD_GLOBAL,
    METHOD_ORACLE_L2_CONTEXT,
    METHOD_ORACLE_TRUTH_INCLUDED,
    METHOD_PREDICTED_L2_CONTEXT,
    METHOD_RANDOM_UNCONDITIONAL,
    OUTCOME_DISTRACTOR_CAPTURE,
    OUTCOME_HYBRID_SPURIOUS,
    OUTCOME_TARGET_RECOVERY,
    OUTCOME_UNSETTLED,
    BaselineConfig,
    SyntheticContextConfig,
    build_contextual_trial_problem,
    build_trial_problem,
    confirmation_seed_ranges,
    level1c_seed_ranges,
    method_selection_seed,
    run_trial_on_problem,
    save_json,
    save_summary_csv,
    save_trials_jsonl,
    summarize_trials,
)

LEVEL1B_COMMIT = "f654e328b8667b57f0bd7a4c74ae1fefcbc07515"
TAXONOMY_RESULTS_DIR = Path("results") / "level1b1_taxonomy"
LEVEL1C_RESULTS_DIR = Path("results") / "level1c"

TAXONOMY_POINTS: dict[str, BaselineConfig] = {
    "EASY": BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=0),
    "BORDERLINE": BaselineConfig(dimensions=1024, num_factors=3, domain_size=5, structured_distractor_count=2),
    "COLLAPSE": BaselineConfig(dimensions=1024, num_factors=4, domain_size=10, structured_distractor_count=0),
}

CONTEXT_REGIMES: dict[str, BaselineConfig] = {
    "EASY_SINGLE": BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=0),
    "HARD_STRUCTURED_MIXTURE": BaselineConfig(
        dimensions=1024,
        num_factors=3,
        domain_size=5,
        structured_distractor_count=2,
    ),
    "COLLAPSE_SINGLE": BaselineConfig(dimensions=1024, num_factors=4, domain_size=10, structured_distractor_count=0),
}

CONTEXT_CONFIG = SyntheticContextConfig(
    num_l1_contexts=3,
    num_l2_per_l1=3,
    multi_membership_rate=0.5,
    tertiary_membership_rate=0.2,
)


def candidate_sizes(domain_size: int) -> list[tuple[str, int]]:
    return [
        ("half", math.ceil(domain_size / 2)),
        ("quarter", max(2, math.ceil(domain_size / 4))),
    ]


def taxonomy_replay_trials() -> list:
    trials = []
    seed_specs = confirmation_seed_ranges()
    for label, config in TAXONOMY_POINTS.items():
        start = seed_specs[label]["start"]
        count = seed_specs[label]["count"]
        for seed in range(start, start + count):
            problem = build_trial_problem(config, seed)
            trials.append(
                run_trial_on_problem(
                    problem,
                    master_seed=LEVEL1C_MASTER_SEED,
                    operating_point_label=label,
                    method=METHOD_GLOBAL,
                    reduction_ratio_label="full",
                )
            )
    return trials


def taxonomy_breakdown(summary_rows: list[dict]) -> list[dict]:
    rows = []
    for label in ("EASY", "BORDERLINE", "COLLAPSE"):
        row = next(item for item in summary_rows if item["operating_point_label"] == label)
        rows.append(
            {
                "operating_point_label": label,
                "false_consensus_rate": row["false_consensus_rate"],
                "distractor_capture_rate": row["distractor_capture_rate"],
                "hybrid_spurious_rate": row["hybrid_spurious_rate"],
                "unsettled_rate": row["unsettled_rate"],
                "false_consensus_distractor_capture_share": row["false_consensus_distractor_capture_share"],
                "false_consensus_hybrid_spurious_share": row["false_consensus_hybrid_spurious_share"],
                "target_recovery_rate": row["target_recovery_rate"],
            }
        )
    return rows


def level1c_trials() -> list:
    trials = []
    seed_specs = level1c_seed_ranges()
    for label, config in CONTEXT_REGIMES.items():
        start = seed_specs[label]["start"]
        count = seed_specs[label]["count"]
        for anomaly_rate in ANOMALY_RATE_GRID:
            for seed in range(start, start + count):
                problem = build_contextual_trial_problem(
                    config,
                    seed=seed,
                    anomaly_rate=anomaly_rate,
                    context_config=CONTEXT_CONFIG,
                )
                trials.append(
                    run_trial_on_problem(
                        problem,
                        master_seed=LEVEL1C_MASTER_SEED,
                        operating_point_label=label,
                        method=METHOD_GLOBAL,
                        reduction_ratio_label="full",
                    )
                )
                for ratio_label, subset_size in candidate_sizes(config.domain_size):
                    for method in (
                        METHOD_RANDOM_UNCONDITIONAL,
                        METHOD_ORACLE_TRUTH_INCLUDED,
                        METHOD_ORACLE_L2_CONTEXT,
                    ):
                        trials.append(
                            run_trial_on_problem(
                                problem,
                                master_seed=LEVEL1C_MASTER_SEED,
                                operating_point_label=label,
                                method=method,
                                reduction_ratio_label=ratio_label,
                                subset_size=subset_size,
                                selection_seed=method_selection_seed(seed, method, ratio_label),
                            )
                        )
                    for context_accuracy in CONTEXT_ACCURACY_GRID:
                        trials.append(
                            run_trial_on_problem(
                                problem,
                                master_seed=LEVEL1C_MASTER_SEED,
                                operating_point_label=label,
                                method=METHOD_PREDICTED_L2_CONTEXT,
                                reduction_ratio_label=ratio_label,
                                subset_size=subset_size,
                                selection_seed=method_selection_seed(seed, METHOD_PREDICTED_L2_CONTEXT, ratio_label),
                                context_accuracy=context_accuracy,
                            )
                        )
    return trials


def summary_lookup(summary_rows: list[dict]) -> dict[tuple, dict]:
    return {
        (
            row["operating_point_label"],
            row["method"],
            row["reduction_ratio_label"],
            row["context_accuracy"],
            row["anomaly_rate"],
        ): row
        for row in summary_rows
    }


def level1c_analysis(summary_rows: list[dict]) -> dict:
    lookup = summary_lookup(summary_rows)
    comparison_rows = []
    for label in CONTEXT_REGIMES:
        for anomaly_rate in ANOMALY_RATE_GRID:
            global_row = lookup[(label, METHOD_GLOBAL, "full", None, anomaly_rate)]
            for ratio_label, _subset_size in candidate_sizes(CONTEXT_REGIMES[label].domain_size):
                random_row = lookup[(label, METHOD_RANDOM_UNCONDITIONAL, ratio_label, None, anomaly_rate)]
                oracle_truth_row = lookup[(label, METHOD_ORACLE_TRUTH_INCLUDED, ratio_label, None, anomaly_rate)]
                oracle_l2_row = lookup[(label, METHOD_ORACLE_L2_CONTEXT, ratio_label, None, anomaly_rate)]
                for context_accuracy in CONTEXT_ACCURACY_GRID:
                    predicted_row = lookup[
                        (label, METHOD_PREDICTED_L2_CONTEXT, ratio_label, context_accuracy, anomaly_rate)
                    ]
                    comparison_rows.append(
                        {
                            "operating_point_label": label,
                            "anomaly_rate": anomaly_rate,
                            "reduction_ratio_label": ratio_label,
                            "candidate_subset_size": oracle_l2_row["candidate_subset_size"],
                            "context_accuracy": context_accuracy,
                            "global_exact_recovery_rate": global_row["exact_recovery_rate"],
                            "global_false_consensus_rate": global_row["false_consensus_rate"],
                            "random_candidate_recall": random_row["mean_candidate_recall"],
                            "random_exact_recovery_rate": random_row["exact_recovery_rate"],
                            "random_hybrid_spurious_rate": random_row["hybrid_spurious_rate"],
                            "random_distractor_capture_rate": random_row["distractor_capture_rate"],
                            "random_compute_proxy": random_row["mean_element_operations_proxy"],
                            "oracle_truth_candidate_recall": oracle_truth_row["mean_candidate_recall"],
                            "oracle_truth_exact_recovery_rate": oracle_truth_row["exact_recovery_rate"],
                            "oracle_truth_compute_proxy": oracle_truth_row["mean_element_operations_proxy"],
                            "oracle_l2_candidate_recall": oracle_l2_row["mean_candidate_recall"],
                            "oracle_l2_exact_recovery_rate": oracle_l2_row["exact_recovery_rate"],
                            "oracle_l2_hybrid_spurious_rate": oracle_l2_row["hybrid_spurious_rate"],
                            "oracle_l2_distractor_capture_rate": oracle_l2_row["distractor_capture_rate"],
                            "oracle_l2_compute_proxy": oracle_l2_row["mean_element_operations_proxy"],
                            "predicted_candidate_recall": predicted_row["mean_candidate_recall"],
                            "predicted_exact_recovery_rate": predicted_row["exact_recovery_rate"],
                            "predicted_hybrid_spurious_rate": predicted_row["hybrid_spurious_rate"],
                            "predicted_distractor_capture_rate": predicted_row["distractor_capture_rate"],
                            "predicted_unsettled_rate": predicted_row["unsettled_rate"],
                            "predicted_compute_proxy": predicted_row["mean_element_operations_proxy"],
                            "predicted_context_prediction_correct_rate": predicted_row[
                                "context_prediction_correct_rate"
                            ],
                            "oracle_l2_vs_random_candidate_recall_delta": (
                                oracle_l2_row["mean_candidate_recall"] - random_row["mean_candidate_recall"]
                            ),
                            "oracle_l2_vs_random_exact_recovery_delta": (
                                oracle_l2_row["exact_recovery_rate"] - random_row["exact_recovery_rate"]
                            ),
                            "predicted_vs_random_candidate_recall_delta": (
                                predicted_row["mean_candidate_recall"] - random_row["mean_candidate_recall"]
                            ),
                            "predicted_vs_random_exact_recovery_delta": (
                                predicted_row["exact_recovery_rate"] - random_row["exact_recovery_rate"]
                            ),
                            "predicted_exact_recovery_regret_vs_oracle_truth_included": predicted_row[
                                "paired_exact_recovery_regret_vs_oracle_truth_included"
                            ],
                            "predicted_candidate_recall_regret_vs_oracle_truth_included": predicted_row[
                                "paired_candidate_recall_regret_vs_oracle_truth_included"
                            ],
                        }
                    )

    operating_gate = []
    for label in CONTEXT_REGIMES:
        oracle_rows = [
            row
            for row in comparison_rows
            if row["operating_point_label"] == label
        ]
        beats_random = all(
            row["oracle_l2_candidate_recall"] > row["random_candidate_recall"]
            for row in oracle_rows
        )
        operating_gate.append(
            {
                "operating_point_label": label,
                "oracle_l2_beats_random_candidate_recall_everywhere": beats_random,
            }
        )

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "level1b_commit": LEVEL1B_COMMIT,
        "master_seed": LEVEL1C_MASTER_SEED,
        "trials_per_regime": LEVEL1C_TRIALS_PER_REGIME,
        "context_hierarchy": {
            "num_l1_contexts": CONTEXT_CONFIG.num_l1_contexts,
            "num_l2_per_l1": CONTEXT_CONFIG.num_l2_per_l1,
            "multi_membership_rate": CONTEXT_CONFIG.multi_membership_rate,
            "tertiary_membership_rate": CONTEXT_CONFIG.tertiary_membership_rate,
        },
        "anomaly_rate_grid": list(ANOMALY_RATE_GRID),
        "context_accuracy_grid": list(CONTEXT_ACCURACY_GRID),
        "comparison_rows": comparison_rows,
        "gate": operating_gate,
    }


def main() -> None:
    taxonomy_trials = taxonomy_replay_trials()
    taxonomy_summary = summarize_trials(taxonomy_trials)
    save_trials_jsonl(TAXONOMY_RESULTS_DIR / "trials.jsonl", taxonomy_trials)
    save_summary_csv(TAXONOMY_RESULTS_DIR / "summary.csv", taxonomy_summary)
    save_json(
        TAXONOMY_RESULTS_DIR / "false_consensus_breakdown.json",
        {
            "schema_version": BENCHMARK_SCHEMA_VERSION,
            "level1b_commit": LEVEL1B_COMMIT,
            "seed_policy": confirmation_seed_ranges(),
            "breakdown": taxonomy_breakdown(taxonomy_summary),
        },
    )

    context_trials = level1c_trials()
    context_summary = summarize_trials(context_trials)
    context_analysis = level1c_analysis(context_summary)
    save_trials_jsonl(LEVEL1C_RESULTS_DIR / "trials.jsonl", context_trials)
    save_summary_csv(LEVEL1C_RESULTS_DIR / "summary.csv", context_summary)
    save_json(LEVEL1C_RESULTS_DIR / "analysis.json", context_analysis)

    print(f"taxonomy_trials={len(taxonomy_trials)}")
    print(f"context_trials={len(context_trials)}")
    print(json.dumps(context_analysis["gate"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
