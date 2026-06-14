from __future__ import annotations

import json
from pathlib import Path

from cgrn_hsr.query_context import (
    ANOMALY_RATE_GRID,
    CONTEXT_ACCURACY_GRID,
    CONTROL_NORMAL,
    CONTROL_SHUFFLED_CONTEXT_METADATA,
    CONTROL_SHUFFLED_QUERY_CONTEXT,
    LEVEL1D_CALIBRATION_MASTER_SEED,
    LEVEL1D_EVAL_MASTER_SEED,
    LEVEL1D_PRIOR_STRENGTHS,
    METHOD_GLOBAL_UNIFORM,
    METHOD_HARD_L2_TOPK,
    METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT,
    METHOD_ORACLE_TRUTH_INCLUDED,
    METHOD_SOFT_L2_WEIGHTED_INIT,
    QUERY_OUTCOME_EQUIVALENT_VALID,
    QUERY_OUTCOME_TARGET_RECOVERY,
    QUERY_SCHEMA_VERSION,
    BaselineConfig,
    SyntheticContextConfig,
    build_query_trial_problem,
    build_stage_snapshots,
    choose_prior_strength,
    level1d_calibration_seed_ranges,
    level1d_evaluation_seed_ranges,
    run_query_trial,
    save_evidence_jsonl,
    save_json,
    save_summary_csv,
    save_trials_jsonl,
    shuffled_query_context_map,
    summarize_query_trials,
)

CHECKPOINT_COMMIT = "1bd409d37f2dbd758ef27f1f56f9911653fb87a2"
LEVEL1D_RESULTS_DIR = Path("results") / "level1d"
LEVEL1C1_RESULTS_DIR = Path("results") / "level1c1"

REGIMES: dict[str, BaselineConfig] = {
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


def build_problem_batches(seed_ranges: dict[str, dict[str, int]], seed_split: str) -> dict[tuple[str, float], list]:
    batches = {}
    for label, config in REGIMES.items():
        seed_start = seed_ranges[label]["start"]
        seed_count = seed_ranges[label]["count"]
        for anomaly_rate in ANOMALY_RATE_GRID:
            problems = []
            for seed in range(seed_start, seed_start + seed_count):
                problems.append(
                    build_query_trial_problem(
                        config,
                        seed=seed,
                        anomaly_rate=anomaly_rate,
                        seed_split=seed_split,
                        context_config=CONTEXT_CONFIG,
                    )
                )
            batches[(label, anomaly_rate)] = problems
    return batches


def calibration_trials(problem_batches: dict[tuple[str, float], list]) -> list:
    trials = []
    for (label, _anomaly_rate), problems in problem_batches.items():
        for problem in problems:
            for context_accuracy in CONTEXT_ACCURACY_GRID:
                for prior_strength in LEVEL1D_PRIOR_STRENGTHS:
                    result, _ = run_query_trial(
                        problem,
                        operating_point_label=label,
                        master_seed=LEVEL1D_CALIBRATION_MASTER_SEED,
                        method=METHOD_SOFT_L2_WEIGHTED_INIT,
                        control_label=CONTROL_NORMAL,
                        context_accuracy=context_accuracy,
                        prior_strength=prior_strength,
                    )
                    trials.append(result)
    return trials


def evaluation_trials(problem_batches: dict[tuple[str, float], list], chosen_prior_strength: float) -> tuple[list, list]:
    trials = []
    evidence_rows = []
    for (label, anomaly_rate), problems in problem_batches.items():
        shuffled_queries = shuffled_query_context_map(problems)
        for problem in problems:
            global_result, _ = run_query_trial(
                problem,
                operating_point_label=label,
                master_seed=LEVEL1D_EVAL_MASTER_SEED,
                method=METHOD_GLOBAL_UNIFORM,
            )
            oracle_truth_result, _ = run_query_trial(
                problem,
                operating_point_label=label,
                master_seed=LEVEL1D_EVAL_MASTER_SEED,
                method=METHOD_ORACLE_TRUTH_INCLUDED,
            )
            oracle_soft_result, _ = run_query_trial(
                problem,
                operating_point_label=label,
                master_seed=LEVEL1D_EVAL_MASTER_SEED,
                method=METHOD_ORACLE_SOFT_L2_WEIGHTED_INIT,
                prior_strength=chosen_prior_strength,
            )
            trials.extend([global_result, oracle_truth_result, oracle_soft_result])

            for context_accuracy in CONTEXT_ACCURACY_GRID:
                hard_result, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_HARD_L2_TOPK,
                    context_accuracy=context_accuracy,
                )
                soft_result, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_SOFT_L2_WEIGHTED_INIT,
                    context_accuracy=context_accuracy,
                    prior_strength=chosen_prior_strength,
                )
                shuffled_meta_hard, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_HARD_L2_TOPK,
                    control_label=CONTROL_SHUFFLED_CONTEXT_METADATA,
                    context_accuracy=context_accuracy,
                )
                shuffled_query_hard, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_HARD_L2_TOPK,
                    control_label=CONTROL_SHUFFLED_QUERY_CONTEXT,
                    context_accuracy=context_accuracy,
                    shuffled_query_context=shuffled_queries[problem.seed],
                )
                shuffled_meta_soft, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_SOFT_L2_WEIGHTED_INIT,
                    control_label=CONTROL_SHUFFLED_CONTEXT_METADATA,
                    context_accuracy=context_accuracy,
                    prior_strength=chosen_prior_strength,
                )
                shuffled_query_soft, _ = run_query_trial(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    method=METHOD_SOFT_L2_WEIGHTED_INIT,
                    control_label=CONTROL_SHUFFLED_QUERY_CONTEXT,
                    context_accuracy=context_accuracy,
                    prior_strength=chosen_prior_strength,
                    shuffled_query_context=shuffled_queries[problem.seed],
                )
                trials.extend(
                    [
                        hard_result,
                        soft_result,
                        shuffled_meta_hard,
                        shuffled_query_hard,
                        shuffled_meta_soft,
                        shuffled_query_soft,
                    ]
                )

                stage_snapshots, stability = build_stage_snapshots(
                    problem,
                    operating_point_label=label,
                    master_seed=LEVEL1D_EVAL_MASTER_SEED,
                    context_accuracy=context_accuracy,
                    shuffled_query_context=shuffled_queries[problem.seed],
                )
                evidence_rows.append(
                    {
                        "schema_version": QUERY_SCHEMA_VERSION,
                        "seed": problem.seed,
                        "seed_split": problem.seed_split,
                        "operating_point_label": label,
                        "anomaly_rate": anomaly_rate,
                        "context_accuracy": context_accuracy,
                        "query_context": problem.query_context,
                        "world_context": problem.world_context,
                        "designated_target_tuple": problem.designated_target_tuple.tolist(),
                        "valid_source_tuples": [row.tolist() for row in problem.valid_source_tuples],
                        "source_composites": [source.to_dict() for source in problem.source_composites],
                        "true_query_outcome_label": stage_snapshots["global"].query_outcome,
                        "stage_evidence": {
                            stage_label: snapshot.__dict__
                            for stage_label, snapshot in stage_snapshots.items()
                        },
                        "stability": stability,
                    }
                )
    return trials, evidence_rows


