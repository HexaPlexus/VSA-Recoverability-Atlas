# Level 3 Exact Capsule Contract Closure

Verdict: `ADOPT / COMPOSE / DEVELOPMENT_ONLY / NO_RUNTIME`

## Purpose
This stage closes a narrower question than the earlier first-order co-activation prototype:

> Does an isolated carried exact trace capsule provide any practical or scientific advantage over an ordinary typed exact field or a conventional sidecar under equal information, equal bit budget and explicit corruption contracts?

It does not authorize carried-fingerprint refinement, recursive provenance, production runtime, or a general self-decoding memory claim.

## Prior Art / Reuse
- `ADOPT`: exact typed handles, sidecar trace payloads, content-addressed IDs, transactional commit semantics.
- `COMPOSE`: prior first-order trace harness for replay-bank generation and typed trace validation.
- `ADOPT`: Stage A.2a packed exact semantic scan as the semantic lookup baseline.
- `ADOPT`: existing shortened BCH wrapper from Level 3.5b for the ECC arm.
- `BLOCK`: new ANN/LSH framework, new ECC implementation, new provenance store, new VSA algebra.

## Scope
Included:
- exact trace token closure;
- ordinary field vs isolated capsule comparison;
- random opaque and content-addressed token variants;
- ECC-protected exact capsule;
- semantic fallback and fingerprint fallback diagnostics;
- lifecycle failure classes;
- replay versus retrieval failure separation.

Excluded:
- held-out execution;
- Stage B decoder orchestration;
- recursive trace traversal;
- production formats;
- new routing algorithms;
- frozen Level 3.5 artifacts.

## Information Contracts
- `P0`: record-aware activation with exact `semantic_record_id`.
- `P1`: detached semantic cue only.
- `P2`: detached record with carried exact capsule.
- `P3`: detached record with erased capsule.
- `P4`: detached record with corrupted capsule.
- `P5`: detached record with wrong but structurally valid capsule.

No primary verdict is allowed to aggregate mismatched information contracts.

## Token Schemas
- Raw exact capsule:
  - `capsule_version = 2 bits`
  - `trace_namespace = 2 bits`
  - `trace_token = 10 bits`
  - `integrity_tag = 7 bits`
  - total `21 bits`
- Compared token families:
  - sequential integer exact token;
  - random opaque token;
  - content-addressed digest prefix;
  - BCH-protected exact token using the reused `21 -> 45` shortened BCH configuration.

The key anti-NIH control is:

> the same exact bits stored as an ordinary typed field versus stored in an isolated capsule zone.

## Arms
- `E0`: known-record sidecar oracle.
- `E1`: semantic lookup plus sidecar.
- `E2`: ordinary carried typed trace field.
- `E3`: isolated raw exact capsule.
- `E4`: random opaque token capsule.
- `E5`: content-addressed capsule.
- `E6`: ECC-protected exact capsule.
- `E7`: exact capsule plus semantic fallback.
- `E8`: fingerprint fallback diagnostic only.

## Dataset and Corruption
Dataset classes:
- `U1`: unique semantic, unique trace.
- `U2`: nearby semantics, different traces.
- `U3`: identical semantics, different traces.
- `U4`: unknown or uncommitted trace.
- `U5`: valid semantic record with stale trace token.
- `U6`: duplicate reified semantic payload under different creation event.
- `U7`: deleted or GC trace target.

Corruption cells:
- `C0`: semantic clean, capsule clean.
- `C1`: semantic noisy, capsule clean.
- `C2`: semantic clean, capsule noisy.
- `C3`: semantic noisy, capsule noisy.
- `C4`: capsule erased.
- `C5`: capsule truncated.
- `C6`: wrong but valid capsule.
- `C7`: stale capsule.
- `C8`: malformed version or namespace.
- `C9`: corrupted integrity tag.
- `C10`: valid capsule referencing uncommitted trace.
- `C11`: valid capsule referencing missing trace.

The semantic substrate remained fixed:
- MAP
- `D = 1024`
- external semantic corruption: Bernoulli sign flips with `p = 0.05`

## Main Results
Primary development cell:
- `N = 960`
- `M0` additive metadata budget and `M1` fixed-total budget
- `64` queries per corruption cell

### Equal-bits placement test
Under equal information and equal raw bits, `E2` and `E3` were effectively identical.

Representative `M0`, `C1` results:
- `E2 ordinary field`: exact-trace coverage `0.65625`, conditional risk `0`, median candidates `1`
- `E3 isolated capsule`: exact-trace coverage `0.65625`, conditional risk `0`, median candidates `1`

Representative `M1`, `C1` results:
- `E2 ordinary field`: exact-trace coverage `0.28125`, conditional risk `0`
- `E3 isolated capsule`: exact-trace coverage `0.28125`, conditional risk `0`

