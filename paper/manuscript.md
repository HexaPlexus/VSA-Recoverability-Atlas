# Recoverability Has a Cost:

## An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures

## Abstract

Vector Symbolic Architectures (VSAs) and Hyperdimensional Computing (HDC) support compact distributed representations, but the practical cost of recovering structured sources from lossy states remains unevenly characterized across algebras, decoders, precision regimes, and hardware assumptions. This manuscript combines a frozen systematic mapping with a repository evidence atlas to ask where that cost is paid. The atlas consolidates 24 normalized lines, while the mapping screened 39 records, retained 32 sources, and excluded 7 under pre-specified protocol rules. A blinded internal rescreening pass revisited 10 of the 39 screened records (25.6%) and resolved two disagreements without changing the master table.

The empirical picture is bounded but informative. In the clean common $F = 3$ envelope, MAP remains useful on easy cells such as the $M = 10$ anchor but degrades sharply across the transition region around $M = 22$, $M = 31$, and $M = 68$, while the robust native BCF arm covers the hard subset that defeats the MAP baselines. Sequential escalation is possible but not favorable in the measured non-easy clean cells: the observed verified MAP exit rate was $0.25$ against an approximate break-even threshold of $0.261$. Across the repository, several mechanisms preserved information or improved statistics, yet many failed to create a new nondominated operating point once representation cost, compute, verification, generalization, and silent-error risk were charged.

The main contribution is therefore not a new decoder or a universal ranking. It is a resource-aware recoverability framework: stronger recovery repeatedly required an identifiable additional resource, such as more dimensions, more coordinate precision, stronger native structure, exact side information, more decoder compute, temporal state, hardware support, or reduced coverage through abstention. The principal limitation is scope. The atlas unifies multiple recoverability tasks under explicit contracts, but several positive lines remain development-stage evidence, and hardware conclusions remain literature-only. <!-- CLAIMS: claim_recoverability_resource_accounting, claim_hardware_may_change_cost_frontier_literature_only, claim_no_universal_impossibility_theorem -->

## 1. Introduction

Vector Symbolic Architectures and Hyperdimensional Computing make composition and approximate similarity inexpensive at write time and useful at read time, but the same compression that makes them attractive also raises a systems question: when the stored state is lossy or superposed, what extra resource is required to recover the original structure with acceptable risk? [@plate1995hrr; @kanerva2009hyperdimensional; @kleyko2022survey_part1]

This paper addresses that question through two linked artifacts. The first is a bounded systematic mapping of recoverability-relevant VSA/HDC literature. The second is a repository evidence atlas that preserves both positive and negative results under frozen protocols, explicit claim boundaries, and machine-readable traceability. The central question is narrower than "which decoder is best?":

> Where is the cost of recoverability paid, which failure modes recur, and when does extra architectural complexity create or fail to create a new nondominated operating point?

The paper makes three contributions. First, it organizes the literature by recoverability task and transfer boundary rather than by a single synthetic leaderboard. Second, it consolidates 24 normalized repository lines into a reproducible atlas that retains stop conditions and negative results instead of editing them out of the narrative. Third, it proposes a resource-aware recoverability framework that treats stronger recovery as something purchased with identifiable additional resources rather than as a free property of a fixed lossy representation. <!-- CLAIMS: claim_recoverability_has_a_cost, claim_recoverability_resource_accounting -->

The paper is intentionally cautious. It does not claim a universal impossibility theorem, a universal BCF theorem, or a production architecture. It argues instead that, within the evaluated envelopes, recoverability improvements stopped being free once representation cost, compute, generalization, verification, and silent-error risk were counted. <!-- CLAIMS: claim_no_universal_impossibility_theorem, claim_bcf_dominates_clean_non_easy_f3 -->

## 2. Background and Related Work

### 2.1 Recoverability tasks

Several tasks are often conflated in recoverability discussions, and the present manuscript keeps them separate. Recovery may mean associative localization, blind factorization of unknown operands, exact structural replay after retrieval, or channel correction under an explicit code contract. These are not interchangeable. Cleanup and unbinding can be exact or approximate, but they are not automatically the same problem as blind factorization. Exact structural replay depends on preserving authority at write time, whereas blind factorization tries to infer latent structure from the stored state itself.

