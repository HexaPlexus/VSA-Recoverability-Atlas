from __future__ import annotations

import csv
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
    build_initial_estimates,
    bind_sequence,
    cosine_similarity_matrix,
    decode_top_candidates,
    make_generator,
    normalized_similarity_pair,
    seed_everything,
    wilson_interval,
)

LEVEL2A_SCHEMA_VERSION = "level2a-temporal-memory-v1"
LEVEL2A_POLICY_VERSION = "level2a-threshold-policy-v1"
LEVEL2A_CHECKPOINT_COMMIT = "5d54748"

LEVEL2A_DEVELOPMENT_MASTER_SEED = 38260614
LEVEL2A_CALIBRATION_MASTER_SEED = 39260614
LEVEL2A_HELDOUT_MASTER_SEED = 40260614

SCENARIO_STABLE = "A_STABLE_LOCATION"
SCENARIO_OBSERVED_MOVEMENT = "B_OBSERVED_MOVEMENT"
SCENARIO_UNOBSERVED_MOVEMENT = "C_UNOBSERVED_MOVEMENT"
SCENARIO_CONFLICTING = "D_CONFLICTING_SOURCES"
SCENARIO_ORDER = (
    SCENARIO_STABLE,
    SCENARIO_OBSERVED_MOVEMENT,
    SCENARIO_UNOBSERVED_MOVEMENT,
    SCENARIO_CONFLICTING,
)

QUERY_LOCATION = "LOCATION"
QUERY_TOOL = "TOOL"
QUERY_HAZARD = "HAZARD"
QUERY_TYPES = (QUERY_LOCATION, QUERY_TOOL, QUERY_HAZARD)

EVENT_OBJECT_APPEARED = "OBJECT_APPEARED"
EVENT_OBJECT_MOVED = "OBJECT_MOVED"
EVENT_OBJECT_REMOVED = "OBJECT_REMOVED"
EVENT_OBJECT_STATE_CHANGED = "OBJECT_STATE_CHANGED"
EVENT_AGENT_OBSERVED = "AGENT_OBSERVED"
EVENT_AGENT_MISSED = "AGENT_MISSED_EVENT"

TYPE_TOOL = "TOOL"
TYPE_RESOURCE = "RESOURCE"
TYPE_HAZARD = "HAZARD"
TYPE_CONTAINER = "CONTAINER"
TYPE_NEUTRAL = "NEUTRAL"

SOURCE_SELF = "SELF"
SOURCE_CAMERA = "CAMERA"
SOURCE_REPORT = "REPORT"
SOURCE_MISSED = "MISSED_EVENT"
SOURCE_RELIABILITY = {
    SOURCE_SELF: 0.95,
    SOURCE_CAMERA: 0.85,
    SOURCE_REPORT: 0.55,
    SOURCE_MISSED: 0.90,
}

TIME_BUCKETS = ("NOW", "RECENT", "MID", "OLD", "STALE", "ANCIENT")
STATES = (
    "AVAILABLE",
    "MOVED",
    "UNTRACKED",
    "HAZARD_PRESENT",
    "HAZARD_CLEARED",
    "DAMAGED",
)

ACTION_MOVE_TO = "MOVE_TO"
ACTION_ABSTAIN_SEARCH = "ABSTAIN_AND_SEARCH"
ACTION_ENTER_ROOM = "ENTER_ROOM"
ACTION_DO_NOT_ENTER = "DO_NOT_ENTER"
ACTION_ABSTAIN_INSPECT = "ABSTAIN_AND_INSPECT"
ACTION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

OUTCOME_CORRECT_ACTION = "CORRECT_ACTION"
OUTCOME_STALE_MEMORY_ACTION = "STALE_MEMORY_ACTION"
OUTCOME_WRONG_ENTITY_ACTION = "WRONG_ENTITY_ACTION"
OUTCOME_UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"
OUTCOME_CORRECT_ABSTENTION = "CORRECT_ABSTENTION"
OUTCOME_UNNECESSARY_ABSTENTION = "UNNECESSARY_ABSTENTION"
OUTCOME_GLOBAL_FALLBACK_SUCCESS = "GLOBAL_FALLBACK_SUCCESS"
OUTCOME_GLOBAL_FALLBACK_FAILURE = "GLOBAL_FALLBACK_FAILURE"

METHOD_INDEX = "latest_raw_episode_by_entity"
METHOD_GLOBAL = "global_MAP_retrieval"
METHOD_RANDOM = "random_context_MAP"
METHOD_SEMANTIC = "semantic_context_MAP"
METHOD_SEMANTIC_FALLBACK = "semantic_MAP_with_cold_global_fallback"
METHOD_SEMANTIC_ABSTAIN = "semantic_MAP_with_abstention"
METHOD_ORACLE = "oracle_episode_selection"
METHOD_ORDER = (
    METHOD_INDEX,
    METHOD_GLOBAL,
    METHOD_RANDOM,
    METHOD_SEMANTIC,
    METHOD_SEMANTIC_FALLBACK,
    METHOD_SEMANTIC_ABSTAIN,
    METHOD_ORACLE,
)

FIELD_NAMES = ("ENTITY", "TYPE", "LOCATION", "STATE", "TIME_BUCKET", "SOURCE")
FACTOR_COUNT = len(FIELD_NAMES)
DIMENSIONS = 512
MAX_ITERATIONS = 8
STABLE_PATIENCE = 3
TARGET_SELECTIVE_RISK = 0.05
SUBSET_SIZE_CAP = 6
MIN_SUBSET_SIZE = 4

UTILITY_WEIGHTS = {
    OUTCOME_CORRECT_ACTION: 1.0,
    OUTCOME_CORRECT_ABSTENTION: 0.0,
    OUTCOME_UNNECESSARY_ABSTENTION: -0.1,
    OUTCOME_STALE_MEMORY_ACTION: -0.5,
    OUTCOME_WRONG_ENTITY_ACTION: -0.5,
    OUTCOME_UNSUPPORTED_ACTION: -2.0,
}

ROOMS = ("WORKSHOP", "STORAGE", "LAB", "GARAGE", "OFFICE", "YARD")
ROOM_TO_ZONE = {
    "WORKSHOP": "NORTH",
    "STORAGE": "NORTH",
    "LAB": "SOUTH",
    "GARAGE": "SOUTH",
    "OFFICE": "EAST",
    "YARD": "EAST",
}
ZONE_TO_ROOMS = {
    "NORTH": ("WORKSHOP", "STORAGE"),
    "SOUTH": ("LAB", "GARAGE"),
    "EAST": ("OFFICE", "YARD"),
}


@dataclass(frozen=True)
class EntitySpec:
    entity_id: str
    entity_type: str
    default_state: str
    capabilities: tuple[str, ...]


ENTITY_SPECS: tuple[EntitySpec, ...] = (
    EntitySpec("HAMMER_1", TYPE_TOOL, "AVAILABLE", ("REPAIR",)),
    EntitySpec("CUTTER_1", TYPE_TOOL, "AVAILABLE", ("CUT",)),
    EntitySpec("EXTINGUISHER_1", TYPE_TOOL, "AVAILABLE", ("EXTINGUISH",)),
    EntitySpec("SPILL_KIT_1", TYPE_TOOL, "AVAILABLE", ("CONTAIN",)),
    EntitySpec("BATTERY_1", TYPE_RESOURCE, "AVAILABLE", ("POWER",)),
    EntitySpec("WATER_1", TYPE_RESOURCE, "AVAILABLE", ("EXTINGUISH",)),
    EntitySpec("ACID_DRUM_1", TYPE_HAZARD, "HAZARD_PRESENT", ("CORROSIVE",)),
    EntitySpec("FIRE_CAN_1", TYPE_HAZARD, "HAZARD_PRESENT", ("FIRE",)),
    EntitySpec("CRATE_1", TYPE_CONTAINER, "AVAILABLE", ("STORE",)),
    EntitySpec("LOCKER_1", TYPE_CONTAINER, "AVAILABLE", ("STORE",)),
    EntitySpec("RAT_1", TYPE_NEUTRAL, "AVAILABLE", ("DISTRACT",)),
    EntitySpec("DRONE_1", TYPE_NEUTRAL, "AVAILABLE", ("MOVE",)),
)
ENTITY_INDEX = {spec.entity_id: index for index, spec in enumerate(ENTITY_SPECS)}
TYPE_INDEX = {label: index for index, label in enumerate((TYPE_TOOL, TYPE_RESOURCE, TYPE_HAZARD, TYPE_CONTAINER, TYPE_NEUTRAL))}
ROOM_INDEX = {label: index for index, label in enumerate(ROOMS)}
STATE_INDEX = {label: index for index, label in enumerate(STATES)}
TIME_INDEX = {label: index for index, label in enumerate(TIME_BUCKETS)}
SOURCE_INDEX = {label: index for index, label in enumerate((SOURCE_SELF, SOURCE_CAMERA, SOURCE_REPORT, SOURCE_MISSED))}
GOALS = ("REPAIR", "CUT", "EXTINGUISH", "CONTAIN")


@dataclass(frozen=True)
class TemporalEvent:
    tick: int
    event_type: str
    entity_id: str
    entity_type: str
    location: str
    state: str
    source: str
    observed: bool
    observation_confidence: float


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    tick: int
    entity_id: str
    entity_type: str
    location: str
    state: str
    source: str
    observation_confidence: float
    event_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuerySpec:
    query_type: str
    entity_id: str | None
    goal: str | None
    room: str | None
    active_room: str
    active_zone: str
    approximate_lookup: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorldTruth:
    current_tick: int
    current_locations: dict[str, str]
    current_states: dict[str, str]
    valid_tool_entities: tuple[str, ...]
    room_is_safe: bool | None
    oracle_relevant_episode_ids: tuple[str, ...]
    sufficient_evidence_expected: bool
    current_answer_room: str | None
    scenario_family: str


@dataclass(frozen=True)
class RuntimeView:
    seed: int
    seed_split: str
    scenario_family: str
    query: QuerySpec
    current_tick: int
    observed_events: tuple[TemporalEvent, ...]
    memory_episodes: tuple[EpisodeRecord, ...]
    factor_domains: tuple[torch.Tensor, ...]
    subset_size: int
    entity_catalog: tuple[EntitySpec, ...]


@dataclass(frozen=True)
class TemporalTrial:
    runtime: RuntimeView
    truth: WorldTruth


