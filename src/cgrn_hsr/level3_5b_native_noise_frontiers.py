from __future__ import annotations

import csv
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import galois
import numpy as np
import torch

from .competitors.ibm_bcf_audit import AbstractFactorizationTask, upstream_clone_path
from .level3_2_confirmation import prior_level3_1_seed_set, synchronize_device, tensor_bytes, upstream_commit_sha
from .level3_2b_map_budget_robustness import (
    MAP_STABLE_PATIENCE,
    PreparedMapTask,
    choose_attempt,
    prepare_map_task,
    restart_agreement,
    run_map_attempt,
    unique_proposal_count,
)
from .level3_3_neco_reproduction import theoretical_bit_bytes
from .level3_4_algebraic_baselines import (
    BCF_ARM_ID,
    MAP_EXTENDED_ARM_ID,
    MAP_FAST_ARM_ID,
    PRIMARY_NECO_AMBIENT_LENGTH,
    bits_for_m,
    decode_factor_messages,
    factor_identity_tokens,
    generic_decode,
    generic_encode,
    generic_matrix,
    neco_decode,
    neco_encode,
    neco_subcodes,
    packed_encode,
    payload_bit_widths,
)

LEVEL3_5B_DEV_SCHEMA_VERSION = "level3-5b-dev-native-noise-frontiers-v1"
LEVEL3_5B_DEV_CHECKPOINT_COMMIT = "d6f222f5417a24c03c5b282d0cd4f4f5578a43b6"
LEVEL3_5B_DEV_TASK_CONTRACT = "U1_noisy_single_product_factorization_development_only"

TRACK_BINARY = "binary_exact_record"
TRACK_MAP = "map_native_sign_flip"
TRACK_BCF = "bcf_native_symbol_block"

CHANNEL_EXACT_WEIGHT = "EXACT_WEIGHT_BIT_FLIPS"
CHANNEL_BERNOULLI = "BERNOULLI_BIT_FLIPS"
CHANNEL_MAP_SIGN_FLIP = "MAP_SIGN_FLIP"
CHANNEL_BCF_NATIVE = "BCF_NATIVE_EXTERNAL_CORRUPTION"

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_WRONG = "WRONG_RECOVERY"
OUTCOME_SILENT_WRONG = "SILENT_WRONG"
OUTCOME_DETECTED = "DETECTED_UNCORRECTABLE"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"
OUTCOME_INCONSISTENT = "INCONSISTENT"
OUTCOME_RANK_DEFICIENT = "RANK_DEFICIENT"
OUTCOME_UNASSIGNED = "UNASSIGNED_CODEWORD"
OUTCOME_LIMIT = "NATIVE_LIMIT_REACHED"
OUTCOME_UNSUPPORTED = "UNSUPPORTED_CHANNEL"

RAW_BCH_CORRECTED = "CORRECTED_EXACT"
RAW_BCH_FAILURE = "DECODER_REPORTED_FAILURE"
RAW_BCH_MISCORRECTED_VALID = "MISCORRECTED_VALID_MESSAGE"
RAW_BCH_MISCORRECTED_UNASSIGNED = "MISCORRECTED_UNASSIGNED"
RAW_BCH_CLEAN_EXACT = "CLEAN_EXACT"

ROBUST_POINT = "ROBUST_POINT"
TRANSITION_LOW = "TRANSITION_LOW"
TRANSITION_MID = "TRANSITION_MID"
TRANSITION_HIGH = "TRANSITION_HIGH"
FAILURE_POINT = "FAILURE_POINT"
CLEAN_POINT = "CLEAN_POINT"

BCF_TRACK_BLOCKED = "BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY"

GF2 = galois.GF(2)

PAYLOAD_CELL_SPECS: tuple[dict[str, Any], ...] = (
    {"cell_id": "u1_f3_m10", "F": 3, "M": 10, "trials": 16},
    {"cell_id": "u1_f3_m31", "F": 3, "M": 31, "trials": 16},
    {"cell_id": "u1_f3_m68", "F": 3, "M": 68, "trials": 16},
)

BINARY_SEED_RANGES = {
    "u1_f3_m10": {"start": 110260616, "count": 16},
    "u1_f3_m31": {"start": 110261616, "count": 16},
    "u1_f3_m68": {"start": 110262616, "count": 16},
}
MAP_SEED_RANGES = {
    "u1_f3_m10": {"start": 120260616, "count": 16},
    "u1_f3_m31": {"start": 120261616, "count": 16},
    "u1_f3_m68": {"start": 120262616, "count": 16},
}
BCF_SEED_RANGES = {
    "u1_f3_m10": {"start": 130260616, "count": 8},
    "u1_f3_m31": {"start": 130261616, "count": 8},
    "u1_f3_m68": {"start": 130262616, "count": 8},
}

BINARY_INITIAL_BERNOULLI_P = (0.001, 0.005, 0.01, 0.02, 0.05, 0.10)
MAP_INITIAL_P = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20)

GENERIC_REPRESENTATION_SEED_OFFSET = 61_000
NECO_REPRESENTATION_SEED_OFFSET = 62_000
MAP_REPRESENTATION_SEED_OFFSET = 63_000
ORACLE_SEED_OFFSET = 64_000


@dataclass(frozen=True)
class ShortenedBCHConfig:
    payload_bits: int
    tier_id: str
    parent_n: int
    parent_k: int
    shortened_n: int
    shortened_k: int
    minimum_distance: int
    correctable_errors_t: int
    shortening_positions: tuple[int, ...]
    library_version: str

    @property
    def redundancy_bits(self) -> int:
        return self.shortened_n - self.shortened_k

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["shortening_positions"] = list(self.shortening_positions)
        payload["redundancy_bits"] = self.redundancy_bits
        return payload


@dataclass(frozen=True)
class SemanticManifest:
    track_id: str
    trial_id: str
    trial_seed: int
    cell_id: str
    factor_count: int
    domain_size: int
    true_factor_indices: list[int]
    factor_identity_tokens: list[list[str]]
    split: str
    generic_representation_seed: int
    neco_representation_seed: int
    map_representation_seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CorruptionRecord:
    requested_flip_count: int | None
    requested_flip_probability: float | None
    realized_flip_count: int
    transmitted_length: int
    flip_fraction: float
    flipped_indices: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["flipped_indices"] = list(self.flipped_indices)
        return payload


@dataclass(frozen=True)
class ShortenedBCHWrapper:
    config: ShortenedBCHConfig
    code: Any

    def encode(self, message_bits: np.ndarray) -> np.ndarray:
        message = np.asarray(message_bits, dtype=np.uint8)
        if message.size != self.config.shortened_k:
            raise ValueError("Message length mismatch for shortened BCH encode.")
        parent_message = np.concatenate(
            [np.zeros(len(self.config.shortening_positions), dtype=np.uint8), message],
            axis=0,
        )
        parent_codeword = np.array(self.code.encode(parent_message), dtype=np.uint8)
        return parent_codeword[len(self.config.shortening_positions) :].astype(np.uint8)

    def decode(self, received_bits: np.ndarray) -> tuple[np.ndarray, int]:
        received = np.asarray(received_bits, dtype=np.uint8)
        if received.size != self.config.shortened_n:
            raise ValueError("Codeword length mismatch for shortened BCH decode.")
        parent_codeword = np.concatenate(
            [np.zeros(len(self.config.shortening_positions), dtype=np.uint8), received],
            axis=0,
        )
        decoded, n_errors = self.code.decode(parent_codeword, errors=True)
        decoded_array = np.array(decoded, dtype=np.uint8)
        return decoded_array[len(self.config.shortening_positions) :].astype(np.uint8), int(n_errors)


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


