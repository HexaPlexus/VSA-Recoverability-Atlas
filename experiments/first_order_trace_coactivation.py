from __future__ import annotations

import json
from pathlib import Path

from cgrn_hsr.first_order_trace_coactivation import (
    PRIMARY_QUERY_COUNT,
    PRIMARY_RECORD_COUNT,
    QUERY_SEED_RANGES,
    RESULTS_NAMESPACE,
    TRACE_DIM_OPTIONS,
    environment_snapshot,
    protocol_payload,
    run_first_order_trace_coactivation,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protocol = protocol_payload(repo_root)
    environment = environment_snapshot()
    corruption_cells = len(QUERY_SEED_RANGES)
    budget_contracts = len(protocol["budget_contracts"])
    trace_configs = len(TRACE_DIM_OPTIONS)
    primary_arms = 8
    expected_trials = primary_arms * corruption_cells * budget_contracts * trace_configs * PRIMARY_QUERY_COUNT
    print("Phase 7 execution plan")
    print(
        json.dumps(
            {
                "record_count": PRIMARY_RECORD_COUNT,
                "query_count_per_cell": PRIMARY_QUERY_COUNT,
                "budget_contracts": budget_contracts,
                "trace_dimension_configs": trace_configs,
                "corruption_cells": corruption_cells,
                "arms": primary_arms,
                "expected_trial_rows": expected_trials,
                "results_namespace": RESULTS_NAMESPACE,
                "device": environment["device"],
                "threads": environment["threads"],
                "protocol_hash": protocol["protocol_hash"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print("Running bounded development benchmark...")
    result = run_first_order_trace_coactivation(repo_root)
    print(
        json.dumps(
            {
                "engineering_verdict": result["analysis"]["engineering_verdict"],
                "scientific_verdict": result["analysis"]["scientific_verdict"],
                "implementation_verdict": result["analysis"]["implementation_verdict"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
