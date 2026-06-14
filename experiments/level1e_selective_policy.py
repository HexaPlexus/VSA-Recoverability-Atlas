from __future__ import annotations

import json
from pathlib import Path

from cgrn_hsr.query_context import (
    METHOD_GLOBAL_STAGE,
    METHOD_GLOBAL_UNIFORM,
    METHOD_HARD_L2_STAGE,
    METHOD_SOFT_L2_WEIGHTED_INIT,
    QUERY_SCHEMA_VERSION,
    BaselineConfig,
    SyntheticContextConfig,
    build_query_trial_problem,
    build_stage_snapshots,
    run_query_trial,
)
from cgrn_hsr.selective_policy import (
    CALIBRATION_CELLS,
    DIAGNOSTIC_CELL,
    EASY_CELL,
    LEVEL1E_CALIBRATION_MASTER_SEED,
    LEVEL1E_DEVELOPMENT_MASTER_SEED,
    LEVEL1E_HELDOUT_MASTER_SEED,
    POLICY_ABSTAIN,
    POLICY_ACCEPT_CORRECT_GLOBAL,
    POLICY_ACCEPT_CORRECT_L1,
    POLICY_ACCEPT_CORRECT_L2,
    POLICY_ACCEPT_WRONG_GLOBAL,
    POLICY_ACCEPT_WRONG_L1,
    POLICY_ACCEPT_WRONG_L2,
    POLICY_CELLS,
    POLICY_VERSION,
    PRIMARY_CELL,
    SELECTIVE_SCHEMA_VERSION,
    SELECTIVE_POLICY_FEATURES,
    STRESS_CELL,
    compute_context_confidence,
    compute_cross_scale_consistency,
    compute_stage_hit_rates_among_all_trials,
    compute_frontier_rows,
    correct_query_outcome,
    decision_outcome_label,
    level1e_calibration_seed_ranges,
    level1e_development_seed_ranges,
    level1e_heldout_seed_ranges,
    make_policy_input,
    run_adaptive_policy,
    save_csv,
    save_json,
    save_jsonl,
    selective_seed_sets_non_overlapping,
    summarize_policy_records,
)

CHECKPOINT_COMMIT = "7702342d8ba317622820631682271dff9e1b0f04"
LEVEL1E_RESULTS_DIR = Path("results") / "level1e"
FROZEN_PRIOR_STRENGTH = 1.0

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

CELL_ID_TO_SPEC = {
    "COLLAPSE_SINGLE_PRIMARY": PRIMARY_CELL,
    "COLLAPSE_SINGLE_STRESS": STRESS_CELL,
    "EASY_SINGLE": EASY_CELL,
    "HARD_STRUCTURED_MIXTURE": DIAGNOSTIC_CELL,
}


def build_problems(seed_ranges: dict[str, dict[str, int]], seed_split: str) -> list[dict]:
    rows = []
    for cell_id, seed_spec in seed_ranges.items():
        cell = CELL_ID_TO_SPEC[cell_id]
        config = REGIMES[cell.label]
        for seed in range(seed_spec["start"], seed_spec["start"] + seed_spec["count"]):
            problem = build_query_trial_problem(
                config,
                seed=seed,
                anomaly_rate=cell.anomaly_rate,
                seed_split=seed_split,
                context_config=CONTEXT_CONFIG,
            )
            rows.append({"cell_id": cell_id, "cell": cell, "problem": problem})
    return rows


def stage_counts(rows: list[dict]) -> dict[str, dict[str, int]]:
    valid_counts = {"L2_narrow": 0, "L1_parent": 0, "global": 0}
    target_counts = {"L2_narrow": 0, "L1_parent": 0, "global": 0}
    for row in rows:
        stability = row["stability"]
        if stability["oracle_earliest_valid_stage"] is not None:
            valid_counts[stability["oracle_earliest_valid_stage"]] += 1
        if stability["oracle_earliest_target_stage"] is not None:
            target_counts[stability["oracle_earliest_target_stage"]] += 1
    return {
        "oracle_earliest_valid_stage_counts": valid_counts,
        "oracle_earliest_target_stage_counts": target_counts,
    }


