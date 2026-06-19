from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import numpy as np

from cgrn_hsr.competitors.ibm_bcf_audit import AbstractFactorizationTask
from cgrn_hsr.level3_5b_native_noise_frontiers import (
    BCF_ARM_ID,
    BCF_TRACK_BLOCKED,
    BINARY_SEED_RANGES,
    CHANNEL_BCF_NATIVE,
    MAP_EXTENDED_ARM_ID,
    MAP_FAST_ARM_ID,
    OUTCOME_DETECTED,
    OUTCOME_SILENT_WRONG,
    ShortenedBCHConfig,
    ShortenedBCHWrapper,
    bernoulli_flip_bits,
    build_bch_configs,
    decode_generic,
    decode_neco,
    exact_weight_flip_bits,
    extract_transition_regions,
    level3_5b_dev_seed_set,
    make_bch_wrapper,
    normalize_full_tuple_outcome,
    oracle_feasible,
    prior_seed_set,
    seeds_are_fresh,
)
from cgrn_hsr.level3_4_algebraic_baselines import decode_factor_messages, generic_matrix, neco_subcodes

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def _load_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sample_task(domain_size: int = 10, factor_count: int = 3) -> AbstractFactorizationTask:
    return AbstractFactorizationTask(
        task_seed=1,
        factor_count=factor_count,
        domain_size_per_factor=[domain_size] * factor_count,
        target_indices=[0] * factor_count,
        distractor_target_indices=[],
        context_membership={},
        active_context="",
        anomaly_rate=0.0,
        query_valid_source_indices=[],
        active_l1=None,
        active_l2=None,
        context_prediction=None,
    )


def test_no_heldout_seed_ranges_are_executed() -> None:
    payload = _load("results/level3_5b_dev/heldout_protocol.json")
    assert payload["executed"] is False


def test_development_seed_ranges_do_not_overlap_prior_levels() -> None:
    analysis = _load("results/level3_5b_dev/analysis.json")
    assert analysis["fresh_seeds_non_overlapping"] is True
    assert seeds_are_fresh() is True
    assert level3_5b_dev_seed_set().isdisjoint(prior_seed_set())


def test_shortened_bch_wrapper_delegates_decoding_to_galois() -> None:
    class FakeCode:
        def __init__(self) -> None:
            self.called_decode = 0
            self.called_encode = 0

        def encode(self, message: np.ndarray) -> np.ndarray:
            self.called_encode += 1
            return np.concatenate([message, np.zeros(5, dtype=np.uint8)], axis=0)

        def decode(self, codeword: np.ndarray, errors: bool = True):
            self.called_decode += 1
            return codeword[:16], 0

    wrapper = ShortenedBCHWrapper(
        config=ShortenedBCHConfig(
            payload_bits=12,
            tier_id="TEST",
            parent_n=21,
            parent_k=16,
            shortened_n=17,
            shortened_k=12,
            minimum_distance=3,
            correctable_errors_t=1,
            shortening_positions=tuple(range(4)),
            library_version="fake",
        ),
        code=FakeCode(),
    )
    message = np.zeros(12, dtype=np.uint8)
    encoded = wrapper.encode(message)
    decoded, _ = wrapper.decode(encoded)
    assert wrapper.code.called_encode == 1
    assert wrapper.code.called_decode == 1
    assert decoded.shape == (12,)


def test_bch_parent_and_shortened_lengths_are_accounted() -> None:
    payload = _load("results/level3_5b_dev/bch_configs.json")
    for row in payload["rows"]:
        assert row["shortened_n"] <= row["parent_n"]
        assert row["shortened_k"] <= row["parent_k"]
        assert row["redundancy_bits"] == row["shortened_n"] - row["shortened_k"]


def test_bch_configurations_are_frozen_before_trial_outcomes() -> None:
    payload = _load("results/level3_5b_dev/bch_configs.json")
    protocol = _load("results/level3_5b_dev/frozen_development_protocol.json")
    assert payload["frozen_before_trial_outcomes"] is True
    assert protocol["bch_configs_frozen_before_trials"] is True


def test_exact_weight_corruption_flips_exactly_e_coordinates() -> None:
    bits = np.zeros(20, dtype=np.uint8)
    corrupted, record = exact_weight_flip_bits(bits, flips=5, seed=1)
    assert record.realized_flip_count == 5
    assert int(np.count_nonzero(bits != corrupted)) == 5


