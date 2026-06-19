from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn.functional as F

from .trace_index import TraceStoreEntry
from .trace_record import (
    TRACE_CHECKSUM_MISMATCH,
    TRACE_OPERATION_FAMILY_MISMATCH,
    TRACE_RECORD_ASSOCIATION_MISMATCH,
    TRACE_VALID,
    TraceValidationResult,
    payload_checksum,
    trace_record_from_dict,
)

DECISION_ACCEPT = "ACCEPT"
DECISION_EXPAND = "EXPAND"
DECISION_ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class RerankedCandidate:
    handle: str
    similarity: float
    validation_status: str
    validation_message: str
    algebra: str
    operation_family: str
    arity: int
    operand_namespaces: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    parent_handles: tuple[str, ...]
    record_id: str
    semantic_payload_checksum: str


@dataclass(frozen=True)
class VerificationDecision:
    decision: str
    accepted_handle: str | None
    top1_similarity: float | None
    top2_similarity: float | None
    margin: float | None
    reranking_latency_sec: float
    candidate_count: int
    validated_candidates: tuple[RerankedCandidate, ...]


def validate_entry(entry: TraceStoreEntry) -> TraceValidationResult:
    trace_record, validation = trace_record_from_dict(entry.trace_record.to_dict())
    if not validation.is_valid or trace_record is None:
        return validation
    if trace_record.record_id != entry.trace_record.record_id:
        return TraceValidationResult(
            status=TRACE_RECORD_ASSOCIATION_MISMATCH,
            message="Trace record id does not match authoritative entry.",
        )
    if trace_record.operation_family != entry.family_label:
        return TraceValidationResult(
            status=TRACE_OPERATION_FAMILY_MISMATCH,
            message="Trace operation family does not match authoritative entry family.",
        )
    if payload_checksum(entry.semantic_payload) != trace_record.semantic_payload_checksum:
        return TraceValidationResult(
            status=TRACE_CHECKSUM_MISMATCH,
            message="Trace checksum does not match the stored semantic payload.",
        )
    return TraceValidationResult(status=TRACE_VALID, message="Trace validated against the authoritative store.")


def rerank_candidates(
    query_payload: torch.Tensor,
    entries: list[TraceStoreEntry],
    *,
    candidate_matrix: torch.Tensor | None = None,
    top_k: int | None = None,
    validation_cache: Mapping[str, TraceValidationResult] | None = None,
) -> tuple[list[RerankedCandidate], float]:
    start = time.perf_counter()
    if not entries:
        return [], time.perf_counter() - start
    query = query_payload.detach().cpu().reshape(1, -1).to(dtype=torch.float32)
    payloads = (
        candidate_matrix
        if candidate_matrix is not None
        else torch.stack(
            [entry.semantic_payload.detach().cpu().reshape(-1).to(dtype=torch.float32) for entry in entries],
            dim=0,
        )
    )
    similarities = F.cosine_similarity(query, payloads, dim=1)
    order = sorted(
        range(len(entries)),
        key=lambda index: (
            -float(similarities[index].item()),
            entries[index].trace_record.trace_handle,
            entries[index].trace_record.record_id,
        ),
    )
    if top_k is not None and top_k < len(order):
        order = order[:top_k]
    ranked: list[RerankedCandidate] = []
    for index in order:
        entry = entries[index]
        handle = entry.trace_record.trace_handle
        validation = (
            validation_cache[handle]
            if validation_cache is not None and handle in validation_cache
            else validate_entry(entry)
        )
        ranked.append(
            RerankedCandidate(
                handle=handle,
                similarity=float(similarities[index].item()),
                validation_status=validation.status,
                validation_message=validation.message,
                algebra=entry.trace_record.algebra,
                operation_family=entry.trace_record.operation_family,
                arity=entry.trace_record.arity,
                operand_namespaces=entry.trace_record.operand_namespaces,
                operation_parameters=dict(entry.trace_record.operation_parameters),
                parent_handles=entry.trace_record.parent_handles,
                record_id=entry.trace_record.record_id,
                semantic_payload_checksum=entry.trace_record.semantic_payload_checksum,
            )
        )
    return ranked, time.perf_counter() - start


def decide_candidate(
    reranked: list[RerankedCandidate],
    *,
    rerank_k: int,
    accept_similarity_threshold: float,
    accept_margin: float,
    expansion_available: bool,
) -> VerificationDecision:
    clipped = reranked[:rerank_k]
    if not clipped:
        return VerificationDecision(
            decision=DECISION_EXPAND if expansion_available else DECISION_ABSTAIN,
            accepted_handle=None,
            top1_similarity=None,
            top2_similarity=None,
            margin=None,
            reranking_latency_sec=0.0,
            candidate_count=0,
            validated_candidates=tuple(),
        )
    top1 = clipped[0]
    top2 = clipped[1] if len(clipped) > 1 else None
    margin = top1.similarity - (top2.similarity if top2 is not None else 0.0)
    if (
        top1.validation_status == TRACE_VALID
        and top1.similarity >= accept_similarity_threshold
        and margin >= accept_margin
    ):
        decision = DECISION_ACCEPT
        accepted_handle = top1.handle
    else:
        decision = DECISION_EXPAND if expansion_available else DECISION_ABSTAIN
        accepted_handle = None
    return VerificationDecision(
        decision=decision,
        accepted_handle=accepted_handle,
        top1_similarity=top1.similarity,
        top2_similarity=top2.similarity if top2 is not None else None,
        margin=margin,
        reranking_latency_sec=0.0,
        candidate_count=len(clipped),
        validated_candidates=tuple(clipped),
    )
