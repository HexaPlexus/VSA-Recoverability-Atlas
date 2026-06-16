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

import galois
import numpy as np

LEVEL3_3_SCHEMA_VERSION = "level3-3-neco-clean-u1-reproduction-v1"
LEVEL3_3_CHECKPOINT_COMMIT = "a3ca3b3536837447a6d8177e1b0b36a5258772fa"
LEVEL3_3_TASK_CONTRACT = "U1_blind_clean_single_product_factorization"
LEVEL3_3_PAPER_TITLE = "Linear Codes for Hyperdimensional Computing"
LEVEL3_3_PAPER_URL = "https://arxiv.org/abs/2403.03278"
LEVEL3_3_SOURCE_PATH = Path.home() / "AppData" / "Local" / "Temp" / "neco_linear_codes_source" / "arXiv_version.tex"
LEVEL3_3_DOC_STATUS = "UNAMBIGUOUS_PAPER_CONTRACT"

OUTCOME_EXACT = "EXACT_RECOVERY"
OUTCOME_AMBIGUOUS = "AMBIGUOUS_DECOMPOSITION"
OUTCOME_RANK_DEFICIENT = "RANK_DEFICIENT"
OUTCOME_INCONSISTENT = "INCONSISTENT_SYSTEM"
OUTCOME_COLLISION = "COLLISION"
OUTCOME_FAILURE = "IMPLEMENTATION_FAILURE"
OUTCOME_PAPER_AMBIGUOUS = "PAPER_CONTRACT_AMBIGUOUS"

COMMON_U1_COMPATIBLE = "COMMON_U1_COMPATIBLE"
COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS = "COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS"
TASK_MISMATCH = "TASK_MISMATCH"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

GF2 = galois.GF(2)


@dataclass(frozen=True)
class PaperContractEntry:
    key: str
    value: str
    source_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryResult:
    outcome: str
    predicted_coefficients: list[list[int]]
    predicted_codewords_pm1: list[list[int]]
    predicted_identity_indices: list[int]
    system_rank: int
    expected_rank: int
    nullity: int
    number_of_solutions_if_available: int | None
    rebind_matches_observation: bool
    truth_used_in_decoder: bool
    factor_mapping_deterministic: bool
    decode_time_sec: float
    solve_time_sec: float
    decoder_state_bytes: int
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NativeTrialSpec:
    trial_id: str
    seed: int
    ambient_length: int
    factor_count: int
    subcode_dimension: int
    trials: int

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


def bits_to_pm1(vector: np.ndarray) -> np.ndarray:
    bits = np.asarray(vector, dtype=np.uint8)
    return np.where(bits == 0, 1, -1).astype(np.int8)


def pm1_to_bits(vector: np.ndarray) -> np.ndarray:
    values = np.asarray(vector, dtype=np.int8)
    if not np.all(np.isin(values, (-1, 1))):
        raise ValueError("Expected +/-1 representation.")
    return np.where(values == -1, 1, 0).astype(np.uint8)


def theoretical_bit_bytes(bit_count: int) -> int:
    return math.ceil(bit_count / 8)


def runtime_bytes(array: np.ndarray) -> int:
    return int(array.nbytes)


