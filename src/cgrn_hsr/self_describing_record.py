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
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import torch
import torchhd

from .baseline import (
    BaselineConfig,
    build_initial_estimates,
    decode_top_candidates,
    factors_from_indices,
    generate_domains,
    make_generator,
)
from .exact_capsule_contract_closure import LEVEL35_V4_SHA256
from .first_order_trace_coactivation import (
    payload_checksum,
    replay_operation as replay_trace_operation,
    semantic_similarity,
)
from .level3_2_confirmation import prior_level3_1_seed_set
from .level3_2b_map_budget_robustness import level3_2_seed_set, level3_2b_seed_set
from .level3_4_algebraic_baselines import level3_4_seed_set
from .level3_5b_native_noise_frontiers import prior_seed_set as level35_prior_seed_set
from .release_artifacts import canonical_sha256

TASK_NAME = "Self-Describing Recursive Hypervector Record v0.1"
SCHEMA_VERSION = "self-describing-record-v0.1-dev"
RESULTS_NAMESPACE = "self_describing_record_v0_1"
STARTING_COMMIT = "19bcb16454a400a9fa67f00eafb6f889a92f2181"

STATUS_FLAGS = [
    "ADOPT_EXISTING_PRIMITIVES",
    "WRAP",
    "PROTOTYPE_SYSTEM_INTEGRATION",
    "DEVELOPMENT_ONLY",
    "NO_NOVELTY_CLAIM",
    "NO_PRODUCTION_CLAIM",
]

ARM_A_BASELINE = "A_MAP_FACTORIZATION_BASELINE"
ARM_B_SIDECAR = "B_ORDINARY_SIDECAR_DAG"
ARM_C_INLINE = "C_INLINE_PACKED_MANIFEST"
ALLOWED_ARMS = (ARM_A_BASELINE, ARM_B_SIDECAR, ARM_C_INLINE)

RECORD_ATOM = "ATOM"
RECORD_COMPOSITE = "COMPOSITE"

OP_BIND_2 = "MAP_BIND_2"
OP_PERMUTE = "MAP_PERMUTE"
ALLOWED_OPS = (OP_BIND_2, OP_PERMUTE)

OUTCOME_ATOM_RESOLVED = "ATOM_RESOLVED"
OUTCOME_COMPOSITE_REPLAY_VERIFIED = "COMPOSITE_REPLAY_VERIFIED"
OUTCOME_COMPOSITE_REPLAY_CACHE_HIT = "COMPOSITE_REPLAY_CACHE_HIT"
OUTCOME_MANIFEST_INTEGRITY_FAILURE = "MANIFEST_INTEGRITY_FAILURE"
OUTCOME_INVALID_MANIFEST = "INVALID_MANIFEST"
OUTCOME_DANGLING_OPERAND_REF = "DANGLING_OPERAND_REF"
OUTCOME_PARENT_VERSION_MISMATCH = "PARENT_VERSION_MISMATCH"
OUTCOME_CYCLE_DETECTED = "CYCLE_DETECTED"
OUTCOME_SEMANTIC_COMMITMENT_MISMATCH = "SEMANTIC_COMMITMENT_MISMATCH"
OUTCOME_REPLAY_BUDGET_EXHAUSTED = "REPLAY_BUDGET_EXHAUSTED"
OUTCOME_FALLBACK_REQUIRED = "FALLBACK_REQUIRED"

SEMANTIC_DIMENSIONS = 1024
PERMUTE_SHIFT = 3
FACTOR_DOMAIN_SIZE = 32
MAX_REPLAY_DEPTH = 128
MAX_REPLAY_UNIQUE_NODES = 4096
FACTORIZATION_ITERATIONS = 12
FACTORIZATION_STABLE_PATIENCE = 3

ATOM_SEED = 963_100_100
FLAT_BIND_SEED = 963_110_100
CHAIN_SEED = 963_120_100
TREE_SEED = 963_130_100
SHARED_SEED = 963_140_100
CORRUPTION_SEED = 963_150_100

BASE50_BASE = 50
BASE50_WIDTH = 4
BASE50_CAPACITY = BASE50_BASE**BASE50_WIDTH
BASE50_MIN_BITS = math.ceil(math.log2(BASE50_BASE)) * BASE50_WIDTH


