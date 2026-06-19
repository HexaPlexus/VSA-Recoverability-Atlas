# Recoverability Has a Cost:

## An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures

## Abstract

Vector Symbolic Architectures (VSAs) and Hyperdimensional Computing (HDC) offer compact distributed representations that support composition, cleanup, and associative computation, but the practical cost of recovering structured sources from lossy distributed states remains unevenly characterized across algebras, decoders, precision levels, and hardware assumptions. This paper combines a systematic mapping completed under a frozen search scope with a reproducible in-repository evidence atlas to study where that cost is paid. The repository component normalizes 24 hypotheses and architectural lines, including MAP resonator baselines, context-conditioned search, native structured recovery, decoder-aware repair mechanisms, exact structural side-information mechanisms, abstention policies, and multiple negative-result lines. The literature component maps recoverability mechanisms, hardware approaches, structured codes, exact side information, and temporal or spiking representations without forcing heterogeneous results into a single leaderboard. Within the evaluated envelopes, our evidence does not support a universal impossibility theorem for factorization, a universal superiority claim for BCF, or any production recommendation. It does support a resource-aware interpretation: recoverability improvements consistently required an identifiable additional resource such as more dimensions, more coordinate precision, stronger code structure, exact side information, more decoder compute, temporal state, materialization, or reduced coverage through abstention. Several mechanisms preserved genuine information or improved local recovery, yet many failed to create a new nondominated operating point after accounting for representation cost, compute, generalization, verification, and silent-error risk. We therefore propose a systems-level recoverability budget framework and an abstention-first architectural guide rather than a new decoder or a universal ranking. [claim:claim_recoverability_resource_accounting] [claim:claim_hardware_may_change_cost_frontier_literature_only] [claim:claim_no_universal_impossibility_theorem]

## 1. Introduction

Vector Symbolic Architectures and Hyperdimensional Computing are attractive because they make symbolic-like composition cheap at write time and approximate similarity cheap at read time. Random or structured high-dimensional representations can bind, bundle, permute, and compare composite states without explicitly storing every symbolic object in a conventional graph form [@plate1995hrr; @kanerva2009hyperdimensional; @kleyko2022survey_part1]. That convenience, however, creates a repeated systems question: when the stored state is lossy or superposed, what additional resource is required to recover the original factors, the intended structure, or the exact authoritative record?

The repository historically called `CGRN-HSR` accumulated partial answers to that question across several distinct lines. Some lines examined dense MAP resonator behavior under bounded compute; others examined context restriction, native structured substrates, repair mechanisms, soft evidence, trace routing, exact structural side information, or abstention. Several lines terminated with negative or blocked verdicts. Others survived only as scoped engineering baselines. The public-facing framing **VSA Recoverability Atlas** is therefore more accurate than treating the repository as a single algorithm or a single architectural hypothesis.

This manuscript does not ask which decoder is universally best. It asks a narrower and more useful question:

> Where is the cost of recoverability paid, which failure modes recur, and when does extra architectural complexity create or fail to create a new nondominated operating point?

The paper makes three contributions. First, it provides a systematic mapping of recoverability-relevant VSA/HDC literature under a frozen search scope, with typed screening, comparability classes, and a bounded transfer analysis instead of an artificial leaderboard. Second, it consolidates a reproducible repository evidence atlas containing 24 normalized hypotheses, frozen protocols, claim limits, and preserved negative results. Third, it proposes a resource-aware design framework that treats recoverability as a systems budget allocated across representation, precision, structure, exact state, compute, hardware, verification, and abstention rather than as a free emergent property of a fixed lossy embedding. [claim:claim_recoverability_has_a_cost] [claim:claim_recoverability_resource_accounting]

The manuscript is intentionally cautious. It does **not** claim a universal impossibility theorem for VSA factorization, a universal BCF superiority theorem, a production architecture, or a hardware result measured in this repository. Instead, it argues that within the evaluated envelopes, recoverability improvements ceased to be free once representation, computation, generalization, verification, and silent-error risk were counted. [claim:claim_no_universal_impossibility_theorem] [claim:claim_bcf_dominates_clean_non_easy_f3]

## 2. Scope and Terminology

The central ambiguity in recoverability discussions is that several different tasks are often conflated. This paper keeps them separate.

**Recoverability** means recovering a relevant source structure from a stored representation under an explicit information and risk contract. That source structure may be a factor tuple, a bundle member set, a typed operation contract, or an exact first-order manifest.

**Cleanup** means retrieving or denoising a stored vector or member candidate from a memory under an available similarity rule. Cleanup may be exact or approximate, and it is not automatically the same problem as blind factorization.

**Unbinding** means applying the inverse operation of a known binding algebra under assumptions about the operands or roles. In several VSA families, unbinding is lawful only when the substrate and task preserve the needed authority.

**Factorization** means recovering latent operands of a composite representation without being given their identities at read time. Factorization can be blind, context-conditioned, or natively structured.

**Exact recovery** means the recovered result matches the authoritative ground truth under the current task contract. For structure-preservation lines, the authoritative ground truth may be a typed parent reference or an immutable exact record. For blind factorization, it is usually the intended factor tuple.

**Silent wrong acceptance** means the system accepted a wrong output without surfacing uncertainty or typed failure. The atlas repeatedly treats this as the dominant safety failure because a wrong accepted output is operationally different from an abstention or a verifier rejection.

**Coverage** means the fraction of queries on which the system emits an accepted answer. Higher coverage is not automatically better when coverage is achieved by increasing silent wrong acceptance.

**Abstention** means the system chooses not to accept an answer under insufficient evidence. The repository treats abstention as a first-class systems control, not as a nuisance statistic.

**Authoritative exact state** means any exact information the system intentionally preserves because the approximate semantic view is not sufficient to reconstruct it later. Examples include typed handles, sidecar manifests, exact parent references, structured codebooks, or protocol metadata.

**Derived semantic view** means a lossy or approximate representation primarily optimized for similarity, algebraic composition, or compact storage. In the repository, the MAP semantic payload often serves as such a view.

**Native substrate** means a representation and decoder family designed together, such as the IBM BCF substrate. A native structured substrate is not just “a stronger decoder” applied to the same MAP geometry.

Four problem families are especially important not to conflate:

1. **Associative localization**: finding a nearby stored record or neighborhood.
2. **Factorization**: recovering unknown operands of a composite.
3. **Exact structural replay**: deterministically replaying structure that was explicitly preserved at write time.
4. **Channel-error correction**: correcting transmission or representation corruption under a structured code contract.