This stage therefore did not support a placement-specific scientific advantage for the isolated capsule zone.

### Sidecar and detached activation
Record-aware sidecar oracle remained strongest when the exact record handle was available.

Representative `M0`, `C1` results:
- `E0 known-record sidecar oracle`: coverage `0.65625`, risk `0`
- `E1 semantic lookup + sidecar`: coverage `0.296875`, risk `0`
- `E3 isolated capsule`: coverage `0.65625`, risk `0`

Interpretation:
- when runtime identity is already available, the capsule is redundant;
- when runtime identity is absent, carried exact trace information helps substantially relative to semantic lookup alone.

### ECC
ECC materially improved capsule-corruption coverage without introducing silent wrong acceptance.

Representative `M0`, `C2` results:
- `E3 raw exact capsule`: coverage `0.15625`, risk `0`
- `E6 ECC exact capsule`: coverage `0.671875`, risk `0`

The benefit persisted, though weakened, under the fixed-total budget.

### Fingerprint fallback
The fingerprint fallback diagnostic did not justify survival in this stage.

Representative `M0`, `C4`:
- `E7 exact capsule + semantic fallback`: coverage `0.3125`, conditional risk `0.0476`
- `E8 fingerprint fallback diagnostic`: coverage `0.0`, risk `0`

### Safety
Raw exact field/capsule arms stayed safe under the tested malformed, stale and wrong-token cells.

The failing safety signal came from the semantic fallback arm:
- `E7`, `C6 wrong valid capsule`, `M0`: conditional risk `1.0`
- `E7`, `C6 wrong valid capsule`, `M1`: conditional risk `1.0`

This means the current fallback path is not lawful enough to promote.

## Memory and Budget
Key deployable memory comparison in `M0`:
- `E2 ordinary field`: `11931.31` total bytes, `1052.31` bytes/record
- `E3 isolated capsule`: `11931.31` total bytes, `1052.31` bytes/record
- `E6 ECC capsule`: `14904.31` total bytes, `1058.31` bytes/record
- `E7 exact capsule + semantic fallback`: `138651.31` total bytes, `1180.31` bytes/record

Under `M1`, all carried exact arms paid the same explicit semantic-capacity tax of `21` dimensions. This did not create any placement-specific benefit for the isolated capsule.

## Latency
Representative `M0`, `C1`:
- `E0 known-record sidecar oracle`: p50 total latency about `0.00053 s`
- `E1 semantic lookup + sidecar`: p50 total latency about `0.01146 s`
- `E3 isolated capsule`: sub-millisecond exact-token path with single-candidate retrieval
- `E8 fingerprint fallback`: roughly semantic-lookup-scale latency once fallback activated

The carried exact-token path helped in detached activation, but isolation itself did not create an additional speed win over the ordinary field.

## Gate Status
- `exact_resolution_gate`: `PASS`
  - exact trace localization for resolvable clean committed records closed successfully.
- `plain_handle_gate`: `PASS`
  - ordinary typed field matched or exceeded isolated capsule under equal information.
- `detached_activation_gate`: `PASS`
  - exact carried trace info helped when runtime identity was absent.
- `ecc_gate`: `PASS`
  - ECC improved noisy-capsule coverage without silent wrong.
- `replay_separation_gate`: `PASS`
  - retrieval and replay failures remained typed separately.
- `equal_information_gate`: `PASS`
- `sidecar_gate`: `FAIL`
  - the isolated capsule did not show a record-aware advantage over direct sidecar access.
- `safety_gate`: `FAIL`
  - semantic fallback remained unsafe in wrong-valid-capsule cases.
- `fingerprint_gate`: `FAIL`
  - fingerprint fallback did not improve erased-capsule coverage.

## Conclusions
Engineering verdict:
- `ADOPT_PLAIN_TYPED_HANDLE`

Scientific verdict:
- `ISOLATED_CAPSULE_ADVANTAGE_NOT_SUPPORTED`

Implementation verdict:
- `NO_RUNTIME`

What survived:
- carried exact trace information is useful for detached activation.

What did not survive:
- a distinct advantage for storing those same exact bits specifically in an isolated capsule zone.

## Claim Boundary
Allowed:
- carried exact trace information can help detached activation;
- ordinary field and isolated capsule can be compared under equal bit and information contracts;
- ECC can materially improve exact-token survival under capsule corruption.

Forbidden:
- new LSH algorithm;
- production decode-carrying runtime;
- recursive trace history claims;
- exact provenance from semantic similarity alone;
- scientific claim that isolated capsule placement itself is beneficial.

## Next Lawful Stage
`REPLAY_RELIABILITY_CLOSURE`

Reason:
- exact token resolution closed cleanly enough;
- placement advantage did not survive;
- the remaining live problem is replay reliability and safe fallback, not capsule placement.
