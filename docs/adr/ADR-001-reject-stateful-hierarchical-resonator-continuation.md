# ADR-001 - Reject Stateful Hierarchical Resonator Continuation

## Status

**ACCEPTED - experimentally falsified for the tested MAP-resonator operating envelope.**

## Context

CGRN-HSR initially proposed hierarchical search relaxation:

```text
L2 narrow context
-> L1 parent context
-> global domain
```

Five implementations were tested:

1. full cold `L2 -> L1 -> global` cascade
2. direct `L2 -> warm global` continuation
3. one-step `L1 probe -> warm global`
4. two-step `L1 probe -> warm global`
5. uncapped warm continuation

## Decision

The active runtime must not use iterative `L2 -> L1 -> global` resonator continuation.

The surviving execution path is:

```text
context-biased L2 attempt
-> calibrated accept
-> discard rejected L2 state
-> cold global fallback
-> accept or abstain
```

Hierarchical context remains valid for candidate organization and prior construction, but not for carrying resonator state between expanded search domains.

## Evidence

### Cold cascade

Level 1E commit: `46709fef4603dbb1f41c74188934c5d7de4218f6`  
Checkpoint before Level 1E.1: `6d885edb016bf6dcf2e4023f36e6232f21248d3b`  
Artifacts: [results/level1e/analysis.json](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e/analysis.json), [results/level1e/summary.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e/summary.csv)

Held-out Level 1E results:

- `COLLAPSE_SINGLE_PRIMARY`: coverage `0.40625`, selective risk `0.0`, false accept rate `0.0`, mean compute `546560.0`
- `COLLAPSE_SINGLE_STRESS`: coverage `0.203125`, selective risk `0.0`, false accept rate `0.0`, mean compute `670720.0`
- `EASY_SINGLE`: coverage `0.984375`, selective risk `0.031746031746031744`, false accept rate `0.03125`, mean compute `24804.0`

The full cold `L2 -> L1 -> global` cascade stayed safe on the primary and stress cells, but it cost more than `always_global` and the `L1` stage accepted no primary or stress cases. In practice `L1` acted as an expensive consistency probe rather than a useful runtime stage.

### Warm continuation

Level 1E.1 commit: `80cdfcfdabb54710e9bf1b34aff4888f68fddc1e`  
Accepted checkpoint: `33f9e44a7364c1640d47588d2cdb02eadafd3c75`  
Artifacts: [results/level1e1/analysis.json](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e1/analysis.json), [results/level1e1/summary.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e1/summary.csv), [results/level1e1/paired_comparisons.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e1/paired_comparisons.csv), [results/level1e1/probe_evidence.json](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e1/probe_evidence.json)

Held-out primary-cell comparison:

- `always_global_cold`: coverage `0.1875`, exact-or-valid recovery `0.1875`, mean compute `428800.0`
- `l2_then_cold_global`: coverage `0.4375`, exact-or-valid recovery `0.4375`, mean compute `319104.0`
- `l2_then_warm_global`: coverage `0.3125`, exact-or-valid recovery `0.3125`, mean compute `332544.0`

Held-out paired warm-vs-cold deltas on `COLLAPSE_SINGLE_PRIMARY`:

- `l2_then_warm_global`: recovery delta `-0.125`, compute delta `+13440.0`, `warm_helped=0`, `warm_hurt=8`
- `l2_probe1_then_warm_global`: recovery delta `-0.125`, compute delta `0.0`, `warm_helped=0`, `warm_hurt=8`
- `l2_probe2_then_warm_global`: recovery delta `-0.109375`, compute delta `+11520.0`, `warm_helped=1`, `warm_hurt=8`

Held-out `EASY_SINGLE` degradation:

- `l2_then_cold_global`: exact-or-valid recovery `0.984375`
- `l2_then_warm_global`: exact-or-valid recovery `0.453125`
- paired warm-vs-cold recovery delta `-0.53125`
- paired warm-vs-cold compute delta `+9060.0`
- `warm_helped=0`, `warm_hurt=34`

Warm continuation reduced primary recovery, produced zero or near-zero warm-helped cases, produced multiple warm-hurt cases, strongly degraded `EASY_SINGLE`, remained inferior even without the strict compute cap, and was not rescued by one-step or two-step probes.

### Cheap probes

One-step and two-step `L1` probes did not preserve the useful separation previously observed after a full `L1` run among the actually rejected `L2` cases. The held-out probe evidence in [results/level1e1/probe_evidence.json](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1e1/probe_evidence.json) shows no useful positive separation on the rejected primary and stress cases.

## Mechanistic Interpretation

The results support, but do not formally prove, the following explanation:

> Resonator estimates are basin-conditioned states rather than neutral accumulated evidence. Estimates produced inside a narrow L2 domain encode commitment to its local attractor landscape. Expanding the domain while preserving these estimates biases subsequent dynamics toward the previous basin and inhibits exploration of newly introduced candidates.

The mechanism is especially visible in `EASY_SINGLE`, where a cold global initialization is already near-optimal while transferred `L2` states substantially degrade recovery.

## Scope

This rejection applies to:

- dense MAP hypervectors
- the tested upstream TorchHD resonator update
- the tested dimensions, domain sizes, and factor counts
- direct estimate transfer without reset or interpolation
- full cold `L1` restart and one-step or two-step `L1` probes

It does not establish a universal impossibility result for:

- other resonator update rules
- attention-based resonators
- stochastic factorizers
- GSBC/BCF
- linear-code HDC
- controlled state-reset mechanisms supported by a separate theory

## Rejected Follow-Up Work

Do not retry without new theoretical or prior-art justification:

- arbitrary estimate interpolation
- manually tuned partial resets
- context annealing
- factor-wise reset heuristics
- additional `L1` iteration counts
- random perturbations added solely to improve this benchmark

## Reopen Conditions

This decision may be revisited only if:

1. a different published factorizer explicitly supports continuation under domain expansion
2. a formal model predicts how state should be transformed between domains
3. an independent substrate benchmark shows continuation as a native operation
4. a new test targets a substantially different operating envelope

## Surviving Claim

> Context-biased local factorization with calibrated acceptance and cold global fallback improves selective coverage and mean compute in the tested single-composite collapse regime without increasing silent false acceptance.
