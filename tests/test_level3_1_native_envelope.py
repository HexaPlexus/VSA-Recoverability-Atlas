from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cgrn_hsr.level3_1_experiment import (
    LEVEL3_1_SCHEMA_VERSION,
    SOURCE_LEDGER,
    U0_TRIALS_PER_POINT,
    U1_TRIALS_PER_POINT,
    build_u1_manifest,
    linear_code_replication_decision,
    source_amendment_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_holovec_implementation_separated_from_attention_algorithm() -> None:
    payload = source_amendment_payload()
    distinction = payload["attention_distinction"]
    assert distinction["holovec_implementation_verdict"] == "BLOCK_TASK_MISMATCH"
    assert distinction["attention_paper_algorithm_verdict"] in {"REPLICATE_PAPER", "DEFER_REPLICATION"}
    assert distinction["holovec_is_not_the_attention_algorithm_family"] is True


def test_source_ledger_includes_all_audited_candidate_families() -> None:
    families = {entry.family for entry in SOURCE_LEDGER}
    assert {
        "classic_resonator",
        "attention_resonator_algorithm",
        "holovec_implementation",
        "ibm_bcf",
        "linear_code_hdc",
        "histogram_recovery",
        "full_tensor_product",
        "fhrr_cleanup",
        "coupled_diffusion",
    }.issubset(families)


def test_abstract_task_manifest_is_representation_independent() -> None:
    manifest, task, _ = build_u1_manifest(12345, 3, 10)
    assert manifest["task_contract"] == "U1_blind_single_product_factorization"
    assert "tensor" not in repr(manifest).lower()
    assert task.context_membership == {}
    assert task.active_context == ""


def test_map_and_bcf_share_true_factor_identities_and_indices() -> None:
    manifest, task, _ = build_u1_manifest(12346, 2, 10)
    assert manifest["true_factor_indices"] == task.target_indices
    assert manifest["factor_identity_tokens"][0][task.target_indices[0]] == f"f0_i{task.target_indices[0]}"
    assert manifest["factor_identity_tokens"][1][task.target_indices[1]] == f"f1_i{task.target_indices[1]}"


def test_context_and_semantic_pruning_are_absent() -> None:
    payload = _load("results/level3_1/analysis.json")
    assert payload["context_or_pruning_used"] is False


def test_bcf_uses_native_stopping_not_cap_16() -> None:
    payload = _load("results/level3_1/bcf_native_reproduction.json")
    assert "cap=16" in payload["removal_of_cap_16_artifact"]
    assert payload["gate_passed"] in {True, False}


def test_official_bcf_reproduction_precedes_comparison() -> None:
    payload = _load("results/level3_1/analysis.json")
    assert payload["official_bcf_reproduction_precedes_common_comparison"] is True


def test_materialization_and_decode_timing_are_separated() -> None:
    resource_path = ROOT / "results" / "level3_1" / "resource_summary.csv"
    header = resource_path.read_text(encoding="utf-8").splitlines()[0]
    assert "representation_materialization_time_sec" in header
    assert "decoder_initialization_time_sec" in header
    assert "decode_time_sec" in header


def test_u0_and_u1_results_are_never_aggregated() -> None:
    payload = _load("results/level3_1/analysis.json")
    assert payload["u0_u1_aggregated"] is False


def test_development_uses_16_trials_per_point() -> None:
    assert U1_TRIALS_PER_POINT == 16
    assert U0_TRIALS_PER_POINT == 16
    rows = (ROOT / "results" / "level3_1" / "u1_boundary_summary.csv").read_text(encoding="utf-8").splitlines()[1:]
    assert rows
    for line in rows:
        assert ",16," in f",{line},"


def test_no_heldout_split_is_consumed() -> None:
    payload = _load("results/level3_1/analysis.json")
    assert payload["heldout_used"] is False


def test_no_new_decoder_implemented() -> None:
    assert not (ROOT / "src" / "cgrn_hsr" / "linear_code_decoder.py").exists()
    assert not (ROOT / "src" / "cgrn_hsr" / "attention_resonator.py").exists()


def test_linear_code_output_is_decision_only() -> None:
    payload = linear_code_replication_decision()
    assert payload["verdict"] in {
        "GO_REPLICATE_MINIMAL",
        "DEFER_UNTIL_U2",
        "DEFER_UPSTREAM",
        "BLOCK_TASK_MISMATCH",
    }
    assert "validation_plan" in payload


def test_cnm_remains_deferred() -> None:
    payload = _load("results/level2b0/final_verdicts.json")
    assert payload["cnm"] == "DEFERRED"


def test_level1_and_level2_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level1*",
            "results/level2*",
            "docs/LEVEL1*",
            "docs/LEVEL2*",
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
        "docs/LEVEL3_1_NATIVE_REPRODUCTION.md",
        "docs/LEVEL3_1_DEVELOPMENT_BOUNDARY.md",
        "results/level3_1/environment.json",
        "results/level3_1/source_amendment.json",
        "results/level3_1/abstract_task_manifest.jsonl",
        "results/level3_1/map_native_reproduction.json",
        "results/level3_1/bcf_native_reproduction.json",
        "results/level3_1/u0_map_cleanup_trials.jsonl",
        "results/level3_1/u0_map_cleanup_summary.csv",
        "results/level3_1/u1_development_trials.jsonl",
        "results/level3_1/u1_boundary_summary.csv",
        "results/level3_1/resource_summary.csv",
        "results/level3_1/pareto_candidates.csv",
        "results/level3_1/linear_code_replication_decision.json",
        "results/level3_1/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_artifact_schema_version_matches() -> None:
    payload = _load("results/level3_1/analysis.json")
    assert payload["schema_version"] == LEVEL3_1_SCHEMA_VERSION
