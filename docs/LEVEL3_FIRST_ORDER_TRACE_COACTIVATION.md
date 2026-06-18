# Level 3 First-Order Trace Co-Activation

## Verdict

`PROTOTYPE / DEVELOPMENT_ONLY`

Engineering verdict:

```text
ADOPT_EXACT_CAPSULE
```

Scientific verdict:

```text
FIRST_ORDER_COACTIVATION_PARTIAL
```

Implementation verdict:

```text
NO_RUNTIME
```

## Canonical seam

This stage tests one narrow causal seam:

```text
semantic operation
-> create first-order trace atom
-> create semantic↔trace association
-> later noisy semantic activation
-> trace spike
-> typed trace validation
-> configured replay path
-> verified reconstruction
```

It is not a production runtime, not recursive trace history, and not Stage B decoder orchestration.

## Prior art / reuse

- `ADOPT`: existing MAP / TorchHD semantic operations.
- `ADOPT`: Stage A.2a exact packed semantic lookup as the equal-information sidecar baseline.
- `WRAP`: existing random-hyperplane primitive for the carried fingerprint capsule only.
- `COMPOSE`: exact typed sidecar trace payload + compact carried capsule + semantic-to-trace bridge.
- `BLOCK`: new ANN, new LSH, new provenance store, new VSA algebra, new factorizer, new ECC.

## Scope

Included:

- first-order trace atoms only;
- exact typed parent handles;
- isolated semantic block plus optional capsule block;
- transactional commit discipline;
- semantic-to-trace bridge;
- exact random capsule;
- carried locality-sensitive fingerprint;
- combined co-activation;
- trace-free replay portfolio baseline;
- ambiguity-safe validation;
- fixed-semantic and fixed-total dimension budgets.

Excluded:

- recursive ancestry traversal;
- full decode-carrying hypervector architecture;
- new noisy decoder;
- BCF execution;
- Stage B orchestration;
- held-out confirmation;
- production runtime.

## Typed contracts

- `SemanticRecord`
- `FirstOrderTraceAtom`
- `TraceRoutingCapsule`
- `TraceSpike`
- `TraceMemoryEntry`

Authority boundary:

- semantic zone: approximate retrieval evidence only;
- semantic bridge / fingerprint / capsule: routing authority only;
- first-order trace atom: local decode contract after validation;
- exact parent handles: targeted replay authority;
- verifier: final accept / expand / abstain authority.

## Baselines

- `B0`: known-handle sidecar oracle
- `B1`: noisy semantic cue -> adopted packed exact semantic lookup -> exact sidecar trace
- `B2`: semantic-to-trace bridge, no carried capsule
- `B3`: carried exact/random routing capsule
- `B4`: carried locality-sensitive trace fingerprint
- `B5`: combined bridge + fingerprint
- `B6`: random bridge control
- `B7`: trace-free replay portfolio

## Information contracts

- `B0` receives `semantic cue + exact runtime handle + sidecar access`.
- `B1` receives `semantic cue + sidecar access`.
- `B2` receives `semantic cue` only.
- `B3/B4/B5` receive `semantic cue + carried capsule`.
- `B7` receives `semantic cue` only and brute-forces the lawful replay bank.

No claim is made across mismatched information contracts.

## Dataset classes

- `U1`: unique semantic, unique trace
- `U2`: nearby semantics, different traces
- `U3`: identical semantics, different traces
- `U4`: unknown or uncommitted result

`U3` is mandatory ambiguity ground:

```text
semantic-only arms must not silently choose exact provenance
```

## Budget contracts

- `FIXED_SEMANTIC_CAPACITY`
  - semantic `D=1024`
  - trace capsule adds extra storage
- `FIXED_TOTAL_CAPACITY`
  - total `D=1024`
  - semantic zone shrinks by reserved trace dimensions

Frozen trace-dimension grid:

```text
0, 64, 128
```

## Frozen development protocol

Protocol hash:

```text
d541a877ee8344ebfa31ab784ef7da364ac79712cf593c169e7fbeb9e469f03b
```

Primary settings:

```text
committed records: 2048
queries per cell: 128
candidate budget: 32
rerank top-k: 32
```

Corruption cells:

- `C0_CLEAN`
- `C1_SEMANTIC_ONLY`
- `C2_CAPSULE_ONLY`
- `C3_SEMANTIC_AND_CAPSULE`
- `C4_CAPSULE_MISSING`
- `C5_SEMANTIC_PARTIAL_MASK`
- `C6_WRONG_VALID_CAPSULE`

## Key results

Primary interpretation cell:

```text
FIXED_SEMANTIC_CAPACITY
trace_dims = 64
```

At `C1_SEMANTIC_ONLY`:

- `B1 semantic sidecar`: exact-trace selection `0.4453`, accepted coverage `0.4453`, conditional risk `0`
- `B2 semantic bridge`: exact-trace selection `0.4453`, accepted coverage `0.4453`, conditional risk `0`
- `B6 random bridge`: exact-trace selection `0.0156`, accepted coverage `0.0156`, conditional risk `0`
- `B7 trace-free replay portfolio`: exact-trace selection `0.6484`, accepted coverage `0.6484`, conditional risk `0`

At `C3_SEMANTIC_AND_CAPSULE`:

- `B3 exact/random capsule`: exact-trace selection `0.7500`, accepted coverage `0.7500`, conditional risk `0`
- `B4 carried fingerprint`: exact-trace selection `0.6563`, accepted coverage `0.6563`, conditional risk `0`
- `B5 combined`: exact-trace selection `0.6563`, accepted coverage `0.6563`, conditional risk `0`

Ambiguity:

- semantic-only ambiguity silent wrong: `0`
- capsule ambiguity silent wrong: `0`

Decoder reduction:

- `B2 semantic bridge` mean decoder invocations: `0.4453`
- `B7 trace-free portfolio` mean decoder invocations: `16304`

But `B2` does not preserve verified reconstruction rate strongly enough against `B7`, so decoder-reduction gate remains incomplete.

## Gate evaluation

- causal co-activation vs random: `PASS`
- decoder reduction vs trace-free portfolio: `FAIL`
- ambiguity safety: `PASS`
- sidecar survival gate: `PASS`

## Main interpretation

What survived:

- semantic-to-trace association is real and beats random routing under equal candidate budget;
- exact carried capsules are currently the strongest narrow seam;
- carried fingerprint and combined co-activation remain useful but not dominant;
- ambiguity handling stayed lawful: no silent exact-provenance commitment in the measured envelope.

What did not survive:

- semantic bridge alone did not beat the equal-information semantic sidecar baseline;
- first-order co-activation did not yet deliver a stronger verified reconstruction frontier than trace-free replay plus exact verification;
- exact parent handles account for much of the benefit, so this stage does not demonstrate general blind factorization relief.

## Isolation and capacity

- lawful designs keep semantic similarity distortion at `0` by construction because semantic similarity is computed only on the semantic block;
- fixed-total budgets show measurable semantic-capacity tax as reserved trace dimensions grow;
- wrong valid capsules and capsule-missing cells remain bounded by verifier-gated abstention rather than silent wrong provenance.

## Known limitations

- the replay bank is finite and synthetic;
- first-order exact parent handles make replay highly targeted;
- no recursive trace traversal is attempted;
- no mature SDM baseline is included yet;
- no held-out or production conclusion is authorized.

## Next lawful stage

```text
CARRIED_FINGERPRINT_REFINEMENT
```

This means:

- keep the runtime blocked;
- do not move to recursive trace history;
- refine the carried fingerprint seam or compare it against another mature associative baseline before any wider decoder orchestration claim.
