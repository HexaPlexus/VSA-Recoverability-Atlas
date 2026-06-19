from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
RELEASE_CANDIDATE_DIR = PAPER_DIR / "release_candidate"
SRC_MODULE_DIR = ROOT / "src" / "cgrn_hsr"
if str(SRC_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_MODULE_DIR))

from release_artifacts import (  # noqa: E402
    canonical_sha256,
    extract_abstract,
    extract_claim_ids,
    extract_markdown_headings,
    word_count,
)

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

COMPARABILITY_CLASSES = {
    "DIRECT_COMMON_HARNESS",
    "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
    "SAME_MECHANISM_DIFFERENT_CONTRACT",
    "TAXONOMIC_ONLY",
    "HARDWARE_ONLY",
    "THEORETICAL_ONLY",
}

FIGURE_COMPARABILITY_CLASSES = {
    "DIRECT_COMMON_HARNESS",
    "CONCEPTUAL_ONLY",
    "DESCRIPTIVE_DERIVED_SUMMARY",
}

FIGURE_PLACEMENTS = {
    "MAIN_TEXT",
    "SUPPLEMENT_ONLY",
}

LITERATURE_EVIDENCE_STRENGTHS = {
    "PRIMARY_EMPIRICAL",
    "PRIMARY_THEORETICAL",
    "OFFICIAL_IMPLEMENTATION",
    "HARDWARE_SYNTHESIS",
    "PHYSICAL_HARDWARE_MEASUREMENT",
    "SURVEY_ONLY",
    "CONCEPTUAL_ONLY",
}


