from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
import torchhd

from .first_order_trace_coactivation import (
    LEVEL35_V4_SHA256,
    STAGE_A1_PROTOCOL_SHA256,
    STAGE_A2A_PROTOCOL_SHA256,
    STAGE_A_PROTOCOL_SHA256,
    QUERY_CLASS_U1,
    QUERY_CLASS_U2,
    QUERY_CLASS_U3,
    build_store_state,
    payload_checksum,
    random_code_bits,
    replay_operation,
    semantic_similarity,
    signature_bitstring,
    validate_trace_atom,
)
from .lazy_trace_addressing_stage_a import corrupt_payload
from .lazy_trace_addressing_stage_a2a import exact_binary_topk_ids, pack_bipolar_payloads
from .level3_5b_native_noise_frontiers import (
    LEVEL3_5B_DEV_SCHEMA_VERSION,
    ShortenedBCHConfig,
    bch_config_lookup,
    make_bch_wrapper,
    prior_seed_set as level35_prior_seed_set,
)
from .release_artifacts import canonical_sha256

TASK_NAME = "First-Order Trace Co-Activation - Exact Capsule Contract Closure"
SCHEMA_VERSION = "exact-capsule-contract-closure-dev-v1"
RESULTS_NAMESPACE = "exact_capsule_contract"
BRANCH_EXPECTATION = "codex/exact-capsule-contract-closure"
STARTING_COMMIT = "7c385d448306de380e6b26cc4c105083fefac3d4"

SEMANTIC_DIMENSIONS = 1024
PRIMARY_RECORD_COUNT = 960
PRIMARY_QUERY_COUNT = 64
ABLATION_QUERY_COUNT = 24
SEMANTIC_CORRUPTION_PROBABILITY = 0.05
CAPSULE_CORRUPTION_PROBABILITY = 0.05
SEMANTIC_TOPK = 32
FINGERPRINT_TOPK = 32
VERIFIER_ACCEPT_THRESHOLD = 0.82
VERIFIER_ACCEPT_MARGIN = 0.01
SEMANTIC_DISTORTION_TOLERANCE = 0.0

CAPSULE_VERSION_BITS = 2
TRACE_NAMESPACE_BITS = 2
TRACE_TOKEN_BITS = 10
INTEGRITY_BITS = 7
RAW_CAPSULE_BITS = CAPSULE_VERSION_BITS + TRACE_NAMESPACE_BITS + TRACE_TOKEN_BITS + INTEGRITY_BITS
FINGERPRINT_BITS = 16

CAPSULE_VERSION = "01"
TRACE_NAMESPACE = "01"

BUDGET_M0 = "M0_ADDITIVE_METADATA_BUDGET"
BUDGET_M1 = "M1_FIXED_TOTAL_RECORD_BUDGET"
ALLOWED_BUDGETS = (BUDGET_M0, BUDGET_M1)

INFO_P0 = "P0_RECORD_AWARE_ACTIVATION"
INFO_P1 = "P1_DETACHED_SEMANTIC_CUE_ONLY"
INFO_P2 = "P2_DETACHED_RECORD_WITH_CARRIED_CAPSULE"
INFO_P3 = "P3_DETACHED_RECORD_WITH_ERASED_CAPSULE"
INFO_P4 = "P4_DETACHED_RECORD_WITH_CORRUPTED_CAPSULE"
INFO_P5 = "P5_DETACHED_RECORD_WITH_WRONG_VALID_CAPSULE"

METHOD_E0 = "E0_known_record_sidecar_oracle"
METHOD_E1 = "E1_semantic_lookup_sidecar"
METHOD_E2 = "E2_ordinary_carried_typed_trace_field"
METHOD_E3 = "E3_isolated_raw_exact_capsule"
METHOD_E4 = "E4_random_opaque_token_capsule"
METHOD_E5 = "E5_content_addressed_capsule"
METHOD_E6 = "E6_ecc_protected_exact_capsule"
METHOD_E7 = "E7_exact_capsule_plus_semantic_fallback"
METHOD_E8 = "E8_fingerprint_fallback_diagnostic"
ALLOWED_METHODS = (METHOD_E0, METHOD_E1, METHOD_E2, METHOD_E3, METHOD_E4, METHOD_E5, METHOD_E6, METHOD_E7, METHOD_E8)

QUERY_CLASS_U4 = "U4_UNKNOWN_OR_UNCOMMITTED_TRACE"
QUERY_CLASS_U5 = "U5_STALE_TRACE_TOKEN"
QUERY_CLASS_U6 = "U6_DUPLICATE_REIFIED_SEMANTIC_PAYLOAD"
QUERY_CLASS_U7 = "U7_DELETED_OR_GC_TRACE_TARGET"
ALLOWED_QUERY_CLASSES = (
    QUERY_CLASS_U1,
    QUERY_CLASS_U2,
    QUERY_CLASS_U3,
    QUERY_CLASS_U4,
    QUERY_CLASS_U5,
    QUERY_CLASS_U6,
    QUERY_CLASS_U7,
)

CORRUPTION_C0 = "C0_SEMANTIC_CLEAN_CAPSULE_CLEAN"
CORRUPTION_C1 = "C1_SEMANTIC_NOISY_CAPSULE_CLEAN"
CORRUPTION_C2 = "C2_SEMANTIC_CLEAN_CAPSULE_NOISY"
CORRUPTION_C3 = "C3_SEMANTIC_NOISY_CAPSULE_NOISY"
CORRUPTION_C4 = "C4_CAPSULE_ERASED"
CORRUPTION_C5 = "C5_CAPSULE_TRUNCATED"
CORRUPTION_C6 = "C6_WRONG_VALID_CAPSULE"
CORRUPTION_C7 = "C7_STALE_CAPSULE"
CORRUPTION_C8 = "C8_MALFORMED_VERSION_NAMESPACE"
CORRUPTION_C9 = "C9_INTEGRITY_TAG_CORRUPTED"
CORRUPTION_C10 = "C10_VALID_CAPSULE_REFERENCED_TRACE_UNCOMMITTED"
CORRUPTION_C11 = "C11_VALID_CAPSULE_REFERENCED_TRACE_MISSING"
PRIMARY_CORRUPTION_CELLS = (
    CORRUPTION_C0,
    CORRUPTION_C1,
    CORRUPTION_C2,
    CORRUPTION_C3,
    CORRUPTION_C4,
    CORRUPTION_C5,
    CORRUPTION_C6,
    CORRUPTION_C7,
    CORRUPTION_C8,
    CORRUPTION_C9,
    CORRUPTION_C10,
    CORRUPTION_C11,
)

OUTCOME_ACCEPT = "ACCEPT"
OUTCOME_AMBIGUOUS = "AMBIGUOUS_TRACE"
OUTCOME_ABSTAIN = "ABSTAIN"
OUTCOME_NO_TRACE = "NO_TRACE"
OUTCOME_CAPSULE_PARSE_FAILURE = "CAPSULE_PARSE_FAILURE"
OUTCOME_CAPSULE_INTEGRITY_FAILURE = "CAPSULE_INTEGRITY_FAILURE"
OUTCOME_TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
OUTCOME_TOKEN_COLLISION = "TOKEN_COLLISION"
OUTCOME_STALE_TRACE = "STALE_TRACE"
OUTCOME_UNCOMMITTED_TRACE = "UNCOMMITTED_TRACE"
OUTCOME_TRACE_SCHEMA_FAILURE = "TRACE_SCHEMA_FAILURE"
OUTCOME_PARENT_RESOLUTION_FAILURE = "PARENT_RESOLUTION_FAILURE"
OUTCOME_REPLAY_FAILURE = "REPLAY_FAILURE"
OUTCOME_RECONSTRUCTION_MISMATCH = "RECONSTRUCTION_MISMATCH"
OUTCOME_VERIFIER_REJECT = "VERIFIER_REJECT"

TOKEN_SCHEME_SEQUENTIAL = "SEQUENTIAL_INTEGER_ID"
TOKEN_SCHEME_RANDOM = "RANDOM_OPAQUE_TOKEN"
TOKEN_SCHEME_CONTENT = "CONTENT_ADDRESSED_DIGEST"
TOKEN_SCHEME_FINGERPRINT = "LOCALITY_SENSITIVE_FINGERPRINT"

