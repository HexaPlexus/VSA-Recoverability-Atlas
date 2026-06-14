from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .baseline import pilot_seed_set, wilson_interval
from .query_context import (
    LEVEL1D_CALIBRATION_MASTER_SEED,
    LEVEL1D_EVAL_MASTER_SEED,
    QUERY_OUTCOME_EQUIVALENT_VALID,
    QUERY_OUTCOME_TARGET_RECOVERY,
    level1d_calibration_seed_set,
    level1d_evaluation_seed_set,
)

SELECTIVE_SCHEMA_VERSION = "level1-selective-v1"
POLICY_VERSION = "threshold-policy-v1"
LEVEL1E_DEVELOPMENT_MASTER_SEED = 25260614
LEVEL1E_CALIBRATION_MASTER_SEED = 26260614
LEVEL1E_HELDOUT_MASTER_SEED = 27260614
LEVEL1E_DEVELOPMENT_TRIALS_PER_CELL = 24
LEVEL1E_CALIBRATION_TRIALS_PER_CELL = 32
LEVEL1E_HELDOUT_TRIALS_PER_CELL = 64
TARGET_RISK_PRIMARY = 0.05
TARGET_RISK_FALLBACK = 0.10
SELECTIVE_POLICY_FEATURES = (
    "stable_prediction_l2",
    "min_normalized_margin_l2",
    "normalized_reconstruction_l2",
    "l2_tuple_survives_l1",
    "l2_tuple_rank_at_l1",
    "min_normalized_margin_l1",
    "min_normalized_margin_global",
    "normalized_reconstruction_global",
)

POLICY_ACCEPT_CORRECT_L2 = "ACCEPT_CORRECT_L2"
POLICY_ACCEPT_WRONG_L2 = "ACCEPT_WRONG_L2"
POLICY_ACCEPT_CORRECT_L1 = "ACCEPT_CORRECT_L1"
POLICY_ACCEPT_WRONG_L1 = "ACCEPT_WRONG_L1"
POLICY_ACCEPT_CORRECT_GLOBAL = "ACCEPT_CORRECT_GLOBAL"
POLICY_ACCEPT_WRONG_GLOBAL = "ACCEPT_WRONG_GLOBAL"
POLICY_ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class ExperimentCell:
    label: str
    anomaly_rate: float
    context_accuracy: float


PRIMARY_CELL = ExperimentCell("COLLAPSE_SINGLE", anomaly_rate=0.1, context_accuracy=0.9)
STRESS_CELL = ExperimentCell("COLLAPSE_SINGLE", anomaly_rate=0.25, context_accuracy=0.7)
EASY_CELL = ExperimentCell("EASY_SINGLE", anomaly_rate=0.1, context_accuracy=0.9)
DIAGNOSTIC_CELL = ExperimentCell("HARD_STRUCTURED_MIXTURE", anomaly_rate=0.1, context_accuracy=0.9)

POLICY_CELLS = (PRIMARY_CELL, STRESS_CELL, EASY_CELL, DIAGNOSTIC_CELL)
CALIBRATION_CELLS = (PRIMARY_CELL, STRESS_CELL, EASY_CELL)


@dataclass(frozen=True)
class StageCompute:
    stage_label: str
    iterations: int
    candidate_count: int
    candidate_evaluations: int
    element_operations_proxy: int


@dataclass(frozen=True)
class L2RuntimeEvidence:
    stable_prediction_l2: bool
    iterations_l2: int
    min_normalized_margin_l2: float
    mean_normalized_margin_l2: float
    normalized_reconstruction_l2: float
    context_confidence: float


@dataclass(frozen=True)
class L1RuntimeEvidence:
    stable_prediction_l1: bool
    iterations_l1: int
    l2_tuple_survives_l1: bool
    l2_factor_survival_fraction_at_l1: float
    l2_tuple_rank_at_l1: float
    prediction_agreement_l2_l1: float
    min_normalized_margin_l1: float
    mean_normalized_margin_l1: float
    normalized_reconstruction_l1: float
    reconstruction_delta_l1_minus_l2: float
    margin_delta_l1_minus_l2: float


@dataclass(frozen=True)
class GlobalRuntimeEvidence:
    stable_prediction_global: bool
    iterations_global: int
    prediction_agreement_l1_global: float
    l1_tuple_rank_at_global: float
    normalized_reconstruction_global: float
    min_normalized_margin_global: float
    mean_normalized_margin_global: float