def random_full_rank_matrix(rows: int, cols: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    attempt = 0
    while True:
        matrix = rng.integers(0, 2, size=(rows, cols), dtype=np.uint8)
        if gf2_rank(matrix) == rows:
            return matrix
        attempt += 1
        if attempt > 5_000:
            raise RuntimeError(f"Failed to sample full-rank GF(2) matrix for rows={rows}, cols={cols}.")


def gf2_rank(matrix: np.ndarray) -> int:
    if matrix.size == 0:
        return 0
    field_matrix = GF2(np.asarray(matrix, dtype=np.uint8))
    return int(np.linalg.matrix_rank(field_matrix))


def gf2_rref(augmented: np.ndarray, n_variables: int) -> tuple[np.ndarray, list[int], int]:
    work = np.asarray(augmented, dtype=np.uint8).copy()
    rows, _ = work.shape
    pivot_row = 0
    pivot_columns: list[int] = []
    for col in range(n_variables):
        pivot = None
        for row in range(pivot_row, rows):
            if int(work[row, col]) == 1:
                pivot = row
                break
        if pivot is None:
            continue
        if pivot != pivot_row:
            work[[pivot_row, pivot]] = work[[pivot, pivot_row]]
        for row in range(rows):
            if row != pivot_row and int(work[row, col]) == 1:
                work[row, :] ^= work[pivot_row, :]
        pivot_columns.append(col)
        pivot_row += 1
        if pivot_row == rows:
            break
    return work, pivot_columns, len(pivot_columns)


def gf2_solve_unique(a_matrix: np.ndarray, b_vector: np.ndarray) -> tuple[str, np.ndarray | None, int, int | None]:
    coefficients = np.asarray(a_matrix, dtype=np.uint8)
    rhs = np.asarray(b_vector, dtype=np.uint8).reshape(-1, 1)
    augmented = np.concatenate([coefficients, rhs], axis=1)
    reduced, pivots, rank = gf2_rref(augmented, coefficients.shape[1])
    for row in range(reduced.shape[0]):
        if np.all(reduced[row, : coefficients.shape[1]] == 0) and int(reduced[row, -1]) == 1:
            return OUTCOME_INCONSISTENT, None, rank, 0
    if rank < coefficients.shape[1]:
        solution_count = 2 ** (coefficients.shape[1] - rank)
        return OUTCOME_AMBIGUOUS, None, rank, solution_count
    solution = np.zeros(coefficients.shape[1], dtype=np.uint8)
    for row_index, pivot_column in enumerate(pivots):
        solution[pivot_column] = reduced[row_index, -1]
    return OUTCOME_EXACT, solution, rank, 1


def bind_codewords_bits(codewords_bits: list[np.ndarray]) -> np.ndarray:
    observation = np.zeros_like(codewords_bits[0], dtype=np.uint8)
    for codeword in codewords_bits:
        observation ^= np.asarray(codeword, dtype=np.uint8)
    return observation


def enumerate_codewords(generator_rows: np.ndarray) -> list[np.ndarray]:
    dimension = int(generator_rows.shape[0])
    rows: list[np.ndarray] = []
    for value in range(2**dimension):
        coefficients = np.array([(value >> shift) & 1 for shift in range(dimension)], dtype=np.uint8)
        rows.append((coefficients @ generator_rows) % 2)
    return rows


def codeword_index_from_bits(generator_rows: np.ndarray, codeword_bits: np.ndarray) -> int:
    all_codewords = enumerate_codewords(generator_rows)
    for index, candidate in enumerate(all_codewords):
        if np.array_equal(candidate, codeword_bits):
            return index
    raise ValueError("Codeword not found in local factor domain.")


def construct_direct_sum_subcodes(
    *,
    ambient_length: int,
    subcode_dimensions: list[int],
    seed: int,
) -> list[np.ndarray]:
    total_dimension = sum(subcode_dimensions)
    generator = random_full_rank_matrix(total_dimension, ambient_length, seed)
    subcodes: list[np.ndarray] = []
    start = 0
    for dimension in subcode_dimensions:
        subcodes.append(generator[start : start + dimension].copy())
        start += dimension
    return subcodes


def sample_factor_coefficients(dimensions: list[int], seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.integers(0, 2, size=dimension, dtype=np.uint8) for dimension in dimensions]


def materialize_factor_codewords(subcodes: list[np.ndarray], coefficients: list[np.ndarray]) -> list[np.ndarray]:
    rows: list[np.ndarray] = []
    for generator_rows, factor_coeffs in zip(subcodes, coefficients, strict=True):
        rows.append((factor_coeffs @ generator_rows) % 2)
    return rows


def subcode_contains(generator_rows: np.ndarray, codeword_bits: np.ndarray) -> bool:
    stacked = np.vstack([generator_rows, np.asarray(codeword_bits, dtype=np.uint8)])
    return gf2_rank(stacked) == gf2_rank(generator_rows)


def decode_binding(
    *,
    subcodes: list[np.ndarray],
    observation_bits: np.ndarray,
    expected_factor_dimensions: list[int] | None = None,
) -> RecoveryResult:
    decode_start = time.perf_counter()
    notes: list[str] = []
    if expected_factor_dimensions is None:
        expected_factor_dimensions = [int(generator_rows.shape[0]) for generator_rows in subcodes]

    local_ranks = [gf2_rank(generator_rows) for generator_rows in subcodes]
    declared_ranks = [int(generator_rows.shape[0]) for generator_rows in subcodes]
    if any(actual_rank < declared_rank for actual_rank, declared_rank in zip(local_ranks, declared_ranks, strict=True)):
        return RecoveryResult(
            outcome=OUTCOME_RANK_DEFICIENT,
            predicted_coefficients=[],
            predicted_codewords_pm1=[],
            predicted_identity_indices=[],
            system_rank=sum(local_ranks),
            expected_rank=sum(declared_ranks),
            nullity=max(0, sum(declared_ranks) - sum(local_ranks)),
            number_of_solutions_if_available=None,
            rebind_matches_observation=False,
            truth_used_in_decoder=False,
            factor_mapping_deterministic=True,
            decode_time_sec=time.perf_counter() - decode_start,
            solve_time_sec=0.0,
            decoder_state_bytes=0,
            notes=["A factor generator matrix is internally rank deficient."],
        )

    stacked_basis = np.vstack(subcodes).astype(np.uint8, copy=True)
    expected_rank = sum(expected_factor_dimensions)
    stacked_rank = gf2_rank(stacked_basis)
    if stacked_rank < expected_rank:
        return RecoveryResult(
            outcome=OUTCOME_AMBIGUOUS,
            predicted_coefficients=[],
            predicted_codewords_pm1=[],
            predicted_identity_indices=[],
            system_rank=stacked_rank,
            expected_rank=expected_rank,
            nullity=max(0, expected_rank - stacked_rank),
            number_of_solutions_if_available=2 ** max(0, expected_rank - stacked_rank),
            rebind_matches_observation=False,
            truth_used_in_decoder=False,
            factor_mapping_deterministic=True,
            decode_time_sec=time.perf_counter() - decode_start,
            solve_time_sec=0.0,
            decoder_state_bytes=0,
            notes=["The union of factor subcodes is not a direct sum; recovery is not uniquely identified."],
        )

    solve_start = time.perf_counter()
    solve_outcome, solution, system_rank, solution_count = gf2_solve_unique(stacked_basis.T, observation_bits)
    solve_time_sec = time.perf_counter() - solve_start
    decoder_state_bytes = runtime_bytes(stacked_basis.T) + runtime_bytes(np.asarray(observation_bits, dtype=np.uint8))
    if solve_outcome != OUTCOME_EXACT or solution is None:
        return RecoveryResult(
            outcome=solve_outcome,
            predicted_coefficients=[],
            predicted_codewords_pm1=[],
            predicted_identity_indices=[],
            system_rank=system_rank,
            expected_rank=expected_rank,
            nullity=max(0, expected_rank - system_rank),
            number_of_solutions_if_available=solution_count,
            rebind_matches_observation=False,
            truth_used_in_decoder=False,
            factor_mapping_deterministic=True,
            decode_time_sec=time.perf_counter() - decode_start,
            solve_time_sec=solve_time_sec,
            decoder_state_bytes=decoder_state_bytes,
            notes=notes,
        )

    predicted_coefficients: list[list[int]] = []
    predicted_codewords_bits: list[np.ndarray] = []
    predicted_indices: list[int] = []
    offset = 0
    for generator_rows, dimension in zip(subcodes, expected_factor_dimensions, strict=True):
        coefficients = solution[offset : offset + dimension]
        offset += dimension
        codeword_bits = (coefficients @ generator_rows) % 2
        predicted_coefficients.append(coefficients.astype(int).tolist())
        predicted_codewords_bits.append(codeword_bits)
        predicted_indices.append(codeword_index_from_bits(generator_rows, codeword_bits))
    rebound = bind_codewords_bits(predicted_codewords_bits)
    predicted_pm1 = [bits_to_pm1(codeword_bits).astype(int).tolist() for codeword_bits in predicted_codewords_bits]
    return RecoveryResult(
        outcome=OUTCOME_EXACT,
        predicted_coefficients=predicted_coefficients,
        predicted_codewords_pm1=predicted_pm1,
        predicted_identity_indices=predicted_indices,
        system_rank=system_rank,
        expected_rank=expected_rank,
        nullity=0,
        number_of_solutions_if_available=1,
        rebind_matches_observation=bool(np.array_equal(rebound, observation_bits)),
        truth_used_in_decoder=False,
        factor_mapping_deterministic=True,
        decode_time_sec=time.perf_counter() - decode_start,
        solve_time_sec=solve_time_sec,
        decoder_state_bytes=decoder_state_bytes,
        notes=notes,
    )


def collision_count(subcodes: list[np.ndarray]) -> int:
    tuple_to_observation: dict[tuple[int, ...], tuple[int, ...]] = {}
    collisions = 0
    all_domains = [enumerate_codewords(generator_rows) for generator_rows in subcodes]
    def walk(factor_index: int, chosen: list[np.ndarray], indices: list[int]) -> None:
        nonlocal collisions
        if factor_index == len(subcodes):
            observation = tuple(bind_codewords_bits(chosen).astype(int).tolist())
            if observation in tuple_to_observation and tuple_to_observation[observation] != tuple(indices):
                collisions += 1
            else:
                tuple_to_observation[observation] = tuple(indices)
            return
        for local_index, codeword in enumerate(all_domains[factor_index]):
            chosen.append(codeword)
            indices.append(local_index)
            walk(factor_index + 1, chosen, indices)
            indices.pop()
            chosen.pop()
    walk(0, [], [])
    return collisions


def build_smoke_trials() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        {"trial_id": "smoke_f2_direct_sum", "ambient_length": 8, "dims": [2, 1], "seed": 330001, "coeff_seed": 330101},
        {"trial_id": "smoke_f3_direct_sum", "ambient_length": 12, "dims": [1, 2, 1], "seed": 330002, "coeff_seed": 330102},
    ]
    for spec in specs:
        subcodes = construct_direct_sum_subcodes(
            ambient_length=spec["ambient_length"],
            subcode_dimensions=list(spec["dims"]),
            seed=spec["seed"],
        )
        coefficients = sample_factor_coefficients(list(spec["dims"]), spec["coeff_seed"])
        codewords_bits = materialize_factor_codewords(subcodes, coefficients)
        observation_bits = bind_codewords_bits(codewords_bits)
        decoded = decode_binding(subcodes=subcodes, observation_bits=observation_bits)
        rows.append(
            {
                "trial_id": spec["trial_id"],
                "stage": "algebra_smoke",
                "ambient_length": spec["ambient_length"],
                "factor_count": len(spec["dims"]),
                "subcode_dimensions": list(spec["dims"]),
                "true_coefficients": [coeff.astype(int).tolist() for coeff in coefficients],
                "true_identity_indices": [
                    codeword_index_from_bits(generator_rows, codeword_bits)
                    for generator_rows, codeword_bits in zip(subcodes, codewords_bits, strict=True)
                ],
                "observation_pm1": bits_to_pm1(observation_bits).astype(int).tolist(),
                "recovery": decoded.to_dict(),
                "all_factors_in_declared_subcodes": all(
                    subcode_contains(generator_rows, codeword_bits)
                    for generator_rows, codeword_bits in zip(subcodes, codewords_bits, strict=True)
                ),
            }
        )
    return rows


