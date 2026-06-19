# Recoverability Has a Cost:

## An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures

## Abstract

This manuscript presents a bounded empirical atlas and a systematic mapping of recoverability mechanisms in Vector Symbolic Architectures (VSAs) and Hyperdimensional Computing (HDC). The central result is not a universal impossibility theorem and not a universal BCF claim. Instead, within the evaluated repository envelopes and the mapped literature, recoverability improvements consistently required an identifiable additional resource: more dimensions, more coordinate precision, more code structure, exact side information, stronger contextual priors, more inference compute, hardware state, reduced coverage through abstention, or an exact fallback. Several mechanisms preserved genuine information or improved local recovery, but many failed to create a new nondominated operating point after accounting for representation cost, compute, verification, generalization, and silent-error risk. We therefore propose a resource-aware interpretation of recoverability rather than a single-method leaderboard. [claim:claim_recoverability_resource_accounting] [claim:claim_hardware_may_change_cost_frontier_literature_only]

## 1. Introduction

The repository historically called `CGRN-HSR` has become a heterogeneous empirical record of recoverability hypotheses, reproductions, negative results, and architectural stop conditions. It is more accurate to frame it as **VSA Recoverability Atlas** than as one monolithic theory. The paper answers a narrower and more honest question than "which decoder is best?":

> Which resources pay for recoverability, which failure modes recur, and when does extra architectural complexity create or fail to create a new nondominated operating point?

The contribution is therefore a systematic mapping/scoping review plus a reproducible in-repository evidence atlas, not a numerical meta-analysis and not a new decoder.

## 2. Scope and Contributions

The paper contributes:

- a systematic mapping protocol with typed inclusion, exclusion, and comparability classes;
- a repository-wide evidence registry linking hypotheses, protocols, commits, tests, and bounded claims;
- a recoverability budget framework for locating the resource cost of each mechanism;
- a failure-mode atlas spanning both repository evidence and mapped literature;
- an architectural decision guide describing when to adopt exact side information, abstention, stronger native substrates, or stop a line entirely.

The paper does **not** claim:

- a universal impossibility theorem for VSA factorization or recoverability;
- a universal superiority result for BCF, MAP, or any other substrate;
- a production architecture;
- a measured hardware result.

## 3. Systematic Mapping Protocol

We treat the literature component as a **systematic mapping / scoping review**. The relevant papers span incompatible algebras, tasks, dimensions, noise contracts, hardware targets, and cost-reporting conventions, so a pooled meta-analysis would be misleading. The frozen protocol (`paper/SYSTEMATIC_REVIEW_PROTOCOL.md`) records:

- research questions RQ1-RQ7;
- search-source families;
- query families for VSA/HDC foundations, recovery, structured codes, precision, hardware, and abstention/portfolio work;
- typed inclusion/exclusion criteria;
- duplicate policy;
- primary-source policy;
- data-extraction schema and comparability classes.

Only `DIRECT_COMMON_HARNESS` entries are used for direct numeric ranking. All other literature is descriptive, contrastive, or hardware-contextual only.

## 4. VSA Recovery Contracts and Terminology

The atlas distinguishes:

- semantic payload versus exact structural metadata;
- approximate routing signal versus authoritative identity;
- development evidence versus held-out confirmation;
- lawful abstention versus silent wrong acceptance;
- common-harness direct comparison versus taxonomic or hardware-only comparison.

It also keeps task contracts explicit. For example, clean F=3 single-product factorization, semantic-to-trace retrieval after record creation, and exact recursive replay after record retrieval are different problems and remain distinct throughout the paper.

## 5. Recoverability Budget Framework

The paper's constructive synthesis is a non-novel but operationally useful accounting rule:

> If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always identify the original source. Reliable recovery therefore requires paying cost somewhere else.

We map that cost into the following resource ontology:

- `R1_DIMENSION`
- `R2_COORDINATE_PRECISION`
- `R3_SPARSITY_OR_BLOCK_STRUCTURE`
- `R4_STRUCTURED_CODE`
- `R5_EXACT_SIDE_INFORMATION`
- `R6_EXTERNAL_CONTEXT_OR_PRIOR`
- `R7_DECODER_COMPUTE`
- `R8_RESTARTS_OR_SEARCH`
- `R9_TEMPORAL_BUDGET`
- `R10_PHYSICAL_PARALLELISM`
- `R11_PREPROCESSING_OR_MATERIALIZATION`
- `R12_DUAL_REPRESENTATION`
- `R13_REDUCED_COVERAGE_ABSTENTION`
- `R14_EXACT_FALLBACK`