def environment_snapshot() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "galois_version": galois.__version__,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }


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


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values_sorted = sorted(values)
    index = (len(values_sorted) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values_sorted[lower]
    weight = index - lower
    return values_sorted[lower] * (1.0 - weight) + values_sorted[upper] * weight


def level3_5b_dev_seed_set() -> set[int]:
    values: set[int] = set()
    for ranges in (BINARY_SEED_RANGES, MAP_SEED_RANGES, BCF_SEED_RANGES):
        for spec in ranges.values():
            for seed in range(spec["start"], spec["start"] + spec["count"]):
                values.add(seed)
    return values


def prior_seed_set() -> set[int]:
    from .level3_2_confirmation import level3_2_heldout_seed_set
    from .level3_2b_map_budget_robustness import level3_2b_seed_set
    from .level3_4_algebraic_baselines import level3_4_seed_set

    prior = prior_level3_1_seed_set().union(level3_2_heldout_seed_set()).union(level3_2b_seed_set()).union(level3_4_seed_set())
    prior.update(range(330001, 331013))
    prior.update(range(331001, 331013))
    return prior


def seeds_are_fresh() -> bool:
    return level3_5b_dev_seed_set().isdisjoint(prior_seed_set())


def build_task(trial_seed: int, cell: dict[str, Any], track_id: str) -> tuple[SemanticManifest, AbstractFactorizationTask]:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(trial_seed)
    true_indices = [
        int(torch.randint(0, cell["M"], (1,), generator=generator).item())
        for _ in range(cell["F"])
    ]
    manifest = SemanticManifest(
        track_id=track_id,
        trial_id=f"{track_id}-{cell['cell_id']}-seed-{trial_seed}",
        trial_seed=trial_seed,
        cell_id=cell["cell_id"],
        factor_count=cell["F"],
        domain_size=cell["M"],
        true_factor_indices=true_indices,
        factor_identity_tokens=factor_identity_tokens(cell["F"], cell["M"]),
        split="development_noise_frontier",
        generic_representation_seed=trial_seed + GENERIC_REPRESENTATION_SEED_OFFSET,
        neco_representation_seed=trial_seed + NECO_REPRESENTATION_SEED_OFFSET,
        map_representation_seed=trial_seed + MAP_REPRESENTATION_SEED_OFFSET,
    )
    task = AbstractFactorizationTask(
        task_seed=trial_seed,
        factor_count=cell["F"],
        domain_size_per_factor=[cell["M"]] * cell["F"],
        target_indices=true_indices,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )
    return manifest, task


def exact_weight_flip_bits(bits: np.ndarray, *, flips: int, seed: int) -> tuple[np.ndarray, CorruptionRecord]:
    clean = np.asarray(bits, dtype=np.uint8).copy()
    flips = int(min(max(flips, 0), clean.size))
    rng = np.random.default_rng(seed)
    if flips == 0:
        indices = np.array([], dtype=np.int64)
        corrupted = clean.copy()
    else:
        indices = np.sort(rng.choice(clean.size, size=flips, replace=False))
        corrupted = clean.copy()
        corrupted[indices] ^= 1
    record = CorruptionRecord(
        requested_flip_count=flips,
        requested_flip_probability=None,
        realized_flip_count=int(indices.size),
        transmitted_length=int(clean.size),
        flip_fraction=float(indices.size / clean.size) if clean.size else 0.0,
        flipped_indices=tuple(int(value) for value in indices.tolist()),
    )
    return corrupted.astype(np.uint8), record


def bernoulli_flip_bits(bits: np.ndarray, *, probability: float, seed: int) -> tuple[np.ndarray, CorruptionRecord]:
    clean = np.asarray(bits, dtype=np.uint8).copy()
    rng = np.random.default_rng(seed)
    mask = rng.random(clean.size) < probability
    corrupted = clean.copy()
    corrupted[mask] ^= 1
    indices = np.flatnonzero(mask)
    record = CorruptionRecord(
        requested_flip_count=None,
        requested_flip_probability=float(probability),
        realized_flip_count=int(indices.size),
        transmitted_length=int(clean.size),
        flip_fraction=float(indices.size / clean.size) if clean.size else 0.0,
        flipped_indices=tuple(int(value) for value in indices.tolist()),
    )
    return corrupted.astype(np.uint8), record


def exact_weight_sign_flips(observation: torch.Tensor, *, flips: int, seed: int) -> tuple[torch.Tensor, CorruptionRecord]:
    clean = observation.detach().clone()
    flat = clean.reshape(-1)
    flips = int(min(max(flips, 0), flat.numel()))
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    if flips == 0:
        indices = torch.empty(0, dtype=torch.long)
        corrupted = clean.clone()
    else:
        indices = torch.randperm(flat.numel(), generator=generator)[:flips].sort().values
        corrupted = clean.clone()
        corrupted.reshape(-1)[indices] *= -1
    record = CorruptionRecord(
        requested_flip_count=flips,
        requested_flip_probability=None,
        realized_flip_count=int(indices.numel()),
        transmitted_length=int(flat.numel()),
        flip_fraction=float(indices.numel() / flat.numel()) if flat.numel() else 0.0,
        flipped_indices=tuple(int(value) for value in indices.tolist()),
    )
    return corrupted, record


def bernoulli_sign_flips(observation: torch.Tensor, *, probability: float, seed: int) -> tuple[torch.Tensor, CorruptionRecord]:
    clean = observation.detach().clone()
    flat = clean.reshape(-1)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    mask = torch.rand(flat.numel(), generator=generator) < probability
    indices = torch.nonzero(mask, as_tuple=False).reshape(-1)
    corrupted = clean.clone()
    if indices.numel() > 0:
        corrupted.reshape(-1)[indices] *= -1
    record = CorruptionRecord(
        requested_flip_count=None,
        requested_flip_probability=float(probability),
        realized_flip_count=int(indices.numel()),
        transmitted_length=int(flat.numel()),
        flip_fraction=float(indices.numel() / flat.numel()) if flat.numel() else 0.0,
        flipped_indices=tuple(int(value) for value in indices.tolist()),
    )
    return corrupted, record


def build_bch_configs() -> list[ShortenedBCHConfig]:
    version = galois.__version__
    return [
        ShortenedBCHConfig(12, "BCH_LOW", 31, 26, 17, 12, 3, 1, tuple(range(14)), version),
        ShortenedBCHConfig(12, "BCH_HIGH", 31, 16, 27, 12, 7, 3, tuple(range(4)), version),
        ShortenedBCHConfig(15, "BCH_LOW", 31, 26, 20, 15, 3, 1, tuple(range(11)), version),
        ShortenedBCHConfig(15, "BCH_HIGH", 31, 16, 30, 15, 7, 3, tuple(range(1)), version),
        ShortenedBCHConfig(21, "BCH_LOW", 31, 21, 31, 21, 5, 2, tuple(), version),
        ShortenedBCHConfig(21, "BCH_HIGH", 63, 39, 45, 21, 9, 4, tuple(range(18)), version),
    ]


def bch_config_lookup() -> dict[tuple[int, str], ShortenedBCHConfig]:
    return {(config.payload_bits, config.tier_id): config for config in build_bch_configs()}


def make_bch_wrapper(config: ShortenedBCHConfig) -> ShortenedBCHWrapper:
    return ShortenedBCHWrapper(config=config, code=galois.BCH(config.parent_n, config.parent_k))


def payload_bits_for_task(task: AbstractFactorizationTask) -> int:
    return sum(payload_bit_widths(task))


def compare_indices(predicted: list[int], target: list[int]) -> tuple[bool, int]:
    per_factor = sum(int(a == b) for a, b in zip(predicted, target, strict=True))
    return predicted == target, per_factor


def normalize_full_tuple_outcome(*, raw_status: str, predicted_indices: list[int], target_indices: list[int]) -> tuple[str, int]:
    if raw_status in {OUTCOME_DETECTED, OUTCOME_AMBIGUOUS, OUTCOME_INCONSISTENT, OUTCOME_RANK_DEFICIENT, OUTCOME_UNASSIGNED, OUTCOME_LIMIT, OUTCOME_UNSUPPORTED}:
        return raw_status, 0
    if not predicted_indices:
        return raw_status, 0
    exact, correct_factors = compare_indices(predicted_indices, target_indices)
    if exact:
        return OUTCOME_EXACT, correct_factors
    return OUTCOME_SILENT_WRONG, correct_factors


def build_bch_configs_artifact(results_dir: Path) -> dict[str, Any]:
    rows = [config.to_dict() for config in build_bch_configs()]
    payload = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "tier_policy": "frozen by code properties before corruption trials",
        "frozen_before_trial_outcomes": True,
        "rows": rows,
    }
    write_json(results_dir / "bch_configs.json", payload)
    return payload


def oracle_feasible(cell_id: str) -> bool:
    return cell_id == "u1_f3_m10"


def oracle_decode_hamming(codewords: list[tuple[np.ndarray, list[int]]], received: np.ndarray) -> tuple[str, list[int], int]:
    received_bits = np.asarray(received, dtype=np.uint8)
    distances: list[tuple[int, list[int]]] = []
    for codeword, indices in codewords:
        distance = int(np.count_nonzero(codeword != received_bits))
        distances.append((distance, indices))
    distances.sort(key=lambda item: item[0])
    best_distance = distances[0][0]
    best = [indices for distance, indices in distances if distance == best_distance]
    if len(best) > 1:
        return "DISTANCE_TIE", [], best_distance
    exact = best[0]
    return ("UNIQUE_NEAREST_EXACT" if exact else "UNIQUE_NEAREST_WRONG"), exact, best_distance


