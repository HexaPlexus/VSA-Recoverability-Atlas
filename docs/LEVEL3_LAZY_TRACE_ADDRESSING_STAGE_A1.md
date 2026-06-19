# Lazy Semantic-to-Trace Addressing - Stage A.1

## Verdict

`PROTOTYPE / DEVELOPMENT_ONLY / PROTOCOL_AMENDMENT`

Build verdict after execution: `PARTIAL`

## Why Stage A Needed An Amendment

Stage A was not a lawful falsification of semantic random-hyperplane routing. Its frozen four-table configuration was simply too small for the target recall at the fixed corruption contract.

For bipolar independent sign-flip corruption with `p = 0.05`:

- `rho = 1 - 2p = 0.9`
- for one random-hyperplane bit:
  - `q = 1 - arccos(rho) / pi ~= 0.856`
- for `b = 12` and `L = 4`:
  - `P(hit at least one table) = 1 - (1 - q^b)^L ~= 0.49`

Stage A observed `recall@32 ~= 0.50` for the four-table router at `N = 10_000`, `D = 1024`, `p = 0.05`, which is consistent with theory rather than evidence that semantic LSH routing was intrinsically broken.

Stage A therefore stayed `PARTIAL`, and Stage A.1 lawfully amends the frozen development protocol before any held-out execution.

## Scope

Stage A.1 tests only:

- semantic cue -> semantic LSH routing -> local candidate set
- exact semantic reranking
- typed trace validation
- decoder-contract retrieval versus exact creation-trace retrieval
- ambiguity handling for semantically indistinguishable but derivationally distinct records

Stage A.1 still excludes:

- actual MAP or BCF decoder execution
- Stage B decoder orchestration
- embedded trace zones
- CGRN-HSR fallback search
- HNSW, SDM, vector DBs, or production runtime
- any held-out confirmation

## Reuse / Anti-NIH

- `ADOPT`: existing MAP/TorchHD semantic substrate
- `WRAP`: existing tiny deterministic random-hyperplane router in [src/cgrn_hsr/semantic_lsh.py](../src/cgrn_hsr/semantic_lsh.py)
- `WRAP`: existing typed [TraceRecord](../src/cgrn_hsr/trace_record.py), [TraceIndex](../src/cgrn_hsr/trace_index.py), and [verification](../src/cgrn_hsr/verification.py) primitives
- `BLOCK`: new ANN framework, new VSA, new self-decoding memory, Stage B orchestration, held-out execution

No mature ANN/LSH routing library exists in the frozen repo dependency graph. Stage A.1 therefore keeps the tiny deterministic wrapper and extends it only with:

- configurable table count
- deterministic projection seeds
- margin-aware per-table neighbor probing
- explicit raw-posting and duplicate-posting accounting
- analytical expectation reporting

## Authority Boundary

- Semantic LSH: routing authority only
- Similarity reranker: candidate ordering only
- Typed trace validation: schema and record-association authority
- Decoder-contract decision: contract-level acceptance authority
- Exact-trace decision: provenance-level acceptance authority
- Ambiguous exact provenance: `AMBIGUOUS_TRACE`
- No valid candidate: `EXPAND` or `ABSTAIN`

## Protocol Amendment

Previous Stage A protocol hash:

- `f9f770c7af19ad7fc5efb2d8191be116ecdccfd6d6b22f51d7c74da8c58f50ab`

Stage A.1 protocol file hash:

- `3457395a278f470f9e0dd8c8a43ae2296ed0629444e8b578218231fc241f2dd6`

Allowed change classes:

- `ANALYTICAL_GRID_REPAIR`
- `BASELINE_IMPLEMENTATION_REPAIR`
- `SAMPLE_SIZE_INCREASE`
- `METRIC_DISAMBIGUATION`
- `ADVERSARIAL_DATASET_STRENGTHENING`
- `METADATA_ONLY`

### Preserved

- semantic substrate: MAP
- dimensions: `D = 1024`
- primary record count: `N = 10_000`
- corruption channel: independent external Bernoulli sign flips
- corruption points: `p in {0.00, 0.01, 0.03, 0.05, 0.10, 0.15}`
- no held-out execution
- no decoder execution
- no frozen Level 3.5 artifact mutation

### Changed

- query count increased from `32` to `512` per primary cell
- analytically selected LSH configs added:
  - `A1-P`: `12 bits x 18 tables`
  - `A1-S1`: `11 bits x 15 tables`
  - `A1-S2`: `13 bits x 21 tables`
  - `A1-MP`: `12 bits x 4 tables` with bounded margin-aware probing
