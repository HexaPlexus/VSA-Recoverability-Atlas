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
from typing import Any

import numpy as np
import torch
import torchhd

from .lazy_trace_addressing_stage_a import (
    CORRUPTION_CHANNEL_ID,
    MAP_DIMENSIONS,
    QUERY_CORRUPTION_POINTS,
    build_dataset as build_stage_a_dataset,
    corrupt_payload,
    prior_known_seed_set as stage_a_prior_known_seed_set,
    stage_a_seed_set,
)
from .level3_5b_native_noise_frontiers import prior_seed_set as level3_5b_prior_seed_set
from .release_artifacts import canonical_sha256
from .semantic_lsh import RandomBucketRouter, RandomHyperplaneLSH, RoutingResult, SignatureConfig
from .trace_index import TraceIndex, TraceStoreEntry
from .trace_record import TRACE_VALID, ALLOWED_OPERATION_FAMILIES, TraceRecord, payload_checksum
from .verification import (
    DECISION_ABSTAIN,
    DECISION_ACCEPT,
    DECISION_EXPAND,
    RerankedCandidate,
    rerank_candidates,
)

STAGE_A1_SCHEMA_VERSION = "lazy-semantic-trace-stage-a1-dev-v1"
STAGE_A1_TASK_NAME = "Lazy Semantic-to-Trace Addressing - Stage A.1"
STAGE_A1_NAMESPACE = "lazy_trace_stage_a1"
STAGE_A1_BRANCH_EXPECTATION = "codex/lazy-trace-addressing-stage-a1"
STAGE_A1_BASE_CHECKPOINT_COMMIT = "ccf3730aab9ada8bac3675eb298f0e755d9bb98f"
STAGE_A_PROTOCOL_HASH = "f9f770c7af19ad7fc5efb2d8191be116ecdccfd6d6b22f51d7c74da8c58f50ab"

DATASET_SPECS: tuple[dict[str, Any], ...] = (
    {"dataset_id": "n10000", "record_count": 10_000, "query_trials_per_point": 512},
)
DATASET_SEED_RANGES = {"n10000": {"start": 930450100, "count": 1}}
QUERY_SEED_RANGES = {
    "n10000": {
        "0.00": {"start": 930460100, "count": 512},
        "0.01": {"start": 930461100, "count": 512},
        "0.03": {"start": 930462100, "count": 512},
        "0.05": {"start": 930463100, "count": 512},
        "0.10": {"start": 930464100, "count": 512},
        "0.15": {"start": 930465100, "count": 512},
    }
}
PROJECTION_SEEDS = (930470101, 930470102, 930470103)
SMOKE_SEED = 930480001

QUERY_CORRUPTION_POINTS_A1 = tuple(float(point) for point in QUERY_CORRUPTION_POINTS)
RERANK_K = 32
PRIMARY_CANDIDATE_BUDGET = 100
STAGE_A_LEGACY_CANDIDATE_BUDGET = 96
ACCEPT_SIMILARITY_THRESHOLD = 0.88
ACCEPT_MARGIN = 0.015
AMBIGUITY_SIMILARITY_EPSILON = 1e-8
PRIMARY_COVERAGE_THRESHOLD = 0.80
THEORY_TOLERANCE = 0.05
MARGIN_PROBE_BUDGET = 4
GLOBAL_SCAN_WARMUP_QUERIES = 8
GLOBAL_SCAN_TIMED_REPEATS = 1

METHOD_GLOBAL_SCAN = "B0_global_exact_semantic_scan"
METHOD_EXACT_HASH = "B1_exact_content_hash_only"
METHOD_RANDOM_ROUTING = "B2_random_bucket_routing"
METHOD_STAGE_A_MULTI_TABLE = "B3_stage_a_four_table_lsh"
METHOD_A1_PRIMARY = "B4_a1p_multi_table_lsh"
METHOD_A1_SECONDARY_1 = "B5_a1s1_multi_table_lsh"
METHOD_A1_SECONDARY_2 = "B6_a1s2_multi_table_lsh"
METHOD_A1_MULTI_PROBE = "B7_margin_aware_multi_probe_lsh"

OUTCOME_ACCEPT = "ACCEPT"
OUTCOME_ABSTAIN = "ABSTAIN"
OUTCOME_EXPAND = "EXPAND"
OUTCOME_AMBIGUOUS_TRACE = "AMBIGUOUS_TRACE"

QUERY_KIND_UNIQUE = "UNIQUE"
QUERY_KIND_NEAR_CONFLICT = "NEAR_CONFLICT"
QUERY_KIND_EXACT_AMBIGUITY = "EXACT_AMBIGUITY"
QUERY_KIND_CONTRACT_AMBIGUITY = "CONTRACT_AMBIGUITY"

ALLOWED_CHANGE_CLASSES = (
    "ANALYTICAL_GRID_REPAIR",
    "BASELINE_IMPLEMENTATION_REPAIR",
    "SAMPLE_SIZE_INCREASE",
    "METRIC_DISAMBIGUATION",
    "ADVERSARIAL_DATASET_STRENGTHENING",
    "METADATA_ONLY",
)


@dataclass(frozen=True)
class MethodConfig:
    method_id: str
    signature_bits: int
    table_count: int
    probe_budget: int
    candidate_budget: int
    rerank_k: int
    projection_seed: int
    routing_mode: str
    family: str
    budget_match_target: str | None = None
    analytical_model: str = "primary_signature_collision"


@dataclass(frozen=True)
class StageA1Record:
    record_id: str
    trace_handle: str
    trace_record: TraceRecord
    semantic_payload: torch.Tensor
    family_label: str
    arity: int
    operand_namespaces: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    parent_handles: tuple[str, ...]
    adversarial_group: str | None
    ambiguity_kind: str | None


@dataclass(frozen=True)
class StageA1Query:
    query_id: str
    trial_seed: int
    dataset_id: str
    corruption_probability: float
    target_handle: str
    target_record_id: str
    target_contract_key: str
    target_exact_key: str
    noisy_payload: torch.Tensor
    clean_payload: torch.Tensor
    target_payload_checksum: str
    target_operation_family: str
    target_arity: int
    target_namespaces: tuple[str, ...]
    target_operation_parameters: dict[str, int | str]
    target_parent_handles: tuple[str, ...]
    query_kind: str
    exact_ambiguous_handles: tuple[str, ...]
    contract_ambiguous_keys: tuple[str, ...]


