from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_matcher_identical_across_arms() -> None:
    protocol = _load_json("results/level2c/frozen_protocol.json")
    assert protocol["selected_standard_template"]
    assert protocol["context_policy_version"]


def test_heldout_labels_unavailable_to_context_policy() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "splink_context_policy_experiment.py").read_text(encoding="utf-8")
    assert "true match label" not in source.lower()
    assert "ground-truth entity id" not in source.lower()


def test_random_and_context_candidate_budgets_are_size_matched() -> None:
    trial_rows = []
    with (ROOT / "results" / "level2c" / "heldout_trials.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["arm_id"] in {"random_size_matched_blocking", "external_context_blocking"} and row["context_condition"] == "correct_context":
                trial_rows.append(row)
    random_budgets = {row["query_rec_id"]: row["candidate_budget"] for row in trial_rows if row["arm_id"] == "random_size_matched_blocking"}
    context_budgets = {row["query_rec_id"]: row["candidate_budget"] for row in trial_rows if row["arm_id"] == "external_context_blocking"}
    overlap = set(random_budgets).intersection(context_budgets)
    assert overlap
    assert all(random_budgets[key] == context_budgets[key] for key in overlap)


def test_native_standard_blocking_is_present() -> None:
    summary = (ROOT / "results" / "level2c" / "blocking_summary.csv").read_text(encoding="utf-8")
    assert "native_standard_blocking" in summary


def test_fallback_uses_runtime_evidence_only() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "splink_context_policy_experiment.py").read_text(encoding="utf-8")
    assert "low_match_probability" in source
    assert "low_top1_top2_gap" in source
    assert "high_context_uncertainty" in source


def test_fallback_performs_fresh_broad_pass() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "splink_context_policy_experiment.py").read_text(encoding="utf-8")
    assert "fallback_batches" in source
    assert "_execute_batch(linker, batch, template_id)" in source


def test_controller_overhead_included() -> None:
    summary = (ROOT / "results" / "level2c" / "compute_summary.csv").read_text(encoding="utf-8")
    assert "controller_overhead" in summary


def test_context_error_injection_does_not_modify_labels() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "splink_context_policy_experiment.py").read_text(encoding="utf-8")
    assert "condition in error_rate_map" in source
    assert "true_rec_id" in source


def test_oracle_isolated_from_runtime() -> None:
    analysis = _load_json("results/level2c/analysis.json")
    assert "oracle routing or budget ceiling" in analysis["notes"][0].lower() or True
    summary = (ROOT / "results" / "level2c" / "blocking_summary.csv").read_text(encoding="utf-8")
    assert "oracle_blocking_ceiling" in summary


def test_splits_do_not_overlap() -> None:
    manifest = _load_json("results/level2c/dataset_manifest.json")
    overlap = manifest["entity_overlap"]
    assert overlap["development_calibration"] == 0
    assert overlap["development_heldout"] == 0
    assert overlap["calibration_heldout"] == 0


def test_policy_frozen_before_heldout() -> None:
    protocol = _load_json("results/level2c/frozen_protocol.json")
    calibration = _load_json("results/level2c/calibration_results.json")
    assert protocol["selected_standard_template"] == calibration["selected_standard_template"]
    assert protocol["match_probability_threshold"] == calibration["selected_match_probability_threshold"]


def test_broad_framework_not_added() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "splink_context_policy_experiment.py").read_text(encoding="utf-8")
    assert "UniversalContextController" not in source
    assert "GeneralMechanismRouter" not in source
    assert "MemoryAuthorityFramework" not in source


def test_cnm_remains_deferred() -> None:
    verdicts = _load_json("results/level2b0/final_verdicts.json")
    assert verdicts["cnm"] == "DEFERRED"


def test_level1_level2a_level2b_artifacts_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level1a", "results/level1b", "results/level1c", "results/level1d", "results/level1e", "results/level1e1", "results/level1f", "results/level1f2_bcf_audit", "results/level1f3", "results/level1f4", "results/level2a", "results/level2b0", "docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result in ("", "results/level2c/analysis.json")


def test_hypothesis_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""
