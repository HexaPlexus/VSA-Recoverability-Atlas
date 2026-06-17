---
status: DEFERRED_BACKLOG
maturity: HYPOTHESIS
implementation_authorized: false
experimental_authorized: false
production_authorized: false
novelty_status: NOT_ESTABLISHED
anti_nih_verdict: COMPOSE
---

# Lazy Composite Reification with Exact Handles, Shared Ambient Space, and Semantic Fingerprints

Working abbreviation: `LCR`

## Child Hypotheses

LCR now explicitly contains a deferred child hypothesis:

- [DECODE_CARRYING_HYPERVECTORS_HYPOTHESIS.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/research/DECODE_CARRYING_HYPERVECTORS_HYPOTHESIS.md)

Parent-child relation:

```text
Hierarchical shallow-composition VSA
    -> Lazy Composite Reification
        -> Decode-Carrying Hypervectors
```

LCR remains the parent hypothesis. The child hypothesis does not authorize implementation, experiments, or protocol changes.

## Verdict

`COMPOSE`

This document records a backlog hypothesis only. It does not authorize runtime implementation, benchmark execution, new dependencies, or a new subsystem.

## Status

- Status: `DEFERRED_BACKLOG`
- Maturity: `HYPOTHESIS`
- Implementation authorized: `false`
- Experimental authorized: `false`
- Production authorized: `false`
- Novelty status: `NOT_ESTABLISHED`
- Anti-NIH verdict: `COMPOSE`

> Отдельные компоненты гипотезы известны как chunking, memoization, hash-consing, content-addressed storage, VSA item memory, ANN/LSH indexing и typed object graphs. Возможная ценность может находиться только в измеренной композиции этих механизмов, а не в новом фундаментальном алгоритме.

## Purpose

LCR asks a narrow research question:

> Can shallow VSA workspace compositions be computed locally and, after independent verification, reified into flat chunk-atoms in the same ambient vector space, while exact identity stays in an external canonical structure and approximate semantic entry stays in a separate fingerprint/index layer?

The intended motivations are:

- limit propagation of compositional depth;
- avoid carrying a noisy nested hypervector forward as if it were authoritative structure;
- reuse recurring composites;
- reduce repeated recomputation;
- localize decoding errors;
- keep one numerical VSA backend;
- avoid conflating identity with similarity.

## Updated Framing

LCR does not assume that two physically separate hyperspheres are necessary.

Let all native vectors live in one fixed ambient space:

```text
H = native VSA vector space of fixed dimension D
```

Logical namespaces may still be distinct inside that space:

```text
ATOM
CHUNK
ROLE
OPTIONAL_LOCAL_WORKSPACE
```

Semantic fingerprints may:

- use the same numerical dimension;
- use a separate ANN representation;
- live in a separate logical index.

Equal dimension does not authorize untyped cleanup.

## Exact Reification Pipeline

Local composition:

```text
x = f(a1, a2, ..., an)
```

Canonical structure:

```text
C = Canonicalize(
    operation_type,
    typed_arguments,
    argument_order,
    parameters,
    schema_version,
    dependency_versions
)
```

Exact identity:

```text
h = ContentAddress(C)
```

Flat chunk-atom in the same ambient space:

```text
c = DeterministicHypervector(
    namespace = CHUNK,
    seed = h,
    dimension = D
)
```

Semantic fingerprint:

```text
s = SemanticFingerprint(x, C)
```

Subsequent VSA operations use `c`, not the nested `x`.  
`C` remains the authoritative source of truth.

## Separation of Roles

LCR requires four logically separate entities:

```text
canonical_structure:
    exact semantic structure

exact_handle:
    stable identity

chunk_atom:
    flat native VSA atom for downstream operations

semantic_fingerprint:
    approximate candidate retrieval
```

The following are forbidden:

- using chunk-vector similarity as exact identity;
- using an LSH bucket as identity;
- using an approximate result as authoritative traversal;
- using a PRNG-generated chunk vector as a replacement for canonical structure.

## Parent-State Update

Before the child-hypothesis extension, LCR centered on:

```text
canonical structure
+ exact handle
+ flat chunk atom
+ semantic fingerprint
```

After the child-hypothesis extension, the backlog design space additionally includes:

```text
canonical structure
+ exact handle
+ flat chunk atom
+ semantic fingerprint
+ local decode capsule
+ operation-trace fingerprint
+ recursive parent derivation
```

This does not change the authoritative role of the exact canonical graph. It only widens the deferred backlog around how decode-relevant metadata might be composed with reified chunk atoms.

## Conceptual Record

This is a logical schema, not a runtime class:

```yaml
CompositeRecord:
  exact_handle:
  canonical_structure:
  namespace: CHUNK
  chunk_atom_seed:
  semantic_fingerprints:
    structural:
    local_vsa:
  operation_type:
  typed_arguments:
  provenance:
  dependency_versions:
  maturity:
  verifier_evidence:
  creation_policy:
  invalidation_policy:
```

## Architecture Variants

### Variant A - Separate Ambient Spaces

```text
local VSA workspace H_local
chunk atoms H_chunk
```

Possible advantages:

- geometric isolation;
- separate metrics or dimensions;
- isolated cleanup codebooks.

Possible costs:

- projection and conversion overhead;
- two numerical backends or stores;
- transfer and synchronization overhead.

Verdict: `COMPARE`

### Variant B - Shared Ambient Space with Typed Namespaces

```text
one ambient H

typed logical stores:
  ATOM
  CHUNK
  ROLE
```

Lookup must always filter by expected type.

Possible advantages:

- one VSA backend;
- no dimension conversion;
- chunk atoms can bind immediately;
- deterministic rematerialization;
- potentially less storage and transfer overhead.

Possible costs:

- larger codebooks and indexes;
- namespace-filtering cost;
- higher nearest-decoy pressure;
- shared resource contention.

Preliminary verdict: `PREFERRED_PROTOTYPE_CANDIDATE`

This is not implementation approval.

### Variant C - Shared Untyped Codebook

Atoms, chunks, and fingerprints all participate in one unrestricted cleanup search.

Verdict: `BLOCK`

Reasons:

- cross-type cleanup;
- semantic substitution;
- index pollution;
- silent errors;
- poor observability.

## Cleanup and Index Contract

Exact atomic cleanup and chunk retrieval must not use one unrestricted candidate set.

Example:

```text
expected_type = CHUNK

candidate_set =
    item_memory.filter(namespace == CHUNK)
```

Approximate semantic retrieval must follow:

```text
query
-> semantic fingerprint / ANN / LSH
-> top-k exact handles
-> verifier
-> exact handle
-> deterministic chunk atom
```

This is explicitly forbidden:

```text
fingerprint
-> directly canonical chunk
```

without exact verification.

## Deterministic Chunk Materialization

Audit, but do not implement, the possibility:

```text
chunk_atom =
    PRNG_HV(exact_handle, namespace_tag, schema_version)
```

Potential benefits:

- no need to persist the full chunk hypervector;
- reproducible identity-to-vector mapping;
- cheap creation of new chunks;
- same native representation family as atoms.

Mandatory questions:

- does namespace separation produce independent vectors;
- is the mapping stable across versions;
- must generator metadata be stored;
- how much does rematerialization latency matter for reuse;
- does determinism create correlated vectors;
- is approximate orthogonality testing required.

No speed claim is allowed without measurement.

## Semantic Fingerprint Alternatives

### Local-VSA Fingerprint

```text
s_vsa = Fingerprint(x)
```

Potential strengths:

- native cue geometry;
- possible retrieval from approximate local workspace outcomes.

Risks:

- inherited crosstalk;
- multiplicative binding similarity collapse;
- dependence on VSA substrate or version;
- instability under local noise.

