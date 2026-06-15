from __future__ import annotations

import ast
import csv
import json
import subprocess
from pathlib import Path

import torch

from cgrn_hsr.level3_2_confirmation import (
    BCF_CONFIG_FAMILY,
    COMMON_CELLS,
    HELDOUT_SEED_RANGES,
    LEVEL3_2_SCHEMA_VERSION,
    MAP_CONFIGS,
    OPTIONAL_EXTENSION_CELL,
    build_abstract_task_manifest,
    build_frozen_protocol,
    common_outcome,
    level3_2_seed_sets_are_fresh,
    prior_level3_1_seed_set,
    wilson_interval,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_configs_frozen_before_heldout() -> None:
    payload = _load("results/level3_2/frozen_protocol.json")
    assert payload["protocol_frozen_before_first_heldout_run"] is True


def test_heldout_seeds_fresh_and_non_overlapping() -> None:
    assert level3_2_seed_sets_are_fresh() is True
    fresh_starts = [spec["start"] for spec in HELDOUT_SEED_RANGES.values()]
    assert min(fresh_starts) > max(prior_level3_1_seed_set())


def test_no_context_controller_or_cnm_path_imported() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_2_confirmation.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = ("query_context", "selective_policy", "warm_start", "temporal_memory", "splink_context_policy")
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    assert all(token not in module for module in imported_modules for token in forbidden)


def test_no_candidate_pruning() -> None:
    payload = _load("results/level3_2/frozen_protocol.json")
    assert payload["scope"]["candidate_pruning"] is False


def test_no_noise_u2_u3() -> None:
    payload = _load("results/level3_2/frozen_protocol.json")
    assert payload["scope"]["noise"] is False
    assert payload["scope"]["u2"] is False
    assert payload["scope"]["u3"] is False


def test_common_semantic_manifest_shared_across_substrates() -> None:
    manifest, task = build_abstract_task_manifest(70000001, COMMON_CELLS[0])
    assert manifest["true_factor_indices"] == task.target_indices
    assert manifest["split"] == "heldout"


def test_native_representations_materialized_independently() -> None:
    manifest, _ = build_abstract_task_manifest(70000002, COMMON_CELLS[0])
    assert manifest["map_representation_seed"] != manifest["bcf_representation_seed"]


def test_both_map_configs_and_one_bcf_config_fixed() -> None:
    assert [row["config_id"] for row in MAP_CONFIGS] == ["map_d512", "map_d1024"]
    assert BCF_CONFIG_FAMILY["config_family"] == "bcf_d512_f3_b4"


def test_bcf_native_stopping_preserved() -> None:
    trials_path = ROOT / "results" / "level3_2" / "heldout_trials.jsonl"
    with trials_path.open("r", encoding="utf-8") as handle:
        bcf_rows = [json.loads(line) for line in handle if '"substrate": "BCF"' in line]
    assert bcf_rows
    assert all(row["native_max_iterations"] > 16 for row in bcf_rows)


def test_old_cap_16_absent() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_2_confirmation.py").read_text(encoding="utf-8")
    assert "cap=16" not in source


def test_no_config_sweep_in_heldout() -> None:
    payload = _load("results/level3_2/frozen_configs.json")
    assert len(payload["map_configs"]) == 2
    assert payload["bcf_config_family"]["config_family"] == "bcf_d512_f3_b4"


def test_no_optional_cell_added_after_outcomes() -> None:
    payload = _load("results/level3_2/frozen_protocol.json")
    frozen_ids = {row["cell_id"] for row in payload["common_cells"]}
    frozen_ids.add(payload["optional_extension_cell"]["cell_id"])
    analysis = _load("results/level3_2/analysis.json")
    executed = set(analysis["executed_cells"])
    assert executed.issubset(frozen_ids)


def test_wilson_intervals_calculated_correctly() -> None:
    low, high = wilson_interval(64, 64)
    assert 0.94 <= low <= 1.0
    assert high == 1.0


def test_phase_boundary_uses_ge_0_90_rule() -> None:
    payload = _load("results/level3_2/capacity_boundary.csv") if False else None
    rows = list(csv.DictReader((ROOT / "results" / "level3_2" / "capacity_boundary.csv").open("r", encoding="utf-8")))
    assert rows
    assert all(row["boundary_rule"] == ">=0.90 exact recovery" for row in rows)


def test_timing_reports_median_p90_p99() -> None:
    header = (ROOT / "results" / "level3_2" / "timing_summary.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "median_decode_time_sec" in header
    assert "p90_decode_time_sec" in header
    assert "p99_decode_time_sec" in header


def test_m110_classified_separately_if_not_common() -> None:
    assert OPTIONAL_EXTENSION_CELL["classification"] == "BCF_NATIVE_EXTENSION"
    rows = list(csv.DictReader((ROOT / "results" / "level3_2" / "recovery_summary.csv").open("r", encoding="utf-8")))
    ext_rows = [row for row in rows if row["cell_id"] == OPTIONAL_EXTENSION_CELL["cell_id"]]
    assert ext_rows
    assert all(row["cell_classification"] == "BCF_NATIVE_EXTENSION" for row in ext_rows)


def test_no_linear_code_implementation() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "linear_code_decoder.py").exists()


def test_level1_level2_level3_1_and_cnm_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level1*",
            "results/level2*",
            "results/level3_1",
            "docs/LEVEL1*",
            "docs/LEVEL2*",
            "docs/LEVEL3_1*",
            "docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_hypothesis_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_2_CLEAN_U1_CONFIRMATION.md",
        "results/level3_2/environment.json",
        "results/level3_2/frozen_protocol.json",
        "results/level3_2/frozen_configs.json",
        "results/level3_2/heldout_task_manifest.jsonl",
        "results/level3_2/heldout_trials.jsonl",
        "results/level3_2/recovery_summary.csv",
        "results/level3_2/capacity_boundary.csv",
        "results/level3_2/timing_summary.csv",
        "results/level3_2/memory_summary.csv",
        "results/level3_2/iteration_summary.csv",
        "results/level3_2/pareto_summary.csv",
        "results/level3_2/claims.json",
        "results/level3_2/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_common_outcome_examples() -> None:
    target = build_abstract_task_manifest(70000003, COMMON_CELLS[0])[1]
    outcome = common_outcome(
        torch.tensor(target.target_indices, dtype=torch.long),
        torch.tensor(target.target_indices, dtype=torch.long),
    )
    assert outcome[0] == "EXACT_RECOVERY"
