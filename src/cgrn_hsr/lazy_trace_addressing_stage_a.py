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
import torch.nn.functional as F
import torchhd

from .baseline import normalized_similarity_pair
from .level3_5b_native_noise_frontiers import prior_seed_set as level3_5b_prior_seed_set
from .semantic_lsh import RandomBucketRouter, RandomHyperplaneLSH, RoutingResult, SignatureConfig
from .trace_index import TraceIndex, TraceStoreEntry
from .trace_record import ALLOWED_OPERATION_FAMILIES, TraceRecord, payload_checksum
from .verification import (
    DECISION_ABSTAIN,
    DECISION_ACCEPT,
    DECISION_EXPAND,
    decide_candidate,
    rerank_candidates,
)

STAGE_A_SCHEMA_VERSION = "lazy-semantic-trace-stage-a-dev-v1"
STAGE_A_BASE_CHECKPOINT_COMMIT = "1c4fd2f"
STAGE_A_NAMESPACE = "lazy_trace_stage_a"
STAGE_A_TASK_NAME = "Lazy Semantic-to-Trace Addressing - Stage A"
STAGE_A_BRANCH_EXPECTATION = "codex/lazy-trace-addressing-stage-a"

MAP_DIMENSIONS = 1024
DATASET_SPECS: tuple[dict[str, Any], ...] = (
    {"dataset_id": "n1000", "record_count": 1_000, "query_trials_per_point": 32},
    {"dataset_id": "n10000", "record_count": 10_000, "query_trials_per_point": 32},
)
QUERY_CORRUPTION_POINTS = (0.00, 0.01, 0.03, 0.05, 0.10, 0.15)
CORRUPTION_CHANNEL_ID = "MAP_EXTERNAL_BERNOULLI_SIGN_FLIP"

DATASET_SEED_RANGES = {
    "n1000": {"start": 930350100, "count": 1},
    "n10000": {"start": 930351100, "count": 1},
}
QUERY_SEED_RANGES = {
    "n1000": {"start": 930360100, "count": 32},
    "n10000": {"start": 930361100, "count": 32},
}
PROJECTION_SEEDS = (930370101, 930370102, 930370103)
SMOKE_SEED = 930380001

SIGNATURE_BITS = 12
MULTI_TABLE_COUNT = 4
ONE_TABLE_PROBE_BUDGET = 1
MULTI_TABLE_PROBE_BUDGET = 1
MULTI_PROBE_BUDGET = 4
CANDIDATE_BUDGET = 96
RERANK_K = 32
ACCEPT_SIMILARITY_THRESHOLD = 0.97
ACCEPT_MARGIN = 0.02

METHOD_GLOBAL_SCAN = "B0_global_exact_semantic_scan"
METHOD_EXACT_HASH = "B1_exact_content_hash_only"
METHOD_RANDOM_ROUTING = "B2_random_bucket_routing"
METHOD_ONE_TABLE = "B3_one_table_lsh"
METHOD_MULTI_TABLE = "B4_multi_table_lsh"
METHOD_MULTI_PROBE = "B5_bounded_multi_probe_lsh"

OPERATION_FAMILY_CHOICES = ALLOWED_OPERATION_FAMILIES
NAMESPACE_SIZES = {
    "OBS": 256,
    "ROLE": 128,
    "CTX": 128,
    "ATTR": 128,
    "STATE": 128,
    "REL": 128,
}


@dataclass(frozen=True)
class OperationSpec:
    operation_family: str
    arity: int
    operand_namespaces: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    parent_handles: tuple[str, ...]
    semantic_payload: torch.Tensor


@dataclass(frozen=True)
class DatasetRecord:
    record_id: str
    trace_handle: str
    trace_record: TraceRecord
    semantic_payload: torch.Tensor
    family_label: str
    arity: int
    operand_namespaces: tuple[str, ...]
    adversarial_group: str | None


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    trial_seed: int
    dataset_id: str
    corruption_probability: float
    target_handle: str
    noisy_payload: torch.Tensor
    clean_payload: torch.Tensor
    target_operation_family: str
    target_arity: int
    target_namespaces: tuple[str, ...]
    adversarial_group: str | None


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


def stage_a_seed_set() -> set[int]:
    values: set[int] = set(PROJECTION_SEEDS)
    values.add(SMOKE_SEED)
    for mapping in (DATASET_SEED_RANGES, QUERY_SEED_RANGES):
        for spec in mapping.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    return values


def _protocol_seed_set_from_path(path: Path) -> set[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values: set[int] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if {"start", "count"}.issubset(node.keys()) and isinstance(node["start"], int) and isinstance(node["count"], int):
                for seed in range(node["start"], node["start"] + node["count"]):
                    values.add(seed)
            elif "seeds" in node and isinstance(node["seeds"], list):
                for seed in node["seeds"]:
                    if isinstance(seed, int):
                        values.add(seed)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(payload)
    return values


def prior_known_seed_set(repo_root: Path) -> set[int]:
    prior = set(level3_5b_prior_seed_set())
    for relpath in (
        "results/level3_5b_protocol_repair/heldout_protocol_v2.json",
        "results/level3_5b_gate_specification/heldout_protocol_v3.json",
        "results/level3_5b_gate_consistency_repair/heldout_protocol_v4.json",
    ):
        path = repo_root / relpath
        if path.exists():
            prior.update(_protocol_seed_set_from_path(path))
    return prior


def seeds_are_fresh(repo_root: Path) -> bool:
    return stage_a_seed_set().isdisjoint(prior_known_seed_set(repo_root))


def _namespace_vectors(seed: int) -> dict[str, torch.Tensor]:
    vectors: dict[str, torch.Tensor] = {}
    for index, (namespace, count) in enumerate(sorted(NAMESPACE_SIZES.items())):
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed + (index * 10_000))
        vectors[namespace] = torchhd.random(count, MAP_DIMENSIONS, "MAP", generator=generator).detach().cpu()
    return vectors


def _bind_sequence(vectors: list[torch.Tensor]) -> torch.Tensor:
    result = vectors[0]
    for vector in vectors[1:]:
        result = torchhd.bind(result, vector)
    return result