def summarize_controls(summary_rows: list[dict]) -> list[dict]:
    keyed = {
        (
            row["operating_point_label"],
            row["method"],
            row["control_label"],
            row["anomaly_rate"],
            row["context_accuracy"],
        ): row
        for row in summary_rows
        if row["seed_split"] == "evaluation"
    }
    comparisons = []
    for label in REGIMES:
        for anomaly_rate in ANOMALY_RATE_GRID:
            for context_accuracy in CONTEXT_ACCURACY_GRID:
                for method in (METHOD_HARD_L2_TOPK, METHOD_SOFT_L2_WEIGHTED_INIT):
                    normal = keyed[(label, method, CONTROL_NORMAL, anomaly_rate, context_accuracy)]
                    shuffled_meta = keyed[(label, method, CONTROL_SHUFFLED_CONTEXT_METADATA, anomaly_rate, context_accuracy)]
                    shuffled_query = keyed[(label, method, CONTROL_SHUFFLED_QUERY_CONTEXT, anomaly_rate, context_accuracy)]
                    comparisons.append(
                        {
                            "operating_point_label": label,
                            "method": method,
                            "anomaly_rate": anomaly_rate,
                            "context_accuracy": context_accuracy,
                            "normal_valid_recovery_rate": normal["query_valid_recovery_rate"],
                            "shuffled_metadata_valid_recovery_rate": shuffled_meta["query_valid_recovery_rate"],
                            "shuffled_query_valid_recovery_rate": shuffled_query["query_valid_recovery_rate"],
                            "normal_target_recovery_rate": normal["designated_target_recovery_rate"],
                            "shuffled_metadata_target_recovery_rate": shuffled_meta["designated_target_recovery_rate"],
                            "shuffled_query_target_recovery_rate": shuffled_query["designated_target_recovery_rate"],
                            "normal_irrelevant_capture_rate": normal["irrelevant_source_capture_rate"],
                            "shuffled_metadata_irrelevant_capture_rate": shuffled_meta["irrelevant_source_capture_rate"],
                            "shuffled_query_irrelevant_capture_rate": shuffled_query["irrelevant_source_capture_rate"],
                        }
                    )
    return comparisons


