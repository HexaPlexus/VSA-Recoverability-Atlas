from __future__ import annotations

import ast
import json
import subprocess
import sys
from itertools import permutations
from pathlib import Path

from cgrn_hsr.oracle_portfolio_complementarity import (
    LAZY_FALLBACK_VIEW,
    METHOD_ABSTAIN,
    METHOD_BCF_NATIVE,
    METHOD_MAP_D1024_FAST,
    METHOD_MAP_D1024_ROBUST,
    METHOD_MAP_D512_FAST,
    NON_ABSTAIN_METHODS,
    PREMATERIALIZED_ALL_VIEWS,
    RESCUE_COUNT_THRESHOLD,
    SPLIT_SPECS,
    STATIC_THRESHOLDS,
    apply_static_policy,
    canonical_json_hash,
    current_stage_seed_set,
    discover_historical_seed_markers,
    evaluate_gates,
    exact_mcnemar_p_value,
    generate_random_distribution,
    oracle_trial_result,
    resolve_frozen_methods,
    seeds_are_fresh,
    strategy_trial_result,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _fake_method(
    *,
    method_id: str,
    correct: bool,
    accepted: bool,
    latency: float,
    materialization: float,
    persistent: int,
    transient: int = 10,
    representation_key: str | None = None,
) -> dict[str, object]:
    return {
        "method_id": method_id,
        "ground_truth_correct": correct,
        "correct_and_accepted": correct and accepted,
        "verifier_accepted": accepted,
        "wrong_and_accepted": accepted and (not correct),
        "latency_total_query_sec": latency,
        "materialization_time_sec": materialization,
        "persistent_bytes": persistent,
        "transient_bytes": transient,
        "representation_key": representation_key,
        "cell_id": "u1_boundary_2",
    }


def test_release_and_frozen_artifacts_unchanged() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "results/level3_2",
            "results/level3_2b",
            "results/level3_5b_heldout",
            "results/level3_5b_heldout_v2",
            "results/level3_5b_heldout_v3",
            "results/level3_5b_gate_specification",
            "results/level3_5b_gate_consistency_repair",
            "docs/PUBLIC_RELEASE_AUDIT.md",
            "docs/PUBLIC_RELEASE_BASELINE.md",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.strip()
    assert result == ""


def test_seed_ranges_are_fresh_and_heldout_free() -> None:
    ok, report = seeds_are_fresh(ROOT)
    assert ok is True
    assert report["overlapping_explicit_seeds"] == []
    assert report["overlapping_marker_files"] == {}
    current = current_stage_seed_set()
    assert len(current) == sum(spec["count"] for split in SPLIT_SPECS.values() for spec in split.values())
    assert min(current) > 970_000_000


def test_historical_seed_markers_are_discoverable() -> None:
    markers = {path.replace("\\", "/"): numbers for path, numbers in discover_historical_seed_markers(ROOT).items()}
    assert "results/level3_2/frozen_protocol.json" in markers
    assert "results/level3_2b/frozen_protocol.json" in markers
    assert any(path.endswith("decoder_certified_codebook_v0_1/frozen_protocol.yaml") for path in markers)


def test_frozen_method_hashes_match_source_artifacts() -> None:
    methods = resolve_frozen_methods(ROOT)
    level3_2 = _load_json("results/level3_2/frozen_configs.json")
    level3_2b = _load_json("results/level3_2b/map_arm_configs.json")
    map_d512 = next(row for row in level3_2["map_configs"] if row["config_id"] == "map_d512")
    map_d1024 = next(row for row in level3_2["map_configs"] if row["config_id"] == "map_d1024")
    robust = next(row for row in level3_2b["map_arms"] if row["arm_id"] == "map_1024_step32_r4_best_native_reconstruction")
    assert methods[METHOD_MAP_D512_FAST].config_hash == canonical_json_hash(map_d512)
    assert methods[METHOD_MAP_D1024_FAST].config_hash == canonical_json_hash(map_d1024)
    assert methods[METHOD_MAP_D1024_ROBUST].config_hash == canonical_json_hash(robust)


def test_static_policy_uses_only_threshold_contract() -> None:
    policy = {"policy_id": "THRESHOLD:22", "threshold": 22, "low_method": METHOD_MAP_D512_FAST, "high_method": METHOD_BCF_NATIVE}
    assert apply_static_policy(policy, {"M": 10}) == METHOD_MAP_D512_FAST
    assert apply_static_policy(policy, {"M": 68}) == METHOD_BCF_NATIVE
    assert STATIC_THRESHOLDS == (10, 22, 31)


def test_oracle_selects_cheapest_correct_method() -> None:
    trial = {
        METHOD_MAP_D512_FAST: _fake_method(method_id=METHOD_MAP_D512_FAST, correct=False, accepted=False, latency=0.02, materialization=0.01, persistent=100, representation_key="map_d512"),
        METHOD_MAP_D1024_FAST: _fake_method(method_id=METHOD_MAP_D1024_FAST, correct=True, accepted=True, latency=0.04, materialization=0.02, persistent=200, representation_key="map_d1024"),
        METHOD_MAP_D1024_ROBUST: _fake_method(method_id=METHOD_MAP_D1024_ROBUST, correct=True, accepted=True, latency=0.10, materialization=0.03, persistent=200, representation_key="map_d1024"),
        METHOD_BCF_NATIVE: _fake_method(method_id=METHOD_BCF_NATIVE, correct=True, accepted=True, latency=0.20, materialization=0.05, persistent=300, representation_key="bcf_d512"),
    }
    result = oracle_trial_result(trial, mode="ORACLE_DIRECT_MIN_COST_CORRECT", cost_mode=PREMATERIALIZED_ALL_VIEWS)
    assert result["accepted_method"] == METHOD_MAP_D1024_FAST
    assert result["ground_truth_correct"] is True


def test_oracle_abstains_when_all_methods_fail() -> None:
    trial = {
        method: _fake_method(method_id=method, correct=False, accepted=False, latency=0.05, materialization=0.01, persistent=10, representation_key=method.lower())
        for method in NON_ABSTAIN_METHODS
    }
    result = oracle_trial_result(trial, mode="ORACLE_DIRECT_MIN_COST_CORRECT", cost_mode=PREMATERIALIZED_ALL_VIEWS)
    assert result["accepted_method"] == METHOD_ABSTAIN
    assert result["coverage"] == 0.0


def test_verifier_constrained_oracle_excludes_rejected_outputs() -> None:
    trial = {
        METHOD_MAP_D512_FAST: _fake_method(method_id=METHOD_MAP_D512_FAST, correct=True, accepted=False, latency=0.01, materialization=0.01, persistent=100, representation_key="map_d512"),
        METHOD_MAP_D1024_FAST: _fake_method(method_id=METHOD_MAP_D1024_FAST, correct=True, accepted=True, latency=0.03, materialization=0.02, persistent=200, representation_key="map_d1024"),
        METHOD_MAP_D1024_ROBUST: _fake_method(method_id=METHOD_MAP_D1024_ROBUST, correct=True, accepted=True, latency=0.06, materialization=0.02, persistent=200, representation_key="map_d1024"),
        METHOD_BCF_NATIVE: _fake_method(method_id=METHOD_BCF_NATIVE, correct=False, accepted=False, latency=0.09, materialization=0.04, persistent=300, representation_key="bcf_d512"),
    }
    result = oracle_trial_result(trial, mode="ORACLE_VERIFIER_CONSTRAINED", cost_mode=PREMATERIALIZED_ALL_VIEWS)
    assert result["accepted_method"] == METHOD_MAP_D1024_FAST


def test_fixed_cascade_accumulates_latency_and_stops_on_accept() -> None:
    trial = {
        METHOD_MAP_D512_FAST: _fake_method(method_id=METHOD_MAP_D512_FAST, correct=False, accepted=False, latency=0.02, materialization=0.01, persistent=100, representation_key="map_d512"),
        METHOD_MAP_D1024_FAST: _fake_method(method_id=METHOD_MAP_D1024_FAST, correct=True, accepted=True, latency=0.04, materialization=0.02, persistent=200, representation_key="map_d1024"),
        METHOD_MAP_D1024_ROBUST: _fake_method(method_id=METHOD_MAP_D1024_ROBUST, correct=True, accepted=True, latency=0.20, materialization=0.03, persistent=200, representation_key="map_d1024"),
        METHOD_BCF_NATIVE: _fake_method(method_id=METHOD_BCF_NATIVE, correct=True, accepted=True, latency=0.30, materialization=0.05, persistent=300, representation_key="bcf_d512"),
    }
    result = strategy_trial_result(trial, (METHOD_MAP_D512_FAST, METHOD_MAP_D1024_FAST, METHOD_BCF_NATIVE), cost_mode=PREMATERIALIZED_ALL_VIEWS)
    assert result["accepted_method"] == METHOD_MAP_D1024_FAST
    assert result["methods_invoked"] == 2
    assert abs(result["latency_sec"] - 0.06) < 1e-9


def test_lazy_materialization_and_dual_representation_are_counted() -> None:
    trial = {
        METHOD_MAP_D512_FAST: _fake_method(method_id=METHOD_MAP_D512_FAST, correct=False, accepted=False, latency=0.02, materialization=0.01, persistent=100, representation_key="map_d512"),
        METHOD_MAP_D1024_FAST: _fake_method(method_id=METHOD_MAP_D1024_FAST, correct=False, accepted=False, latency=0.04, materialization=0.02, persistent=200, representation_key="map_d1024"),
        METHOD_MAP_D1024_ROBUST: _fake_method(method_id=METHOD_MAP_D1024_ROBUST, correct=False, accepted=False, latency=0.20, materialization=0.03, persistent=200, representation_key="map_d1024"),
        METHOD_BCF_NATIVE: _fake_method(method_id=METHOD_BCF_NATIVE, correct=True, accepted=True, latency=0.30, materialization=0.05, persistent=300, representation_key="bcf_d512"),
    }
    result = strategy_trial_result(trial, (METHOD_MAP_D512_FAST, METHOD_BCF_NATIVE), cost_mode=LAZY_FALLBACK_VIEW)
    assert result["accepted_method"] == METHOD_BCF_NATIVE
    assert result["persistent_bytes"] == 400
    assert abs(result["cold_latency_sec"] - (0.02 + 0.30 + 0.01 + 0.05)) < 1e-9


def test_random_distribution_matches_target_budget_within_tolerance() -> None:
    calibration_rows = []
    for method, latency in (
        (METHOD_MAP_D512_FAST, 0.02),
        (METHOD_MAP_D1024_FAST, 0.04),
        (METHOD_MAP_D1024_ROBUST, 0.08),
        (METHOD_BCF_NATIVE, 0.10),
    ):
        for _ in range(4):
            calibration_rows.append({"method_id": method, "latency_total_query_sec": latency})
    distribution = generate_random_distribution(calibration_rows, target_latency=0.05)
    expected = sum(
        distribution[method] * latency
        for method, latency in (
            (METHOD_MAP_D512_FAST, 0.02),
            (METHOD_MAP_D1024_FAST, 0.04),
            (METHOD_MAP_D1024_ROBUST, 0.08),
            (METHOD_BCF_NATIVE, 0.10),
        )
    )
    assert abs(expected - 0.05) <= 0.01


def test_fixed_order_permutations_are_complete() -> None:
    assert len(list(permutations(NON_ABSTAIN_METHODS))) == 24


def test_exact_mcnemar_is_symmetric() -> None:
    assert exact_mcnemar_p_value(3, 7) == exact_mcnemar_p_value(7, 3)


def test_gate_logic_detects_static_route_sufficiency() -> None:
    method_rows = [
        {"subset": "ALL_FINAL", "method_id": METHOD_MAP_D512_FAST, "accepted_exact_coverage": 0.70, "conditional_risk": 0.0, "median_latency_sec": 0.02, "mean_persistent_bytes": 100},
        {"subset": "ALL_FINAL", "method_id": METHOD_BCF_NATIVE, "accepted_exact_coverage": 0.80, "conditional_risk": 0.0, "median_latency_sec": 0.10, "mean_persistent_bytes": 300},
        {"subset": "FINAL_NON_EASY", "method_id": METHOD_MAP_D512_FAST, "accepted_exact_coverage": 0.60, "conditional_risk": 0.0, "median_latency_sec": 0.02, "mean_persistent_bytes": 100},
        {"subset": "FINAL_NON_EASY", "method_id": METHOD_BCF_NATIVE, "accepted_exact_coverage": 0.80, "conditional_risk": 0.0, "median_latency_sec": 0.10, "mean_persistent_bytes": 300},
    ]
    rescue_rows = [
        {"subset": "FINAL_NON_EASY", "failed_method": METHOD_MAP_D512_FAST, "rescue_method": METHOD_BCF_NATIVE, "rescue_rate_given_failure": 0.2, "rescued_trial_count": RESCUE_COUNT_THRESHOLD, "verifier_accepted_rescue_count": 4, "verifier_accepted_rescue_rate_given_failure": 0.2, "reverse_rescue_count": 0}
    ]
    oracle_rows = [
        {"strategy_id": "ORACLE_DIRECT_MIN_COST_CORRECT", "subset": "FINAL_NON_EASY", "cost_mode": PREMATERIALIZED_ALL_VIEWS, "accepted_exact_coverage": 0.86},
        {"strategy_id": "ORACLE_DIRECT_MIN_COST_CORRECT", "subset": "FINAL_ALL", "cost_mode": PREMATERIALIZED_ALL_VIEWS, "accepted_exact_coverage": 0.86},
        {"strategy_id": "ORACLE_VERIFIER_CONSTRAINED", "subset": "FINAL_NON_EASY", "cost_mode": PREMATERIALIZED_ALL_VIEWS, "accepted_exact_coverage": 0.84},
    ]
    static_rows = [
        {"subset": "FINAL_NON_EASY", "profile": "BALANCED", "cost_mode": PREMATERIALIZED_ALL_VIEWS, "accepted_exact_coverage": 0.85}
    ]
    strategy_rows = [
        {"strategy_id": "THRESHOLD:22", "subset": "FINAL_ALL", "cost_mode": PREMATERIALIZED_ALL_VIEWS, "accepted_exact_coverage": 0.85, "silent_wrong_rate": 0.0, "median_latency_sec": 0.05, "mean_persistent_bytes": 200}
    ]
    gates = evaluate_gates(method_rows, rescue_rows, oracle_rows, static_rows, strategy_rows)
    assert gates["gate_oracle_gain"] is True
    assert gates["gate_static_route_sufficiency"] is True


def test_static_route_fit_source_uses_calibration_only() -> None:
    source = (ROOT / "src" / "cgrn_hsr" / "oracle_portfolio_complementarity.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fit_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fit_static_routes")
    fit_source = ast.get_source_segment(source, fit_node) or ""
    assert 'row["split"] == "PORTFOLIO_CALIBRATION"' in fit_source
    assert "best_policy = None" in fit_source


def test_evidence_registry_validator_remains_green() -> None:
    result = subprocess.run(
        [sys.executable, "scripts\\validate_evidence_registry.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Hypotheses:" in result.stdout