def canonical_json_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    return canonical_sha256(path).upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def yaml_lines(value: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {json.dumps(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {json.dumps(item)}")
        return lines
    return [f"{pad}{json.dumps(value)}"]


def tensor_bytes(tensor: torch.Tensor) -> int:
    return int(tensor.nelement() * tensor.element_size())


def replay_operation(
    operation_code: str,
    parent_payloads: tuple[torch.Tensor, ...],
    operation_parameters: dict[str, int | str],
) -> torch.Tensor:
    if operation_code == OP_PERMUTE:
        return replay_trace_operation("MAP_PERMUTE_K", parent_payloads, operation_parameters)
    return replay_trace_operation(operation_code, parent_payloads, operation_parameters)


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": "cpu",
    }


def stage_seed_set() -> set[int]:
    return {
        ATOM_SEED,
        FLAT_BIND_SEED,
        CHAIN_SEED,
        TREE_SEED,
        SHARED_SEED,
        CORRUPTION_SEED,
    }


def prior_known_seed_set(repo_root: Path) -> set[int]:
    prior = set(level35_prior_seed_set())
    prior.update(prior_level3_1_seed_set())
    prior.update(level3_2_seed_set())
    prior.update(level3_2b_seed_set())
    prior.update(level3_4_seed_set())
    for path in (repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json",):
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            for track in ("binary_seed_ranges", "map_seed_ranges", "seed_ranges"):
                value = payload.get(track)
                if isinstance(value, dict):
                    for spec in value.values():
                        if isinstance(spec, dict) and "start" in spec and "count" in spec:
                            prior.update(range(int(spec["start"]), int(spec["start"]) + int(spec["count"])))
    return prior


def seeds_are_fresh(repo_root: Path) -> bool:
    return stage_seed_set().isdisjoint(prior_known_seed_set(repo_root))


@dataclass(frozen=True)
class Base50x4Code:
    digits: tuple[int, int, int, int]

    @classmethod
    def encode(cls, local_integer: int) -> "Base50x4Code":
        if not 0 <= local_integer < BASE50_CAPACITY:
            raise ValueError("local_integer out of base50x4 range")
        value = local_integer
        digits: list[int] = []
        for _ in range(BASE50_WIDTH):
            digits.append(value % BASE50_BASE)
            value //= BASE50_BASE
        return cls(tuple(reversed(digits)))

    def decode(self) -> int:
        value = 0
        for digit in self.digits:
            if not 0 <= digit < BASE50_BASE:
                raise ValueError("base50 digit out of range")
            value = value * BASE50_BASE + digit
        return value

    def validate(self) -> bool:
        return all(0 <= digit < BASE50_BASE for digit in self.digits)


@dataclass(frozen=True)
class OperandRef:
    namespace_id: str
    concept_code: int
    version: int

    def key(self) -> str:
        return f"{self.namespace_id}:{self.concept_code}:v{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompositeManifest:
    schema_version: str
    operation_code: str
    arity: int
    ordered_operand_refs: tuple[OperandRef, ...]
    operation_parameters: dict[str, int | str]
    manifest_digest: str

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation_code": self.operation_code,
            "arity": self.arity,
            "ordered_operand_refs": [item.to_dict() for item in self.ordered_operand_refs],
            "operation_parameters": dict(sorted(self.operation_parameters.items())),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload()
        payload["manifest_digest"] = self.manifest_digest
        return payload


@dataclass(frozen=True)
class ConceptRecord:
    concept_id: str
    namespace_id: str
    concept_code: int
    version: int
    record_kind: str
    semantic_dimension: int
    semantic_payload: torch.Tensor
    semantic_digest: str
    manifest: CompositeManifest | None
    record_integrity: str

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "namespace_id": self.namespace_id,
            "concept_code": self.concept_code,
            "version": self.version,
            "record_kind": self.record_kind,
            "semantic_dimension": self.semantic_dimension,
            "semantic_digest": self.semantic_digest,
            "manifest": self.manifest.to_dict() if self.manifest is not None else None,
        }


@dataclass(frozen=True)
class ReplayStats:
    unique_nodes_visited: int
    cache_hits: int
    operation_count: int
    lookup_count: int
    maximum_depth: int
    replay_latency_sec: float
    semantic_similarity_to_observed: float | None
    factorizer_invoked: bool


@dataclass(frozen=True)
class ReplayResult:
    outcome: str
    record_id: str
    semantic_payload: torch.Tensor | None
    semantic_digest: str | None
    reachable_record_ids: tuple[str, ...]
    stats: ReplayStats


@dataclass
class ReplaySession:
    cache: dict[str, torch.Tensor]
    reachable_ids: set[str]
    visiting: set[str]
    cache_hits: int = 0
    operation_count: int = 0
    lookup_count: int = 0
    maximum_depth: int = 0


class ConceptStore:
    def __init__(self) -> None:
        self.records: dict[str, ConceptRecord] = {}
        self.versions: dict[tuple[str, int], set[int]] = {}

    def add(self, record: ConceptRecord) -> None:
        self.records[record.concept_id] = record
        self.versions.setdefault((record.namespace_id, record.concept_code), set()).add(record.version)

    def get(self, concept_id: str) -> ConceptRecord | None:
        return self.records.get(concept_id)

    def resolve(self, reference: OperandRef) -> tuple[str, ConceptRecord | None]:
        concept_id = reference.key()
        if concept_id in self.records:
            return concept_id, self.records[concept_id]
        if (reference.namespace_id, reference.concept_code) in self.versions:
            return concept_id, None
        return concept_id, None

    def has_other_versions(self, reference: OperandRef) -> bool:
        versions = self.versions.get((reference.namespace_id, reference.concept_code), set())
        return bool(versions and reference.version not in versions)


def manifest_digest(payload: dict[str, Any]) -> str:
    return canonical_json_hash(payload)


def record_integrity(payload: dict[str, Any]) -> str:
    return canonical_json_hash(payload)


def serialize_manifest_bytes(manifest: CompositeManifest) -> bytes:
    return json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_atom_record(
    *,
    namespace_id: str,
    concept_code: int,
    version: int,
    semantic_payload: torch.Tensor,
) -> ConceptRecord:
    concept_id = f"{namespace_id}:{concept_code}:v{version}"
    semantic = semantic_payload.detach().cpu().clone()
    digest = payload_checksum(semantic)
    body = {
        "concept_id": concept_id,
        "namespace_id": namespace_id,
        "concept_code": concept_code,
        "version": version,
        "record_kind": RECORD_ATOM,
        "semantic_dimension": semantic.numel(),
        "semantic_digest": digest,
        "manifest": None,
    }
    integrity = record_integrity(body)
    return ConceptRecord(
        concept_id=concept_id,
        namespace_id=namespace_id,
        concept_code=concept_code,
        version=version,
        record_kind=RECORD_ATOM,
        semantic_dimension=semantic.numel(),
        semantic_payload=semantic,
        semantic_digest=digest,
        manifest=None,
        record_integrity=integrity,
    )


def create_composite_record(
    *,
    store: ConceptStore,
    namespace_id: str,
    concept_code: int,
    version: int,
    operation_code: str,
    ordered_operand_refs: tuple[OperandRef, ...],
    operation_parameters: dict[str, int | str],
) -> ConceptRecord:
    parent_records: list[ConceptRecord] = []
    for reference in ordered_operand_refs:
        concept_id, record = store.resolve(reference)
        if record is None:
            raise KeyError(f"Missing parent for composite creation: {concept_id}")
        parent_records.append(record)
    parent_payloads = tuple(parent.semantic_payload for parent in parent_records)
    semantic = replay_operation(operation_code, parent_payloads, operation_parameters)
    digest = payload_checksum(semantic)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation_code": operation_code,
        "arity": len(ordered_operand_refs),
        "ordered_operand_refs": [item.to_dict() for item in ordered_operand_refs],
        "operation_parameters": dict(sorted(operation_parameters.items())),
    }
    manifest = CompositeManifest(
        schema_version=SCHEMA_VERSION,
        operation_code=operation_code,
        arity=len(ordered_operand_refs),
        ordered_operand_refs=ordered_operand_refs,
        operation_parameters=dict(sorted(operation_parameters.items())),
        manifest_digest=manifest_digest(payload),
    )
    concept_id = f"{namespace_id}:{concept_code}:v{version}"
    body = {
        "concept_id": concept_id,
        "namespace_id": namespace_id,
        "concept_code": concept_code,
        "version": version,
        "record_kind": RECORD_COMPOSITE,
        "semantic_dimension": semantic.numel(),
        "semantic_digest": digest,
        "manifest": manifest.to_dict(),
    }
    integrity = record_integrity(body)
    candidate = ConceptRecord(
        concept_id=concept_id,
        namespace_id=namespace_id,
        concept_code=concept_code,
        version=version,
        record_kind=RECORD_COMPOSITE,
        semantic_dimension=semantic.numel(),
        semantic_payload=semantic,
        semantic_digest=digest,
        manifest=manifest,
        record_integrity=integrity,
    )
    temp_store = ConceptStore()
    temp_store.records = dict(store.records)
    temp_store.versions = {key: set(values) for key, values in store.versions.items()}
    temp_store.add(candidate)
    replay = replay_record(temp_store, concept_id)
    if replay.outcome not in {OUTCOME_COMPOSITE_REPLAY_VERIFIED, OUTCOME_COMPOSITE_REPLAY_CACHE_HIT}:
        raise RuntimeError(f"Replay validation failed before commit: {replay.outcome}")
    return candidate


def verify_record_integrity(record: ConceptRecord) -> bool:
    body = record.to_manifest_dict()
    return record_integrity(body) == record.record_integrity


def verify_manifest(manifest: CompositeManifest | None) -> bool:
    if manifest is None:
        return True
    if manifest.schema_version != SCHEMA_VERSION:
        return False
    if manifest.operation_code not in ALLOWED_OPS:
        return False
    if manifest.arity != len(manifest.ordered_operand_refs):
        return False
    expected = manifest_digest(manifest.payload())
    return expected == manifest.manifest_digest


def corrupt_observed(payload: torch.Tensor, probability: float, seed: int) -> torch.Tensor:
    if probability <= 0.0:
        return payload.detach().cpu().clone()
    flat = payload.detach().cpu().clone().reshape(-1)
    generator = make_generator(seed)
    mask = torch.rand(flat.numel(), generator=generator) < probability
    flat[mask] *= -1
    return flat.reshape(payload.shape)


def factorization_baseline(
    *,
    observation: torch.Tensor,
    domains: torch.Tensor,
) -> dict[str, Any]:
    current_estimates = build_initial_estimates(domains)
    previous: torch.Tensor | None = None
    stable = 0
    decoded: dict[str, torch.Tensor] | None = None
    start = time.perf_counter()
    for iteration in range(1, FACTORIZATION_ITERATIONS + 1):
        current_estimates = torchhd.resonator(observation, current_estimates, domains)
        similarities = torch.nn.functional.cosine_similarity(
            current_estimates.unsqueeze(-2).expand_as(domains),
            domains,
            dim=-1,
        )
        decoded = decode_top_candidates(similarities)
        if previous is not None and torch.equal(previous, decoded["top1_indices"]):
            stable += 1
        else:
            stable = 1
        previous = decoded["top1_indices"].clone()
        if stable >= FACTORIZATION_STABLE_PATIENCE:
            break
    if decoded is None:
        raise RuntimeError("Factorization baseline produced no decode")
    return {
        "predicted_indices": [int(item) for item in decoded["top1_indices"].tolist()],
        "latency_sec": time.perf_counter() - start,
        "iterations": iteration,
    }


def replay_record(
    store: ConceptStore,
    record_id: str,
    *,
    observed_semantic: torch.Tensor | None = None,
    max_depth: int = MAX_REPLAY_DEPTH,
    max_unique_nodes: int = MAX_REPLAY_UNIQUE_NODES,
    storage_arm: str = ARM_B_SIDECAR,
) -> ReplayResult:
    session = ReplaySession(cache={}, reachable_ids=set(), visiting=set())
    start = time.perf_counter()
    outcome, payload = _replay_recursive(
        store,
        record_id,
        session=session,
        depth=0,
        max_depth=max_depth,
        max_unique_nodes=max_unique_nodes,
    )
    latency = time.perf_counter() - start
    similarity = None if observed_semantic is None or payload is None else semantic_similarity(payload, observed_semantic)
    stats = ReplayStats(
        unique_nodes_visited=len(session.reachable_ids),
        cache_hits=session.cache_hits,
        operation_count=session.operation_count,
        lookup_count=session.lookup_count + (0 if storage_arm == ARM_C_INLINE else len(session.reachable_ids)),
        maximum_depth=session.maximum_depth,
        replay_latency_sec=latency,
        semantic_similarity_to_observed=similarity,
        factorizer_invoked=False,
    )
    return ReplayResult(
        outcome=outcome,
        record_id=record_id,
        semantic_payload=payload,
        semantic_digest=payload_checksum(payload) if payload is not None else None,
        reachable_record_ids=tuple(sorted(session.reachable_ids)),
        stats=stats,
    )


def _replay_recursive(
    store: ConceptStore,
    record_id: str,
    *,
    session: ReplaySession,
    depth: int,
    max_depth: int,
    max_unique_nodes: int,
) -> tuple[str, torch.Tensor | None]:
    session.maximum_depth = max(session.maximum_depth, depth)
    if depth > max_depth:
        return OUTCOME_REPLAY_BUDGET_EXHAUSTED, None
    if record_id in session.cache:
        session.cache_hits += 1
        return OUTCOME_COMPOSITE_REPLAY_CACHE_HIT, session.cache[record_id]
    if record_id in session.visiting:
        return OUTCOME_CYCLE_DETECTED, None
    session.lookup_count += 1
    record = store.get(record_id)
    if record is None:
        return OUTCOME_DANGLING_OPERAND_REF, None
    if len(session.reachable_ids) >= max_unique_nodes:
        return OUTCOME_REPLAY_BUDGET_EXHAUSTED, None
    session.reachable_ids.add(record_id)
    if not verify_record_integrity(record):
        return OUTCOME_MANIFEST_INTEGRITY_FAILURE, None
    if record.record_kind == RECORD_ATOM:
        session.cache[record_id] = record.semantic_payload
        return OUTCOME_ATOM_RESOLVED, record.semantic_payload
    if record.manifest is None or not verify_manifest(record.manifest):
        return OUTCOME_INVALID_MANIFEST, None
    session.visiting.add(record_id)
    parent_payloads: list[torch.Tensor] = []
    for reference in record.manifest.ordered_operand_refs:
        child_id, child = store.resolve(reference)
        if child is None:
            session.visiting.discard(record_id)
            if store.has_other_versions(reference):
                return OUTCOME_PARENT_VERSION_MISMATCH, None
            return OUTCOME_DANGLING_OPERAND_REF, None
        child_outcome, child_payload = _replay_recursive(
            store,
            child_id,
            session=session,
            depth=depth + 1,
            max_depth=max_depth,
            max_unique_nodes=max_unique_nodes,
        )
        if child_payload is None:
            session.visiting.discard(record_id)
            return child_outcome, None
        parent_payloads.append(child_payload)
    replayed = replay_operation(record.manifest.operation_code, tuple(parent_payloads), record.manifest.operation_parameters)
    session.operation_count += 1
    if payload_checksum(replayed) != record.semantic_digest:
        session.visiting.discard(record_id)
        return OUTCOME_SEMANTIC_COMMITMENT_MISMATCH, None
    session.cache[record_id] = replayed
    session.visiting.discard(record_id)
    return OUTCOME_COMPOSITE_REPLAY_VERIFIED, replayed


def build_atom_domains(dimensions: int, domain_size: int, seed: int) -> torch.Tensor:
    config = BaselineConfig(
        dimensions=dimensions,
        num_factors=2,
        domain_size=domain_size,
        structured_distractor_count=0,
        max_iterations=FACTORIZATION_ITERATIONS,
        stable_patience=FACTORIZATION_STABLE_PATIENCE,
    )
    return generate_domains(config, make_generator(seed))


def build_store_with_atoms(dimensions: int, domain_size: int, seed: int) -> tuple[ConceptStore, torch.Tensor]:
    domains = build_atom_domains(dimensions, domain_size, seed)
    store = ConceptStore()
    for factor_index in range(domains.size(0)):
        namespace_id = f"F{factor_index}"
        for concept_code in range(domain_size):
            store.add(
                create_atom_record(
                    namespace_id=namespace_id,
                    concept_code=concept_code,
                    version=1,
                    semantic_payload=domains[factor_index, concept_code],
                )
            )
    return store, domains


def build_flat_records(store: ConceptStore, count: int, seed: int) -> list[str]:
    generator = make_generator(seed)
    record_ids: list[str] = []
    for offset in range(count):
        left = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
        right = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
        record = create_composite_record(
            store=store,
            namespace_id="C_FLAT",
            concept_code=offset,
            version=1,
            operation_code=OP_BIND_2,
            ordered_operand_refs=(OperandRef("F0", left, 1), OperandRef("F1", right, 1)),
            operation_parameters={},
        )
        store.add(record)
        record_ids.append(record.concept_id)
    return record_ids


def build_chain_root(store: ConceptStore, depth: int, seed: int) -> str:
    generator = make_generator(seed)
    current_ref = OperandRef("F0", int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item()), 1)
    current_record_id = current_ref.key()
    for index in range(depth):
        if index % 2 == 0:
            record = create_composite_record(
                store=store,
                namespace_id="C_CHAIN",
                concept_code=10_000 + seed + index,
                version=1,
                operation_code=OP_PERMUTE,
                ordered_operand_refs=(OperandRef(store.get(current_record_id).namespace_id, store.get(current_record_id).concept_code, store.get(current_record_id).version),),
                operation_parameters={"shifts": PERMUTE_SHIFT},
            )
        else:
            other = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
            record = create_composite_record(
                store=store,
                namespace_id="C_CHAIN",
                concept_code=10_000 + seed + index,
                version=1,
                operation_code=OP_BIND_2,
                ordered_operand_refs=(
                    OperandRef(store.get(current_record_id).namespace_id, store.get(current_record_id).concept_code, store.get(current_record_id).version),
                    OperandRef("F1", other, 1),
                ),
                operation_parameters={},
            )
        store.add(record)
        current_record_id = record.concept_id
    return current_record_id