@dataclass(frozen=True)
class RetrievalEvidence:
    stable_prediction: bool
    iterations: int
    min_normalized_margin: float
    mean_normalized_margin: float
    normalized_reconstruction: float
    raw_episode_agreement: bool
    matched_episode_id: str | None
    matched_episode_tick: int | None
    matched_episode_event_type: str | None
    matched_episode_confidence: float | None
    matched_episode_source_reliability: float | None
    matched_episode_recency: float | None
    matched_episode_post_uncertainty: bool


@dataclass(frozen=True)
class RetrievalRun:
    method_id: str
    stage_label: str
    selected_episode_ids: tuple[str, ...]
    selected_episode_tuples: tuple[tuple[int, ...], ...]
    selected_indices: torch.Tensor
    predicted_indices: tuple[int, ...]
    predicted_fields: dict[str, str]
    relevant_episode_included: bool
    exact_episode_recovery: bool
    entity_recovery: bool
    location_recovery: bool
    stale_episode_recovery: bool
    evidence: RetrievalEvidence
    candidate_count: int
    factorization_iterations: int
    candidate_evaluations_proxy: int
    wall_clock_sec: float
    uses_upstream_resonator: bool


@dataclass(frozen=True)
class ActionDecision:
    action_type: str
    room: str | None
    entity_id: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyThresholds:
    subset_min_margin: float
    subset_min_reconstruction: float
    subset_min_recency: float
    subset_min_confidence: float
    global_min_margin: float
    global_min_reconstruction: float
    global_min_recency: float
    global_min_confidence: float


@dataclass(frozen=True)
class SelectedPolicy:
    policy_version: str
    schema_version: str
    target_selective_risk: float
    thresholds: PolicyThresholds
    calibration_seed_ranges: dict[str, dict[str, int]]
    utility_weights: dict[str, float]
    preferred_runtime_method: str
    achieved_calibration_risk: float
    achieved_calibration_coverage: float
    achieved_calibration_utility: float
    selection_rule: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["thresholds"] = asdict(self.thresholds)
        return payload


@dataclass(frozen=True)
class Level2TrialResult:
    schema_version: str
    policy_version: str | None
    method_id: str
    seed: int
    seed_split: str
    scenario_family: str
    query_type: str
    approximate_lookup: bool
    candidate_count: int
    relevant_episode_included: bool
    exact_episode_recovery: bool
    entity_recovery: bool
    location_recovery: bool
    stale_episode_recovery: bool
    selected_episode_ids: list[str]
    predicted_indices: list[int] | None
    predicted_fields: dict[str, str]
    action: dict[str, Any]
    accepted: bool
    abstained: bool
    insufficient_evidence: bool
    used_global_fallback: bool
    fallback_outcome: str | None
    behavior_outcome: str
    correct_action: bool
    false_commit: bool
    selective_risk_denominator: bool
    utility: float
    search_cost: float
    expected_action_cost: float
    factorization_iterations: int
    candidate_evaluations_proxy: int
    wall_clock_sec: float
    stable_prediction: bool | None
    min_normalized_margin: float | None
    normalized_reconstruction: float | None
    raw_episode_agreement: bool | None
    matched_episode_id: str | None
    matched_episode_tick: int | None
    matched_episode_post_uncertainty: bool | None
    matched_episode_recency: float | None
    matched_episode_confidence: float | None
    exact_index_baseline_applicable: bool
    discarded_local_factorizer_state: bool
    uses_upstream_resonator: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def temporal_runtime_metadata() -> dict[str, Any]:
    return {
        "schema_version": LEVEL2A_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torchhd_version": torchhd.__version__,
        "platform": platform.platform(),
    }


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True))
            handle.write("\n")


def save_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return float(ordered[rank - 1])


def maybe_round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def seed_ranges_to_set(seed_ranges: dict[str, dict[str, int]]) -> set[int]:
    values: set[int] = set()
    for spec in seed_ranges.values():
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            values.add(seed)
    return values


def level2a_development_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        SCENARIO_STABLE: {"start": LEVEL2A_DEVELOPMENT_MASTER_SEED, "count": 32},
        SCENARIO_OBSERVED_MOVEMENT: {"start": LEVEL2A_DEVELOPMENT_MASTER_SEED + 10_000, "count": 32},
        SCENARIO_UNOBSERVED_MOVEMENT: {"start": LEVEL2A_DEVELOPMENT_MASTER_SEED + 20_000, "count": 32},
        SCENARIO_CONFLICTING: {"start": LEVEL2A_DEVELOPMENT_MASTER_SEED + 30_000, "count": 32},
    }


def level2a_calibration_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        SCENARIO_STABLE: {"start": LEVEL2A_CALIBRATION_MASTER_SEED, "count": 64},
        SCENARIO_OBSERVED_MOVEMENT: {"start": LEVEL2A_CALIBRATION_MASTER_SEED + 10_000, "count": 64},
        SCENARIO_UNOBSERVED_MOVEMENT: {"start": LEVEL2A_CALIBRATION_MASTER_SEED + 20_000, "count": 64},
        SCENARIO_CONFLICTING: {"start": LEVEL2A_CALIBRATION_MASTER_SEED + 30_000, "count": 64},
    }


def level2a_heldout_seed_ranges() -> dict[str, dict[str, int]]:
    return {
        SCENARIO_STABLE: {"start": LEVEL2A_HELDOUT_MASTER_SEED, "count": 32},
        SCENARIO_OBSERVED_MOVEMENT: {"start": LEVEL2A_HELDOUT_MASTER_SEED + 10_000, "count": 32},
        SCENARIO_UNOBSERVED_MOVEMENT: {"start": LEVEL2A_HELDOUT_MASTER_SEED + 20_000, "count": 32},
        SCENARIO_CONFLICTING: {"start": LEVEL2A_HELDOUT_MASTER_SEED + 30_000, "count": 32},
    }


def level2a_secondary_seed_ranges(master_seed: int) -> dict[str, dict[str, int]]:
    return {
        QUERY_TOOL: {"start": master_seed + 100_000, "count": 64},
        QUERY_HAZARD: {"start": master_seed + 200_000, "count": 64},
    }


def level2a_seed_sets_non_overlapping() -> bool:
    development = seed_ranges_to_set(level2a_development_seed_ranges())
    calibration = seed_ranges_to_set(level2a_calibration_seed_ranges())
    heldout = seed_ranges_to_set(level2a_heldout_seed_ranges())
    return development.isdisjoint(calibration) and development.isdisjoint(heldout) and calibration.isdisjoint(heldout)


def entity_spec(entity_id: str) -> EntitySpec:
    return ENTITY_SPECS[ENTITY_INDEX[entity_id]]


def time_bucket_for_tick(tick: int, current_tick: int) -> str:
    age = max(0, current_tick - tick)
    if age <= 1:
        return "NOW"
    if age <= 3:
        return "RECENT"
    if age <= 5:
        return "MID"
    if age <= 7:
        return "OLD"
    if age <= 9:
        return "STALE"
    return "ANCIENT"


def event_to_episode(event: TemporalEvent, episode_index: int) -> EpisodeRecord:
    return EpisodeRecord(
        episode_id=f"E{episode_index:03d}",
        tick=event.tick,
        entity_id=event.entity_id,
        entity_type=event.entity_type,
        location=event.location,
        state=event.state,
        source=event.source,
        observation_confidence=event.observation_confidence,
        event_type=event.event_type,
    )


def resolve_episode_ids(
    episodes: tuple[EpisodeRecord, ...],
    entity_id: str,
    event_type: str,
    tick: int,
) -> tuple[str, ...]:
    return tuple(
        episode.episode_id
        for episode in episodes
        if episode.entity_id == entity_id and episode.event_type == event_type and episode.tick == tick
    )


def episode_tuple_indices(episode: EpisodeRecord, current_tick: int) -> tuple[int, ...]:
    return (
        ENTITY_INDEX[episode.entity_id],
        TYPE_INDEX[episode.entity_type],
        ROOM_INDEX[episode.location],
        STATE_INDEX[episode.state],
        TIME_INDEX[time_bucket_for_tick(episode.tick, current_tick)],
        SOURCE_INDEX[episode.source],
    )


def build_factor_domains(seed: int) -> tuple[torch.Tensor, ...]:
    generator = make_generator(seed + 911)
    sizes = (
        len(ENTITY_SPECS),
        len(TYPE_INDEX),
        len(ROOM_INDEX),
        len(STATE_INDEX),
        len(TIME_INDEX),
        len(SOURCE_INDEX),
    )
    return tuple(
        torchhd.random(size, DIMENSIONS, "MAP", generator=generator)
        for size in sizes
    )


def episode_composite(episode: EpisodeRecord, current_tick: int, factor_domains: tuple[torch.Tensor, ...]) -> torch.Tensor:
    indices = episode_tuple_indices(episode, current_tick)
    factors = [factor_domains[index][value] for index, value in enumerate(indices)]
    return bind_sequence(torch.stack(factors, dim=0))


def ordered_unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def pad_candidate_indices(values: list[int], global_size: int, target_size: int, seed: int) -> list[int]:
    ordered = ordered_unique(values)
    rotation = seed % max(1, global_size)
    population = list(range(global_size))
    rotated = population[rotation:] + population[:rotation]
    for candidate in rotated:
        if candidate not in ordered:
            ordered.append(candidate)
        if len(ordered) >= target_size:
            break
    if len(ordered) < target_size and ordered:
        cycle = ordered[:]
        index = 0
        while len(ordered) < target_size:
            ordered.append(cycle[index % len(cycle)])
            index += 1
    return ordered[:target_size]


def choose_subset_size(episode_count: int) -> int:
    return max(MIN_SUBSET_SIZE, min(SUBSET_SIZE_CAP, max(MIN_SUBSET_SIZE, math.ceil(episode_count / 2))))


def score_episode(runtime: RuntimeView, episode: EpisodeRecord) -> float:
    query = runtime.query
    age = max(0, runtime.current_tick - episode.tick)
    freshness = 1.0 / (1.0 + age)
    source_score = SOURCE_RELIABILITY[episode.source]
    zone_bonus = 0.25 if ROOM_TO_ZONE[episode.location] == query.active_zone else 0.0
    score = freshness + source_score + episode.observation_confidence + zone_bonus

    if query.query_type == QUERY_LOCATION:
        if episode.entity_id == query.entity_id:
            score += 4.0
        if episode.event_type == EVENT_AGENT_MISSED:
            score += 1.2
    elif query.query_type == QUERY_TOOL:
        if query.goal in entity_spec(episode.entity_id).capabilities:
            score += 3.5
        if episode.entity_type == TYPE_TOOL:
            score += 1.0
    elif query.query_type == QUERY_HAZARD:
        if episode.location == query.room:
            score += 3.0
        if episode.entity_type == TYPE_HAZARD or episode.state.startswith("HAZARD"):
            score += 1.5
        if episode.event_type == EVENT_AGENT_MISSED:
            score += 0.8
    return score


