# Failure-Mode Atlas

This atlas normalizes the main failure signatures observed across the repository.

## capacity_collapse

- Description: Decoder accuracy drops sharply when candidate domains or bundle width exceed the substrate's practical envelope.
- Observable signature: Recovery flattening or collapse under modest added scale despite more compute.
- Affected methods: ['MAP resonator baseline', 'bundling soft-information lines']
- How detected: Level 3.2 / 3.2b budget robustness and bundling comparisons
- What helped: more structure, exact baselines, abstention
- What failed: compute alone, warm continuation myths
- Safety consequence: Can trigger silent wrong outputs if acceptance is not gated.
- Architectural response: Prefer bounded claims, abstention, or exact fallback.
- Observed in repo: True
- Reported in literature: frady2020resonator, kleyko2022survey_part1
- Mechanistic explanation: Finite dimension, finite precision, and overlapping codebooks flatten the reconstruction landscape once interference exceeds the decoder's effective margin budget.
- Resource shortfall: R1_DIMENSION, R7_DECODER_COMPUTE
- Detection signal: Recovery flattening or collapse under modest added scale despite more compute.
- Mitigation: Increase representational budget, narrow the task contract, or abstain before silent wrong acceptance.
- Remaining risk: Can trigger silent wrong outputs if acceptance is not gated.
- Evidence refs: ['level3_2_map_budget_robustness', 'codebook_residue_block_lut']

## false_attractor

- Description: Iterative decoders settle into wrong stable states that still look internally coherent.
- Observable signature: Wrong reconstruction with apparent convergence or high self-consistency.
- Affected methods: ['MAP resonator', 'trace-free replay portfolio']
- How detected: Level 1 and Level 3 MAP analyses
- What helped: selective acceptance, verifier-backed reconstruction checks
- What failed: cheap probes and warm continuation
- Safety consequence: Raises silent wrong acceptance risk.
- Architectural response: Keep an explicit verifier and abstention.
- Observed in repo: True
- Reported in literature: frady2020resonator
- Mechanistic explanation: Iterative cleanup can settle into an energetically consistent but semantically wrong local optimum.
- Resource shortfall: R7_DECODER_COMPUTE, R13_REDUCED_COVERAGE_ABSTENTION
- Detection signal: Wrong reconstruction with apparent convergence or high self-consistency.
- Mitigation: selective acceptance, verifier-backed reconstruction checks
- Remaining risk: Raises silent wrong acceptance risk.
- Evidence refs: ['level1_context_conditioned_search', 'level3_2_map_budget_robustness']

## false_consensus

- Description: Multiple restarts or weak evidential hints agree on the same wrong answer.
- Observable signature: High apparent confidence without ground-truth recovery.
- Affected methods: ['decoder-certified admission', 'tagged-symbol repair']
- How detected: Construction and repair v0.1 lines
- What helped: shuffled controls and exact verification
- What failed: using decoder confidence as a proxy for truth
- Safety consequence: Can silently promote the wrong architecture.
- Architectural response: Demand causal controls and held-out discipline.
- Observed in repo: True
- Reported in literature: satzilla2011, selective_classification_survey
- Mechanistic explanation: Agreement among retries or weak hints is not equivalent to ground-truth recovery when all hypotheses are driven by the same distorted evidence.
- Resource shortfall: R7_DECODER_COMPUTE, R14_EXACT_FALLBACK
- Detection signal: High apparent confidence without ground-truth recovery.
- Mitigation: shuffled controls and exact verification
- Remaining risk: Can silently promote the wrong architecture.
- Evidence refs: ['decoder_certified_codebook', 'decoder_guided_tag_repair']

## context_exclusion

- Description: A context policy excludes the true candidate from the narrowed domain.
- Observable signature: Coverage falls unless broad fallback is available.
- Affected methods: ['Level 1 context routing', 'Level 2C existing matcher overlay']
- How detected: Fallback and coverage analysis
- What helped: cold broad fallback and abstention
- What failed: overconfident narrow context
- Safety consequence: False negatives or forced wrong commits.
- Architectural response: Always preserve a safe expansion path.
- Observed in repo: True
- Reported in literature: satzilla2011, chow_reject_option
- Mechanistic explanation: A routing prior narrows the candidate set so aggressively that the true factor or tuple is removed before native decoding begins.
- Resource shortfall: R6_EXTERNAL_CONTEXT_OR_PRIOR, R14_EXACT_FALLBACK
- Detection signal: Coverage falls unless broad fallback is available.
- Mitigation: cold broad fallback and abstention
- Remaining risk: False negatives or forced wrong commits.
- Evidence refs: ['level1_context_conditioned_search', 'level2c_existing_matcher_context_policy']