@dataclass(frozen=True)
class PolicyInput:
    l2: L2RuntimeEvidence
    l1: L1RuntimeEvidence
    global_stage: GlobalRuntimeEvidence
    l2_compute: StageCompute
    l1_compute: StageCompute
    global_compute: StageCompute


@dataclass(frozen=True)
class PolicyThresholds:
    l2_min_margin: float
    l2_reconstruction: float
    l1_rank_max: float
    l1_min_margin: float
    global_min_margin: float
    global_reconstruction: float


@dataclass(frozen=True)
class SelectedPolicy:
    policy_version: str
    schema_version: str
    features: tuple[str, ...]
    thresholds: PolicyThresholds
    calibration_seed_range: dict[str, dict[str, int]]
    target_risk: float
    achieved_calibration_risk: float
    calibration_coverage: float
    selection_rule: str
    fallback_risk_target_used: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["thresholds"] = asdict(self.thresholds)
        return payload


@dataclass(frozen=True)
class PolicyDecision:
    accepted_stage: str | None
    ran_l2: bool
    ran_l1: bool
    ran_global: bool
    total_iterations: int
    candidate_evaluations: int
    element_operations_proxy: int


def cell_seed_ranges(master_seed: int, trials_per_cell: int) -> dict[str, dict[str, int]]:
    return {
        PRIMARY_CELL.label: {"start": master_seed, "count": trials_per_cell},
        DIAGNOSTIC_CELL.label: {"start": master_seed + 10_000, "count": trials_per_cell},
        EASY_CELL.label: {"start": master_seed + 20_000, "count": trials_per_cell},
    } | {
        STRESS_CELL.label: {"start": master_seed + 30_000, "count": trials_per_cell},
    }


def level1e_development_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E_DEVELOPMENT_MASTER_SEED, "count": LEVEL1E_DEVELOPMENT_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E_DEVELOPMENT_MASTER_SEED + 10_000, "count": LEVEL1E_DEVELOPMENT_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E_DEVELOPMENT_MASTER_SEED + 20_000, "count": LEVEL1E_DEVELOPMENT_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E_DEVELOPMENT_MASTER_SEED + 30_000, "count": LEVEL1E_DEVELOPMENT_TRIALS_PER_CELL},
    }


def level1e_calibration_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E_CALIBRATION_MASTER_SEED, "count": LEVEL1E_CALIBRATION_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E_CALIBRATION_MASTER_SEED + 10_000, "count": LEVEL1E_CALIBRATION_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E_CALIBRATION_MASTER_SEED + 20_000, "count": LEVEL1E_CALIBRATION_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E_CALIBRATION_MASTER_SEED + 30_000, "count": LEVEL1E_CALIBRATION_TRIALS_PER_CELL},
    }


def level1e_heldout_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        "COLLAPSE_SINGLE_PRIMARY": {"start": LEVEL1E_HELDOUT_MASTER_SEED, "count": LEVEL1E_HELDOUT_TRIALS_PER_CELL},
        "COLLAPSE_SINGLE_STRESS": {"start": LEVEL1E_HELDOUT_MASTER_SEED + 10_000, "count": LEVEL1E_HELDOUT_TRIALS_PER_CELL},
        "EASY_SINGLE": {"start": LEVEL1E_HELDOUT_MASTER_SEED + 20_000, "count": LEVEL1E_HELDOUT_TRIALS_PER_CELL},
        "HARD_STRUCTURED_MIXTURE": {"start": LEVEL1E_HELDOUT_MASTER_SEED + 30_000, "count": LEVEL1E_HELDOUT_TRIALS_PER_CELL},
    }


def seed_ranges_to_set(seed_ranges: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in seed_ranges.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level1e_development_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e_development_seed_ranges())


def level1e_calibration_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e_calibration_seed_ranges())


def level1e_heldout_seed_set() -> set[int]:
    return seed_ranges_to_set(level1e_heldout_seed_ranges())


def selective_seed_sets_non_overlapping() -> bool:
    return (
        level1e_development_seed_set().isdisjoint(level1e_calibration_seed_set())
        and level1e_development_seed_set().isdisjoint(level1e_heldout_seed_set())
        and level1e_calibration_seed_set().isdisjoint(level1e_heldout_seed_set())
        and level1e_development_seed_set().isdisjoint(level1d_calibration_seed_set())
        and level1e_development_seed_set().isdisjoint(level1d_evaluation_seed_set())
        and level1e_calibration_seed_set().isdisjoint(level1d_calibration_seed_set())
        and level1e_calibration_seed_set().isdisjoint(level1d_evaluation_seed_set())
        and level1e_heldout_seed_set().isdisjoint(level1d_calibration_seed_set())
        and level1e_heldout_seed_set().isdisjoint(level1d_evaluation_seed_set())
        and level1e_development_seed_set().isdisjoint(pilot_seed_set())
        and level1e_calibration_seed_set().isdisjoint(pilot_seed_set())
        and level1e_heldout_seed_set().isdisjoint(pilot_seed_set())
    )


