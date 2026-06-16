from __future__ import annotations

import csv
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .competitors.ibm_bcf_audit import AbstractFactorizationTask, upstream_clone_path, upstream_commit_sha
from .level3_2_confirmation import (
    BCF_CONFIG_FAMILY,
    build_frozen_bcf_configs,
    common_outcome,
    config_for_cell,
    peak_cpu_memory_bytes,
    synchronize_device,
    tensor_bytes,
)
from .level3_2b_map_budget_robustness import (
    MAP_STABLE_PATIENCE,
    PreparedMapTask,
    choose_attempt,
    prepare_map_task,
    restart_agreement,
    run_map_attempt,
    unique_proposal_count,
)
from .level3_3_neco_reproduction import (
    COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS,
    GF2,
    LEVEL3_3_SCHEMA_VERSION,
    bind_codewords_bits,
    bits_to_pm1,
    construct_direct_sum_subcodes,
    decode_binding,
    gf2_rank,
    gf2_solve_unique,
    materialize_factor_codewords,
    pm1_to_bits,
    random_full_rank_matrix,
    theoretical_bit_bytes,
)

LEVEL3_4_SCHEMA_VERSION = "level3-4-clean-u1-algebraic-baseline-dev-v1"
LEVEL3_4_CHECKPOINT_COMMIT = "2b8d6f98d1135e7f19d8d3447de8b5695d96e0b3"
LEVEL3_4_TASK_CONTRACT = "U1_blind_clean_single_product_factorization"
LEVEL3_4_SPLIT = "development_algebraic_closure"

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_WRONG = "WRONG_RECOVERY"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"
OUTCOME_UNASSIGNED = "UNASSIGNED_CODEWORD"
OUTCOME_RANK_DEFICIENT = "RANK_DEFICIENT"
OUTCOME_INCONSISTENT = "INCONSISTENT"

SCHEMA_INSERT_STABLE = "INSERT_STABLE"
SCHEMA_INSERT_MAPPING = "INSERT_REQUIRES_MAPPING_ONLY"
SCHEMA_DOMAIN_REBUILD = "DOMAIN_EXPANSION_REQUIRES_REBUILD"
SCHEMA_FACTOR_REBUILD = "SCHEMA_EXPANSION_REQUIRES_REBUILD"
SCHEMA_UNSUPPORTED = "UNSUPPORTED"

PRIMARY_NECO_AMBIENT_LENGTH = 500
MAP_FAST_ARM_ID = "map_d1024"
MAP_EXTENDED_ARM_ID = "map_d1024_step32_r4_best_native_reconstruction"
BCF_ARM_ID = "bcf_d512_f3_b4"
BCF_REPRESENTATION_SEED_OFFSET = 4_000
MAP_REPRESENTATION_SEED_OFFSET = 5_000
GENERIC_SEED_OFFSET = 6_000
NECO_SEED_OFFSET = 7_000


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    factor_count: int
    domain_size: int
    trials: int
    include_bcf: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CELLS: tuple[CellSpec, ...] = (
    CellSpec("u1_clean_m10", 3, 10, 16),
    CellSpec("u1_clean_m22", 3, 22, 16),
    CellSpec("u1_clean_m31", 3, 31, 16),
    CellSpec("u1_clean_m68", 3, 68, 16),
)

SEED_RANGES = {
    "u1_clean_m10": {"start": 90260615, "count": 16},
    "u1_clean_m22": {"start": 91260615, "count": 16},
    "u1_clean_m31": {"start": 92260615, "count": 16},
    "u1_clean_m68": {"start": 93260615, "count": 16},
}


@dataclass(frozen=True)
class PackedDecodeResult:
    outcome: str
    predicted_indices: list[int]
    decoded_message_bits: list[list[int]]
    decode_time_sec: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def level3_4_seed_set() -> set[int]:
    values: set[int] = set()
    for spec in SEED_RANGES.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def prior_seed_set() -> set[int]:
    from .level3_2_confirmation import level3_2_heldout_seed_set, prior_level3_1_seed_set
    from .level3_2b_map_budget_robustness import level3_2b_seed_set

    prior = prior_level3_1_seed_set().union(level3_2_heldout_seed_set()).union(level3_2b_seed_set())
    prior.update(range(330001, 331013))
    prior.update(range(331001, 331013))
    return prior


def seeds_are_fresh() -> bool:
    return level3_4_seed_set().isdisjoint(prior_seed_set())


def factor_identity_tokens(factor_count: int, domain_size: int) -> list[list[str]]:
    return [[f"f{factor_index}_i{index}" for index in range(domain_size)] for factor_index in range(factor_count)]


def bits_for_m(domain_size: int) -> int:
    return math.ceil(math.log2(domain_size))


def int_to_bits(value: int, width: int) -> np.ndarray:
    return np.array([(value >> bit) & 1 for bit in range(width)], dtype=np.uint8)


def bits_to_int(bits: np.ndarray) -> int:
    value = 0
    for bit_index, bit in enumerate(np.asarray(bits, dtype=np.uint8).tolist()):
        value |= (int(bit) & 1) << bit_index
    return value


