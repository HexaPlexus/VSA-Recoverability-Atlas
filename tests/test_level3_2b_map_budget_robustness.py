from __future__ import annotations

import ast
import csv
import json
import subprocess
from pathlib import Path

from cgrn_hsr.level3_2b_map_budget_robustness import (
    COMPUTE_MATCHED_ARM_IDS,
    LEVEL3_2B_SCHEMA_VERSION,
    MAP_RESTART_SELECTION_RULES,
    SEED_RANGES,
    build_map_arm_configs,
    build_task_manifest,
    level3_2_seed_set,
    level3_2b_seed_sets_are_fresh,
    level3_2b_seed_set,
    prior_level3_1_seed_set,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relpath: str) -> dict[str, object]:
    return json.loads((ROOT / relpath).read_text(encoding="utf-8"))


def test_level3_2_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level3_2",
            "docs/LEVEL3_2_CLEAN_U1_CONFIRMATION.md",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_fresh_seeds_do_not_overlap_earlier_splits() -> None:
    assert level3_2b_seed_sets_are_fresh() is True
    current = level3_2b_seed_set()
    assert current.isdisjoint(prior_level3_1_seed_set())
    assert current.isdisjoint(level3_2_seed_set())
    assert min(spec["start"] for spec in SEED_RANGES.values()) > max(level3_2_seed_set())


def test_u1_clean_only() -> None:
    payload = _load_json("results/level3_2b/frozen_protocol.json")
    assert payload["scope"]["u1_clean_only"] is True
    assert payload["scope"]["noise"] is False
    assert payload["scope"]["erasures"] is False
    assert payload["scope"]["u2"] is False
    assert payload["scope"]["u3"] is False


def test_no_context_controller_or_cnm_imports() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_2b_map_budget_robustness.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = ("query_context", "selective_policy", "warm_start", "temporal_memory", "splink_context_policy")
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    assert all(token not in module for module in imported_modules for token in forbidden)


def test_map_equations_unchanged() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_2b_map_budget_robustness.py").read_text(encoding="utf-8")
    assert "torchhd.resonator(" in source
    assert "def resonator(" not in source


def test_only_steps_restarts_and_budget_vary() -> None:
    rows = build_map_arm_configs(ROOT)
    assert {row.dimensions for row in rows} == {512, 1024}
    assert {row.max_iterations for row in rows if row.compute_matching_mode is None and row.restart_count == 1} == {12, 32, 64, 128}
    assert {
        row.restart_count
        for row in rows
        if row.compute_matching_mode is None and row.selection_rule in MAP_RESTART_SELECTION_RULES
    } == {4}
    assert {
        row.compute_matching_mode
        for row in rows
        if "wallclock_matched_bcf_" in row.arm_id
    } == {"sequential_cold_restarts"}


def test_bcf_config_frozen() -> None:
    payload = _load_json("results/level3_2b/map_arm_configs.json")
    assert payload["frozen_bcf_reference"]["config_family"] == "bcf_d512_f3_b4"


def test_native_stopping_preserved() -> None:
    trials_path = ROOT / "results" / "level3_2b" / "trials.jsonl"
    with trials_path.open("r", encoding="utf-8") as handle:
        bcf_rows = [json.loads(line) for line in handle if '"substrate": "BCF"' in line]
    assert bcf_rows
    assert all(row["uses_official_bcf_class"] for row in bcf_rows)
    assert all(row["max_iterations"] > 16 for row in bcf_rows)


def test_restart_selection_never_uses_truth() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_2b_map_budget_robustness.py").read_text(encoding="utf-8")
    start = source.index("def choose_attempt(")
    end = source.index("def restart_agreement(")
    choose_source = source[start:end]
    assert "true_factor_indices" not in choose_source
    assert "exact_recovery" not in choose_source


def test_random_restart_control_exists() -> None:
    rows = build_map_arm_configs(ROOT)
    assert any(row.selection_rule == "random_restart_selection" for row in rows)


def test_compute_matching_uses_frozen_wall_clock_budgets() -> None:
    payload = _load_json("results/level3_2b/frozen_protocol.json")
    assert payload["frozen_compute_matched_budgets"]
    rows = list(csv.DictReader((ROOT / "results" / "level3_2b" / "compute_matched_summary.csv").open("r", encoding="utf-8")))
    assert any(row["frozen_wallclock_budget_sec"] for row in rows if "wallclock_matched" in row["arm_id"])


def test_no_heldout_split_consumed() -> None:
    analysis = _load_json("results/level3_2b/analysis.json")
    assert analysis["split"] == "development_robustness"
    assert analysis["heldout_used"] is False


def test_no_linear_code_decoder_added() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "linear_code_decoder.py").exists()


def test_results_separated_by_cell_and_dimension() -> None:
    rows = list(csv.DictReader((ROOT / "results" / "level3_2b" / "recovery_summary.csv").open("r", encoding="utf-8")))
    assert rows
    assert "cell_id" in rows[0]
    assert "dimensions" in rows[0]
    assert len({(row["cell_id"], row["dimensions"]) for row in rows}) >= 4


def test_claims_distinguish_development_from_confirmation() -> None:
    payload = _load_json("results/level3_2b/claims.json")
    assert payload["status"] == "development_robustness_only"
    assert "held-out" not in " ".join(payload["allowed_claims"]).lower()


def test_representation_independent_manifest() -> None:
    manifest, task = build_task_manifest(80000001, {"cell_id": "x", "classification": "PRIMARY", "F": 3, "M": 22})
    assert manifest["true_factor_indices"] == task.target_indices
    assert "domains" not in manifest
    assert "observation" not in manifest
    assert manifest["split"] == "development_robustness"