## context_misrouting

- Description: Context steers compute to the wrong mechanism or candidate subset.
- Observable signature: Utility gain disappears when fallback is disabled.
- Affected methods: ['Level 2A temporal retrieval', 'Level 2B controller seam']
- How detected: Temporal-memory and prior-art closures
- What helped: exact indexed retrieval and conservative authority control
- What failed: unqualified controller ambition
- Safety consequence: Wasted compute or false commit risk.
- Architectural response: Keep controller seams thin and measurable.
- Observed in repo: True
- Reported in literature: satzilla2011
- Mechanistic explanation: A controller or route prior allocates compute to the wrong mechanism, wasting budget without changing the underlying substrate error pattern.
- Resource shortfall: R6_EXTERNAL_CONTEXT_OR_PRIOR, R7_DECODER_COMPUTE
- Detection signal: Utility gain disappears when fallback is disabled.
- Mitigation: exact indexed retrieval and conservative authority control
- Remaining risk: Wasted compute or false commit risk.
- Evidence refs: ['level2a_temporal_memory_narrow', 'level2b_portable_context_controller']

## certification_overfit

- Description: A construction rule looks strong on its own certification workload but fails to generalize.
- Observable signature: Arm C improves on certification but not on validation/final development evaluation.
- Affected methods: ['decoder-certified codebook']
- How detected: Certification/evaluation split in v0.1
- What helped: shuffled-score control and old-atom regression set
- What failed: decoder-linked admission as a general recipe
- Safety consequence: Can spend large offline compute for illusory gains.
- Architectural response: Block the line unless it survives unseen evaluation and equal-risk comparison.
- Observed in repo: True
- Reported in literature: satzilla2011
- Mechanistic explanation: Construction-time selection overfits to its own certification tuples and decoder seeds instead of creating a robust new codebook point.
- Resource shortfall: R11_PREPROCESSING_OR_MATERIALIZATION, R7_DECODER_COMPUTE
- Detection signal: Arm C improves on certification but not on validation/final development evaluation.
- Mitigation: shuffled-score control and old-atom regression set
- Remaining risk: Can spend large offline compute for illusory gains.
- Evidence refs: ['decoder_certified_codebook']

## silent_wrong_acceptance

- Description: A method returns a wrong result without surfacing uncertainty or typed failure.
- Observable signature: Conditional risk among accepted outputs rises above zero.
- Affected methods: ['semantic fallbacks', 'ungated decoders', 'corrupted exact-handle paths']
- How detected: Repository-wide verifier-backed metrics
- What helped: typed validators, abstention, exact digests, ambiguity outcomes
- What failed: blind fallback and unverified top-1 acceptance
- Safety consequence: Most serious safety failure in the atlas.
- Architectural response: Favor abstention-first designs and exact verification.
- Observed in repo: True
- Reported in literature: selective_classification_survey, chow_reject_option
- Mechanistic explanation: Approximate evidence is treated as authoritative even though the information contract cannot disambiguate the true source structure.
- Resource shortfall: R13_REDUCED_COVERAGE_ABSTENTION, R14_EXACT_FALLBACK
- Detection signal: Conditional risk among accepted outputs rises above zero.
- Mitigation: typed validators, abstention, exact digests, ambiguity outcomes
- Remaining risk: Most serious safety failure in the atlas.
- Evidence refs: ['exact_capsule_contract_closure', 'self_describing_record_sidecar_closure', 'first_order_trace_coactivation']

## native_substrate_mismatch

- Description: A competitor or alternative substrate cannot satisfy the repository's task contract without changing the task.
- Observable signature: API mismatch, shared codebook where factor-specific domains are required, or incomparable noise semantics.
- Affected methods: ['HoloVec audit', 'cross-substrate noise claims']
- How detected: Level 1F and Level 3.5a audits
- What helped: anti-NIH audits and typed contract matrices
- What failed: forcing the competitor into the benchmark
- Safety consequence: False comparisons and bad architectural inference.
- Architectural response: Block or narrow claims rather than rewrite upstream methods.
- Observed in repo: True
- Reported in literature: kleyko2022survey_part1, vsa_comparison_2022
- Mechanistic explanation: Two methods may target similar symbolic tasks while relying on incompatible algebra, codebook semantics, stopping rules, or noise contracts.
- Resource shortfall: R4_STRUCTURED_CODE, R6_EXTERNAL_CONTEXT_OR_PRIOR
- Detection signal: API mismatch, shared codebook where factor-specific domains are required, or incomparable noise semantics.
- Mitigation: anti-NIH audits and typed contract matrices
- Remaining risk: False comparisons and bad architectural inference.
- Evidence refs: ['level1f_holovec_task_mismatch', 'level3_5a_noise_contract_audit']