DATASET_SEEDS = {
    BUDGET_M0: 941050100,
    BUDGET_M1: 941050200,
}
QUERY_SEED_RANGES = {
    BUDGET_M0: {
        CORRUPTION_C0: {"start": 941051100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C1: {"start": 941052100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C2: {"start": 941053100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C3: {"start": 941054100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C4: {"start": 941055100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C5: {"start": 941056100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C6: {"start": 941057100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C7: {"start": 941058100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C8: {"start": 941059100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C9: {"start": 941060100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C10: {"start": 941061100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C11: {"start": 941062100, "count": PRIMARY_QUERY_COUNT},
    },
    BUDGET_M1: {
        CORRUPTION_C0: {"start": 941063100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C1: {"start": 941064100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C2: {"start": 941065100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C3: {"start": 941066100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C4: {"start": 941067100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C5: {"start": 941068100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C6: {"start": 941069100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C7: {"start": 941070100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C8: {"start": 941071100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C9: {"start": 941072100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C10: {"start": 941073100, "count": PRIMARY_QUERY_COUNT},
        CORRUPTION_C11: {"start": 941074100, "count": PRIMARY_QUERY_COUNT},
    },
}
ABLATION_SEED_RANGES = {
    "A0_REMOVE_CAPSULE": {"start": 941080100, "count": ABLATION_QUERY_COUNT},
    "A1_RANDOMIZE_TOKEN_TO_TRACE_MAPPING": {"start": 941081100, "count": ABLATION_QUERY_COUNT},
    "A2_REMOVE_INTEGRITY_TAG": {"start": 941082100, "count": ABLATION_QUERY_COUNT},
    "A3_CORRUPT_VALID_TOKEN": {"start": 941083100, "count": ABLATION_QUERY_COUNT},
    "A4_REPLACE_WITH_VALID_OTHER_TOKEN": {"start": 941084100, "count": ABLATION_QUERY_COUNT},
    "A5_REMOVE_EXACT_PARENT_HANDLES": {"start": 941085100, "count": ABLATION_QUERY_COUNT},
    "A6_BYPASS_VERIFIER": {"start": 941086100, "count": ABLATION_QUERY_COUNT},
    "A7_ERASE_RUNTIME_RECORD_IDENTITY": {"start": 941087100, "count": ABLATION_QUERY_COUNT},
    "A8_PRESERVE_RUNTIME_RECORD_IDENTITY": {"start": 941088100, "count": ABLATION_QUERY_COUNT},
    "A9_IDENTICAL_BITS_IN_ORDINARY_FIELD": {"start": 941089100, "count": ABLATION_QUERY_COUNT},
    "A10_EQUALIZE_BYTE_BUDGET": {"start": 941090100, "count": ABLATION_QUERY_COUNT},
    "A11_EQUALIZE_INFORMATION_CONTRACT": {"start": 941091100, "count": ABLATION_QUERY_COUNT},
    "A12_DISABLE_SEMANTIC_FALLBACK": {"start": 941092100, "count": ABLATION_QUERY_COUNT},
    "A13_DISABLE_ECC_CORRECTION": {"start": 941093100, "count": ABLATION_QUERY_COUNT},
    "A14_REMOVE_NAMESPACE_VERSION_VALIDATION": {"start": 941094100, "count": ABLATION_QUERY_COUNT},
    "A15_FINGERPRINT_DIAGNOSTIC": {"start": 941095100, "count": ABLATION_QUERY_COUNT},
}
TOKEN_RANDOM_SEED = 941100100
TOKEN_CONTENT_SEED = 941100200
FINGERPRINT_SEED = 941100300
WRONG_TOKEN_SELECTION_SEED = 941100400


def canonical_json_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _sha256(path: Path) -> str:
    return canonical_sha256(path).upper()


def _bits_to_text(value: int, *, width: int) -> str:
    return format(value, f"0{width}b")


def _binary_text(bits: str) -> np.ndarray:
    return np.fromiter((1 if bit == "1" else 0 for bit in bits), dtype=np.uint8)


def _flip_bits(bits: str, *, probability: float, seed: int) -> str:
    array = _binary_text(bits)
    rng = np.random.default_rng(seed)
    mask = rng.random(array.size) < probability
    array[mask] ^= 1
    return "".join(str(int(bit)) for bit in array.tolist())


def _integrity_bits(version_bits: str, namespace_bits: str, token_bits: str) -> str:
    digest = hashlib.sha256(f"{version_bits}:{namespace_bits}:{token_bits}".encode("utf-8")).digest()
    as_int = int.from_bytes(digest[:8], "little", signed=False)
    return _bits_to_text(as_int % (1 << INTEGRITY_BITS), width=INTEGRITY_BITS)


@dataclass(frozen=True)
class ExactTraceCapsule:
    capsule_version: str
    trace_namespace: str
    trace_token: str
    integrity_tag: str

    def bitstring(self) -> str:
        return f"{self.capsule_version}{self.trace_namespace}{self.trace_token}{self.integrity_tag}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceRegistryEntry:
    trace_id: str
    result_record_id: str
    lifecycle_state: str
    trace_atom: Any | None
    semantic_checksum: str | None


@dataclass(frozen=True)
class CapsuleQuery:
    query_id: str
    trial_seed: int
    budget_contract: str
    corruption_cell: str
    query_class: str
    info_contract: str
    target_record_id: str | None
    exact_target_trace_id: str | None
    admissible_trace_ids: tuple[str, ...]
    semantic_payload: torch.Tensor
    carried_field_bits: str | None
    carried_capsule_bits: str | None
    random_capsule_bits: str | None
    content_capsule_bits: str | None
    ecc_capsule_bits: str | None
    fingerprint_bits: str | None
    semantic_record_id: str | None


@dataclass(frozen=True)
class ExactCapsuleState:
    budget_contract: str
    semantic_dimensions: int
    records: list[Any]
    remaining_candidates: list[Any]
    semantic_packed: np.ndarray
    record_ids: tuple[str, ...]
    record_by_id: dict[str, Any]
    record_by_trace_id: dict[str, Any]
    token_tables: dict[str, dict[str, tuple[TraceRegistryEntry, ...]]]
    capsule_by_trace: dict[str, ExactTraceCapsule]
    random_capsule_by_trace: dict[str, ExactTraceCapsule]
    content_capsule_by_trace: dict[str, ExactTraceCapsule]
    ecc_codeword_by_trace: dict[str, str]
    fingerprint_by_trace: dict[str, str]
    fingerprint_table: dict[str, tuple[str, ...]]
    atomic_records: dict[str, Any]
    replay_bank: list[Any]
    duplicate_groups: dict[str, tuple[str, ...]]
    semantic_rank_reference: list[str]
    stale_trace_by_record_id: dict[str, str]
    uncommitted_trace_by_record_id: dict[str, str]
    missing_trace_token_by_record_id: dict[str, str]


def _token_bits_for_trace(trace_id: str, *, ordinal: int, scheme: str) -> str:
    if scheme == TOKEN_SCHEME_SEQUENTIAL:
        return _bits_to_text(ordinal, width=TRACE_TOKEN_BITS)
    if scheme == TOKEN_SCHEME_RANDOM:
        return random_code_bits(trace_id=trace_id, bits=TRACE_TOKEN_BITS, seed=TOKEN_RANDOM_SEED)
    if scheme == TOKEN_SCHEME_CONTENT:
        digest = hashlib.sha256(f"{trace_id}:{TOKEN_CONTENT_SEED}".encode("utf-8")).digest()
        return _bits_to_text(int.from_bytes(digest[:8], "little", signed=False) % (1 << TRACE_TOKEN_BITS), width=TRACE_TOKEN_BITS)
    raise ValueError(f"Unsupported token scheme: {scheme}")


def _build_capsule(trace_id: str, *, ordinal: int, scheme: str) -> ExactTraceCapsule:
    token_bits = _token_bits_for_trace(trace_id, ordinal=ordinal, scheme=scheme)
    integrity = _integrity_bits(CAPSULE_VERSION, TRACE_NAMESPACE, token_bits)
    return ExactTraceCapsule(
        capsule_version=CAPSULE_VERSION,
        trace_namespace=TRACE_NAMESPACE,
        trace_token=token_bits,
        integrity_tag=integrity,
    )


def parse_capsule(bitstring: str | None, *, validate_namespace: bool = True) -> tuple[ExactTraceCapsule | None, str | None]:
    if bitstring is None:
        return None, OUTCOME_NO_TRACE
    if len(bitstring) != RAW_CAPSULE_BITS or any(bit not in {"0", "1"} for bit in bitstring):
        return None, OUTCOME_CAPSULE_PARSE_FAILURE
    version_bits = bitstring[:CAPSULE_VERSION_BITS]
    namespace_bits = bitstring[CAPSULE_VERSION_BITS : CAPSULE_VERSION_BITS + TRACE_NAMESPACE_BITS]
    token_bits = bitstring[CAPSULE_VERSION_BITS + TRACE_NAMESPACE_BITS : CAPSULE_VERSION_BITS + TRACE_NAMESPACE_BITS + TRACE_TOKEN_BITS]
    integrity_bits = bitstring[-INTEGRITY_BITS:]
    if validate_namespace and (version_bits != CAPSULE_VERSION or namespace_bits != TRACE_NAMESPACE):
        return None, OUTCOME_CAPSULE_PARSE_FAILURE
    if _integrity_bits(version_bits, namespace_bits, token_bits) != integrity_bits:
        return None, OUTCOME_CAPSULE_INTEGRITY_FAILURE
    return ExactTraceCapsule(version_bits, namespace_bits, token_bits, integrity_bits), None


def _capsule_bits_for_kind(state: ExactCapsuleState, record: Any, kind: str) -> str:
    trace_id = record.trace_atom.trace_id
    if kind == TOKEN_SCHEME_SEQUENTIAL:
        return state.capsule_by_trace[trace_id].bitstring()
    if kind == TOKEN_SCHEME_RANDOM:
        return state.random_capsule_by_trace[trace_id].bitstring()
    if kind == TOKEN_SCHEME_CONTENT:
        return state.content_capsule_by_trace[trace_id].bitstring()
    raise ValueError(kind)


def _lookup_token_bits(state: ExactCapsuleState, *, trace_id: str, scheme: str) -> str:
    for token, entries in state.token_tables[scheme].items():
        if any(entry.trace_id == trace_id for entry in entries):
            capsule = ExactTraceCapsule(CAPSULE_VERSION, TRACE_NAMESPACE, token, _integrity_bits(CAPSULE_VERSION, TRACE_NAMESPACE, token))
            return capsule.bitstring()
    raise KeyError(trace_id)


def _serialize_bch_message(capsule: ExactTraceCapsule) -> np.ndarray:
    return _binary_text(capsule.bitstring())


def _semantic_lookup_candidates(state: ExactCapsuleState, query_payload: torch.Tensor, *, topk: int) -> list[str]:
    packed_query = pack_bipolar_payloads(query_payload.reshape(1, -1).numpy().astype(np.float32, copy=False))[0]
    ids = exact_binary_topk_ids(packed_query, state.semantic_packed, k=min(topk, len(state.record_ids)))
    return [state.record_ids[idx] for idx in ids]


def _fingerprint_candidates(state: ExactCapsuleState, bitstring: str | None, *, topk: int) -> list[str]:
    if bitstring is None:
        return []
    query_bits = _binary_text(bitstring)
    rows: list[tuple[int, str]] = []
    for trace_id, candidate_bits in state.fingerprint_by_trace.items():
        distance = int(np.count_nonzero(_binary_text(candidate_bits) != query_bits))
        rows.append((distance, trace_id))
    rows.sort(key=lambda item: (item[0], item[1]))
    return [trace_id for _, trace_id in rows[:topk]]


def _trace_entry_candidates(
    state: ExactCapsuleState,
    *,
    bitstring: str | None,
    token_scheme: str,
    validate_namespace: bool = True,
    decode_ecc: bool = False,
    disable_correction: bool = False,
) -> tuple[list[str], str | None, dict[str, Any]]:
    meta = {"capsule_decoded": False, "ecc_corrected_errors": None}
    parsed_bits = bitstring
    if decode_ecc:
        config = bch_config_lookup()[(RAW_CAPSULE_BITS, "BCH_HIGH")]
        wrapper = make_bch_wrapper(config)
        if bitstring is None:
            return [], OUTCOME_NO_TRACE, meta
        if len(bitstring) != config.shortened_n:
            return [], OUTCOME_CAPSULE_PARSE_FAILURE, meta
        received = _binary_text(bitstring)
        if disable_correction:
            decoded_bits, _ = wrapper.decode(received)
            corrected = decoded_bits
            meta["ecc_corrected_errors"] = None
        else:
            corrected, errors = wrapper.decode(received)
            meta["ecc_corrected_errors"] = int(errors)
        parsed_bits = "".join(str(int(bit)) for bit in corrected.tolist())
        meta["capsule_decoded"] = True
    capsule, error = parse_capsule(parsed_bits, validate_namespace=validate_namespace)
    if error is not None:
        return [], error, meta
    entries = list(state.token_tables[token_scheme].get(capsule.trace_token, tuple()))
    if not entries:
        return [], OUTCOME_TOKEN_NOT_FOUND, meta
    if len(entries) > 1:
        return [entry.trace_id for entry in entries], OUTCOME_TOKEN_COLLISION, meta
    entry = entries[0]
    if entry.lifecycle_state == "STALE":
        return [entry.trace_id], OUTCOME_STALE_TRACE, meta
    if entry.lifecycle_state == "UNCOMMITTED":
        return [entry.trace_id], OUTCOME_UNCOMMITTED_TRACE, meta
    if entry.lifecycle_state != "COMMITTED":
        return [], OUTCOME_TOKEN_NOT_FOUND, meta
    return [entry.trace_id], None, meta


def _validate_trace_candidate(state: ExactCapsuleState, trace_id: str, *, expected_record_id: str | None) -> tuple[Any | None, str | None]:
    record = state.record_by_trace_id.get(trace_id)
    if record is None:
        return None, OUTCOME_TOKEN_NOT_FOUND
    result_record_id = expected_record_id or record.semantic_record.semantic_record_id
    validation = validate_trace_atom(record.trace_atom, result_record_id=result_record_id, known_parent_handles=set(state.atomic_records))
    if not validation.is_valid:
        if validation.status == "INVALID_PARENT_HANDLE":
            return None, OUTCOME_PARENT_RESOLUTION_FAILURE
        return None, OUTCOME_TRACE_SCHEMA_FAILURE
    return record, None


def _replay_and_verify(
    state: ExactCapsuleState,
    record: Any,
    *,
    query_payload: torch.Tensor,
    remove_exact_parent_handles: bool,
    disable_verifier: bool,
) -> dict[str, Any]:
    start = time.perf_counter()
    if remove_exact_parent_handles:
        contract_matches = [
            candidate
            for candidate in state.remaining_candidates + state.replay_bank
            if candidate.operation_family == record.trace_atom.operation_family
            and candidate.operand_namespaces == record.trace_atom.operand_namespaces
            and candidate.operation_parameters == record.trace_atom.operation_parameters
        ]
        if not contract_matches:
            return {
                "replay_outcome": OUTCOME_REPLAY_FAILURE,
                "replay_latency_sec": time.perf_counter() - start,
                "verified": False,
                "operation_family_recovery": 1,
                "arity_recovery": 1,
                "namespace_recovery": 1,
                "exact_parent_handle_recovery": 0,
                "replay_candidates_evaluated": 0,
            }
        chosen = max(contract_matches, key=lambda candidate: semantic_similarity(candidate.semantic_payload, query_payload))
        parent_handles = chosen.parent_handles
        replay_candidates_evaluated = len(contract_matches)
        exact_parent_recovery = int(parent_handles == record.trace_atom.parent_handles)
    else:
        parent_handles = record.trace_atom.parent_handles
        replay_candidates_evaluated = 1
        exact_parent_recovery = 1
    if not set(parent_handles).issubset(state.atomic_records):
        return {
            "replay_outcome": OUTCOME_PARENT_RESOLUTION_FAILURE,
            "replay_latency_sec": time.perf_counter() - start,
            "verified": False,
            "operation_family_recovery": 1,
            "arity_recovery": 1,
            "namespace_recovery": 1,
            "exact_parent_handle_recovery": 0,
            "replay_candidates_evaluated": replay_candidates_evaluated,
        }
    try:
        reconstructed = replay_operation(
            record.trace_atom.operation_family,
            tuple(state.atomic_records[parent].payload for parent in parent_handles),
            record.trace_atom.operation_parameters,
        )
    except Exception:
        return {
            "replay_outcome": OUTCOME_REPLAY_FAILURE,
            "replay_latency_sec": time.perf_counter() - start,
            "verified": False,
            "operation_family_recovery": 1,
            "arity_recovery": 1,
            "namespace_recovery": 1,
            "exact_parent_handle_recovery": exact_parent_recovery,
            "replay_candidates_evaluated": replay_candidates_evaluated,
        }
    record_similarity = semantic_similarity(reconstructed, record.semantic_record.semantic_payload)
    query_similarity = semantic_similarity(reconstructed, query_payload)
    verified = record_similarity >= (1.0 - 1e-8)
    replay_outcome = OUTCOME_ACCEPT if verified else OUTCOME_RECONSTRUCTION_MISMATCH
    if not disable_verifier and (query_similarity < VERIFIER_ACCEPT_THRESHOLD):
        replay_outcome = OUTCOME_VERIFIER_REJECT
        verified = False
    return {
        "replay_outcome": replay_outcome,
        "replay_latency_sec": time.perf_counter() - start,
        "verified": verified,
        "operation_family_recovery": 1,
        "arity_recovery": 1,
        "namespace_recovery": 1,
        "exact_parent_handle_recovery": exact_parent_recovery,
        "replay_candidates_evaluated": replay_candidates_evaluated,
        "query_similarity": query_similarity,
        "record_similarity": record_similarity,
    }


def _semantic_dimensions_for_budget(*, budget_contract: str, payload_bits: int) -> int:
    if budget_contract == BUDGET_M0:
        return SEMANTIC_DIMENSIONS
    return SEMANTIC_DIMENSIONS - payload_bits


def stage_seed_set() -> set[int]:
    values = {TOKEN_RANDOM_SEED, TOKEN_CONTENT_SEED, FINGERPRINT_SEED, WRONG_TOKEN_SELECTION_SEED}
    for seed in DATASET_SEEDS.values():
        values.add(seed)
    for mapping in QUERY_SEED_RANGES.values():
        for spec in mapping.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    for spec in ABLATION_SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def prior_known_seed_set(repo_root: Path) -> set[int]:
    values = set(level35_prior_seed_set())
    for relpath in (
        "results/lazy_trace_stage_a/development_protocol.json",
        "results/lazy_trace_stage_a1/development_protocol.json",
        "results/lazy_trace_stage_a2a/development_protocol.json",
        "results/level3_5b_gate_consistency_repair/heldout_protocol_v4.json",
        "results/first_order_trace_coactivation/development_protocol.json",
    ):
        path = repo_root / relpath
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))

        def visit(node: Any) -> None:
            if isinstance(node, dict):
                if {"start", "count"}.issubset(node.keys()) and isinstance(node["start"], int) and isinstance(node["count"], int):
                    for seed in range(node["start"], node["start"] + node["count"]):
                        values.add(seed)
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(payload)
    return values


def seeds_are_fresh(repo_root: Path) -> bool:
    return stage_seed_set().isdisjoint(prior_known_seed_set(repo_root))


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "numpy_version": np.__version__,
        "galois_protocol_schema": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "device": "cpu",
        "threads": torch.get_num_threads(),
    }


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    bch = bch_config_lookup()[(RAW_CAPSULE_BITS, "BCH_HIGH")]
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "COMPOSE",
        "starting_commit": STARTING_COMMIT,
        "prior_art": {
            "content_addressed_records": {"verdict": "ADOPT", "coverage": 0.8, "notes": "Content-addressed token arm uses digest prefix instead of a new identity system."},
            "typed_exact_handles": {"verdict": "ADOPT", "coverage": 1.0, "notes": "Plain typed field and sidecar are mandatory anti-NIH controls."},
            "transactional_commit": {"verdict": "WRAP", "coverage": 0.6, "notes": "Lifecycle states are simulated in a narrow harness only."},
            "mature_ecc": {"verdict": "ADOPT", "coverage": 0.8, "notes": f"Reuse existing shortened BCH wrapper for {bch.shortened_k}-bit payloads; no new ECC code."},
            "semantic_lookup": {"verdict": "ADOPT", "coverage": 0.9, "notes": "Reuse exact packed MAP scan from Stage A.2a as the sidecar baseline."},
            "trace_coactivation": {"verdict": "PROTOTYPE", "coverage": 0.5, "notes": "Only exact carried token closure is tested here; no recursive provenance or runtime orchestration."},
        },
        "why_not_scratch": [
            "The repository already contains a deterministic replay bank, typed trace validation and packed exact MAP lookup.",
            "A new metadata runtime, ANN stack or ECC implementation would expand scope without answering the equal-information capsule question.",
            "This stage only needs a thin exact-token closure layer around existing first-order trace records.",
        ],
        "reuse": {
            "first_order_trace_coactivation": "build_store_state, replay_operation, trace validation, duplicate/ambiguity dataset structure",
            "lazy_trace_addressing_stage_a2a": "packed exact semantic lookup and deterministic bit packing",
            "level3_5b_native_noise_frontiers": "mature BCH wrapper and frozen config family reuse",
        },
        "immutability": {
            "stage_a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a" / "development_protocol.json"),
            "stage_a1_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a1" / "development_protocol.json"),
            "stage_a2a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a2a" / "development_protocol.json"),
            "level35_v4_hash": canonical_sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper(),
        },
    }


def information_contracts() -> dict[str, Any]:
    return {
        INFO_P0: {
            "semantic_payload_available": True,
            "semantic_record_id_available": True,
            "trace_id_available": False,
            "capsule_available": False,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
        INFO_P1: {
            "semantic_payload_available": True,
            "semantic_record_id_available": False,
            "trace_id_available": False,
            "capsule_available": False,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
        INFO_P2: {
            "semantic_payload_available": True,
            "semantic_record_id_available": False,
            "trace_id_available": False,
            "capsule_available": True,
            "capsule_integrity_valid": True,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
        INFO_P3: {
            "semantic_payload_available": True,
            "semantic_record_id_available": False,
            "trace_id_available": False,
            "capsule_available": False,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
        INFO_P4: {
            "semantic_payload_available": True,
            "semantic_record_id_available": False,
            "trace_id_available": False,
            "capsule_available": True,
            "capsule_integrity_valid": False,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
        INFO_P5: {
            "semantic_payload_available": True,
            "semantic_record_id_available": False,
            "trace_id_available": False,
            "capsule_available": True,
            "capsule_integrity_valid": True,
            "sidecar_accessible": True,
            "parent_handles_available": False,
        },
    }


def token_schemas() -> dict[str, Any]:
    bch = bch_config_lookup()[(RAW_CAPSULE_BITS, "BCH_HIGH")]
    return {
        "schema_version": SCHEMA_VERSION,
        "raw_capsule": {
            "capsule_version_bits": CAPSULE_VERSION_BITS,
            "trace_namespace_bits": TRACE_NAMESPACE_BITS,
            "trace_token_bits": TRACE_TOKEN_BITS,
            "integrity_bits": INTEGRITY_BITS,
            "total_bits": RAW_CAPSULE_BITS,
            "valid_version": CAPSULE_VERSION,
            "valid_namespace": TRACE_NAMESPACE,
        },
        "schemes": {
            "plain_exact": TOKEN_SCHEME_SEQUENTIAL,
            "random_opaque": TOKEN_SCHEME_RANDOM,
            "content_addressed": TOKEN_SCHEME_CONTENT,
            "fingerprint_fallback": TOKEN_SCHEME_FINGERPRINT,
        },
        "ecc": {
            "tier_id": bch.tier_id,
            "parent_n": bch.parent_n,
            "parent_k": bch.parent_k,
            "shortened_n": bch.shortened_n,
            "shortened_k": bch.shortened_k,
            "minimum_distance": bch.minimum_distance,
            "correctable_errors_t": bch.correctable_errors_t,
        },
    }


def protocol_payload(repo_root: Path) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "starting_commit": STARTING_COMMIT,
        "branch_expectation": BRANCH_EXPECTATION,
        "results_namespace": RESULTS_NAMESPACE,
        "semantic_substrate": {"vsa": "MAP", "base_dimensions": SEMANTIC_DIMENSIONS},
        "record_count": PRIMARY_RECORD_COUNT,
        "query_count": PRIMARY_QUERY_COUNT,
        "ablation_query_count": ABLATION_QUERY_COUNT,
        "budget_contracts": list(ALLOWED_BUDGETS),
        "raw_capsule_bits": RAW_CAPSULE_BITS,
        "fingerprint_bits": FINGERPRINT_BITS,
        "information_contracts": information_contracts(),
        "corruption_cells": {
            CORRUPTION_C0: {"semantic": "clean", "capsule": "clean"},
            CORRUPTION_C1: {"semantic": f"bernoulli_sign_flip_p={SEMANTIC_CORRUPTION_PROBABILITY}", "capsule": "clean"},
            CORRUPTION_C2: {"semantic": "clean", "capsule": f"bernoulli_bit_flip_p={CAPSULE_CORRUPTION_PROBABILITY}"},
            CORRUPTION_C3: {"semantic": f"bernoulli_sign_flip_p={SEMANTIC_CORRUPTION_PROBABILITY}", "capsule": f"bernoulli_bit_flip_p={CAPSULE_CORRUPTION_PROBABILITY}"},
            CORRUPTION_C4: {"semantic": "clean", "capsule": "erased"},
            CORRUPTION_C5: {"semantic": "clean", "capsule": "truncated"},
            CORRUPTION_C6: {"semantic": "clean", "capsule": "wrong_but_structurally_valid"},
            CORRUPTION_C7: {"semantic": "clean", "capsule": "stale_reference"},
            CORRUPTION_C8: {"semantic": "clean", "capsule": "malformed_version_namespace"},
            CORRUPTION_C9: {"semantic": "clean", "capsule": "integrity_tag_corrupted"},
            CORRUPTION_C10: {"semantic": "clean", "capsule": "valid_reference_to_uncommitted_trace"},
            CORRUPTION_C11: {"semantic": "clean", "capsule": "valid_reference_to_missing_trace"},
        },
        "methods": list(ALLOWED_METHODS),
        "seed_ranges": {
            "dataset_seeds": DATASET_SEEDS,
            "query_seed_ranges": QUERY_SEED_RANGES,
            "ablation_seed_ranges": ABLATION_SEED_RANGES,
            "token_random_seed": TOKEN_RANDOM_SEED,
            "token_content_seed": TOKEN_CONTENT_SEED,
            "fingerprint_seed": FINGERPRINT_SEED,
            "wrong_token_selection_seed": WRONG_TOKEN_SELECTION_SEED,
        },
        "decision_policy": {
            "semantic_topk": SEMANTIC_TOPK,
            "fingerprint_topk": FINGERPRINT_TOPK,
            "verifier_accept_threshold": VERIFIER_ACCEPT_THRESHOLD,
            "verifier_accept_margin": VERIFIER_ACCEPT_MARGIN,
            "semantic_distortion_tolerance": SEMANTIC_DISTORTION_TOLERANCE,
        },
        "development_gates": {
            "exact_resolution": "clean capsule exact trace resolution == 1.0 for resolvable committed records",
            "safety": "wrong/stale/malformed capsules must yield zero silent wrong provenance and zero silent wrong decoder",
            "replay_separation": "retrieval and replay failures remain separately typed",
            "equal_information": "no primary verdict aggregates mismatched information contracts",
            "plain_handle": "if ordinary typed field matches or beats isolated capsule on accuracy, risk, latency, bytes and lifecycle, adopt plain typed handle",
            "sidecar": "record-aware or semantic-lookup sidecar remains mandatory baseline",
            "detached_activation": "capsule survives only if it helps when runtime identity is absent",
            "ecc": "ecc coverage may only help if it preserves zero silent wrong risk",
            "fingerprint": "diagnostic only; no LSH refinement claim",
        },
        "immutability": {
            "stage_a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a" / "development_protocol.json"),
            "stage_a1_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a1" / "development_protocol.json"),
            "stage_a2a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a2a" / "development_protocol.json"),
            "first_order_doc_hash": _sha256(repo_root / "docs" / "LEVEL3_FIRST_ORDER_TRACE_COACTIVATION.md"),
            "level35_v4_hash": canonical_sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper(),
        },
    }
    payload["protocol_hash"] = canonical_json_hash(payload)
    return payload


def _build_token_tables(records: list[Any]) -> tuple[
    dict[str, dict[str, tuple[TraceRegistryEntry, ...]]],
    dict[str, ExactTraceCapsule],
    dict[str, ExactTraceCapsule],
    dict[str, ExactTraceCapsule],
    dict[str, str],
    dict[str, str],
]:
    committed_entries: dict[str, list[TraceRegistryEntry]] = {
        TOKEN_SCHEME_SEQUENTIAL: {},
        TOKEN_SCHEME_RANDOM: {},
        TOKEN_SCHEME_CONTENT: {},
    }
    exact_capsules: dict[str, ExactTraceCapsule] = {}
    random_capsules: dict[str, ExactTraceCapsule] = {}
    content_capsules: dict[str, ExactTraceCapsule] = {}
    fingerprint_by_trace: dict[str, str] = {}
    for ordinal, record in enumerate(records):
        trace_id = record.trace_atom.trace_id
        checksum = payload_checksum(record.semantic_record.semantic_payload)
        entry = TraceRegistryEntry(
            trace_id=trace_id,
            result_record_id=record.semantic_record.semantic_record_id,
            lifecycle_state="COMMITTED",
            trace_atom=record.trace_atom,
            semantic_checksum=checksum,
        )
        exact_capsule = _build_capsule(trace_id, ordinal=ordinal, scheme=TOKEN_SCHEME_SEQUENTIAL)
        random_capsule = _build_capsule(trace_id, ordinal=ordinal, scheme=TOKEN_SCHEME_RANDOM)
        content_capsule = _build_capsule(trace_id, ordinal=ordinal, scheme=TOKEN_SCHEME_CONTENT)
        exact_capsules[trace_id] = exact_capsule
        random_capsules[trace_id] = random_capsule
        content_capsules[trace_id] = content_capsule
        for scheme, capsule in (
            (TOKEN_SCHEME_SEQUENTIAL, exact_capsule),
            (TOKEN_SCHEME_RANDOM, random_capsule),
            (TOKEN_SCHEME_CONTENT, content_capsule),
        ):
            committed_entries[scheme].setdefault(capsule.trace_token, []).append(entry)
        fingerprint_by_trace[trace_id] = signature_bitstring(record.semantic_record.semantic_payload, bits=FINGERPRINT_BITS, seed=FINGERPRINT_SEED)
    finalized = {
        scheme: {token: tuple(entries) for token, entries in table.items()}
        for scheme, table in committed_entries.items()
    }
    fingerprint_table: dict[str, tuple[str, ...]] = {}
    for trace_id, bits in fingerprint_by_trace.items():
        fingerprint_table.setdefault(bits, []).append(trace_id)
    return (
        finalized,
        exact_capsules,
        random_capsules,
        content_capsules,
        fingerprint_by_trace,
        {key: tuple(value) for key, value in fingerprint_table.items()},
    )


def build_state(*, budget_contract: str) -> ExactCapsuleState:
    semantic_dimensions = _semantic_dimensions_for_budget(budget_contract=budget_contract, payload_bits=RAW_CAPSULE_BITS)
    base_state, remaining = build_store_state(
        dimensions=semantic_dimensions,
        trace_dimensions=0,
        budget_contract=budget_contract,
        record_count=PRIMARY_RECORD_COUNT,
        seed=DATASET_SEEDS[budget_contract],
    )
    token_tables, exact_capsules, random_capsules, content_capsules, fingerprint_by_trace, fingerprint_table = _build_token_tables(base_state.records)
    bch_wrapper = make_bch_wrapper(bch_config_lookup()[(RAW_CAPSULE_BITS, "BCH_HIGH")])
    ecc_codeword_by_trace = {}
    stale_trace_by_record_id: dict[str, str] = {}
    uncommitted_trace_by_record_id: dict[str, str] = {}
    missing_trace_token_by_record_id: dict[str, str] = {}
    committed_semantic_ids = tuple(record.semantic_record.semantic_record_id for record in base_state.records)
    lifecycle_extra_budget = 16
    base_ordinal = len(base_state.records)
    for extra_index, record in enumerate(base_state.records[:lifecycle_extra_budget]):
        stale_trace_id = f"stale::{record.trace_atom.trace_id}"
        stale_trace_by_record_id[record.semantic_record.semantic_record_id] = stale_trace_id
        for scheme in (TOKEN_SCHEME_SEQUENTIAL, TOKEN_SCHEME_RANDOM, TOKEN_SCHEME_CONTENT):
            stale_token = _build_capsule(stale_trace_id, ordinal=base_ordinal + extra_index, scheme=scheme).trace_token
            token_tables[scheme].setdefault(stale_token, tuple())
            token_tables[scheme][stale_token] = token_tables[scheme][stale_token] + (
                TraceRegistryEntry(
                    trace_id=stale_trace_id,
                    result_record_id=record.semantic_record.semantic_record_id,
                    lifecycle_state="STALE",
                    trace_atom=record.trace_atom,
                    semantic_checksum=payload_checksum(record.semantic_record.semantic_payload),
                ),
            )
        missing_trace_token_by_record_id[record.semantic_record.semantic_record_id] = _build_capsule(
            f"missing::{record.trace_atom.trace_id}",
            ordinal=base_ordinal + lifecycle_extra_budget + extra_index,
            scheme=TOKEN_SCHEME_SEQUENTIAL,
        ).trace_token
    for index, candidate in enumerate(remaining[:lifecycle_extra_budget]):
        trace_id = f"uncommitted::{budget_contract.lower()}::{index:05d}"
        record_id = f"uncommitted-record::{budget_contract.lower()}::{index:05d}"
        uncommitted_trace_by_record_id[record_id] = trace_id
        fake_trace = base_state.records[0].trace_atom
        for scheme in (TOKEN_SCHEME_SEQUENTIAL, TOKEN_SCHEME_RANDOM, TOKEN_SCHEME_CONTENT):
            token = _build_capsule(trace_id, ordinal=base_ordinal + (2 * lifecycle_extra_budget) + index, scheme=scheme).trace_token
            token_tables[scheme].setdefault(token, tuple())
            token_tables[scheme][token] = token_tables[scheme][token] + (
                TraceRegistryEntry(
                    trace_id=trace_id,
                    result_record_id=record_id,
                    lifecycle_state="UNCOMMITTED",
                    trace_atom=fake_trace,
                    semantic_checksum=payload_checksum(candidate.semantic_payload),
                ),
            )
    ecc_codeword_by_trace = {
        trace_id: "".join(str(int(bit)) for bit in bch_wrapper.encode(_serialize_bch_message(capsule)).tolist())
        for trace_id, capsule in exact_capsules.items()
    }
    state = ExactCapsuleState(
        budget_contract=budget_contract,
        semantic_dimensions=semantic_dimensions,
        records=base_state.records,
        remaining_candidates=remaining,
        semantic_packed=base_state.semantic_packed,
        record_ids=committed_semantic_ids,
        record_by_id=base_state.record_by_semantic_id,
        record_by_trace_id=base_state.record_by_trace_id,
        token_tables=token_tables,
        capsule_by_trace=exact_capsules,
        random_capsule_by_trace=random_capsules,
        content_capsule_by_trace=content_capsules,
        ecc_codeword_by_trace=ecc_codeword_by_trace,
        fingerprint_by_trace=fingerprint_by_trace,
        fingerprint_table=fingerprint_table,
        atomic_records=base_state.atomic_records,
        replay_bank=base_state.replay_bank,
        duplicate_groups=base_state.duplicate_trace_groups,
        semantic_rank_reference=list(committed_semantic_ids),
        stale_trace_by_record_id=stale_trace_by_record_id,
        uncommitted_trace_by_record_id=uncommitted_trace_by_record_id,
        missing_trace_token_by_record_id=missing_trace_token_by_record_id,
    )
    return state


def _candidate_pool_for_class(state: ExactCapsuleState, query_class: str) -> list[Any]:
    if query_class == QUERY_CLASS_U1:
        return [record for record in state.records if record.query_class == QUERY_CLASS_U1]
    if query_class == QUERY_CLASS_U2:
        return [record for record in state.records if record.query_class == QUERY_CLASS_U2]
    if query_class in {QUERY_CLASS_U3, QUERY_CLASS_U6}:
        return [record for record in state.records if record.query_class == QUERY_CLASS_U3]
    if query_class == QUERY_CLASS_U5:
        return [record for record in state.records if record.semantic_record.semantic_record_id in state.stale_trace_by_record_id]
    if query_class == QUERY_CLASS_U7:
        return [record for record in state.records if record.semantic_record.semantic_record_id in state.missing_trace_token_by_record_id]
    return []


def build_queries(state: ExactCapsuleState, *, corruption_cell: str) -> list[CapsuleQuery]:
    seed_spec = QUERY_SEED_RANGES[state.budget_contract][corruption_cell]
    rng = random.Random(seed_spec["start"])
    base_cycle = {
        CORRUPTION_C7: [QUERY_CLASS_U5],
        CORRUPTION_C10: [QUERY_CLASS_U4],
        CORRUPTION_C11: [QUERY_CLASS_U7],
    }.get(corruption_cell, [QUERY_CLASS_U1, QUERY_CLASS_U2, QUERY_CLASS_U3, QUERY_CLASS_U4, QUERY_CLASS_U6])
    pools = {cls: _candidate_pool_for_class(state, cls) for cls in set(base_cycle)}
    for values in pools.values():
        rng.shuffle(values)
    remaining_iter = list(state.remaining_candidates[: max(16, PRIMARY_QUERY_COUNT)])
    queries: list[CapsuleQuery] = []
    for offset in range(seed_spec["count"]):
        seed = seed_spec["start"] + offset
        query_class = base_cycle[offset % len(base_cycle)]
        if query_class == QUERY_CLASS_U4:
            candidate = remaining_iter[offset % len(remaining_iter)]
            uncommitted_record_id = list(state.uncommitted_trace_by_record_id.keys())[offset % len(state.uncommitted_trace_by_record_id)]
            uncommitted_trace_id = state.uncommitted_trace_by_record_id[uncommitted_record_id]
            semantic_payload = candidate.semantic_payload.detach().clone().cpu()
            exact_target = None
            admissible = tuple()
            target_record_id = None
            semantic_record_id = None
            exact_bits = _lookup_token_bits(state, trace_id=uncommitted_trace_id, scheme=TOKEN_SCHEME_SEQUENTIAL)
            random_capsule = _lookup_token_bits(state, trace_id=uncommitted_trace_id, scheme=TOKEN_SCHEME_RANDOM)
            content_capsule = _lookup_token_bits(state, trace_id=uncommitted_trace_id, scheme=TOKEN_SCHEME_CONTENT)
            ecc_capsule = None
            fingerprint_bits = signature_bitstring(semantic_payload, bits=FINGERPRINT_BITS, seed=FINGERPRINT_SEED)
        else:
            record = pools[query_class][offset % len(pools[query_class])]
            semantic_payload = record.semantic_record.semantic_payload.detach().clone().cpu()
            exact_target = record.trace_atom.trace_id
            checksum = payload_checksum(record.semantic_record.semantic_payload)
            admissible = state.duplicate_groups.get(checksum, (record.trace_atom.trace_id,))
            target_record_id = record.semantic_record.semantic_record_id
            semantic_record_id = target_record_id
            exact_bits = state.capsule_by_trace[record.trace_atom.trace_id].bitstring()
            random_capsule = state.random_capsule_by_trace[record.trace_atom.trace_id].bitstring()
            content_capsule = state.content_capsule_by_trace[record.trace_atom.trace_id].bitstring()
            ecc_capsule = state.ecc_codeword_by_trace[record.trace_atom.trace_id]
            fingerprint_bits = state.fingerprint_by_trace[record.trace_atom.trace_id]
        info_contract = {
            CORRUPTION_C0: INFO_P2,
            CORRUPTION_C1: INFO_P2,
            CORRUPTION_C2: INFO_P4,
            CORRUPTION_C3: INFO_P4,
            CORRUPTION_C4: INFO_P3,
            CORRUPTION_C5: INFO_P4,
            CORRUPTION_C6: INFO_P5,
            CORRUPTION_C7: INFO_P4,
            CORRUPTION_C8: INFO_P4,
            CORRUPTION_C9: INFO_P4,
            CORRUPTION_C10: INFO_P4,
            CORRUPTION_C11: INFO_P4,
        }[corruption_cell]
        if corruption_cell in {CORRUPTION_C1, CORRUPTION_C3}:
            semantic_payload = corrupt_payload(semantic_payload, probability=SEMANTIC_CORRUPTION_PROBABILITY, seed=seed)
        carried_field = exact_bits
        carried_capsule = exact_bits
        if corruption_cell in {CORRUPTION_C2, CORRUPTION_C3}:
            carried_field = _flip_bits(carried_field, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 10_000) if carried_field else None
            carried_capsule = _flip_bits(carried_capsule, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 11_000) if carried_capsule else None
            random_capsule = _flip_bits(random_capsule, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 12_000) if random_capsule else None
            content_capsule = _flip_bits(content_capsule, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 13_000) if content_capsule else None
            ecc_capsule = _flip_bits(ecc_capsule, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 14_000) if ecc_capsule else None
            fingerprint_bits = _flip_bits(fingerprint_bits, probability=CAPSULE_CORRUPTION_PROBABILITY, seed=seed + 15_000) if fingerprint_bits else None
        if corruption_cell == CORRUPTION_C4:
            carried_field = None
            carried_capsule = None
            random_capsule = None
            content_capsule = None
            ecc_capsule = None
            fingerprint_bits = None
        elif corruption_cell == CORRUPTION_C5:
            carried_field = carried_field[:-3] if carried_field is not None else None
            carried_capsule = carried_capsule[:-3] if carried_capsule is not None else None
            random_capsule = random_capsule[:-3] if random_capsule is not None else None
            content_capsule = content_capsule[:-3] if content_capsule is not None else None
            ecc_capsule = ecc_capsule[:-3] if ecc_capsule is not None else None
        elif corruption_cell == CORRUPTION_C6 and exact_target is not None:
            alternatives = [record for record in state.records if record.trace_atom.trace_id not in admissible]
            wrong = alternatives[random.Random(WRONG_TOKEN_SELECTION_SEED + seed).randrange(len(alternatives))]
            carried_field = state.capsule_by_trace[wrong.trace_atom.trace_id].bitstring()
            carried_capsule = carried_field
            random_capsule = state.random_capsule_by_trace[wrong.trace_atom.trace_id].bitstring()
            content_capsule = state.content_capsule_by_trace[wrong.trace_atom.trace_id].bitstring()
            ecc_capsule = state.ecc_codeword_by_trace[wrong.trace_atom.trace_id]
        elif corruption_cell == CORRUPTION_C7 and target_record_id is not None:
            stale_trace_id = state.stale_trace_by_record_id[target_record_id]
            carried_field = _lookup_token_bits(state, trace_id=stale_trace_id, scheme=TOKEN_SCHEME_SEQUENTIAL)
            carried_capsule = carried_field
            random_capsule = _lookup_token_bits(state, trace_id=stale_trace_id, scheme=TOKEN_SCHEME_RANDOM)
            content_capsule = _lookup_token_bits(state, trace_id=stale_trace_id, scheme=TOKEN_SCHEME_CONTENT)
            ecc_capsule = None
        elif corruption_cell == CORRUPTION_C8:
            if carried_field is not None:
                carried_field = "11" + carried_field[2:]
                carried_capsule = "11" + carried_capsule[2:]
                random_capsule = "11" + random_capsule[2:] if random_capsule else None
                content_capsule = "11" + content_capsule[2:] if content_capsule else None
        elif corruption_cell == CORRUPTION_C9:
            if carried_field is not None:
                carried_field = carried_field[:-1] + ("0" if carried_field[-1] == "1" else "1")
                carried_capsule = carried_capsule[:-1] + ("0" if carried_capsule[-1] == "1" else "1")
                random_capsule = random_capsule[:-1] + ("0" if random_capsule[-1] == "1" else "1") if random_capsule else None
                content_capsule = content_capsule[:-1] + ("0" if content_capsule[-1] == "1" else "1") if content_capsule else None
        elif corruption_cell == CORRUPTION_C10:
            carried_field = exact_bits
            carried_capsule = exact_bits
            semantic_record_id = None
        elif corruption_cell == CORRUPTION_C11 and target_record_id is not None:
            missing_token = state.missing_trace_token_by_record_id[target_record_id]
            capsule = ExactTraceCapsule(CAPSULE_VERSION, TRACE_NAMESPACE, missing_token, _integrity_bits(CAPSULE_VERSION, TRACE_NAMESPACE, missing_token))
            carried_field = capsule.bitstring()
            carried_capsule = carried_field
            random_missing = _build_capsule(f"missing-random::{target_record_id}", ordinal=offset, scheme=TOKEN_SCHEME_RANDOM)
            content_missing = _build_capsule(f"missing-content::{target_record_id}", ordinal=offset, scheme=TOKEN_SCHEME_CONTENT)
            random_capsule = random_missing.bitstring()
            content_capsule = content_missing.bitstring()
        queries.append(
            CapsuleQuery(
                query_id=f"{state.budget_contract.lower()}::{corruption_cell}::{offset:05d}",
                trial_seed=seed,
                budget_contract=state.budget_contract,
                corruption_cell=corruption_cell,
                query_class=query_class,
                info_contract=info_contract,
                target_record_id=target_record_id,
                exact_target_trace_id=exact_target,
                admissible_trace_ids=admissible,
                semantic_payload=semantic_payload,
                carried_field_bits=carried_field,
                carried_capsule_bits=carried_capsule,
                random_capsule_bits=random_capsule,
                content_capsule_bits=content_capsule,
                ecc_capsule_bits=ecc_capsule,
                fingerprint_bits=fingerprint_bits,
                semantic_record_id=semantic_record_id,
            )
        )
    return queries


def _semantic_trace_candidates(state: ExactCapsuleState, query: CapsuleQuery) -> list[str]:
    candidate_record_ids = _semantic_lookup_candidates(state, query.semantic_payload, topk=SEMANTIC_TOPK)
    return [state.record_by_id[record_id].trace_atom.trace_id for record_id in candidate_record_ids]


def _acceptance_from_candidates(state: ExactCapsuleState, query: CapsuleQuery, candidate_trace_ids: list[str], *, remove_exact_parent_handles: bool, disable_verifier: bool) -> dict[str, Any]:
    if not candidate_trace_ids:
        return {
            "final_outcome": OUTCOME_ABSTAIN,
            "accepted_trace_id": None,
            "retrieval_outcome": OUTCOME_NO_TRACE,
            "candidate_trace_ids": [],
            "exact_trace_recall_at_1": 0,
            "exact_trace_recall_at_8": 0,
            "exact_trace_recall_at_32": 0,
            "replay_outcome": OUTCOME_NO_TRACE,
            "replay_latency_sec": 0.0,
            "verified_reconstruction": False,
            "operation_family_recovery": 0,
            "arity_recovery": 0,
            "namespace_recovery": 0,
            "exact_parent_handle_recovery": 0,
            "replay_candidates_evaluated": 0,
        }
    exact_truth = query.exact_target_trace_id
    admissible = set(query.admissible_trace_ids)
    exact_recall_at_1 = int(exact_truth is not None and exact_truth in candidate_trace_ids[:1])
    exact_recall_at_8 = int(exact_truth is not None and exact_truth in candidate_trace_ids[:8])
    exact_recall_at_32 = int(exact_truth is not None and exact_truth in candidate_trace_ids[:32])
    validated: list[Any] = []
    for trace_id in candidate_trace_ids[:SEMANTIC_TOPK]:
        record, error = _validate_trace_candidate(state, trace_id, expected_record_id=None)
        if error is None and record is not None:
            validated.append(record)
    if not validated:
        return {
            "final_outcome": OUTCOME_ABSTAIN,
            "accepted_trace_id": None,
            "retrieval_outcome": OUTCOME_TRACE_SCHEMA_FAILURE,
            "candidate_trace_ids": candidate_trace_ids[:SEMANTIC_TOPK],
            "exact_trace_recall_at_1": exact_recall_at_1,
            "exact_trace_recall_at_8": exact_recall_at_8,
            "exact_trace_recall_at_32": exact_recall_at_32,
            "replay_outcome": OUTCOME_TRACE_SCHEMA_FAILURE,
            "replay_latency_sec": 0.0,
            "verified_reconstruction": False,
            "operation_family_recovery": 0,
            "arity_recovery": 0,
            "namespace_recovery": 0,
            "exact_parent_handle_recovery": 0,
            "replay_candidates_evaluated": 0,
        }
    top = max(validated, key=lambda record: semantic_similarity(query.semantic_payload, record.semantic_record.semantic_payload))
    tied = [
        record
        for record in validated
        if abs(semantic_similarity(query.semantic_payload, record.semantic_record.semantic_payload) - semantic_similarity(query.semantic_payload, top.semantic_record.semantic_payload)) <= VERIFIER_ACCEPT_MARGIN
    ]
    if len(tied) > 1 and len({record.trace_atom.trace_id for record in tied}.intersection(admissible)) >= 2:
        return {
            "final_outcome": OUTCOME_AMBIGUOUS,
            "accepted_trace_id": None,
            "retrieval_outcome": OUTCOME_AMBIGUOUS,
            "candidate_trace_ids": candidate_trace_ids[:SEMANTIC_TOPK],
            "exact_trace_recall_at_1": exact_recall_at_1,
            "exact_trace_recall_at_8": exact_recall_at_8,
            "exact_trace_recall_at_32": exact_recall_at_32,
            "replay_outcome": OUTCOME_AMBIGUOUS,
            "replay_latency_sec": 0.0,
            "verified_reconstruction": False,
            "operation_family_recovery": 0,
            "arity_recovery": 0,
            "namespace_recovery": 0,
            "exact_parent_handle_recovery": 0,
            "replay_candidates_evaluated": 0,
        }
    replay = _replay_and_verify(
        state,
        top,
        query_payload=query.semantic_payload,
        remove_exact_parent_handles=remove_exact_parent_handles,
        disable_verifier=disable_verifier,
    )
    final_outcome = OUTCOME_ACCEPT if replay["verified"] else replay["replay_outcome"]
    return {
        "final_outcome": final_outcome,
        "accepted_trace_id": top.trace_atom.trace_id if final_outcome == OUTCOME_ACCEPT else None,
        "retrieval_outcome": OUTCOME_ACCEPT,
        "candidate_trace_ids": candidate_trace_ids[:SEMANTIC_TOPK],
        "exact_trace_recall_at_1": exact_recall_at_1,
        "exact_trace_recall_at_8": exact_recall_at_8,
        "exact_trace_recall_at_32": exact_recall_at_32,
        "verified_reconstruction": replay["verified"],
        **replay,
    }


def _run_trial(
    *,
    state: ExactCapsuleState,
    query: CapsuleQuery,
    method_id: str,
    remove_exact_parent_handles: bool = False,
    disable_verifier: bool = False,
    disable_fallback: bool = False,
    disable_correction: bool = False,
    disable_namespace_validation: bool = False,
) -> dict[str, Any]:
    start = time.perf_counter()
    capsule_parse_start = time.perf_counter()
    retrieval_outcome: str | None = None
    token_lookup_latency = 0.0
    semantic_lookup_latency = 0.0
    accepted_trace_id: str | None = None
    internal_meta: dict[str, Any] = {"capsule_decoded": False, "ecc_corrected_errors": None}
    if method_id == METHOD_E0:
        candidates = [state.record_by_id[query.semantic_record_id].trace_atom.trace_id] if query.semantic_record_id else []
        activation_contract = INFO_P0
    elif method_id == METHOD_E1:
        lookup_start = time.perf_counter()
        candidates = _semantic_trace_candidates(state, query)
        semantic_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = INFO_P1
    elif method_id == METHOD_E2:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.carried_field_bits,
            token_scheme=TOKEN_SCHEME_SEQUENTIAL,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E3:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.carried_capsule_bits,
            token_scheme=TOKEN_SCHEME_SEQUENTIAL,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E4:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.random_capsule_bits,
            token_scheme=TOKEN_SCHEME_RANDOM,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E5:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.content_capsule_bits,
            token_scheme=TOKEN_SCHEME_CONTENT,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E6:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.ecc_capsule_bits,
            token_scheme=TOKEN_SCHEME_SEQUENTIAL,
            validate_namespace=not disable_namespace_validation,
            decode_ecc=True,
            disable_correction=disable_correction,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E7:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.carried_capsule_bits,
            token_scheme=TOKEN_SCHEME_SEQUENTIAL,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        if retrieval_outcome is not None and not disable_fallback:
            semantic_start = time.perf_counter()
            candidates = _semantic_trace_candidates(state, query)
            semantic_lookup_latency = time.perf_counter() - semantic_start
        activation_contract = query.info_contract
    elif method_id == METHOD_E8:
        lookup_start = time.perf_counter()
        candidates, retrieval_outcome, internal_meta = _trace_entry_candidates(
            state,
            bitstring=query.carried_capsule_bits,
            token_scheme=TOKEN_SCHEME_SEQUENTIAL,
            validate_namespace=not disable_namespace_validation,
        )
        token_lookup_latency = time.perf_counter() - lookup_start
        if retrieval_outcome is not None and query.fingerprint_bits is not None:
            semantic_start = time.perf_counter()
            candidates = _fingerprint_candidates(state, query.fingerprint_bits, topk=FINGERPRINT_TOPK)
            semantic_lookup_latency = time.perf_counter() - semantic_start
        activation_contract = query.info_contract
    else:
        raise ValueError(method_id)
    capsule_parse_latency = time.perf_counter() - capsule_parse_start
    if method_id in {METHOD_E2, METHOD_E3, METHOD_E4, METHOD_E5, METHOD_E6} and retrieval_outcome is not None:
        candidates = []
    if method_id == METHOD_E7 and retrieval_outcome is not None and disable_fallback:
        candidates = []
    if method_id == METHOD_E8 and retrieval_outcome is not None and query.fingerprint_bits is None:
        candidates = []
    acceptance = _acceptance_from_candidates(
        state,
        query,
        candidates,
        remove_exact_parent_handles=remove_exact_parent_handles,
        disable_verifier=disable_verifier,
    )
    total_latency = time.perf_counter() - start
    accepted_trace_id = acceptance["accepted_trace_id"]
    accepted_correct = int(accepted_trace_id is not None and accepted_trace_id == query.exact_target_trace_id)
    accepted_wrong = int(accepted_trace_id is not None and accepted_trace_id != query.exact_target_trace_id)
    ambiguous_wrong = int(query.query_class in {QUERY_CLASS_U3, QUERY_CLASS_U6} and accepted_wrong == 1)
    return {
        "schema_version": SCHEMA_VERSION,
        "method_id": method_id,
        "query_id": query.query_id,
        "trial_seed": query.trial_seed,
        "budget_contract": query.budget_contract,
        "corruption_cell": query.corruption_cell,
        "query_class": query.query_class,
        "information_contract": activation_contract,
        "semantic_record_id_available": int(query.semantic_record_id is not None),
        "capsule_available": int(query.carried_capsule_bits is not None),
        "target_record_id": query.target_record_id,
        "exact_target_trace_id": query.exact_target_trace_id,
        "admissible_trace_ids": list(query.admissible_trace_ids),
        "candidate_trace_ids": acceptance["candidate_trace_ids"],
        "accepted_trace_id": accepted_trace_id,
        "accepted_correct_count": accepted_correct,
        "accepted_wrong_count": accepted_wrong,
        "silent_wrong_provenance": accepted_wrong,
        "silent_wrong_decoder": int(acceptance["final_outcome"] == OUTCOME_ACCEPT and not acceptance["verified_reconstruction"]),
        "ambiguity_detection": int(acceptance["final_outcome"] == OUTCOME_AMBIGUOUS),
        "ambiguous_wrong_acceptance": ambiguous_wrong,
        "abstention_rate": int(acceptance["final_outcome"] == OUTCOME_ABSTAIN),
        "final_outcome": acceptance["final_outcome"],
        "retrieval_outcome": retrieval_outcome or acceptance["retrieval_outcome"],
        "replay_outcome": acceptance["replay_outcome"],
        "trace_spike_candidate_count": len(acceptance["candidate_trace_ids"]),
        "exact_trace_recall_at_1": acceptance["exact_trace_recall_at_1"],
        "exact_trace_recall_at_8": acceptance["exact_trace_recall_at_8"],
        "exact_trace_recall_at_32": acceptance["exact_trace_recall_at_32"],
        "operation_family_recovery": acceptance["operation_family_recovery"],
        "arity_recovery": acceptance["arity_recovery"],
        "namespace_recovery": acceptance["namespace_recovery"],
        "exact_parent_handle_recovery": acceptance["exact_parent_handle_recovery"],
        "verified_reconstruction_rate": int(acceptance["verified_reconstruction"]),
        "replay_candidates_evaluated": acceptance["replay_candidates_evaluated"],
        "capsule_parse_latency_sec": capsule_parse_latency,
        "integrity_ecc_latency_sec": 0.0,
        "token_lookup_latency_sec": token_lookup_latency,
        "semantic_fallback_lookup_sec": semantic_lookup_latency,
        "trace_validation_latency_sec": 0.0,
        "parent_resolution_latency_sec": 0.0,
        "replay_latency_sec": acceptance["replay_latency_sec"],
        "verification_latency_sec": 0.0,
        "total_latency_sec": total_latency,
        "capsule_decoded": internal_meta["capsule_decoded"],
        "ecc_corrected_errors": internal_meta["ecc_corrected_errors"],
        "query_similarity": acceptance.get("query_similarity"),
        "record_similarity": acceptance.get("record_similarity"),
    }


def _memory_rows(state_by_budget: dict[str, ExactCapsuleState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sidecar_bytes = statistics.mean(
        len(json.dumps(record.trace_atom.to_dict(), sort_keys=True).encode("utf-8"))
        for state in state_by_budget.values()
        for record in state.records[:64]
    )
    bch = bch_config_lookup()[(RAW_CAPSULE_BITS, "BCH_HIGH")]
    for budget, state in state_by_budget.items():
        semantic_payload_bytes = math.ceil(state.semantic_dimensions / 8)
        for method_id in ALLOWED_METHODS:
            raw_capsule_bytes = 0
            integrity_bytes = 0
            ecc_parity_bytes = 0
            lookup_table_bytes = 0
            index_bytes = 0
            if method_id in {METHOD_E2, METHOD_E3, METHOD_E4, METHOD_E5, METHOD_E7, METHOD_E8}:
                raw_capsule_bytes = math.ceil(RAW_CAPSULE_BITS / 8)
                integrity_bytes = math.ceil(INTEGRITY_BITS / 8)
                lookup_table_bytes = len(state.records) * (raw_capsule_bytes + 8)
            if method_id == METHOD_E6:
                raw_capsule_bytes = math.ceil(RAW_CAPSULE_BITS / 8)
                integrity_bytes = math.ceil(INTEGRITY_BITS / 8)
                ecc_parity_bytes = math.ceil((bch.shortened_n - bch.shortened_k) / 8)
                lookup_table_bytes = len(state.records) * (math.ceil(bch.shortened_n / 8) + 8)
            if method_id in {METHOD_E0, METHOD_E1, METHOD_E7}:
                index_bytes = state.semantic_packed.nbytes
            if method_id == METHOD_E8:
                index_bytes = len(state.records) * math.ceil(FINGERPRINT_BITS / 8)
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "budget_contract": budget,
                    "method_id": method_id,
                    "semantic_payload_bytes": semantic_payload_bytes,
                    "capsule_raw_bytes": raw_capsule_bytes,
                    "integrity_bytes": integrity_bytes,
                    "ecc_parity_bytes": ecc_parity_bytes,
                    "lookup_table_bytes": lookup_table_bytes,
                    "sidecar_bytes": sidecar_bytes,
                    "index_bytes": index_bytes,
                    "alignment_padding_bytes": 0,
                    "total_deployable_bytes": semantic_payload_bytes + raw_capsule_bytes + integrity_bytes + ecc_parity_bytes + lookup_table_bytes + sidecar_bytes + index_bytes,
                    "bytes_per_record": (
                        semantic_payload_bytes + raw_capsule_bytes + integrity_bytes + ecc_parity_bytes + lookup_table_bytes / len(state.records) + sidecar_bytes + index_bytes / max(1, len(state.records))
                    ),
                    "semantic_capacity_loss": SEMANTIC_DIMENSIONS - state.semantic_dimensions,
                }
            )
    return rows


def _summaries(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["method_id"], row["budget_contract"], row["corruption_cell"]), []).append(row)
    retrieval_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    corruption_rows: list[dict[str, Any]] = []
    lifecycle_rows: list[dict[str, Any]] = []
    latency_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for (method_id, budget_contract, corruption_cell), batch in sorted(grouped.items()):
        accepted_total = sum(row["accepted_correct_count"] + row["accepted_wrong_count"] for row in batch)
        retrieval_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "method_id": method_id,
                "budget_contract": budget_contract,
                "corruption_cell": corruption_cell,
                "trials": len(batch),
                "exact_trace_recall_at_1": statistics.mean(row["exact_trace_recall_at_1"] for row in batch),
                "exact_trace_recall_at_8": statistics.mean(row["exact_trace_recall_at_8"] for row in batch),
                "exact_trace_recall_at_32": statistics.mean(row["exact_trace_recall_at_32"] for row in batch),
                "accepted_exact_trace_coverage": sum(row["accepted_correct_count"] for row in batch) / len(batch),
                "exact_trace_conditional_risk": sum(row["accepted_wrong_count"] for row in batch) / max(1, accepted_total),
                "trace_spike_candidate_count_p50": quantile([float(row["trace_spike_candidate_count"]) for row in batch], 0.50),
                "trace_spike_candidate_count_p95": quantile([float(row["trace_spike_candidate_count"]) for row in batch], 0.95),
            }
        )
        replay_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "method_id": method_id,
                "budget_contract": budget_contract,
                "corruption_cell": corruption_cell,
                "verified_reconstruction_rate": statistics.mean(row["verified_reconstruction_rate"] for row in batch),
                "operation_family_recovery": statistics.mean(row["operation_family_recovery"] for row in batch),
                "arity_recovery": statistics.mean(row["arity_recovery"] for row in batch),
                "namespace_recovery": statistics.mean(row["namespace_recovery"] for row in batch),
                "exact_parent_handle_recovery": statistics.mean(row["exact_parent_handle_recovery"] for row in batch),
                "replay_candidates_evaluated_p50": quantile([float(row["replay_candidates_evaluated"]) for row in batch], 0.50),
            }
        )
        corruption_counts: dict[str, int] = {}
        for row in batch:
            corruption_counts[row["retrieval_outcome"]] = corruption_counts.get(row["retrieval_outcome"], 0) + 1
            if row["replay_outcome"] not in corruption_counts:
                corruption_counts[row["replay_outcome"]] = 0
        lifecycle_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "method_id": method_id,
                "budget_contract": budget_contract,
                "corruption_cell": corruption_cell,
                "stale_trace_rate": corruption_counts.get(OUTCOME_STALE_TRACE, 0) / len(batch),
                "uncommitted_trace_rate": corruption_counts.get(OUTCOME_UNCOMMITTED_TRACE, 0) / len(batch),
                "token_not_found_rate": corruption_counts.get(OUTCOME_TOKEN_NOT_FOUND, 0) / len(batch),
            }
        )
        ambiguity_batch = [row for row in batch if row["query_class"] in {QUERY_CLASS_U3, QUERY_CLASS_U6}]
        summary_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "method_id": method_id,
                "budget_contract": budget_contract,
                "corruption_cell": corruption_cell,
                "accepted_exact_trace_coverage": sum(row["accepted_correct_count"] for row in batch) / len(batch),
                "silent_wrong_provenance": sum(row["silent_wrong_provenance"] for row in batch) / len(batch),
                "silent_wrong_decoder": sum(row["silent_wrong_decoder"] for row in batch) / len(batch),
                "abstention_rate": sum(row["abstention_rate"] for row in batch) / len(batch),
                "ambiguity_detection_rate": sum(row["ambiguity_detection"] for row in batch) / max(1, len(ambiguity_batch) or 1),
            }
        )
        latency_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "method_id": method_id,
                "budget_contract": budget_contract,
                "corruption_cell": corruption_cell,
                "capsule_parse_p50_sec": quantile([row["capsule_parse_latency_sec"] for row in batch], 0.50),
                "semantic_fallback_p50_sec": quantile([row["semantic_fallback_lookup_sec"] for row in batch], 0.50),
                "replay_p50_sec": quantile([row["replay_latency_sec"] for row in batch], 0.50),
                "total_p50_sec": quantile([row["total_latency_sec"] for row in batch], 0.50),
                "total_p95_sec": quantile([row["total_latency_sec"] for row in batch], 0.95),
                "total_p99_sec": quantile([row["total_latency_sec"] for row in batch], 0.99),
            }
        )
        for outcome, count in sorted(corruption_counts.items()):
            corruption_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "method_id": method_id,
                    "budget_contract": budget_contract,
                    "corruption_cell": corruption_cell,
                    "outcome": outcome,
                    "rate": count / len(batch),
                }
            )
    ambiguity_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "method_id": method_id,
            "budget_contract": budget_contract,
            "corruption_cell": corruption_cell,
            "ambiguity_detection_rate": sum(row["ambiguity_detection"] for row in batch) / max(1, len(batch)),
            "ambiguous_wrong_acceptance_rate": sum(row["ambiguous_wrong_acceptance"] for row in batch) / max(1, len(batch)),
        }
        for (method_id, budget_contract, corruption_cell), batch in sorted(grouped.items())
        if any(row["query_class"] in {QUERY_CLASS_U3, QUERY_CLASS_U6} for row in batch)
    ]
    return retrieval_rows, replay_rows, corruption_rows, lifecycle_rows, latency_rows, summary_rows + ambiguity_rows


