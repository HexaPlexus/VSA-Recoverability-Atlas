# Supplementary Evidence Atlas

This atlas is generated from the machine-readable registries and summarizes all normalized hypotheses.

The main manuscript intentionally keeps only compact tables, figures, and bounded claims in the main text. This supplement retains the full evidence-oriented material:

- all normalized repository hypotheses;
- all current evidence statuses and architectural dispositions;
- full protocol-hash and result-path references where available;
- the full prior-art matrix and transfer limits;
- the full claim ledger and reopen conditions.

Use this document together with:

- [CLAIM_TRACEABILITY.md](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/CLAIM_TRACEABILITY.md)
- [CITATION_AUDIT.md](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/CITATION_AUDIT.md)
- [LITERATURE_SCREENING_AUDIT.md](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/LITERATURE_SCREENING_AUDIT.md)

## level0_dependency_bootstrap

- Title: Dependency-locked TorchHD/MAP bootstrap for reproducible local experiments
- Category: `INFRASTRUCTURE_BASELINE`
- Evidence status: `ADOPTED_ENGINEERING_BASELINE`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Can the repository maintain a minimal reproducible local substrate without custom VSA runtime code?
- Method: Pinned Python environment, TorchHD reuse, pytest smoke checks
- Result paths: pyproject.toml, pylock.toml, tests/test_level0_smoke.py, DEPENDENCIES.md
- Protocol hashes: None recorded
- Key result: Core repo remains installable without bespoke runtime primitives.
- Main failure point: Public release still requires explicit licensing and path hygiene.
- Allowed claims: The repository has a reproducible local bootstrap path for core CPU experiments.
- Forbidden claims: The bootstrap layer is a novel VSA runtime or decoder.
- Reopen conditions: Reopen only to adjust dependency pins, Python support, or smoke coverage.

## level1_context_conditioned_search

- Title: External semantic context can improve candidate routing over random subsets in bounded Level 1 single-product recovery
- Category: `CONTEXT_CONDITIONED_SEARCH`
- Evidence status: `REPRODUCED_IN_REPO`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Can external probabilistic context improve candidate routing, compute use, and silent-failure control without changing the underlying MAP geometry?
- Method: MAP resonator with context-selected candidate subsets, selective acceptance, and cold global fallback
- Result paths: docs/LEVEL1_RESEARCH_CLOSURE.md, results/level1a, results/level1c, results/level1d, results/level1e, results/level1e1, results/level1f3, results/level1f4
- Protocol hashes: None recorded
- Key result: Semantic context beat random candidate selection in tested single-product regimes; cold fallback survived while warm continuation failed.
- Main failure point: Warm continuation, cheap probes, and over-broad hierarchical runtime claims did not survive audit.
- Allowed claims: Semantic context beat random candidate selection in the tested Level 1 settings., The external context-selection seam transferred across MAP and the official IBM BCF selector layer.
- Forbidden claims: Universal substrate independence, Hierarchical resonator continuation as the default runtime, Verifier or lifecycle transfer to BCF beyond the audited selector envelope
- Reopen conditions: Reopen only for new typed controller experiments or new public BCF confirmations under fresh seeds.

## level1f_holovec_task_mismatch

- Title: HoloVec attention resonator is not a fair drop-in competitor under the repository's factor-specific domain contract
- Category: `COMPETITOR_AUDIT`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Can HoloVec be wrapped as a lawful drop-in factorizer for the existing multi-domain benchmark?
- Method: Dependency audit and API audit of HoloVec attention cleanup
- Result paths: docs/LEVEL3_1_NATIVE_REPRODUCTION.md, results/level1f/dependency_audit.json
- Protocol hashes: None recorded
- Key result: HoloVec exposes one shared flat codebook and no lawful per-factor domain interface for the benchmark contract.
- Main failure point: Task mismatch blocked a fair shootout.
- Allowed claims: The audited HoloVec API is not a lawful drop-in substitute for this benchmark contract.
- Forbidden claims: HoloVec is universally worse than MAP.
- Reopen conditions: Reopen only if an upstream factor-specific domain API appears.

## level1f_bcf_selector_transfer