### Structural Fingerprint

```text
s_struct = Embed(C)
```

Potential strengths:

- stable under local VSA noise;
- typed structural features;
- more backend-invariant than local composition geometry.

Risks:

- may collapse into graph embedding plus ANN;
- may make the VSA workspace unnecessary.

### Composite Sketch

Consider as a baseline only:

- TensorSketch;
- compact bilinear sketch;
- kernel approximation.

Do not claim exactness or invertibility.

### Dual Fingerprint

Candidate architecture:

```yaml
semantic_fingerprints:
  structural:
  local_vsa:
```

## Lifecycle

```text
ObservedComposite
-> CandidateComposite
-> ProvisionalChunk
-> VerifiedChunk
-> ConfirmedChunk
-> ConsolidatedChunk
```

Additional states:

```text
RejectedChunk
InvalidatedChunk
SupersededChunk
```

Provisional chunks:

- may participate in candidate retrieval;
- may not become authoritative dependencies;
- may not replace canonical structure;
- may not be used in committed exact traversal.

## Lazy Utility-Gated Materialization

LCR does not assume that every composite should be reified.

Possible promotion signals:

- observed reuse frequency;
- predicted reuse;
- recomputation cost;
- structural stability;
- verifier confidence;
- depth-containment value;
- memory cost;
- expected lookup savings;
- collision or error risk.

Candidate future policies:

- frequency threshold;
- expected saved compute;
- compression or MDL gain;
- repeated independent reconstruction;
- operator-directed promotion;
- bounded cache with eviction.

Policy choice remains a future experiment.

## Potential Speed Model

This section is documentary only.

Without reification:

```text
repeated_cost ~= reuse_count * composition_cost
```

With reification:

```text
total_cost ~=
    initial_composition
  + canonicalization
  + verification
  + registration
  + reuse_count * chunk_lookup_or_materialization
```

Potential gain exists only if:

```text
saved_recomputation
>
canonicalization
+ verification
+ indexing
+ invalidation
+ lookup overhead
```

One shared ambient space may reduce:

- projection;
- dimension conversion;
- cross-store vector copying.

It may also increase:

- codebook size;
- cleanup latency;
- ANN maintenance;
- false-nearest pressure.

Therefore:

> Shared space is not assumed faster by definition.

## Anti-NIH Prior-Art Matrix

| Prior art | What it already covers | What it does not cover here | Verdict |
| --- | --- | --- | --- |
| Standard VSA item memory / cleanup | queries and prototypes in shared geometry; approximate nearest-neighbour cleanup | exact canonical identity; chunk lifecycle; verifier-gated reification; open-world invalidation | `ADOPT` |
| Chunking and memoization | reusable composites; avoided recomputation | typed VSA chunk atoms; exact-handle split; verifier-gated promotion | `ADOPT` |
| Hash-consing / content-addressed DAG | exact structural deduplication; canonical identity; reusable graph nodes | ambient VSA reuse path; chunk fingerprints; approximate associative entry | `ADOPT` |
| ANN / LSH / vector database | approximate candidate retrieval; index scaling | exact identity; canonical traversal authority; reification lifecycle | `ADOPT` |
| Semantic cache | reuse under similar queries; locality-driven savings | exact handles; typed chunk atoms; dependency invalidation | `COMPARE` |
| TensorSketch / compact bilinear representations | compact approximate composite features; avoids full tensor materialization | exact identity; invertibility; lifecycle | `COMPARE` |
| Structured or scalable VSA codebooks | scalable cleanup; compact codebook materialization | canonical content addressing; chunk lifecycle; verifier boundary | `COMPARE` |
| Orthogonal Subspace Carving | alternative deep-recursion hypothesis via subspace isolation | lazy reification; exact handles; shared-space typed chunking | `COMPARE / DEFER` |

LCR is only defensible if measured composition of adopted mechanisms creates a new nondominated operating point.

