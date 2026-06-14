from __future__ import annotations

import inspect
import importlib.metadata
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch

from ..baseline import bind_sequence, factors_from_indices

HOLOVEC_COMPETITOR_SCHEMA_VERSION = "level1f-holovec-audit-v1"
HOLOVEC_ATTENTION_CLASS_PATH = "holovec.utils.cleanup.attention.AttentionResonatorCleanup"


class HoloVecCompatibilityError(RuntimeError):
    """Raised when HoloVec cannot represent the benchmark contract honestly."""


@dataclass(frozen=True)
class HoloVecDependencyAudit:
    schema_version: str
    package_name: str
    resolved_version: str
    requires_python: str
    license_expression: str
    homepage: str
    documentation_url: str
    repository_url: str
    supports_torch_extra: bool
    torch_requirement: str | None
    installed_with_torch_backend: bool
    factorize_signature: str
    factorize_verbose_signature: str
    class_path: str
    source_path: str
    source_sha256: str | None
    python_314_compatible_on_host: bool
    cpu_execution_validated: bool
    accepts_external_codebooks: bool
    exposes_final_estimates: bool
    exposes_iteration_count: bool
    deterministic_seed_supported: bool
    factor_specific_domains_supported: bool
    blocker_summary: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SharedCodebookFactorization:
    labels: list[str]
    similarities: list[float]
    history: list[float]

    @property
    def iterations(self) -> int:
        return len(self.history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labels": self.labels,
            "similarities": self.similarities,
            "history": self.history,
            "iterations": self.iterations,
        }


def _holovec_objects():
    from holovec import VSA
    from holovec.utils.cleanup.attention import AttentionResonatorCleanup

    return VSA, AttentionResonatorCleanup


def _metadata_value(message: importlib.metadata.PackageMetadata, key: str) -> str | None:
    values = message.get_all(key)
    if not values:
        return None
    return values[0]


def _project_url(message: importlib.metadata.PackageMetadata, prefix: str) -> str | None:
    values = message.get_all("Project-URL") or []
    for value in values:
        if value.startswith(prefix):
            return value.split(", ", maxsplit=1)[1]
    return None


def _supports_factor_specific_domains() -> bool:
    _, attention_cls = _holovec_objects()
    signature = inspect.signature(attention_cls.factorize)
    return any(parameter.name in {"factor_codebooks", "domains", "candidate_subsets"} for parameter in signature.parameters.values())


def _source_path() -> Path:
    _, attention_cls = _holovec_objects()
    return Path(inspect.getsourcefile(attention_cls) or "")


def load_holovec_dependency_audit() -> HoloVecDependencyAudit:
    metadata = importlib.metadata.metadata("holovec")
    _, attention_cls = _holovec_objects()
    source_path = _source_path()
    supports_factor_domains = _supports_factor_specific_domains()
    blocker = None
    if not supports_factor_domains:
        blocker = (
            "HoloVec exposes one shared flat codebook for factorization and no API for "
            "per-factor domains or factor-specific candidate masks. Using it in the current "
            "benchmark would change the task rather than wrap the same task."
        )

    return HoloVecDependencyAudit(
        schema_version=HOLOVEC_COMPETITOR_SCHEMA_VERSION,
        package_name="holovec",
        resolved_version=importlib.metadata.version("holovec"),
        requires_python=_metadata_value(metadata, "Requires-Python") or "",
        license_expression=_metadata_value(metadata, "License-Expression") or "",
        homepage=_project_url(metadata, "Homepage") or "",
        documentation_url=_project_url(metadata, "Documentation") or "",
        repository_url=_project_url(metadata, "Repository") or "",
        supports_torch_extra="torch" in (metadata.get_all("Provides-Extra") or []),
        torch_requirement=next(
            (
                value
                for value in (metadata.get_all("Requires-Dist") or [])
                if value.startswith("torch>=")
            ),
            None,
        ),
        installed_with_torch_backend=True,
        factorize_signature=str(inspect.signature(attention_cls.factorize)),
        factorize_verbose_signature=str(inspect.signature(attention_cls.factorize_verbose)),
        class_path=HOLOVEC_ATTENTION_CLASS_PATH,
        source_path=str(source_path),
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.exists() else None,
        python_314_compatible_on_host=True,
        cpu_execution_validated=True,
        accepts_external_codebooks=True,
        exposes_final_estimates=False,
        exposes_iteration_count=True,
        deterministic_seed_supported=True,
        factor_specific_domains_supported=supports_factor_domains,
        blocker_summary=blocker,
    )