def build_exhaustive_oracle_trials() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    unique_subcodes = construct_direct_sum_subcodes(ambient_length=7, subcode_dimensions=[1, 1], seed=330201)
    unique_domains = [enumerate_codewords(generator_rows) for generator_rows in unique_subcodes]
    for left_index, left in enumerate(unique_domains[0]):
        for right_index, right in enumerate(unique_domains[1]):
            observation = bind_codewords_bits([left, right])
            decoded = decode_binding(subcodes=unique_subcodes, observation_bits=observation)
            rows.append(
                {
                    "trial_id": f"oracle_unique_{left_index}_{right_index}",
                    "stage": "exhaustive_oracle",
                    "case": "unique_direct_sum",
                    "true_indices": [left_index, right_index],
                    "observation_pm1": bits_to_pm1(observation).astype(int).tolist(),
                    "oracle_collision_count": 0,
                    "decoder_outcome": decoded.outcome,
                    "decoder_predicted_indices": decoded.predicted_identity_indices,
                    "decoder_rebind_matches_observation": decoded.rebind_matches_observation,
                }
            )

    shared_vector = np.array([[1, 0, 1, 1]], dtype=np.uint8)
    overlapping_subcodes = [shared_vector.copy(), shared_vector.copy()]
    overlapping_domains = [enumerate_codewords(generator_rows) for generator_rows in overlapping_subcodes]
    overlap_observation = bind_codewords_bits([overlapping_domains[0][0], overlapping_domains[1][1]])
    overlap_decoded = decode_binding(subcodes=overlapping_subcodes, observation_bits=overlap_observation)
    rows.append(
        {
            "trial_id": "oracle_overlap_collision",
            "stage": "exhaustive_oracle",
            "case": "overlapping_subcodes",
            "true_indices": [0, 1],
            "observation_pm1": bits_to_pm1(overlap_observation).astype(int).tolist(),
            "oracle_collision_count": collision_count(overlapping_subcodes),
            "decoder_outcome": overlap_decoded.outcome,
            "decoder_predicted_indices": overlap_decoded.predicted_identity_indices,
            "decoder_rebind_matches_observation": overlap_decoded.rebind_matches_observation,
        }
    )
    return rows