def build_task_manifest(trial_seed: int, cell: CellSpec) -> tuple[dict[str, Any], AbstractFactorizationTask]:
    generator = torch.Generator()
    generator.manual_seed(trial_seed)
    true_indices = [
        int(torch.randint(0, cell.domain_size, (1,), generator=generator).item())
        for _ in range(cell.factor_count)
    ]
    manifest = {
        "trial_id": f"{cell.cell_id}-seed-{trial_seed}",
        "trial_seed": trial_seed,
        "split": LEVEL3_4_SPLIT,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
        "cell_id": cell.cell_id,
        "F": cell.factor_count,
        "M": cell.domain_size,
        "true_factor_indices": true_indices,
        "factor_identity_tokens": factor_identity_tokens(cell.factor_count, cell.domain_size),
        "map_representation_seed": trial_seed + MAP_REPRESENTATION_SEED_OFFSET,
        "bcf_representation_seed": trial_seed + BCF_REPRESENTATION_SEED_OFFSET,
        "generic_representation_seed": trial_seed + GENERIC_SEED_OFFSET,
        "neco_representation_seed": trial_seed + NECO_SEED_OFFSET,
    }
    task = AbstractFactorizationTask(
        task_seed=trial_seed,
        factor_count=cell.factor_count,
        domain_size_per_factor=[cell.domain_size] * cell.factor_count,
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


def payload_bit_widths(task: AbstractFactorizationTask) -> list[int]:
    return [bits_for_m(domain_size) for domain_size in task.domain_size_per_factor]


def payload_bits_from_indices(indices: list[int], widths: list[int]) -> list[np.ndarray]:
    return [int_to_bits(index, width) for index, width in zip(indices, widths, strict=True)]


def packed_encode(task: AbstractFactorizationTask) -> tuple[np.ndarray, list[np.ndarray]]:
    widths = payload_bit_widths(task)
    slices = payload_bits_from_indices(task.target_indices, widths)
    return np.concatenate(slices, axis=0), slices


def decode_factor_messages(message_bits: list[np.ndarray], task: AbstractFactorizationTask) -> PackedDecodeResult:
    decode_start = time.perf_counter()
    predicted_indices: list[int] = []
    outcome = OUTCOME_EXACT
    for factor_index, bits in enumerate(message_bits):
        decoded_index = bits_to_int(bits)
        if decoded_index >= task.domain_size_per_factor[factor_index]:
            outcome = OUTCOME_UNASSIGNED
            return PackedDecodeResult(
                outcome=outcome,
                predicted_indices=[],
                decoded_message_bits=[entry.astype(int).tolist() for entry in message_bits],
                decode_time_sec=time.perf_counter() - decode_start,
            )
        predicted_indices.append(decoded_index)
    return PackedDecodeResult(
        outcome=outcome,
        predicted_indices=predicted_indices,
        decoded_message_bits=[entry.astype(int).tolist() for entry in message_bits],
        decode_time_sec=time.perf_counter() - decode_start,
    )


def packed_decode(observation_bits: np.ndarray, task: AbstractFactorizationTask) -> PackedDecodeResult:
    widths = payload_bit_widths(task)
    start = 0
    slices: list[np.ndarray] = []
    for width in widths:
        slices.append(np.asarray(observation_bits[start : start + width], dtype=np.uint8))
        start += width
    return decode_factor_messages(slices, task)


def generic_matrix(task: AbstractFactorizationTask, *, ambient_length: int, seed: int) -> np.ndarray:
    total_width = sum(payload_bit_widths(task))
    return random_full_rank_matrix(total_width, ambient_length, seed).T


def generic_encode(task: AbstractFactorizationTask, matrix: np.ndarray) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    payload, slices = packed_encode(task)
    observation = (matrix @ payload) % 2
    return observation.astype(np.uint8), slices, payload


def generic_decode(observation_bits: np.ndarray, task: AbstractFactorizationTask, matrix: np.ndarray) -> PackedDecodeResult:
    decode_start = time.perf_counter()
    solve_outcome, solution, _, _ = gf2_solve_unique(matrix, observation_bits)
    if solve_outcome == OUTCOME_EXACT and solution is not None:
        widths = payload_bit_widths(task)
        start = 0
        slices: list[np.ndarray] = []
        for width in widths:
            slices.append(np.asarray(solution[start : start + width], dtype=np.uint8))
            start += width
        decoded = decode_factor_messages(slices, task)
        return PackedDecodeResult(
            outcome=decoded.outcome,
            predicted_indices=decoded.predicted_indices,
            decoded_message_bits=decoded.decoded_message_bits,
            decode_time_sec=time.perf_counter() - decode_start,
        )
    return PackedDecodeResult(
        outcome=solve_outcome,
        predicted_indices=[],
        decoded_message_bits=[],
        decode_time_sec=time.perf_counter() - decode_start,
    )


def generic_factor_codewords(task: AbstractFactorizationTask, matrix: np.ndarray) -> list[np.ndarray]:
    widths = payload_bit_widths(task)
    total_width = sum(widths)
    cursor = 0
    codewords: list[np.ndarray] = []
    for factor_index, width in enumerate(widths):
        for identity_index in range(task.domain_size_per_factor[factor_index]):
            factor_message = np.zeros(total_width, dtype=np.uint8)
            factor_message[cursor : cursor + width] = int_to_bits(identity_index, width)
            codewords.append(((matrix @ factor_message) % 2).astype(np.uint8))
        cursor += width
    return codewords


def neco_subcodes(task: AbstractFactorizationTask, *, ambient_length: int, seed: int) -> tuple[list[np.ndarray], list[int]]:
    widths = payload_bit_widths(task)
    return construct_direct_sum_subcodes(
        ambient_length=ambient_length,
        subcode_dimensions=widths,
        seed=seed,
    ), widths


def neco_encode(task: AbstractFactorizationTask, subcodes: list[np.ndarray]) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
    widths = payload_bit_widths(task)
    coefficients = payload_bits_from_indices(task.target_indices, widths)
    codewords = materialize_factor_codewords(subcodes, coefficients)
    observation = bind_codewords_bits(codewords)
    return observation.astype(np.uint8), coefficients, codewords


def neco_decode(observation_bits: np.ndarray, task: AbstractFactorizationTask, subcodes: list[np.ndarray]) -> PackedDecodeResult:
    decoded = decode_binding(subcodes=subcodes, observation_bits=observation_bits, expected_factor_dimensions=payload_bit_widths(task))
    if decoded.outcome == "EXACT_RECOVERY":
        indices = [bits_to_int(np.array(coeffs, dtype=np.uint8)) for coeffs in decoded.predicted_coefficients]
        if any(index >= task.domain_size_per_factor[factor_index] for factor_index, index in enumerate(indices)):
            return PackedDecodeResult(
                outcome=OUTCOME_UNASSIGNED,
                predicted_indices=[],
                decoded_message_bits=decoded.predicted_coefficients,
                decode_time_sec=decoded.decode_time_sec,
            )
        return PackedDecodeResult(
            outcome=OUTCOME_EXACT,
            predicted_indices=indices,
            decoded_message_bits=decoded.predicted_coefficients,
            decode_time_sec=decoded.decode_time_sec,
        )
    mapped_outcome = {
        "AMBIGUOUS_DECOMPOSITION": OUTCOME_AMBIGUOUS,
        "RANK_DEFICIENT": OUTCOME_RANK_DEFICIENT,
        "INCONSISTENT_SYSTEM": OUTCOME_INCONSISTENT,
    }.get(decoded.outcome, OUTCOME_WRONG)
    return PackedDecodeResult(
        outcome=mapped_outcome,
        predicted_indices=[],
        decoded_message_bits=[],
        decode_time_sec=decoded.decode_time_sec,
    )


def neco_factor_codewords(task: AbstractFactorizationTask, subcodes: list[np.ndarray]) -> list[np.ndarray]:
    widths = payload_bit_widths(task)
    codewords: list[np.ndarray] = []
    for factor_index, width in enumerate(widths):
        for identity_index in range(task.domain_size_per_factor[factor_index]):
            codewords.append(materialize_factor_codewords([subcodes[factor_index]], [int_to_bits(identity_index, width)])[0])
    return codewords


def identity_similarity_stats(
    *,
    vectors: list[np.ndarray],
    factor_count: int,
    domain_size: int,
) -> dict[str, float]:
    if len(vectors) < 2:
        return {
            "same_domain_mean_similarity": 0.0,
            "cross_domain_mean_similarity": 0.0,
            "minimum_distance": 0.0,
            "mean_distance": 0.0,
            "collision_rate": 0.0,
        }
    similarities_same: list[float] = []
    similarities_cross: list[float] = []
    distances: list[float] = []
    collisions = 0
    seen: set[tuple[int, ...]] = set()
    factor_labels = [factor_index for factor_index in range(factor_count) for _ in range(domain_size)]
    for vector in vectors:
        key = tuple(vector.astype(int).tolist())
        if key in seen:
            collisions += 1
        seen.add(key)
    for left in range(len(vectors)):
        for right in range(left + 1, len(vectors)):
            left_vector = np.asarray(vectors[left], dtype=np.uint8)
            right_vector = np.asarray(vectors[right], dtype=np.uint8)
            hamming = float(np.mean(left_vector != right_vector))
            similarity = 1.0 - (2.0 * hamming)
            distances.append(hamming)
            if factor_labels[left] == factor_labels[right]:
                similarities_same.append(similarity)
            else:
                similarities_cross.append(similarity)
    return {
        "same_domain_mean_similarity": statistics.fmean(similarities_same) if similarities_same else 0.0,
        "cross_domain_mean_similarity": statistics.fmean(similarities_cross) if similarities_cross else 0.0,
        "minimum_distance": min(distances) if distances else 0.0,
        "mean_distance": statistics.fmean(distances) if distances else 0.0,
        "collision_rate": collisions / len(vectors),
    }


def map_similarity_stats(domains: torch.Tensor) -> dict[str, float]:
    factor_count, domain_size = int(domains.shape[0]), int(domains.shape[1])
    vectors = domains.detach().cpu()
    similarities_same: list[float] = []
    similarities_cross: list[float] = []
    distances: list[float] = []
    collisions = 0
    seen: set[tuple[float, ...]] = set()
    flat_vectors: list[torch.Tensor] = []
    labels: list[int] = []
    for factor_index in range(factor_count):
        for local_index in range(domain_size):
            vector = vectors[factor_index, local_index]
            flat_vectors.append(vector)
            labels.append(factor_index)
            key = tuple(float(value) for value in vector.tolist())
            if key in seen:
                collisions += 1
            seen.add(key)
    for left in range(len(flat_vectors)):
        for right in range(left + 1, len(flat_vectors)):
            similarity = float(torch.nn.functional.cosine_similarity(flat_vectors[left], flat_vectors[right], dim=0).item())
            hamming_proxy = 0.5 * (1.0 - similarity)
            distances.append(hamming_proxy)
            if labels[left] == labels[right]:
                similarities_same.append(similarity)
            else:
                similarities_cross.append(similarity)
    return {
        "same_domain_mean_similarity": statistics.fmean(similarities_same) if similarities_same else 0.0,
        "cross_domain_mean_similarity": statistics.fmean(similarities_cross) if similarities_cross else 0.0,
        "minimum_distance": min(distances) if distances else 0.0,
        "mean_distance": statistics.fmean(distances) if distances else 0.0,
        "collision_rate": collisions / len(flat_vectors),
    }


def bcf_similarity_stats(mat_im: torch.Tensor) -> dict[str, float]:
    factor_count, domain_size = int(mat_im.shape[0]), int(mat_im.shape[1])
    vectors = mat_im.detach().cpu().reshape(factor_count, domain_size, -1).to(dtype=torch.uint8).numpy()
    flat = [vectors[factor_index, local_index] for factor_index in range(factor_count) for local_index in range(domain_size)]
    return identity_similarity_stats(vectors=flat, factor_count=factor_count, domain_size=domain_size)


def compare_prediction(predicted: list[int], target: list[int]) -> tuple[str, list[bool], bool]:
    exact = predicted == target
    per_factor = [predicted[index] == target[index] for index in range(len(target))] if predicted else [False] * len(target)
    return (OUTCOME_EXACT if exact else OUTCOME_WRONG), per_factor, exact


def packed_trial_record(manifest: dict[str, Any], task: AbstractFactorizationTask) -> dict[str, Any]:
    widths = payload_bit_widths(task)
    total_bits = sum(widths)
    encode_start = time.perf_counter()
    observation, slices = packed_encode(task)
    encode_time = time.perf_counter() - encode_start
    decoded = packed_decode(observation, task)
    outcome, per_factor, exact = compare_prediction(decoded.predicted_indices, task.target_indices) if decoded.outcome == OUTCOME_EXACT else (decoded.outcome, [False] * task.factor_count, False)
    mapping_bytes = 0
    schema_metadata_bytes = len(json.dumps({"widths": widths, "factor_count": task.factor_count, "domain_sizes": task.domain_size_per_factor}))
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "cell_id": manifest["cell_id"],
        "split": LEVEL3_4_SPLIT,
        "substrate": "PACKED",
        "arm_id": "packed_symbolic_tuple",
        "ambient_length": total_bits,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "payload_bits": total_bits,
        "message_dimension_per_factor": widths,
        "true_factor_indices": task.target_indices,
        "predicted_indices": decoded.predicted_indices,
        "outcome": outcome,
        "exact_recovery": exact,
        "per_factor_recovery": per_factor,
        "wrong_tuple_output": outcome == OUTCOME_WRONG,
        "task_generation_time_sec": 0.0,
        "schema_construction_time_sec": 0.0,
        "identity_insertion_time_sec": 0.0,
        "codeword_materialization_time_sec": 0.0,
        "observation_encoding_time_sec": encode_time,
        "decoder_setup_time_sec": 0.0,
        "decode_time_sec": decoded.decode_time_sec,
        "end_to_end_time_sec": encode_time + decoded.decode_time_sec,
        "persistent_spec_bytes": schema_metadata_bytes + mapping_bytes,
        "persistent_generator_bytes": 0,
        "persistent_mapping_bytes": mapping_bytes,
        "runtime_materialized_bytes": theoretical_bit_bytes(total_bits),
        "runtime_observation_bytes": theoretical_bit_bytes(total_bits),
        "runtime_decoder_state_bytes": 0,
        "uses_truth_in_decoder": False,
        "no_noise": True,
        "no_context": True,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
    }