- global scan baseline repaired to a contiguous matrix + vectorized top-k path
- decoder-contract retrieval separated from exact creation-trace retrieval
- explicit ambiguity contract added
- new adversarial data augmentations added
- acceptance coverage and conditional risk made first-class metrics

## Frozen Stage A.1 Configurations

Primary semantic routers:

- `B3_stage_a_four_table_lsh`: Stage A historical reference (`12 bits x 4 tables`)
- `B4_a1p_multi_table_lsh`: `12 bits x 18 tables`
- `B5_a1s1_multi_table_lsh`: `11 bits x 15 tables`
- `B6_a1s2_multi_table_lsh`: `13 bits x 21 tables`
- `B7_margin_aware_multi_probe_lsh`: `12 bits x 4 tables`, `probe_budget_per_table = 4`

Controls:

- `B0_global_exact_semantic_scan`
- `B1_exact_content_hash_only`
- `B2_random_bucket_routing` budget-matched to each semantic router

Fixed acceptance policy:

- `rerank_k = 32`
- `accept_similarity_threshold = 0.88`
- `accept_margin = 0.015`

This is a new Stage A.1 development threshold, not a confirmatory scientific gate.

## Fresh Development Seeds

Dataset seed namespace:

- `n10000`: `930450100`

Query seed ranges:

- `p=0.00`: `930460100..930460611`
- `p=0.01`: `930461100..930461611`
- `p=0.03`: `930462100..930462611`
- `p=0.05`: `930463100..930463611`
- `p=0.10`: `930464100..930464611`
- `p=0.15`: `930465100..930465611`

Projection seeds:

- `930470101`
- `930470102`
- `930470103`

Smoke seed:

- `930480001`

These ranges are disjoint from Stage A, Level 3.5, and held-out namespaces.

## Retrieval Tasks

### Task 1 - Decoder-Contract Retrieval

Correct if the retrieved candidate identifies the correct:

- operation family
- algebra
- arity
- operand namespaces
- relevant operation parameters

Exact parent handles and exact creation event are not required.

### Task 2 - Exact Creation-Trace Retrieval

Correct only if the retrieved candidate identifies the exact:

- trace handle
- creation event / record association
- parent handles
- operation parameters
- payload association

Decoder-contract success does not imply exact provenance success.

## Ambiguity Contract

Stage A.1 adds controlled ambiguous cases:

- identical semantic payload with different exact parent handles
- identical semantic payload with conflicting decoder contracts
- semantically near but derivationally different neighborhoods

Expected behavior:

- semantic-only routing may retrieve the local neighborhood
- exact-trace acceptance must not silently choose one exact trace when multiple exact traces remain consistent
- lawful exact-trace outcome is `AMBIGUOUS_TRACE` or `ABSTAIN`

## Results Summary

Primary evaluation cell:

- `N = 10_000`
- `D = 1024`
- `p = 0.05`
- `512` queries

### Decoder-Contract Routing

At `p = 0.05`, non-ambiguous-contract subset:

| Method | decoder_contract_recall@32 | acceptance_coverage | median candidates | p95 candidates | p50 latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 global scan | 1.0000 | 0.8458 | 10000 | 10000 | 0.02513 |
| B3 Stage A 4-table | 0.8875 | 0.4563 | 11 | 17 | 0.00254 |
| B4 A1-P | 0.9958 | 0.8000 | 48 | 61 | 0.01017 |
| B7 A1-MP | 0.9896 | 0.7333 | 42 | 57 | 0.00964 |
| B2 random matched to A1-P | 0.9521 | 0.0021 | 43 | 44 | 0.00843 |

### Exact Creation-Trace Routing

At `p = 0.05`, non-ambiguous-contract subset:

| Method | exact_trace_recall@32 | acceptance_coverage | conditional risk |
| --- | ---: | ---: | ---: |
| B0 global scan | 1.0000 | 0.8000 | 0.0000 |
| B3 Stage A 4-table | 0.5063 | 0.4292 | 0.0000 |
| B4 A1-P | 0.9354 | 0.7563 | 0.0000 |
| B7 A1-MP | 0.8354 | 0.6917 | 0.0000 |
| B2 random matched to A1-P | 0.0021 | 0.0021 | 0.0000 |

### Ambiguity Handling

At `p = 0.05`:

| Method | ambiguity_detection_rate | ambiguous_wrong_acceptance_rate | ambiguous_abstention_rate |
| --- | ---: | ---: | ---: |
| B0 global scan | 1.0000 | 0.0000 | 1.0000 |
| B3 Stage A 4-table | 0.5156 | 0.0000 | 1.0000 |
| B4 A1-P | 0.9375 | 0.0000 | 1.0000 |
| B7 A1-MP | 0.8281 | 0.0000 | 1.0000 |

### Theory vs Observed

At `p = 0.05`:

| Method | expected any-table hit | observed decoder recall@32 | expected occupancy | observed candidates |
| --- | ---: | ---: | ---: | ---: |
| B3 Stage A 4-table | 0.4919 | 0.8875 | 9.77 | 10.89 |
| B4 A1-P | 0.9525 | 0.9958 | 43.95 | 47.89 |
| B5 A1-S1 | 0.9507 | 0.9938 | 73.24 | 77.94 |
| B6 A1-S2 | 0.9505 | 0.9938 | 25.63 | 28.38 |
| B7 A1-MP | 0.6558 | 0.9896 | 39.06 | 41.85 |

The primary A1-P configuration stays within the prospective `±0.05` theory-consistency tolerance.

## Adversarial Ablations

At `p = 0.05` on the primary semantic router:

- projection-seed ablation (`A9`) remained stable: decoder-contract recall@32 stayed `1.0` for all three fixed projection seeds in the 64-query ablation slice
- semantic-to-exact-trace shuffle (`A6`) collapsed exact-trace recovery while preserving contract-level recovery
- semantic-to-contract shuffle (`A7`) produced very high decoder-contract conditional risk (`0.9167`), confirming that meaningful contract recovery depends on lawful semantic-to-contract alignment
- parent-handle shuffle preserved contract retrieval but destroyed exact-trace recovery

## Gate Evaluation

Primary gates at `N=10_000`, `p=0.05`, method `B4_a1p_multi_table_lsh`:

- `routing_gate_decoder_contract_recall_at_32`: `PASS`
- `candidate_gate_median_le_100`: `PASS`
- `safety_gate_zero_wrong_acceptance`: `PASS`
- `utility_gate_nontrivial_acceptance`: `FAIL`
- `latency_gate_vs_vectorized_global_scan`: `PASS`
- `theory_consistency_gate`: `PASS`

### Why Utility Failed

The utility gate requires both:

- non-trivial acceptance coverage
- candidate reduction that beats budget-matched random routing

The primary router achieved the coverage target exactly (`0.80`), but budget-matched random routing to the same candidate budget family produced a slightly stronger candidate-reduction ratio:

- `B4 A1-P`: `0.995211`
- `random matched to B4`: `0.995881`

This does not erase the routing effect. It shows that the decoder-contract target is coarse enough that a random 43-candidate neighborhood already captures the right contract very often, even though it almost never recovers the exact trace.

## Interpretation

Stage A.1 confirms:

- semantic LSH routing can reach very high decoder-contract recall under the frozen MAP sign-flip contract
- exact-trace retrieval is materially harder than decoder-contract retrieval
- ambiguity can be handled lawfully without silent wrong acceptance
- the repaired vectorized global scan no longer trivializes the latency comparison

Stage A.1 does **not** confirm:

- that semantic-only routing is sufficient for exact provenance identity
- that the current semantic router dominates budget-matched random routing on the chosen utility trade-off
- that Stage B decoder orchestration should start

## Kill-Gate Status

No hard block condition fired:

- no held-out or frozen artifacts were touched
- wrong acceptance stayed zero
- ambiguous exact traces were not silently accepted
- vectorized full scan remained slower than the primary router

However the remaining gap is important:

> Semantic-only routing is strong for decoder-family narrowing, but exact creation-trace identity still needs stronger routing information or a carried trace fingerprint.

## Claim Boundary

Allowed:

- semantic random-hyperplane routing is development-feasible for decoder-contract retrieval
- exact provenance recovery must be evaluated separately from contract retrieval
- ambiguity handling is mandatory when semantically indistinguishable records have different traces

Forbidden:

- no new ANN or LSH algorithm was created
- no exact provenance recovery claim follows from decoder-contract recall
- no superiority over mature ANN/SDM baselines is established
- no Stage B authorization follows automatically
- no held-out or production confirmation exists

## Next Lawful Stage

Only if this line of work continues:

- `Stage A.2`: compare semantic routing against mature ANN and SDM-style baselines under the same memory, candidate-budget, ambiguity, and safety accounting

Stage B remains unauthorized.