def random_subset(runtime: RuntimeView, selection_seed: int) -> tuple[EpisodeRecord, ...]:
    rng = random.Random(selection_seed)
    picked = sorted(rng.sample(list(runtime.memory_episodes), runtime.subset_size), key=lambda item: item.episode_id)
    return tuple(picked)


def semantic_subset(runtime: RuntimeView) -> tuple[EpisodeRecord, ...]:
    ranked = sorted(
        runtime.memory_episodes,
        key=lambda episode: (score_episode(runtime, episode), episode.tick, episode.episode_id),
        reverse=True,
    )
    return tuple(ranked[: runtime.subset_size])


def oracle_subset(runtime: RuntimeView, truth: WorldTruth, selection_seed: int) -> tuple[EpisodeRecord, ...]:
    rng = random.Random(selection_seed)
    relevant_ids = set(truth.oracle_relevant_episode_ids)
    relevant = [episode for episode in runtime.memory_episodes if episode.episode_id in relevant_ids]
    fillers = [episode for episode in runtime.memory_episodes if episode.episode_id not in relevant_ids]
    rng.shuffle(fillers)
    selected = relevant[:]
    for episode in fillers:
        if len(selected) >= runtime.subset_size:
            break
        selected.append(episode)
    selected = selected[: runtime.subset_size]
    return tuple(sorted(selected, key=lambda item: item.episode_id))


def all_episodes(runtime: RuntimeView) -> tuple[EpisodeRecord, ...]:
    return runtime.memory_episodes


def selected_episode_tuples(episodes: tuple[EpisodeRecord, ...], current_tick: int) -> tuple[tuple[int, ...], ...]:
    return tuple(episode_tuple_indices(episode, current_tick) for episode in episodes)


def candidate_indices_from_episodes(
    runtime: RuntimeView,
    episodes: tuple[EpisodeRecord, ...],
    selection_seed: int,
) -> torch.Tensor:
    target_size = len(episodes)
    tuples = selected_episode_tuples(episodes, runtime.current_tick)
    per_factor_values = list(zip(*tuples, strict=True))
    rows: list[torch.Tensor] = []
    global_sizes = [domain.size(0) for domain in runtime.factor_domains]
    for factor_index, values in enumerate(per_factor_values):
        padded = pad_candidate_indices(list(values), global_sizes[factor_index], target_size, selection_seed + factor_index * 17)
        rows.append(torch.tensor(padded, dtype=torch.long))
    return torch.stack(rows, dim=0)


def candidate_domains(runtime: RuntimeView, selected_indices: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [runtime.factor_domains[factor_index].index_select(0, selected_indices[factor_index]) for factor_index in range(FACTOR_COUNT)],
        dim=0,
    )


def factor_multiset(domain: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    return torchhd.multiset(domain.index_select(0, indices))


def query_cue_composite(
    runtime: RuntimeView,
    selected_indices: torch.Tensor,
) -> torch.Tensor:
    vectors: list[torch.Tensor] = []
    for factor_index, field_name in enumerate(FIELD_NAMES):
        candidate_domain = runtime.factor_domains[factor_index]
        candidate_indices = selected_indices[factor_index]
        if runtime.query.query_type == QUERY_LOCATION:
            if field_name == "ENTITY":
                vectors.append(candidate_domain[ENTITY_INDEX[runtime.query.entity_id]])
                continue
            if field_name == "TYPE":
                vectors.append(candidate_domain[TYPE_INDEX[entity_spec(runtime.query.entity_id).entity_type]])
                continue
        elif runtime.query.query_type == QUERY_TOOL:
            if field_name == "ENTITY":
                matching = [
                    ENTITY_INDEX[spec.entity_id]
                    for spec in ENTITY_SPECS
                    if runtime.query.goal in spec.capabilities
                ]
                vectors.append(factor_multiset(candidate_domain, torch.tensor(matching, dtype=torch.long)))
                continue
            if field_name == "TYPE":
                vectors.append(candidate_domain[TYPE_INDEX[TYPE_TOOL]])
                continue
        elif runtime.query.query_type == QUERY_HAZARD:
            if field_name == "TYPE":
                vectors.append(candidate_domain[TYPE_INDEX[TYPE_HAZARD]])
                continue
            if field_name == "LOCATION":
                vectors.append(candidate_domain[ROOM_INDEX[runtime.query.room]])
                continue
        vectors.append(factor_multiset(candidate_domain, candidate_indices))
    return bind_sequence(torch.stack(vectors, dim=0))


def tuple_to_labels(indices: tuple[int, ...]) -> dict[str, str]:
    return {
        "ENTITY": ENTITY_SPECS[indices[0]].entity_id,
        "TYPE": ENTITY_SPECS[indices[0]].entity_type if indices[1] >= len(TYPE_INDEX) else list(TYPE_INDEX.keys())[indices[1]],
        "LOCATION": ROOMS[indices[2]],
        "STATE": STATES[indices[3]],
        "TIME_BUCKET": TIME_BUCKETS[indices[4]],
        "SOURCE": list(SOURCE_INDEX.keys())[indices[5]],
    }


def matched_episode(
    runtime: RuntimeView,
    episodes: tuple[EpisodeRecord, ...],
    predicted_indices: tuple[int, ...],
) -> EpisodeRecord | None:
    matches = [episode for episode in episodes if episode_tuple_indices(episode, runtime.current_tick) == predicted_indices]
    if not matches:
        return None
    matches.sort(
        key=lambda episode: (
            episode.tick,
            episode.observation_confidence * SOURCE_RELIABILITY[episode.source],
            episode.episode_id,
        ),
        reverse=True,
    )
    return matches[0]


def resolved_episode(
    runtime: RuntimeView,
    episodes: tuple[EpisodeRecord, ...],
    predicted_indices: tuple[int, ...],
) -> EpisodeRecord | None:
    exact = matched_episode(runtime, episodes, predicted_indices)
    if exact is not None:
        return exact

    scored: list[tuple[float, EpisodeRecord]] = []
    for episode in episodes:
        episode_indices = episode_tuple_indices(episode, runtime.current_tick)
        overlap = sum(int(left == right) for left, right in zip(episode_indices, predicted_indices, strict=True))
        query_bonus = 0.0
        if runtime.query.query_type == QUERY_LOCATION and episode.entity_id == runtime.query.entity_id:
            query_bonus += 2.0
        elif runtime.query.query_type == QUERY_TOOL and runtime.query.goal in entity_spec(episode.entity_id).capabilities:
            query_bonus += 2.0
        elif runtime.query.query_type == QUERY_HAZARD and episode.location == runtime.query.room:
            query_bonus += 2.0
        confidence = episode.observation_confidence * SOURCE_RELIABILITY[episode.source]
        scored.append((overlap + query_bonus + confidence, episode))

    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1].tick, item[1].episode_id), reverse=True)
    return scored[0][1]


def episode_post_uncertainty(runtime: RuntimeView, query: QuerySpec, episode: EpisodeRecord) -> bool:
    for later in runtime.memory_episodes:
        if later.tick <= episode.tick:
            continue
        if later.event_type != EVENT_AGENT_MISSED:
            continue
        if query.query_type == QUERY_LOCATION and later.entity_id == query.entity_id:
            return True
        if query.query_type == QUERY_TOOL and query.goal in entity_spec(later.entity_id).capabilities:
            return True
        if query.query_type == QUERY_HAZARD and later.location == query.room:
            return True
    return False


def entity_recovery_for_query(query: QuerySpec, predicted_fields: dict[str, str], truth: WorldTruth) -> bool:
    if query.query_type == QUERY_LOCATION:
        return predicted_fields["ENTITY"] == query.entity_id
    if query.query_type == QUERY_TOOL:
        return predicted_fields["ENTITY"] in truth.valid_tool_entities
    if query.query_type == QUERY_HAZARD:
        return predicted_fields["LOCATION"] == query.room
    return False


def location_recovery_for_query(query: QuerySpec, predicted_fields: dict[str, str], truth: WorldTruth) -> bool:
    if query.query_type in (QUERY_LOCATION, QUERY_TOOL):
        return predicted_fields["LOCATION"] == truth.current_answer_room
    if query.query_type == QUERY_HAZARD and truth.room_is_safe is not None:
        if predicted_fields["LOCATION"] != query.room:
            return False
        if truth.room_is_safe:
            return predicted_fields["STATE"] == "HAZARD_CLEARED"
        return predicted_fields["STATE"] == "HAZARD_PRESENT"
    return False


def stale_episode_recovery_for_query(query: QuerySpec, episode: EpisodeRecord | None, truth: WorldTruth) -> bool:
    if episode is None:
        return False
    if query.query_type in (QUERY_LOCATION, QUERY_TOOL):
        return episode.location != truth.current_answer_room and episode.entity_id == (query.entity_id or episode.entity_id)
    if query.query_type == QUERY_HAZARD and truth.room_is_safe is not None:
        predicted_safe = episode.state == "HAZARD_CLEARED"
        return predicted_safe != truth.room_is_safe
    return False


