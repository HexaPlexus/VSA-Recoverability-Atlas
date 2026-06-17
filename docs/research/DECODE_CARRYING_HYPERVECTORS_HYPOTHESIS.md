---
status: DEFERRED_BACKLOG
maturity: STRONG_PROTOTYPE_HYPOTHESIS
implementation_authorized: false
experimental_authorized: false
production_authorized: false
novelty_status: NOT_ESTABLISHED
anti_nih_verdict: COMPOSE
parent_hypothesis: LAZY_COMPOSITE_REIFICATION
relationship: CHILD_HYPOTHESIS
---

# Decode-Carrying Hypervectors with In-Sphere Operation-Trace Indexing

Working abbreviation: `DCH`

## Verdict

`COMPOSE`

This is a documentation-only child hypothesis inside the `Lazy Composite Reification` family. It does not authorize a prototype, benchmark, dependency, runtime path, or protocol change.

## Status

- Status: `DEFERRED_BACKLOG`
- Maturity: `STRONG_PROTOTYPE_HYPOTHESIS`
- Implementation authorized: `false`
- Experimental authorized: `false`
- Production authorized: `false`
- Novelty status: `NOT_ESTABLISHED`
- Anti-NIH verdict: `COMPOSE`
- Parent hypothesis: `LAZY_COMPOSITE_REIFICATION`
- Relationship: `CHILD_HYPOTHESIS`

> Do not implement before Level 3.5 held-out confirmation is closed and a separate anti-NIH/prior-art audit is completed.

## Parent Relationship

```text
Hierarchical shallow-composition VSA
    ->
Lazy Composite Reification
    ->
Decode-Carrying Hypervectors
```

This child hypothesis does not replace the authoritative exact graph assumed by LCR. It asks whether decode-relevant metadata and structural routing hints may be carried in the same ambient hyperdimensional representation as a reified semantic payload.

## Central Hypothesis

Primary motivation is not explainability and not provenance for its own sake.

Main hypothesis:

> Decode-relevant VSA operations should leave, inside the same ambient hyperdimensional representation, an isolated typed decode capsule and an approximate operation-trace fingerprint. A later decoder can use this as a fast inverse route, candidate-space restriction, and reconstruction scaffold instead of blind global Hamming cleanup or full factorization search.

Key thesis:

```text
the result of a VSA operation
need not be only semantic payload;

it may additionally carry:
- local creation method
- operator type
- arity
- typed operand namespaces
- stable parent handles
- inverse decode contract
- verification metadata
- approximate trace-routing fingerprint
```

Technical framing:

```text
typed operation traces become procedural and decoding memory
```

This is not a claim that the system stores "thought" in any human sense.

## Decode Provenance Versus Explanatory Provenance

The hypothesis is primarily about decode provenance, not generic explanation.

### Explanatory provenance

Answers:

```text
why or under what circumstances did a concept appear?
```

### Decode provenance

Answers:

```text
which operations, operands, and inverse contracts lawfully recover the concept structure?
```

Explainability, audit trail, and replay are possible secondary benefits. They are not the primary architectural reason.

## Decode-Carrying Hypervector

Conceptual structure:

```text
DecodeCarryingHypervector =
    semantic payload
    + decode capsule
    + trace fingerprint
```

Logical ambient-space decomposition:

```text
H =
    H_semantic
    + H_decode
    + H_trace
```

Where:

```text
H_semantic
- ordinary semantic/compositional representation

H_decode
- exact or ECC-protected local decode metadata

H_trace
- approximate structural fingerprint / LSH routing key
```

Important constraints:

- this may still be one physical packed hypervector
- zones may be implemented by disjoint bit ranges, sparse blocks, typed masks, orthogonal projectors, or other zone-preserving mechanisms
- exact implementation is not chosen
- logical same-space does not imply globally mixing all dimensions

## Mandatory Zone Isolation

Strict invariant:

> Semantic operations must not arbitrarily destroy decode or trace zones.

Binding, bundling, permutation, and cleanup must be zone-preserving or explicitly typed.

Candidate mechanisms:

```text
fixed disjoint zones
masked binding
block-diagonal permutations
typed projectors
sparse block-code partitions
orthogonal subspaces
```

Similarity must be split:

```text
semantic_similarity
trace_similarity
decode_integrity
```

Forbidden default:

```text
one global Hamming distance across all zones as a universal similarity score
```

Failure condition:

> If trace metadata materially contaminates semantic similarity, or semantic operations damage decode capsule integrity, the architecture is blocked.

## Local Trace, Not Full History Duplication

Each vector should carry only the local decode-relevant step, not the entire derivation chain.

```yaml
LocalDecodeCapsule:
  operator_type:
  arity:
  operand_namespaces:
  parent_handles:
  operation_parameters:
  depth_before:
  depth_after:
  superposition_width_before:
  superposition_width_after:
  inverse_contract:
  verifier_status:
  integrity_code:
```

Full history is reconstructed recursively:

```text
C created by OP(A, B)

A and B carry their own local capsules

full history =
recursive traversal
```

This is a provenance DAG, not full trace duplication in every descendant vector.

## Exact and Approximate Layers Must Stay Separate

### Exact authoritative layer

```text
stable typed parent handles
operator identity
arity
namespace
inverse contract
integrity/checksum/ECC
```

### Approximate routing layer

```text
trace fingerprint
LSH bucket key
structural similarity
candidate derivation family
```

Invariant:

> LSH or fingerprint is never canonical identity, authoritative parent linkage, or proof of origin.

Collisions may only widen a candidate set. They may not alter canonical traversal.

## Fast Path and Fallback Path

### Fast exact path

```text
read decode capsule
→ validate integrity
→ retrieve exact parent handles
→ apply inverse contract or replay operation
→ independently verify reconstruction
```

In this mode a resonator or factorizer may be unnecessary.

### Approximate fallback

If an exact handle is missing, damaged, unknown, partial, or not directly retrievable:

```text
read trace fingerprint
→ retrieve LSH / sparse-block bucket
→ obtain candidate derivation families
→ restrict operator, arity, and namespaces
→ CGRN-HSR factorization proposes operands
→ verifier evaluates reconstruction
→ hierarchical search relaxation expands candidates if needed
```

This adds a second prior source:

```text
semantic context prior
+
derivational trace prior
```

These should stay distinct rather than being merged into one opaque score.

## Inverse Decode Contract

First-class schema:

```yaml
InverseDecodeContract:
  forward_operator:
  known_inputs_required:
  expected_output_type:
  recoverable_operands:
  operand_namespaces:
  inverse_operation:
  integrity_requirements:
  expected_failure_modes:
  verifier_contract:
```

Example:

```text
operator: BIND

forward:
output = bind(left, right)

inverse:
given output + exact left handle
recover right candidate

constraints:
right ∈ RELATION namespace

verification:
rebind recovered operands and compare against authoritative record
```

Thesis:

> When a decode-relevant composition is created, the system also records how that composition is later allowed to be decoded.

## Selective Operation Logging

Do not assume logging every low-level operation is preferred.

### Variant A - ALL_OPERATION_TRACE

Store all operations.

Status:

```text
COMPARE_ONLY
likely excessive write amplification
```

### Variant B - DECODE_RELEVANT_TRACE

Store operations that change:

```text
compositional depth
superposition width
ambiguity
information loss
namespace/domain
inverse recoverability
reification boundary
cross-domain traversal
```

Status:

```text
PREFERRED_PROTOTYPE_CANDIDATE
```

### Variant C - REIFICATION_ONLY_TRACE

Store only the local operation at commit or reification boundary.

Status:

```text
MINIMAL_BASELINE
```

Durable trace should be favored when results are:

```text
verified
committed
frequently reused
expensive to reconstruct
concept-forming
required for rollback
```

## Trace Fingerprint and Lazy-LSH

Trace fingerprint should reflect structural derivation pattern, not semantic payload alone.

Candidate inputs:

```text
operator type
arity
operand namespace pattern
depth delta
superposition delta
operation sequence fragment
reification boundary
inverse-contract type
verification class
```

Example:

```text
BUNDLE[OBSERVATION×N]
→ INVARIANT_EXTRACTION
→ BIND[CONTEXT]
→ REIFY
```