- Title: Official IBM BCF can participate in scoped selector-level comparisons but not yet in full parity claims
- Category: `SUBSTRATE_COMPARISON`
- Evidence status: `IMPLEMENTATION_AUDITED`
- Architectural disposition: `IMPLEMENTATION_AUDITED`
- Research question: Can the official IBM BCF implementation be wrapped lawfully for the repository's single-product benchmark contract?
- Method: Official upstream smoke audit, selector-level comparison, and native-envelope reproduction
- Result paths: docs/LEVEL1_RESEARCH_CLOSURE.md, docs/LEVEL3_1_NATIVE_REPRODUCTION.md, results/level3_1/bcf_native_reproduction.json
- Protocol hashes: None recorded
- Key result: BCF was reproducible as an audited native envelope, but parity claims remain scoped and expensive.
- Main failure point: Structured-mixture parity and broad runtime substitution remain unresolved.
- Allowed claims: The official IBM BCF implementation can be reproduced and wrapped for scoped single-product audits., Context transfer reached the selector level.
- Forbidden claims: BCF is inherently slower in all settings., BCF is a drop-in replacement for the full MAP control stack.
- Reopen conditions: Reopen only for fresh public held-out confirmation or new structured-mixture parity protocols.

## level2a_temporal_memory_narrow

- Title: Approximate semantic retrieval can help temporal replay only as a narrow fallback, while exact indexed location remains stronger
- Category: `TEMPORAL_RETRIEVAL`
- Evidence status: `PARTIALLY_REPRODUCED`
- Architectural disposition: `PARTIALLY_REPRODUCED`
- Research question: Can semantic retrieval plus abstention provide useful temporal memory behavior without BCF or a new memory system?
- Method: Semantic MAP retrieval with abstention and cold fallback versus exact indexed location controls
- Result paths: results/level2a/analysis.json
- Protocol hashes: None recorded
- Key result: Semantic retrieval was directionally useful, but exact indexed location remained stronger and the verdict stayed narrow.
- Main failure point: Semantic retrieval did not justify replacing exact indexed location.
- Allowed claims: Semantic retrieval supplied useful locality in a narrow temporal-memory seam.
- Forbidden claims: A new memory substrate or replacement for exact indexing.
- Reopen conditions: Reopen only for exact-vs-approximate crossover studies with clear utility accounting.

## level2b_portable_context_controller

- Title: Portable external context control across heterogeneous native mechanisms remains a narrow open hypothesis, not a custom ER architecture
- Category: `META_CONTROL`
- Evidence status: `DEFERRED_HYPOTHESIS`
- Architectural disposition: `DEFERRED_HYPOTHESIS`
- Research question: Is there a residual research seam beyond ordinary algorithm selection and metareasoning for a typed authority-preserving controller?
- Method: Prior-art closure and seam isolation over existing matchers, trackers, and resolver outputs
- Result paths: docs/LEVEL2B_RESEARCH_CLOSURE.md, docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md
- Protocol hashes: None recorded
- Key result: Broad custom entity-resolution research was blocked; only a thin controller seam remained as a deferred hypothesis.
- Main failure point: Most of the apparent novelty was already covered by portfolio methods and metareasoning.
- Allowed claims: Portable context control is still only a bounded research hypothesis.
- Forbidden claims: A new entity-resolution architecture or new metareasoning theory.
- Reopen conditions: Reopen only as a thin controller experiment over unchanged native mechanisms.

## level2c_existing_matcher_context_policy

- Title: Context policy can be tested as a narrow overlay on an existing matcher without inventing a new matcher
- Category: `CONTEXT_CONDITIONED_SEARCH`
- Evidence status: `PARTIALLY_REPRODUCED`
- Architectural disposition: `PARTIALLY_REPRODUCED`
- Research question: Can a transparent context policy improve candidate blocking and fallback behavior over an unchanged existing matcher?
- Method: Frozen Splink matcher with transparent context policy and safe broad fallback
- Result paths: results/level2c/analysis.json
- Protocol hashes: level2c-frozen-protocol-v1
- Key result: The policy remained narrow and explicitly forbade claims of a universal context controller or new matcher.
- Main failure point: The seam is not evidence for CNM or a new probabilistic matcher.
- Allowed claims: Candidate-policy portability beyond VSA can be studied narrowly on an adopted matcher.
- Forbidden claims: New matcher claim, CNM/H2 necessity claim
- Reopen conditions: Reopen only for larger external-matcher comparisons under equal-information contracts.

