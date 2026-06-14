from __future__ import annotations

from pathlib import Path

import pytest
import torch

from cgrn_hsr.baseline import BaselineConfig, build_trial_problem
from cgrn_hsr.competitors.holovec_attention import (
    HOLOVEC_ATTENTION_CLASS_PATH,
    HoloVecCompatibilityError,
    build_flat_codebook,
    factorize_shared_codebook,
    load_holovec_dependency_audit,
    minimal_domain_mismatch_reproduction,
    require_shared_codebook_compatibility,
    roundtrip_numpy_torch,
)


def test_holovec_metadata_is_present() -> None:
    audit = load_holovec_dependency_audit()
    assert audit.package_name == "holovec"
    assert audit.resolved_version == "1.0.2"
    assert audit.license_expression == "Apache-2.0"
    assert audit.class_path == HOLOVEC_ATTENTION_CLASS_PATH
    assert audit.cpu_execution_validated is True


def test_attention_adapter_uses_external_codebooks() -> None:
    problem = build_trial_problem(
        BaselineConfig(dimensions=64, num_factors=1, domain_size=4, structured_distractor_count=0),
        seed=6001,
    )
    codebook = build_flat_codebook(problem.domains)
    assert len(codebook) == problem.config.domain_size
    assert torch.equal(codebook["f0_i0"], problem.domains[0, 0])


def test_roundtrip_numpy_torch_preserves_values() -> None:
    tensor = torch.tensor([[1.0, -1.0], [0.25, -0.5]], dtype=torch.float32)
    recovered = roundtrip_numpy_torch(tensor)
    assert recovered.dtype == tensor.dtype
    assert torch.equal(recovered, tensor)


def test_holovec_factorization_is_deterministic() -> None:
    problem = build_trial_problem(
        BaselineConfig(dimensions=64, num_factors=1, domain_size=4, structured_distractor_count=0),
        seed=6002,
    )
    codebook = build_flat_codebook(problem.domains)
    result_a = factorize_shared_codebook(
        problem.observation,
        codebook,
        dimension=problem.config.dimensions,
        n_factors=1,
        seed=6002,
        beta=250.0,
        max_iterations=6,
        threshold=0.99,
        patience=5,
    )
    result_b = factorize_shared_codebook(
        problem.observation,
        codebook,
        dimension=problem.config.dimensions,
        n_factors=1,
        seed=6002,
        beta=250.0,
        max_iterations=6,
        threshold=0.99,
        patience=5,
    )
    assert result_a.to_dict() == result_b.to_dict()


def test_shared_codebook_guard_rejects_factor_specific_candidate_rows() -> None:
    candidate_indices = torch.tensor(
        [
            [0, 1, 2, 3],
            [1, 2, 3, 0],
            [0, 1, 2, 3],
        ],
        dtype=torch.long,
    )
    with pytest.raises(HoloVecCompatibilityError):
        require_shared_codebook_compatibility(candidate_indices)


def test_minimal_reproduction_shows_duplicate_prediction_risk() -> None:
    reproduction = minimal_domain_mismatch_reproduction()
    assert reproduction["shared_codebook_only"] is True
    assert reproduction["duplicate_prediction"] is True


def test_dependency_audit_reports_factor_domain_blocker() -> None:
    audit = load_holovec_dependency_audit()
    assert audit.factor_specific_domains_supported is False
    assert audit.blocker_summary is not None


def test_holovec_source_is_referenced_not_copied() -> None:
    source_path = Path(load_holovec_dependency_audit().source_path)
    assert source_path.exists()
    assert ".venv" in str(source_path)