Recurring trace patterns may themselves be lazily reified as:

```text
ReusableDerivationSchema
ProceduralChunk
OperationTemplate
```

That is another child-hypothesis candidate, not an established result.

## Same Hypersphere Constraints

Do not confuse formal address space with practical reliable memory.

Separate:

```text
formal address space
practical associative capacity
```

Practical capacity depends on:

- dimension
- minimum separation
- codebook size
- noise
- reserved-zone tax
- bundling width
- decoder
- cleanup contract
- acceptable silent-error rate

Correct framing:

> A large number of possible hypervectors makes same-space storage plausible, but does not prove usable capacity or reliable retrieval.

## Same Space Is Not Automatically Fast

Honest constraint:

```text
global Hamming scan remains O(ND)
```

without a real index path.

Required physical mechanism:

```text
trace fingerprint
→ bucket address
→ candidate posting list
→ exact capsule verification
```

Candidate implementations:

```text
lightweight external posting table
sparse block-code bucket memory
content-addressed shard
hierarchical hash buckets
hardware associative lookup
```

Important admission:

> Routing key and decode capsule may live inside the hypervector, but bucket-to-record mapping may still require a minimal external index.

Zero external metadata is not assumed.

## Integration with LCR

Before this extension:

```text
canonical structure
+ exact handle
+ flat chunk atom
+ semantic fingerprint
```

After this extension:

```text
canonical structure
+ exact handle
+ flat chunk atom
+ semantic fingerprint
+ local decode capsule
+ operation-trace fingerprint
+ recursive parent derivation
```

This child hypothesis does not replace the authoritative exact graph.

It asks:

> Can placing decode-relevant metadata and a structural routing fingerprint into the same hyperdimensional representation reduce reconstruction, lookup, and factorization cost?

## Integration with CGRN-HSR

Design-only integration contract:

```text
query / noisy composite
-> semantic prior retrieves likely concepts
-> trace prior retrieves likely construction families
-> typed operator / arity / namespaces narrow factorization
-> resonator proposes candidates
-> exact verifier checks reconstruction
-> search relaxation widens semantic and/or trace context
-> uncertain result abstains and does not commit
```

Decode capsule does not replace an independent verifier.

Failed verification may not become authoritative parent structure.

## Anti-NIH Matrix

### ADOPT

```text
exact provenance DAG
event sourcing
content-addressed storage
typed stable handles
checksums/ECC for exact metadata
LSH/ANN as approximate index
VSA item memory
```

### COMPARE

```text
ordinary graph + indexed handles
graph + conventional ANN
separate metadata records
sparse block codes
structured VSA codebooks
Orthogonal Subspace Carving
pointer-based compositional memory
TensorSketch / structural sketches
content-addressable memories
```

### ADAPT / COMPOSE

```text
local in-vector decode capsule
exact recursive parent handles
trace-LSH structural routing
verifier-gated lazy reification
CGRN-HSR fallback factorization
```

### BLOCK

```text
LSH used as identity
untyped shared codebook
global scan presented as fast indexing
claim of unlimited capacity from 2^D
full duplicated history in every vector
trace metadata allowed to contaminate semantics
```

Potential novelty, if any, would exist only in measured composition, not in a new fundamental VSA, LSH, or provenance algorithm.

## Candidate Data Contracts

```yaml
DecodeCarryingHypervector:
  semantic_zone:
  decode_zone:
  trace_zone:
  concept_handle:
  integrity_status:
```

```yaml
DecodeCapsule:
  operator_type:
  arity:
  operand_namespaces:
  parent_handles:
  parameters:
  depth_delta:
  superposition_delta:
  inverse_contract:
  verifier_metadata:
```

```yaml
TraceFingerprint:
  fingerprint_version:
  operator_pattern:
  structural_features:
  bucket_keys:
  collision_policy:
```

```yaml
OperationTraceNode:
  node_handle:
  output_handle:
  parent_handles:
  local_operation:
  maturity:
  provenance_kind:
```

Provenance kind:

```text
ACTUAL_EXECUTED_OPERATION
RECONSTRUCTED_TRACE
ALTERNATIVE_DERIVATION
COMPRESSED_EXPLANATION
```

Only `ACTUAL_EXECUTED_OPERATION` may count as authoritative execution history.

## Required Future Baselines

- exact provenance DAG + direct handle lookup
- exact DAG + conventional database index
- exact DAG + conventional ANN
- reified atom without trace
- reified atom + separate metadata record
- reified atom + parent pointers only
- in-vector fixed decode zone
- in-vector decode zone + trace fingerprint
- sparse block-code trace buckets
- OSC / subspace design
- global Hamming cleanup
- CGRN-HSR without trace prior
- CGRN-HSR with trace prior

All comparisons must use comparable total memory budgets.

## Required Future Benchmark Questions

1. Are exact parent handles recovered from the decode capsule?
2. Are operator type and arity recovered correctly?
3. How much does trace prior reduce the candidate set?
4. How much factorization latency is removed?
5. Does reconstruction accuracy stay intact?
6. Do silent wrong traversals appear?
7. What is the reserved-dimension tax?
8. How does semantic capacity change under different zone allocations?
9. How robust is the trace zone to corruption?
10. What are the collision and occupancy dynamics of LSH buckets?
11. Is there benefit under partial cue or missing handle?
12. Does same-space design beat exact graph + ANN?
13. Does the advantage remain after posting-index and verification costs?
14. Do repeated derivation schemas produce reuse benefit?
15. Are resonator restarts or search expansions reduced?

## Required Metrics

- exact parent recovery
- operator recovery
- arity recovery
- namespace recovery
- full reconstruction accuracy
- partial reconstruction accuracy
- candidate-set reduction
- lookup latency
- factorization latency
- end-to-end latency
- silent wrong traversal rate
- detected failure rate
- semantic-capacity loss
- trace-zone corruption tolerance
- bucket collision rate
- bucket occupancy distribution
- posting-list length
- memory bytes
- write amplification
- verification cost
- replay cost
- benefit under missing handle
- benefit under partial cue

## Kill Gates

```text
K1. If exact graph/index is faster, cheaper, and equally robust:
    BLOCK in-sphere trace mechanism.

K2. If reserved zones materially reduce semantic capacity:
    BLOCK fixed-zone design.

K3. If semantic and trace zones contaminate each other:
    BLOCK.

K4. If LSH collision affects canonical traversal:
    BLOCK.

K5. If speedup disappears after posting-list, memory fetch, and verification cost:
    BLOCK.

K6. If exact handle is almost always available and trace-LSH is not used:
    remove approximate trace layer.

K7. If logging causes excessive write amplification:
    restrict to decode-relevant or reification-only logging, or BLOCK.

K8. If in-vector metadata is less robust than a separate metadata record without compensating benefit:
    prefer separate record.

K9. If trace prior does not reduce factorization candidate space or restarts:
    remove integration with CGRN-HSR.

K10. If ordinary graph + mature ANN dominates end-to-end:
     BLOCK the architecture.
```

## Claim Boundaries

Allowed:

```text
This design may provide a decoding scaffold.
It may reduce blind search.
It may enable partial-cue retrieval of construction paths.
It may allow reuse of recurring derivation patterns.
```

Forbidden:

```text
the hypersphere has unlimited capacity
all metadata can be stored for free
same-space storage is automatically faster
the design models human thought
the design eliminates VSA noise
the design guarantees exact factorization
the design is novel
```

## Research Status Summary

```text
Exact local decode metadata:
technically plausible

Trace fingerprint in same ambient representation:
plausible prototype candidate

Full operation logging:
likely excessive

Decode-relevant selective logging:
preferred candidate

Exact recursive parent traversal:
strong component

Trace-conditioned CGRN-HSR fallback:
strong prototype hypothesis

Novelty:
not established

Implementation:
not authorized

Next action:
defer until Level 3.5 held-out closure
```

## Allowed Next Step

The next admissible move is still documentation or anti-NIH audit only:

```text
defer until Level 3.5 held-out closure, then run a separate prior-art / necessity kill-test
before any prototype authorization
```