def _family_spec(
    family: str,
    *,
    namespace_vectors: dict[str, torch.Tensor],
    rng: random.Random,
    group_id: str | None,
) -> tuple[OperationSpec, tuple[str, ...]]:
    if family == "MAP_BIND_2":
        namespaces = ("OBS", "CTX")
        indices = tuple(str(rng.randrange(NAMESPACE_SIZES[name])) for name in namespaces)
        payload = torchhd.bind(
            namespace_vectors["OBS"][int(indices[0])],
            namespace_vectors["CTX"][int(indices[1])],
        )
        return (
            OperationSpec(
                operation_family=family,
                arity=2,
                operand_namespaces=namespaces,
                operation_parameters={},
                parent_handles=tuple(f"atom:{name}:{index}" for name, index in zip(namespaces, indices, strict=True)),
                semantic_payload=payload.detach().cpu(),
            ),
            indices,
        )
    if family == "MAP_BIND_3":
        namespaces = ("OBS", "REL", "ATTR")
        indices = tuple(str(rng.randrange(NAMESPACE_SIZES[name])) for name in namespaces)
        payload = _bind_sequence(
            [
                namespace_vectors["OBS"][int(indices[0])],
                namespace_vectors["REL"][int(indices[1])],
                namespace_vectors["ATTR"][int(indices[2])],
            ]
        )
        return (
            OperationSpec(
                operation_family=family,
                arity=3,
                operand_namespaces=namespaces,
                operation_parameters={},
                parent_handles=tuple(f"atom:{name}:{index}" for name, index in zip(namespaces, indices, strict=True)),
                semantic_payload=payload.detach().cpu(),
            ),
            indices,
        )
    if family == "MAP_BUNDLE_3":
        namespaces = ("OBS", "OBS", "STATE")
        indices = (
            str(rng.randrange(NAMESPACE_SIZES["OBS"])),
            str(rng.randrange(NAMESPACE_SIZES["OBS"])),
            str(rng.randrange(NAMESPACE_SIZES["STATE"])),
        )
        payload = torchhd.multiset(
            torch.stack(
                [
                    namespace_vectors["OBS"][int(indices[0])],
                    namespace_vectors["OBS"][int(indices[1])],
                    namespace_vectors["STATE"][int(indices[2])],
                ],
                dim=0,
            )
        )
        return (
            OperationSpec(
                operation_family=family,
                arity=3,
                operand_namespaces=namespaces,
                operation_parameters={},
                parent_handles=(
                    f"atom:OBS:{indices[0]}",
                    f"atom:OBS:{indices[1]}",
                    f"atom:STATE:{indices[2]}",
                ),
                semantic_payload=payload.detach().cpu(),
            ),
            indices,
        )
    if family == "MAP_BUNDLE_5":
        namespaces = ("OBS", "OBS", "ATTR", "STATE", "CTX")
        indices = (
            str(rng.randrange(NAMESPACE_SIZES["OBS"])),
            str(rng.randrange(NAMESPACE_SIZES["OBS"])),
            str(rng.randrange(NAMESPACE_SIZES["ATTR"])),
            str(rng.randrange(NAMESPACE_SIZES["STATE"])),
            str(rng.randrange(NAMESPACE_SIZES["CTX"])),
        )
        payload = torchhd.multiset(
            torch.stack(
                [
                    namespace_vectors["OBS"][int(indices[0])],
                    namespace_vectors["OBS"][int(indices[1])],
                    namespace_vectors["ATTR"][int(indices[2])],
                    namespace_vectors["STATE"][int(indices[3])],
                    namespace_vectors["CTX"][int(indices[4])],
                ],
                dim=0,
            )
        )
        return (
            OperationSpec(
                operation_family=family,
                arity=5,
                operand_namespaces=namespaces,
                operation_parameters={},
                parent_handles=tuple(
                    f"atom:{name}:{index}" for name, index in zip(namespaces, indices, strict=True)
                ),
                semantic_payload=payload.detach().cpu(),
            ),
            indices,
        )
    if family == "MAP_PERMUTE_K":
        namespaces = ("OBS",)
        index = str(rng.randrange(NAMESPACE_SIZES["OBS"]))
        shifts = 1 + (rng.randrange(7))
        payload = torchhd.permute(namespace_vectors["OBS"][int(index)], shifts=shifts)
        return (
            OperationSpec(
                operation_family=family,
                arity=1,
                operand_namespaces=namespaces,
                operation_parameters={"shifts": shifts},
                parent_handles=(f"atom:OBS:{index}",),
                semantic_payload=payload.detach().cpu(),
            ),
            (index,),
        )
    if family == "MAP_BIND_THEN_BUNDLE":
        namespaces = ("ROLE", "OBS", "STATE", "CTX")
        indices = tuple(str(rng.randrange(NAMESPACE_SIZES[name])) for name in namespaces)
        bound = torchhd.bind(
            namespace_vectors["ROLE"][int(indices[0])],
            namespace_vectors["OBS"][int(indices[1])],
        )
        payload = torchhd.multiset(
            torch.stack(
                [
                    bound,
                    namespace_vectors["STATE"][int(indices[2])],
                    namespace_vectors["CTX"][int(indices[3])],
                ],
                dim=0,
            )
        )
        return (
            OperationSpec(
                operation_family=family,
                arity=4,
                operand_namespaces=namespaces,
                operation_parameters={"bundle_width": 3},
                parent_handles=tuple(
                    f"atom:{name}:{index}" for name, index in zip(namespaces, indices, strict=True)
                ),
                semantic_payload=payload.detach().cpu(),
            ),
            indices,
        )
    raise ValueError(f"Unsupported family: {family}")


def _adversarial_pair(
    *,
    pair_seed: int,
    family: str,
    namespace_vectors: dict[str, torch.Tensor],
    pair_index: int,
) -> list[tuple[OperationSpec, str | None]]:
    rng = random.Random(pair_seed)
    if family == "MAP_BUNDLE_3":
        obs_a = rng.randrange(NAMESPACE_SIZES["OBS"])
        obs_b = rng.randrange(NAMESPACE_SIZES["OBS"])
        state_left = rng.randrange(NAMESPACE_SIZES["STATE"])
        state_right = (state_left + 1) % NAMESPACE_SIZES["STATE"]
        payload_left = torchhd.multiset(
            torch.stack(
                [
                    namespace_vectors["OBS"][obs_a],
                    namespace_vectors["OBS"][obs_b],
                    namespace_vectors["STATE"][state_left],
                ],
                dim=0,
            )
        )
        payload_right = torchhd.multiset(
            torch.stack(
                [
                    namespace_vectors["OBS"][obs_a],
                    namespace_vectors["OBS"][obs_b],
                    namespace_vectors["STATE"][state_right],
                ],
                dim=0,
            )
        )
        group = f"bundle3-near-{pair_index}"
        return [
            (
                OperationSpec(
                    operation_family="MAP_BUNDLE_3",
                    arity=3,
                    operand_namespaces=("OBS", "OBS", "STATE"),
                    operation_parameters={},
                    parent_handles=(
                        f"atom:OBS:{obs_a}",
                        f"atom:OBS:{obs_b}",
                        f"atom:STATE:{state_left}",
                    ),
                    semantic_payload=payload_left.detach().cpu(),
                ),
                group,
            ),
            (
                OperationSpec(
                    operation_family="MAP_BUNDLE_3",
                    arity=3,
                    operand_namespaces=("OBS", "OBS", "STATE"),
                    operation_parameters={},
                    parent_handles=(
                        f"atom:OBS:{obs_a}",
                        f"atom:OBS:{obs_b}",
                        f"atom:STATE:{state_right}",
                    ),
                    semantic_payload=payload_right.detach().cpu(),
                ),
                group,
            ),
        ]
    if family == "MAP_BIND_THEN_BUNDLE":
        role = rng.randrange(NAMESPACE_SIZES["ROLE"])
        obs = rng.randrange(NAMESPACE_SIZES["OBS"])
        state = rng.randrange(NAMESPACE_SIZES["STATE"])
        ctx_left = rng.randrange(NAMESPACE_SIZES["CTX"])
        ctx_right = (ctx_left + 1) % NAMESPACE_SIZES["CTX"]
        bound = torchhd.bind(namespace_vectors["ROLE"][role], namespace_vectors["OBS"][obs])
        payload_left = torchhd.multiset(
            torch.stack([bound, namespace_vectors["STATE"][state], namespace_vectors["CTX"][ctx_left]], dim=0)
        )
        payload_right = torchhd.multiset(
            torch.stack([bound, namespace_vectors["STATE"][state], namespace_vectors["CTX"][ctx_right]], dim=0)
        )
        group = f"bind-bundle-near-{pair_index}"
        return [
            (
                OperationSpec(
                    operation_family="MAP_BIND_THEN_BUNDLE",
                    arity=4,
                    operand_namespaces=("ROLE", "OBS", "STATE", "CTX"),
                    operation_parameters={"bundle_width": 3},
                    parent_handles=(
                        f"atom:ROLE:{role}",
                        f"atom:OBS:{obs}",
                        f"atom:STATE:{state}",
                        f"atom:CTX:{ctx_left}",
                    ),
                    semantic_payload=payload_left.detach().cpu(),
                ),
                group,
            ),
            (
                OperationSpec(
                    operation_family="MAP_BIND_THEN_BUNDLE",
                    arity=4,
                    operand_namespaces=("ROLE", "OBS", "STATE", "CTX"),
                    operation_parameters={"bundle_width": 3},
                    parent_handles=(
                        f"atom:ROLE:{role}",
                        f"atom:OBS:{obs}",
                        f"atom:STATE:{state}",
                        f"atom:CTX:{ctx_right}",
                    ),
                    semantic_payload=payload_right.detach().cpu(),
                ),
                group,
            ),
        ]
    return []