def correct_query_outcome(query_outcome: str) -> bool:
    return query_outcome in (QUERY_OUTCOME_TARGET_RECOVERY, QUERY_OUTCOME_EQUIVALENT_VALID)


def compute_context_confidence(prior_weights: list[list[float]] | None = None) -> float:
    if not prior_weights:
        return 0.0
    maxima = [max(weights) for weights in prior_weights]
    return float(sum(maxima) / len(maxima))


def tuple_agreement_fraction(lhs: list[int], rhs: list[int]) -> float:
    return sum(int(left == right) for left, right in zip(lhs, rhs, strict=False)) / len(lhs)


def stage_compute_from_snapshot(snapshot: dict[str, Any]) -> StageCompute:
    return StageCompute(
        stage_label=snapshot["stage_label"],
        iterations=int(snapshot["iterations"]),
        candidate_count=int(snapshot["candidate_count"]),
        candidate_evaluations=int(snapshot["candidate_evaluations_proxy"]),
        element_operations_proxy=int(snapshot["element_operations_proxy"]),
    )


def stage_min_margin(snapshot: dict[str, Any]) -> float:
    return float(min(snapshot["normalized_margin"]))


def stage_mean_margin(snapshot: dict[str, Any]) -> float:
    return float(statistics.fmean(snapshot["normalized_margin"]))


def make_policy_input(
    l2_snapshot: dict[str, Any],
    l1_snapshot: dict[str, Any],
    global_snapshot: dict[str, Any],
    stability: dict[str, Any],
    context_confidence: float,
) -> PolicyInput:
    l2_prediction = l2_snapshot["predicted_tuple"]
    l1_prediction = l1_snapshot["predicted_tuple"]
    global_prediction = global_snapshot["predicted_tuple"]
    return PolicyInput(
        l2=L2RuntimeEvidence(
            stable_prediction_l2=bool(l2_snapshot["stable_prediction"]),
            iterations_l2=int(l2_snapshot["iterations"]),
            min_normalized_margin_l2=stage_min_margin(l2_snapshot),
            mean_normalized_margin_l2=stage_mean_margin(l2_snapshot),
            normalized_reconstruction_l2=float(l2_snapshot["normalized_reconstruction_similarity"]),
            context_confidence=context_confidence,
        ),
        l1=L1RuntimeEvidence(
            stable_prediction_l1=bool(l1_snapshot["stable_prediction"]),
            iterations_l1=int(l1_snapshot["iterations"]),
            l2_tuple_survives_l1=bool(stability["l2_prediction_survives_l1"]),
            l2_factor_survival_fraction_at_l1=tuple_agreement_fraction(l2_prediction, l1_prediction),
            l2_tuple_rank_at_l1=float(stability["l2_rank_at_l1"]),
            prediction_agreement_l2_l1=tuple_agreement_fraction(l2_prediction, l1_prediction),
            min_normalized_margin_l1=stage_min_margin(l1_snapshot),
            mean_normalized_margin_l1=stage_mean_margin(l1_snapshot),
            normalized_reconstruction_l1=float(l1_snapshot["normalized_reconstruction_similarity"]),
            reconstruction_delta_l1_minus_l2=float(
                l1_snapshot["normalized_reconstruction_similarity"] - l2_snapshot["normalized_reconstruction_similarity"]
            ),
            margin_delta_l1_minus_l2=float(stage_mean_margin(l1_snapshot) - stage_mean_margin(l2_snapshot)),
        ),
        global_stage=GlobalRuntimeEvidence(
            stable_prediction_global=bool(global_snapshot["stable_prediction"]),
            iterations_global=int(global_snapshot["iterations"]),
            prediction_agreement_l1_global=tuple_agreement_fraction(l1_prediction, global_prediction),
            l1_tuple_rank_at_global=float(stability["l1_rank_at_global"]),
            normalized_reconstruction_global=float(global_snapshot["normalized_reconstruction_similarity"]),
            min_normalized_margin_global=stage_min_margin(global_snapshot),
            mean_normalized_margin_global=stage_mean_margin(global_snapshot),
        ),
        l2_compute=stage_compute_from_snapshot(l2_snapshot),
        l1_compute=stage_compute_from_snapshot(l1_snapshot),
        global_compute=stage_compute_from_snapshot(global_snapshot),
    )