## level3_2_map_budget_robustness

- Title: MAP resonator recoverability has a bounded intermediate region shaped by budget, restart policy, and abstention
- Category: `MAP_RESONATOR_BASELINE`
- Evidence status: `REPRODUCED_IN_REPO`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: How far can unchanged MAP resonator recovery be pushed before recoverability accounting demands more compute, more structure, or abstention?
- Method: Compute-matched MAP budget robustness and clean U1 confirmation without context
- Result paths: results/level3_2, results/level3_2b/analysis.json, docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md
- Protocol hashes: None recorded
- Key result: MAP retained a bounded intermediate region rather than an unlimited clean-factorization regime.
- Main failure point: More compute alone did not remove the transition-region constraints.
- Allowed claims: MAP has a bounded intermediate recoverability region in the tested clean U1 envelope.
- Forbidden claims: Unlimited clean MAP factorization or universal impossibility for all VSA recovery.
- Reopen conditions: Reopen only for equal-information comparisons against alternative substrates or exact side information.

## level3_3_linear_code_reproduction

- Title: The NeCo linear-code paper contract can be reproduced for clean U1 under explicit GF(2) constraints
- Category: `PAPER_REPRODUCTION`
- Evidence status: `PAPER_REPRODUCTION`
- Architectural disposition: `REPRODUCED_IN_REPO`
- Research question: Can the reported linear-code recovery mechanism be reproduced lawfully in-repo without inventing a new GF(2) framework?
- Method: Paper-specific clean U1 reproduction using galois over GF(2)
- Result paths: docs/LEVEL3_3_LINEAR_CODE_REPRODUCTION.md, results/level3_3
- Protocol hashes: None recorded
- Key result: The paper contract was reproduced under explicit common-U1 constraints.
- Main failure point: No noise, no broader substrate claim, and no promotion beyond the paper contract.
- Allowed claims: The clean U1 linear-code paper contract was reproduced with explicit constraints.
- Forbidden claims: Noise robustness or universal superiority of linear codes from this stage alone.
- Reopen conditions: Reopen only for noise-frontier or equal-information comparisons against symbolic and MAP baselines.

## level3_4_algebraic_baseline_closure

- Title: Clean U1 algebraic baselines match each other while the packed symbolic exact baseline dominates the task envelope
- Category: `SUBSTRATE_COMPARISON`
- Evidence status: `REPRODUCED_IN_REPO`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Does the clean U1 task justify native noisy substrates when symbolic exact recovery is available?
- Method: NeCo versus generic linear-code comparison plus symbolic exact tuple baseline
- Result paths: docs/LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md, results/level3_4
- Protocol hashes: None recorded
- Key result: NeCo and generic linear baselines were equivalent on clean U1, while the symbolic exact baseline dominated the task.
- Main failure point: This did not settle noisy behavior and therefore did not authorize broad substrate claims.
- Allowed claims: NeCo and generic linear baselines were equivalent on the tested clean U1 cells., The symbolic exact record baseline dominated the clean U1 task.
- Forbidden claims: Noise-frontier or universal substrate superiority from this stage alone.
- Reopen conditions: Reopen only in explicit noise-frontier or storage-cost comparisons.

## level3_5a_noise_contract_audit

- Title: Noise must be split into explicit external corruption contracts and substrate-native error semantics before any comparison claim
- Category: `NOISE_AND_PROTOCOL`
- Evidence status: `ADOPTED_ENGINEERING_BASELINE`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: What minimum audit contract is required before cross-substrate noise claims become lawful?
- Method: Noise baseline matrix, source ledger, and typed corruption audit
- Result paths: docs/LEVEL3_5A_NOISE_BASELINE_MATRIX.md, results/level3_5a
- Protocol hashes: None recorded
- Key result: Universal raw-p noise claims were blocked; lawful comparison requires typed substrate-specific contracts.
- Main failure point: Cross-substrate noise scales are not interchangeable without explicit calibration.
- Allowed claims: Noise comparisons require explicit typed contracts and separated corruption channels.
- Forbidden claims: Universal raw-p frontier across incompatible substrates.
- Reopen conditions: Reopen only for new substrate-specific contracts or calibrated severity mappings.