The systematic mapping found that many literature claims are strong only within one of these families and become non-transferable when moved into another. The repository evidence base follows the same discipline. [@vsa_comparison_2022; @concepts_semantic_pointers_2015; @neco_linear_codes]

## 3. Systematic Mapping Protocol

The literature component is a **systematic mapping / scoping review**, not a numerical meta-analysis. The choice is methodological rather than cosmetic. The literature spans incompatible algebras, tasks, dimensions, code structures, noise contracts, and hardware assumptions. In many cases the reported metrics are not directly commensurable, and even the definition of “recovery” varies across papers. A pooled leaderboard would therefore create more confidence than the evidence warrants.

The frozen protocol is recorded in [SYSTEMATIC_REVIEW_PROTOCOL.md](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/SYSTEMATIC_REVIEW_PROTOCOL.md). It specifies research questions, search families, search sources, inclusion and exclusion criteria, a primary-source preference, a data extraction schema, and a comparability classification. The search families covered VSA/HDC foundations, recovery and factorization, structured recovery, precision and soft information, hardware, and abstention or algorithm-selection literature. The target of the present stage was not an exhaustive field census but a defensible frozen search scope that closes obvious conceptual gaps for the manuscript.

The targeted closure pass in this stage added four families that were underdeveloped in the earlier scaffold:

- hierarchical resonator architectures and multi-level resonator decoding;
- orthogonal or partitioned representational subspaces and typed partitions;
- Loihi, Lava, and spiking VSA recovery or deployment literature;
- BCH/ECC-flavored and structured-code transfer limits.

The closure did not assume in advance that each family would produce a directly comparable positive result. In fact, part of the purpose of the closure pass was to prevent three common review mistakes. The first mistake is to cite any hierarchical or multi-stage resonator paper as if it justified arbitrary cross-substrate escalation. The second is to treat any partitioned representation as equivalent to an isolated trace or exact side-information channel. The third is to treat any error-correction result as direct evidence for blind compositional recovery. The present protocol was explicitly written to stop those transfer errors at the screening and extraction stage rather than to repair them later in prose.

Searches were logged with exact query text, date, source family, and notes in [literature_search_log.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/literature_search_log.csv). Screening outcomes were recorded in [literature_screening.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/literature_screening.csv). At the end of the closure pass, the frozen search scope contained `39` screened records, `32` included sources, and `7` excluded records. Exclusions were typed rather than ad hoc, such as `NO_COMMON_REPO_EVIDENCE`, `SECONDARY_SOURCE_WHEN_PRIMARY_EXISTS`, or `OUT_OF_SCOPE_GENERAL_ECC`.

The manuscript also includes a blinded internal re-screening pass as a consistency check. A deterministic sample covering `10` of the `39` screened records (`25.6%`) was rescreened without showing the original include/exclude decision. The rescreening procedure, disagreements, and resolutions are documented in [literature_rescreening.csv](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/literature_rescreening.csv) and [LITERATURE_SCREENING_AUDIT.md](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/LITERATURE_SCREENING_AUDIT.md). Two disagreements occurred and were resolved without changing the master table. The manuscript therefore uses the bounded wording:

> A blinded internal re-screening pass was used as a consistency check; it does not replace independent multi-reviewer screening.

Data extraction used a shared schema for representation, algebra, task contract, decoder, side information, noise contract, reported metrics, cost location, failure modes, closest repository evidence, and transfer limits. Every literature entry received a **comparability class**:

- `DIRECT_COMMON_HARNESS`
- `CLOSE_TASK_DIFFERENT_IMPLEMENTATION`
- `SAME_MECHANISM_DIFFERENT_CONTRACT`
- `TAXONOMIC_ONLY`
- `HARDWARE_ONLY`
- `THEORETICAL_ONLY`

Only `DIRECT_COMMON_HARNESS` evidence is lawful for direct numeric ranking against repository methods. In practice, the systematic mapping found that much of the literature was descriptive or taxonomic with respect to the atlas rather than directly rankable. That is a limitation of the field’s heterogeneity, not a defect in one paper. [@kleyko2022survey_part1; @kleyko2023survey_part2; @satzilla2011]

The mapping also revealed a more subtle but important asymmetry between literature and repository evidence. The repository's negative lines are often exceptionally well controlled for their local question because they were designed to kill seductive mechanisms under equal-bit, equal-information, or shuffled-score controls. Much of the literature, by contrast, is stronger on native task demonstrations, hardware execution, or architectural breadth than on cross-contract adversarial controls. That difference does not make one body of evidence “better” in the abstract. It means the manuscript should use them for different purposes: the literature to map the design space and the repository to audit costed stop conditions inside explicit contracts.

### Table 1. Resource ontology used in this manuscript

| Tag | Resource location | Typical meaning |
| --- | --- | --- |
| `R1_DIMENSION` | More coordinates | Increased representational capacity or margin budget |
| `R2_COORDINATE_PRECISION` | More bits or analog state per coordinate | Preserved soft evidence or less quantization loss |
| `R3_SPARSITY_OR_BLOCK_STRUCTURE` | Sparse or grouped coordinate organization | Reduced interference or structured evidence |
| `R4_STRUCTURED_CODE` | Code design beyond random assignment | Explicit algebraic or combinatorial constraints |
| `R5_EXACT_SIDE_INFORMATION` | Typed exact metadata or handles | Recovery authority not recoverable from geometry alone |
| `R6_EXTERNAL_CONTEXT_OR_PRIOR` | Search restriction or contextual narrowing | Reduced candidate space |
| `R7_DECODER_COMPUTE` | More iterations or stronger procedure | Higher inference cost for better recovery |
| `R8_RESTARTS_OR_SEARCH` | Multi-start or wider search | More exploration budget |
| `R9_TEMPORAL_BUDGET` | More time steps or internal state evolution | Recovery paid via temporal processing |
| `R10_PHYSICAL_PARALLELISM` | Hardware concurrency or local state | Recoverability paid through device capability |
| `R11_PREPROCESSING_OR_MATERIALIZATION` | Extra view creation or indexing | Upfront or write-time cost |
| `R12_DUAL_REPRESENTATION` | Multiple coexisting native views | Persistent storage and maintenance overhead |
| `R13_REDUCED_COVERAGE_ABSTENTION` | Refusal to answer under uncertainty | Safety paid through lower coverage |
| `R14_EXACT_FALLBACK` | Symbolic or exact recovery path | Recovery preserved by retaining a non-lossy path |