def test_bernoulli_corruption_stores_realized_count() -> None:
    bits = np.zeros(100, dtype=np.uint8)
    corrupted, record = bernoulli_flip_bits(bits, probability=0.2, seed=2)
    assert record.realized_flip_count == int(np.count_nonzero(bits != corrupted))
    assert abs(record.flip_fraction - (record.realized_flip_count / 100.0)) < 1e-12


def test_truth_is_not_passed_to_any_decoder() -> None:
    rows = _load_jsonl("results/level3_5b_dev/binary_trials.jsonl") + _load_jsonl("results/level3_5b_dev/map_trials.jsonl")
    assert rows
    assert all(row["uses_truth_in_decoder"] is False for row in rows)


def test_unassigned_messages_return_typed_failure() -> None:
    task = _sample_task(domain_size=10, factor_count=1)
    decoded = decode_factor_messages([np.array([0, 1, 0, 1], dtype=np.uint8)], task)
    assert decoded.outcome == "UNASSIGNED_CODEWORD"


def test_generic_and_neco_decoders_remain_unchanged() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_native_noise_frontiers.py").read_text(encoding="utf-8")
    assert "def generic_decode(" not in source
    assert "def neco_decode(" not in source
    assert "from .level3_4_algebraic_baselines import" in source


def test_no_neco_noisy_decoder_is_added() -> None:
    analysis = _load("results/level3_5b_dev/analysis.json")
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_native_noise_frontiers.py").read_text(encoding="utf-8")
    assert analysis["no_new_decoder"] is True
    assert "noise decoder" not in source.lower()


def test_map_observation_corruption_happens_after_clean_product_construction() -> None:
    rows = _load_jsonl("results/level3_5b_dev/map_trials.jsonl")
    assert rows
    assert all(row["corruption_after_clean_product_construction"] is True for row in rows)


def test_map_codebooks_remain_unchanged() -> None:
    rows = _load_jsonl("results/level3_5b_dev/map_trials.jsonl")
    assert all(row["map_codebooks_unchanged"] is True for row in rows)


def test_map_configurations_remain_frozen() -> None:
    rows = _load_jsonl("results/level3_5b_dev/map_trials.jsonl")
    arm_ids = {row["method_id"] for row in rows}
    assert arm_ids == {MAP_FAST_ARM_ID, MAP_EXTENDED_ARM_ID}


def test_bcf_external_and_internal_noise_are_stored_separately() -> None:
    contract = _load("results/level3_5b_dev/bcf_native_corruption_contract.json")
    rows = _load_jsonl("results/level3_5b_dev/bcf_trials.jsonl")
    assert contract["status"] == BCF_TRACK_BLOCKED
    assert rows[0]["channel_id"] == CHANNEL_BCF_NATIVE
    assert rows[0]["external_corruption_spec"] is None
    assert rows[0]["internal_decoder_noise_spec"]["native_initialization_noise"]


def test_bcf_unsupported_channels_are_blocked() -> None:
    contract = _load("results/level3_5b_dev/bcf_native_corruption_contract.json")
    summary = _load_csv("results/level3_5b_dev/bcf_summary.csv")
    assert contract["status"] == BCF_TRACK_BLOCKED
    assert summary[0]["status"] == BCF_TRACK_BLOCKED


def test_no_universal_raw_p_table_is_generated() -> None:
    timing = _load_csv("results/level3_5b_dev/timing_summary.csv")
    tracks = {row["track_id"] for row in timing}
    assert tracks == {"binary_exact_record", "map_native_sign_flip"}


def test_common_semantic_manifests_are_reused_where_lawful() -> None:
    rows = _load_jsonl("results/level3_5b_dev/semantic_manifests.jsonl")
    assert rows
    per_track_trial = {(row["track_id"], row["trial_id"]) for row in rows}
    assert len(per_track_trial) == len(rows)


def test_silent_wrong_is_distinguished_from_detected_failure() -> None:
    rows = _load_csv("results/level3_5b_dev/silent_error_summary.csv")
    assert any(float(row["detected_failure_rate"]) > 0.0 for row in rows if row["track_id"] == "binary_exact_record")
    map_rows = [row for row in rows if row["track_id"] == "map_native_sign_flip"]
    assert any(float(row["silent_wrong_rate"]) > 0.0 for row in map_rows)


