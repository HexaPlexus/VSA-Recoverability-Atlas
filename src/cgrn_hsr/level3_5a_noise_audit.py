from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

LEVEL3_5A_SCHEMA_VERSION = "level3-5a-noise-audit-v1"
LEVEL3_5A_CHECKPOINT_COMMIT = "9fa47d9bb9aded882dc20ba8b4438c74bd817b05"
LEVEL3_5A_TASK_SCOPE = "Level 3.5a audit/design only"
LEVEL3_5A_NEXT_STAGE = "Level 3.5b noisy-U1 frontier development"

N0 = "N0_CLEAN_REFERENCE"
N1 = "N1_BINARY_SYMMETRIC_COORDINATE_CORRUPTION"
N2 = "N2_COORDINATE_ERASURE"
N3 = "N3_NATIVE_SYMBOL_OR_BLOCK_CORRUPTION"
N4 = "N4_SEMANTIC_FACTOR_CORRUPTION"
N5 = "N5_APPROXIMATE_PERCEPTUAL_OBSERVATION"
N6 = "N6_SUPERPOSITION_INTERFERENCE"

MANDATORY_METHODS = (
    "uncoded_packed_tuple",
    "packed_tuple_bch_low_redundancy",
    "packed_tuple_bch_high_redundancy",
    "generic_full_rank_linear_mix",
    "raw_neco_algebraic_recovery",
    "map_classic_resonator",
    "map_extended_restarted",
    "official_ibm_bcf",
    "tiny_nearest_codeword_oracle",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_rows(repo_root: Path) -> list[dict[str, Any]]:
    configs = _load_json(repo_root / "results" / "level3_4" / "representation_configs.json")
    rows: list[dict[str, Any]] = []
    for row in configs["rows"]:
        rows.append(
            {
                "cell_id": row["cell_id"],
                "factor_count": row["factor_count"],
                "domain_size": row["domain_size"],
                "payload_bits": row["payload_bits"],
                "message_dimension_per_factor": row["message_dimension_per_factor"],
                "ambient_code_length_neco_generic": row["ambient_code_length"],
                "unassigned_messages_per_factor": row["unassigned_messages_per_factor"],
            }
        )
    return rows


def build_source_ledger() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "entries": [
            {
                "family": "dense_map_classic",
                "primary_source_title": "A Resonator Network for Factoring Distributed Representations of Data Structures",
                "primary_source_url": "https://www.frontiersin.org/articles/10.3389/fnbot.2020.00063/full",
                "official_implementation_title": "TorchHD",
                "official_implementation_url": "https://github.com/hyperdimensional-computing/torchhd",
                "contract_role": "frozen MAP noisy-U1 baseline candidate under lawful sign-flip corruption",
            },
            {
                "family": "ibm_bcf",
                "primary_source_title": "Factorizers for distributed sparse block codes",
                "primary_source_url": "https://content.iospress.com/articles/neurosymbolic-artificial-intelligence/nai240713",
                "official_implementation_title": "IBM/in-memory-factorizer",
                "official_implementation_url": "https://github.com/IBM/in-memory-factorizer",
                "pinned_commit": "a353f1e918dcb515cad4a89c8e47ce24668954a7",
                "contract_role": "official GSBC/BCF native noisy-product and block-symbol factorization reference",
            },
            {
                "family": "ibm_noise_factorizers",
                "primary_source_title": "On the Role of Noise in Factorizers",
                "primary_source_url": "https://arxiv.org/search/?query=On+the+Role+of+Noise+in+Factorizers&searchtype=all",
                "official_implementation_title": "IBM/in-memory-factorizer native noise experiments",
                "official_implementation_url": "https://github.com/IBM/in-memory-factorizer",
                "contract_role": "native internal stochasticity and noisy-product envelope reference",
            },
            {
                "family": "linear_code_hdc_neco",
                "primary_source_title": "Linear Codes for Hyperdimensional Computing",
                "primary_source_url": "https://arxiv.org/abs/2403.03278",
                "official_implementation_title": "No public upstream; Level 3.3 independent reproduction only",
                "official_implementation_url": "",
                "contract_role": "clean algebraic U1 reproduction; no authorized noisy decoder",
            },
            {
                "family": "histogram_recovery",
                "primary_source_title": "Efficient Vector Symbolic Architectures from Histogram Recovery",
                "primary_source_url": "https://arxiv.org/search/?query=Efficient+Vector+Symbolic+Architectures+from+Histogram+Recovery&searchtype=all",
                "official_implementation_title": "Deferred upstream or author implementation",
                "official_implementation_url": "",
                "contract_role": "future U2/noisy-composition candidate, not active in Level 3.5a",
            },
            {
                "family": "galois_bch_rs",
                "primary_source_title": "galois documentation",
                "primary_source_url": "https://mhostetter.github.io/galois/latest/",
                "official_implementation_title": "galois Python library",
                "official_implementation_url": "https://github.com/mhostetter/galois",
                "contract_role": "mature ECC implementation substrate for BCH and Reed-Solomon controls",
            },
            {
                "family": "generic_linear_mix_control",
                "primary_source_title": "Level 3.4 algebraic baseline closure",
                "primary_source_url": "https://github.com/Thanatos/CGRN-HSR",
                "official_implementation_title": "Local clean-U1 anti-NIH control",
                "official_implementation_url": "",
                "contract_role": "binary full-rank linear anti-NIH control under matched ambient length",
            },
        ],
    }


