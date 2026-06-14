from __future__ import annotations

from pathlib import Path

from cgrn_hsr.baseline import (
    BaselineConfig,
    run_trial,
    save_operating_points,
    save_summary_csv,
    save_trials_jsonl,
    select_operating_points,
    summarize_trials,
)

MASTER_SEED = 20260614
TRIALS_PER_CONFIG = 12
RESULTS_DIR = Path("results") / "level1a"


def make_initial_grid() -> list[BaselineConfig]:
    configs: list[BaselineConfig] = []
    for dimensions in (256, 512, 1024):
        for num_factors, domain_size in ((3, 5), (4, 10), (5, 20)):
            for external_noise in (0, 2):
                configs.append(
                    BaselineConfig(
                        dimensions=dimensions,
                        num_factors=num_factors,
                        domain_size=domain_size,
                        external_noise=external_noise,
                    )
                )
    return configs


def find_transition_configs(summary_rows: list[dict]) -> list[BaselineConfig]:
    by_family: dict[tuple[int, int, int], dict[int, float]] = {}
    for row in summary_rows:
        family = (row["D"], row["F"], row["M"])
        by_family.setdefault(family, {})[row["external_noise"]] = row["exact_recovery_rate"]

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
                    external_noise=1,
                )
            )
    return expansions


def fallback_expansions() -> list[BaselineConfig]:
    return [
        BaselineConfig(dimensions=2048, num_factors=3, domain_size=5, external_noise=0),
        BaselineConfig(dimensions=128, num_factors=6, domain_size=30, external_noise=3),
    ]


def run_configs(configs: list[BaselineConfig], start_index: int = 0) -> list:
    trials = []
    for config_index, config in enumerate(configs, start=start_index):
        for trial_index in range(TRIALS_PER_CONFIG):
            seed = MASTER_SEED + config_index * 1000 + trial_index
            trials.append(run_trial(config, seed=seed, master_seed=MASTER_SEED))
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
