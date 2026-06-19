from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"

EVIDENCE_STATUSES = {
    "REPRODUCED_IN_REPO",
    "PARTIALLY_REPRODUCED",
    "PAPER_REPRODUCTION",
    "IMPLEMENTATION_AUDITED",
    "LITERATURE_ONLY",
    "DESIGN_ONLY",
    "DEFERRED_HYPOTHESIS",
    "BLOCKED_WITH_EVIDENCE",
    "ADOPTED_ENGINEERING_BASELINE",
}

CLAIM_STATUSES = {
    "CONFIRMED_IN_FROZEN_ENVELOPE",
    "SUPPORTED_DEVELOPMENT_ONLY",
    "DIRECTIONAL_ONLY",
    "NOT_SUPPORTED",
    "BLOCKED",
    "DESIGN_PRINCIPLE",
    "OPEN",
}


def load_json_yaml(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def git_commit_exists(commit: str) -> bool:
    if not commit:
        return False
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    errors: list[str] = []

    evidence_payload = load_json_yaml(PAPER_DIR / "evidence_registry.yaml")
    claim_payload = load_json_yaml(PAPER_DIR / "claim_ledger.yaml")
    failure_payload = load_json_yaml(PAPER_DIR / "failure_mode_atlas.yaml")
    prior_payload = load_json_yaml(PAPER_DIR / "prior_art_registry.yaml")

    evidence_entries = evidence_payload.get("entries", [])  # type: ignore[assignment]
    claims = claim_payload.get("claims", [])  # type: ignore[assignment]
    failures = failure_payload.get("failures", [])  # type: ignore[assignment]
    prior_entries = prior_payload.get("entries", [])  # type: ignore[assignment]

    required_evidence_fields = {
        "hypothesis_id",
        "title",
        "category",
        "origin",
        "evidence_status",
        "maturity",
        "implementation_status",
        "research_question",
        "method",
        "substrate",
        "operation_contract",
        "dimensions",
        "factor_count",
        "search_space",
        "noise_contract",
        "baselines",
        "controls",
        "evidence",
        "results",
        "failure_modes",
        "causal_interpretation",
        "allowed_claims",
        "forbidden_claims",
        "prior_art",
        "architectural_disposition",
        "reopen_conditions",
        "information_added",
        "compute_added",
        "prior_added",
        "exact_side_information",
        "primary_result",
        "primary_failure_point",
        "safety_outcome",
        "cost_outcome",
    }

    seen_hypotheses: set[str] = set()
    for entry in evidence_entries:
        missing = sorted(required_evidence_fields - set(entry))
        if missing:
            errors.append(f"Evidence entry {entry.get('hypothesis_id', '<missing>')} missing fields: {missing}")
        hypothesis_id = entry.get("hypothesis_id")
        if hypothesis_id in seen_hypotheses:
            errors.append(f"Duplicate hypothesis_id: {hypothesis_id}")
        seen_hypotheses.add(hypothesis_id)
        status = entry.get("evidence_status")
        if status not in EVIDENCE_STATUSES:
            errors.append(f"Unsupported evidence status for {hypothesis_id}: {status}")

        evidence = entry.get("evidence", {})
        for commit in evidence.get("commits", []):
            if not git_commit_exists(commit):
                errors.append(f"Unknown commit reference for {hypothesis_id}: {commit}")
        for path_text in evidence.get("result_paths", []):
            if not (ROOT / path_text).exists():
                errors.append(f"Missing result path for {hypothesis_id}: {path_text}")
        for test_text in evidence.get("tests", []):
            if not (ROOT / test_text).exists():
                errors.append(f"Missing test path for {hypothesis_id}: {test_text}")

    claim_ids: set[str] = set()
    for claim in claims:
        claim_id = claim.get("claim_id")
        if claim_id in claim_ids:
            errors.append(f"Duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            errors.append(f"Unsupported claim status for {claim_id}: {status}")
        for evidence_id in claim.get("supporting_evidence", []):
            if evidence_id not in seen_hypotheses:
                errors.append(f"Claim {claim_id} references unknown supporting evidence: {evidence_id}")
        if status in {"CONFIRMED_IN_FROZEN_ENVELOPE", "SUPPORTED_DEVELOPMENT_ONLY", "DIRECTIONAL_ONLY"} and not claim.get("supporting_evidence"):
            errors.append(f"Claim {claim_id} has positive status but no supporting evidence.")

    seen_failures: set[str] = set()
    for failure in failures:
        failure_mode = failure.get("failure_mode")
        if failure_mode in seen_failures:
            errors.append(f"Duplicate failure_mode: {failure_mode}")
        seen_failures.add(failure_mode)
        for evidence_id in failure.get("evidence_refs", []):
            if evidence_id not in seen_hypotheses:
                errors.append(f"Failure mode {failure_mode} references unknown evidence: {evidence_id}")

    seen_prior: set[str] = set()
    for entry in prior_entries:
        citation_key = entry.get("citation_key")
        if citation_key in seen_prior:
            errors.append(f"Duplicate citation_key: {citation_key}")
        seen_prior.add(citation_key)
        for evidence_id in entry.get("closest_repo_hypotheses", []):
            if evidence_id not in seen_hypotheses:
                errors.append(f"Prior-art entry {citation_key} references unknown hypothesis: {evidence_id}")

    required_generated = [
        PAPER_DIR / "hypothesis_matrix.csv",
        PAPER_DIR / "hypothesis_matrix.md",
        PAPER_DIR / "recoverability_cost_matrix.csv",
        PAPER_DIR / "recoverability_cost_matrix.md",
        PAPER_DIR / "prior_art_matrix.csv",
        PAPER_DIR / "prior_art_matrix.md",
        PAPER_DIR / "claim_ledger.md",
        PAPER_DIR / "failure_mode_atlas.md",
        PAPER_DIR / "literature_transfer_matrix.md",
        PAPER_DIR / "manuscript.md",
        PAPER_DIR / "supplementary_evidence_atlas.md",
    ]
    for path in required_generated:
        if not path.exists():
            errors.append(f"Missing generated artifact: {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Evidence registry, claim ledger, prior-art registry, and derived tables validated.")
    print(f"Hypotheses: {len(evidence_entries)}")
    print(f"Claims: {len(claims)}")
    print(f"Failure modes: {len(failures)}")
    print(f"Prior-art entries: {len(prior_entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
