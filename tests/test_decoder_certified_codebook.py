from __future__ import annotations

import json
from pathlib import Path

import torch

from cgrn_hsr.decoder_certified_codebook import (
    ALLOWED_ARMS,
    ARM_DECODER_CERTIFIED,
    ARM_DISTANCE_MAXMIN,
    ARM_RANDOM_FIRST,
    ARM_SHUFFLED_CONTROL,
    CELLS,
    CERT_SEED_OFFSET,
    FINAL_SEED_OFFSET,
    K_VALUES,
    LEVEL35_V4_SHA256,
    NO_COMMIT,
    POOL_SEED_OFFSET,
    SHUFFLE_SEED_OFFSET,
    VALIDATION_SEED_OFFSET,
    build_protocol,
    candidate_pool,
    certification_workload,
    choose_certified_candidate,
    choose_shuffled_candidate,
    decode_tuple,
    execute_smoke_cell,
    initial_codebook,
    prior_known_seed_set,
    seeds_are_fresh,
    stage_seed_set,
)

ROOT = Path(__file__).resolve().parents[1]


def _score_without_latency(score: object) -> dict[str, object]:
    payload = score.__dict__.copy()
    payload.pop("mean_latency_sec", None)
    return payload


def test_same_seed_same_candidate_pool() -> None:
    cell = CELLS[0]
    first = candidate_pool(cell, cell.codebook_seed_start, 0, 4)
    second = candidate_pool(cell, cell.codebook_seed_start, 0, 4)
    assert torch.equal(first, second)


def test_same_input_same_selected_candidate() -> None:
    cell = CELLS[1]
    domains = initial_codebook(cell, cell.codebook_seed_start)
    pool = candidate_pool(cell, cell.codebook_seed_start, 0, 4)
    hard_templates = [(0, 0, 0)]
    first = choose_certified_candidate(
        domains,
        cell.initial_domain_size,
        pool[0],
        0,
        cell.codebook_seed_start + CERT_SEED_OFFSET,
        hard_templates,
        cell.certification_tuples_per_factor,
    )
    second = choose_certified_candidate(
        domains,
        cell.initial_domain_size,
        pool[0],
        0,
        cell.codebook_seed_start + CERT_SEED_OFFSET,
        hard_templates,
        cell.certification_tuples_per_factor,
    )
    assert first.selected_candidate_index == second.selected_candidate_index
    assert [_score_without_latency(score) for score in first.candidate_scores] == [
        _score_without_latency(score) for score in second.candidate_scores
    ]


def test_k1_collapses_to_random_behavior() -> None:
    cell = CELLS[0]
    raw_rows, _ = execute_smoke_cell(cell, cell.codebook_seed_start, 1)
    selections = [
        row
        for row in raw_rows
        if row["record_type"] == "candidate_selection"
        and row["arm_id"] in {ARM_RANDOM_FIRST, ARM_DECODER_CERTIFIED, ARM_SHUFFLED_CONTROL}
    ]
    assert selections
    for row in selections:
        if row["selected_candidate_index"] is not None:
            assert row["selected_candidate_index"] == 0


def test_decoder_never_receives_ground_truth_factor_identities() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "decoder_certified_codebook.py").read_text(encoding="utf-8")
    start = source.index("def decode_tuple(")
    end = source.index("def random_tuple(")
    snippet = source[start:end]
    assert "ground_truth" not in snippet
    assert "torchhd.resonator" in snippet


def test_distance_arm_uses_no_decoder_calls() -> None:
    cell = CELLS[0]
    raw_rows, _ = execute_smoke_cell(cell, cell.codebook_seed_start, 4)
    distance_rows = [row for row in raw_rows if row["record_type"] == "candidate_selection" and row["arm_id"] == ARM_DISTANCE_MAXMIN]
    assert distance_rows
    assert all(row["certification_calls"] == 0 for row in distance_rows)