The paper therefore uses a narrow definition of *recoverability*: recovering the relevant source structure from a stored representation under an explicit information and risk contract. The most important safety failure is *silent wrong acceptance*, namely a wrong output accepted without surfacing uncertainty. Coverage is treated separately from exact recovery, and abstention is treated as a systems control rather than as a nuisance statistic.

### 2.2 Dense MAP and resonator networks

Dense MAP baselines matter because they test what can be recovered without stronger exact side information or a different native substrate. Existing VSA/HDC surveys establish the general write-read trade-off, while resonator-style work shows that iterative factorization can succeed when the representation, search space, and compute budget stay within a favorable envelope [@kleyko2022survey_part1; @kleyko2023survey_part2; @vsa_comparison_2022]. The repository evidence extends that point by showing a practical transition region rather than unlimited factorization capacity. <!-- CLAIMS: claim_map_intermediate_region -->

Hierarchical and resonator-based visual systems are informative for transfer boundaries. They demonstrate that structured latent recovery can work when hierarchy, temporal state, and task-specific assumptions are built into the model, but they do not justify treating heterogeneous cross-substrate escalation as if it were the same architectural object [@renner2022_hrn_scene; @renner2023_hrn_odometry].

### 2.3 Structured substrates and codes

Structured recovery changes the contract rather than extracting hidden exact structure from an unchanged lossy semantic view. This appears in linear-code HDC, sparse block code factorization, native BCF-style substrates, and channel-correction work [@ibm_bcf_paper; @neco_linear_codes; @factorizers_sparse_block_codes; @roodsari2025_nuecc_hdc]. These lines matter because they show that stronger recovery can be achieved when the representation itself carries more recoverability authority.

The central interpretive point is conservative: strong results under explicit code structure, typed partitions, or native decoders do not automatically transfer to arbitrary blind factorization. They are evidence that recoverability can be purchased by changing the representation and decoder contract.

### 2.4 Selective prediction, portfolios, and abstention

Search restriction, selective prediction, and algorithm portfolios provide a separate set of ideas: do not always ask the expensive decoder to solve the full problem when a narrower prior or abstention policy can reduce risk or cost [@satzilla2011; @selective_classification_survey; @chow_reject_option]. These lines support the present manuscript mainly as systems analogies. They explain why context restriction, verification, and abstention should be evaluated as explicit components of the overall architecture rather than as free hints that do not count in the budget.

Figure \ref{fig:workflow} provides the conceptual workflow used throughout the manuscript. It is placed before the empirical atlas so that later figures and tables can be read against the same verification-first decision contract.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/figure1_budget_map.pdf}
\caption{Recoverability workflow. Conceptual path from task and risk contract through budget allocation, representation choice, candidate generation, independent verification, and the resulting accept, fallback, or abstain outcome. This is a conceptual figure, not a measured benchmark result.}
\label{fig:workflow}
\end{figure}
\FloatBarrier
<!-- CLAIMS: claim_recoverability_resource_accounting -->

## 3. Methodology

### 3.1 Research questions

The study asks four linked questions:

1. Which recoverability tasks are actually supported by the available literature, and under what transfer boundaries?
2. Which repository mechanisms created measurable gains within their own contracts?
3. Which gains survived equal-information, equal-bit, or verification-aware controls?
4. What recurring resource trade-offs explain the surviving positive and negative results?

### 3.2 Systematic mapping protocol

The literature component is a systematic mapping rather than a pooled meta-analysis. The field spans incompatible algebras, task contracts, code structures, noise models, and hardware assumptions, so a single leaderboard would create more comparability than the evidence warrants. The frozen protocol records the search families, screening rules, extraction schema, and transfer classes in the repository materials linked from Section 9.

The bounded search scope screened 39 records, retained 32 included sources, and excluded 7 under typed criteria such as out-of-scope error-correction transfer or secondary-source replacement where a primary source existed. A blinded internal rescreening pass revisited 10 of the 39 screened records and resolved two disagreements without changing the master table. That rescreening improves consistency but does not substitute for independent multi-reviewer screening.

### 3.3 Repository evidence atlas