## oracle_portfolio_complementarity_v0_1

- Title: In the common clean F=3 envelope, BCF dominated hard paired failures and no deployable instance-level cross-substrate router was justified
- Category: `CROSS_SUBSTRATE_PORTFOLIO`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Do already-implemented MAP and BCF methods exhibit verified, cost-aware per-instance complementarity strong enough to justify a practical escalation router?
- Method: Paired clean F=3 evaluation of frozen MAP D512 fast, MAP D1024 fast, MAP D1024 robust, BCF native, static threshold routes, fixed-order cascades, random controls, and oracle upper bounds
- Result paths: docs/PORTFOLIO_ORACLE_COMPLEMENTARITY_AUDIT.md, docs/PORTFOLIO_ORACLE_COMPLEMENTARITY_PROTOCOL.md, results/oracle_portfolio_v0_1
- Protocol hashes: e7b56d4a5c780d2e45270b203b4d8df6efd73585f0b6f34f6fb2a0ec1a3ad1fd
- Key result: BCF_NATIVE covered the same clean hard/non-easy paired instances that defeated the MAP arms, so direct per-instance oracle exact-recovery gain over always-BCF was 0 in the common envelope.
- Main failure point: Instance-level method selection value disappeared, and MAP-first sequential escalation was also not cost-effective on non-easy cells because verified exit rates stayed below measured break-even.
- Allowed claims: In the tested clean F=3 common envelope, BCF_NATIVE dominated the hard/non-easy frontier while MAP remained only an easy-cell latency path., A trivial M-threshold static route captured the only practical portfolio value observed in this stage., Current MAP-to-BCF dual-view sequential escalation was not cost-effective on clean non-easy cells.
- Forbidden claims: learned cross-substrate router justified, FPGA or Lava cascade justified, general cross-substrate complementarity across noise or other contracts
- Reopen conditions: Reopen only if a new lawful contract introduces residual verifier-preserved routing regret after the best static route.

## level3_5b_confirmatory_protocol_discipline

- Title: Held-out confirmatory execution requires prospectively frozen executable gate semantics before the first held-out observation
- Category: `NOISE_AND_PROTOCOL`
- Evidence status: `ADOPTED_ENGINEERING_BASELINE`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: How should confirmatory noise verdicts be serialized so that the held-out runner cannot invent semantics after seeing outcomes?
- Method: Protocol repair, prospective gate specification, diff audit, and contract-gate consistency repair
- Result paths: docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md, docs/LEVEL3_5B_PROSPECTIVE_GATE_SPECIFICATION.md, docs/LEVEL3_5B_CONTRACT_GATE_CONSISTENCY_REPAIR.md, results/level3_5b_protocol_repair, results/level3_5b_gate_specification, results/level3_5b_gate_consistency_repair
- Protocol hashes: 649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf
- Key result: The repo now contains an explicit rule: no confirmatory gate may be executed without prospectively frozen executable semantics.
- Main failure point: Earlier protocols blocked exactly because those semantics were missing or inconsistent.
- Allowed claims: Prospective executable gate semantics are mandatory before held-out confirmation.
- Forbidden claims: A blocked held-out run is scientific evidence for the substantive noise frontier.
- Reopen conditions: Reopen only for a new confirmatory protocol version before any corresponding held-out run.

## level3_5b_zero_trial_integrity_blocks

- Title: Runner-side integrity blocks are positive evidence for lawful non-execution when confirmatory contracts are incomplete
- Category: `NOISE_AND_PROTOCOL`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Should the runner execute anyway when confirmatory semantics are incomplete or inconsistent?
- Method: Preserved blocked held-out attempts
- Result paths: docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md, docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md, docs/LEVEL3_5B_HELDOUT_V3_NOISE_CONFIRMATION.md, results/level3_5b_heldout, results/level3_5b_heldout_v2, results/level3_5b_heldout_v3
- Protocol hashes: None recorded
- Key result: Three blocked attempts preserved zero-trial integrity instead of generating invalid outcomes.
- Main failure point: The line could not become substantive evidence without a lawful protocol.
- Allowed claims: Blocked zero-trial artifacts preserved confirmatory integrity.
- Forbidden claims: Substantive noise-frontier claims from blocked held-out runs.
- Reopen conditions: Reopen only under a new lawful protocol version before any corresponding held-out execution.