## Relationship to Existing Backlog

LCR should be treated as a:

```text
CHILD_HYPOTHESIS
CONCRETE_REIFICATION_MECHANISM
```

relative to the parent backlog idea:

```text
Hierarchical shallow-composition VSA with typed cross-domain indirection
```

Important refinement:

> Cross-domain indirection does not require separate physical ambient spaces. A domain may be a logical typed namespace inside one shared geometry.

LCR extends the parent idea with:

- lazy promotion of composites;
- exact canonical handles;
- deterministic chunk atoms;
- separate fingerprint and index layers;
- lifecycle states;
- verifier-gated commit.

## What LCR May Address

- propagation of compositional depth;
- repeated recomputation;
- reusable macro-concepts;
- bounded local VSA depth;
- error containment after a reification boundary;
- associative entry to known composites;
- rollback and versioning locality;
- unified native VSA operations after reification.

## What LCR Does Not Address

- information already destroyed by lossy bundling;
- arbitrary wide U2 recovery;
- external noise without a decoder;
- blind factorization inside the local workspace;
- exact identity from LSH;
- similarity collapse in the source composition;
- chunk explosion;
- general open-world learning;
- guaranteed speedup;
- canonical truth inside VSA geometry.

## Safety Invariants

```text
I1. Canonical structure is authoritative.
I2. Exact handle is independent from semantic similarity.
I3. Chunk atom is not canonical identity.
I4. Fingerprint/LSH is candidate index only.
I5. Approximate retrieval must end in exact handle verification.
I6. Typed namespaces are mandatory in a shared ambient space.
I7. Shared untyped cleanup is forbidden.
I8. Provisional chunks cannot become committed dependencies.
I9. Reification does not restore information already lost.
I10. Dependency changes trigger invalidation or versioning.
I11. PRNG/vector generator and schema versions are recorded.
I12. Exact traversal uses handles, never nearest-neighbour choice.
```

## Failure Modes

- wrong canonicalization;
- content-hash collision;
- LSH collision;
- semantic false candidate;
- cross-type cleanup;
- shared-index pollution;
- chunk explosion;
- stale chunk;
- dangling handle;
- dependency drift;
- deterministic generator version drift;
- correlated generated chunk atoms;
- premature promotion;
- poisoned provisional chunk;
- local noisy composition committed as exact;
- fingerprint drift;
- verifier cost exceeding reuse savings;
- ANN maintenance cost;
- memory locality regression;
- no measurable reuse;
- self-reification cycles;
- a chunk referring recursively to itself;
- cyclic dependency graph without explicit handling.

## Required Future Baselines

- ordinary exact graph;
- hash-consed or content-addressed DAG;
- graph plus mature ANN or vector index;
- semantic cache;
- monolithic nested VSA;
- separate-space shallow VSA plus chunks;
- shared-space typed VSA plus chunks;
- shared untyped codebook as negative control only;
- shared-space typed chunks without fingerprint;
- shared-space typed chunks plus structural fingerprint;
- shared-space typed chunks plus local-VSA fingerprint;
- TensorSketch or compact composite sketch;
- structured scalable VSA codebook;
- TPR oracle;
- Orthogonal Subspace Carving.

## Required Future Benchmark Questions

### B1 - Shared versus Separate Space Overhead

Measure:

- vector conversion or projection;
- copying;
- materialization;
- cleanup and index latency;
- cache locality;
- codebook growth.

### B2 - Chunk Reuse

Measure:

- avoided recomputation;
- materialization frequency;
- chunk reuse distribution;
- memory growth;
- eviction and churn.

### B3 - Typed Cleanup Correctness

Measure:

- atom-to-chunk false substitution;
- chunk-to-atom false substitution;
- nearest-decoy rate;
- effect of namespace filtering;
- cleanup latency.

### B4 - Approximate Associative Entry

Measure:

- recall@k;
- precision@k;
- verifier rejection;
- false merge rate;
- latency.

### B5 - Deep Error Containment

Measure:

- path, leaf, and full recovery;
- propagation depth;
- rollback locality;
- silent wrong traversal.

### B6 - Graph Plus ANN Comparison

Determine whether local VSA workspace or chunk atoms add value beyond:

```text
canonical graph
+
ordinary structural or semantic embedding
+
mature ANN index
```

## Kill Gates

```text
K1. If graph + ANN is more accurate, faster, simpler and cheaper:
    BLOCK LCR-specific VSA architecture.

K2. If shared-space typed namespaces do not outperform separate spaces:
    do not prefer shared space.

K3. If one shared index worsens cleanup or ANN latency:
    physically partition stores while retaining a common vector format.

K4. If structural fingerprint dominates local-VSA fingerprint:
    remove local-VSA fingerprint.

K5. If symbolic execution dominates shallow VSA workspace:
    remove the VSA workspace.

K6. If chunks grow nearly one-to-one with operations without meaningful reuse:
    BLOCK.

K7. If verifier + canonicalization costs exceed saved compute:
    BLOCK promotion.

K8. If deterministic chunk generation creates harmful correlations:
    replace generation scheme or BLOCK.

K9. If typed filtering cannot prevent silent cross-type cleanup:
    BLOCK the shared-space variant.

K10. Continue only if a new nondominated point appears in:
     associative retrieval,
     repeated-computation savings,
     graceful degradation,
     local superposed computation,
     or deep-error containment.
```

## Relationship to Current Findings

LCR must be read against already frozen results:

- symbolic records dominate clean exact storage;
- BCH dominates binary exact-record corruption in development;
- raw NeCo has a noisy-decoding gap;
- MAP shows silent collapse under sign-flip corruption;
- deep nesting and crosstalk are distinct problems;
- exact graph remains the authoritative baseline.

These findings raise the bar for any future LCR experiment:

- clean exact storage is already well served by symbolic records;
- plain coding-theory controls dominate many exact-noise regimes;
- raw noisy local composition cannot be treated as authoritative structure;
- any value claim must come from bounded-depth reuse, associative entry, or error containment, not from rebranding exact records.

## Allowed Claims

- hypothesis documented;
- single-ambient variant defined;
- prior-art overlap identified;
- architecture variants and kill gates specified;
- benchmark contract proposed.

## Forbidden Claims

- a new VSA was invented;
- a new hashing method was invented;
- shared space is faster;
- crosstalk is eliminated;
- deep recursion is solved;
- LSH provides identity;
- production readiness;
- novelty established.

## Repository Integration

This file is intentionally the only repository change for the hypothesis stage:

```text
docs/research/LAZY_COMPOSITE_REIFICATION_HYPOTHESIS.md
```

No new registry framework, runtime code, vector database, PRNG chunk implementation, canonical AST implementation, codebook, benchmark harness, or migration system is authorized here.

## Recommended Next Step

The first admissible future step is still documentation or audit work, not implementation:

```text
Prior-art and necessity kill-test for LCR against graph + ANN, memoized DAG, and typed shared-space cleanup baselines.
```

For the child hypothesis specifically:

```text
Do not implement before Level 3.5 held-out confirmation is closed and a separate anti-NIH/prior-art audit is completed.
```

## References to Reuse

- [CGRN_HSR_CNM_RESEARCH_SPEC.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md)
- [LEVEL1_RESEARCH_CLOSURE.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/LEVEL1_RESEARCH_CLOSURE.md)
- [LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md)
- [LEVEL3_5A_NOISE_CONTRACTS.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/LEVEL3_5A_NOISE_CONTRACTS.md)
- [LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md](C:/Users/Thanatos/Desktop/CGRN-HSR/docs/LEVEL3_5B_DEV_NATIVE_NOISE_FRONTIERS.md)
