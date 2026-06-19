from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_external_and_internal_noise_are_separated() -> None:
    payload = _load("results/level3_5a/channel_contracts.json")
    distinction = payload["external_internal_distinction"]
    assert distinction["must_not_be_mixed"] is True
    assert distinction["bcf_internal_noise_not_external_corruption"] is True
    assert "external_corruption_spec" in payload["trial_fields"]
    assert "internal_decoder_noise_spec" in payload["trial_fields"]


def test_u1_and_u2_are_separated() -> None:
    payload = _load("results/level3_5a/channel_contracts.json")
    assert payload["u1_u2_separation"]["mixed_protocol_forbidden"] is True
    channels = {row["channel_id"]: row for row in payload["channels"]}
    assert channels["N6_SUPERPOSITION_INTERFERENCE"]["included_in_level3_5b_primary"] is False


def test_every_method_has_explicit_lawful_channels() -> None:
    payload = _load("results/level3_5a/method_channel_compatibility.json")
    for row in payload["rows"]:
        assert set(row["channels"].keys()) == {
            "N0_CLEAN_REFERENCE",
            "N1_BINARY_SYMMETRIC_COORDINATE_CORRUPTION",
            "N2_COORDINATE_ERASURE",
            "N3_NATIVE_SYMBOL_OR_BLOCK_CORRUPTION",
            "N4_SEMANTIC_FACTOR_CORRUPTION",
            "N5_APPROXIMATE_PERCEPTUAL_OBSERVATION",
            "N6_SUPERPOSITION_INTERFERENCE",
        }


def test_unsupported_channels_are_typed() -> None:
    payload = _load("results/level3_5a/method_channel_compatibility.json")
    values = {value for row in payload["rows"] for value in row["channels"].values()}
    assert "UNSUPPORTED_CHANNEL" in values
    assert payload["unsupported_channel_token"] == "UNSUPPORTED_CHANNEL"


def test_bch_symbolic_baseline_is_mandatory() -> None:
    payload = _load("results/level3_5a/ecc_dependency_audit.json")
    verdicts = {row["control_id"]: row["verdict"] for row in payload["controls"]}
    assert verdicts["binary_bch"] == "ADOPT_ECC_CONTROL"


def test_uncoded_packed_is_not_the_only_non_vsa_baseline() -> None:
    payload = _load("results/level3_5a/implementation_ladder.json")
    verdicts = {row["method_id"]: row["verdict"] for row in payload["rows"]}
    assert "uncoded_packed_tuple" in verdicts
    assert "packed_tuple_bch_low_redundancy" in verdicts
    assert "packed_tuple_bch_high_redundancy" in verdicts


def test_ecc_redundancy_is_counted() -> None:
    payload = _load("results/level3_5a/redundancy_accounting.json")
    for row in payload["rows"]:
        assert row["ecc_low_bits"] > row["payload_bits"]
        assert row["ecc_high_bits"] > row["payload_bits"]


def test_error_erasure_and_semantic_corruption_are_distinct() -> None:
    payload = _load("results/level3_5a/channel_contracts.json")
    channels = {row["channel_id"]: row for row in payload["channels"]}
    assert channels["N1_BINARY_SYMMETRIC_COORDINATE_CORRUPTION"]["channel_class"] == "external"
    assert channels["N2_COORDINATE_ERASURE"]["channel_class"] == "external"
    assert channels["N4_SEMANTIC_FACTOR_CORRUPTION"]["channel_class"] == "semantic"


def test_map_sign_flips_not_equated_to_gsbc_block_corruption() -> None:
    payload = _load("results/level3_5a/method_channel_compatibility.json")
    lookup = {row["method_id"]: row for row in payload["rows"]}
    assert lookup["map_classic_resonator"]["channels"]["N1_BINARY_SYMMETRIC_COORDINATE_CORRUPTION"] == "SUPPORTED_NATIVE_SIGN_FLIP_CHANNEL"
    assert lookup["official_ibm_bcf"]["channels"]["N3_NATIVE_SYMBOL_OR_BLOCK_CORRUPTION"] == "SUPPORTED_NATIVE_BLOCK_SYMBOL_CHANNEL"