def roundtrip_numpy_torch(tensor: torch.Tensor) -> torch.Tensor:
    return torch.from_numpy(tensor.detach().cpu().numpy()).to(dtype=tensor.dtype)


def build_flat_codebook(domains: torch.Tensor) -> dict[str, torch.Tensor]:
    codebook: dict[str, torch.Tensor] = {}
    for factor_index in range(domains.size(0)):
        for atom_index in range(domains.size(1)):
            codebook[f"f{factor_index}_i{atom_index}"] = domains[factor_index, atom_index].detach().clone()
    return codebook


def require_shared_codebook_compatibility(candidate_indices: torch.Tensor) -> None:
    if candidate_indices.ndim != 2:
        raise ValueError("candidate_indices must be rank-2 with shape (F, K).")
    if candidate_indices.size(0) > 1:
        raise HoloVecCompatibilityError(
            "HoloVec AttentionResonatorCleanup accepts one shared codebook only. "
            "The current benchmark requires separate factor domains for each factor slot, so "
            "a fair drop-in wrapper would require internal masking or a rewritten update rule."
        )


def factorize_shared_codebook(
    observation: torch.Tensor,
    codebook: dict[str, torch.Tensor],
    *,
    dimension: int,
    n_factors: int,
    seed: int,
    beta: float = 250.0,
    max_iterations: int = 12,
    threshold: float = 0.99,
    patience: int = 5,
) -> SharedCodebookFactorization:
    VSA, attention_cls = _holovec_objects()
    model = VSA.create("MAP", dim=dimension, backend="torch", seed=seed)
    cleanup = attention_cls(
        beta=beta,
        max_iterations=max_iterations,
        convergence_threshold=threshold,
        patience=patience,
    )
    labels, similarities, history = cleanup.factorize_verbose(
        observation,
        codebook,
        model,
        n_factors=n_factors,
        max_iterations=max_iterations,
        threshold=threshold,
    )
    return SharedCodebookFactorization(
        labels=list(labels),
        similarities=[float(value) for value in similarities],
        history=[float(value) for value in history],
    )


def minimal_domain_mismatch_reproduction() -> dict[str, Any]:
    VSA, _ = _holovec_objects()
    model = VSA.create("MAP", dim=8, backend="torch", seed=1)
    codebook = {
        "f0_i0": torch.tensor([1.0] * 8),
        "f0_i1": torch.tensor([-1.0] * 8),
        "f1_i0": torch.tensor([1.0, -1.0] * 4),
        "f1_i1": torch.tensor([-1.0, 1.0] * 4),
    }
    target_labels = ["f0_i0", "f1_i0"]
    observation = model.bind(codebook[target_labels[0]], codebook[target_labels[1]])
    result = factorize_shared_codebook(
        observation,
        codebook,
        dimension=8,
        n_factors=2,
        seed=1,
        beta=10.0,
        max_iterations=3,
        threshold=0.99,
        patience=3,
    )
    return {
        "schema_version": HOLOVEC_COMPETITOR_SCHEMA_VERSION,
        "type": "shared_codebook_domain_mismatch",
        "target_labels": target_labels,
        "predicted_labels": result.labels,
        "duplicate_prediction": len(set(result.labels)) < len(result.labels),
        "iterations": result.iterations,
        "history": result.history,
        "similarities": result.similarities,
        "shared_codebook_only": True,
        "interpretation": (
            "A duplicate factor prediction is possible because HoloVec exposes one flat codebook "
            "without factor-specific domain constraints."
        ),
    }


def build_observation_from_domains(domains: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    return bind_sequence(factors_from_indices(domains, indices))