The repository component normalizes 24 evidence lines, including dense MAP baselines, context-conditioned search, native structured recovery, decoder-aware repair, exact structural side-information mechanisms, abstention policies, and several negative-result lines. The atlas differs from a benchmark collection in two ways. First, it treats stop conditions and negative results as first-class outputs. Second, it preserves protocol discipline explicitly rather than allowing development-stage evidence to drift into stronger claims later.

Figure 2 gives a descriptive overview of that atlas. Panel (a) shows evidence maturity, and panel (b) shows architectural disposition. The purpose is not to rank mechanisms against one another, but to show how much of the repository consists of bounded baselines, deferred hypotheses, partial reproductions, and blocked lines.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/figure2_evidence_atlas.pdf}
\caption{Repository evidence status summary. Panel (a) shows evidence maturity and panel (b) shows architectural disposition for the 24 normalized repository lines. Exact counts are printed above the bars.}
\label{fig:evidence-atlas}
\end{figure}
\FloatBarrier
<!-- CLAIMS: claim_recoverability_resource_accounting -->

### 3.4 Evidence maturity and comparability

Each literature or repository line is classified by maturity and transferability. Direct same-harness comparisons are separated from close-task comparisons, taxonomic comparisons, and hardware-only evidence. This matters because many attractive transfer stories fail precisely at this boundary: a structured-code result is not automatically evidence for blind factorization, and a hardware paper is not automatically evidence for a software-visible recoverability frontier.

### 3.5 Metrics and evaluation policy

The main metrics are exact recovery rate, accepted exact coverage, verifier-conditioned exit probability, latency, and physical storage cost where applicable. Reader-facing tables use compact labels in the main paper; the supplementary atlas preserves the full machine-readable mapping.

Table \ref{tab:resource-ontology} summarizes the resource ontology used throughout the manuscript. The framework tracks where stronger recovery is paid for instead of assuming it emerges for free.

\input{tables/resource_ontology.tex}
\FloatBarrier

## 4. Recoverability Budget Framework

The systematic mapping and the repository evidence support a common interpretation:

> If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always identify the original source. Stronger recovery must therefore draw on an additional resource.

This is not presented as a new theorem. It is an operational design lens for VSA/HDC systems. In the present atlas, the extra authority repeatedly came from more dimensions, more coordinate precision, stronger native code structure, exact side information, external context, more compute, temporal state, hardware parallelism, or reduced coverage through abstention [@gray1998quantization; @satzilla2011]. <!-- CLAIMS: claim_recoverability_resource_accounting -->

The design implication is that recoverability is a budget-allocation problem rather than a decoder contest. A system should define the task and risk contract, preserve exact authority when it is already available, choose the approximate representation intentionally, allocate capacity or precision openly, define independent verification, and add fallback only if it creates a better measured operating point.

Figure 1 summarizes this workflow. The key point is architectural: candidate outputs are not accepted directly from the decoder. They pass through an independent verifier that can still route the system to fallback or abstention.

## 5. Experimental Setup

### 5.1 Dense MAP baselines

The dense MAP baselines use factor-specific domains and fixed compute budgets to study what can be recovered from a compact semantic view without stronger native structure. The important regime for this paper is the clean common $F = 3$ envelope, where both dimensional capacity and compute sensitivity become visible.

### 5.2 Native BCF baseline

The BCF comparison is included because it represents a different native substrate rather than just a stronger iterative controller applied to the same MAP geometry. The BCF arm is therefore interpreted as a structured recovery baseline with different representational assumptions, not as a generic accelerator for all MAP-style tasks [@ibm_bcf_repo; @ibm_bcf_paper]. <!-- CLAIMS: claim_bcf_dominates_clean_non_easy_f3 -->

### 5.3 Context-conditioned search and exact side information

Context-conditioned search is evaluated as a prior over the candidate space, not as evidence that the semantic view secretly preserved exact structure. Exact structural replay is evaluated separately when typed manifests or handles are intentionally preserved at write time.

### 5.4 Repair controls and equal-information baselines

Repair mechanisms are compared against equal-bit or equal-information controls whenever possible. This avoids attributing gains to elaborate add-on mechanisms when the same gain is better explained by straightforward extra dimension, explicit exact structure, or a simpler storage format.

### 5.5 Verification, latency, and statistical treatment

