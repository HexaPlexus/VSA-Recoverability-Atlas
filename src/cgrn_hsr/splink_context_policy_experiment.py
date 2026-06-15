from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


LEVEL2C_SCHEMA_VERSION = "level2c-splink-context-policy-v1"
LEVEL2C_PROTOCOL_VERSION = "level2c-frozen-protocol-v1"
LEVEL2C_CONTEXT_POLICY_VERSION = "level2c-transparent-context-policy-v1"
LEVEL2C_MASTER_SEED = 20260615
LEVEL2C_SPLIT_SEED = 20260616

ARM_NATIVE_STANDARD = "native_standard_blocking"
ARM_RANDOM = "random_size_matched_blocking"
ARM_CONTEXT = "external_context_blocking"
ARM_CONTEXT_FALLBACK = "external_context_blocking_with_safe_fallback"
ARM_ORACLE = "oracle_blocking_ceiling"
ARM_ORDER = (
    ARM_NATIVE_STANDARD,
    ARM_RANDOM,
    ARM_CONTEXT,
    ARM_CONTEXT_FALLBACK,
    ARM_ORACLE,
)

CONTEXT_CORRECT = "correct_context"
CONTEXT_MISSING = "missing_context"
CONTEXT_AMBIGUOUS = "ambiguous_context"
CONTEXT_INCORRECT_10 = "incorrect_context_10_percent"
CONTEXT_INCORRECT_25 = "incorrect_context_25_percent"
CONTEXT_INCORRECT_40 = "incorrect_context_40_percent"
CONTEXT_UNKNOWN = "unknown_context"
CONTEXT_ORDER = (
    CONTEXT_CORRECT,
    CONTEXT_MISSING,
    CONTEXT_AMBIGUOUS,
    CONTEXT_INCORRECT_10,
    CONTEXT_INCORRECT_25,
    CONTEXT_INCORRECT_40,
    CONTEXT_UNKNOWN,
)

TEMPLATE_SOC_SEC = "tpl_soc_sec_id"
TEMPLATE_STATE_POSTCODE = "tpl_state_postcode"
TEMPLATE_STATE_SUBURB = "tpl_state_suburb"
TEMPLATE_SURNAME_DOB = "tpl_surname_dob"
TEMPLATE_MEDIUM_NAME_GEO = "tpl_state_postcode_or_surname_dob"
TEMPLATE_MEDIUM_LOCALITY = "tpl_state_suburb_or_surname_dob"
TEMPLATE_STANDARD_BALANCED = "tpl_standard_balanced"
TEMPLATE_STANDARD_BROAD = "tpl_standard_broad"

BLOCKING_TEMPLATE_RULES: dict[str, list[tuple[str, ...]]] = {
    TEMPLATE_SOC_SEC: [("soc_sec_id",)],
    TEMPLATE_STATE_POSTCODE: [("state", "postcode")],
    TEMPLATE_STATE_SUBURB: [("state", "suburb")],
    TEMPLATE_SURNAME_DOB: [("surname", "date_of_birth")],
    TEMPLATE_MEDIUM_NAME_GEO: [("state", "postcode"), ("surname", "date_of_birth")],
    TEMPLATE_MEDIUM_LOCALITY: [("state", "suburb"), ("surname", "date_of_birth")],
    TEMPLATE_STANDARD_BALANCED: [("state", "postcode"), ("state", "suburb"), ("surname", "date_of_birth")],
    TEMPLATE_STANDARD_BROAD: [("soc_sec_id",), ("state", "postcode"), ("state", "suburb"), ("surname", "date_of_birth")],
}

NARROW_TEMPLATES = (
    TEMPLATE_SOC_SEC,
    TEMPLATE_STATE_POSTCODE,
    TEMPLATE_STATE_SUBURB,
    TEMPLATE_SURNAME_DOB,
)
MEDIUM_TEMPLATES = (
    TEMPLATE_MEDIUM_NAME_GEO,
    TEMPLATE_MEDIUM_LOCALITY,
)
STANDARD_TEMPLATE_CANDIDATES = (
    TEMPLATE_MEDIUM_NAME_GEO,
    TEMPLATE_MEDIUM_LOCALITY,
    TEMPLATE_STANDARD_BALANCED,
    TEMPLATE_STANDARD_BROAD,
)

UTILITY_WEIGHTS = {
    "correct_links_value": 1.0,
    "false_merge_penalty": 2.0,
    "false_split_penalty": 1.0,
    "candidate_comparison_cost": 0.00002,
    "fallback_cost": 0.05,
}


@dataclass(frozen=True)
class SplitRanges:
    development_entities: list[int]
    calibration_entities: list[int]
    heldout_entities: list[int]


@dataclass(frozen=True)
class ContextRoutingDecision:
    context_hypotheses: list[dict[str, Any]]
    context_confidence: float
    blocking_policy_id: str
    blocking_parameters: dict[str, Any]
    candidate_budget: str
    fallback_policy: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class FrozenProtocol:
    schema_version: str
    protocol_version: str
    context_policy_version: str
    master_seed: int
    split_seed: int
    dataset_name: str
    training_comparisons: list[str]
    standard_template_candidates: list[str]
    context_error_conditions: list[str]
    threshold_grid: list[float]
    fallback_probability_grid: list[float]
    fallback_gap_grid: list[float]
    fallback_context_confidence_grid: list[float]
    utility_weights: dict[str, float]
    match_probability_threshold: float
    selected_standard_template: str
    selected_fallback_probability_threshold: float
    selected_fallback_gap_threshold: float
    selected_fallback_context_confidence_threshold: float


def _require_splink() -> Any:
    try:
        import pandas as pd
        import splink.comparison_library as cl
        from splink import Linker, SettingsCreator, block_on
        from splink.datasets import splink_datasets
        from splink.internals.duckdb.database_api import DuckDBAPI
    except ImportError as exc:  # pragma: no cover - separate env only
        raise RuntimeError(
            "Level 2C requires the separate Splink environment. "
            "Use .venv_level2c and install splink, pandas, pyarrow, duckdb."
        ) from exc
    return {
        "pd": pd,
        "cl": cl,
        "Linker": Linker,
        "SettingsCreator": SettingsCreator,
        "block_on": block_on,
        "splink_datasets": splink_datasets,
        "DuckDBAPI": DuckDBAPI,
    }


def _entity_id(rec_id: str) -> int:
    match = re.search(r"rec-(\d+)-", str(rec_id))
    if match is None:
        raise ValueError(f"Unexpected rec_id format: {rec_id}")
    return int(match.group(1))


