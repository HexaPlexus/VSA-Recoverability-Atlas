# Level 3.2b MAP Compute-Budget Robustness Audit

Schema version: `level3-2b-map-budget-robustness-dev-v1`

## Scope

- Clean U1 only
- Fresh development seeds only
- No context, pruning, CNM/H2, controller, noise, U2, U3, or new decoder

## Verdict flags

- `bcf_representation_decoder_advantage_supported`: `True`
- `bcf_pareto_advantage_supported`: `True`
- `map_budget_artifact`: `False`
- `map_intermediate_region`: `True`
- `no_benefit_from_extra_map_compute`: `False`

## Best-by-cell MAP details

- `u1_boundary_31 / D=512`: best MAP arm `map_512_step32_r4_majority_vote` exact `0.375`, BCF `1.0`, gap `0.625`.
- `u1_boundary_31 / D=1024`: best MAP arm `map_1024_step32_r4_best_native_reconstruction` exact `0.5625`, BCF `1.0`, gap `0.4375`.
- `u1_separation_68 / D=512`: best MAP arm `map_512_step12` exact `0.0`, BCF `1.0`, gap `1.0`.
- `u1_separation_68 / D=1024`: best MAP arm `map_1024_wallclock_matched_bcf_p90` exact `0.0625`, BCF `1.0`, gap `0.9375`.

## Development note

This audit does not modify the frozen Level 3.2 held-out claim; it only tests whether extra MAP compute narrows the already confirmed frozen-baseline separation.