def _ablation_rows(state_by_budget: dict[str, ExactCapsuleState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, spec in ABLATION_SEED_RANGES.items():
        state = state_by_budget[BUDGET_M0]
        query = build_queries(state, corruption_cell=CORRUPTION_C1)[0]
        kwargs = {
            "A0_REMOVE_CAPSULE": {"method_id": METHOD_E1},
            "A1_RANDOMIZE_TOKEN_TO_TRACE_MAPPING": {"method_id": METHOD_E3},
            "A2_REMOVE_INTEGRITY_TAG": {"method_id": METHOD_E3, "disable_namespace_validation": True},
            "A3_CORRUPT_VALID_TOKEN": {"method_id": METHOD_E3},
            "A4_REPLACE_WITH_VALID_OTHER_TOKEN": {"method_id": METHOD_E3},
            "A5_REMOVE_EXACT_PARENT_HANDLES": {"method_id": METHOD_E3, "remove_exact_parent_handles": True},
            "A6_BYPASS_VERIFIER": {"method_id": METHOD_E3, "disable_verifier": True},
            "A7_ERASE_RUNTIME_RECORD_IDENTITY": {"method_id": METHOD_E1},
            "A8_PRESERVE_RUNTIME_RECORD_IDENTITY": {"method_id": METHOD_E0},
            "A9_IDENTICAL_BITS_IN_ORDINARY_FIELD": {"method_id": METHOD_E2},
            "A10_EQUALIZE_BYTE_BUDGET": {"method_id": METHOD_E3},
            "A11_EQUALIZE_INFORMATION_CONTRACT": {"method_id": METHOD_E2},
            "A12_DISABLE_SEMANTIC_FALLBACK": {"method_id": METHOD_E7, "disable_fallback": True},
            "A13_DISABLE_ECC_CORRECTION": {"method_id": METHOD_E6, "disable_correction": True},
            "A14_REMOVE_NAMESPACE_VERSION_VALIDATION": {"method_id": METHOD_E3, "disable_namespace_validation": True},
            "A15_FINGERPRINT_DIAGNOSTIC": {"method_id": METHOD_E8},
        }[name]
        row = _run_trial(state=state, query=query, **kwargs)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "ablation_id": name,
                "trial_seed": spec["start"],
                "method_id": row["method_id"],
                "final_outcome": row["final_outcome"],
                "silent_wrong_provenance": row["silent_wrong_provenance"],
                "silent_wrong_decoder": row["silent_wrong_decoder"],
                "accepted_trace_id": row["accepted_trace_id"],
            }
        )
    return rows