Verification is treated as part of the architecture, not as a post hoc diagnostic. Let $L_A$ denote the median fast-path probe latency on the shared runtime and hardware, including the verifier work needed to accept fast-path outputs. Let $L_B$ denote the median fallback latency from invocation to verified decision once the fallback arm is called. Let $p_{\mathrm{exit}}$ denote the verified fast-path exit probability. The expected sequential latency is then

\begin{equation}
\label{eq:cascade-latency}
\mathbb{E}[L_{\mathrm{cascade}}] = L_A + \left(1 - p_{\mathrm{exit}}\right)L_B.
\end{equation}

Break-even requires

\begin{equation}
\label{eq:break-even}
p_{\mathrm{exit}} > \frac{L_A}{L_B}.
\end{equation}

Equations \eqref{eq:cascade-latency} and \eqref{eq:break-even} describe latency only. They do not include one-time materialization cost or persistent dual-representation storage cost, which are accounted for separately as architectural overhead rather than folded into the per-query latency statistic. All latency values compared in the main text come from the same machine-readable runtime summaries and use the same runtime and hardware context. <!-- CLAIMS: claim_current_map_bcf_escalation_not_cost_effective -->

## 6. Results

### 6.1 Dense MAP capacity

Dense MAP remains an essential baseline because it shows that the representation is not intrinsically useless while also exposing a practical transition region. On easy cells such as the clean common $M = 10$ anchor, MAP at $D = 1024$ can recover exactly at low latency. As the domain grows, exact recovery deteriorates sharply around $M = 22$, $M = 31$, and $M = 68$, with $D = 512$ failing earlier than $D = 1024$. The failure modes are not random; they repeatedly take the form of false attractors, diffuse interference, and flattened validation geometry. <!-- CLAIMS: claim_map_intermediate_region -->

Figure 3 presents the clean $F = 3$ frontier with trial counts and confidence intervals taken directly from the machine-readable summary.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/figure3_clean_f3_frontier.pdf}
\caption{Clean $F = 3$ capacity frontier. Exact recovery rate versus domain size $M$ for the frozen clean single-product common envelope. Error bars show the stored exact recovery confidence intervals, and the point labels preserve the underlying trial counts.}
\label{fig:clean-f3-frontier}
\end{figure}
\FloatBarrier
<!-- CLAIMS: claim_map_intermediate_region -->

### 6.2 Context-conditioned search

Context-conditioned search produced a real but narrow positive result: a good prior can improve candidate recall and reduce wasted search relative to random restriction. That is useful, but it is not the same as proving structural recovery. A context seam helps only when it retains the right candidates, does not dominate the saved compute, and remains coupled to verification and abstention. The repository therefore treats context as a systems seam rather than as a new algebra. <!-- CLAIMS: claim_context_beats_random -->

### 6.3 Native structured recovery

The strongest positive result in the shared clean common envelope came from the native BCF substrate rather than from a stronger MAP controller. On the pooled non-easy subset, the robust native BCF arm covered the same hard instances that defeated the tested MAP arms. The claim is deliberately narrow: it applies to the evaluated clean $F = 3$ common envelope and should not be generalized to unrelated noisy or open-world tasks. <!-- CLAIMS: claim_bcf_dominates_clean_non_easy_f3 -->

This result aligns with the structured-code literature. Linear-code HDC, sparse block factorization, and related native decoders show that stronger recovery can be achieved when the representational contract itself preserves more authority [@neco_linear_codes; @factorizers_sparse_block_codes]. The right interpretation is not that hidden exact structure can always be extracted from the same lossy semantic view, but that some tasks become tractable when the representation and decoder are designed together.

Table \ref{tab:mechanism-summary} uses compact mechanism labels in the main paper; the supplementary atlas preserves the full machine-readable mapping.

\input{tables/mechanism_summary.tex}
\FloatBarrier

### 6.4 Decoder-aware repair

Several repair mechanisms preserved real local signal. Decoder-certified codebook admission exposed candidate-specific score differences, conflict-guided repair exposed local conflict hints, and block-residue channels preserved soft evidence from accumulator magnitude. The repeated negative result was not that the signal was fake. It was that these mechanisms did not create a better measured operating point once equal-bit controls, verification, and generalization were counted. <!-- CLAIMS: claim_decoder_certified_admission_not_supported, claim_tagged_repair_not_supported, claim_block_residue_advantage_not_supported, claim_decoder_repair_not_free_in_tested_envelopes -->

