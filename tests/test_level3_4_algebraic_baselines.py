from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import numpy as np

from cgrn_hsr.level3_4_algebraic_baselines import (
    LEVEL3_4_SCHEMA_VERSION,
    OUTCOME_INCONSISTENT,
    OUTCOME_UNASSIGNED,
    bits_for_m,
    decode_factor_messages,
    generic_decode,
    generic_matrix,
    level3_4_seed_set,
    neco_decode,
    neco_subcodes,
    prior_seed_set,
    seeds_are_fresh,
)
from cgrn_hsr.competitors.ibm_bcf_audit import AbstractFactorizationTask
from cgrn_hsr.level3_3_neco_reproduction import bind_codewords_bits, gf2_rank, materialize_factor_codewords

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def _load_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sample_task(domain_size: int = 10, factor_count: int = 3) -> AbstractFactorizationTask:
    return AbstractFactorizationTask(
        task_seed=1,
        factor_count=factor_count,
        domain_size_per_factor=[domain_size] * factor_count,
        target_indices=[0] * factor_count,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )


def test_packed_payload_uses_ceil_log2_m_per_factor() -> None:
    configs = _load("results/level3_4/representation_configs.json")
    for row in configs["rows"]:
        expected = [bits_for_m(int(row["domain_size"]))] * int(row["factor_count"])
        assert row["message_dimension_per_factor"] == expected


def test_exactly_m_identities_are_assigned() -> None:
    configs = _load("results/level3_4/representation_configs.json")
    for row in configs["rows"]:
        domain_size = int(row["domain_size"])
        assert row["assigned_identities_per_factor"] == [domain_size] * int(row["factor_count"])


def test_unused_messages_return_unassigned_codeword() -> None:
    task = _sample_task(domain_size=10, factor_count=1)
    decoded = decode_factor_messages([np.array([0, 1, 0, 1], dtype=np.uint8)], task)
    assert decoded.outcome == OUTCOME_UNASSIGNED


def test_generic_matrix_has_required_rank() -> None:
    task = _sample_task(domain_size=31, factor_count=3)
    matrix = generic_matrix(task, ambient_length=500, seed=123)
    assert gf2_rank(matrix) == sum([bits_for_m(31)] * 3)


def test_generic_linear_mix_and_neco_use_same_ambient_length() -> None:
    configs = _load("results/level3_4/representation_configs.json")
    assert configs["generic_same_length_required"] is True
    for row in configs["rows"]:
        assert row["ambient_code_length"] == 500


def test_semantic_manifests_are_shared() -> None:
    manifests = _load_jsonl("results/level3_4/task_manifest.jsonl")
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in manifests:
        grouped.setdefault(str(row["trial_id"]), []).append(row)
    for batch in grouped.values():
        assert len(batch) == 1


def test_truth_indices_absent_from_decoders() -> None:
    rows = _load_jsonl("results/level3_4/correctness_trials.jsonl")
    assert rows
    assert all(row["uses_truth_in_decoder"] is False for row in rows)


def test_neco_direct_sum_conditions_are_checked() -> None:
    configs = _load("results/level3_4/representation_configs.json")
    for row in configs["rows"]:
        assert row["generator_rank"] == sum(row["message_dimension_per_factor"])
        assert all(value == 0 for value in row["subcode_intersections"])


def test_persistent_and_runtime_memory_are_separate() -> None:
    summary = _load_csv("results/level3_4/resource_summary.csv")
    for row in summary:
        assert "mean_persistent_spec_bytes" in row
        assert "mean_runtime_materialized_bytes" in row


def test_generator_matrices_are_not_omitted_from_accounting() -> None:
    summary = _load_csv("results/level3_4/resource_summary.csv")
    lookup = {(row["cell_id"], row["arm_id"]): row for row in summary}
    for cell_id in ("u1_clean_m10", "u1_clean_m22", "u1_clean_m31", "u1_clean_m68"):
        assert float(lookup[(cell_id, "generic_random_linear_mix")]["mean_persistent_generator_bytes"]) > 0
        assert float(lookup[(cell_id, "neco_reproduced_direct_sum")]["mean_persistent_generator_bytes"]) > 0