def make_trial_bundle(problem_row: dict, master_seed: int) -> dict:
    cell_id = problem_row["cell_id"]
    cell = problem_row["cell"]
    problem = problem_row["problem"]
    snapshots, stability = build_stage_snapshots(
        problem,
        operating_point_label=cell.label,
        master_seed=master_seed,
        context_accuracy=cell.context_accuracy,
        shuffled_query_context=problem.query_context,
    )
    global_result, _ = run_query_trial(
        problem,
        operating_point_label=cell.label,
        master_seed=master_seed,
        method=METHOD_GLOBAL_UNIFORM,
    )
    soft_result, _ = run_query_trial(
        problem,
        operating_point_label=cell.label,
        master_seed=master_seed,
        method=METHOD_SOFT_L2_WEIGHTED_INIT,
        context_accuracy=cell.context_accuracy,
        prior_strength=FROZEN_PRIOR_STRENGTH,
    )
    context_confidence = compute_context_confidence()
    policy_input = make_policy_input(
        snapshots["L2_narrow"].__dict__,
        snapshots["L1_parent"].__dict__,
        snapshots["global"].__dict__,
        stability,
        context_confidence=context_confidence,
    )
    l2_query_outcome = snapshots["L2_narrow"].query_outcome
    l1_query_outcome = snapshots["L1_parent"].query_outcome
    global_query_outcome = snapshots["global"].query_outcome
    oracle_stage = stability["oracle_earliest_valid_stage"]
    oracle_compute = stability["oracle_progressive_compute"]
    oracle_policy_outcome = POLICY_ABSTAIN if oracle_stage is None else {
        "L2_narrow": POLICY_ACCEPT_CORRECT_L2,
        "L1_parent": POLICY_ACCEPT_CORRECT_L1,
        "global": POLICY_ACCEPT_CORRECT_GLOBAL,
    }[oracle_stage]
    return {
        "seed_split": problem.seed_split,
        "cell_id": cell_id,
        "operating_point_label": cell.label,
        "seed": problem.seed,
        "anomaly_rate": cell.anomaly_rate,
        "context_accuracy": cell.context_accuracy,
        "problem_id": f"{cell_id}:seed{problem.seed}",
        "query_context": problem.query_context,
        "world_context": problem.world_context,
        "stage_evidence": {key: value.__dict__ for key, value in snapshots.items()},
        "stability": stability,
        "policy_input": policy_input,
        "features": SELECTIVE_POLICY_FEATURES,
        "query_outcome_by_stage": {
            "L2": l2_query_outcome,
            "L1": l1_query_outcome,
            "GLOBAL": global_query_outcome,
        },
        "l2_prediction_correct": correct_query_outcome(l2_query_outcome),
        "l2_tuple_survives_l1": stability["l2_prediction_survives_l1"],
        "l2_tuple_rank_at_l1": stability["l2_rank_at_l1"],
        "baselines": {
            "global_uniform_always_accept": {
                "accepted_stage": "GLOBAL",
                "accepted_correct": correct_query_outcome(global_result.query_outcome_class),
                "policy_outcome": decision_outcome_label("GLOBAL", global_result.query_outcome_class),
                "ran_l2": False,
                "ran_l1": False,
                "ran_global": True,
                "total_iterations": global_result.iterations_used,
                "candidate_evaluations": global_result.candidate_evaluations_proxy,
                "element_operations_proxy": global_result.element_operations_proxy,
                "query_outcome": global_result.query_outcome_class,
            },
            "l2_hard_always_accept": {
                "accepted_stage": "L2",
                "accepted_correct": correct_query_outcome(l2_query_outcome),
                "policy_outcome": decision_outcome_label("L2", l2_query_outcome),
                "ran_l2": True,
                "ran_l1": False,
                "ran_global": False,
                "total_iterations": snapshots["L2_narrow"].iterations,
                "candidate_evaluations": snapshots["L2_narrow"].candidate_evaluations_proxy,
                "element_operations_proxy": snapshots["L2_narrow"].element_operations_proxy,
                "query_outcome": l2_query_outcome,
            },
            "l2_soft_initialization_always_accept": {
                "accepted_stage": "L2",
                "accepted_correct": correct_query_outcome(soft_result.query_outcome_class),
                "policy_outcome": decision_outcome_label("L2", soft_result.query_outcome_class),
                "ran_l2": True,
                "ran_l1": False,
                "ran_global": False,
                "total_iterations": soft_result.iterations_used,
                "candidate_evaluations": soft_result.candidate_evaluations_proxy,
                "element_operations_proxy": soft_result.element_operations_proxy,
                "query_outcome": soft_result.query_outcome_class,
            },
            "always_global": {
                "accepted_stage": "GLOBAL",
                "accepted_correct": correct_query_outcome(global_result.query_outcome_class),
                "policy_outcome": decision_outcome_label("GLOBAL", global_result.query_outcome_class),
                "ran_l2": False,
                "ran_l1": False,
                "ran_global": True,
                "total_iterations": global_result.iterations_used,
                "candidate_evaluations": global_result.candidate_evaluations_proxy,
                "element_operations_proxy": global_result.element_operations_proxy,
                "query_outcome": global_result.query_outcome_class,
            },
            "oracle_progressive_stop": {
                "accepted_stage": None if oracle_stage is None else oracle_stage.replace("_narrow", "").replace("_parent", "").upper(),
                "accepted_correct": oracle_stage is not None,
                "policy_outcome": oracle_policy_outcome,
                "ran_l2": True,
                "ran_l1": oracle_stage in ("L1_parent", "global") or oracle_stage is None,
                "ran_global": oracle_stage == "global" or oracle_stage is None,
                "total_iterations": (
                    snapshots["L2_narrow"].iterations
                    + (snapshots["L1_parent"].iterations if oracle_stage in ("L1_parent", "global") or oracle_stage is None else 0)
                    + (snapshots["global"].iterations if oracle_stage == "global" or oracle_stage is None else 0)
                ),
                "candidate_evaluations": (
                    snapshots["L2_narrow"].candidate_evaluations_proxy
                    + (snapshots["L1_parent"].candidate_evaluations_proxy if oracle_stage in ("L1_parent", "global") or oracle_stage is None else 0)
                    + (snapshots["global"].candidate_evaluations_proxy if oracle_stage == "global" or oracle_stage is None else 0)
                ),
                "element_operations_proxy": oracle_compute if oracle_stage is not None else (
                    snapshots["L2_narrow"].element_operations_proxy
                    + snapshots["L1_parent"].element_operations_proxy
                    + snapshots["global"].element_operations_proxy
                ),
                "query_outcome": global_query_outcome if oracle_stage is None else (
                    l2_query_outcome if oracle_stage == "L2_narrow" else (
                        l1_query_outcome if oracle_stage == "L1_parent" else global_query_outcome
                    )
                ),
            },
        },
    }