def build_channel_contracts() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "task_scope": "U1 noisy single-product design only; U2 remains separate",
        "trial_fields": [
            "external_corruption_spec",
            "internal_decoder_noise_spec",
        ],
        "external_internal_distinction": {
            "external_observation_corruption": "clean representation -> external corruption channel -> decoder",
            "internal_algorithmic_stochasticity": "clean or noisy observation -> decoder initialization or iteration noise",
            "must_not_be_mixed": True,
            "bcf_internal_noise_not_external_corruption": True,
        },
        "channels": [
            {
                "channel_id": N0,
                "name": "Clean reference",
                "channel_class": "external",
                "contract": "No observation corruption; non-regression anchor only.",
                "included_in_level3_5b_primary": True,
            },
            {
                "channel_id": N1,
                "name": "Binary symmetric coordinate corruption",
                "channel_class": "external",
                "contract": "Independent coordinate flips on a lawful binary or bipolar serialization.",
                "included_in_level3_5b_primary": True,
                "guardrails": [
                    "Equal raw p must not be interpreted as equal semantic damage across representations.",
                    "BCF participates only if a lawful coordinate serialization is explicitly frozen.",
                ],
            },
            {
                "channel_id": N2,
                "name": "Coordinate erasure",
                "channel_class": "external",
                "contract": "A known subset of coordinates or symbols is marked erased.",
                "included_in_level3_5b_primary": True,
                "guardrails": [
                    "Zero-fill must not be presented as native erasure decoding.",
                    "The erasure mask must be explicit when the decoder actually uses it.",
                ],
            },
            {
                "channel_id": N3,
                "name": "Native symbol or block corruption",
                "channel_class": "external",
                "contract": "Representation-specific symbol, block, or finite-field corruption channel.",
                "included_in_level3_5b_primary": True,
                "guardrails": [
                    "Compare only inside lawful native symbol families.",
                    "Do not build a universal ranking from one raw corruption percentage.",
                ],
            },
            {
                "channel_id": N4,
                "name": "Semantic factor corruption",
                "channel_class": "semantic",
                "contract": "The semantic source tuple is changed before encoding; not a channel noise model.",
                "included_in_level3_5b_primary": False,
            },
            {
                "channel_id": N5,
                "name": "Approximate perceptual observation",
                "channel_class": "external",
                "contract": "The observation is off-manifold or approximately produced rather than a corrupted valid codeword.",
                "included_in_level3_5b_primary": False,
                "notes": [
                    "Most subject-relevant long-term direction.",
                    "Deferred until N1/N2/N3 closure.",
                ],
            },
            {
                "channel_id": N6,
                "name": "Superposition interference",
                "channel_class": "semantic",
                "contract": "Multiple valid tuples are bundled or superposed.",
                "included_in_level3_5b_primary": False,
                "notes": [
                    "This is U2, not U1 noise.",
                ],
            },
        ],
        "u1_u2_separation": {
            "u1_contract": "one clean or corrupted single bound tuple -> exactly one factor index per domain",
            "u2_contract": "superposed tuples -> tuple set or histogram output",
            "mixed_protocol_forbidden": True,
        },
    }