def build_balanced_tree_root(store: ConceptStore, depth: int, seed: int) -> str:
    generator = make_generator(seed)
    nodes: list[str] = []
    for offset in range(2**depth):
        namespace = "F0" if offset % 2 == 0 else "F1"
        idx = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
        nodes.append(OperandRef(namespace, idx, 1).key())
    layer = nodes
    serial = 20_000 + seed
    while len(layer) > 1:
        next_layer: list[str] = []
        for pair_index in range(0, len(layer), 2):
            left = store.get(layer[pair_index])
            right = store.get(layer[pair_index + 1])
            record = create_composite_record(
                store=store,
                namespace_id="C_TREE",
                concept_code=serial,
                version=1,
                operation_code=OP_BIND_2,
                ordered_operand_refs=(
                    OperandRef(left.namespace_id, left.concept_code, left.version),
                    OperandRef(right.namespace_id, right.concept_code, right.version),
                ),
                operation_parameters={},
            )
            serial += 1
            store.add(record)
            next_layer.append(record.concept_id)
        layer = next_layer
    return layer[0]


def build_shared_subgraph_roots(store: ConceptStore, seed: int) -> tuple[str, str]:
    generator = make_generator(seed)
    a = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
    b = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
    child = create_composite_record(
        store=store,
        namespace_id="C_SHARED",
        concept_code=30_000 + seed,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", a, 1), OperandRef("F1", b, 1)),
        operation_parameters={},
    )
    store.add(child)
    p = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
    q = int(torch.randint(0, FACTOR_DOMAIN_SIZE, (1,), generator=generator).item())
    left = create_composite_record(
        store=store,
        namespace_id="C_SHARED",
        concept_code=30_001 + seed,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(
            OperandRef(child.namespace_id, child.concept_code, child.version),
            OperandRef("F0", p, 1),
        ),
        operation_parameters={},
    )
    store.add(left)
    right = create_composite_record(
        store=store,
        namespace_id="C_SHARED",
        concept_code=30_002 + seed,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(
            OperandRef(child.namespace_id, child.concept_code, child.version),
            OperandRef("F1", q, 1),
        ),
        operation_parameters={},
    )
    store.add(right)
    return left.concept_id, right.concept_id


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "ADOPT_EXISTING_PRIMITIVES",
        "status": STATUS_FLAGS,
        "previous_blocked_lines": [
            {
                "checkpoint": "c6a24d7e16eef366bf03d78db306266a00c05e0c",
                "verdict": "BLOCK_DECODER_CERTIFICATION_LINE",
                "scientific_verdict": "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED",
            },
            {
                "checkpoint": STARTING_COMMIT,
                "verdict": "BLOCK_TAGGED_SYMBOL_LINE",
                "scientific_verdict": "CONFLICT_GUIDED_REPAIR_ADVANTAGE_NOT_SUPPORTED",
            },
        ],
        "anti_nih": {
            "ordinary_object_records": {"verdict": "ADOPT", "coverage": 1.0, "notes": "ConceptRecord is just a typed immutable object record."},
            "typed_structs_ast_dag": {"verdict": "ADOPT", "coverage": 0.9, "notes": "CompositeManifest is an exact first-order AST/DAG node."},
            "provenance_merkle_content_addressed": {"verdict": "ADOPT", "coverage": 0.8, "notes": "Reuse digest/integrity and immutable references instead of inventing a new identity system."},
            "hash_consing_event_sourcing": {"verdict": "ADOPT", "coverage": 0.7, "notes": "Optional dedup fits ordinary immutable record patterns."},
            "self_describing_records_and_tagged_unions": {"verdict": "ADOPT", "coverage": 1.0, "notes": "Inline manifest is a packaging choice, not a new learning mechanism."},
            "systematic_codes_and_exact_graph_plus_vector": {"verdict": "COMPARE", "coverage": 0.6, "notes": "This stage compares exact structural bits beside a semantic payload against ordinary sidecar storage."},
            "vsa_item_memories_and_map_ops": {"verdict": "WRAP", "coverage": 1.0, "notes": "Reuse existing MAP operations and verification, not a new VSA algebra."},
        },
        "blocked_claims": [
            "new fundamental VSA algebra",
            "compact identity codes are not pointers/handles",
            "exact history recovered from semantic similarity alone",
        ],
        "level35_frozen_artifact_hash": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json"),
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    protocol = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "starting_commit": STARTING_COMMIT,
        "status": STATUS_FLAGS,
        "heldout_execution_allowed": False,
        "identity_format": "namespace_id + uint32 local concept_code + version",
        "base50x4_codec": {
            "implemented": True,
            "capacity": BASE50_CAPACITY,
            "min_physical_bits": BASE50_MIN_BITS,
            "primary_storage_path": "uint32 local concept_code",
        },
        "manifest_schema": {
            "schema_version": SCHEMA_VERSION,
            "record_kind": [RECORD_ATOM, RECORD_COMPOSITE],
            "operation_registry": list(ALLOWED_OPS),
            "immediate_operands_only": True,
        },
        "replay_contract": {
            "memoization": True,
            "cycle_detection": True,
            "max_depth": MAX_REPLAY_DEPTH,
            "max_unique_nodes": MAX_REPLAY_UNIQUE_NODES,
            "deterministic_traversal_order": True,
        },
        "workloads": {
            "flat_bind_records": 12,
            "recursive_chain_depths": [1, 2, 4, 8, 16],
            "balanced_tree_depths": [2, 4, 6],
            "shared_subgraph_pairs": 1,
            "repeated_reads": [1, 10, 100, 1000],
            "semantic_observation_corruption": [0.0, 0.01, 0.05],
        },
        "arms": list(ALLOWED_ARMS),
        "allowed_claims": [
            "exact first-order structural manifests can be replayed safely",
            "self-describing after record retrieval",
            "inline versus sidecar is an engineering packaging comparison",
        ],
        "forbidden_claims": [
            "new VSA algorithm",
            "self-unbinding hypervector",
            "semantic self-addressing from noisy cue alone",
            "production readiness",
        ],
        "seed_fresh": seeds_are_fresh(repo_root),
        "level35_frozen_artifacts_unchanged": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256,
    }
    protocol["protocol_hash"] = canonical_json_hash(protocol)
    return protocol