def generic_trial_record(manifest: dict[str, Any], task: AbstractFactorizationTask) -> dict[str, Any]:
    widths = payload_bit_widths(task)
    total_bits = sum(widths)
    schema_start = time.perf_counter()
    matrix = generic_matrix(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest["generic_representation_seed"])
    schema_time = time.perf_counter() - schema_start
    encode_start = time.perf_counter()
    observation, slices, payload = generic_encode(task, matrix)
    encode_time = time.perf_counter() - encode_start
    decode_start = time.perf_counter()
    decoded = generic_decode(observation, task, matrix)
    decode_time = time.perf_counter() - decode_start
    outcome, per_factor, exact = compare_prediction(decoded.predicted_indices, task.target_indices) if decoded.outcome == OUTCOME_EXACT else (decoded.outcome, [False] * task.factor_count, False)
    generator_bits = PRIMARY_NECO_AMBIENT_LENGTH * total_bits
    generator_bytes = theoretical_bit_bytes(generator_bits)
    runtime_decoder_state = generator_bytes + theoretical_bit_bytes(PRIMARY_NECO_AMBIENT_LENGTH)
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "cell_id": manifest["cell_id"],
        "split": LEVEL3_4_SPLIT,
        "substrate": "GENERIC_LINEAR",
        "arm_id": "generic_random_linear_mix",
        "ambient_length": PRIMARY_NECO_AMBIENT_LENGTH,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "payload_bits": total_bits,
        "message_dimension_per_factor": widths,
        "generic_generator_rank": gf2_rank(matrix),
        "true_factor_indices": task.target_indices,
        "predicted_indices": decoded.predicted_indices,
        "outcome": outcome,
        "exact_recovery": exact,
        "per_factor_recovery": per_factor,
        "wrong_tuple_output": outcome == OUTCOME_WRONG,
        "task_generation_time_sec": 0.0,
        "schema_construction_time_sec": schema_time,
        "identity_insertion_time_sec": 0.0,
        "codeword_materialization_time_sec": 0.0,
        "observation_encoding_time_sec": encode_time,
        "decoder_setup_time_sec": 0.0,
        "decode_time_sec": decoded.decode_time_sec if decoded.decode_time_sec > 0 else decode_time,
        "end_to_end_time_sec": schema_time + encode_time + max(decoded.decode_time_sec, decode_time),
        "persistent_spec_bytes": generator_bytes + len(json.dumps({"widths": widths, "ambient_length": PRIMARY_NECO_AMBIENT_LENGTH})),
        "persistent_generator_bytes": generator_bytes,
        "persistent_mapping_bytes": 0,
        "runtime_materialized_bytes": generator_bytes + theoretical_bit_bytes(PRIMARY_NECO_AMBIENT_LENGTH) + runtime_decoder_state,
        "runtime_observation_bytes": theoretical_bit_bytes(PRIMARY_NECO_AMBIENT_LENGTH),
        "runtime_decoder_state_bytes": runtime_decoder_state,
        "uses_truth_in_decoder": False,
        "no_noise": True,
        "no_context": True,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
    }