def l2_accepts(evidence: L2RuntimeEvidence, thresholds: PolicyThresholds) -> bool:
    return (
        evidence.stable_prediction_l2
        and evidence.min_normalized_margin_l2 >= thresholds.l2_min_margin
        and evidence.normalized_reconstruction_l2 >= thresholds.l2_reconstruction
    )


def l1_accepts(evidence: L1RuntimeEvidence, thresholds: PolicyThresholds) -> bool:
    return (
        evidence.stable_prediction_l1
        and evidence.l2_tuple_survives_l1
        and evidence.l2_tuple_rank_at_l1 <= thresholds.l1_rank_max
        and evidence.min_normalized_margin_l1 >= thresholds.l1_min_margin
    )


def global_accepts(evidence: GlobalRuntimeEvidence, thresholds: PolicyThresholds) -> bool:
    return (
        evidence.stable_prediction_global
        and evidence.min_normalized_margin_global >= thresholds.global_min_margin
        and evidence.normalized_reconstruction_global >= thresholds.global_reconstruction
    )


def run_adaptive_policy(policy_input: PolicyInput, selected_policy: SelectedPolicy) -> PolicyDecision:
    thresholds = selected_policy.thresholds
    ran_l2 = True
    ran_l1 = False
    ran_global = False
    total_iterations = policy_input.l2_compute.iterations
    candidate_evaluations = policy_input.l2_compute.candidate_evaluations
    element_operations = policy_input.l2_compute.element_operations_proxy

    if l2_accepts(policy_input.l2, thresholds):
        return PolicyDecision("L2", ran_l2, ran_l1, ran_global, total_iterations, candidate_evaluations, element_operations)

    ran_l1 = True
    total_iterations += policy_input.l1_compute.iterations
    candidate_evaluations += policy_input.l1_compute.candidate_evaluations
    element_operations += policy_input.l1_compute.element_operations_proxy
    if l1_accepts(policy_input.l1, thresholds):
        return PolicyDecision("L1", ran_l2, ran_l1, ran_global, total_iterations, candidate_evaluations, element_operations)

    ran_global = True
    total_iterations += policy_input.global_compute.iterations
    candidate_evaluations += policy_input.global_compute.candidate_evaluations
    element_operations += policy_input.global_compute.element_operations_proxy
    if global_accepts(policy_input.global_stage, thresholds):
        return PolicyDecision("GLOBAL", ran_l2, ran_l1, ran_global, total_iterations, candidate_evaluations, element_operations)

    return PolicyDecision(None, ran_l2, ran_l1, ran_global, total_iterations, candidate_evaluations, element_operations)


def compute_selective_risk(accepted_correct: int, accepted_total: int) -> float:
    if accepted_total == 0:
        return 0.0
    return 1.0 - (accepted_correct / accepted_total)


def compute_coverage(accepted_total: int, total_trials: int) -> float:
    if total_trials <= 0:
        raise ValueError("total_trials must be positive.")
    return accepted_total / total_trials


def decision_outcome_label(accepted_stage: str | None, final_query_outcome: str) -> str:
    if accepted_stage is None:
        return POLICY_ABSTAIN
    correct = correct_query_outcome(final_query_outcome)
    if accepted_stage == "L2":
        return POLICY_ACCEPT_CORRECT_L2 if correct else POLICY_ACCEPT_WRONG_L2
    if accepted_stage == "L1":
        return POLICY_ACCEPT_CORRECT_L1 if correct else POLICY_ACCEPT_WRONG_L1
    if accepted_stage == "GLOBAL":
        return POLICY_ACCEPT_CORRECT_GLOBAL if correct else POLICY_ACCEPT_WRONG_GLOBAL
    raise ValueError(f"Unknown accepted stage: {accepted_stage}")


