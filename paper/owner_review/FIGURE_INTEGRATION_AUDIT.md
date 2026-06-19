# Figure Integration Audit

## Baseline state before this stage

- Figures 1, 2, and 6 existed in `paper/figures/` but were not integrated into the manuscript body.
- Figures 3, 4, and 5 were referenced only by textual placeholders such as `### Figure 3`.
- No figure counted as manuscript-integrated merely because a file existed on disk.
- The release candidate mirrored the canonical manuscript and therefore also lacked real integrated figure links for Figures 1, 2, and 6.

## Decisions made in this stage

| Figure | Exists | Embedded in manuscript | Real image link | Caption aligned | Claim mapping aligned | Comparability class aligned | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Figure 1 | Yes | Yes | Yes | Yes | Yes | Yes | Keep in main text |
| Figure 2 | Yes | Yes | Yes | Yes | N/A | Repaired to `DESCRIPTIVE_DERIVED_SUMMARY` | Replace old atlas view with maturity summary |
| Figure 3 | Yes | Yes | Yes | Repaired | Yes | Yes | Keep in main text |
| Figure 4 | Yes | Yes | Yes | Repaired | Yes | Yes | Keep in main text |
| Figure 5 | Yes | Yes | Yes | Repaired | Narrowed to direct sequential-economics support only | Yes | Keep in main text |
| Figure 6 | Yes | No | No | Supplementary only | Yes | Yes | Move out of main text as supplementary conceptual guide |

## Duplications and semantic overlap

- Figure 1 and Figure 6 partially overlapped conceptually.
- Figure 1 now owns the main-text workflow from contract to verifier-gated accept/fallback/abstain.
- Figure 6 remains supplementary only as a branching design guide and is not cited as a separate main-text result.

## Remaining human review requirement

- Visual readability at manuscript scale still requires owner sign-off.
- Claim-to-figure directness still requires owner sign-off.
- Caption wording still requires owner sign-off.