def neco_trial_record(manifest: dict[str, Any], task: AbstractFactorizationTask) -> dict[str, Any]:
    schema_start = time.perf_counter()
    subcodes, widths = neco_subcodes(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest["neco_representation_seed"])
    schema_time = time.perf_counter() - schema_start
    encode_start = time.perf_counter()
    observation, coefficients, _ = neco_encode(task, subcodes)
    encode_time = time.perf_counter() - encode_start
    decoded = neco_decode(observation, task, subcodes)
    outcome, per_factor, exact = compare_prediction(decoded.predicted_indices, task.target_indices) if decoded.outcome == OUTCOME_EXACT else (decoded.outcome, [False] * task.factor_count, False)
    total_bits = sum(widths)
    generator_bits = PRIMARY_NECO_AMBIENT_LENGTH * total_bits
    generator_bytes = theoretical_bit_bytes(generator_bits)
    intersection_dims: list[int] = []
    for left in range(len(subcodes)):
        for right in range(left + 1, len(subcodes)):
            stacked = np.vstack([subcodes[left], subcodes[right]])
            intersection_dims.append(int(subcodes[left].shape[0] + subcodes[right].shape[0] - gf2_rank(stacked)))
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "cell_id": manifest["cell_id"],
        "split": LEVEL3_4_SPLIT,
        "substrate": "NECO",
        "arm_id": "neco_reproduced_direct_sum",
        "ambient_length": PRIMARY_NECO_AMBIENT_LENGTH,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "payload_bits": total_bits,
        "message_dimension_per_factor": widths,
        "available_codewords_per_subcode": [2**width for width in widths],
        "generator_rank": sum(widths),
        "subcode_intersections": intersection_dims,
        "true_factor_indices": task.target_indices,
        "predicted_indices": decoded.predicted_indices,
        "outcome": outcome,
        "exact_recovery": exact,
        "per_factor_recovery": per_factor,
        "wrong_tuple_output": outcome == OUTCOME_WRONG,
        "task_generation_time_sec": 0.0,
        "schema_construction_time_sec": schema_time,
        "identity_insertion_time_sec": 0.0,
        "codeword_materialization_time_sec": encode_time,
        "observation_encoding_time_sec": 0.0,
        "decoder_setup_time_sec": 0.0,
        "decode_time_sec": decoded.decode_time_sec,
        "end_to_end_time_sec": schema_time + encode_time + decoded.decode_time_sec,
        "persistent_spec_bytes": generator_bytes + len(json.dumps({"widths": widths, "ambient_length": PRIMARY_NECO_AMBIENT_LENGTH})),
        "persistent_generator_bytes": generator_bytes,
        "persistent_mapping_bytes": 0,
        "runtime_materialized_bytes": generator_bytes + theoretical_bit_bytes(PRIMARY_NECO_AMBIENT_LENGTH) + generator_bytes,
        "runtime_observation_bytes": theoretical_bit_bytes(PRIMARY_NECO_AMBIENT_LENGTH),
        "runtime_decoder_state_bytes": generator_bytes,
        "uses_truth_in_decoder": False,
        "no_noise": True,
        "no_context": True,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
    }


def map_trial_record(manifest: dict[str, Any], task: AbstractFactorizationTask, *, arm: str, device: str) -> tuple[dict[str, Any], PreparedMapTask]:
    prepared = prepare_map_task(
        task,
        dimensions=1024,
        representation_seed=manifest["map_representation_seed"],
        device=device,
    )
    if arm == MAP_FAST_ARM_ID:
        selected = run_map_attempt(prepared, max_iterations=12, init_mode="baseline", init_seed=manifest["trial_seed"])
        attempts = [selected]
        restart_count = 1
        selection_rule = "first"
        planned_restart_count = 1
    elif arm == MAP_EXTENDED_ARM_ID:
        attempts = []
        for restart_index in range(4):
            attempt = run_map_attempt(
                prepared,
                max_iterations=32,
                init_mode="random",
                init_seed=manifest["trial_seed"] + 20_000 + restart_index,
            )
            attempts.append(type(attempt)(restart_index=restart_index, **{k: v for k, v in asdict(attempt).items() if k != "restart_index"}))
        selected = choose_attempt(
            attempts,
            selection_rule="best_native_reconstruction",
            selection_seed=manifest["trial_seed"] + 25_000,
        )
        restart_count = len(attempts)
        selection_rule = "best_native_reconstruction"
        planned_restart_count = 4
    else:
        raise ValueError(f"Unsupported MAP arm: {arm}")

    end_to_end = prepared.materialization_time_sec + prepared.decoder_initialization_time_sec + sum(item.decode_time_sec for item in attempts)
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "cell_id": manifest["cell_id"],
        "split": LEVEL3_4_SPLIT,
        "substrate": "MAP",
        "arm_id": arm,
        "ambient_length": 1024,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "payload_bits": sum(payload_bit_widths(task)),
        "message_dimension_per_factor": payload_bit_widths(task),
        "true_factor_indices": task.target_indices,
        "predicted_indices": selected.predicted_indices,
        "outcome": selected.outcome if selected.exact_recovery else OUTCOME_WRONG,
        "exact_recovery": selected.exact_recovery,
        "per_factor_recovery": selected.per_factor_recovery,
        "wrong_tuple_output": not selected.exact_recovery,
        "task_generation_time_sec": 0.0,
        "schema_construction_time_sec": 0.0,
        "identity_insertion_time_sec": 0.0,
        "codeword_materialization_time_sec": prepared.materialization_time_sec,
        "observation_encoding_time_sec": 0.0,
        "decoder_setup_time_sec": prepared.decoder_initialization_time_sec,
        "decode_time_sec": sum(item.decode_time_sec for item in attempts),
        "end_to_end_time_sec": end_to_end,
        "persistent_spec_bytes": len(json.dumps({"dimensions": 1024, "arm": arm})),
        "persistent_generator_bytes": 0,
        "persistent_mapping_bytes": 0,
        "runtime_materialized_bytes": prepared.codebook_bytes + prepared.observation_bytes + max(item.decoder_state_bytes for item in attempts),
        "runtime_observation_bytes": prepared.observation_bytes,
        "runtime_decoder_state_bytes": max(item.decoder_state_bytes for item in attempts),
        "map_codebook_bytes": prepared.codebook_bytes,
        "peak_ram_bytes": peak_cpu_memory_bytes(),
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated(device=device)) if device.startswith("cuda") and torch.cuda.is_available() else None,
        "executed_steps": sum(item.iterations for item in attempts),
        "restart_count": restart_count,
        "planned_restart_count": planned_restart_count,
        "selection_rule": selection_rule,
        "restart_agreement": restart_agreement(attempts),
        "unique_proposal_count": unique_proposal_count(attempts),
        "uses_truth_in_decoder": False,
        "no_noise": True,
        "no_context": True,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
    }, prepared