def load_json_yaml(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def git_commit_is_ancestor(commit: str, head: str = "HEAD") -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def extract_figure_paths(markdown: str) -> set[str]:
    return {
        match.strip()
        for match in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    }


def main() -> int:
    errors: list[str] = []

    evidence_payload = load_json_yaml(PAPER_DIR / "evidence_registry.yaml")
    claim_payload = load_json_yaml(PAPER_DIR / "claim_ledger.yaml")
    failure_payload = load_json_yaml(PAPER_DIR / "failure_mode_atlas.yaml")
    prior_payload = load_json_yaml(PAPER_DIR / "prior_art_registry.yaml")
    figure_payload = load_json_yaml(PAPER_DIR / "FIGURE_MANIFEST.yaml") if (PAPER_DIR / "FIGURE_MANIFEST.yaml").exists() else {"figures": []}

    evidence_entries = evidence_payload.get("entries", [])  # type: ignore[assignment]
    claims = claim_payload.get("claims", [])  # type: ignore[assignment]
    failures = failure_payload.get("failures", [])  # type: ignore[assignment]
    prior_entries = prior_payload.get("entries", [])  # type: ignore[assignment]
    manuscript_text = (PAPER_DIR / "manuscript.md").read_text(encoding="utf-8") if (PAPER_DIR / "manuscript.md").exists() else ""
    claim_traceability_text = (PAPER_DIR / "CLAIM_TRACEABILITY.md").read_text(encoding="utf-8") if (PAPER_DIR / "CLAIM_TRACEABILITY.md").exists() else ""
    references_text = (PAPER_DIR / "references.bib").read_text(encoding="utf-8") if (PAPER_DIR / "references.bib").exists() else ""
    figures = figure_payload.get("figures", [])  # type: ignore[assignment]

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
        if "observed_in_repo" not in failure:
            errors.append(f"Failure mode {failure_mode} missing observed_in_repo.")
        if "reported_in_literature" not in failure:
            errors.append(f"Failure mode {failure_mode} missing reported_in_literature.")
        if "mechanistic_explanation" not in failure:
            errors.append(f"Failure mode {failure_mode} missing mechanistic_explanation.")
        if "resource_shortfall" not in failure:
            errors.append(f"Failure mode {failure_mode} missing resource_shortfall.")
        if "detection_signal" not in failure:
            errors.append(f"Failure mode {failure_mode} missing detection_signal.")
        if "mitigation" not in failure:
            errors.append(f"Failure mode {failure_mode} missing mitigation.")
        if "remaining_risk" not in failure:
            errors.append(f"Failure mode {failure_mode} missing remaining_risk.")

    seen_prior: set[str] = set()
    required_prior_fields = {
        "citation_key",
        "title",
        "authors",
        "year",
        "venue",
        "source_url_or_doi",
        "official_code",
        "vsa_family",
        "algebra",
        "representation",
        "coordinate_precision",
        "sparsity",
        "binding_operation",
        "bundling_operation",
        "similarity_operation",
        "task_category",
        "task_contract",
        "factor_count",
        "candidate_domain",
        "dimension",
        "noise_contract",
        "decoder",
        "iterations",
        "restarts",
        "stopping_rule",
        "side_information",
        "external_prior",
        "exact_metadata",
        "reported_accuracy",
        "reported_latency",
        "reported_memory",
        "reported_energy",
        "reported_hardware",
        "reported_scale",
        "cost_location",
        "failure_modes",
        "limitations",
        "comparability_class",
        "closest_repo_hypotheses",
        "closest_repo_evidence",
        "transferable_claim",
        "non_transferable_claim",
        "anti_nih_verdict",
        "evidence_strength",
    }
    for entry in prior_entries:
        citation_key = entry.get("citation_key")
        if citation_key in seen_prior:
            errors.append(f"Duplicate citation_key: {citation_key}")
        seen_prior.add(citation_key)
        missing = sorted(required_prior_fields - set(entry))
        if missing:
            errors.append(f"Prior-art entry {citation_key} missing fields: {missing}")
        comparability_class = entry.get("comparability_class")
        if comparability_class not in COMPARABILITY_CLASSES:
            errors.append(f"Unsupported comparability class for {citation_key}: {comparability_class}")
        evidence_strength = entry.get("evidence_strength")
        if evidence_strength not in LITERATURE_EVIDENCE_STRENGTHS:
            errors.append(f"Unsupported literature evidence strength for {citation_key}: {evidence_strength}")
        for evidence_id in entry.get("closest_repo_hypotheses", []):
            if evidence_id not in seen_hypotheses:
                errors.append(f"Prior-art entry {citation_key} references unknown hypothesis: {evidence_id}")
        cost_location = entry.get("cost_location", {})
        if not isinstance(cost_location, dict):
            errors.append(f"Prior-art entry {citation_key} cost_location is not a mapping.")

    required_generated = [
        PAPER_DIR / "hypothesis_matrix.csv",
        PAPER_DIR / "hypothesis_matrix.md",
        PAPER_DIR / "recoverability_cost_matrix.csv",
        PAPER_DIR / "recoverability_cost_matrix.md",
        PAPER_DIR / "method_resource_atlas.csv",
        PAPER_DIR / "method_resource_atlas.md",
        PAPER_DIR / "prior_art_matrix.csv",
        PAPER_DIR / "prior_art_matrix.md",
        PAPER_DIR / "claim_ledger.md",
        PAPER_DIR / "failure_mode_atlas.md",
        PAPER_DIR / "literature_transfer_matrix.md",
        PAPER_DIR / "SYSTEMATIC_REVIEW_PROTOCOL.md",
        PAPER_DIR / "literature_search_log.csv",
        PAPER_DIR / "literature_screening.csv",
        PAPER_DIR / "architectural_decision_guide.md",
        PAPER_DIR / "manuscript.md",
        PAPER_DIR / "supplementary_evidence_atlas.md",
        PAPER_DIR / "references.bib",
        PAPER_DIR / "CLAIM_TRACEABILITY.md",
        PAPER_DIR / "CITATION_AUDIT.md",
        PAPER_DIR / "FIGURE_MANIFEST.yaml",
        PAPER_DIR / "RED_TEAM_REVIEW.md",
        PAPER_DIR / "RED_TEAM_RESPONSE.md",
        PAPER_DIR / "LITERATURE_SCREENING_AUDIT.md",
        PAPER_DIR / "literature_rescreening.csv",
        PAPER_DIR / "BIBLIOGRAPHY_HARDENING_REPORT.md",
        PAPER_DIR / "RELEASE_CANDIDATE_MANIFEST.yaml",
    ]
    for path in required_generated:
        if not path.exists():
            errors.append(f"Missing generated artifact: {path.relative_to(ROOT)}")

    claim_refs = set(extract_claim_ids(manuscript_text))
    for claim_ref in claim_refs:
        if claim_ref not in claim_ids:
            errors.append(f"Manuscript references unknown claim id: {claim_ref}")
    for required_claim in {
        "claim_recoverability_resource_accounting",
        "claim_current_map_bcf_escalation_not_cost_effective",
        "claim_static_cell_route_sufficient_in_current_envelope",
    }:
        if required_claim not in claim_refs:
            errors.append(f"Manuscript is missing required claim anchor: {required_claim}")

    if "universal impossibility theorem" not in manuscript_text:
        errors.append("Manuscript is missing the no-universal-impossibility scope guard.")
    if "within the evaluated" not in manuscript_text:
        errors.append("Manuscript is missing bounded-scope wording using 'within the evaluated ...'.")
    for banned in ["paradigm shift", "production-ready", "production ready"]:
        if banned in manuscript_text.lower():
            errors.append(f"Manuscript contains banned wording: {banned}")
    if "literature-only" not in manuscript_text.lower() or "not measured in this repository" not in manuscript_text.lower():
        errors.append("Hardware section must contain both 'literature-only' and 'not measured in this repository' scope markers.")
    if "[claim:" in manuscript_text:
        errors.append("Canonical manuscript still exposes visible [claim:...] anchors instead of hidden metadata.")

    try:
        abstract_text = extract_abstract(manuscript_text)
    except ValueError:
        errors.append("Could not locate manuscript abstract.")
        abstract_text = ""
    if abstract_text:
        abstract_words = word_count(abstract_text)
        if not (200 <= abstract_words <= 300):
            errors.append(f"Abstract word count out of range: {abstract_words}")

    manuscript_words = word_count(manuscript_text)
    if manuscript_words < 7000:
        errors.append(f"Manuscript is still too short for a full draft: {manuscript_words} words")

    bib_keys = set(re.findall(r"@\w+\{([^,]+),", references_text))
    citation_chunks = re.findall(r"\[@([^\]]+)\]", manuscript_text)
    cited_keys: set[str] = set()
    for chunk in citation_chunks:
        for part in chunk.split(";"):
            key = part.strip()
            if key.startswith("@"):
                key = key[1:]
            if key:
                cited_keys.add(key)
    for key in cited_keys:
        if key not in bib_keys:
            errors.append(f"Manuscript cites missing bibliography key: {key}")
        if key not in seen_prior:
            errors.append(f"Manuscript cites key not present in prior-art registry: {key}")

    for claim_ref in claim_refs:
        if claim_ref not in claim_traceability_text:
            errors.append(f"Claim traceability file is missing manuscript claim: {claim_ref}")

    required_release_candidate = [
        RELEASE_CANDIDATE_DIR / "manuscript_rc1.md",
        RELEASE_CANDIDATE_DIR / "abstract.txt",
        RELEASE_CANDIDATE_DIR / "title_and_metadata.md",
        RELEASE_CANDIDATE_DIR / "references.bib",
        RELEASE_CANDIDATE_DIR / "figure_captions.md",
        RELEASE_CANDIDATE_DIR / "table_captions.md",
        RELEASE_CANDIDATE_DIR / "release_notes.md",
    ]
    for path in required_release_candidate:
        if not path.exists():
            errors.append(f"Missing release-candidate artifact: {path.relative_to(ROOT)}")

    manuscript_headings = set(extract_markdown_headings(manuscript_text))

    release_candidate_text = ""
    rc_path = RELEASE_CANDIDATE_DIR / "manuscript_rc1.md"
    if rc_path.exists():
        release_candidate_text = rc_path.read_text(encoding="utf-8")
        if release_candidate_text != manuscript_text:
            errors.append("Release-candidate manuscript must equal canonical manuscript exactly after generation.")
        rc_words = word_count(release_candidate_text)
        if rc_words != manuscript_words:
            errors.append(f"Release-candidate manuscript word count {rc_words} does not match canonical manuscript {manuscript_words}.")
    abstract_path = RELEASE_CANDIDATE_DIR / "abstract.txt"
    if abstract_path.exists() and abstract_text:
        release_abstract = abstract_path.read_text(encoding="utf-8").strip()
        if release_abstract != abstract_text:
            errors.append("Release-candidate abstract must equal the abstract extracted from canonical manuscript.")
    metadata_path = RELEASE_CANDIDATE_DIR / "title_and_metadata.md"
    if metadata_path.exists():
        metadata_text = metadata_path.read_text(encoding="utf-8")
        if "<OWNER_DECISION_REQUIRED>" not in metadata_text:
            errors.append("Release-candidate metadata file must preserve explicit owner-decision placeholders.")

    public_docs = [
        PAPER_DIR / "manuscript.md",
        PAPER_DIR / "CITATION_AUDIT.md",
        PAPER_DIR / "CLAIM_TRACEABILITY.md",
        PAPER_DIR / "LITERATURE_SCREENING_AUDIT.md",
        PAPER_DIR / "supplementary_evidence_atlas.md",
        PAPER_DIR / "BIBLIOGRAPHY_HARDENING_REPORT.md",
        RELEASE_CANDIDATE_DIR / "manuscript_rc1.md",
        RELEASE_CANDIDATE_DIR / "title_and_metadata.md",
    ]
    local_path_pattern = re.compile(r"C:/Users/Thanatos|C:\\Users\\Thanatos|/home/|file://", re.I)
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    for path in public_docs:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if local_path_pattern.search(text):
            errors.append(f"Public-facing file still contains machine-specific path: {path.relative_to(ROOT)}")
        if email_pattern.search(text):
            errors.append(f"Unexpected email address found in public-facing file: {path.relative_to(ROOT)}")

    forbidden_public_workflow_artifacts = [
        ROOT / "docs" / "LICENSE_DECISION.md",
        ROOT / "docs" / "PUBLIC_RELEASE_AUDIT.md",
        ROOT / "docs" / "PUBLIC_RELEASE_BASELINE.md",
        PAPER_DIR / "EXTERNAL_REVIEW_BUNDLE.md",
        PAPER_DIR / "EXTERNAL_REVIEW_LOG.csv",
        PAPER_DIR / "EXTERNAL_REVIEW_TARGETS.md",
        PAPER_DIR / "OWNER_METADATA_FORM.md",
        PAPER_DIR / "OWNER_REVIEW_CHECKLIST.md",
        PAPER_DIR / "PREPRINT_PLATFORM_DECISION.md",
        PAPER_DIR / "REVIEWER_RISK_REGISTER.md",
        PAPER_DIR / "SECRET_SCAN_PREPARATION.md",
        PAPER_DIR / "VENUE_CANDIDATES.md",
        PAPER_DIR / "owner_review",
        PAPER_DIR / "review_packets",
    ]
    for path in forbidden_public_workflow_artifacts:
        if path.exists():
            errors.append(f"Transient public workflow artifact should not be tracked: {path.relative_to(ROOT)}")

    release_manifest = load_json_yaml(PAPER_DIR / "RELEASE_CANDIDATE_MANIFEST.yaml")
    expected_manifest_fields = {
        "schema_version",
        "generated_from_commit",
        "generated_from_commit_semantics",
        "generation_date",
        "held_out_status",
        "release_candidate_hashes",
        "reference_hash",
        "claim_ledger_hash",
        "evidence_registry_hash",
        "supplement_hash",
        "figure_hashes",
    }
    missing_manifest = sorted(expected_manifest_fields - set(release_manifest))
    if missing_manifest:
        errors.append(f"Release candidate manifest missing fields: {missing_manifest}")
    generated_from_commit = release_manifest.get("generated_from_commit", "")
    if generated_from_commit and not git_commit_exists(generated_from_commit):
        errors.append(f"Unknown generated_from_commit in release manifest: {generated_from_commit}")
    if generated_from_commit and not git_commit_is_ancestor(generated_from_commit):
        errors.append(f"generated_from_commit is not an ancestor of HEAD: {generated_from_commit}")
    held_out_status = release_manifest.get("held_out_status", {})
    if not isinstance(held_out_status, dict) or held_out_status.get("official_held_out_execution_count") != 0:
        errors.append("Release manifest must record official_held_out_execution_count == 0.")
    release_candidate_hashes = release_manifest.get("release_candidate_hashes", {})
    if isinstance(release_candidate_hashes, dict):
        for relpath, expected_hash in release_candidate_hashes.items():
            path = ROOT / relpath
            if not path.exists():
                errors.append(f"Release manifest references missing file: {relpath}")
            elif canonical_sha256(path) != expected_hash:
                errors.append(f"Release manifest hash mismatch for {relpath}")
    if release_manifest.get("reference_hash") and canonical_sha256(PAPER_DIR / "references.bib") != release_manifest.get("reference_hash"):
        errors.append("Release manifest reference_hash does not match paper/references.bib.")
    if release_manifest.get("claim_ledger_hash") and canonical_sha256(PAPER_DIR / "claim_ledger.yaml") != release_manifest.get("claim_ledger_hash"):
        errors.append("Release manifest claim_ledger_hash does not match paper/claim_ledger.yaml.")
    if release_manifest.get("evidence_registry_hash") and canonical_sha256(PAPER_DIR / "evidence_registry.yaml") != release_manifest.get("evidence_registry_hash"):
        errors.append("Release manifest evidence_registry_hash does not match paper/evidence_registry.yaml.")
    if release_manifest.get("supplement_hash") and canonical_sha256(PAPER_DIR / "supplementary_evidence_atlas.md") != release_manifest.get("supplement_hash"):
        errors.append("Release manifest supplement_hash does not match paper/supplementary_evidence_atlas.md.")
    figure_hashes = release_manifest.get("figure_hashes", {})
    if isinstance(figure_hashes, dict):
        for relpath, expected_hash in figure_hashes.items():
            path = ROOT / relpath
            if not path.exists():
                errors.append(f"Release manifest references missing figure: {relpath}")
            elif canonical_sha256(path) != expected_hash:
                errors.append(f"Release manifest figure hash mismatch for {relpath}")

    frozen_results_status = subprocess.run(
        ["git", "status", "--porcelain", "--", "results"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if frozen_results_status.stdout.strip():
        errors.append("Frozen result artifacts were modified in the working tree.")

    screening_rows = []
    rescreen_rows = []
    screening_path = PAPER_DIR / "literature_screening.csv"
    if screening_path.exists():
        screening_rows = screening_path.read_text(encoding="utf-8").strip().splitlines()[1:]
    rescreen_path = PAPER_DIR / "literature_rescreening.csv"
    if rescreen_path.exists():
        rescreen_rows = rescreen_path.read_text(encoding="utf-8").strip().splitlines()[1:]
    min_rescreen = math.ceil(len(screening_rows) * 0.25) if screening_rows else 0
    if len(rescreen_rows) < min_rescreen:
        errors.append(
            f"Rescreening sample too small: have {len(rescreen_rows)}, need at least {min_rescreen} for 25% coverage."
        )

    if not isinstance(figures, list) or not figures:
        errors.append("Figure manifest must contain a non-empty 'figures' list.")
    if isinstance(figures, list) and not (1 <= len(figures) <= 8):
        errors.append(f"Unexpected number of manuscript figures: {len(figures)}")
    embedded_figure_paths = extract_figure_paths(manuscript_text)
    for figure in figures:
        for field in {
            "figure_id",
            "title",
            "files",
            "source_data",
            "generator_script",
            "caption",
            "claim_ids",
            "comparability_class",
            "measured_result",
            "placement",
            "manuscript_section",
        }:
            if field not in figure:
                errors.append(f"Figure manifest entry missing field {field}: {figure}")
        for file_text in figure.get("files", []):
            if not (ROOT / file_text).exists():
                errors.append(f"Missing figure file: {file_text}")
        for source_text in figure.get("source_data", []):
            if not (ROOT / source_text).exists():
                errors.append(f"Missing figure source data path: {source_text}")
        generator_path = ROOT / figure.get("generator_script", "")
        if figure.get("generator_script") and not generator_path.exists():
            errors.append(f"Missing figure generator script: {figure.get('generator_script')}")
        for claim_id in figure.get("claim_ids", []):
            if claim_id not in claim_ids:
                errors.append(f"Figure manifest references unknown claim id: {claim_id}")
        if figure.get("comparability_class") not in FIGURE_COMPARABILITY_CLASSES:
            errors.append(
                f"Unsupported figure comparability class for {figure.get('figure_id')}: {figure.get('comparability_class')}"
            )
        if figure.get("placement") not in FIGURE_PLACEMENTS:
            errors.append(f"Unsupported figure placement for {figure.get('figure_id')}: {figure.get('placement')}")
        manuscript_section = figure.get("manuscript_section", "")
        if figure.get("placement") == "MAIN_TEXT":
            if manuscript_section not in manuscript_headings:
                errors.append(
                    f"Main-text figure {figure.get('figure_id')} references missing manuscript section: {manuscript_section}"
                )
            expected_path = f"figures/{figure.get('figure_id')}.png"
            if expected_path not in embedded_figure_paths:
                errors.append(f"Main-text figure {figure.get('figure_id')} is not embedded in manuscript.")
            if figure.get("title") not in manuscript_text:
                errors.append(f"Main-text figure title missing from manuscript prose: {figure.get('title')}")

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
