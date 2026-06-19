from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import torch

from cgrn_hsr.competitors.ibm_bcf_audit import upstream_clone_path, upstream_commit_sha
from cgrn_hsr.single_product_shootout import (
    BCF_OFFICIAL_CLASS_PATH,
    EASY_CELL,
    LEVEL1F3_SCHEMA_VERSION,
    METHOD_GLOBAL,
    METHOD_ORACLE_HALF,
    METHOD_RANDOM_HALF,
    METHOD_SEMANTIC_HALF,
    PRIMARY_CELL,
    SUBSTRATE_BCF,
    SUBSTRATE_MAP,
    build_bcf_config_candidates,
    build_single_product_task,
    common_outcome,
    detect_same_device_timing_status,
    evaluate_bcf_trial,
    evaluate_map_trial,
    level1f3_config_seed_set,
    level1f3_development_seed_set,
    level1f3_heldout_seed_set,
    level1f3_heldout_seed_ranges,
    level1f3_seed_sets_are_disjoint,
    measure_decode_timing,
    method_subset_size_label,
    prepare_bcf_trial,
    select_shared_candidate_subset,
    subset_size_for_label,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeBCF:
    calls = 0

    def __init__(self, D, F, Mx, B, IM=None, useCuda=False, **kwargs):
        FakeBCF.calls += 1
        self._device = "cpu"
        self._IM = IM.clone() if IM is not None else torch.arange(F * Mx * B, dtype=torch.float32).view(F, Mx, B)
        self._matIM = torch.zeros(F, Mx, B, max(1, D // B), dtype=torch.float32)
        self._init_guess = torch.zeros(F, B, max(1, D // B), dtype=torch.float32)
        self._mx = Mx
        self._f = F
        self._last_iterations = torch.ones(1, 1, dtype=torch.float32)

    def encode(self, u):
        return torch.zeros(u.size(0), self._IM.size(-1), 1, dtype=torch.int32)

    def decode(self, observation, max_iter):
        self._last_iterations = torch.full((1, 1), float(min(3, max_iter)))
        return torch.zeros(1, self._f, dtype=torch.long)

    def _get_number_iter(self):
        return self._last_iterations


def test_level1f3_seed_ranges_are_non_overlapping() -> None:
    assert level1f3_seed_sets_are_disjoint() is True
    assert level1f3_config_seed_set().isdisjoint(level1f3_development_seed_set())
    assert level1f3_config_seed_set().isdisjoint(level1f3_heldout_seed_set())
    assert level1f3_development_seed_set().isdisjoint(level1f3_heldout_seed_set())


def test_level1f3_heldout_amendment_counts_are_explicit() -> None:
    ranges = level1f3_heldout_seed_ranges()

    assert ranges["COLLAPSE_SINGLE_PRIMARY"]["count"] == 128
    assert ranges["COLLAPSE_SINGLE_STRESS"]["count"] == 64
    assert ranges["EASY_SINGLE"]["count"] == 64


def test_single_product_task_contains_no_mixture_metadata() -> None:
    bundle = build_single_product_task(EASY_CELL, 34260614)

    assert bundle.task.distractor_target_indices == []
    assert bundle.task.query_valid_source_indices == []
    assert bundle.task.active_l1 == bundle.task.active_l1
    assert bundle.task.active_l2 == bundle.task.active_context
    assert bundle.task.context_prediction is not None


def test_semantic_selector_does_not_depend_on_ground_truth() -> None:
    bundle = build_single_product_task(EASY_CELL, 34260615)
    changed_target = torch.tensor([(value + 1) % EASY_CELL.config.domain_size for value in bundle.task.target_indices], dtype=torch.long)
    changed_task = replace(bundle.task, target_indices=[int(value) for value in changed_target.tolist()])
    changed_bundle = replace(bundle, task=changed_task, target_indices=changed_target)

    assert torch.equal(
        select_shared_candidate_subset(bundle, METHOD_SEMANTIC_HALF),
        select_shared_candidate_subset(changed_bundle, METHOD_SEMANTIC_HALF),
    )


def test_oracle_selector_explicitly_depends_on_truth() -> None:
    bundle = build_single_product_task(EASY_CELL, 34260616)
    changed_target = torch.tensor([(value + 1) % EASY_CELL.config.domain_size for value in bundle.task.target_indices], dtype=torch.long)
    changed_task = replace(bundle.task, target_indices=[int(value) for value in changed_target.tolist()])
    changed_bundle = replace(bundle, task=changed_task, target_indices=changed_target)

    assert not torch.equal(
        select_shared_candidate_subset(bundle, METHOD_ORACLE_HALF),
        select_shared_candidate_subset(changed_bundle, METHOD_ORACLE_HALF),
    )


def test_hard_subset_exact_size_and_determinism() -> None:
    bundle = build_single_product_task(PRIMARY_CELL, 34260617)
    subset_a = select_shared_candidate_subset(bundle, METHOD_RANDOM_HALF)
    subset_b = select_shared_candidate_subset(bundle, METHOD_RANDOM_HALF)

    assert subset_a.size(1) == subset_size_for_label(PRIMARY_CELL.config.domain_size, method_subset_size_label(METHOD_RANDOM_HALF))
    assert torch.equal(subset_a, subset_b)


def test_map_trial_uses_upstream_resonator_and_nonnegative_memory() -> None:
    bundle = build_single_product_task(EASY_CELL, 34260618)
    subset = select_shared_candidate_subset(bundle, METHOD_GLOBAL)
    trial = evaluate_map_trial(bundle, EASY_CELL, METHOD_GLOBAL, subset, device="cpu")

    assert trial.schema_version == LEVEL1F3_SCHEMA_VERSION
    assert trial.substrate == SUBSTRATE_MAP
    assert trial.uses_upstream_resonator is True
    assert trial.no_query_aware_mixture_input is True
    assert trial.native_codebook_bytes > 0
    assert trial.native_observation_bytes > 0
    assert trial.runtime_state_bytes is not None and trial.runtime_state_bytes >= 0
    assert trial.end_to_end_task_time_sec >= trial.factorization_time_sec >= 0.0


def test_bcf_trial_invokes_official_class_loader(monkeypatch) -> None:
    bundle = build_single_product_task(EASY_CELL, 34260619)
    subset = select_shared_candidate_subset(bundle, METHOD_GLOBAL)
    config = build_bcf_config_candidates()[0]
    FakeBCF.calls = 0
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.load_official_bcf_class", lambda repo_path: FakeBCF)
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.upstream_commit_sha", lambda repo_path: "test-sha")

    trial = evaluate_bcf_trial(
        bundle,
        EASY_CELL,
        METHOD_GLOBAL,
        subset,
        config=config,
        repo_path=upstream_clone_path(ROOT),
        prefer_cuda=False,
    )

    assert FakeBCF.calls >= 1
    assert trial.substrate == SUBSTRATE_BCF
    assert trial.uses_official_bcf_class is True
    assert trial.official_bcf_class_path == BCF_OFFICIAL_CLASS_PATH
    assert trial.bcf_config_id == config.config_id
    assert trial.runtime_state_bytes is not None and trial.runtime_state_bytes >= 0


def test_bcf_prepared_trial_reuses_one_full_codebook_across_methods(monkeypatch) -> None:
    bundle = build_single_product_task(EASY_CELL, 342606191)
    global_subset = select_shared_candidate_subset(bundle, METHOD_GLOBAL)
    random_subset = select_shared_candidate_subset(bundle, METHOD_RANDOM_HALF)
    config = build_bcf_config_candidates()[0]
    FakeBCF.calls = 0
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.load_official_bcf_class", lambda repo_path: FakeBCF)
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.upstream_commit_sha", lambda repo_path: "test-sha")

    prepared = prepare_bcf_trial(
        bundle,
        config,
        repo_path=upstream_clone_path(ROOT),
        prefer_cuda=False,
    )
    global_trial = evaluate_bcf_trial(
        bundle,
        EASY_CELL,
        METHOD_GLOBAL,
        global_subset,
        config=config,
        repo_path=upstream_clone_path(ROOT),
        prefer_cuda=False,
        prepared=prepared,
    )
    random_trial = evaluate_bcf_trial(
        bundle,
        EASY_CELL,
        METHOD_RANDOM_HALF,
        random_subset,
        config=config,
        repo_path=upstream_clone_path(ROOT),
        prefer_cuda=False,
        prepared=prepared,
    )

    assert FakeBCF.calls == 2
    assert global_trial.materialization_time_sec > 0.0
    assert random_trial.materialization_time_sec >= prepared.shared_materialization_time_sec
    assert global_trial.factorization_time_sec >= 0.0
    assert random_trial.factorization_time_sec >= 0.0


def test_map_and_bcf_share_one_abstract_task_and_subset_identities(monkeypatch) -> None:
    bundle = build_single_product_task(EASY_CELL, 34260620)
    subset = select_shared_candidate_subset(bundle, METHOD_RANDOM_HALF)
    config = build_bcf_config_candidates()[0]
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.load_official_bcf_class", lambda repo_path: FakeBCF)
    monkeypatch.setattr("cgrn_hsr.single_product_shootout.upstream_commit_sha", lambda repo_path: "test-sha")

    map_trial = evaluate_map_trial(bundle, EASY_CELL, METHOD_RANDOM_HALF, subset, device="cpu")
    bcf_trial = evaluate_bcf_trial(
        bundle,
        EASY_CELL,
        METHOD_RANDOM_HALF,
        subset,
        config=config,
        repo_path=upstream_clone_path(ROOT),
        prefer_cuda=False,
    )

    assert map_trial.task_seed == bcf_trial.task_seed
    assert map_trial.target_indices == bcf_trial.target_indices
    assert map_trial.candidate_subset_indices == bcf_trial.candidate_subset_indices


def test_common_outcome_covers_exact_partial_and_failure() -> None:
    target = torch.tensor([1, 2, 3], dtype=torch.long)
    assert common_outcome(torch.tensor([1, 2, 3]), target)[0] == "EXACT_RECOVERY"
    assert common_outcome(torch.tensor([1, 0, 3]), target)[0] == "PARTIAL_RECOVERY"
    assert common_outcome(torch.tensor([0, 0, 0]), target)[0] == "FAILURE"


def test_cuda_timing_helper_synchronizes_when_requested(monkeypatch) -> None:
    sync_calls = {"count": 0}
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda: sync_calls.__setitem__("count", sync_calls["count"] + 1))
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda device=None: None)
    monkeypatch.setattr(torch.cuda, "max_memory_allocated", lambda device=None: 1234)

    def run_once():
        return {"ok": True}

    result, elapsed, peak_cuda, peak_cpu = measure_decode_timing(
        run_once,
        device="cuda:0",
        warmup_repeats=1,
        measure_repeats=2,
    )

    assert result == {"ok": True}
    assert elapsed >= 0.0
    assert peak_cuda == 1234
    assert peak_cpu is not None or peak_cpu is None
    assert sync_calls["count"] >= 4


def test_bcf_candidate_configs_are_officially_sourced() -> None:
    candidates = build_bcf_config_candidates()

    assert len(candidates) == 3
    assert {candidate.config_id for candidate in candidates} == {
        "official_hp_d256_b4_m10",
        "official_hp_d512_b4_m10",
        "official_hp_d1024_b4_m10",
    }
    assert all(candidate.source_path.startswith("experiments/200a_bcf/") for candidate in candidates)


def test_upstream_commit_is_still_pinned() -> None:
    assert upstream_commit_sha(upstream_clone_path(ROOT)) == "a353f1e918dcb515cad4a89c8e47ce24668954a7"


def test_same_device_timing_status_is_recorded() -> None:
    assert detect_same_device_timing_status(map_cuda_available=True) in {"same_wsl_gpu", "no_same_device_gpu"}


def test_core_windows_environment_stays_untouched() -> None:
    import torch as local_torch

    assert local_torch.__version__.startswith("2.12.")
    assert local_torch.cuda.is_available() is False


def test_hypothesis_file_is_unchanged() -> None:
    result = (
        __import__("subprocess")
        .run(
            ["git", "diff", "--name-only", "HEAD", "--", "CGRN-HSR_research_hypothesis.md"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        .stdout.strip()
    )
    assert result == ""