def test_bcf_internal_stochasticity_not_counted_as_observation_corruption() -> None:
    payload = _load("results/level3_5a/method_channel_compatibility.json")
    lookup = {row["method_id"]: row for row in payload["rows"]}
    assert lookup["official_ibm_bcf"]["internal_decoder_noise_spec"] == "SUPPORTED_NATIVE_INITIALIZATION_AND_ITERATIVE_NOISE"


def test_neco_has_no_unauthorized_noisy_decoder() -> None:
    payload = _load("results/level3_5a/analysis.json")
    ladder = _load("results/level3_5a/implementation_ladder.json")
    verdicts = {row["method_id"]: row["verdict"] for row in ladder["rows"]}
    assert payload["raw_neco_noisy_decoder_authorized"] is False
    assert verdicts["raw_neco_noise_decoder"] == "BLOCK"


def test_histogram_recovery_remains_deferred() -> None:
    payload = _load("results/level3_5a/analysis.json")
    ladder = _load("results/level3_5a/implementation_ladder.json")
    verdicts = {row["method_id"]: row["verdict"] for row in ladder["rows"]}
    assert payload["histogram_recovery_deferred"] is True
    assert verdicts["histogram_recovery"] == "DEFER_UPSTREAM_FOR_U2_OR_NOISY_COMPOSITION"


def test_no_full_benchmark_executed() -> None:
    payload = _load("results/level3_5a/analysis.json")
    assert payload["full_benchmark_executed"] is False
    assert payload["new_decoder_implemented"] is False


def test_no_heldout_seeds_consumed() -> None:
    payload = _load("results/level3_5a/analysis.json")
    assert payload["heldout_consumed"] is False


def test_map_bcf_neco_configs_remain_frozen() -> None:
    payload = _load("results/level3_5a/claims.json")
    allowed = set(payload["allowed_claims"])
    assert "raw NeCo has no authorized noisy decoder" in allowed


def test_source_ledger_uses_primary_and_official_sources() -> None:
    payload = _load("results/level3_5a/source_ledger.json")
    assert payload["entries"]
    assert all(entry["primary_source_url"] for entry in payload["entries"])
    assert any(entry["official_implementation_url"] for entry in payload["entries"])


def test_decoder_taxonomy_includes_silent_miscorrection() -> None:
    payload = _load("results/level3_5a/decoder_failure_taxonomy.json")
    assert "miscorrection_rate" in payload["safety_metrics"]
    assert "miscorrected_silently" in payload["ecc_specific"]


def test_packed_payload_sizes_match_level3_4() -> None:
    payload = _load("results/level3_5a/ecc_candidate_configs.json")
    observed = {entry["payload_bits"] for entry in payload["payload_specs"]}
    assert observed == {12, 15, 21}


def test_proposed_protocol_uses_phase_boundary_search() -> None:
    payload = _load("results/level3_5a/fairness_contract.json")
    cells = _load("results/level3_5a/proposed_cells.json")
    assert payload["phase_boundary_search_required"] is True
    assert cells["development_policy"]["search_style"] == "adaptive phase-boundary search"


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_5A_NOISE_CONTRACTS.md",
        "docs/LEVEL3_5A_NOISE_BASELINE_MATRIX.md",
        "docs/LEVEL3_5B_FROZEN_PROTOCOL_DRAFT.md",
        "results/level3_5a/source_ledger.json",
        "results/level3_5a/channel_contracts.json",
        "results/level3_5a/method_channel_compatibility.json",
        "results/level3_5a/ecc_dependency_audit.json",
        "results/level3_5a/ecc_candidate_configs.json",
        "results/level3_5a/redundancy_accounting.json",
        "results/level3_5a/decoder_failure_taxonomy.json",
        "results/level3_5a/fairness_contract.json",
        "results/level3_5a/proposed_cells.json",
        "results/level3_5a/implementation_ladder.json",
        "results/level3_5a/claims.json",
        "results/level3_5a/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_git_status_clean_after_commit() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "docs/LEVEL3_5A_NOISE_BASELINE_MATRIX.md",
            "docs/LEVEL3_5A_NOISE_CONTRACTS.md",
            "results/level3_5a",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""
