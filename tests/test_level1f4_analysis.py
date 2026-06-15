from __future__ import annotations

import json
import subprocess
from functools import lru_cache
from pathlib import Path

from cgrn_hsr.level1f4_analysis import (
    CELL_PRIMARY,
    LEVEL1F3_CHECKPOINT_COMMIT,
    METHOD_GLOBAL,
    METHOD_ORACLE_HALF,
    METHOD_RANDOM_HALF,
    METHOD_SEMANTIC_HALF,
    PROVENANCE_STATUS_REPAIRED,
    build_claims,
    build_conditional_recovery_rows,
    build_config_sweep_rows,
    build_level1_closure_markdown,
    build_level1f4,
    build_truth_inclusion_rows,
    build_cap_saturation_rows,
    conditional_regret_decomposition,
    exact_requires_all_truth_included,
    load_json,
    load_trials,
    method_k_label,
)

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ANALYSIS_TOKENS = (
    "import torch\n",
    "import torchhd\n",
    "evaluate_map_trial",
    "evaluate_bcf_trial",
    "load_official_bcf_class",
)


@lru_cache(maxsize=1)
def built_level1f4() -> dict[str, object]:
    return build_level1f4(ROOT)


def test_exact_subset_recovery_requires_all_truth_included_on_real_trials() -> None:
    trials = load_trials(ROOT / "results" / "level1f3" / "heldout_trials.jsonl")
    assert all(exact_requires_all_truth_included(trial) for trial in trials)


def test_conditional_denominators_correct() -> None:
    trials = [
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_RANDOM_HALF,
            "factor_count": 2,
            "truth_included_per_factor": [True, True],
            "all_truth_included": True,
            "exact_recovery": True,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_RANDOM_HALF,
            "factor_count": 2,
            "truth_included_per_factor": [True, False],
            "all_truth_included": False,
            "exact_recovery": False,
        },
    ]
    rows = build_truth_inclusion_rows(trials)
    row = rows[0]

    assert row["all_truth_included_count"] == 1
    assert row["truth_missing_count"] == 1
    assert row["exact_given_all_truth_included"] == 1.0
    assert row["exact_given_truth_missing"] == 0.0


def test_semantic_and_random_use_same_k() -> None:
    assert method_k_label(METHOD_RANDOM_HALF) == method_k_label(METHOD_SEMANTIC_HALF)
    assert method_k_label(METHOD_RANDOM_HALF) == method_k_label(METHOD_ORACLE_HALF)


def test_selector_advantage_calculation() -> None:
    truth_rows = [
        {"cell_id": CELL_PRIMARY, "substrate": "MAP", "method_id": METHOD_GLOBAL, "exact_recovery_rate": 0.2},
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_RANDOM_HALF,
            "all_truth_included_rate": 0.2,
            "exact_given_all_truth_included": 1.0,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.2,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_SEMANTIC_HALF,
            "all_truth_included_rate": 0.5,
            "exact_given_all_truth_included": 0.8,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.4,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_ORACLE_HALF,
            "all_truth_included_rate": 1.0,
            "exact_given_all_truth_included": 0.9,
            "exact_given_truth_missing": None,
            "exact_recovery_rate": 0.9,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "random_unconditional_quarter",
            "all_truth_included_rate": 0.0,
            "exact_given_all_truth_included": None,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.0,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "semantic_l2_quarter",
            "all_truth_included_rate": 0.1,
            "exact_given_all_truth_included": 1.0,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.1,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "oracle_truth_included_quarter",
            "all_truth_included_rate": 1.0,
            "exact_given_all_truth_included": 1.0,
            "exact_given_truth_missing": None,
            "exact_recovery_rate": 1.0,
        },
    ]
    rows = build_conditional_recovery_rows(truth_rows)
    half_row = next(row for row in rows if row["k_label"] == "half")

    assert half_row["selector_advantage"] == 0.3


