from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

from cgrn_hsr.temporal_memory import (
    ACTION_ABSTAIN_SEARCH,
    EVENT_AGENT_MISSED,
    LEVEL2A_POLICY_VERSION,
    METHOD_GLOBAL,
    METHOD_INDEX,
    METHOD_ORACLE,
    METHOD_RANDOM,
    METHOD_SEMANTIC,
    METHOD_SEMANTIC_ABSTAIN,
    METHOD_SEMANTIC_FALLBACK,
    OUTCOME_CORRECT_ABSTENTION,
    OUTCOME_STALE_MEMORY_ACTION,
    QUERY_HAZARD,
    QUERY_LOCATION,
    QUERY_TOOL,
    SCENARIO_CONFLICTING,
    SCENARIO_STABLE,
    SCENARIO_UNOBSERVED_MOVEMENT,
    UTILITY_WEIGHTS,
    build_split_trials,
    build_trial,
    choose_selected_policy,
    evaluate_map_method,
    level2a_calibration_seed_ranges,
    level2a_heldout_seed_ranges,
    level2a_seed_sets_non_overlapping,
    oracle_subset,
    random_subset,
    resolve_episode_ids,
    resolved_episode,
    run_level2a,
    scenario_manifest,
    score_episode,
    seed_ranges_to_set,
    semantic_subset,
    summarize_safety,
)

ROOT = Path(__file__).resolve().parents[1]


def test_world_truth_is_separated_from_runtime_observations() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    assert hasattr(trial.truth, "current_locations")
    assert not hasattr(trial.runtime, "current_locations")


def test_unobserved_movement_does_not_enter_memory_as_observed_location() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    target = trial.runtime.query.entity_id
    truth_room = trial.truth.current_locations[target]
    assert all(
        not (
            episode.entity_id == target
            and episode.location == truth_room
            and episode.event_type != EVENT_AGENT_MISSED
        )
        for episode in trial.runtime.memory_episodes
    )


def test_episode_tick_ordering_is_sorted() -> None:
    trial = build_trial(40260614, SCENARIO_CONFLICTING, QUERY_TOOL, "heldout")
    ticks = [episode.tick for episode in trial.runtime.memory_episodes]
    assert ticks == sorted(ticks)


def test_stale_episode_is_classified_separately_from_factorization_error() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    result = evaluate_map_method(trial, METHOD_GLOBAL, trial.runtime.seed + 11, None)
    assert result.behavior_outcome == OUTCOME_STALE_MEMORY_ACTION
    assert result.exact_episode_recovery is False


def test_semantic_and_random_candidate_sets_are_size_matched() -> None:
    trial = build_trial(40260614, SCENARIO_STABLE, QUERY_LOCATION, "heldout")
    semantic = semantic_subset(trial.runtime)
    random = random_subset(trial.runtime, trial.runtime.seed + 1)
    assert len(semantic) == len(random) == trial.runtime.subset_size


def test_semantic_selector_does_not_accept_current_world_truth() -> None:
    signature = inspect.signature(semantic_subset)
    assert "truth" not in signature.parameters
    assert "current_locations" not in inspect.getsource(score_episode)


def test_oracle_selector_is_explicitly_separated() -> None:
    trial = build_trial(40260614, SCENARIO_STABLE, QUERY_LOCATION, "heldout")
    oracle = oracle_subset(trial.runtime, trial.truth, trial.runtime.seed + 5)
    oracle_ids = {episode.episode_id for episode in oracle}
    assert oracle_ids.intersection(trial.truth.oracle_relevant_episode_ids)


def test_paired_methods_share_one_history_and_query() -> None:
    trial = build_trial(40260614, SCENARIO_CONFLICTING, QUERY_HAZARD, "heldout")
    semantic = evaluate_map_method(trial, METHOD_SEMANTIC, trial.runtime.seed + 1, None)
    random = evaluate_map_method(trial, METHOD_RANDOM, trial.runtime.seed + 1, None)
    assert semantic.seed == random.seed == trial.runtime.seed
    assert semantic.query_type == random.query_type == trial.runtime.query.query_type
    assert trial.runtime.query.room is not None


def test_latest_index_baseline_uses_latest_matching_episode() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    result = evaluate_map_method(trial, METHOD_INDEX, trial.runtime.seed + 1, None)
    latest_target_tick = max(
        episode.tick
        for episode in trial.runtime.memory_episodes
        if episode.entity_id == trial.runtime.query.entity_id
    )
    assert result.matched_episode_tick == latest_target_tick


