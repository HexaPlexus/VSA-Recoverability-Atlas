from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cgrn_hsr.level3_0_audit import (
    CLAIMS,
    FAIRNESS_CONTRACT,
    LEVEL3_0_SCHEMA_VERSION,
    REPRESENTATION_DECODER_PAIRS,
    TASK_CONTRACTS,
    build_frozen_benchmark_protocol_markdown,
    build_prior_art_matrix_markdown,
    build_production_promotion_gate_markdown,
    build_recovery_task_contracts_markdown,
    write_level3_0_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_u0_u1_u2_u3_are_separated() -> None:
    task_ids = [row["task_id"] for row in TASK_CONTRACTS]
    assert task_ids[:4] == ["U0", "U1", "U2", "U3"]
    assert len({row["name"] for row in TASK_CONTRACTS[:4]}) == 4


def test_every_method_has_an_explicit_task_contract() -> None:
    for row in REPRESENTATION_DECODER_PAIRS:
        contract = row["task_contract"]
        assert all(task_id in contract for task_id in ["U0", "U1", "U2", "U3", "U4", "U5"])


def test_every_implementation_has_an_anti_nih_verdict() -> None:
    allowed = {
        "ADOPT_UPSTREAM",
        "WRAP_UPSTREAM",
        "REPLICATE_PAPER",
        "ORACLE_ONLY",
        "DEFER_UPSTREAM",
        "BLOCK_TASK_MISMATCH",
    }
    assert all(row["verdict"] in allowed for row in REPRESENTATION_DECODER_PAIRS)


def test_no_broad_build_verdict_exists() -> None:
    forbidden = {"BUILD", "CUSTOM", "PROTOTYPE"}
    assert all(row["verdict"] not in forbidden for row in REPRESENTATION_DECODER_PAIRS)


def test_equal_d_is_not_the_sole_fairness_rule() -> None:
    forbidden_shortcuts = FAIRNESS_CONTRACT["forbidden_shortcuts"]
    assert "equal-D as the sole fairness rule" in forbidden_shortcuts


def test_context_mechanisms_are_disabled() -> None:
    payload = _load("results/level3_0/fairness_contract.json")
    disabled = payload["context_mechanisms_disabled"]
    assert "context policy" in disabled
    assert "authority controller" in disabled


def test_production_gate_includes_non_vsa_alternatives() -> None:
    payload = _load("results/level3_0/analysis.json")
    gate_doc = build_production_promotion_gate_markdown()
    assert "Non-VSA alternatives" in gate_doc
    assert payload["new_decoder_added"] is False


def test_paper_reproductions_require_replacement_plan() -> None:
    replicate_rows = [row for row in REPRESENTATION_DECODER_PAIRS if row["verdict"] == "REPLICATE_PAPER"]
    assert replicate_rows
    for row in replicate_rows:
        notes = row["implementation_notes"]
        assert notes["replacement_plan"]
        assert notes["paper_curve_test"]


def test_held_out_protocol_is_frozen_before_execution() -> None:
    payload = _load("results/level3_0/benchmark_manifest.json")
    assert payload["freeze_protocol"]["retuning_after_held_out"] is False
    assert payload["long_experiments_run_during_level3_0"] is False


def test_no_long_benchmark_or_new_decoder_was_added() -> None:
    experiment_source = (ROOT / "experiments" / "level3_0_substrate_audit.py").read_text(encoding="utf-8")
    assert "write_level3_0_artifacts" in experiment_source
    assert "torchhd.resonator" not in experiment_source
    payload = _load("results/level3_0/analysis.json")
    assert payload["long_benchmark_run_added"] is False
    assert payload["new_decoder_added"] is False


def test_level1_level2_cnm_artifacts_remain_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level1*",
            "results/level2*",
            "docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_hypothesis_wording_is_serialized() -> None:
    payload = _load("results/level3_0/claims.json")
    assert payload["schema_version"] == LEVEL3_0_SCHEMA_VERSION
    assert payload["primary_hypothesis"] == CLAIMS["primary_hypothesis"]
    assert payload["null_hypothesis"] == CLAIMS["null_hypothesis"]


def test_artifacts_can_be_regenerated() -> None:
    payloads = write_level3_0_artifacts(ROOT)
    assert payloads["claims.json"]["schema_version"] == LEVEL3_0_SCHEMA_VERSION


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_SUBSTRATE_PRIOR_ART_MATRIX.md",
        "docs/LEVEL3_RECOVERY_TASK_CONTRACTS.md",
        "docs/LEVEL3_FROZEN_BENCHMARK_PROTOCOL.md",
        "docs/LEVEL3_PRODUCTION_PROMOTION_GATE.md",
        "results/level3_0/dependency_audit.json",
        "results/level3_0/representation_decoder_matrix.json",
        "results/level3_0/task_support_matrix.json",
        "results/level3_0/implementation_ladder.json",
        "results/level3_0/benchmark_manifest.json",
        "results/level3_0/fairness_contract.json",
        "results/level3_0/claims.json",
        "results/level3_0/analysis.json",
        "research/level3/README.md",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_markdown_outputs_include_core_sections() -> None:
    assert "Task decomposition" in build_recovery_task_contracts_markdown()
    assert "representation" in build_prior_art_matrix_markdown()
    assert "Phase-boundary protocol" in build_frozen_benchmark_protocol_markdown()
    assert "Non-VSA alternatives" in build_production_promotion_gate_markdown()
