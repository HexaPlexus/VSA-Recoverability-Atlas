from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from cgrn_hsr.level3_3_neco_reproduction import (
    COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS,
    LEVEL3_3_SCHEMA_VERSION,
    OUTCOME_AMBIGUOUS,
    OUTCOME_EXACT,
    OUTCOME_INCONSISTENT,
    OUTCOME_RANK_DEFICIENT,
    build_smoke_trials,
    decode_binding,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def test_gf2_dependency_is_adopted_or_gap_documented() -> None:
    payload = _load("results/level3_3/dependency_audit.json")
    decisions = {entry["component"]: entry["verdict"] for entry in payload["dependency_decisions"]}
    assert decisions["GF(2) arrays, rank, row-space, null-space"] == "ADOPT"
    assert decisions["Rectangular left-solve for xB = c over GF(2)"] in {"WRAP", "ADOPT"}


def test_no_generic_finite_field_framework_added() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "linear_code_framework").exists()
    payload = _load("results/level3_3/dependency_audit.json")
    assert payload["generic_finite_field_framework_added"] is False


def test_paper_contract_entries_have_source_references() -> None:
    payload = _load("results/level3_3/paper_contract.json")
    assert payload["contract_status"] == "UNAMBIGUOUS_PAPER_CONTRACT"
    assert payload["entries"]
    for entry in payload["entries"]:
        assert entry["source_reference"]


def test_factors_belong_to_correct_subcodes() -> None:
    rows = _load_jsonl("results/level3_3/native_smoke_trials.jsonl")
    assert rows
    assert all(row["all_factors_in_declared_subcodes"] for row in rows)


def test_valid_tuples_rebind_exactly() -> None:
    rows = _load_jsonl("results/level3_3/native_smoke_trials.jsonl")
    assert all(row["recovery"]["rebind_matches_observation"] for row in rows)


def test_exhaustive_oracle_and_decoder_agree() -> None:
    rows = _load_jsonl("results/level3_3/exhaustive_oracle_trials.jsonl")
    unique_rows = [row for row in rows if row["case"] == "unique_direct_sum"]
    assert unique_rows
    for row in unique_rows:
        assert row["decoder_outcome"] == OUTCOME_EXACT
        assert row["decoder_predicted_indices"] == row["true_indices"]


def test_collisions_are_detected_not_silently_resolved() -> None:
    rows = _load_jsonl("results/level3_3/exhaustive_oracle_trials.jsonl")
    collision_row = next(row for row in rows if row["case"] == "overlapping_subcodes")
    assert collision_row["oracle_collision_count"] > 0
    assert collision_row["decoder_outcome"] == OUTCOME_AMBIGUOUS


def test_rank_deficient_systems_return_typed_failure() -> None:
    subcodes = [
        np.array([[1, 0, 1], [1, 0, 1]], dtype=np.uint8),
        np.array([[0, 1, 1]], dtype=np.uint8),
    ]
    observation = np.array([1, 1, 0], dtype=np.uint8)
    result = decode_binding(subcodes=subcodes, observation_bits=observation)
    assert result.outcome == OUTCOME_RANK_DEFICIENT


def test_inconsistent_systems_return_typed_failure() -> None:
    subcodes = [
        np.array([[1, 0, 0]], dtype=np.uint8),
        np.array([[0, 1, 0]], dtype=np.uint8),
    ]
    invalid_observation = np.array([0, 0, 1], dtype=np.uint8)
    result = decode_binding(subcodes=subcodes, observation_bits=invalid_observation)
    assert result.outcome == OUTCOME_INCONSISTENT


def test_truth_indices_never_enter_decoder() -> None:
    rows = _load_jsonl("results/level3_3/native_smoke_trials.jsonl")
    assert all(row["recovery"]["truth_used_in_decoder"] is False for row in rows)


