# Level 3 Frozen Benchmark Protocol

Schema version: `level3-0-substrate-audit-v1`

## Frozen semantics

- Semantic payload axes: `F`, `M`, `K`.
- Native representation axes are separate: dimension/code length, alphabet, sparsity/block count, field size, and subcode dimensions.
- Equal `D` is not sufficient fairness on its own.

## Noise categories

1. Clean capacity.
2. Native coordinate corruption.
3. Erasure.
4. Semantic distractor superposition.

## Phase-boundary protocol

- Development uses coarse search with `16` trials per point only to identify easy, boundary, and failure regions.
- Freeze easy anchors, boundary cells, failure anchors, and selected noise cells before held-out.
- Held-out uses `64-128` paired trials per frozen cell with no tuning after inspection.

## Timing and memory

- Report materialization time, decode latency, and end-to-end latency separately.
- Report observation bytes, codebook bytes, runtime-state bytes, and peak RAM/VRAM.

## Disabled mechanisms

- Context policy, CNM/H2, semantic pruning, authority controller, hierarchy, and warm transfer are disabled for the whole Level 3 shootout.

## Effect gate

- A substrate is materially stronger only if it creates a new nondominated Pareto point or crosses one of the frozen material-effect thresholds.
- Tiny isolated wins do not authorize production promotion.

## Held-out discipline

- Level 3.0 is audit/design only. No long held-out substrate run is authorized here.