def build_method_channel_compatibility() -> dict[str, Any]:
    def channels(
        *,
        n0: str,
        n1: str,
        n2: str,
        n3: str,
        n4: str = "DEFER_SEMANTIC_CORRUPTION",
        n5: str = "DEFER_APPROXIMATE_OBSERVATION",
        n6: str = "TASK_MISMATCH_U2",
    ) -> dict[str, str]:
        return {
            N0: n0,
            N1: n1,
            N2: n2,
            N3: n3,
            N4: n4,
            N5: n5,
            N6: n6,
        }

    rows = [
        {
            "method_id": "uncoded_packed_tuple",
            "representation": "concatenated packed factor-local indices",
            "native_decoder": "deterministic slicing",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED_NO_ROBUSTNESS",
                n2="SUPPORTED_NO_ROBUSTNESS",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "UNASSIGNED_CODEWORD or WRONG_RECOVERY depending on corrupted bit pattern",
        },
        {
            "method_id": "packed_tuple_bch_low_redundancy",
            "representation": "packed tuple protected by shortened BCH",
            "native_decoder": "galois BCH decode with optional erasures",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED",
                n2="SUPPORTED",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "CORRECTED, DETECTED_UNCORRECTABLE, or MISCORRECTED silently",
        },
        {
            "method_id": "packed_tuple_bch_high_redundancy",
            "representation": "packed tuple protected by higher-redundancy shortened BCH",
            "native_decoder": "galois BCH decode with optional erasures",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED",
                n2="SUPPORTED",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "CORRECTED, DETECTED_UNCORRECTABLE, or MISCORRECTED silently",
        },
        {
            "method_id": "generic_full_rank_linear_mix",
            "representation": "binary full-column-rank linear transform of packed payload",
            "native_decoder": "GF(2) exact linear solve",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED_BUT_NO_ERROR_CORRECTION",
                n2="SUPPORTED_WITH_EXPLICIT_ERASURE_MASK",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "EXACT_RECOVERY, AMBIGUOUS, INCONSISTENT, or WRONG_RECOVERY",
        },
        {
            "method_id": "raw_neco_algebraic_recovery",
            "representation": "paper-compatible direct-sum linear-code construction",
            "native_decoder": "paper clean algebraic solve only",
            "channels": channels(
                n0="SUPPORTED",
                n1="UNSUPPORTED_CHANNEL",
                n2="UNSUPPORTED_CHANNEL",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "EXACT_RECOVERY, AMBIGUOUS, RANK_DEFICIENT, INCONSISTENT, or COLLISION",
            "notes": [
                "No custom NeCo noisy decoder is authorized.",
            ],
        },
        {
            "method_id": "map_classic_resonator",
            "representation": "dense MAP bipolar hypervectors",
            "native_decoder": "frozen classic TorchHD resonator",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED_NATIVE_SIGN_FLIP_CHANNEL",
                n2="WRAP_PREPROCESSING_REQUIRED",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "EXACT_RECOVERY, WRONG_RECOVERY, or NATIVE_LIMIT_REACHED",
        },
        {
            "method_id": "map_extended_restarted",
            "representation": "dense MAP bipolar hypervectors",
            "native_decoder": "frozen extended/restarted MAP arm",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED_NATIVE_SIGN_FLIP_CHANNEL",
                n2="WRAP_PREPROCESSING_REQUIRED",
                n3="UNSUPPORTED_CHANNEL",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "EXACT_RECOVERY, WRONG_RECOVERY, or NATIVE_LIMIT_REACHED",
        },
        {
            "method_id": "official_ibm_bcf",
            "representation": "GSBC sparse block code factorization",
            "native_decoder": "official IBM BCF with native stopping",
            "channels": channels(
                n0="SUPPORTED",
                n1="TASK_MISMATCH_FOR_N1",
                n2="TASK_MISMATCH_FOR_N2",
                n3="SUPPORTED_NATIVE_BLOCK_SYMBOL_CHANNEL",
                n5="DEFER_APPROXIMATE_PRODUCT_TRACK",
            ),
            "internal_decoder_noise_spec": "SUPPORTED_NATIVE_INITIALIZATION_AND_ITERATIVE_NOISE",
            "typed_failure_behavior": "EXACT_RECOVERY, WRONG_RECOVERY, or NATIVE_LIMIT_REACHED",
            "notes": [
                "Internal stochasticity must remain separate from external corruption.",
            ],
        },
        {
            "method_id": "tiny_nearest_codeword_oracle",
            "representation": "evaluator-only nearest valid semantic codeword",
            "native_decoder": "exhaustive oracle",
            "channels": channels(
                n0="SUPPORTED",
                n1="SUPPORTED_TINY_ONLY",
                n2="SUPPORTED_TINY_ONLY",
                n3="SUPPORTED_TINY_ONLY",
            ),
            "internal_decoder_noise_spec": "NONE",
            "typed_failure_behavior": "EXACT_RECOVERY, AMBIGUOUS, or WRONG_RECOVERY",
        },
    ]
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "rows": rows,
        "unsupported_channel_token": "UNSUPPORTED_CHANNEL",
    }


def build_ecc_dependency_audit() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "galois_dependency": {
            "resolved_version_from_lock": "0.4.11",
            "official_docs": "https://mhostetter.github.io/galois/latest/",
            "official_repo": "https://github.com/mhostetter/galois",
            "local_smoke_summary": {
                "bch_class_available": True,
                "reed_solomon_class_available": True,
                "bch_decode_signature": "decode(codeword, erasures=None, output='message', errors=False)",
                "reed_solomon_decode_signature": "decode(codeword, erasures=None, output='message', errors=False)",
                "native_shortened_constructor_available": False,
                "shortening_requires_wrapper": True,
            },
        },
        "controls": [
            {
                "control_id": "binary_bch",
                "verdict": "ADOPT_ECC_CONTROL",
                "coverage": "short binary payloads, errors, and erasures",
                "why": "Mature maintained implementation already in the Level 3 environment; strong exact typed-record control for channel noise.",
            },
            {
                "control_id": "reed_solomon",
                "verdict": "DEFER_SYMBOL_CHANNEL",
                "coverage": "q-ary symbol errors and erasures",
                "why": "Strong mature control, but not the default baseline for raw binary flips without a separately frozen symbol serialization policy.",
            },
            {
                "control_id": "ldpc",
                "verdict": "DEFER_COMPLEX_CONTROL",
                "candidate_library": "pyldpc",
                "official_repo": "https://github.com/hichamjanati/pyldpc",
                "why": "Useful for longer soft-decision channels, but high setup and fairness burden for 12-21 bit payloads.",
            },
            {
                "control_id": "polar",
                "verdict": "DEFER_COMPLEX_CONTROL",
                "candidate_library": "polar-codes",
                "official_repo": "https://github.com/mcba1n/polar-codes",
                "why": "Mature enough to exist, but not required if BCH already provides a strong short-block control for Level 3.5b.",
            },
            {
                "control_id": "neco_noisy_decoder",
                "verdict": "BLOCK",
                "coverage": "raw NeCo off-subspace noise decoding",
                "why": "The paper and Level 3.3 reproduction do not authorize inventing a separate noisy NeCo decoder.",
            },
        ],
    }


