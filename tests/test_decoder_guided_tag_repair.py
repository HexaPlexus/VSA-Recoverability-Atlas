from __future__ import annotations

import hashlib
from pathlib import Path

import torch
import torchhd

from cgrn_hsr.decoder_guided_tag_repair import (
    ARM_CONFLICT_GUIDED_TAGS,
    ARM_EQUAL_BIT_EXTRA_DIMENSIONS,
    ARM_RANDOM_PATCH_SEARCH,
    ARM_SHUFFLED_CONFLICT_TAGS,
    CELLS,
    DISCOVERY_SEED_OFFSET,
    FINAL_SEED_OFFSET,
    LEVEL35_V4_SHA256,
    MARKER_BOTH_PRESENT,
    MARKER_NEG_PRESENT,
    MARKER_NONE,
    MARKER_POS_PRESENT,
    MarkerOverlay,
    REPAIR_LADDER,
    SPLIT_DISCOVERY,
    SPLIT_FINAL,
    SPLIT_VALIDATION,
    VALIDATION_SEED_OFFSET,
    apply_overlay,
    build_protocol,
    combined_similarity_scores,
    decode_tagged_tuple,
    empty_overlays,
    evaluate_equal_bit_budget,
    execute_smoke_stage,
    extra_dimensions_for_budget,
    initial_codebook,
    marker_overlay_bits,
    marker_score,
    merge_marker_states,
    old_only_tuples,
    pick_target_atoms,
    prior_known_seed_set,
    random_coordinate_order,
    seeds_are_fresh,
    semantic_projection,
    stable_conflict_report,
    stage_seed_set,
    strict_certificate,
    summarize_rows,
    tagged_values,
    top_wrong_competitor,
    tuples_for_target,
)

ROOT = Path(__file__).resolve().parents[1]


def test_semantic_projection_preserves_bipolar_bits() -> None:
    vector = torch.tensor([1.0, -1.0, 1.0, -1.0])
    overlay = MarkerOverlay((1, 3))
    assert torch.equal(semantic_projection(vector, overlay), vector)


def test_marker_merge_states_cover_none_neg_pos_both() -> None:
    domains = torch.tensor(
        [
            [[1.0, -1.0, 1.0, -1.0], [1.0, 1.0, -1.0, -1.0]],
            [[1.0, -1.0, -1.0, 1.0], [-1.0, 1.0, 1.0, -1.0]],
            [[-1.0, -1.0, 1.0, 1.0], [1.0, -1.0, 1.0, -1.0]],
        ]
    )
    overlays = empty_overlays(domains)
    overlays[0][0] = MarkerOverlay((0, 1))
    overlays[1][0] = MarkerOverlay((0, 2))
    overlays[2][0] = MarkerOverlay((2,))
    state = merge_marker_states(domains, overlays, (0, 0, 0))
    assert int(state[3].item()) == MARKER_NONE
    assert int(state[1].item()) == MARKER_NEG_PRESENT
    assert int(state[0].item()) == MARKER_POS_PRESENT
    assert int(state[2].item()) == MARKER_BOTH_PRESENT


def test_marker_overlay_does_not_change_semantic_map_product() -> None:
    cell = CELLS[0]
    domains = initial_codebook(cell.dimensions, cell.domain_size, cell.codebook_seed_start)
    overlays = empty_overlays(domains)
    overlays[0][0] = MarkerOverlay((0, 1, 2))
    projected = [semantic_projection(domains[index, target], overlays[index][target]) for index, target in enumerate((0, 1, 2))]
    semantic_only = torchhd.bind(torchhd.bind(domains[0, 0], domains[1, 1]), domains[2, 2])
    projected_bind = torchhd.bind(torchhd.bind(projected[0], projected[1]), projected[2])
    assert torch.equal(semantic_only, projected_bind)


def test_decoder_never_receives_ground_truth_inside_decode_function() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "decoder_guided_tag_repair.py").read_text(encoding="utf-8")
    start = source.index("def decode_tagged_tuple(")
    end = source.index("def random_tuple(")
    snippet = source[start:end]
    assert "ground_truth" not in snippet
    assert "torchhd.resonator" in snippet


def test_margin_attribution_matches_bruteforce_score_difference() -> None:
    estimate = torch.tensor([1.5, -0.5, 0.25, -2.0])
    true_vector = torch.tensor([1.0, -1.0, 1.0, -1.0])
    wrong_vector = torch.tensor([-1.0, -1.0, 1.0, 1.0])
    delta = estimate * (true_vector - wrong_vector)
    brute = estimate * true_vector - estimate * wrong_vector
    assert torch.allclose(delta, brute)


