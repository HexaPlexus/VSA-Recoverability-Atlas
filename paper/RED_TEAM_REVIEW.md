# Internal Red-Team Review

This document records an adversarial review of the manuscript as if it were being evaluated by a skeptical reviewer. The goal is not to defend the draft but to identify the most plausible scientific attacks before external circulation.

## Overall assessment

- **Novelty:** moderate as a synthesis and evidence-atlas paper; low if misread as a new decoder paper.
- **Scientific contribution:** potentially solid if framed as a resource-accounting atlas plus bounded empirical synthesis.
- **Systematic-review rigor:** acceptable for a scoped mapping, but not exhaustive enough for broad field-finality language.
- **Experimental validity:** strongest where the repository used frozen controls and exact baselines; weaker where only development evidence exists.
- **Comparability:** improved, but still a major reviewer risk if narrative shortcuts remain.
- **Submission readiness:** not yet venue-polished; internally reviewable.

## Major criticisms

### 1. This may still read like a repository report rather than a coherent scientific paper.

- **Severity:** high
- **Affected sections:** 1, 5, 16, supplement references throughout
- **Why plausible:** the paper synthesizes a large single-author repository and includes many internal artifact references.
- **Required repair:** foreground the common contribution as recoverability accounting and keep raw provenance in supplement rather than in the main argument.
- **Needs new experiment:** no

### 2. The systematic mapping is useful but still small relative to the breadth of the field.

- **Severity:** high
- **Affected sections:** 3, 13, literature tables
- **Why plausible:** 39 screened records and 32 included sources are enough for a scoped mapping, not for an exhaustive review of all VSA/HDC recovery work.
- **Required repair:** keep “frozen search scope” wording explicit and avoid any near-exhaustive tone.
- **Needs new experiment:** no

### 3. Heterogeneous methods are still at risk of being compared unfairly.

- **Severity:** high
- **Affected sections:** 8, 9, 13
- **Why plausible:** MAP, BCF, linear codes, hardware, and exact structural replay solve different contracts and pay different costs.
- **Required repair:** repeat comparability classes where cross-family discussion occurs and avoid shared frontier language except inside common-harness figures.
- **Needs new experiment:** no

### 4. The clean F=3 common contract could still be seen as a BCF-favorable slice.

- **Severity:** medium-high
- **Affected sections:** 8, 11, conclusion
- **Why plausible:** BCF is native to structured coding and clean single-product settings.
- **Required repair:** explicitly state that the result is lawful but narrow, and avoid using it as a field-wide substrate verdict.
- **Needs new experiment:** yes, if the authors want a broader claim; no, for the current bounded paper

### 5. Development-only results remain numerous and could be overstated by synthesis.

- **Severity:** high
- **Affected sections:** abstract, 5, 9, 10
- **Why plausible:** the atlas includes negative and partial lines that were never held-out-confirmed.
- **Required repair:** keep claim-ledger scope visible in the manuscript and distinguish design principles from empirical confirmations.
- **Needs new experiment:** no, unless stronger claims are desired

### 6. The recoverability budget framework risks sounding like common sense relabeling.

- **Severity:** medium
- **Affected sections:** 4, 14, conclusion
- **Why plausible:** reviewers may say the framework merely restates that nothing is free.
- **Required repair:** emphasize that the contribution is a traceable operational accounting framework tied to concrete VSA failure modes and stop conditions, not a new theorem.
- **Needs new experiment:** no

### 7. The hardware section may still be read as speculative.

- **Severity:** medium-high
- **Affected sections:** 13
- **Why plausible:** the repository did not measure FPGA, Loihi, Lava, or in-memory systems.
- **Required repair:** keep `literature-only` labeling visually obvious and prevent any merged frontier plot between repo and literature points.
- **Needs new experiment:** yes, for any stronger hardware claim

### 8. The portfolio section is easy to misinterpret.

- **Severity:** high
- **Affected sections:** 11.2, 11.3
- **Why plausible:** method-selection complementarity and sequential escalation economics are different questions, and many readers will collapse them.
- **Required repair:** state both questions explicitly and keep the break-even logic in the paper, not just in supplement.
- **Needs new experiment:** no

### 9. Bibliography hardening is incomplete.

- **Severity:** medium
- **Affected sections:** references, hardware and implementation citations
- **Why plausible:** several entries use partial author strings or implementation-team labels.
- **Required repair:** document the limitation in the citation audit and treat it as pre-submission hardening rather than hidden polish debt.
- **Needs new experiment:** no

### 10. The paper still lacks an end-to-end user workload.

- **Severity:** medium
- **Affected sections:** threats to validity, conclusion
- **Why plausible:** the evidence consists of structured synthetic contracts rather than a subject-facing application.
- **Required repair:** treat this as an explicit external-validity limitation and avoid claims about practical AGI systems or deployed agents.
- **Needs new experiment:** yes, for broader deployment claims

## Red-team verdict

The manuscript now has one coherent contribution **if** it is read as:

> a systematic mapping plus reproducible repository evidence atlas that argues for resource-aware recoverability accounting and preserves stop decisions.

It is **not** yet safe to frame it as:

- the final word on VSA recoverability;
- a universal BCF victory;
- a new theorem;
- a comprehensive field-wide meta-analysis.