def test_adaptive_point_additions_are_logged() -> None:
    payload = _load("results/level3_5b_dev/adaptive_search_ledger.json")
    assert payload["rows"]
    assert all("reason_for_addition" in row for row in payload["rows"])


def test_transition_extraction_is_deterministic() -> None:
    sample_rows = [
        {"track_id": "t", "method_id": "m", "cell_id": "c", "channel_id": "x", "corruption_label": "0.0", "external_corruption_spec": {"severity_value": 0.0}, "exact_recovery": True, "silent_wrong": False, "detected_failure": False},
        {"track_id": "t", "method_id": "m", "cell_id": "c", "channel_id": "x", "corruption_label": "0.1", "external_corruption_spec": {"severity_value": 0.1}, "exact_recovery": False, "silent_wrong": True, "detected_failure": False},
        {"track_id": "t", "method_id": "m", "cell_id": "c", "channel_id": "x", "corruption_label": "0.2", "external_corruption_spec": {"severity_value": 0.2}, "exact_recovery": False, "silent_wrong": False, "detected_failure": True},
    ]
    first = extract_transition_regions(sample_rows)
    second = extract_transition_regions(sample_rows)
    assert first == second


def test_heldout_protocol_is_generated_but_not_executed() -> None:
    payload = _load("results/level3_5b_dev/heldout_protocol.json")
    assert payload["executed"] is False
    assert payload["bcf_track"]["status"] == BCF_TRACK_BLOCKED


def test_no_histogram_u2_context_or_cnm_imports() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "level3_5b_native_noise_frontiers.py").read_text(encoding="utf-8").lower()
    forbidden = ["histogram recovery", "query_context", "selective_policy", "temporal_memory", "cnm"]
    assert all(token not in source for token in forbidden)


def test_level3_5a_artifacts_remain_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/level3_5a/*", "docs/LEVEL3_5A*", "docs/LEVEL3_5B_FROZEN_PROTOCOL_DRAFT.md"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_required_artifacts_exist() -> None:
    expected = {
        "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md",
        "docs/LEVEL3_5B_HELDOUT_PROTOCOL.md",
        "results/level3_5b_dev/environment.json",
        "results/level3_5b_dev/frozen_development_protocol.json",
        "results/level3_5b_dev/semantic_manifests.jsonl",
        "results/level3_5b_dev/bch_configs.json",
        "results/level3_5b_dev/bcf_native_corruption_contract.json",
        "results/level3_5b_dev/adaptive_search_ledger.json",
        "results/level3_5b_dev/binary_trials.jsonl",
        "results/level3_5b_dev/map_trials.jsonl",
        "results/level3_5b_dev/bcf_trials.jsonl",
        "results/level3_5b_dev/binary_summary.csv",
        "results/level3_5b_dev/map_summary.csv",
        "results/level3_5b_dev/bcf_summary.csv",
        "results/level3_5b_dev/transition_regions.json",
        "results/level3_5b_dev/silent_error_summary.csv",
        "results/level3_5b_dev/resource_summary.csv",
        "results/level3_5b_dev/timing_summary.csv",
        "results/level3_5b_dev/heldout_protocol.json",
        "results/level3_5b_dev/claims.json",
        "results/level3_5b_dev/analysis.json",
    }
    for relpath in expected:
        assert (ROOT / relpath).exists(), relpath


def test_oracle_is_only_used_where_feasible() -> None:
    assert oracle_feasible("u1_f3_m10") is True
    assert oracle_feasible("u1_f3_m31") is False
    assert oracle_feasible("u1_f3_m68") is False


def test_bch_wrapper_real_config_roundtrip_works() -> None:
    config = next(row for row in build_bch_configs() if row.payload_bits == 15 and row.tier_id == "BCH_HIGH")
    wrapper = make_bch_wrapper(config)
    message = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=np.uint8)
    codeword = wrapper.encode(message)
    decoded, nerr = wrapper.decode(codeword)
    assert nerr == 0
    assert np.array_equal(decoded, message)


def test_binary_seed_ranges_are_serialized() -> None:
    analysis = _load("results/level3_5b_dev/analysis.json")
    assert analysis["fresh_seed_ranges"]["binary_track"] == BINARY_SEED_RANGES


def test_git_status_clean_after_commit() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md",
            "results/level3_5b_dev",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""
