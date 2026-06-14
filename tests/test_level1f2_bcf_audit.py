from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cgrn_hsr.competitors.ibm_bcf_audit import (
    BCF_OFFICIAL_CLASS_PATH,
    IBM_BCF_AUDIT_SCHEMA_VERSION,
    AbstractFactorizationTask,
    compute_file_sha256,
    is_json_roundtrippable,
    load_recorded_json,
    upstream_clone_path,
    upstream_commit_sha,
    upstream_tracked_source_clean,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results" / "level1f2_bcf_audit"


def read_result(name: str) -> dict:
    return load_recorded_json(RESULTS_DIR / name)


def test_dependency_audit_records_exact_commit_and_license() -> None:
    dependency = read_result("dependency_audit.json")
    clone_path = upstream_clone_path(ROOT)

    assert dependency["schema_version"] == IBM_BCF_AUDIT_SCHEMA_VERSION
    assert dependency["upstream"]["pinned_commit_sha"] == upstream_commit_sha(clone_path)
    assert dependency["upstream"]["license"] == "Apache-2.0"
    assert dependency["upstream"]["official_class_path"] == BCF_OFFICIAL_CLASS_PATH


def test_core_environment_remains_separate_from_competitor_env() -> None:
    dependency = read_result("dependency_audit.json")

    assert dependency["core_environment"]["platform"] == "Windows"
    assert dependency["core_environment"]["python_version"].startswith("3.14.")
    assert dependency["core_environment"]["torch_version"].endswith("+cpu")
    assert dependency["core_environment"]["changed_by_audit"] is False
    assert dependency["competitor_environment"]["python_version"].startswith("3.11.")
    assert dependency["competitor_environment"]["cuda_available"] is True


def test_upstream_smoke_invokes_official_path_and_records_factorwise_shape() -> None:
    smoke = read_result("upstream_smoke.json")

    assert smoke["schema_version"] == IBM_BCF_AUDIT_SCHEMA_VERSION
    assert smoke["entrypoint"] == "main_capacity.py"
    assert smoke["invokes_official_bcf_path"] is True
    assert smoke["cuda_used"] is True
    assert smoke["success"] is True
    assert smoke["direct_official_class_smoke"]["prediction_shape"] == [1, 2]
    assert smoke["direct_official_class_smoke"]["finite_observation"] is True
    assert smoke["direct_official_class_smoke"]["finite_prediction_tensor"] is True


def test_seed_reproducibility_external_injection_and_subset_feasibility_are_recorded() -> None:
    contract = read_result("contract_audit.json")
    checks = contract["direct_contract_checks"]

    assert checks["same_seed_same_codebook"] is True
    assert checks["same_seed_same_prediction"] is True
    assert checks["external_indices_injected"] == checks["injected_prediction"]
    assert checks["subset_reuses_same_observation"] is True
    assert checks["subset_truth_included"] == [True, True, True]
    assert checks["subset_prediction_global"] == checks["external_indices_injected"]


def test_abstract_factorization_task_stays_representation_independent() -> None:
    task = AbstractFactorizationTask(
        task_seed=42,
        factor_count=3,
        domain_size_per_factor=[5, 5, 5],
        target_indices=[1, 2, 3],
        distractor_target_indices=[[4, 0, 1]],
        context_membership={"f0_i1": ["L1_A/L2_X", "L1_A/L2_Y"]},
        active_context="L1_A/L2_X",
        anomaly_rate=0.1,
        query_valid_source_indices=[0],
    )

    payload = task.to_dict()
    assert is_json_roundtrippable(payload) is True
    assert json.loads(json.dumps(payload)) == payload
    assert "torch" not in repr(payload).lower()
    assert "tensor" not in repr(payload).lower()


def test_adapter_does_not_import_or_copy_map_encoder() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "competitors" / "ibm_bcf_audit.py").read_text(encoding="utf-8")

    assert "torchhd" not in source
    assert "from ..baseline" not in source
    assert "bind_sequence" not in source
    assert "factors_from_indices" not in source


def test_result_files_share_schema_and_are_json_serializable() -> None:
    for name in (
        "dependency_audit.json",
        "upstream_smoke.json",
        "contract_audit.json",
        "parity_report.json",
        "analysis.json",
    ):
        payload = read_result(name)
        assert payload["schema_version"] == IBM_BCF_AUDIT_SCHEMA_VERSION
        assert is_json_roundtrippable(payload) is True


def test_upstream_clone_has_no_tracked_source_modifications() -> None:
    assert upstream_tracked_source_clean(upstream_clone_path(ROOT)) is True


def test_hypothesis_file_is_unmodified_relative_to_head() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.stdout.strip() == ""


def test_dependency_audit_records_current_hypothesis_hash() -> None:
    dependency = read_result("dependency_audit.json")
    hypothesis_path = ROOT / "CGRN-HSR_research_hypothesis.md"

    assert dependency["hypothesis_sha256"].lower() == compute_file_sha256(hypothesis_path)
