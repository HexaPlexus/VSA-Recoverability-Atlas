from __future__ import annotations

from pathlib import Path

from cgrn_hsr.baseline import (
    BaselineConfig,
    PILOT_MASTER_SEED,
    PILOT_TRIALS_PER_CONFIG,
    run_trial,
    save_operating_points,
    save_summary_csv,
    save_trials_jsonl,
    select_operating_points,
    summarize_trials,
)

MASTER_SEED = PILOT_MASTER_SEED
TRIALS_PER_CONFIG = PILOT_TRIALS_PER_CONFIG
RESULTS_DIR = Path("results") / "level1a_v2"


def make_initial_grid() -> list[BaselineConfig]:
    configs: list[BaselineConfig] = []
        for dimensions in (256, 512, 1024):
        for num_factors, domain_size in ((3, 5), (4, 10), (5, 20)):
            for structured_distractor_count in (0, 2):
                configs.append(
                    BaselineConfig(
                        dimensions=dimensions,
                        num_factors=num_factors,
                        domain_size=domain_size,
                        structured_distractor_count=structured_distractor_count,
                    )
                )
    return configs


def find_transition_configs(summary_rows: list[dict]) -> list[BaselineConfig]:
    by_family: dict[tuple[int, int, int], dict[int, float]] = {}
    for row in summary_rows:
        family = (row["D"], row["F"], row["M"])
        by_family.setdefault(family, {})[row["structured_distractor_count"]] = row["exact_recovery_rate"]

    expansions: list[BaselineConfig] = []
    for (dimensions, num_factors, domain_size), rates in sorted(by_family.items()):
        low_noise = rates.get(0)
        high_noise = rates.get(2)
        if low_noise is None or high_noise is None:
            continue
        if low_noise >= 0.80 and high_noise <= 0.35:
            expansions.append(
                BaselineConfig(
                    dimensions=dimensions,
                    num_factors=num_factors,
                    domain_size=domain_size,
                    structured_distractor_count=1,
                )
            )
    return expansions


def fallback_expansions() -> list[BaselineConfig]:
    return [
        BaselineConfig(dimensions=2048, num_factors=3, domain_size=5, structured_distractor_count=0),
        BaselineConfig(dimensions=128, num_factors=6, domain_size=30, structured_distractor_count=3),
    ]


def run_configs(configs: list[BaselineConfig], start_index: int = 0) -> list:
    trials = []
    for config_index, config in enumerate(configs, start=start_index):
        for trial_index in range(TRIALS_PER_CONFIG):
            seed = MASTER_SEED + config_index * 1000 + trial_index
            trials.append(
                run_trial(
                    config,
                    seed=seed,
                    master_seed=MASTER_SEED,
                    operating_point_label="PILOT",
                )
            )
    return trials


def main() -> None:
    pilot_grid = make_initial_grid()
    trials = run_configs(pilot_grid)
    summary_rows = summarize_trials(trials)
    operating_points = select_operating_points(summary_rows)

    if operating_points["BORDERLINE"] is None:
        expansions = find_transition_configs(summary_rows)
        if expansions:
            trials.extend(run_configs(expansions, start_index=len(pilot_grid)))
            pilot_grid.extend(expansions)
            summary_rows = summarize_trials(trials)
            operating_points = select_operating_points(summary_rows)

    if any(operating_points[label] is None for label in ("EASY", "COLLAPSE")):
        expansions = fallback_expansions()
        trials.extend(run_configs(expansions, start_index=len(pilot_grid)))
        pilot_grid.extend(expansions)
        summary_rows = summarize_trials(trials)
        operating_points = select_operating_points(summary_rows)

    save_trials_jsonl(RESULTS_DIR / "trials.jsonl", trials)
    save_summary_csv(RESULTS_DIR / "summary.csv", summary_rows)
    save_operating_points(
        RESULTS_DIR / "operating_points.json",
        operating_points=operating_points,
        master_seed=MASTER_SEED,
        pilot_grid=pilot_grid,
    )

    print(f"saved_trials={len(trials)}")
    for label, row in operating_points.items():
        if row is None:
            print(f"{label}=NOT_FOUND")
            continue
        print(
            f"{label}={row['config_id']} "
            f"exact={row['exact_recovery_rate']:.3f} "
            f"false_consensus={row['false_consensus_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