## lazy_trace_stage_a_semantic_locality

- Title: Noisy MAP semantic cues contain useful locality for retrieving a nearby creation-trace neighborhood
- Category: `SEMANTIC_TO_TRACE_ROUTING`
- Evidence status: `PARTIALLY_REPRODUCED`
- Architectural disposition: `PARTIALLY_REPRODUCED`
- Research question: Can a noisy semantic cue route to a small local trace set without global memory scan?
- Method: Random-hyperplane LSH routing, exact reranking, typed trace validation
- Result paths: docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A.md, docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A1.md, results/lazy_trace_stage_a, results/lazy_trace_stage_a1
- Protocol hashes: f9f770c7af19ad7fc5efb2d8191be116ecdccfd6d6b22f51d7c74da8c58f50ab, 3457395a278f470f9e0dd8c8a43ae2296ed0629444e8b578218231fc241f2dd6
- Key result: Stage A was partial rather than falsifying semantic locality; analytically chosen Stage A.1 configurations reached high exact-trace candidate recall under bounded candidates.
- Main failure point: Acceptance coverage and latency still lagged stronger baselines, and semantic-only routing could not resolve exact ambiguity.
- Allowed claims: Noisy MAP semantic cues contain useful locality for trace-neighborhood retrieval in the tested development envelope.
- Forbidden claims: Exact provenance from semantic similarity alone, held-out confirmation
- Reopen conditions: Reopen only for mature-index or carried-fingerprint comparisons under equal-information contracts.

## lazy_trace_stage_a2a_mature_index_shootout

- Title: At N=10k, mature exact packed search dominates the custom thin semantic router on the practical frontier
- Category: `SEMANTIC_TO_TRACE_ROUTING`
- Evidence status: `REPRODUCED_IN_REPO`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Which mature exact or ANN-style index best returns the exact associated creation trace under bounded latency, memory, and safety constraints?
- Method: Faiss exact float scan, float HNSW, exact binary scan, binary HNSW, binary multi-hash, and incumbent thin LSH
- Result paths: docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A1_ERRATUM.md, docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A2A.md, results/lazy_trace_stage_a2a
- Protocol hashes: None recorded
- Key result: Exact packed binary scan beat the tested approximate methods on the primary practical frontier at N=10k.
- Main failure point: The thin custom LSH did not remain nondominated once mature baselines were included.
- Allowed claims: A noisy MAP cue can retrieve an exact creation-trace neighborhood in a development envelope., At N=10k the adopted engineering baseline is exact packed binary scan, not the custom thin router.
- Forbidden claims: New ANN/LSH algorithm, production self-decoding memory, Stage B decoder execution
- Reopen conditions: Reopen only for scale crossover, SDM comparison, or carried-fingerprint protocols.

## first_order_trace_coactivation

- Title: First-order trace co-activation beats random routing but does not yet beat exact sidecar retrieval end-to-end
- Category: `TRACE_COACTIVATION`
- Evidence status: `PARTIALLY_REPRODUCED`
- Architectural disposition: `PARTIALLY_REPRODUCED`
- Research question: Can semantic operations create a first-order trace association whose later co-activation reduces decoder or replay search?
- Method: First-order trace atoms, optional carried capsules, semantic-to-trace bridge, and trace-free replay portfolio baseline
- Result paths: docs/LEVEL3_FIRST_ORDER_TRACE_COACTIVATION.md, results/first_order_trace_coactivation
- Protocol hashes: d541a877ee8344ebfa31ab784ef7da364ac79712cf593c169e7fbeb9e469f03b
- Key result: Co-activation beat random routing and exact capsules were the strongest narrow seam, but semantic bridge alone did not beat the equal-information sidecar baseline.
- Main failure point: Decoder-reduction benefits were not strong enough to displace the trace-free portfolio or exact sidecar baseline outright.
- Allowed claims: First-order trace co-activation is partially supported as a bounded development seam.
- Forbidden claims: Recursive history solved, full self-decoding memory, production runtime
- Reopen conditions: Reopen only for narrow carried-fingerprint refinement or scale crossover studies.