def test_insufficient_evidence_leads_to_abstention() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    result = evaluate_map_method(trial, METHOD_SEMANTIC, trial.runtime.seed + 1, None)
    assert result.action["action_type"] == ACTION_ABSTAIN_SEARCH
    assert result.behavior_outcome == OUTCOME_CORRECT_ABSTENTION


def test_abstention_is_not_counted_as_false_action() -> None:
    trial = build_trial(40260614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout")
    result = evaluate_map_method(trial, METHOD_SEMANTIC, trial.runtime.seed + 1, None)
    assert result.abstained is True
    assert result.false_commit is False


def test_false_commit_rate_calculation_is_correct() -> None:
    rows = [
        evaluate_map_method(build_trial(40260614, SCENARIO_STABLE, QUERY_LOCATION, "heldout"), METHOD_INDEX, 1, None),
        evaluate_map_method(build_trial(40270614, SCENARIO_UNOBSERVED_MOVEMENT, QUERY_LOCATION, "heldout"), METHOD_GLOBAL, 1, None),
    ]
    summary = summarize_safety(rows)
    index_row = next(row for row in summary if row["method_id"] == METHOD_INDEX)
    global_row = next(row for row in summary if row["method_id"] == METHOD_GLOBAL)
    assert index_row["false_commit_rate"] == 0.0
    assert global_row["false_commit_rate"] in (0.0, 1.0)


def test_utility_weights_are_frozen_in_policy_artifact() -> None:
    policy_payload = json.loads((ROOT / "results" / "level2a" / "selected_policy.json").read_text(encoding="utf-8"))
    assert policy_payload["policy_version"] == LEVEL2A_POLICY_VERSION
    assert policy_payload["utility_weights"] == UTILITY_WEIGHTS


def test_calibration_and_heldout_seed_ranges_do_not_overlap() -> None:
    assert level2a_seed_sets_non_overlapping() is True
    assert seed_ranges_to_set(level2a_calibration_seed_ranges()).isdisjoint(seed_ranges_to_set(level2a_heldout_seed_ranges()))


def test_selected_policy_is_chosen_only_from_calibration_trials() -> None:
    policy = choose_selected_policy(build_split_trials(level2a_calibration_seed_ranges(), QUERY_LOCATION, "calibration")[:8])
    assert policy.calibration_seed_ranges == level2a_calibration_seed_ranges()


def test_cold_global_fallback_discards_local_factorizer_state() -> None:
    policy = choose_selected_policy(build_split_trials(level2a_calibration_seed_ranges(), QUERY_LOCATION, "calibration")[:8])
    trial = build_trial(40260614, SCENARIO_STABLE, QUERY_LOCATION, "heldout")
    result = evaluate_map_method(trial, METHOD_SEMANTIC_FALLBACK, trial.runtime.seed + 1, policy)
    if result.used_global_fallback:
        assert result.discarded_local_factorizer_state is True


def test_level1_artifacts_are_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level1a", "results/level1b", "results/level1c", "results/level1d", "results/level1e", "results/level1e1", "results/level1f", "results/level1f2_bcf_audit", "results/level1f3", "results/level1f4"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_bcf_is_not_used_by_level2a_module() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "temporal_memory.py").read_text(encoding="utf-8").lower()
    assert "ibm_bcf" not in source
    assert "competitors" not in source


def test_hypothesis_file_is_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_resolved_episode_prefers_query_relevant_overlap() -> None:
    trial = build_trial(40260614, SCENARIO_STABLE, QUERY_LOCATION, "heldout")
    selected = semantic_subset(trial.runtime)
    predicted = (0, 0, 0, 0, 0, 0)
    resolved = resolved_episode(trial.runtime, selected, predicted)
    assert resolved is not None
    assert resolved.entity_id == trial.runtime.query.entity_id


def test_scenario_manifest_freezes_closed_level1_mechanisms() -> None:
    manifest = scenario_manifest()
    closed = set(manifest["closed_mechanisms_from_level1"])
    assert "warm_estimate_transfer" in closed
    assert "full_l2_l1_global_cascade" in closed


def test_results_artifacts_exist() -> None:
    expected = {
        "scenario_manifest.json",
        "calibration_trials.jsonl",
        "selected_policy.json",
        "heldout_trials.jsonl",
        "retrieval_summary.csv",
        "behavioral_summary.csv",
        "safety_summary.csv",
        "compute_summary.csv",
        "baseline_comparison.csv",
        "scenario_breakdown.csv",
        "analysis.json",
    }
    observed = {path.name for path in (ROOT / "results" / "level2a").iterdir()}
    assert expected.issubset(observed)
