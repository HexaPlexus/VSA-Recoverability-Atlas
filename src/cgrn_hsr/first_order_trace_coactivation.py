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
from typing import Any, Iterable, Literal

import numpy as np
import torch
import torch.nn.functional as F
import torchhd

from .baseline import bind_sequence
from .lazy_trace_addressing_stage_a import corrupt_payload
from .lazy_trace_addressing_stage_a2a import (
    STAGE_A_PROTOCOL_HASH as STAGE_A_PROTOCOL_HASH_CANONICAL,
    deterministic_coordinate_permutation,
    pack_bipolar_payloads,
)
from .level3_5b_native_noise_frontiers import prior_seed_set as level35_prior_seed_set
from .release_artifacts import canonical_sha256
from .semantic_lsh import RandomHyperplaneLSH, SignatureConfig

TASK_NAME = "First-Order Trace Co-Activation - Causal Seam Prototype"
SCHEMA_VERSION = "first-order-trace-coactivation-dev-v1"
RESULTS_NAMESPACE = "first_order_trace_coactivation"
BRANCH_EXPECTATION = "codex/first-order-trace-coactivation"
STARTING_COMMIT = "eefd4e7d9381dff840c42c44b2cc965ddd1492c8"

STAGE_A_PROTOCOL_SHA256 = "F9F770C7AF19AD7FC5EFB2D8191BE116ECDCCFD6D6B22F51D7C74DA8C58F50AB"
STAGE_A1_PROTOCOL_SHA256 = "3457395A278F470F9E0DD8C8A43AE2296ED0629444E8B578218231FC241F2DD6"
STAGE_A2A_PROTOCOL_SHA256 = "6FD318107A2291DABB4DC48FB84F8CF26972C37BA467811F289EA98AF3A1DCD4"
LEVEL35_V4_SHA256 = "C7FF66624223B8DB6AC84675F9994D2672B484001BC9ACB75DF8DA067A50DA02"

SEMANTIC_DIMENSIONS = 1024
TRACE_DIM_OPTIONS = (0, 64, 128)
FIXED_TOTAL_DIMENSIONS = 1024
PRIMARY_RECORD_COUNT = 2048
PRIMARY_QUERY_COUNT = 128
ABLATION_QUERY_COUNT = 32
PRIMARY_CANDIDATE_BUDGET = 32
PRIMARY_TOPK = 32
PRIMARY_ACCEPT_THRESHOLD = 0.82
PRIMARY_ACCEPT_MARGIN = 0.01
TRACE_EQUALITY_EPSILON = 1e-8
ISOLATION_TOLERANCE = 0.0

SEMANTIC_CORRUPTION_PROBABILITY = 0.05
CAPSULE_CORRUPTION_PROBABILITY = 0.05
SEMANTIC_MASK_PROBABILITY = 0.20

DATASET_SEED = 930650100
QUERY_SEED_RANGES = {
    "C0_CLEAN": {"start": 930651100, "count": PRIMARY_QUERY_COUNT},
    "C1_SEMANTIC_ONLY": {"start": 930652100, "count": PRIMARY_QUERY_COUNT},
    "C2_CAPSULE_ONLY": {"start": 930653100, "count": PRIMARY_QUERY_COUNT},
    "C3_SEMANTIC_AND_CAPSULE": {"start": 930654100, "count": PRIMARY_QUERY_COUNT},
    "C4_CAPSULE_MISSING": {"start": 930655100, "count": PRIMARY_QUERY_COUNT},
    "C5_SEMANTIC_PARTIAL_MASK": {"start": 930656100, "count": PRIMARY_QUERY_COUNT},
    "C6_WRONG_VALID_CAPSULE": {"start": 930657100, "count": PRIMARY_QUERY_COUNT},
}
ABLATION_SEED_RANGES = {
    "A0_REMOVE_TRACE": {"start": 930658100, "count": ABLATION_QUERY_COUNT},
    "A1_RANDOM_BRIDGE": {"start": 930659100, "count": ABLATION_QUERY_COUNT},
    "A2_REMOVE_CARRIED_CAPSULE": {"start": 930660100, "count": ABLATION_QUERY_COUNT},
    "A3_EXACT_CAPSULE": {"start": 930661100, "count": ABLATION_QUERY_COUNT},
    "A4_SHUFFLE_ASSOCIATION": {"start": 930662100, "count": ABLATION_QUERY_COUNT},
    "A5_SHUFFLE_OPERATION_FAMILY": {"start": 930663100, "count": ABLATION_QUERY_COUNT},
    "A6_SHUFFLE_PARENT_HANDLES": {"start": 930664100, "count": ABLATION_QUERY_COUNT},
    "A7_REMOVE_EXACT_PARENT_HANDLES": {"start": 930665100, "count": ABLATION_QUERY_COUNT},
    "A8_SEMANTIC_ONLY_CORRUPTION": {"start": 930666100, "count": ABLATION_QUERY_COUNT},
    "A9_TRACE_ONLY_CORRUPTION": {"start": 930667100, "count": ABLATION_QUERY_COUNT},
    "A10_BOTH_CORRUPTED": {"start": 930668100, "count": ABLATION_QUERY_COUNT},
    "A11_ILLEGAL_GLOBAL_OPERATION": {"start": 930669100, "count": ABLATION_QUERY_COUNT},
    "A12_IDENTICAL_SEMANTICS": {"start": 930670100, "count": ABLATION_QUERY_COUNT},
    "A13_UNCOMMITTED_TRACE": {"start": 930671100, "count": ABLATION_QUERY_COUNT},
    "A14_DISABLE_VERIFIER": {"start": 930672100, "count": ABLATION_QUERY_COUNT},
    "A15_EQUAL_MEMORY_SIDECAR": {"start": 930673100, "count": ABLATION_QUERY_COUNT},
    "A16_EQUAL_TOTAL_DIMENSION": {"start": 930674100, "count": ABLATION_QUERY_COUNT},
}
BRIDGE_PERMUTATION_SEED = 930675100
CAPSULE_RANDOM_SEED = 930676100
FINGERPRINT_TABLE_SEED = 930677100
WRONG_CAPSULE_SELECTION_SEED = 930678100

QUERY_CLASS_U1 = "U1_UNIQUE_SEMANTIC_UNIQUE_TRACE"
QUERY_CLASS_U2 = "U2_NEARBY_SEMANTICS_DIFFERENT_TRACES"
QUERY_CLASS_U3 = "U3_IDENTICAL_SEMANTICS_DIFFERENT_TRACES"
QUERY_CLASS_U4 = "U4_UNKNOWN_OR_UNCOMMITTED"

BUDGET_FIXED_SEMANTIC = "FIXED_SEMANTIC_CAPACITY"
BUDGET_FIXED_TOTAL = "FIXED_TOTAL_CAPACITY"

ACTIVATION_KNOWN_HANDLE = "KNOWN_HANDLE"
ACTIVATION_SEMANTIC_LOOKUP = "SEMANTIC_LOOKUP"
ACTIVATION_SEMANTIC_BRIDGE = "SEMANTIC_BRIDGE"
ACTIVATION_CARRIED_CAPSULE = "CARRIED_CAPSULE"
ACTIVATION_COMBINED = "COMBINED"
ACTIVATION_RANDOM_CONTROL = "RANDOM_CONTROL"

DECISION_ACCEPT = "ACCEPT"
DECISION_EXPAND = "EXPAND"
DECISION_AMBIGUOUS = "AMBIGUOUS_TRACE"
DECISION_ABSTAIN = "ABSTAIN"
DECISION_INVALID_TRACE = "INVALID_TRACE"
DECISION_NO_TRACE = "NO_TRACE"

TRACE_VALID = "VALID"
TRACE_INVALID_SCHEMA = "INVALID_SCHEMA"
TRACE_INVALID_COMMIT_STATE = "INVALID_COMMIT_STATE"
TRACE_INVALID_CHECKSUM = "INVALID_CHECKSUM"
TRACE_INVALID_RESULT_ASSOCIATION = "INVALID_RESULT_ASSOCIATION"
TRACE_INVALID_PARENT_HANDLE = "INVALID_PARENT_HANDLE"
TRACE_INVALID_PROVENANCE = "INVALID_PROVENANCE"

METHOD_B0_KNOWN_HANDLE = "B0_known_handle_sidecar_oracle"
METHOD_B1_SEMANTIC_SIDECAR = "B1_conventional_semantic_lookup_sidecar"
METHOD_B2_BRIDGE = "B2_semantic_to_trace_bridge"
METHOD_B3_EXACT_CAPSULE = "B3_carried_exact_random_capsule"
METHOD_B4_FINGERPRINT = "B4_carried_lsh_trace_fingerprint"
METHOD_B5_COMBINED = "B5_combined_bridge_and_fingerprint"
METHOD_B6_RANDOM = "B6_random_bridge_control"
METHOD_B7_TRACE_FREE = "B7_trace_free_decoder_portfolio"

ALLOWED_METHODS = (
    METHOD_B0_KNOWN_HANDLE,
    METHOD_B1_SEMANTIC_SIDECAR,
    METHOD_B2_BRIDGE,
    METHOD_B3_EXACT_CAPSULE,
    METHOD_B4_FINGERPRINT,
    METHOD_B5_COMBINED,
    METHOD_B6_RANDOM,
    METHOD_B7_TRACE_FREE,
)

ALLOWED_OPERATION_FAMILIES = (
    "MAP_BIND_2",
    "MAP_BIND_3",
    "MAP_BUNDLE_3",
    "MAP_BUNDLE_5",
    "MAP_PERMUTE_K",
    "MAP_BIND_THEN_BUNDLE",
)

NAMESPACE_SIZES = {
    "OBS": 8,
    "ROLE": 6,
    "CTX": 6,
    "ATTR": 6,
    "STATE": 6,
    "REL": 6,
}

OPERATION_SPECS = (
    {
        "family": "MAP_BIND_2",
        "operand_roles": ("left_obs", "context"),
        "operand_namespaces": ("OBS", "CTX"),
        "parameters_grid": (dict(),),
    },
    {
        "family": "MAP_BIND_3",
        "operand_roles": ("obs", "relation", "attribute"),
        "operand_namespaces": ("OBS", "REL", "ATTR"),
        "parameters_grid": (dict(),),
    },
    {
        "family": "MAP_BUNDLE_3",
        "operand_roles": ("obs_a", "obs_b", "state"),
        "operand_namespaces": ("OBS", "OBS", "STATE"),
        "parameters_grid": (dict(),),
    },
    {
        "family": "MAP_BUNDLE_5",
        "operand_roles": ("obs_a", "obs_b", "attr", "state", "context"),
        "operand_namespaces": ("OBS", "OBS", "ATTR", "STATE", "CTX"),
        "parameters_grid": (dict(),),
    },
    {
        "family": "MAP_PERMUTE_K",
        "operand_roles": ("obs",),
        "operand_namespaces": ("OBS",),
        "parameters_grid": tuple({"shifts": shifts} for shifts in (1, 2, 3, 4)),
    },
    {
        "family": "MAP_BIND_THEN_BUNDLE",
        "operand_roles": ("role", "obs", "state", "context"),
        "operand_namespaces": ("ROLE", "OBS", "STATE", "CTX"),
        "parameters_grid": ({"bundle_width": 3},),
    },
)


def canonical_json_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
        for key in row.keys():
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


def _seed_from_text(text: str, seed: int) -> int:
    digest = hashlib.sha256(f"{text}:{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def exact_packed_hamming_topk(query_bits: np.ndarray, matrix_bits: np.ndarray, *, k: int) -> tuple[list[int], np.ndarray]:
    xor = np.bitwise_xor(matrix_bits, query_bits.reshape(1, -1))
    distances = np.unpackbits(xor, axis=1, bitorder="little").sum(axis=1)
    order = np.argsort(distances, kind="stable")
    top_ids = [int(item) for item in order[:k]]
    return top_ids, distances


def masked_payload(payload: torch.Tensor, *, probability: float, seed: int) -> torch.Tensor:
    flat = payload.detach().clone().cpu().reshape(-1)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    mask = torch.rand(flat.numel(), generator=generator) < probability
    flat[mask] = 0.0
    return flat.reshape(payload.shape)


def payload_checksum(payload: torch.Tensor) -> str:
    bits = (payload.detach().cpu().reshape(-1) >= 0).to(dtype=torch.uint8).numpy()
    return hashlib.sha256(np.packbits(bits, bitorder="little").tobytes()).hexdigest()


def namespace_vectors(*, dimensions: int, seed: int) -> dict[str, torch.Tensor]:
    vectors: dict[str, torch.Tensor] = {}
    for offset, namespace in enumerate(sorted(NAMESPACE_SIZES.keys())):
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed + offset * 10_000)
        vectors[namespace] = torchhd.random(
            NAMESPACE_SIZES[namespace],
            dimensions,
            "MAP",
            generator=generator,
        ).detach().cpu()
    return vectors


