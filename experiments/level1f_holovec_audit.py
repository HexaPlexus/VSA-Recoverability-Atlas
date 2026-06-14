from __future__ import annotations

import json
from pathlib import Path

import torch

from cgrn_hsr.baseline import BaselineConfig, build_trial_problem
from cgrn_hsr.competitors.holovec_attention import (
    HOLOVEC_COMPETITOR_SCHEMA_VERSION,
    HoloVecCompatibilityError,
    build_flat_codebook,
    factorize_shared_codebook,
    load_holovec_dependency_audit,
    minimal_domain_mismatch_reproduction,
    require_shared_codebook_compatibility,
)

RESULTS_DIR = Path("results") / "level1f"


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    audit = load_holovec_dependency_audit()
    save_json(RESULTS_DIR / "dependency_audit.json", audit.to_dict())

    single_domain_config = BaselineConfig(
        dimensions=64,
        num_factors=1,
        domain_size=4,
        structured_distractor_count=0,
        max_iterations=6,
        stable_patience=3,
    )
    single_problem = build_trial_problem(single_domain_config, seed=314159)
    single_codebook = {
        label: vector
        for label, vector in build_flat_codebook(single_problem.domains).items()
        if label.startswith("f0_")
    }
    single_result = factorize_shared_codebook(
        single_problem.observation,
        single_codebook,
        dimension=single_problem.config.dimensions,
        n_factors=1,
        seed=314159,
        beta=250.0,
        max_iterations=6,
        threshold=0.99,
        patience=5,
    )

    incompatible_problem = build_trial_problem(
        BaselineConfig(
            dimensions=64,
            num_factors=3,
            domain_size=5,
            structured_distractor_count=0,
            max_iterations=6,
            stable_patience=3,
        ),
        seed=271828,
    )
    incompatible_indices = torch.stack(
        [torch.arange(incompatible_problem.config.domain_size, dtype=torch.long) for _ in range(incompatible_problem.config.num_factors)],
        dim=0,
    )
    incompatible_indices[1] = torch.tensor([0, 2, 4, 1, 3], dtype=torch.long)
    blocker_message = None
    try:
        require_shared_codebook_compatibility(incompatible_indices)
    except HoloVecCompatibilityError as exc:
        blocker_message = str(exc)

    minimal_repro = minimal_domain_mismatch_reproduction()
    parity_report = {
        "schema_version": HOLOVEC_COMPETITOR_SCHEMA_VERSION,
        "verdict": "BLOCKED_FOR_LEVEL1F1",
        "class_path": audit.class_path,
        "paper_basis": "arXiv:2403.13218",
        "paper_claims_checked": {
            "attention_logits_from_candidate_similarities": True,
            "softmax_beta_weighting": True,
            "weighted_combination_update": True,
            "update_uses_unbinding_with_other_estimates": True,
            "normalization_hook_present": True,
            "stopping_semantics_documented": True,
        },
        "notable_holovec_defaults": {
            "beta": 250.0,
            "max_iterations": 100,
            "convergence_threshold": 0.99,
            "patience": 5,
            "initialization": "mean(codebook)",
        },
        "single_factor_external_codebook_smoke": single_result.to_dict() | {
            "ground_truth_label": f"f0_i{int(single_problem.target_indices[0].item())}",
            "predicted_matches_ground_truth": single_result.labels == [f"f0_i{int(single_problem.target_indices[0].item())}"],
        },
        "factor_domain_blocker": {
            "factor_specific_domains_supported": audit.factor_specific_domains_supported,
            "shared_codebook_signature": audit.factorize_signature,
            "compatibility_guard_message": blocker_message,
            "minimal_reproduction": minimal_repro,
        },
        "stop_reason": (
            "Level 1F.1 shootout was not run because using HoloVec on the existing benchmark would "
            "require replacing separate factor domains with one flat competitor codebook."
        ),
    }
    save_json(RESULTS_DIR / "parity_report.json", parity_report)
    save_json(
        RESULTS_DIR / "analysis.json",
        {
            "schema_version": HOLOVEC_COMPETITOR_SCHEMA_VERSION,
            "status": "BLOCKED",
            "dependency_audit_path": str(RESULTS_DIR / "dependency_audit.json"),
            "parity_report_path": str(RESULTS_DIR / "parity_report.json"),
            "missing_artifacts": [
                "micro_reproduction.csv",
                "beta_calibration.csv",
                "selected_attention_config.json",
                "heldout_trials.jsonl",
                "summary.csv",
                "paired_comparisons.csv",
                "pareto_analysis.json",
            ],
            "blocker": blocker_message,
        },
    )

    print(json.dumps({"status": "BLOCKED", "schema_version": HOLOVEC_COMPETITOR_SCHEMA_VERSION}, ensure_ascii=True))


if __name__ == "__main__":
    main()