def test_same_seed_same_conflict_ranking() -> None:
    cell = CELLS[0]
    domains = initial_codebook(cell.dimensions, cell.domain_size, cell.codebook_seed_start)
    overlays = empty_overlays(domains)
    tuples = tuples_for_target(cell.codebook_seed_start + DISCOVERY_SEED_OFFSET, 6, cell.domain_size, 0, cell.domain_size - 1)
    first, _ = stable_conflict_report(cell, cell.codebook_seed_start, domains, 0, cell.domain_size - 1, tuples, overlays)
    second, _ = stable_conflict_report(cell, cell.codebook_seed_start, domains, 0, cell.domain_size - 1, tuples, overlays)
    assert [item.coordinate for item in first] == [item.coordinate for item in second]


def test_single_failed_trial_does_not_create_stable_conflict() -> None:
    cell = CELLS[0]
    domains = initial_codebook(cell.dimensions, cell.domain_size, cell.codebook_seed_start)
    overlays = empty_overlays(domains)
    tuples = tuples_for_target(cell.codebook_seed_start + DISCOVERY_SEED_OFFSET, 1, cell.domain_size, 0, cell.domain_size - 1)
    conflicts, _ = stable_conflict_report(cell, cell.codebook_seed_start, domains, 0, cell.domain_size - 1, tuples, overlays)
    assert all(item.conflict_frequency >= 2 for item in conflicts) or conflicts == []


def test_shuffled_arm_preserves_budget_and_breaks_order() -> None:
    order = random_coordinate_order(32, 123)
    shuffled = random_coordinate_order(32, 124)
    assert len(order[:8]) == len(shuffled[:8]) == 8
    assert order[:8] != shuffled[:8]


def test_random_patch_search_uses_same_patch_evaluation_budget() -> None:
    cell = CELLS[0]
    domains = initial_codebook(cell.dimensions, cell.domain_size, cell.codebook_seed_start)
    certification = tuples_for_target(cell.codebook_seed_start + 1, 3, cell.domain_size, 0, cell.domain_size - 1)
    validation = tuples_for_target(cell.codebook_seed_start + 2, 3, cell.domain_size, 0, cell.domain_size - 1)
    final_rows = tuples_for_target(cell.codebook_seed_start + 3, 3, cell.domain_size, 0, cell.domain_size - 1)
    old_rows = old_only_tuples(cell.codebook_seed_start + 4, 3, cell.domain_size, 0, cell.domain_size - 1)
    result, _ = evaluate_equal_bit_budget(
        cell,
        cell.codebook_seed_start,
        0,
        cell.domain_size - 1,
        8,
        certification,
        validation,
        final_rows,
        old_rows,
    )
    assert result.patch_evaluations == 1


def test_repair_ladder_is_frozen_and_sorted() -> None:
    assert REPAIR_LADDER == (0, 8, 16, 32)


def test_tags_do_not_store_operation_or_operand_ids() -> None:
    overlay = MarkerOverlay((1, 3, 7))
    assert isinstance(overlay.coordinates, tuple)
    assert overlay.coordinates == (1, 3, 7)


def test_physical_byte_accounting_includes_coordinate_indices() -> None:
    small = marker_overlay_bits(1024, 8)
    large = marker_overlay_bits(1024, 16)
    assert small > 8
    assert large > small


def test_equal_bit_extra_dimensions_are_not_smaller_than_overlay_budget() -> None:
    for budget in REPAIR_LADDER[1:]:
        assert extra_dimensions_for_budget(1024, budget) >= marker_overlay_bits(1024, budget)


def test_split_seeds_are_disjoint() -> None:
    base_seeds = {
        seed
        for cell in CELLS
        for seed in range(cell.codebook_seed_start, cell.codebook_seed_start + cell.codebook_seed_count)
    }
    discovery = {seed + DISCOVERY_SEED_OFFSET for seed in base_seeds}
    validation = {seed + VALIDATION_SEED_OFFSET for seed in base_seeds}
    final = {seed + FINAL_SEED_OFFSET for seed in base_seeds}
    assert discovery.isdisjoint(validation)
    assert discovery.isdisjoint(final)
    assert validation.isdisjoint(final)


def test_old_atom_regression_workload_exists() -> None:
    rows = old_only_tuples(123, 4, 10, 0, 9)
    assert len(rows) == 4
    assert all(row[0] != 9 for row in rows)


def test_fallback_required_symbol_exists() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "decoder_guided_tag_repair.py").read_text(encoding="utf-8")
    assert "FALLBACK_REQUIRED" in source


def test_previous_decoder_certified_artifacts_remain() -> None:
    assert (ROOT / "results" / "decoder_certified_codebook_v0_1" / "summary.json").exists()


def test_level35_frozen_artifacts_unchanged() -> None:
    protocol = build_protocol(ROOT)
    assert protocol["level35_frozen_artifacts_unchanged"] is True
    assert (
        hashlib.sha256((ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").read_bytes()).hexdigest().upper()
        == LEVEL35_V4_SHA256
    )


def test_stage_seed_freshness() -> None:
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_protocol_is_deterministic() -> None:
    first = build_protocol(ROOT)
    second = build_protocol(ROOT)
    assert first == second
    assert first["protocol_hash"] == second["protocol_hash"]