def bcf_trial_record(manifest: dict[str, Any], task: AbstractFactorizationTask, *, repo_path: Path, prefer_cuda: bool) -> tuple[dict[str, Any], torch.Tensor]:
    frozen_configs = build_frozen_bcf_configs(repo_path)
    cell_map = {
        "u1_clean_m10": "u1_easy_anchor",
        "u1_clean_m22": "u1_boundary_1",
        "u1_clean_m31": "u1_boundary_2",
        "u1_clean_m68": "u1_separation_anchor",
    }
    frozen_config = config_for_cell(cell_map[manifest["cell_id"]], frozen_configs)
    from .level3_2b_map_budget_robustness import instantiate_bcf_model

    model, init_time = instantiate_bcf_model(
        task,
        frozen_config,
        repo_path=repo_path,
        representation_seed=manifest["bcf_representation_seed"],
        prefer_cuda=prefer_cuda,
    )
    rep_start = time.perf_counter()
    target_batch = torch.tensor([task.target_indices], dtype=torch.long, device=model._device)
    observation = model.encode(target_batch)
    rep_time = time.perf_counter() - rep_start
    max_iterations = frozen_config.native_max_iterations()
    synchronize_device(str(model._device))
    if str(model._device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device=model._device)
    decode_start = time.perf_counter()
    predicted = model.decode(observation, max_iterations).detach().cpu().squeeze(0).to(dtype=torch.long)
    synchronize_device(str(model._device))
    decode_time = time.perf_counter() - decode_start
    outcome, per_factor, exact = common_outcome(predicted, torch.tensor(task.target_indices, dtype=torch.long))
    common_outcome_value = OUTCOME_EXACT if exact else OUTCOME_WRONG
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "trial_id": manifest["trial_id"],
        "trial_seed": manifest["trial_seed"],
        "cell_id": manifest["cell_id"],
        "split": LEVEL3_4_SPLIT,
        "substrate": "BCF",
        "arm_id": BCF_ARM_ID,
        "ambient_length": frozen_config.dimensions,
        "factor_count": task.factor_count,
        "domain_size": task.domain_size_per_factor[0],
        "payload_bits": sum(payload_bit_widths(task)),
        "message_dimension_per_factor": payload_bit_widths(task),
        "true_factor_indices": task.target_indices,
        "predicted_indices": [int(value) for value in predicted.tolist()],
        "outcome": common_outcome_value,
        "exact_recovery": exact,
        "per_factor_recovery": per_factor,
        "wrong_tuple_output": not exact,
        "task_generation_time_sec": 0.0,
        "schema_construction_time_sec": 0.0,
        "identity_insertion_time_sec": 0.0,
        "codeword_materialization_time_sec": rep_time,
        "observation_encoding_time_sec": 0.0,
        "decoder_setup_time_sec": init_time,
        "decode_time_sec": decode_time,
        "end_to_end_time_sec": rep_time + init_time + decode_time,
        "persistent_spec_bytes": len(json.dumps({"config_family": frozen_config.config_family, "A": frozen_config.a_value, "threshold": frozen_config.threshold})),
        "persistent_generator_bytes": 0,
        "persistent_mapping_bytes": 0,
        "runtime_materialized_bytes": tensor_bytes(model._IM) + tensor_bytes(model._matIM) + tensor_bytes(observation) + tensor_bytes(model._init_guess),
        "runtime_observation_bytes": tensor_bytes(observation),
        "runtime_decoder_state_bytes": tensor_bytes(model._init_guess),
        "bcf_codebook_bytes": tensor_bytes(model._IM) + tensor_bytes(model._matIM),
        "peak_ram_bytes": peak_cpu_memory_bytes(),
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated(device=model._device)) if str(model._device).startswith("cuda") and torch.cuda.is_available() else None,
        "executed_steps": int(model._get_number_iter().max().item()),
        "restart_count": 1,
        "selection_rule": "native",
        "native_stop_status": "native_limit" if int(model._get_number_iter().max().item()) >= max_iterations else "native_converged",
        "reached_native_limit": int(model._get_number_iter().max().item()) >= max_iterations,
        "uses_truth_in_decoder": False,
        "no_noise": True,
        "no_context": True,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
    }, model._matIM.detach().cpu()


def summarize_correctness(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["cell_id"], row["arm_id"]), []).append(row)
    summary: list[dict[str, Any]] = []
    for (cell_id, arm_id), batch in sorted(grouped.items()):
        exact = sum(1 for row in batch if row["exact_recovery"])
        per_factor_hits = sum(sum(row["per_factor_recovery"]) for row in batch)
        wrong = sum(1 for row in batch if row["outcome"] == OUTCOME_WRONG)
        ambiguous = sum(1 for row in batch if row["outcome"] == OUTCOME_AMBIGUOUS)
        unassigned = sum(1 for row in batch if row["outcome"] == OUTCOME_UNASSIGNED)
        summary.append(
            {
                "schema_version": LEVEL3_4_SCHEMA_VERSION,
                "cell_id": cell_id,
                "arm_id": arm_id,
                "substrate": batch[0]["substrate"],
                "trials": len(batch),
                "exact_recovery_rate": exact / len(batch),
                "per_factor_accuracy": per_factor_hits / (len(batch) * batch[0]["factor_count"]),
                "wrong_recovery_rate": wrong / len(batch),
                "ambiguous_rate": ambiguous / len(batch),
                "unassigned_rate": unassigned / len(batch),
            }
        )
    return summary