## 4. Recoverability Budget Framework

The systematic mapping and the repository evidence converge on a simple interpretation that is not claimed as a new theorem:

> If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always identify the original source. Recoverability therefore requires paying cost somewhere else.

This statement is close in spirit to familiar themes from rate–distortion, structured coding, reject-option decision theory, and algorithm portfolios, but the atlas makes it operational for VSA/HDC system design [@gray1998quantization; @chow_reject_option; @satzilla2011]. The point is not that loss is bad. Loss is often the reason the representation is useful. The point is that once the representation becomes lossy, any stronger recovery claim must explain which other resource is carrying the missing authority.

In the repository evidence, that additional authority appeared in several forms:

- more dimension in MAP codebooks or equal-bit controls;
- more precision in MAP-I or hardware-oriented multi-bit work;
- explicit structure in BCF, linear codes, or sparse block variants;
- exact structural preservation via typed sidecar manifests;
- search restriction via external context;
- increased decoder compute and restarts;
- temporal or hardware-local state in spiking or neuromorphic literature;
- abstention and verifier rejection instead of forced acceptance.

The framework therefore treats recoverability as a **budget allocation problem** rather than a decoder contest. A useful design procedure is:

`define task and risk contract -> preserve authoritative exact state -> choose approximate representation -> allocate capacity or precision -> select a native decoder -> define independent verification -> measure silent wrong acceptance -> add fallback only if it creates a nondominated point -> abstain when budget is insufficient`

This framing explains why apparently different lines in the repository often ended with similar negative results. Decoder-aware codebook admission, tagged repair, block-LUT residue compression, isolated trace capsules, and inline manifests all attempted to improve some local statistic. Several of them succeeded in preserving or exposing real information. Yet they failed the stronger engineering question: after cost, verification, generalization, and equal-information controls, did they create a new nondominated operating point? Often the answer was no. [claim:claim_recoverability_resource_accounting] [claim:claim_decoder_repair_not_free_in_tested_envelopes]

Concrete examples help. In dense MAP factorization, the extra resource was often dimension or compute: more coordinates, more restarts, or longer iteration schedules. In structured-code lines, the extra resource was native algebraic structure and its accompanying code constraints. In exact-structure lines, the extra resource was deliberate preservation of exact state at write time. In hardware literature, the extra resource was frequently temporal state, physical parallelism, or device precision that does not appear as a plain byte count in software. Once these cases are viewed through one accounting lens, the repeated manuscript theme becomes easier to evaluate and less likely to be mistaken for decoder pessimism.

### Table 2. Repository evidence overview by normalized line

| Group | Representative evidence | Current disposition |
| --- | --- | --- |
| Dense MAP factorization | `level3_2_map_budget_robustness`, `level3_2b` | Useful bounded baseline; capacity-limited |
| Context-conditioned search | `level1_context_conditioned_search` | Positive scoped seam with bounded claims |
| Native structured substrate | `level1f_bcf_selector_transfer`, `oracle_portfolio_complementarity_v0_1` | Positive only within narrow clean common envelope |
| Exact symbolic or exact structure | `level3_4_algebraic_baseline_closure`, `self_describing_record_sidecar_closure` | Adopted when exact state already exists |
| Decoder-aware repair | `decoder_certified_codebook`, `decoder_guided_tag_repair`, `codebook_residue_block_lut` | Negative or blocked after full accounting |
| Trace routing and co-activation | `lazy_trace_stage_a*`, `first_order_trace_coactivation` | Partial locality signal; practical exact baselines still stronger |
| Portfolio escalation | `oracle_portfolio_complementarity_v0_1` | Instance routing not supported in common clean envelope |
| Protocol and safety discipline | `level3_5a_noise_contract_audit`, `level3_5b_confirmatory_protocol_discipline` | Adopted repository-wide design principle |

## 5. Repository Evidence Base

The repository evidence base differs from a conventional benchmark collection in two ways. First, it treats negative results and stop decisions as first-class outputs. Second, it carries explicit protocol discipline. That discipline became necessary because early exploratory stages mixed development observations, evolving gates, and wide search freedom. Later stages repaired this by freezing gates prospectively, separating development from held-out logic, and explicitly blocking confirmatory interpretation when the protocol was not yet lawful.

The normalized evidence registry now contains `24` repository hypotheses or architectural lines. They include reproductions, adopted engineering baselines, design-only hypotheses, deferred lines, and blocked mechanisms. The atlas retains historical verdicts instead of overwriting them when a more convenient narrative appears later. This matters for public release because many of the most valuable conclusions are architectural stop conditions rather than novel positive mechanisms.

Three additional repository-wide conventions are especially important.

First, **development evidence is not promoted to universal evidence**. Several lines have development-only support with frozen scope limits but no held-out confirmation. The manuscript uses that status consistently in both prose and claim scope. [claim:claim_first_order_coactivation_partial] [claim:claim_semantic_lsh_locality]

Second, **held-out protocol discipline is itself evidence**. The atlas now treats prospective gate serialization, seed discipline, and zero-trial integrity blocks as scientific infrastructure rather than bureaucracy. If a confirmatory run would have leaked information or altered gates post hoc, the correct scientific action is to block interpretation rather than to salvage a frontier claim. [claim:claim_confirmatory_gates_must_be_prospective] [claim:claim_noise_requires_typed_contracts]

Third, **the repository is no longer one CGRN-HSR hypothesis**. It contains multiple partially overlapping questions: dense factorization, native structured recovery, exact replay after retrieval, weak repair mechanisms, and literature-only architectural ideas. The manuscript therefore presents the repository as an atlas of recoverability hypotheses and limits instead of a single monolithic theory.

This reframing also explains why repository chronology is discussed only briefly in the main text. The chronological record still matters for reproducibility and is preserved in the supplementary atlas, but chronology is a poor organizing principle for a scientific reader. The reader needs to know what classes of mechanism were tried, what authority they added, what failure modes they encountered, and why some were promoted while others were blocked. The atlas organization is therefore mechanistic rather than autobiographical.

## 6. Dimensional Capacity and Dense MAP Recovery

The dense MAP line remains an essential baseline because it tests what can be recovered without adding strong exact side information or switching to a wholly different native substrate. The common clean U1 and clean F=3 envelopes use factor-specific domains and TorchHD resonator primitives under explicit compute budgets. In these settings, MAP does not behave like a universal factorizer. It behaves like a bounded solver with a practical transition region.