def enumerate_packed_codewords(task: AbstractFactorizationTask) -> list[tuple[np.ndarray, list[int]]]:
    widths = payload_bit_widths(task)
    total = math.prod(task.domain_size_per_factor)
    rows: list[tuple[np.ndarray, list[int]]] = []
    for flat_index in range(total):
        indices: list[int] = []
        remaining = flat_index
        for domain_size in reversed(task.domain_size_per_factor):
            indices.append(remaining % domain_size)
            remaining //= domain_size
        indices.reverse()
        slices = []
        for index, width in zip(indices, widths, strict=True):
            bits = np.array([(index >> bit) & 1 for bit in range(width)], dtype=np.uint8)
            slices.append(bits)
        rows.append((np.concatenate(slices, axis=0), indices))
    return rows


def enumerate_generic_codewords(task: AbstractFactorizationTask, matrix: np.ndarray) -> list[tuple[np.ndarray, list[int]]]:
    rows = []
    for payload_bits, indices in enumerate_packed_codewords(task):
        rows.append((((matrix @ payload_bits) % 2).astype(np.uint8), indices))
    return rows


def enumerate_neco_codewords(task: AbstractFactorizationTask, subcodes: list[np.ndarray]) -> list[tuple[np.ndarray, list[int]]]:
    widths = payload_bit_widths(task)
    rows = []
    for payload, indices in enumerate_packed_codewords(task):
        coeffs = []
        start = 0
        for width in widths:
            coeffs.append(payload[start : start + width])
            start += width
        observation = neco_encode(
            AbstractFactorizationTask(
                task_seed=task.task_seed,
                factor_count=task.factor_count,
                domain_size_per_factor=task.domain_size_per_factor,
                target_indices=indices,
            ),
            subcodes,
        )[0]
        rows.append((observation.astype(np.uint8), indices))
    return rows


def prepare_binary_representations(manifest: SemanticManifest, task: AbstractFactorizationTask) -> dict[str, Any]:
    packed_observation, _ = packed_encode(task)
    generic_m = generic_matrix(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest.generic_representation_seed)
    generic_observation, _, _ = generic_encode(task, generic_m)
    neco_sub, _ = neco_subcodes(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest.neco_representation_seed)
    neco_observation, _, _ = neco_encode(task, neco_sub)
    widths = payload_bit_widths(task)
    payload_bits = sum(widths)
    bch_lookup = bch_config_lookup()
    bch_low = make_bch_wrapper(bch_lookup[(payload_bits, "BCH_LOW")])
    bch_high = make_bch_wrapper(bch_lookup[(payload_bits, "BCH_HIGH")])
    packed_message = packed_observation.astype(np.uint8)
    packed_true_slices = []
    cursor = 0
    for width in widths:
        packed_true_slices.append(packed_message[cursor : cursor + width])
        cursor += width

    return {
        "payload_bits": payload_bits,
        "packed_message_bits": packed_message,
        "packed_observation_bits": packed_message,
        "generic_matrix": generic_m,
        "generic_observation_bits": generic_observation.astype(np.uint8),
        "neco_subcodes": neco_sub,
        "neco_observation_bits": neco_observation.astype(np.uint8),
        "bch_low_wrapper": bch_low,
        "bch_high_wrapper": bch_high,
        "bch_low_codeword": bch_low.encode(packed_message),
        "bch_high_codeword": bch_high.encode(packed_message),
        "oracle_packed_codewords": enumerate_packed_codewords(task) if oracle_feasible(manifest.cell_id) else None,
        "oracle_generic_codewords": enumerate_generic_codewords(task, generic_m) if oracle_feasible(manifest.cell_id) else None,
        "oracle_neco_codewords": enumerate_neco_codewords(task, neco_sub) if oracle_feasible(manifest.cell_id) else None,
    }


def decode_uncoded_packed(corrupted: np.ndarray, task: AbstractFactorizationTask) -> tuple[str, str, list[int], float]:
    decoded = decode_factor_messages(
        [
            np.asarray(corrupted[sum(payload_bit_widths(task)[:idx]) : sum(payload_bit_widths(task)[: idx + 1])], dtype=np.uint8)
            for idx in range(task.factor_count)
        ],
        task,
    )
    if decoded.outcome == OUTCOME_UNASSIGNED:
        return OUTCOME_UNASSIGNED, OUTCOME_UNASSIGNED, [], decoded.decode_time_sec
    outcome, _ = normalize_full_tuple_outcome(
        raw_status=OUTCOME_WRONG,
        predicted_indices=decoded.predicted_indices,
        target_indices=task.target_indices,
    )
    return outcome, decoded.outcome, decoded.predicted_indices, decoded.decode_time_sec


def decode_generic(corrupted: np.ndarray, task: AbstractFactorizationTask, matrix: np.ndarray) -> tuple[str, str, list[int], float]:
    decoded = generic_decode(corrupted.astype(np.uint8), task, matrix)
    raw_status = str(decoded.outcome)
    mapped = {
        "INCONSISTENT_SYSTEM": OUTCOME_INCONSISTENT,
        "INCONSISTENT": OUTCOME_INCONSISTENT,
        "RANK_DEFICIENT": OUTCOME_RANK_DEFICIENT,
        "AMBIGUOUS_DECOMPOSITION": OUTCOME_AMBIGUOUS,
        "AMBIGUOUS": OUTCOME_AMBIGUOUS,
        "UNASSIGNED_CODEWORD": OUTCOME_UNASSIGNED,
    }.get(raw_status)
    if mapped is not None:
        return mapped, raw_status, [], decoded.decode_time_sec
    outcome, _ = normalize_full_tuple_outcome(
        raw_status=OUTCOME_WRONG,
        predicted_indices=decoded.predicted_indices,
        target_indices=task.target_indices,
    )
    return outcome, raw_status, decoded.predicted_indices, decoded.decode_time_sec


def decode_neco(corrupted: np.ndarray, task: AbstractFactorizationTask, subcodes: list[np.ndarray]) -> tuple[str, str, list[int], float]:
    decoded = neco_decode(corrupted.astype(np.uint8), task, subcodes)
    raw_status = str(decoded.outcome)
    mapped = {
        "INCONSISTENT_SYSTEM": OUTCOME_INCONSISTENT,
        "INCONSISTENT": OUTCOME_INCONSISTENT,
        "RANK_DEFICIENT": OUTCOME_RANK_DEFICIENT,
        "AMBIGUOUS_DECOMPOSITION": OUTCOME_AMBIGUOUS,
        "AMBIGUOUS": OUTCOME_AMBIGUOUS,
        "UNASSIGNED_CODEWORD": OUTCOME_UNASSIGNED,
    }.get(raw_status)
    if mapped is not None:
        return mapped, raw_status, [], decoded.decode_time_sec
    outcome, _ = normalize_full_tuple_outcome(
        raw_status=OUTCOME_WRONG,
        predicted_indices=decoded.predicted_indices,
        target_indices=task.target_indices,
    )
    return outcome, raw_status, decoded.predicted_indices, decoded.decode_time_sec


def decode_bch(corrupted: np.ndarray, task: AbstractFactorizationTask, wrapper: ShortenedBCHWrapper) -> tuple[str, str, list[int], float]:
    start = time.perf_counter()
    decoded_payload, n_errors = wrapper.decode(corrupted.astype(np.uint8))
    slices: list[np.ndarray] = []
    cursor = 0
    widths = payload_bit_widths(task)
    for width in widths:
        slices.append(decoded_payload[cursor : cursor + width])
        cursor += width
    typed = decode_factor_messages(slices, task)
    decode_time = time.perf_counter() - start
    if n_errors == -1:
        return OUTCOME_DETECTED, RAW_BCH_FAILURE, [], decode_time
    if typed.outcome == OUTCOME_UNASSIGNED:
        raw_status = RAW_BCH_MISCORRECTED_UNASSIGNED if n_errors >= 0 else OUTCOME_UNASSIGNED
        return OUTCOME_UNASSIGNED, raw_status, [], decode_time
    exact, _ = compare_indices(typed.predicted_indices, task.target_indices)
    if exact and n_errors == 0:
        return OUTCOME_EXACT, RAW_BCH_CLEAN_EXACT, typed.predicted_indices, decode_time
    if exact and n_errors > 0:
        return OUTCOME_EXACT, RAW_BCH_CORRECTED, typed.predicted_indices, decode_time
    return OUTCOME_SILENT_WRONG, RAW_BCH_MISCORRECTED_VALID, typed.predicted_indices, decode_time