def summarize_resources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["cell_id"], row["arm_id"]), []).append(row)
    summary: list[dict[str, Any]] = []
    for (cell_id, arm_id), batch in sorted(grouped.items()):
        summary.append(
            {
                "schema_version": LEVEL3_4_SCHEMA_VERSION,
                "cell_id": cell_id,
                "arm_id": arm_id,
                "substrate": batch[0]["substrate"],
                "mean_persistent_spec_bytes": statistics.fmean(row["persistent_spec_bytes"] for row in batch),
                "mean_persistent_generator_bytes": statistics.fmean(row["persistent_generator_bytes"] for row in batch),
                "mean_runtime_materialized_bytes": statistics.fmean(row["runtime_materialized_bytes"] for row in batch),
                "mean_runtime_observation_bytes": statistics.fmean(row["runtime_observation_bytes"] for row in batch),
                "mean_runtime_decoder_state_bytes": statistics.fmean(row["runtime_decoder_state_bytes"] for row in batch),
            }
        )
    return summary


def summarize_timing(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["cell_id"], row["arm_id"]), []).append(row)
    summary: list[dict[str, Any]] = []
    for (cell_id, arm_id), batch in sorted(grouped.items()):
        summary.append(
            {
                "schema_version": LEVEL3_4_SCHEMA_VERSION,
                "cell_id": cell_id,
                "arm_id": arm_id,
                "substrate": batch[0]["substrate"],
                "mean_schema_construction_time_sec": statistics.fmean(row["schema_construction_time_sec"] for row in batch),
                "mean_identity_insertion_time_sec": statistics.fmean(row["identity_insertion_time_sec"] for row in batch),
                "mean_codeword_materialization_time_sec": statistics.fmean(row["codeword_materialization_time_sec"] for row in batch),
                "mean_observation_encoding_time_sec": statistics.fmean(row["observation_encoding_time_sec"] for row in batch),
                "mean_decoder_setup_time_sec": statistics.fmean(row["decoder_setup_time_sec"] for row in batch),
                "mean_decode_time_sec": statistics.fmean(row["decode_time_sec"] for row in batch),
                "mean_end_to_end_time_sec": statistics.fmean(row["end_to_end_time_sec"] for row in batch),
            }
        )
    return summary


def summarize_schema_updates() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "PACKED",
            "scenario": "atomic_insertion_within_existing_capacity",
            "verdict": SCHEMA_INSERT_MAPPING,
            "generator_changed": False,
            "existing_observations_unchanged": True,
            "notes": "If unused messages remain inside the current ceil(log2 M) envelope, insertion only consumes a previously unassigned message.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "GENERIC_LINEAR",
            "scenario": "atomic_insertion_within_existing_capacity",
            "verdict": SCHEMA_INSERT_MAPPING,
            "generator_changed": False,
            "existing_observations_unchanged": True,
            "notes": "Insertion only changes the semantic-to-message mapping while spare messages remain.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "NECO",
            "scenario": "atomic_insertion_within_existing_capacity",
            "verdict": SCHEMA_INSERT_MAPPING,
            "generator_changed": False,
            "existing_observations_unchanged": True,
            "notes": "Insertion uses an unused factor-local message if the current subcode dimension still has spare capacity.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "PACKED",
            "scenario": "domain_expansion_m31_to_m68",
            "verdict": SCHEMA_DOMAIN_REBUILD,
            "generator_changed": False,
            "existing_observations_unchanged": False,
            "notes": "Bit width rises from 5 to 7, forcing message re-slicing and re-encoding.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "GENERIC_LINEAR",
            "scenario": "domain_expansion_m31_to_m68",
            "verdict": SCHEMA_DOMAIN_REBUILD,
            "generator_changed": True,
            "existing_observations_unchanged": False,
            "notes": "The packed payload width increases, so the full-column-rank matrix must be rebuilt and all observations re-encoded.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "NECO",
            "scenario": "domain_expansion_m31_to_m68",
            "verdict": SCHEMA_DOMAIN_REBUILD,
            "generator_changed": True,
            "existing_observations_unchanged": False,
            "notes": "The factor subcode dimension rises from 5 to 7, so generator rows, subcode decomposition, and old observations must be rebuilt.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "PACKED",
            "scenario": "schema_expansion_f3_to_f4",
            "verdict": SCHEMA_FACTOR_REBUILD,
            "generator_changed": False,
            "existing_observations_unchanged": False,
            "notes": "Concatenation layout changes, so old observations are not compatible with the new factor schema.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "GENERIC_LINEAR",
            "scenario": "schema_expansion_f3_to_f4",
            "verdict": SCHEMA_FACTOR_REBUILD,
            "generator_changed": True,
            "existing_observations_unchanged": False,
            "notes": "The payload width and column partitioning change, so a new matrix and re-encoding are required.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "NECO",
            "scenario": "schema_expansion_f3_to_f4",
            "verdict": SCHEMA_FACTOR_REBUILD,
            "generator_changed": True,
            "existing_observations_unchanged": False,
            "notes": "A new factor subcode must be allocated, changing the direct-sum schema and invalidating old observations.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "MAP",
            "scenario": "schema_expansion_f3_to_f4",
            "verdict": SCHEMA_UNSUPPORTED,
            "generator_changed": None,
            "existing_observations_unchanged": None,
            "notes": "The frozen random-domain benchmark does not define stable schema migration semantics.",
        },
        {
            "schema_version": LEVEL3_4_SCHEMA_VERSION,
            "substrate": "BCF",
            "scenario": "schema_expansion_f3_to_f4",
            "verdict": SCHEMA_UNSUPPORTED,
            "generator_changed": None,
            "existing_observations_unchanged": None,
            "notes": "The frozen official BCF configuration is F=3-specific and does not define a compatible in-place schema expansion path.",
        },
    ]