The empirical story has two parts. At easier cells, such as the clean F=3 common `M=10` anchor, MAP at `D=1024` can recover exactly with low latency. That result matters because it shows the representation is not intrinsically useless. However, as domain size and search space grow, recovery deteriorates sharply. The common-envelope transition around `M=22`, `M=31`, and `M=68` exposes both capacity limits and compute sensitivity. MAP at `D=512` fails earlier than `D=1024`, while longer or restarted `D=1024` configurations partially recover some boundary cells but pay with much higher latency and more iterations. [claim:claim_map_intermediate_region]

The failure mechanism is not random bad luck. The failure atlas repeatedly shows false attractors, diffuse interference, and flattened validation geometry. The resonator can converge, but convergence does not guarantee correctness. A stronger configuration can therefore improve raw recovery while still failing to create a good cost point if the added compute and restarts outweigh the rescued cases.

The dense MAP line is especially valuable because it calibrates later claims. When a later mechanism claims to help “recovery,” the correct first question is often whether it is simply restoring resources that the dense baseline never had enough of in the first place. Equal-bit extra-dimension controls, compute-matched comparisons, and exact symbolic baselines all serve this calibrating role. In that sense, the MAP line is not only a baseline but also a diagnostic instrument for anti-NIH reasoning: if the new mechanism does not outperform “more of the old resource” under equal accounting, its interpretation must narrow.

The repository also explored equal-bit alternatives. In the block-residue line, simply spending comparable physical storage on extra binary dimensions created a stronger baseline than a more elaborate block-dictionary residue channel. That result matters beyond that one stage because it warns against attributing every marginal recovery gain to a clever new mechanism. Sometimes the real cause is the old one: more representational budget. [claim:claim_block_residue_advantage_not_supported]

### Figure 3

Figure 3 plots the clean common F=3 frontier using frozen machine-readable results. It shows exact recovery versus `M` for `MAP_D512`, `MAP_D1024`, and the native BCF arm, with trial counts and scope labels preserved in the caption. The figure is not presented as a universal substrate leaderboard. It is a compact picture of one lawful common envelope.

## 7. Context-Conditioned Search and Selective Computation

Context-conditioned search was one of the more positive repository seams, but its value is narrower than a naive reading might suggest. The basic idea is straightforward: when the search domain is large and factorization is expensive, additional contextual information or a good external narrowing policy can make the candidate set smaller before the decoder does its costly work. The repository tested oracle context, random context, query-aware context, and narrow-to-wide expansions.

The positive result is that semantic or external context can beat random candidate restriction in the tested single-product settings. Candidate recall improved, and some constrained searches reduced wasted compute. That is a real effect, not an artifact. [claim:claim_context_beats_random]

The negative result is that context benefit is not automatically an end-to-end Pareto benefit. A context seam can help only when three conditions hold at once:

1. the context retains the right candidates with high enough recall;
2. the narrowing cost does not dominate the saved decoder cost;
3. the verifier and abstention logic preserve safety.

The repository repeatedly found that context can improve a local statistic such as candidate recall without producing a better overall cost, latency, or risk point. This is why the atlas treats search control as a systems seam rather than as a new algebra or a new decoder.

The systematic mapping supports that interpretation. In broader algorithm-selection and reject-option literature, search restriction and early-exit policies are valuable only when their own cost and error modes are measured, not when they are treated as free hints [@satzilla2011; @selective_classification_survey; @chow_reject_option]. The atlas transfers that lesson conservatively: context is a prior, not a proof.

This is also the place where the manuscript most clearly separates **coverage management** from **structural recovery**. A context policy can be excellent at saying “do not even try the expensive path here,” yet still say nothing about whether the surviving path is structurally correct. Conversely, a strong structural decoder can solve hard instances while still being a poor front-end candidate selector. The repository's context work is therefore best read as a search-control contribution that must be paired with a verifier and a cost model, not as a latent proof that the semantic representation secretly preserved the missing structure.

## 8. Structured Recovery and Native Substrates

The most important positive result in the common clean F=3 envelope came from a native structured substrate rather than from a stronger MAP controller. The IBM BCF line matters because it is not just MAP with more steps. It uses a different representation and factorization contract, with native structure built into the substrate and the official implementation treated as authoritative for that line [@ibm_bcf_repo; @ibm_bcf_paper].

Within the tested clean common envelope, BCF dominated the hard or non-easy instances that defeated the MAP baselines. On the final non-easy pooled subset, the robust native BCF arm recovered every instance while the MAP arms failed on much of the same set. The lawful claim is narrow but strong:

> In the evaluated clean F=3 common envelope, the robust native BCF arm covered the same hard instances that defeated the MAP arms. [claim:claim_bcf_dominates_clean_non_easy_f3]

That claim does **not** imply universal BCF superiority. The comparison is limited to clean, single-product, factor-specific-domain tasks with dual native views and no shared raw-noise contract. It also does not imply that BCF is merely “more compute.” The substrate itself carries structure that MAP does not.

The structured-recovery section of the literature shows why that distinction matters. Sparse block and generalized sparse block code families already place recoverability cost into code structure, candidate organization, and native decoder assumptions [@factorizers_sparse_block_codes]. The NeCo linear-code reproduction likewise showed that exact recovery is possible under explicit GF(2) code constraints, but only within a sharply scoped clean contract [@neco_linear_codes]. Those lines preserve information by changing the contract, not by extracting hidden exact structure from the same old lossy representation. [claim:claim_linear_code_paper_reproduced]

The BCH/ECC closure pass makes this transfer limit even clearer. Error-correction work such as non-uniform ECC for HDC improves robustness when the task is phrased as channel-style correction under explicit code structure and correction metadata [@roodsari2025_nuecc_hdc]. That is important evidence for the recoverability budget framework, but it is **not** direct evidence for arbitrary factorization, compositional replay, or open-world recovery. The manuscript therefore keeps channel correction, structured coding, and blind factorization in separate categories.

The orthogonal-subspace closure led to a similarly bounded conclusion. True orthogonal or typed partitions in the relevant literature usually appear as part of a broader representational contract: role-specific spaces in semantic-pointer systems, staged latent-state partitions in hierarchical resonator networks, or code families whose blocks are semantically meaningful by design [@concepts_semantic_pointers_2015; @renner2022_hrn_scene]. They are not the same thing as taking an existing lossy semantic view and carving out a new exact authority channel after the fact. This matters because several blocked repository ideas were tempting precisely because they blurred that line.