def serializable_trial_row(bundle: dict, adaptive_record: dict | None = None) -> dict:
    row = {
        "schema_version": SELECTIVE_SCHEMA_VERSION,
        "query_schema_version": QUERY_SCHEMA_VERSION,
        "seed_split": bundle["seed_split"],
        "cell_id": bundle["cell_id"],
        "operating_point_label": bundle["operating_point_label"],
        "seed": bundle["seed"],
        "anomaly_rate": bundle["anomaly_rate"],
        "context_accuracy": bundle["context_accuracy"],
        "problem_id": bundle["problem_id"],
        "query_context": bundle["query_context"],
        "world_context": bundle["world_context"],
        "stage_evidence": bundle["stage_evidence"],
        "stability": bundle["stability"],
        "baselines": bundle["baselines"],
    }
    if adaptive_record is not None:
        row["adaptive_calibrated_policy"] = adaptive_record
    return row


def policy_record(bundle: dict, policy_id: str, accepted_stage: str | None, accepted_correct: bool, policy_outcome: str, ran_l2: bool, ran_l1: bool, ran_global: bool, total_iterations: int, candidate_evaluations: int, element_operations_proxy: int) -> dict:
    return {
        "schema_version": SELECTIVE_SCHEMA_VERSION,
        "seed_split": bundle["seed_split"],
        "cell_id": bundle["cell_id"],
        "policy_id": policy_id,
        "seed": bundle["seed"],
        "accepted_stage": accepted_stage,
        "accepted_correct": accepted_correct,
        "policy_outcome": policy_outcome,
        "ran_l2": ran_l2,
        "ran_l1": ran_l1,
        "ran_global": ran_global,
        "total_iterations": total_iterations,
        "candidate_evaluations": candidate_evaluations,
        "element_operations_proxy": element_operations_proxy,
    }