def build_ecc_candidate_configs(payload_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_payload = {row["payload_bits"]: row for row in payload_rows}
    payload_specs = [
        {
            "payload_bits": 12,
            "semantic_cells": [by_payload[12]["cell_id"]],
            "tiers": [
                {
                    "tier_id": "ECC_LOW_REDUNDANCY",
                    "family": "shortened_BCH",
                    "parent_code": {"n": 31, "k": 26, "d": 3, "t": 1},
                    "effective_code": {"n": 17, "k": 12, "minimum_distance_lower_bound": 3, "t": 1},
                    "redundancy_bits": 5,
                    "wrapper_required": True,
                },
                {
                    "tier_id": "ECC_HIGH_REDUNDANCY",
                    "family": "shortened_BCH",
                    "parent_code": {"n": 31, "k": 16, "d": 7, "t": 3},
                    "effective_code": {"n": 27, "k": 12, "minimum_distance_lower_bound": 7, "t": 3},
                    "redundancy_bits": 15,
                    "wrapper_required": True,
                },
            ],
        },
        {
            "payload_bits": 15,
            "semantic_cells": ["u1_clean_m22", "u1_clean_m31"],
            "tiers": [
                {
                    "tier_id": "ECC_LOW_REDUNDANCY",
                    "family": "shortened_BCH",
                    "parent_code": {"n": 31, "k": 26, "d": 3, "t": 1},
                    "effective_code": {"n": 20, "k": 15, "minimum_distance_lower_bound": 3, "t": 1},
                    "redundancy_bits": 5,
                    "wrapper_required": True,
                },
                {
                    "tier_id": "ECC_HIGH_REDUNDANCY",
                    "family": "shortened_BCH",
                    "parent_code": {"n": 31, "k": 16, "d": 7, "t": 3},
                    "effective_code": {"n": 30, "k": 15, "minimum_distance_lower_bound": 7, "t": 3},
                    "redundancy_bits": 15,
                    "wrapper_required": True,
                },
            ],
        },
        {
            "payload_bits": 21,
            "semantic_cells": [by_payload[21]["cell_id"]],
            "tiers": [
                {
                    "tier_id": "ECC_LOW_REDUNDANCY",
                    "family": "primitive_BCH",
                    "parent_code": {"n": 31, "k": 21, "d": 5, "t": 2},
                    "effective_code": {"n": 31, "k": 21, "minimum_distance_lower_bound": 5, "t": 2},
                    "redundancy_bits": 10,
                    "wrapper_required": False,
                },
                {
                    "tier_id": "ECC_HIGH_REDUNDANCY",
                    "family": "shortened_BCH",
                    "parent_code": {"n": 63, "k": 39, "d": 9, "t": 4},
                    "effective_code": {"n": 45, "k": 21, "minimum_distance_lower_bound": 9, "t": 4},
                    "redundancy_bits": 24,
                    "wrapper_required": True,
                },
            ],
        },
    ]
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "galois_shortening_requires_wrapper": True,
        "payload_specs": payload_specs,
    }


def build_redundancy_accounting(
    payload_rows: list[dict[str, Any]],
    ecc_candidate_configs: dict[str, Any],
) -> dict[str, Any]:
    ecc_by_payload = {entry["payload_bits"]: entry for entry in ecc_candidate_configs["payload_specs"]}
    rows: list[dict[str, Any]] = []
    for payload in payload_rows:
        payload_bits = payload["payload_bits"]
        tiers = ecc_by_payload[payload_bits]["tiers"]
        rows.append(
            {
                "cell_id": payload["cell_id"],
                "factor_count": payload["factor_count"],
                "domain_size": payload["domain_size"],
                "payload_bits": payload_bits,
                "uncoded_bits": payload_bits,
                "neco_generic_ambient_bits": payload["ambient_code_length_neco_generic"],
                "neco_generic_redundancy_ratio": round(payload["ambient_code_length_neco_generic"] / payload_bits, 6),
                "ecc_low_bits": tiers[0]["effective_code"]["n"],
                "ecc_low_redundancy_ratio": round(tiers[0]["effective_code"]["n"] / payload_bits, 6),
                "ecc_high_bits": tiers[1]["effective_code"]["n"],
                "ecc_high_redundancy_ratio": round(tiers[1]["effective_code"]["n"] / payload_bits, 6),
            }
        )
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "rows": rows,
        "persistent_bytes_must_include": [
            "generator_matrices",
            "subcode_definitions",
            "identity_to_message_mappings",
            "decoder metadata",
        ],
        "runtime_bytes_must_include": [
            "materialized_codebooks_if_used",
            "observation",
            "decoder_state",
            "temporary_solve_or_decode_buffers",
        ],
    }


def build_decoder_failure_taxonomy() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "common_outcomes": [
            "EXACT_RECOVERY",
            "WRONG_RECOVERY",
            "DETECTED_UNCORRECTABLE",
            "AMBIGUOUS",
            "INCONSISTENT",
            "UNASSIGNED_CODEWORD",
            "NATIVE_LIMIT_REACHED",
            "UNSUPPORTED_CHANNEL",
        ],
        "safety_metrics": [
            "exact_recovery",
            "silent_wrong_recovery",
            "detected_failure",
            "abstention_or_failure_coverage",
            "miscorrection_rate",
        ],
        "ecc_specific": [
            "corrected",
            "detected_uncorrectable",
            "miscorrected_silently",
        ],
        "notes": [
            "A decoder-reported success must not be treated as semantic truth without a semantic re-encoding check.",
            "Silent miscorrection is a first-class failure mode.",
        ],
    }