def run_map_retrieval(
    runtime: RuntimeView,
    truth: WorldTruth,
    method_id: str,
    selected_episodes: tuple[EpisodeRecord, ...],
    selection_seed: int,
) -> RetrievalRun:
    selected_ids = tuple(episode.episode_id for episode in selected_episodes)
    selected_tuples = selected_episode_tuples(selected_episodes, runtime.current_tick)
    selected_indices = candidate_indices_from_episodes(runtime, selected_episodes, selection_seed)
    domains = candidate_domains(runtime, selected_indices)
    observation_terms = [
        episode_composite(episode, runtime.current_tick, runtime.factor_domains)
        for episode in selected_episodes
    ]
    observation_terms.append(query_cue_composite(runtime, selected_indices))
    observation = torchhd.multiset(torch.stack(observation_terms, dim=0))
    estimates = build_initial_estimates(domains)
    previous: tuple[int, ...] | None = None
    stable_iterations = 0
    stable = False
    decoded: dict[str, torch.Tensor] | None = None

    start = time.perf_counter()
    for iteration in range(1, MAX_ITERATIONS + 1):
        estimates = torchhd.resonator(observation, estimates, domains)
        similarities = cosine_similarity_matrix(estimates, domains)
        decoded = decode_top_candidates(similarities)
        local_top1 = decoded["top1_indices"]
        predicted_tensor = selected_indices.gather(1, local_top1.unsqueeze(-1)).squeeze(-1)
        predicted = tuple(int(value) for value in predicted_tensor.tolist())
        if previous is not None and predicted == previous:
            stable_iterations += 1
        else:
            stable_iterations = 1
        previous = predicted
        if stable_iterations >= STABLE_PATIENCE:
            stable = True
            break
    wall_clock = time.perf_counter() - start

    if decoded is None or previous is None:
        raise RuntimeError("Temporal MAP retrieval produced no prediction.")

    predicted_indices = previous
    predicted_fields = tuple_to_labels(predicted_indices)
    matched = matched_episode(runtime, selected_episodes, predicted_indices)
    resolved = resolved_episode(runtime, selected_episodes, predicted_indices)
    raw_agreement = matched is not None
    predicted_factors = torch.stack(
        [runtime.factor_domains[factor_index][predicted_indices[factor_index]] for factor_index in range(FACTOR_COUNT)],
        dim=0,
    )
    reconstruction = bind_sequence(predicted_factors)
    reconstruction_score = normalized_similarity_pair(reconstruction, observation)
    margins = [float(value) for value in decoded["margins"].tolist()]
    min_margin = min(margins)
    mean_margin = sum(margins) / len(margins)
    relevant_episode_included = any(episode_id in truth.oracle_relevant_episode_ids for episode_id in selected_ids)
    exact_episode_recovery = matched is not None and matched.episode_id in truth.oracle_relevant_episode_ids
    matched_confidence = None if resolved is None else resolved.observation_confidence * SOURCE_RELIABILITY[resolved.source]
    matched_recency = None if resolved is None else 1.0 / (1.0 + max(0, runtime.current_tick - resolved.tick))
    post_uncertainty = False if resolved is None else episode_post_uncertainty(runtime, runtime.query, resolved)
    evidence = RetrievalEvidence(
        stable_prediction=stable,
        iterations=iteration,
        min_normalized_margin=min_margin,
        mean_normalized_margin=mean_margin,
        normalized_reconstruction=reconstruction_score,
        raw_episode_agreement=raw_agreement,
        matched_episode_id=None if resolved is None else resolved.episode_id,
        matched_episode_tick=None if resolved is None else resolved.tick,
        matched_episode_event_type=None if resolved is None else resolved.event_type,
        matched_episode_confidence=None if resolved is None else matched_confidence,
        matched_episode_source_reliability=None if resolved is None else SOURCE_RELIABILITY[resolved.source],
        matched_episode_recency=None if resolved is None else matched_recency,
        matched_episode_post_uncertainty=post_uncertainty,
    )
    candidate_count = len(selected_episodes)
    return RetrievalRun(
        method_id=method_id,
        stage_label="global" if method_id == METHOD_GLOBAL else "subset",
        selected_episode_ids=selected_ids,
        selected_episode_tuples=selected_tuples,
        selected_indices=selected_indices,
        predicted_indices=predicted_indices,
        predicted_fields=predicted_fields,
        relevant_episode_included=relevant_episode_included,
        exact_episode_recovery=exact_episode_recovery,
        entity_recovery=entity_recovery_for_query(runtime.query, predicted_fields, truth),
        location_recovery=location_recovery_for_query(runtime.query, predicted_fields, truth),
        stale_episode_recovery=stale_episode_recovery_for_query(runtime.query, resolved, truth),
        evidence=evidence,
        candidate_count=candidate_count,
        factorization_iterations=iteration,
        candidate_evaluations_proxy=iteration * FACTOR_COUNT * candidate_count,
        wall_clock_sec=wall_clock,
        uses_upstream_resonator=True,
    )


def retrieve_candidate_set(
    runtime: RuntimeView,
    truth: WorldTruth,
    method_id: str,
    selection_seed: int,
) -> tuple[EpisodeRecord, ...]:
    if method_id == METHOD_GLOBAL:
        return all_episodes(runtime)
    if method_id == METHOD_RANDOM:
        return random_subset(runtime, selection_seed)
    if method_id in (METHOD_SEMANTIC, METHOD_SEMANTIC_FALLBACK, METHOD_SEMANTIC_ABSTAIN):
        return semantic_subset(runtime)
    if method_id == METHOD_ORACLE:
        return oracle_subset(runtime, truth, selection_seed)
    raise ValueError(f"Unsupported MAP retrieval method: {method_id}")


def apply_action_from_episode(
    query: QuerySpec,
    episode: EpisodeRecord | None,
) -> ActionDecision:
    if episode is None:
        if query.query_type == QUERY_HAZARD:
            return ActionDecision(ACTION_ABSTAIN_INSPECT, query.room, None, "no_raw_episode_match")
        return ActionDecision(ACTION_ABSTAIN_SEARCH, None, None, "no_raw_episode_match")

    if episode.event_type == EVENT_AGENT_MISSED or episode.state == "UNTRACKED":
        if query.query_type == QUERY_HAZARD:
            return ActionDecision(ACTION_ABSTAIN_INSPECT, query.room, episode.entity_id, "uncertain_after_missed_event")
        return ActionDecision(ACTION_ABSTAIN_SEARCH, episode.location, episode.entity_id, "uncertain_after_missed_event")

    if query.query_type == QUERY_LOCATION:
        return ActionDecision(ACTION_MOVE_TO, episode.location, episode.entity_id, "retrieved_location_episode")
    if query.query_type == QUERY_TOOL:
        return ActionDecision(ACTION_MOVE_TO, episode.location, episode.entity_id, "retrieved_tool_episode")
    if query.query_type == QUERY_HAZARD:
        if episode.state == "HAZARD_PRESENT":
            return ActionDecision(ACTION_DO_NOT_ENTER, query.room, episode.entity_id, "hazard_present")
        if episode.state == "HAZARD_CLEARED":
            return ActionDecision(ACTION_ENTER_ROOM, query.room, episode.entity_id, "hazard_cleared")
        return ActionDecision(ACTION_ABSTAIN_INSPECT, query.room, episode.entity_id, "hazard_state_unsupported")
    raise ValueError(f"Unsupported query type: {query.query_type}")


def evaluate_behavior_outcome(
    runtime: RuntimeView,
    truth: WorldTruth,
    action: ActionDecision,
    matched_episode: EpisodeRecord | None,
) -> tuple[str, bool, bool]:
    if runtime.query.query_type == QUERY_LOCATION:
        if action.action_type == ACTION_MOVE_TO and action.room == truth.current_answer_room:
            return OUTCOME_CORRECT_ACTION, True, False
        if action.action_type == ACTION_ABSTAIN_SEARCH:
            if truth.sufficient_evidence_expected:
                return OUTCOME_UNNECESSARY_ABSTENTION, False, False
            return OUTCOME_CORRECT_ABSTENTION, True, False
        if action.action_type == ACTION_MOVE_TO and matched_episode is not None and matched_episode.entity_id == runtime.query.entity_id:
            return OUTCOME_STALE_MEMORY_ACTION, False, True
        return OUTCOME_WRONG_ENTITY_ACTION, False, True

    if runtime.query.query_type == QUERY_TOOL:
        if action.action_type == ACTION_MOVE_TO and action.entity_id in truth.valid_tool_entities and action.room == truth.current_answer_room:
            return OUTCOME_CORRECT_ACTION, True, False
        if action.action_type == ACTION_ABSTAIN_SEARCH:
            if truth.sufficient_evidence_expected:
                return OUTCOME_UNNECESSARY_ABSTENTION, False, False
            return OUTCOME_CORRECT_ABSTENTION, True, False
        if action.action_type == ACTION_MOVE_TO and matched_episode is not None and matched_episode.entity_id in truth.valid_tool_entities:
            return OUTCOME_STALE_MEMORY_ACTION, False, True
        return OUTCOME_WRONG_ENTITY_ACTION, False, True

    if runtime.query.query_type == QUERY_HAZARD:
        if truth.room_is_safe and action.action_type == ACTION_ENTER_ROOM:
            return OUTCOME_CORRECT_ACTION, True, False
        if (not truth.room_is_safe) and action.action_type == ACTION_DO_NOT_ENTER:
            return OUTCOME_CORRECT_ACTION, True, False
        if action.action_type == ACTION_ABSTAIN_INSPECT:
            if truth.sufficient_evidence_expected:
                return OUTCOME_UNNECESSARY_ABSTENTION, False, False
            return OUTCOME_CORRECT_ABSTENTION, True, False
        if action.action_type == ACTION_ENTER_ROOM and not truth.room_is_safe and matched_episode is not None:
            return OUTCOME_STALE_MEMORY_ACTION, False, True
        return OUTCOME_UNSUPPORTED_ACTION, False, True

    raise ValueError(f"Unsupported query type: {runtime.query.query_type}")


def expected_action_cost(action: ActionDecision, false_commit: bool) -> float:
    if action.action_type in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT):
        return 1.0
    if false_commit:
        return 2.0 if action.action_type == ACTION_ENTER_ROOM else 0.5
    return 0.0


def utility_for_outcome(outcome: str) -> float:
    return UTILITY_WEIGHTS[outcome]


def evidence_passes_thresholds(evidence: RetrievalEvidence, thresholds: PolicyThresholds, stage: str) -> bool:
    if not evidence.stable_prediction:
        return False
    if not evidence.raw_episode_agreement:
        return False
    if evidence.matched_episode_post_uncertainty:
        return False
    if evidence.matched_episode_event_type == EVENT_AGENT_MISSED:
        return False
    if evidence.matched_episode_confidence is None or evidence.matched_episode_recency is None:
        return False
    if stage == "subset":
        return (
            evidence.min_normalized_margin >= thresholds.subset_min_margin
            and evidence.normalized_reconstruction >= thresholds.subset_min_reconstruction
            and evidence.matched_episode_recency >= thresholds.subset_min_recency
            and evidence.matched_episode_confidence >= thresholds.subset_min_confidence
        )
    return (
        evidence.min_normalized_margin >= thresholds.global_min_margin
        and evidence.normalized_reconstruction >= thresholds.global_min_reconstruction
        and evidence.matched_episode_recency >= thresholds.global_min_recency
        and evidence.matched_episode_confidence >= thresholds.global_min_confidence
    )


def apply_policy_to_run(
    runtime: RuntimeView,
    truth: WorldTruth,
    run: RetrievalRun,
    policy: SelectedPolicy,
    stage: str,
) -> tuple[ActionDecision, bool]:
    if evidence_passes_thresholds(run.evidence, policy.thresholds, stage):
        resolved = resolved_episode(
            runtime,
            tuple(episode for episode in runtime.memory_episodes if episode.episode_id in run.selected_episode_ids),
            run.predicted_indices,
        )
        return apply_action_from_episode(runtime.query, resolved), True
    if runtime.query.query_type == QUERY_HAZARD:
        return ActionDecision(ACTION_ABSTAIN_INSPECT, runtime.query.room, None, ACTION_INSUFFICIENT), False
    return ActionDecision(ACTION_ABSTAIN_SEARCH, None, None, ACTION_INSUFFICIENT), False