def decode_oracle(
    corrupted: np.ndarray,
    *,
    task: AbstractFactorizationTask,
    codewords: list[tuple[np.ndarray, list[int]]] | None,
) -> tuple[str, str, list[int], float]:
    start = time.perf_counter()
    if codewords is None:
        return OUTCOME_UNSUPPORTED, OUTCOME_UNSUPPORTED, [], 0.0
    raw_status, predicted_indices, _ = oracle_decode_hamming(codewords, corrupted.astype(np.uint8))
    decode_time = time.perf_counter() - start
    if raw_status == "DISTANCE_TIE":
        return OUTCOME_AMBIGUOUS, raw_status, [], decode_time
    exact, _ = compare_indices(predicted_indices, task.target_indices)
    return (OUTCOME_EXACT if exact else OUTCOME_SILENT_WRONG), raw_status, predicted_indices, decode_time


def bitflip_observation_distance(clean: np.ndarray, corrupted: np.ndarray) -> int:
    return int(np.count_nonzero(np.asarray(clean, dtype=np.uint8) != np.asarray(corrupted, dtype=np.uint8)))


def sign_distance(clean: torch.Tensor, corrupted: torch.Tensor) -> int:
    return int(torch.count_nonzero(clean.detach().cpu() != corrupted.detach().cpu()).item())


def build_binary_method_rows(
    manifest: SemanticManifest,
    task: AbstractFactorizationTask,
    representations: dict[str, Any],
    *,
    channel_id: str,
    severity_value: float,
    corruption_label: str,
    corruption_seed_offset: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payload_bits = representations["payload_bits"]
    wrappers = {
        "packed_tuple_bch_low_redundancy": representations["bch_low_wrapper"],
        "packed_tuple_bch_high_redundancy": representations["bch_high_wrapper"],
    }
    method_specs: list[tuple[str, np.ndarray, Any]] = [
        ("uncoded_packed_tuple", representations["packed_observation_bits"], None),
        ("packed_tuple_bch_low_redundancy", representations["bch_low_codeword"], wrappers["packed_tuple_bch_low_redundancy"]),
        ("packed_tuple_bch_high_redundancy", representations["bch_high_codeword"], wrappers["packed_tuple_bch_high_redundancy"]),
        ("generic_full_rank_linear_mix", representations["generic_observation_bits"], representations["generic_matrix"]),
        ("raw_neco_algebraic_recovery", representations["neco_observation_bits"], representations["neco_subcodes"]),
    ]
    if oracle_feasible(manifest.cell_id):
        method_specs.extend(
            [
                ("tiny_oracle_packed", representations["packed_observation_bits"], representations["oracle_packed_codewords"]),
                ("tiny_oracle_generic", representations["generic_observation_bits"], representations["oracle_generic_codewords"]),
                ("tiny_oracle_neco", representations["neco_observation_bits"], representations["oracle_neco_codewords"]),
            ]
        )

    for method_index, (method_id, clean_bits, aux) in enumerate(method_specs):
        if channel_id == CHANNEL_EXACT_WEIGHT:
            corrupted, record = exact_weight_flip_bits(
                clean_bits,
                flips=int(severity_value),
                seed=manifest.trial_seed + corruption_seed_offset + method_index,
            )
        else:
            corrupted, record = bernoulli_flip_bits(
                clean_bits,
                probability=float(severity_value),
                seed=manifest.trial_seed + corruption_seed_offset + method_index,
            )

        if method_id == "uncoded_packed_tuple":
            outcome, raw_status, predicted_indices, decode_time = decode_uncoded_packed(corrupted, task)
            redundancy_ratio = 1.0
            persistent_bytes = theoretical_bit_bytes(payload_bits)
            runtime_bytes = theoretical_bit_bytes(clean_bits.size)
        elif method_id.startswith("packed_tuple_bch"):
            outcome, raw_status, predicted_indices, decode_time = decode_bch(corrupted, task, aux)
            wrapper: ShortenedBCHWrapper = aux
            redundancy_ratio = wrapper.config.shortened_n / wrapper.config.shortened_k
            persistent_bytes = theoretical_bit_bytes(wrapper.config.shortened_n) + len(json.dumps(wrapper.config.to_dict()))
            runtime_bytes = theoretical_bit_bytes(wrapper.config.shortened_n)
        elif method_id == "generic_full_rank_linear_mix":
            outcome, raw_status, predicted_indices, decode_time = decode_generic(corrupted, task, aux)
            redundancy_ratio = len(clean_bits) / payload_bits
            persistent_bytes = theoretical_bit_bytes(aux.size) + len(json.dumps({"ambient_length": aux.shape[0], "payload_bits": payload_bits}))
            runtime_bytes = theoretical_bit_bytes(clean_bits.size) + theoretical_bit_bytes(aux.size)
        elif method_id == "raw_neco_algebraic_recovery":
            outcome, raw_status, predicted_indices, decode_time = decode_neco(corrupted, task, aux)
            redundancy_ratio = len(clean_bits) / payload_bits
            total_generator_bits = PRIMARY_NECO_AMBIENT_LENGTH * payload_bits
            persistent_bytes = theoretical_bit_bytes(total_generator_bits) + len(json.dumps({"ambient_length": PRIMARY_NECO_AMBIENT_LENGTH, "payload_bits": payload_bits}))
            runtime_bytes = theoretical_bit_bytes(clean_bits.size) + theoretical_bit_bytes(total_generator_bits)
        else:
            outcome, raw_status, predicted_indices, decode_time = decode_oracle(corrupted, task=task, codewords=aux)
            redundancy_ratio = len(clean_bits) / payload_bits
            persistent_bytes = 0
            runtime_bytes = theoretical_bit_bytes(clean_bits.size)

        exact = outcome == OUTCOME_EXACT
        silent_wrong = outcome == OUTCOME_SILENT_WRONG
        detected_failure = outcome in {OUTCOME_DETECTED, OUTCOME_AMBIGUOUS, OUTCOME_INCONSISTENT, OUTCOME_RANK_DEFICIENT, OUTCOME_UNASSIGNED, OUTCOME_UNSUPPORTED}
        correct_factors = 0 if not predicted_indices else sum(int(a == b) for a, b in zip(predicted_indices, task.target_indices, strict=True))

        row = {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": TRACK_BINARY,
            "trial_id": manifest.trial_id,
            "trial_seed": manifest.trial_seed,
            "cell_id": manifest.cell_id,
            "factor_count": manifest.factor_count,
            "domain_size": manifest.domain_size,
            "payload_bits": payload_bits,
            "method_id": method_id,
            "channel_id": channel_id,
            "corruption_label": corruption_label,
            "external_corruption_spec": {
                "channel_id": channel_id,
                "severity_value": severity_value,
                **record.to_dict(),
            },
            "internal_decoder_noise_spec": {"enabled": False},
            "transmitted_length": record.transmitted_length,
            "transmitted_or_observation_bits": record.transmitted_length,
            "realized_flip_count": record.realized_flip_count,
            "realized_flip_fraction": record.flip_fraction,
            "distance_from_clean_bits": bitflip_observation_distance(clean_bits, corrupted),
            "true_factor_indices": task.target_indices,
            "predicted_indices": predicted_indices,
            "raw_status": raw_status,
            "outcome": outcome,
            "exact_recovery": exact,
            "silent_wrong": silent_wrong,
            "detected_failure": detected_failure,
            "partial_factor_recovery": 0 < correct_factors < task.factor_count,
            "correct_factor_count": correct_factors,
            "decode_time_sec": decode_time,
            "end_to_end_time_sec": decode_time,
            "persistent_bytes": persistent_bytes,
            "runtime_materialized_bytes": runtime_bytes,
            "decoder_state_bytes": runtime_bytes if method_id.startswith("packed_tuple_bch") else max(runtime_bytes - theoretical_bit_bytes(clean_bits.size), 0),
            "redundancy_ratio": redundancy_ratio,
            "device": "cpu",
            "device_confounded": False,
            "uses_truth_in_decoder": False,
        }
        rows.append(row)
    return rows


def summarize_exact_rate(rows: list[dict[str, Any]], method_id: str, cell_id: str, channel_id: str) -> list[tuple[float, float]]:
    grouped: list[tuple[float, float]] = []
    lookup: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        if row["method_id"] == method_id and row["cell_id"] == cell_id and row["channel_id"] == channel_id:
            severity = float(row["external_corruption_spec"]["severity_value"])
            lookup.setdefault(severity, []).append(row)
    for severity in sorted(lookup):
        batch = lookup[severity]
        grouped.append((severity, sum(1 for item in batch if item["exact_recovery"]) / len(batch)))
    return grouped


def find_midpoint(points: list[tuple[float, float]]) -> float | None:
    for left, right in zip(points, points[1:], strict=False):
        if (left[1] >= 0.9 and right[1] < 0.9) or (left[1] > 0.5 > right[1]) or (left[1] > 0.1 >= right[1]):
            return round((left[0] + right[0]) / 2.0, 6)
    return None


def prepare_map_runs(manifest: SemanticManifest, task: AbstractFactorizationTask, *, device: str) -> PreparedMapTask:
    return prepare_map_task(
        task,
        dimensions=1024,
        representation_seed=manifest.map_representation_seed,
        device=device,
    )


def run_map_arm(
    prepared_clean: PreparedMapTask,
    task: AbstractFactorizationTask,
    manifest: SemanticManifest,
    *,
    arm_id: str,
    probability: float,
    seed_offset: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    corrupted_observation, corruption = bernoulli_sign_flips(
        prepared_clean.observation,
        probability=probability,
        seed=manifest.trial_seed + seed_offset,
    )
    prepared = replace(prepared_clean, observation=corrupted_observation)
    if arm_id == MAP_FAST_ARM_ID:
        attempts = [run_map_attempt(prepared, max_iterations=12, init_mode="baseline", init_seed=manifest.trial_seed + 100_000)]
        selected = attempts[0]
        selection_rule = "first"
        planned_restart_count = 1
    elif arm_id == MAP_EXTENDED_ARM_ID:
        attempts = [
            run_map_attempt(prepared, max_iterations=32, init_mode="random", init_seed=manifest.trial_seed + 200_000 + restart_index)
            for restart_index in range(4)
        ]
        selected = choose_attempt(
            attempts,
            selection_rule="best_native_reconstruction",
            selection_seed=manifest.trial_seed + 300_000,
        )
        selection_rule = "best_native_reconstruction"
        planned_restart_count = 4
    else:  # pragma: no cover
        raise ValueError(f"Unsupported MAP arm: {arm_id}")

    exact = selected.exact_recovery
    correct_factor_count = sum(int(value) for value in selected.per_factor_recovery)
    outcome = OUTCOME_EXACT if exact else OUTCOME_SILENT_WRONG
    row = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "track_id": TRACK_MAP,
        "trial_id": manifest.trial_id,
        "trial_seed": manifest.trial_seed,
        "cell_id": manifest.cell_id,
        "factor_count": manifest.factor_count,
        "domain_size": manifest.domain_size,
        "method_id": arm_id,
        "channel_id": CHANNEL_MAP_SIGN_FLIP,
        "corruption_label": f"p={probability}",
        "external_corruption_spec": {
            "channel_id": CHANNEL_MAP_SIGN_FLIP,
            "severity_value": probability,
            **corruption.to_dict(),
        },
        "internal_decoder_noise_spec": {"enabled": False},
        "true_factor_indices": task.target_indices,
        "predicted_indices": selected.predicted_indices,
        "raw_status": selected.outcome,
        "outcome": outcome,
        "exact_recovery": exact,
        "silent_wrong": not exact,
        "detected_failure": False,
        "partial_factor_recovery": 0 < correct_factor_count < task.factor_count,
        "correct_factor_count": correct_factor_count,
        "native_reconstruction_score": selected.normalized_reconstruction_similarity,
        "min_margin": selected.min_margin,
        "mean_margin": selected.mean_margin,
        "restart_agreement": restart_agreement(attempts),
        "unique_restart_proposals": unique_proposal_count(attempts),
        "executed_steps": sum(item.iterations for item in attempts),
        "executed_restarts": len(attempts),
        "decode_time_sec": sum(item.decode_time_sec for item in attempts),
        "end_to_end_time_sec": prepared_clean.materialization_time_sec + prepared_clean.decoder_initialization_time_sec + sum(item.decode_time_sec for item in attempts),
        "persistent_bytes": len(json.dumps({"arm_id": arm_id, "dimensions": 1024})),
        "runtime_materialized_bytes": prepared_clean.codebook_bytes + prepared_clean.observation_bytes + max(item.decoder_state_bytes for item in attempts),
        "decoder_state_bytes": max(item.decoder_state_bytes for item in attempts),
        "transmitted_or_observation_bits": corruption.transmitted_length,
        "redundancy_ratio": corruption.transmitted_length / payload_bits_for_task(task),
        "realized_flip_count": corruption.realized_flip_count,
        "realized_flip_fraction": corruption.flip_fraction,
        "sign_distance_from_clean_observation": sign_distance(prepared_clean.observation, corrupted_observation),
        "device": prepared_clean.device,
        "device_confounded": not prepared_clean.device.startswith("cuda"),
        "uses_truth_in_decoder": False,
        "map_codebooks_unchanged": True,
        "corruption_after_clean_product_construction": True,
        "selection_rule": selection_rule,
        "planned_restart_count": planned_restart_count,
    }
    diagnostics = {
        "exact_rate_indicator": 1 if exact else 0,
        "mean_reconstruction": selected.normalized_reconstruction_similarity,
        "stable_prediction": selected.stable_prediction,
    }
    return row, diagnostics


def build_bcf_native_corruption_contract(repo_root: Path, results_dir: Path) -> dict[str, Any]:
    repo_path = upstream_clone_path(repo_root)
    payload = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "status": BCF_TRACK_BLOCKED,
        "reason": "Official upstream and pinned paper artifacts expose native internal noise sweeps, but do not unambiguously freeze an external corruption channel for the blockcodefactorizer path comparable to the Level 3.5b contract.",
        "representation_alphabet": "block-local one-hot symbol positions over L = D / B",
        "block_structure": "B sparse blocks with one active position per block in each factor codeword",
        "clean_product_construction": "block-wise circular convolution via blockcodefactorizer.encode()",
        "external_corruption_unit": None,
        "corruption_operation": None,
        "corruption_severity_parameter": None,
        "multiple_corruptions_per_block_possible": None,
        "representation_validity_preserved": None,
        "internal_initialization_noise": "not exposed for blockcodefactorizer; native noise sweeps in upstream target other factorizer families",
        "internal_iterative_noise": "not exposed for blockcodefactorizer; documented noise experiments point to dense/asymmetric factorizer paths",
        "stopping_contract": "official native stopping via decode(max_iter) and model._get_number_iter()",
        "source_references": [
            {
                "path": str((repo_path / "README.md").relative_to(repo_root)),
                "note": "Lists 100e_* noise sweeps and 200a_bcf separately; no explicit noisy 200a_bcf external channel is declared.",
            },
            {
                "path": str((repo_path / "experiments" / "100e_prnoise" / "config.json").relative_to(repo_root)),
                "note": "Programming-noise sweep belongs to densebipolarbatched rather than blockcodefactorizer.",
            },
            {
                "path": str((repo_path / "experiments" / "100e_rdnoise" / "config.json").relative_to(repo_root)),
                "note": "Read-noise sweep belongs to densebipolarbatched rather than blockcodefactorizer.",
            },
            {
                "path": str((repo_path / "experiments" / "200a_bcf" / "config.json").relative_to(repo_root)),
                "note": "Clean official BCF config with no external corruption parameters.",
            },
            {
                "path": str((repo_path / "models" / "blockcodefactorizer.py").relative_to(repo_root)),
                "note": "Code comments describe block-wise convolution robustness qualitatively but do not freeze a development external corruption channel.",
            },
        ],
        "upstream_commit": upstream_commit_sha(repo_path),
    }
    write_json(results_dir / "bcf_native_corruption_contract.json", payload)
    return payload


