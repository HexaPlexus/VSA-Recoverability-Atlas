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
import torchhd

from .baseline import (
    BaselineConfig,
    bind_sequence,
    build_initial_estimates,
    cosine_similarity_matrix,
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

SCHEMA_VERSION = "decoder-certified-codebook-v0.1-dev"
TASK_NAME = "Decoder-Certified Codebook Construction v0.1"
RESULTS_NAMESPACE = "decoder_certified_codebook_v0_1"
U1_TASK_CONTRACT = "U1_blind_single_product_factorization"
STARTING_COMMIT = "52060ef73c41bbde2110b479120710a4f1750bb7"

VERDICT_PROTOTYPE = "PROTOTYPE"
VERDICT_NO_PRODUCTION = "NO_PRODUCTION_CLAIM"
RESEARCH_VERDICTS = (
    "ADOPT_DECODER_CERTIFIED_ADMISSION",
    "ADOPT_DISTANCE_ONLY_ADMISSION",
    "PARTIAL_DECODER_CERTIFICATION_EFFECT",
    "SCIENTIFIC_EFFECT_ONLY",
    "BLOCK_DECODER_CERTIFICATION_LINE",
    "INCONCLUSIVE_REQUIRES_MORE_POWER",
)
CLAIM_VERDICTS = (
    "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_SUPPORTED",
    "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_PARTIAL",
    "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED",
)

ARM_RANDOM_FIRST = "A_RANDOM_FIRST"
ARM_DISTANCE_MAXMIN = "B_DISTANCE_MAXMIN"
ARM_DECODER_CERTIFIED = "C_DECODER_CERTIFIED"
ARM_SHUFFLED_CONTROL = "D_SHUFFLED_CERTIFICATION_CONTROL"
ALLOWED_ARMS = (ARM_RANDOM_FIRST, ARM_DISTANCE_MAXMIN, ARM_DECODER_CERTIFIED, ARM_SHUFFLED_CONTROL)

NO_COMMIT = "NO_COMMIT_AT_FIXED_BUDGET"
OUTCOME_ACCEPT = "ACCEPT"
OUTCOME_VERIFIER_REJECT = "VERIFIER_REJECT"
OUTCOME_PARTIAL = "PARTIAL_RECOVERY"
OUTCOME_FAILURE = "FAILURE"

SPLIT_CERTIFICATION = "CERTIFICATION"
SPLIT_VALIDATION = "DEVELOPMENT_VALIDATION"
SPLIT_FINAL = "FINAL_DEVELOPMENT_EVALUATION"
ALLOWED_SPLITS = (SPLIT_CERTIFICATION, SPLIT_VALIDATION, SPLIT_FINAL)

WORKLOAD_OLD_ONLY = "old_only"
WORKLOAD_NEW_ATOM = "new_atom"
WORKLOAD_HARD = "previous_hard_case"

MAX_ITERATIONS = 12
STABLE_PATIENCE = 3
FACTOR_COUNT = 3
K_VALUES = (1, 4)
SEMANTIC_CORRUPTION = "clean_only"
EXECUTE_LONG_RUN = False

POOL_SEED_OFFSET = 100_000
CERT_SEED_OFFSET = 200_000
VALIDATION_SEED_OFFSET = 300_000
FINAL_SEED_OFFSET = 400_000
SHUFFLE_SEED_OFFSET = 500_000

PRIMARY_SILENT_ERROR_GATE = 0
PROGRESS_PREFIX = "[decoder-certified]"


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    dimensions: int
    initial_domain_size: int
    final_domain_size: int
    codebook_seed_start: int
    codebook_seed_count: int
    certification_tuples_per_factor: int
    validation_tuples_per_factor: int
    final_tuples_per_factor: int
    old_only_tuples: int
    hard_templates: int
    execute_in_stage: bool
    stage_role: str

    @property
    def insertion_rounds(self) -> int:
        return self.final_domain_size - self.initial_domain_size

    def seed_range(self) -> dict[str, int]:
        return {"start": self.codebook_seed_start, "count": self.codebook_seed_count}


@dataclass(frozen=True)
class DecodeMetrics:
    predicted_indices: tuple[int, ...]
    exact_recovery: bool
    verified_reconstruction: bool
    stable_prediction: bool
    per_factor_recovery: tuple[bool, ...]
    min_margin: float
    mean_margin: float
    iterations: int
    decode_latency_sec: float


@dataclass(frozen=True)
class CandidateScore:
    candidate_index: int
    silent_wrong_count: int
    exact_factor_recovery_rate: float
    verified_reconstruction_rate: float
    mean_min_margin: float
    mean_iterations: float
    mean_latency_sec: float
    accepted_outputs: int
    total_trials: int

    @property
    def passes_gate(self) -> bool:
        return self.silent_wrong_count <= PRIMARY_SILENT_ERROR_GATE


@dataclass(frozen=True)
class SelectionOutcome:
    selected_candidate_index: int | None
    selected_by_rule: str
    no_commit: bool
    candidate_scores: tuple[CandidateScore, ...]
    certification_calls: int
    shuffled_mapping: tuple[int, ...] | None = None


CELLS: tuple[CellSpec, ...] = (
    CellSpec(
        cell_id="smoke_d512_m10",
        dimensions=512,
        initial_domain_size=8,
        final_domain_size=10,
        codebook_seed_start=961_510_100,
        codebook_seed_count=1,
        certification_tuples_per_factor=2,
        validation_tuples_per_factor=2,
        final_tuples_per_factor=3,
        old_only_tuples=3,
        hard_templates=1,
        execute_in_stage=True,
        stage_role="sanity",
    ),
    CellSpec(
        cell_id="transition_d1024_m22",
        dimensions=1024,
        initial_domain_size=20,
        final_domain_size=22,
        codebook_seed_start=961_522_100,
        codebook_seed_count=2,
        certification_tuples_per_factor=4,
        validation_tuples_per_factor=4,
        final_tuples_per_factor=6,
        old_only_tuples=4,
        hard_templates=2,
        execute_in_stage=True,
        stage_role="paired_smoke",
    ),
    CellSpec(
        cell_id="transition_d1024_m31",
        dimensions=1024,
        initial_domain_size=29,
        final_domain_size=31,
        codebook_seed_start=961_531_100,
        codebook_seed_count=2,
        certification_tuples_per_factor=4,
        validation_tuples_per_factor=4,
        final_tuples_per_factor=6,
        old_only_tuples=4,
        hard_templates=2,
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


def normalized_similarity_pair(lhs: torch.Tensor, rhs: torch.Tensor) -> float:
    return float(torch.nn.functional.cosine_similarity(lhs.unsqueeze(0), rhs.unsqueeze(0), dim=-1).item())


def stage_seed_set() -> set[int]:
    values: set[int] = set()
    for cell in CELLS:
        for seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count):
            values.add(seed)
            values.add(seed + POOL_SEED_OFFSET)
            values.add(seed + CERT_SEED_OFFSET)
            values.add(seed + VALIDATION_SEED_OFFSET)
            values.add(seed + FINAL_SEED_OFFSET)
            values.add(seed + SHUFFLE_SEED_OFFSET)
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


def transition_evidence() -> list[dict[str, Any]]:
    return [
        {
            "source": "docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md",
            "cell_id": "u1_boundary_22",
            "evidence": "existing clean U1 boundary region",
        },
        {
            "source": "docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md",
            "cell_id": "u1_boundary_31",
            "evidence": "existing clean U1 transition region",
        },
    ]


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


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "COMPOSE",
        "starting_commit": STARTING_COMMIT,
        "anti_nih_findings": [
            {
                "family": "max-min Hamming / spherical code placement",
                "verdict": "ADOPT",
                "coverage": 0.6,
                "notes": "Directly covered by the distance-maxmin baseline; no need to reinvent a packing objective.",
            },
            {
                "family": "vector quantization / codebook search",
                "verdict": "ADAPT",
                "coverage": 0.5,
                "notes": "Similar search-over-codebook idea exists, but not as online factor-domain admission with the repository's blind MAP resonator in the loop.",
            },
            {
                "family": "learned encoder-decoder codebooks",
                "verdict": "BLOCK",
                "coverage": 0.2,
                "notes": "Out of scope here because this stage forbids a new decoder, learned scorer, or full training loop.",
            },
            {
                "family": "decoder-aware quantization / admission control",
                "verdict": "PROTOTYPE",
                "coverage": 0.4,
                "notes": "Motivational overlap exists, but no drop-in open-world MAP factor-codebook admission primitive is already present in the repo.",
            },
            {
                "family": "existing repo primitives",
                "verdict": "WRAP",
                "coverage": 1.0,
                "notes": "Reuse baseline.py and level3_2 confirmation MAP resonator path instead of building a new benchmark framework.",
            },
        ],
        "why_not_scratch": [
            "The repository already contains deterministic MAP domain generation, upstream TorchHD resonator calls, candidate ranking margins, and seed discipline.",
            "A new benchmark framework, optimizer, or learned codebook trainer would answer a different question than this narrow causal admission audit.",
            "This stage only needs a small wrapper around candidate-pool generation, decoder-in-the-loop certification, and split-aware evaluation.",
        ],
        "frozen_artifact_hashes": {
            "level35_v4_hash": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json"),
        },
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    protocol = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "development_only_smoke_pre_level3_5b_closure",
        "initial_verdict": [VERDICT_PROTOTYPE, "DEVELOPMENT_ONLY", VERDICT_NO_PRODUCTION],
        "starting_commit": STARTING_COMMIT,
        "long_run_authorized": EXECUTE_LONG_RUN,
        "heldout_execution_allowed": False,
        "scope_limit_reason": "Level 3.5b confirmatory closure is not complete; only audit, protocol, tests, and tiny smoke are lawful.",
        "substrate": {
            "family": "MAP",
            "decoder": "TorchHD resonator",
            "task_contract": U1_TASK_CONTRACT,
            "factor_count": FACTOR_COUNT,
            "max_iterations": MAX_ITERATIONS,
            "stable_patience": STABLE_PATIENCE,
            "corruption_contract": SEMANTIC_CORRUPTION,
        },
        "cells": [asdict(cell) | {"seed_range": cell.seed_range()} for cell in CELLS],
        "candidate_budget": {"k_values": list(K_VALUES), "candidate_pool_shared_across_arms": True},
        "arms": list(ALLOWED_ARMS),
        "selection_policy": [
            "exclude candidates that violate silent-error gate",
            "maximize exact factor recovery",
            "maximize verified reconstruction",
            "maximize top1-top2 margin",
            "minimize decoder iterations",
            "deterministic candidate-index tie-break",
        ],
        "split_separation": {
            "certification": "candidate selection only",
            "validation": "development validation only",
            "final_development_evaluation": "unseen smoke evaluation only",
            "disjoint_seed_offsets": {
                "candidate_pool": POOL_SEED_OFFSET,
                "certification": CERT_SEED_OFFSET,
                "validation": VALIDATION_SEED_OFFSET,
                "final": FINAL_SEED_OFFSET,
                "shuffle": SHUFFLE_SEED_OFFSET,
            },
        },
        "transition_evidence": transition_evidence(),
        "metrics": [
            "exact factor recovery",
            "verified reconstruction rate",
            "conditional risk among accepted outputs",
            "silent wrong acceptance rate",
            "abstention/no-commit rate",
            "top1-top2 margin",
            "decoder iterations",
            "decode latency",
            "candidate certification latency",
            "total insertion cost",
            "number of rejected candidates",
            "old-atom regression",
            "pairwise Hamming-distance distribution",
            "generalization gap",
            "break-even future query count",
        ],
        "allowed_claims": [
            "tiny smoke harness exists",
            "K=1 collapse sanity was checked",
            "decoder-certified admission can be compared causally against distance-only and shuffled controls",
        ],
        "forbidden_claims": [
            "general noisy superiority",
            "production readiness",
            "new decoder",
            "BCF or linear-code improvement",
            "held-out confirmation",
        ],
        "seed_fresh": seeds_are_fresh(repo_root),
        "level35_frozen_artifacts_unchanged": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256,
    }
    protocol["protocol_hash"] = canonical_json_hash(protocol)
    return protocol


def candidate_pool(cell: CellSpec, seed: int, insertion_round: int, k: int) -> torch.Tensor:
    generator = make_generator(seed + POOL_SEED_OFFSET + insertion_round * 100 + k)
    return torch.stack(
        [torchhd.random(k, cell.dimensions, "MAP", generator=generator) for _ in range(FACTOR_COUNT)],
        dim=0,
    )


def initial_codebook(cell: CellSpec, seed: int) -> torch.Tensor:
    config = BaselineConfig(
        dimensions=cell.dimensions,
        num_factors=FACTOR_COUNT,
        domain_size=cell.final_domain_size,
        structured_distractor_count=0,
        max_iterations=MAX_ITERATIONS,
        stable_patience=STABLE_PATIENCE,
    )
    return generate_domains(config, make_generator(seed))


def hamming_distance(candidate: torch.Tensor, existing: torch.Tensor) -> torch.Tensor:
    candidate_bits = candidate.gt(0)
    existing_bits = existing.gt(0)
    return (candidate_bits.unsqueeze(0) != existing_bits).sum(dim=-1).to(dtype=torch.int64)


def pairwise_hamming_summary(domains: torch.Tensor) -> dict[str, float]:
    distances: list[int] = []
    for factor_index in range(domains.size(0)):
        domain = domains[factor_index]
        for left in range(domain.size(0)):
            for right in range(left + 1, domain.size(0)):
                distances.append(int(hamming_distance(domain[left], domain[right].unsqueeze(0))[0].item()))
    return {
        "pairwise_hamming_min": float(min(distances)) if distances else 0.0,
        "pairwise_hamming_mean": float(statistics.fmean(distances)) if distances else 0.0,
        "pairwise_hamming_p10": float(sorted(distances)[max(0, len(distances) // 10 - 1)]) if distances else 0.0,
    }


def decode_tuple(domains: torch.Tensor, target_indices: torch.Tensor) -> DecodeMetrics:
    observation = bind_sequence(factors_from_indices(domains, target_indices))
    estimates = build_initial_estimates(domains)
    previous_prediction: torch.Tensor | None = None
    stable_iterations = 0
    stable_prediction = False
    decoded: dict[str, torch.Tensor] | None = None
    similarities: torch.Tensor | None = None
    start = time.perf_counter()
    current_estimates = estimates.clone()
    for iteration in range(1, MAX_ITERATIONS + 1):
        current_estimates = torchhd.resonator(observation, current_estimates, domains)
        similarities = cosine_similarity_matrix(current_estimates, domains)
        decoded = decode_top_candidates(similarities)
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
    if decoded is None or similarities is None:
        raise RuntimeError("Decode produced no output.")
    predicted = decoded["top1_indices"].detach().cpu().to(dtype=torch.long)
    predicted_factors = factors_from_indices(domains, predicted)
    reconstruction = bind_sequence(predicted_factors)
    exact = bool(torch.equal(predicted, target_indices.cpu()))
    verified = bool(torch.equal(reconstruction, observation.cpu()))
    per_factor = tuple(bool(value) for value in predicted.eq(target_indices.cpu()).tolist())
    margins = [float(value) for value in decoded["margins"].tolist()]
    return DecodeMetrics(
        predicted_indices=tuple(int(value) for value in predicted.tolist()),
        exact_recovery=exact,
        verified_reconstruction=verified,
        stable_prediction=stable_prediction,
        per_factor_recovery=per_factor,
        min_margin=min(margins),
        mean_margin=float(statistics.fmean(margins)),
        iterations=iteration,
        decode_latency_sec=latency,
    )


def random_tuple(seed: int, factor_count: int, domain_size: int) -> tuple[int, ...]:
    generator = make_generator(seed)
    return tuple(int(torch.randint(0, domain_size, (1,), generator=generator).item()) for _ in range(factor_count))


def old_only_workload(seed: int, count: int, domain_size: int) -> list[tuple[int, ...]]:
    return [random_tuple(seed + index, FACTOR_COUNT, domain_size) for index in range(count)]


def certification_workload(
    seed: int,
    count: int,
    base_domain_size: int,
    factor_index: int,
    new_index: int,
    hard_templates: list[tuple[int, ...]],
) -> list[tuple[int, ...]]:
    half = max(1, count // 2)
    rows: list[tuple[int, ...]] = []
    for index in range(half):
        values = list(random_tuple(seed + index, FACTOR_COUNT, base_domain_size))
        values[factor_index] = new_index
        rows.append(tuple(values))
    for index in range(count - half):
        if hard_templates:
            template = list(hard_templates[index % len(hard_templates)])
            template[factor_index] = new_index
            rows.append(tuple(template))
        else:
            values = list(random_tuple(seed + 10_000 + index, FACTOR_COUNT, base_domain_size))
            values[factor_index] = new_index
            rows.append(tuple(values))
    return rows


def evaluate_candidate_score(domains: torch.Tensor, tuples: list[tuple[int, ...]], candidate_index: int) -> CandidateScore:
    decodes = [decode_tuple(domains, torch.tensor(item, dtype=torch.long)) for item in tuples]
    silent_wrong = sum(1 for decode in decodes if decode.stable_prediction and not decode.exact_recovery)
    accepted = sum(1 for decode in decodes if decode.stable_prediction)
    exact_factor_total = sum(sum(1 for flag in decode.per_factor_recovery if flag) for decode in decodes)
    total_factor_slots = max(1, len(decodes) * FACTOR_COUNT)
    return CandidateScore(
        candidate_index=candidate_index,
        silent_wrong_count=silent_wrong,
        exact_factor_recovery_rate=exact_factor_total / total_factor_slots,
        verified_reconstruction_rate=sum(1 for decode in decodes if decode.verified_reconstruction) / max(1, len(decodes)),
        mean_min_margin=float(statistics.fmean(decode.min_margin for decode in decodes)),
        mean_iterations=float(statistics.fmean(decode.iterations for decode in decodes)),
        mean_latency_sec=float(statistics.fmean(decode.decode_latency_sec for decode in decodes)),
        accepted_outputs=accepted,
        total_trials=len(decodes),
    )


def select_distance_candidate(existing: torch.Tensor, candidates: torch.Tensor) -> int:
    best_index = 0
    best_key: tuple[int, int] | None = None
    for candidate_index in range(candidates.size(0)):
        candidate = candidates[candidate_index]
        min_distance = int(hamming_distance(candidate, existing).min().item())
        key = (min_distance, -candidate_index)
        if best_key is None or key > best_key:
            best_key = key
            best_index = candidate_index
    return best_index


def choose_certified_candidate(
    domains: torch.Tensor,
    current_size: int,
    candidates: torch.Tensor,
    factor_index: int,
    seed: int,
    hard_templates: list[tuple[int, ...]],
    count: int,
) -> SelectionOutcome:
    base_domain_size = current_size
    new_index = current_size
    scores: list[CandidateScore] = []
    for candidate_index in range(candidates.size(0)):
        augmented = domains[:, : current_size + 1].clone()
        augmented[factor_index, new_index] = candidates[candidate_index]
        tuples = certification_workload(seed, count, base_domain_size, factor_index, new_index, hard_templates)
        scores.append(evaluate_candidate_score(augmented, tuples, candidate_index))
    passing = [score for score in scores if score.passes_gate]
    if not passing:
        return SelectionOutcome(
            selected_candidate_index=None,
            selected_by_rule=NO_COMMIT,
            no_commit=True,
            candidate_scores=tuple(scores),
            certification_calls=len(scores) * count,
        )
    selected = max(
        passing,
        key=lambda score: (
            score.exact_factor_recovery_rate,
            score.verified_reconstruction_rate,
            score.mean_min_margin,
            -score.mean_iterations,
            -score.candidate_index,
        ),
    )
    return SelectionOutcome(
        selected_candidate_index=selected.candidate_index,
        selected_by_rule="lexicographic_decoder_certification",
        no_commit=False,
        candidate_scores=tuple(scores),
        certification_calls=len(scores) * count,
    )


def choose_shuffled_candidate(certified: SelectionOutcome, seed: int) -> SelectionOutcome:
    indices = list(range(len(certified.candidate_scores)))
    rng = random.Random(seed)
    shuffled_targets = indices[:]
    rng.shuffle(shuffled_targets)
    remapped = [
        CandidateScore(candidate_index=score.candidate_index, **{k: v for k, v in asdict(certified.candidate_scores[source]).items() if k != "candidate_index"})
        for score, source in zip(certified.candidate_scores, shuffled_targets, strict=True)
    ]
    passing = [score for score in remapped if score.passes_gate]
    if not passing:
        return SelectionOutcome(
            selected_candidate_index=None,
            selected_by_rule=NO_COMMIT,
            no_commit=True,
            candidate_scores=tuple(remapped),
            certification_calls=certified.certification_calls,
            shuffled_mapping=tuple(shuffled_targets),
        )
    selected = max(
        passing,
        key=lambda score: (
            score.exact_factor_recovery_rate,
            score.verified_reconstruction_rate,
            score.mean_min_margin,
            -score.mean_iterations,
            -score.candidate_index,
        ),
    )
    return SelectionOutcome(
        selected_candidate_index=selected.candidate_index,
        selected_by_rule="shuffled_decoder_certification_control",
        no_commit=False,
        candidate_scores=tuple(remapped),
        certification_calls=certified.certification_calls,
        shuffled_mapping=tuple(shuffled_targets),
    )


def commit_candidates(domains: torch.Tensor, current_size: int, chosen: list[torch.Tensor]) -> tuple[torch.Tensor, int]:
    updated = domains.clone()
    for factor_index in range(FACTOR_COUNT):
        updated[factor_index, current_size] = chosen[factor_index]
    return updated, current_size + 1


def evaluate_workload(domains: torch.Tensor, tuples: list[tuple[int, ...]], workload_kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in tuples:
        decode = decode_tuple(domains, torch.tensor(item, dtype=torch.long))
        accepted = decode.stable_prediction
        rows.append(
            {
                "workload_kind": workload_kind,
                "target_indices": list(item),
                "predicted_indices": list(decode.predicted_indices),
                "exact_recovery": decode.exact_recovery,
                "verified_reconstruction": decode.verified_reconstruction,
                "stable_prediction": decode.stable_prediction,
                "silent_wrong": accepted and not decode.exact_recovery,
                "min_margin": decode.min_margin,
                "iterations": decode.iterations,
                "decode_latency_sec": decode.decode_latency_sec,
                "accepted": accepted,
            }
        )
    return rows


def hard_templates_from_rows(rows: list[dict[str, Any]], limit: int) -> list[tuple[int, ...]]:
    hard = sorted(rows, key=lambda row: (row["exact_recovery"], row["min_margin"]))[:limit]
    return [tuple(int(value) for value in row["target_indices"]) for row in hard]


def summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_rows = [row for row in rows if row["accepted"]]
    exact_rows = [row for row in rows if row["exact_recovery"]]
    return {
        "trials": len(rows),
        "exact_recovery_rate": len(exact_rows) / max(1, len(rows)),
        "verified_reconstruction_rate": sum(1 for row in rows if row["verified_reconstruction"]) / max(1, len(rows)),
        "silent_wrong_acceptance_rate": sum(1 for row in rows if row["silent_wrong"]) / max(1, len(rows)),
        "conditional_risk_among_accepted": (
            sum(1 for row in accepted_rows if not row["exact_recovery"]) / len(accepted_rows)
            if accepted_rows
            else 0.0
        ),
        "accepted_coverage": len(accepted_rows) / max(1, len(rows)),
        "mean_min_margin": float(statistics.fmean(row["min_margin"] for row in rows)) if rows else 0.0,
        "mean_iterations": float(statistics.fmean(row["iterations"] for row in rows)) if rows else 0.0,
        "mean_decode_latency_sec": float(statistics.fmean(row["decode_latency_sec"] for row in rows)) if rows else 0.0,
    }


def execute_smoke_cell(cell: CellSpec, codebook_seed: int, k: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    base_domains = initial_codebook(cell, codebook_seed)
    arm_domains = {arm_id: base_domains.clone() for arm_id in ALLOWED_ARMS}
    arm_sizes = {arm_id: cell.initial_domain_size for arm_id in ALLOWED_ARMS}
    hard_bank = {arm_id: [] for arm_id in ALLOWED_ARMS}

    for insertion_round in range(cell.insertion_rounds):
        pool = candidate_pool(cell, codebook_seed, insertion_round, k)
        for arm_id in ALLOWED_ARMS:
            current = arm_domains[arm_id]
            current_size = arm_sizes[arm_id]
            chosen_vectors: list[torch.Tensor] = []
            selection_rows: list[dict[str, Any]] = []
            all_committed = True
            for factor_index in range(FACTOR_COUNT):
                candidates = pool[factor_index]
                if arm_id == ARM_RANDOM_FIRST:
                    selection = SelectionOutcome(0, "first_candidate", False, tuple(), 0)
                elif arm_id == ARM_DISTANCE_MAXMIN:
                    chosen = select_distance_candidate(current[factor_index, :current_size], candidates)
                    selection = SelectionOutcome(chosen, "distance_maxmin", False, tuple(), 0)
                elif arm_id == ARM_DECODER_CERTIFIED:
                    selection = choose_certified_candidate(
                        current,
                        current_size,
                        candidates,
                        factor_index,
                        codebook_seed + CERT_SEED_OFFSET + insertion_round * 100 + factor_index,
                        hard_bank[arm_id],
                        cell.certification_tuples_per_factor,
                    )
                else:
                    certified = choose_certified_candidate(
                        current,
                        current_size,
                        candidates,
                        factor_index,
                        codebook_seed + CERT_SEED_OFFSET + insertion_round * 100 + factor_index,
                        hard_bank[ARM_DECODER_CERTIFIED] if hard_bank[ARM_DECODER_CERTIFIED] else hard_bank[arm_id],
                        cell.certification_tuples_per_factor,
                    )
                    selection = choose_shuffled_candidate(
                        certified,
                        codebook_seed + SHUFFLE_SEED_OFFSET + insertion_round * 100 + factor_index,
                    )
                if selection.no_commit or selection.selected_candidate_index is None:
                    all_committed = False
                else:
                    chosen_vectors.append(candidates[selection.selected_candidate_index].clone())
                selection_rows.append(
                    {
                        "record_type": "candidate_selection",
                        "cell_id": cell.cell_id,
                        "codebook_seed": codebook_seed,
                        "k": k,
                        "arm_id": arm_id,
                        "insertion_round": insertion_round,
                        "factor_index": factor_index,
                        "domain_size_before": current_size,
                        "selected_candidate_index": selection.selected_candidate_index,
                        "selected_by_rule": selection.selected_by_rule,
                        "no_commit": selection.no_commit,
                        "certification_calls": selection.certification_calls,
                        "candidate_scores": [asdict(score) for score in selection.candidate_scores],
                        "shuffled_mapping": list(selection.shuffled_mapping) if selection.shuffled_mapping is not None else None,
                    }
                )
            raw_rows.extend(selection_rows)
            if all_committed and len(chosen_vectors) == FACTOR_COUNT:
                arm_domains[arm_id], arm_sizes[arm_id] = commit_candidates(current, current_size, chosen_vectors)
                commit_state = "committed"
            else:
                commit_state = NO_COMMIT
            new_size = arm_sizes[arm_id]
            old_only_tuples = old_only_workload(
                codebook_seed + VALIDATION_SEED_OFFSET + insertion_round * 100,
                cell.old_only_tuples,
                current_size,
            )
            final_new_index = new_size - 1
            new_atom_tuples: list[tuple[int, ...]] = []
            if commit_state == "committed":
                for factor_index in range(FACTOR_COUNT):
                    new_atom_tuples.extend(
                        certification_workload(
                            codebook_seed + FINAL_SEED_OFFSET + insertion_round * 100 + factor_index,
                            cell.final_tuples_per_factor,
                            new_size,
                            factor_index,
                            final_new_index,
                            hard_bank[arm_id],
                        )
                    )
            active_domains = arm_domains[arm_id][:, :new_size]
            old_rows = evaluate_workload(active_domains, old_only_tuples, WORKLOAD_OLD_ONLY)
            new_rows = evaluate_workload(active_domains, new_atom_tuples, WORKLOAD_NEW_ATOM) if new_atom_tuples else []
            final_rows = old_rows + new_rows
            hard_bank[arm_id] = hard_templates_from_rows(old_rows, cell.hard_templates)
            regression = summary_from_rows(old_rows)
            final_summary = summary_from_rows(final_rows)
            summary_row = {
                "schema_version": SCHEMA_VERSION,
                "cell_id": cell.cell_id,
                "dimensions": cell.dimensions,
                "codebook_seed": codebook_seed,
                "k": k,
                "arm_id": arm_id,
                "insertion_round": insertion_round,
                "commit_state": commit_state,
                "domain_size_before": current_size,
                "domain_size_after": new_size,
                "old_atom_regression_exact_recovery": regression["exact_recovery_rate"],
                "final_exact_recovery_rate": final_summary["exact_recovery_rate"],
                "final_verified_reconstruction_rate": final_summary["verified_reconstruction_rate"],
                "final_silent_wrong_acceptance_rate": final_summary["silent_wrong_acceptance_rate"],
                "final_conditional_risk": final_summary["conditional_risk_among_accepted"],
                "final_accepted_coverage": final_summary["accepted_coverage"],
                "mean_decode_latency_sec": final_summary["mean_decode_latency_sec"],
                "pairwise_hamming_min": pairwise_hamming_summary(active_domains)["pairwise_hamming_min"],
                "pairwise_hamming_mean": pairwise_hamming_summary(active_domains)["pairwise_hamming_mean"],
                "construction_cost_sec": sum(row["certification_calls"] for row in selection_rows) * final_summary["mean_decode_latency_sec"],
            }
            summary_rows.append(summary_row)
            for row in final_rows:
                raw_rows.append(
                    {
                        "record_type": "evaluation_trial",
                        "schema_version": SCHEMA_VERSION,
                        "cell_id": cell.cell_id,
                        "dimensions": cell.dimensions,
                        "codebook_seed": codebook_seed,
                        "k": k,
                        "arm_id": arm_id,
                        "insertion_round": insertion_round,
                        "domain_size_after": new_size,
                        "commit_state": commit_state,
                        **row,
                    }
                )
    return raw_rows, summary_rows


def build_execution_plan(protocol: dict[str, Any]) -> str:
    executed_cells = [cell for cell in protocol["cells"] if cell["execute_in_stage"]]
    active_specs = [cell for cell in CELLS if cell.execute_in_stage]
    codebook_seeds = sum(cell.codebook_seed_count for cell in active_specs)
    decoder_calls_estimate = sum(
        cell.codebook_seed_count
        * len(K_VALUES)
        * cell.insertion_rounds
        * FACTOR_COUNT
        * K_VALUES[-1]
        * cell.certification_tuples_per_factor
        for cell in active_specs
    )
    rows_estimate = decoder_calls_estimate + codebook_seeds * len(ALLOWED_ARMS) * 16
    lines = [
        f"# {TASK_NAME} execution plan",
        "",
        f"- starting_commit: `{STARTING_COMMIT}`",
        f"- selected_device: `cpu`",
        f"- executed_cells: `{len(executed_cells)}`",
        f"- codebook_seeds: `{codebook_seeds}`",
        f"- arms: `{len(ALLOWED_ARMS)}`",
        f"- K_values: `{list(K_VALUES)}`",
        f"- estimated_decoder_calls: `{decoder_calls_estimate}`",
        f"- estimated_trial_rows: `{rows_estimate}`",
        f"- long_run_authorized: `{EXECUTE_LONG_RUN}`",
        "",
        "This stage executes only a tiny deterministic smoke run because Level 3.5b confirmatory closure is still open.",
    ]
    return "\n".join(lines) + "\n"


def build_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} audit",
        "",
        "- Verdict: `COMPOSE`",
        "- Status: `PROTOTYPE / DEVELOPMENT_ONLY / NO_PRODUCTION_CLAIM`",
        "",
        "## Prior art",
        "",
    ]
    for item in audit["anti_nih_findings"]:
        lines.append(
            f"- `{item['family']}`: `{item['verdict']}` with estimated coverage `{item['coverage']:.1f}`. {item['notes']}"
        )
    lines.extend(
        [
            "",
            "## Why not scratch",
            "",
        ]
    )
    for item in audit["why_not_scratch"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Minimal path",
            "",
            "- Reuse the existing MAP/TorchHD resonator harness and factor-domain generation utilities.",
            "- Add only a thin candidate-pool, certification, shuffled-control, and split-aware smoke runner.",
            "- Freeze tiny smoke cells now; defer any long development run until Level 3.5b confirmatory closure is complete.",
            "",
            "## AGI claim gate",
            "",
            "- Claim: `operation-aware online codeword admission for an open-world VSA codebook, using the actual blinded factor decoder and explicit non-commit`.",
            "- Authority boundary: decoder sees only lawful read-time information; verifier sees ground truth only after decode.",
            "- Failure criterion: if decoder-certified selection fails against distance-only or shuffled budget-matched control on unseen development evaluation, block the line.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_protocol_markdown(protocol: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} protocol",
        "",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        f"- Starting commit: `{protocol['starting_commit']}`",
        f"- Long run authorized: `{protocol['long_run_authorized']}`",
        f"- Held-out execution allowed: `{protocol['heldout_execution_allowed']}`",
        "",
        "## Frozen substrate",
        "",
        f"- Family: `{protocol['substrate']['family']}`",
        f"- Decoder: `{protocol['substrate']['decoder']}`",
        f"- Task contract: `{protocol['substrate']['task_contract']}`",
        f"- Factor count: `{protocol['substrate']['factor_count']}`",
        f"- Max iterations: `{protocol['substrate']['max_iterations']}`",
        f"- Stable patience: `{protocol['substrate']['stable_patience']}`",
        f"- Corruption contract: `{protocol['substrate']['corruption_contract']}`",
        "",
        "## Frozen cells",
        "",
    ]
    for cell in protocol["cells"]:
        lines.append(
            f"- `{cell['cell_id']}`: D=`{cell['dimensions']}`, initial M=`{cell['initial_domain_size']}`, final M=`{cell['final_domain_size']}`, seeds `{cell['seed_range']['start']}..{cell['seed_range']['start'] + cell['seed_range']['count'] - 1}`."
        )
    lines.extend(
        [
            "",
            "## Arms",
            "",
        ]
    )
    for arm in protocol["arms"]:
        lines.append(f"- `{arm}`")
    lines.extend(
        [
            "",
            "## Split separation",
            "",
            "- Certification drives candidate selection only.",
            "- Development validation and final development evaluation remain seed-disjoint from certification.",
            "- Candidate pool, certification, validation, final evaluation, and shuffle controls use frozen offset namespaces.",
            "",
            "## Selection rule",
            "",
        ]
    )
    for rule in protocol["selection_policy"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## Scope limit",
            "",
            f"- {protocol['scope_limit_reason']}",
        ]
    )
    return "\n".join(lines) + "\n"


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
                "mean_final_exact_recovery_rate": float(statistics.fmean(row["final_exact_recovery_rate"] for row in batch)),
                "mean_final_verified_reconstruction_rate": float(statistics.fmean(row["final_verified_reconstruction_rate"] for row in batch)),
                "mean_old_atom_regression_exact_recovery": float(statistics.fmean(row["old_atom_regression_exact_recovery"] for row in batch)),
                "mean_final_conditional_risk": float(statistics.fmean(row["final_conditional_risk"] for row in batch)),
                "mean_final_accepted_coverage": float(statistics.fmean(row["final_accepted_coverage"] for row in batch)),
                "mean_construction_cost_sec": float(statistics.fmean(row["construction_cost_sec"] for row in batch)),
            }
        )
    lookup = {row["arm_id"]: row for row in arm_rows}
    if ARM_DECODER_CERTIFIED not in lookup or ARM_SHUFFLED_CONTROL not in lookup:
        scientific = "INCONCLUSIVE_REQUIRES_MORE_POWER"
        claim = "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED"
    else:
        c_row = lookup[ARM_DECODER_CERTIFIED]
        b_row = lookup[ARM_DISTANCE_MAXMIN]
        d_row = lookup[ARM_SHUFFLED_CONTROL]
        if c_row["mean_final_conditional_risk"] > 0.0:
            scientific = "BLOCK_DECODER_CERTIFICATION_LINE"
            claim = "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED"
        elif c_row["mean_final_exact_recovery_rate"] > b_row["mean_final_exact_recovery_rate"] and c_row["mean_final_exact_recovery_rate"] > d_row["mean_final_exact_recovery_rate"]:
            scientific = "PARTIAL_DECODER_CERTIFICATION_EFFECT"
            claim = "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_PARTIAL"
        else:
            scientific = "INCONCLUSIVE_REQUIRES_MORE_POWER"
            claim = "DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED"
    return {
        "build_verdict": VERDICT_PROTOTYPE,
        "scientific_verdict": scientific,
        "claim_state": claim,
        "execution_scope": "tiny_smoke_only",
        "arm_summary": arm_rows,
        "heldout_execution_count": 0,
    }


def build_report(protocol: dict[str, Any], summary: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"- Build verdict: `{summary['build_verdict']}`",
        f"- Scientific verdict: `{summary['scientific_verdict']}`",
        f"- Claim state: `{summary['claim_state']}`",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        "",
        "## Scope note",
        "",
        "This report covers only a tiny deterministic smoke run. A full development benchmark remains deferred until Level 3.5b confirmatory closure is complete.",
        "",
        "## Arm snapshot",
        "",
    ]
    for row in summary["arm_summary"]:
        lines.append(
            f"- `{row['arm_id']}`: exact `{row['mean_final_exact_recovery_rate']:.4f}`, "
            f"verified `{row['mean_final_verified_reconstruction_rate']:.4f}`, "
            f"risk `{row['mean_final_conditional_risk']:.4f}`, "
            f"old-only `{row['mean_old_atom_regression_exact_recovery']:.4f}`."
        )
    return "\n".join(lines) + "\n"


def run_decoder_certified_codebook(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs"
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    protocol = build_protocol(repo_root)
    audit = dependency_audit(repo_root)
    plan_text = build_execution_plan(protocol)
    print(plan_text, flush=True)

    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for cell in CELLS:
        if not cell.execute_in_stage:
            continue
        for codebook_seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count):
            for k in K_VALUES:
                print(f"{PROGRESS_PREFIX} cell={cell.cell_id} seed={codebook_seed} k={k}", flush=True)
                cell_raw, cell_summary = execute_smoke_cell(cell, codebook_seed, k)
                raw_rows.extend(cell_raw)
                summary_rows.extend(cell_summary)

    summary = summarize(summary_rows)
    report = build_report(protocol, summary)
    audit_markdown = build_audit_markdown(audit)
    protocol_markdown = build_protocol_markdown(protocol)

    write_text(docs_dir / "LEVEL3_DECODER_CERTIFIED_CODEBOOK_AUDIT.md", audit_markdown)
    write_text(docs_dir / "LEVEL3_DECODER_CERTIFIED_CODEBOOK_PROTOCOL.md", protocol_markdown)
    write_text(results_dir / "execution_plan.md", plan_text)
    write_text(results_dir / "frozen_protocol.yaml", "\n".join(yaml_lines(protocol)) + "\n")
    write_json(results_dir / "summary.json", summary | {"protocol_hash": protocol["protocol_hash"], "seed_fresh": seeds_are_fresh(repo_root)})
    write_text(results_dir / "report.md", report)
    write_json(results_dir / "dependency_audit.json", audit)
    write_json(results_dir / "environment.json", environment_snapshot())
    write_jsonl(results_dir / "raw_trial_records.jsonl", raw_rows)

    return {
        "protocol": protocol,
        "summary": summary,
        "raw_rows": raw_rows,
        "summary_rows": summary_rows,
    }