Figure 4 shows this distinction directly. The block-residue arm retained meaningful information, but equal-bit extra dimensions and scalar residue remained stronger or equally strong engineering controls in the measured $K = 31$ cell.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/figure4_repair_costs.pdf}
\caption{Repair cost versus recall. Physical bits per bundle versus full-member enumeration recall for the comparable repair and equal-information controls in the final $K = 31$ development evaluation cell. Exact plotted values are displayed next to each method label.}
\label{fig:repair-costs}
\end{figure}
\FloatBarrier
<!-- CLAIMS: claim_block_residue_advantage_not_supported -->

Table \ref{tab:negative-results} collects negative-result lines that preserved some local signal but still failed promotion under full accounting.

\input{tables/negative_results.tex}
\FloatBarrier

### 6.5 Exact structural preservation

The exact-structure lines invert the basic question. Instead of asking whether a lossy semantic geometry can be forced to reveal exact structure after the fact, they ask whether exact structure known at write time should simply be preserved in typed form. Within the repository, the answer is yes, with an important boundary: exact side information supports safe deterministic replay after retrieval, but it is not evidence that the approximate semantic view can self-reconstruct authority it never retained. <!-- CLAIMS: claim_recursive_replay_safe_after_retrieval, claim_inline_manifest_advantage_not_supported -->

This is the clearest positive argument for preserving authority instead of trying to infer it later. Compact typed handles or manifests are useful precisely because they keep exact structure explicit rather than because they turn the semantic representation into a hidden exact archive.

### 6.6 Portfolio and escalation economics

The portfolio analysis separates two questions that are often mixed together. The first is per-instance complementarity: do different methods solve different instances in a way that justifies an instance router? In the clean common $F = 3$ envelope, the answer was no. BCF rescued hard MAP failures, but MAP did not return unique hard wins over BCF, so the measured instance-level complementarity was unsupported. <!-- CLAIMS: claim_instance_router_not_supported_in_common_clean_envelope -->

The second question is sequential economics: can a cheap fast path still save latency if it exits early on enough cases before invoking a stronger fallback? In the measured non-easy clean cells, the answer was again negative. With $L_A \approx 0.00972$ s, $L_B \approx 0.03717$ s, and $p_{\mathrm{exit}} = 0.25$, the observed fast-path exit rate stayed below the break-even threshold from Eq. \eqref{eq:break-even}. The measured benefit therefore supported a simple static route for the easy $M = 10$ cell rather than an instance-level router or a profitable MAP-first cascade on the harder common cells. <!-- CLAIMS: claim_current_map_bcf_escalation_not_cost_effective, claim_static_cell_route_sufficient_in_current_envelope -->

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/figure5_escalation.pdf}
\caption{Sequential escalation economics. Panel (a) compares the observed verified fast-path exit probability with the break-even threshold implied by Eq. \eqref{eq:break-even}. Panel (b) compares the expected cascade latency from Eq. \eqref{eq:cascade-latency} with the always-BCF baseline. The figure addresses sequential economics only.}
\label{fig:escalation}
\end{figure}
\FloatBarrier
<!-- CLAIMS: claim_current_map_bcf_escalation_not_cost_effective -->

## 7. Discussion

### 7.1 Recurrent failure modes

The same failure patterns recur across mechanisms that otherwise look different: capacity collapse, false attractors, certification overfit, silent wrong acceptance, storage non-dominance, and dominant single-method portfolios. These are not cosmetic observations; they explain why several locally promising mechanisms stopped short of architectural promotion.

Table \ref{tab:failure-modes} summarizes the most reusable failure signatures and the resource shortfalls they exposed.

\input{tables/failure_modes.tex}
\FloatBarrier

### 7.2 Resource-aware implications

The central implication of the atlas is that recoverability is not a free decoder property of a fixed lossy embedding. More exact recovery can certainly be achieved, but the cost moves somewhere identifiable: into dimensions, precision, structure, exact side information, compute, temporal state, hardware support, or reduced coverage. This is why a compact semantic view and an exact authority channel should be treated as complementary roles rather than as competitors.