The hierarchical resonator literature provides another useful contrast. Papers such as *Neuromorphic Visual Scene Understanding with Resonator Networks* and *Visual Odometry with Neuromorphic Resonator Networks* demonstrate that multi-level resonator designs can recover structured latent state when the hierarchy, temporal state, and task-specific structure are built into the model [@renner2022_hrn_scene; @renner2023_hrn_odometry]. These sources close an earlier literature gap, but they do **not** justify a lightweight heterogeneous MAP→BCF escalation narrative. Their hierarchy is endogenous to the representation and the task; it is not a post hoc portfolio controller over incompatible native substrates.

This distinction also clarifies the orthogonal-subspace and partitioning gap. The targeted search found that true partitioning mechanisms in the relevant literature usually appear either as explicit typed partitions or as task-structured representational separation inside a larger architecture, not as a free generic add-on. The conceptual proximity is real, but the transfer is limited. The atlas therefore uses that literature to motivate caution around interference isolation, not to claim that a proposed trace zone or partitioned capsule mechanism had already been validated in the repository.

### Table 3. Representative recovery mechanisms and where they pay

| Mechanism family | Representative evidence | Main added resource | Main benefit | Main transfer limit |
| --- | --- | --- | --- | --- |
| Dense MAP resonator | `level3_2`, `level3_2b` | `R1`, `R7`, `R8` | Cheap baseline and easy-cell success | Capacity-limited on harder cells |
| Native BCF substrate | `ibm_bcf_*`, `oracle_portfolio_v0_1` | `R4`, `R12` | Strong clean common-envelope recovery | Different native contract |
| Linear-code recovery | `level3_3` | `R4`, `R5` | Exact clean-U1 recovery under code constraints | Narrow algebraic envelope |
| Context-conditioned search | `level1_context_conditioned_search` | `R6`, sometimes `R13` | Candidate narrowing | Does not guarantee Pareto gain |
| Exact sidecar DAG / replay | `self_describing_record_sidecar_closure` | `R5`, `R14` | Safe exact replay after retrieval | Does not solve initial localization |
| Soft-information repair | `codebook_residue_block_lut` | `R2`, `R3`, `R11` | Genuine local signal retention | Often loses to simpler equal-bit baselines |

## 9. Decoder-Aware Codebooks and Representation Repair

One of the repository's recurring temptations was to salvage more recoverability from approximately the same substrate by adding a small repair mechanism: choose better atomic vectors, attach weak tags, compress local residue, or preserve sign-level confidence hints. These ideas were not irrational. Many of them preserve real information or expose a real local signal. The problem is that preserving a local signal is not yet the same thing as creating an engineering win.

The decoder-certified codebook line is a clean example. Its hypothesis was that atomic hypervectors might be chosen from a small candidate pool after blinded decoder-in-the-loop certification, thereby improving later factor recovery without changing the MAP algebra. The line was carefully controlled against ordinary random assignment, max-min Hamming packing, and compute-matched shuffled certification. The negative result was not that decoder-aware selection could never help any instance. It was that true candidate-to-score linkage did not create a generalizable advantage over simpler baselines under the frozen v0.1 contract. [claim:claim_decoder_certified_admission_not_supported]

The tagged repair line produced the same deeper lesson. Weak sparse tags and conflict-guided patches did expose some local reliability information, but equal-bit or simpler controls explained the measured advantage. Once cost, generalization, and silent wrong safety were counted, the line did not justify architectural promotion. [claim:claim_tagged_repair_not_supported]

The block-codebook residue line went further by explicitly preserving a compressed reliability plane for MAP bundling. That mechanism is especially important for this manuscript because it demonstrates the difference between **retained signal** and **nondominated system value**. The block-LUT residue arm retained genuine accumulator information and could outperform hard sign-only MAP-B in some local statistics. However, at equal physical bit budgets, scalar residue or plain extra dimensions either matched or beat the dictionary arm. The correct conclusion was therefore not “soft evidence is fake.” It was “this particular block dictionary did not buy enough relative to its cost and controls.” [claim:claim_block_residue_advantage_not_supported]

This distinction aligns with the literature. Quantization and multi-bit work repeatedly show that extra precision, analog state, or stored soft evidence can help [@gray1998quantization; @mimhd_2021; @fefet_multibit_2022]. The repository agrees with that general principle. What it does **not** support is a stronger claim that every compressed or indirect repair mechanism will create a new nondominated frontier once all costs are charged.

This section also clarifies why the repeated negative results should not be read as hostility toward repair. Repair is sensible when the system has already decided to store approximate views and wants to reclaim some lost evidence cheaply. The repository simply found that “cheaply” is the crucial word. If the repair channel starts to look like exact side information, a larger substrate, or a near-native structured code, then the comparison target shifts. The correct question becomes whether the repair line still beats just storing the more authoritative representation directly.

### Figure 4

Figure 4 compares comparable repair and precision arms using machine-readable repository outputs: hard MAP, scalar residue, block-LUT residue, equal-bit extra dimensions, and MAP-I exact accumulator. The figure does not rank these against unrelated literature points. It shows the local frontier and the gap between retained signal and practical engineering value inside one lawful repository contract.

### Table 4. Negative-result summary

| Line | What signal existed | Why it still failed promotion |
| --- | --- | --- |
| Decoder-certified codebook admission | Candidate-specific decoder score differences | Did not beat distance-only or shuffled compute controls on unseen evaluation |
| Conflict-guided tagged repair | Local conflict hints | Equal-bit and simpler baselines explained the gain |
| Block-codebook residue | Real soft evidence from accumulator magnitude | Lost to scalar or equal-bit dimension controls after storage accounting |
| Inline packed manifest | Packaging convenience | No packaging advantage over sidecar DAG |
| Capsule-style exact trace carriers | Additional carried exact information | Plain typed handles matched or beat the capsule under equal-information accounting |

## 10. Exact Structural Preservation

The exact-structure lines invert the basic question. Instead of asking whether a lossy semantic geometry can be forced to reveal exact structure after the fact, they ask whether exact structure that was already known at write time should simply be preserved in typed form. The answer within the repository is yes, with an important boundary: exact structure is useful **after retrieval**, not as proof of self-addressing from a noisy cue.

The self-describing record stage tested a compact first-order manifest plus recursive replay. Each composite record stores its semantic payload together with an exact first-order manifest that enumerates immediate operands and operation parameters. Read-time replay resolves the immutable parent records, memoizes repeated subgraphs, and reconstructs the clean semantic result deterministically. The main safety requirements were explicit: cycle detection, typed missing-parent failure, version mismatch, corruption detection, and refusal to silently accept wrong-but-valid handles.