@dataclass(frozen=True)
class TaskDecision:
    outcome: str
    accepted_handle: str | None
    accepted_contract_key: str | None
    accepted_exact_key: str | None
    coverage: int
    wrong_acceptance: int


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


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials == 0:
        return (0.0, 0.0)
    phat = successes / trials
    denom = 1.0 + (z * z) / trials
    center = (phat + (z * z) / (2 * trials)) / denom
    margin = (
        z
        * math.sqrt((phat * (1.0 - phat) / trials) + ((z * z) / (4 * trials * trials)))
        / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def expected_query_similarity(probability: float) -> float:
    return max(-1.0, min(1.0, 1.0 - (2.0 * probability)))


def expected_single_bit_collision_probability(probability: float) -> float:
    rho = expected_query_similarity(probability)
    return 1.0 - (math.acos(max(-1.0, min(1.0, rho))) / math.pi)


def expected_single_table_hit_probability(*, signature_bits: int, probability: float, probe_budget: int, routing_mode: str) -> float:
    q = expected_single_bit_collision_probability(probability)
    primary = q**signature_bits
    if routing_mode != "margin_probe" or probe_budget <= 1:
        return primary
    first_order = (q ** max(0, signature_bits - 1)) * (1.0 - q)
    neighbor_mass = min(signature_bits, probe_budget - 1) * first_order
    return min(1.0, primary + neighbor_mass)


def expected_any_table_hit_probability(*, signature_bits: int, table_count: int, probability: float, probe_budget: int, routing_mode: str) -> float:
    single = expected_single_table_hit_probability(
        signature_bits=signature_bits,
        probability=probability,
        probe_budget=probe_budget,
        routing_mode=routing_mode,
    )
    return 1.0 - ((1.0 - single) ** table_count)


def expected_random_bucket_occupancy(*, record_count: int, signature_bits: int, table_count: int, probe_budget: int) -> float:
    probed_buckets = table_count * max(1, probe_budget)
    return probed_buckets * (record_count / float(2**signature_bits))


def ordered_items(mapping: dict[str, int | str]) -> tuple[tuple[str, int | str], ...]:
    return tuple(sorted(mapping.items()))


def contract_key_from_trace(trace_record: TraceRecord) -> str:
    payload = {
        "operation_family": trace_record.operation_family,
        "algebra": trace_record.algebra,
        "arity": trace_record.arity,
        "operand_namespaces": list(trace_record.operand_namespaces),
        "operation_parameters": dict(sorted(trace_record.operation_parameters.items())),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def contract_key_from_candidate(candidate: RerankedCandidate) -> str:
    payload = {
        "operation_family": candidate.operation_family,
        "algebra": candidate.algebra,
        "arity": candidate.arity,
        "operand_namespaces": list(candidate.operand_namespaces),
        "operation_parameters": dict(sorted(candidate.operation_parameters.items())),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def exact_key_from_trace(trace_record: TraceRecord) -> str:
    payload = {
        "trace_handle": trace_record.trace_handle,
        "record_id": trace_record.record_id,
        "operation_parameters": dict(sorted(trace_record.operation_parameters.items())),
        "parent_handles": list(trace_record.parent_handles),
        "semantic_payload_checksum": trace_record.semantic_payload_checksum,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def exact_key_from_candidate(candidate: RerankedCandidate) -> str:
    payload = {
        "trace_handle": candidate.handle,
        "record_id": candidate.record_id,
        "operation_parameters": dict(sorted(candidate.operation_parameters.items())),
        "parent_handles": list(candidate.parent_handles),
        "semantic_payload_checksum": candidate.semantic_payload_checksum,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def stage_a1_seed_set() -> set[int]:
    values: set[int] = set(PROJECTION_SEEDS)
    values.add(SMOKE_SEED)
    for mapping in (DATASET_SEED_RANGES,):
        for spec in mapping.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    for per_dataset in QUERY_SEED_RANGES.values():
        for spec in per_dataset.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    return values


def prior_known_seed_set(repo_root: Path) -> set[int]:
    prior = set(stage_a_prior_known_seed_set(repo_root))
    prior.update(stage_a_seed_set())
    prior.update(level3_5b_prior_seed_set())
    return prior


def seeds_are_fresh(repo_root: Path) -> bool:
    return stage_a1_seed_set().isdisjoint(prior_known_seed_set(repo_root))


def _clone_record(
    *,
    source: StageA1Record,
    record_ordinal: int,
    operation_family: str | None = None,
    arity: int | None = None,
    operand_namespaces: tuple[str, ...] | None = None,
    operation_parameters: dict[str, int | str] | None = None,
    parent_handles: tuple[str, ...] | None = None,
    ambiguity_kind: str | None = None,
    adversarial_group: str | None = None,
) -> StageA1Record:
    trace_handle = f"trace:a1:{record_ordinal:05d}"
    record_id = f"record:a1:{record_ordinal:05d}"
    family = operation_family or source.family_label
    record_arity = arity if arity is not None else source.arity
    namespaces = operand_namespaces or source.operand_namespaces
    params = dict(operation_parameters if operation_parameters is not None else source.operation_parameters)
    parents = parent_handles or source.parent_handles
    trace_record = TraceRecord(
        trace_handle=trace_handle,
        record_id=record_id,
        operation_family=family,
        algebra="MAP",
        arity=record_arity,
        operand_namespaces=namespaces,
        operation_parameters=params,
        parent_handles=parents,
        semantic_payload_checksum=payload_checksum(source.semantic_payload),
    )
    return StageA1Record(
        record_id=record_id,
        trace_handle=trace_handle,
        trace_record=trace_record,
        semantic_payload=source.semantic_payload.detach().clone().cpu(),
        family_label=family,
        arity=record_arity,
        operand_namespaces=namespaces,
        operation_parameters=params,
        parent_handles=parents,
        adversarial_group=adversarial_group,
        ambiguity_kind=ambiguity_kind,
    )


def _alt_contract_template(index: int, original_family: str) -> tuple[str, int, tuple[str, ...], dict[str, int | str]]:
    templates = (
        ("MAP_BIND_2", 2, ("OBS", "CTX"), {}),
        ("MAP_BIND_3", 3, ("OBS", "REL", "ATTR"), {}),
        ("MAP_BUNDLE_3", 3, ("OBS", "OBS", "STATE"), {}),
        ("MAP_BUNDLE_5", 5, ("OBS", "OBS", "ATTR", "STATE", "CTX"), {}),
        ("MAP_PERMUTE_K", 1, ("OBS",), {"shifts": 3}),
        ("MAP_BIND_THEN_BUNDLE", 4, ("ROLE", "OBS", "STATE", "CTX"), {"bundle_width": 3}),
    )
    for offset in range(len(templates)):
        family, arity, namespaces, params = templates[(index + offset) % len(templates)]
        if family != original_family:
            return family, arity, namespaces, params
    raise RuntimeError("No alternative contract template available.")


def build_dataset(*, dataset_seed: int, record_count: int) -> list[StageA1Record]:
    ambiguity_budget = max(0, record_count - 200)
    exact_ambiguity_duplicates = min(100, max(0, ambiguity_budget // 2))
    contract_ambiguity_duplicates = min(100, max(0, ambiguity_budget // 2))
    base_unique_count = record_count - exact_ambiguity_duplicates - contract_ambiguity_duplicates
    base_records = build_stage_a_dataset(dataset_seed=dataset_seed, record_count=base_unique_count)
    records: list[StageA1Record] = []
    for ordinal, record in enumerate(base_records):
        records.append(
            StageA1Record(
                record_id=f"record:a1:{ordinal:05d}",
                trace_handle=f"trace:a1:{ordinal:05d}",
                trace_record=TraceRecord(
                    trace_handle=f"trace:a1:{ordinal:05d}",
                    record_id=f"record:a1:{ordinal:05d}",
                    operation_family=record.family_label,
                    algebra="MAP",
                    arity=record.arity,
                    operand_namespaces=record.operand_namespaces,
                    operation_parameters=dict(record.trace_record.operation_parameters),
                    parent_handles=record.trace_record.parent_handles,
                    semantic_payload_checksum=payload_checksum(record.semantic_payload),
                ),
                semantic_payload=record.semantic_payload.detach().clone().cpu(),
                family_label=record.family_label,
                arity=record.arity,
                operand_namespaces=record.operand_namespaces,
                operation_parameters=dict(record.trace_record.operation_parameters),
                parent_handles=record.trace_record.parent_handles,
                adversarial_group=record.adversarial_group,
                ambiguity_kind=None,
            )
        )

    for duplicate_index, source in enumerate(records[:exact_ambiguity_duplicates]):
        group = f"exact-ambiguity-{duplicate_index:03d}"
        alt_parents = tuple(f"{parent}|alt_parent:{duplicate_index}:{position}" for position, parent in enumerate(source.parent_handles))
        records.append(
            _clone_record(
                source=source,
                record_ordinal=len(records),
                parent_handles=alt_parents,
                ambiguity_kind=QUERY_KIND_EXACT_AMBIGUITY,
                adversarial_group=group,
            )
        )
        records[duplicate_index] = StageA1Record(
            record_id=source.record_id,
            trace_handle=source.trace_handle,
            trace_record=source.trace_record,
            semantic_payload=source.semantic_payload,
            family_label=source.family_label,
            arity=source.arity,
            operand_namespaces=source.operand_namespaces,
            operation_parameters=source.operation_parameters,
            parent_handles=source.parent_handles,
            adversarial_group=group,
            ambiguity_kind=QUERY_KIND_EXACT_AMBIGUITY,
        )

    contract_sources = records[exact_ambiguity_duplicates : exact_ambiguity_duplicates + contract_ambiguity_duplicates]
    for duplicate_index, source in enumerate(contract_sources):
        family, arity, namespaces, params = _alt_contract_template(duplicate_index, source.family_label)
        group = f"contract-ambiguity-{duplicate_index:03d}"
        parent_handles = tuple(f"contract_alt:{family}:{duplicate_index}:{slot}" for slot in range(arity))
        records.append(
            _clone_record(
                source=source,
                record_ordinal=len(records),
                operation_family=family,
                arity=arity,
                operand_namespaces=namespaces,
                operation_parameters=params,
                parent_handles=parent_handles,
                ambiguity_kind=QUERY_KIND_CONTRACT_AMBIGUITY,
                adversarial_group=group,
            )
        )
        source_index = exact_ambiguity_duplicates + duplicate_index
        records[source_index] = StageA1Record(
            record_id=source.record_id,
            trace_handle=source.trace_handle,
            trace_record=source.trace_record,
            semantic_payload=source.semantic_payload,
            family_label=source.family_label,
            arity=source.arity,
            operand_namespaces=source.operand_namespaces,
            operation_parameters=source.operation_parameters,
            parent_handles=source.parent_handles,
            adversarial_group=group,
            ambiguity_kind=QUERY_KIND_CONTRACT_AMBIGUITY,
        )
    return records[:record_count]


def build_trace_index(records: list[StageA1Record]) -> TraceIndex:
    index = TraceIndex()
    for record in records:
        index.insert(
            TraceStoreEntry(
                trace_record=record.trace_record,
                semantic_payload=record.semantic_payload,
                committed=True,
                family_label=record.family_label,
                namespace_contract=record.operand_namespaces,
                arity=record.arity,
            )
        )
    return index


def build_queries(
    *,
    dataset_id: str,
    records: list[StageA1Record],
    query_seed_start: int,
    query_count: int,
    corruption_probability: float,
) -> list[StageA1Query]:
    grouped: dict[str, list[StageA1Record]] = {}
    unique_records: list[StageA1Record] = []
    near_conflict_records: list[StageA1Record] = []
    for record in records:
        if record.adversarial_group:
            grouped.setdefault(record.adversarial_group, []).append(record)
        if record.ambiguity_kind is None and record.adversarial_group is None:
            unique_records.append(record)
        elif record.ambiguity_kind is None:
            near_conflict_records.append(record)

    exact_groups = [group for group in grouped.values() if any(item.ambiguity_kind == QUERY_KIND_EXACT_AMBIGUITY for item in group)]
    contract_groups = [group for group in grouped.values() if any(item.ambiguity_kind == QUERY_KIND_CONTRACT_AMBIGUITY for item in group)]
    near_groups = [group for group in grouped.values() if all(item.ambiguity_kind is None for item in group)]

    queries: list[StageA1Query] = []
    for offset in range(query_count):
        seed = query_seed_start + offset
        rng = random.Random(seed)
        if contract_groups and offset % 16 == 0:
            group = contract_groups[(offset // 16) % len(contract_groups)]
            target = group[rng.randrange(len(group))]
            query_kind = QUERY_KIND_CONTRACT_AMBIGUITY
            exact_handles = tuple(item.trace_handle for item in group)
            contract_keys = tuple(contract_key_from_trace(item.trace_record) for item in group)
        elif exact_groups and offset % 8 == 0:
            group = exact_groups[(offset // 8) % len(exact_groups)]
            target = group[rng.randrange(len(group))]
            query_kind = QUERY_KIND_EXACT_AMBIGUITY
            exact_handles = tuple(item.trace_handle for item in group)
            contract_keys = tuple(contract_key_from_trace(item.trace_record) for item in group)
        elif near_groups and offset % 4 == 0:
            group = near_groups[(offset // 4) % len(near_groups)]
            target = group[rng.randrange(len(group))]
            query_kind = QUERY_KIND_NEAR_CONFLICT
            exact_handles = (target.trace_handle,)
            contract_keys = (contract_key_from_trace(target.trace_record),)
        else:
            target = unique_records[rng.randrange(len(unique_records))]
            query_kind = QUERY_KIND_UNIQUE
            exact_handles = (target.trace_handle,)
            contract_keys = (contract_key_from_trace(target.trace_record),)
        queries.append(
            StageA1Query(
                query_id=f"{dataset_id}-p{corruption_probability:.2f}-q{offset:04d}",
                trial_seed=seed,
                dataset_id=dataset_id,
                corruption_probability=corruption_probability,
                target_handle=target.trace_handle,
                target_record_id=target.record_id,
                target_contract_key=contract_key_from_trace(target.trace_record),
                target_exact_key=exact_key_from_trace(target.trace_record),
                noisy_payload=corrupt_payload(target.semantic_payload, probability=corruption_probability, seed=seed + 41),
                clean_payload=target.semantic_payload,
                target_payload_checksum=payload_checksum(target.semantic_payload),
                target_operation_family=target.family_label,
                target_arity=target.arity,
                target_namespaces=target.operand_namespaces,
                target_operation_parameters=dict(target.operation_parameters),
                target_parent_handles=target.parent_handles,
                query_kind=query_kind,
                exact_ambiguous_handles=exact_handles,
                contract_ambiguous_keys=contract_keys,
            )
        )
    return queries


def _router_memory_breakdown(router: RandomHyperplaneLSH | RandomBucketRouter | None) -> dict[str, int]:
    if router is None:
        return {
            "projection_matrix_bytes": 0,
            "hash_table_overhead_estimate": 0,
            "posting_bytes": 0,
            "duplicate_postings": 0,
        }
    tables = getattr(router, "_tables", [])
    projection_matrix_bytes = 0
    for projection in getattr(router, "_projections", []):
        projection_matrix_bytes += int(projection.nelement() * projection.element_size())
    posting_bytes = 0
    overhead = 0
    posting_count = 0
    for table in tables:
        overhead += sys.getsizeof(table)
        for signature, handles in table.items():
            posting_count += len(handles)
            overhead += sys.getsizeof(signature) + sys.getsizeof(handles)
            posting_bytes += len(signature.encode("utf-8"))
            posting_bytes += sum(len(handle.encode("utf-8")) for handle in handles)
    return {
        "projection_matrix_bytes": projection_matrix_bytes,
        "hash_table_overhead_estimate": overhead,
        "posting_bytes": posting_bytes,
        "duplicate_postings": max(0, posting_count - len({handle for table in tables for handles in table.values() for handle in handles})),
    }


def _trace_record_bytes(records: list[StageA1Record]) -> int:
    return sum(len(record.trace_record.stable_bytes()) for record in records)


def _build_lsh_router(config: MethodConfig) -> RandomHyperplaneLSH:
    return RandomHyperplaneLSH(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=config.signature_bits,
            table_count=config.table_count,
            table_seed=config.projection_seed,
            probe_budget=config.probe_budget,
            routing_mode=config.routing_mode,
        )
    )


def _build_random_router(config: MethodConfig) -> RandomBucketRouter:
    return RandomBucketRouter(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=config.signature_bits,
            table_count=config.table_count,
            table_seed=config.projection_seed,
            probe_budget=config.probe_budget,
        )
    )


def method_configs() -> dict[str, MethodConfig]:
    return {
        METHOD_STAGE_A_MULTI_TABLE: MethodConfig(
            method_id=METHOD_STAGE_A_MULTI_TABLE,
            signature_bits=12,
            table_count=4,
            probe_budget=1,
            candidate_budget=STAGE_A_LEGACY_CANDIDATE_BUDGET,
            rerank_k=32,
            projection_seed=PROJECTION_SEEDS[0],
            routing_mode="primary_only",
            family="semantic_lsh",
        ),
        METHOD_A1_PRIMARY: MethodConfig(
            method_id=METHOD_A1_PRIMARY,
            signature_bits=12,
            table_count=18,
            probe_budget=1,
            candidate_budget=PRIMARY_CANDIDATE_BUDGET,
            rerank_k=32,
            projection_seed=PROJECTION_SEEDS[0],
            routing_mode="primary_only",
            family="semantic_lsh",
        ),
        METHOD_A1_SECONDARY_1: MethodConfig(
            method_id=METHOD_A1_SECONDARY_1,
            signature_bits=11,
            table_count=15,
            probe_budget=1,
            candidate_budget=PRIMARY_CANDIDATE_BUDGET,
            rerank_k=32,
            projection_seed=PROJECTION_SEEDS[0],
            routing_mode="primary_only",
            family="semantic_lsh",
        ),
        METHOD_A1_SECONDARY_2: MethodConfig(
            method_id=METHOD_A1_SECONDARY_2,
            signature_bits=13,
            table_count=21,
            probe_budget=1,
            candidate_budget=PRIMARY_CANDIDATE_BUDGET,
            rerank_k=32,
            projection_seed=PROJECTION_SEEDS[0],
            routing_mode="primary_only",
            family="semantic_lsh",
        ),
        METHOD_A1_MULTI_PROBE: MethodConfig(
            method_id=METHOD_A1_MULTI_PROBE,
            signature_bits=12,
            table_count=4,
            probe_budget=MARGIN_PROBE_BUDGET,
            candidate_budget=PRIMARY_CANDIDATE_BUDGET,
            rerank_k=32,
            projection_seed=PROJECTION_SEEDS[0],
            routing_mode="margin_probe",
            family="semantic_lsh",
            analytical_model="primary_plus_first_order_neighbor_union_bound",
        ),
    }


def budget_matched_random_configs() -> dict[str, MethodConfig]:
    targets = method_configs()
    configs: dict[str, MethodConfig] = {}
    for target_method in (
        METHOD_STAGE_A_MULTI_TABLE,
        METHOD_A1_PRIMARY,
        METHOD_A1_SECONDARY_1,
        METHOD_A1_SECONDARY_2,
        METHOD_A1_MULTI_PROBE,
    ):
        target = targets[target_method]
        budget = int(
            min(
                PRIMARY_CANDIDATE_BUDGET,
                max(
                    1,
                    math.ceil(
                        expected_random_bucket_occupancy(
                            record_count=10_000,
                            signature_bits=target.signature_bits,
                            table_count=target.table_count,
                            probe_budget=target.probe_budget,
                        )
                    ),
                ),
            )
        )
        configs[target_method] = MethodConfig(
            method_id=METHOD_RANDOM_ROUTING,
            signature_bits=target.signature_bits,
            table_count=target.table_count,
            probe_budget=target.probe_budget,
            candidate_budget=budget,
            rerank_k=32,
            projection_seed=target.projection_seed,
            routing_mode="primary_only",
            family="random_routing",
            budget_match_target=target_method,
        )
    return configs


def _build_runtime_indexes(records: list[StageA1Record]) -> dict[str, list[StageA1Record]]:
    checksum_groups: dict[str, list[StageA1Record]] = {}
    for record in records:
        checksum_groups.setdefault(record.trace_record.semantic_payload_checksum, []).append(record)
    return checksum_groups


def _contract_match(candidate: RerankedCandidate, query: StageA1Query) -> bool:
    return contract_key_from_candidate(candidate) == query.target_contract_key


def _exact_match(candidate: RerankedCandidate, query: StageA1Query) -> bool:
    return exact_key_from_candidate(candidate) == query.target_exact_key


def _ambiguity_detected(candidates: list[RerankedCandidate], query: StageA1Query) -> bool:
    if query.query_kind not in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY}:
        return False
    if len(candidates) < 2:
        return False
    top_similarity = candidates[0].similarity
    conflicting = [
        candidate
        for candidate in candidates
        if abs(candidate.similarity - top_similarity) <= AMBIGUITY_SIMILARITY_EPSILON
        and candidate.semantic_payload_checksum == query.target_payload_checksum
        and candidate.handle in query.exact_ambiguous_handles
    ]
    return len(conflicting) >= 2


def _decoder_contract_decision(
    candidates: list[RerankedCandidate],
    *,
    expansion_available: bool,
) -> TaskDecision:
    valid = [candidate for candidate in candidates if candidate.validation_status == TRACE_VALID]
    if not valid:
        return TaskDecision(
            outcome=OUTCOME_EXPAND if expansion_available else OUTCOME_ABSTAIN,
            accepted_handle=None,
            accepted_contract_key=None,
            accepted_exact_key=None,
            coverage=0,
            wrong_acceptance=0,
        )
    grouped: dict[str, list[RerankedCandidate]] = {}
    for candidate in valid:
        grouped.setdefault(contract_key_from_candidate(candidate), []).append(candidate)
    ranked_groups = sorted(
        ((key, max(group, key=lambda item: item.similarity)) for key, group in grouped.items()),
        key=lambda pair: (-pair[1].similarity, pair[0]),
    )
    top_key, top_candidate = ranked_groups[0]
    second_similarity = ranked_groups[1][1].similarity if len(ranked_groups) > 1 else 0.0
    margin = top_candidate.similarity - second_similarity
    if top_candidate.similarity >= ACCEPT_SIMILARITY_THRESHOLD and margin >= ACCEPT_MARGIN:
        return TaskDecision(
            outcome=OUTCOME_ACCEPT,
            accepted_handle=top_candidate.handle,
            accepted_contract_key=top_key,
            accepted_exact_key=exact_key_from_candidate(top_candidate),
            coverage=1,
            wrong_acceptance=0,
        )
    return TaskDecision(
        outcome=OUTCOME_EXPAND if expansion_available else OUTCOME_ABSTAIN,
        accepted_handle=None,
        accepted_contract_key=None,
        accepted_exact_key=None,
        coverage=0,
        wrong_acceptance=0,
    )


def _exact_trace_decision(
    candidates: list[RerankedCandidate],
    query: StageA1Query,
    *,
    expansion_available: bool,
) -> TaskDecision:
    valid = [candidate for candidate in candidates if candidate.validation_status == TRACE_VALID]
    if not valid:
        return TaskDecision(
            outcome=OUTCOME_EXPAND if expansion_available else OUTCOME_ABSTAIN,
            accepted_handle=None,
            accepted_contract_key=None,
            accepted_exact_key=None,
            coverage=0,
            wrong_acceptance=0,
        )
    if _ambiguity_detected(valid, query):
        return TaskDecision(
            outcome=OUTCOME_AMBIGUOUS_TRACE,
            accepted_handle=None,
            accepted_contract_key=None,
            accepted_exact_key=None,
            coverage=0,
            wrong_acceptance=0,
        )
    top = valid[0]
    second_similarity = valid[1].similarity if len(valid) > 1 else 0.0
    margin = top.similarity - second_similarity
    if top.similarity >= ACCEPT_SIMILARITY_THRESHOLD and margin >= ACCEPT_MARGIN:
        return TaskDecision(
            outcome=OUTCOME_ACCEPT,
            accepted_handle=top.handle,
            accepted_contract_key=contract_key_from_candidate(top),
            accepted_exact_key=exact_key_from_candidate(top),
            coverage=1,
            wrong_acceptance=0,
        )
    return TaskDecision(
        outcome=OUTCOME_EXPAND if expansion_available else OUTCOME_ABSTAIN,
        accepted_handle=None,
        accepted_contract_key=None,
        accepted_exact_key=None,
        coverage=0,
        wrong_acceptance=0,
    )


def _global_scan(
    index: TraceIndex,
    query: StageA1Query,
    *,
    rerank_k: int,
) -> tuple[RoutingResult, list[RerankedCandidate], float, float]:
    start = time.perf_counter()
    entries = index.committed_entries()
    payload_matrix = index.committed_payload_matrix()
    routing = RoutingResult(
        candidate_handles=tuple(index.committed_handles()),
        primary_signatures=("GLOBAL_SCAN",),
        probed_signatures=("GLOBAL_SCAN",),
        expansion_used=False,
        duplicate_postings=0,
        empty_primary_bucket=False,
        raw_postings_retrieved=len(entries),
        probed_table_indices=(0,),
        probe_margins=(0.0,),
    )
    routing_latency = time.perf_counter() - start
    reranked, reranking_latency = rerank_candidates(
        query.noisy_payload,
        entries,
        candidate_matrix=payload_matrix,
        top_k=rerank_k,
    )
    return routing, reranked, routing_latency, reranking_latency


def _route_with_method(
    *,
    method_id: str,
    query: StageA1Query,
    index: TraceIndex,
    lsh_router: RandomHyperplaneLSH | None,
    random_router: RandomBucketRouter | None,
    candidate_budget: int,
    rerank_k: int,
) -> tuple[RoutingResult, list[RerankedCandidate], float, float]:
    if method_id == METHOD_GLOBAL_SCAN:
        return _global_scan(index, query, rerank_k=rerank_k)
    if method_id == METHOD_EXACT_HASH:
        start = time.perf_counter()
        matched = index.exact_lookup(query.noisy_payload)
        routing_latency = time.perf_counter() - start
        entries = [entry for handle in matched for entry in [index.get(handle)] if entry is not None]
        routing = RoutingResult(
            candidate_handles=matched,
            primary_signatures=("EXACT_HASH",),
            probed_signatures=("EXACT_HASH",),
            expansion_used=False,
            duplicate_postings=0,
            empty_primary_bucket=(len(matched) == 0),
            raw_postings_retrieved=len(entries),
            probed_table_indices=(0,),
            probe_margins=(0.0,),
        )
        reranked, reranking_latency = rerank_candidates(query.noisy_payload, entries)
        return routing, reranked, routing_latency, reranking_latency
    if method_id == METHOD_RANDOM_ROUTING:
        assert random_router is not None
        start = time.perf_counter()
        routing = random_router.route(query_key=query.query_id, candidate_budget=candidate_budget)
        routing_latency = time.perf_counter() - start
        entries = [entry for handle in routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
        reranked, reranking_latency = rerank_candidates(query.noisy_payload, entries)
        return routing, reranked, routing_latency, reranking_latency
    assert lsh_router is not None
    start = time.perf_counter()
    routing = lsh_router.route(query.noisy_payload, candidate_budget=candidate_budget)
    routing_latency = time.perf_counter() - start
    entries = [entry for handle in routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
    reranked, reranking_latency = rerank_candidates(query.noisy_payload, entries)
    return routing, reranked, routing_latency, reranking_latency


def run_query(
    *,
    method_id: str,
    config_id: str,
    query: StageA1Query,
    index: TraceIndex,
    router: RandomHyperplaneLSH | None,
    random_router: RandomBucketRouter | None,
    candidate_budget: int,
    rerank_k: int,
) -> dict[str, Any]:
    routing, reranked, routing_latency, reranking_latency = _route_with_method(
        method_id=method_id,
        query=query,
        index=index,
        lsh_router=router,
        random_router=random_router,
        candidate_budget=candidate_budget,
        rerank_k=rerank_k,
    )
    top_candidates = reranked[:rerank_k]
    expansion_available = method_id in {
        METHOD_RANDOM_ROUTING,
        METHOD_STAGE_A_MULTI_TABLE,
        METHOD_A1_PRIMARY,
        METHOD_A1_SECONDARY_1,
        METHOD_A1_SECONDARY_2,
        METHOD_A1_MULTI_PROBE,
    }
    decoder_decision = _decoder_contract_decision(top_candidates, expansion_available=expansion_available)
    exact_decision = _exact_trace_decision(top_candidates, query, expansion_available=expansion_available)
    top1 = top_candidates[0] if top_candidates else None
    decoder_top1_correct = bool(top1 is not None and _contract_match(top1, query))
    exact_top1_correct = bool(top1 is not None and _exact_match(top1, query))
    decoder_accepted_wrong = int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key != query.target_contract_key)
    exact_accepted_wrong = int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle != query.target_handle)
    ambiguous_wrong_acceptance = int(
        query.query_kind in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY}
        and exact_decision.outcome == OUTCOME_ACCEPT
    )
    unique_candidates = len(routing.candidate_handles)
    similarity_scored = len(index.committed_handles()) if method_id == METHOD_GLOBAL_SCAN else unique_candidates
    return {
        "schema_version": STAGE_A1_SCHEMA_VERSION,
        "method_id": method_id,
        "config_id": config_id,
        "query_id": query.query_id,
        "dataset_id": query.dataset_id,
        "corruption_probability": query.corruption_probability,
        "corruption_channel_id": CORRUPTION_CHANNEL_ID,
        "query_kind": query.query_kind,
        "target_handle": query.target_handle,
        "target_contract_key": query.target_contract_key,
        "target_exact_key": query.target_exact_key,
        "decoder_contract_recall_at_1": int(any(_contract_match(candidate, query) for candidate in top_candidates[:1])),
        "decoder_contract_recall_at_8": int(any(_contract_match(candidate, query) for candidate in top_candidates[:8])),
        "decoder_contract_recall_at_32": int(any(_contract_match(candidate, query) for candidate in top_candidates[:32])),
        "decoder_contract_top1_accuracy": int(decoder_top1_correct),
        "exact_trace_recall_at_1": int(any(_exact_match(candidate, query) for candidate in top_candidates[:1])),
        "exact_trace_recall_at_8": int(any(_exact_match(candidate, query) for candidate in top_candidates[:8])),
        "exact_trace_recall_at_32": int(any(_exact_match(candidate, query) for candidate in top_candidates[:32])),
        "exact_trace_top1_accuracy": int(exact_top1_correct),
        "decoder_contract_outcome": decoder_decision.outcome,
        "decoder_contract_acceptance_coverage": decoder_decision.coverage,
        "decoder_contract_accepted_correct": int(decoder_decision.outcome == OUTCOME_ACCEPT and decoder_decision.accepted_contract_key == query.target_contract_key),
        "decoder_contract_accepted_wrong": decoder_accepted_wrong,
        "decoder_contract_conditional_risk_denominator": int(decoder_decision.outcome == OUTCOME_ACCEPT),
        "exact_trace_outcome": exact_decision.outcome,
        "exact_trace_acceptance_coverage": exact_decision.coverage,
        "exact_trace_accepted_correct": int(exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle == query.target_handle),
        "exact_trace_accepted_wrong": exact_accepted_wrong,
        "exact_trace_conditional_risk_denominator": int(exact_decision.outcome == OUTCOME_ACCEPT),
        "ambiguity_detected": int(exact_decision.outcome == OUTCOME_AMBIGUOUS_TRACE),
        "ambiguous_wrong_acceptance": ambiguous_wrong_acceptance,
        "ambiguous_abstention": int(query.query_kind in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY} and exact_decision.outcome in {OUTCOME_ABSTAIN, OUTCOME_EXPAND, OUTCOME_AMBIGUOUS_TRACE}),
        "ambiguous_candidate_multiplicity": len(query.exact_ambiguous_handles) if query.query_kind in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY} else 0,
        "candidate_set_size": unique_candidates,
        "raw_postings_retrieved": routing.raw_postings_retrieved,
        "unique_candidates_after_dedup": unique_candidates,
        "candidates_actually_reranked": similarity_scored,
        "validated_topk_count": len(top_candidates),
        "candidate_reduction_ratio": 1.0 - (unique_candidates / max(1, len(index.committed_handles()))),
        "duplicate_postings": routing.duplicate_postings,
        "duplicate_posting_rate": routing.duplicate_postings / max(1, routing.raw_postings_retrieved),
        "routing_latency_sec": routing_latency,
        "reranking_latency_sec": reranking_latency,
        "total_query_latency_sec": routing_latency + reranking_latency,
        "operation_family_accuracy": int(top1 is not None and top1.operation_family == query.target_operation_family),
        "arity_accuracy": int(top1 is not None and top1.arity == query.target_arity),
        "namespace_contract_accuracy": int(top1 is not None and top1.operand_namespaces == query.target_namespaces),
        "top1_similarity": float(top1.similarity) if top1 is not None else None,
        "top2_similarity": float(top_candidates[1].similarity) if len(top_candidates) > 1 else None,
        "exact_hash_hit": int(method_id == METHOD_EXACT_HASH and len(routing.candidate_handles) > 0),
        "empty_primary_bucket": int(routing.empty_primary_bucket),
        "expansion_used": int(routing.expansion_used),
        "probed_bucket_count": len(routing.probed_signatures),
        "verified_correct_trace_retrieval_per_candidate": (1.0 / max(1, unique_candidates)) if exact_decision.outcome == OUTCOME_ACCEPT and exact_decision.accepted_handle == query.target_handle else 0.0,
        "expected_decoder_family_invocations_avoided": len(index.committed_handles()) - unique_candidates,
    }


def _aggregate_task_summary(
    rows: list[dict[str, Any]],
    *,
    task_prefix: str,
    record_count: int,
    subset: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["method_id"], row["config_id"], row["corruption_probability"], subset)
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        recall_successes = sum(row[f"{task_prefix}_recall_at_32"] for row in batch)
        ci_low, ci_high = wilson_interval(recall_successes, len(batch))
        accepted = sum(row[f"{task_prefix}_accepted_correct"] + row[f"{task_prefix}_accepted_wrong"] for row in batch)
        wrong = sum(row[f"{task_prefix}_accepted_wrong"] for row in batch)
        summary.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "method_id": key[0],
                "config_id": key[1],
                "corruption_probability": key[2],
                "query_subset": key[3],
                "trials": len(batch),
                f"{task_prefix}_recall_at_1": statistics.mean(row[f"{task_prefix}_recall_at_1"] for row in batch),
                f"{task_prefix}_recall_at_8": statistics.mean(row[f"{task_prefix}_recall_at_8"] for row in batch),
                f"{task_prefix}_recall_at_32": statistics.mean(row[f"{task_prefix}_recall_at_32"] for row in batch),
                f"{task_prefix}_recall_at_32_ci_low": ci_low,
                f"{task_prefix}_recall_at_32_ci_high": ci_high,
                f"{task_prefix}_top1_accuracy": statistics.mean(row[f"{task_prefix}_top1_accuracy"] for row in batch),
                f"{task_prefix}_acceptance_coverage": statistics.mean(row[f"{task_prefix}_acceptance_coverage"] for row in batch),
                f"{task_prefix}_conditional_risk": wrong / accepted if accepted else 0.0,
                "candidate_set_size_median": statistics.median(row["candidate_set_size"] for row in batch),
                "candidate_set_size_p95": quantile([row["candidate_set_size"] for row in batch], 0.95),
                "candidate_reduction_ratio": 1.0 - (statistics.mean(row["candidate_set_size"] for row in batch) / record_count),
                "routing_latency_sec_p50": statistics.median(row["routing_latency_sec"] for row in batch),
                "routing_latency_sec_p95": quantile([row["routing_latency_sec"] for row in batch], 0.95),
                "routing_latency_sec_p99": quantile([row["routing_latency_sec"] for row in batch], 0.99),
                "reranking_latency_sec_p50": statistics.median(row["reranking_latency_sec"] for row in batch),
                "total_query_latency_sec_p50": statistics.median(row["total_query_latency_sec"] for row in batch),
                "total_query_latency_sec_p95": quantile([row["total_query_latency_sec"] for row in batch], 0.95),
                "total_query_latency_sec_p99": quantile([row["total_query_latency_sec"] for row in batch], 0.99),
            }
        )
    return summary


def _query_subset(rows: list[dict[str, Any]], subset: str) -> list[dict[str, Any]]:
    if subset == "all":
        return rows
    if subset == "non_ambiguous_contract":
        return [row for row in rows if row["query_kind"] in {QUERY_KIND_UNIQUE, QUERY_KIND_NEAR_CONFLICT, QUERY_KIND_EXACT_AMBIGUITY}]
    if subset == "ambiguous_only":
        return [row for row in rows if row["query_kind"] in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY}]
    raise ValueError(f"Unsupported subset: {subset}")


def summarize_trials(rows: list[dict[str, Any]], *, record_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    overall: list[dict[str, Any]] = []
    contract_rows: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    for subset in ("all", "non_ambiguous_contract", "ambiguous_only"):
        subset_rows = _query_subset(rows, subset)
        if not subset_rows:
            continue
        contract_rows.extend(_aggregate_task_summary(subset_rows, task_prefix="decoder_contract", record_count=record_count, subset=subset))
        exact_rows.extend(_aggregate_task_summary(subset_rows, task_prefix="exact_trace", record_count=record_count, subset=subset))
    by_key = {(row["method_id"], row["config_id"], row["corruption_probability"], row["query_subset"]): row for row in contract_rows}
    for key, contract_row in by_key.items():
        exact_row = next(
            row for row in exact_rows
            if (row["method_id"], row["config_id"], row["corruption_probability"], row["query_subset"]) == key
        )
        overall.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "method_id": key[0],
                "config_id": key[1],
                "corruption_probability": key[2],
                "query_subset": key[3],
                "decoder_contract_recall_at_32": contract_row["decoder_contract_recall_at_32"],
                "decoder_contract_acceptance_coverage": contract_row["decoder_contract_acceptance_coverage"],
                "exact_trace_recall_at_32": exact_row["exact_trace_recall_at_32"],
                "exact_trace_acceptance_coverage": exact_row["exact_trace_acceptance_coverage"],
                "candidate_set_size_median": contract_row["candidate_set_size_median"],
                "candidate_set_size_p95": contract_row["candidate_set_size_p95"],
                "candidate_reduction_ratio": contract_row["candidate_reduction_ratio"],
                "total_query_latency_sec_p50": contract_row["total_query_latency_sec_p50"],
                "total_query_latency_sec_p95": contract_row["total_query_latency_sec_p95"],
                "total_query_latency_sec_p99": contract_row["total_query_latency_sec_p99"],
            }
        )
    return overall, contract_rows, exact_rows


def summarize_ambiguity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = {}
    for row in rows:
        if row["query_kind"] not in {QUERY_KIND_EXACT_AMBIGUITY, QUERY_KIND_CONTRACT_AMBIGUITY}:
            continue
        key = (row["method_id"], row["config_id"], row["corruption_probability"])
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for key, batch in sorted(grouped.items()):
        summary.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "method_id": key[0],
                "config_id": key[1],
                "corruption_probability": key[2],
                "trials": len(batch),
                "ambiguity_detection_rate": statistics.mean(row["ambiguity_detected"] for row in batch),
                "ambiguous_wrong_acceptance_rate": statistics.mean(row["ambiguous_wrong_acceptance"] for row in batch),
                "ambiguous_abstention_rate": statistics.mean(row["ambiguous_abstention"] for row in batch),
                "ambiguous_candidate_multiplicity": statistics.mean(row["ambiguous_candidate_multiplicity"] for row in batch),
            }
        )
    return summary


def build_protocol(repo_root: Path) -> dict[str, Any]:
    router_configs = method_configs()
    random_configs = budget_matched_random_configs()
    preserved = {
        "semantic_substrate": {"vsa": "MAP", "dimensions": MAP_DIMENSIONS},
        "corruption_channel": {
            "channel_id": CORRUPTION_CHANNEL_ID,
            "type": "independent_external_bernoulli_sign_flip",
            "points": list(QUERY_CORRUPTION_POINTS_A1),
        },
        "stage_a_artifact_hash": STAGE_A_PROTOCOL_HASH,
    }
    payload = {
        "schema_version": STAGE_A1_SCHEMA_VERSION,
        "task_name": STAGE_A1_TASK_NAME,
        "base_checkpoint_commit": STAGE_A1_BASE_CHECKPOINT_COMMIT,
        "results_namespace": STAGE_A1_NAMESPACE,
        "protocol_amendment_of": STAGE_A_PROTOCOL_HASH,
        "branch_expectation": STAGE_A1_BRANCH_EXPECTATION,
        "allowed_change_classes": list(ALLOWED_CHANGE_CLASSES),
        "preserved_fields": preserved,
        "changed_fields": {
            "analytical_lsh_configs": ["A1-P", "A1-S1", "A1-S2", "A1-MP"],
            "query_trials_per_primary_point": 512,
            "task_split": ["decoder_contract_retrieval", "exact_creation_trace_retrieval"],
            "ambiguity_contract": OUTCOME_AMBIGUOUS_TRACE,
            "vectorized_global_scan": True,
        },
        "dataset_specs": list(DATASET_SPECS),
        "dataset_seed_ranges": DATASET_SEED_RANGES,
        "query_seed_ranges": QUERY_SEED_RANGES,
        "projection_seeds": list(PROJECTION_SEEDS),
        "smoke_seed": SMOKE_SEED,
        "methods": {
            method_id: asdict(config)
            for method_id, config in {**router_configs, **{f"random::{key}": value for key, value in random_configs.items()}}.items()
        },
        "random_budget_matching": {
            target: {
                "candidate_budget": config.candidate_budget,
                "signature_bits": config.signature_bits,
                "table_count": config.table_count,
                "probe_budget": config.probe_budget,
            }
            for target, config in random_configs.items()
        },
        "fixed_acceptance_policy": {
            "rerank_k": RERANK_K,
            "accept_similarity_threshold": ACCEPT_SIMILARITY_THRESHOLD,
            "accept_margin": ACCEPT_MARGIN,
            "coverage_threshold_primary": PRIMARY_COVERAGE_THRESHOLD,
            "theory_tolerance_absolute": THEORY_TOLERANCE,
        },
        "global_scan_policy": {
            "warmup_queries": GLOBAL_SCAN_WARMUP_QUERIES,
            "timed_repeats_per_query": GLOBAL_SCAN_TIMED_REPEATS,
            "topk_only_validation": RERANK_K,
        },
        "no_overlap_with_prior_frozen_seeds": seeds_are_fresh(repo_root),
        "heldout_execution": False,
        "stage_a_artifacts_unchanged": _stage_a_protocol_hash(repo_root) == STAGE_A_PROTOCOL_HASH,
    }
    payload["protocol_hash"] = canonical_json_hash(payload)
    return payload


def _stage_a_protocol_hash(repo_root: Path) -> str:
    path = repo_root / "results" / "lazy_trace_stage_a" / "development_protocol.json"
    return canonical_sha256(path)


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": STAGE_A1_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "numpy_version": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": "cpu",
        "torch_num_threads": torch.get_num_threads(),
        "branch_expectation": STAGE_A1_BRANCH_EXPECTATION,
        "global_scan_batching": "single-query vectorized cosine over contiguous payload matrix; top-k materialization only",
    }


def _warmup(
    *,
    queries: list[StageA1Query],
    index: TraceIndex,
    router_configs: dict[str, MethodConfig],
    routers: dict[str, RandomHyperplaneLSH],
    random_routers: dict[str, RandomBucketRouter],
) -> None:
    for query in queries[:GLOBAL_SCAN_WARMUP_QUERIES]:
        run_query(
            method_id=METHOD_GLOBAL_SCAN,
            config_id=METHOD_GLOBAL_SCAN,
            query=query,
            index=index,
            router=None,
            random_router=None,
            candidate_budget=len(index.committed_handles()),
            rerank_k=RERANK_K,
        )
        run_query(
            method_id=METHOD_EXACT_HASH,
            config_id=METHOD_EXACT_HASH,
            query=query,
            index=index,
            router=None,
            random_router=None,
            candidate_budget=0,
            rerank_k=RERANK_K,
        )
        for method_id, config in router_configs.items():
            run_query(
                method_id=method_id,
                config_id=method_id,
                query=query,
                index=index,
                router=routers[method_id],
                random_router=None,
                candidate_budget=config.candidate_budget,
                rerank_k=config.rerank_k,
            )
        for target_method, config in budget_matched_random_configs().items():
            run_query(
                method_id=METHOD_RANDOM_ROUTING,
                config_id=f"{METHOD_RANDOM_ROUTING}::{target_method}",
                query=query,
                index=index,
                router=None,
                random_router=random_routers[target_method],
                candidate_budget=config.candidate_budget,
                rerank_k=config.rerank_k,
            )


def _projection_seed_ablation(
    *,
    method_config: MethodConfig,
    index: TraceIndex,
    queries: list[StageA1Query],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for projection_seed in PROJECTION_SEEDS:
        config = MethodConfig(**{**asdict(method_config), "projection_seed": projection_seed})
        router = _build_lsh_router(config)
        router.fit(index.committed_payloads())
        hits = 0
        for query in queries:
            row = run_query(
                method_id=config.method_id,
                config_id=f"{config.method_id}::projection_seed_{projection_seed}",
                query=query,
                index=index,
                router=router,
                random_router=None,
                candidate_budget=config.candidate_budget,
                rerank_k=config.rerank_k,
            )
            hits += row["decoder_contract_recall_at_32"]
        rows.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "ablation_id": "A9_different_fixed_projection_seeds",
                "method_id": config.method_id,
                "projection_seed": projection_seed,
                "decoder_contract_recall_at_32": hits / len(queries),
            }
        )
    return rows


def _mutate_records_for_exact_trace_shuffle(records: list[StageA1Record]) -> list[StageA1Record]:
    grouped: dict[str, list[StageA1Record]] = {}
    for record in records:
        grouped.setdefault(contract_key_from_trace(record.trace_record), []).append(record)
    shuffled: list[StageA1Record] = []
    for group in grouped.values():
        if len(group) == 1:
            shuffled.append(group[0])
            continue
        rotated = group[1:] + group[:1]
        for original, donor in zip(group, rotated, strict=True):
            shuffled.append(
                _clone_record(
                    source=original,
                    record_ordinal=len(shuffled),
                    operation_family=original.family_label,
                    arity=original.arity,
                    operand_namespaces=original.operand_namespaces,
                    operation_parameters=original.operation_parameters,
                    parent_handles=donor.parent_handles,
                    ambiguity_kind=original.ambiguity_kind,
                    adversarial_group=original.adversarial_group,
                )
            )
    return shuffled


def _mutate_records_for_contract_shuffle(records: list[StageA1Record]) -> list[StageA1Record]:
    rotated = records[1:] + records[:1]
    shuffled: list[StageA1Record] = []
    for original, donor in zip(records, rotated, strict=True):
        shuffled.append(
            _clone_record(
                source=original,
                record_ordinal=len(shuffled),
                operation_family=donor.family_label,
                arity=donor.arity,
                operand_namespaces=donor.operand_namespaces,
                operation_parameters=donor.operation_parameters,
                parent_handles=donor.parent_handles,
                ambiguity_kind=original.ambiguity_kind,
                adversarial_group=original.adversarial_group,
            )
        )
    return shuffled


def _mutate_records_for_parent_shuffle(records: list[StageA1Record]) -> list[StageA1Record]:
    rotated_parents = [record.parent_handles for record in records[1:]] + [records[0].parent_handles]
    shuffled: list[StageA1Record] = []
    for original, parents in zip(records, rotated_parents, strict=True):
        shuffled.append(
            _clone_record(
                source=original,
                record_ordinal=len(shuffled),
                parent_handles=parents,
                ambiguity_kind=original.ambiguity_kind,
                adversarial_group=original.adversarial_group,
            )
        )
    return shuffled


def _run_ablation_rows(
    *,
    records: list[StageA1Record],
    queries: list[StageA1Query],
    method_config: MethodConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ablation_id, mutate in (
        ("A6_semantic_to_exact_trace_shuffle", _mutate_records_for_exact_trace_shuffle),
        ("A7_semantic_to_contract_shuffle", _mutate_records_for_contract_shuffle),
        ("A15_parent_handle_shuffle", _mutate_records_for_parent_shuffle),
    ):
        mutated_records = mutate(records)
        mutated_index = build_trace_index(mutated_records)
        router = _build_lsh_router(method_config)
        router.fit(mutated_index.committed_payloads())
        trial_rows = [
            run_query(
                method_id=method_config.method_id,
                config_id=f"{method_config.method_id}::{ablation_id}",
                query=query,
                index=mutated_index,
                router=router,
                random_router=None,
                candidate_budget=method_config.candidate_budget,
                rerank_k=method_config.rerank_k,
            )
            for query in queries
        ]
        rows.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "ablation_id": ablation_id,
                "method_id": method_config.method_id,
                "decoder_contract_recall_at_32": statistics.mean(row["decoder_contract_recall_at_32"] for row in trial_rows),
                "exact_trace_recall_at_32": statistics.mean(row["exact_trace_recall_at_32"] for row in trial_rows),
                "decoder_contract_conditional_risk": (
                    sum(row["decoder_contract_accepted_wrong"] for row in trial_rows)
                    / max(1, sum(row["decoder_contract_conditional_risk_denominator"] for row in trial_rows))
                ),
                "exact_trace_conditional_risk": (
                    sum(row["exact_trace_accepted_wrong"] for row in trial_rows)
                    / max(1, sum(row["exact_trace_conditional_risk_denominator"] for row in trial_rows))
                ),
            }
        )
    return rows