def _normalize_frame(df: Any) -> Any:
    df = df.rename(columns=lambda c: c.strip()).copy()
    for column in df.columns:
        df[column] = df[column].map(
            lambda value: "" if value is None else str(value).strip().lower()
        )
    df["entity_id"] = df["rec_id"].map(_entity_id)
    return df


def load_public_dataset() -> tuple[Any, Any, dict[str, Any]]:
    api = _require_splink()
    left = _normalize_frame(api["splink_datasets"].febrl4a)
    right = _normalize_frame(api["splink_datasets"].febrl4b)
    manifest = {
        "dataset_name": "FEBRL4",
        "left_table": "febrl4a",
        "right_table": "febrl4b",
        "source": "Splink bundled public datasets",
        "urls": {
            "febrl4a": "https://raw.githubusercontent.com/moj-analytical-services/splink_datasets/master/data/febrl/dataset4a.csv",
            "febrl4b": "https://raw.githubusercontent.com/moj-analytical-services/splink_datasets/master/data/febrl/dataset4b.csv",
        },
        "record_counts": {
            "left": int(len(left)),
            "right": int(len(right)),
        },
        "columns": left.columns.tolist(),
    }
    return left, right, manifest


def build_split_ranges(entity_ids: list[int], seed: int = LEVEL2C_SPLIT_SEED) -> SplitRanges:
    rng = random.Random(seed)
    entity_ids = entity_ids.copy()
    rng.shuffle(entity_ids)
    total = len(entity_ids)
    dev_end = int(total * 0.6)
    cal_end = int(total * 0.8)
    return SplitRanges(
        development_entities=entity_ids[:dev_end],
        calibration_entities=entity_ids[dev_end:cal_end],
        heldout_entities=entity_ids[cal_end:],
    )


def _subset_by_entities(df: Any, entity_ids: set[int]) -> Any:
    return df[df["entity_id"].isin(entity_ids)].copy()


def _labels_table_df(left_df: Any, right_df: Any) -> Any:
    api = _require_splink()
    labels = left_df[["rec_id", "entity_id"]].merge(
        right_df[["rec_id", "entity_id"]],
        on="entity_id",
        suffixes=("_l", "_r"),
    )
    labels = labels.assign(
        source_dataset_l="a",
        source_dataset_r="b",
        clerical_match_score=1.0,
    )[
        [
            "source_dataset_l",
            "rec_id_l",
            "source_dataset_r",
            "rec_id_r",
            "clerical_match_score",
        ]
    ]
    return api["pd"].DataFrame(labels)


def _training_comparison_names() -> list[str]:
    return [
        "NameComparison(given_name)",
        "NameComparison(surname)",
        "ExactMatch(state)",
        "ExactMatch(postcode)",
        "ExactMatch(suburb)",
        "ExactMatch(date_of_birth)",
        "ExactMatch(soc_sec_id)",
    ]


def _settings_creator() -> Any:
    api = _require_splink()
    cl = api["cl"]
    SettingsCreator = api["SettingsCreator"]
    block_on = api["block_on"]
    return SettingsCreator(
        link_type="link_only",
        comparisons=[
            cl.NameComparison("given_name"),
            cl.NameComparison("surname"),
            cl.ExactMatch("state"),
            cl.ExactMatch("postcode"),
            cl.ExactMatch("suburb"),
            cl.ExactMatch("date_of_birth"),
            cl.ExactMatch("soc_sec_id"),
        ],
        blocking_rules_to_generate_predictions=[block_on("surname")],
        unique_id_column_name="rec_id",
        source_dataset_column_name="source_dataset",
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=False,
    )


def _blocking_rule_creators(template_id: str) -> list[Any]:
    api = _require_splink()
    block_on = api["block_on"]
    return [block_on(*rule) for rule in BLOCKING_TEMPLATE_RULES[template_id]]


def _template_budget(template_id: str) -> str:
    if template_id in NARROW_TEMPLATES:
        return "narrow"
    if template_id in MEDIUM_TEMPLATES:
        return "medium"
    return "broad"


def _template_serialization(template_id: str) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "rules": [list(rule) for rule in BLOCKING_TEMPLATE_RULES[template_id]],
        "candidate_budget": _template_budget(template_id),
    }


def train_frozen_matcher(left_dev: Any, right_dev: Any, output_path: Path) -> dict[str, Any]:
    api = _require_splink()
    Linker = api["Linker"]
    DuckDBAPI = api["DuckDBAPI"]
    pd = api["pd"]
    block_on = api["block_on"]

    linker = Linker(
        [
            left_dev.assign(source_dataset="a"),
            right_dev.assign(source_dataset="b"),
        ],
        _settings_creator(),
        db_api=DuckDBAPI(),
        set_up_basic_logging=False,
    )
    linker.training.estimate_u_using_random_sampling(max_pairs=500000, seed=LEVEL2C_MASTER_SEED)

    labels = _labels_table_df(left_dev, right_dev)
    labels_table = linker.table_management.register_labels_table(labels)
    linker.training.estimate_m_from_pairwise_labels(labels_table)

    deterministic_true_pairs = left_dev[["entity_id", "soc_sec_id"]].merge(
        right_dev[["entity_id", "soc_sec_id"]], on="entity_id", suffixes=("_l", "_r")
    )
    recall_soc_sec = float(
        (
            deterministic_true_pairs["soc_sec_id_l"]
            == deterministic_true_pairs["soc_sec_id_r"]
        ).mean()
    )
    recall_soc_sec = max(recall_soc_sec, 0.01)
    linker.training.estimate_probability_two_random_records_match(
        [block_on("soc_sec_id")],
        recall=recall_soc_sec,
    )
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("state"))
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("surname"))

    linker.misc.save_model_to_json(str(output_path), overwrite=True)
    trained = json.loads(output_path.read_text(encoding="utf-8"))
    runtime_settings = json.loads(json.dumps(trained))
    runtime_settings["link_type"] = "dedupe_only"
    runtime_settings["source_dataset_column_name"] = None
    output_path.write_text(json.dumps(runtime_settings, indent=2) + "\n", encoding="utf-8")
    return runtime_settings


def _load_runtime_linker(canonical_df: Any, matcher_settings: dict[str, Any]) -> Any:
    api = _require_splink()
    Linker = api["Linker"]
    DuckDBAPI = api["DuckDBAPI"]
    return Linker(canonical_df, matcher_settings, db_api=DuckDBAPI(), set_up_basic_logging=False)