The line succeeded on those safety terms. Exact first-order manifests can support safe recursive replay after retrieval. Distinct derivations can remain distinct even when their semantic payloads are identical. Shared subgraphs can be replayed once per session by memoization. Silent wrong reconstruction from malformed or stale manifests was blocked by typed failure outcomes rather than forced acceptance. [claim:claim_recursive_replay_safe_after_retrieval]

At the same time, the packaging comparison produced a negative but useful result. Physical inline placement of the manifest next to the semantic payload did not show a meaningful packaging advantage over an ordinary sidecar DAG under the tested v0.1 contract. That conclusion is scientifically honest because it rejects a seductive but unsupported aesthetic argument: co-location is not automatically information or performance. [claim:claim_inline_manifest_advantage_not_supported]

This exact-structure line matters architecturally beyond its own narrow task. It is the repository's clearest demonstration that some recoverability problems should be solved by preserving authority, not by increasing decoder cleverness. If exact parent identity was known at write time and will later matter, then the cheapest honest design may simply be to keep it. The price is explicit side information and replay cost, not magical self-description. The benefit is that the resulting system can separate exact authority from approximate semantic similarity without pretending they are the same channel.

This line also resolves a conceptual confusion that recurred in several earlier hypotheses. A compact exact manifest or typed handle is not a magical self-unbinding hypervector. It is a form of exact side information. Its value comes from preserving authority that would otherwise be unrecoverable from the lossy geometry alone. This is fully compatible with the recoverability budget framework and should not be presented as a new VSA algebra. [@merkle_dag_git; @concepts_semantic_pointers_2015]

## 11. Verification, Abstention, and Sequential Escalation

Verification and abstention are cross-cutting rather than stage-specific. The repository repeatedly found that naive accuracy comparisons hide the most important safety question: was the wrong answer silently accepted?

### 11.1 Verification as an architectural seam

The dominant repository pattern is:

`factorizer or replay path proposes -> independent verifier evaluates -> system accepts, rejects, or abstains -> commit only after verification`

This architecture appears in dense factorization, context-conditioned search, trace routing, and exact replay lines. It is not merely defensive programming. It is the mechanism that turns local decoder evidence into a typed systems outcome. Without verification, several development lines could have shown better apparent coverage only by silently accepting wrong outputs. The atlas therefore treats verifier design and typed non-commit as part of the recoverability budget, not as optional decoration. [claim:claim_noise_requires_typed_contracts]

### 11.2 Method-selection complementarity

The portfolio audit initially risked mixing two different questions. The first question is whether different methods solve different instances in a way that justifies **per-instance method selection**. In the clean common F=3 envelope, the answer was no. BCF rescued MAP failures on the hard shared cells, but MAP did not rescue BCF failures in the reverse direction. Direct oracle exact-recovery gain over always-BCF was therefore zero. The scientifically correct conclusion is:

> Instance-level cross-substrate method selection was not supported in the tested clean common F=3 envelope. [claim:claim_instance_router_not_supported_in_common_clean_envelope]

This result is stronger than “the router was not implemented.” It says there was no measured per-instance complementarity value left to justify a practical router in that envelope.

### 11.3 Sequential escalation economics

The second question is different: even without per-instance complementarity, could a cheap fast path still save cost if a stronger fallback were invoked only after verifier rejection? That is a sequential escalation problem rather than a rescue-symmetry problem.

For a fast path `A` and fallback `B`, the simplified expected cost is:

`E[C_cascade] = C_A + (1 - p_exit) C_B`

with break-even:

`p_exit > C_A / C_B`

For `MAP_D1024_FAST -> BCF_NATIVE` on the measured clean non-easy cells:

- fast-path cost was approximately `0.00972 s`;
- fallback cost was approximately `0.03717 s`;
- break-even verified exit was therefore approximately `0.261`;
- observed verified exit was `0.25`.

The cascade was therefore logically valid but not economically favorable on clean non-easy cells. This is an important nuance. The repository did **not** reject sequential escalation because MAP failed to rescue BCF. Reverse rescue is irrelevant to early exit. It rejected the current dual-view escalation because the measured verified exit rate did not compensate for the probe cost in that envelope. [claim:claim_current_map_bcf_escalation_not_cost_effective]

The only observed practical fast-path value came from a trivial cell-level threshold: use MAP on the easy `M=10` anchor where it already succeeds cheaply, and use BCF on the harder common cells. That means the lawful architectural recommendation for the current envelope is a static cell-level route, not an instance-level router. [claim:claim_static_cell_route_sufficient_in_current_envelope]

### Figure 5

Figure 5 visualizes this economics directly. It shows the actual verified exit rate, the break-even exit rate, the expected cascade cost, and the always-fallback cost. The point of the figure is not to dramatize failure; it is to make the stop condition explicit and reproducible.

## 12. Failure-Mode Atlas

The failure-mode atlas is one of the most reusable outputs of the repository because the same mechanistic patterns recur across lines that otherwise appear unrelated.

**Capacity collapse** occurs when the representational margin budget is too small relative to the search space or interference. In MAP, it appears as a sharp recovery drop beyond a transition region. In repair lines, it reappears when weak side information cannot separate heavily interfered candidates.

**False attractor** means a decoder converges confidently but to the wrong latent structure. This is especially visible in iterative dense factorization.

**False consensus** means repeated restarts or local evidence agree on the same wrong structure, creating a deceptive feeling of reliability.

**Flat validation geometry** means multiple candidates are too similar under the current approximate view, so extra computation does not create enough discriminatory evidence.

**Diffuse interference** means bundled or composed states smear evidence across too many dimensions or candidates.

**Context exclusion** and **context misrouting** occur when a narrowing prior removes the right candidate or directs search to the wrong region.

**Certification overfit** occurs when a candidate-admission or repair mechanism improves the certification workload without transferring to unseen evaluation.

**Silent wrong acceptance** is the highest-risk failure because it combines wrong recovery with false confidence.

**Substrate mismatch** occurs when a method’s native assumptions are ignored, as when a structured-code solver is treated as a drop-in MAP replacement.

**Compute non-dominance** occurs when a stronger procedure improves raw recovery but not enough to justify its compute.

**Storage non-dominance** and **packaging non-benefit** occur when the method’s added bytes or layout complexity fail to buy a better frontier.