def test_conditional_factorizer_advantage_calculation() -> None:
    truth_rows = [
        {"cell_id": CELL_PRIMARY, "substrate": "MAP", "method_id": METHOD_GLOBAL, "exact_recovery_rate": 0.2},
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_RANDOM_HALF,
            "all_truth_included_rate": 0.2,
            "exact_given_all_truth_included": 0.5,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.1,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_SEMANTIC_HALF,
            "all_truth_included_rate": 0.5,
            "exact_given_all_truth_included": 0.8,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.4,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": METHOD_ORACLE_HALF,
            "all_truth_included_rate": 1.0,
            "exact_given_all_truth_included": 0.9,
            "exact_given_truth_missing": None,
            "exact_recovery_rate": 0.9,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "random_unconditional_quarter",
            "all_truth_included_rate": 0.0,
            "exact_given_all_truth_included": None,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.0,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "semantic_l2_quarter",
            "all_truth_included_rate": 0.1,
            "exact_given_all_truth_included": 1.0,
            "exact_given_truth_missing": 0.0,
            "exact_recovery_rate": 0.1,
        },
        {
            "cell_id": CELL_PRIMARY,
            "substrate": "MAP",
            "method_id": "oracle_truth_included_quarter",
            "all_truth_included_rate": 1.0,
            "exact_given_all_truth_included": 1.0,
            "exact_given_truth_missing": None,
            "exact_recovery_rate": 1.0,
        },
    ]
    rows = build_conditional_recovery_rows(truth_rows)
    half_row = next(row for row in rows if row["k_label"] == "half")

    assert half_row["conditional_factorizer_advantage"] == 0.3


def test_oracle_regret_decomposition() -> None:
    truth_exclusion, factorization = conditional_regret_decomposition(0.5, 0.8, 1.0, 0.9)
    assert round(truth_exclusion, 6) == 0.45
    assert round(factorization, 6) == 0.05


def test_cap_saturation_calculation() -> None:
    rows = build_cap_saturation_rows(
        [
            {
                "cell_id": CELL_PRIMARY,
                "substrate": "BCF",
                "method_id": METHOD_GLOBAL,
                "iterations": 16,
                "max_iterations_cap": 16,
            },
            {
                "cell_id": CELL_PRIMARY,
                "substrate": "BCF",
                "method_id": METHOD_GLOBAL,
                "iterations": 8,
                "max_iterations_cap": 16,
            },
            {
                "cell_id": CELL_PRIMARY,
                "substrate": "BCF",
                "method_id": METHOD_GLOBAL,
                "iterations": 16,
                "max_iterations_cap": 16,
            },
        ]
    )
    row = rows[0]
    assert row["fraction_reaching_cap_16"] == 0.666667
    assert row["max_iterations_cap"] == 16


def test_configuration_summary_reads_existing_artifacts_only() -> None:
    payload = load_json(ROOT / "results" / "level1f3" / "selected_bcf_config.json")
    rows = build_config_sweep_rows(payload)

    assert len(rows) == 3
    assert any(row["selected"] for row in rows)
    assert all(row["timing_available_in_artifact"] is False for row in rows)


def test_no_factorizer_invocation_during_analysis() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level1f4_analysis.py").read_text(encoding="utf-8")
    assert all(token not in source for token in FORBIDDEN_ANALYSIS_TOKENS)


def test_heldout_provenance_status_serialized() -> None:
    analysis = built_level1f4()["analysis"]
    assert analysis["provenance_audit"]["status"] == PROVENANCE_STATUS_REPAIRED


def test_claims_obey_allowed_wording() -> None:
    claims = built_level1f4()["claims"]
    assert claims["claim_c_map_stronger_than_bcf"]["status"] == "SUPPORTED_IN_TESTED_OPERATING_ENVELOPE"
    assert "GENERAL_CONFIRMED" not in json.dumps(claims)
    assert "verifier" not in claims["claim_d_external_context_transfer"]["wording"].lower()


def test_level1_closure_includes_falsified_mechanisms() -> None:
    closure_text = (ROOT / "docs" / "LEVEL1_RESEARCH_CLOSURE.md").read_text(encoding="utf-8")
    closure_text_lower = closure_text.lower()
    assert "warm transfer of resonator estimates" in closure_text_lower
    assert "cheap l1 probes as a verifier surrogate" in closure_text_lower
    assert "holovec as a fair per-factor competitor" in closure_text_lower


def test_hypothesis_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""