### 7.3 Transfer boundaries and hardware

Hardware can change the practical frontier without removing the accounting principle. FPGA acceleration can reduce latency for operations with strong parallel structure, while in-memory and multi-bit HDC can move part of the cost into device precision, memory arrays, or local state [@fach_fpga_2019; @mimhd_2021; @fefet_multibit_2022; @in_memory_hdc_review_2020]. Spiking and neuromorphic systems similarly trade software-visible precision for event-driven state and time [@gosmann2016_spiking_spa; @orchard2023_spiking_phasors; @renner2022_hrn_scene; @renner2023_hrn_odometry; @loihi2_2021; @lava_docs_2026].

This section is literature-only. The cited hardware and platform sources are not measured in this repository. The claim is therefore limited: hardware may shift the price of recoverability resources, but it does not make those resources disappear. <!-- CLAIMS: claim_hardware_may_change_cost_frontier_literature_only -->

### 7.4 Practical guidance

Four design recommendations survive the atlas. First, preserve exact authority when it is already available and will matter later. Second, use approximate semantic views for the tasks they actually support rather than as excuses to discard authority. Third, prefer native structured substrates for native structured tasks. Fourth, keep verification and abstention explicit, and add fallback only when it improves the measured frontier rather than merely decorating the system.

## 8. Threats to Validity

The paper has meaningful limitations. Several positive lines remain development-stage evidence rather than held-out confirmation. The repository studies multiple recoverability tasks under explicit contracts, but many of those tasks are still synthetic or bounded rather than end-to-end application workloads. Trial counts are limited, and some of the strongest conclusions are persuasive because the controls are strong, not because the sample sizes are large.

External validity is also narrow by design. The BCF advantage applies to the tested clean common envelope rather than to all noisy or open-world settings. The hardware discussion is literature-only. The systematic mapping is bounded to a frozen search scope, and the internal rescreening pass does not remove single-author bias. The paper addresses these concerns by keeping claim scopes conservative, preserving negative results, and moving exhaustive machine-readable detail to the supplementary atlas rather than compressing it into stronger prose. <!-- CLAIMS: claim_confirmatory_gates_must_be_prospective, claim_noise_requires_typed_contracts -->

## 9. Reproducibility, Data, and Code Availability

Reproducibility is treated as part of the scientific contribution. The public repository snapshot contains the manuscript source, the evidence registry, the claim ledger, the prior-art registry, figure sources, and validators for registry integrity and manuscript consistency. The reader-facing main paper uses compact labels, while the supplementary atlas preserves the full machine-readable mappings, figure provenance, and protocol records.

The main entry point is the [public repository snapshot](../). Supporting machine-readable artifacts include the [evidence registry](evidence_registry.yaml), [claim ledger](claim_ledger.yaml), [figure manifest](FIGURE_MANIFEST.yaml), and [prior-art registry](prior_art_registry.yaml). These links are rewritten to commit-pinned public URLs in the reviewer preprint.

This separation is intentional. The main paper focuses on scientific interpretation, while the repository materials preserve the raw identifiers, detailed protocol chronology, and other implementation-level evidence needed for audit and reuse.

## 10. Conclusion

The evidence collected here does not support the stronger story that recoverability is a free emergent property of a fixed lossy representation. It supports a narrower and more useful conclusion: stronger recovery repeatedly required an identifiable additional resource. Some mechanisms improved local statistics or preserved genuine information, but many failed to create a new nondominated point after representation cost, compute, verification, generalization, and silent-error risk were counted. <!-- CLAIMS: claim_recoverability_has_a_cost, claim_decoder_repair_not_free_in_tested_envelopes -->

Within the evaluated envelopes, the practical guidance is therefore modest and systems-oriented. Preserve exact structure when it is already known. Use approximate semantic views where they are genuinely useful. Prefer native structured substrates for native structured tasks. Keep verification and abstention explicit. Promote new mechanisms only when they improve the measured frontier under a pre-specified task contract. <!-- CLAIMS: claim_no_universal_impossibility_theorem, claim_bcf_dominates_clean_non_easy_f3, claim_hardware_may_change_cost_frontier_literature_only -->