## exact_capsule_contract_closure

- Title: Carried exact trace information helps detached activation, but isolated capsule placement itself is not advantageous over a plain typed field
- Category: `EXACT_SIDE_INFORMATION`
- Evidence status: `ADOPTED_ENGINEERING_BASELINE`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Does an isolated exact capsule have any benefit over an ordinary exact field or sidecar under equal information and equal bits?
- Method: Ordinary field vs isolated capsule vs ECC capsule vs unsafe semantic fallback
- Result paths: docs/LEVEL3_EXACT_CAPSULE_CONTRACT_CLOSURE.md, results/exact_capsule_contract
- Protocol hashes: None recorded
- Key result: Plain typed exact handle survived; isolated placement did not.
- Main failure point: Fingerprint fallback and wrong-valid semantic fallback were unsafe or non-beneficial.
- Allowed claims: Carried exact trace information can help detached activation under a bounded development contract.
- Forbidden claims: Isolated capsule placement itself is scientifically beneficial.
- Reopen conditions: Reopen only if a future carried zone adds new information rather than repackaging the same exact bits.

## decoder_certified_codebook

- Title: Decoder-certified atomic admission did not show a stable causal recovery advantage over simpler controls
- Category: `ENCODER_ADAPTATION`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Does true candidate-to-decoder-score linkage produce a generalizable codebook advantage at fixed dimension and fixed candidate budget?
- Method: Random-first, distance-maxmin, decoder-certified, and shuffled-certification control
- Result paths: docs/LEVEL3_DECODER_CERTIFIED_CODEBOOK_AUDIT.md, results/decoder_certified_codebook_v0_1
- Protocol hashes: c38252c5823def1ea86454146f62b8e3c55bcec6beaf10cbf94985800734a4f1
- Key result: The line remained prototype-only and did not support a stable decoder-certified recovery advantage.
- Main failure point: Shuffled-control and simpler baselines stayed too competitive.
- Allowed claims: None beyond prototype-level directional observations.
- Forbidden claims: Generalizable decoder-certified codebook advantage.
- Reopen conditions: Do not reopen this line without a new substrate, larger power, and stronger causal controls.

## decoder_guided_tag_repair

- Title: Conflict-guided sparse tags did not justify their complexity over equal-bit extra dimensions
- Category: `REPRESENTATION_REPAIR`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Can sparse conflict-guided tags improve recovery at equal bit budget without silently leaking identities?
- Method: Base binary, random tags, shuffled conflict tags, random patch search, conflict-guided tags, equal-bit extra dimensions
- Result paths: docs/LEVEL3_DECODER_GUIDED_TAG_REPAIR_AUDIT.md, results/decoder_guided_tag_repair_v0_1
- Protocol hashes: ba57e148f752a9d77a4982c1921bab732d0c8ea4d812bb4b8d61467f69ec2c28
- Key result: Equal-bit extra dimensions dominated the tag line; the scientific advantage was not supported.
- Main failure point: Conflict-guided tags matched random or shuffled controls too closely.
- Allowed claims: None beyond the negative result.
- Forbidden claims: Conflict-guided tag repair advantage.
- Reopen conditions: Do not reopen without a new information contract clearly stronger than weak sign hints.

## self_describing_record_sidecar_closure

- Title: Exact first-order manifests safely enable recursive replay after record retrieval, but ordinary sidecar DAG remains the honest baseline
- Category: `EXACT_STRUCTURE`
- Evidence status: `ADOPTED_ENGINEERING_BASELINE`
- Architectural disposition: `ADOPTED_ENGINEERING_BASELINE`
- Research question: Is a compact exact first-order manifest safe and useful for recursive replay, and does inline packing beat ordinary sidecar storage?
- Method: Ordinary sidecar DAG, inline packed manifest, optional lazy semantic arm, and MAP factorization baseline
- Result paths: docs/LEVEL3_SELF_DESCRIBING_HYPERVECTOR_AUDIT.md, results/self_describing_record_v0_1
- Protocol hashes: a0d3674810dd041370c14da3474b3bdf976bb4a9b39a971259d6c251b2a6b69a
- Key result: Exact replay was safe and exact, but inline packed placement showed no meaningful advantage over ordinary sidecar DAG.
- Main failure point: Packaging advantage was not supported.
- Allowed claims: Exact first-order manifests can support safe recursive replay after record retrieval.
- Forbidden claims: Self-addressing from noisy semantic cue, new VSA algorithm, inline packing as proven advantage
- Reopen conditions: Reopen only if a future locator or scale study changes the sidecar vs inline trade-off.