def build_paper_reproduction_trials() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        NativeTrialSpec("paper_easy_n500_k3_f3", 331001, 500, 3, 3, 10),
        NativeTrialSpec("paper_scaling_n500_k5_f4", 331002, 500, 4, 5, 10),
        NativeTrialSpec("paper_scaling_n1000_k7_f5", 331003, 1000, 5, 7, 10),
    ]
    for spec in specs:
        for trial_offset in range(spec.trials):
            trial_seed = spec.seed + trial_offset
            subcodes = construct_direct_sum_subcodes(
                ambient_length=spec.ambient_length,
                subcode_dimensions=[spec.subcode_dimension] * spec.factor_count,
                seed=trial_seed,
            )
            coefficients = sample_factor_coefficients([spec.subcode_dimension] * spec.factor_count, trial_seed + 50_000)
            codewords_bits = materialize_factor_codewords(subcodes, coefficients)
            observation_bits = bind_codewords_bits(codewords_bits)
            decoded = decode_binding(subcodes=subcodes, observation_bits=observation_bits)
            generator_bits = spec.ambient_length * spec.subcode_dimension * spec.factor_count
            observation_bits_count = spec.ambient_length
            rows.append(
                {
                    "trial_id": f"{spec.trial_id}-run-{trial_offset}",
                    "stage": "paper_native_reproduction",
                    "spec": spec.to_dict(),
                    "trial_seed": trial_seed,
                    "true_indices": [
                        codeword_index_from_bits(generator_rows, codeword_bits)
                        for generator_rows, codeword_bits in zip(subcodes, codewords_bits, strict=True)
                    ],
                    "recovery": decoded.to_dict(),
                    "success_by_paper_rule": (
                        decoded.outcome == OUTCOME_EXACT
                        and decoded.rebind_matches_observation
                        and all(
                            subcode_contains(generator_rows, pm1_to_bits(np.array(predicted_pm1, dtype=np.int8)))
                            for generator_rows, predicted_pm1 in zip(
                                subcodes,
                                decoded.predicted_codewords_pm1,
                                strict=True,
                            )
                        )
                    ),
                    "generator_bits": generator_bits,
                    "generator_bytes": theoretical_bit_bytes(generator_bits),
                    "observation_bits": observation_bits_count,
                    "observation_bytes": theoretical_bit_bytes(observation_bits_count),
                    "decoder_state_bytes": decoded.decoder_state_bytes,
                    "materialization_time_sec": 0.0,
                    "solve_time_sec": decoded.solve_time_sec,
                    "end_to_end_time_sec": decoded.decode_time_sec,
                }
            )
    return rows


def correctness_summary(
    smoke_rows: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    paper_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, data in (
        ("algebra_smoke", smoke_rows),
        ("exhaustive_oracle", oracle_rows),
        ("paper_native_reproduction", paper_rows),
    ):
        if not data:
            continue
        exact = 0
        ambiguous = 0
        collisions = 0
        for row in data:
            outcome = row["recovery"]["outcome"] if "recovery" in row else row["decoder_outcome"]
            if outcome == OUTCOME_EXACT:
                exact += 1
            if outcome == OUTCOME_AMBIGUOUS:
                ambiguous += 1
            collisions += int(row.get("oracle_collision_count", 0) > 0)
        rows.append(
            {
                "stage": label,
                "trial_count": len(data),
                "exact_recovery_count": exact,
                "ambiguous_count": ambiguous,
                "collision_case_count": collisions,
            }
        )
    return rows


def rank_summary(smoke_rows: list[dict[str, Any]], paper_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    all_rows = smoke_rows + paper_rows
    for row in all_rows:
        recovery = row["recovery"]
        rows.append(
            {
                "trial_id": row["trial_id"],
                "stage": row["stage"],
                "system_rank": recovery["system_rank"],
                "expected_rank": recovery["expected_rank"],
                "nullity": recovery["nullity"],
                "number_of_solutions_if_available": recovery["number_of_solutions_if_available"],
                "outcome": recovery["outcome"],
            }
        )
    return rows


def scaling_summary(paper_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in paper_rows:
        grouped.setdefault(row["spec"]["trial_id"], []).append(row)
    rows: list[dict[str, Any]] = []
    for trial_id, group in grouped.items():
        exact_rate = sum(1 for row in group if row["success_by_paper_rule"]) / len(group)
        rows.append(
            {
                "trial_id": trial_id,
                "ambient_length": group[0]["spec"]["ambient_length"],
                "factor_count": group[0]["spec"]["factor_count"],
                "subcode_dimension": group[0]["spec"]["subcode_dimension"],
                "trials": len(group),
                "success_rate_by_paper_rule": exact_rate,
                "mean_solve_time_sec": statistics.fmean(row["solve_time_sec"] for row in group),
                "mean_end_to_end_time_sec": statistics.fmean(row["end_to_end_time_sec"] for row in group),
                "mean_generator_bytes": statistics.fmean(row["generator_bytes"] for row in group),
                "mean_observation_bytes": statistics.fmean(row["observation_bytes"] for row in group),
            }
        )
    return rows


def resource_summary(smoke_rows: list[dict[str, Any]], paper_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in smoke_rows:
        dims = row["subcode_dimensions"]
        generator_bits = row["ambient_length"] * sum(dims)
        rows.append(
            {
                "trial_id": row["trial_id"],
                "stage": row["stage"],
                "semantic_factor_capacity": int(np.prod([2**dimension for dimension in dims])),
                "generator_bytes": theoretical_bit_bytes(generator_bits),
                "observation_bytes": theoretical_bit_bytes(row["ambient_length"]),
                "decoder_state_bytes": row["recovery"]["decoder_state_bytes"],
                "solve_time_sec": row["recovery"]["solve_time_sec"],
                "end_to_end_time_sec": row["recovery"]["decode_time_sec"],
            }
        )
    for row in paper_rows:
        rows.append(
            {
                "trial_id": row["trial_id"],
                "stage": row["stage"],
                "semantic_factor_capacity": (2 ** row["spec"]["subcode_dimension"]) ** row["spec"]["factor_count"],
                "generator_bytes": row["generator_bytes"],
                "observation_bytes": row["observation_bytes"],
                "decoder_state_bytes": row["decoder_state_bytes"],
                "solve_time_sec": row["solve_time_sec"],
                "end_to_end_time_sec": row["end_to_end_time_sec"],
            }
        )
    return rows


def dependency_audit_payload() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "dependency_decisions": [
            {
                "component": "GF(2) arrays, rank, row-space, null-space",
                "candidate": "galois==0.4.11",
                "verdict": "ADOPT",
                "why": "Mature finite-field algebra library explicitly used in the paper experiments.",
            },
            {
                "component": "Rectangular left-solve for xB = c over GF(2)",
                "candidate": "galois built-ins only",
                "verdict": "WRAP",
                "why": "The library provides rank and row reduction, but the reproduction needs a tiny paper-local Gauss-Jordan helper for a rectangular unique-solve path.",
            },
            {
                "component": "Generic finite-field framework",
                "candidate": "custom framework",
                "verdict": "BLOCK",
                "why": "Out of scope; only paper-specific assembly and solving are authorized.",
            },
        ],
        "generic_finite_field_framework_added": False,
    }


def paper_contract_payload() -> dict[str, Any]:
    entries = [
        PaperContractEntry(
            "representation_alphabet_field",
            "Binary field F_2 represented as real {+1,-1}; Boolean 1 is encoded as real -1 and Boolean 0 as real +1.",
            "Section 'A primer on linear codes', lines 304-305; Tables 1-2.",
        ),
        PaperContractEntry(
            "hypervector_codeword_construction",
            "An [n,k]_2 linear code is represented by a generator matrix G in F_2^{k x n}; codewords are xG for x in F_2^k.",
            "Section 'A primer on linear codes', lines 340-342.",
        ),
        PaperContractEntry(
            "factor_subcode_construction",
            "Factor domains are subcodes formed from disjoint subsets of a linearly independent basis so that the global code is a direct sum/product of subcodes.",
            "Subcode discussion and example, lines 368-376.",
        ),
        PaperContractEntry(
            "binding_operation",
            "Binding for clean recovery is Boolean addition/XOR, implemented as point-wise multiplication in the +/-1 representation.",
            "Section 'A primer on linear codes', line 304; Section 'oplus-recovery', lines 580-584.",
        ),
        PaperContractEntry(
            "recovery_inputs",
            "Input is an observation c in {+1,-1}^n and linear factor codes C_1,...,C_F.",
            "Section 'oplus-recovery', lines 580-584.",
        ),
        PaperContractEntry(
            "recovery_outputs",
            "Output is one vector c_i in each factor code C_i such that c equals XOR/bind of the recovered factors.",
            "Section 'oplus-recovery', lines 580-584.",
        ),
        PaperContractEntry(
            "basis_recovery_algorithm",
            "Find a maximal linearly independent subset B' from the union of factor-code bases, arrange it as matrix B, solve xB = c over F_2, then reconstruct each factor from coefficients in B' intersect B_i.",
            "Theorem and proof in Section 'oplus-recovery', lines 594-606.",
        ),
        PaperContractEntry(
            "uniqueness_condition",
            "Unique factor recovery requires the factor subcodes to behave as a direct sum/product with trivial intersections.",
            "Remark XORuniqueness, lines 606-608; subcode product discussion lines 368-376.",
        ),
        PaperContractEntry(
            "failure_conditions",
            "Non-unique decomposition appears when factor subcodes overlap nontrivially; clean noise-free decoding does not cover noisy linear-code decoding.",
            "Remark XORuniqueness lines 606-608; decoding-with-noise caveat near end of preliminaries.",
        ),
        PaperContractEntry(
            "complexity_claim",
            "The clean XOR-recovery algorithm has complexity at most O(Delta^3 n), where Delta is the sum of factor-code dimensions.",
            "Complexity paragraph immediately after the oplus-recovery proof.",
        ),
        PaperContractEntry(
            "native_benchmark_setup",
            "The paper reports n in {500,1000,2000}, k in {3,5,7}, F in {3,4,5}, each repeated 10 times, with success defined by factor membership plus exact rebind to the observation.",
            "Experiments subsection 'oplus-recovery', lines 765-773.",
        ),
        PaperContractEntry(
            "dependency_note",
            "The experiments were implemented with standard Python libraries including galois for F_2 computations.",
            "Experiments subsection 'oplus-recovery', lines 766 and 792.",
        ),
    ]
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "paper_title": LEVEL3_3_PAPER_TITLE,
        "paper_url": LEVEL3_3_PAPER_URL,
        "contract_status": LEVEL3_3_DOC_STATUS,
        "entries": [entry.to_dict() for entry in entries],
    }


def common_u1_compatibility_payload() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "verdict": COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS,
        "mapping": {
            "F": "Number of factor subcodes C_i.",
            "M": "Native factor-domain size is 2^k_i when the full subcode is used; smaller M requires a deterministic subset of codewords rather than arbitrary independent atoms.",
            "candidate_dictionary": "A factor domain is a subcode-generated dictionary, not a free set of unrelated atomic vectors.",
            "arbitrary_atomic_identities": False,
            "code_length_dependency": "Code length n is native and independent of MAP D; fairness should match semantic payload and stored generator state, not equal D alone.",
            "generator_and_state_accounting": "Storage must include generator matrices, observation bits, and any solve-state buffers.",
            "dynamic_insertion": "Possible only by choosing new coefficient vectors or extending code construction under schema-aware constraints; arbitrary open-world insertion is not free.",
            "new_factor_concept_rebuild_required": "Potentially yes if the factor dictionary must exceed the current subcode dimension or preserve direct-sum assumptions.",
        },
        "constraints": [
            "Factor domains are constrained to linear subcodes over F_2 rather than arbitrary random atomic codebooks.",
            "Unique clean recovery depends on direct-sum/trivial-intersection assumptions across factor subcodes.",
            "The clean reproduction does not cover noise, erasure, or superposed-tuple U2 contracts.",
        ],
    }


def upstream_replacement_plan_payload() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "trigger": "A suitable audited upstream NeCo or TorchHD-compatible linear-code implementation becomes publicly available.",
        "custom_reproduction_files": [
            "src/cgrn_hsr/level3_3_neco_reproduction.py",
            "experiments/level3_3_neco_reproduction.py",
            "tests/test_level3_3_neco_reproduction.py",
        ],
        "interfaces_that_may_survive": [
            "paper_contract.json schema",
            "common_u1_compatibility.json schema",
            "typed failure taxonomy for clean algebraic reproduction",
        ],
        "required_differential_tests": [
            "Exact agreement on deterministic algebra smoke trials.",
            "Exact agreement with exhaustive tiny-oracle collision detection.",
            "Equivalent typed failures for ambiguous, rank-deficient, and inconsistent cases.",
        ],
        "deletion_plan": "Delete or replace the custom reproduction module after differential tests pass; do not keep a permanent fork without a fresh review.",
        "official_upstream_available": False,
    }


def claims_payload(*, reproduction_verdict: str, common_u1_verdict: str) -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "allowed_claims": [
            "paper contract extracted",
            "minimal clean binding recovery reproduced",
            "algebraic decoder agrees with exhaustive tiny oracle",
            "paper-native scaling approximately reproduced",
            "common-U1 compatibility assessed",
        ],
        "forbidden_claims": [
            "linear-code HDC is superior to MAP",
            "linear-code HDC is superior to BCF",
            "noise robustness",
            "production readiness",
            "universal factorization",
            "official implementation",
        ],
        "reproduction_verdict": reproduction_verdict,
        "common_u1_verdict": common_u1_verdict,
        "superiority_claim_authorized": False,
    }


def analysis_payload(
    *,
    smoke_rows: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    paper_rows: list[dict[str, Any]],
    common_u1: dict[str, Any],
) -> dict[str, Any]:
    paper_successes = sum(1 for row in paper_rows if row["success_by_paper_rule"])
    paper_trials = len(paper_rows)
    oracle_agreement = all(
        (row["decoder_outcome"] == OUTCOME_EXACT and row["decoder_predicted_indices"] == row["true_indices"])
        if row["case"] == "unique_direct_sum"
        else row["decoder_outcome"] == OUTCOME_AMBIGUOUS
        for row in oracle_rows
    )
    if LEVEL3_3_DOC_STATUS != "UNAMBIGUOUS_PAPER_CONTRACT":
        reproduction_verdict = "BLOCKED_BY_AMBIGUITY"
    elif not all(row["recovery"]["outcome"] == OUTCOME_EXACT for row in smoke_rows):
        reproduction_verdict = "IMPLEMENTATION_FAILURE"
    elif not oracle_agreement:
        reproduction_verdict = "IMPLEMENTATION_FAILURE"
    elif paper_trials == 0:
        reproduction_verdict = "PARTIAL_REPRODUCTION"
    elif paper_successes == paper_trials:
        reproduction_verdict = "REPRODUCED"
    else:
        reproduction_verdict = "PARTIAL_REPRODUCTION"
    return {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_3_CHECKPOINT_COMMIT,
        "paper_title": LEVEL3_3_PAPER_TITLE,
        "paper_url": LEVEL3_3_PAPER_URL,
        "official_upstream_available": False,
        "author_correspondence_status": {
            "official_public_neco_implementation_available": False,
            "author_reported_minimal_algorithm": "little beyond Gaussian elimination over F2",
            "independent_reproduction_expected": True,
            "histogram_recovery_upstream_status": "separate workstream, not implemented here",
            "this_repo_is_not_official_implementation": True,
            "replacement_when_upstream_appears": True,
        },
        "algebra_smoke_passed": all(row["recovery"]["outcome"] == OUTCOME_EXACT for row in smoke_rows),
        "exhaustive_oracle_exact_agreement": oracle_agreement,
        "paper_native_successes": paper_successes,
        "paper_native_trials": paper_trials,
        "common_u1_verdict": common_u1["verdict"],
        "reproduction_verdict": reproduction_verdict,
        "noise_implemented": False,
        "u2_implemented": False,
        "histogram_recovery_implemented": False,
        "context_or_controller_used": False,
    }


def build_docs(
    *,
    contract: dict[str, Any],
    dependency_audit: dict[str, Any],
    analysis: dict[str, Any],
    common_u1: dict[str, Any],
) -> dict[str, str]:
    extraction_lines = [
        f"# Level 3.3 NeCo Contract Extraction",
        "",
        f"- Paper: [{LEVEL3_3_PAPER_TITLE}]({LEVEL3_3_PAPER_URL})",
        f"- Status: `{contract['contract_status']}`",
        f"- Checkpoint: `{LEVEL3_3_CHECKPOINT_COMMIT}`",
        "",
        "## Author status",
        "",
        "- Official/public NeCo implementation: unavailable in the audited repo context.",
        "- Author correspondence summary: the relevant clean algebra is expected to require little beyond Gaussian elimination over F2.",
        "- This repository contains an independent paper-specific reproduction, not an official implementation.",
        "- Replacement rule: delete or replace the custom reproduction when a suitable audited upstream appears.",
        "",
        "## Extracted contract",
        "",
    ]
    for entry in contract["entries"]:
        extraction_lines.append(f"- `{entry['key']}`: {entry['value']} ({entry['source_reference']})")

    reproduction_lines = [
        "# Level 3.3 Linear-Code Reproduction",
        "",
        f"- Reproduction verdict: `{analysis['reproduction_verdict']}`",
        f"- Common U1 verdict: `{common_u1['verdict']}`",
        "",
        "## Dependency path",
        "",
    ]
    for decision in dependency_audit["dependency_decisions"]:
        reproduction_lines.append(
            f"- `{decision['component']}` -> `{decision['verdict']}` via `{decision['candidate']}`: {decision['why']}"
        )
    reproduction_lines.extend(
        [
            "",
            "## Custom implementation boundary",
            "",
            "- Allowed custom code: paper-specific subcode construction, paper-specific recovery-system assembly, local GF(2) unique-solve helper, and reproduction harness.",
            "- Forbidden custom code: generic finite-field framework, generic ECC framework, noise decoder, histogram/U2 logic, or production integration.",
            "",
            "## Claim boundary",
            "",
            "- Allowed: contract extraction, minimal clean recovery reproduction, exhaustive tiny-oracle agreement, paper-native approximate reproduction, and U1 compatibility assessment.",
            "- Forbidden: superiority over MAP/BCF, noise claims, production readiness, universal factorization, or official-implementation claims.",
        ]
    )
    return {
        "LEVEL3_3_NECO_CONTRACT_EXTRACTION.md": "\n".join(extraction_lines) + "\n",
        "LEVEL3_3_LINEAR_CODE_REPRODUCTION.md": "\n".join(reproduction_lines) + "\n",
    }