def _context_hypotheses_for_record(record: dict[str, str]) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    if record.get("soc_sec_id"):
        hypotheses.append({"template_id": TEMPLATE_SOC_SEC, "score": 0.95})
    if record.get("state") and record.get("postcode"):
        hypotheses.append({"template_id": TEMPLATE_STATE_POSTCODE, "score": 0.80})
    if record.get("state") and record.get("suburb"):
        hypotheses.append({"template_id": TEMPLATE_STATE_SUBURB, "score": 0.65})
    if record.get("surname") and record.get("date_of_birth"):
        hypotheses.append({"template_id": TEMPLATE_SURNAME_DOB, "score": 0.55})
    hypotheses.sort(key=lambda item: (-item["score"], item["template_id"]))
    return hypotheses


def _rotate_wrong_template(template_id: str, available: list[str]) -> str:
    ordered = [candidate for candidate in NARROW_TEMPLATES if candidate in available]
    if template_id not in ordered or len(ordered) <= 1:
        return template_id
    index = ordered.index(template_id)
    return ordered[(index + 1) % len(ordered)]


def build_context_routing_decision(
    record: dict[str, str],
    condition: str,
    seed: int,
) -> ContextRoutingDecision:
    rng = random.Random(seed)
    hypotheses = _context_hypotheses_for_record(record)
    provenance = {
        "condition": condition,
        "available_templates": [item["template_id"] for item in hypotheses],
    }

    if condition == CONTEXT_MISSING:
        return ContextRoutingDecision(
            context_hypotheses=[],
            context_confidence=0.0,
            blocking_policy_id=TEMPLATE_SURNAME_DOB,
            blocking_parameters=_template_serialization(TEMPLATE_SURNAME_DOB),
            candidate_budget=_template_budget(TEMPLATE_SURNAME_DOB),
            fallback_policy=TEMPLATE_STANDARD_BROAD,
            provenance={**provenance, "reason": "missing_context"},
        )

    if condition == CONTEXT_UNKNOWN:
        return ContextRoutingDecision(
            context_hypotheses=[],
            context_confidence=0.05,
            blocking_policy_id=TEMPLATE_SURNAME_DOB,
            blocking_parameters=_template_serialization(TEMPLATE_SURNAME_DOB),
            candidate_budget=_template_budget(TEMPLATE_SURNAME_DOB),
            fallback_policy=TEMPLATE_STANDARD_BROAD,
            provenance={**provenance, "reason": "unknown_context"},
        )

    if not hypotheses:
        return ContextRoutingDecision(
            context_hypotheses=[],
            context_confidence=0.0,
            blocking_policy_id=TEMPLATE_SURNAME_DOB,
            blocking_parameters=_template_serialization(TEMPLATE_SURNAME_DOB),
            candidate_budget=_template_budget(TEMPLATE_SURNAME_DOB),
            fallback_policy=TEMPLATE_STANDARD_BROAD,
            provenance={**provenance, "reason": "no_available_hypotheses"},
        )

    if condition == CONTEXT_AMBIGUOUS and len(hypotheses) >= 2:
        template_id = TEMPLATE_MEDIUM_NAME_GEO
        return ContextRoutingDecision(
            context_hypotheses=hypotheses[:2],
            context_confidence=0.5,
            blocking_policy_id=template_id,
            blocking_parameters=_template_serialization(template_id),
            candidate_budget=_template_budget(template_id),
            fallback_policy=TEMPLATE_STANDARD_BROAD,
            provenance={**provenance, "reason": "ambiguous_union"},
        )

    top = hypotheses[0]
    selected_template = top["template_id"]

    error_rate_map = {
        CONTEXT_INCORRECT_10: 0.10,
        CONTEXT_INCORRECT_25: 0.25,
        CONTEXT_INCORRECT_40: 0.40,
    }
    if condition in error_rate_map and rng.random() < error_rate_map[condition]:
        available = [item["template_id"] for item in hypotheses]
        selected_template = _rotate_wrong_template(selected_template, available)
        provenance["corrupted"] = True
    else:
        provenance["corrupted"] = False

    confidence = 0.9 if condition == CONTEXT_CORRECT else 0.85
    return ContextRoutingDecision(
        context_hypotheses=hypotheses,
        context_confidence=confidence,
        blocking_policy_id=selected_template,
        blocking_parameters=_template_serialization(selected_template),
        candidate_budget=_template_budget(selected_template),
        fallback_policy=TEMPLATE_STANDARD_BROAD,
        provenance=provenance,
    )


def _hash_seed(*parts: str) -> int:
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def build_random_size_matched_decision(
    record: dict[str, str],
    context_decision: ContextRoutingDecision,
    condition: str,
) -> ContextRoutingDecision:
    del record
    budget = context_decision.candidate_budget
    if budget == "narrow":
        pool = list(NARROW_TEMPLATES)
    elif budget == "medium":
        pool = list(MEDIUM_TEMPLATES)
    else:
        pool = [TEMPLATE_STANDARD_BALANCED, TEMPLATE_STANDARD_BROAD]

    seed = _hash_seed(context_decision.blocking_policy_id, condition, context_decision.provenance.get("reason", "ok"))
    rng = random.Random(seed)
    template_id = pool[rng.randrange(len(pool))]
    return ContextRoutingDecision(
        context_hypotheses=[],
        context_confidence=0.0,
        blocking_policy_id=template_id,
        blocking_parameters=_template_serialization(template_id),
        candidate_budget=budget,
        fallback_policy=TEMPLATE_STANDARD_BROAD,
        provenance={
            "condition": condition,
            "size_matched_to": context_decision.blocking_policy_id,
            "random_seed": seed,
        },
    )


def _safe_probability_gap(sorted_rows: list[dict[str, Any]]) -> float:
    if len(sorted_rows) < 2:
        return 1.0 if sorted_rows else 0.0
    return float(sorted_rows[0]["match_probability"] - sorted_rows[1]["match_probability"])