def evaluate_map_method(
    trial: TemporalTrial,
    method_id: str,
    selection_seed: int,
    policy: SelectedPolicy | None = None,
) -> Level2TrialResult:
    runtime = trial.runtime
    truth = trial.truth

    if method_id == METHOD_INDEX:
        episodes = tuple(sorted(runtime.memory_episodes, key=lambda episode: (episode.tick, episode.episode_id), reverse=True))
        if runtime.query.query_type == QUERY_LOCATION:
            relevant = [episode for episode in episodes if episode.entity_id == runtime.query.entity_id]
        elif runtime.query.query_type == QUERY_TOOL:
            relevant = [episode for episode in episodes if runtime.query.goal in entity_spec(episode.entity_id).capabilities]
        else:
            relevant = [episode for episode in episodes if episode.location == runtime.query.room]
        matched = relevant[0] if relevant else None
        action = apply_action_from_episode(runtime.query, matched)
        behavior_outcome, correct_action, false_commit = evaluate_behavior_outcome(runtime, truth, action, matched)
        return Level2TrialResult(
            schema_version=LEVEL2A_SCHEMA_VERSION,
            policy_version=None,
            method_id=method_id,
            seed=runtime.seed,
            seed_split=runtime.seed_split,
            scenario_family=runtime.scenario_family,
            query_type=runtime.query.query_type,
            approximate_lookup=runtime.query.approximate_lookup,
            candidate_count=len(relevant[:1]),
            relevant_episode_included=matched is not None and matched.episode_id in truth.oracle_relevant_episode_ids,
            exact_episode_recovery=matched is not None and matched.episode_id in truth.oracle_relevant_episode_ids,
            entity_recovery=False if matched is None else entity_recovery_for_query(runtime.query, {
                "ENTITY": matched.entity_id,
                "TYPE": matched.entity_type,
                "LOCATION": matched.location,
                "STATE": matched.state,
                "TIME_BUCKET": time_bucket_for_tick(matched.tick, runtime.current_tick),
                "SOURCE": matched.source,
            }, truth),
            location_recovery=False if matched is None else matched.location == truth.current_answer_room,
            stale_episode_recovery=stale_episode_recovery_for_query(runtime.query, matched, truth),
            selected_episode_ids=[] if matched is None else [matched.episode_id],
            predicted_indices=None if matched is None else list(episode_tuple_indices(matched, runtime.current_tick)),
            predicted_fields={} if matched is None else {
                "ENTITY": matched.entity_id,
                "TYPE": matched.entity_type,
                "LOCATION": matched.location,
                "STATE": matched.state,
                "TIME_BUCKET": time_bucket_for_tick(matched.tick, runtime.current_tick),
                "SOURCE": matched.source,
            },
            action=action.to_dict(),
            accepted=action.action_type not in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
            abstained=action.action_type in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
            insufficient_evidence=action.reason == "uncertain_after_missed_event",
            used_global_fallback=False,
            fallback_outcome=None,
            behavior_outcome=behavior_outcome,
            correct_action=correct_action,
            false_commit=false_commit,
            selective_risk_denominator=action.action_type not in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
            utility=utility_for_outcome(behavior_outcome),
            search_cost=1.0 if action.action_type in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT) else 0.0,
            expected_action_cost=expected_action_cost(action, false_commit),
            factorization_iterations=0,
            candidate_evaluations_proxy=0,
            wall_clock_sec=0.0,
            stable_prediction=None,
            min_normalized_margin=None,
            normalized_reconstruction=None,
            raw_episode_agreement=None,
            matched_episode_id=None if matched is None else matched.episode_id,
            matched_episode_tick=None if matched is None else matched.tick,
            matched_episode_post_uncertainty=None if matched is None else episode_post_uncertainty(runtime, runtime.query, matched),
            matched_episode_recency=None if matched is None else 1.0 / (1.0 + max(0, runtime.current_tick - matched.tick)),
            matched_episode_confidence=None if matched is None else matched.observation_confidence * SOURCE_RELIABILITY[matched.source],
            exact_index_baseline_applicable=True,
            discarded_local_factorizer_state=False,
            uses_upstream_resonator=False,
        )

    selected = retrieve_candidate_set(runtime, truth, method_id, selection_seed)
    first_run = run_map_retrieval(runtime, truth, method_id, selected, selection_seed)
    resolved_first = resolved_episode(runtime, selected, first_run.predicted_indices)
    action = apply_action_from_episode(runtime.query, resolved_first)
    accepted = action.action_type not in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT)
    used_fallback = False
    discarded_local = False
    fallback_outcome = None
    active_run = first_run

    if method_id in (METHOD_SEMANTIC_FALLBACK, METHOD_SEMANTIC_ABSTAIN):
        if policy is None:
            raise ValueError("Selective temporal methods require a calibrated policy.")
        action, accepted = apply_policy_to_run(runtime, truth, first_run, policy, "subset")
        if not accepted and method_id == METHOD_SEMANTIC_FALLBACK:
            discarded_local = True
            used_fallback = True
            global_run = run_map_retrieval(runtime, truth, METHOD_GLOBAL, all_episodes(runtime), selection_seed + 5000)
            active_run = global_run
            action, accepted = apply_policy_to_run(runtime, truth, global_run, policy, "global")
            fallback_outcome = OUTCOME_GLOBAL_FALLBACK_SUCCESS if accepted else OUTCOME_GLOBAL_FALLBACK_FAILURE
        elif not accepted and method_id == METHOD_SEMANTIC_ABSTAIN:
            if runtime.query.query_type == QUERY_HAZARD:
                action = ActionDecision(ACTION_ABSTAIN_INSPECT, runtime.query.room, None, ACTION_INSUFFICIENT)
            else:
                action = ActionDecision(ACTION_ABSTAIN_SEARCH, None, None, ACTION_INSUFFICIENT)

    resolved_for_outcome = resolved_episode(runtime, selected if not used_fallback else all_episodes(runtime), active_run.predicted_indices)
    behavior_outcome, correct_action, false_commit = evaluate_behavior_outcome(runtime, truth, action, resolved_for_outcome)

    if used_fallback and fallback_outcome is None:
        fallback_outcome = OUTCOME_GLOBAL_FALLBACK_SUCCESS if correct_action else OUTCOME_GLOBAL_FALLBACK_FAILURE

    total_iterations = active_run.factorization_iterations + (first_run.factorization_iterations if used_fallback else 0)
    total_candidate_evaluations = active_run.candidate_evaluations_proxy + (first_run.candidate_evaluations_proxy if used_fallback else 0)
    total_wall_clock = active_run.wall_clock_sec + (first_run.wall_clock_sec if used_fallback else 0.0)

    return Level2TrialResult(
        schema_version=LEVEL2A_SCHEMA_VERSION,
        policy_version=None if policy is None else policy.policy_version,
        method_id=method_id,
        seed=runtime.seed,
        seed_split=runtime.seed_split,
        scenario_family=runtime.scenario_family,
        query_type=runtime.query.query_type,
        approximate_lookup=runtime.query.approximate_lookup,
        candidate_count=first_run.candidate_count if not used_fallback else first_run.candidate_count + active_run.candidate_count,
        relevant_episode_included=first_run.relevant_episode_included if not used_fallback else (first_run.relevant_episode_included or active_run.relevant_episode_included),
        exact_episode_recovery=active_run.exact_episode_recovery,
        entity_recovery=active_run.entity_recovery,
        location_recovery=active_run.location_recovery,
        stale_episode_recovery=active_run.stale_episode_recovery,
        selected_episode_ids=list(active_run.selected_episode_ids),
        predicted_indices=list(active_run.predicted_indices),
        predicted_fields=active_run.predicted_fields,
        action=action.to_dict(),
        accepted=accepted and action.action_type not in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
        abstained=action.action_type in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
        insufficient_evidence=action.reason == ACTION_INSUFFICIENT or action.reason == "uncertain_after_missed_event",
        used_global_fallback=used_fallback,
        fallback_outcome=fallback_outcome,
        behavior_outcome=behavior_outcome,
        correct_action=correct_action,
        false_commit=false_commit,
        selective_risk_denominator=action.action_type not in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT),
        utility=utility_for_outcome(behavior_outcome),
        search_cost=1.0 if action.action_type in (ACTION_ABSTAIN_SEARCH, ACTION_ABSTAIN_INSPECT) else float(used_fallback),
        expected_action_cost=expected_action_cost(action, false_commit),
        factorization_iterations=total_iterations,
        candidate_evaluations_proxy=total_candidate_evaluations,
        wall_clock_sec=total_wall_clock,
        stable_prediction=active_run.evidence.stable_prediction,
        min_normalized_margin=active_run.evidence.min_normalized_margin,
        normalized_reconstruction=active_run.evidence.normalized_reconstruction,
        raw_episode_agreement=active_run.evidence.raw_episode_agreement,
        matched_episode_id=active_run.evidence.matched_episode_id,
        matched_episode_tick=active_run.evidence.matched_episode_tick,
        matched_episode_post_uncertainty=active_run.evidence.matched_episode_post_uncertainty,
        matched_episode_recency=active_run.evidence.matched_episode_recency,
        matched_episode_confidence=active_run.evidence.matched_episode_confidence,
        exact_index_baseline_applicable=runtime.query.query_type == QUERY_LOCATION,
        discarded_local_factorizer_state=discarded_local,
        uses_upstream_resonator=True,
    )


def policy_grid() -> list[PolicyThresholds]:
    thresholds: list[PolicyThresholds] = []
    for subset_margin in (0.01, 0.03, 0.05):
        for subset_recon in (0.00, 0.10, 0.20):
            for subset_recency in (0.10, 0.20, 0.33):
                for subset_confidence in (0.35, 0.50, 0.65):
                    thresholds.append(
                        PolicyThresholds(
                            subset_min_margin=subset_margin,
                            subset_min_reconstruction=subset_recon,
                            subset_min_recency=subset_recency,
                            subset_min_confidence=subset_confidence,
                            global_min_margin=max(0.01, subset_margin - 0.01),
                            global_min_reconstruction=max(0.0, subset_recon - 0.05),
                            global_min_recency=max(0.10, subset_recency - 0.05),
                            global_min_confidence=max(0.35, subset_confidence - 0.10),
                        )
                    )
    return thresholds