**Wrong-but-valid exact handle** is the exact-state analog of silent wrong similarity: the reference is structurally valid but semantically wrong, so the system must still verify the recovered commitment.

**Protocol leakage** covers any path by which evaluation, seed reuse, or post hoc gate editing could contaminate a result.

**Dominant single method** is the portfolio version of non-complementarity: all hard wins come from the same arm, so there is no remaining value for an instance-level selector.

### Table 5. Failure modes, signals, and responses

| Failure mode | Observable signature | Resource shortfall | What helped | Remaining risk |
| --- | --- | --- | --- | --- |
| Capacity collapse | Recovery cliff at larger `M` or bundle width | `R1`, `R7`, sometimes `R4` | More dimension, stronger native substrate, or exact fallback | Bigger state may still be too costly |
| False attractor | Converged but wrong tuple | `R7`, `R8`, `R6` | Verification, restarts, or better native structure | Compute may still explode |
| Certification overfit | Gain on certification split only | `R11` without generalization | Shuffled controls and split discipline | Hard to spot without frozen protocol |
| Silent wrong acceptance | Wrong output accepted | `R13`, verifier weakness | Independent verification and abstention | Coverage loss |
| Storage non-dominance | Added bytes with no new frontier | `R2`, `R3`, `R5`, or `R12` spent badly | Equal-bit controls and sidecar honesty | Engineering temptation persists |
| Dominant single method | Oracle adds no gain over best fixed arm | Missing useful complementarity | Static route or stop | Over-building portfolio logic |

The full atlas, with evidence references, mitigation notes, and reopen conditions, is kept in the supplementary material rather than copied verbatim into the main text.

## 13. Hardware Changes the Frontier, Not the Accounting

This section is literature synthesis only. None of the hardware or neuromorphic sources discussed here were measured in this repository. They are **not measured in this repository** and are used only to explain how the practical frontier may shift under different physical assumptions. They matter because they change the practical price of some resources in the recoverability budget, not because they invalidate accounting.

The mapping identified several ways hardware can shift the frontier:

- procedural or rematerialized hypervector generation can reduce persistent storage at the cost of compute or timing constraints;
- FPGA acceleration can reduce latency for operations that are structurally parallel, while introducing area and implementation cost [@fach_fpga_2019];
- in-memory or multi-bit HDC can preserve precision at lower apparent software-visible cost by moving the bill into device properties [@mimhd_2021; @fefet_multibit_2022; @in_memory_hdc_review_2020];
- spiking and temporal representations can replace static per-coordinate precision with event-driven local state and time [@gosmann2016_spiking_spa; @orchard2023_spiking_phasors];
- neuromorphic resonator deployments can embed hierarchy and temporal state directly into the recovery substrate [@renner2022_hrn_scene; @renner2023_hrn_odometry];
- platforms such as Loihi 2 and official runtimes such as Lava show that temporal state and event-driven execution are concrete engineering resources, not just conceptual metaphors [@loihi2_2021; @lava_docs_2026].

The key interpretation is deliberately modest:

> Hardware may substantially change the practical price of dimension, precision, temporal state, and parallel search, but it does not remove the need to account for those resources. [claim:claim_hardware_may_change_cost_frontier_literature_only]

This section also closes the earlier Loihi/Lava gap carefully. The atlas now includes official hardware and runtime references so that the hardware discussion is not built only on secondary summaries. But those entries remain `LITERATURE_ONLY` or `HARDWARE_ONLY`. They do not authorize any measured claim about the repository itself.

The hardware synthesis is constructive rather than dismissive. The manuscript does not argue that software-visible byte counts are the only legitimate currency. On the contrary, it argues that hardware can move cost into event rates, local state, parallel execution units, memory arrays, or rematerialization logic. A reviewer who prefers hardware-efficient designs should therefore not read the budget framework as software chauvinism. The framework is intended precisely to let such designs state honestly where the cost moved.

## 14. Resource-Aware Architectural Guide

The architectural guide derived from the atlas can be summarized as a procedure rather than as a list of favorite mechanisms.

1. **Define the task and risk contract.** Is the problem exact structure replay, blind factorization, approximate lookup, or channel correction? What is the silent-error tolerance?
2. **Preserve authoritative exact state where it already exists.** If exact parent handles or structural manifests are known at write time, preserve them instead of attempting to reconstruct them later from lossy geometry.
3. **Choose an approximate representation intentionally.** Use MAP or another VSA view where associative similarity or compact composition is valuable, not as an excuse to discard authority that will later be needed.
4. **Allocate dimension and precision openly.** If recovery improves only when extra bits or extra dimensions are added, say so.
5. **Prefer native substrates for native tasks.** When structured recovery is the task, compare against native structured representations, not only against denser versions of a mismatched substrate.
6. **Define independent verification and typed abstention.** Safety should not depend on a decoder's internal confidence alone.
7. **Add fallback only if it creates a nondominated point.** Dual views, extra materialization, or escalation policies are not free.
8. **Stop lines that do not survive equal-information and equal-bit controls.**

The decision guide is intentionally conservative about escalation. A fallback or dual-view system becomes worthwhile only when there is measured value left after counting persistent storage, materialization, verification, and coverage changes. This is why the guide recommends exact fallbacks and sidecar structure in some settings but rejects gratuitous dual-view cascades in others. The rule is not “prefer exact state over distributed state” in every case. The rule is “preserve whichever authority would otherwise have to be guessed later at higher cost or higher risk.”

### Table 6. Architectural decision guide

| Situation | Recommended representation | Recovery path | Required verifier | Main cost | Evidence status |
| --- | --- | --- | --- | --- | --- |
| Known exact structure | Semantic view + exact sidecar manifest | Recursive replay after retrieval | Digest and typed handle checks | `R5`, `R14` | Supported development-only |
| Approximate semantic lookup | Compact semantic view | Exact or mature lookup baseline first | Association and ambiguity checks | `R11`, possibly `R12` | Supported narrow baseline |
| Clean single-product factorization | MAP baseline and native BCF comparator | Best lawful native decoder for the chosen substrate | Tuple verifier | `R1`, `R4`, `R7` | Supported within frozen envelopes |
| Unknown composite with no exact state | Bounded approximate representation | Factorization with abstention | Independent verifier and typed non-commit | `R7`, `R8`, `R13` | Development-only |
| Noisy symbolic channel under explicit code | Structured code + correction metadata | Correction under code contract | Code and commitment checks | `R4`, `R5` | Literature and narrow repo evidence |
| Safety-critical decision | Approximate view plus exact fallback | Verify then abstain or fallback | Strong verifier required | `R13`, `R14` | Design principle |
| Memory-constrained workspace | Prefer simplest nondominated point | Avoid dual views unless justified | Cost accounting | `R11`, `R12` | Supported by multiple negative lines |
| Hardware-limited deployment | Follow literature-only hardware transfer rules | Choose hardware-aware substrate carefully | Scope claims to measured hardware only | `R10` | Literature-only |