def build_fairness_contract() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "matching_regimes": [
            {
                "regime_id": "payload_matched",
                "contract": [
                    "same factor count F",
                    "same domain size M",
                    "same true tuple",
                    "same payload bit count",
                ],
            },
            {
                "regime_id": "storage_or_redundancy_matched",
                "contract": [
                    "compare total persistent bytes",
                    "compare total runtime bytes",
                    "compare codeword or observation length",
                    "compare redundancy ratio",
                ],
            },
            {
                "regime_id": "corruption_matched",
                "contract": [
                    "only inside a lawful shared channel",
                    "always report native corruption rate separately from semantic damage",
                ],
            },
        ],
        "not_allowed": [
            "equal D as the only fairness rule",
            "equal raw flip probability as universal semantic equivalence",
            "mixing external corruption and internal decoder stochasticity",
        ],
        "controller_disabled": True,
        "context_disabled": True,
        "no_heldout_consumed": True,
        "phase_boundary_search_required": True,
    }


def build_proposed_cells() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "semantic_cells": [
            {
                "cell_id": "u1_f3_m10",
                "role": "easy non-regression",
                "payload_bits": 12,
            },
            {
                "cell_id": "u1_f3_m31",
                "role": "MAP intermediate boundary",
                "payload_bits": 15,
            },
            {
                "cell_id": "u1_f3_m68",
                "role": "BCF separation/high-capacity anchor",
                "payload_bits": 21,
            },
        ],
        "development_policy": {
            "coarse_trials_per_corruption_point": 16,
            "freeze_rule": "2 easy points, 2 boundary points, 1 failure point per lawful channel family",
            "search_style": "adaptive phase-boundary search",
        },
        "no_universal_probability_grid": True,
        "no_heldout_frozen_yet": True,
        "tracks": [
            {
                "track_id": "binary_channel_controls",
                "methods": [
                    "uncoded_packed_tuple",
                    "packed_tuple_bch_low_redundancy",
                    "packed_tuple_bch_high_redundancy",
                    "generic_full_rank_linear_mix",
                    "raw_neco_algebraic_recovery",
                    "tiny_nearest_codeword_oracle",
                ],
                "channels": [N0, N1, N2],
            },
            {
                "track_id": "map_sign_flip",
                "methods": [
                    "map_classic_resonator",
                    "map_extended_restarted",
                ],
                "channels": [N0, N1, N2],
            },
            {
                "track_id": "bcf_native_block_or_symbol",
                "methods": [
                    "official_ibm_bcf",
                ],
                "channels": [N0, N3],
                "internal_noise_reported_separately": True,
            },
        ],
    }


def build_implementation_ladder() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "rows": [
            {"method_id": "uncoded_packed_tuple", "verdict": "ADOPT_BASELINE"},
            {"method_id": "packed_tuple_bch_low_redundancy", "verdict": "ADOPT_ECC_CONTROL"},
            {"method_id": "packed_tuple_bch_high_redundancy", "verdict": "ADOPT_ECC_CONTROL"},
            {"method_id": "generic_full_rank_linear_mix", "verdict": "WRAP_EXISTING_CONTROL"},
            {"method_id": "raw_neco_algebraic_recovery", "verdict": "WRAP_EXISTING_CLEAN_ONLY"},
            {"method_id": "raw_neco_noise_decoder", "verdict": "BLOCK"},
            {"method_id": "generic_linear_mix_plus_ecc", "verdict": "DEFER_REDUNDANT_CONTROL"},
            {"method_id": "official_ibm_bcf", "verdict": "WRAP_UPSTREAM"},
            {"method_id": "official_ibm_bcf_internal_noise", "verdict": "WRAP_UPSTREAM"},
            {"method_id": "reed_solomon_control", "verdict": "DEFER_SYMBOL_CHANNEL"},
            {"method_id": "ldpc_control", "verdict": "DEFER_COMPLEX_CONTROL"},
            {"method_id": "polar_control", "verdict": "DEFER_COMPLEX_CONTROL"},
            {"method_id": "histogram_recovery", "verdict": "DEFER_UPSTREAM_FOR_U2_OR_NOISY_COMPOSITION"},
        ],
    }


def build_claims() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "allowed_claims": [
            "channel contracts were separated by lawful corruption semantics",
            "mature BCH symbolic controls are mandatory for Level 3.5b",
            "BCF internal stochasticity remains distinct from observation corruption",
            "raw NeCo has no authorized noisy decoder",
            "Level 3.5b must compare separate lawful channel families rather than one universal raw-p frontier",
        ],
        "forbidden_claims": [
            "equal bit-flip rate means equal semantic damage across representations",
            "ordinary coding theory can be ignored for noisy typed records",
            "raw NeCo has a validated noisy decoder",
            "Level 3.5a confirms a substrate winner",
            "one universal noise benchmark covers U1 and U2 simultaneously",
        ],
    }


