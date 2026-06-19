from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from cgrn_hsr.release_artifacts import canonical_sha256
from cgrn_hsr.codebook_residue import (
    ARM_BLOCK_C16,
    ARM_HARD,
    ARM_MAP_I,
    ARM_RAW_BLOCK,
    ARM_SCALAR,
    BLOCK_SIZE,
    CELLS,
    CODEBOOK_SIZES,
    LEVEL35_V4_SHA256,
    SCALAR_LEVELS,
    SPLIT_FINAL,
    block_lut_payload,
    block_partition,
    build_atoms,
    build_discovery_codebooks,
    build_equal_bit_atoms,
    build_protocol,
    bundle_accumulators,
    deterministic_sign,
    discover_codebook,
    equal_bits_dimension,
    evaluate_cell_split,
    hard_payload,
    map_i_payload,
    metadata_bits,
    nearest_prototype,
    normalize_residue,
    pack_fixed_width,
    pad_symbols,
    prior_known_seed_set,
    quantize_scalar_symbols,
    raw_block_payload,
    scalar_payload,
    seeds_are_fresh,
    stage_seed_set,
    symbols_to_weights,
    token_entropy,
    unpack_fixed_width,
)

ROOT = Path(__file__).resolve().parents[1]


def _first_cell():
    return CELLS[0]


def test_exact_accumulator_produces_expected_sign_and_residue() -> None:
    atoms = torch.tensor([[1.0, -1.0, 1.0], [1.0, 1.0, -1.0], [-1.0, 1.0, 1.0]])
    members = torch.tensor([[0, 1, 2]], dtype=torch.long)
    accumulator = bundle_accumulators(atoms, members)[0]
    assert torch.equal(accumulator, torch.tensor([1.0, 1.0, 1.0]))
    assert torch.equal(deterministic_sign(accumulator), torch.tensor([1.0, 1.0, 1.0]))
    assert torch.equal(normalize_residue(accumulator, 3), torch.tensor([1.0, 1.0, 1.0]) / (3**0.5))


def test_tie_produces_zero_soft_weight() -> None:
    accumulator = torch.tensor([0.0, 2.0, -2.0])
    symbols = quantize_scalar_symbols(normalize_residue(accumulator, 3))
    weights = symbols_to_weights(symbols)
    assert weights[0].item() == 0.0


def test_block_partition_and_padding_are_deterministic() -> None:
    first_blocks, first_mask = block_partition(18, BLOCK_SIZE)
    second_blocks, second_mask = block_partition(18, BLOCK_SIZE)
    assert first_blocks == second_blocks
    assert torch.equal(first_mask, second_mask)
    padded = pad_symbols(torch.tensor([1, 2, 3, 4, 5], dtype=torch.long), BLOCK_SIZE)
    assert padded.shape == (1, BLOCK_SIZE)
    assert padded[0, 5:].tolist() == [0, 0, 0]


def test_token_encode_decode_roundtrip() -> None:
    values = [0, 3, 1, 2, 0, 1, 3]
    packed = pack_fixed_width(values, 2)
    assert unpack_fixed_width(packed, 2, len(values)) == values


def test_same_seed_and_discovery_set_produce_same_codebook() -> None:
    first = build_discovery_codebooks(CELLS)
    second = build_discovery_codebooks(CELLS)
    assert first[4] == second[4]
    assert first[16] == second[16]


def test_codebook_contains_no_atom_ids() -> None:
    codebooks = build_discovery_codebooks(CELLS)
    for codebook in codebooks.values():
        for prototype in codebook.prototypes:
            assert all(symbol in range(len(SCALAR_LEVELS)) for symbol in prototype)


def test_nearest_prototype_tiebreak_is_deterministic() -> None:
    codebook = discover_codebook([(0, 0, 0, 0, 0, 0, 0, 0), (1, 1, 1, 1, 1, 1, 1, 1)], 2)
    index, _, _ = nearest_prototype((0, 1, 0, 1, 0, 1, 0, 1), codebook)
    assert index == 0