## compute_non_dominance

- Description: A more complicated method adds compute but fails to create a better recovery-risk frontier.
- Observable signature: Shuffled controls or exact baselines match the more complex method.
- Affected methods: ['decoder-certified codebook', 'tagged repair', 'thin LSH at N=10k']
- How detected: Equal-budget controls and mature baseline shootouts
- What helped: equal-information, equal-bit, and equal-candidate controls
- What failed: complex construction or routing alone
- Safety consequence: Wasted engineering effort and misleading optimization.
- Architectural response: Prefer simpler adopted baselines when the frontier is dominated.
- Observed in repo: True
- Reported in literature: satzilla2011, gray1998quantization
- Mechanistic explanation: Extra compute or tuning explores more hypotheses but fails to move the verified frontier once strong simpler baselines are matched.
- Resource shortfall: R7_DECODER_COMPUTE, R11_PREPROCESSING_OR_MATERIALIZATION
- Detection signal: Shuffled controls or exact baselines match the more complex method.
- Mitigation: equal-information, equal-bit, and equal-candidate controls
- Remaining risk: Wasted engineering effort and misleading optimization.
- Evidence refs: ['decoder_certified_codebook', 'decoder_guided_tag_repair', 'lazy_trace_stage_a2a_mature_index_shootout']

## storage_non_dominance

- Description: A compressed or packed representation adds storage complexity without creating a better recovery-storage point.
- Observable signature: Equal-bit extra dimensions or ordinary sidecar storage dominates.
- Affected methods: ['block residue codebook', 'inline manifest packing']
- How detected: Equal-bit and sidecar-vs-inline controls
- What helped: physical bit accounting and deployable-byte accounting
- What failed: compression or packing aesthetics alone
- Safety consequence: Bigger artifact and maintenance burden without scientific benefit.
- Architectural response: Adopt simpler storage when packaging advantage is not measured.
- Observed in repo: True
- Reported in literature: gray1998quantization, jegou2011pq
- Mechanistic explanation: Compressed or packed structure increases byte complexity without preserving enough additional signal to beat equal-rate alternatives.
- Resource shortfall: R2_COORDINATE_PRECISION, R11_PREPROCESSING_OR_MATERIALIZATION
- Detection signal: Equal-bit extra dimensions or ordinary sidecar storage dominates.
- Mitigation: physical bit accounting and deployable-byte accounting
- Remaining risk: Bigger artifact and maintenance burden without scientific benefit.
- Evidence refs: ['codebook_residue_block_lut', 'self_describing_record_sidecar_closure']

## packaging_non_benefit

- Description: A new physical packing layout does not create any information advantage over an ordinary sidecar.
- Observable signature: Sidecar and inline packed variants have equal logical behavior and similar bytes/latency.
- Affected methods: ['inline packed manifest', 'isolated exact capsule']
- How detected: Equal-information placement tests
- What helped: ordinary sidecar baselines
- What failed: same bits in a new physical wrapper
- Safety consequence: Can fuel architecture fiction without added capability.
- Architectural response: Say plainly that packaging alone is not a scientific result.
- Observed in repo: True
- Reported in literature: merkle_dag_git
- Mechanistic explanation: Changing physical colocation without changing the information contract cannot create new recoverability by itself.
- Resource shortfall: R5_EXACT_SIDE_INFORMATION
- Detection signal: Sidecar and inline packed variants have equal logical behavior and similar bytes/latency.
- Mitigation: ordinary sidecar baselines
- Remaining risk: Can fuel architecture fiction without added capability.
- Evidence refs: ['self_describing_record_sidecar_closure', 'exact_capsule_contract_closure']

## wrong_but_valid_exact_handle

