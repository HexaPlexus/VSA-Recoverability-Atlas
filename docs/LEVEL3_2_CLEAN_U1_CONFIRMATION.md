# Level 3.2 Clean U1 Confirmation

Schema version: `level3-2-clean-u1-heldout-v1`

## Frozen configs

- MAP: `map_d512`, `map_d1024`
- BCF family: `bcf_d512_f3_b4` with per-cell official `A`/`threshold` rows from the pinned IBM hyperparameter table

## Common held-out cells

- `F=3, M=10, trials=64`
- `F=3, M=22, trials=128`
- `F=3, M=31, trials=128`
- `F=3, M=68, trials=64`

## Capacity shift

- BCF vs `map_d512`: `2.497527` log10 units
- BCF vs `map_d1024`: `2.497527` log10 units

## Boundary brackets

- `BCF / bcf_d512_f3_b4`: largest `>=0.90` = `u1_separation_anchor`, smallest `<0.90` = `None`.
- `MAP / map_d1024`: largest `>=0.90` = `u1_easy_anchor`, smallest `<0.90` = `u1_boundary_1`.
- `MAP / map_d512`: largest `>=0.90` = `u1_easy_anchor`, smallest `<0.90` = `u1_boundary_1`.

## Timing note

- Timing uses a separate frozen 16-task subset per common cell with warm-up and synchronized CUDA measurements.
- Same-device status remained explicit throughout the run.