## codebook_residue_block_lut

- Title: Block-LUT residue compression did not beat scalar residue or equal-bit extra dimensions in the tested MAP bundling envelope
- Category: `SOFT_INFORMATION`
- Evidence status: `BLOCKED_WITH_EVIDENCE`
- Architectural disposition: `BLOCKED_WITH_EVIDENCE`
- Research question: Can a small decoder-side block dictionary compress accumulator magnitudes into short tokens while keeping a better recovery-storage frontier than scalar residue or extra dimensions?
- Method: MAP-B hard, ternary tie-aware, scalar residue, block codebook C4/C16, shuffled tokens, MAP-I exact accumulator, equal-total-bit extra dimensions, raw block storage
- Result paths: docs/LEVEL3_CODEBOOK_COMPRESSED_RESIDUE_AUDIT.md, results/codebook_residue_v0_1
- Protocol hashes: dad34b84db6baa5a120cc69bf1e27d5a55d207321efa2b60670e403effc9f447
- Key result: The block dictionary line did not justify itself; equal-bit extra dimensions survived instead.
- Main failure point: Scalar or raw alternatives remained too competitive, and extra dimensions dominated the frontier.
- Allowed claims: Residue information matters; the tested block dictionary did not justify itself.
- Forbidden claims: New quantization algorithm, advantage of block dictionary compression over simpler controls in the tested envelope
- Reopen conditions: Reopen only for a clearly different soft-information substrate or mature quantization baseline.

## lazy_composite_reification

- Title: Lazy Composite Reification remains a deferred design hypothesis rather than a supported architecture result
- Category: `DEFERRED_ARCHITECTURE`
- Evidence status: `DEFERRED_HYPOTHESIS`
- Architectural disposition: `DEFERRED_HYPOTHESIS`
- Research question: Can mature concepts be reified lazily while preserving exact handles, semantic fingerprints, and safe rollback?
- Method: Documentation-only hypothesis
- Result paths: docs/research/LAZY_COMPOSITE_REIFICATION_HYPOTHESIS.md
- Protocol hashes: None recorded
- Key result: This line remains deferred pending stronger prior-art audit and closure of higher-priority held-out work.
- Main failure point: No experimental evidence yet.
- Allowed claims: Lazy Composite Reification is a deferred design hypothesis.
- Forbidden claims: Supported architecture or implementation authorization.
- Reopen conditions: Reopen only after held-out closure and a fresh anti-NIH audit.

## decode_carrying_hypervectors

- Title: Decode-Carrying Hypervectors remain a composed child hypothesis, not an established memory architecture
- Category: `DEFERRED_ARCHITECTURE`
- Evidence status: `DEFERRED_HYPOTHESIS`
- Architectural disposition: `DEFERRED_HYPOTHESIS`
- Research question: Can semantic records co-activate decode-relevant local trace metadata and trace-routing fingerprints in the same ambient representation?
- Method: Documentation-only hypothesis
- Result paths: docs/research/DECODE_CARRYING_HYPERVECTORS_HYPOTHESIS.md
- Protocol hashes: None recorded
- Key result: Only the hypothesis and anti-NIH boundaries were recorded; no implementation was authorized.
- Main failure point: Novelty, capacity, and practical benefit remain unestablished.
- Allowed claims: Decode-carrying hypervectors are a deferred hypothesis with explicit claim boundaries.
- Forbidden claims: Novel architecture confirmed, models human thought, automatic speed from same-space storage
- Reopen conditions: Reopen only after held-out closure and a dedicated prior-art audit.