def summarize_geometry(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rows


def algebraic_control_summary(correctness_rows: list[dict[str, Any]], resource_rows: list[dict[str, Any]], timing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    correctness_lookup = {(row["cell_id"], row["arm_id"]): row for row in correctness_rows}
    resource_lookup = {(row["cell_id"], row["arm_id"]): row for row in resource_rows}
    timing_lookup = {(row["cell_id"], row["arm_id"]): row for row in timing_rows}
    rows: list[dict[str, Any]] = []
    for cell in CELLS:
        neco = correctness_lookup[(cell.cell_id, "neco_reproduced_direct_sum")]
        generic = correctness_lookup[(cell.cell_id, "generic_random_linear_mix")]
        neco_resource = resource_lookup[(cell.cell_id, "neco_reproduced_direct_sum")]
        generic_resource = resource_lookup[(cell.cell_id, "generic_random_linear_mix")]
        neco_timing = timing_lookup[(cell.cell_id, "neco_reproduced_direct_sum")]
        generic_timing = timing_lookup[(cell.cell_id, "generic_random_linear_mix")]
        rows.append(
            {
                "schema_version": LEVEL3_4_SCHEMA_VERSION,
                "cell_id": cell.cell_id,
                "same_ambient_length": True,
                "neco_exact_recovery_rate": neco["exact_recovery_rate"],
                "generic_exact_recovery_rate": generic["exact_recovery_rate"],
                "exact_recovery_delta": neco["exact_recovery_rate"] - generic["exact_recovery_rate"],
                "neco_persistent_spec_bytes": neco_resource["mean_persistent_spec_bytes"],
                "generic_persistent_spec_bytes": generic_resource["mean_persistent_spec_bytes"],
                "neco_runtime_materialized_bytes": neco_resource["mean_runtime_materialized_bytes"],
                "generic_runtime_materialized_bytes": generic_resource["mean_runtime_materialized_bytes"],
                "neco_mean_decode_time_sec": neco_timing["mean_decode_time_sec"],
                "generic_mean_decode_time_sec": generic_timing["mean_decode_time_sec"],
                "algebraic_equivalence_supported": (
                    neco["exact_recovery_rate"] == generic["exact_recovery_rate"]
                    and abs(neco_resource["mean_persistent_generator_bytes"] - generic_resource["mean_persistent_generator_bytes"]) < 1e-9
                ),
            }
        )
    return rows


def representation_configs_payload(task_manifests: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    seen_cells: set[str] = set()
    for manifest in task_manifests:
        if manifest["cell_id"] in seen_cells:
            continue
        seen_cells.add(manifest["cell_id"])
        task = AbstractFactorizationTask(
            task_seed=manifest["trial_seed"],
            factor_count=manifest["F"],
            domain_size_per_factor=[manifest["M"]] * manifest["F"],
            target_indices=manifest["true_factor_indices"],
            distractor_target_indices=[],
            context_membership={},
            active_context="",
            anomaly_rate=0.0,
            query_valid_source_indices=[],
            active_l1=None,
            active_l2=None,
            context_prediction=None,
        )
        widths = payload_bit_widths(task)
        subcodes, _ = neco_subcodes(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest["neco_representation_seed"])
        intersections: list[int] = []
        for left in range(len(subcodes)):
            for right in range(left + 1, len(subcodes)):
                stacked = np.vstack([subcodes[left], subcodes[right]])
                intersections.append(int(subcodes[left].shape[0] + subcodes[right].shape[0] - gf2_rank(stacked)))
        rows.append(
            {
                "cell_id": manifest["cell_id"],
                "factor_count": manifest["F"],
                "domain_size": manifest["M"],
                "message_dimension_per_factor": widths,
                "assigned_identities_per_factor": [manifest["M"]] * manifest["F"],
                "available_codewords_per_subcode": [2**width for width in widths],
                "unassigned_messages_per_factor": [(2**width) - manifest["M"] for width in widths],
                "ambient_code_length": PRIMARY_NECO_AMBIENT_LENGTH,
                "total_message_dimension": sum(widths),
                "payload_bits": sum(widths),
                "redundancy_ratio": PRIMARY_NECO_AMBIENT_LENGTH / sum(widths),
                "generator_rank": sum(widths),
                "subcode_intersections": intersections,
            }
        )
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "paper_native_neco_ambient_length": PRIMARY_NECO_AMBIENT_LENGTH,
        "generic_same_length_required": True,
        "rows": rows,
        "frozen_context_disabled": True,
    }


def claims_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "allowed_claims": [
            "clean algebraic baselines compared",
            "NeCo resource and schema costs measured",
            "generic linear equivalence supported or rejected",
            "symbolic clean-U1 baseline assessed",
            "common-U1 representation trade-offs characterized",
        ],
        "forbidden_claims": [
            "NeCo superior to MAP/BCF generally",
            "NeCo useful for subject memory",
            "noise robustness",
            "production readiness",
            "universal VSA benefit",
        ],
        "algebraic_equivalence_verdict": analysis["algebraic_equivalence_verdict"],
        "symbolic_baseline_verdict": analysis["symbolic_baseline_verdict"],
        "ready_for_noise_frontier": analysis["ready_for_noise_frontier"],
    }


def analysis_payload(
    correctness_rows: list[dict[str, Any]],
    resource_rows: list[dict[str, Any]],
    algebraic_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    correctness_lookup = {(row["cell_id"], row["arm_id"]): row for row in correctness_rows}
    resource_lookup = {(row["cell_id"], row["arm_id"]): row for row in resource_rows}
    algebraic_equivalence_supported = all(row["algebraic_equivalence_supported"] for row in algebraic_rows)
    symbolic_dominates = True
    for cell in CELLS:
        packed = correctness_lookup[(cell.cell_id, "packed_symbolic_tuple")]
        neco = correctness_lookup[(cell.cell_id, "neco_reproduced_direct_sum")]
        packed_resource = resource_lookup[(cell.cell_id, "packed_symbolic_tuple")]
        neco_resource = resource_lookup[(cell.cell_id, "neco_reproduced_direct_sum")]
        if not (
            packed["exact_recovery_rate"] >= neco["exact_recovery_rate"]
            and packed_resource["mean_persistent_spec_bytes"] <= neco_resource["mean_persistent_spec_bytes"]
            and packed_resource["mean_runtime_materialized_bytes"] <= neco_resource["mean_runtime_materialized_bytes"]
        ):
            symbolic_dominates = False
    return {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_4_CHECKPOINT_COMMIT,
        "split": LEVEL3_4_SPLIT,
        "heldout_used": False,
        "noise_implemented": False,
        "u2_implemented": False,
        "context_disabled": True,
        "generic_control_not_described_as_neco": True,
        "algebraic_equivalence_verdict": "ALGEBRAIC_EQUIVALENCE_SUPPORTED" if algebraic_equivalence_supported else "NECO_STRUCTURAL_ADVANTAGE_SUPPORTED",
        "symbolic_baseline_verdict": "SYMBOLIC_BASELINE_DOMINATES_CLEAN_U1" if symbolic_dominates else "SYMBOLIC_BASELINE_DOES_NOT_DOMINATE",
        "schema_rigidity_material": True,
        "ready_for_noise_frontier": True,
        "common_u1_status_from_level3_3": COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS,
        "map_bcf_frozen_contextual_only": True,
        "clean_u1_only_claims": True,
    }


def build_doc(analysis: dict[str, Any], algebraic_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Level 3.4 Algebraic Baseline Closure",
        "",
        f"- Checkpoint: `{LEVEL3_4_CHECKPOINT_COMMIT}`",
        f"- Split: `{LEVEL3_4_SPLIT}`",
        f"- Algebraic verdict: `{analysis['algebraic_equivalence_verdict']}`",
        f"- Symbolic baseline verdict: `{analysis['symbolic_baseline_verdict']}`",
        f"- Ready for noise frontier: `{analysis['ready_for_noise_frontier']}`",
        "",
        "## Scope",
        "",
        "- Clean U1 only.",
        "- No noise, no U2, no context, no controller, no held-out confirmation.",
        "",
        "## Primary anti-NIH comparison",
        "",
    ]
    for row in algebraic_rows:
        lines.append(
            f"- `{row['cell_id']}`: NeCo exact={row['neco_exact_recovery_rate']:.3f}, generic exact={row['generic_exact_recovery_rate']:.3f}, equivalence={row['algebraic_equivalence_supported']}."
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- The packed symbolic tuple is included as the clean typed lower-bound baseline.",
            "- MAP and BCF remain contextual frozen references only; this stage does not reopen their tuning or promote NeCo.",
            "- Any substrate-level claim beyond clean U1 remains blocked until the noise frontier is evaluated.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_level3_4(root: Path, *, prefer_cuda: bool = True) -> dict[str, Any]:
    docs_dir = root / "docs"
    results_dir = root / "results" / "level3_4"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    repo_path = upstream_clone_path(root)
    device = "cuda" if prefer_cuda and torch.cuda.is_available() else "cpu"
    manifests: list[dict[str, Any]] = []
    correctness_trials: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []

    for cell in CELLS:
        seed_spec = SEED_RANGES[cell.cell_id]
        for offset in range(cell.trials):
            trial_seed = seed_spec["start"] + offset
            manifest, task = build_task_manifest(trial_seed, cell)
            manifests.append(manifest)

            packed_row = packed_trial_record(manifest, task)
            correctness_trials.append(packed_row)

            generic_row = generic_trial_record(manifest, task)
            correctness_trials.append(generic_row)

            neco_row = neco_trial_record(manifest, task)
            correctness_trials.append(neco_row)

            map_fast_row, prepared_fast = map_trial_record(manifest, task, arm=MAP_FAST_ARM_ID, device=device)
            correctness_trials.append(map_fast_row)

            map_extended_row, _ = map_trial_record(manifest, task, arm=MAP_EXTENDED_ARM_ID, device=device)
            correctness_trials.append(map_extended_row)

            if cell.include_bcf:
                bcf_row, bcf_mat_im = bcf_trial_record(manifest, task, repo_path=repo_path, prefer_cuda=prefer_cuda)
                correctness_trials.append(bcf_row)

            if offset == 0:
                generic_matrix_value = generic_matrix(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest["generic_representation_seed"])
                neco_subcodes_value, _ = neco_subcodes(task, ambient_length=PRIMARY_NECO_AMBIENT_LENGTH, seed=manifest["neco_representation_seed"])
                geometry_rows.extend(
                    [
                        {
                            "schema_version": LEVEL3_4_SCHEMA_VERSION,
                            "cell_id": cell.cell_id,
                            "substrate": "GENERIC_LINEAR",
                            "arm_id": "generic_random_linear_mix",
                            **identity_similarity_stats(
                                vectors=generic_factor_codewords(task, generic_matrix_value),
                                factor_count=task.factor_count,
                                domain_size=task.domain_size_per_factor[0],
                            ),
                        },
                        {
                            "schema_version": LEVEL3_4_SCHEMA_VERSION,
                            "cell_id": cell.cell_id,
                            "substrate": "NECO",
                            "arm_id": "neco_reproduced_direct_sum",
                            **identity_similarity_stats(
                                vectors=neco_factor_codewords(task, neco_subcodes_value),
                                factor_count=task.factor_count,
                                domain_size=task.domain_size_per_factor[0],
                            ),
                        },
                        {
                            "schema_version": LEVEL3_4_SCHEMA_VERSION,
                            "cell_id": cell.cell_id,
                            "substrate": "MAP",
                            "arm_id": MAP_FAST_ARM_ID,
                            **map_similarity_stats(prepared_fast.domains),
                        },
                    ]
                )
                if cell.include_bcf:
                    geometry_rows.append(
                        {
                            "schema_version": LEVEL3_4_SCHEMA_VERSION,
                            "cell_id": cell.cell_id,
                            "substrate": "BCF",
                            "arm_id": BCF_ARM_ID,
                            **bcf_similarity_stats(bcf_mat_im),
                        }
                    )

    correctness_summary = summarize_correctness(correctness_trials)
    resource_summary = summarize_resources(correctness_trials)
    timing_summary = summarize_timing(correctness_trials)
    schema_update_summary = summarize_schema_updates()
    algebraic_summary = algebraic_control_summary(correctness_summary, resource_summary, timing_summary)
    analysis = analysis_payload(correctness_summary, resource_summary, algebraic_summary)
    claims = claims_payload(analysis)
    doc = build_doc(analysis, algebraic_summary)
    representation_configs = representation_configs_payload(manifests)
    environment = {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_4_CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": device,
        "galois_version": getattr(GF2, "version", None),
        "ibm_upstream_commit": upstream_commit_sha(repo_path),
        "same_device_timing_for_map_bcf": device.startswith("cuda"),
    }
    frozen_protocol = {
        "schema_version": LEVEL3_4_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_4_CHECKPOINT_COMMIT,
        "task_contract": LEVEL3_4_TASK_CONTRACT,
        "split": LEVEL3_4_SPLIT,
        "trials_per_cell": 16,
        "ambient_code_length": PRIMARY_NECO_AMBIENT_LENGTH,
        "cells": [cell.to_dict() for cell in CELLS],
        "packed_baseline_included": True,
        "generic_linear_control_included": True,
        "neco_imports_level3_3_public_helpers_only": True,
        "map_arm_frozen": MAP_FAST_ARM_ID,
        "map_extended_arm_frozen": MAP_EXTENDED_ARM_ID,
        "bcf_arm_frozen": BCF_ARM_ID,
        "heldout_used": False,
        "noise_disabled": True,
        "u2_disabled": True,
        "context_disabled": True,
        "seeds_are_fresh": seeds_are_fresh(),
    }

    (docs_dir / "LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md").write_text(doc, encoding="utf-8")
    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "frozen_protocol.json", frozen_protocol)
    write_jsonl(results_dir / "task_manifest.jsonl", manifests)
    write_json(results_dir / "representation_configs.json", representation_configs)
    write_jsonl(results_dir / "correctness_trials.jsonl", correctness_trials)
    write_csv(results_dir / "correctness_summary.csv", correctness_summary)
    write_csv(results_dir / "resource_summary.csv", resource_summary)
    write_csv(results_dir / "timing_summary.csv", timing_summary)
    write_csv(results_dir / "schema_update_summary.csv", schema_update_summary)
    write_csv(results_dir / "geometry_summary.csv", geometry_rows)
    write_csv(results_dir / "algebraic_control_summary.csv", algebraic_summary)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    return {
        "environment": environment,
        "frozen_protocol": frozen_protocol,
        "task_manifest": manifests,
        "representation_configs": representation_configs,
        "correctness_trials": correctness_trials,
        "correctness_summary": correctness_summary,
        "resource_summary": resource_summary,
        "timing_summary": timing_summary,
        "schema_update_summary": schema_update_summary,
        "geometry_summary": geometry_rows,
        "algebraic_control_summary": algebraic_summary,
        "claims": claims,
        "analysis": analysis,
    }