def _fallback_needed(
    context_decision: ContextRoutingDecision,
    candidate_rows: list[dict[str, Any]],
    top_probability_threshold: float,
    top_gap_threshold: float,
    context_confidence_threshold: float,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not candidate_rows:
        reasons.append("no_candidates")
    else:
        top_prob = float(candidate_rows[0]["match_probability"])
        if top_prob < top_probability_threshold:
            reasons.append("low_match_probability")
        if _safe_probability_gap(candidate_rows) < top_gap_threshold:
            reasons.append("low_top1_top2_gap")
    if context_decision.context_confidence < context_confidence_threshold:
        reasons.append("high_context_uncertainty")
    return (len(reasons) > 0, reasons)


def _execute_batch(
    linker: Any,
    records: list[dict[str, str]],
    template_id: str,
) -> tuple[list[dict[str, Any]], float]:
    start = time.perf_counter()
    predictions = linker.inference.find_matches_to_new_records(
        records,
        blocking_rules=_blocking_rule_creators(template_id),
        match_weight_threshold=-999,
    ).as_pandas_dataframe()
    elapsed = time.perf_counter() - start
    rows = predictions.to_dict(orient="records")
    return rows, elapsed


def _group_rows_by_query(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["rec_id_r"], []).append(row)
    for value in grouped.values():
        value.sort(key=lambda item: float(item["match_probability"]), reverse=True)
    return grouped


def _choose_runtime_link(
    sorted_rows: list[dict[str, Any]],
    threshold: float,
    true_rec_id: str,
) -> dict[str, Any]:
    accepted = bool(sorted_rows) and float(sorted_rows[0]["match_probability"]) >= threshold
    if not accepted:
        return {
            "accepted": False,
            "predicted_rec_id": None,
            "match_probability": 0.0,
            "top_gap": _safe_probability_gap(sorted_rows),
            "is_true_match": False,
            "truth_included": any(row["rec_id_l"] == true_rec_id for row in sorted_rows),
        }
    top = sorted_rows[0]
    return {
        "accepted": True,
        "predicted_rec_id": top["rec_id_l"],
        "match_probability": float(top["match_probability"]),
        "top_gap": _safe_probability_gap(sorted_rows),
        "is_true_match": top["rec_id_l"] == true_rec_id,
        "truth_included": any(row["rec_id_l"] == true_rec_id for row in sorted_rows),
    }


def _utility(correct: bool, false_merge: bool, false_split: bool, candidate_comparisons: int, fallback_used: bool) -> float:
    value = 0.0
    if correct:
        value += UTILITY_WEIGHTS["correct_links_value"]
    if false_merge:
        value -= UTILITY_WEIGHTS["false_merge_penalty"]
    if false_split:
        value -= UTILITY_WEIGHTS["false_split_penalty"]
    value -= candidate_comparisons * UTILITY_WEIGHTS["candidate_comparison_cost"]
    if fallback_used:
        value -= UTILITY_WEIGHTS["fallback_cost"]
    return value


def _evaluate_arm_for_condition(
    linker: Any,
    query_df: Any,
    canonical_df: Any,
    arm_id: str,
    condition: str,
    threshold: float,
    standard_template: str,
    fallback_probability_threshold: float,
    fallback_gap_threshold: float,
    fallback_context_confidence_threshold: float,
) -> list[dict[str, Any]]:
    records = query_df.to_dict(orient="records")
    candidate_count_total = len(canonical_df)

    decisions: dict[str, ContextRoutingDecision] = {}
    for record in records:
        seed = _hash_seed(record["rec_id"], condition, LEVEL2C_CONTEXT_POLICY_VERSION)
        context_decision = build_context_routing_decision(record, condition, seed)
        if arm_id == ARM_NATIVE_STANDARD:
            decisions[record["rec_id"]] = ContextRoutingDecision(
                context_hypotheses=[],
                context_confidence=1.0,
                blocking_policy_id=standard_template,
                blocking_parameters=_template_serialization(standard_template),
                candidate_budget=_template_budget(standard_template),
                fallback_policy=standard_template,
                provenance={"arm": arm_id},
            )
        elif arm_id == ARM_RANDOM:
            decisions[record["rec_id"]] = build_random_size_matched_decision(record, context_decision, condition)
        else:
            decisions[record["rec_id"]] = context_decision

    grouped_records: dict[str, list[dict[str, str]]] = {}
    for record in records:
        grouped_records.setdefault(decisions[record["rec_id"]].blocking_policy_id, []).append(record)

    controller_start = time.perf_counter()
    pass_one_rows: dict[str, list[dict[str, Any]]] = {}
    native_time = 0.0
    for template_id, batch in grouped_records.items():
        rows, elapsed = _execute_batch(linker, batch, template_id)
        native_time += elapsed
        batch_rows = _group_rows_by_query(rows)
        for record in batch:
            pass_one_rows[record["rec_id"]] = batch_rows.get(record["rec_id"], [])
    controller_overhead = time.perf_counter() - controller_start - native_time

    fallback_batches: dict[str, list[dict[str, str]]] = {}
    fallback_reasons: dict[str, list[str]] = {}
    for record in records:
        if arm_id != ARM_CONTEXT_FALLBACK:
            continue
        need_fallback, reasons = _fallback_needed(
            decisions[record["rec_id"]],
            pass_one_rows.get(record["rec_id"], []),
            fallback_probability_threshold,
            fallback_gap_threshold,
            fallback_context_confidence_threshold,
        )
        if need_fallback:
            fallback_batches.setdefault(standard_template, []).append(record)
            fallback_reasons[record["rec_id"]] = reasons

    fallback_rows: dict[str, list[dict[str, Any]]] = {}
    fallback_native_time = 0.0
    for template_id, batch in fallback_batches.items():
        rows, elapsed = _execute_batch(linker, batch, template_id)
        fallback_native_time += elapsed
        batch_rows = _group_rows_by_query(rows)
        for record in batch:
            fallback_rows[record["rec_id"]] = batch_rows.get(record["rec_id"], [])
    native_time += fallback_native_time

    results: list[dict[str, Any]] = []
    for record in records:
        query_id = record["rec_id"]
        true_rec_id = f"rec-{record['entity_id']}-org"
        first_rows = pass_one_rows.get(query_id, [])
        final_rows = fallback_rows.get(query_id, first_rows)
        link = _choose_runtime_link(final_rows, threshold, true_rec_id)
        truth_included_first = any(row["rec_id_l"] == true_rec_id for row in first_rows)
        truth_included_final = any(row["rec_id_l"] == true_rec_id for row in final_rows)
        fallback_used = query_id in fallback_rows
        candidate_comparisons = len(first_rows) + len(fallback_rows.get(query_id, []))
        false_merge = bool(link["accepted"]) and not link["is_true_match"]
        false_split = not link["accepted"]
        correct = bool(link["accepted"]) and link["is_true_match"]
        results.append(
            {
                "schema_version": LEVEL2C_SCHEMA_VERSION,
                "arm_id": arm_id,
                "context_condition": condition,
                "query_rec_id": query_id,
                "true_rec_id": true_rec_id,
                "context_decision": asdict(decisions[query_id]),
                "candidate_budget": decisions[query_id].candidate_budget,
                "selected_template_id": decisions[query_id].blocking_policy_id,
                "candidate_pairs_count": len(first_rows),
                "candidates_per_record": len(first_rows),
                "pair_completeness": 1.0 if truth_included_first else 0.0,
                "truth_pair_recall": 1.0 if truth_included_first else 0.0,
                "truth_pair_irrecoverably_excluded": (not truth_included_first) and (not fallback_used),
                "reduction_ratio": 1.0 - (len(first_rows) / candidate_count_total),
                "accepted": link["accepted"],
                "predicted_rec_id": link["predicted_rec_id"],
                "match_probability": link["match_probability"],
                "top1_top2_separation": link["top_gap"],
                "correct_link": correct,
                "false_merge": false_merge,
                "false_split": false_split,
                "unresolved": not link["accepted"],
                "truth_pair_included_after_fallback": truth_included_final,
                "fallback_used": fallback_used,
                "fallback_reasons": fallback_reasons.get(query_id, []),
                "fallback_success": fallback_used and truth_included_final,
                "fallback_false_trigger": fallback_used and truth_included_first,
                "truth_recovery_after_fallback": fallback_used and truth_included_final and not truth_included_first,
                "extra_candidate_cost": len(fallback_rows.get(query_id, [])),
                "candidate_comparisons": candidate_comparisons,
                "blocking_time": None,
                "matching_time": native_time / max(len(records), 1),
                "end_to_end_time": (native_time + max(controller_overhead, 0.0)) / max(len(records), 1),
                "controller_overhead": max(controller_overhead, 0.0) / max(len(records), 1),
                "utility": _utility(correct, false_merge, false_split, candidate_comparisons, fallback_used),
            }
        )
    return results


def _summarize_trials(rows: list[dict[str, Any]], group_fields: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row[field] for field in group_fields)
        grouped.setdefault(key, []).append(row)
    summaries: list[dict[str, Any]] = []
    for key, items in grouped.items():
        total = len(items)
        correct = sum(1 for row in items if row["correct_link"])
        false_merge = sum(1 for row in items if row["false_merge"])
        false_split = sum(1 for row in items if row["false_split"])
        unresolved = sum(1 for row in items if row["unresolved"])
        truth_pair_recall = sum(float(row["truth_pair_recall"]) for row in items) / total
        pair_completeness = sum(float(row["pair_completeness"]) for row in items) / total
        reduction_ratio = sum(float(row["reduction_ratio"]) for row in items) / total
        candidate_pairs = sum(int(row["candidate_pairs_count"]) for row in items)
        candidate_comparisons = sum(int(row["candidate_comparisons"]) for row in items)
        fallback_count = sum(1 for row in items if row["fallback_used"])
        irrecoverable = sum(1 for row in items if row["truth_pair_irrecoverably_excluded"])
        summary = {
            field: value for field, value in zip(group_fields, key)
        }
        summary.update(
            {
                "total_queries": total,
                "pair_completeness": pair_completeness,
                "truth_pair_recall": truth_pair_recall,
                "reduction_ratio": reduction_ratio,
                "candidate_pairs_count": candidate_pairs,
                "candidates_per_record": candidate_pairs / total,
                "truth_pair_irrecoverably_excluded_rate": irrecoverable / total,
                "match_precision": correct / max(correct + false_merge, 1),
                "match_recall": correct / total,
                "match_f1": (2 * correct) / max((2 * correct) + false_merge + false_split, 1),
                "false_merge_rate": false_merge / total,
                "false_split_rate": false_split / total,
                "unresolved_rate": unresolved / total,
                "fallback_rate": fallback_count / total,
                "fallback_success_rate": (
                    sum(1 for row in items if row["fallback_success"]) / max(fallback_count, 1)
                ),
                "fallback_false_trigger_rate": (
                    sum(1 for row in items if row["fallback_false_trigger"]) / max(fallback_count, 1)
                ),
                "truth_recovery_after_fallback_rate": (
                    sum(1 for row in items if row["truth_recovery_after_fallback"]) / max(fallback_count, 1)
                ),
                "extra_candidate_cost": sum(int(row["extra_candidate_cost"]) for row in items),
                "blocking_time": None,
                "matching_time": sum(float(row["matching_time"]) for row in items),
                "end_to_end_time": sum(float(row["end_to_end_time"]) for row in items),
                "controller_overhead": sum(float(row["controller_overhead"]) for row in items),
                "candidate_comparisons": candidate_comparisons,
                "utility": sum(float(row["utility"]) for row in items),
            }
        )
        summaries.append(summary)
    return summaries


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _select_threshold_from_calibration(calibration_rows: list[dict[str, Any]], thresholds: list[float]) -> float:
    best_threshold = thresholds[0]
    best_utility = -1e18
    for threshold in thresholds:
        rescored = []
        for row in calibration_rows:
            sorted_truth = row["sorted_candidates"]
            link = _choose_runtime_link(sorted_truth, threshold, row["true_rec_id"])
            false_merge = bool(link["accepted"]) and not link["is_true_match"]
            false_split = not link["accepted"]
            correct = bool(link["accepted"]) and link["is_true_match"]
            rescored.append(_utility(correct, false_merge, false_split, len(sorted_truth), False))
        utility = sum(rescored)
        if utility > best_utility:
            best_utility = utility
            best_threshold = threshold
    return best_threshold


def _evaluate_standard_candidates(
    linker: Any,
    query_df: Any,
    candidate_templates: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows = []
    for template_id in candidate_templates:
        arm_rows = _evaluate_arm_for_condition(
            linker=linker,
            query_df=query_df,
            canonical_df=linker._input_tables_dict[list(linker._input_tables_dict.keys())[0]].as_pandas_dataframe(),
            arm_id=ARM_NATIVE_STANDARD,
            condition=CONTEXT_CORRECT,
            threshold=0.5,
            standard_template=template_id,
            fallback_probability_threshold=0.0,
            fallback_gap_threshold=0.0,
            fallback_context_confidence_threshold=0.0,
        )
        rows.extend(arm_rows)
    return rows


def _build_calibration_scored_rows(linker: Any, query_df: Any, standard_template: str) -> list[dict[str, Any]]:
    rows = _evaluate_arm_for_condition(
        linker=linker,
        query_df=query_df,
        canonical_df=linker._input_tables_dict[list(linker._input_tables_dict.keys())[0]].as_pandas_dataframe(),
        arm_id=ARM_NATIVE_STANDARD,
        condition=CONTEXT_CORRECT,
        threshold=0.0,
        standard_template=standard_template,
        fallback_probability_threshold=0.0,
        fallback_gap_threshold=0.0,
        fallback_context_confidence_threshold=0.0,
    )
    scored_rows = []
    for row in rows:
        scored_rows.append(
            {
                "query_rec_id": row["query_rec_id"],
                "true_rec_id": row["true_rec_id"],
                "sorted_candidates": [],
            }
        )
    # This placeholder is intentionally overwritten in run_level2c once raw candidate rows are available.
    return scored_rows


def _template_mean_candidates(calibration_trials: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[int]] = {}
    for row in calibration_trials:
        grouped.setdefault(row["selected_template_id"], []).append(int(row["candidate_pairs_count"]))
    return {
        key: statistics.mean(values)
        for key, values in grouped.items()
    }


def _select_standard_template(calibration_rows: list[dict[str, Any]]) -> str:
    summaries = _summarize_trials(calibration_rows, ["arm_id", "selected_template_id"])
    best = max(summaries, key=lambda row: row["utility"])
    return str(best["selected_template_id"])


def _select_fallback_thresholds(
    linker: Any,
    query_df: Any,
    canonical_df: Any,
    threshold: float,
    standard_template: str,
    probability_grid: list[float],
    gap_grid: list[float],
    context_confidence_grid: list[float],
) -> tuple[float, float, float]:
    best = (probability_grid[0], gap_grid[0], context_confidence_grid[0])
    best_utility = -1e18
    for probability_threshold in probability_grid:
        for gap_threshold in gap_grid:
            for context_confidence_threshold in context_confidence_grid:
                rows: list[dict[str, Any]] = []
                for condition in (CONTEXT_CORRECT, CONTEXT_INCORRECT_25, CONTEXT_UNKNOWN):
                    rows.extend(
                        _evaluate_arm_for_condition(
                            linker=linker,
                            query_df=query_df,
                            canonical_df=canonical_df,
                            arm_id=ARM_CONTEXT_FALLBACK,
                            condition=condition,
                            threshold=threshold,
                            standard_template=standard_template,
                            fallback_probability_threshold=probability_threshold,
                            fallback_gap_threshold=gap_threshold,
                            fallback_context_confidence_threshold=context_confidence_threshold,
                        )
                    )
                utility = sum(float(row["utility"]) for row in rows)
                if utility > best_utility:
                    best_utility = utility
                    best = (probability_threshold, gap_threshold, context_confidence_threshold)
    return best


def _canonical_dict(canonical_df: Any) -> dict[str, dict[str, str]]:
    return {
        row["rec_id"]: row
        for row in canonical_df.to_dict(orient="records")
    }


def _oracle_trials(
    linker: Any,
    query_df: Any,
    canonical_df: Any,
    threshold: float,
    standard_template: str,
) -> list[dict[str, Any]]:
    records = query_df.to_dict(orient="records")
    candidates_by_template: dict[str, dict[str, list[dict[str, Any]]]] = {}
    native_time_total = 0.0
    for template_id in NARROW_TEMPLATES + MEDIUM_TEMPLATES + (standard_template,):
        rows, elapsed = _execute_batch(linker, records, template_id)
        native_time_total += elapsed
        candidates_by_template[template_id] = _group_rows_by_query(rows)
    canonical_lookup = _canonical_dict(canonical_df)
    rows: list[dict[str, Any]] = []
    for record in records:
        query_id = record["rec_id"]
        true_rec_id = f"rec-{record['entity_id']}-org"
        best_template = standard_template
        best_candidates = candidates_by_template.get(standard_template, {}).get(query_id, [])
        best_size = len(best_candidates) if best_candidates else math.inf
        for template_id, grouped in candidates_by_template.items():
            candidates = grouped.get(query_id, [])
            if any(candidate["rec_id_l"] == true_rec_id for candidate in candidates):
                if len(candidates) < best_size:
                    best_template = template_id
                    best_candidates = candidates
                    best_size = len(candidates)
        link = _choose_runtime_link(best_candidates, threshold, true_rec_id)
        false_merge = bool(link["accepted"]) and not link["is_true_match"]
        false_split = not link["accepted"]
        correct = bool(link["accepted"]) and link["is_true_match"]
        rows.append(
            {
                "schema_version": LEVEL2C_SCHEMA_VERSION,
                "arm_id": ARM_ORACLE,
                "context_condition": CONTEXT_CORRECT,
                "query_rec_id": query_id,
                "true_rec_id": true_rec_id,
                "context_decision": None,
                "candidate_budget": _template_budget(best_template),
                "selected_template_id": best_template,
                "candidate_pairs_count": len(best_candidates),
                "candidates_per_record": len(best_candidates),
                "pair_completeness": 1.0 if link["truth_included"] else 0.0,
                "truth_pair_recall": 1.0 if link["truth_included"] else 0.0,
                "truth_pair_irrecoverably_excluded": False,
                "reduction_ratio": 1.0 - (len(best_candidates) / len(canonical_df)),
                "accepted": link["accepted"],
                "predicted_rec_id": link["predicted_rec_id"],
                "match_probability": link["match_probability"],
                "top1_top2_separation": link["top_gap"],
                "correct_link": correct,
                "false_merge": false_merge,
                "false_split": false_split,
                "unresolved": not link["accepted"],
                "truth_pair_included_after_fallback": link["truth_included"],
                "fallback_used": False,
                "fallback_reasons": [],
                "fallback_success": False,
                "fallback_false_trigger": False,
                "truth_recovery_after_fallback": False,
                "extra_candidate_cost": 0,
                "candidate_comparisons": len(best_candidates),
                "blocking_time": None,
                "matching_time": native_time_total / max(len(records), 1),
                "end_to_end_time": native_time_total / max(len(records), 1),
                "controller_overhead": 0.0,
                "utility": _utility(correct, false_merge, false_split, len(best_candidates), False),
            }
        )
    return rows


def run_level2c(root: Path) -> dict[str, Any]:
    results_dir = root / "results" / "level2c"
    docs_dir = root / "docs"
    results_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    left, right, dataset_manifest = load_public_dataset()
    entity_ids = sorted(set(left["entity_id"]).intersection(set(right["entity_id"])))
    splits = build_split_ranges(entity_ids)
    split_sets = {
        "development": set(splits.development_entities),
        "calibration": set(splits.calibration_entities),
        "heldout": set(splits.heldout_entities),
    }

    left_dev = _subset_by_entities(left, split_sets["development"])
    right_dev = _subset_by_entities(right, split_sets["development"])
    left_cal = _subset_by_entities(left, split_sets["calibration"])
    right_cal = _subset_by_entities(right, split_sets["calibration"])
    left_held = _subset_by_entities(left, split_sets["heldout"])
    right_held = _subset_by_entities(right, split_sets["heldout"])

    frozen_matcher_path = results_dir / "frozen_matcher.json"
    matcher_settings = train_frozen_matcher(left_dev, right_dev, frozen_matcher_path)

    linker_cal = _load_runtime_linker(left_cal, matcher_settings)
    calibration_standard_rows: list[dict[str, Any]] = []
    for template_id in STANDARD_TEMPLATE_CANDIDATES:
        calibration_standard_rows.extend(
            _evaluate_arm_for_condition(
                linker=linker_cal,
                query_df=right_cal,
                canonical_df=left_cal,
                arm_id=ARM_NATIVE_STANDARD,
                condition=CONTEXT_CORRECT,
                threshold=0.5,
                standard_template=template_id,
                fallback_probability_threshold=0.0,
                fallback_gap_threshold=0.0,
                fallback_context_confidence_threshold=0.0,
            )
        )
    selected_standard_template = _select_standard_template(calibration_standard_rows)

    threshold_grid = [0.4, 0.5, 0.6, 0.7]
    fallback_probability_grid = [0.35, 0.5, 0.65]
    fallback_gap_grid = [0.02, 0.05, 0.10]
    fallback_context_confidence_grid = [0.10, 0.30, 0.60]

    raw_rows_for_threshold = _evaluate_arm_for_condition(
        linker=linker_cal,
        query_df=right_cal,
        canonical_df=left_cal,
        arm_id=ARM_NATIVE_STANDARD,
        condition=CONTEXT_CORRECT,
        threshold=0.0,
        standard_template=selected_standard_template,
        fallback_probability_threshold=0.0,
        fallback_gap_threshold=0.0,
        fallback_context_confidence_threshold=0.0,
    )
    threshold_utility_rows = []
    for row in raw_rows_for_threshold:
        threshold_utility_rows.append(
            {
                "sorted_candidates": [],
                "true_rec_id": row["true_rec_id"],
            }
        )
    # Re-run one broad scoring pass to collect sorted candidates directly.
    rows, _ = _execute_batch(
        linker_cal,
        right_cal.to_dict(orient="records"),
        selected_standard_template,
    )
    grouped_candidates = _group_rows_by_query(rows)
    threshold_utility_rows = [
        {
            "query_rec_id": query_rec_id,
            "true_rec_id": f"rec-{_entity_id(query_rec_id)}-org",
            "sorted_candidates": grouped_candidates.get(query_rec_id, []),
        }
        for query_rec_id in right_cal["rec_id"].tolist()
    ]
    match_probability_threshold = _select_threshold_from_calibration(
        threshold_utility_rows,
        threshold_grid,
    )

    selected_fallback_probability_threshold, selected_fallback_gap_threshold, selected_fallback_context_confidence_threshold = _select_fallback_thresholds(
        linker=linker_cal,
        query_df=right_cal,
        canonical_df=left_cal,
        threshold=match_probability_threshold,
        standard_template=selected_standard_template,
        probability_grid=fallback_probability_grid,
        gap_grid=fallback_gap_grid,
        context_confidence_grid=fallback_context_confidence_grid,
    )

    protocol = FrozenProtocol(
        schema_version=LEVEL2C_SCHEMA_VERSION,
        protocol_version=LEVEL2C_PROTOCOL_VERSION,
        context_policy_version=LEVEL2C_CONTEXT_POLICY_VERSION,
        master_seed=LEVEL2C_MASTER_SEED,
        split_seed=LEVEL2C_SPLIT_SEED,
        dataset_name=dataset_manifest["dataset_name"],
        training_comparisons=_training_comparison_names(),
        standard_template_candidates=list(STANDARD_TEMPLATE_CANDIDATES),
        context_error_conditions=list(CONTEXT_ORDER),
        threshold_grid=threshold_grid,
        fallback_probability_grid=fallback_probability_grid,
        fallback_gap_grid=fallback_gap_grid,
        fallback_context_confidence_grid=fallback_context_confidence_grid,
        utility_weights=UTILITY_WEIGHTS,
        match_probability_threshold=match_probability_threshold,
        selected_standard_template=selected_standard_template,
        selected_fallback_probability_threshold=selected_fallback_probability_threshold,
        selected_fallback_gap_threshold=selected_fallback_gap_threshold,
        selected_fallback_context_confidence_threshold=selected_fallback_context_confidence_threshold,
    )

    linker_held = _load_runtime_linker(left_held, matcher_settings)
    heldout_rows: list[dict[str, Any]] = []
    for condition in CONTEXT_ORDER:
        for arm_id in ARM_ORDER[:-1]:
            heldout_rows.extend(
                _evaluate_arm_for_condition(
                    linker=linker_held,
                    query_df=right_held,
                    canonical_df=left_held,
                    arm_id=arm_id,
                    condition=condition,
                    threshold=match_probability_threshold,
                    standard_template=selected_standard_template,
                    fallback_probability_threshold=selected_fallback_probability_threshold,
                    fallback_gap_threshold=selected_fallback_gap_threshold,
                    fallback_context_confidence_threshold=selected_fallback_context_confidence_threshold,
                )
            )
    heldout_rows.extend(
        _oracle_trials(
            linker=linker_held,
            query_df=right_held,
            canonical_df=left_held,
            threshold=match_probability_threshold,
            standard_template=selected_standard_template,
        )
    )

    blocking_summary = _summarize_trials(heldout_rows, ["arm_id", "context_condition"])
    matching_summary = _summarize_trials(heldout_rows, ["arm_id", "context_condition"])
    fallback_summary = [
        row
        for row in blocking_summary
        if row["arm_id"] in (ARM_CONTEXT, ARM_CONTEXT_FALLBACK)
    ]
    context_error_breakdown = [
        row
        for row in blocking_summary
        if row["context_condition"] != CONTEXT_CORRECT or row["arm_id"] in (ARM_CONTEXT, ARM_CONTEXT_FALLBACK)
    ]
    compute_summary = _summarize_trials(heldout_rows, ["arm_id", "context_condition"])

    pareto_summary = []
    for row in blocking_summary:
        pareto_summary.append(
            {
                "arm_id": row["arm_id"],
                "context_condition": row["context_condition"],
                "pair_completeness": row["pair_completeness"],
                "match_f1": row["match_f1"],
                "truth_pair_irrecoverably_excluded_rate": row["truth_pair_irrecoverably_excluded_rate"],
                "candidate_comparisons": row["candidate_comparisons"],
                "controller_overhead": row["controller_overhead"],
                "utility": row["utility"],
            }
        )

    correct_context_rows = [
        row for row in blocking_summary if row["context_condition"] == CONTEXT_CORRECT
    ]
    row_by_arm = {row["arm_id"]: row for row in correct_context_rows}
    context_row = row_by_arm.get(ARM_CONTEXT)
    random_row = row_by_arm.get(ARM_RANDOM)
    standard_row = row_by_arm.get(ARM_NATIVE_STANDARD)
    fallback_row = row_by_arm.get(ARM_CONTEXT_FALLBACK)

    verdict = "NARROW"
    allowed_claims = []
    forbidden_claims = [
        "universal context controller",
        "CNM or H2 necessity",
        "new probabilistic matcher",
    ]
    if context_row and random_row and context_row["truth_pair_recall"] > random_row["truth_pair_recall"]:
        allowed_claims.append("candidate-policy portability beyond VSA")
    if context_row and standard_row and context_row["match_f1"] >= standard_row["match_f1"] and context_row["candidate_comparisons"] <= standard_row["candidate_comparisons"]:
        allowed_claims.append("useful Pareto point over standard blocking")
        verdict = "GO PORTABLE CONTEXT POLICY"
    if fallback_row and context_row and fallback_row["truth_pair_irrecoverably_excluded_rate"] < context_row["truth_pair_irrecoverably_excluded_rate"]:
        allowed_claims.append("safe fallback reduces catastrophic exclusions")
    if standard_row and context_row and context_row["match_f1"] < standard_row["match_f1"] and context_row["candidate_comparisons"] >= standard_row["candidate_comparisons"]:
        verdict = "BLOCK L10 IN ENTITY RESOLUTION"
    elif allowed_claims == ["candidate-policy portability beyond VSA"] or (context_row and standard_row and context_row["match_f1"] < standard_row["match_f1"]):
        verdict = "NARROW"
    elif context_row and standard_row and abs(context_row["candidate_comparisons"] - standard_row["candidate_comparisons"]) < 1e-9:
        verdict = "ENGINEERING ONLY"

    environment = {
        "schema_version": LEVEL2C_SCHEMA_VERSION,
        "python_version": sys.version,
        "platform": platform.platform(),
        "splink_environment_path": ".venv_level2c",
        "packages": {
            "splink": "4.0.16",
            "duckdb": "1.5.3",
            "pandas": "3.0.3",
            "pyarrow": "24.0.0",
        },
        "install_command": ".venv_level2c\\Scripts\\python -m pip install splink pandas pyarrow duckdb",
    }

    dataset_manifest.update(
        {
            "split_seed": LEVEL2C_SPLIT_SEED,
            "split_sizes": {
                "development": len(left_dev),
                "calibration": len(left_cal),
                "heldout": len(left_held),
            },
            "entity_overlap": {
                "development_calibration": len(split_sets["development"].intersection(split_sets["calibration"])),
                "development_heldout": len(split_sets["development"].intersection(split_sets["heldout"])),
                "calibration_heldout": len(split_sets["calibration"].intersection(split_sets["heldout"])),
            },
        }
    )

    calibration_results = {
        "selected_standard_template": selected_standard_template,
        "selected_match_probability_threshold": match_probability_threshold,
        "selected_fallback_probability_threshold": selected_fallback_probability_threshold,
        "selected_fallback_gap_threshold": selected_fallback_gap_threshold,
        "selected_fallback_context_confidence_threshold": selected_fallback_context_confidence_threshold,
    }

    analysis = {
        "schema_version": LEVEL2C_SCHEMA_VERSION,
        "protocol_version": LEVEL2C_PROTOCOL_VERSION,
        "context_policy_version": LEVEL2C_CONTEXT_POLICY_VERSION,
        "verdict": verdict,
        "allowed_claims": allowed_claims,
        "forbidden_claims": forbidden_claims,
        "notes": [
            "Splink matcher remained fixed across arms; only blocking policy changed.",
            "Safe fallback always re-ran a fresh broad/native pass.",
            "Blocking time is not separately observable from Splink's coupled find_matches_to_new_records call; matching_time captures native blocking+scoring time.",
        ],
    }

    _write_json(results_dir / "environment.json", environment)
    _write_json(results_dir / "dataset_manifest.json", dataset_manifest)
    _write_json(results_dir / "frozen_protocol.json", asdict(protocol))
    _write_json(results_dir / "calibration_results.json", calibration_results)
    _write_jsonl(results_dir / "heldout_trials.jsonl", heldout_rows)
    _write_csv(results_dir / "blocking_summary.csv", blocking_summary)
    _write_csv(results_dir / "matching_summary.csv", matching_summary)
    _write_csv(results_dir / "fallback_summary.csv", fallback_summary)
    _write_csv(results_dir / "context_error_breakdown.csv", context_error_breakdown)
    _write_csv(results_dir / "compute_summary.csv", compute_summary)
    _write_csv(results_dir / "pareto_summary.csv", pareto_summary)
    _write_json(results_dir / "analysis.json", analysis)

    docs_path = docs_dir / "LEVEL2C_PORTABLE_CONTEXT_POLICY.md"
    docs_path.write_text(
        "\n".join(
            [
                "# Level 2C Portable Context Policy",
                "",
                f"Schema version: `{LEVEL2C_SCHEMA_VERSION}`",
                "",
                "## Scope",
                "",
                "- Native resolver: Splink probabilistic matcher.",
                "- Policy seam: external context chooses blocking template, candidate budget, and safe fallback only.",
                "- Forbidden: custom matcher, custom ER, broad controller framework, CNM runtime.",
                "",
                "## Public Dataset",
                "",
                "- FEBRL4a / FEBRL4b via Splink public datasets.",
                "- Canonical table: `febrl4a` originals.",
                "- Query table: `febrl4b` duplicates.",
                "- Ground truth: `entity_id` recovered from `rec_id`.",
                "",
                "## Arms",
                "",
                f"- `{ARM_NATIVE_STANDARD}`",
                f"- `{ARM_RANDOM}`",
                f"- `{ARM_CONTEXT}`",
                f"- `{ARM_CONTEXT_FALLBACK}`",
                f"- `{ARM_ORACLE}`",
                "",
                "## Context Contract",
                "",
                "```text",
                "ContextRoutingDecision:",
                "    context_hypotheses",
                "    context_confidence",
                "    blocking_policy_id",
                "    blocking_parameters",
                "    candidate_budget",
                "    fallback_policy",
                "    provenance",
                "```",
                "",
                "## Notes",
                "",
                "- Matcher parameters are frozen once and reused across all arms.",
                "- Context error is injected only into routing metadata, never into labels or native records.",
                "- Safe fallback re-runs Splink with a fresh broad blocking template.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "environment": environment,
        "dataset_manifest": dataset_manifest,
        "protocol": asdict(protocol),
        "analysis": analysis,
    }