def build_execution_plan(protocol: dict[str, Any]) -> str:
    chain_depths = protocol["workloads"]["recursive_chain_depths"]
    tree_depths = protocol["workloads"]["balanced_tree_depths"]
    repeated = protocol["workloads"]["repeated_reads"]
    estimated_trials = 12 + len(chain_depths) + len(tree_depths) + 2 + len(repeated) * 2 + 12
    lines = [
        f"# {TASK_NAME} execution plan",
        "",
        f"- starting_commit: `{STARTING_COMMIT}`",
        f"- branch: `codex/self-describing-record-v0_1`",
        f"- selected_operations: `{list(ALLOWED_OPS)}`",
        f"- depth_cells: chains `{chain_depths}`, trees `{tree_depths}`",
        f"- record_counts: flat_bind=`12`, shared_pair=`2 roots`",
        f"- estimated_trials: `{estimated_trials}`",
        f"- estimated_runtime: `sub-minute to low-minute CPU development run`",
        f"- output_path: `results/{RESULTS_NAMESPACE}`",
        f"- selected_device: `cpu`",
        "",
        "This stage is a bounded development-only replay audit, not a long benchmark or held-out run.",
    ]
    return "\n".join(lines) + "\n"


def build_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} audit",
        "",
        "- Verdict: `ADOPT_EXISTING_PRIMITIVES / WRAP`",
        "- Status: `ADOPT_EXISTING_PRIMITIVES / WRAP / PROTOTYPE_SYSTEM_INTEGRATION / DEVELOPMENT_ONLY / NO_NOVELTY_CLAIM / NO_PRODUCTION_CLAIM`",
        "",
        "## Previous blocked lines",
        "",
    ]
    for item in audit["previous_blocked_lines"]:
        lines.append(
            f"- `{item['checkpoint']}`: `{item['verdict']}` / `{item['scientific_verdict']}`"
        )
    lines.extend(["", "## Prior art", ""])
    for key, value in audit["anti_nih"].items():
        lines.append(f"- `{key}`: `{value['verdict']}` with coverage `{value['coverage']:.1f}`. {value['notes']}")
    lines.extend(
        [
            "",
            "## Expected anti-NIH conclusion",
            "",
            "- `ADOPT`: exact typed parent references, immutable/versioned records, DAG traversal, memoized replay, checksums/digests.",
            "- `WRAP`: existing MAP semantic operations and verifier.",
            "- `COMPARE`: inline manifest vs ordinary sidecar DAG.",
            "- `BLOCK`: any overclaim that the semantic geometry contains its own exact history.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_protocol_markdown(protocol: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} protocol",
        "",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        f"- Starting commit: `{protocol['starting_commit']}`",
        f"- Identity format: `{protocol['identity_format']}`",
        f"- Base-50 codec primary path: `{protocol['base50x4_codec']['primary_storage_path']}`",
        "",
        "## Operation registry",
        "",
    ]
    for op in protocol["manifest_schema"]["operation_registry"]:
        lines.append(f"- `{op}`")
    lines.extend(
        [
            "",
            "## Replay contract",
            "",
            f"- memoization: `{protocol['replay_contract']['memoization']}`",
            f"- cycle_detection: `{protocol['replay_contract']['cycle_detection']}`",
            f"- max_depth: `{protocol['replay_contract']['max_depth']}`",
            f"- max_unique_nodes: `{protocol['replay_contract']['max_unique_nodes']}`",
            "",
            "## Workloads",
            "",
            f"- flat_bind_records: `{protocol['workloads']['flat_bind_records']}`",
            f"- recursive_chain_depths: `{protocol['workloads']['recursive_chain_depths']}`",
            f"- balanced_tree_depths: `{protocol['workloads']['balanced_tree_depths']}`",
            f"- repeated_reads: `{protocol['workloads']['repeated_reads']}`",
            "",
            "## Scope limit",
            "",
            "- No locator, ANN, BCF, linear codes, runtime manager, or production storage stack in this stage.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_self_describing_record(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs"
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol = build_protocol(repo_root)
    audit = dependency_audit(repo_root)
    plan_text = build_execution_plan(protocol)
    print(plan_text, flush=True)

    store, domains = build_store_with_atoms(SEMANTIC_DIMENSIONS, FACTOR_DOMAIN_SIZE, ATOM_SEED)
    flat_ids = build_flat_records(store, 12, FLAT_BIND_SEED)
    chain_roots = [build_chain_root(store, depth, CHAIN_SEED + depth) for depth in protocol["workloads"]["recursive_chain_depths"]]
    tree_roots = [build_balanced_tree_root(store, depth, TREE_SEED + depth) for depth in protocol["workloads"]["balanced_tree_depths"]]
    shared_left, shared_right = build_shared_subgraph_roots(store, SHARED_SEED)

    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    def add_replay_trial(arm_id: str, workload: str, record_id: str, observed: torch.Tensor | None = None) -> ReplayResult:
        result = replay_record(store, record_id, observed_semantic=observed, storage_arm=arm_id)
        raw_rows.append(
            {
                "record_type": "replay_trial",
                "arm_id": arm_id,
                "workload": workload,
                "record_id": record_id,
                "outcome": result.outcome,
                "semantic_digest": result.semantic_digest,
                "reachable_record_ids": list(result.reachable_record_ids),
                **asdict(result.stats),
            }
        )
        return result

    for arm in (ARM_B_SIDECAR, ARM_C_INLINE):
        for record_id in flat_ids:
            record = store.get(record_id)
            for noise in protocol["workloads"]["semantic_observation_corruption"]:
                observed = corrupt_observed(record.semantic_payload, noise, CORRUPTION_SEED + int(noise * 1000) + record.concept_code)
                add_replay_trial(arm, f"flat_bind_noise_{noise:.2f}", record_id, observed)
        for record_id in chain_roots:
            add_replay_trial(arm, "recursive_chain", record_id)
        for record_id in tree_roots:
            add_replay_trial(arm, "balanced_tree", record_id)
        add_replay_trial(arm, "shared_left", shared_left)
        add_replay_trial(arm, "shared_right", shared_right)
        for repeat in protocol["workloads"]["repeated_reads"]:
            target = chain_roots[-1]
            latencies: list[float] = []
            for _ in range(repeat):
                result = replay_record(store, target, storage_arm=arm)
                latencies.append(result.stats.replay_latency_sec)
            raw_rows.append(
                {
                    "record_type": "repeated_read",
                    "arm_id": arm,
                    "workload": f"repeat_{repeat}",
                    "record_id": target,
                    "repeat_count": repeat,
                    "mean_replay_latency_sec": float(statistics.fmean(latencies)),
                }
            )

    for record_id in flat_ids:
        record = store.get(record_id)
        ref_a = record.manifest.ordered_operand_refs[0]
        ref_b = record.manifest.ordered_operand_refs[1]
        observation = corrupt_observed(record.semantic_payload, 0.05, CORRUPTION_SEED + record.concept_code)
        factor_domains = torch.stack(
            [
                domains[0],
                domains[1],
            ],
            dim=0,
        )
        baseline = factorization_baseline(observation=observation, domains=factor_domains)
        exact = baseline["predicted_indices"] == [ref_a.concept_code, ref_b.concept_code]
        raw_rows.append(
            {
                "record_type": "factorization_baseline",
                "arm_id": ARM_A_BASELINE,
                "workload": "flat_bind_noise_0.05",
                "record_id": record_id,
                "predicted_indices": baseline["predicted_indices"],
                "exact_recovery": exact,
                "latency_sec": baseline["latency_sec"],
                "iterations": baseline["iterations"],
            }
        )

    # Corruption safety trials.
    sample_record = store.get(flat_ids[0])
    corrupted_manifest = replace(
        sample_record,
        manifest=replace(sample_record.manifest, manifest_digest="0" * len(sample_record.manifest.manifest_digest)),
    )
    corrupt_store = ConceptStore()
    corrupt_store.records = dict(store.records)
    corrupt_store.versions = {key: set(values) for key, values in store.versions.items()}
    corrupt_store.records[corrupted_manifest.concept_id] = corrupted_manifest
    raw_rows.append(
        {
            "record_type": "corruption_trial",
            "case": "manifest_bitflip",
            "outcome": replay_record(corrupt_store, corrupted_manifest.concept_id).outcome,
        }
    )
    wrong_ref_manifest = replace(
        sample_record.manifest,
        ordered_operand_refs=(OperandRef("F0", sample_record.manifest.ordered_operand_refs[0].concept_code + 1, 1), sample_record.manifest.ordered_operand_refs[1]),
    )
    wrong_ref_manifest = replace(wrong_ref_manifest, manifest_digest=manifest_digest(wrong_ref_manifest.payload()))
    wrong_ref_record = replace(sample_record, manifest=wrong_ref_manifest)
    wrong_ref_record = replace(wrong_ref_record, record_integrity=record_integrity(wrong_ref_record.to_manifest_dict()))
    wrong_store = ConceptStore()
    wrong_store.records = dict(store.records)
    wrong_store.versions = {key: set(values) for key, values in store.versions.items()}
    wrong_store.records[wrong_ref_record.concept_id] = wrong_ref_record
    raw_rows.append(
        {
            "record_type": "corruption_trial",
            "case": "wrong_valid_handle",
            "outcome": replay_record(wrong_store, wrong_ref_record.concept_id).outcome,
        }
    )
    dangling_manifest = replace(
        sample_record.manifest,
        ordered_operand_refs=(OperandRef("F0", 999_999, 1), sample_record.manifest.ordered_operand_refs[1]),
    )
    dangling_manifest = replace(dangling_manifest, manifest_digest=manifest_digest(dangling_manifest.payload()))
    dangling_record = replace(sample_record, manifest=dangling_manifest)
    dangling_record = replace(dangling_record, record_integrity=record_integrity(dangling_record.to_manifest_dict()))
    dangling_store = ConceptStore()
    dangling_store.records = dict(store.records)
    dangling_store.versions = {key: set(values) for key, values in store.versions.items()}
    dangling_store.records[dangling_record.concept_id] = dangling_record
    raw_rows.append(
        {
            "record_type": "corruption_trial",
            "case": "dangling_parent",
            "outcome": replay_record(dangling_store, dangling_record.concept_id).outcome,
        }
    )
    stale_manifest = replace(
        sample_record.manifest,
        ordered_operand_refs=(OperandRef("F0", sample_record.manifest.ordered_operand_refs[0].concept_code, 7), sample_record.manifest.ordered_operand_refs[1]),
    )
    stale_manifest = replace(stale_manifest, manifest_digest=manifest_digest(stale_manifest.payload()))
    stale_record = replace(sample_record, manifest=stale_manifest)
    stale_record = replace(stale_record, record_integrity=record_integrity(stale_record.to_manifest_dict()))
    stale_store = ConceptStore()
    stale_store.records = dict(store.records)
    stale_store.versions = {key: set(values) for key, values in store.versions.items()}
    stale_store.records[stale_record.concept_id] = stale_record
    raw_rows.append(
        {
            "record_type": "corruption_trial",
            "case": "stale_parent_version",
            "outcome": replay_record(stale_store, stale_record.concept_id).outcome,
        }
    )
    cycle_store = ConceptStore()
    cycle_store.records = dict(store.records)
    cycle_store.versions = {key: set(values) for key, values in store.versions.items()}
    a = create_composite_record(
        store=cycle_store,
        namespace_id="CYCLE",
        concept_code=1,
        version=1,
        operation_code=OP_PERMUTE,
        ordered_operand_refs=(OperandRef("F0", 0, 1),),
        operation_parameters={"shifts": PERMUTE_SHIFT},
    )
    cycle_store.add(a)
    b_manifest = CompositeManifest(
        schema_version=SCHEMA_VERSION,
        operation_code=OP_PERMUTE,
        arity=1,
        ordered_operand_refs=(OperandRef("CYCLE", 1, 1),),
        operation_parameters={"shifts": PERMUTE_SHIFT},
        manifest_digest=manifest_digest(
            {
                "schema_version": SCHEMA_VERSION,
                "operation_code": OP_PERMUTE,
                "arity": 1,
                "ordered_operand_refs": [OperandRef("CYCLE", 1, 1).to_dict()],
                "operation_parameters": {"shifts": PERMUTE_SHIFT},
            }
        ),
    )
    b = replace(a, concept_id="CYCLE:2:v1", concept_code=2, manifest=b_manifest)
    b = replace(b, record_integrity=record_integrity(b.to_manifest_dict()))
    cycle_a_manifest = CompositeManifest(
        schema_version=SCHEMA_VERSION,
        operation_code=OP_PERMUTE,
        arity=1,
        ordered_operand_refs=(OperandRef("CYCLE", 2, 1),),
        operation_parameters={"shifts": PERMUTE_SHIFT},
        manifest_digest=manifest_digest(
            {
                "schema_version": SCHEMA_VERSION,
                "operation_code": OP_PERMUTE,
                "arity": 1,
                "ordered_operand_refs": [OperandRef("CYCLE", 2, 1).to_dict()],
                "operation_parameters": {"shifts": PERMUTE_SHIFT},
            }
        ),
    )
    a = replace(a, manifest=cycle_a_manifest)
    a = replace(a, record_integrity=record_integrity(a.to_manifest_dict()))
    cycle_store.records[a.concept_id] = a
    cycle_store.add(b)
    raw_rows.append(
        {
            "record_type": "corruption_trial",
            "case": "cycle_detected",
            "outcome": replay_record(cycle_store, a.concept_id).outcome,
        }
    )

    for arm in (ARM_B_SIDECAR, ARM_C_INLINE):
        batch = [row for row in raw_rows if row.get("record_type") == "replay_trial" and row["arm_id"] == arm]
        summary_rows.append(
            {
                "arm_id": arm,
                "exact_reconstruction_rate": sum(
                    row["outcome"] in {OUTCOME_ATOM_RESOLVED, OUTCOME_COMPOSITE_REPLAY_VERIFIED, OUTCOME_COMPOSITE_REPLAY_CACHE_HIT}
                    for row in batch
                )
                / max(1, len(batch)),
                "mean_latency_sec": float(statistics.fmean(row["replay_latency_sec"] for row in batch)),
                "mean_lookup_count": float(statistics.fmean(row["lookup_count"] for row in batch)),
                "mean_unique_nodes": float(statistics.fmean(row["unique_nodes_visited"] for row in batch)),
                "mean_cache_hits": float(statistics.fmean(row["cache_hits"] for row in batch)),
                "deployable_total_bytes": tensor_bytes(next(iter(store.records.values())).semantic_payload) + statistics.fmean(
                    len(serialize_manifest_bytes(record.manifest)) if record.manifest is not None else 0
                    for record in store.records.values()
                ),
            }
        )
    baseline_batch = [row for row in raw_rows if row.get("record_type") == "factorization_baseline"]
    summary_rows.append(
        {
            "arm_id": ARM_A_BASELINE,
            "exact_reconstruction_rate": sum(row["exact_recovery"] for row in baseline_batch) / max(1, len(baseline_batch)),
            "mean_latency_sec": float(statistics.fmean(row["latency_sec"] for row in baseline_batch)),
            "mean_lookup_count": 0.0,
            "mean_unique_nodes": 0.0,
            "mean_cache_hits": 0.0,
            "deployable_total_bytes": tensor_bytes(next(iter(store.records.values())).semantic_payload),
        }
    )

    lookup = {row["arm_id"]: row for row in summary_rows}
    sidecar = lookup[ARM_B_SIDECAR]
    inline = lookup[ARM_C_INLINE]
    if sidecar["exact_reconstruction_rate"] < 1.0 or inline["exact_reconstruction_rate"] < 1.0:
        engineering_verdict = "BLOCK_SELF_DESCRIBING_RECORD_PATH"
        scientific_status = "PACKAGING_ADVANTAGE_NOT_SUPPORTED"
        build_verdict = "BLOCK_SELF_DESCRIBING_RECORD_PATH"
    elif sidecar["mean_latency_sec"] <= inline["mean_latency_sec"] and sidecar["deployable_total_bytes"] <= inline["deployable_total_bytes"]:
        engineering_verdict = "ADOPT_ORDINARY_SIDECAR_DAG"
        scientific_status = "PACKAGING_ADVANTAGE_NOT_SUPPORTED"
        build_verdict = "ADOPT_ORDINARY_SIDECAR_DAG"
    elif inline["mean_latency_sec"] < sidecar["mean_latency_sec"] and inline["deployable_total_bytes"] < sidecar["deployable_total_bytes"]:
        engineering_verdict = "ADOPT_INLINE_PACKED_RECORD"
        scientific_status = "PACKAGING_ADVANTAGE_SUPPORTED"
        build_verdict = "ADOPT_INLINE_PACKED_RECORD"
    else:
        engineering_verdict = "ADOPT_EXACT_FIRST_ORDER_MANIFEST"
        scientific_status = "PACKAGING_ADVANTAGE_NOT_SUPPORTED"
        build_verdict = "INLINE_PACKING_EQUIVALENT_ONLY"

    summary = {
        "build_verdict": build_verdict,
        "engineering_verdict": engineering_verdict,
        "scientific_status": scientific_status,
        "protocol_hash": protocol["protocol_hash"],
        "heldout_execution_count": 0,
        "arm_summary": summary_rows,
        "corruption_outcomes": {
            row["case"]: row["outcome"]
            for row in raw_rows
            if row.get("record_type") == "corruption_trial"
        },
        "base50_result": {
            "capacity": BASE50_CAPACITY,
            "min_physical_bits": BASE50_MIN_BITS,
            "packed_uint24_bits": 24,
            "equivalent_for_primary_storage": True,
        },
    }

    audit_markdown = build_audit_markdown(audit)
    protocol_markdown = build_protocol_markdown(protocol)
    report_lines = [
        f"# {TASK_NAME}",
        "",
        f"- Build verdict: `{summary['build_verdict']}`",
        f"- Engineering verdict: `{summary['engineering_verdict']}`",
        f"- Scientific status: `{summary['scientific_status']}`",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        "",
        "## Arm snapshot",
        "",
    ]
    for row in summary_rows:
        report_lines.append(
            f"- `{row['arm_id']}`: exact `{row['exact_reconstruction_rate']:.4f}`, latency `{row['mean_latency_sec']:.6f}s`, "
            f"lookups `{row['mean_lookup_count']:.2f}`, bytes `{row['deployable_total_bytes']:.2f}`."
        )
    report_lines.extend(["", "## Corruption outcomes", ""])
    for case, outcome in summary["corruption_outcomes"].items():
        report_lines.append(f"- `{case}`: `{outcome}`")
    report = "\n".join(report_lines) + "\n"

    write_text(docs_dir / "LEVEL3_SELF_DESCRIBING_HYPERVECTOR_AUDIT.md", audit_markdown)
    write_text(docs_dir / "LEVEL3_SELF_DESCRIBING_HYPERVECTOR_PROTOCOL.md", protocol_markdown)
    write_text(results_dir / "execution_plan.md", plan_text)
    write_text(results_dir / "frozen_protocol.yaml", "\n".join(yaml_lines(protocol)) + "\n")
    write_json(results_dir / "summary.json", summary)
    write_text(results_dir / "report.md", report)
    write_jsonl(results_dir / "raw_trials.jsonl", raw_rows)
    write_json(results_dir / "environment.json", environment_snapshot())
    write_json(results_dir / "dependency_audit.json", audit)

    return {"protocol": protocol, "summary": summary, "raw_rows": raw_rows}
