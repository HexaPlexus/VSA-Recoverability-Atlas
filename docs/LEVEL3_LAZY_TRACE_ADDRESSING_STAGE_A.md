# Lazy Semantic-to-Trace Addressing - Stage A

## Verdict

`PROTOTYPE / DEVELOPMENT_ONLY`

## Hypothesis

> A semantic MAP hypervector may compute an approximate locality-sensitive routing signal that narrows trace retrieval to a small local candidate set before any decoder-family search begins.

## Prior Art / Reuse

- Reused `torch-hd` MAP primitives for semantic payload construction.
- Reused exact cosine reranking over stored MAP payloads.
- No mature ANN/LSH library exists in the frozen dependency graph, so Stage A uses a tiny deterministic random-hyperplane wrapper plus posting dictionaries instead of a new framework.

## Scope

- Semantic cue -> approximate content address -> local trace candidate set only.
- Sidecar `TraceRecord` only; no in-vector trace zone, recursive provenance traversal, BCF, factorization fallback, or transactional write-back.

## Authority Boundary

- Semantic LSH: routing authority only.
- TraceRecord: operation-contract authority after validation.
- Similarity reranker: candidate ordering only.
- Verifier: acceptance authority.
- No valid candidate: `EXPAND` or `ABSTAIN`.

## Baselines

- `B0_global_exact_semantic_scan`
- `B1_exact_content_hash_only`
- `B2_random_bucket_routing`
- `B3_one_table_lsh`
- `B4_multi_table_lsh`
- `B5_bounded_multi_probe_lsh`

## Leakage Controls

- LSH signatures are computed only from semantic payloads.
- No trace handle, record id, operation label, or parent id enters the semantic payload.
- Trace label shuffles and semantic-to-trace shuffles are explicit ablations.

## Development Gates

- `G1_trace_recall_at_32_n10000_p005`: `FAIL`
- `G2_candidate_median_le_1pct_n10000_p005`: `PASS`
- `G3_wrong_acceptance_zero_n10000_p005`: `PASS`
- `G4_beats_budget_matched_random_n10000_p005`: `PASS`
- `G5_query_latency_lt_global_scan_n10000_p005`: `PASS`

## Non-goals

- No production decoder orchestration.
- No recursive trace traversal.
- No held-out confirmation.
- No new ANN service or vector database.

## Next Lawful Stage

- Stage B is only admissible if Stage A stays within the stated claim boundary and passes the local feasibility gates.

