# Portfolio Oracle Complementarity Audit

## Verdict

`ADOPT`

## Prior Art

- Algorithm portfolios and per-instance solver selection
- SATzilla-style algorithm selection and oracle baselines
- Fixed-order cascades and early-exit systems
- Selective prediction and abstention-first evaluation
- Budgeted inference and utility-sensitive deployment analysis

## Coverage

- `ADOPT`: paired instance analysis, oracle upper bounds, Pareto frontiers, fixed-order cascades, random controls
- `WRAP`: existing frozen MAP and BCF adapters plus verifier-compatible replay checks
- `COMPARE`: best single method, static threshold route, random route, random fixed-order cascade, verifier-constrained oracle
- `BLOCK`: learned router, hidden-state transfer across substrates, hardware modelling, new VSA method implementation

## Why Not Scratch

- The repository already contains lawful MAP and official-BFC wrappers for the clean `F=3` single-product contract.
- Adding a new router, ANN layer, or shared latent state before proving oracle complementarity would be pure anti-reproducible complexity.
- This stage needs only a thin paired harness and cost accounting layer, not a new decoding framework.

## Minimal Path

1. Resolve frozen method configs and hashes from existing Level 3.2 / 3.2b artifacts.
2. Generate fresh paired semantic trials with disjoint development-only seeds.
3. Run independent MAP/BCF executions under a common semantic trial description.
4. Compare single methods, oracles, fixed-order cascades, static thresholds, and random controls.
5. Stop the cascade line unless verified, cost-aware complementarity survives static routing.

## Claim Gate

- Claim under test:
  - different already-implemented VSA recovery methods may complement each other on the same lawful semantic task
- Authority boundary:
  - methods propose
  - verifier accepts or rejects
  - oracle analyses are descriptive upper bounds only
- Required falsifier:
  - best expensive method dominates the same failures that defeat cheaper methods, or static routing captures all value
- Forbidden strengthening:
  - no learned router
  - no FPGA/Lava seam
  - no new cross-substrate latent transfer