def build_analysis() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_5A_CHECKPOINT_COMMIT,
        "task_scope": LEVEL3_5A_TASK_SCOPE,
        "full_benchmark_executed": False,
        "heldout_consumed": False,
        "new_decoder_implemented": False,
        "context_disabled": True,
        "controller_disabled": True,
        "cnm_disabled": True,
        "u1_u2_separated": True,
        "external_internal_noise_separated": True,
        "mandatory_bch_control_present": True,
        "uncoded_packed_not_only_non_vsa_baseline": True,
        "raw_neco_noisy_decoder_authorized": False,
        "histogram_recovery_deferred": True,
        "ready_for_level3_5b": True,
        "common_frontier_requires_separate_lawful_tracks": True,
        "overall_completion_verdict": "READY_FOR_LEVEL_3_5B",
        "next_stage": LEVEL3_5A_NEXT_STAGE,
        "limitations": [
            "No corruption probabilities are frozen until native channel ranges are searched.",
            "BCF does not yet share a universal raw bit-flip contract with the binary controls.",
            "Shortened BCH requires a thin wrapper over parent codes in galois rather than a direct constructor.",
        ],
    }


def build_docs(
    *,
    repo_root: Path,
    method_channel_compatibility: dict[str, Any],
    ecc_dependency_audit: dict[str, Any],
    proposed_cells: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[Path, str]:
    method_rows = method_channel_compatibility["rows"]
    matrix_lines = [
        "# Level 3.5a Noise Baseline Matrix",
        "",
        "| method | representation | payload contract | native decoder | external noise supported | internal stochasticity | errors supported | erasures supported | typed failure available | redundancy | storage | implementation | license | task compatibility | anti-NIH verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    matrix_rows = [
        {
            "method": "uncoded packed tuple",
            "representation": "packed factor-local bits",
            "payload": "U1 exact typed tuple",
            "decoder": "deterministic slicing",
            "external": "N0,N1,N2",
            "internal": "none",
            "errors": "no correction",
            "erasures": "no correction",
            "failure": "UNASSIGNED_CODEWORD / WRONG_RECOVERY",
            "redundancy": "none",
            "storage": "information lower bound",
            "implementation": "local trivial control",
            "license": "N/A",
            "compatibility": "binary typed record",
            "verdict": "ADOPT_BASELINE",
        },
        {
            "method": "packed tuple + BCH low redundancy",
            "representation": "packed bits + shortened BCH",
            "payload": "U1 exact typed tuple",
            "decoder": "galois BCH decode",
            "external": "N0,N1,N2",
            "internal": "none",
            "errors": "yes",
            "erasures": "yes",
            "failure": "corrected / detected_uncorrectable / silent_miscalculation",
            "redundancy": "low",
            "storage": "payload + parity",
            "implementation": "galois wrapper",
            "license": "MIT",
            "compatibility": "binary typed record",
            "verdict": "ADOPT_ECC_CONTROL",
        },
        {
            "method": "packed tuple + BCH high redundancy",
            "representation": "packed bits + shortened BCH",
            "payload": "U1 exact typed tuple",
            "decoder": "galois BCH decode",
            "external": "N0,N1,N2",
            "internal": "none",
            "errors": "yes",
            "erasures": "yes",
            "failure": "corrected / detected_uncorrectable / silent_miscalculation",
            "redundancy": "high",
            "storage": "payload + more parity",
            "implementation": "galois wrapper",
            "license": "MIT",
            "compatibility": "binary typed record",
            "verdict": "ADOPT_ECC_CONTROL",
        },
        {
            "method": "generic full-rank linear mix",
            "representation": "binary linear transform",
            "payload": "U1 exact typed tuple",
            "decoder": "GF(2) exact solve",
            "external": "N0,N1,N2",
            "internal": "none",
            "errors": "no correction",
            "erasures": "possible with mask",
            "failure": "AMBIGUOUS / INCONSISTENT / WRONG_RECOVERY",
            "redundancy": "ambient length fixed by Level 3.4",
            "storage": "generator + observation",
            "implementation": "existing Level 3.4 control",
            "license": "MIT via galois dependency",
            "compatibility": "binary typed record",
            "verdict": "WRAP_EXISTING_CONTROL",
        },
        {
            "method": "raw NeCo algebraic recovery",
            "representation": "paper direct-sum linear code",
            "payload": "U1 clean exact tuple",
            "decoder": "paper clean solve only",
            "external": "N0 only",
            "internal": "none",
            "errors": "no",
            "erasures": "not frozen",
            "failure": "AMBIGUOUS / RANK_DEFICIENT / INCONSISTENT / COLLISION",
            "redundancy": "ambient code length from paper-compatible schema",
            "storage": "generator + subcode metadata",
            "implementation": "Level 3.3 reproduction",
            "license": "local research reproduction",
            "compatibility": "clean U1 only unless a lawful noisy contract is established",
            "verdict": "WRAP_EXISTING_CLEAN_ONLY",
        },
        {
            "method": "MAP classic resonator",
            "representation": "dense bipolar MAP",
            "payload": "U1 factorization",
            "decoder": "TorchHD resonator",
            "external": "N0,N1,N2?",
            "internal": "none",
            "errors": "approximate only",
            "erasures": "preprocessing contract required",
            "failure": "WRONG_RECOVERY / NATIVE_LIMIT_REACHED",
            "redundancy": "distributed dense geometry",
            "storage": "large codebook",
            "implementation": "upstream TorchHD",
            "license": "MIT",
            "compatibility": "native MAP sign-flip track, not equal to GSBC block corruption",
            "verdict": "ADOPT_FROZEN_BASELINE",
        },
        {
            "method": "extended/restarted MAP",
            "representation": "dense bipolar MAP",
            "payload": "U1 factorization",
            "decoder": "frozen extended MAP arm",
            "external": "N0,N1,N2?",
            "internal": "none",
            "errors": "approximate only",
            "erasures": "preprocessing contract required",
            "failure": "WRONG_RECOVERY / NATIVE_LIMIT_REACHED",
            "redundancy": "distributed dense geometry",
            "storage": "large codebook",
            "implementation": "frozen Level 3.2b arm",
            "license": "MIT via TorchHD",
            "compatibility": "native MAP sign-flip track",
            "verdict": "ADOPT_FROZEN_BASELINE",
        },
        {
            "method": "official IBM BCF",
            "representation": "GSBC sparse block code",
            "payload": "U1 factorization",
            "decoder": "official IBM BCF",
            "external": "N0,N3",
            "internal": "native initialization / iteration noise supported",
            "errors": "native block-symbol track only",
            "erasures": "not a shared binary erasure contract",
            "failure": "WRONG_RECOVERY / NATIVE_LIMIT_REACHED",
            "redundancy": "block code geometry",
            "storage": "native sparse codebook",
            "implementation": "pinned upstream",
            "license": "Apache-2.0",
            "compatibility": "separate lawful noisy-product track",
            "verdict": "WRAP_UPSTREAM",
        },
        {
            "method": "tiny nearest-codeword oracle",
            "representation": "evaluator-only exhaustive control",
            "payload": "tiny U1 only",
            "decoder": "oracle",
            "external": "N0,N1,N2,N3 on tiny spaces",
            "internal": "none",
            "errors": "oracle",
            "erasures": "oracle",
            "failure": "AMBIGUOUS",
            "redundancy": "not practical",
            "storage": "enumerated evaluator state",
            "implementation": "local evaluator only",
            "license": "N/A",
            "compatibility": "debug ceiling only",
            "verdict": "ORACLE_ONLY",
        },
        {
            "method": "Reed-Solomon",
            "representation": "q-ary block code",
            "payload": "symbol channel, not default binary flip control",
            "decoder": "galois RS decode",
            "external": "N3 symbol track",
            "internal": "none",
            "errors": "yes",
            "erasures": "yes",
            "failure": "detected / miscorrected depending on setup",
            "redundancy": "symbol parity",
            "storage": "symbol codeword",
            "implementation": "available but deferred",
            "license": "MIT",
            "compatibility": "activate only for a frozen symbol channel",
            "verdict": "DEFER_SYMBOL_CHANNEL",
        },
    ]
    for row in matrix_rows:
        matrix_lines.append(
            "| {method} | {representation} | {payload} | {decoder} | {external} | {internal} | {errors} | {erasures} | {failure} | {redundancy} | {storage} | {implementation} | {license} | {compatibility} | {verdict} |".format(
                **row
            )
        )

    contracts_lines = [
        "# Level 3.5a Noise Contracts",
        "",
        f"- Verdict: `{analysis['overall_completion_verdict']}`",
        f"- Schema: `{LEVEL3_5A_SCHEMA_VERSION}`",
        f"- Checkpoint: `{LEVEL3_5A_CHECKPOINT_COMMIT}`",
        "",
        "## Frozen Frame",
        "",
        "- Clean exact U1 no longer justifies a VSA or coding substrate by itself.",
        "- Level 3.5b must therefore justify any substrate on noise, erasure, approximate observation, associative recall, or future U2 superposition rather than on clean tuple recovery alone.",
        "",
        "## External vs Internal",
        "",
        "- `external_corruption_spec`: lawful corruption applied to the already encoded observation.",
        "- `internal_decoder_noise_spec`: stochasticity injected by the decoder dynamics themselves.",
        "- These must remain separate in every trial record.",
        "- Official IBM BCF initialization or iterative noise is not observation corruption.",
        "",
        "## Noise Taxonomy",
        "",
        f"- `{N0}`: clean non-regression anchor.",
        f"- `{N1}`: binary or bipolar coordinate corruption inside a lawful serialization.",
        f"- `{N2}`: coordinate erasure with an explicit mask.",
        f"- `{N3}`: native symbol or block corruption; compare only within compatible representations.",
        f"- `{N4}`: semantic source corruption before encoding; not a primary Level 3.5b channel.",
        f"- `{N5}`: approximate perceptual observation; subject-relevant but deferred until N1/N2/N3 closure.",
        f"- `{N6}`: superposition interference; belongs to U2, not U1.",
        "",
        "## Mandatory Controls",
        "",
        "- `uncoded packed tuple` remains the information lower bound and fragility sanity control.",
        "- `packed tuple + BCH` is mandatory and must appear in at least low- and high-redundancy tiers.",
        "- `generic full-rank linear mix` remains the anti-NIH algebraic control.",
        "- `raw NeCo` stays clean-only unless a lawful noisy contract appears; no custom noisy decoder is authorized.",
        "- `official IBM BCF` is evaluated only on native noisy-product or block-symbol tracks unless a shared binary channel is formalized.",
        "",
        "## Guardrails",
        "",
        "- Zero-fill must not be described as native erasure decoding.",
        "- Equal raw bit-flip probability is not equal semantic damage across MAP, symbolic bits, and GSBC blocks.",
        "- Histogram recovery remains deferred to U2/noisy composition.",
        "- Level 3.5a adds no new decoder and executes no full benchmark.",
        "",
        "## ECC Audit Snapshot",
        "",
        f"- `galois 0.4.11` exposes BCH and Reed-Solomon encode/decode APIs with optional erasures and typed error counts where requested.",
        f"- Direct shortened BCH constructors are not exposed in the local audit smoke, so shortened controls require a thin wrapper over parent codes.",
        f"- Reed-Solomon is deferred to symbol-native tracks rather than used as the default control for binary coordinate flips.",
        "",
    ]

    draft_lines = [
        "# Level 3.5b Frozen Protocol Draft",
        "",
        "## Scope",
        "",
        "- U1 noisy single-product only.",
        "- No context, CNM, routing, pruning, or controller logic.",
        "- No held-out execution is authorized by this document.",
        "",
        "## Candidate Semantic Cells",
        "",
    ]
    for row in proposed_cells["semantic_cells"]:
        draft_lines.append(
            f"- `{row['cell_id']}`: {row['role']} (`payload_bits={row['payload_bits']}`)"
        )
    draft_lines.extend(
        [
            "",
            "## Development Search Policy",
            "",
            "- Use adaptive phase-boundary search, not a dense universal probability grid.",
            "- Development coarse pass: `16 trials per corruption point`.",
            "- Freeze per lawful track: `2 easy points`, `2 boundary points`, `1 failure point`.",
            "- Hold-out remains blocked until corruption ranges are audited and frozen.",
            "",
            "## Lawful Track Separation",
            "",
            "- `binary_channel_controls`: uncoded packed, BCH low/high, generic linear mix, raw NeCo, tiny oracle on N0/N1/N2.",
            "- `map_sign_flip`: frozen MAP arms on N0 and native sign-flip corruption, with any erasure handling logged as a separate wrapped contract.",
            "- `bcf_native_block_or_symbol`: official IBM BCF on N0 and native N3 block or symbol corruption, with internal stochasticity logged separately.",
            "",
            "## Mandatory Outputs",
            "",
            "- Exact recovery, silent wrong recovery, detected failure, and failure coverage.",
            "- Redundancy, persistent bytes, runtime bytes, and decode latency.",
            "- Channel-specific corruption descriptors rather than one universal raw percentage.",
            "",
            "## Claims Blocked",
            "",
            "- No substrate winner claim is authorized by the draft alone.",
            "- No shared binary-vs-GSBC raw-p frontier is authorized without a formal serialization contract.",
        ]
    )

    return {
        repo_root / "docs" / "LEVEL3_5A_NOISE_CONTRACTS.md": "\n".join(contracts_lines) + "\n",
        repo_root / "docs" / "LEVEL3_5A_NOISE_BASELINE_MATRIX.md": "\n".join(matrix_lines) + "\n",
        repo_root / "docs" / "LEVEL3_5B_FROZEN_PROTOCOL_DRAFT.md": "\n".join(draft_lines) + "\n",
    }


def generate_level3_5a_artifacts(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5a"
    results_dir.mkdir(parents=True, exist_ok=True)

    payload_rows = _payload_rows(repo_root)
    source_ledger = build_source_ledger()
    channel_contracts = build_channel_contracts()
    method_channel_compatibility = build_method_channel_compatibility()
    ecc_dependency_audit = build_ecc_dependency_audit()
    ecc_candidate_configs = build_ecc_candidate_configs(payload_rows)
    redundancy_accounting = build_redundancy_accounting(payload_rows, ecc_candidate_configs)
    decoder_failure_taxonomy = build_decoder_failure_taxonomy()
    fairness_contract = build_fairness_contract()
    proposed_cells = build_proposed_cells()
    implementation_ladder = build_implementation_ladder()
    claims = build_claims()
    analysis = build_analysis()

    write_json(results_dir / "source_ledger.json", source_ledger)
    write_json(results_dir / "channel_contracts.json", channel_contracts)
    write_json(results_dir / "method_channel_compatibility.json", method_channel_compatibility)
    write_json(results_dir / "ecc_dependency_audit.json", ecc_dependency_audit)
    write_json(results_dir / "ecc_candidate_configs.json", ecc_candidate_configs)
    write_json(results_dir / "redundancy_accounting.json", redundancy_accounting)
    write_json(results_dir / "decoder_failure_taxonomy.json", decoder_failure_taxonomy)
    write_json(results_dir / "fairness_contract.json", fairness_contract)
    write_json(results_dir / "proposed_cells.json", proposed_cells)
    write_json(results_dir / "implementation_ladder.json", implementation_ladder)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    docs_payloads = build_docs(
        repo_root=repo_root,
        method_channel_compatibility=method_channel_compatibility,
        ecc_dependency_audit=ecc_dependency_audit,
        proposed_cells=proposed_cells,
        analysis=analysis,
    )
    for path, content in docs_payloads.items():
        path.write_text(content, encoding="utf-8")

    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "results_dir": str(results_dir),
        "docs_written": sorted(str(path.relative_to(repo_root)) for path in docs_payloads),
        "mandatory_methods": list(MANDATORY_METHODS),
        "ready_for_level3_5b": analysis["ready_for_level3_5b"],
    }


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5A_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }
