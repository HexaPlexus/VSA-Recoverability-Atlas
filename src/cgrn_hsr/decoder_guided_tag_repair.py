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

import torch
import torch.nn.functional as F
import torchhd

from .baseline import (
    BaselineConfig,
    bind_sequence,
    build_initial_estimates,
    decode_top_candidates,
    factors_from_indices,
    generate_domains,
    make_generator,
)
from .exact_capsule_contract_closure import LEVEL35_V4_SHA256
from .first_order_trace_coactivation import stage_seed_set as first_order_stage_seed_set
from .lazy_trace_addressing_stage_a import stage_a_seed_set
from .lazy_trace_addressing_stage_a1 import stage_a1_seed_set
from .lazy_trace_addressing_stage_a2a import stage_a2a_seed_set
from .level3_2_confirmation import prior_level3_1_seed_set
from .level3_2b_map_budget_robustness import level3_2_seed_set, level3_2b_seed_set
from .level3_4_algebraic_baselines import level3_4_seed_set
from .level3_5b_native_noise_frontiers import prior_seed_set as level35_prior_seed_set
from .release_artifacts import canonical_sha256

SCHEMA_VERSION = "decoder-guided-tag-repair-v0.1-dev"
TASK_NAME = "Decoder-Guided Minimal Representation Repair v0.1"
RESULTS_NAMESPACE = "decoder_guided_tag_repair_v0_1"
STARTING_COMMIT = "c6a24d7e16eef366bf03d78db306266a00c05e0c"
U1_TASK_CONTRACT = "U1_blind_single_product_factorization"

ARM_BASE_BINARY = "A_BASE_BINARY"
ARM_RANDOM_TAGS = "B_RANDOM_TAGS"
ARM_SHUFFLED_CONFLICT_TAGS = "C_SHUFFLED_CONFLICT_TAGS"
ARM_RANDOM_PATCH_SEARCH = "D_RANDOM_PATCH_SEARCH"
ARM_CONFLICT_GUIDED_TAGS = "E_CONFLICT_GUIDED_TAGS"
ARM_EQUAL_BIT_EXTRA_DIMENSIONS = "F_EQUAL_BIT_EXTRA_DIMENSIONS"
ALLOWED_ARMS = (
    ARM_BASE_BINARY,
    ARM_RANDOM_TAGS,
    ARM_SHUFFLED_CONFLICT_TAGS,
    ARM_RANDOM_PATCH_SEARCH,
    ARM_CONFLICT_GUIDED_TAGS,
    ARM_EQUAL_BIT_EXTRA_DIMENSIONS,
)

OUTCOME_STANDARD_CERTIFIED = "STANDARD_CERTIFIED"
OUTCOME_TAG_REPAIRED_CERTIFIED = "TAG_REPAIRED_CERTIFIED"
OUTCOME_REPAIR_IMPROVED_NOT_CERTIFIED = "REPAIR_IMPROVED_BUT_NOT_CERTIFIED"
OUTCOME_NO_STABLE_CONFLICTS = "NO_STABLE_CONFLICTS"
OUTCOME_TAG_BUDGET_EXHAUSTED = "TAG_BUDGET_EXHAUSTED"
OUTCOME_FALLBACK_REQUIRED = "FALLBACK_REQUIRED"

SPLIT_DISCOVERY = "CONFLICT_DISCOVERY"
SPLIT_CERTIFICATION = "REPAIR_CERTIFICATION"
SPLIT_VALIDATION = "DEVELOPMENT_VALIDATION"
SPLIT_FINAL = "FINAL_DEVELOPMENT_EVALUATION"
ALLOWED_SPLITS = (SPLIT_DISCOVERY, SPLIT_CERTIFICATION, SPLIT_VALIDATION, SPLIT_FINAL)

WORKLOAD_TARGET = "target_present"
WORKLOAD_OLD_ONLY = "old_only"
WORKLOAD_HARD = "previous_hard_case"

MARKER_NONE = 0
MARKER_NEG_PRESENT = 1
MARKER_POS_PRESENT = 2
MARKER_BOTH_PRESENT = 3

REPAIR_LADDER = (0, 8, 16, 32)
TARGETS_PER_FACTOR = 1
DISCOVERY_TRIALS = 6
CERTIFICATION_TRIALS = 6
VALIDATION_TRIALS = 6
FINAL_TRIALS = 8
OLD_ONLY_TRIALS = 6
RANDOM_PATCH_CANDIDATES = 1
MAX_ITERATIONS = 12
STABLE_PATIENCE = 3
FACTOR_COUNT = 3
MARKER_HEADER_BITS = 16
MIN_STABLE_CONFLICT_FREQUENCY = 2
MINIMUM_COVERAGE = 0.75
CERT_EXACT_THRESHOLD = 0.90
CERT_RISK_THRESHOLD = 0.05
PRIMARY_SILENT_ERROR_GATE = 0.0
EXECUTE_LONG_RUN = False
CORRUPTION_CONTRACT = "clean_only"

DISCOVERY_SEED_OFFSET = 110_000
CERT_SEED_OFFSET = 210_000
VALIDATION_SEED_OFFSET = 310_000
FINAL_SEED_OFFSET = 410_000
SHUFFLE_SEED_OFFSET = 510_000
PATCH_SEED_OFFSET = 610_000

PROGRESS_PREFIX = "[decoder-guided-tag]"


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    dimensions: int
    domain_size: int
    codebook_seed_start: int
    codebook_seed_count: int
    target_atom_count: int
    execute_in_stage: bool
    stage_role: str

    def seed_range(self) -> dict[str, int]:
        return {"start": self.codebook_seed_start, "count": self.codebook_seed_count}


@dataclass(frozen=True)
class MarkerOverlay:
    coordinates: tuple[int, ...]


@dataclass(frozen=True)
class ConflictCoordinate:
    atom_id: str
    factor_domain: int
    coordinate: int
    true_value: int
    conflict_frequency: int
    mean_negative_margin: float
    wrong_competitor_count: int
    distinct_partner_count: int
    distinct_decoder_seed_count: int
    stability_score: float


@dataclass(frozen=True)
class TaggedDecodeMetrics:
    predicted_indices: tuple[int, ...]
    top2_indices: tuple[int, ...]
    exact_recovery: bool
    verified_reconstruction: bool
    stable_prediction: bool
    per_factor_recovery: tuple[bool, ...]
    min_margin: float
    mean_margin: float
    iterations: int
    decode_latency_sec: float
    factor_estimates: torch.Tensor
    semantic_scores: torch.Tensor
    combined_scores: torch.Tensor


@dataclass(frozen=True)
class EvaluationSummary:
    split_name: str
    trials: int
    exact_recovery_rate: float
    verified_reconstruction_rate: float
    accepted_coverage: float
    conditional_risk: float
    silent_wrong_acceptance_rate: float
    mean_min_margin: float
    mean_iterations: float
    mean_latency_sec: float


@dataclass(frozen=True)
class ArmBudgetResult:
    arm_id: str
    budget: int
    certified: bool
    evaluation: EvaluationSummary
    validation: EvaluationSummary
    final_eval: EvaluationSummary
    old_only: EvaluationSummary
    physical_bits: int
    semantic_bits: int
    marker_overlay_bits: int
    composite_marker_bits: int
    certification_calls: int
    patch_evaluations: int
    typed_outcome: str
    selected_coordinates: tuple[int, ...]
    expanded_dimensions: int | None = None


CELLS: tuple[CellSpec, ...] = (
    CellSpec(
        cell_id="smoke_d512_m10",
        dimensions=512,
        domain_size=10,
        codebook_seed_start=962_510_100,
        codebook_seed_count=1,
        target_atom_count=1,
        execute_in_stage=True,
        stage_role="sanity",
    ),
    CellSpec(
        cell_id="transition_d1024_m22",
        dimensions=1024,
        domain_size=22,
        codebook_seed_start=962_522_100,
        codebook_seed_count=1,
        target_atom_count=1,
        execute_in_stage=True,
        stage_role="paired_smoke",
    ),
    CellSpec(
        cell_id="transition_d1024_m31",
        dimensions=1024,
        domain_size=31,
        codebook_seed_start=962_531_100,
        codebook_seed_count=1,
        target_atom_count=1,
        execute_in_stage=True,
        stage_role="paired_smoke",
    ),
)


def canonical_json_hash(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, indent=None, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    return canonical_sha256(path).upper()


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
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def stage_seed_set() -> set[int]:
    values: set[int] = set()
    for cell in CELLS:
        for seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count):
            values.add(seed)
            values.add(seed + DISCOVERY_SEED_OFFSET)
            values.add(seed + CERT_SEED_OFFSET)
            values.add(seed + VALIDATION_SEED_OFFSET)
            values.add(seed + FINAL_SEED_OFFSET)
            values.add(seed + SHUFFLE_SEED_OFFSET)
            values.add(seed + PATCH_SEED_OFFSET)
    return values


def prior_known_seed_set(repo_root: Path) -> set[int]:
    prior = set(level35_prior_seed_set())
    prior.update(prior_level3_1_seed_set())
    prior.update(level3_2_seed_set())
    prior.update(level3_2b_seed_set())
    prior.update(level3_4_seed_set())
    prior.update(stage_a_seed_set())
    prior.update(stage_a1_seed_set())
    prior.update(stage_a2a_seed_set())
    prior.update(first_order_stage_seed_set())
    for path in (
        repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json",
    ):
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


def transition_evidence() -> list[dict[str, Any]]:
    return [
        {
            "source": "docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md",
            "cell_id": "transition_d1024_m22",
            "evidence": "existing MAP clean transition region",
        },
        {
            "source": "docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md",
            "cell_id": "transition_d1024_m31",
            "evidence": "existing MAP hard clean transition region",
        },
    ]


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "PROTOTYPE",
        "status": ["PROTOTYPE", "DEVELOPMENT_ONLY", "NEW_HYPOTHESIS", "NO_PRODUCTION_CLAIM"],
        "previous_blocked_line": {
            "commit": STARTING_COMMIT,
            "scientific_verdict": "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED",
            "kill_gate": "BLOCK_DECODER_CERTIFICATION_LINE",
        },
        "anti_nih_findings": [
            {
                "family": "q-ary / erasure symbols",
                "verdict": "ADAPT",
                "coverage": 0.4,
                "notes": "Tagged four-symbol repair overlaps with enriched alphabets and erasure-style side information, but this stage keeps semantic MAP bits unchanged and uses tags only as sparse recovery evidence.",
            },
            {
                "family": "error-correcting output codes / reliability weighting",
                "verdict": "ADAPT",
                "coverage": 0.5,
                "notes": "The causal idea resembles decoder-informed selective redundancy, but no existing repo primitive already performs conflict-localized sparse repair on open-world factor domains.",
            },
            {
                "family": "sparse codes / sparse block codes / spreading codes",
                "verdict": "COMPARE",
                "coverage": 0.3,
                "notes": "These are the honest redundancy controls; Arm F and random-tag controls are included so the stage cannot claim victory from generic extra bits.",
            },
            {
                "family": "Bloom-filter-like membership sketches / confidence masks",
                "verdict": "COMPARE",
                "coverage": 0.3,
                "notes": "Marker overlays act like sparse confidence hints, not canonical identity or pointer payloads.",
            },
            {
                "family": "existing MAP/TorchHD resonator harness",
                "verdict": "WRAP",
                "coverage": 1.0,
                "notes": "Reuse the native semantic decoder and only add a thin marker-aware cleanup wrapper, conflict attribution, and patch protocol.",
            },
        ],
        "why_not_scratch": [
            "A new resonator, new VSA algebra, or learned encoder would answer a different question than the narrow causal repair hypothesis.",
            "The repository already contains deterministic MAP domain generation, resonator iteration budgets, and exact reconstruction checks.",
            "This stage only needs a versioned recovery view, conflict accounting, sparse tag placement, and matched controls.",
        ],
        "level35_frozen_artifact_hash": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json"),
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    protocol = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "starting_commit": STARTING_COMMIT,
        "status": ["PROTOTYPE", "DEVELOPMENT_ONLY", "NEW_HYPOTHESIS", "NO_PRODUCTION_CLAIM"],
        "long_run_authorized": EXECUTE_LONG_RUN,
        "heldout_execution_allowed": False,
        "scope_limit_reason": "Level 3.5b confirmatory closure is not complete; only audit, protocol, unit tests, and tiny smoke are lawful.",
        "representation_contract": {
            "semantic_alphabet": ["-1", "+1"],
            "tagged_alphabet": ["NORMAL_NEG", "NORMAL_POS", "TAGGED_NEG", "TAGGED_POS"],
            "semantic_projection_preserved": True,
            "marker_merge_states": ["NONE", "NEG_PRESENT", "POS_PRESENT", "BOTH_PRESENT"],
            "marker_score_formula": "(D * semantic_score + effective_marker_bits * marker_score) / (D + effective_marker_bits)",
            "effective_marker_bits": "number_of_tags(candidate)",
        },
        "substrate": {
            "family": "MAP",
            "task_contract": U1_TASK_CONTRACT,
            "factor_count": FACTOR_COUNT,
            "decoder": "TorchHD resonator + thin marker-aware cleanup wrapper",
            "max_iterations": MAX_ITERATIONS,
            "stable_patience": STABLE_PATIENCE,
            "corruption_contract": CORRUPTION_CONTRACT,
        },
        "cells": [asdict(cell) | {"seed_range": cell.seed_range()} for cell in CELLS],
        "repair_ladder": list(REPAIR_LADDER),
        "arms": list(ALLOWED_ARMS),
        "split_counts": {
            SPLIT_DISCOVERY: DISCOVERY_TRIALS,
            SPLIT_CERTIFICATION: CERTIFICATION_TRIALS,
            SPLIT_VALIDATION: VALIDATION_TRIALS,
            SPLIT_FINAL: FINAL_TRIALS,
            WORKLOAD_OLD_ONLY: OLD_ONLY_TRIALS,
        },
        "strict_certificate": {
            "verified_exact_recovery_min": CERT_EXACT_THRESHOLD,
            "conditional_risk_max": CERT_RISK_THRESHOLD,
            "silent_wrong_acceptance_max": PRIMARY_SILENT_ERROR_GATE,
            "accepted_coverage_min": MINIMUM_COVERAGE,
        },
        "seed_offsets": {
            "discovery": DISCOVERY_SEED_OFFSET,
            "certification": CERT_SEED_OFFSET,
            "validation": VALIDATION_SEED_OFFSET,
            "final": FINAL_SEED_OFFSET,
            "shuffle": SHUFFLE_SEED_OFFSET,
            "patch": PATCH_SEED_OFFSET,
        },
        "allowed_claims": [
            "bit-exact marker recovery view exists",
            "conflict-guided tag placement can be compared causally against shuffled and random controls",
            "equal-bit extra-dimension control is included",
        ],
        "forbidden_claims": [
            "new decoder",
            "new VSA algebra",
            "production readiness",
            "noisy frontier",
            "held-out confirmation",
            "new coding theory",
        ],
        "transition_evidence": transition_evidence(),
        "seed_fresh": seeds_are_fresh(repo_root),
        "level35_frozen_artifacts_unchanged": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256,
    }
    protocol["protocol_hash"] = canonical_json_hash(protocol)
    return protocol


def marker_overlay_bits(dimensions: int, tag_count: int) -> int:
    if tag_count <= 0:
        return 0
    position_bits = math.ceil(math.log2(dimensions))
    return MARKER_HEADER_BITS + tag_count * (position_bits + 1)


def extra_dimensions_for_budget(dimensions: int, tag_budget: int) -> int:
    return int(math.ceil(marker_overlay_bits(dimensions, tag_budget)))


def semantic_projection(vector: torch.Tensor, overlay: MarkerOverlay) -> torch.Tensor:
    return vector


def initial_codebook(dimensions: int, domain_size: int, seed: int) -> torch.Tensor:
    config = BaselineConfig(
        dimensions=dimensions,
        num_factors=FACTOR_COUNT,
        domain_size=domain_size,
        structured_distractor_count=0,
        max_iterations=MAX_ITERATIONS,
        stable_patience=STABLE_PATIENCE,
    )
    return generate_domains(config, make_generator(seed))


def cosine_similarity_matrix(estimates: torch.Tensor, domains: torch.Tensor) -> torch.Tensor:
    expanded_estimates = estimates.unsqueeze(-2).expand_as(domains)
    return F.cosine_similarity(expanded_estimates, domains, dim=-1)


def empty_overlays(domains: torch.Tensor) -> list[list[MarkerOverlay]]:
    return [[MarkerOverlay(tuple()) for _ in range(domains.size(1))] for _ in range(domains.size(0))]


def clone_overlays(overlays: list[list[MarkerOverlay]]) -> list[list[MarkerOverlay]]:
    return [[MarkerOverlay(tuple(item.coordinates)) for item in factor] for factor in overlays]


def tagged_values(vector: torch.Tensor, overlay: MarkerOverlay) -> tuple[int, ...]:
    values: list[int] = []
    for coordinate in overlay.coordinates:
        values.append(int(vector[coordinate].item()))
    return tuple(values)


def merge_marker_states(
    domains: torch.Tensor,
    overlays: list[list[MarkerOverlay]],
    target_indices: tuple[int, ...],
) -> torch.Tensor:
    neg_present = torch.zeros(domains.size(-1), dtype=torch.bool)
    pos_present = torch.zeros(domains.size(-1), dtype=torch.bool)
    for factor_index, atom_index in enumerate(target_indices):
        vector = domains[factor_index, atom_index]
        overlay = overlays[factor_index][atom_index]
        for coordinate in overlay.coordinates:
            if int(vector[coordinate].item()) > 0:
                pos_present[coordinate] = True
            else:
                neg_present[coordinate] = True
    state = torch.full((domains.size(-1),), MARKER_NONE, dtype=torch.int64)
    state[neg_present] = MARKER_NEG_PRESENT
    state[pos_present] = torch.where(
        neg_present[pos_present],
        torch.full_like(state[pos_present], MARKER_BOTH_PRESENT),
        torch.full_like(state[pos_present], MARKER_POS_PRESENT),
    )
    state[neg_present & pos_present] = MARKER_BOTH_PRESENT
    return state


def marker_score(vector: torch.Tensor, overlay: MarkerOverlay, marker_state: torch.Tensor) -> float:
    if not overlay.coordinates:
        return 0.0
    total = 0.0
    for coordinate in overlay.coordinates:
        state = int(marker_state[coordinate].item())
        sign = 1 if int(vector[coordinate].item()) > 0 else -1
        if sign > 0 and state == MARKER_POS_PRESENT:
            total += 1.0
        elif sign < 0 and state == MARKER_NEG_PRESENT:
            total += 1.0
        elif sign > 0 and state == MARKER_NEG_PRESENT:
            total -= 1.0
        elif sign < 0 and state == MARKER_POS_PRESENT:
            total -= 1.0
    return total / max(1, len(overlay.coordinates))


def combined_similarity_scores(
    semantic_scores: torch.Tensor,
    domain_vectors: torch.Tensor,
    factor_overlays: list[MarkerOverlay],
    marker_state: torch.Tensor,
) -> torch.Tensor:
    combined = semantic_scores.clone()
    for atom_index in range(semantic_scores.numel()):
        overlay = factor_overlays[atom_index]
        marker_bits = len(overlay.coordinates)
        if marker_bits <= 0:
            continue
        candidate_marker_score = marker_score(domain_vectors[atom_index], overlay, marker_state)
        combined[atom_index] = (
            domain_vectors.size(-1) * semantic_scores[atom_index] + marker_bits * candidate_marker_score
        ) / (domain_vectors.size(-1) + marker_bits)
    return combined


def decode_tagged_tuple(
    domains: torch.Tensor,
    overlays: list[list[MarkerOverlay]],
    target_indices: tuple[int, ...],
) -> TaggedDecodeMetrics:
    semantic_observation = bind_sequence(factors_from_indices(domains, torch.tensor(target_indices, dtype=torch.long)))
    marker_state = merge_marker_states(domains, overlays, target_indices)
    current_estimates = build_initial_estimates(domains)
    previous_prediction: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    decoded: dict[str, torch.Tensor] | None = None
    semantic_scores: torch.Tensor | None = None
    combined_scores: torch.Tensor | None = None
    start = time.perf_counter()
    for iteration in range(1, MAX_ITERATIONS + 1):
        current_estimates = torchhd.resonator(semantic_observation, current_estimates, domains)
        semantic_scores = cosine_similarity_matrix(current_estimates, domains)
        combined_scores = torch.stack(
            [
                combined_similarity_scores(
                    semantic_scores[factor_index],
                    domains[factor_index],
                    overlays[factor_index],
                    marker_state,
                )
                for factor_index in range(domains.size(0))
            ],
            dim=0,
        )
        decoded = decode_top_candidates(combined_scores)
        prediction = decoded["top1_indices"]
        if previous_prediction is not None and torch.equal(prediction, previous_prediction):
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous_prediction = prediction.clone()
        if stable_iterations >= STABLE_PATIENCE:
            stable_prediction = True
            break
    latency = time.perf_counter() - start
    if decoded is None or semantic_scores is None or combined_scores is None:
        raise RuntimeError("Tagged decode produced no output.")
    predicted = decoded["top1_indices"].detach().cpu().to(dtype=torch.long)
    reconstruction = bind_sequence(factors_from_indices(domains, predicted))
    exact = tuple(int(value) for value in predicted.tolist()) == tuple(target_indices)
    verified = bool(torch.equal(reconstruction, semantic_observation.cpu()))
    margins = [float(value) for value in decoded["margins"].tolist()]
    return TaggedDecodeMetrics(
        predicted_indices=tuple(int(value) for value in predicted.tolist()),
        top2_indices=tuple(int(value) for value in decoded["top2_indices"].tolist()),
        exact_recovery=exact,
        verified_reconstruction=verified,
        stable_prediction=stable_prediction,
        per_factor_recovery=tuple(
            bool(int(predicted[index].item()) == target_indices[index]) for index in range(len(target_indices))
        ),
        min_margin=min(margins),
        mean_margin=float(statistics.fmean(margins)),
        iterations=iteration,
        decode_latency_sec=latency,
        factor_estimates=current_estimates.detach().cpu().clone(),
        semantic_scores=semantic_scores.detach().cpu().clone(),
        combined_scores=combined_scores.detach().cpu().clone(),
    )


def random_tuple(seed: int, factor_count: int, domain_size: int) -> tuple[int, ...]:
    generator = make_generator(seed)
    return tuple(int(torch.randint(0, domain_size, (1,), generator=generator).item()) for _ in range(factor_count))


def tuples_for_target(
    seed: int,
    count: int,
    domain_size: int,
    factor_index: int,
    atom_index: int,
) -> list[tuple[int, ...]]:
    rows: list[tuple[int, ...]] = []
    for row_index in range(count):
        values = list(random_tuple(seed + row_index, FACTOR_COUNT, domain_size))
        values[factor_index] = atom_index
        rows.append(tuple(values))
    return rows


def old_only_tuples(
    seed: int,
    count: int,
    domain_size: int,
    factor_index: int,
    atom_index: int,
) -> list[tuple[int, ...]]:
    rows: list[tuple[int, ...]] = []
    generator = make_generator(seed)
    for _ in range(count):
        values: list[int] = []
        for current_factor in range(FACTOR_COUNT):
            if current_factor == factor_index:
                available = [index for index in range(domain_size) if index != atom_index]
                choice = available[int(torch.randint(0, len(available), (1,), generator=generator).item())]
            else:
                choice = int(torch.randint(0, domain_size, (1,), generator=generator).item())
            values.append(choice)
        rows.append(tuple(values))
    return rows


def summarize_rows(split_name: str, rows: list[dict[str, Any]]) -> EvaluationSummary:
    accepted_rows = [row for row in rows if row["accepted"]]
    exact_rows = [row for row in rows if row["exact_recovery"]]
    return EvaluationSummary(
        split_name=split_name,
        trials=len(rows),
        exact_recovery_rate=len(exact_rows) / max(1, len(rows)),
        verified_reconstruction_rate=sum(1 for row in rows if row["verified_reconstruction"]) / max(1, len(rows)),
        accepted_coverage=len(accepted_rows) / max(1, len(rows)),
        conditional_risk=(
            sum(1 for row in accepted_rows if not row["exact_recovery"]) / len(accepted_rows)
            if accepted_rows
            else 0.0
        ),
        silent_wrong_acceptance_rate=sum(1 for row in rows if row["silent_wrong"]) / max(1, len(rows)),
        mean_min_margin=float(statistics.fmean(row["min_margin"] for row in rows)) if rows else 0.0,
        mean_iterations=float(statistics.fmean(row["iterations"] for row in rows)) if rows else 0.0,
        mean_latency_sec=float(statistics.fmean(row["decode_latency_sec"] for row in rows)) if rows else 0.0,
    )


def evaluate_tuples(
    domains: torch.Tensor,
    overlays: list[list[MarkerOverlay]],
    tuples: list[tuple[int, ...]],
    split_name: str,
) -> tuple[list[dict[str, Any]], EvaluationSummary]:
    rows: list[dict[str, Any]] = []
    for target_indices in tuples:
        decode = decode_tagged_tuple(domains, overlays, target_indices)
        accepted = decode.stable_prediction
        rows.append(
            {
                "split_name": split_name,
                "target_indices": list(target_indices),
                "predicted_indices": list(decode.predicted_indices),
                "exact_recovery": decode.exact_recovery,
                "verified_reconstruction": decode.verified_reconstruction,
                "stable_prediction": decode.stable_prediction,
                "silent_wrong": accepted and not decode.exact_recovery,
                "min_margin": decode.min_margin,
                "mean_margin": decode.mean_margin,
                "iterations": decode.iterations,
                "decode_latency_sec": decode.decode_latency_sec,
                "accepted": accepted,
            }
        )
    return rows, summarize_rows(split_name, rows)


def strict_certificate(summary: EvaluationSummary) -> bool:
    return (
        summary.verified_reconstruction_rate >= CERT_EXACT_THRESHOLD
        and summary.conditional_risk <= CERT_RISK_THRESHOLD
        and summary.silent_wrong_acceptance_rate <= PRIMARY_SILENT_ERROR_GATE
        and summary.accepted_coverage >= MINIMUM_COVERAGE
    )


def top_wrong_competitor(scores: torch.Tensor, true_index: int) -> int:
    ordered = torch.argsort(scores, descending=True)
    for item in ordered.tolist():
        if int(item) != true_index:
            return int(item)
    return true_index


def stable_conflict_report(
    cell: CellSpec,
    codebook_seed: int,
    domains: torch.Tensor,
    factor_index: int,
    atom_index: int,
    discovery_tuples_rows: list[tuple[int, ...]],
    overlays: list[list[MarkerOverlay]],
) -> tuple[list[ConflictCoordinate], list[dict[str, Any]]]:
    conflict_map: dict[int, dict[str, Any]] = {}
    raw_rows: list[dict[str, Any]] = []
    for tuple_index, target_indices in enumerate(discovery_tuples_rows):
        decode = decode_tagged_tuple(domains, overlays, target_indices)
        if decode.predicted_indices[factor_index] == atom_index:
            continue
        true_vector = domains[factor_index, atom_index]
        wrong_index = top_wrong_competitor(decode.semantic_scores[factor_index], atom_index)
        wrong_vector = domains[factor_index, wrong_index]
        estimate = decode.factor_estimates[factor_index]
        delta = estimate * (true_vector - wrong_vector)
        partner_signature = tuple(value for idx, value in enumerate(target_indices) if idx != factor_index)
        negative_coords = torch.where(delta < 0)[0].tolist()
        raw_rows.append(
            {
                "cell_id": cell.cell_id,
                "codebook_seed": codebook_seed,
                "factor_index": factor_index,
                "atom_index": atom_index,
                "target_indices": list(target_indices),
                "wrong_competitor_index": wrong_index,
                "negative_coordinates": negative_coords,
            }
        )
        for coordinate in negative_coords:
            bucket = conflict_map.setdefault(
                int(coordinate),
                {
                    "negative_margins": [],
                    "wrong_competitors": set(),
                    "partner_signatures": set(),
                },
            )
            bucket["negative_margins"].append(float(-delta[coordinate].item()))
            bucket["wrong_competitors"].add(wrong_index)
            bucket["partner_signatures"].add(partner_signature)
    result: list[ConflictCoordinate] = []
    for coordinate, bucket in conflict_map.items():
        frequency = len(bucket["negative_margins"])
        if frequency < MIN_STABLE_CONFLICT_FREQUENCY:
            continue
        true_value = int(domains[factor_index, atom_index, coordinate].item())
        distinct_partner_count = len(bucket["partner_signatures"])
        stability_score = frequency * statistics.fmean(bucket["negative_margins"])
        result.append(
            ConflictCoordinate(
                atom_id=f"{cell.cell_id}:f{factor_index}:a{atom_index}",
                factor_domain=factor_index,
                coordinate=coordinate,
                true_value=true_value,
                conflict_frequency=frequency,
                mean_negative_margin=float(statistics.fmean(bucket["negative_margins"])),
                wrong_competitor_count=len(bucket["wrong_competitors"]),
                distinct_partner_count=distinct_partner_count,
                distinct_decoder_seed_count=1,
                stability_score=float(stability_score),
            )
        )
    result.sort(
        key=lambda item: (
            item.stability_score,
            item.mean_negative_margin,
            item.distinct_partner_count,
            -item.coordinate,
        ),
        reverse=True,
    )
    return result, raw_rows


def random_coordinate_order(dimensions: int, seed: int) -> tuple[int, ...]:
    values = list(range(dimensions))
    rng = random.Random(seed)
    rng.shuffle(values)
    return tuple(values)


def shuffled_conflict_order(conflicts: list[ConflictCoordinate], seed: int) -> tuple[int, ...]:
    coords = [item.coordinate for item in conflicts]
    rng = random.Random(seed)
    rng.shuffle(coords)
    return tuple(coords)


def overlay_from_order(order: tuple[int, ...], budget: int) -> MarkerOverlay:
    return MarkerOverlay(tuple(order[:budget]))


def apply_overlay(
    base_overlays: list[list[MarkerOverlay]],
    factor_index: int,
    atom_index: int,
    overlay: MarkerOverlay,
) -> list[list[MarkerOverlay]]:
    updated = clone_overlays(base_overlays)
    updated[factor_index][atom_index] = overlay
    return updated


def build_random_patch_candidates(dimensions: int, budget: int, seed: int) -> list[MarkerOverlay]:
    if budget <= 0:
        return [MarkerOverlay(tuple())]
    values = list(range(dimensions))
    rng = random.Random(seed)
    overlays: list[MarkerOverlay] = []
    for proposal_index in range(RANDOM_PATCH_CANDIDATES):
        rng.shuffle(values)
        overlays.append(MarkerOverlay(tuple(values[:budget])))
        values = values[:]
    return overlays


def typed_outcome_from_budgets(results: list[ArmBudgetResult]) -> str:
    if not results:
        return OUTCOME_FALLBACK_REQUIRED
    if results[0].certified:
        return OUTCOME_STANDARD_CERTIFIED
    for result in results[1:]:
        if result.certified:
            return OUTCOME_TAG_REPAIRED_CERTIFIED
    if any(result.selected_coordinates for result in results[1:]):
        best_final = max(result.final_eval.exact_recovery_rate for result in results[1:])
        if best_final > results[0].final_eval.exact_recovery_rate:
            return OUTCOME_REPAIR_IMPROVED_NOT_CERTIFIED
        return OUTCOME_TAG_BUDGET_EXHAUSTED
    return OUTCOME_NO_STABLE_CONFLICTS


def evaluate_overlay_budget(
    arm_id: str,
    cell: CellSpec,
    codebook_seed: int,
    domains: torch.Tensor,
    base_overlays: list[list[MarkerOverlay]],
    factor_index: int,
    atom_index: int,
    budget: int,
    overlay: MarkerOverlay,
    certification_tuples_rows: list[tuple[int, ...]],
    validation_tuples_rows: list[tuple[int, ...]],
    final_tuples_rows: list[tuple[int, ...]],
    old_only_rows: list[tuple[int, ...]],
) -> tuple[ArmBudgetResult, list[dict[str, Any]]]:
    overlays = apply_overlay(base_overlays, factor_index, atom_index, overlay)
    cert_rows, cert_summary = evaluate_tuples(domains, overlays, certification_tuples_rows, SPLIT_CERTIFICATION)
    validation_rows, validation_summary = evaluate_tuples(domains, overlays, validation_tuples_rows, SPLIT_VALIDATION)
    final_rows, final_summary = evaluate_tuples(domains, overlays, final_tuples_rows, SPLIT_FINAL)
    old_rows, old_summary = evaluate_tuples(domains, overlays, old_only_rows, WORKLOAD_OLD_ONLY)
    typed = OUTCOME_STANDARD_CERTIFIED if budget == 0 and strict_certificate(cert_summary) else (
        OUTCOME_TAG_REPAIRED_CERTIFIED if strict_certificate(cert_summary) else OUTCOME_TAG_BUDGET_EXHAUSTED
    )
    result = ArmBudgetResult(
        arm_id=arm_id,
        budget=budget,
        certified=strict_certificate(cert_summary),
        evaluation=cert_summary,
        validation=validation_summary,
        final_eval=final_summary,
        old_only=old_summary,
        physical_bits=domains.size(-1) + marker_overlay_bits(domains.size(-1), len(overlay.coordinates)),
        semantic_bits=domains.size(-1),
        marker_overlay_bits=marker_overlay_bits(domains.size(-1), len(overlay.coordinates)),
        composite_marker_bits=2 * domains.size(-1),
        certification_calls=len(certification_tuples_rows),
        patch_evaluations=1,
        typed_outcome=typed,
        selected_coordinates=overlay.coordinates,
    )
    rows = cert_rows + validation_rows + final_rows + old_rows
    return result, rows


def evaluate_equal_bit_budget(
    cell: CellSpec,
    codebook_seed: int,
    factor_index: int,
    atom_index: int,
    budget: int,
    certification_tuples_rows: list[tuple[int, ...]],
    validation_tuples_rows: list[tuple[int, ...]],
    final_tuples_rows: list[tuple[int, ...]],
    old_only_rows: list[tuple[int, ...]],
) -> tuple[ArmBudgetResult, list[dict[str, Any]]]:
    extra_dimensions = extra_dimensions_for_budget(cell.dimensions, budget)
    expanded_domains = initial_codebook(cell.dimensions + extra_dimensions, cell.domain_size, codebook_seed + budget + 9_000)
    overlays = empty_overlays(expanded_domains)
    cert_rows, cert_summary = evaluate_tuples(expanded_domains, overlays, certification_tuples_rows, SPLIT_CERTIFICATION)
    validation_rows, validation_summary = evaluate_tuples(expanded_domains, overlays, validation_tuples_rows, SPLIT_VALIDATION)
    final_rows, final_summary = evaluate_tuples(expanded_domains, overlays, final_tuples_rows, SPLIT_FINAL)
    old_rows, old_summary = evaluate_tuples(expanded_domains, overlays, old_only_rows, WORKLOAD_OLD_ONLY)
    result = ArmBudgetResult(
        arm_id=ARM_EQUAL_BIT_EXTRA_DIMENSIONS,
        budget=budget,
        certified=strict_certificate(cert_summary),
        evaluation=cert_summary,
        validation=validation_summary,
        final_eval=final_summary,
        old_only=old_summary,
        physical_bits=expanded_domains.size(-1),
        semantic_bits=expanded_domains.size(-1),
        marker_overlay_bits=0,
        composite_marker_bits=0,
        certification_calls=len(certification_tuples_rows),
        patch_evaluations=1,
        typed_outcome=OUTCOME_STANDARD_CERTIFIED if strict_certificate(cert_summary) else OUTCOME_TAG_BUDGET_EXHAUSTED,
        selected_coordinates=tuple(),
        expanded_dimensions=expanded_domains.size(-1),
    )
    return result, cert_rows + validation_rows + final_rows + old_rows


def choose_random_patch_result(
    cell: CellSpec,
    codebook_seed: int,
    domains: torch.Tensor,
    base_overlays: list[list[MarkerOverlay]],
    factor_index: int,
    atom_index: int,
    budget: int,
    certification_tuples_rows: list[tuple[int, ...]],
    validation_tuples_rows: list[tuple[int, ...]],
    final_tuples_rows: list[tuple[int, ...]],
    old_only_rows: list[tuple[int, ...]],
) -> tuple[ArmBudgetResult, list[dict[str, Any]]]:
    best_result: ArmBudgetResult | None = None
    best_rows: list[dict[str, Any]] = []
    for proposal_index, overlay in enumerate(
        build_random_patch_candidates(
            domains.size(-1),
            budget,
            codebook_seed + PATCH_SEED_OFFSET + factor_index * 100 + atom_index * 10 + budget,
        )
    ):
        result, rows = evaluate_overlay_budget(
            ARM_RANDOM_PATCH_SEARCH,
            cell,
            codebook_seed,
            domains,
            base_overlays,
            factor_index,
            atom_index,
            budget,
            overlay,
            certification_tuples_rows,
            validation_tuples_rows,
            final_tuples_rows,
            old_only_rows,
        )
        if best_result is None:
            best_result = result
            best_rows = rows
            continue
        current_key = (
            result.certified,
            result.evaluation.exact_recovery_rate,
            result.evaluation.verified_reconstruction_rate,
            -result.evaluation.conditional_risk,
            result.evaluation.mean_min_margin,
            -proposal_index,
        )
        best_key = (
            best_result.certified,
            best_result.evaluation.exact_recovery_rate,
            best_result.evaluation.verified_reconstruction_rate,
            -best_result.evaluation.conditional_risk,
            best_result.evaluation.mean_min_margin,
            -1,
        )
        if current_key > best_key:
            best_result = result
            best_rows = rows
    if best_result is None:
        raise RuntimeError("Random patch arm produced no proposals.")
    return (
        ArmBudgetResult(
            arm_id=best_result.arm_id,
            budget=best_result.budget,
            certified=best_result.certified,
            evaluation=best_result.evaluation,
            validation=best_result.validation,
            final_eval=best_result.final_eval,
            old_only=best_result.old_only,
            physical_bits=best_result.physical_bits,
            semantic_bits=best_result.semantic_bits,
            marker_overlay_bits=best_result.marker_overlay_bits,
            composite_marker_bits=best_result.composite_marker_bits,
            certification_calls=best_result.certification_calls,
            patch_evaluations=RANDOM_PATCH_CANDIDATES,
            typed_outcome=best_result.typed_outcome,
            selected_coordinates=best_result.selected_coordinates,
            expanded_dimensions=best_result.expanded_dimensions,
        ),
        best_rows,
    )


def pick_target_atoms(cell: CellSpec) -> tuple[int, ...]:
    return tuple(cell.domain_size - 1 - index for index in range(cell.target_atom_count))


def execute_smoke_stage(repo_root: Path) -> dict[str, Any]:
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    conflict_rows: list[dict[str, Any]] = []

    for cell in CELLS:
        if not cell.execute_in_stage:
            continue
        target_atoms = pick_target_atoms(cell)
        for codebook_seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count):
            print(f"{PROGRESS_PREFIX} cell={cell.cell_id} seed={codebook_seed}", flush=True)
            domains = initial_codebook(cell.dimensions, cell.domain_size, codebook_seed)
            base_overlays = empty_overlays(domains)
            for factor_index in range(FACTOR_COUNT):
                for atom_index in target_atoms:
                    discovery_tuples_rows = tuples_for_target(
                        codebook_seed + DISCOVERY_SEED_OFFSET + factor_index * 100 + atom_index,
                        DISCOVERY_TRIALS,
                        cell.domain_size,
                        factor_index,
                        atom_index,
                    )
                    certification_tuples_rows = tuples_for_target(
                        codebook_seed + CERT_SEED_OFFSET + factor_index * 100 + atom_index,
                        CERTIFICATION_TRIALS,
                        cell.domain_size,
                        factor_index,
                        atom_index,
                    )
                    validation_tuples_rows = tuples_for_target(
                        codebook_seed + VALIDATION_SEED_OFFSET + factor_index * 100 + atom_index,
                        VALIDATION_TRIALS,
                        cell.domain_size,
                        factor_index,
                        atom_index,
                    )
                    final_tuples_rows = tuples_for_target(
                        codebook_seed + FINAL_SEED_OFFSET + factor_index * 100 + atom_index,
                        FINAL_TRIALS,
                        cell.domain_size,
                        factor_index,
                        atom_index,
                    )
                    old_only_rows = old_only_tuples(
                        codebook_seed + FINAL_SEED_OFFSET + 9_000 + factor_index * 100 + atom_index,
                        OLD_ONLY_TRIALS,
                        cell.domain_size,
                        factor_index,
                        atom_index,
                    )
                    conflicts, conflict_raw = stable_conflict_report(
                        cell,
                        codebook_seed,
                        domains,
                        factor_index,
                        atom_index,
                        discovery_tuples_rows,
                        base_overlays,
                    )
                    conflict_rows.extend(conflict_raw)
                    conflict_order = tuple(item.coordinate for item in conflicts)
                    random_order = random_coordinate_order(
                        cell.dimensions,
                        codebook_seed + PATCH_SEED_OFFSET + factor_index * 100 + atom_index,
                    )
                    shuffled_order = shuffled_conflict_order(
                        conflicts,
                        codebook_seed + SHUFFLE_SEED_OFFSET + factor_index * 100 + atom_index,
                    )
                    per_arm_results: dict[str, list[ArmBudgetResult]] = {arm_id: [] for arm_id in ALLOWED_ARMS}
                    per_arm_rows: dict[str, list[dict[str, Any]]] = {arm_id: [] for arm_id in ALLOWED_ARMS}

                    for budget in REPAIR_LADDER:
                        arm_a_result, arm_a_rows = evaluate_overlay_budget(
                            ARM_BASE_BINARY,
                            cell,
                            codebook_seed,
                            domains,
                            base_overlays,
                            factor_index,
                            atom_index,
                            0,
                            MarkerOverlay(tuple()),
                            certification_tuples_rows,
                            validation_tuples_rows,
                            final_tuples_rows,
                            old_only_rows,
                        )
                        if budget == 0:
                            per_arm_results[ARM_BASE_BINARY].append(arm_a_result)
                            per_arm_rows[ARM_BASE_BINARY].extend(arm_a_rows)
                        if budget > 0:
                            arm_b_result, arm_b_rows = evaluate_overlay_budget(
                                ARM_RANDOM_TAGS,
                                cell,
                                codebook_seed,
                                domains,
                                base_overlays,
                                factor_index,
                                atom_index,
                                budget,
                                overlay_from_order(random_order, budget),
                                certification_tuples_rows,
                                validation_tuples_rows,
                                final_tuples_rows,
                                old_only_rows,
                            )
                            per_arm_results[ARM_RANDOM_TAGS].append(arm_b_result)
                            per_arm_rows[ARM_RANDOM_TAGS].extend(arm_b_rows)
                            arm_c_result, arm_c_rows = evaluate_overlay_budget(
                                ARM_SHUFFLED_CONFLICT_TAGS,
                                cell,
                                codebook_seed,
                                domains,
                                base_overlays,
                                factor_index,
                                atom_index,
                                budget,
                                overlay_from_order(shuffled_order, budget),
                                certification_tuples_rows,
                                validation_tuples_rows,
                                final_tuples_rows,
                                old_only_rows,
                            )
                            per_arm_results[ARM_SHUFFLED_CONFLICT_TAGS].append(arm_c_result)
                            per_arm_rows[ARM_SHUFFLED_CONFLICT_TAGS].extend(arm_c_rows)
                            arm_d_result, arm_d_rows = choose_random_patch_result(
                                cell,
                                codebook_seed,
                                domains,
                                base_overlays,
                                factor_index,
                                atom_index,
                                budget,
                                certification_tuples_rows,
                                validation_tuples_rows,
                                final_tuples_rows,
                                old_only_rows,
                            )
                            per_arm_results[ARM_RANDOM_PATCH_SEARCH].append(arm_d_result)
                            per_arm_rows[ARM_RANDOM_PATCH_SEARCH].extend(arm_d_rows)
                            arm_e_overlay = overlay_from_order(conflict_order, budget)
                            arm_e_result, arm_e_rows = evaluate_overlay_budget(
                                ARM_CONFLICT_GUIDED_TAGS,
                                cell,
                                codebook_seed,
                                domains,
                                base_overlays,
                                factor_index,
                                atom_index,
                                budget,
                                arm_e_overlay,
                                certification_tuples_rows,
                                validation_tuples_rows,
                                final_tuples_rows,
                                old_only_rows,
                            )
                            per_arm_results[ARM_CONFLICT_GUIDED_TAGS].append(arm_e_result)
                            per_arm_rows[ARM_CONFLICT_GUIDED_TAGS].extend(arm_e_rows)
                            arm_f_result, arm_f_rows = evaluate_equal_bit_budget(
                                cell,
                                codebook_seed,
                                factor_index,
                                atom_index,
                                budget,
                                certification_tuples_rows,
                                validation_tuples_rows,
                                final_tuples_rows,
                                old_only_rows,
                            )
                            per_arm_results[ARM_EQUAL_BIT_EXTRA_DIMENSIONS].append(arm_f_result)
                            per_arm_rows[ARM_EQUAL_BIT_EXTRA_DIMENSIONS].extend(arm_f_rows)

                    for arm_id, budget_results in per_arm_results.items():
                        if not budget_results:
                            continue
                        arm_outcome = typed_outcome_from_budgets(budget_results)
                        selected = next((item for item in budget_results if item.certified), budget_results[-1])
                        summary_rows.append(
                            {
                                "schema_version": SCHEMA_VERSION,
                                "cell_id": cell.cell_id,
                                "dimensions": cell.dimensions,
                                "codebook_seed": codebook_seed,
                                "factor_index": factor_index,
                                "atom_index": atom_index,
                                "arm_id": arm_id,
                                "typed_outcome": arm_outcome,
                                "selected_budget": selected.budget,
                                "certified": selected.certified,
                                "exact_recovery_final": selected.final_eval.exact_recovery_rate,
                                "verified_reconstruction_final": selected.final_eval.verified_reconstruction_rate,
                                "accepted_coverage_final": selected.final_eval.accepted_coverage,
                                "conditional_risk_final": selected.final_eval.conditional_risk,
                                "old_only_exact_recovery": selected.old_only.exact_recovery_rate,
                                "marker_overlay_bits": selected.marker_overlay_bits,
                                "physical_bits": selected.physical_bits,
                                "expanded_dimensions": selected.expanded_dimensions,
                                "patch_evaluations": sum(item.patch_evaluations for item in budget_results),
                                "conflict_coordinate_count": len(conflict_order),
                            }
                        )
                        for result in budget_results:
                            raw_rows.append(
                                {
                                    "record_type": "budget_result",
                                    "cell_id": cell.cell_id,
                                    "dimensions": cell.dimensions,
                                    "codebook_seed": codebook_seed,
                                    "factor_index": factor_index,
                                    "atom_index": atom_index,
                                    "arm_id": arm_id,
                                    **asdict(result),
                                }
                            )
                        raw_rows.extend(
                            {
                                "record_type": "evaluation_trial",
                                "cell_id": cell.cell_id,
                                "dimensions": cell.dimensions,
                                "codebook_seed": codebook_seed,
                                "factor_index": factor_index,
                                "atom_index": atom_index,
                                "arm_id": arm_id,
                                "typed_outcome": arm_outcome,
                                **row,
                            }
                            for row in per_arm_rows[arm_id]
                        )
                        raw_rows.append(
                            {
                                "record_type": "conflict_report",
                                "cell_id": cell.cell_id,
                                "codebook_seed": codebook_seed,
                                "factor_index": factor_index,
                                "atom_index": atom_index,
                                "arm_id": arm_id,
                                "conflict_coordinate_count": len(conflict_order),
                                "conflict_coordinates": list(conflict_order),
                                "stability_scores": [item.stability_score for item in conflicts],
                            }
                        )
    return {
        "raw_rows": raw_rows,
        "summary_rows": summary_rows,
        "conflict_rows": conflict_rows,
    }


def summarize(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in summary_rows:
        grouped.setdefault(row["arm_id"], []).append(row)
    arm_rows: list[dict[str, Any]] = []
    for arm_id in ALLOWED_ARMS:
        batch = grouped.get(arm_id, [])
        if not batch:
            continue
        arm_rows.append(
            {
                "arm_id": arm_id,
                "rows": len(batch),
                "mean_final_exact_recovery": float(statistics.fmean(row["exact_recovery_final"] for row in batch)),
                "mean_final_verified_reconstruction": float(
                    statistics.fmean(row["verified_reconstruction_final"] for row in batch)
                ),
                "mean_final_accepted_coverage": float(
                    statistics.fmean(row["accepted_coverage_final"] for row in batch)
                ),
                "mean_final_conditional_risk": float(
                    statistics.fmean(row["conditional_risk_final"] for row in batch)
                ),
                "mean_old_only_exact_recovery": float(
                    statistics.fmean(row["old_only_exact_recovery"] for row in batch)
                ),
                "mean_physical_bits": float(statistics.fmean(row["physical_bits"] for row in batch)),
            }
        )
    lookup = {row["arm_id"]: row for row in arm_rows}
    scientific_verdict = "INCONCLUSIVE_REQUIRES_MORE_POWER"
    claim_state = "CONFLICT_GUIDED_REPAIR_ADVANTAGE_NOT_SUPPORTED"
    engineering_verdict = "BLOCK_TAGGED_SYMBOL_LINE"
    if ARM_CONFLICT_GUIDED_TAGS in lookup and ARM_RANDOM_PATCH_SEARCH in lookup and ARM_SHUFFLED_CONFLICT_TAGS in lookup:
        guided = lookup[ARM_CONFLICT_GUIDED_TAGS]
        shuffled = lookup[ARM_SHUFFLED_CONFLICT_TAGS]
        random_patch = lookup[ARM_RANDOM_PATCH_SEARCH]
        extra_dim = lookup[ARM_EQUAL_BIT_EXTRA_DIMENSIONS]
        guided_better_controls = (
            guided["mean_final_exact_recovery"] > shuffled["mean_final_exact_recovery"]
            and guided["mean_final_exact_recovery"] > random_patch["mean_final_exact_recovery"]
        )
        guided_safe = guided["mean_final_conditional_risk"] <= min(
            shuffled["mean_final_conditional_risk"], random_patch["mean_final_conditional_risk"]
        )
        extra_dim_dominates = (
            extra_dim["mean_final_exact_recovery"] >= guided["mean_final_exact_recovery"]
            and extra_dim["mean_final_conditional_risk"] <= guided["mean_final_conditional_risk"]
            and extra_dim["mean_physical_bits"] <= guided["mean_physical_bits"]
        )
        if guided_better_controls and guided_safe and not extra_dim_dominates:
            scientific_verdict = "PARTIAL_CONFLICT_GUIDED_EFFECT"
            claim_state = "CONFLICT_GUIDED_REPAIR_ADVANTAGE_PARTIAL"
            engineering_verdict = "SCIENTIFIC_EFFECT_ONLY"
        elif extra_dim_dominates:
            scientific_verdict = "BLOCK_TAGGED_SYMBOL_LINE"
            claim_state = "CONFLICT_GUIDED_REPAIR_ADVANTAGE_NOT_SUPPORTED"
            engineering_verdict = "ADOPT_EXTRA_DIMENSIONS"
    return {
        "build_verdict": "PROTOTYPE",
        "engineering_verdict": engineering_verdict,
        "scientific_verdict": scientific_verdict,
        "claim_state": claim_state,
        "execution_scope": "tiny_smoke_only",
        "heldout_execution_count": 0,
        "arm_summary": arm_rows,
    }


def build_execution_plan(protocol: dict[str, Any]) -> str:
    active_specs = [cell for cell in CELLS if cell.execute_in_stage]
    codebook_seeds = sum(cell.codebook_seed_count for cell in active_specs)
    target_atoms = sum(cell.target_atom_count for cell in active_specs) * FACTOR_COUNT * codebook_seeds
    discovery_trials = target_atoms * DISCOVERY_TRIALS
    certification_trials = target_atoms * CERTIFICATION_TRIALS * (len(REPAIR_LADDER) * 5 + 1)
    final_trials = target_atoms * FINAL_TRIALS * len(ALLOWED_ARMS)
    patch_evaluations = target_atoms * (len(REPAIR_LADDER) - 1) * (1 + RANDOM_PATCH_CANDIDATES + 1 + 1)
    lines = [
        f"# {TASK_NAME} execution plan",
        "",
        f"- starting_commit: `{STARTING_COMMIT}`",
        f"- selected_cells: `{len(active_specs)}`",
        f"- target_atoms: `{target_atoms}`",
        f"- codebook_seeds: `{codebook_seeds}`",
        f"- discovery_trials: `{discovery_trials}`",
        f"- certification_trials: `{certification_trials}`",
        f"- final_evaluation_trials: `{final_trials}`",
        f"- patch_evaluations: `{patch_evaluations}`",
        f"- estimated_decoder_calls: `{discovery_trials + certification_trials + final_trials}`",
        f"- selected_device: `cpu`",
        f"- output_path: `results/{RESULTS_NAMESPACE}`",
        f"- long_run_authorized: `{EXECUTE_LONG_RUN}`",
        "",
        "This stage executes only a tiny deterministic smoke run because Level 3.5b confirmatory closure is still open.",
    ]
    return "\n".join(lines) + "\n"


def build_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} audit",
        "",
        "- Verdict: `PROTOTYPE / COMPOSE`",
        "- Status: `PROTOTYPE / DEVELOPMENT_ONLY / NEW_HYPOTHESIS / NO_PRODUCTION_CLAIM`",
        "",
        "## Previous blocked line",
        "",
        f"- commit: `{audit['previous_blocked_line']['commit']}`",
        f"- scientific verdict: `{audit['previous_blocked_line']['scientific_verdict']}`",
        f"- kill gate: `{audit['previous_blocked_line']['kill_gate']}`",
        "",
        "## Prior art",
        "",
    ]
    for item in audit["anti_nih_findings"]:
        lines.append(
            f"- `{item['family']}`: `{item['verdict']}` with estimated coverage `{item['coverage']:.1f}`. {item['notes']}"
        )
    lines.extend(["", "## Why not scratch", ""])
    for item in audit["why_not_scratch"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Minimal path",
            "",
            "- Reuse the current MAP/TorchHD semantic decoder.",
            "- Add only a bit-exact tagged recovery view, marker merge, conflict attribution, and matched controls.",
            "- Keep exact fallback as a typed outcome only; do not implement a runtime router, ANN, DAG, or pointer layer.",
            "",
            "## AGI claim gate",
            "",
            "- Claim boundary: decoder-derived stable conflict attribution driving minimal sparse tagged-symbol repair in an open-world VSA recovery view.",
            "- Authority boundary: semantic MAP state remains native; marker evidence only changes candidate cleanup/ranking.",
            "- Failure criterion: if guided placement does not beat shuffled/random controls or is dominated by equal-bit extra dimensions, block the line.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_protocol_markdown(protocol: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} protocol",
        "",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        f"- Starting commit: `{protocol['starting_commit']}`",
        f"- Held-out execution allowed: `{protocol['heldout_execution_allowed']}`",
        f"- Long run authorized: `{protocol['long_run_authorized']}`",
        "",
        "## Representation contract",
        "",
        f"- Tagged alphabet: `{', '.join(protocol['representation_contract']['tagged_alphabet'])}`",
        f"- Semantic projection preserved: `{protocol['representation_contract']['semantic_projection_preserved']}`",
        f"- Marker score: `{protocol['representation_contract']['marker_score_formula']}`",
        "",
        "## Frozen cells",
        "",
    ]
    for cell in protocol["cells"]:
        lines.append(
            f"- `{cell['cell_id']}`: D=`{cell['dimensions']}`, M=`{cell['domain_size']}`, seeds `{cell['seed_range']['start']}..{cell['seed_range']['start'] + cell['seed_range']['count'] - 1}`."
        )
    lines.extend(["", "## Arms", ""])
    for arm in protocol["arms"]:
        lines.append(f"- `{arm}`")
    lines.extend(
        [
            "",
            "## Repair ladder",
            "",
            f"- `{protocol['repair_ladder']}`",
            "",
            "## Certificate",
            "",
            f"- verified exact recovery >= `{protocol['strict_certificate']['verified_exact_recovery_min']}`",
            f"- conditional risk <= `{protocol['strict_certificate']['conditional_risk_max']}`",
            f"- silent wrong acceptance <= `{protocol['strict_certificate']['silent_wrong_acceptance_max']}`",
            f"- accepted coverage >= `{protocol['strict_certificate']['accepted_coverage_min']}`",
            "",
            "## Scope limit",
            "",
            f"- {protocol['scope_limit_reason']}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(protocol: dict[str, Any], summary: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"- Build verdict: `{summary['build_verdict']}`",
        f"- Engineering verdict: `{summary['engineering_verdict']}`",
        f"- Scientific verdict: `{summary['scientific_verdict']}`",
        f"- Claim state: `{summary['claim_state']}`",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        "",
        "## Scope note",
        "",
        "This report covers only a tiny deterministic smoke run. A longer development run remains blocked until Level 3.5b confirmatory closure is complete.",
        "",
        "## Arm snapshot",
        "",
    ]
    for row in summary["arm_summary"]:
        lines.append(
            f"- `{row['arm_id']}`: final exact `{row['mean_final_exact_recovery']:.4f}`, "
            f"coverage `{row['mean_final_accepted_coverage']:.4f}`, "
            f"risk `{row['mean_final_conditional_risk']:.4f}`, "
            f"old-only `{row['mean_old_only_exact_recovery']:.4f}`, "
            f"bits `{row['mean_physical_bits']:.1f}`."
        )
    return "\n".join(lines) + "\n"


def run_decoder_guided_tag_repair(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs"
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol = build_protocol(repo_root)
    audit = dependency_audit(repo_root)
    plan_text = build_execution_plan(protocol)
    print(plan_text, flush=True)

    execution = execute_smoke_stage(repo_root)
    summary = summarize(execution["summary_rows"])
    audit_markdown = build_audit_markdown(audit)
    protocol_markdown = build_protocol_markdown(protocol)
    report = build_report(protocol, summary)

    write_text(docs_dir / "LEVEL3_DECODER_GUIDED_TAG_REPAIR_AUDIT.md", audit_markdown)
    write_text(docs_dir / "LEVEL3_DECODER_GUIDED_TAG_REPAIR_PROTOCOL.md", protocol_markdown)
    write_text(results_dir / "execution_plan.md", plan_text)
    write_text(results_dir / "frozen_protocol.yaml", "\n".join(yaml_lines(protocol)) + "\n")
    write_json(results_dir / "summary.json", summary | {"protocol_hash": protocol["protocol_hash"], "seed_fresh": seeds_are_fresh(repo_root)})
    write_text(results_dir / "report.md", report)
    write_json(results_dir / "dependency_audit.json", audit)
    write_json(results_dir / "environment.json", environment_snapshot())
    write_jsonl(results_dir / "raw_trials.jsonl", execution["raw_rows"])
    write_jsonl(results_dir / "conflict_reports.jsonl", execution["conflict_rows"])
    write_csv(results_dir / "arm_summary.csv", execution["summary_rows"])

    return {
        "protocol": protocol,
        "summary": summary,
        "raw_rows": execution["raw_rows"],
        "summary_rows": execution["summary_rows"],
        "conflict_rows": execution["conflict_rows"],
    }
