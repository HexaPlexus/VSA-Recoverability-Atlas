---
packet_id: BCF_GSBC_REVIEW
manuscript_sections:
  - "8. Structured Recovery and Native Substrates"
  - "11. Verification, Abstention, and Sequential Escalation"
  - "17. Conclusion"
---

# Packet B: BCF / GSBC / Structured Factorization Review

## Reviewer profile

This packet is for readers who know BCF, GSBC, sparse block or structured-code factorization, or native structured HDC substrates.

## Sections to review

- Section 8: structured recovery and native substrates
- Section 11.2: method-selection complementarity
- Section 11.3: sequential escalation economics
- conclusion paragraphs that summarize the BCF result

## What the manuscript currently claims

- In the evaluated clean common F=3 envelope, the robust native BCF arm covered the same hard instances that defeated the MAP arms.
- This does not justify universal BCF superiority.
- The repository does not show useful per-instance MAP-versus-BCF method-selection complementarity in that envelope.
- A MAP-first probe followed by BCF fallback was not cost-effective on the non-easy cells because the fast-path verified exit rate was too low.

## Key repository anchors

- `ibm_bcf_repo`
- `ibm_bcf_paper`
- `oracle_portfolio_complementarity_v0_1`
- `level3_3_neco_reproduction`

## Specific questions

1. Is BCF technically described correctly as a native substrate rather than "just a better decoder"?
2. Does the manuscript clearly separate BCF from dense MAP resonator baselines?
3. Is the clean F=3 common-envelope comparison fair and bounded tightly enough?
4. Are native-substrate limitations explicit enough, especially around noise, recursion, and generality?
5. Does any sentence still imply universal superiority or a transfer claim the evidence does not support?

## Compact extract

The BCF claim is intentionally narrow: it is strong inside one lawful common clean F=3 envelope and should not be generalized into a broad cross-substrate theorem. The portfolio subsection further argues that this same hard-cell dominance removes the motivation for an instance-level router in that envelope.
