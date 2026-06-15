# Level 2B.0 Prior-Art Matrix

Schema version: `level2b0-anti-nih-audit-v1`

| Requirement | Existing method/library | Coverage | Mismatch | Verdict | Why not scratch | Required adapter |
| --- | --- | --- | --- | --- | --- | --- |
| exact entity lookup | Indexed key-value lookup | 100% | None in closed-world exact-id cases. | ADOPT | Commodity database/index problem. | Key extraction only. |
| noisy structured cue | dedupe / Splink probabilistic ER | 90% | Need thin query-object adapter and abstention wrapper. | WRAP | Would re-implement fuzzy matching and calibration. | Cue-to-record conversion and ranked-id handoff. |
| canonical entity resolution | dedupe Gazetteer | 95% | No explicit action-layer abstention token. | ADOPT | Gazetteer path already exists upstream. | Optional threshold to unresolved state. |
| context-dependent candidate restriction | Splink blocking rules / Dedupe fingerprinter | 95% | Must benchmark against ordinary blocking; otherwise novelty collapses. | ADAPT | Blocking is standard ER tooling. | External policy picks among upstream blocking policies. |
| probabilistic ambiguity | Splink probabilities / dedupe confidence / Stone Soup hypothesis weights | 85% | Need shared uncertainty handoff to downstream action policy. | COMPOSE | Native systems already score uncertainty. | Normalize scores, preserve provenance. |
| temporal continuity | Stone Soup JPDA-style association | 85% | Requires observation adapter from symbolic events. | WRAP | Sequential association is established tracking prior art. | Observation/state translation layer. |
| possible unobserved change | Tracking missed detections plus explicit belief reducer | 80% | Need explicit action-layer stale/conflict semantics. | COMPOSE | This is reducer logic, not a new retrieval algorithm. | Reducer with support/conflict references. |
| new entity initiation | Stone Soup initiators / unresolved ER no-match | 55% | Full provisional identity lifecycle remains out of scope. | BLOCK | Too large and underspecified for current stage. | Defer until separate lifecycle benchmark exists. |
| provisional identity | Partial overlap from MHT and unresolved ER | 50% | No audited system gives the exact cross-memory authority contract for provisional identities. | BLOCK | Would balloon into a lifecycle architecture project. | None until scope is narrowed. |
| false merge prevention | Thresholded no-match + multi-hypothesis tracking | 75% | Requires authority policy spanning matcher and action layers. | COMPOSE | Confidence thresholds already exist upstream. | Shared abstain/defer contract. |
| evidence provenance | Native scores plus explicit controller logs | 70% | No single library logs cross-mechanism decision provenance end to end. | COMPOSE | Provenance is glue around adopted tools. | Structured decision record. |
| rollback/non-commit | Unresolved/no-match thresholds and deferred track initiation | 70% | Need explicit authority boundary, not just low score. | COMPOSE | Non-commit policy should wrap native scores, not replace them. | Thresholded abstain wrapper. |
| downstream action integration | Controller layer over native matcher/tracker outputs | 45% | No upstream package owns context routing, budget control, and safe fallback across heterogeneous systems. | BUILD | This is the only plausible minimal seam left after prior-art overlap. | Small external controller with explicit ablations. |
