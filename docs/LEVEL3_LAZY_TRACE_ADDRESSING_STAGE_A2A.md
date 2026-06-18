# Level 3 Lazy Trace Addressing Stage A.2a

## Verdict

`ADOPT / COMPOSE / DEVELOPMENT_ONLY`

## Question

Given a noisy MAP semantic cue, which mature retrieval method best returns the exact associated creation-trace record under bounded latency, memory and safety constraints?

Primary target:

```text
exact creation-trace retrieval
```

Secondary diagnostic:

```text
decoder-contract retrieval
```

## Prior art and reuse

- `ADOPT`: Faiss exact float scan (`IndexFlatIP`)
- `ADOPT`: Faiss float HNSW (`IndexHNSWFlat`)
- `ADOPT`: Faiss exact binary Hamming scan (`IndexBinaryFlat`)
- `ADOPT`: Faiss binary HNSW (`IndexBinaryHNSW`)
- `ADOPT`: Faiss binary multi-hash (`IndexBinaryMultiHash`)
- `WRAP`: existing Stage A.1 thin random-hyperplane router as the incumbent baseline only
- `REJECT`: new custom ANN / graph / hash-table framework

## Scope

Included:

- MAP semantic substrate at `D=1024`
- `N=10,000`
- Bernoulli sign-flip corruption with `p = {0.00, 0.01, 0.03, 0.05, 0.10, 0.15}`
- exact-trace retrieval
- decoder-contract diagnostics
- ambiguity-safe verification
- memory, build/update and latency accounting

Excluded:

- Stage B decoder execution
- carried trace zones
- CGRN-HSR fallback factorization
- SDM
- held-out confirmation
- production routing

## Fixed contracts

Common pipeline:

```text
noisy query
-> mature index or incumbent thin router
-> bounded external candidate ids
-> canonical exact reranking
-> top-32 exact trace candidates
-> typed trace validation
-> ambiguity policy
-> ACCEPT / ABSTAIN
```

Important authority boundary:

- index: routing authority only
- canonical reranker: ordering only
- trace record validation: contract authority
- ambiguity policy: exact provenance commit authority

## Baselines

- `B0`: vectorized exact semantic scan
- `B1`: Faiss exact float scan
- `B2`: frozen thin Stage A.1 LSH incumbent
- `B3`: float HNSW
- `B4`: exact binary Hamming scan
- `B5`: binary HNSW
- `B6`: binary multi-hash

## Metric-equivalence contract

For bipolar MAP payloads with fixed dimensionality:

```text
dot(x, y) = D - 2 * hamming(bits(x), bits(y))
```

Therefore:

- inner-product ranking,
- cosine ranking for equal-norm bipolar vectors,
- packed Hamming ranking

must agree modulo explicit deterministic tie handling.

## Development gates

Primary cell:

```text
N = 10,000
D = 1024
p = 0.05
queries = 512
K_candidate = 100
rerank_k = 32
```

Gates:

- safety:
  - `exact_trace_conditional_risk == 0`
  - `ambiguous_wrong_acceptance_rate == 0`
  - `malformed_trace_acceptance == 0`
- retrieval utility:
  - `exact_trace_recall_at_32 >= 0.93`
  - `accepted_exact_trace_coverage >= 0.75`
- latency:
  - `p50 total latency < repaired vectorized B0`
- mature-baseline survival:
  - thin LSH survives only if it remains nondominated on a meaningful practical frontier

## Kill gates

Block the routing line if:

1. no approximate method beats optimized exact search in a useful region;
2. ambiguity-safe exact provenance cannot be maintained;
3. candidate routing does not materially localize the exact trace neighborhood;
4. the custom thin router is strictly dominated by a mature baseline.

## Next lawful stage

Exactly one of:

- `A2B_SDM_COMPARISON`
- `A2B_SCALE_CROSSOVER`
- `A2B_CARRIED_FINGERPRINT_PROTOCOL`
- `BLOCK_BEFORE_STAGE_B`

Stage B remains blocked.