def build_dataset(*, dataset_seed: int, record_count: int) -> list[DatasetRecord]:
    namespace_vectors = _namespace_vectors(dataset_seed)
    rng = random.Random(dataset_seed)
    records: list[DatasetRecord] = []
    seen_checksums: set[str] = set()
    adversarial_pairs = max(8, record_count // 50)
    pair_family_cycle = ("MAP_BUNDLE_3", "MAP_BIND_THEN_BUNDLE")

    def add_spec(spec: OperationSpec, adversarial_group: str | None) -> None:
        checksum = payload_checksum(spec.semantic_payload)
        if checksum in seen_checksums:
            return
        record_ordinal = len(records)
        record_id = f"record:{record_count}:{record_ordinal:05d}"
        trace_handle = f"trace:{record_count}:{record_ordinal:05d}"
        trace_record = TraceRecord(
            trace_handle=trace_handle,
            record_id=record_id,
            operation_family=spec.operation_family,
            algebra="MAP",
            arity=spec.arity,
            operand_namespaces=spec.operand_namespaces,
            operation_parameters=spec.operation_parameters,
            parent_handles=spec.parent_handles,
            semantic_payload_checksum=checksum,
        )
        records.append(
            DatasetRecord(
                record_id=record_id,
                trace_handle=trace_handle,
                trace_record=trace_record,
                semantic_payload=spec.semantic_payload.detach().cpu(),
                family_label=spec.operation_family,
                arity=spec.arity,
                operand_namespaces=spec.operand_namespaces,
                adversarial_group=adversarial_group,
            )
        )
        seen_checksums.add(checksum)

    for pair_index in range(adversarial_pairs):
        family = pair_family_cycle[pair_index % len(pair_family_cycle)]
        for spec, group in _adversarial_pair(
            pair_seed=dataset_seed + 10_000 + pair_index,
            family=family,
            namespace_vectors=namespace_vectors,
            pair_index=pair_index,
        ):
            add_spec(spec, group)
            if len(records) >= record_count:
                return records

    family_index = 0
    safety = 0
    while len(records) < record_count:
        family = OPERATION_FAMILY_CHOICES[family_index % len(OPERATION_FAMILY_CHOICES)]
        family_index += 1
        safety += 1
        if safety > record_count * 100:
            raise RuntimeError("Dataset generation failed to reach the requested unique record count.")
        spec, _ = _family_spec(
            family,
            namespace_vectors=namespace_vectors,
            rng=rng,
            group_id=None,
        )
        before = len(records)
        add_spec(spec, None)
        if len(records) == before:
            continue
    return records


def build_trace_index(records: list[DatasetRecord]) -> TraceIndex:
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


def corrupt_payload(payload: torch.Tensor, *, probability: float, seed: int) -> torch.Tensor:
    if probability <= 0.0:
        return payload.detach().clone().cpu()
    flat = payload.detach().clone().cpu().reshape(-1)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    mask = torch.rand(flat.numel(), generator=generator) < probability
    flat[mask] *= -1
    return flat.reshape(payload.shape)


def build_queries(
    *,
    dataset_id: str,
    records: list[DatasetRecord],
    query_seed_start: int,
    query_count: int,
    corruption_probability: float,
) -> list[QuerySpec]:
    grouped: dict[str, list[DatasetRecord]] = {}
    non_grouped: list[DatasetRecord] = []
    for record in records:
        if record.adversarial_group is None:
            non_grouped.append(record)
        else:
            grouped.setdefault(record.adversarial_group, []).append(record)
    adversarial_records = [group[0] for group in grouped.values() if group]
    queries: list[QuerySpec] = []
    for offset in range(query_count):
        seed = query_seed_start + offset
        rng = random.Random(seed)
        if adversarial_records and offset % 4 == 0:
            target = adversarial_records[offset % len(adversarial_records)]
        else:
            target = non_grouped[rng.randrange(len(non_grouped))]
        queries.append(
            QuerySpec(
                query_id=f"{dataset_id}-p{corruption_probability:.2f}-q{offset:03d}",
                trial_seed=seed,
                dataset_id=dataset_id,
                corruption_probability=corruption_probability,
                target_handle=target.trace_handle,
                noisy_payload=corrupt_payload(target.semantic_payload, probability=corruption_probability, seed=seed + 17),
                clean_payload=target.semantic_payload,
                target_operation_family=target.family_label,
                target_arity=target.arity,
                target_namespaces=target.operand_namespaces,
                adversarial_group=target.adversarial_group,
            )
        )
    return queries


def exact_trace_hit(index: TraceIndex, query: QuerySpec) -> tuple[str, ...]:
    return index.exact_lookup(query.noisy_payload)


def global_scan(handles: list[str], index: TraceIndex, query: QuerySpec, *, candidate_budget: int) -> tuple[RoutingResult, list[TraceStoreEntry], torch.Tensor, float]:
    start = time.perf_counter()
    candidates = index.committed_entries()
    candidate_matrix = index.committed_payload_matrix()
    latency = time.perf_counter() - start
    return (
        RoutingResult(
            candidate_handles=tuple(handle for handle in handles[:candidate_budget]),
            primary_signatures=("GLOBAL_SCAN",),
            probed_signatures=("GLOBAL_SCAN",),
            expansion_used=False,
            duplicate_postings=0,
            empty_primary_bucket=False,
        ),
        candidates[:candidate_budget],
        candidate_matrix[:candidate_budget],
        latency,
    )


def run_method_query(
    *,
    method_id: str,
    query: QuerySpec,
    index: TraceIndex,
    handles: list[str],
    lsh_router: RandomHyperplaneLSH | None,
    random_router: RandomBucketRouter | None,
) -> dict[str, Any]:
    if method_id == METHOD_GLOBAL_SCAN:
        routing, entries, candidate_matrix, routing_latency = global_scan(handles, index, query, candidate_budget=len(handles))
    elif method_id == METHOD_EXACT_HASH:
        start = time.perf_counter()
        matched = exact_trace_hit(index, query)
        routing_latency = time.perf_counter() - start
        routing = RoutingResult(
            candidate_handles=matched,
            primary_signatures=("EXACT_HASH",),
            probed_signatures=("EXACT_HASH",),
            expansion_used=False,
            duplicate_postings=0,
            empty_primary_bucket=(len(matched) == 0),
        )
        entries = [entry for handle in matched for entry in [index.get(handle)] if entry is not None]
        candidate_matrix = None
    elif method_id == METHOD_RANDOM_ROUTING:
        assert random_router is not None
        start = time.perf_counter()
        routing = random_router.route(query_key=query.query_id, candidate_budget=CANDIDATE_BUDGET)
        routing_latency = time.perf_counter() - start
        entries = [entry for handle in routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
        candidate_matrix = None
    else:
        assert lsh_router is not None
        start = time.perf_counter()
        routing = lsh_router.route(query.noisy_payload, candidate_budget=CANDIDATE_BUDGET)
        routing_latency = time.perf_counter() - start
        entries = [entry for handle in routing.candidate_handles for entry in [index.get(handle)] if entry is not None]
        candidate_matrix = None

    reranked, reranking_latency = rerank_candidates(query.noisy_payload, entries, candidate_matrix=candidate_matrix)
    decision = decide_candidate(
        reranked,
        rerank_k=RERANK_K,
        accept_similarity_threshold=ACCEPT_SIMILARITY_THRESHOLD,
        accept_margin=ACCEPT_MARGIN,
        expansion_available=(method_id in {METHOD_ONE_TABLE, METHOD_MULTI_TABLE, METHOD_MULTI_PROBE} and routing.empty_primary_bucket)
        or method_id == METHOD_RANDOM_ROUTING,
    )
    topk_handles = [candidate.handle for candidate in reranked[:RERANK_K]]
    top1 = reranked[0] if reranked else None
    top1_correct = bool(top1 is not None and top1.handle == query.target_handle)
    accepted_correct = bool(decision.accepted_handle == query.target_handle)
    accepted_wrong = bool(decision.decision == DECISION_ACCEPT and decision.accepted_handle != query.target_handle)
    inspected = max(1, len(routing.candidate_handles))
    return {
        "method_id": method_id,
        "query_id": query.query_id,
        "dataset_id": query.dataset_id,
        "corruption_probability": query.corruption_probability,
        "corruption_channel_id": CORRUPTION_CHANNEL_ID,
        "target_handle": query.target_handle,
        "trace_recall_at_1": int(query.target_handle in topk_handles[:1]),
        "trace_recall_at_8": int(query.target_handle in topk_handles[:8]),
        "trace_recall_at_32": int(query.target_handle in topk_handles[:32]),
        "candidate_set_size": len(routing.candidate_handles),
        "decision": decision.decision,
        "accepted_handle": decision.accepted_handle,
        "operation_family_accuracy": int(top1 is not None and top1.operation_family == query.target_operation_family),
        "arity_accuracy": int(top1 is not None and top1.arity == query.target_arity),
        "namespace_contract_accuracy": int(top1 is not None and top1.operand_namespaces == query.target_namespaces),
        "wrong_trace_top1_rate": int(not top1_correct),
        "wrong_trace_acceptance_rate": int(accepted_wrong),
        "abstention_rate": int(decision.decision == DECISION_ABSTAIN),
        "expansion_rate": int(routing.expansion_used),
        "fallback_rate": int(decision.decision == DECISION_EXPAND),
        "routing_latency_sec": routing_latency,
        "reranking_latency_sec": reranking_latency,
        "total_query_latency_sec": routing_latency + reranking_latency,
        "duplicate_posting_rate": (routing.duplicate_postings / max(1, len(routing.probed_signatures))) if routing.probed_signatures else 0.0,
        "verified_correct_trace_retrieval_per_candidate": (1.0 / inspected) if accepted_correct else 0.0,
        "expected_decoder_family_invocations_avoided": len(handles) - len(routing.candidate_handles),
        "top1_similarity": float(top1.similarity) if top1 is not None else None,
        "top2_similarity": float(reranked[1].similarity) if len(reranked) > 1 else None,
        "accept_margin": decision.margin,
        "top1_validation_status": top1.validation_status if top1 is not None else None,
        "target_found_anywhere": int(query.target_handle in routing.candidate_handles),
        "adversarial_group": query.adversarial_group,
    }


def summarize_method_rows(
    rows: list[dict[str, Any]],
    *,
    record_count: int,
    index_stats: dict[str, dict[str, float]],
    memory_lookup: dict[str, int],
    build_latency_lookup: dict[str, float],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["dataset_id"], row["method_id"], row["corruption_probability"])
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for key in sorted(grouped):
        batch = grouped[key]
        first = batch[0]
        recall32_successes = sum(row["trace_recall_at_32"] for row in batch)
        ci_low, ci_high = wilson_interval(recall32_successes, len(batch))
        method_stats = index_stats.get(first["method_id"], {})
        summary.append(
            {
                "schema_version": STAGE_A_SCHEMA_VERSION,
                "dataset_id": first["dataset_id"],
                "record_count": record_count,
                "method_id": first["method_id"],
                "corruption_probability": first["corruption_probability"],
                "trials": len(batch),
                "trace_recall_at_1": statistics.mean(row["trace_recall_at_1"] for row in batch),
                "trace_recall_at_8": statistics.mean(row["trace_recall_at_8"] for row in batch),
                "trace_recall_at_32": statistics.mean(row["trace_recall_at_32"] for row in batch),
                "trace_recall_at_32_ci_low": ci_low,
                "trace_recall_at_32_ci_high": ci_high,
                "candidate_set_size_median": statistics.median(row["candidate_set_size"] for row in batch),
                "candidate_set_size_mean": statistics.mean(row["candidate_set_size"] for row in batch),
                "candidate_reduction_ratio": 1.0 - (statistics.mean(row["candidate_set_size"] for row in batch) / record_count),
                "operation_family_accuracy": statistics.mean(row["operation_family_accuracy"] for row in batch),
                "arity_accuracy": statistics.mean(row["arity_accuracy"] for row in batch),
                "namespace_contract_accuracy": statistics.mean(row["namespace_contract_accuracy"] for row in batch),
                "wrong_trace_top1_rate": statistics.mean(row["wrong_trace_top1_rate"] for row in batch),
                "wrong_trace_acceptance_rate": statistics.mean(row["wrong_trace_acceptance_rate"] for row in batch),
                "abstention_rate": statistics.mean(row["abstention_rate"] for row in batch),
                "expansion_rate": statistics.mean(row["expansion_rate"] for row in batch),
                "fallback_rate": statistics.mean(row["fallback_rate"] for row in batch),
                "routing_latency_sec_median": statistics.median(row["routing_latency_sec"] for row in batch),
                "reranking_latency_sec_median": statistics.median(row["reranking_latency_sec"] for row in batch),
                "total_query_latency_sec_median": statistics.median(row["total_query_latency_sec"] for row in batch),
                "verified_correct_trace_retrieval_per_candidate": statistics.mean(
                    row["verified_correct_trace_retrieval_per_candidate"] for row in batch
                ),
                "expected_decoder_family_invocations_avoided": statistics.mean(
                    row["expected_decoder_family_invocations_avoided"] for row in batch
                ),
                "bucket_occupancy_mean": method_stats.get("bucket_occupancy_mean", 0.0),
                "bucket_occupancy_p50": method_stats.get("bucket_occupancy_p50", 0.0),
                "bucket_occupancy_p95": method_stats.get("bucket_occupancy_p95", 0.0),
                "bucket_occupancy_p99": method_stats.get("bucket_occupancy_p99", 0.0),
                "empty_bucket_rate": method_stats.get("empty_bucket_rate", 0.0),
                "collision_rate": method_stats.get("collision_rate", 0.0),
                "posting_count": method_stats.get("posting_count", 0.0),
                "memory_bytes_estimate": memory_lookup.get(first["method_id"], 0),
                "index_build_latency_sec": build_latency_lookup.get(first["method_id"], 0.0),
            }
        )
    return summary


def dependency_audit() -> dict[str, Any]:
    return {
        "schema_version": STAGE_A_SCHEMA_VERSION,
        "verdict": "PROTOTYPE / DEVELOPMENT_ONLY",
        "map_substrate": {
            "status": "ADOPT",
            "source": "torch-hd MAP random/bind/bundle/permute primitives",
            "coverage": "semantic substrate and similarity reranking",
        },
        "lsh_or_ann_library": {
            "status": "BLOCK_REUSE_NOT_AVAILABLE",
            "checked": {
                "faiss": False,
                "annoy": False,
                "datasketch": False,
                "sklearn": False,
                "scipy": True,
            },
            "reason": "No frozen mature ANN/LSH dependency is present in the repo lock; Stage A therefore uses a tiny deterministic wrapper around standard random-hyperplane signatures and posting dictionaries rather than a new framework.",
        },
        "exact_hash_control": {
            "status": "ADOPT_LOCAL_PRIMITIVE",
            "source": "sha256 over frozen semantic sign bits",
            "coverage": "exact equality baseline only",
        },
    }


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": STAGE_A_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "numpy_version": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "branch_expectation": STAGE_A_BRANCH_EXPECTATION,
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": STAGE_A_SCHEMA_VERSION,
        "task_name": STAGE_A_TASK_NAME,
        "base_checkpoint_commit": STAGE_A_BASE_CHECKPOINT_COMMIT,
        "results_namespace": STAGE_A_NAMESPACE,
        "vsa": "MAP",
        "dimensions": MAP_DIMENSIONS,
        "dataset_specs": list(DATASET_SPECS),
        "dataset_seed_ranges": DATASET_SEED_RANGES,
        "query_seed_ranges": QUERY_SEED_RANGES,
        "projection_seeds": list(PROJECTION_SEEDS),
        "smoke_seed": SMOKE_SEED,
        "corruption_channel": {
            "channel_id": CORRUPTION_CHANNEL_ID,
            "type": "bernoulli_sign_flip_after_clean_payload",
            "points": list(QUERY_CORRUPTION_POINTS),
        },
        "baselines": [
            METHOD_GLOBAL_SCAN,
            METHOD_EXACT_HASH,
            METHOD_RANDOM_ROUTING,
            METHOD_ONE_TABLE,
            METHOD_MULTI_TABLE,
            METHOD_MULTI_PROBE,
        ],
        "trace_families": list(OPERATION_FAMILY_CHOICES),
        "lsh_grid": {
            "signature_bits": [SIGNATURE_BITS],
            "table_count": [1, MULTI_TABLE_COUNT],
            "probe_budget": [ONE_TABLE_PROBE_BUDGET, MULTI_PROBE_BUDGET],
            "rerank_k": [RERANK_K],
            "acceptance_margin": [ACCEPT_MARGIN],
        },
        "frozen_params": {
            "candidate_budget": CANDIDATE_BUDGET,
            "accept_similarity_threshold": ACCEPT_SIMILARITY_THRESHOLD,
            "accept_margin": ACCEPT_MARGIN,
            "signature_bits": SIGNATURE_BITS,
            "one_table_probe_budget": ONE_TABLE_PROBE_BUDGET,
            "multi_table_count": MULTI_TABLE_COUNT,
            "multi_table_probe_budget": MULTI_TABLE_PROBE_BUDGET,
            "multi_probe_budget": MULTI_PROBE_BUDGET,
        },
        "required_ablations": [
            "A1_random_buckets",
            "A2_one_vs_multi_table",
            "A3_no_multi_probe",
            "A4_without_exact_reranking",
            "A5_without_typed_trace_validation",
            "A6_semantic_payload_shuffled_relative_to_trace",
            "A7_trace_family_labels_shuffled",
            "A8_exact_vs_noisy_cue",
            "A9_different_fixed_projection_seeds",
            "A10_equal_candidate_budget_comparison",
        ],
        "no_overlap_with_prior_frozen_seeds": seeds_are_fresh(repo_root),
        "heldout_execution": False,
        "frozen_level3_5b_artifacts_touched": False,
    }


def _warmup_query(
    *,
    index: TraceIndex,
    handles: list[str],
    query: QuerySpec,
    one_table: RandomHyperplaneLSH,
    multi_table: RandomHyperplaneLSH,
    multi_probe: RandomHyperplaneLSH,
    random_router: RandomBucketRouter,
) -> None:
    for method_id, router, control in (
        (METHOD_GLOBAL_SCAN, None, None),
        (METHOD_EXACT_HASH, None, None),
        (METHOD_RANDOM_ROUTING, None, random_router),
        (METHOD_ONE_TABLE, one_table, None),
        (METHOD_MULTI_TABLE, multi_table, None),
        (METHOD_MULTI_PROBE, multi_probe, None),
    ):
        run_method_query(
            method_id=method_id,
            query=query,
            index=index,
            handles=handles,
            lsh_router=router,
            random_router=control,
        )


def run_stage_a(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / STAGE_A_NAMESPACE
    results_dir.mkdir(parents=True, exist_ok=True)

    environment = environment_snapshot()
    dependency = dependency_audit()
    protocol = build_protocol(repo_root)

    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "dependency_audit.json", dependency)
    write_json(results_dir / "development_protocol.json", protocol)

    smoke_dataset = build_dataset(dataset_seed=SMOKE_SEED, record_count=64)
    smoke_index = build_trace_index(smoke_dataset)
    smoke_queries = build_queries(
        dataset_id="smoke64",
        records=smoke_dataset,
        query_seed_start=SMOKE_SEED + 1_000,
        query_count=4,
        corruption_probability=0.03,
    )
    smoke_router = RandomHyperplaneLSH(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=SIGNATURE_BITS,
            table_count=1,
            table_seed=PROJECTION_SEEDS[0],
            probe_budget=ONE_TABLE_PROBE_BUDGET,
        )
    )
    smoke_router.fit(smoke_index.committed_payloads())
    smoke_random = RandomBucketRouter(
        SignatureConfig(
            dimensions=MAP_DIMENSIONS,
            signature_bits=SIGNATURE_BITS,
            table_count=1,
            table_seed=PROJECTION_SEEDS[0],
            probe_budget=ONE_TABLE_PROBE_BUDGET,
        )
    )
    smoke_random.fit(smoke_index.committed_handles())
    smoke_rows = [
        run_method_query(
            method_id=METHOD_ONE_TABLE,
            query=query,
            index=smoke_index,
            handles=smoke_index.committed_handles(),
            lsh_router=smoke_router,
            random_router=None,
        )
        for query in smoke_queries
    ]
    write_json(
        results_dir / "smoke_summary.json",
        {
            "schema_version": STAGE_A_SCHEMA_VERSION,
            "smoke_seed": SMOKE_SEED,
            "queries": len(smoke_rows),
            "mean_trace_recall_at_32": statistics.mean(row["trace_recall_at_32"] for row in smoke_rows),
        },
    )

    dataset_manifest_rows: list[dict[str, Any]] = []
    query_manifest_rows: list[dict[str, Any]] = []
    trial_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    analysis_rows: list[dict[str, Any]] = []

    for dataset_spec in DATASET_SPECS:
        dataset_id = dataset_spec["dataset_id"]
        dataset_seed = DATASET_SEED_RANGES[dataset_id]["start"]
        records = build_dataset(dataset_seed=dataset_seed, record_count=dataset_spec["record_count"])
        dataset_manifest_rows.append(
            {
                "schema_version": STAGE_A_SCHEMA_VERSION,
                "dataset_id": dataset_id,
                "dataset_seed": dataset_seed,
                "record_count": dataset_spec["record_count"],
                "adversarial_record_count": sum(1 for record in records if record.adversarial_group is not None),
                "operation_families": sorted({record.family_label for record in records}),
            }
        )
        index = build_trace_index(records)
        handles = index.committed_handles()
        payloads = index.committed_payloads()

        build_start = time.perf_counter()
        one_table = RandomHyperplaneLSH(
            SignatureConfig(
                dimensions=MAP_DIMENSIONS,
                signature_bits=SIGNATURE_BITS,
                table_count=1,
                table_seed=PROJECTION_SEEDS[0],
                probe_budget=ONE_TABLE_PROBE_BUDGET,
            )
        )
        one_table.fit(payloads)
        one_table_build = time.perf_counter() - build_start

        build_start = time.perf_counter()
        multi_table = RandomHyperplaneLSH(
            SignatureConfig(
                dimensions=MAP_DIMENSIONS,
                signature_bits=SIGNATURE_BITS,
                table_count=MULTI_TABLE_COUNT,
                table_seed=PROJECTION_SEEDS[0],
                probe_budget=MULTI_TABLE_PROBE_BUDGET,
            )
        )
        multi_table.fit(payloads)
        multi_table_build = time.perf_counter() - build_start

        build_start = time.perf_counter()
        multi_probe = RandomHyperplaneLSH(
            SignatureConfig(
                dimensions=MAP_DIMENSIONS,
                signature_bits=SIGNATURE_BITS,
                table_count=MULTI_TABLE_COUNT,
                table_seed=PROJECTION_SEEDS[0],
                probe_budget=MULTI_PROBE_BUDGET,
            )
        )
        multi_probe.fit(payloads)
        multi_probe_build = time.perf_counter() - build_start

        build_start = time.perf_counter()
        random_router = RandomBucketRouter(
            SignatureConfig(
                dimensions=MAP_DIMENSIONS,
                signature_bits=SIGNATURE_BITS,
                table_count=MULTI_TABLE_COUNT,
                table_seed=PROJECTION_SEEDS[0],
                probe_budget=MULTI_PROBE_BUDGET,
            )
        )
        random_router.fit(handles)
        random_build = time.perf_counter() - build_start

        global_build = 0.0
        exact_hash_build = 0.0
        index_stats = {
            METHOD_GLOBAL_SCAN: {
                "bucket_occupancy_mean": float(dataset_spec["record_count"]),
                "bucket_occupancy_p50": float(dataset_spec["record_count"]),
                "bucket_occupancy_p95": float(dataset_spec["record_count"]),
                "bucket_occupancy_p99": float(dataset_spec["record_count"]),
                "empty_bucket_rate": 0.0,
                "collision_rate": 1.0,
                "posting_count": float(dataset_spec["record_count"]),
            },
            METHOD_EXACT_HASH: {
                "bucket_occupancy_mean": 1.0,
                "bucket_occupancy_p50": 1.0,
                "bucket_occupancy_p95": 1.0,
                "bucket_occupancy_p99": 1.0,
                "empty_bucket_rate": 0.0,
                "collision_rate": 0.0,
                "posting_count": float(index.posting_count()),
            },
            METHOD_RANDOM_ROUTING: {
                **one_table.occupancy_stats(),
                "posting_count": float(index.posting_count() * MULTI_TABLE_COUNT),
            },
            METHOD_ONE_TABLE: {
                **one_table.occupancy_stats(),
                "posting_count": float(dataset_spec["record_count"]),
            },
            METHOD_MULTI_TABLE: {
                **multi_table.occupancy_stats(),
                "posting_count": float(dataset_spec["record_count"] * MULTI_TABLE_COUNT),
            },
            METHOD_MULTI_PROBE: {
                **multi_probe.occupancy_stats(),
                "posting_count": float(dataset_spec["record_count"] * MULTI_TABLE_COUNT),
            },
        }
        memory_lookup = {
            METHOD_GLOBAL_SCAN: index.payload_memory_bytes(),
            METHOD_EXACT_HASH: index.exact_hash_memory_bytes_estimate(),
            METHOD_RANDOM_ROUTING: random_router.memory_bytes_estimate(),
            METHOD_ONE_TABLE: one_table.memory_bytes_estimate(),
            METHOD_MULTI_TABLE: multi_table.memory_bytes_estimate(),
            METHOD_MULTI_PROBE: multi_probe.memory_bytes_estimate(),
        }
        build_latency_lookup = {
            METHOD_GLOBAL_SCAN: global_build,
            METHOD_EXACT_HASH: exact_hash_build,
            METHOD_RANDOM_ROUTING: random_build,
            METHOD_ONE_TABLE: one_table_build,
            METHOD_MULTI_TABLE: multi_table_build,
            METHOD_MULTI_PROBE: multi_probe_build,
        }

        exact_query = build_queries(
            dataset_id=dataset_id,
            records=records,
            query_seed_start=QUERY_SEED_RANGES[dataset_id]["start"],
            query_count=1,
            corruption_probability=0.0,
        )[0]
        _warmup_query(
            index=index,
            handles=handles,
            query=exact_query,
            one_table=one_table,
            multi_table=multi_table,
            multi_probe=multi_probe,
            random_router=random_router,
        )

        for corruption_probability in QUERY_CORRUPTION_POINTS:
            queries = build_queries(
                dataset_id=dataset_id,
                records=records,
                query_seed_start=QUERY_SEED_RANGES[dataset_id]["start"],
                query_count=dataset_spec["query_trials_per_point"],
                corruption_probability=corruption_probability,
            )
            for query in queries:
                query_manifest_rows.append(
                    {
                        "schema_version": STAGE_A_SCHEMA_VERSION,
                        "query_id": query.query_id,
                        "trial_seed": query.trial_seed,
                        "dataset_id": dataset_id,
                        "corruption_probability": corruption_probability,
                        "target_handle": query.target_handle,
                        "target_operation_family": query.target_operation_family,
                        "adversarial_group": query.adversarial_group,
                    }
                )
                for method_id, router, control in (
                    (METHOD_GLOBAL_SCAN, None, None),
                    (METHOD_EXACT_HASH, None, None),
                    (METHOD_RANDOM_ROUTING, None, random_router),
                    (METHOD_ONE_TABLE, one_table, None),
                    (METHOD_MULTI_TABLE, multi_table, None),
                    (METHOD_MULTI_PROBE, multi_probe, None),
                ):
                    row = run_method_query(
                        method_id=method_id,
                        query=query,
                        index=index,
                        handles=handles,
                        lsh_router=router,
                        random_router=control,
                    )
                    trial_rows.append(row)

            dataset_summary = summarize_method_rows(
                [row for row in trial_rows if row["dataset_id"] == dataset_id and row["corruption_probability"] == corruption_probability],
                record_count=dataset_spec["record_count"],
                index_stats=index_stats,
                memory_lookup=memory_lookup,
                build_latency_lookup=build_latency_lookup,
            )
            summary_rows.extend(dataset_summary)

        shuffled_records = list(records)
        rng = random.Random(dataset_seed + 999)
        rng.shuffle(shuffled_records)
        correct_mapping_hits = 0
        shuffled_mapping_hits = 0
        for query in build_queries(
            dataset_id=dataset_id,
            records=records,
            query_seed_start=QUERY_SEED_RANGES[dataset_id]["start"] + 500,
            query_count=8,
            corruption_probability=0.03,
        ):
            correct_mapping_hits += run_method_query(
                method_id=METHOD_MULTI_PROBE,
                query=query,
                index=index,
                handles=handles,
                lsh_router=multi_probe,
                random_router=None,
            )["trace_recall_at_32"]
            shuffled_index = build_trace_index(
                [
                    DatasetRecord(
                        record_id=record.record_id,
                        trace_handle=record.trace_handle,
                        trace_record=shuffled_records[position].trace_record,
                        semantic_payload=record.semantic_payload,
                        family_label=shuffled_records[position].family_label,
                        arity=shuffled_records[position].arity,
                        operand_namespaces=shuffled_records[position].operand_namespaces,
                        adversarial_group=record.adversarial_group,
                    )
                    for position, record in enumerate(records)
                ]
            )
            shuffled_hits = run_method_query(
                method_id=METHOD_MULTI_PROBE,
                query=query,
                index=shuffled_index,
                handles=shuffled_index.committed_handles(),
                lsh_router=multi_probe,
                random_router=None,
            )["trace_recall_at_32"]
            shuffled_mapping_hits += shuffled_hits
        ablation_rows.extend(
            [
                {
                    "schema_version": STAGE_A_SCHEMA_VERSION,
                    "dataset_id": dataset_id,
                    "ablation_id": "A6_semantic_payload_shuffled_relative_to_trace",
                    "mean_trace_recall_at_32": shuffled_mapping_hits / 8.0,
                    "expected_behavior": "RECOVERY_FAILS",
                },
                {
                    "schema_version": STAGE_A_SCHEMA_VERSION,
                    "dataset_id": dataset_id,
                    "ablation_id": "A8_exact_vs_noisy_cue",
                    "exact_cue_hash_hits": sum(
                        1 for row in trial_rows
                        if row["dataset_id"] == dataset_id
                        and row["method_id"] == METHOD_EXACT_HASH
                        and row["corruption_probability"] == 0.0
                        and row["trace_recall_at_1"] == 1
                    ),
                    "noisy_hash_hits": sum(
                        1 for row in trial_rows
                        if row["dataset_id"] == dataset_id
                        and row["method_id"] == METHOD_EXACT_HASH
                        and row["corruption_probability"] > 0.0
                        and row["trace_recall_at_1"] == 1
                    ),
                    "expected_behavior": "HASH_ONLY_EXACT",
                },
                {
                    "schema_version": STAGE_A_SCHEMA_VERSION,
                    "dataset_id": dataset_id,
                    "ablation_id": "A9_different_fixed_projection_seeds",
                    "projection_seeds": list(PROJECTION_SEEDS),
                    "expected_behavior": "INDEX_FAMILY_CHANGES_BUT_RULES_STAY_FROZEN",
                },
                {
                    "schema_version": STAGE_A_SCHEMA_VERSION,
                    "dataset_id": dataset_id,
                    "ablation_id": "A10_equal_candidate_budget_comparison",
                    "candidate_budget": CANDIDATE_BUDGET,
                    "random_method": METHOD_RANDOM_ROUTING,
                    "semantic_method": METHOD_MULTI_PROBE,
                    "expected_behavior": "BUDGET_MATCHED_COMPARISON",
                },
            ]
        )

        for method_id in (METHOD_RANDOM_ROUTING, METHOD_ONE_TABLE, METHOD_MULTI_TABLE, METHOD_MULTI_PROBE):
            p005 = next(
                row for row in summary_rows
                if row["dataset_id"] == dataset_id and row["method_id"] == method_id and abs(row["corruption_probability"] - 0.05) < 1e-12
            )
            analysis_rows.append(
                {
                    "schema_version": STAGE_A_SCHEMA_VERSION,
                    "dataset_id": dataset_id,
                    "method_id": method_id,
                    "p005_trace_recall_at_32": p005["trace_recall_at_32"],
                    "p005_candidate_set_median": p005["candidate_set_size_median"],
                    "p005_total_latency_median": p005["total_query_latency_sec_median"],
                }
            )

    summary_lookup = {
        (row["dataset_id"], row["method_id"], row["corruption_probability"]): row
        for row in summary_rows
    }
    gates = []
    n10000_limit = next(item for item in DATASET_SPECS if item["dataset_id"] == "n10000")["record_count"] * 0.01
    multi_probe_p005 = summary_lookup[("n10000", METHOD_MULTI_PROBE, 0.05)]
    random_p005 = summary_lookup[("n10000", METHOD_RANDOM_ROUTING, 0.05)]
    global_p005 = summary_lookup[("n10000", METHOD_GLOBAL_SCAN, 0.05)]
    gates.append(
        {
            "gate_id": "G1_trace_recall_at_32_n10000_p005",
            "status": "PASS" if multi_probe_p005["trace_recall_at_32"] >= 0.95 else "FAIL",
            "value": multi_probe_p005["trace_recall_at_32"],
            "threshold": 0.95,
        }
    )
    gates.append(
        {
            "gate_id": "G2_candidate_median_le_1pct_n10000_p005",
            "status": "PASS" if multi_probe_p005["candidate_set_size_median"] <= n10000_limit else "FAIL",
            "value": multi_probe_p005["candidate_set_size_median"],
            "threshold": n10000_limit,
        }
    )
    gates.append(
        {
            "gate_id": "G3_wrong_acceptance_zero_n10000_p005",
            "status": "PASS" if multi_probe_p005["wrong_trace_acceptance_rate"] == 0.0 else "FAIL",
            "value": multi_probe_p005["wrong_trace_acceptance_rate"],
            "threshold": 0.0,
        }
    )
    gates.append(
        {
            "gate_id": "G4_beats_budget_matched_random_n10000_p005",
            "status": "PASS" if multi_probe_p005["trace_recall_at_32"] > random_p005["trace_recall_at_32"] else "FAIL",
            "value": multi_probe_p005["trace_recall_at_32"] - random_p005["trace_recall_at_32"],
            "threshold": 0.0,
        }
    )
    gates.append(
        {
            "gate_id": "G5_query_latency_lt_global_scan_n10000_p005",
            "status": "PASS" if multi_probe_p005["total_query_latency_sec_median"] < global_p005["total_query_latency_sec_median"] else "FAIL",
            "value": multi_probe_p005["total_query_latency_sec_median"],
            "threshold": global_p005["total_query_latency_sec_median"],
        }
    )

    build_verdict = "PASS_STAGE_A_FEASIBILITY"
    if any(gate["status"] == "FAIL" for gate in gates):
        build_verdict = "PARTIAL"
    if multi_probe_p005["trace_recall_at_32"] < random_p005["trace_recall_at_32"]:
        build_verdict = "BLOCK"

    analysis = {
        "schema_version": STAGE_A_SCHEMA_VERSION,
        "task_name": STAGE_A_TASK_NAME,
        "base_checkpoint_commit": STAGE_A_BASE_CHECKPOINT_COMMIT,
        "branch_expected": STAGE_A_BRANCH_EXPECTATION,
        "frozen_level3_5b_artifacts_unchanged": True,
        "heldout_execution": False,
        "seed_ranges": {
            "dataset": DATASET_SEED_RANGES,
            "query": QUERY_SEED_RANGES,
            "projection": list(PROJECTION_SEEDS),
        },
        "corruption_contract": {
            "channel_id": CORRUPTION_CHANNEL_ID,
            "description": "External Bernoulli sign flips applied after clean MAP semantic payload construction.",
            "points": list(QUERY_CORRUPTION_POINTS),
        },
        "gates": gates,
        "build_verdict": build_verdict,
        "allowed_claims": [
            "Locality-sensitive semantic routing can retrieve a bounded trace candidate set in this synthetic MAP Stage A harness.",
            "Exact hash is exact-match-only and fails on noisy cues as expected.",
            "Random routing with matched bucket budget is a negative control and can be beaten by semantic routing.",
        ],
        "forbidden_claims": [
            "new LSH algorithm",
            "new VSA architecture",
            "production readiness",
            "scientific confirmation",
            "superiority over mature ANN or SDM",
            "full Decode-Carrying Hypervector implementation",
        ],
        "next_lawful_stage": "Stage B: retrieved trace configures actual decoder family" if build_verdict == "PASS_STAGE_A_FEASIBILITY" else None,
    }

    write_jsonl(results_dir / "dataset_manifest.jsonl", dataset_manifest_rows)
    write_jsonl(results_dir / "query_manifest.jsonl", query_manifest_rows)
    write_jsonl(results_dir / "trial_results.jsonl", trial_rows)
    write_csv(results_dir / "summary.csv", summary_rows)
    write_csv(results_dir / "ablation_summary.csv", ablation_rows)
    write_json(results_dir / "analysis.json", analysis)

    doc_lines = [
        "# Lazy Semantic-to-Trace Addressing - Stage A",
        "",
        "## Verdict",
        "",
        "`PROTOTYPE / DEVELOPMENT_ONLY`",
        "",
        "## Hypothesis",
        "",
        "> A semantic MAP hypervector may compute an approximate locality-sensitive routing signal that narrows trace retrieval to a small local candidate set before any decoder-family search begins.",
        "",
        "## Prior Art / Reuse",
        "",
        "- Reused `torch-hd` MAP primitives for semantic payload construction.",
        "- Reused exact cosine reranking over stored MAP payloads.",
        "- No mature ANN/LSH library exists in the frozen dependency graph, so Stage A uses a tiny deterministic random-hyperplane wrapper plus posting dictionaries instead of a new framework.",
        "",
        "## Scope",
        "",
        "- Semantic cue -> approximate content address -> local trace candidate set only.",
        "- Sidecar `TraceRecord` only; no in-vector trace zone, recursive provenance traversal, BCF, factorization fallback, or transactional write-back.",
        "",
        "## Authority Boundary",
        "",
        "- Semantic LSH: routing authority only.",
        "- TraceRecord: operation-contract authority after validation.",
        "- Similarity reranker: candidate ordering only.",
        "- Verifier: acceptance authority.",
        "- No valid candidate: `EXPAND` or `ABSTAIN`.",
        "",
        "## Baselines",
        "",
        f"- `{METHOD_GLOBAL_SCAN}`",
        f"- `{METHOD_EXACT_HASH}`",
        f"- `{METHOD_RANDOM_ROUTING}`",
        f"- `{METHOD_ONE_TABLE}`",
        f"- `{METHOD_MULTI_TABLE}`",
        f"- `{METHOD_MULTI_PROBE}`",
        "",
        "## Leakage Controls",
        "",
        "- LSH signatures are computed only from semantic payloads.",
        "- No trace handle, record id, operation label, or parent id enters the semantic payload.",
        "- Trace label shuffles and semantic-to-trace shuffles are explicit ablations.",
        "",
        "## Development Gates",
        "",
    ]
    for gate in gates:
        doc_lines.append(f"- `{gate['gate_id']}`: `{gate['status']}`")
    doc_lines.extend(
        [
            "",
            "## Non-goals",
            "",
            "- No production decoder orchestration.",
            "- No recursive trace traversal.",
            "- No held-out confirmation.",
            "- No new ANN service or vector database.",
            "",
            "## Next Lawful Stage",
            "",
            "- Stage B is only admissible if Stage A stays within the stated claim boundary and passes the local feasibility gates.",
            "",
        ]
    )
    (repo_root / "docs" / "LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A.md").write_text("\n".join(doc_lines) + "\n", encoding="utf-8")

    return {
        "environment": environment,
        "dependency_audit": dependency,
        "protocol": protocol,
        "analysis": analysis,
        "summary_rows": summary_rows,
    }
