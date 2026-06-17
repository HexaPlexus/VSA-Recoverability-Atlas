# Level 3.5b Prospective Gate Specification

- Schema: `level3-5b-gate-specification-v1`
- Completion verdict: `GATES_SPECIFIED_AND_FINAL_PROTOCOL_FROZEN`
- Ready verdict: `READY_FOR_LEVEL_3_5B_HELDOUT_V3`
- heldout_trials_observed: `0`
- heldout_outcomes_available_to_gate_design: `False`
- Protocol v2 hash: `649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf`
- Protocol v3 hash: `4b197802b51f2bf1d02798d3bca2e857cb77b22e8c39350759221725ba8a48f2`

## Classification

- PRE_EXECUTION_PROTOCOL_COMPLETION
- PROSPECTIVE_GATE_SPECIFICATION
- NO_HELDOUT_LEAKAGE

## Why v2 Was Incomplete

- v2 froze methods, cells, points, seeds, configs and metrics.
- v2 serialized disposition labels in `gates`, but not executable quantitative decision rules.
- The v2 runner therefore blocked execution before first trial.

## Recovered vs Newly Defined

- Recovered pre-heldout contract rules: `no_shared_noise_winner_contract_v1`
- Newly defined prospective rules from development-only evidence: `bch_binary_exact_record_dominance_v1, raw_neco_noise_gap_v1, generic_linear_practical_equivalence_v1, map_silent_collapse_v1, map_graceful_region_v1`

## Claim Limits

- No binary, BCH, NeCo, generic-linear, MAP or BCF held-out outcome has been observed.
- v3 is the first final executable confirmatory protocol for Level 3.5b.
- All gate thresholds remain development-calibrated and held-out-unseen.
