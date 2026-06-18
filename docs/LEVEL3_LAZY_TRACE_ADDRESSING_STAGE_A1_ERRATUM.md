# Level 3 Lazy Trace Addressing Stage A.1 Erratum

## Status

- type: `IMMUTABLE_ADDENDUM`
- evidence_class: `REANALYSIS_ONLY_FROZEN_PROTOCOL`
- original_stage_a1_artifacts_modified: `false`
- held_out_execution: `0`

## Why this erratum exists

Stage A.1 compared the random-hyperplane collision model against a coarse decoder-contract retrieval metric. That was too permissive for the research target that now governs the routing line.

The corrected comparison is:

```text
expected exact bucket-hit probability
vs
observed exact-trace candidate-generation recall
```

Not:

```text
expected exact bucket-hit probability
vs
decoder-contract recall
```

## Corrected decomposition

For each Stage A.1 method in the reanalysis at the primary operating point:

1. `raw_exact_trace_candidate_recall`
2. `post_budget_exact_trace_recall`
3. `post_rerank_exact_trace_recall_at_32`
4. `accepted_exact_trace_coverage`
5. `conditional_risk_among_accepted`

This separates:

- raw inclusion in the routed neighborhood,
- loss from candidate-budget truncation,
- loss from top-32 reranking,
- final verifier-authorized coverage.

## Scope of the reanalysis

The addendum is restricted to the Stage A.1 primary operating point:

```text
N = 10,000
D = 1024
p = 0.05
queries = 512
```

This is sufficient for the A.2a mature-index shootout because the Stage A.1 theoretical discussion and the original gating tension were centered on the same primary cell.

## Interpretation change

- Decoder-contract retrieval remains useful as a diagnostic.
- Exact creation-trace retrieval is the primary target.
- Stage A.1 should therefore be read as evidence that semantic LSH can retrieve a useful neighborhood, not as evidence that it already solves exact provenance recovery.

## Corrected primary-cell comparison

Reanalysis at `p = 0.05` shows:

| Method | Expected exact bucket hit | Observed raw exact-trace inclusion | Accepted exact-trace coverage |
| --- | ---: | ---: | ---: |
| `B3_stage_a_four_table_lsh` | `0.4919` | `0.5078` | `0.4023` |
| `B4_a1p_multi_table_lsh` | `0.9525` | `0.9395` | `0.7090` |
| `B7_margin_aware_multi_probe_lsh` | `0.6558` | `0.8379` | `0.6484` |

The key repair is that the theoretical collision model tracks candidate-generation inclusion well enough for the frozen A.1 LSH family, but it does not by itself guarantee exact-trace acceptance coverage.

## Contract preserved

Nothing in this erratum:

- changes Stage A.1 seeds,
- changes Stage A.1 methods,
- changes Stage A.1 corruption points,
- changes Stage A.1 acceptance policy,
- authorizes Stage B.