def policy_threshold_grid() -> list[PolicyThresholds]:
    thresholds = []
    for l2_margin in (0.05, 0.10, 0.15, 0.20):
        for l2_recon in (0.05, 0.10, 0.15, 0.20):
            for l1_rank_max in (1.0, 1.5, 2.0):
                for l1_margin in (0.05, 0.10, 0.15):
                    for global_margin in (0.05, 0.10, 0.15):
                        for global_recon in (0.05, 0.10, 0.15):
                            thresholds.append(
                                PolicyThresholds(
                                    l2_min_margin=l2_margin,
                                    l2_reconstruction=l2_recon,
                                    l1_rank_max=l1_rank_max,
                                    l1_min_margin=l1_margin,
                                    global_min_margin=global_margin,
                                    global_reconstruction=global_recon,
                                )
                            )
    return thresholds


def policy_complexity_score(_thresholds: PolicyThresholds) -> int:
    return 6


def compute_frontier_rows(
    calibration_rows: list[dict[str, Any]],
    calibration_seed_range: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], SelectedPolicy]:
    frontier_rows = []
    for policy_id, thresholds in enumerate(policy_threshold_grid(), start=1):
        accepted_total = 0
        accepted_correct = 0
        false_accepts = 0
        l1_escalations = 0
        global_escalations = 0
        abstentions = 0
        compute_values = []
        for row in calibration_rows:
            decision: PolicyDecision = run_adaptive_policy(row["policy_input"], SelectedPolicy(
                policy_version=POLICY_VERSION,
                schema_version=SELECTIVE_SCHEMA_VERSION,
                features=row["features"],
                thresholds=thresholds,
                calibration_seed_range=calibration_seed_range,
                target_risk=TARGET_RISK_PRIMARY,
                achieved_calibration_risk=0.0,
                calibration_coverage=0.0,
                selection_rule="pending",
                fallback_risk_target_used=False,
            ))
            compute_values.append(decision.element_operations_proxy)
            if decision.accepted_stage is None:
                abstentions += 1
            else:
                accepted_total += 1
                if decision.accepted_stage in ("L1", "GLOBAL"):
                    l1_escalations += 1
                if decision.accepted_stage == "GLOBAL":
                    global_escalations += 1
                if correct_query_outcome(row["query_outcome_by_stage"][decision.accepted_stage]):
                    accepted_correct += 1
                else:
                    false_accepts += 1

        total_trials = len(calibration_rows)
        selective_risk = compute_selective_risk(accepted_correct, accepted_total)
        coverage = compute_coverage(accepted_total, total_trials)
        frontier_rows.append(
            {
                "policy_id": f"P{policy_id:04d}",
                "thresholds": json.dumps(asdict(thresholds), ensure_ascii=True, sort_keys=True),
                "coverage": coverage,
                "selective_risk": selective_risk,
                "mean_compute": sum(compute_values) / total_trials,
                "global_escalation_rate": global_escalations / total_trials,
                "abstention_rate": abstentions / total_trials,
                "false_accept_rate": false_accepts / total_trials,
                "overall_correct_accept_rate": accepted_correct / total_trials,
                "complexity": policy_complexity_score(thresholds),
                "thresholds_obj": thresholds,
            }
        )

    def choose_best(target_risk: float) -> dict[str, Any] | None:
        feasible = [row for row in frontier_rows if row["selective_risk"] <= target_risk]
        if not feasible:
            return None
        return min(
            feasible,
            key=lambda row: (-row["coverage"], row["mean_compute"], row["complexity"], row["policy_id"]),
        )

    chosen = choose_best(TARGET_RISK_PRIMARY)
    fallback_used = False
    if chosen is None:
        chosen = choose_best(TARGET_RISK_FALLBACK)
        fallback_used = True
    if chosen is None:
        chosen = min(frontier_rows, key=lambda row: (row["selective_risk"], -row["coverage"], row["mean_compute"], row["policy_id"]))
        fallback_used = True

    selected_policy = SelectedPolicy(
        policy_version=POLICY_VERSION,
        schema_version=SELECTIVE_SCHEMA_VERSION,
        features=SELECTIVE_POLICY_FEATURES,
        thresholds=chosen["thresholds_obj"],
        calibration_seed_range=calibration_seed_range,
        target_risk=TARGET_RISK_PRIMARY,
        achieved_calibration_risk=chosen["selective_risk"],
        calibration_coverage=chosen["coverage"],
        selection_rule="max coverage under target risk, then lower mean compute, then lower complexity",
        fallback_risk_target_used=fallback_used and chosen["selective_risk"] > TARGET_RISK_PRIMARY,
    )
    for row in frontier_rows:
        row.pop("thresholds_obj")
    return frontier_rows, selected_policy