def adaptive_record(bundle: dict, selected_policy) -> dict:
    decision = run_adaptive_policy(bundle["policy_input"], selected_policy)
    accepted_correct = False
    query_outcome = "UNSETTLED"
    if decision.accepted_stage is not None:
        query_outcome = bundle["query_outcome_by_stage"][decision.accepted_stage]
        accepted_correct = correct_query_outcome(query_outcome)
    return {
        "accepted_stage": decision.accepted_stage,
        "accepted_correct": accepted_correct,
        "policy_outcome": decision_outcome_label(decision.accepted_stage, query_outcome),
        "ran_l2": decision.ran_l2,
        "ran_l1": decision.ran_l1,
        "ran_global": decision.ran_global,
        "total_iterations": decision.total_iterations,
        "candidate_evaluations": decision.candidate_evaluations,
        "element_operations_proxy": decision.element_operations_proxy,
        "query_outcome": query_outcome,
    }


def records_for_split(bundles: list[dict], selected_policy) -> tuple[list[dict], list[dict]]:
    trial_rows = []
    policy_rows = []
    for bundle in bundles:
        adaptive = adaptive_record(bundle, selected_policy)
        trial_rows.append(serializable_trial_row(bundle, adaptive_record=adaptive))

        for policy_id, baseline in bundle["baselines"].items():
            policy_rows.append(
                policy_record(
                    bundle,
                    policy_id=policy_id,
                    accepted_stage=baseline["accepted_stage"],
                    accepted_correct=baseline["accepted_correct"],
                    policy_outcome=baseline["policy_outcome"],
                    ran_l2=baseline["ran_l2"],
                    ran_l1=baseline["ran_l1"],
                    ran_global=baseline["ran_global"],
                    total_iterations=baseline["total_iterations"],
                    candidate_evaluations=baseline["candidate_evaluations"],
                    element_operations_proxy=baseline["element_operations_proxy"],
                )
            )

        policy_rows.append(
            policy_record(
                bundle,
                policy_id="adaptive_calibrated_policy",
                accepted_stage=adaptive["accepted_stage"],
                accepted_correct=adaptive["accepted_correct"],
                policy_outcome=adaptive["policy_outcome"],
                ran_l2=adaptive["ran_l2"],
                ran_l1=adaptive["ran_l1"],
                ran_global=adaptive["ran_global"],
                total_iterations=adaptive["total_iterations"],
                candidate_evaluations=adaptive["candidate_evaluations"],
                element_operations_proxy=adaptive["element_operations_proxy"],
            )
        )
    return trial_rows, policy_rows


def cross_scale_rows(bundles: list[dict]) -> list[dict]:
    return [
        {
            "l2_tuple_survives_l1": bundle["stability"]["l2_prediction_survives_l1"],
            "l2_tuple_rank_at_l1": bundle["stability"]["l2_rank_at_l1"],
            "l2_prediction_correct": correct_query_outcome(bundle["stage_evidence"]["L2_narrow"]["query_outcome"]),
        }
        for bundle in bundles
    ]