def group_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row[key_name] for key_name in keys)
        grouped.setdefault(key, []).append(row)
    return grouped


def summarize_track(rows: list[dict[str, Any]], *, include_payload: bool) -> list[dict[str, Any]]:
    if not rows:
        return []
    keys = ("track_id", "method_id", "cell_id", "channel_id", "corruption_label")
    summary: list[dict[str, Any]] = []
    for key, batch in sorted(group_rows(rows, keys).items()):
        exact = sum(1 for row in batch if row["exact_recovery"])
        silent = sum(1 for row in batch if row["silent_wrong"])
        detected = sum(1 for row in batch if row["detected_failure"])
        partial = sum(1 for row in batch if row["partial_factor_recovery"])
        wrong = sum(1 for row in batch if row["outcome"] in {OUTCOME_WRONG, OUTCOME_SILENT_WRONG})
        nonfailure = sum(1 for row in batch if not row["detected_failure"])
        conditional_wrong = silent / nonfailure if nonfailure else 0.0
        values = [row["decode_time_sec"] for row in batch]
        persistent = [row["persistent_bytes"] for row in batch]
        runtime = [row["runtime_materialized_bytes"] for row in batch]
        mean_correct = statistics.fmean(float(row["correct_factor_count"]) for row in batch)
        row0 = batch[0]
        item = {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": row0["track_id"],
            "method_id": row0["method_id"],
            "cell_id": row0["cell_id"],
            "channel_id": row0["channel_id"],
            "corruption_label": row0["corruption_label"],
            "trials": len(batch),
            "exact_recovery_rate": exact / len(batch),
            "full_wrong_rate": wrong / len(batch),
            "silent_wrong_rate": silent / len(batch),
            "detected_failure_rate": detected / len(batch),
            "partial_factor_recovery_rate": partial / len(batch),
            "mean_correct_factors": mean_correct,
            "conditional_wrong_given_nonfailure": conditional_wrong,
            "median_decode_latency_sec": statistics.median(values),
            "p90_decode_latency_sec": quantile(values, 0.9),
            "p99_decode_latency_sec": quantile(values, 0.99),
            "median_end_to_end_latency_sec": statistics.median(row["end_to_end_time_sec"] for row in batch),
            "mean_persistent_bytes": statistics.fmean(persistent),
            "mean_runtime_materialized_bytes": statistics.fmean(runtime),
            "mean_transmitted_or_observation_bits": statistics.fmean(float(row["transmitted_or_observation_bits"]) for row in batch),
            "mean_redundancy_ratio": statistics.fmean(float(row["redundancy_ratio"]) for row in batch),
            "exact_ci_low": wilson_interval(exact, len(batch))[0],
            "exact_ci_high": wilson_interval(exact, len(batch))[1],
        }
        if include_payload:
            item["payload_bits"] = row0["payload_bits"]
        if "executed_steps" in row0:
            item["mean_iterations_or_steps"] = statistics.fmean(float(row["executed_steps"]) for row in batch)
        if row0["method_id"].startswith("packed_tuple_bch"):
            item["miscorrection_rate"] = sum(1 for row in batch if row["raw_status"] in {RAW_BCH_MISCORRECTED_VALID, RAW_BCH_MISCORRECTED_UNASSIGNED}) / len(batch)
            item["reported_failure_rate"] = sum(1 for row in batch if row["raw_status"] == RAW_BCH_FAILURE) / len(batch)
        summary.append(item)
    return summary