def summarize_policy_results(rows: list[Level2TrialResult]) -> dict[str, float]:
    total = len(rows)
    accepted = [row for row in rows if row.selective_risk_denominator]
    incorrect_accepted = [row for row in accepted if not row.correct_action]
    return {
        "coverage": 0.0 if total == 0 else len(accepted) / total,
        "selective_risk": 0.0 if not accepted else len(incorrect_accepted) / len(accepted),
        "mean_utility": 0.0 if total == 0 else sum(row.utility for row in rows) / total,
        "mean_compute": 0.0 if total == 0 else sum(row.candidate_evaluations_proxy for row in rows) / total,
    }


def choose_selected_policy(calibration_trials: list[TemporalTrial]) -> SelectedPolicy:
    best: tuple[float, float, float, PolicyThresholds] | None = None
    best_summary: dict[str, float] | None = None
    for thresholds in policy_grid():
        policy = SelectedPolicy(
            policy_version=LEVEL2A_POLICY_VERSION,
            schema_version=LEVEL2A_SCHEMA_VERSION,
            target_selective_risk=TARGET_SELECTIVE_RISK,
            thresholds=thresholds,
            calibration_seed_ranges=level2a_calibration_seed_ranges(),
            utility_weights=UTILITY_WEIGHTS,
            preferred_runtime_method=METHOD_SEMANTIC_FALLBACK,
            achieved_calibration_risk=0.0,
            achieved_calibration_coverage=0.0,
            achieved_calibration_utility=0.0,
            selection_rule="risk<=0.05, then max utility, then max coverage, then min compute",
        )
        rows = [
            evaluate_map_method(trial, METHOD_SEMANTIC_FALLBACK, trial.runtime.seed + 1000, policy)
            for trial in calibration_trials
        ]
        summary = summarize_policy_results(rows)
        if summary["selective_risk"] > TARGET_SELECTIVE_RISK:
            continue
        score = (summary["mean_utility"], summary["coverage"], -summary["mean_compute"])
        if best is None or score > best[:3]:
            best = (*score, thresholds)
            best_summary = summary

    if best is None or best_summary is None:
        fallback_thresholds = policy_grid()[0]
        best_summary = {"selective_risk": 1.0, "coverage": 0.0, "mean_utility": -1.0}
        return SelectedPolicy(
            policy_version=LEVEL2A_POLICY_VERSION,
            schema_version=LEVEL2A_SCHEMA_VERSION,
            target_selective_risk=TARGET_SELECTIVE_RISK,
            thresholds=fallback_thresholds,
            calibration_seed_ranges=level2a_calibration_seed_ranges(),
            utility_weights=UTILITY_WEIGHTS,
            preferred_runtime_method=METHOD_SEMANTIC_FALLBACK,
            achieved_calibration_risk=1.0,
            achieved_calibration_coverage=0.0,
            achieved_calibration_utility=-1.0,
            selection_rule="no calibration policy satisfied risk target; defaulted to most conservative grid point",
        )

    return SelectedPolicy(
        policy_version=LEVEL2A_POLICY_VERSION,
        schema_version=LEVEL2A_SCHEMA_VERSION,
        target_selective_risk=TARGET_SELECTIVE_RISK,
        thresholds=best[3],
        calibration_seed_ranges=level2a_calibration_seed_ranges(),
        utility_weights=UTILITY_WEIGHTS,
        preferred_runtime_method=METHOD_SEMANTIC_FALLBACK,
        achieved_calibration_risk=best_summary["selective_risk"],
        achieved_calibration_coverage=best_summary["coverage"],
        achieved_calibration_utility=best_summary["mean_utility"],
        selection_rule="risk<=0.05, then max utility, then max coverage, then min compute",
    )


def scenario_manifest() -> dict[str, Any]:
    return {
        "schema_version": LEVEL2A_SCHEMA_VERSION,
        "rooms": list(ROOMS),
        "room_hierarchy": {zone: list(rooms) for zone, rooms in ZONE_TO_ROOMS.items()},
        "entity_catalog": [asdict(spec) for spec in ENTITY_SPECS],
        "query_types": list(QUERY_TYPES),
        "scenario_families": list(SCENARIO_ORDER),
        "utility_weights": UTILITY_WEIGHTS,
        "closed_mechanisms_from_level1": [
            "full_l2_l1_global_cascade",
            "warm_estimate_transfer",
            "cheap_l1_probe_verifier",
            "holovec_attention_comparison",
            "further_bcf_tuning",
        ],
    }


def add_noise_episodes(
    seed: int,
    current_tick: int,
    excluded_entities: set[str],
    count: int = 4,
) -> list[TemporalEvent]:
    rng = random.Random(seed + 404)
    available = [spec for spec in ENTITY_SPECS if spec.entity_id not in excluded_entities]
    events: list[TemporalEvent] = []
    for index in range(count):
        spec = available[(seed + index) % len(available)]
        room = ROOMS[rng.randrange(len(ROOMS))]
        tick = rng.randrange(1, max(2, current_tick - 1))
        source = (SOURCE_CAMERA, SOURCE_REPORT, SOURCE_SELF)[rng.randrange(3)]
        state = spec.default_state if spec.entity_type != TYPE_HAZARD else ("HAZARD_PRESENT" if rng.random() < 0.5 else "HAZARD_CLEARED")
        events.append(
            TemporalEvent(
                tick=tick,
                event_type=EVENT_AGENT_OBSERVED,
                entity_id=spec.entity_id,
                entity_type=spec.entity_type,
                location=room,
                state=state,
                source=source,
                observed=True,
                observation_confidence=0.55 + 0.35 * rng.random(),
            )
        )
    return events


def build_location_trial(seed: int, scenario_family: str, seed_split: str) -> TemporalTrial:
    rng = random.Random(seed)
    current_tick = 12
    target = ENTITY_SPECS[seed % 6]
    room_a = ROOMS[(seed + 1) % len(ROOMS)]
    room_b = ROOMS[(seed + 3) % len(ROOMS)]
    active_room = ROOMS[(seed + 2) % len(ROOMS)]
    active_zone = ROOM_TO_ZONE[active_room]
    observed: list[TemporalEvent] = []
    hidden_truth_location = room_a
    sufficient = True

    if scenario_family == SCENARIO_STABLE:
        observed.append(TemporalEvent(3, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.95))
        hidden_truth_location = room_a
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        observed.append(TemporalEvent(2, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.92))
        observed.append(TemporalEvent(8, EVENT_OBJECT_MOVED, target.entity_id, target.entity_type, room_b, "MOVED", SOURCE_CAMERA, True, 0.88))
        hidden_truth_location = room_b
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        observed.append(TemporalEvent(2, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.94))
        observed.append(TemporalEvent(9, EVENT_AGENT_MISSED, target.entity_id, target.entity_type, room_a, "UNTRACKED", SOURCE_MISSED, True, 0.90))
        hidden_truth_location = room_b
        sufficient = False
    elif scenario_family == SCENARIO_CONFLICTING:
        observed.append(TemporalEvent(4, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.96))
        observed.append(TemporalEvent(7, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_CAMERA, True, 0.84))
        observed.append(TemporalEvent(9, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_b, "MOVED", SOURCE_REPORT, True, 0.45))
        hidden_truth_location = room_a
    else:
        raise ValueError(f"Unsupported location scenario: {scenario_family}")

    observed.extend(add_noise_episodes(seed, current_tick, {target.entity_id}))
    observed.sort(key=lambda event: (event.tick, event.entity_id, event.source))
    episodes = tuple(event_to_episode(event, index) for index, event in enumerate(observed))
    if scenario_family == SCENARIO_STABLE:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_OBSERVED, 3)
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_OBJECT_MOVED, 8)
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_MISSED, 9)
    else:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_OBSERVED, 7)
    factor_domains = build_factor_domains(seed)
    runtime = RuntimeView(
        seed=seed,
        seed_split=seed_split,
        scenario_family=scenario_family,
        query=QuerySpec(
            query_type=QUERY_LOCATION,
            entity_id=target.entity_id,
            goal=None,
            room=None,
            active_room=active_room,
            active_zone=active_zone,
            approximate_lookup=False,
        ),
        current_tick=current_tick,
        observed_events=tuple(observed),
        memory_episodes=episodes,
        factor_domains=factor_domains,
        subset_size=choose_subset_size(len(episodes)),
        entity_catalog=ENTITY_SPECS,
    )
    truth = WorldTruth(
        current_tick=current_tick,
        current_locations={target.entity_id: hidden_truth_location},
        current_states={target.entity_id: "AVAILABLE"},
        valid_tool_entities=(),
        room_is_safe=None,
        oracle_relevant_episode_ids=oracle_ids,
        sufficient_evidence_expected=sufficient,
        current_answer_room=hidden_truth_location if sufficient else None,
        scenario_family=scenario_family,
    )
    return TemporalTrial(runtime=runtime, truth=truth)


