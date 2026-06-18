from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch

TRACE_RECORD_SCHEMA_VERSION = "lazy-trace-stage-a-trace-record-v1"
TRACE_VALID = "VALID"
TRACE_SCHEMA_MISMATCH = "SCHEMA_VERSION_MISMATCH"
TRACE_MALFORMED = "MALFORMED_TRACE"
TRACE_CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
TRACE_RECORD_ASSOCIATION_MISMATCH = "RECORD_ASSOCIATION_MISMATCH"
TRACE_OPERATION_FAMILY_MISMATCH = "OPERATION_FAMILY_MISMATCH"

ALLOWED_OPERATION_FAMILIES = (
    "MAP_BIND_2",
    "MAP_BIND_3",
    "MAP_BUNDLE_3",
    "MAP_BUNDLE_5",
    "MAP_PERMUTE_K",
    "MAP_BIND_THEN_BUNDLE",
)


def payload_sign_bits(payload: torch.Tensor) -> np.ndarray:
    flat = payload.detach().cpu().reshape(-1)
    bits = (flat >= 0).to(dtype=torch.uint8).numpy()
    return bits.astype(np.uint8, copy=False)


def payload_checksum(payload: torch.Tensor) -> str:
    bits = payload_sign_bits(payload)
    packed = np.packbits(bits, bitorder="little").tobytes()
    return hashlib.sha256(packed).hexdigest()


@dataclass(frozen=True)
class TraceRecord:
    trace_handle: str
    record_id: str
    operation_family: str
    algebra: str
    arity: int
    operand_namespaces: tuple[str, ...]
    operation_parameters: dict[str, int | str]
    parent_handles: tuple[str, ...]
    semantic_payload_checksum: str
    schema_version: str = TRACE_RECORD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operand_namespaces"] = list(self.operand_namespaces)
        payload["parent_handles"] = list(self.parent_handles)
        payload["operation_parameters"] = dict(sorted(self.operation_parameters.items()))
        return payload

    def stable_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def stable_bytes(self) -> bytes:
        return self.stable_json().encode("utf-8")


@dataclass(frozen=True)
class TraceValidationResult:
    status: str
    message: str

    @property
    def is_valid(self) -> bool:
        return self.status == TRACE_VALID


def validate_trace_dict(payload: dict[str, Any]) -> TraceValidationResult:
    required_keys = {
        "trace_handle",
        "record_id",
        "operation_family",
        "algebra",
        "arity",
        "operand_namespaces",
        "operation_parameters",
        "parent_handles",
        "semantic_payload_checksum",
        "schema_version",
    }
    if set(payload.keys()) != required_keys:
        return TraceValidationResult(
            status=TRACE_MALFORMED,
            message="TraceRecord keys do not match the frozen schema.",
        )
    if payload["schema_version"] != TRACE_RECORD_SCHEMA_VERSION:
        return TraceValidationResult(
            status=TRACE_SCHEMA_MISMATCH,
            message="TraceRecord schema version mismatch.",
        )
    if payload["operation_family"] not in ALLOWED_OPERATION_FAMILIES:
        return TraceValidationResult(
            status=TRACE_MALFORMED,
            message="TraceRecord operation family is outside the allowed frozen set.",
        )
    if not isinstance(payload["arity"], int) or payload["arity"] <= 0:
        return TraceValidationResult(
            status=TRACE_MALFORMED,
            message="TraceRecord arity must be a positive integer.",
        )
    if len(payload["operand_namespaces"]) != payload["arity"]:
        return TraceValidationResult(
            status=TRACE_MALFORMED,
            message="TraceRecord arity must match operand namespace count.",
        )
    if not isinstance(payload["operation_parameters"], dict):
        return TraceValidationResult(
            status=TRACE_MALFORMED,
            message="TraceRecord operation parameters must be a typed mapping.",
        )
    return TraceValidationResult(status=TRACE_VALID, message="TraceRecord validated.")


def trace_record_from_dict(payload: dict[str, Any]) -> tuple[TraceRecord | None, TraceValidationResult]:
    validation = validate_trace_dict(payload)
    if not validation.is_valid:
        return None, validation
    return (
        TraceRecord(
            trace_handle=str(payload["trace_handle"]),
            record_id=str(payload["record_id"]),
            operation_family=str(payload["operation_family"]),
            algebra=str(payload["algebra"]),
            arity=int(payload["arity"]),
            operand_namespaces=tuple(str(value) for value in payload["operand_namespaces"]),
            operation_parameters={str(key): value for key, value in payload["operation_parameters"].items()},
            parent_handles=tuple(str(value) for value in payload["parent_handles"]),
            semantic_payload_checksum=str(payload["semantic_payload_checksum"]),
            schema_version=str(payload["schema_version"]),
        ),
        validation,
    )