def summarize_stage_evidence(evidence_rows: list[dict]) -> dict:
    stage_order = {"L2_narrow": 1, "L1_parent": 2, "global": 3}
    valid_stage_hits = {label: 0 for label in stage_order}
    target_stage_hits = {label: 0 for label in stage_order}
    progressive_compute = []
    stable_correct = []
    stable_incorrect = []

    for row in evidence_rows:
        snapshots = row["stage_evidence"]
        stability = row["stability"]
        if stability["oracle_earliest_valid_stage"] is not None:
            valid_stage_hits[stability["oracle_earliest_valid_stage"]] += 1
        if stability["oracle_earliest_target_stage"] is not None:
            target_stage_hits[stability["oracle_earliest_target_stage"]] += 1
        progressive_compute.append(stability["oracle_progressive_compute"])

        l2_outcome = snapshots["L2_narrow"]["query_outcome"]
        bucket = stable_correct if l2_outcome in (QUERY_OUTCOME_TARGET_RECOVERY, QUERY_OUTCOME_EQUIVALENT_VALID) else stable_incorrect
        bucket.append(stability)

    def stability_stats(values: list[dict]) -> dict:
        if not values:
            return {}
        return {
            "l2_prediction_survives_l1_rate": sum(item["l2_prediction_survives_l1"] for item in values) / len(values),
            "l2_prediction_survives_global_rate": sum(item["l2_prediction_survives_global"] for item in values) / len(values),
            "mean_l2_rank_at_l1": sum(item["l2_rank_at_l1"] for item in values) / len(values),
            "mean_l2_rank_at_global": sum(item["l2_rank_at_global"] for item in values) / len(values),
            "mean_l2_margin_delta_at_l1": sum(item["l2_margin_delta_at_l1"] for item in values) / len(values),
            "mean_l2_margin_delta_at_global": sum(item["l2_margin_delta_at_global"] for item in values) / len(values),
        }

    return {
        "oracle_earliest_valid_stage_counts": valid_stage_hits,
        "oracle_earliest_target_stage_counts": target_stage_hits,
        "mean_oracle_progressive_compute": sum(progressive_compute) / len(progressive_compute),
        "correct_l2_prediction_stability": stability_stats(stable_correct),
        "incorrect_l2_prediction_stability": stability_stats(stable_incorrect),
    }


def main() -> None:
    calibration_batches = build_problem_batches(level1d_calibration_seed_ranges(), seed_split="calibration")
    calibration = calibration_trials(calibration_batches)
    chosen_prior_strength = choose_prior_strength(calibration)
    calibration_summary = summarize_query_trials(calibration)

    evaluation_batches = build_problem_batches(level1d_evaluation_seed_ranges(), seed_split="evaluation")
    evaluation, evidence_rows = evaluation_trials(evaluation_batches, chosen_prior_strength=chosen_prior_strength)
    evaluation_summary = summarize_query_trials(evaluation)
    controls = summarize_controls(evaluation_summary)
    stage_analysis = summarize_stage_evidence(evidence_rows)

    save_trials_jsonl(LEVEL1D_RESULTS_DIR / "calibration_trials.jsonl", calibration)
    save_summary_csv(LEVEL1D_RESULTS_DIR / "calibration_summary.csv", calibration_summary)
    save_json(
        LEVEL1D_RESULTS_DIR / "calibration.json",
        {
            "schema_version": QUERY_SCHEMA_VERSION,
            "checkpoint_commit": CHECKPOINT_COMMIT,
            "calibration_master_seed": LEVEL1D_CALIBRATION_MASTER_SEED,
            "prior_strength_candidates": list(LEVEL1D_PRIOR_STRENGTHS),
            "chosen_prior_strength": chosen_prior_strength,
        },
    )

    save_trials_jsonl(LEVEL1D_RESULTS_DIR / "trials.jsonl", evaluation)
    save_summary_csv(LEVEL1D_RESULTS_DIR / "summary.csv", evaluation_summary)
    save_evidence_jsonl(LEVEL1D_RESULTS_DIR / "evidence.jsonl", evidence_rows)
    save_json(
        LEVEL1D_RESULTS_DIR / "analysis.json",
        {
            "schema_version": QUERY_SCHEMA_VERSION,
            "checkpoint_commit": CHECKPOINT_COMMIT,
            "evaluation_master_seed": LEVEL1D_EVAL_MASTER_SEED,
            "chosen_prior_strength": chosen_prior_strength,
            "controls": controls,
            "stage_analysis": stage_analysis,
        },
    )

    save_trials_jsonl(LEVEL1C1_RESULTS_DIR / "trials.jsonl", evaluation)
    save_summary_csv(LEVEL1C1_RESULTS_DIR / "summary.csv", evaluation_summary)
    save_json(
        LEVEL1C1_RESULTS_DIR / "analysis.json",
        {
            "schema_version": QUERY_SCHEMA_VERSION,
            "checkpoint_commit": CHECKPOINT_COMMIT,
            "query_mixture_protocol": {
                "source_roles": [
                    "DESIGNATED_TARGET",
                    "OUT_OF_QUERY_CONTEXT",
                    "SIBLING_QUERY_CONTEXT",
                    "OVERLAPPING_CONTEXT",
                    "QUERY_EQUIVALENT_VALID",
                ],
                "controls": [CONTROL_SHUFFLED_CONTEXT_METADATA, CONTROL_SHUFFLED_QUERY_CONTEXT],
            },
            "controls": controls,
        },
    )

    print(f"calibration_trials={len(calibration)}")
    print(f"evaluation_trials={len(evaluation)}")
    print(f"evidence_rows={len(evidence_rows)}")
    print(json.dumps({"chosen_prior_strength": chosen_prior_strength}, ensure_ascii=True))


if __name__ == "__main__":
    main()
