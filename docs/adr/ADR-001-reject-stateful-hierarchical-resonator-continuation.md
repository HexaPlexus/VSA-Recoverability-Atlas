# ADR-001 — Reject Stateful Hierarchical Resonator Continuation

## Status

**Accepted — experimentally falsified for the tested MAP-resonator operating envelope.**

## Context

CGRN-HSR initially proposed hierarchical search relaxation:

```text
L2 narrow context
→ L1 parent context
→ global domain
```

Two implementations were tested:

1. cold full resonator restart at every level;
2. transfer of final L2 estimates into expanded L1/global domains, including one-step and two-step L1 probes.

## Decision

The active runtime must not use iterative L2 → L1 → global resonator continuation.

The surviving execution path is:

```text
context-biased L2 attempt
→ calibrated early acceptance
→ discard local estimates when rejected
→ cold global fallback
→ accept or abstain
```

Hierarchical context remains valid for candidate organization and prior construction, but not for carrying resonator state between expanded search domains.

## Evidence

### Cold cascade

The complete L2 → L1 → global cascade achieved low selective risk but had higher mean compute than an always-global baseline. The L1 stage accepted no primary or stress cases and acted only as an expensive consistency probe.

### Warm continuation

Compared with L2 → cold global fallback, warm continuation:

- reduced primary recovery;
- produced zero or near-zero warm-helped cases;
- produced multiple warm-hurt cases;
- strongly degraded EASY_SINGLE;
- remained inferior even without the strict compute cap;
- was not rescued by one-step or two-step L1 probes.

### Cheap probes

One-step and two-step L1 probes did not preserve the useful separation previously observed after a full L1 run among the actually rejected L2 cases.

## Mechanistic interpretation

The results support, but do not formally prove, the following explanation:

> Resonator estimates are basin-conditioned states rather than neutral accumulated evidence. Estimates produced inside a narrow L2 domain encode commitment to its local attractor landscape. Expanding the domain while preserving these estimates biases subsequent dynamics toward the previous basin and inhibits exploration of newly introduced candidates.

The mechanism is especially visible in EASY_SINGLE, where a cold global initialization is already near-optimal while transferred L2 states substantially degrade recovery.

## Scope

This rejection applies to:

- dense MAP hypervectors;
- the tested upstream TorchHD resonator update;
- the tested dimensions, domain sizes and factor counts;
- direct estimate transfer without reset or interpolation;
- full cold L1 restart and one-/two-step L1 probes.

It does not establish a universal impossibility result for:

- other resonator update rules;
- attention-based resonators;
- stochastic factorizers;
- GSBC/BCF;
- linear-code HDC;
- controlled state-reset mechanisms supported by a separate theory.

## Rejected follow-up work

Do not retry without new theoretical or prior-art justification:

- arbitrary estimate interpolation;
- manually tuned partial resets;
- context annealing;
- factor-wise reset heuristics;
- additional L1 iteration counts;
- random perturbations added solely to improve this benchmark.

## Reopen conditions

This decision may be revisited only if:

1. a different published factorizer explicitly supports continuation under domain expansion;
2. a formal model predicts how state should be transformed between domains;
3. an independent substrate benchmark shows continuation as a native operation;
4. a new test targets a substantially different operating envelope.

## Surviving claim

> Context-biased local factorization with calibrated acceptance and cold global fallback improves selective coverage and mean compute in the tested single-composite collapse regime without increasing silent false acceptance.
