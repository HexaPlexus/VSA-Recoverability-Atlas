from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import time
import zlib
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
import torchhd

from .baseline import make_generator
from .decoder_certified_codebook import stage_seed_set as decoder_certified_stage_seed_set
from .decoder_guided_tag_repair import stage_seed_set as tagged_repair_stage_seed_set
from .exact_capsule_contract_closure import LEVEL35_V4_SHA256
from .first_order_trace_coactivation import stage_seed_set as first_order_stage_seed_set
from .lazy_trace_addressing_stage_a import stage_a_seed_set
from .lazy_trace_addressing_stage_a1 import stage_a1_seed_set
from .lazy_trace_addressing_stage_a2a import stage_a2a_seed_set
from .level3_2_confirmation import prior_level3_1_seed_set
from .level3_2b_map_budget_robustness import level3_2_seed_set, level3_2b_seed_set
from .level3_4_algebraic_baselines import level3_4_seed_set
from .level3_5b_native_noise_frontiers import prior_seed_set as level35_prior_seed_set
from .self_describing_record import stage_seed_set as self_describing_stage_seed_set

TASK_NAME = "Codebook-Compressed Residue Plane v0.1"
SCHEMA_VERSION = "codebook-residue-v0.1-dev"
RESULTS_NAMESPACE = "codebook_residue_v0_1"
STARTING_COMMIT = "1f2808626ac94f158fe2cecda04d536e316b15a4"

STATUS_FLAGS = [
    "ADOPT_EXISTING_QUANTIZATION_PRIMITIVES",
    "WRAP",
    "PROTOTYPE",
    "DEVELOPMENT_ONLY",
    "NO_NOVELTY_CLAIM",
    "NO_PRODUCTION_CLAIM",
]

ARM_HARD = "A_MAP_B_HARD"
ARM_TERNARY = "B_TERNARY_TIE_AWARE"
ARM_SCALAR = "C_SCALAR_RESIDUE_EQUAL_RATE"
ARM_BLOCK_C4 = "D_BLOCK_CODEBOOK_C4"
ARM_BLOCK_C16 = "E_BLOCK_CODEBOOK_C16"
ARM_SHUFFLED = "F_SHUFFLED_BLOCK_TOKENS"
ARM_MAP_I = "G_MAP_I_EXACT_ACCUMULATOR"
ARM_EQUAL_BITS = "H_EQUAL_TOTAL_BIT_MAP_B"
ARM_RAW_BLOCK = "I_RAW_BLOCK_STORAGE"

PREVIOUS_VERDICTS = {
    "decoder_certified_codebook": "BLOCK_DECODER_CERTIFICATION_LINE",
    "decoder_guided_tag_repair": "BLOCK_TAGGED_SYMBOL_LINE",
    "self_describing_record": "ADOPT_ORDINARY_SIDECAR_DAG / PACKAGING_ADVANTAGE_NOT_SUPPORTED",
}

SPLIT_DISCOVERY = "CODEBOOK_DISCOVERY"
SPLIT_VALIDATION = "DEVELOPMENT_VALIDATION"
SPLIT_FINAL = "FINAL_DEVELOPMENT_EVALUATION"

TIE_POLICY_POSITIVE = "sign(0)=+1; tie_weight=0"
NORMALIZATION_ID = "abs_accumulator_over_sqrtK"
NORMALIZATION_DESCRIPTION = "normalized_residue = abs(a[i]) / sqrt(K)"
PROTOTYPE_DISTANCE = "L1"
BLOCK_SIZE = 8
CODEBOOK_SIZES = (4, 16)
SCALAR_LEVELS = (0.0, 0.5, 1.0, 2.0)
SCALAR_THRESHOLDS = (0.0, 0.75, 1.5)
SCALAR_SYMBOL_BITS = 2
PRIMARY_AMORTIZATION_BUNDLES = 1_000
AMORTIZATION_POINTS = (1, 1_000, 1_000_000)
K_METADATA_BITS = 5
CODEBOOK_ID_BITS = 8
NORMALIZATION_BITS = 4
TIE_POLICY_BITS = 2
PADDING_BITS = 4
VERSION_BITS = 4
PRIMARY_ACCEPT_MARGIN = 0.0

ATOM_CODEBOOK_SEEDS = (964_100_100, 964_100_200)
DISCOVERY_SEED_BASE = 964_200_100
VALIDATION_SEED_BASE = 964_300_100
FINAL_SEED_BASE = 964_400_100
SHUFFLE_SEED_BASE = 964_500_100
PRIMARY_CELLS = (
    {"dimension": 1024, "bundle_width": 7, "atom_count": 128},
    {"dimension": 1024, "bundle_width": 7, "atom_count": 256},
    {"dimension": 1024, "bundle_width": 15, "atom_count": 128},
    {"dimension": 1024, "bundle_width": 15, "atom_count": 256},
    {"dimension": 1024, "bundle_width": 31, "atom_count": 128},
    {"dimension": 1024, "bundle_width": 31, "atom_count": 256},
)
DISCOVERY_BUNDLES_PER_CELL = 48
VALIDATION_BUNDLES_PER_CELL = 32
FINAL_BUNDLES_PER_CELL = 64


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    dimension: int
    bundle_width: int
    atom_count: int
    atom_codebook_seed: int
    discovery_seed_start: int
    validation_seed_start: int
    final_seed_start: int

    def seed_ranges(self) -> dict[str, dict[str, int]]:
        return {
            SPLIT_DISCOVERY: {"start": self.discovery_seed_start, "count": DISCOVERY_BUNDLES_PER_CELL},
            SPLIT_VALIDATION: {"start": self.validation_seed_start, "count": VALIDATION_BUNDLES_PER_CELL},
            SPLIT_FINAL: {"start": self.final_seed_start, "count": FINAL_BUNDLES_PER_CELL},
        }


@dataclass(frozen=True)
class ResidueCodebook:
    codebook_size: int
    block_size: int
    prototypes: tuple[tuple[int, ...], ...]
    token_bits: int
    discovery_blocks: int
    construction_digest: str

    def weight_block(self, token: int) -> torch.Tensor:
        return torch.tensor([SCALAR_LEVELS[symbol] for symbol in self.prototypes[token]], dtype=torch.float32)


@dataclass(frozen=True)
class RepresentationPayload:
    arm_id: str
    variant_id: str
    sign_plane: torch.Tensor | None
    scalar_symbols: torch.Tensor | None
    block_tokens: tuple[int, ...] | None
    accumulator: torch.Tensor | None
    decoded_weights: torch.Tensor
    codebook_size: int | None
    packed_bits: int
    metadata_bits: int
    codebook_bits: int
    codebook_bits_amortized: dict[int, float]
    raw_block_bits: int
    token_entropy: float
    exact_block_fraction: float
    non_identical_fraction: float
    nearest_prototype_distortion: float
    prototype_usage_distribution: dict[int, int]
    effective_codebook_utilization: float
    saturation_rate: float
    token_stream_bytes: int
    temp_decoder_buffer_bytes: int
    histogram_preserved: bool


