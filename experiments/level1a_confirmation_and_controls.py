from __future__ import annotations

import json
import math
from pathlib import Path

from cgrn_hsr.baseline import (
    BaselineConfig,
    CONFIRMATION_TRIALS_PER_POINT,
    confirmation_seed_ranges,
    confirm_operating_point,
    build_trial_problem,
    method_selection_seed,
    run_trial_on_problem,
    save_confirmation_payload,
    save_summary_csv,
    save_trials_jsonl,
    summarize_trials,
)

LEVEL1A_COMMIT = "09748d4ad250cbf4a88a6214812728dc2d56ab19"
HELD_OUT_MASTER_SEED = 21260614
CONFIRMATION_RESULTS_DIR = Path("results") / "level1a_confirmation"
CONTROLS_RESULTS_DIR = Path("results") / "level1b"

FROZEN_POINTS: dict[str, BaselineConfig] = {
    "EASY": BaselineConfig(dimensions=256, num_factors=3, domain_size=5, structured_distractor_count=0),
    "BORDERLINE": BaselineConfig(dimensions=1024, num_factors=3, domain_size=5, structured_distractor_count=2),
    "COLLAPSE": BaselineConfig(dimensions=1024, num_factors=4, domain_size=10, structured_distractor_count=0),
}


def confirmation_trials() -> list:
    trials = []
    seed_specs = confirmation_seed_ranges()
    for label, config in FROZEN_POINTS.items():
        start = seed_specs[label]["start"]
        for seed in range(start, start + CONFIRMATION_TRIALS_PER_POINT):
            trials.append(
                run_trial_on_problem(
                    build_trial_problem(config, seed),
                    master_seed=HELD_OUT_MASTER_SEED,
                    operating_point_label=label,
                )
            )
    return trials


def confirmation_payload(summary_rows: list[dict]) -> list[dict]:
    payload_rows = []
    by_label = {row["operating_point_label"]: row for row in summary_rows}
    for label in ("EASY", "BORDERLINE", "COLLAPSE"):
        row = by_label[label]
        payload_rows.append(
            {
                "operating_point_label": label,
                "status": confirm_operating_point(label, row["exact_recovery_rate"]),
                **row,
            }
        )
    return payload_rows


def candidate_sizes(domain_size: int) -> list[tuple[str, int]]:
    return [
        ("half", math.ceil(domain_size / 2)),
        ("quarter", max(2, math.ceil(domain_size / 4))),
    ]


def control_trials() -> list:
    trials = []
    seed_specs = confirmation_seed_ranges()
    for label, config in FROZEN_POINTS.items():
        start = seed_specs[label]["start"]
        for seed in range(start, start + CONFIRMATION_TRIALS_PER_POINT):
            problem = build_trial_problem(config, seed)
            trials.append(
                run_trial_on_problem(
                    problem,
                    master_seed=HELD_OUT_MASTER_SEED,
                    operating_point_label=label,
                    method="global",
                    reduction_ratio_label="full",
                )
            )
            for ratio_label, subset_size in candidate_sizes(config.domain_size):
                for method in ("random_unconditional", "random_truth_included"):
                    trials.append(
                        run_trial_on_problem(
                            problem,
                            master_seed=HELD_OUT_MASTER_SEED,
                            operating_point_label=label,
                            method=method,
                            reduction_ratio_label=ratio_label,
                            subset_size=subset_size,
                            selection_seed=method_selection_seed(seed, method, ratio_label),
                        )
                    )
    return trials


def save_controls_payload(path: Path, summary_rows: list[dict]) -> None:
    payload = {
        "level1a_commit": LEVEL1A_COMMIT,
        "seed_policy": confirmation_seed_ranges(),
        "controls_summary": summary_rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def main() -> None:
    confirmation = confirmation_trials()
    confirmation_summary = summarize_trials(confirmation)
    confirmation_rows = confirmation_payload(confirmation_summary)
    save_trials_jsonl(CONFIRMATION_RESULTS_DIR / "trials.jsonl", confirmation)
    save_summary_csv(CONFIRMATION_RESULTS_DIR / "summary.csv", confirmation_summary)
    save_confirmation_payload(
        CONFIRMATION_RESULTS_DIR / "operating_points_confirmation.json",
        confirmation_rows=confirmation_rows,
        seed_ranges=confirmation_seed_ranges(),
        level1a_commit=LEVEL1A_COMMIT,
    )

    controls = control_trials()
    controls_summary = summarize_trials(controls)
    save_trials_jsonl(CONTROLS_RESULTS_DIR / "trials.jsonl", controls)
    save_summary_csv(CONTROLS_RESULTS_DIR / "summary.csv", controls_summary)
    save_controls_payload(CONTROLS_RESULTS_DIR / "paired_controls.json", controls_summary)

    print(f"confirmation_trials={len(confirmation)}")
    print(f"control_trials={len(controls)}")
    for row in confirmation_rows:
        print(
            f"{row['operating_point_label']}={row['status']} "
            f"exact={row['exact_recovery_rate']:.3f} "
            f"false_consensus={row['false_consensus_rate']:.3f} "
            f"unsettled={row['unsettled_failure_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