def test_shuffled_arm_preserves_compute_but_breaks_mapping() -> None:
    cell = CELLS[1]
    domains = initial_codebook(cell, cell.codebook_seed_start)
    pool = candidate_pool(cell, cell.codebook_seed_start, 0, 4)
    certified = choose_certified_candidate(
        domains,
        cell.initial_domain_size,
        pool[0],
        0,
        cell.codebook_seed_start + CERT_SEED_OFFSET,
        [],
        cell.certification_tuples_per_factor,
    )
    shuffled = choose_shuffled_candidate(certified, cell.codebook_seed_start + SHUFFLE_SEED_OFFSET)
    assert shuffled.certification_calls == certified.certification_calls
    assert shuffled.shuffled_mapping is not None


def test_certification_and_validation_seeds_are_disjoint() -> None:
    base_seeds = {
        seed
        for cell in CELLS
        for seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count)
    }
    pool_seeds = {seed + POOL_SEED_OFFSET for seed in base_seeds}
    cert_seeds = {seed + CERT_SEED_OFFSET for seed in base_seeds}
    validation_seeds = {seed + VALIDATION_SEED_OFFSET for seed in base_seeds}
    final_seeds = {seed + FINAL_SEED_OFFSET for seed in base_seeds}
    shuffle_seeds = {seed + SHUFFLE_SEED_OFFSET for seed in base_seeds}
    seed_groups = (base_seeds, pool_seeds, cert_seeds, validation_seeds, final_seeds, shuffle_seeds)
    for left_index, left in enumerate(seed_groups):
        for right in seed_groups[left_index + 1 :]:
            assert left.isdisjoint(right)


def test_old_atom_regression_workload_is_executed() -> None:
    cell = CELLS[0]
    raw_rows, _ = execute_smoke_cell(cell, cell.codebook_seed_start, 1)
    assert any(row["record_type"] == "evaluation_trial" and row["workload_kind"] == "old_only" for row in raw_rows)


def test_no_official_heldout_seed_overlap() -> None:
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_no_commit_is_typed() -> None:
    assert NO_COMMIT == "NO_COMMIT_AT_FIXED_BUDGET"


def test_metrics_and_protocol_serialize_deterministically() -> None:
    first = build_protocol(ROOT)
    second = build_protocol(ROOT)
    assert first == second
    assert first["protocol_hash"] == second["protocol_hash"]


def test_no_bcf_or_linear_code_dependency_introduced() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "decoder_certified_codebook.py").read_text(encoding="utf-8")
    assert "competitors.ibm_bcf_audit" not in source
    assert "level3_3_neco_reproduction" not in source
    assert "linear_code" not in source


def test_stage_respects_level35_frozen_hash() -> None:
    assert build_protocol(ROOT)["level35_frozen_artifacts_unchanged"] is True
    assert (
        __import__("hashlib").sha256((ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").read_bytes()).hexdigest().upper()
        == LEVEL35_V4_SHA256
    )


def test_candidate_pool_sizes_follow_protocol_k_values() -> None:
    cell = CELLS[0]
    for k in K_VALUES:
        pool = candidate_pool(cell, cell.codebook_seed_start, 0, k)
        assert pool.shape == (3, k, cell.dimensions)


def test_certification_workload_places_new_atom_in_target_factor() -> None:
    rows = certification_workload(1234, 4, 10, 1, 10, [(1, 2, 3)])
    assert rows
    assert all(row[1] == 10 for row in rows)


def test_decode_tuple_returns_deterministic_fields() -> None:
    cell = CELLS[0]
    domains = initial_codebook(cell, cell.codebook_seed_start)
    target = torch.tensor([0, 1, 2], dtype=torch.long)
    first = decode_tuple(domains, target)
    second = decode_tuple(domains, target)
    assert first.predicted_indices == second.predicted_indices
    assert first.exact_recovery == second.exact_recovery