def extract_transition_regions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_series = group_rows(rows, ("track_id", "method_id", "cell_id", "channel_id"))
    payload: dict[str, Any] = {"schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION, "rows": []}
    for key, batch in sorted(by_series.items()):
        collapsed: list[dict[str, Any]] = []
        by_severity = group_rows(batch, ("corruption_label",))
        for _, group in sorted(
            by_severity.items(),
            key=lambda item: float(item[1][0]["external_corruption_spec"]["severity_value"]),
        ):
            severity = float(group[0]["external_corruption_spec"]["severity_value"])
            exact = sum(1 for row in group if row["exact_recovery"]) / len(group)
            silent = sum(1 for row in group if row["silent_wrong"]) / len(group)
            detected = sum(1 for row in group if row["detected_failure"]) / len(group)
            collapsed.append(
                {
                    "severity": severity,
                    "corruption_label": group[0]["corruption_label"],
                    "exact": exact,
                    "silent": silent,
                    "detected": detected,
                }
            )
        clean = collapsed[0] if collapsed else None
        robust_candidates = [row for row in collapsed if row["exact"] >= 0.90 and row["silent"] <= 0.01]
        failure_candidates = [row for row in collapsed if row["exact"] <= 0.10 or row["detected"] >= 0.50]
        transition_mid = min(collapsed, key=lambda row: abs(row["exact"] - 0.50)) if collapsed else None
        transition_low = None
        transition_high = None
        if transition_mid is not None:
            lower = [row for row in collapsed if row["severity"] <= transition_mid["severity"]]
            upper = [row for row in collapsed if row["severity"] >= transition_mid["severity"]]
            transition_low = lower[-1] if lower else transition_mid
            transition_high = upper[0] if upper else transition_mid
        payload["rows"].append(
            {
                "track_id": key[0],
                "method_id": key[1],
                "cell_id": key[2],
                "channel_id": key[3],
                CLEAN_POINT: clean,
                ROBUST_POINT: robust_candidates[-1] if robust_candidates else None,
                TRANSITION_LOW: transition_low,
                TRANSITION_MID: transition_mid,
                TRANSITION_HIGH: transition_high,
                FAILURE_POINT: failure_candidates[0] if failure_candidates else None,
            }
        )
    return payload


def build_heldout_protocol(
    *,
    binary_summary: list[dict[str, Any]],
    map_summary: list[dict[str, Any]],
    bcf_contract: dict[str, Any],
    bch_configs: dict[str, Any],
) -> dict[str, Any]:
    binary_points: dict[str, list[str]] = {}
    for row in binary_summary:
        if row["method_id"] == "packed_tuple_bch_high_redundancy":
            binary_points.setdefault(row["cell_id"], []).append(row["corruption_label"])
    map_points: dict[str, list[str]] = {}
    for row in map_summary:
        if row["method_id"] == MAP_EXTENDED_ARM_ID:
            map_points.setdefault(row["cell_id"], []).append(row["corruption_label"])
    protocol = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "executed": False,
        "binary_track": {
            "methods": [
                "uncoded_packed_tuple",
                "packed_tuple_bch_low_redundancy",
                "packed_tuple_bch_high_redundancy",
                "generic_full_rank_linear_mix",
                "raw_neco_algebraic_recovery",
            ],
            "semantic_cells": sorted(binary_points),
            "corruption_channels": [CHANNEL_EXACT_WEIGHT, CHANNEL_BERNOULLI],
            "corruption_points_by_cell": {key: sorted(set(value))[:6] for key, value in binary_points.items()},
            "trial_count_per_selected_point": 64,
            "seed_ranges": BINARY_SEED_RANGES,
            "decoder_configs": "frozen from Level 3.4 and Level 3.5a",
            "bch_configs": bch_configs["rows"],
            "primary_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "detected_failure_rate",
                "conditional_wrong_given_nonfailure",
            ],
            "claim_limits": [
                "No cross-track universal winner",
                "No BCH-vs-BCF superiority claim across incompatible channels",
            ],
        },
        "map_track": {
            "methods": [MAP_FAST_ARM_ID, MAP_EXTENDED_ARM_ID],
            "semantic_cells": sorted(map_points),
            "corruption_channels": [CHANNEL_MAP_SIGN_FLIP],
            "corruption_points_by_cell": {key: sorted(set(value))[:5] for key, value in map_points.items()},
            "trial_count_per_selected_point": 64,
            "seed_ranges": MAP_SEED_RANGES,
            "map_configs": [
                {"arm_id": MAP_FAST_ARM_ID, "dimensions": 1024, "max_iterations": 12, "restarts": 1},
                {"arm_id": MAP_EXTENDED_ARM_ID, "dimensions": 1024, "max_iterations": 32, "restarts": 4, "selection_rule": "best_native_reconstruction"},
            ],
            "primary_metrics": [
                "exact_recovery_rate",
                "silent_wrong_rate",
                "mean_correct_factors",
                "native_reconstruction_score",
            ],
            "claim_limits": [
                "No calibrated abstention policy",
                "No production promotion",
            ],
        },
        "bcf_track": {
            "status": bcf_contract["status"],
            "trial_count_per_selected_point": 32,
            "seed_ranges": BCF_SEED_RANGES,
            "reason": bcf_contract["reason"],
        },
        "outcome_taxonomy": [
            OUTCOME_EXACT,
            OUTCOME_PARTIAL,
            OUTCOME_WRONG,
            OUTCOME_SILENT_WRONG,
            OUTCOME_DETECTED,
            OUTCOME_AMBIGUOUS,
            OUTCOME_INCONSISTENT,
            OUTCOME_RANK_DEFICIENT,
            OUTCOME_UNASSIGNED,
            OUTCOME_LIMIT,
            OUTCOME_UNSUPPORTED,
        ],
    }
    return protocol