- Description: An exact-looking operand or trace handle points to a real but wrong record.
- Observable signature: Manifest or capsule decodes structurally, but replay digest mismatches or provenance becomes inconsistent.
- Affected methods: ['self-describing record', 'exact capsule closure']
- How detected: Wrong-valid handle and wrong-valid capsule corruption tests
- What helped: semantic commitment digests, record-association checks, typed failure codes
- What failed: trusting structure without verification
- Safety consequence: Potential silent false provenance if unguarded.
- Architectural response: Require verification against committed semantics or exact digests.
- Observed in repo: True
- Reported in literature: merkle_dag_git
- Mechanistic explanation: An exact-looking pointer is still unsafe if record association and semantic commitment are not independently verified.
- Resource shortfall: R5_EXACT_SIDE_INFORMATION, R14_EXACT_FALLBACK
- Detection signal: Manifest or capsule decodes structurally, but replay digest mismatches or provenance becomes inconsistent.
- Mitigation: semantic commitment digests, record-association checks, typed failure codes
- Remaining risk: Potential silent false provenance if unguarded.
- Evidence refs: ['self_describing_record_sidecar_closure', 'exact_capsule_contract_closure']

## dangling_or_stale_handle

- Description: A manifest references a missing parent or an outdated version.
- Observable signature: Typed failure such as DANGLING_OPERAND_REF or PARENT_VERSION_MISMATCH.
- Affected methods: ['self-describing record', 'future lazy reification hypotheses']
- How detected: Manifest corruption and version tests
- What helped: immutable/versioned record identities and transactional commit
- What failed: assuming exact handles are self-healing
- Safety consequence: Replay cannot continue and must not fabricate history.
- Architectural response: Prefer explicit typed fallback over silent partial reconstruction.
- Observed in repo: True
- Reported in literature: merkle_dag_git
- Mechanistic explanation: Exact structure preserves only what still exists and remains version-compatible in the authoritative store.
- Resource shortfall: R5_EXACT_SIDE_INFORMATION, R11_PREPROCESSING_OR_MATERIALIZATION
- Detection signal: Typed failure such as DANGLING_OPERAND_REF or PARENT_VERSION_MISMATCH.
- Mitigation: immutable/versioned record identities and transactional commit
- Remaining risk: Replay cannot continue and must not fabricate history.
- Evidence refs: ['self_describing_record_sidecar_closure']

## protocol_leakage

- Description: Confirmatory logic is changed after seeing development or held-out outcomes.
- Observable signature: Blocked runner, missing gate semantics, or unauthorized protocol diffs.
- Affected methods: ['Level 3.5 protocol lines']
- How detected: Gate-source audits, diff allowlists, zero-trial integrity blocks
- What helped: prospective executable gate serialization and validator coverage
- What failed: implicit verdict labels and post-hoc threshold invention
- Safety consequence: Invalid confirmatory claims.
- Architectural response: Fail closed and preserve immutable block evidence.
- Observed in repo: True
- Reported in literature: selective_classification_survey
- Mechanistic explanation: Post-hoc gate changes erase the boundary between exploratory tuning and confirmatory evaluation.
- Resource shortfall: R11_PREPROCESSING_OR_MATERIALIZATION
- Detection signal: Blocked runner, missing gate semantics, or unauthorized protocol diffs.
- Mitigation: prospective executable gate serialization and validator coverage
- Remaining risk: Invalid confirmatory claims.
- Evidence refs: ['level3_5a_noise_contract_audit', 'level3_5b_confirmatory_protocol_discipline', 'level3_5b_zero_trial_integrity_blocks']

## dominant_single_method

- Description: A prospective portfolio shows pairwise rescues among weaker methods, but one lawful method already covers the hard instances, erasing practical oracle gain.
- Observable signature: Direct oracle and verifier-constrained oracle match the best single method on hard/non-easy cells, while static routing captures any residual easy-cell latency trim.
- Affected methods: ['cross-substrate portfolio audits', 'prospective cascades']
- How detected: Paired clean F=3 complementarity audit with best-single, oracle, cascade, and static-route analyses
- What helped: paired trial matrices, verifier-constrained oracle, hard-cell pooling
- What failed: learned-router or hardware escalation before residual routing regret exists
- Safety consequence: Can rationalize unnecessary routing complexity while adding no verified coverage.
- Architectural response: Adopt the dominant single method or trivial static threshold and stop the router line.
- Observed in repo: True
- Reported in literature: satzilla2011
- Mechanistic explanation: Pairwise rescue among weaker methods is irrelevant if one lawful method already covers the hard instances where routing was supposed to help.
- Resource shortfall: R12_DUAL_REPRESENTATION, R7_DECODER_COMPUTE
- Detection signal: Direct oracle and verifier-constrained oracle match the best single method on hard/non-easy cells, while static routing captures any residual easy-cell latency trim.
- Mitigation: paired trial matrices, verifier-constrained oracle, hard-cell pooling
- Remaining risk: Can rationalize unnecessary routing complexity while adding no verified coverage.
- Evidence refs: ['oracle_portfolio_complementarity_v0_1']
