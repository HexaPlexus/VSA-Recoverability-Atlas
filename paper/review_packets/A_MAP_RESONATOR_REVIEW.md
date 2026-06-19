---
packet_id: MAP_RESONATOR_REVIEW
manuscript_sections:
  - "2. Scope and Terminology"
  - "6. Dimensional Capacity and Dense MAP Recovery"
  - "7. Context-Conditioned Search and Selective Computation"
  - "12. Failure-Mode Atlas"
---

# Packet A: VSA / MAP / Resonator Review

## Reviewer profile

This packet is for readers who know MAP, resonator networks, factor-specific domains, or dense VSA factorization baselines.

## Sections to review

- Section 2: task boundaries and terminology
- Section 6: dense MAP capacity and compute interpretation
- Section 7: context-conditioned search and selective computation
- Section 12: failure modes related to false attractors, interference, and convergence

## What the manuscript currently claims

- MAP resonators are useful bounded baselines, not universal factorizers.
- The common clean F=3 envelopes expose a practical transition region rather than all-or-nothing behavior.
- Context can help candidate restriction, but local narrowing gains do not automatically become global Pareto gains.
- Recurrent dense-MAP failure modes include capacity collapse, false attractors, diffuse interference, and flat validation geometry.

## Key repository anchors

- `level3_2_map_budget_robustness`
- `level3_2b`
- `level1_context_conditioned_search`

## Specific questions

1. Is MAP represented accurately and fairly, especially the distinction between easy-cell success and hard-cell collapse?
2. Are resonator-network limitations stated in a technically responsible way, without overclaiming impossibility?
3. Are the context-conditioned search claims scoped correctly as search-control effects rather than structural recovery proofs?
4. Which primary resonator or MAP source is still missing or underused?
5. Is any terminology likely to mislead a specialist reviewer?

## Compact extract

The core MAP conclusion is deliberately bounded: MAP remains a necessary baseline and a useful diagnostic instrument, but in this repository it repeatedly buys recovery with more dimension, more iteration budget, or more restarts, and it still fails on the hard common clean F=3 cells that native BCF solves.
