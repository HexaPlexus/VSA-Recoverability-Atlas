# Level 2B.0 Architecture Overlap

## Proposed path

```text
partial/noisy cue
    -> candidate restriction
    -> native matcher or tracker
    -> indexed belief projection
    -> commit / abstain / fallback
```

## Overlap map

| Proposed component | Existing pattern | Status | Note |
| --- | --- | --- | --- |
| Exact entity lookup | Database index / key-value store | Not new | Use indexed lookup directly for exact-id queries; VSA should not be on this path. |
| Structured fuzzy entity matching | dedupe / Splink | Not new | Standard structured ER already covers noisy tabular identity matching and ranking. |
| Context-biased candidate restriction | Standard blocking in ER | Weak novelty | Only defensible if evaluated as external policy over unchanged native matchers. |
| Sequential association under misses/clutter | Stone Soup PDA/JPDA/MHT family | Not new | Do not hand-roll trackers or hypothesis maintenance. |
| Cue-based episodic retrieval | Soar episodic memory | Not new | Architecture pattern exists; do not present retrieval-by-cue as a fresh mechanism. |
| Partial matching and thresholded declarative retrieval | ACT-R declarative memory | Not new | Partial matching, spreading activation, and retrieval thresholds are established. |
| Memory/action decomposition | CoALA | Not new | The high-level split between memory systems and actions is already a named pattern. |
| Authority-preserving controller across heterogeneous native systems | No single audited upstream package closed this seam | Possible seam | Only survives if compared against ordinary blocking/routing and if native uncertainty remains intact. |

## Read-through

- Splink already covers probabilistic matching, explicit blocking, and evaluation over structured records.
- dedupe already covers gazetteer-style canonical matching over noisy structured inputs.
- Stone Soup already covers association hypotheses, missed detections, initiators, and deleters.
- Soar and ACT-R already cover cue-based episodic/declarative retrieval patterns and thresholded recall.
- CoALA already names the memory/action decomposition at the architecture level.
- The only seam still plausibly worth building is a very small external controller that chooses among adopted native mechanisms while preserving uncertainty and non-commit authority.