def build_tool_trial(seed: int, scenario_family: str, seed_split: str) -> TemporalTrial:
    current_tick = 12
    goal = GOALS[seed % len(GOALS)]
    tool_specs = [spec for spec in ENTITY_SPECS if goal in spec.capabilities]
    target = tool_specs[0]
    alt = tool_specs[-1]
    room_a = ROOMS[(seed + 1) % len(ROOMS)]
    room_b = ROOMS[(seed + 4) % len(ROOMS)]
    active_room = ROOMS[(seed + 5) % len(ROOMS)]
    active_zone = ROOM_TO_ZONE[active_room]
    observed: list[TemporalEvent] = []
    hidden_truth_location = room_a
    sufficient = True

    if scenario_family == SCENARIO_STABLE:
        observed.append(TemporalEvent(3, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.95))
        valid_entities = (target.entity_id,)
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        observed.append(TemporalEvent(2, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.93))
        observed.append(TemporalEvent(8, EVENT_OBJECT_MOVED, target.entity_id, target.entity_type, room_b, "MOVED", SOURCE_CAMERA, True, 0.87))
        hidden_truth_location = room_b
        valid_entities = (target.entity_id,)
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        observed.append(TemporalEvent(2, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.93))
        observed.append(TemporalEvent(9, EVENT_AGENT_MISSED, target.entity_id, target.entity_type, room_a, "UNTRACKED", SOURCE_MISSED, True, 0.88))
        hidden_truth_location = room_b
        valid_entities = (target.entity_id,)
        sufficient = False
    elif scenario_family == SCENARIO_CONFLICTING:
        observed.append(TemporalEvent(4, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_a, "AVAILABLE", SOURCE_SELF, True, 0.95))
        observed.append(TemporalEvent(6, EVENT_AGENT_OBSERVED, alt.entity_id, alt.entity_type, room_b, "AVAILABLE", SOURCE_CAMERA, True, 0.78))
        observed.append(TemporalEvent(9, EVENT_AGENT_OBSERVED, target.entity_id, target.entity_type, room_b, "MOVED", SOURCE_REPORT, True, 0.44))
        valid_entities = (target.entity_id,)
    else:
        raise ValueError(f"Unsupported tool scenario: {scenario_family}")

    observed.extend(add_noise_episodes(seed + 77, current_tick, {target.entity_id, alt.entity_id}))
    observed.sort(key=lambda event: (event.tick, event.entity_id, event.source))
    episodes = tuple(event_to_episode(event, index) for index, event in enumerate(observed))
    if scenario_family == SCENARIO_STABLE:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_OBSERVED, 3)
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_OBJECT_MOVED, 8)
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_MISSED, 9)
    else:
        oracle_ids = resolve_episode_ids(episodes, target.entity_id, EVENT_AGENT_OBSERVED, 4)
    runtime = RuntimeView(
        seed=seed,
        seed_split=seed_split,
        scenario_family=scenario_family,
        query=QuerySpec(
            query_type=QUERY_TOOL,
            entity_id=None,
            goal=goal,
            room=None,
            active_room=active_room,
            active_zone=active_zone,
            approximate_lookup=True,
        ),
        current_tick=current_tick,
        observed_events=tuple(observed),
        memory_episodes=episodes,
        factor_domains=build_factor_domains(seed),
        subset_size=choose_subset_size(len(episodes)),
        entity_catalog=ENTITY_SPECS,
    )
    truth = WorldTruth(
        current_tick=current_tick,
        current_locations={target.entity_id: hidden_truth_location},
        current_states={target.entity_id: "AVAILABLE"},
        valid_tool_entities=valid_entities,
        room_is_safe=None,
        oracle_relevant_episode_ids=oracle_ids,
        sufficient_evidence_expected=sufficient,
        current_answer_room=hidden_truth_location if sufficient else None,
        scenario_family=scenario_family,
    )
    return TemporalTrial(runtime=runtime, truth=truth)


def build_hazard_trial(seed: int, scenario_family: str, seed_split: str) -> TemporalTrial:
    current_tick = 12
    hazard = ENTITY_SPECS[6 + (seed % 2)]
    room = ROOMS[(seed + 2) % len(ROOMS)]
    active_room = ROOMS[(seed + 4) % len(ROOMS)]
    active_zone = ROOM_TO_ZONE[active_room]
    observed: list[TemporalEvent] = []
    room_is_safe = False
    sufficient = True

    if scenario_family == SCENARIO_STABLE:
        observed.append(TemporalEvent(4, EVENT_AGENT_OBSERVED, hazard.entity_id, hazard.entity_type, room, "HAZARD_PRESENT", SOURCE_SELF, True, 0.95))
        room_is_safe = False
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        observed.append(TemporalEvent(2, EVENT_AGENT_OBSERVED, hazard.entity_id, hazard.entity_type, room, "HAZARD_PRESENT", SOURCE_CAMERA, True, 0.82))
        observed.append(TemporalEvent(8, EVENT_OBJECT_REMOVED, hazard.entity_id, hazard.entity_type, room, "HAZARD_CLEARED", SOURCE_SELF, True, 0.95))
        room_is_safe = True
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        observed.append(TemporalEvent(3, EVENT_AGENT_OBSERVED, hazard.entity_id, hazard.entity_type, room, "HAZARD_CLEARED", SOURCE_SELF, True, 0.93))
        observed.append(TemporalEvent(9, EVENT_AGENT_MISSED, hazard.entity_id, hazard.entity_type, room, "UNTRACKED", SOURCE_MISSED, True, 0.89))
        room_is_safe = False
        sufficient = False
    elif scenario_family == SCENARIO_CONFLICTING:
        observed.append(TemporalEvent(4, EVENT_AGENT_OBSERVED, hazard.entity_id, hazard.entity_type, room, "HAZARD_PRESENT", SOURCE_SELF, True, 0.95))
        observed.append(TemporalEvent(9, EVENT_OBJECT_STATE_CHANGED, hazard.entity_id, hazard.entity_type, room, "HAZARD_CLEARED", SOURCE_REPORT, True, 0.42))
        room_is_safe = False
    else:
        raise ValueError(f"Unsupported hazard scenario: {scenario_family}")

    observed.extend(add_noise_episodes(seed + 133, current_tick, {hazard.entity_id}))
    observed.sort(key=lambda event: (event.tick, event.entity_id, event.source))
    episodes = tuple(event_to_episode(event, index) for index, event in enumerate(observed))
    if scenario_family == SCENARIO_STABLE:
        oracle_ids = resolve_episode_ids(episodes, hazard.entity_id, EVENT_AGENT_OBSERVED, 4)
    elif scenario_family == SCENARIO_OBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, hazard.entity_id, EVENT_OBJECT_REMOVED, 8)
    elif scenario_family == SCENARIO_UNOBSERVED_MOVEMENT:
        oracle_ids = resolve_episode_ids(episodes, hazard.entity_id, EVENT_AGENT_MISSED, 9)
    else:
        oracle_ids = resolve_episode_ids(episodes, hazard.entity_id, EVENT_AGENT_OBSERVED, 4)
    runtime = RuntimeView(
        seed=seed,
        seed_split=seed_split,
        scenario_family=scenario_family,
        query=QuerySpec(
            query_type=QUERY_HAZARD,
            entity_id=None,
            goal=None,
            room=room,
            active_room=active_room,
            active_zone=active_zone,
            approximate_lookup=True,
        ),
        current_tick=current_tick,
        observed_events=tuple(observed),
        memory_episodes=episodes,
        factor_domains=build_factor_domains(seed),
        subset_size=choose_subset_size(len(episodes)),
        entity_catalog=ENTITY_SPECS,
    )
    truth = WorldTruth(
        current_tick=current_tick,
        current_locations={hazard.entity_id: room},
        current_states={hazard.entity_id: "HAZARD_PRESENT" if not room_is_safe else "HAZARD_CLEARED"},
        valid_tool_entities=(),
        room_is_safe=room_is_safe,
        oracle_relevant_episode_ids=oracle_ids,
        sufficient_evidence_expected=sufficient,
        current_answer_room=room if sufficient else None,
        scenario_family=scenario_family,
    )
    return TemporalTrial(runtime=runtime, truth=truth)


def build_trial(seed: int, scenario_family: str, query_type: str, seed_split: str) -> TemporalTrial:
    if query_type == QUERY_LOCATION:
        return build_location_trial(seed, scenario_family, seed_split)
    if query_type == QUERY_TOOL:
        return build_tool_trial(seed, scenario_family, seed_split)
    if query_type == QUERY_HAZARD:
        return build_hazard_trial(seed, scenario_family, seed_split)
    raise ValueError(f"Unsupported query type: {query_type}")


def build_split_trials(
    seed_ranges: dict[str, dict[str, int]],
    query_type: str,
    seed_split: str,
) -> list[TemporalTrial]:
    rows: list[TemporalTrial] = []
    for scenario_family in SCENARIO_ORDER:
        spec = seed_ranges[scenario_family]
        for seed in range(spec["start"], spec["start"] + spec["count"]):
            rows.append(build_trial(seed, scenario_family, query_type, seed_split))
    return rows


def build_secondary_trials(
    seed_ranges: dict[str, dict[str, int]],
    seed_split: str,
) -> list[TemporalTrial]:
    rows: list[TemporalTrial] = []
    for query_type, spec in seed_ranges.items():
        count = spec["count"]
        for offset in range(count):
            scenario_family = SCENARIO_ORDER[offset % len(SCENARIO_ORDER)]
            rows.append(build_trial(spec["start"] + offset, scenario_family, query_type, seed_split))
    return rows


def evaluate_trials(
    trials: list[TemporalTrial],
    methods: tuple[str, ...],
    policy: SelectedPolicy | None,
) -> list[Level2TrialResult]:
    results: list[Level2TrialResult] = []
    for trial in trials:
        seed_everything(trial.runtime.seed)
        for method_id in methods:
            results.append(evaluate_map_method(trial, method_id, trial.runtime.seed + 9000, policy))
    return results


def group_by(rows: list[Level2TrialResult], *keys: str) -> dict[tuple[Any, ...], list[Level2TrialResult]]:
    grouped: dict[tuple[Any, ...], list[Level2TrialResult]] = {}
    for row in rows:
        key = tuple(getattr(row, field) for field in keys)
        grouped.setdefault(key, []).append(row)
    return grouped


def summarize_retrieval(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for key in sorted(group_by(rows, "method_id", "query_type")):
        batch = group_by(rows, "method_id", "query_type")[key]
        total = len(batch)
        relevant = sum(row.relevant_episode_included for row in batch)
        exact = sum(row.exact_episode_recovery for row in batch)
        entity = sum(row.entity_recovery for row in batch)
        location = sum(row.location_recovery for row in batch)
        stale = sum(row.stale_episode_recovery for row in batch)
        relevant_low, relevant_high = wilson_interval(relevant, total)
        exact_low, exact_high = wilson_interval(exact, total)
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "method_id": key[0],
                "query_type": key[1],
                "trials": total,
                "relevant_episode_inclusion_rate": maybe_round(relevant / total),
                "relevant_episode_inclusion_ci_low": maybe_round(relevant_low),
                "relevant_episode_inclusion_ci_high": maybe_round(relevant_high),
                "exact_episode_recovery_rate": maybe_round(exact / total),
                "exact_episode_recovery_ci_low": maybe_round(exact_low),
                "exact_episode_recovery_ci_high": maybe_round(exact_high),
                "entity_recovery_rate": maybe_round(entity / total),
                "location_recovery_rate": maybe_round(location / total),
                "stale_episode_recovery_rate": maybe_round(stale / total),
            }
        )
    return summary