The workflow recommended by the atlas is:

`define task and risk contract -> select authoritative exact state -> choose approximate representation -> allocate dimension/precision -> select native decoder -> specify verification -> measure silent error -> add fallback only if nondominated -> abstain if budget is insufficient`

[claim:claim_recoverability_resource_accounting]

## 6. Repository Evidence Base

The repository evidence base now includes:

- MAP / resonator baselines and budget sweeps;
- context-conditioned search and selective fallback;
- official IBM BCF audits and common-envelope comparisons;
- a clean-U1 linear-code reproduction;
- exact symbolic and exact-structure baselines;
- blocked lines for decoder-certified admission, tagged repair, and block-codebook residue compression;
- protocol-discipline artifacts for noise and held-out execution.

The atlas therefore values negative results and architectural stop conditions as evidence, not as clutter.

## 7. Capacity and Dimensional Allocation

The MAP line remained a bounded baseline rather than a universal decoder. In the tested clean envelopes, MAP resonator behavior exhibited a practical intermediate region rather than unlimited factorization capacity. More dimension and more restart budget could improve recovery in some regimes, but not for free. Capacity collapse and false attractors remained recurrent failure modes once codebooks or bundle widths crossed the practical margin budget. [claim:claim_map_intermediate_region]

## 8. Structured Recovery and Native Substrates

The repository reproduced or audited several structured alternatives:

- the official IBM BCF implementation as a lawful native competitor under a scoped common contract;
- the NeCo linear-code clean-U1 paper contract under explicit GF(2) rules;
- exact symbolic baselines on clean U1.

The strongest current common-envelope result is narrow:

> In the evaluated clean F=3 common envelope, the robust native BCF arm covered the same non-easy instances that defeated all tested MAP arms. [claim:claim_bcf_dominates_clean_non_easy_f3]

This is not a universal BCF claim. It is restricted to:

- clean only;
- F=3 only;
- single product;
- known factor-specific domains;
- dual native views;
- no shared raw-noise contract.

## 9. Decoder Repair and Soft Information

Several lines explored whether weak or compressed side evidence could create a better frontier:

- decoder-certified codebook admission;
- conflict-guided tagged-symbol repair;
- block-codebook residue compression.

These lines did not support a strong architectural upgrade once equal-bit controls, generalization, certification shuffles, and silent-error safeguards were counted. The repeated pattern was not that no local signal existed, but that the extra mechanism failed to create a new nondominated operating point after full accounting. [claim:claim_decoder_repair_not_free_in_tested_envelopes]

## 10. Exact Structural Preservation

The exact-structure lines support a different conclusion from noisy factorization:

- exact first-order manifests can safely enumerate immediate operands after record retrieval;
- recursive replay can reconstruct the clean semantic result with memoization and typed failure handling;
- ordinary sidecar DAG storage is the honest engineering baseline;
- inline packing alone did not show a packaging advantage.

This is not "semantic geometry contains its own exact history." It is exact structural preservation plus deterministic replay after retrieval. [claim:claim_recursive_replay_safe_after_retrieval] [claim:claim_inline_manifest_advantage_not_supported]

## 11. Verification, Abstention, and Sequential Escalation

Verification and abstention recur across otherwise unrelated lines. The repository repeatedly found that the main safety failure is silent wrong acceptance, not mere inaccuracy. This leads to two portfolio conclusions that must remain separate.

### 11.1 Method-selection complementarity

The question here is whether different methods solve different trials in a way that justifies per-instance selection. In the clean common F=3 envelope, BCF rescued MAP failures, but MAP did not rescue BCF failures on the hard shared cells. Direct oracle exact-recovery gain over always-BCF was therefore zero. The lawful conclusion is:

> `INSTANCE_LEVEL_METHOD_SELECTION_NOT_SUPPORTED` in the tested clean F=3 envelope. [claim:claim_instance_router_not_supported_in_common_clean_envelope]

### 11.2 Sequential escalation economics

A different question is whether a cheap fast path can still be worthwhile if an expensive fallback is invoked only after verifier rejection. For a fast path `A` and fallback `B`, the simplified expected cost is:

`E[C_cascade] = C_A + (1 - p_exit) * C_B`

with break-even condition:

`p_exit > C_A / C_B`

In the measured clean non-easy common F=3 cells:

- `C_A` for `MAP_D1024_FAST` was about `0.00972 s`;
- `C_B` for `BCF_NATIVE` was about `0.03717 s`;
- break-even exit rate was therefore about `0.261`;
- actual verified exit rate was `0.25`.

So current MAP-first to BCF dual-view escalation was not cost-effective on clean non-easy cells. The only practical benefit came from a trivial cell-level threshold that sends the easy `M=10` cell to MAP and everything else to BCF. [claim:claim_current_map_bcf_escalation_not_cost_effective] [claim:claim_static_cell_route_sufficient_in_current_envelope]

This does **not** use reverse rescue as an argument against sequential early exit. Reverse rescue is irrelevant to early exit. The negative result is economic: the verified exit rate did not amortize the probe in the tested envelope.

## 12. Failure-Mode Atlas

The failure-mode atlas is central, not decorative. The recurrent modes include:

- capacity collapse;
- false attractors;
- false consensus;
- context exclusion and context misrouting;
- certification overfit;
- silent wrong acceptance;
- native substrate mismatch;
- compute non-dominance;
- storage non-dominance;
- packaging non-benefit;
- wrong-but-valid exact handles;
- dangling or stale handles;
- protocol leakage;
- dominant single-method portfolios.

Each mode is linked to:

- an observable signature;
- a mechanistic explanation;
- a resource shortfall;
- what helped;
- what failed;
- the remaining risk.

## 13. Hardware Changes the Frontier, Not the Accounting

This section is **literature synthesis only, not repository evidence**.

Hardware work suggests that the practical cost frontier may shift when recoverability is paid through:

- procedural hypervector generation;
- streaming high-dimensional computation;
- FPGA area/latency trade-offs;
- in-memory compute;
- analog or multi-bit coordinates;
- spiking or temporal local state.

The atlas therefore does not say hardware is irrelevant. It says hardware may change the frontier while leaving the accounting principle intact: the cost is still paid somewhere, just often in physical parallelism, device precision, or memory architecture instead of software-visible bytes or latency. [claim:claim_hardware_may_change_cost_frontier_literature_only]

## 14. Resource-Aware Architectural Guide

The architectural guide consolidates the current engineering advice:

- use exact first-order manifests when exact structure is already known at write time;
- use ordinary sidecar DAG storage unless inline placement shows a measured packaging win;
- treat context-conditioned search as a search controller seam, not a new algebra;
- use the dominant native substrate for the current lawful common contract;
- stop complex routing when a dominant single method or trivial static threshold already explains the gain;
- keep exact fallbacks and typed abstention when the information contract is insufficient.

## 15. Threats to Validity

The main threats are:

### Internal validity

- many positive lines remain development-only;
- some early historical runs predate today's stricter public-release framing.

### Construct validity

- task contracts vary substantially across repository stages;
- some lines test retrieval after record creation or retrieval after exact lookup rather than blind factorization.

### External validity

- the cross-substrate portfolio result is clean-only and F=3 only;
- no physical hardware measurements are present;
- synthetic recoverability tasks are not application workloads.

### Statistical conclusion validity

- several stages use modest trial counts and bounded development envelopes;
- not every negative result has a large confirmatory sample.

### Implementation fidelity

- some literature methods were audited or wrapped rather than reimplemented from scratch, by design;
- direct numeric comparison is limited to common-harness entries.

### Publication and search bias

- this is a repository-anchored systematic mapping, not an exhaustive field-wide census.

### Researcher degrees of freedom

- the same single-author program designed most repository stages, even though blocked verdicts and anti-NIH baselines were preserved.

### Hardware transfer validity

- hardware literature may shift practical costs, but not every device-level result transfers to software or CPU experiments.

## 16. Reproducibility

The paper distinguishes:

- CI validation and smoke tests;
- local unit and validator runs;
- full historical scientific reruns.

All empirical claims are tied back to:

- `paper/evidence_registry.yaml`;
- `paper/claim_ledger.yaml`;
- protocol hashes;
- concrete result directories;
- tests where locally available.

## 17. Conclusion

The repeated negative result of the atlas was not that recovery could never be improved. It was that the improvement ceased to be free once all relevant resources were counted. Within the evaluated envelopes, some mechanisms preserved real information, some improved bounded local recovery, and several were worth adopting as engineering baselines. Others failed because the same benefit could be achieved more honestly with exact structure, a stronger native substrate, extra dimensions, abstention, or a simpler static policy. That is the paper's main message. [claim:claim_recoverability_has_a_cost] [claim:claim_no_universal_impossibility_theorem]
