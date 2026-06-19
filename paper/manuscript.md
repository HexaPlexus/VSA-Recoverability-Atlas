# Recoverability Has a Cost:

## An Empirical Atlas of Factorization, Repair, and Abstention in Vector Symbolic Architectures

## Abstract

This manuscript scaffold summarizes a repository-wide empirical atlas rather than a single winning hypothesis. The central synthesis is practical rather than theorem-level: reliable recoverability was never free in the measured repository envelopes. Gains came from paying cost somewhere else: more exact structure, more bits, more dimensions, more compute, stronger routing priors, narrower task contracts, selective abstention, or exact fallback. The atlas therefore records both bounded successes and stop conditions. It does not claim a universal impossibility theorem for VSA factorization, universal superiority of any single substrate, or production readiness of the experimental lines. Instead it turns a historically single-hypothesis repository into a reproducible record of what transferred, what failed, what remained ambiguous, and what engineering baselines survived.

## 1. Introduction

The repository historically called `CGRN-HSR` began as a hypothesis about context-guided recovery in Vector Symbolic Architectures. It is no longer scientifically honest to present it as one monolithic idea. The evidence now spans:

- MAP / resonator baselines and capacity limits
- context-conditioned search and fallback
- substrate audits and paper reproductions
- noise-contract repair and confirmatory protocol discipline
- exact-structure alternatives
- soft-information and codebook experiments
- negative results and blocked lines

The public framing adopted here is therefore **VSA Recoverability Atlas**.

## 2. Recoverability Accounting Principle

The repository adopts a non-novel but operationally useful proposition:

> If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always recover the original source. Reliable recovery therefore requires paying cost somewhere else: additional stored information, stronger structural assumptions, external evidence, more search or computation, reduced coverage through abstention, or an exact fallback.

The atlas uses this proposition descriptively. It is not presented as a new theorem.

## 3. Background and Terminology

The atlas distinguishes:

- semantic payloads versus exact structural metadata
- approximate retrieval signals versus exact identity
- development evidence versus held-out confirmation
- lawful abstention versus silent wrong acceptance
- adopted baselines versus still-open research hypotheses

## 4. Research Questions

The normalized research questions across the repository are:

1. How far can blind MAP/resonator factorization be pushed before recoverability cost dominates?
2. When does context-conditioned search help more than it harms?
3. Which alternative substrates or code structures survive equal-information comparison?
4. When is exact side information simply the honest solution?
5. Which negative results genuinely close a line rather than merely fail to tune it?
6. What protocol discipline is necessary before any confirmatory noise claim becomes lawful?

## 5. Reproducibility and Protocol Discipline

The repository now treats reproducibility and protocol discipline as first-class evidence. The strongest protocol conclusion is from Level 3.5:

- noise comparisons require typed external-vs-native corruption contracts;
- confirmatory gates must be fully serialized before the first held-out observation;
- zero-trial integrity blocks are positive evidence of lawful non-execution, not administrative noise.

## 6. Baseline MAP/Resonator Results

The MAP line survived as a bounded baseline, not as a universal winner. Context-conditioned search improved over random subsets in tested Level 1 single-product settings, and Level 3.2/3.2b showed a bounded intermediate recoverability region rather than unlimited clean factorization.

## 7. Context-Conditioned Search

The strongest surviving early result is narrow: external semantic context can improve candidate routing and reduce bad commitments when:

- the task stays within a bounded contract,
- fallback remains available,
- selective acceptance remains explicit,
- the context controller is not mistaken for a new substrate.

This is a search-and-safety result, not a new VSA algebra.

## 8. Native Alternative Substrates

Three substrate conclusions matter:

- the official IBM BCF implementation can be wrapped for scoped single-product audits, but broad parity claims remain unresolved;
- the NeCo clean-U1 paper contract can be reproduced under explicit GF(2) constraints;
- on clean U1, the symbolic exact tuple baseline dominates the task envelope.

## 9. Encoder and Codebook Adaptation

Two encoder-side lines were explicitly blocked:

- decoder-certified atomic admission;
- conflict-guided tagged-symbol repair.

In both cases, the line failed because a more complicated mechanism did not survive causal or equal-bit controls strongly enough to justify architecture growth.

## 10. Representation Repair and Soft Information

The residue-plane work shows a recurring pattern in the atlas: useful information may exist, but a proposed mechanism for storing it can still lose. Soft residue information helped relative to sign-only cleanup, yet the block-LUT dictionary line lost to scalar/equal-bit controls and the surviving engineering recommendation became extra dimensions rather than a custom compressed residue plane.

## 11. Exact Structural Preservation

The strongest exact-structure conclusion is conservative:

- exact first-order manifests can safely support recursive replay after record retrieval;
- ordinary sidecar DAG storage is the honest baseline;
- inline packing did not show a packaging advantage;
- carried exact trace handles helped detached activation, but isolated capsule placement itself did not.

## 12. Noise Contracts and Safety

The atlas repeatedly converged on the same safety lesson: silent wrong recovery is the key failure mode. Typed abstention, exact verification, ambiguity handling, and explicit no-commit policies survive across otherwise unrelated lines.

## 13. Recoverability Cost Atlas

The recoverability cost matrix shows that the repository's surviving methods buy reliability through different currencies:

- more compute
- structured codes
- exact side information
- external context
- more dimensions or bits
- reduced coverage through abstention
- exact fallback

No line demonstrated free recoverability.

## 14. Failure-Mode Atlas

The failure-mode atlas includes:

- capacity collapse
- false attractors and false consensus
- context exclusion and misrouting
- certification overfit
- silent wrong acceptance
- storage and compute non-dominance
- packaging without benefit
- wrong-but-valid handles
- protocol leakage

These are not footnotes; they are the main architectural constraints.

## 15. Abstention-First Architecture

The strongest architecture recommendation the atlas can currently support is modest:

> Prefer exact or well-audited baselines, add context or approximate routing only when it demonstrably improves a bounded frontier, keep an explicit verifier, preserve abstention, and use exact fallbacks when the task contract already grants exact structural information.

## 16. Threats to Validity

Major threats remain:

- many positive lines are development-only rather than confirmatory;
- some early historical artifacts used narrower contracts than a public reader might assume;
- optional dependencies and hardware differences matter for reproduction;
- the repository contains more negative and boundary-setting evidence than final architecture wins;
- not all literature categories have yet been transferred into direct empirical baselines.

## 17. Reproducibility

The public release should distinguish:

- CI validation and smoke tests
- local unit-suite validation
- full historical scientific reruns

The paper tables should cite exact result paths, protocol hashes, and commit references through the evidence registry.

## 18. Conclusion

The atlas does not show that recoverability is impossible. It shows that recoverability is expensive, contract-dependent, and easily overclaimed. The public value of the repository is therefore not a single triumphant mechanism, but a reproducible map of what had to be paid, what failed to pay off, and where exact structure or abstention were the more honest answers.