## 15. Threats to Validity

The paper has meaningful limitations and states them directly.

### Internal validity

Several positive lines remain development-only rather than held-out-confirmed. Early repository history also predates the current public-release and protocol-discipline standards. The atlas mitigates this by preserving historical status rather than silently upgrading it, but the limitation remains.

### Construct validity

The repository studies multiple recoverability tasks: factorization, semantic localization, exact structural replay, and repair. These are deliberately separated in the manuscript, but they are still synthetic or scoped tasks rather than one end-to-end application workload.

### External validity

The cross-substrate portfolio result is limited to clean F=3 single-product factorization with known factor-specific domains. The BCF advantage cannot be generalized to all noisy, recursive, or open-world tasks. Hardware claims are literature-only, and no physical measurement exists in this repository.

### Statistical conclusion validity

Trial counts are bounded. Some negative lines are compelling because the controls are strong, not because the sample sizes are huge. The manuscript therefore avoids universal strength claims and keeps several conclusions at development-only scope.

### Implementation fidelity

The atlas reuses authoritative implementations where possible, such as TorchHD and the official IBM BCF repository. That reduces some anti-NIH risk but does not eliminate the possibility of wrapper or interface bias.

### Search and publication bias

The systematic mapping is bounded to a frozen search scope and is not exhaustive. The internal re-screening pass improves consistency but is not independent multi-reviewer screening.

### Single-author bias

The repository and manuscript originate from one research loop. The evidence registry, claim ledger, rescreening pass, and red-team review reduce but do not remove that bias.

### Hardware transfer validity

The hardware section is explicitly literature-only. No FPGA, Loihi, Lava, or physical in-memory implementation was measured here, so the manuscript treats hardware as a frontier-shifting factor, not as repository evidence.

One additional threat cuts across several sections: **scope breadth**. The manuscript attempts to unify dimensional capacity studies, structured native substrates, repair mechanisms, exact structural preservation, portfolio semantics, and literature synthesis under one argument. That breadth is justified only because the unifying contribution is not “best decoder selection” but recoverability accounting. Readers interested in only one mechanism family may reasonably prefer more specialized papers. The manuscript addresses this by moving exhaustive matrices, hashes, and reopen conditions to the supplementary atlas rather than forcing every detail into the main text.

### Table 7. Threats and evidence limits

| Threat | Why it matters | Current mitigation |
| --- | --- | --- |
| Development-only evidence | Some promising lines were never confirmatory | Explicit claim scopes and held-out status tracking |
| Heterogeneous task contracts | Cross-paper ranking can become misleading | Comparability classes and no global meta-analysis |
| Synthetic workloads | Real applications may stress different properties | Bounded claims and architectural rather than application-level conclusions |
| Single-author screening and interpretation | Increases bias risk | Frozen protocol, internal re-screening, claim ledger, red-team review |
| No hardware measurement | Hardware conclusions could drift into speculation | Literature-only labeling and no measured hardware claims |

## 16. Reproducibility

Reproducibility is treated as part of the scientific output. The repository now exposes a public evidence atlas with:

- frozen protocol documents;
- result directories linked by normalized evidence IDs;
- a machine-readable evidence registry;
- a machine-readable claim ledger;
- prior-art and transfer registries;
- validators for registry integrity and manuscript claim resolution;
- CI smoke coverage for tests and validators;
- explicit separation between development evidence and held-out status.

Large raw artifacts remain in repository result paths when they are scientifically relevant, but the manuscript itself relies on generated summaries and figure manifests rather than manual transcription. Figures in this stage are generated from machine-readable outputs by a single script, and the figure manifest records the source data, generating script, claim IDs supported, and comparability class. The manuscript therefore aims to be inspectable end-to-end without turning the main text into an appendix of SHAs and CSV dumps.

The same discipline also explains several negative results. A blocked line is often scientifically valuable because the protocol was strong enough to show that an attractive mechanism failed either a causal control, a cost-aware comparison, or a safety constraint. In an atlas whose purpose is architectural decision support, “stop here” is a positive reproducibility outcome when it is well evidenced.

This perspective is also what makes the manuscript different from a traditional benchmark paper. The purpose is not to produce a one-line SOTA table. The purpose is to show, with traceable evidence, which kinds of added resource repeatedly mattered, which did not pay for themselves, and which lines require no further engineering until the information contract changes. That is why reproducibility infrastructure, claim ledgers, and frozen stop decisions appear in the scientific contribution rather than only in repository metadata.

## 17. Conclusion

VSA remains useful as an associative and computational representation when its contract is explicit. The evidence collected here does not support the stronger story that recoverability is a free decoder property of a fixed lossy representation. Instead, the repeated pattern is that recoverability improvements required an identifiable additional resource: more dimension, more precision, stronger structure, exact side information, stronger priors, more compute, temporal state, hardware support, or reduced coverage through abstention.

Several mechanisms did improve local recovery or preserve genuine information. That is important. The repeated negative result was not that recovery could never be improved, but that the improvement ceased to be free once representation, computation, generalization, verification, and silent-error risk were counted. [claim:claim_recoverability_has_a_cost] [claim:claim_decoder_repair_not_free_in_tested_envelopes]

Within the evaluated envelopes, the practical recommendations are therefore modest and systems-oriented. Preserve exact structure when you already know it. Use approximate semantic views where they are actually helpful. Prefer native structured substrates for native structured tasks. Keep independent verification and typed abstention. Add fallbacks only when they create a verified nondominated operating point. Stop building elegant complexity when a simpler baseline or exact side channel already dominates.

This is not a universal impossibility theorem, not a universal BCF claim, and not a production architecture. It is a reproducible argument for **recoverability accounting**: a VSA system should allocate its budget across representation, structure, computation, hardware, exact memory, and abstention, and should promote new mechanisms only when they improve the measured frontier under a lawful task contract. [claim:claim_no_universal_impossibility_theorem] [claim:claim_bcf_dominates_clean_non_easy_f3] [claim:claim_hardware_may_change_cost_frontier_literature_only]