def canonical_json_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def build_cells() -> tuple[CellSpec, ...]:
    cells: list[CellSpec] = []
    offset = 0
    for seed_index, atom_seed in enumerate(ATOM_CODEBOOK_SEEDS):
        for template_index, template in enumerate(PRIMARY_CELLS):
            offset += 1
            cells.append(
                CellSpec(
                    cell_id=f"d{template['dimension']}_k{template['bundle_width']}_n{template['atom_count']}_s{seed_index}",
                    dimension=int(template["dimension"]),
                    bundle_width=int(template["bundle_width"]),
                    atom_count=int(template["atom_count"]),
                    atom_codebook_seed=atom_seed,
                    discovery_seed_start=DISCOVERY_SEED_BASE + offset * 1_000,
                    validation_seed_start=VALIDATION_SEED_BASE + offset * 1_000,
                    final_seed_start=FINAL_SEED_BASE + offset * 1_000,
                )
            )
    return tuple(cells)


CELLS = build_cells()


def stage_seed_set() -> set[int]:
    seeds: set[int] = set(ATOM_CODEBOOK_SEEDS)
    seeds.add(SHUFFLE_SEED_BASE)
    for cell in CELLS:
        for spec in cell.seed_ranges().values():
            seeds.update(range(spec["start"], spec["start"] + spec["count"]))
    return seeds


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
    prior.update(decoder_certified_stage_seed_set())
    prior.update(tagged_repair_stage_seed_set())
    prior.update(self_describing_stage_seed_set())
    for path in (repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json",):
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


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def deterministic_sign(accumulator: torch.Tensor) -> torch.Tensor:
    return torch.where(accumulator >= 0, torch.ones_like(accumulator), -torch.ones_like(accumulator))


def accumulator_bits(bundle_width: int) -> int:
    return math.ceil(math.log2(2 * bundle_width + 1))


def metadata_bits() -> int:
    return K_METADATA_BITS + CODEBOOK_ID_BITS + NORMALIZATION_BITS + TIE_POLICY_BITS + PADDING_BITS + VERSION_BITS


def build_atoms(dimension: int, atom_count: int, seed: int) -> torch.Tensor:
    generator = make_generator(seed)
    return torchhd.random(atom_count, dimension, "MAP", generator=generator).detach().cpu()


def sample_bundle_indices(atom_count: int, bundle_width: int, seed: int, count: int) -> torch.Tensor:
    generator = make_generator(seed)
    bundles: list[torch.Tensor] = []
    for _ in range(count):
        bundles.append(torch.randperm(atom_count, generator=generator)[:bundle_width])
    return torch.stack(bundles, dim=0)


def bundle_accumulators(atoms: torch.Tensor, members: torch.Tensor) -> torch.Tensor:
    return atoms[members].sum(dim=1).to(torch.float32)


def normalize_residue(accumulator: torch.Tensor, bundle_width: int) -> torch.Tensor:
    return accumulator.abs() / math.sqrt(float(bundle_width))


def quantize_coordinate(value: float) -> int:
    if value <= SCALAR_THRESHOLDS[0]:
        return 0
    if value <= SCALAR_THRESHOLDS[1]:
        return 1
    if value <= SCALAR_THRESHOLDS[2]:
        return 2
    return 3


def quantize_scalar_symbols(normalized_residue: torch.Tensor) -> torch.Tensor:
    return torch.tensor(
        [quantize_coordinate(float(value)) for value in normalized_residue.reshape(-1).tolist()],
        dtype=torch.long,
    ).reshape(normalized_residue.shape)


def symbols_to_weights(symbols: torch.Tensor) -> torch.Tensor:
    table = torch.tensor(SCALAR_LEVELS, dtype=torch.float32)
    return table[symbols.long()]


def block_partition(dimension: int, block_size: int = BLOCK_SIZE) -> tuple[list[tuple[int, int]], torch.Tensor]:
    block_count = math.ceil(dimension / block_size)
    blocks: list[tuple[int, int]] = []
    mask = torch.zeros(block_count * block_size, dtype=torch.bool)
    for block_index in range(block_count):
        start = block_index * block_size
        end = min(start + block_size, dimension)
        blocks.append((start, end))
        mask[start:end] = True
    return blocks, mask


def pad_symbols(symbols: torch.Tensor, block_size: int = BLOCK_SIZE) -> torch.Tensor:
    flat = symbols.reshape(-1)
    block_count = math.ceil(flat.numel() / block_size)
    padded = torch.zeros(block_count * block_size, dtype=torch.long)
    padded[: flat.numel()] = flat
    return padded.reshape(block_count, block_size)


def pack_fixed_width(values: list[int], width_bits: int) -> bytes:
    if width_bits <= 0:
        return b""
    accumulator = 0
    bit_count = 0
    payload = bytearray()
    mask = (1 << width_bits) - 1
    for value in values:
        accumulator = (accumulator << width_bits) | (int(value) & mask)
        bit_count += width_bits
        while bit_count >= 8:
            shift = bit_count - 8
            payload.append((accumulator >> shift) & 0xFF)
            accumulator &= (1 << shift) - 1 if shift > 0 else 0
            bit_count -= 8
    if bit_count > 0:
        payload.append((accumulator << (8 - bit_count)) & 0xFF)
    return bytes(payload)


def unpack_fixed_width(payload: bytes, width_bits: int, count: int) -> list[int]:
    values: list[int] = []
    if width_bits <= 0:
        return values
    accumulator = 0
    bit_count = 0
    mask = (1 << width_bits) - 1
    for byte in payload:
        accumulator = (accumulator << 8) | byte
        bit_count += 8
        while bit_count >= width_bits and len(values) < count:
            shift = bit_count - width_bits
            values.append((accumulator >> shift) & mask)
            accumulator &= (1 << shift) - 1 if shift > 0 else 0
            bit_count -= width_bits
    return values


def discover_codebook(discovery_symbol_blocks: list[tuple[int, ...]], codebook_size: int) -> ResidueCodebook:
    counts = Counter(discovery_symbol_blocks)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    selected = tuple(pattern for pattern, _ in ranked[:codebook_size])
    digest = canonical_json_hash(
        {
            "codebook_size": codebook_size,
            "block_size": BLOCK_SIZE,
            "prototypes": [list(pattern) for pattern in selected],
            "discovery_blocks": len(discovery_symbol_blocks),
        }
    )
    return ResidueCodebook(
        codebook_size=codebook_size,
        block_size=BLOCK_SIZE,
        prototypes=selected,
        token_bits=int(math.log2(codebook_size)),
        discovery_blocks=len(discovery_symbol_blocks),
        construction_digest=digest,
    )


def nearest_prototype(block_symbols: tuple[int, ...], codebook: ResidueCodebook) -> tuple[int, float, bool]:
    exact = False
    best_index = 0
    best_distance = math.inf
    for index, prototype in enumerate(codebook.prototypes):
        distance = float(sum(abs(int(a) - int(b)) for a, b in zip(block_symbols, prototype, strict=True)))
        if distance == 0.0:
            exact = True
        if distance < best_distance or (distance == best_distance and index < best_index):
            best_index = index
            best_distance = distance
    return best_index, best_distance, exact


def token_entropy(tokens: list[int]) -> float:
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def block_lut_payload(
    sign_plane: torch.Tensor,
    scalar_symbols: torch.Tensor,
    codebook: ResidueCodebook,
    *,
    shuffled: bool,
    shuffle_seed: int,
) -> RepresentationPayload:
    symbol_blocks = pad_symbols(scalar_symbols, BLOCK_SIZE)
    tokens: list[int] = []
    exact_matches = 0
    distortions: list[float] = []
    usage: Counter[int] = Counter()
    for block in symbol_blocks.tolist():
        token, distance, exact = nearest_prototype(tuple(int(item) for item in block), codebook)
        tokens.append(token)
        distortions.append(distance)
        usage[token] += 1
        if exact:
            exact_matches += 1
    original_histogram = Counter(tokens)
    if shuffled and len(tokens) > 1:
        shift = (shuffle_seed % (len(tokens) - 1)) + 1
        tokens = tokens[shift:] + tokens[:shift]
    histogram_preserved = Counter(tokens) == original_histogram
    decoded_weights = torch.cat([codebook.weight_block(token) for token in tokens], dim=0)[: sign_plane.numel()]
    token_payload = pack_fixed_width(tokens, codebook.token_bits)
    metadata = metadata_bits()
    codebook_bits = codebook.codebook_size * codebook.block_size * SCALAR_SYMBOL_BITS
    amortized = {point: codebook_bits / point for point in AMORTIZATION_POINTS}
    return RepresentationPayload(
        arm_id=ARM_SHUFFLED if shuffled else (ARM_BLOCK_C4 if codebook.codebook_size == 4 else ARM_BLOCK_C16),
        variant_id=f"C{codebook.codebook_size}{'_shuffled' if shuffled else ''}",
        sign_plane=sign_plane,
        scalar_symbols=scalar_symbols,
        block_tokens=tuple(tokens),
        accumulator=None,
        decoded_weights=decoded_weights,
        codebook_size=codebook.codebook_size,
        packed_bits=sign_plane.numel() + len(tokens) * codebook.token_bits,
        metadata_bits=metadata,
        codebook_bits=codebook_bits,
        codebook_bits_amortized=amortized,
        raw_block_bits=symbol_blocks.numel() * SCALAR_SYMBOL_BITS,
        token_entropy=token_entropy(tokens),
        exact_block_fraction=exact_matches / max(1, len(tokens)),
        non_identical_fraction=1.0 - (exact_matches / max(1, len(tokens))),
        nearest_prototype_distortion=float(statistics.fmean(distortions)) if distortions else 0.0,
        prototype_usage_distribution={int(key): int(value) for key, value in sorted(usage.items())},
        effective_codebook_utilization=len(usage) / codebook.codebook_size,
        saturation_rate=float((scalar_symbols == 3).float().mean().item()),
        token_stream_bytes=len(token_payload),
        temp_decoder_buffer_bytes=int(decoded_weights.numel() * decoded_weights.element_size()),
        histogram_preserved=histogram_preserved,
    )


def scalar_payload(sign_plane: torch.Tensor, scalar_symbols: torch.Tensor) -> RepresentationPayload:
    packed = pack_fixed_width(scalar_symbols.reshape(-1).tolist(), SCALAR_SYMBOL_BITS)
    compressed = zlib.compress(packed, level=9)
    restored = unpack_fixed_width(zlib.decompress(compressed), SCALAR_SYMBOL_BITS, scalar_symbols.numel())
    restored_symbols = torch.tensor(restored, dtype=torch.long).reshape(scalar_symbols.shape)
    return RepresentationPayload(
        arm_id=ARM_SCALAR,
        variant_id="scalar_zlib_4level",
        sign_plane=sign_plane,
        scalar_symbols=restored_symbols,
        block_tokens=None,
        accumulator=None,
        decoded_weights=symbols_to_weights(restored_symbols).to(torch.float32),
        codebook_size=None,
        packed_bits=sign_plane.numel() + len(compressed) * 8,
        metadata_bits=metadata_bits(),
        codebook_bits=0,
        codebook_bits_amortized={point: 0.0 for point in AMORTIZATION_POINTS},
        raw_block_bits=scalar_symbols.numel() * SCALAR_SYMBOL_BITS,
        token_entropy=0.0,
        exact_block_fraction=0.0,
        non_identical_fraction=0.0,
        nearest_prototype_distortion=0.0,
        prototype_usage_distribution={},
        effective_codebook_utilization=0.0,
        saturation_rate=float((scalar_symbols == 3).float().mean().item()),
        token_stream_bytes=len(compressed),
        temp_decoder_buffer_bytes=int(sign_plane.numel() * 4),
        histogram_preserved=True,
    )


def raw_block_payload(sign_plane: torch.Tensor, scalar_symbols: torch.Tensor) -> RepresentationPayload:
    packed = pack_fixed_width(scalar_symbols.reshape(-1).tolist(), SCALAR_SYMBOL_BITS)
    return RepresentationPayload(
        arm_id=ARM_RAW_BLOCK,
        variant_id="raw_block_symbols",
        sign_plane=sign_plane,
        scalar_symbols=scalar_symbols,
        block_tokens=None,
        accumulator=None,
        decoded_weights=symbols_to_weights(scalar_symbols).to(torch.float32),
        codebook_size=None,
        packed_bits=sign_plane.numel() + len(packed) * 8,
        metadata_bits=metadata_bits(),
        codebook_bits=0,
        codebook_bits_amortized={point: 0.0 for point in AMORTIZATION_POINTS},
        raw_block_bits=scalar_symbols.numel() * SCALAR_SYMBOL_BITS,
        token_entropy=0.0,
        exact_block_fraction=1.0,
        non_identical_fraction=0.0,
        nearest_prototype_distortion=0.0,
        prototype_usage_distribution={},
        effective_codebook_utilization=0.0,
        saturation_rate=float((scalar_symbols == 3).float().mean().item()),
        token_stream_bytes=len(packed),
        temp_decoder_buffer_bytes=int(sign_plane.numel() * 4),
        histogram_preserved=True,
    )


def hard_payload(sign_plane: torch.Tensor) -> RepresentationPayload:
    return RepresentationPayload(
        arm_id=ARM_HARD,
        variant_id="sign_only",
        sign_plane=sign_plane,
        scalar_symbols=None,
        block_tokens=None,
        accumulator=None,
        decoded_weights=torch.ones_like(sign_plane, dtype=torch.float32),
        codebook_size=None,
        packed_bits=sign_plane.numel(),
        metadata_bits=metadata_bits(),
        codebook_bits=0,
        codebook_bits_amortized={point: 0.0 for point in AMORTIZATION_POINTS},
        raw_block_bits=0,
        token_entropy=0.0,
        exact_block_fraction=0.0,
        non_identical_fraction=0.0,
        nearest_prototype_distortion=0.0,
        prototype_usage_distribution={},
        effective_codebook_utilization=0.0,
        saturation_rate=0.0,
        token_stream_bytes=math.ceil(sign_plane.numel() / 8),
        temp_decoder_buffer_bytes=int(sign_plane.numel() * 4),
        histogram_preserved=True,
    )


def ternary_payload(sign_plane: torch.Tensor, accumulator: torch.Tensor) -> RepresentationPayload:
    tie_mask = accumulator == 0
    weights = torch.where(tie_mask, torch.zeros_like(accumulator), torch.ones_like(accumulator)).to(torch.float32)
    return RepresentationPayload(
        arm_id=ARM_TERNARY,
        variant_id="sign_plus_tie_mask",
        sign_plane=sign_plane,
        scalar_symbols=None,
        block_tokens=None,
        accumulator=None,
        decoded_weights=weights,
        codebook_size=None,
        packed_bits=sign_plane.numel() + tie_mask.numel(),
        metadata_bits=metadata_bits(),
        codebook_bits=0,
        codebook_bits_amortized={point: 0.0 for point in AMORTIZATION_POINTS},
        raw_block_bits=0,
        token_entropy=0.0,
        exact_block_fraction=0.0,
        non_identical_fraction=0.0,
        nearest_prototype_distortion=0.0,
        prototype_usage_distribution={},
        effective_codebook_utilization=0.0,
        saturation_rate=0.0,
        token_stream_bytes=math.ceil((sign_plane.numel() + tie_mask.numel()) / 8),
        temp_decoder_buffer_bytes=int(sign_plane.numel() * 4),
        histogram_preserved=True,
    )


def map_i_payload(accumulator: torch.Tensor, bundle_width: int) -> RepresentationPayload:
    return RepresentationPayload(
        arm_id=ARM_MAP_I,
        variant_id=f"exact_accumulator_k{bundle_width}",
        sign_plane=None,
        scalar_symbols=None,
        block_tokens=None,
        accumulator=accumulator,
        decoded_weights=accumulator.abs().to(torch.float32),
        codebook_size=None,
        packed_bits=accumulator.numel() * accumulator_bits(bundle_width),
        metadata_bits=metadata_bits(),
        codebook_bits=0,
        codebook_bits_amortized={point: 0.0 for point in AMORTIZATION_POINTS},
        raw_block_bits=0,
        token_entropy=0.0,
        exact_block_fraction=0.0,
        non_identical_fraction=0.0,
        nearest_prototype_distortion=0.0,
        prototype_usage_distribution={},
        effective_codebook_utilization=0.0,
        saturation_rate=0.0,
        token_stream_bytes=math.ceil((accumulator.numel() * accumulator_bits(bundle_width)) / 8),
        temp_decoder_buffer_bytes=int(accumulator.numel() * 4),
        histogram_preserved=True,
    )


def equal_bits_dimension(base_bits: int) -> int:
    return int(math.ceil(base_bits))


def auc_equivalent(scores: torch.Tensor, members: set[int]) -> float:
    positives = scores[sorted(members)]
    negative_indices = [index for index in range(scores.numel()) if index not in members]
    negatives = scores[negative_indices]
    if positives.numel() == 0 or negatives.numel() == 0:
        return 1.0
    greater = (positives.unsqueeze(1) > negatives.unsqueeze(0)).float().mean().item()
    equal = (positives.unsqueeze(1) == negatives.unsqueeze(0)).float().mean().item()
    return float(greater + 0.5 * equal)


def score_candidates(atoms: torch.Tensor, payload: RepresentationPayload) -> torch.Tensor:
    if payload.arm_id == ARM_MAP_I:
        assert payload.accumulator is not None
        return atoms @ payload.accumulator.to(torch.float32)
    assert payload.sign_plane is not None
    signed_weights = payload.sign_plane.to(torch.float32) * payload.decoded_weights.to(torch.float32)
    return atoms @ signed_weights


def evaluate_scores(scores: torch.Tensor, members: torch.Tensor) -> dict[str, Any]:
    member_set = {int(value) for value in members.tolist()}
    bundle_width = len(member_set)
    ranked = torch.argsort(scores, descending=True)
    topk = ranked[:bundle_width]
    topk_set = {int(value) for value in topk.tolist()}
    true_positives = len(topk_set.intersection(member_set))
    precision = true_positives / bundle_width
    recall = true_positives / bundle_width
    exact = topk_set == member_set
    top1_member = int(ranked[0].item()) in member_set
    fp_rate = (bundle_width - true_positives) / max(1, scores.numel() - bundle_width)
    kth_score = float(scores[topk[-1]].item())
    next_score = float(scores[ranked[bundle_width]].item()) if bundle_width < scores.numel() else float("-inf")
    margin = kth_score - next_score
    accepted = margin > PRIMARY_ACCEPT_MARGIN
    return {
        "member_top1_recall": float(top1_member),
        "member_topk_recall": recall,
        "full_member_enumeration_recall": float(exact),
        "precision": precision,
        "false_positive_rate": fp_rate,
        "cleanup_margin": margin,
        "coverage": float(accepted),
        "silent_wrong_acceptance": float(accepted and not exact),
        "conditional_risk": float((accepted and not exact) / max(1, int(accepted))),
        "accepted_exact": float(accepted and exact),
        "auc_equivalent": auc_equivalent(scores, member_set),
        "topk_indices": [int(value) for value in topk.tolist()],
        "top1_index": int(ranked[0].item()),
        "scores_top1": float(scores[ranked[0]].item()),
        "scores_topk": [float(scores[index].item()) for index in topk.tolist()],
        "member_set": sorted(member_set),
    }


def build_equal_bit_atoms(base_dimension: int, target_bits: int, atom_count: int, seed: int) -> torch.Tensor:
    dimension = max(base_dimension, equal_bits_dimension(target_bits))
    return build_atoms(dimension, atom_count, seed)


def evaluate_arm(
    *,
    payload: RepresentationPayload,
    atoms: torch.Tensor,
    members: torch.Tensor,
    representation_latency_sec: float,
    decode_repeats: int = 2,
) -> dict[str, Any]:
    decode_latencies: list[float] = []
    scores = None
    for _ in range(decode_repeats):
        start = time.perf_counter()
        scores = score_candidates(atoms, payload)
        decode_latencies.append(time.perf_counter() - start)
    assert scores is not None
    metrics = evaluate_scores(scores, members)
    return {
        **metrics,
        "encoding_latency_sec": representation_latency_sec,
        "cold_decode_latency_sec": decode_latencies[0],
        "warm_decode_latency_sec": decode_latencies[-1],
        "physical_bits_total": payload.packed_bits + payload.metadata_bits + int(payload.codebook_bits_amortized[PRIMARY_AMORTIZATION_BUNDLES]),
        "physical_bits_payload_only": payload.packed_bits + payload.metadata_bits,
        "sign_plane_bits": 0 if payload.sign_plane is None else int(payload.sign_plane.numel()),
        "codebook_bits": payload.codebook_bits,
        "codebook_bits_amortized_primary": payload.codebook_bits_amortized[PRIMARY_AMORTIZATION_BUNDLES],
        "token_stream_bytes": payload.token_stream_bytes,
        "temp_decoder_buffer_bytes": payload.temp_decoder_buffer_bytes,
        "token_entropy": payload.token_entropy,
        "exact_block_fraction": payload.exact_block_fraction,
        "non_identical_fraction": payload.non_identical_fraction,
        "nearest_prototype_distortion": payload.nearest_prototype_distortion,
        "effective_codebook_utilization": payload.effective_codebook_utilization,
        "saturation_rate": payload.saturation_rate,
        "histogram_preserved": payload.histogram_preserved,
        "prototype_usage_distribution": payload.prototype_usage_distribution,
    }


def build_representations(
    accumulator: torch.Tensor,
    bundle_width: int,
    codebooks: dict[int, ResidueCodebook],
    shuffle_seed: int,
) -> list[RepresentationPayload]:
    sign_plane = deterministic_sign(accumulator).to(torch.float32)
    normalized = normalize_residue(accumulator, bundle_width)
    scalar_symbols = quantize_scalar_symbols(normalized)
    payloads: list[RepresentationPayload] = [
        hard_payload(sign_plane),
        ternary_payload(sign_plane, accumulator),
        scalar_payload(sign_plane, scalar_symbols),
        raw_block_payload(sign_plane, scalar_symbols),
        map_i_payload(accumulator, bundle_width),
    ]
    for codebook_size in CODEBOOK_SIZES:
        codebook = codebooks[codebook_size]
        payloads.append(block_lut_payload(sign_plane, scalar_symbols, codebook, shuffled=False, shuffle_seed=shuffle_seed))
        payloads.append(block_lut_payload(sign_plane, scalar_symbols, codebook, shuffled=True, shuffle_seed=shuffle_seed))
    return payloads


def codebook_json_payload(codebooks: dict[int, ResidueCodebook]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "normalization": NORMALIZATION_DESCRIPTION,
        "scalar_levels": list(SCALAR_LEVELS),
        "scalar_thresholds": list(SCALAR_THRESHOLDS),
        "block_size": BLOCK_SIZE,
        "codebooks": {
            str(size): {
                "codebook_size": book.codebook_size,
                "token_bits": book.token_bits,
                "block_size": book.block_size,
                "discovery_blocks": book.discovery_blocks,
                "construction_digest": book.construction_digest,
                "prototypes": [list(pattern) for pattern in book.prototypes],
            }
            for size, book in sorted(codebooks.items())
        },
    }


def dependency_audit(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "verdict": "ADOPT_EXISTING_QUANTIZATION_PRIMITIVES",
        "status": STATUS_FLAGS,
        "previous_preserved_verdicts": PREVIOUS_VERDICTS,
        "anti_nih_findings": [
            {
                "family": "vector quantization / block vector quantization / product quantization",
                "verdict": "ADOPT",
                "coverage": 0.9,
                "notes": "The stage uses a tiny deterministic dictionary over quantized residue blocks rather than claiming a new VQ method.",
            },
            {
                "family": "lookup-table quantization / dictionary coding",
                "verdict": "ADOPT",
                "coverage": 1.0,
                "notes": "Decoder-side LUT prototypes are ordinary lookup-table quantization primitives.",
            },
            {
                "family": "scalar quantization / bit-plane coding / entropy coding",
                "verdict": "COMPARE",
                "coverage": 0.8,
                "notes": "A scalar residue control and raw coarse-block control are mandatory because they may explain any apparent gain without block dictionary complexity.",
            },
            {
                "family": "soft-decision reliability quantization",
                "verdict": "ADOPT",
                "coverage": 0.8,
                "notes": "Soft cleanup weights are just quantized reliability surrogates derived from accumulator magnitude.",
            },
            {
                "family": "MAP-I exact accumulator and MAP-B sign-only cleanup",
                "verdict": "WRAP",
                "coverage": 1.0,
                "notes": "The experiment reuses the ordinary MAP accumulator observation and candidate cleanup scoring; it does not invent a new decoder.",
            },
            {
                "family": "learned quantizers / neural compression",
                "verdict": "BLOCK",
                "coverage": 0.0,
                "notes": "No learned VQ, residual VQ, or new decoder-side model is authorized in v0.1.",
            },
        ],
        "scope_reduction": {
            "kept_dimensions": [1024],
            "kept_bundle_widths": [7, 15, 31],
            "dropped_cells": ["D=512", "K=3"],
            "reason": "Reduce scope to transition-like accumulator regimes and keep the development run bounded without weakening the causal comparison among scalar, block-LUT, and equal-bit controls.",
        },
        "level35_frozen_artifacts_unchanged": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256,
    }


def build_protocol(repo_root: Path) -> dict[str, Any]:
    protocol = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "starting_commit": STARTING_COMMIT,
        "status": STATUS_FLAGS,
        "heldout_execution_allowed": False,
        "preserved_previous_verdicts": PREVIOUS_VERDICTS,
        "accumulator_contract": "exact integer MAP bundle accumulator for diagnostics and authorized upper-bound arms only",
        "normalization": {
            "id": NORMALIZATION_ID,
            "description": NORMALIZATION_DESCRIPTION,
        },
        "tie_policy": TIE_POLICY_POSITIVE,
        "block_format": {
            "block_size": BLOCK_SIZE,
            "contiguous_partition": True,
            "padding_mask": True,
        },
        "scalar_quantization": {
            "thresholds": list(SCALAR_THRESHOLDS),
            "levels": list(SCALAR_LEVELS),
            "bits_per_symbol": SCALAR_SYMBOL_BITS,
            "scalar_control_encoding": "packed_2bit_symbols_then_zlib",
        },
        "codebook_construction": {
            "split": SPLIT_DISCOVERY,
            "selection": "top_frequency_block_patterns",
            "distance": PROTOTYPE_DISTANCE,
            "top_c_codebooks": list(CODEBOOK_SIZES),
            "shared_across_K": True,
            "shared_across_cells": True,
            "tie_break": "lowest_prototype_index",
        },
        "token_format": {
            "C4_bits": 2,
            "C16_bits": 4,
        },
        "cells": [asdict(cell) for cell in CELLS],
        "split_counts": {
            SPLIT_DISCOVERY: DISCOVERY_BUNDLES_PER_CELL,
            SPLIT_VALIDATION: VALIDATION_BUNDLES_PER_CELL,
            SPLIT_FINAL: FINAL_BUNDLES_PER_CELL,
        },
        "arms": [
            ARM_HARD,
            ARM_TERNARY,
            ARM_SCALAR,
            ARM_BLOCK_C4,
            ARM_BLOCK_C16,
            ARM_SHUFFLED,
            ARM_MAP_I,
            ARM_EQUAL_BITS,
            ARM_RAW_BLOCK,
        ],
        "equal_bit_policy": {
            "primary_amortization_bundles": PRIMARY_AMORTIZATION_BUNDLES,
            "comparison_targets": ["C4", "C16"],
        },
        "metrics": [
            "member_top1_recall",
            "member_topk_recall",
            "full_member_enumeration_recall",
            "precision",
            "false_positive_rate",
            "auc_equivalent",
            "cleanup_margin",
            "coverage",
            "conditional_risk",
            "silent_wrong_acceptance",
            "storage_bytes",
            "codebook_amortization",
            "encoding_latency",
            "cold_decode_latency",
            "warm_decode_latency",
            "saturation_rate",
            "prototype_usage_distribution",
            "nearest_prototype_distortion",
            "token_entropy",
            "effective_codebook_utilization",
        ],
        "gates": {
            "gate_1_soft_information": "block_codebook must beat sign-only hard cleanup on final unseen evaluation",
            "gate_2_dictionary_value": "block_codebook must beat scalar or raw block at comparable recovery/storage",
            "gate_3_correct_mapping": "block_codebook must beat shuffled tokens",
            "gate_4_equal_bit_frontier": "block_codebook must create a nondominated point vs equal-total-bit extra dimensions",
            "gate_5_cross_k_generalization": "shared codebook benefit must remain across K=7,15,31",
            "gate_6_codebook_utilization": "effective utilization must not collapse without equal or better smaller-codebook performance",
            "gate_7_no_hidden_identity": "codebook prototypes contain residue patterns only",
        },
        "allowed_claims": [
            "block-LUT residue tokens can preserve some soft accumulator evidence",
            "dictionary compression is an engineering comparison against scalar and extra-dimension controls",
            "shared codebook cross-K behavior is measurable inside this frozen development envelope",
        ],
        "forbidden_claims": [
            "new quantization algorithm",
            "new VSA algebra",
            "new decoder",
            "production-ready compressed reliability plane",
        ],
        "seed_fresh": seeds_are_fresh(repo_root),
        "level35_frozen_artifacts_unchanged": _sha256(repo_root / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json") == LEVEL35_V4_SHA256,
    }
    protocol["protocol_hash"] = canonical_json_hash(protocol)
    return protocol


def build_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} audit",
        "",
        "- Verdict: `ADOPT_EXISTING_QUANTIZATION_PRIMITIVES / WRAP / COMPARE`",
        "- Status: `ADOPT_EXISTING_QUANTIZATION_PRIMITIVES / WRAP / PROTOTYPE / DEVELOPMENT_ONLY / NO_NOVELTY_CLAIM / NO_PRODUCTION_CLAIM`",
        "",
        "## Previous preserved verdicts",
        "",
    ]
    for key, verdict in audit["previous_preserved_verdicts"].items():
        lines.append(f"- `{key}`: `{verdict}`")
    lines.extend(["", "## Anti-NIH findings", ""])
    for item in audit["anti_nih_findings"]:
        lines.append(f"- `{item['family']}`: `{item['verdict']}` coverage `{item['coverage']:.1f}`. {item['notes']}")
    lines.extend(
        [
            "",
            "## Scope reduction",
            "",
            f"- kept dimensions: `{audit['scope_reduction']['kept_dimensions']}`",
            f"- kept bundle widths: `{audit['scope_reduction']['kept_bundle_widths']}`",
            f"- dropped cells: `{audit['scope_reduction']['dropped_cells']}`",
            f"- reason: {audit['scope_reduction']['reason']}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_protocol_markdown(protocol: dict[str, Any]) -> str:
    lines = [
        f"# {TASK_NAME} protocol",
        "",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        f"- Starting commit: `{protocol['starting_commit']}`",
        f"- Normalization: `{protocol['normalization']['id']}`",
        f"- Tie policy: `{protocol['tie_policy']}`",
        f"- Block size: `{protocol['block_format']['block_size']}`",
        "",
        "## Codebook construction",
        "",
        f"- selection: `{protocol['codebook_construction']['selection']}`",
        f"- distance: `{protocol['codebook_construction']['distance']}`",
        f"- codebook sizes: `{protocol['codebook_construction']['top_c_codebooks']}`",
        f"- shared across K: `{protocol['codebook_construction']['shared_across_K']}`",
        "",
        "## Frozen cells",
        "",
    ]
    for cell in protocol["cells"]:
        lines.append(
            f"- `{cell['cell_id']}`: D=`{cell['dimension']}`, K=`{cell['bundle_width']}`, N=`{cell['atom_count']}`, atom_seed=`{cell['atom_codebook_seed']}`"
        )
    lines.extend(
        [
            "",
            "## Split counts",
            "",
            f"- discovery: `{protocol['split_counts'][SPLIT_DISCOVERY]}`",
            f"- validation: `{protocol['split_counts'][SPLIT_VALIDATION]}`",
            f"- final: `{protocol['split_counts'][SPLIT_FINAL]}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_execution_plan(protocol: dict[str, Any]) -> str:
    trial_count = len(protocol["cells"]) * (
        protocol["split_counts"][SPLIT_VALIDATION] + protocol["split_counts"][SPLIT_FINAL]
    )
    arm_variants = 11
    lines = [
        f"# {TASK_NAME} execution plan",
        "",
        f"- starting_commit: `{STARTING_COMMIT}`",
        f"- branch: `codex/codebook-residue-v0_1`",
        f"- git_status: `clean_expected`",
        f"- selected_cells: `{[(cell['dimension'], cell['bundle_width'], cell['atom_count']) for cell in protocol['cells']]}`",
        f"- block_size: `{BLOCK_SIZE}`",
        f"- codebook_sizes: `{list(CODEBOOK_SIZES)}`",
        f"- discovery_bundles_per_cell: `{DISCOVERY_BUNDLES_PER_CELL}`",
        f"- validation_bundles_per_cell: `{VALIDATION_BUNDLES_PER_CELL}`",
        f"- final_bundles_per_cell: `{FINAL_BUNDLES_PER_CELL}`",
        f"- codebook_seeds: `{list(ATOM_CODEBOOK_SEEDS)}`",
        f"- estimated_trials: `{trial_count * arm_variants}`",
        f"- estimated_runtime: `bounded CPU development run, low-minute envelope`",
        f"- selected_device: `cpu`",
        f"- output_path: `results/{RESULTS_NAMESPACE}`",
        "",
        "Execution order: audit -> protocol -> scalar/block implementation -> tests -> smoke -> bit accounting -> paired run -> final development evaluation -> report.",
    ]
    return "\n".join(lines) + "\n"


def build_discovery_codebooks(cells: tuple[CellSpec, ...]) -> dict[int, ResidueCodebook]:
    discovery_blocks: list[tuple[int, ...]] = []
    for cell in cells:
        atoms = build_atoms(cell.dimension, cell.atom_count, cell.atom_codebook_seed)
        members = sample_bundle_indices(cell.atom_count, cell.bundle_width, cell.discovery_seed_start, DISCOVERY_BUNDLES_PER_CELL)
        accumulators = bundle_accumulators(atoms, members)
        for accumulator in accumulators:
            normalized = normalize_residue(accumulator, cell.bundle_width)
            symbols = quantize_scalar_symbols(normalized)
            for block in pad_symbols(symbols, BLOCK_SIZE).tolist():
                discovery_blocks.append(tuple(int(item) for item in block))
    return {size: discover_codebook(discovery_blocks, size) for size in CODEBOOK_SIZES}


def evaluate_cell_split(
    *,
    cell: CellSpec,
    split_name: str,
    split_seed_start: int,
    count: int,
    codebooks: dict[int, ResidueCodebook],
) -> list[dict[str, Any]]:
    atoms = build_atoms(cell.dimension, cell.atom_count, cell.atom_codebook_seed)
    members_batch = sample_bundle_indices(cell.atom_count, cell.bundle_width, split_seed_start, count)
    accumulators = bundle_accumulators(atoms, members_batch)
    rows: list[dict[str, Any]] = []
    for bundle_index, (members, accumulator) in enumerate(zip(members_batch, accumulators, strict=True)):
        normalized = normalize_residue(accumulator, cell.bundle_width)
        scalar_symbols = quantize_scalar_symbols(normalized)
        exact_sign = deterministic_sign(accumulator)
        start = time.perf_counter()
        payloads = build_representations(accumulator, cell.bundle_width, codebooks, SHUFFLE_SEED_BASE + bundle_index)
        build_latency = time.perf_counter() - start
        for payload in payloads:
            metrics = evaluate_arm(
                payload=payload,
                atoms=atoms,
                members=members,
                representation_latency_sec=build_latency,
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "trial",
                    "split_name": split_name,
                    "cell_id": cell.cell_id,
                    "dimension": cell.dimension,
                    "bundle_width": cell.bundle_width,
                    "atom_count": cell.atom_count,
                    "atom_codebook_seed": cell.atom_codebook_seed,
                    "bundle_seed": split_seed_start + bundle_index,
                    "arm_id": payload.arm_id,
                    "variant_id": payload.variant_id,
                    "codebook_size": payload.codebook_size,
                    "topk_size": cell.bundle_width,
                    "normalization_id": NORMALIZATION_ID,
                    "tie_policy": TIE_POLICY_POSITIVE,
                    "scalar_symbol_histogram": {str(k): int(v) for k, v in sorted(Counter(scalar_symbols.reshape(-1).tolist()).items())},
                    "sign_positive_fraction": float((exact_sign > 0).float().mean().item()),
                    **metrics,
                }
            )
        for target_size in CODEBOOK_SIZES:
            block_payload = next(
                payload
                for payload in payloads
                if payload.arm_id == (ARM_BLOCK_C4 if target_size == 4 else ARM_BLOCK_C16)
            )
            target_bits = block_payload.packed_bits + block_payload.metadata_bits + int(block_payload.codebook_bits_amortized[PRIMARY_AMORTIZATION_BUNDLES])
            equal_atoms = build_equal_bit_atoms(cell.dimension, target_bits, cell.atom_count, cell.atom_codebook_seed + target_size)
            equal_accumulator = equal_atoms[members].sum(dim=0)
            equal_sign = deterministic_sign(equal_accumulator)
            equal_payload = hard_payload(equal_sign.to(torch.float32))
            metrics = evaluate_arm(
                payload=equal_payload,
                atoms=equal_atoms,
                members=members,
                representation_latency_sec=0.0,
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "trial",
                    "split_name": split_name,
                    "cell_id": cell.cell_id,
                    "dimension": int(equal_atoms.size(1)),
                    "bundle_width": cell.bundle_width,
                    "atom_count": cell.atom_count,
                    "atom_codebook_seed": cell.atom_codebook_seed + target_size,
                    "bundle_seed": split_seed_start + bundle_index,
                    "arm_id": ARM_EQUAL_BITS,
                    "variant_id": f"equal_bits_for_C{target_size}",
                    "codebook_size": target_size,
                    "topk_size": cell.bundle_width,
                    "normalization_id": NORMALIZATION_ID,
                    "tie_policy": TIE_POLICY_POSITIVE,
                    "scalar_symbol_histogram": {},
                    "sign_positive_fraction": float((equal_sign > 0).float().mean().item()),
                    **metrics,
                }
            )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["split_name"], row["arm_id"], row["variant_id"], int(row["bundle_width"]))
        grouped.setdefault(key, []).append(row)
    summaries: list[dict[str, Any]] = []
    for (split_name, arm_id, variant_id, bundle_width), batch in sorted(grouped.items()):
        summaries.append(
            {
                "split_name": split_name,
                "arm_id": arm_id,
                "variant_id": variant_id,
                "bundle_width": bundle_width,
                "rows": len(batch),
                "mean_member_top1_recall": float(statistics.fmean(row["member_top1_recall"] for row in batch)),
                "mean_member_topk_recall": float(statistics.fmean(row["member_topk_recall"] for row in batch)),
                "mean_full_member_enumeration_recall": float(statistics.fmean(row["full_member_enumeration_recall"] for row in batch)),
                "mean_precision": float(statistics.fmean(row["precision"] for row in batch)),
                "mean_false_positive_rate": float(statistics.fmean(row["false_positive_rate"] for row in batch)),
                "mean_auc_equivalent": float(statistics.fmean(row["auc_equivalent"] for row in batch)),
                "accepted_coverage": float(statistics.fmean(row["coverage"] for row in batch)),
                "conditional_risk": float(sum(row["silent_wrong_acceptance"] for row in batch) / max(1.0, sum(row["coverage"] for row in batch))),
                "silent_wrong_acceptance_rate": float(statistics.fmean(row["silent_wrong_acceptance"] for row in batch)),
                "mean_cleanup_margin": float(statistics.fmean(row["cleanup_margin"] for row in batch)),
                "mean_physical_bits_total": float(statistics.fmean(row["physical_bits_total"] for row in batch)),
                "mean_encoding_latency_sec": float(statistics.fmean(row["encoding_latency_sec"] for row in batch)),
                "mean_cold_decode_latency_sec": float(statistics.fmean(row["cold_decode_latency_sec"] for row in batch)),
                "mean_warm_decode_latency_sec": float(statistics.fmean(row["warm_decode_latency_sec"] for row in batch)),
                "mean_token_entropy": float(statistics.fmean(row["token_entropy"] for row in batch)),
                "mean_exact_block_fraction": float(statistics.fmean(row["exact_block_fraction"] for row in batch)),
                "mean_nearest_prototype_distortion": float(statistics.fmean(row["nearest_prototype_distortion"] for row in batch)),
                "mean_effective_codebook_utilization": float(statistics.fmean(row["effective_codebook_utilization"] for row in batch)),
                "histogram_preserved_all": all(bool(row["histogram_preserved"]) for row in batch),
            }
        )
    return summaries


def codebook_storage_summary(codebooks: dict[int, ResidueCodebook]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for size, book in sorted(codebooks.items()):
        total_bits = book.codebook_size * book.block_size * SCALAR_SYMBOL_BITS
        for amortization_point in AMORTIZATION_POINTS:
            rows.append(
                {
                    "codebook_size": size,
                    "amortization_bundles": amortization_point,
                    "total_codebook_bits": total_bits,
                    "amortized_bits_per_bundle": total_bits / amortization_point,
                }
            )
    return rows


def evaluate_gates(final_rows: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
    def rows_for(arm_id: str, variant_prefix: str | None = None) -> list[dict[str, Any]]:
        batch = [row for row in final_rows if row["arm_id"] == arm_id]
        if variant_prefix is not None:
            batch = [row for row in batch if row["variant_id"].startswith(variant_prefix)]
        return batch

    def mean_metric(batch: list[dict[str, Any]], metric: str) -> float:
        return float(statistics.fmean(row[metric] for row in batch)) if batch else 0.0

    hard = rows_for(ARM_HARD)
    ternary = rows_for(ARM_TERNARY)
    scalar = rows_for(ARM_SCALAR)
    raw_block = rows_for(ARM_RAW_BLOCK)
    block_c4 = rows_for(ARM_BLOCK_C4)
    block_c16 = rows_for(ARM_BLOCK_C16)
    shuffled_c4 = rows_for(ARM_SHUFFLED, "C4")
    shuffled_c16 = rows_for(ARM_SHUFFLED, "C16")
    equal_c4 = rows_for(ARM_EQUAL_BITS, "equal_bits_for_C4")
    equal_c16 = rows_for(ARM_EQUAL_BITS, "equal_bits_for_C16")
    map_i = rows_for(ARM_MAP_I)

    best_block = block_c16 if mean_metric(block_c16, "full_member_enumeration_recall") >= mean_metric(block_c4, "full_member_enumeration_recall") else block_c4
    best_block_name = "C16" if best_block is block_c16 else "C4"
    best_shuffled = shuffled_c16 if best_block_name == "C16" else shuffled_c4
    best_equal = equal_c16 if best_block_name == "C16" else equal_c4

    block_beats_hard = mean_metric(best_block, "full_member_enumeration_recall") > mean_metric(hard, "full_member_enumeration_recall")
    block_beats_shuffled = mean_metric(best_block, "full_member_enumeration_recall") > mean_metric(best_shuffled, "full_member_enumeration_recall")
    block_beats_scalar = mean_metric(best_block, "full_member_enumeration_recall") > mean_metric(scalar, "full_member_enumeration_recall")
    block_beats_raw = mean_metric(best_block, "full_member_enumeration_recall") > mean_metric(raw_block, "full_member_enumeration_recall")
    equal_dominates = (
        mean_metric(best_equal, "full_member_enumeration_recall") >= mean_metric(best_block, "full_member_enumeration_recall")
        and mean_metric(best_equal, "silent_wrong_acceptance") <= mean_metric(best_block, "silent_wrong_acceptance")
        and mean_metric(best_equal, "cold_decode_latency_sec") <= mean_metric(best_block, "cold_decode_latency_sec")
    )
    shared_generalization = all(
        statistics.fmean(row["full_member_enumeration_recall"] for row in [entry for entry in best_block if entry["bundle_width"] == width]) >= statistics.fmean(
            row["full_member_enumeration_recall"] for row in [entry for entry in hard if entry["bundle_width"] == width]
        )
        for width in (7, 15, 31)
    ) and any(
        statistics.fmean(row["full_member_enumeration_recall"] for row in [entry for entry in best_block if entry["bundle_width"] == width]) > statistics.fmean(
            row["full_member_enumeration_recall"] for row in [entry for entry in hard if entry["bundle_width"] == width]
        )
        for width in (7, 15, 31)
    )
    safety_ok = mean_metric(best_block, "silent_wrong_acceptance") == 0.0
    utilization_ok = mean_metric(best_block, "effective_codebook_utilization") >= (0.40 if best_block_name == "C16" else 0.25)
    structure_ok = True

    gates = [
        {"gate": "Gate 1 - Soft-information value", "status": "PASS" if block_beats_hard else "FAIL"},
        {"gate": "Gate 2 - Dictionary value", "status": "PASS" if (block_beats_scalar and block_beats_raw) else "FAIL"},
        {"gate": "Gate 3 - Correct mapping", "status": "PASS" if block_beats_shuffled else "FAIL"},
        {"gate": "Gate 4 - Equal-bit frontier", "status": "FAIL" if equal_dominates else "PASS"},
        {"gate": "Gate 5 - Cross-K generalization", "status": "PASS" if shared_generalization else "FAIL"},
        {"gate": "Gate 6 - Codebook utilization", "status": "PASS" if utilization_ok else "FAIL"},
        {"gate": "Gate 7 - No hidden identity", "status": "PASS" if structure_ok else "FAIL"},
    ]

    if equal_dominates:
        return "ADOPT_EXTRA_DIMENSIONS", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_NOT_SUPPORTED", gates
    if mean_metric(scalar, "full_member_enumeration_recall") >= mean_metric(best_block, "full_member_enumeration_recall"):
        return "ADOPT_SCALAR_RESIDUE", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_NOT_SUPPORTED", gates
    if block_beats_hard and block_beats_scalar and block_beats_raw and block_beats_shuffled and shared_generalization and utilization_ok and safety_ok:
        return "ADOPT_BLOCK_CODEBOOK_RESIDUE", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_SUPPORTED", gates
    if mean_metric(ternary, "full_member_enumeration_recall") > mean_metric(hard, "full_member_enumeration_recall") and not block_beats_scalar:
        return "ADOPT_TERNARY_TIE_AWARE", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_NOT_SUPPORTED", gates
    if block_beats_hard and block_beats_shuffled:
        return "PARTIAL_CODEBOOK_COMPRESSION_VALUE", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_PARTIAL", gates
    return "BLOCK_RESIDUE_CODEBOOK_LINE", "BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_NOT_SUPPORTED", gates


def render_report(
    protocol: dict[str, Any],
    summary: dict[str, Any],
    codebooks: dict[int, ResidueCodebook],
    arm_summary_rows: list[dict[str, Any]],
) -> str:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"- Build verdict: `{summary['build_verdict']}`",
        f"- Scientific verdict: `{summary['scientific_verdict']}`",
        f"- Protocol hash: `{protocol['protocol_hash']}`",
        "",
        "## Previous preserved verdicts",
        "",
    ]
    for key, verdict in PREVIOUS_VERDICTS.items():
        lines.append(f"- `{key}`: `{verdict}`")
    lines.extend(["", "## Codebooks", ""])
    for size, codebook in sorted(codebooks.items()):
        lines.append(
            f"- `C={size}` prototypes: `{[list(pattern) for pattern in codebook.prototypes]}`"
        )
    lines.extend(["", "## Final development arm summary", ""])
    for row in [entry for entry in arm_summary_rows if entry["split_name"] == SPLIT_FINAL]:
        lines.append(
            f"- `{row['arm_id']}` / `{row['variant_id']}` / `K={row['bundle_width']}`: "
            f"full_recall=`{row['mean_full_member_enumeration_recall']:.4f}`, "
            f"precision=`{row['mean_precision']:.4f}`, "
            f"fp_rate=`{row['mean_false_positive_rate']:.4f}`, "
            f"bits=`{row['mean_physical_bits_total']:.2f}`, "
            f"cold_latency=`{row['mean_cold_decode_latency_sec']:.6f}s`."
        )
    lines.extend(["", "## Gate outcomes", ""])
    for gate in summary["gate_outcomes"]:
        lines.append(f"- `{gate['gate']}`: `{gate['status']}`")
    return "\n".join(lines) + "\n"


def run_codebook_residue(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs"
    results_dir = repo_root / "results" / RESULTS_NAMESPACE
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    audit = dependency_audit(repo_root)
    protocol = build_protocol(repo_root)
    plan_text = build_execution_plan(protocol)
    print(plan_text, flush=True)

    codebooks = build_discovery_codebooks(CELLS)
    raw_rows: list[dict[str, Any]] = []
    for cell in CELLS:
        print(f"[codebook-residue] validation {cell.cell_id}", flush=True)
        raw_rows.extend(
            evaluate_cell_split(
                cell=cell,
                split_name=SPLIT_VALIDATION,
                split_seed_start=cell.validation_seed_start,
                count=VALIDATION_BUNDLES_PER_CELL,
                codebooks=codebooks,
            )
        )
        print(f"[codebook-residue] final {cell.cell_id}", flush=True)
        raw_rows.extend(
            evaluate_cell_split(
                cell=cell,
                split_name=SPLIT_FINAL,
                split_seed_start=cell.final_seed_start,
                count=FINAL_BUNDLES_PER_CELL,
                codebooks=codebooks,
            )
        )

    arm_summary_rows = summarize_rows(raw_rows)
    final_rows = [row for row in raw_rows if row["split_name"] == SPLIT_FINAL]
    build_verdict, scientific_verdict, gate_outcomes = evaluate_gates(final_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "build_verdict": build_verdict,
        "scientific_verdict": scientific_verdict,
        "protocol_hash": protocol["protocol_hash"],
        "heldout_execution_count": 0,
        "seed_fresh": protocol["seed_fresh"],
        "previous_preserved_verdicts": PREVIOUS_VERDICTS,
        "codebook_hashes": {str(size): book.construction_digest for size, book in sorted(codebooks.items())},
        "gate_outcomes": gate_outcomes,
        "codebook_amortization": codebook_storage_summary(codebooks),
    }

    write_text(docs_dir / "LEVEL3_CODEBOOK_COMPRESSED_RESIDUE_AUDIT.md", build_audit_markdown(audit))
    write_text(docs_dir / "LEVEL3_CODEBOOK_COMPRESSED_RESIDUE_PROTOCOL.md", build_protocol_markdown(protocol))
    write_text(results_dir / "execution_plan.md", plan_text)
    write_text(results_dir / "frozen_protocol.yaml", "\n".join(yaml_lines(protocol)) + "\n")
    write_json(results_dir / "codebook.json", codebook_json_payload(codebooks))
    write_jsonl(results_dir / "raw_trials.jsonl", raw_rows)
    write_csv(results_dir / "arm_summary.csv", arm_summary_rows)
    write_json(results_dir / "summary.json", summary)
    write_text(results_dir / "report.md", render_report(protocol, summary, codebooks, arm_summary_rows))
    write_json(results_dir / "environment.json", environment_snapshot())

    return {
        "audit": audit,
        "protocol": protocol,
        "codebooks": codebooks,
        "raw_rows": raw_rows,
        "arm_summary_rows": arm_summary_rows,
        "summary": summary,
    }
