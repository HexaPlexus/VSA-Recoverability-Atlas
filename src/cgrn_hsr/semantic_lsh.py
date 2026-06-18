from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

import torch


def _seed_from_text(text: str, seed: int) -> int:
    digest = hashlib.sha256(f"{text}:{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


@dataclass(frozen=True)
class SignatureConfig:
    dimensions: int
    signature_bits: int
    table_count: int
    table_seed: int
    probe_budget: int = 1
    routing_mode: str = "primary_only"


@dataclass(frozen=True)
class RoutingResult:
    candidate_handles: tuple[str, ...]
    primary_signatures: tuple[str, ...]
    probed_signatures: tuple[str, ...]
    expansion_used: bool
    duplicate_postings: int
    empty_primary_bucket: bool
    raw_postings_retrieved: int = 0
    probed_table_indices: tuple[int, ...] = ()
    probe_margins: tuple[float, ...] = ()


@dataclass(frozen=True)
class ProbeEvent:
    table_index: int
    signature: str
    is_primary: bool
    estimated_cost: float


class RandomHyperplaneLSH:
    def __init__(self, config: SignatureConfig) -> None:
        self.config = config
        self._projections = self._build_projections()
        self._tables: list[dict[str, list[str]]] = [dict() for _ in range(self.config.table_count)]

    def _build_projections(self) -> list[torch.Tensor]:
        projections: list[torch.Tensor] = []
        for table_index in range(self.config.table_count):
            generator = torch.Generator(device="cpu")
            generator.manual_seed(self.config.table_seed + table_index)
            projections.append(
                torch.randn(
                    self.config.signature_bits,
                    self.config.dimensions,
                    generator=generator,
                    dtype=torch.float32,
                )
            )
        return projections

    def table_count(self) -> int:
        return self.config.table_count

    def projections(self) -> list[torch.Tensor]:
        return [projection.clone() for projection in self._projections]

    def fit(self, payloads_by_handle: dict[str, torch.Tensor]) -> None:
        self._tables = [dict() for _ in range(self.config.table_count)]
        for handle, payload in payloads_by_handle.items():
            table_signatures = self.signatures(payload)
            for table_index, signature in enumerate(table_signatures):
                self._tables[table_index].setdefault(signature, []).append(handle)

    def signatures(self, payload: torch.Tensor) -> tuple[str, ...]:
        flat = payload.detach().cpu().reshape(-1).to(dtype=torch.float32)
        values: list[str] = []
        for projection in self._projections:
            dots = projection @ flat
            bits = ["1" if value >= 0 else "0" for value in dots.tolist()]
            values.append("".join(bits))
        return tuple(values)

    def _probe_events(self, payload: torch.Tensor) -> tuple[tuple[str, ...], tuple[ProbeEvent, ...]]:
        flat = payload.detach().cpu().reshape(-1).to(dtype=torch.float32)
        primary: list[str] = []
        events: list[ProbeEvent] = []
        per_table_budget = max(1, self.config.probe_budget)
        for table_index, projection in enumerate(self._projections):
            dots = projection @ flat
            base_bits = ["1" if value >= 0 else "0" for value in dots.tolist()]
            base = "".join(base_bits)
            primary.append(base)
            events.append(
                ProbeEvent(
                    table_index=table_index,
                    signature=base,
                    is_primary=True,
                    estimated_cost=0.0,
                )
            )
            if per_table_budget <= 1:
                continue
            ranked_positions = sorted(
                range(len(base_bits)),
                key=lambda index: (abs(float(dots[index].item())), index),
            )
            for position in ranked_positions[: per_table_budget - 1]:
                neighbor = list(base_bits)
                neighbor[position] = "0" if neighbor[position] == "1" else "1"
                events.append(
                    ProbeEvent(
                        table_index=table_index,
                        signature="".join(neighbor),
                        is_primary=False,
                        estimated_cost=abs(float(dots[position].item())),
                    )
                )
        if self.config.routing_mode == "margin_probe":
            primary_events = [event for event in events if event.is_primary]
            secondary_events = [event for event in events if not event.is_primary]
            secondary_events.sort(
                key=lambda event: (event.estimated_cost, event.table_index, event.signature)
            )
            ordered = primary_events + secondary_events
        else:
            ordered = events
        return tuple(primary), tuple(ordered)

    def route(self, payload: torch.Tensor, *, candidate_budget: int) -> RoutingResult:
        primary_signatures, ordered = self._probe_events(payload)
        seen: set[str] = set()
        candidates: list[str] = []
        duplicate_postings = 0
        raw_postings_retrieved = 0
        empty_primary_bucket = True
        probed_signatures: list[str] = []
        probed_table_indices: list[int] = []
        probe_margins: list[float] = []
        for event in ordered:
            probed_signatures.append(event.signature)
            probed_table_indices.append(event.table_index)
            probe_margins.append(event.estimated_cost)
            records = self._tables[event.table_index].get(event.signature, [])
            raw_postings_retrieved += len(records)
            if event.is_primary and records:
                empty_primary_bucket = False
            for handle in records:
                if handle in seen:
                    duplicate_postings += 1
                    continue
                seen.add(handle)
                candidates.append(handle)
                if len(candidates) >= candidate_budget:
                    return RoutingResult(
                        candidate_handles=tuple(candidates),
                        primary_signatures=primary_signatures,
                        probed_signatures=tuple(probed_signatures),
                        expansion_used=any(not event.is_primary for event in ordered),
                        duplicate_postings=duplicate_postings,
                        empty_primary_bucket=empty_primary_bucket,
                        raw_postings_retrieved=raw_postings_retrieved,
                        probed_table_indices=tuple(probed_table_indices),
                        probe_margins=tuple(probe_margins),
                    )
        return RoutingResult(
            candidate_handles=tuple(candidates),
            primary_signatures=primary_signatures,
            probed_signatures=tuple(probed_signatures),
            expansion_used=any(not event.is_primary for event in ordered),
            duplicate_postings=duplicate_postings,
            empty_primary_bucket=empty_primary_bucket,
            raw_postings_retrieved=raw_postings_retrieved,
            probed_table_indices=tuple(probed_table_indices),
            probe_margins=tuple(probe_margins),
        )

    def occupancy_stats(self) -> dict[str, float]:
        occupancies = [len(bucket) for table in self._tables for bucket in table.values()]
        if not occupancies:
            return {
                "bucket_occupancy_mean": 0.0,
                "bucket_occupancy_p50": 0.0,
                "bucket_occupancy_p95": 0.0,
                "bucket_occupancy_p99": 0.0,
                "empty_bucket_rate": 1.0,
                "collision_rate": 0.0,
            }
        values = sorted(float(item) for item in occupancies)

        def quantile(q: float) -> float:
            if len(values) == 1:
                return values[0]
            index = (len(values) - 1) * q
            lower = int(index)
            upper = min(len(values) - 1, lower + 1)
            weight = index - lower
            return values[lower] * (1.0 - weight) + values[upper] * weight

        non_singletons = sum(1 for item in occupancies if item > 1)
        bucket_count = 2**self.config.signature_bits * self.config.table_count
        return {
            "bucket_occupancy_mean": sum(values) / len(values),
            "bucket_occupancy_p50": quantile(0.50),
            "bucket_occupancy_p95": quantile(0.95),
            "bucket_occupancy_p99": quantile(0.99),
            "empty_bucket_rate": max(0.0, (bucket_count - len(occupancies)) / bucket_count),
            "collision_rate": non_singletons / len(occupancies),
        }

    def memory_bytes_estimate(self) -> int:
        projection_bytes = sum(int(projection.nelement() * projection.element_size()) for projection in self._projections)
        posting_bytes = 0
        for table in self._tables:
            for signature, handles in table.items():
                posting_bytes += len(signature.encode("utf-8"))
                posting_bytes += sum(len(handle.encode("utf-8")) for handle in handles)
        return projection_bytes + posting_bytes


class RandomBucketRouter:
    def __init__(self, config: SignatureConfig) -> None:
        self.config = config
        self._tables: list[dict[str, list[str]]] = [dict() for _ in range(self.config.table_count)]

    def fit(self, handles: list[str]) -> None:
        self._tables = [dict() for _ in range(self.config.table_count)]
        bucket_count = 2**self.config.signature_bits
        for table_index in range(self.config.table_count):
            for handle in handles:
                seed = _seed_from_text(handle, self.config.table_seed + table_index)
                bucket = seed % bucket_count
                signature = format(bucket, f"0{self.config.signature_bits}b")
                self._tables[table_index].setdefault(signature, []).append(handle)

    def route(self, *, query_key: str, candidate_budget: int) -> RoutingResult:
        primary: list[str] = []
        probed: list[str] = []
        probed_table_indices: list[int] = []
        bucket_count = 2**self.config.signature_bits
        rng = random.Random(_seed_from_text(query_key, self.config.table_seed))
        for table_index in range(self.config.table_count):
            bucket = rng.randrange(bucket_count)
            signature = format(bucket, f"0{self.config.signature_bits}b")
            primary.append(signature)
            probed.append(signature)
            probed_table_indices.append(table_index)
            if self.config.probe_budget > 1:
                for _ in range(self.config.probe_budget - 1):
                    neighbor_bucket = rng.randrange(bucket_count)
                    probed.append(format(neighbor_bucket, f"0{self.config.signature_bits}b"))
                    probed_table_indices.append(table_index)
        seen: set[str] = set()
        candidates: list[str] = []
        duplicate_postings = 0
        raw_postings_retrieved = 0
        empty_primary_bucket = True
        for table_index, signature in zip(probed_table_indices, probed, strict=True):
            records = self._tables[table_index].get(signature, [])
            raw_postings_retrieved += len(records)
            if signature in primary and records:
                empty_primary_bucket = False
            for handle in records:
                if handle in seen:
                    duplicate_postings += 1
                    continue
                seen.add(handle)
                candidates.append(handle)
                if len(candidates) >= candidate_budget:
                    return RoutingResult(
                        candidate_handles=tuple(candidates),
                        primary_signatures=tuple(primary),
                        probed_signatures=tuple(probed),
                        expansion_used=self.config.probe_budget > 1,
                        duplicate_postings=duplicate_postings,
                        empty_primary_bucket=empty_primary_bucket,
                        raw_postings_retrieved=raw_postings_retrieved,
                        probed_table_indices=tuple(probed_table_indices),
                        probe_margins=tuple(0.0 for _ in probed),
                    )
        return RoutingResult(
            candidate_handles=tuple(candidates),
            primary_signatures=tuple(primary),
            probed_signatures=tuple(probed),
            expansion_used=self.config.probe_budget > 1,
            duplicate_postings=duplicate_postings,
            empty_primary_bucket=empty_primary_bucket,
            raw_postings_retrieved=raw_postings_retrieved,
            probed_table_indices=tuple(probed_table_indices),
            probe_margins=tuple(0.0 for _ in probed),
        )

    def memory_bytes_estimate(self) -> int:
        posting_bytes = 0
        for table in self._tables:
            for signature, handles in table.items():
                posting_bytes += len(signature.encode("utf-8"))
                posting_bytes += sum(len(handle.encode("utf-8")) for handle in handles)
        return posting_bytes