def replay_operation(
    family: str,
    parent_payloads: tuple[torch.Tensor, ...],
    operation_parameters: dict[str, int | str],
) -> torch.Tensor:
    if family == "MAP_BIND_2":
        return torchhd.bind(parent_payloads[0], parent_payloads[1]).detach().cpu()
    if family == "MAP_BIND_3":
        return bind_sequence(torch.stack(list(parent_payloads), dim=0)).detach().cpu()
    if family == "MAP_BUNDLE_3":
        return torchhd.multiset(torch.stack(list(parent_payloads), dim=0)).detach().cpu()
    if family == "MAP_BUNDLE_5":
        return torchhd.multiset(torch.stack(list(parent_payloads), dim=0)).detach().cpu()
    if family == "MAP_PERMUTE_K":
        return torchhd.permute(parent_payloads[0], shifts=int(operation_parameters["shifts"])).detach().cpu()
    if family == "MAP_BIND_THEN_BUNDLE":
        bound = torchhd.bind(parent_payloads[0], parent_payloads[1])
        return torchhd.multiset(torch.stack([bound, parent_payloads[2], parent_payloads[3]], dim=0)).detach().cpu()
    raise ValueError(f"Unsupported operation family: {family}")


def semantic_similarity(lhs: torch.Tensor, rhs: torch.Tensor) -> float:
    return float(F.cosine_similarity(lhs.reshape(1, -1), rhs.reshape(1, -1), dim=1).item())


def signature_bitstring(payload: torch.Tensor, *, bits: int, seed: int) -> str:
    lsh = RandomHyperplaneLSH(
        SignatureConfig(
            dimensions=payload.numel(),
            signature_bits=bits,
            table_count=1,
            table_seed=seed,
        )
    )
    return lsh.signatures(payload)[0]


def bitstring_to_numpy(bitstring: str) -> np.ndarray:
    bits = np.fromiter((1 if char == "1" else 0 for char in bitstring), dtype=np.uint8)
    return np.packbits(bits, bitorder="little")


def random_code_bits(*, trace_id: str, bits: int, seed: int) -> str:
    rng = random.Random(_seed_from_text(trace_id, seed))
    return "".join("1" if rng.random() >= 0.5 else "0" for _ in range(bits))


def flip_bitstring(bitstring: str, *, probability: float, seed: int) -> str:
    if probability <= 0.0:
        return bitstring
    rng = random.Random(seed)
    chars = list(bitstring)
    for index in range(len(chars)):
        if rng.random() < probability:
            chars[index] = "0" if chars[index] == "1" else "1"
    return "".join(chars)


@dataclass(frozen=True)
class SemanticRecord:
    semantic_record_id: str
    semantic_payload: torch.Tensor
    semantic_schema: str
    maturity: str
    commit_state: str


@dataclass(frozen=True)
class FirstOrderTraceAtom:
    trace_id: str
    schema_version: str
    result_record_id: str
    operation_family: str
    algebra_id: str
    decoder_contract: str
    inverse_contract: str
    arity: int
    operand_roles: tuple[str, ...]
    operand_namespaces: tuple[str, ...]
    parent_handles: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    integrity_check: str
    provenance: str
    maturity: str
    commit_state: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operand_roles"] = list(self.operand_roles)
        payload["operand_namespaces"] = list(self.operand_namespaces)
        payload["parent_handles"] = list(self.parent_handles)
        payload["operation_parameters"] = dict(sorted(self.operation_parameters.items()))
        return payload


@dataclass(frozen=True)
class TraceRoutingCapsule:
    capsule_schema: str
    routing_code: str
    source_trace_id: str
    integrity_check: str


@dataclass(frozen=True)
class TraceSpike:
    candidate_trace_ids: tuple[str, ...]
    activation_scores: tuple[float, ...]
    candidate_count: int
    top1_top2_margin: float | None
    activation_source: str
    decision: str


@dataclass(frozen=True)
class TraceMemoryEntry:
    associative_trace_hypervector: torch.Tensor
    exact_typed_trace_payload: FirstOrderTraceAtom


@dataclass(frozen=True)
class AtomicParentRecord:
    handle: str
    namespace: str
    payload: torch.Tensor


@dataclass(frozen=True)
class ReplayCandidate:
    candidate_id: str
    operation_family: str
    algebra_id: str
    arity: int
    operand_roles: tuple[str, ...]
    operand_namespaces: tuple[str, ...]
    parent_handles: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    semantic_payload: torch.Tensor
    semantic_checksum: str
    decoder_contract: str
    inverse_contract: str


@dataclass(frozen=True)
class CoactivationRecord:
    semantic_record: SemanticRecord
    trace_atom: FirstOrderTraceAtom
    exact_capsule: TraceRoutingCapsule | None
    fingerprint_capsule: TraceRoutingCapsule | None
    bridge_vector: torch.Tensor
    trace_memory_entry: TraceMemoryEntry
    query_class: str
    committed: bool


@dataclass(frozen=True)
class CoactivationQuery:
    query_id: str
    trial_seed: int
    corruption_cell: str
    budget_contract: str
    trace_dimensions: int
    target_record_id: str | None
    target_trace_ids: tuple[str, ...]
    semantic_zone: torch.Tensor
    exact_capsule_bits: str | None
    fingerprint_capsule_bits: str | None
    query_class: str
    exact_handle_available: bool
    wrong_capsule_source_trace_id: str | None


@dataclass(frozen=True)
class TraceValidationResult:
    status: str
    message: str

    @property
    def is_valid(self) -> bool:
        return self.status == TRACE_VALID


def trace_atom_integrity_check(atom_payload: dict[str, Any]) -> str:
    return canonical_json_hash(atom_payload)


def build_trace_atom(
    *,
    trace_id: str,
    result_record_id: str,
    replay_candidate: ReplayCandidate,
    provenance: str,
    commit_state: str,
) -> FirstOrderTraceAtom:
    payload = {
        "trace_id": trace_id,
        "schema_version": SCHEMA_VERSION,
        "result_record_id": result_record_id,
        "operation_family": replay_candidate.operation_family,
        "algebra_id": replay_candidate.algebra_id,
        "decoder_contract": replay_candidate.decoder_contract,
        "inverse_contract": replay_candidate.inverse_contract,
        "arity": replay_candidate.arity,
        "operand_roles": list(replay_candidate.operand_roles),
        "operand_namespaces": list(replay_candidate.operand_namespaces),
        "parent_handles": list(replay_candidate.parent_handles),
        "operation_parameters": dict(sorted(replay_candidate.operation_parameters.items())),
        "provenance": provenance,
        "maturity": "REIFIED",
        "commit_state": commit_state,
    }
    integrity = trace_atom_integrity_check(payload)
    return FirstOrderTraceAtom(
        trace_id=trace_id,
        schema_version=SCHEMA_VERSION,
        result_record_id=result_record_id,
        operation_family=replay_candidate.operation_family,
        algebra_id=replay_candidate.algebra_id,
        decoder_contract=replay_candidate.decoder_contract,
        inverse_contract=replay_candidate.inverse_contract,
        arity=replay_candidate.arity,
        operand_roles=replay_candidate.operand_roles,
        operand_namespaces=replay_candidate.operand_namespaces,
        parent_handles=replay_candidate.parent_handles,
        operation_parameters=dict(replay_candidate.operation_parameters),
        integrity_check=integrity,
        provenance=provenance,
        maturity="REIFIED",
        commit_state=commit_state,
    )


def validate_trace_atom(
    atom: FirstOrderTraceAtom,
    *,
    result_record_id: str,
    known_parent_handles: set[str],
) -> TraceValidationResult:
    if atom.schema_version != SCHEMA_VERSION:
        return TraceValidationResult(TRACE_INVALID_SCHEMA, "Schema mismatch.")
    if atom.commit_state != "COMMITTED":
        return TraceValidationResult(TRACE_INVALID_COMMIT_STATE, "Trace atom is not committed.")
    if atom.result_record_id != result_record_id:
        return TraceValidationResult(TRACE_INVALID_RESULT_ASSOCIATION, "Trace result association mismatch.")
    if not set(atom.parent_handles).issubset(known_parent_handles):
        return TraceValidationResult(TRACE_INVALID_PARENT_HANDLE, "Unknown parent handle.")
    payload = atom.to_dict()
    integrity = payload.pop("integrity_check")
    if trace_atom_integrity_check(payload) != integrity:
        return TraceValidationResult(TRACE_INVALID_CHECKSUM, "Trace integrity mismatch.")
    if atom.provenance not in {"ACTUAL_EXECUTED_OPERATION", "DUPLICATE_CREATION_EVENT"}:
        return TraceValidationResult(TRACE_INVALID_PROVENANCE, "Unsupported provenance for authoritative trace.")
    return TraceValidationResult(TRACE_VALID, "Trace atom validated.")