def main() -> None:
    if not selective_seed_sets_non_overlapping():
        raise RuntimeError("Level 1E seed splits overlap with prior runs or each other.")

    calibration_seed_ranges = level1e_calibration_seed_ranges()
    calibration_selection_seed_ranges = {
        cell_id: seed_spec
        for cell_id, seed_spec in calibration_seed_ranges.items()
        if cell_id != "HARD_STRUCTURED_MIXTURE"
    }

    development_bundles = [
        make_trial_bundle(problem_row, LEVEL1E_DEVELOPMENT_MASTER_SEED)
        for problem_row in build_problems(level1e_development_seed_ranges(), seed_split="development")
    ]
    calibration_bundles = [
        make_trial_bundle(problem_row, LEVEL1E_CALIBRATION_MASTER_SEED)
        for problem_row in build_problems(calibration_seed_ranges, seed_split="calibration")
    ]

    calibration_policy_rows = [
        {
            "policy_input": bundle["policy_input"],
            "query_outcome_by_stage": bundle["query_outcome_by_stage"],
            "features": bundle["features"],
        }
        for bundle in calibration_bundles
        if bundle["cell_id"] != "HARD_STRUCTURED_MIXTURE"
    ]
    frontier_rows, selected_policy = compute_frontier_rows(
        calibration_policy_rows,
        calibration_seed_range=calibration_selection_seed_ranges,
    )

    heldout_bundles = [
        make_trial_bundle(problem_row, LEVEL1E_HELDOUT_MASTER_SEED)
        for problem_row in build_problems(level1e_heldout_seed_ranges(), seed_split="heldout")
    ]

    calibration_trial_rows, calibration_policy_records = records_for_split(calibration_bundles, selected_policy)
    heldout_trial_rows, heldout_policy_records = records_for_split(heldout_bundles, selected_policy)

    calibration_summary = summarize_policy_records(calibration_policy_records)
    heldout_summary = summarize_policy_records(heldout_policy_records)

    development_cross_scale = compute_cross_scale_consistency(cross_scale_rows(development_bundles))
    calibration_cross_scale = compute_cross_scale_consistency(cross_scale_rows(calibration_bundles))
    heldout_cross_scale = compute_cross_scale_consistency(cross_scale_rows(heldout_bundles))

    invariant_audit = compute_stage_hit_rates_among_all_trials(
        stage_counts(heldout_bundles),
        total_trials=len(heldout_bundles),
    )

    save_jsonl(LEVEL1E_RESULTS_DIR / "calibration_trials.jsonl", calibration_trial_rows)
    save_csv(LEVEL1E_RESULTS_DIR / "calibration_frontier.csv", frontier_rows)
    save_json(LEVEL1E_RESULTS_DIR / "selected_policy.json", selected_policy.to_dict())
    save_jsonl(LEVEL1E_RESULTS_DIR / "heldout_trials.jsonl", heldout_trial_rows)
    save_csv(LEVEL1E_RESULTS_DIR / "summary.csv", heldout_summary)
    save_json(
        LEVEL1E_RESULTS_DIR / "evidence_separation.json",
        {
            "schema_version": SELECTIVE_SCHEMA_VERSION,
            "development": development_cross_scale,
            "calibration": calibration_cross_scale,
            "heldout": heldout_cross_scale,
        },
    )
    save_json(
        LEVEL1E_RESULTS_DIR / "analysis.json",
        {
            "schema_version": SELECTIVE_SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "query_schema_version": QUERY_SCHEMA_VERSION,
            "checkpoint_commit": CHECKPOINT_COMMIT,
            "fixed_prior_strength": FROZEN_PRIOR_STRENGTH,
            "split_seed_ranges": {
                "development": level1e_development_seed_ranges(),
                "calibration": calibration_seed_ranges,
                "calibration_selection": calibration_selection_seed_ranges,
                "heldout": level1e_heldout_seed_ranges(),
            },
            "invariant_audit": invariant_audit,
            "development_cross_scale": development_cross_scale,
            "calibration_cross_scale": calibration_cross_scale,
            "heldout_cross_scale": heldout_cross_scale,
            "calibration_summary": calibration_summary,
            "heldout_summary": heldout_summary,
            "selected_policy": selected_policy.to_dict(),
        },
    )

    print(f"development_trials={len(development_bundles)}")
    print(f"calibration_trials={len(calibration_bundles)}")
    print(f"heldout_trials={len(heldout_bundles)}")
    print(json.dumps({"selected_policy": selected_policy.to_dict()}, ensure_ascii=True))


if __name__ == "__main__":
    main()