def run_level3_3(root: Path) -> dict[str, Any]:
    docs_dir = root / "docs"
    results_dir = root / "results" / "level3_3"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    contract = paper_contract_payload()
    dependency_audit = dependency_audit_payload()
    smoke_rows = build_smoke_trials()
    oracle_rows = build_exhaustive_oracle_trials()
    paper_rows = build_paper_reproduction_trials()
    common_u1 = common_u1_compatibility_payload()
    analysis = analysis_payload(
        smoke_rows=smoke_rows,
        oracle_rows=oracle_rows,
        paper_rows=paper_rows,
        common_u1=common_u1,
    )
    claims = claims_payload(
        reproduction_verdict=analysis["reproduction_verdict"],
        common_u1_verdict=common_u1["verdict"],
    )
    replacement_plan = upstream_replacement_plan_payload()

    docs = build_docs(
        contract=contract,
        dependency_audit=dependency_audit,
        analysis=analysis,
        common_u1=common_u1,
    )
    for name, content in docs.items():
        (docs_dir / name).write_text(content, encoding="utf-8")

    environment = {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL3_3_CHECKPOINT_COMMIT,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "galois_version": galois.__version__,
        "numpy_version": np.__version__,
        "paper_source_path": str(LEVEL3_3_SOURCE_PATH),
        "paper_source_available": LEVEL3_3_SOURCE_PATH.exists(),
        "clean_only_scope": True,
    }
    frozen_protocol = {
        "schema_version": LEVEL3_3_SCHEMA_VERSION,
        "task_contract": LEVEL3_3_TASK_CONTRACT,
        "stages": {
            "A": "deterministic algebra smoke",
            "B": "exhaustive tiny oracle",
            "C": "paper-native clean reproduction",
        },
        "noise_disabled": True,
        "u2_disabled": True,
        "context_disabled": True,
        "official_upstream_missing": True,
    }
    correctness = correctness_summary(smoke_rows, oracle_rows, paper_rows)
    ranks = rank_summary(smoke_rows, paper_rows)
    scaling = scaling_summary(paper_rows)
    resources = resource_summary(smoke_rows, paper_rows)

    write_json(results_dir / "environment.json", environment)
    write_json(results_dir / "dependency_audit.json", dependency_audit)
    write_json(results_dir / "paper_contract.json", contract)
    write_json(results_dir / "frozen_protocol.json", frozen_protocol)
    write_jsonl(results_dir / "native_smoke_trials.jsonl", smoke_rows)
    write_jsonl(results_dir / "exhaustive_oracle_trials.jsonl", oracle_rows)
    write_jsonl(results_dir / "paper_reproduction_trials.jsonl", paper_rows)
    write_csv(results_dir / "correctness_summary.csv", correctness)
    write_csv(results_dir / "rank_summary.csv", ranks)
    write_csv(results_dir / "scaling_summary.csv", scaling)
    write_csv(results_dir / "resource_summary.csv", resources)
    write_json(results_dir / "common_u1_compatibility.json", common_u1)
    write_json(results_dir / "upstream_replacement_plan.json", replacement_plan)
    write_json(results_dir / "claims.json", claims)
    write_json(results_dir / "analysis.json", analysis)

    return {
        "environment": environment,
        "dependency_audit": dependency_audit,
        "paper_contract": contract,
        "native_smoke_trials": smoke_rows,
        "exhaustive_oracle_trials": oracle_rows,
        "paper_reproduction_trials": paper_rows,
        "correctness_summary": correctness,
        "rank_summary": ranks,
        "scaling_summary": scaling,
        "resource_summary": resources,
        "common_u1_compatibility": common_u1,
        "upstream_replacement_plan": replacement_plan,
        "claims": claims,
        "analysis": analysis,
    }