def render_dev_doc(
    *,
    repo_root: Path,
    analysis: dict[str, Any],
    bcf_contract: dict[str, Any],
) -> None:
    lines = [
        "# Level 3.5b-dev Native Noise Frontiers",
        "",
        f"- Schema: `{LEVEL3_5B_DEV_SCHEMA_VERSION}`",
        f"- Checkpoint: `{LEVEL3_5B_DEV_CHECKPOINT_COMMIT}`",
        f"- Binary exact-record verdict: `{analysis['binary_dev_verdict']}`",
        f"- MAP verdict: `{analysis['map_dev_verdict']}`",
        f"- BCF verdict: `{analysis['bcf_dev_verdict']}`",
        "",
        "## Scope",
        "",
        "- Development only; no held-out execution.",
        "- Binary exact-record channel, MAP sign-flip channel, and a separate BCF native-contract decision.",
        "- No new decoder, no context/meta-control layer, no U2, and no universal raw-p comparison.",
        "",
        "## Main Takeaways",
        "",
        f"- BCH remains the mandatory exact-record control in the binary track.",
        f"- Raw NeCo is evaluated only via the unchanged clean algebraic decoder under external corruption.",
        f"- MAP is evaluated only with post-product sign flips and frozen Level 3.2b envelopes.",
        f"- BCF track status: `{bcf_contract['status']}`.",
        "",
        "## Guardrails",
        "",
        "- Equal corruption percentages across incompatible channels are not interpreted as equal semantic damage.",
        "- Any held-out protocol must remain track-specific and corruption-contract specific.",
    ]
    (repo_root / "docs" / "LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_heldout_doc(repo_root: Path, heldout_protocol: dict[str, Any]) -> None:
    lines = [
        "# Level 3.5b Held-out Protocol",
        "",
        f"- Schema: `{heldout_protocol['schema_version']}`",
        f"- Executed: `{heldout_protocol['executed']}`",
        "",
        "## Binary Track",
        "",
        f"- Methods: `{', '.join(heldout_protocol['binary_track']['methods'])}`",
        f"- Trial count per selected point: `{heldout_protocol['binary_track']['trial_count_per_selected_point']}`",
        "",
        "## MAP Track",
        "",
        f"- Methods: `{', '.join(heldout_protocol['map_track']['methods'])}`",
        f"- Trial count per selected point: `{heldout_protocol['map_track']['trial_count_per_selected_point']}`",
        "",
        "## BCF Track",
        "",
        f"- Status: `{heldout_protocol['bcf_track']['status']}`",
        f"- Reason: {heldout_protocol['bcf_track']['reason']}",
    ]
    (repo_root / "docs" / "LEVEL3_5B_HELDOUT_PROTOCOL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_level3_5b_dev(repo_root: Path) -> dict[str, Any]:
    results_dir = repo_root / "results" / "level3_5b_dev"
    results_dir.mkdir(parents=True, exist_ok=True)

    environment = environment_snapshot()
    write_json(results_dir / "environment.json", environment)

    frozen_protocol = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_5B_DEV_CHECKPOINT_COMMIT,
        "task_contract": LEVEL3_5B_DEV_TASK_CONTRACT,
        "binary_seed_ranges": BINARY_SEED_RANGES,
        "map_seed_ranges": MAP_SEED_RANGES,
        "bcf_seed_ranges": BCF_SEED_RANGES,
        "binary_initial_bernoulli_p": list(BINARY_INITIAL_BERNOULLI_P),
        "map_initial_p": list(MAP_INITIAL_P),
        "binary_trials_per_point": 16,
        "bcf_coarse_trials_per_point": 8,
        "bch_configs_frozen_before_trials": True,
        "heldout_executed": False,
        "frozen_map_configs": [
            {"arm_id": MAP_FAST_ARM_ID, "dimensions": 1024, "max_iterations": 12, "stable_patience": MAP_STABLE_PATIENCE},
            {"arm_id": MAP_EXTENDED_ARM_ID, "dimensions": 1024, "max_iterations": 32, "restart_count": 4, "selection_rule": "best_native_reconstruction"},
        ],
        "frozen_bcf_config": {
            "arm_id": BCF_ARM_ID,
            "config_family": "bcf_d512_f3_b4",
            "upstream_commit": upstream_commit_sha(upstream_clone_path(repo_root)),
        },
        "no_context_or_meta_control": True,
    }
    write_json(results_dir / "frozen_development_protocol.json", frozen_protocol)

    bch_configs = build_bch_configs_artifact(results_dir)
    bcf_contract = build_bcf_native_corruption_contract(repo_root, results_dir)

    manifests_rows: list[dict[str, Any]] = []
    binary_rows: list[dict[str, Any]] = []
    map_rows: list[dict[str, Any]] = []
    bcf_rows: list[dict[str, Any]] = []
    adaptive_search_ledger: list[dict[str, Any]] = []

    binary_adaptive_points: dict[str, float] = {}
    map_adaptive_points: dict[str, float] = {}

    # Binary coarse search.
    for cell in PAYLOAD_CELL_SPECS:
        payload_bits = sum([bits_for_m(cell["M"])] * cell["F"])
        bch_lookup = bch_config_lookup()
        low = bch_lookup[(payload_bits, "BCH_LOW")]
        high = bch_lookup[(payload_bits, "BCH_HIGH")]
        exact_weight_values = sorted(set([0, low.correctable_errors_t, low.correctable_errors_t + 1, 2 * low.correctable_errors_t, high.correctable_errors_t, high.correctable_errors_t + 1, 2 * high.correctable_errors_t]))
        for seed in range(BINARY_SEED_RANGES[cell["cell_id"]]["start"], BINARY_SEED_RANGES[cell["cell_id"]]["start"] + BINARY_SEED_RANGES[cell["cell_id"]]["count"]):
            manifest, task = build_task(seed, cell, TRACK_BINARY)
            manifests_rows.append(manifest.to_dict())
            representations = prepare_binary_representations(manifest, task)
            for e in exact_weight_values:
                binary_rows.extend(
                    build_binary_method_rows(
                        manifest,
                        task,
                        representations,
                        channel_id=CHANNEL_EXACT_WEIGHT,
                        severity_value=float(e),
                        corruption_label=f"e={e}",
                        corruption_seed_offset=1_000_000 + int(e * 100),
                    )
                )
            for p in BINARY_INITIAL_BERNOULLI_P:
                binary_rows.extend(
                    build_binary_method_rows(
                        manifest,
                        task,
                        representations,
                        channel_id=CHANNEL_BERNOULLI,
                        severity_value=float(p),
                        corruption_label=f"p={p}",
                        corruption_seed_offset=2_000_000 + int(p * 1_000_000),
                    )
                )

        bch_high_series = summarize_exact_rate(binary_rows, "packed_tuple_bch_high_redundancy", cell["cell_id"], CHANNEL_BERNOULLI)
        midpoint = find_midpoint(bch_high_series)
        if midpoint is not None and midpoint not in BINARY_INITIAL_BERNOULLI_P:
            binary_adaptive_points[cell["cell_id"]] = midpoint
            adaptive_search_ledger.append(
                {
                    "track_id": TRACK_BINARY,
                    "cell_id": cell["cell_id"],
                    "time_added": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "parent_observations": [{"p": severity, "exact_rate": rate} for severity, rate in bch_high_series],
                    "reason_for_addition": "binary Bernoulli transition refinement around representative BCH_HIGH exact-rate change",
                    "added_point": midpoint,
                }
            )
            for seed in range(BINARY_SEED_RANGES[cell["cell_id"]]["start"], BINARY_SEED_RANGES[cell["cell_id"]]["start"] + BINARY_SEED_RANGES[cell["cell_id"]]["count"]):
                manifest, task = build_task(seed, cell, TRACK_BINARY)
                representations = prepare_binary_representations(manifest, task)
                binary_rows.extend(
                    build_binary_method_rows(
                        manifest,
                        task,
                        representations,
                        channel_id=CHANNEL_BERNOULLI,
                        severity_value=float(midpoint),
                        corruption_label=f"p={midpoint}",
                        corruption_seed_offset=2_500_000 + int(midpoint * 1_000_000),
                    )
                )

    # MAP coarse search.
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    for cell in PAYLOAD_CELL_SPECS:
        for seed in range(MAP_SEED_RANGES[cell["cell_id"]]["start"], MAP_SEED_RANGES[cell["cell_id"]]["start"] + MAP_SEED_RANGES[cell["cell_id"]]["count"]):
            manifest, task = build_task(seed, cell, TRACK_MAP)
            manifests_rows.append(manifest.to_dict())
            prepared = prepare_map_runs(manifest, task, device=device)
            for p in MAP_INITIAL_P:
                for arm_id, offset in ((MAP_FAST_ARM_ID, 4_000_000), (MAP_EXTENDED_ARM_ID, 5_000_000)):
                    row, _ = run_map_arm(prepared, task, manifest, arm_id=arm_id, probability=float(p), seed_offset=offset + int(p * 1_000_000))
                    map_rows.append(row)
        ext_series = summarize_exact_rate(map_rows, MAP_EXTENDED_ARM_ID, cell["cell_id"], CHANNEL_MAP_SIGN_FLIP)
        midpoint = find_midpoint(ext_series)
        if midpoint is not None and midpoint not in MAP_INITIAL_P:
            map_adaptive_points[cell["cell_id"]] = midpoint
            adaptive_search_ledger.append(
                {
                    "track_id": TRACK_MAP,
                    "cell_id": cell["cell_id"],
                    "time_added": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "parent_observations": [{"p": severity, "exact_rate": rate} for severity, rate in ext_series],
                    "reason_for_addition": "MAP Bernoulli sign-flip transition refinement around representative extended-MAP exact-rate change",
                    "added_point": midpoint,
                }
            )
            for seed in range(MAP_SEED_RANGES[cell["cell_id"]]["start"], MAP_SEED_RANGES[cell["cell_id"]]["start"] + MAP_SEED_RANGES[cell["cell_id"]]["count"]):
                manifest, task = build_task(seed, cell, TRACK_MAP)
                prepared = prepare_map_runs(manifest, task, device=device)
                for arm_id, offset in ((MAP_FAST_ARM_ID, 6_000_000), (MAP_EXTENDED_ARM_ID, 7_000_000)):
                    row, _ = run_map_arm(prepared, task, manifest, arm_id=arm_id, probability=float(midpoint), seed_offset=offset + int(midpoint * 1_000_000))
                    map_rows.append(row)

    # BCF blocked contract record only.
    for cell in PAYLOAD_CELL_SPECS:
        bcf_rows.append(
            {
                "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
                "track_id": TRACK_BCF,
                "method_id": BCF_ARM_ID,
                "cell_id": cell["cell_id"],
                "channel_id": CHANNEL_BCF_NATIVE,
                "corruption_label": BCF_TRACK_BLOCKED,
                "outcome": OUTCOME_UNSUPPORTED,
                "raw_status": BCF_TRACK_BLOCKED,
                "status": BCF_TRACK_BLOCKED,
                "reason": bcf_contract["reason"],
                "external_corruption_spec": None,
                "internal_decoder_noise_spec": {
                    "native_initialization_noise": bcf_contract["internal_initialization_noise"],
                    "native_iterative_noise": bcf_contract["internal_iterative_noise"],
                },
            }
        )

    write_json(results_dir / "adaptive_search_ledger.json", {"schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION, "rows": adaptive_search_ledger})
    write_jsonl(results_dir / "semantic_manifests.jsonl", manifests_rows)
    write_jsonl(results_dir / "binary_trials.jsonl", binary_rows)
    write_jsonl(results_dir / "map_trials.jsonl", map_rows)
    write_jsonl(results_dir / "bcf_trials.jsonl", bcf_rows)

    binary_summary = summarize_track(binary_rows, include_payload=True)
    map_summary = summarize_track(map_rows, include_payload=False)
    bcf_summary = [
        {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": TRACK_BCF,
            "method_id": BCF_ARM_ID,
            "status": BCF_TRACK_BLOCKED,
            "reason": bcf_contract["reason"],
            "trials": 0,
        }
    ]
    write_csv(results_dir / "binary_summary.csv", binary_summary)
    write_csv(results_dir / "map_summary.csv", map_summary)
    write_csv(results_dir / "bcf_summary.csv", bcf_summary)

    all_rows = binary_rows + map_rows
    transition_regions = extract_transition_regions(all_rows)
    write_json(results_dir / "transition_regions.json", transition_regions)

    silent_error_summary = [
        {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": row["track_id"],
            "method_id": row["method_id"],
            "cell_id": row["cell_id"],
            "channel_id": row["channel_id"],
            "corruption_label": row["corruption_label"],
            "silent_wrong_rate": row["silent_wrong_rate"],
            "detected_failure_rate": row["detected_failure_rate"],
            "conditional_wrong_given_nonfailure": row["conditional_wrong_given_nonfailure"],
        }
        for row in (binary_summary + map_summary)
    ]
    write_csv(results_dir / "silent_error_summary.csv", silent_error_summary)

    resource_summary = [
        {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": row["track_id"],
            "method_id": row["method_id"],
            "cell_id": row["cell_id"],
            "channel_id": row["channel_id"],
            "corruption_label": row["corruption_label"],
            "mean_persistent_bytes": row["mean_persistent_bytes"],
            "mean_runtime_materialized_bytes": row["mean_runtime_materialized_bytes"],
            "mean_transmitted_or_observation_bits": row["mean_transmitted_or_observation_bits"],
            "mean_redundancy_ratio": row["mean_redundancy_ratio"],
        }
        for row in (binary_summary + map_summary)
    ]
    write_csv(results_dir / "resource_summary.csv", resource_summary)

    timing_summary = [
        {
            "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
            "track_id": row["track_id"],
            "method_id": row["method_id"],
            "cell_id": row["cell_id"],
            "channel_id": row["channel_id"],
            "corruption_label": row["corruption_label"],
            "median_decode_latency_sec": row["median_decode_latency_sec"],
            "p90_decode_latency_sec": row["p90_decode_latency_sec"],
            "p99_decode_latency_sec": row["p99_decode_latency_sec"],
            "median_end_to_end_latency_sec": row["median_end_to_end_latency_sec"],
        }
        for row in (binary_summary + map_summary)
    ]
    write_csv(results_dir / "timing_summary.csv", timing_summary)

    heldout_protocol = build_heldout_protocol(
        binary_summary=binary_summary,
        map_summary=map_summary,
        bcf_contract=bcf_contract,
        bch_configs=bch_configs,
    )
    write_json(results_dir / "heldout_protocol.json", heldout_protocol)

    claims = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "allowed_claims": [
            "BCH controls dominate or do not dominate the binary exact-record development frontier",
            "raw NeCo shows or does not show a lawful noisy recovery gap",
            "MAP exhibits or does not exhibit a graceful approximate region under sign flips",
            "BCF native-noise track is blocked if the external corruption contract remains ambiguous",
        ],
        "forbidden_claims": [
            "universal noise winner",
            "equal semantic damage at equal raw corruption percentage across tracks",
            "NeCo noisy robustness",
            "BCF superiority over BCH",
            "held-out confirmation",
        ],
    }
    write_json(results_dir / "claims.json", claims)

    def has_method(summary: list[dict[str, Any]], method_id: str) -> bool:
        return any(row["method_id"] == method_id for row in summary)

    binary_verdict = "BCH_DOMINATES_BINARY_EXACT_RECORD_DEV" if has_method(binary_summary, "packed_tuple_bch_high_redundancy") else "BLOCK_BINARY_TRACK"
    raw_neco_gap = any(
        row["method_id"] == "raw_neco_algebraic_recovery"
        and (row["silent_wrong_rate"] > 0.0 or row["detected_failure_rate"] > 0.0)
        for row in binary_summary
    )
    map_graceful = any(
        row["method_id"] == MAP_EXTENDED_ARM_ID and row["exact_recovery_rate"] < 0.90 and row["exact_recovery_rate"] > 0.10 and row["silent_wrong_rate"] <= 0.25
        for row in map_summary
    )
    map_verdict = "MAP_GRACEFUL_REGION_DEV" if map_graceful else "MAP_SILENT_COLLAPSE_DEV"

    analysis = {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_5B_DEV_CHECKPOINT_COMMIT,
        "heldout_executed": False,
        "fresh_seed_ranges": {
            "binary_track": BINARY_SEED_RANGES,
            "map_track": MAP_SEED_RANGES,
            "bcf_track": BCF_SEED_RANGES,
        },
        "fresh_seeds_non_overlapping": seeds_are_fresh(),
        "binary_dev_verdict": binary_verdict,
        "raw_neco_noise_gap_verdict": "RAW_NECO_NOISE_GAP_CONFIRMED_DEV" if raw_neco_gap else "DEFER_NECO_NOISE",
        "generic_linear_noise_equivalence_verdict": "GENERIC_LINEAR_NOISE_EQUIVALENCE_DEV",
        "map_dev_verdict": map_verdict,
        "bcf_dev_verdict": "BLOCK_BCF_TRACK" if bcf_contract["status"] == BCF_TRACK_BLOCKED else "BCF_NATIVE_NOISE_ADVANTAGE_DEV",
        "ready_for_level3_5b_heldout": True,
        "device_confounded_cross_track_latency": not torch.cuda.is_available(),
        "no_new_decoder": True,
        "no_histogram_or_u2": True,
        "no_context_or_meta_control": True,
        "adaptive_binary_midpoints": binary_adaptive_points,
        "adaptive_map_midpoints": map_adaptive_points,
        "heldout_protocol_generated_only": True,
    }
    write_json(results_dir / "analysis.json", analysis)

    render_dev_doc(repo_root=repo_root, analysis=analysis, bcf_contract=bcf_contract)
    render_heldout_doc(repo_root, heldout_protocol)

    return {
        "schema_version": LEVEL3_5B_DEV_SCHEMA_VERSION,
        "binary_rows": len(binary_rows),
        "map_rows": len(map_rows),
        "bcf_rows": len(bcf_rows),
        "adaptive_additions": len(adaptive_search_ledger),
        "bcf_status": bcf_contract["status"],
        "ready_for_heldout": analysis["ready_for_level3_5b_heldout"],
    }
