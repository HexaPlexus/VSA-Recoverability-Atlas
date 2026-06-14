from __future__ import annotations

import json
from pathlib import Path

import torch

from cgrn_hsr.baseline import (
    BaselineConfig,
    build_trial_problem,
    classify_false_consensus,
    decode_top_candidates,
    run_trial,
    save_operating_points,
    save_summary_csv,
    save_trials_jsonl,
    select_operating_points,
    summarize_trials,
)


def test_trial_is_deterministic_for_same_seed() -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, external_noise=0)
    first = run_trial(config, seed=12345, master_seed=20260614)
    second = run_trial(config, seed=12345, master_seed=20260614)

    assert first.to_dict() == second.to_dict()


def test_problem_generation_shapes_and_ground_truth() -> None:
    config = BaselineConfig(dimensions=256, num_factors=4, domain_size=7, external_noise=1)
    problem = build_trial_problem(config, seed=55)

    assert tuple(problem.domains.shape) == (4, 7, 256)
    assert tuple(problem.ground_truth_indices.shape) == (4,)
    assert tuple(problem.ground_truth_factors.shape) == (4, 256)
    assert tuple(problem.initial_estimates.shape) == (4, 256)
    assert tuple(problem.clean_composite.shape) == (256,)
    assert tuple(problem.observation.shape) == (256,)
    assert torch.all(problem.ground_truth_indices.ge(0)).item()
    assert torch.all(problem.ground_truth_indices.lt(config.domain_size)).item()


def test_easy_configuration_exact_recovery() -> None:
    config = BaselineConfig(dimensions=1000, num_factors=3, domain_size=5, external_noise=0)
    result = run_trial(config, seed=7, master_seed=20260614)

    assert result.exact_recovery is True
    assert result.false_consensus is False
    assert result.predicted_indices == result.ground_truth_indices


def test_top1_top2_margin_computation() -> None:
    similarities = torch.tensor(
        [
            [5.0, 3.5, 1.0],
            [2.0, 4.0, 3.5],
        ]
    )
    decoded = decode_top_candidates(similarities)

    assert decoded["top1_indices"].tolist() == [0, 1]
    assert decoded["top2_indices"].tolist() == [1, 2]
    assert decoded["margins"].tolist() == [1.5, 0.5]


def test_false_consensus_classification_for_stable_wrong_answer() -> None:
    assert classify_false_consensus(converged=True, exact_recovery=False) is True
    assert classify_false_consensus(converged=True, exact_recovery=True) is False
    assert classify_false_consensus(converged=False, exact_recovery=False) is False


def test_result_serialization_roundtrip(tmp_path: Path) -> None:
    config = BaselineConfig(dimensions=512, num_factors=3, domain_size=5, external_noise=0)
    result = run_trial(config, seed=123, master_seed=20260614)
    summary_rows = summarize_trials([result])
    operating_points = select_operating_points(summary_rows)

    trials_path = tmp_path / "trials.jsonl"
    summary_path = tmp_path / "summary.csv"
    operating_points_path = tmp_path / "operating_points.json"

    save_trials_jsonl(trials_path, [result])
    save_summary_csv(summary_path, summary_rows)
    save_operating_points(
        operating_points_path,
        operating_points=operating_points,
        master_seed=20260614,
        pilot_grid=[config],
    )

    trial_lines = trials_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(trial_lines) == 1
    assert json.loads(trial_lines[0])["config_id"] == config.config_id()

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "exact_recovery_rate" in summary_text
    assert config.config_id() in summary_text

    payload = json.loads(operating_points_path.read_text(encoding="utf-8"))
    assert payload["schema_version"]
    assert payload["pilot_grid"][0]["config_id"] == config.config_id()
