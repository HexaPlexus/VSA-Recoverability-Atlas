from __future__ import annotations

import hashlib
from dataclasses import dataclass

import torch

from .trace_record import TraceRecord, payload_checksum


@dataclass(frozen=True)
class TraceStoreEntry:
    trace_record: TraceRecord
    semantic_payload: torch.Tensor
    committed: bool
    family_label: str
    namespace_contract: tuple[str, ...]
    arity: int


class TraceIndex:
    def __init__(self) -> None:
        self._entries_by_handle: dict[str, TraceStoreEntry] = {}
        self._exact_hash_to_handles: dict[str, list[str]] = {}
        self._cached_committed_handles: list[str] | None = None
        self._cached_committed_entries: list[TraceStoreEntry] | None = None
        self._cached_committed_payload_matrix: torch.Tensor | None = None

    def _invalidate_cache(self) -> None:
        self._cached_committed_handles = None
        self._cached_committed_entries = None
        self._cached_committed_payload_matrix = None

    @staticmethod
    def exact_content_hash(payload: torch.Tensor) -> str:
        return payload_checksum(payload)

    def insert(self, entry: TraceStoreEntry) -> None:
        self._entries_by_handle[entry.trace_record.trace_handle] = entry
        self._invalidate_cache()
        if not entry.committed:
            return
        exact_hash = self.exact_content_hash(entry.semantic_payload)
        self._exact_hash_to_handles.setdefault(exact_hash, []).append(entry.trace_record.trace_handle)

    def committed_payloads(self) -> dict[str, torch.Tensor]:
        return {
            handle: entry.semantic_payload
            for handle, entry in self._entries_by_handle.items()
            if entry.committed
        }

    def committed_handles(self) -> list[str]:
        if self._cached_committed_handles is None:
            self._cached_committed_handles = [
                handle
                for handle, entry in self._entries_by_handle.items()
                if entry.committed
            ]
        return self._cached_committed_handles

    def committed_entries(self) -> list[TraceStoreEntry]:
        if self._cached_committed_entries is None:
            self._cached_committed_entries = [
                entry for entry in self._entries_by_handle.values() if entry.committed
            ]
        return self._cached_committed_entries

    def committed_payload_matrix(self) -> torch.Tensor:
        if self._cached_committed_payload_matrix is None:
            entries = self.committed_entries()
            self._cached_committed_payload_matrix = torch.stack(
                [entry.semantic_payload.detach().cpu().reshape(-1).to(dtype=torch.float32) for entry in entries],
                dim=0,
            )
        return self._cached_committed_payload_matrix

    def get(self, handle: str) -> TraceStoreEntry | None:
        entry = self._entries_by_handle.get(handle)
        if entry is None or not entry.committed:
            return None
        return entry

    def exact_lookup(self, payload: torch.Tensor) -> tuple[str, ...]:
        exact_hash = self.exact_content_hash(payload)
        return tuple(self._exact_hash_to_handles.get(exact_hash, ()))

    def posting_count(self) -> int:
        return sum(len(handles) for handles in self._exact_hash_to_handles.values())

    def payload_memory_bytes(self) -> int:
        return sum(
            int(entry.semantic_payload.nelement() * entry.semantic_payload.element_size())
            for entry in self._entries_by_handle.values()
            if entry.committed
        )

    def exact_hash_memory_bytes_estimate(self) -> int:
        total = 0
        for key, handles in self._exact_hash_to_handles.items():
            total += len(key.encode("utf-8"))
            total += sum(len(handle.encode("utf-8")) for handle in handles)
        return total