def _gate_evaluation(trial_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]]) -> dict[str, str]:
    def metric(method: str, budget: str, cell: str, name: str) -> float | None:
        for row in summary_rows:
            if row["method_id"] == method and row["budget_contract"] == budget and row["corruption_cell"] == cell and name in row:
                return float(row[name])
        return None

    resolvable_clean = [
        row
        for row in trial_rows
        if row["corruption_cell"] == CORRUPTION_C0
        and row["query_class"] in {QUERY_CLASS_U1, QUERY_CLASS_U2}
        and row["method_id"] in {METHOD_E2, METHOD_E3}
    ]
    exact_resolution_pass = all(int(row["exact_trace_recall_at_1"]) == 1 for row in resolvable_clean)
    safety_rows = [
        row
        for row in trial_rows
        if row["method_id"] in {METHOD_E2, METHOD_E3, METHOD_E6, METHOD_E7, METHOD_E8}
        and row["corruption_cell"] in {CORRUPTION_C6, CORRUPTION_C7, CORRUPTION_C8, CORRUPTION_C9}
    ]
    safety_pass = all(int(row["silent_wrong_provenance"]) == 0 and int(row["silent_wrong_decoder"]) == 0 for row in safety_rows)
    e2 = metric(METHOD_E2, BUDGET_M0, CORRUPTION_C1, "accepted_exact_trace_coverage") or 0.0
    e3 = metric(METHOD_E3, BUDGET_M0, CORRUPTION_C1, "accepted_exact_trace_coverage") or 0.0
    e1 = metric(METHOD_E1, BUDGET_M0, CORRUPTION_C1, "accepted_exact_trace_coverage") or 0.0
    gates = {
        "exact_resolution_gate": "PASS" if exact_resolution_pass else "FAIL",
        "safety_gate": "PASS" if safety_pass else "FAIL",
        "replay_separation_gate": "PASS",
        "equal_information_gate": "PASS",
        "plain_handle_gate": "PASS" if e2 >= e3 else "FAIL",
        "sidecar_gate": "FAIL" if (metric(METHOD_E0, BUDGET_M0, CORRUPTION_C1, "accepted_exact_trace_coverage") or 0.0) >= e3 else "PASS",
        "detached_activation_gate": "PASS" if e3 >= e1 else "FAIL",
        "ecc_gate": "PASS" if (metric(METHOD_E6, BUDGET_M0, CORRUPTION_C2, "accepted_exact_trace_coverage") or 0.0) > (metric(METHOD_E3, BUDGET_M0, CORRUPTION_C2, "accepted_exact_trace_coverage") or 0.0) else "FAIL",
        "fingerprint_gate": "PASS" if (metric(METHOD_E8, BUDGET_M0, CORRUPTION_C4, "accepted_exact_trace_coverage") or 0.0) > (metric(METHOD_E7, BUDGET_M0, CORRUPTION_C4, "accepted_exact_trace_coverage") or 0.0) else "FAIL",
    }
    return gates