def run_stage_a1(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / STAGE_A1_NAMESPACE
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol = build_protocol(repo_root)
    environment = environment_snapshot()
    write_json(results_dir / "development_protocol.json", protocol)
    write_json(results_dir / "environment.json", environment)

    dataset_manifest_rows: list[dict[str, Any]] = []
    query_manifest_rows: list[dict[str, Any]] = []
    trial_rows: list[dict[str, Any]] = []
    theory_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    analysis_rows: list[dict[str, Any]] = []

    router_configs = method_configs()
    random_configs = budget_matched_random_configs()

    for dataset_spec in DATASET_SPECS:
        dataset_id = dataset_spec["dataset_id"]
        dataset_seed = DATASET_SEED_RANGES[dataset_id]["start"]
        records = build_dataset(dataset_seed=dataset_seed, record_count=dataset_spec["record_count"])
        index = build_trace_index(records)
        dataset_manifest_rows.append(
            {
                "schema_version": STAGE_A1_SCHEMA_VERSION,
                "dataset_id": dataset_id,
                "dataset_seed": dataset_seed,
                "record_count": len(records),
                "exact_ambiguity_records": sum(1 for record in records if record.ambiguity_kind == QUERY_KIND_EXACT_AMBIGUITY),
                "contract_ambiguity_records": sum(1 for record in records if record.ambiguity_kind == QUERY_KIND_CONTRACT_AMBIGUITY),
                "near_conflict_records": sum(1 for record in records if record.ambiguity_kind is None and record.adversarial_group is not None),
            }
        )

        routers: dict[str, RandomHyperplaneLSH] = {}
        router_memory: dict[str, dict[str, int]] = {}
        build_latency_lookup: dict[str, float] = {}
        for method_id, config in router_configs.items():
            start = time.perf_counter()
            router = _build_lsh_router(config)
            router.fit(index.committed_payloads())
            build_latency_lookup[method_id] = time.perf_counter() - start
            routers[method_id] = router
            router_memory[method_id] = _router_memory_breakdown(router)

        random_routers: dict[str, RandomBucketRouter] = {}
        for target_method, config in random_configs.items():
            start = time.perf_counter()
            router = _build_random_router(config)
            router.fit(index.committed_handles())
            build_latency_lookup[f"{METHOD_RANDOM_ROUTING}::{target_method}"] = time.perf_counter() - start
            random_routers[target_method] = router
            router_memory[f"{METHOD_RANDOM_ROUTING}::{target_method}"] = _router_memory_breakdown(router)

        for probability in QUERY_CORRUPTION_POINTS_A1:
            seed_spec = QUERY_SEED_RANGES[dataset_id][f"{probability:.2f}"]
            queries = build_queries(
                dataset_id=dataset_id,
                records=records,
                query_seed_start=seed_spec["start"],
                query_count=seed_spec["count"],
                corruption_probability=probability,
            )
            if probability == QUERY_CORRUPTION_POINTS_A1[0]:
                _warmup(
                    queries=queries,
                    index=index,
                    router_configs=router_configs,
                    routers=routers,
                    random_routers=random_routers,
                )
            for query in queries:
                query_manifest_rows.append(
                    {
                        "schema_version": STAGE_A1_SCHEMA_VERSION,
                        "query_id": query.query_id,
                        "trial_seed": query.trial_seed,
                        "dataset_id": dataset_id,
                        "corruption_probability": probability,
                        "query_kind": query.query_kind,
                        "target_handle": query.target_handle,
                    }
                )
                trial_rows.append(
                    run_query(
                        method_id=METHOD_GLOBAL_SCAN,
                        config_id=METHOD_GLOBAL_SCAN,
                        query=query,
                        index=index,
                        router=None,
                        random_router=None,
                        candidate_budget=len(index.committed_handles()),
                        rerank_k=RERANK_K,
                    )
                )
                trial_rows.append(
                    run_query(
                        method_id=METHOD_EXACT_HASH,
                        config_id=METHOD_EXACT_HASH,
                        query=query,
                        index=index,
                        router=None,
                        random_router=None,
                        candidate_budget=0,
                        rerank_k=RERANK_K,
                    )
                )
                for method_id, config in router_configs.items():
                    trial_rows.append(
                        run_query(
                            method_id=method_id,
                            config_id=method_id,
                            query=query,
                            index=index,
                            router=routers[method_id],
                            random_router=None,
                            candidate_budget=config.candidate_budget,
                            rerank_k=config.rerank_k,
                        )
                    )
                for target_method, config in random_configs.items():
                    trial_rows.append(
                        run_query(
                            method_id=METHOD_RANDOM_ROUTING,
                            config_id=f"{METHOD_RANDOM_ROUTING}::{target_method}",
                            query=query,
                            index=index,
                            router=None,
                            random_router=random_routers[target_method],
                            candidate_budget=config.candidate_budget,
                            rerank_k=config.rerank_k,
                        )
                    )

            for method_id, config in router_configs.items():
                theory_rows.append(
                    {
                        "schema_version": STAGE_A1_SCHEMA_VERSION,
                        "method_id": method_id,
                        "config_id": method_id,
                        "corruption_probability": probability,
                        "expected_query_similarity": expected_query_similarity(probability),
                        "expected_single_bit_collision_probability": expected_single_bit_collision_probability(probability),
                        "expected_single_table_hit_probability": expected_single_table_hit_probability(
                            signature_bits=config.signature_bits,
                            probability=probability,
                            probe_budget=config.probe_budget,
                            routing_mode=config.routing_mode,
                        ),
                        "expected_any_table_hit_probability": expected_any_table_hit_probability(
                            signature_bits=config.signature_bits,
                            table_count=config.table_count,
                            probability=probability,
                            probe_budget=config.probe_budget,
                            routing_mode=config.routing_mode,
                        ),
                        "expected_random_bucket_occupancy": expected_random_bucket_occupancy(
                            record_count=len(records),
                            signature_bits=config.signature_bits,
                            table_count=config.table_count,
                            probe_budget=config.probe_budget,
                        ),
                        "observed_recall": statistics.mean(
                            row["decoder_contract_recall_at_32"]
                            for row in trial_rows
                            if row["method_id"] == method_id and row["config_id"] == method_id and row["corruption_probability"] == probability and row["query_kind"] in {QUERY_KIND_UNIQUE, QUERY_KIND_NEAR_CONFLICT, QUERY_KIND_EXACT_AMBIGUITY}
                        ),
                        "observed_candidate_count": statistics.mean(
                            row["candidate_set_size"]
                            for row in trial_rows
                            if row["method_id"] == method_id and row["config_id"] == method_id and row["corruption_probability"] == probability and row["query_kind"] in {QUERY_KIND_UNIQUE, QUERY_KIND_NEAR_CONFLICT, QUERY_KIND_EXACT_AMBIGUITY}
                        ),
                        "observed_collision_count": statistics.mean(
                            row["duplicate_postings"]
                            for row in trial_rows
                            if row["method_id"] == method_id and row["config_id"] == method_id and row["corruption_probability"] == probability
                        ),
                    }
                )

        p005_queries = [
            query for query in build_queries(
                dataset_id=dataset_id,
                records=records,
                query_seed_start=QUERY_SEED_RANGES[dataset_id]["0.05"]["start"],
                query_count=64,
                corruption_probability=0.05,
            )
        ]
        ablation_rows.extend(_projection_seed_ablation(method_config=router_configs[METHOD_A1_PRIMARY], index=index, queries=p005_queries))
        ablation_rows.extend(_run_ablation_rows(records=records, queries=p005_queries, method_config=router_configs[METHOD_A1_PRIMARY]))

        payload_bytes = index.payload_memory_bytes()
        trace_bytes = _trace_record_bytes(records)
        for method_id, config in router_configs.items():
            breakdown = router_memory[method_id]
            analysis_rows.append(
                {
                    "schema_version": STAGE_A1_SCHEMA_VERSION,
                    "method_id": method_id,
                    "projection_matrix_bytes": breakdown["projection_matrix_bytes"],
                    "hash_table_overhead_estimate": breakdown["hash_table_overhead_estimate"],
                    "posting_bytes": breakdown["posting_bytes"],
                    "duplicate_postings": breakdown["duplicate_postings"],
                    "semantic_payload_bytes": payload_bytes,
                    "trace_record_bytes": trace_bytes,
                    "total_index_bytes": breakdown["projection_matrix_bytes"] + breakdown["hash_table_overhead_estimate"] + breakdown["posting_bytes"] + payload_bytes + trace_bytes,
                    "bytes_per_stored_semantic_record": (breakdown["projection_matrix_bytes"] + breakdown["hash_table_overhead_estimate"] + breakdown["posting_bytes"] + payload_bytes + trace_bytes) / len(records),
                    "index_build_latency_sec": build_latency_lookup[method_id],
                }
            )

    summary_rows, contract_summary_rows, exact_summary_rows = summarize_trials(trial_rows, record_count=10_000)
    ambiguity_summary_rows = summarize_ambiguity(trial_rows)

    p005_primary_contract = next(
        row for row in contract_summary_rows
        if row["method_id"] == METHOD_A1_PRIMARY and row["config_id"] == METHOD_A1_PRIMARY and row["corruption_probability"] == 0.05 and row["query_subset"] == "non_ambiguous_contract"
    )
    p005_primary_exact = next(
        row for row in exact_summary_rows
        if row["method_id"] == METHOD_A1_PRIMARY and row["config_id"] == METHOD_A1_PRIMARY and row["corruption_probability"] == 0.05 and row["query_subset"] == "non_ambiguous_contract"
    )
    p005_primary_ambiguity = next(
        row for row in ambiguity_summary_rows
        if row["method_id"] == METHOD_A1_PRIMARY and row["config_id"] == METHOD_A1_PRIMARY and row["corruption_probability"] == 0.05
    )
    p005_random = next(
        row for row in contract_summary_rows
        if row["method_id"] == METHOD_RANDOM_ROUTING and row["config_id"] == f"{METHOD_RANDOM_ROUTING}::{METHOD_A1_PRIMARY}" and row["corruption_probability"] == 0.05 and row["query_subset"] == "non_ambiguous_contract"
    )
    p005_theory = next(
        row for row in theory_rows
        if row["method_id"] == METHOD_A1_PRIMARY and row["config_id"] == METHOD_A1_PRIMARY and row["corruption_probability"] == 0.05
    )
    p005_global = next(
        row for row in contract_summary_rows
        if row["method_id"] == METHOD_GLOBAL_SCAN and row["config_id"] == METHOD_GLOBAL_SCAN and row["corruption_probability"] == 0.05 and row["query_subset"] == "non_ambiguous_contract"
    )

    gates = [
        {
            "gate_id": "routing_gate_decoder_contract_recall_at_32",
            "status": "PASS" if p005_primary_contract["decoder_contract_recall_at_32"] >= 0.95 else "FAIL",
            "value": p005_primary_contract["decoder_contract_recall_at_32"],
            "threshold": 0.95,
        },
        {
            "gate_id": "candidate_gate_median_le_100",
            "status": "PASS" if p005_primary_contract["candidate_set_size_median"] <= 100 and p005_primary_contract["candidate_set_size_p95"] <= 100 else "FAIL",
            "value": {
                "median": p005_primary_contract["candidate_set_size_median"],
                "p95": p005_primary_contract["candidate_set_size_p95"],
            },
            "threshold": {"median": 100, "p95": 100},
        },
        {
            "gate_id": "safety_gate_zero_wrong_acceptance",
            "status": "PASS" if p005_primary_contract["decoder_contract_conditional_risk"] == 0.0 and p005_primary_exact["exact_trace_conditional_risk"] == 0.0 and p005_primary_ambiguity["ambiguous_wrong_acceptance_rate"] == 0.0 else "FAIL",
            "value": {
                "decoder_contract_conditional_risk": p005_primary_contract["decoder_contract_conditional_risk"],
                "exact_trace_conditional_risk": p005_primary_exact["exact_trace_conditional_risk"],
                "ambiguous_wrong_acceptance_rate": p005_primary_ambiguity["ambiguous_wrong_acceptance_rate"],
            },
        },
        {
            "gate_id": "utility_gate_nontrivial_acceptance",
            "status": "PASS" if p005_primary_contract["decoder_contract_acceptance_coverage"] >= PRIMARY_COVERAGE_THRESHOLD and p005_primary_contract["candidate_reduction_ratio"] > p005_random["candidate_reduction_ratio"] else "FAIL",
            "value": {
                "coverage": p005_primary_contract["decoder_contract_acceptance_coverage"],
                "candidate_reduction_ratio": p005_primary_contract["candidate_reduction_ratio"],
                "random_candidate_reduction_ratio": p005_random["candidate_reduction_ratio"],
            },
            "threshold": {"coverage": PRIMARY_COVERAGE_THRESHOLD},
        },
        {
            "gate_id": "latency_gate_vs_vectorized_global_scan",
            "status": "PASS" if p005_primary_contract["total_query_latency_sec_p50"] < p005_global["total_query_latency_sec_p50"] else "FAIL",
            "value": {
                "primary_p50": p005_primary_contract["total_query_latency_sec_p50"],
                "global_p50": p005_global["total_query_latency_sec_p50"],
            },
        },
        {
            "gate_id": "theory_consistency_gate",
            "status": "PASS" if abs(p005_theory["observed_recall"] - p005_theory["expected_any_table_hit_probability"]) <= THEORY_TOLERANCE else "FAIL",
            "value": {
                "observed": p005_theory["observed_recall"],
                "expected": p005_theory["expected_any_table_hit_probability"],
            },
            "threshold": THEORY_TOLERANCE,
        },
    ]

    verdict = "PASS_STAGE_A1_ROUTING" if all(gate["status"] == "PASS" for gate in gates) else "PARTIAL"
    if p005_primary_ambiguity["ambiguous_wrong_acceptance_rate"] > 0.0 or not seeds_are_fresh(repo_root) or _stage_a_protocol_hash(repo_root) != STAGE_A_PROTOCOL_HASH:
        verdict = "BLOCK"

    analysis = {
        "schema_version": STAGE_A1_SCHEMA_VERSION,
        "build_verdict": verdict,
        "stage_a_protocol_hash": STAGE_A_PROTOCOL_HASH,
        "stage_a_artifacts_unchanged": _stage_a_protocol_hash(repo_root) == STAGE_A_PROTOCOL_HASH,
        "heldout_execution_count": 0,
        "memory_rows": analysis_rows,
        "gates": gates,
        "allowed_claims": [
            "Semantic LSH can be development-tested as a routing prior for decoder-contract retrieval.",
            "Decoder-contract retrieval can be separated from exact provenance retrieval.",
            "Ambiguous exact traces require typed ambiguity handling rather than arbitrary acceptance.",
        ],
        "forbidden_claims": [
            "No new ANN or LSH algorithm was invented.",
            "No exact provenance recovery claim follows from decoder-contract recall.",
            "No Stage B authorization follows automatically from Stage A.1.",
            "No held-out or production confirmation was performed.",
        ],
        "next_lawful_stage": "Stage A.2: compare semantic LSH routing against mature ANN and SDM-style baselines",
    }

    write_jsonl(results_dir / "dataset_manifest.jsonl", dataset_manifest_rows)
    write_jsonl(results_dir / "query_manifest.jsonl", query_manifest_rows)
    write_jsonl(results_dir / "trial_results.jsonl", trial_rows)
    write_csv(results_dir / "summary.csv", summary_rows)
    write_csv(results_dir / "contract_retrieval_summary.csv", contract_summary_rows)
    write_csv(results_dir / "exact_trace_summary.csv", exact_summary_rows)
    write_csv(results_dir / "ambiguity_summary.csv", ambiguity_summary_rows)
    write_csv(results_dir / "theory_vs_observed.csv", theory_rows)
    write_csv(results_dir / "ablation_summary.csv", ablation_rows)
    write_json(results_dir / "analysis.json", analysis)

    return {
        "protocol": protocol,
        "summary_rows": summary_rows,
        "contract_retrieval_summary": contract_summary_rows,
        "exact_trace_summary": exact_summary_rows,
        "ambiguity_summary": ambiguity_summary_rows,
        "theory_rows": theory_rows,
        "ablation_rows": ablation_rows,
        "analysis": analysis,
    }
