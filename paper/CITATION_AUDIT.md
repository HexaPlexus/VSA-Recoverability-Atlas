# Citation Audit

## Scope

This audit checks citation traceability for the full manuscript draft, not venue-specific bibliography styling. The goals are:

- every literature-derived factual statement in the manuscript uses a citation key;
- every citation key resolves in both [prior_art_registry.yaml](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/prior_art_registry.yaml) and [references.bib](/C:/Users/Thanatos/Desktop/CGRN-HSR/paper/references.bib);
- official documentation and hardware-only sources are explicitly labeled as such rather than used as if they were common-harness empirical results.

## Current counts

- Manuscript inline citation mentions: `39`
- Unique citation keys used in manuscript: `26`
- Unique cited keys resolving in prior-art registry: `26 / 26`
- Unique cited keys resolving in bibliography: `26 / 26`
- Literature screening records: `39`
- Included sources in frozen search scope: `32`

## Checks performed

1. Duplicate or missing citation keys.
2. Missing bibliography entries.
3. Citation keys present in bibliography but absent from the prior-art registry.
4. Hardware statements supported only by hardware-only or literature-only sources.
5. Secondary-source use where a primary paper or official implementation source was available.

## Outcome

The draft passes key-resolution traceability: every citation key used in `paper/manuscript.md` resolves in both the bibliography and the prior-art registry.

## Remaining hardening items

The current draft is adequate for internal and friendly external scientific review, but several bibliography entries still need owner/editor hardening before formal submission:

- some non-core entries use repository-frozen shorthand author strings such as `authors`, `collaborators`, or implementation-team labels rather than fully normalized venue metadata;
- official repository and documentation entries are represented as `@software`, `@misc`, or `@online` records and may need venue-specific normalization;
- several URLs should be replaced by DOI or publisher landing pages if the target venue prefers those formats.

These are editorial completeness issues, not broken citation links.

## Scope guard

The citation system supports the manuscript's bounded claims. It does **not** convert literature-only hardware or ECC-transfer sources into common-harness empirical evidence.