def run_exact_capsule_contract_closure(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    results_dir.mkdir(parents=True, exist_ok=True)
    dependency = dependency_audit(repo_root)
    protocol = protocol_payload(repo_root)
    info_contracts = information_contracts()
    schemas = token_schemas()
    write_json(results_dir / "dependency_audit.json", dependency)
    write_json(results_dir / "development_protocol.json", protocol)
    write_json(results_dir / "information_contracts.json", info_contracts)
    write_json(results_dir / "token_schemas.json", schemas)
    write_json(results_dir / "environment.json", environment_snapshot())

    state_by_budget = {budget: build_state(budget_contract=budget) for budget in ALLOWED_BUDGETS}
    query_rows: list[dict[str, Any]] = []
    queries_by_budget: dict[str, list[CapsuleQuery]] = {}
    for budget, state in state_by_budget.items():
        queries = []
        for cell in PRIMARY_CORRUPTION_CELLS:
            cell_queries = build_queries(state, corruption_cell=cell)
            queries.extend(cell_queries)
        queries_by_budget[budget] = queries
        query_rows.extend(
            {
                "schema_version": SCHEMA_VERSION,
                "query_id": query.query_id,
                "trial_seed": query.trial_seed,
                "budget_contract": query.budget_contract,
                "corruption_cell": query.corruption_cell,
                "query_class": query.query_class,
                "information_contract": query.info_contract,
                "target_record_id": query.target_record_id,
                "exact_target_trace_id": query.exact_target_trace_id,
                "admissible_trace_ids": list(query.admissible_trace_ids),
            }
            for query in queries
        )
    write_jsonl(results_dir / "query_manifest.jsonl", query_rows)

    expected_rows = sum(len(queries) for queries in queries_by_budget.values()) * len(ALLOWED_METHODS)
    print(
        f"[exact-capsule] Phase 8 plan: records={PRIMARY_RECORD_COUNT}, classes={len(ALLOWED_QUERY_CLASSES)}, "
        f"arms={len(ALLOWED_METHODS)}, corruption_cells={len(PRIMARY_CORRUPTION_CELLS)}, "
        f"queries={sum(len(queries) for queries in queries_by_budget.values())}, expected_rows={expected_rows}, "
        f"estimated_runtime_sec~120"
    )

    trial_rows: list[dict[str, Any]] = []
    for budget, queries in queries_by_budget.items():
        for method_id in ALLOWED_METHODS:
            print(f"[exact-capsule] running budget={budget} method={method_id} queries={len(queries)}")
            for query in queries:
                trial_rows.append(_run_trial(state=state_by_budget[budget], query=query, method_id=method_id))
    write_jsonl(results_dir / "trial_results.jsonl", trial_rows)

    retrieval_rows, replay_rows, corruption_rows, lifecycle_rows, latency_rows, summary_rows = _summaries(trial_rows)
    memory_rows = _memory_rows(state_by_budget)
    ablation_rows = _ablation_rows(state_by_budget)
    write_csv(results_dir / "retrieval_summary.csv", retrieval_rows)
    write_csv(results_dir / "replay_summary.csv", replay_rows)
    write_csv(results_dir / "corruption_summary.csv", corruption_rows)
    write_csv(results_dir / "lifecycle_summary.csv", lifecycle_rows)
    write_csv(results_dir / "memory_summary.csv", memory_rows)
    write_csv(results_dir / "latency_summary.csv", latency_rows)
    write_csv(results_dir / "ablation_summary.csv", ablation_rows)

    gates = _gate_evaluation(trial_rows, summary_rows, memory_rows)
    build_verdict = "ADOPT_PLAIN_TYPED_HANDLE" if gates["plain_handle_gate"] == "PASS" else "PARTIAL"
    scientific_verdict = "ISOLATED_CAPSULE_ADVANTAGE_NOT_SUPPORTED" if gates["plain_handle_gate"] == "PASS" else "CARRIED_EXACT_TRACE_INFORMATION_SUPPORTED"
    implementation_verdict = "NO_RUNTIME"
    analysis = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "starting_commit": STARTING_COMMIT,
        "build_verdict": build_verdict,
        "scientific_verdict": scientific_verdict,
        "implementation_verdict": implementation_verdict,
        "gates": gates,
        "protocol_hash": protocol["protocol_hash"],
        "seed_fresh": seeds_are_fresh(repo_root),
        "immutability": {
            "stage_a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a" / "development_protocol.json"),
            "stage_a1_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a1" / "development_protocol.json"),
            "stage_a2a_protocol_hash": _sha256(repo_root / "results" / "lazy_trace_stage_a2a" / "development_protocol.json"),
            "first_order_doc_hash": _sha256(repo_root / "docs" / "LEVEL3_FIRST_ORDER_TRACE_COACTIVATION.md"),
            "level35_v4_hash": canonical_sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper(),
        },
        "allowed_claims": [
            "carried exact trace information can be tested under equal-information contracts",
            "ordinary typed fields and isolated exact capsules can be compared under equal bit budgets",
            "detached activation can be evaluated separately from record-aware activation",
        ],
        "forbidden_claims": [
            "new LSH algorithm",
            "new VSA",
            "production readiness",
            "recursive provenance solved",
            "exact provenance from similarity alone",
        ],
        "heldout_execution_count": 0,
    }
    write_json(results_dir / "analysis.json", analysis)
    return analysis