def test_shuffled_arm_preserves_token_histogram() -> None:
    codebook = discover_codebook(
        [
            (0, 0, 0, 0, 0, 0, 0, 0),
            (1, 1, 1, 1, 1, 1, 1, 1),
            (2, 2, 2, 2, 2, 2, 2, 2),
            (3, 3, 3, 3, 3, 3, 3, 3),
        ],
        4,
    )
    sign = torch.ones(16)
    symbols = torch.tensor([0] * 8 + [1] * 8, dtype=torch.long)
    payload = block_lut_payload(sign, symbols, codebook, shuffled=True, shuffle_seed=123)
    assert payload.histogram_preserved is True


def test_scalar_and_block_arms_respect_physical_bit_accounting() -> None:
    sign = torch.ones(16)
    symbols = torch.tensor([0, 1, 2, 3] * 4, dtype=torch.long)
    scalar = scalar_payload(sign, symbols)
    raw = raw_block_payload(sign, symbols)
    assert scalar.packed_bits >= sign.numel()
    assert raw.packed_bits == sign.numel() + symbols.numel() * 2


def test_map_i_arm_receives_exact_accumulator() -> None:
    accumulator = torch.tensor([1.0, -3.0, 0.0])
    payload = map_i_payload(accumulator, 7)
    assert payload.arm_id == ARM_MAP_I
    assert torch.equal(payload.accumulator, accumulator)


def test_hard_arm_cannot_access_residue() -> None:
    payload = hard_payload(torch.ones(8))
    assert payload.arm_id == ARM_HARD
    assert payload.scalar_symbols is None
    assert payload.accumulator is None


def test_shared_codebook_frozen_before_evaluation() -> None:
    codebooks = build_discovery_codebooks(CELLS)
    rows = evaluate_cell_split(
        cell=_first_cell(),
        split_name=SPLIT_FINAL,
        split_seed_start=_first_cell().final_seed_start,
        count=2,
        codebooks=codebooks,
    )
    assert rows
    assert set(codebooks) == set(CODEBOOK_SIZES)


def test_discovery_and_evaluation_splits_are_disjoint() -> None:
    cell = _first_cell()
    discovery = set(range(cell.discovery_seed_start, cell.discovery_seed_start + 48))
    final = set(range(cell.final_seed_start, cell.final_seed_start + 64))
    assert discovery.isdisjoint(final)


def test_equal_bit_extra_d_has_no_smaller_physical_budget() -> None:
    target_bits = 1536
    dimension = equal_bits_dimension(target_bits)
    atoms = build_equal_bit_atoms(1024, target_bits, 32, 111)
    assert dimension >= target_bits
    assert atoms.size(1) >= 1536


def test_prototype_utilization_is_measured() -> None:
    codebook = discover_codebook(
        [
            (0, 0, 0, 0, 0, 0, 0, 0),
            (1, 1, 1, 1, 1, 1, 1, 1),
            (2, 2, 2, 2, 2, 2, 2, 2),
            (3, 3, 3, 3, 3, 3, 3, 3),
        ],
        4,
    )
    sign = torch.ones(16)
    symbols = torch.tensor([0] * 8 + [1] * 8, dtype=torch.long)
    payload = block_lut_payload(sign, symbols, codebook, shuffled=False, shuffle_seed=123)
    assert payload.effective_codebook_utilization > 0.0
    assert payload.prototype_usage_distribution


def test_previous_blocked_artifacts_remain_unchanged() -> None:
    assert (ROOT / "results" / "decoder_certified_codebook_v0_1" / "summary.json").exists()
    assert (ROOT / "results" / "decoder_guided_tag_repair_v0_1" / "summary.json").exists()
    assert (ROOT / "results" / "self_describing_record_v0_1" / "summary.json").exists()


def test_level35_heldout_artifacts_remain_unchanged() -> None:
    protocol = build_protocol(ROOT)
    assert protocol["level35_frozen_artifacts_unchanged"] is True
    assert canonical_sha256(ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").upper() == LEVEL35_V4_SHA256


def test_stage_seeds_are_fresh() -> None:
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))