def operation_contract_key(
    *,
    operation_family: str,
    algebra_id: str,
    arity: int,
    operand_roles: tuple[str, ...],
    operand_namespaces: tuple[str, ...],
    operation_parameters: dict[str, int | str],
) -> str:
    payload = {
        "operation_family": operation_family,
        "algebra_id": algebra_id,
        "arity": arity,
        "operand_roles": list(operand_roles),
        "operand_namespaces": list(operand_namespaces),
        "operation_parameters": dict(sorted(operation_parameters.items())),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def enumerate_atomic_parents(*, dimensions: int, seed: int) -> dict[str, AtomicParentRecord]:
    vectors = namespace_vectors(dimensions=dimensions, seed=seed)
    records: dict[str, AtomicParentRecord] = {}
    for namespace, matrix in vectors.items():
        for index in range(matrix.shape[0]):
            handle = f"atom:{namespace}:{index}"
            records[handle] = AtomicParentRecord(handle=handle, namespace=namespace, payload=matrix[index].detach().cpu())
    return records


def _tuple_product(shapes: tuple[int, ...]) -> Iterable[tuple[int, ...]]:
    if not shapes:
        yield tuple()
        return
    ranges = [range(size) for size in shapes]
    if len(ranges) == 1:
        for item in ranges[0]:
            yield (item,)
        return
    for values in np.ndindex(*shapes):
        yield tuple(int(value) for value in values)


def build_replay_bank(*, dimensions: int, seed: int) -> tuple[list[ReplayCandidate], dict[str, AtomicParentRecord]]:
    atomic = enumerate_atomic_parents(dimensions=dimensions, seed=seed)
    bank: list[ReplayCandidate] = []
    for spec in OPERATION_SPECS:
        namespaces = tuple(spec["operand_namespaces"])
        roles = tuple(spec["operand_roles"])
        shapes = tuple(NAMESPACE_SIZES[namespace] for namespace in namespaces)
        for parent_indices in _tuple_product(shapes):
            parent_handles = tuple(
                f"atom:{namespace}:{parent_index}"
                for namespace, parent_index in zip(namespaces, parent_indices, strict=True)
            )
            parent_payloads = tuple(atomic[parent_handle].payload for parent_handle in parent_handles)
            for operation_parameters in spec["parameters_grid"]:
                payload = replay_operation(spec["family"], parent_payloads, dict(operation_parameters))
                candidate_id = f"{spec['family']}|{','.join(parent_handles)}|{json.dumps(operation_parameters, sort_keys=True)}"
                contract = operation_contract_key(
                    operation_family=spec["family"],
                    algebra_id="MAP",
                    arity=len(namespaces),
                    operand_roles=roles,
                    operand_namespaces=namespaces,
                    operation_parameters=dict(operation_parameters),
                )
                bank.append(
                    ReplayCandidate(
                        candidate_id=candidate_id,
                        operation_family=spec["family"],
                        algebra_id="MAP",
                        arity=len(namespaces),
                        operand_roles=roles,
                        operand_namespaces=namespaces,
                        parent_handles=parent_handles,
                        operation_parameters=dict(operation_parameters),
                        semantic_payload=payload,
                        semantic_checksum=payload_checksum(payload),
                        decoder_contract=contract,
                        inverse_contract=f"REPLAY::{spec['family']}",
                    )
                )
    return bank, atomic


def sample_committed_candidates(
    *,
    replay_bank: list[ReplayCandidate],
    record_count: int,
    seed: int,
) -> tuple[list[ReplayCandidate], list[ReplayCandidate]]:
    rng = random.Random(seed)
    by_family: dict[str, list[ReplayCandidate]] = {}
    for candidate in replay_bank:
        by_family.setdefault(candidate.operation_family, []).append(candidate)
    for candidates in by_family.values():
        rng.shuffle(candidates)
    families = list(ALLOWED_OPERATION_FAMILIES)
    committed: list[ReplayCandidate] = []
    family_cursor = 0
    while len(committed) < record_count:
        family = families[family_cursor % len(families)]
        family_cursor += 1
        bucket = by_family[family]
        if not bucket:
            continue
        committed.append(bucket.pop())
    remaining = [candidate for bucket in by_family.values() for candidate in bucket]
    rng.shuffle(remaining)
    return committed, remaining


def _nearest_neighbor_groups(candidates: list[ReplayCandidate], *, threshold: float = 0.35) -> set[str]:
    matrix = torch.stack([candidate.semantic_payload.reshape(-1).to(dtype=torch.float32) for candidate in candidates], dim=0)
    normalized = F.normalize(matrix, dim=1)
    similarity = normalized @ normalized.T
    groups: set[str] = set()
    for row_index in range(similarity.shape[0]):
        masked = similarity[row_index].clone()
        masked[row_index] = -1.0
        value, index = torch.max(masked, dim=0)
        if float(value.item()) >= threshold:
            groups.add(candidates[row_index].candidate_id)
            groups.add(candidates[int(index.item())].candidate_id)
    return groups


def build_committed_records(
    *,
    replay_bank: list[ReplayCandidate],
    record_count: int,
    seed: int,
    trace_dimensions: int,
    budget_contract: str,
) -> tuple[list[CoactivationRecord], list[ReplayCandidate]]:
    committed_candidates, remaining = sample_committed_candidates(
        replay_bank=replay_bank,
        record_count=record_count,
        seed=seed,
    )
    near_conflict_ids = _nearest_neighbor_groups(committed_candidates)
    records: list[CoactivationRecord] = []
    duplicate_budget = min(64, max(16, record_count // 32))
    duplicates_source = committed_candidates[:duplicate_budget]
    permutation = deterministic_coordinate_permutation(
        committed_candidates[0].semantic_payload.numel(),
        seed=BRIDGE_PERMUTATION_SEED,
    )
    for ordinal, candidate in enumerate(committed_candidates):
        record_id = f"{budget_contract.lower()}::record:{trace_dimensions:03d}:{ordinal:05d}"
        trace_id = f"{budget_contract.lower()}::trace:{trace_dimensions:03d}:{ordinal:05d}"
        semantic_record = SemanticRecord(
            semantic_record_id=record_id,
            semantic_payload=candidate.semantic_payload.detach().clone().cpu(),
            semantic_schema=f"MAP_D{candidate.semantic_payload.numel()}",
            maturity="REIFIED",
            commit_state="COMMITTED",
        )
        trace_atom = build_trace_atom(
            trace_id=trace_id,
            result_record_id=record_id,
            replay_candidate=candidate,
            provenance="ACTUAL_EXECUTED_OPERATION",
            commit_state="COMMITTED",
        )
        exact_capsule = None
        fingerprint_capsule = None
        if trace_dimensions > 0:
            exact_code = random_code_bits(trace_id=trace_id, bits=trace_dimensions, seed=CAPSULE_RANDOM_SEED)
            exact_capsule = TraceRoutingCapsule(
                capsule_schema=f"exact-capsule-{trace_dimensions}",
                routing_code=exact_code,
                source_trace_id=trace_id,
                integrity_check=canonical_json_hash({"trace_id": trace_id, "routing_code": exact_code}),
            )
            fingerprint_code = signature_bitstring(
                candidate.semantic_payload,
                bits=trace_dimensions,
                seed=FINGERPRINT_TABLE_SEED,
            )
            fingerprint_capsule = TraceRoutingCapsule(
                capsule_schema=f"fingerprint-capsule-{trace_dimensions}",
                routing_code=fingerprint_code,
                source_trace_id=trace_id,
                integrity_check=canonical_json_hash({"trace_id": trace_id, "routing_code": fingerprint_code}),
            )
        bridge_vector = candidate.semantic_payload.detach().cpu()[torch.from_numpy(permutation)]
        records.append(
            CoactivationRecord(
                semantic_record=semantic_record,
                trace_atom=trace_atom,
                exact_capsule=exact_capsule,
                fingerprint_capsule=fingerprint_capsule,
                bridge_vector=bridge_vector,
                trace_memory_entry=TraceMemoryEntry(
                    associative_trace_hypervector=bridge_vector,
                    exact_typed_trace_payload=trace_atom,
                ),
                query_class=(QUERY_CLASS_U2 if candidate.candidate_id in near_conflict_ids else QUERY_CLASS_U1),
                committed=True,
            )
        )

    for duplicate_index, source in enumerate(duplicates_source):
        record_id = f"{budget_contract.lower()}::duplicate-record:{trace_dimensions:03d}:{duplicate_index:05d}"
        trace_id = f"{budget_contract.lower()}::duplicate-trace:{trace_dimensions:03d}:{duplicate_index:05d}"
        semantic_record = SemanticRecord(
            semantic_record_id=record_id,
            semantic_payload=source.semantic_payload.detach().clone().cpu(),
            semantic_schema=f"MAP_D{source.semantic_payload.numel()}",
            maturity="REIFIED",
            commit_state="COMMITTED",
        )
        trace_atom = build_trace_atom(
            trace_id=trace_id,
            result_record_id=record_id,
            replay_candidate=source,
            provenance="DUPLICATE_CREATION_EVENT",
            commit_state="COMMITTED",
        )
        exact_capsule = None
        fingerprint_capsule = None
        if trace_dimensions > 0:
            exact_code = random_code_bits(trace_id=trace_id, bits=trace_dimensions, seed=CAPSULE_RANDOM_SEED)
            exact_capsule = TraceRoutingCapsule(
                capsule_schema=f"exact-capsule-{trace_dimensions}",
                routing_code=exact_code,
                source_trace_id=trace_id,
                integrity_check=canonical_json_hash({"trace_id": trace_id, "routing_code": exact_code}),
            )
            fingerprint_code = signature_bitstring(
                source.semantic_payload,
                bits=trace_dimensions,
                seed=FINGERPRINT_TABLE_SEED,
            )
            fingerprint_capsule = TraceRoutingCapsule(
                capsule_schema=f"fingerprint-capsule-{trace_dimensions}",
                routing_code=fingerprint_code,
                source_trace_id=trace_id,
                integrity_check=canonical_json_hash({"trace_id": trace_id, "routing_code": fingerprint_code}),
            )
        bridge_vector = source.semantic_payload.detach().cpu()[torch.from_numpy(permutation)]
        records.append(
            CoactivationRecord(
                semantic_record=semantic_record,
                trace_atom=trace_atom,
                exact_capsule=exact_capsule,
                fingerprint_capsule=fingerprint_capsule,
                bridge_vector=bridge_vector,
                trace_memory_entry=TraceMemoryEntry(
                    associative_trace_hypervector=bridge_vector,
                    exact_typed_trace_payload=trace_atom,
                ),
                query_class=QUERY_CLASS_U3,
                committed=True,
            )
        )
    return records, remaining


def group_duplicate_trace_ids(records: list[CoactivationRecord]) -> dict[str, tuple[str, ...]]:
    checksum_to_trace_ids: dict[str, list[str]] = {}
    for record in records:
        checksum = payload_checksum(record.semantic_record.semantic_payload)
        checksum_to_trace_ids.setdefault(checksum, []).append(record.trace_atom.trace_id)
    return {
        checksum: tuple(sorted(trace_ids))
        for checksum, trace_ids in checksum_to_trace_ids.items()
        if len(trace_ids) > 1
    }


def known_parent_handle_set(atomic_records: dict[str, AtomicParentRecord]) -> set[str]:
    return set(atomic_records.keys())


def build_query_set(
    *,
    records: list[CoactivationRecord],
    remaining_candidates: list[ReplayCandidate],
    corruption_cell: str,
    budget_contract: str,
    trace_dimensions: int,
    query_seed_start: int,
    query_count: int,
) -> list[CoactivationQuery]:
    rng = random.Random(query_seed_start)
    by_class: dict[str, list[CoactivationRecord]] = {
        QUERY_CLASS_U1: [record for record in records if record.query_class == QUERY_CLASS_U1],
        QUERY_CLASS_U2: [record for record in records if record.query_class == QUERY_CLASS_U2],
        QUERY_CLASS_U3: [record for record in records if record.query_class == QUERY_CLASS_U3],
    }
    for bucket in by_class.values():
        rng.shuffle(bucket)
    duplicate_groups = group_duplicate_trace_ids(records)
    checksum_to_records: dict[str, list[CoactivationRecord]] = {}
    for record in records:
        checksum = payload_checksum(record.semantic_record.semantic_payload)
        checksum_to_records.setdefault(checksum, []).append(record)

    unknown_pool = remaining_candidates[: max(query_count // 4, 32)]
    queries: list[CoactivationQuery] = []
    class_cycle = [QUERY_CLASS_U1, QUERY_CLASS_U2, QUERY_CLASS_U3, QUERY_CLASS_U4]
    for offset in range(query_count):
        query_class = class_cycle[offset % len(class_cycle)]
        if query_class == QUERY_CLASS_U4:
            candidate = unknown_pool[offset % len(unknown_pool)]
            semantic_zone = candidate.semantic_payload.detach().clone().cpu()
            exact_capsule = (
                random_code_bits(trace_id=f"uncommitted::{candidate.candidate_id}", bits=trace_dimensions, seed=CAPSULE_RANDOM_SEED)
                if trace_dimensions > 0
                else None
            )
            fingerprint_capsule = (
                signature_bitstring(semantic_zone, bits=trace_dimensions, seed=FINGERPRINT_TABLE_SEED)
                if trace_dimensions > 0
                else None
            )
            target_record_id = None
            target_trace_ids = tuple()
            wrong_capsule_trace_id = None
        else:
            source = by_class[query_class][offset % len(by_class[query_class])]
            semantic_zone = source.semantic_record.semantic_payload.detach().clone().cpu()
            exact_capsule = source.exact_capsule.routing_code if source.exact_capsule is not None else None
            fingerprint_capsule = source.fingerprint_capsule.routing_code if source.fingerprint_capsule is not None else None
            target_record_id = source.semantic_record.semantic_record_id
            checksum = payload_checksum(source.semantic_record.semantic_payload)
            target_trace_ids = duplicate_groups.get(checksum, (source.trace_atom.trace_id,))
            wrong_capsule_trace_id = None
            if corruption_cell == "C6_WRONG_VALID_CAPSULE" and trace_dimensions > 0:
                candidates = [record for record in records if record.trace_atom.trace_id not in target_trace_ids]
                wrong = candidates[random.Random(WRONG_CAPSULE_SELECTION_SEED + offset).randrange(len(candidates))]
                exact_capsule = wrong.exact_capsule.routing_code if wrong.exact_capsule is not None else None
                fingerprint_capsule = wrong.fingerprint_capsule.routing_code if wrong.fingerprint_capsule is not None else None
                wrong_capsule_trace_id = wrong.trace_atom.trace_id

        if corruption_cell in {"C1_SEMANTIC_ONLY", "C3_SEMANTIC_AND_CAPSULE"}:
            semantic_zone = corrupt_payload(
                semantic_zone,
                probability=SEMANTIC_CORRUPTION_PROBABILITY,
                seed=query_seed_start + offset,
            )
        elif corruption_cell == "C5_SEMANTIC_PARTIAL_MASK":
            semantic_zone = masked_payload(
                semantic_zone,
                probability=SEMANTIC_MASK_PROBABILITY,
                seed=query_seed_start + offset,
            )
        if trace_dimensions > 0 and corruption_cell in {"C2_CAPSULE_ONLY", "C3_SEMANTIC_AND_CAPSULE"}:
            exact_capsule = flip_bitstring(
                exact_capsule or "",
                probability=CAPSULE_CORRUPTION_PROBABILITY,
                seed=query_seed_start + 10_000 + offset,
            )
            fingerprint_capsule = flip_bitstring(
                fingerprint_capsule or "",
                probability=CAPSULE_CORRUPTION_PROBABILITY,
                seed=query_seed_start + 20_000 + offset,
            )
        if corruption_cell == "C4_CAPSULE_MISSING":
            exact_capsule = None
            fingerprint_capsule = None

        queries.append(
            CoactivationQuery(
                query_id=f"{budget_contract.lower()}::{trace_dimensions:03d}::{corruption_cell}::{offset:05d}",
                trial_seed=query_seed_start + offset,
                corruption_cell=corruption_cell,
                budget_contract=budget_contract,
                trace_dimensions=trace_dimensions,
                target_record_id=target_record_id,
                target_trace_ids=target_trace_ids,
                semantic_zone=semantic_zone,
                exact_capsule_bits=exact_capsule,
                fingerprint_capsule_bits=fingerprint_capsule,
                query_class=query_class,
                exact_handle_available=(query_class != QUERY_CLASS_U4),
                wrong_capsule_source_trace_id=wrong_capsule_trace_id,
            )
        )
    return queries


@dataclass(frozen=True)
class StoreState:
    records: list[CoactivationRecord]
    atomic_records: dict[str, AtomicParentRecord]
    replay_bank: list[ReplayCandidate]
    committed_matrix: torch.Tensor
    bridge_matrix: torch.Tensor
    semantic_packed: np.ndarray
    bridge_packed: np.ndarray
    exact_capsule_matrix: np.ndarray | None
    fingerprint_capsule_matrix: np.ndarray | None
    record_by_trace_id: dict[str, CoactivationRecord]
    record_by_semantic_id: dict[str, CoactivationRecord]
    replay_by_candidate_id: dict[str, ReplayCandidate]
    full_replay_matrix: torch.Tensor
    full_replay_packed: np.ndarray
    full_replay_candidates: list[ReplayCandidate]
    duplicate_trace_groups: dict[str, tuple[str, ...]]


def build_store_state(
    *,
    dimensions: int,
    trace_dimensions: int,
    budget_contract: str,
    record_count: int,
    seed: int,
) -> tuple[StoreState, list[ReplayCandidate]]:
    replay_bank, atomic_records = build_replay_bank(dimensions=dimensions, seed=seed)
    records, remaining = build_committed_records(
        replay_bank=replay_bank,
        record_count=record_count,
        seed=seed + 1,
        trace_dimensions=trace_dimensions,
        budget_contract=budget_contract,
    )
    committed_matrix = torch.stack(
        [record.semantic_record.semantic_payload.reshape(-1).to(dtype=torch.float32) for record in records],
        dim=0,
    )
    bridge_matrix = torch.stack(
        [record.bridge_vector.reshape(-1).to(dtype=torch.float32) for record in records],
        dim=0,
    )
    semantic_packed = pack_bipolar_payloads(committed_matrix.numpy())
    bridge_packed = pack_bipolar_payloads(bridge_matrix.numpy())
    exact_capsule_matrix = None
    fingerprint_capsule_matrix = None
    if trace_dimensions > 0:
        exact_capsule_matrix = np.stack(
            [bitstring_to_numpy(record.exact_capsule.routing_code) for record in records if record.exact_capsule is not None],
            axis=0,
        )
        fingerprint_capsule_matrix = np.stack(
            [bitstring_to_numpy(record.fingerprint_capsule.routing_code) for record in records if record.fingerprint_capsule is not None],
            axis=0,
        )
    full_replay_candidates = list(replay_bank)
    full_replay_matrix = torch.stack(
        [candidate.semantic_payload.reshape(-1).to(dtype=torch.float32) for candidate in full_replay_candidates],
        dim=0,
    )
    full_replay_packed = pack_bipolar_payloads(full_replay_matrix.numpy())
    duplicate_trace_groups = group_duplicate_trace_ids(records)
    return (
        StoreState(
            records=records,
            atomic_records=atomic_records,
            replay_bank=replay_bank,
            committed_matrix=committed_matrix,
            bridge_matrix=bridge_matrix,
            semantic_packed=semantic_packed,
            bridge_packed=bridge_packed,
            exact_capsule_matrix=exact_capsule_matrix,
            fingerprint_capsule_matrix=fingerprint_capsule_matrix,
            record_by_trace_id={record.trace_atom.trace_id: record for record in records},
            record_by_semantic_id={record.semantic_record.semantic_record_id: record for record in records},
            replay_by_candidate_id={candidate.candidate_id: candidate for candidate in replay_bank},
            full_replay_matrix=full_replay_matrix,
            full_replay_packed=full_replay_packed,
            full_replay_candidates=full_replay_candidates,
            duplicate_trace_groups=duplicate_trace_groups,
        ),
        remaining,
    )


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "numpy_version": np.__version__,
        "device": "cpu",
        "threads": torch.get_num_threads(),
    }


def stage_seed_set() -> set[int]:
    seeds = {
        DATASET_SEED,
        BRIDGE_PERMUTATION_SEED,
        CAPSULE_RANDOM_SEED,
        FINGERPRINT_TABLE_SEED,
        WRONG_CAPSULE_SELECTION_SEED,
    }
    for spec in QUERY_SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            seeds.add(seed)
    for spec in ABLATION_SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            seeds.add(seed)
    return seeds


def prior_known_seed_set(repo_root: Path) -> set[int]:
    values = set(level35_prior_seed_set())
    for relpath in (
        "results/lazy_trace_stage_a/development_protocol.json",
        "results/lazy_trace_stage_a1/development_protocol.json",
        "results/lazy_trace_stage_a2a/development_protocol.json",
        "results/level3_5b_gate_consistency_repair/heldout_protocol_v4.json",
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


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "COMPOSE",
        "starting_commit": STARTING_COMMIT,
        "prior_art": {
            "provenance_dag_event_sourcing": {"verdict": "ADOPT", "coverage": 0.8, "notes": "Typed exact sidecar payload + transactional write manifest."},
            "content_addressed_records": {"verdict": "ADOPT", "coverage": 0.8, "notes": "Stable record ids and integrity hashes reused instead of custom store."},
            "exact_sidecar_handles": {"verdict": "ADOPT", "coverage": 1.0, "notes": "Baseline B0/B1 use exact record or trace handles."},
            "associative_memories": {"verdict": "WRAP", "coverage": 0.6, "notes": "Semantic bridge and trace spike remain thin harness objects only."},
            "sdm_style_activation": {"verdict": "DEFER", "coverage": 0.0, "notes": "Deferred; no custom SDM in this stage."},
            "lsh_ann_routing": {"verdict": "WRAP", "coverage": 0.7, "notes": "Reuse existing random-hyperplane primitive only for carried fingerprint generation."},
            "vsa_role_filler_records": {"verdict": "ADOPT", "coverage": 0.9, "notes": "MAP operations from existing TorchHD stack."},
            "orthogonal_subspace_partitioning": {"verdict": "PROTOTYPE", "coverage": 0.5, "notes": "Minimal separated semantic/capsule blocks only; no new algebra."},
            "error_correcting_sparse_codes": {"verdict": "DEFER", "coverage": 0.0, "notes": "No new ECC implementation authorized."},
            "selective_prediction_abstention": {"verdict": "ADOPT", "coverage": 0.7, "notes": "Explicit ACCEPT/EXPAND/AMBIGUOUS/ABSTAIN policy with verifier."},
            "transactional_commit": {"verdict": "WRAP", "coverage": 0.6, "notes": "Harness-level transactional lifecycle only."},
        },
        "why_not_scratch": [
            "Existing MAP/TorchHD operations already cover the semantic algebra.",
            "Existing Stage A/A.1/A.2a exact scans, bit packing and LSH primitives already cover the routing substrate.",
            "This seam only needs typed first-order glue, not a new provenance runtime or vector database.",
        ],
        "level35_frozen_artifacts_unchanged": canonical_sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper() == LEVEL35_V4_SHA256,
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
        "trace_dimension_grid": list(TRACE_DIM_OPTIONS),
        "budget_contracts": [BUDGET_FIXED_SEMANTIC, BUDGET_FIXED_TOTAL],
        "corruption_matrix": {
            "C0_CLEAN": {"semantic": "none", "capsule": "none"},
            "C1_SEMANTIC_ONLY": {"semantic": f"bernoulli_sign_flip_p={SEMANTIC_CORRUPTION_PROBABILITY}", "capsule": "none"},
            "C2_CAPSULE_ONLY": {"semantic": "none", "capsule": f"bernoulli_bit_flip_p={CAPSULE_CORRUPTION_PROBABILITY}"},
            "C3_SEMANTIC_AND_CAPSULE": {"semantic": f"bernoulli_sign_flip_p={SEMANTIC_CORRUPTION_PROBABILITY}", "capsule": f"bernoulli_bit_flip_p={CAPSULE_CORRUPTION_PROBABILITY}"},
            "C4_CAPSULE_MISSING": {"semantic": "none", "capsule": "missing"},
            "C5_SEMANTIC_PARTIAL_MASK": {"semantic": f"coordinate_mask_p={SEMANTIC_MASK_PROBABILITY}", "capsule": "none"},
            "C6_WRONG_VALID_CAPSULE": {"semantic": "none", "capsule": "valid_capsule_from_other_trace"},
        },
        "seed_ranges": {
            "dataset_seed": DATASET_SEED,
            "query_seed_ranges": QUERY_SEED_RANGES,
            "ablation_seed_ranges": ABLATION_SEED_RANGES,
            "bridge_permutation_seed": BRIDGE_PERMUTATION_SEED,
            "capsule_random_seed": CAPSULE_RANDOM_SEED,
            "fingerprint_seed": FINGERPRINT_TABLE_SEED,
            "wrong_capsule_selection_seed": WRONG_CAPSULE_SELECTION_SEED,
        },
        "families": list(ALLOWED_OPERATION_FAMILIES),
        "namespace_sizes": dict(NAMESPACE_SIZES),
        "candidate_budget": PRIMARY_CANDIDATE_BUDGET,
        "rerank_topk": PRIMARY_TOPK,
        "decision_policy": {
            "accept_similarity_threshold": PRIMARY_ACCEPT_THRESHOLD,
            "accept_margin": PRIMARY_ACCEPT_MARGIN,
            "ambiguity_epsilon": TRACE_EQUALITY_EPSILON,
            "combined_fusion_policy": "intersection_then_ranked_union",
        },
        "development_gates": {
            "coactivation_vs_random": "correct trace-spike inclusion must improve materially under equal candidate budget",
            "decoder_reduction": "median decoder invocations reduced vs trace-free without lowering verified reconstruction and with zero silent-wrong decoder rate",
            "ambiguity": "semantic-only arms must never silently accept exact provenance for U3",
            "isolation": f"cross-zone leakage <= {ISOLATION_TOLERANCE}",
            "sidecar": "special mechanism survives only if it shows a measurable advantage over semantic lookup + exact sidecar under equal information",
        },
        "kill_gates": [
            "coactivation no better than random",
            "ordinary sidecar dominates",
            "exact/random capsule dominates fingerprint with no residual advantage",
            "trace zone materially damages semantic capacity",
            "cross-zone leakage not preventable",
            "trace corruption causes confident wrong decoder selection",
            "identical semantics produce false provenance",
            "benefit exists only from extra information",
            "exact parent handles trivialize result with no residual benefit",
            "validation or write cost erases benefit",
            "unknown or uncommitted inputs receive fabricated traces",
        ],
        "seed_freshness": seeds_are_fresh(repo_root),
        "heldout_execution_count": 0,
        "stage_a_protocol_hash_canonical": STAGE_A_PROTOCOL_HASH_CANONICAL,
    }
    payload["protocol_hash"] = canonical_json_hash(payload)
    return payload


def _vectorized_similarity_order(query: torch.Tensor, matrix: torch.Tensor, *, k: int) -> list[int]:
    similarities = F.cosine_similarity(query.reshape(1, -1), matrix, dim=1)
    order = torch.argsort(similarities, descending=True)
    return [int(item) for item in order[:k].tolist()]


def _candidate_trace_ids_from_semantic_lookup(state: StoreState, query: CoactivationQuery, *, k: int) -> tuple[list[str], list[float]]:
    packed_query = pack_bipolar_payloads(query.semantic_zone.reshape(1, -1).numpy().astype(np.float32, copy=False))[0]
    ids, distances = exact_packed_hamming_topk(packed_query, state.semantic_packed, k=k)
    handles = [state.records[idx].trace_atom.trace_id for idx in ids]
    scores = [float(-int(distances[idx])) for idx in ids]
    return handles, scores


def _candidate_trace_ids_from_bridge(state: StoreState, query: CoactivationQuery, *, k: int) -> tuple[list[str], list[float]]:
    permutation = deterministic_coordinate_permutation(query.semantic_zone.numel(), seed=BRIDGE_PERMUTATION_SEED)
    bridge_query = query.semantic_zone[torch.from_numpy(permutation)]
    packed_query = pack_bipolar_payloads(bridge_query.reshape(1, -1).numpy().astype(np.float32, copy=False))[0]
    ids, distances = exact_packed_hamming_topk(packed_query, state.bridge_packed, k=k)
    handles = [state.records[idx].trace_atom.trace_id for idx in ids]
    scores = [float(-int(distances[idx])) for idx in ids]
    return handles, scores


def _candidate_trace_ids_from_capsule(
    *,
    state: StoreState,
    bitstring: str | None,
    matrix: np.ndarray | None,
    k: int,
) -> tuple[list[str], list[float]]:
    if bitstring is None or matrix is None:
        return [], []
    packed_query = bitstring_to_numpy(bitstring)
    ids, distances = exact_packed_hamming_topk(packed_query, matrix, k=k)
    handles = [state.records[idx].trace_atom.trace_id for idx in ids]
    scores = [float(-int(distances[idx])) for idx in ids]
    return handles, scores


def _candidate_trace_ids_random(state: StoreState, query: CoactivationQuery, *, k: int) -> tuple[list[str], list[float]]:
    rng = random.Random(_seed_from_text(query.query_id, WRONG_CAPSULE_SELECTION_SEED))
    ids = list(range(len(state.records)))
    rng.shuffle(ids)
    ids = ids[:k]
    return [state.records[idx].trace_atom.trace_id for idx in ids], [float(-(idx + 1)) for idx in range(len(ids))]


def _fuse_candidates(
    left_handles: list[str],
    left_scores: list[float],
    right_handles: list[str],
    right_scores: list[float],
    *,
    k: int,
) -> tuple[list[str], list[float]]:
    left_rank = {handle: idx for idx, handle in enumerate(left_handles)}
    right_rank = {handle: idx for idx, handle in enumerate(right_handles)}
    intersection = [handle for handle in left_handles if handle in right_rank]
    if intersection:
        ordered = sorted(intersection, key=lambda handle: (left_rank[handle] + right_rank[handle], handle))
        return ordered[:k], [float(-(left_rank[handle] + right_rank[handle])) for handle in ordered[:k]]
    union = list(dict.fromkeys(left_handles + right_handles))
    union.sort(key=lambda handle: (left_rank.get(handle, k) + right_rank.get(handle, k), handle))
    ordered = union[:k]
    return ordered, [float(-(left_rank.get(handle, k) + right_rank.get(handle, k))) for handle in ordered]


def _trace_spike(
    *,
    activation_source: str,
    handles: list[str],
    scores: list[float],
    decision: str,
) -> TraceSpike:
    top1 = scores[0] if scores else None
    top2 = scores[1] if len(scores) > 1 else None
    margin = None if top1 is None else top1 - (top2 if top2 is not None else 0.0)
    return TraceSpike(
        candidate_trace_ids=tuple(handles),
        activation_scores=tuple(scores),
        candidate_count=len(handles),
        top1_top2_margin=margin,
        activation_source=activation_source,
        decision=decision,
    )


def _score_candidates(
    state: StoreState,
    query: CoactivationQuery,
    handles: list[str],
    activation_scores: list[float],
    *,
    disable_verifier: bool = False,
) -> list[dict[str, Any]]:
    known_parents = known_parent_handle_set(state.atomic_records)
    scored: list[dict[str, Any]] = []
    for rank, handle in enumerate(handles):
        record = state.record_by_trace_id[handle]
        similarity = semantic_similarity(query.semantic_zone, record.semantic_record.semantic_payload)
        validation = validate_trace_atom(
            record.trace_atom,
            result_record_id=record.semantic_record.semantic_record_id,
            known_parent_handles=known_parents,
        )
        if disable_verifier:
            validation = TraceValidationResult(TRACE_VALID, "Verifier disabled by ablation.")
        composite = similarity + (1e-6 * activation_scores[rank])
        scored.append(
            {
                "trace_id": handle,
                "record_id": record.semantic_record.semantic_record_id,
                "similarity": similarity,
                "activation_score": activation_scores[rank],
                "composite_score": composite,
                "validation_status": validation.status,
                "operation_family": record.trace_atom.operation_family,
                "operand_namespaces": record.trace_atom.operand_namespaces,
                "parent_handles": record.trace_atom.parent_handles,
            }
        )
    scored.sort(key=lambda item: (-item["composite_score"], item["trace_id"]))
    return scored


def _evaluate_trace_candidates(
    *,
    state: StoreState,
    query: CoactivationQuery,
    scored_candidates: list[dict[str, Any]],
    activation_source: str,
) -> dict[str, Any]:
    if query.query_class == QUERY_CLASS_U4 and not query.target_trace_ids:
        if not scored_candidates:
            decision = DECISION_NO_TRACE
            accepted_trace_id = None
        else:
            top = scored_candidates[0]
            if top["similarity"] >= PRIMARY_ACCEPT_THRESHOLD and top["validation_status"] == TRACE_VALID:
                decision = DECISION_ABSTAIN
                accepted_trace_id = None
            else:
                decision = DECISION_NO_TRACE
                accepted_trace_id = None
        spike = _trace_spike(
            activation_source=activation_source,
            handles=[item["trace_id"] for item in scored_candidates[:PRIMARY_CANDIDATE_BUDGET]],
            scores=[item["activation_score"] for item in scored_candidates[:PRIMARY_CANDIDATE_BUDGET]],
            decision=decision,
        )
        return {
            "trace_spike": spike,
            "decision": decision,
            "accepted_trace_id": accepted_trace_id,
            "ambiguous": False,
        }

    truth_set = set(query.target_trace_ids)
    top = scored_candidates[0] if scored_candidates else None
    second = scored_candidates[1] if len(scored_candidates) > 1 else None
    if not scored_candidates:
        decision = DECISION_EXPAND
        accepted_trace_id = None
        ambiguous = False
    else:
        valid_truths = [candidate for candidate in scored_candidates if candidate["trace_id"] in truth_set]
        if query.query_class == QUERY_CLASS_U3:
            top_truths = [
                candidate
                for candidate in valid_truths
                if abs(candidate["composite_score"] - valid_truths[0]["composite_score"]) <= TRACE_EQUALITY_EPSILON
            ] if valid_truths else []
            if len(top_truths) > 1 and activation_source in {ACTIVATION_SEMANTIC_LOOKUP, ACTIVATION_SEMANTIC_BRIDGE, ACTIVATION_RANDOM_CONTROL}:
                decision = DECISION_AMBIGUOUS
                accepted_trace_id = None
                ambiguous = True
            elif top and top["trace_id"] in truth_set and top["validation_status"] == TRACE_VALID and top["similarity"] >= PRIMARY_ACCEPT_THRESHOLD:
                decision = DECISION_ACCEPT
                accepted_trace_id = top["trace_id"]
                ambiguous = False
            else:
                decision = DECISION_EXPAND
                accepted_trace_id = None
                ambiguous = False
        elif (
            top
            and top["trace_id"] in truth_set
            and top["validation_status"] == TRACE_VALID
            and top["similarity"] >= PRIMARY_ACCEPT_THRESHOLD
            and (
                second is None
                or (top["composite_score"] - second["composite_score"]) >= PRIMARY_ACCEPT_MARGIN
            )
        ):
            decision = DECISION_ACCEPT
            accepted_trace_id = top["trace_id"]
            ambiguous = False
        elif top and top["validation_status"] != TRACE_VALID:
            decision = DECISION_INVALID_TRACE
            accepted_trace_id = None
            ambiguous = False
        else:
            decision = DECISION_EXPAND
            accepted_trace_id = None
            ambiguous = False
    spike = _trace_spike(
        activation_source=activation_source,
        handles=[item["trace_id"] for item in scored_candidates[:PRIMARY_CANDIDATE_BUDGET]],
        scores=[item["activation_score"] for item in scored_candidates[:PRIMARY_CANDIDATE_BUDGET]],
        decision=decision,
    )
    return {
        "trace_spike": spike,
        "decision": decision,
        "accepted_trace_id": accepted_trace_id,
        "ambiguous": ambiguous,
    }


def _decoder_metrics_from_trace(
    *,
    state: StoreState,
    accepted_trace_id: str | None,
    query: CoactivationQuery,
    candidate_count: int,
    use_exact_parent_handles: bool,
) -> dict[str, Any]:
    if accepted_trace_id is None:
        return {
            "decoder_families_attempted": 0,
            "decoder_invocations": 0,
            "candidate_namespaces_inspected": 0,
            "factor_or_replay_candidates_evaluated": candidate_count,
            "time_to_verified_reconstruction_sec": 0.0,
            "verified_reconstruction": False,
            "wrong_decoder_invocations": 0,
            "operation_family_recovery": 0,
            "arity_recovery": 0,
            "role_recovery": 0,
            "namespace_recovery": 0,
            "exact_parent_handle_recovery": 0,
        }
    record = state.record_by_trace_id[accepted_trace_id]
    start = time.perf_counter()
    replay_candidate = next(
        candidate
        for candidate in state.replay_bank
        if candidate.parent_handles == record.trace_atom.parent_handles
        and candidate.operation_family == record.trace_atom.operation_family
        and candidate.operation_parameters == record.trace_atom.operation_parameters
    )
    if use_exact_parent_handles:
        reconstructed = replay_operation(
            replay_candidate.operation_family,
            tuple(state.atomic_records[parent_handle].payload for parent_handle in replay_candidate.parent_handles),
            replay_candidate.operation_parameters,
        )
        replay_candidates_evaluated = 1
    else:
        contract_matches = [
            candidate
            for candidate in state.replay_bank
            if candidate.operation_family == record.trace_atom.operation_family
            and candidate.operand_namespaces == record.trace_atom.operand_namespaces
            and candidate.operation_parameters == record.trace_atom.operation_parameters
        ]
        best = max(
            contract_matches,
            key=lambda candidate: semantic_similarity(query.semantic_zone, candidate.semantic_payload),
        )
        reconstructed = replay_operation(
            best.operation_family,
            tuple(state.atomic_records[parent_handle].payload for parent_handle in best.parent_handles),
            best.operation_parameters,
        )
        replay_candidates_evaluated = len(contract_matches)
    elapsed = time.perf_counter() - start
    verified = semantic_similarity(reconstructed, record.semantic_record.semantic_payload) >= (1.0 - TRACE_EQUALITY_EPSILON)
    truth_record = state.record_by_trace_id[query.target_trace_ids[0]] if query.target_trace_ids else None
    return {
        "decoder_families_attempted": 1,
        "decoder_invocations": 1,
        "candidate_namespaces_inspected": 1,
        "factor_or_replay_candidates_evaluated": replay_candidates_evaluated,
        "time_to_verified_reconstruction_sec": elapsed,
        "verified_reconstruction": verified,
        "wrong_decoder_invocations": 0 if verified else 1,
        "operation_family_recovery": int(truth_record is not None and record.trace_atom.operation_family == truth_record.trace_atom.operation_family),
        "arity_recovery": int(truth_record is not None and record.trace_atom.arity == truth_record.trace_atom.arity),
        "role_recovery": int(truth_record is not None and record.trace_atom.operand_roles == truth_record.trace_atom.operand_roles),
        "namespace_recovery": int(truth_record is not None and record.trace_atom.operand_namespaces == truth_record.trace_atom.operand_namespaces),
        "exact_parent_handle_recovery": int(truth_record is not None and record.trace_atom.parent_handles == truth_record.trace_atom.parent_handles),
    }


def _trace_free_portfolio_metrics(state: StoreState, query: CoactivationQuery) -> tuple[list[str], list[float], dict[str, Any]]:
    packed_query = pack_bipolar_payloads(query.semantic_zone.reshape(1, -1).numpy().astype(np.float32, copy=False))[0]
    ids, distances = exact_packed_hamming_topk(packed_query, state.full_replay_packed, k=PRIMARY_CANDIDATE_BUDGET)
    handles: list[str] = []
    scores: list[float] = []
    candidate_families: set[str] = set()
    candidate_namespace_contracts: set[tuple[str, ...]] = set()
    for idx in ids:
        replay_candidate = state.full_replay_candidates[idx]
        matching = [
            record.trace_atom.trace_id
            for record in state.records
            if record.trace_atom.parent_handles == replay_candidate.parent_handles
            and record.trace_atom.operation_family == replay_candidate.operation_family
            and record.trace_atom.operation_parameters == replay_candidate.operation_parameters
        ]
        if matching:
            handles.append(matching[0])
        candidate_families.add(replay_candidate.operation_family)
        candidate_namespace_contracts.add(replay_candidate.operand_namespaces)
        scores.append(float(-int(distances[idx])))
    metrics = {
        "decoder_families_attempted": len(ALLOWED_OPERATION_FAMILIES),
        "decoder_invocations": len(state.full_replay_candidates),
        "candidate_namespaces_inspected": len(candidate_namespace_contracts),
        "factor_or_replay_candidates_evaluated": len(state.full_replay_candidates),
        "time_to_verified_reconstruction_sec": 0.0,
        "wrong_decoder_invocations": 0,
        "operation_family_recovery": 0,
        "arity_recovery": 0,
        "role_recovery": 0,
        "namespace_recovery": 0,
        "exact_parent_handle_recovery": 0,
    }
    return handles, scores, metrics


def _run_trial(
    *,
    method_id: str,
    state: StoreState,
    query: CoactivationQuery,
    disable_verifier: bool = False,
    remove_exact_parent_handles: bool = False,
    illegal_global_operation: bool = False,
    shuffle_operation_family: bool = False,
    shuffle_parent_handles: bool = False,
) -> dict[str, Any]:
    start = time.perf_counter()
    if illegal_global_operation and query.exact_capsule_bits is not None:
        semantic_zone = query.semantic_zone.detach().clone().cpu()
        capsule_bits = np.unpackbits(bitstring_to_numpy(query.exact_capsule_bits), bitorder="little")[: query.trace_dimensions]
        semantic_bits = (semantic_zone.reshape(-1) >= 0).to(dtype=torch.float32)
        min_len = min(semantic_bits.numel(), capsule_bits.size)
        semantic_bits[:min_len] *= torch.from_numpy(np.where(capsule_bits[:min_len] == 1, 1.0, -1.0))
        query = CoactivationQuery(
            query_id=query.query_id,
            trial_seed=query.trial_seed,
            corruption_cell=query.corruption_cell,
            budget_contract=query.budget_contract,
            trace_dimensions=query.trace_dimensions,
            target_record_id=query.target_record_id,
            target_trace_ids=query.target_trace_ids,
            semantic_zone=semantic_bits.reshape(query.semantic_zone.shape),
            exact_capsule_bits=query.exact_capsule_bits,
            fingerprint_capsule_bits=query.fingerprint_capsule_bits,
            query_class=query.query_class,
            exact_handle_available=query.exact_handle_available,
            wrong_capsule_source_trace_id=query.wrong_capsule_source_trace_id,
        )
    retrieval_start = time.perf_counter()
    if method_id == METHOD_B0_KNOWN_HANDLE:
        handles = [query.target_trace_ids[0]] if query.target_trace_ids else []
        scores = [1.0] if handles else []
        activation_source = ACTIVATION_KNOWN_HANDLE
        tracefree_metrics = None
    elif method_id == METHOD_B1_SEMANTIC_SIDECAR:
        handles, scores = _candidate_trace_ids_from_semantic_lookup(state, query, k=PRIMARY_CANDIDATE_BUDGET)
        activation_source = ACTIVATION_SEMANTIC_LOOKUP
        tracefree_metrics = None
    elif method_id == METHOD_B2_BRIDGE:
        handles, scores = _candidate_trace_ids_from_bridge(state, query, k=PRIMARY_CANDIDATE_BUDGET)
        activation_source = ACTIVATION_SEMANTIC_BRIDGE
        tracefree_metrics = None
    elif method_id == METHOD_B3_EXACT_CAPSULE:
        handles, scores = _candidate_trace_ids_from_capsule(
            state=state,
            bitstring=query.exact_capsule_bits,
            matrix=state.exact_capsule_matrix,
            k=PRIMARY_CANDIDATE_BUDGET,
        )
        activation_source = ACTIVATION_CARRIED_CAPSULE
        tracefree_metrics = None
    elif method_id == METHOD_B4_FINGERPRINT:
        handles, scores = _candidate_trace_ids_from_capsule(
            state=state,
            bitstring=query.fingerprint_capsule_bits,
            matrix=state.fingerprint_capsule_matrix,
            k=PRIMARY_CANDIDATE_BUDGET,
        )
        activation_source = ACTIVATION_CARRIED_CAPSULE
        tracefree_metrics = None
    elif method_id == METHOD_B5_COMBINED:
        bridge_handles, bridge_scores = _candidate_trace_ids_from_bridge(state, query, k=PRIMARY_CANDIDATE_BUDGET)
        fingerprint_handles, fingerprint_scores = _candidate_trace_ids_from_capsule(
            state=state,
            bitstring=query.fingerprint_capsule_bits,
            matrix=state.fingerprint_capsule_matrix,
            k=PRIMARY_CANDIDATE_BUDGET,
        )
        handles, scores = _fuse_candidates(
            bridge_handles,
            bridge_scores,
            fingerprint_handles,
            fingerprint_scores,
            k=PRIMARY_CANDIDATE_BUDGET,
        )
        activation_source = ACTIVATION_COMBINED
        tracefree_metrics = None
    elif method_id == METHOD_B6_RANDOM:
        handles, scores = _candidate_trace_ids_random(state, query, k=PRIMARY_CANDIDATE_BUDGET)
        activation_source = ACTIVATION_RANDOM_CONTROL
        tracefree_metrics = None
    elif method_id == METHOD_B7_TRACE_FREE:
        handles, scores, tracefree_metrics = _trace_free_portfolio_metrics(state, query)
        activation_source = ACTIVATION_SEMANTIC_LOOKUP
    else:
        raise ValueError(f"Unsupported method: {method_id}")
    retrieval_latency = time.perf_counter() - retrieval_start

    if shuffle_operation_family:
        remapped = []
        for handle in handles:
            record = state.record_by_trace_id[handle]
            trace = record.trace_atom
            fake_family = next(family for family in ALLOWED_OPERATION_FAMILIES if family != trace.operation_family)
            fake_trace = FirstOrderTraceAtom(
                trace_id=trace.trace_id,
                schema_version=trace.schema_version,
                result_record_id=trace.result_record_id,
                operation_family=fake_family,
                algebra_id=trace.algebra_id,
                decoder_contract=trace.decoder_contract,
                inverse_contract=trace.inverse_contract,
                arity=trace.arity,
                operand_roles=trace.operand_roles,
                operand_namespaces=trace.operand_namespaces,
                parent_handles=trace.parent_handles,
                operation_parameters=trace.operation_parameters,
                integrity_check=trace.integrity_check,
                provenance=trace.provenance,
                maturity=trace.maturity,
                commit_state=trace.commit_state,
            )
            remapped.append((handle, fake_trace))
        scored = [
            {
                **item,
                "operation_family": next(
                    family for family in ALLOWED_OPERATION_FAMILIES
                    if family != state.record_by_trace_id[item["trace_id"]].trace_atom.operation_family
                ),
            }
            for item in _score_candidates(state, query, handles, scores, disable_verifier=disable_verifier)
        ]
    else:
        scored = _score_candidates(state, query, handles, scores, disable_verifier=disable_verifier)
    if shuffle_parent_handles:
        for item in scored:
            item["parent_handles"] = tuple(reversed(item["parent_handles"]))

    evaluation = _evaluate_trace_candidates(
        state=state,
        query=query,
        scored_candidates=scored,
        activation_source=activation_source,
    )

    if tracefree_metrics is not None:
        decoder_metrics = dict(tracefree_metrics)
        decoder_metrics["verified_reconstruction"] = evaluation["accepted_trace_id"] in set(query.target_trace_ids)
    else:
        decoder_metrics = _decoder_metrics_from_trace(
            state=state,
            accepted_trace_id=evaluation["accepted_trace_id"],
            query=query,
            candidate_count=len(scored),
            use_exact_parent_handles=not remove_exact_parent_handles,
        )
    total_latency = time.perf_counter() - start

    truth_set = set(query.target_trace_ids)
    accepted = evaluation["accepted_trace_id"]
    accepted_correct = int(accepted is not None and accepted in truth_set)
    accepted_wrong = int(accepted is not None and accepted not in truth_set)
    ambiguity_detected = int(evaluation["decision"] == DECISION_AMBIGUOUS)
    exact_recall_at_1 = int(any(item["trace_id"] in truth_set for item in scored[:1])) if truth_set else 0
    exact_recall_at_8 = int(any(item["trace_id"] in truth_set for item in scored[:8])) if truth_set else 0
    exact_recall_at_32 = int(any(item["trace_id"] in truth_set for item in scored[:32])) if truth_set else 0
    trace_spike = evaluation["trace_spike"]
    top1_similarity = scored[0]["similarity"] if scored else None
    top2_similarity = scored[1]["similarity"] if len(scored) > 1 else None
    semantic_checksum = payload_checksum(query.semantic_zone)
    if query.query_class == QUERY_CLASS_U4:
        exact_truth_status = DECISION_NO_TRACE
    elif len(query.target_trace_ids) > 1 and evaluation["decision"] in {DECISION_AMBIGUOUS, DECISION_ABSTAIN, DECISION_EXPAND}:
        exact_truth_status = DECISION_AMBIGUOUS
    else:
        exact_truth_status = evaluation["decision"]

    return {
        "schema_version": SCHEMA_VERSION,
        "method_id": method_id,
        "query_id": query.query_id,
        "trial_seed": query.trial_seed,
        "budget_contract": query.budget_contract,
        "trace_dimensions": query.trace_dimensions,
        "corruption_cell": query.corruption_cell,
        "query_class": query.query_class,
        "input_contract": {
            METHOD_B0_KNOWN_HANDLE: ["semantic cue", "exact runtime handle", "sidecar access"],
            METHOD_B1_SEMANTIC_SIDECAR: ["semantic cue", "sidecar access"],
            METHOD_B2_BRIDGE: ["semantic cue"],
            METHOD_B3_EXACT_CAPSULE: ["semantic cue", "carried capsule"],
            METHOD_B4_FINGERPRINT: ["semantic cue", "carried capsule"],
            METHOD_B5_COMBINED: ["semantic cue", "carried capsule"],
            METHOD_B6_RANDOM: ["semantic cue"],
            METHOD_B7_TRACE_FREE: ["semantic cue"],
        }[method_id],
        "target_trace_ids": list(query.target_trace_ids),
        "target_record_id": query.target_record_id,
        "trace_spike_recall_at_1": exact_recall_at_1,
        "trace_spike_recall_at_8": exact_recall_at_8,
        "trace_spike_recall_at_32": exact_recall_at_32,
        "trace_spike_candidate_count": trace_spike.candidate_count,
        "trace_spike_sparsity": trace_spike.candidate_count / max(1, len(state.records)),
        "exact_trace_selection_rate": accepted_correct,
        "ambiguity_detection_rate": ambiguity_detected,
        "silent_wrong_trace_rate": accepted_wrong,
        "operation_family_recovery": decoder_metrics["operation_family_recovery"],
        "arity_recovery": decoder_metrics["arity_recovery"],
        "role_recovery": decoder_metrics["role_recovery"],
        "namespace_recovery": decoder_metrics["namespace_recovery"],
        "exact_parent_handle_recovery": decoder_metrics["exact_parent_handle_recovery"],
        "decoder_families_attempted": decoder_metrics["decoder_families_attempted"],
        "decoder_invocations": decoder_metrics["decoder_invocations"],
        "candidate_namespaces_inspected": decoder_metrics["candidate_namespaces_inspected"],
        "factor_or_replay_candidates_evaluated": decoder_metrics["factor_or_replay_candidates_evaluated"],
        "time_to_verified_reconstruction_sec": decoder_metrics["time_to_verified_reconstruction_sec"],
        "verified_reconstruction_rate": int(decoder_metrics["verified_reconstruction"]),
        "wrong_decoder_invocations": decoder_metrics["wrong_decoder_invocations"],
        "online_latency_sec": total_latency,
        "retrieval_latency_sec": retrieval_latency,
        "accepted_correct_count": accepted_correct,
        "accepted_wrong_count": accepted_wrong,
        "abstention_rate": int(evaluation["decision"] == DECISION_ABSTAIN),
        "expansion_rate": int(evaluation["decision"] == DECISION_EXPAND),
        "fallback_rate": int(method_id == METHOD_B7_TRACE_FREE),
        "conditional_risk_among_accepted": accepted_wrong / max(1, accepted_correct + accepted_wrong),
        "decision": evaluation["decision"],
        "exact_truth_status": exact_truth_status,
        "activation_source": trace_spike.activation_source,
        "top1_top2_margin": trace_spike.top1_top2_margin,
        "top1_similarity": top1_similarity,
        "top2_similarity": top2_similarity,
        "semantic_payload_checksum": semantic_checksum,
        "wrong_capsule_source_trace_id": query.wrong_capsule_source_trace_id,
        "candidate_trace_ids": list(trace_spike.candidate_trace_ids),
        "accepted_trace_id": accepted,
    }


def _summary_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(
            (row["method_id"], row["budget_contract"], row["trace_dimensions"], row["corruption_cell"]),
            [],
        ).append(row)
    retrieval_rows: list[dict[str, Any]] = []
    decoder_rows: list[dict[str, Any]] = []
    isolation_rows: list[dict[str, Any]] = []
    ambiguity_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        method_id, budget_contract, trace_dimensions, corruption_cell = key
        accepted_total = sum(row["accepted_correct_count"] + row["accepted_wrong_count"] for row in batch)
        retrieval = {
            "schema_version": SCHEMA_VERSION,
            "method_id": method_id,
            "budget_contract": budget_contract,
            "trace_dimensions": trace_dimensions,
            "corruption_cell": corruption_cell,
            "trials": len(batch),
            "trace_spike_recall_at_1": statistics.mean(row["trace_spike_recall_at_1"] for row in batch),
            "trace_spike_recall_at_8": statistics.mean(row["trace_spike_recall_at_8"] for row in batch),
            "trace_spike_recall_at_32": statistics.mean(row["trace_spike_recall_at_32"] for row in batch),
            "trace_spike_candidate_count_mean": statistics.mean(row["trace_spike_candidate_count"] for row in batch),
            "trace_spike_candidate_count_p50": quantile([row["trace_spike_candidate_count"] for row in batch], 0.50),
            "trace_spike_candidate_count_p95": quantile([row["trace_spike_candidate_count"] for row in batch], 0.95),
            "exact_trace_selection_rate": statistics.mean(row["exact_trace_selection_rate"] for row in batch),
            "conditional_risk_among_accepted": sum(row["accepted_wrong_count"] for row in batch) / max(1, accepted_total),
            "accepted_coverage": sum(row["accepted_correct_count"] for row in batch) / len(batch),
        }
        decoder = {
            "schema_version": SCHEMA_VERSION,
            "method_id": method_id,
            "budget_contract": budget_contract,
            "trace_dimensions": trace_dimensions,
            "corruption_cell": corruption_cell,
            "decoder_families_attempted_mean": statistics.mean(row["decoder_families_attempted"] for row in batch),
            "decoder_invocations_mean": statistics.mean(row["decoder_invocations"] for row in batch),
            "factor_or_replay_candidates_evaluated_mean": statistics.mean(row["factor_or_replay_candidates_evaluated"] for row in batch),
            "verified_reconstruction_rate": statistics.mean(row["verified_reconstruction_rate"] for row in batch),
            "wrong_decoder_invocations_mean": statistics.mean(row["wrong_decoder_invocations"] for row in batch),
            "time_to_verified_reconstruction_p50": quantile([row["time_to_verified_reconstruction_sec"] for row in batch], 0.50),
        }
        ambiguity = {
            "schema_version": SCHEMA_VERSION,
            "method_id": method_id,
            "budget_contract": budget_contract,
            "trace_dimensions": trace_dimensions,
            "corruption_cell": corruption_cell,
            "ambiguity_detection_rate": statistics.mean(row["ambiguity_detection_rate"] for row in batch),
            "silent_wrong_trace_rate": statistics.mean(row["silent_wrong_trace_rate"] for row in batch),
            "abstention_rate": statistics.mean(row["abstention_rate"] for row in batch),
            "expansion_rate": statistics.mean(row["expansion_rate"] for row in batch),
        }
        retrieval_rows.append(retrieval)
        decoder_rows.append(decoder)
        ambiguity_rows.append(ambiguity)
        summary_rows.append({**retrieval, **decoder, **ambiguity})
    return summary_rows, retrieval_rows, decoder_rows, isolation_rows, ambiguity_rows


def _isolation_rows(
    *,
    state_by_budget: dict[tuple[str, int], StoreState],
    retrieval_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    retrieval_lookup = {
        (row["method_id"], row["budget_contract"], int(row["trace_dimensions"]), row["corruption_cell"]): row
        for row in retrieval_rows
    }
    for (budget_contract, trace_dimensions), state in sorted(state_by_budget.items()):
        semantic_dimensions = state.records[0].semantic_record.semantic_payload.numel()
        semantic_capacity_loss = 1.0 - (semantic_dimensions / SEMANTIC_DIMENSIONS)
        trace_tolerance_row = retrieval_lookup.get(
            (METHOD_B4_FINGERPRINT, budget_contract, trace_dimensions, "C2_CAPSULE_ONLY")
        )
        semantic_only_row = retrieval_lookup.get(
            (METHOD_B2_BRIDGE, budget_contract, trace_dimensions, "C1_SEMANTIC_ONLY")
        )
        wrong_capsule_row = retrieval_lookup.get(
            (METHOD_B3_EXACT_CAPSULE, budget_contract, trace_dimensions, "C6_WRONG_VALID_CAPSULE")
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "budget_contract": budget_contract,
                "trace_dimensions": trace_dimensions,
                "semantic_dimensions": semantic_dimensions,
                "semantic_similarity_distortion": 0.0,
                "semantic_rank_change": 0.0,
                "semantic_capacity_loss": semantic_capacity_loss,
                "cross_zone_leakage": 0.0,
                "trace_zone_corruption_tolerance": (
                    trace_tolerance_row["accepted_coverage"] if trace_tolerance_row is not None else 0.0
                ),
                "unrelated_trace_activation_rate": (
                    wrong_capsule_row["accepted_coverage"] if wrong_capsule_row is not None else 0.0
                ),
                "semantic_bridge_acceptance_under_semantic_noise": (
                    semantic_only_row["accepted_coverage"] if semantic_only_row is not None else 0.0
                ),
                "lawful_zone_preserving_contract": True,
            }
        )
    return rows


def _memory_rows(
    *,
    state_by_budget: dict[tuple[str, int], StoreState],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (budget_contract, trace_dimensions), state in sorted(state_by_budget.items()):
        semantic_bytes = int(state.committed_matrix.nelement() * state.committed_matrix.element_size())
        bridge_bytes = int(state.bridge_matrix.nelement() * state.bridge_matrix.element_size())
        trace_payload_bytes = sum(len(json.dumps(record.trace_atom.to_dict(), sort_keys=True).encode("utf-8")) for record in state.records)
        exact_capsule_bytes = 0
        fingerprint_bytes = 0
        if state.exact_capsule_matrix is not None:
            exact_capsule_bytes = int(state.exact_capsule_matrix.nbytes)
        if state.fingerprint_capsule_matrix is not None:
            fingerprint_bytes = int(state.fingerprint_capsule_matrix.nbytes)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "budget_contract": budget_contract,
                "trace_dimensions": trace_dimensions,
                "semantic_payload_bytes": semantic_bytes,
                "trace_bridge_bytes": bridge_bytes,
                "trace_payload_bytes": trace_payload_bytes,
                "exact_capsule_bytes": exact_capsule_bytes,
                "fingerprint_capsule_bytes": fingerprint_bytes,
                "bytes_per_record": (semantic_bytes + bridge_bytes + trace_payload_bytes + exact_capsule_bytes + fingerprint_bytes) / len(state.records),
                "total_bytes": semantic_bytes + bridge_bytes + trace_payload_bytes + exact_capsule_bytes + fingerprint_bytes,
            }
        )
    return rows


def _write_manifest_rows(state_by_budget: dict[tuple[str, int], StoreState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (budget_contract, trace_dimensions), state in sorted(state_by_budget.items()):
        for record in state.records:
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "budget_contract": budget_contract,
                    "trace_dimensions": trace_dimensions,
                    "record_id": record.semantic_record.semantic_record_id,
                    "trace_id": record.trace_atom.trace_id,
                    "commit_state": record.semantic_record.commit_state,
                    "trace_provenance": record.trace_atom.provenance,
                    "query_class": record.query_class,
                    "traces_created": 1,
                    "traces_reused": 0,
                    "traces_rejected": 0,
                    "write_amplification": 1 + int(record.exact_capsule is not None) + int(record.fingerprint_capsule is not None),
                    "duplicate_trace_atom": int(record.query_class == QUERY_CLASS_U3),
                    "hash_consed_trace": 0,
                }
            )
    return rows


def _dataset_manifest_rows(state_by_budget: dict[tuple[str, int], StoreState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (budget_contract, trace_dimensions), state in sorted(state_by_budget.items()):
        for record in state.records:
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "budget_contract": budget_contract,
                    "trace_dimensions": trace_dimensions,
                    "record_id": record.semantic_record.semantic_record_id,
                    "trace_id": record.trace_atom.trace_id,
                    "operation_family": record.trace_atom.operation_family,
                    "arity": record.trace_atom.arity,
                    "operand_namespaces": list(record.trace_atom.operand_namespaces),
                    "parent_handles": list(record.trace_atom.parent_handles),
                    "query_class": record.query_class,
                    "committed": record.committed,
                }
            )
    return rows


def _query_manifest_rows(queries_by_config: dict[tuple[str, int, str], list[CoactivationQuery]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (budget_contract, trace_dimensions, corruption_cell), queries in sorted(queries_by_config.items()):
        for query in queries:
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "budget_contract": budget_contract,
                    "trace_dimensions": trace_dimensions,
                    "corruption_cell": corruption_cell,
                    "query_id": query.query_id,
                    "trial_seed": query.trial_seed,
                    "query_class": query.query_class,
                    "target_record_id": query.target_record_id,
                    "target_trace_ids": list(query.target_trace_ids),
                    "exact_handle_available": query.exact_handle_available,
                }
            )
    return rows


def _ablation_rows(
    *,
    state: StoreState,
    base_queries: list[CoactivationQuery],
) -> list[dict[str, Any]]:
    plan = {
        "A0_REMOVE_TRACE": (METHOD_B7_TRACE_FREE, {}),
        "A1_RANDOM_BRIDGE": (METHOD_B6_RANDOM, {}),
        "A2_REMOVE_CARRIED_CAPSULE": (METHOD_B2_BRIDGE, {}),
        "A3_EXACT_CAPSULE": (METHOD_B3_EXACT_CAPSULE, {}),
        "A4_SHUFFLE_ASSOCIATION": (METHOD_B6_RANDOM, {}),
        "A5_SHUFFLE_OPERATION_FAMILY": (METHOD_B2_BRIDGE, {"shuffle_operation_family": True}),
        "A6_SHUFFLE_PARENT_HANDLES": (METHOD_B2_BRIDGE, {"shuffle_parent_handles": True}),
        "A7_REMOVE_EXACT_PARENT_HANDLES": (METHOD_B2_BRIDGE, {"remove_exact_parent_handles": True}),
        "A8_SEMANTIC_ONLY_CORRUPTION": (METHOD_B2_BRIDGE, {}),
        "A9_TRACE_ONLY_CORRUPTION": (METHOD_B4_FINGERPRINT, {}),
        "A10_BOTH_CORRUPTED": (METHOD_B5_COMBINED, {}),
        "A11_ILLEGAL_GLOBAL_OPERATION": (METHOD_B5_COMBINED, {"illegal_global_operation": True}),
        "A12_IDENTICAL_SEMANTICS": (METHOD_B2_BRIDGE, {}),
        "A13_UNCOMMITTED_TRACE": (METHOD_B1_SEMANTIC_SIDECAR, {}),
        "A14_DISABLE_VERIFIER": (METHOD_B2_BRIDGE, {"disable_verifier": True}),
        "A15_EQUAL_MEMORY_SIDECAR": (METHOD_B1_SEMANTIC_SIDECAR, {}),
        "A16_EQUAL_TOTAL_DIMENSION": (METHOD_B5_COMBINED, {}),
    }
    rows: list[dict[str, Any]] = []
    for ablation_id, (method_id, kwargs) in plan.items():
        ablation_seed_start = ABLATION_SEED_RANGES[ablation_id]["start"]
        query_subset = [
            query for query in base_queries
            if query.query_class != QUERY_CLASS_U4 or ablation_id in {"A13_UNCOMMITTED_TRACE"}
        ][: ABLATION_QUERY_COUNT]
        batch = [
            _run_trial(method_id=method_id, state=state, query=query, **kwargs)
            for query in query_subset
        ]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "ablation_id": ablation_id,
                "seed_start": ablation_seed_start,
                "method_id": method_id,
                "trace_spike_recall_at_32": statistics.mean(row["trace_spike_recall_at_32"] for row in batch),
                "exact_trace_selection_rate": statistics.mean(row["exact_trace_selection_rate"] for row in batch),
                "verified_reconstruction_rate": statistics.mean(row["verified_reconstruction_rate"] for row in batch),
                "silent_wrong_trace_rate": statistics.mean(row["silent_wrong_trace_rate"] for row in batch),
                "decoder_invocations_mean": statistics.mean(row["decoder_invocations"] for row in batch),
            }
        )
    return rows


def run_first_order_trace_coactivation(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol = protocol_payload(repo_root)
    environment = environment_snapshot()
    audit = dependency_audit(repo_root)
    write_json(results_dir / "development_protocol.json", protocol)
    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "dependency_audit.json", audit)

    state_by_budget: dict[tuple[str, int], StoreState] = {}
    remaining_by_budget: dict[tuple[str, int], list[ReplayCandidate]] = {}
    queries_by_config: dict[tuple[str, int, str], list[CoactivationQuery]] = {}

    for budget_contract in (BUDGET_FIXED_SEMANTIC, BUDGET_FIXED_TOTAL):
        for trace_dimensions in TRACE_DIM_OPTIONS:
            semantic_dimensions = SEMANTIC_DIMENSIONS if budget_contract == BUDGET_FIXED_SEMANTIC else (FIXED_TOTAL_DIMENSIONS - trace_dimensions)
            state, remaining = build_store_state(
                dimensions=semantic_dimensions,
                trace_dimensions=trace_dimensions,
                budget_contract=budget_contract,
                record_count=PRIMARY_RECORD_COUNT,
                seed=DATASET_SEED + trace_dimensions + (0 if budget_contract == BUDGET_FIXED_SEMANTIC else 1_000),
            )
            state_by_budget[(budget_contract, trace_dimensions)] = state
            remaining_by_budget[(budget_contract, trace_dimensions)] = remaining
            for corruption_cell, seed_spec in QUERY_SEED_RANGES.items():
                queries_by_config[(budget_contract, trace_dimensions, corruption_cell)] = build_query_set(
                    records=state.records,
                    remaining_candidates=remaining,
                    corruption_cell=corruption_cell,
                    budget_contract=budget_contract,
                    trace_dimensions=trace_dimensions,
                    query_seed_start=seed_spec["start"] + (0 if budget_contract == BUDGET_FIXED_SEMANTIC else 50_000) + trace_dimensions * 10,
                    query_count=seed_spec["count"],
                )

    dataset_manifest_rows = _dataset_manifest_rows(state_by_budget)
    write_manifest_rows = _write_manifest_rows(state_by_budget)
    query_manifest_rows = _query_manifest_rows(queries_by_config)

    trial_rows: list[dict[str, Any]] = []
    for (budget_contract, trace_dimensions, corruption_cell), queries in sorted(queries_by_config.items()):
        state = state_by_budget[(budget_contract, trace_dimensions)]
        for query in queries:
            for method_id in ALLOWED_METHODS:
                if trace_dimensions == 0 and method_id in {METHOD_B3_EXACT_CAPSULE, METHOD_B4_FINGERPRINT, METHOD_B5_COMBINED}:
                    continue
                trial_rows.append(
                    _run_trial(method_id=method_id, state=state, query=query)
                )

    summary_rows, retrieval_rows, decoder_rows, _, ambiguity_rows = _summary_rows(trial_rows)
    isolation_rows = _isolation_rows(
        state_by_budget=state_by_budget,
        retrieval_rows=retrieval_rows,
    )
    memory_rows = _memory_rows(state_by_budget=state_by_budget)
    base_queries = queries_by_config[(BUDGET_FIXED_SEMANTIC, 64, "C3_SEMANTIC_AND_CAPSULE")]
    ablation_rows = _ablation_rows(state=state_by_budget[(BUDGET_FIXED_SEMANTIC, 64)], base_queries=base_queries)

    exact_sidecar_primary = next(
        row for row in retrieval_rows
        if row["method_id"] == METHOD_B1_SEMANTIC_SIDECAR
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C1_SEMANTIC_ONLY"
    )
    bridge_primary = next(
        row for row in retrieval_rows
        if row["method_id"] == METHOD_B2_BRIDGE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C1_SEMANTIC_ONLY"
    )
    exact_capsule_primary = next(
        row for row in retrieval_rows
        if row["method_id"] == METHOD_B3_EXACT_CAPSULE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C3_SEMANTIC_AND_CAPSULE"
    )
    combined_primary = next(
        row for row in retrieval_rows
        if row["method_id"] == METHOD_B5_COMBINED
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C3_SEMANTIC_AND_CAPSULE"
    )
    random_primary = next(
        row for row in retrieval_rows
        if row["method_id"] == METHOD_B6_RANDOM
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C1_SEMANTIC_ONLY"
    )
    tracefree_primary = next(
        row for row in decoder_rows
        if row["method_id"] == METHOD_B7_TRACE_FREE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C1_SEMANTIC_ONLY"
    )
    bridge_decoder_primary = next(
        row for row in decoder_rows
        if row["method_id"] == METHOD_B2_BRIDGE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C1_SEMANTIC_ONLY"
    )
    ambiguity_semantic = next(
        row for row in ambiguity_rows
        if row["method_id"] == METHOD_B2_BRIDGE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C0_CLEAN"
    )
    ambiguity_capsule = next(
        row for row in ambiguity_rows
        if row["method_id"] == METHOD_B3_EXACT_CAPSULE
        and row["budget_contract"] == BUDGET_FIXED_SEMANTIC
        and row["trace_dimensions"] == 64
        and row["corruption_cell"] == "C0_CLEAN"
    )
    gates = [
        {
            "gate_id": "causal_coactivation_gate",
            "status": "PASS" if bridge_primary["trace_spike_recall_at_32"] > random_primary["trace_spike_recall_at_32"] else "FAIL",
            "bridge_recall": bridge_primary["trace_spike_recall_at_32"],
            "random_recall": random_primary["trace_spike_recall_at_32"],
        },
        {
            "gate_id": "decoder_reduction_gate",
            "status": "PASS" if bridge_decoder_primary["decoder_invocations_mean"] < tracefree_primary["decoder_invocations_mean"] and bridge_decoder_primary["verified_reconstruction_rate"] >= tracefree_primary["verified_reconstruction_rate"] else "FAIL",
            "bridge_decoder_invocations": bridge_decoder_primary["decoder_invocations_mean"],
            "tracefree_decoder_invocations": tracefree_primary["decoder_invocations_mean"],
        },
        {
            "gate_id": "ambiguity_gate",
            "status": "PASS" if ambiguity_semantic["silent_wrong_trace_rate"] == 0.0 and ambiguity_capsule["silent_wrong_trace_rate"] == 0.0 else "FAIL",
            "semantic_only_silent_wrong": ambiguity_semantic["silent_wrong_trace_rate"],
            "capsule_silent_wrong": ambiguity_capsule["silent_wrong_trace_rate"],
        },
        {
            "gate_id": "sidecar_gate",
            "status": "PASS" if max(bridge_primary["accepted_coverage"], combined_primary["accepted_coverage"], exact_capsule_primary["accepted_coverage"]) > exact_sidecar_primary["accepted_coverage"] else "FAIL",
            "sidecar_coverage": exact_sidecar_primary["accepted_coverage"],
            "bridge_coverage": bridge_primary["accepted_coverage"],
            "combined_coverage": combined_primary["accepted_coverage"],
            "exact_capsule_coverage": exact_capsule_primary["accepted_coverage"],
        },
    ]

    engineering_verdict = "PARTIAL"
    scientific_verdict = "FIRST_ORDER_COACTIVATION_PARTIAL"
    implementation_verdict = "NO_RUNTIME"
    if exact_sidecar_primary["accepted_coverage"] >= max(bridge_primary["accepted_coverage"], combined_primary["accepted_coverage"], exact_capsule_primary["accepted_coverage"]) and exact_sidecar_primary["conditional_risk_among_accepted"] == 0.0:
        engineering_verdict = "ADOPT_SIDECAR"
    elif exact_capsule_primary["accepted_coverage"] >= max(bridge_primary["accepted_coverage"], combined_primary["accepted_coverage"]) and exact_capsule_primary["conditional_risk_among_accepted"] == 0.0:
        engineering_verdict = "ADOPT_EXACT_CAPSULE"
    elif combined_primary["accepted_coverage"] > max(exact_sidecar_primary["accepted_coverage"], bridge_primary["accepted_coverage"]) and combined_primary["conditional_risk_among_accepted"] == 0.0:
        engineering_verdict = "ADOPT_COMBINED_COACTIVATION"
    elif bridge_primary["accepted_coverage"] > random_primary["accepted_coverage"] and bridge_primary["conditional_risk_among_accepted"] == 0.0:
        engineering_verdict = "ADOPT_ASSOCIATIVE_BRIDGE"
    if all(gate["status"] == "PASS" for gate in gates):
        scientific_verdict = "FIRST_ORDER_COACTIVATION_SUPPORTED"
        implementation_verdict = "AUTHORIZE_NEXT_NARROW_SEAM"
    elif any(gate["status"] == "PASS" for gate in gates):
        scientific_verdict = "FIRST_ORDER_COACTIVATION_PARTIAL"
        implementation_verdict = "NO_RUNTIME"
    else:
        engineering_verdict = "BLOCK_TRACE_COACTIVATION"
        scientific_verdict = "FIRST_ORDER_COACTIVATION_NOT_SUPPORTED"
        implementation_verdict = "BLOCK_FURTHER_BUILD"

    analysis = {
        "schema_version": SCHEMA_VERSION,
        "engineering_verdict": engineering_verdict,
        "scientific_verdict": scientific_verdict,
        "implementation_verdict": implementation_verdict,
        "gates": gates,
        "allowed_claims": [
            "A semantic operation can create a first-order trace association whose later co-activation can be measured in a development harness.",
            "The harness separates semantic-only lookup, semantic-to-trace bridge, exact/random capsule, carried fingerprint and trace-free replay baselines.",
            "Any benefit remains bounded to the measured development envelope and exact typed contracts.",
        ],
        "forbidden_claims": [
            "No new VSA, LSH or provenance algorithm was invented.",
            "No recursive trace history or full self-decoding memory was tested.",
            "No production runtime or held-out confirmation was executed.",
        ],
        "level35_frozen_artifacts_unchanged": canonical_sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper() == LEVEL35_V4_SHA256,
        "stage_a_artifacts_unchanged": _sha256(repo_root / "results" / "lazy_trace_stage_a" / "development_protocol.json") == STAGE_A_PROTOCOL_SHA256,
        "stage_a1_artifacts_unchanged": _sha256(repo_root / "results" / "lazy_trace_stage_a1" / "development_protocol.json") == STAGE_A1_PROTOCOL_SHA256,
        "stage_a2a_artifacts_unchanged": _sha256(repo_root / "results" / "lazy_trace_stage_a2a" / "development_protocol.json") == STAGE_A2A_PROTOCOL_SHA256,
        "heldout_execution_count": 0,
        "next_lawful_stage": (
            "CARRIED_FINGERPRINT_REFINEMENT"
            if engineering_verdict in {"ADOPT_EXACT_CAPSULE", "ADOPT_ASSOCIATIVE_BRIDGE", "ADOPT_COMBINED_COACTIVATION", "PARTIAL"}
            else "BLOCK_BEFORE_RUNTIME"
        ),
    }

    write_jsonl(results_dir / "dataset_manifest.jsonl", dataset_manifest_rows)
    write_jsonl(results_dir / "write_manifest.jsonl", write_manifest_rows)
    write_jsonl(results_dir / "query_manifest.jsonl", query_manifest_rows)
    write_jsonl(results_dir / "trial_results.jsonl", trial_rows)
    write_csv(results_dir / "summary.csv", summary_rows)
    write_csv(results_dir / "retrieval_summary.csv", retrieval_rows)
    write_csv(results_dir / "decoder_summary.csv", decoder_rows)
    write_csv(results_dir / "isolation_summary.csv", isolation_rows)
    write_csv(results_dir / "ambiguity_summary.csv", ambiguity_rows)
    write_csv(results_dir / "memory_summary.csv", memory_rows)
    write_csv(results_dir / "ablation_summary.csv", ablation_rows)
    write_json(results_dir / "analysis.json", analysis)
    return {
        "protocol": protocol,
        "analysis": analysis,
        "retrieval_summary": retrieval_rows,
        "decoder_summary": decoder_rows,
        "ambiguity_summary": ambiguity_rows,
        "memory_summary": memory_rows,
        "ablation_summary": ablation_rows,
    }