def summarize_policy_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault((record["cell_id"], record["policy_id"]), []).append(record)

    summary_rows = []
    for (cell_id, policy_id), batch in sorted(grouped.items()):
        total = len(batch)
        accepted = [row for row in batch if row["accepted_stage"] is not None]
        correct = [row for row in accepted if row["accepted_correct"]]
        false_accept = [row for row in accepted if not row["accepted_correct"]]
        risk = compute_selective_risk(len(correct), len(accepted))
        coverage = compute_coverage(len(accepted), total)
        risk_low, risk_high = wilson_interval(len(false_accept), len(accepted)) if accepted else (0.0, 0.0)
        coverage_low, coverage_high = wilson_interval(len(accepted), total)
        summary_rows.append(
            {
                "schema_version": SELECTIVE_SCHEMA_VERSION,
                "cell_id": cell_id,
                "policy_id": policy_id,
                "trials": total,
                "coverage": coverage,
                "coverage_ci_low": coverage_low,
                "coverage_ci_high": coverage_high,
                "selective_risk": risk,
                "selective_risk_ci_low": risk_low,
                "selective_risk_ci_high": risk_high,
                "overall_correct_accept_rate": len(correct) / total,
                "false_accept_rate": len(false_accept) / total,
                "abstention_rate": sum(row["accepted_stage"] is None for row in batch) / total,
                "l1_escalation_rate": sum(row["ran_l1"] for row in batch) / total,
                "global_escalation_rate": sum(row["ran_global"] for row in batch) / total,
                "mean_compute": sum(row["element_operations_proxy"] for row in batch) / total,
                "median_compute": statistics.median(row["element_operations_proxy"] for row in batch),
                "p90_compute": sorted(row["element_operations_proxy"] for row in batch)[math.ceil(0.9 * total) - 1],
                "accept_correct_l2_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_CORRECT_L2 for row in batch) / total,
                "accept_wrong_l2_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_WRONG_L2 for row in batch) / total,
                "accept_correct_l1_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_CORRECT_L1 for row in batch) / total,
                "accept_wrong_l1_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_WRONG_L1 for row in batch) / total,
                "accept_correct_global_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_CORRECT_GLOBAL for row in batch) / total,
                "accept_wrong_global_rate": sum(row["policy_outcome"] == POLICY_ACCEPT_WRONG_GLOBAL for row in batch) / total,
            }
        )
    return summary_rows


def compute_cross_scale_consistency(stage_rows: list[dict[str, Any]]) -> dict[str, Any]:
    survives = [row for row in stage_rows if row["l2_tuple_survives_l1"]]
    not_survives = [row for row in stage_rows if not row["l2_tuple_survives_l1"]]
    rank1 = [row for row in stage_rows if row["l2_tuple_rank_at_l1"] <= 1.0]
    rank_gt1 = [row for row in stage_rows if row["l2_tuple_rank_at_l1"] > 1.0]

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        correct = sum(row["l2_prediction_correct"] for row in rows)
        if total == 0:
            return {"rate": None, "ci_low": None, "ci_high": None, "total": 0}
        low, high = wilson_interval(correct, total)
        return {"rate": correct / total, "ci_low": low, "ci_high": high, "total": total}

    return {
        "P(correct | survives L1)": summarize(survives),
        "P(correct | does not survive L1)": summarize(not_survives),
        "P(correct | rank_at_L1 = 1)": summarize(rank1),
        "P(correct | rank_at_L1 > 1)": summarize(rank_gt1),
    }


def compute_stage_hit_rates_among_all_trials(stage_analysis: dict[str, Any], total_trials: int) -> dict[str, Any]:
    valid_counts = stage_analysis["oracle_earliest_valid_stage_counts"]
    target_counts = stage_analysis["oracle_earliest_target_stage_counts"]
    valid_before_global = (valid_counts["L2_narrow"] + valid_counts["L1_parent"]) / total_trials
    target_before_global = (target_counts["L2_narrow"] + target_counts["L1_parent"]) / total_trials
    return {
        "oracle_earliest_valid_before_global_hit_rate_among_all_trials": valid_before_global,
        "oracle_earliest_target_before_global_hit_rate_among_all_trials": target_before_global,
        "invariant_target_le_valid_same_denominator": target_before_global <= valid_before_global + 1e-12,
        "explanation": (
            "Older v4 reports divided valid and target early-stage hits by different totals "
            "(valid-hit total vs target-hit total), so those percentages were conditional and not directly comparable."
        ),
    }


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write empty CSV.")
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