def test_schema_expansion_behavior_is_measured() -> None:
    rows = _load_csv("results/level3_4/schema_update_summary.csv")
    scenarios = {(row["substrate"], row["scenario"]) for row in rows}
    assert ("NECO", "domain_expansion_m31_to_m68") in scenarios
    assert ("GENERIC_LINEAR", "schema_expansion_f3_to_f4") in scenarios


def test_no_noise_or_u2_implementation_exists() -> None:
    analysis = _load("results/level3_4/analysis.json")
    assert analysis["noise_implemented"] is False
    assert analysis["u2_implemented"] is False


def test_map_and_bcf_configurations_remain_frozen() -> None:
    trials = _load_jsonl("results/level3_4/correctness_trials.jsonl")
    arm_ids = {row["arm_id"] for row in trials if row["substrate"] in {"MAP", "BCF"}}
    assert "map_d1024" in arm_ids
    assert "map_d1024_step32_r4_best_native_reconstruction" in arm_ids
    assert "bcf_d512_f3_b4" in arm_ids


def test_level3_3_artifacts_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level3_3/*", "docs/LEVEL3_3*"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_no_heldout_split_consumed() -> None:
    analysis = _load("results/level3_4/analysis.json")
    assert analysis["heldout_used"] is False
    assert seeds_are_fresh() is True
    assert level3_4_seed_set().isdisjoint(prior_seed_set())


def test_generic_control_not_described_as_neco() -> None:
    analysis = _load("results/level3_4/analysis.json")
    assert analysis["generic_control_not_described_as_neco"] is True


def test_packed_symbolic_baseline_is_included() -> None:
    rows = _load_csv("results/level3_4/correctness_summary.csv")
    arm_ids = {row["arm_id"] for row in rows}
    assert "packed_symbolic_tuple" in arm_ids


def test_invalid_outputs_are_typed() -> None:
    task = _sample_task(domain_size=10, factor_count=1)
    matrix = generic_matrix(task, ambient_length=16, seed=777)
    invalid_message = np.array([1, 1, 1, 1], dtype=np.uint8)
    invalid_observation = (matrix @ invalid_message) % 2
    decoded = generic_decode(invalid_observation.astype(np.uint8), task, matrix)
    assert decoded.outcome == OUTCOME_UNASSIGNED

    subcodes, _ = neco_subcodes(task, ambient_length=16, seed=999)
    invalid_neco_observation = bind_codewords_bits(
        materialize_factor_codewords(subcodes, [invalid_message])
    )
    invalid_neco = neco_decode(invalid_neco_observation.astype(np.uint8), task, subcodes)
    assert invalid_neco.outcome == OUTCOME_UNASSIGNED


def test_claims_remain_clean_u1_only() -> None:
    analysis = _load("results/level3_4/analysis.json")
    claims = _load("results/level3_4/claims.json")
    assert analysis["clean_u1_only_claims"] is True
    forbidden = set(claims["forbidden_claims"])
    assert "noise robustness" in forbidden
    assert "production readiness" in forbidden


def test_git_status_clean_after_commit() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "docs/LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md",
            "results/level3_4",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md",
        "results/level3_4/environment.json",
        "results/level3_4/frozen_protocol.json",
        "results/level3_4/task_manifest.jsonl",
        "results/level3_4/representation_configs.json",
        "results/level3_4/correctness_trials.jsonl",
        "results/level3_4/correctness_summary.csv",
        "results/level3_4/resource_summary.csv",
        "results/level3_4/timing_summary.csv",
        "results/level3_4/schema_update_summary.csv",
        "results/level3_4/geometry_summary.csv",
        "results/level3_4/algebraic_control_summary.csv",
        "results/level3_4/claims.json",
        "results/level3_4/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_schema_version_matches() -> None:
    analysis = _load("results/level3_4/analysis.json")
    assert analysis["schema_version"] == LEVEL3_4_SCHEMA_VERSION