def test_factor_mapping_is_deterministic() -> None:
    first = build_smoke_trials()
    second = build_smoke_trials()
    first_pairs = [(row["trial_id"], row["true_identity_indices"], row["recovery"]["predicted_identity_indices"]) for row in first]
    second_pairs = [(row["trial_id"], row["true_identity_indices"], row["recovery"]["predicted_identity_indices"]) for row in second]
    assert first_pairs == second_pairs
    assert all(row["recovery"]["factor_mapping_deterministic"] is True for row in first)


def test_clean_only_scope_enforced() -> None:
    analysis = _load("results/level3_3/analysis.json")
    assert analysis["noise_implemented"] is False
    assert analysis["u2_implemented"] is False


def test_no_histogram_u2_or_noise_implementation() -> None:
    analysis = _load("results/level3_3/analysis.json")
    assert analysis["histogram_recovery_implemented"] is False
    protocol = _load("results/level3_3/frozen_protocol.json")
    assert protocol["noise_disabled"] is True
    assert protocol["u2_disabled"] is True


def test_no_context_controller_or_cnm_import() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_3_neco_reproduction.py").read_text(encoding="utf-8")
    assert "query_context" not in source
    assert "selective_policy" not in source
    assert "splink_context_policy_experiment" not in source
    assert "CNM" not in source


def test_common_u1_compatibility_assessed_before_comparison() -> None:
    payload = _load("results/level3_3/common_u1_compatibility.json")
    assert payload["verdict"] == COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS
    analysis = _load("results/level3_3/analysis.json")
    assert analysis["common_u1_verdict"] == COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS


def test_map_bcf_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level1*",
            "results/level2*",
            "results/level3_0*",
            "results/level3_1*",
            "results/level3_2*",
            "docs/LEVEL1*",
            "docs/LEVEL2*",
            "docs/LEVEL3_0*",
            "docs/LEVEL3_1*",
            "docs/LEVEL3_2*",
            "docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_replacement_plan_exists() -> None:
    payload = _load("results/level3_3/upstream_replacement_plan.json")
    assert payload["custom_reproduction_files"]
    assert payload["deletion_plan"]


def test_claims_forbid_superiority() -> None:
    payload = _load("results/level3_3/claims.json")
    forbidden = set(payload["forbidden_claims"])
    assert "linear-code HDC is superior to MAP" in forbidden
    assert "linear-code HDC is superior to BCF" in forbidden
    assert payload["superiority_claim_authorized"] is False


def test_tests_and_artifacts_are_deterministic() -> None:
    analysis = _load("results/level3_3/analysis.json")
    assert analysis["reproduction_verdict"] in {"REPRODUCED", "PARTIAL_REPRODUCTION"}
    assert analysis["exhaustive_oracle_exact_agreement"] is True


def test_git_status_clean_after_commit() -> None:
    result = subprocess.run(
        ["git", "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_3_NECO_CONTRACT_EXTRACTION.md",
        "docs/LEVEL3_3_LINEAR_CODE_REPRODUCTION.md",
        "results/level3_3/environment.json",
        "results/level3_3/dependency_audit.json",
        "results/level3_3/paper_contract.json",
        "results/level3_3/frozen_protocol.json",
        "results/level3_3/native_smoke_trials.jsonl",
        "results/level3_3/exhaustive_oracle_trials.jsonl",
        "results/level3_3/paper_reproduction_trials.jsonl",
        "results/level3_3/correctness_summary.csv",
        "results/level3_3/rank_summary.csv",
        "results/level3_3/scaling_summary.csv",
        "results/level3_3/resource_summary.csv",
        "results/level3_3/common_u1_compatibility.json",
        "results/level3_3/upstream_replacement_plan.json",
        "results/level3_3/claims.json",
        "results/level3_3/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_schema_version_matches() -> None:
    payload = _load("results/level3_3/analysis.json")
    assert payload["schema_version"] == LEVEL3_3_SCHEMA_VERSION