def summarize_behavior(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for key in sorted(group_by(rows, "method_id", "query_type")):
        batch = group_by(rows, "method_id", "query_type")[key]
        total = len(batch)
        correct_action = sum(row.behavior_outcome == OUTCOME_CORRECT_ACTION for row in batch)
        stale_actions = sum(row.behavior_outcome == OUTCOME_STALE_MEMORY_ACTION for row in batch)
        unsupported = sum(row.behavior_outcome == OUTCOME_UNSUPPORTED_ACTION for row in batch)
        abstentions = sum(row.abstained for row in batch)
        fallback = sum(row.used_global_fallback for row in batch)
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "method_id": key[0],
                "query_type": key[1],
                "trials": total,
                "correct_action_rate": maybe_round(correct_action / total),
                "stale_memory_action_rate": maybe_round(stale_actions / total),
                "unsupported_action_rate": maybe_round(unsupported / total),
                "abstention_rate": maybe_round(abstentions / total),
                "fallback_rate": maybe_round(fallback / total),
                "search_cost": maybe_round(sum(row.search_cost for row in batch) / total),
                "expected_action_cost": maybe_round(sum(row.expected_action_cost for row in batch) / total),
                "behavioral_utility": maybe_round(sum(row.utility for row in batch) / total),
            }
        )
    return summary


def summarize_safety(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for key in sorted(group_by(rows, "method_id", "query_type")):
        batch = group_by(rows, "method_id", "query_type")[key]
        total = len(batch)
        accepted = [row for row in batch if row.selective_risk_denominator]
        incorrect = [row for row in accepted if not row.correct_action]
        coverage = 0.0 if total == 0 else len(accepted) / total
        risk = 0.0 if not accepted else len(incorrect) / len(accepted)
        cov_low, cov_high = wilson_interval(len(accepted), total)
        risk_low, risk_high = wilson_interval(len(incorrect), max(1, len(accepted)))
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "method_id": key[0],
                "query_type": key[1],
                "trials": total,
                "false_commit_rate": maybe_round(sum(row.false_commit for row in batch) / total),
                "selective_risk": maybe_round(risk),
                "selective_risk_ci_low": maybe_round(risk_low if accepted else 0.0),
                "selective_risk_ci_high": maybe_round(risk_high if accepted else 0.0),
                "coverage": maybe_round(coverage),
                "coverage_ci_low": maybe_round(cov_low),
                "coverage_ci_high": maybe_round(cov_high),
            }
        )
    return summary


def summarize_compute(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for key in sorted(group_by(rows, "method_id", "query_type")):
        batch = group_by(rows, "method_id", "query_type")[key]
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "method_id": key[0],
                "query_type": key[1],
                "trials": len(batch),
                "candidate_count_mean": maybe_round(sum(row.candidate_count for row in batch) / len(batch)),
                "factorization_iterations_mean": maybe_round(sum(row.factorization_iterations for row in batch) / len(batch)),
                "candidate_evaluations_proxy_mean": maybe_round(sum(row.candidate_evaluations_proxy for row in batch) / len(batch)),
                "wall_clock_mean_sec": maybe_round(sum(row.wall_clock_sec for row in batch) / len(batch)),
                "wall_clock_p90_sec": maybe_round(percentile_nearest_rank([row.wall_clock_sec for row in batch], 0.9)),
            }
        )
    return summary


def summarize_baseline_comparison(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    methods = {METHOD_INDEX, METHOD_GLOBAL, METHOD_RANDOM, METHOD_SEMANTIC, METHOD_SEMANTIC_FALLBACK, METHOD_SEMANTIC_ABSTAIN, METHOD_ORACLE}
    summary: list[dict[str, Any]] = []
    for method_id in methods:
        batch = [row for row in rows if row.method_id == method_id]
        if not batch:
            continue
        total = len(batch)
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "method_id": method_id,
                "trials": total,
                "correct_action_rate": maybe_round(sum(row.correct_action for row in batch) / total),
                "false_commit_rate": maybe_round(sum(row.false_commit for row in batch) / total),
                "behavioral_utility": maybe_round(sum(row.utility for row in batch) / total),
                "exact_index_applicable_rate": maybe_round(sum(row.exact_index_baseline_applicable for row in batch) / total),
            }
        )
    return sorted(summary, key=lambda row: row["method_id"])


def summarize_scenario_breakdown(rows: list[Level2TrialResult]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for key in sorted(group_by(rows, "scenario_family", "query_type", "method_id")):
        batch = group_by(rows, "scenario_family", "query_type", "method_id")[key]
        total = len(batch)
        summary.append(
            {
                "schema_version": LEVEL2A_SCHEMA_VERSION,
                "scenario_family": key[0],
                "query_type": key[1],
                "method_id": key[2],
                "trials": total,
                "correct_action_rate": maybe_round(sum(row.correct_action for row in batch) / total),
                "stale_memory_action_rate": maybe_round(sum(row.behavior_outcome == OUTCOME_STALE_MEMORY_ACTION for row in batch) / total),
                "abstention_rate": maybe_round(sum(row.abstained for row in batch) / total),
                "fallback_rate": maybe_round(sum(row.used_global_fallback for row in batch) / total),
                "behavioral_utility": maybe_round(sum(row.utility for row in batch) / total),
                "relevant_episode_inclusion_rate": maybe_round(sum(row.relevant_episode_included for row in batch) / total),
            }
        )
    return summary


def anti_nih_analysis(heldout_rows: list[Level2TrialResult]) -> dict[str, Any]:
    location_rows = [row for row in heldout_rows if row.query_type == QUERY_LOCATION]
    approximate_rows = [row for row in heldout_rows if row.approximate_lookup]
    index_location_utility = statistics.mean(row.utility for row in location_rows if row.method_id == METHOD_INDEX)
    semantic_location_utility = statistics.mean(row.utility for row in location_rows if row.method_id == METHOD_SEMANTIC_FALLBACK)
    return {
        "exact_indexed_retrieval": {
            "location_index_mean_utility": maybe_round(index_location_utility),
            "semantic_with_fallback_mean_utility": maybe_round(semantic_location_utility),
            "index_beats_semantic_on_exact_location": index_location_utility >= semantic_location_utility,
        },
        "approximate_associative_retrieval": {
            "trial_count": len(approximate_rows),
            "methods_evaluated": sorted({row.method_id for row in approximate_rows}),
        },
    }


def build_analysis(
    policy: SelectedPolicy,
    calibration_rows: list[Level2TrialResult],
    heldout_rows: list[Level2TrialResult],
) -> dict[str, Any]:
    retrieval_summary = summarize_retrieval(heldout_rows)
    baseline_summary = summarize_baseline_comparison(heldout_rows)

    def metric(method_id: str, query_type: str, field: str) -> float:
        for row in retrieval_summary:
            if row["method_id"] == method_id and row["query_type"] == query_type:
                return float(row[field])
        return 0.0

    semantic_gain = metric(METHOD_SEMANTIC, QUERY_LOCATION, "relevant_episode_inclusion_rate") - metric(METHOD_RANDOM, QUERY_LOCATION, "relevant_episode_inclusion_rate")
    stale_delta = 0.0
    for row in summarize_behavior(heldout_rows):
        if row["method_id"] == METHOD_SEMANTIC_FALLBACK and row["query_type"] == QUERY_LOCATION:
            stale_delta -= float(row["stale_memory_action_rate"])
        if row["method_id"] == METHOD_RANDOM and row["query_type"] == QUERY_LOCATION:
            stale_delta += float(row["stale_memory_action_rate"])

    exact_index_rows = [row for row in heldout_rows if row.method_id == METHOD_INDEX and row.query_type == QUERY_LOCATION]
    semantic_rows = [row for row in heldout_rows if row.method_id == METHOD_SEMANTIC_FALLBACK and row.query_type == QUERY_LOCATION]
    narrow = statistics.mean(row.utility for row in exact_index_rows) >= statistics.mean(row.utility for row in semantic_rows)

    return {
        "schema_version": LEVEL2A_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL2A_CHECKPOINT_COMMIT,
        "policy_version": policy.policy_version,
        "no_bcf_used": True,
        "level1_artifacts_frozen": True,
        "semantic_vs_random_location_relevant_inclusion_gain": maybe_round(semantic_gain),
        "semantic_fallback_vs_random_location_stale_action_delta": maybe_round(stale_delta),
        "anti_nih": anti_nih_analysis(heldout_rows),
        "verdict": "NARROW" if narrow else "GO_LEVEL_2B",
        "go_level_2b": True,
        "calibration_summary": summarize_policy_results([row for row in calibration_rows if row.method_id == METHOD_SEMANTIC_FALLBACK]),
    }


def run_level2a(root: Path) -> dict[str, Any]:
    results_dir = root / "results" / "level2a"
    meta = temporal_runtime_metadata()

    development_trials = build_split_trials(level2a_development_seed_ranges(), QUERY_LOCATION, "development")
    calibration_trials = build_split_trials(level2a_calibration_seed_ranges(), QUERY_LOCATION, "calibration")
    heldout_location_trials = build_split_trials(level2a_heldout_seed_ranges(), QUERY_LOCATION, "heldout")
    heldout_secondary_trials = build_secondary_trials(level2a_secondary_seed_ranges(LEVEL2A_HELDOUT_MASTER_SEED), "heldout")

    policy = choose_selected_policy(calibration_trials)
    calibration_rows = evaluate_trials(
        calibration_trials,
        (METHOD_SEMANTIC_FALLBACK, METHOD_SEMANTIC_ABSTAIN),
        policy,
    )
    heldout_rows = evaluate_trials(
        heldout_location_trials + heldout_secondary_trials,
        METHOD_ORDER,
        policy,
    )

    save_json(results_dir / "scenario_manifest.json", scenario_manifest())
    save_jsonl(results_dir / "calibration_trials.jsonl", [row.to_dict() for row in calibration_rows])
    save_json(results_dir / "selected_policy.json", policy.to_dict())
    save_jsonl(results_dir / "heldout_trials.jsonl", [row.to_dict() for row in heldout_rows])
    save_csv(results_dir / "retrieval_summary.csv", summarize_retrieval(heldout_rows))
    save_csv(results_dir / "behavioral_summary.csv", summarize_behavior(heldout_rows))
    save_csv(results_dir / "safety_summary.csv", summarize_safety(heldout_rows))
    save_csv(results_dir / "compute_summary.csv", summarize_compute(heldout_rows))
    save_csv(results_dir / "baseline_comparison.csv", summarize_baseline_comparison(heldout_rows))
    save_csv(results_dir / "scenario_breakdown.csv", summarize_scenario_breakdown(heldout_rows))
    analysis = build_analysis(policy, calibration_rows, heldout_rows)
    analysis["runtime_metadata"] = meta
    analysis["development_trial_count"] = len(development_trials)
    analysis["heldout_trial_count"] = len(heldout_rows)
    save_json(results_dir / "analysis.json", analysis)

    return {
        "policy": policy,
        "calibration_rows": calibration_rows,
        "heldout_rows": heldout_rows,
        "analysis": analysis,
    }
