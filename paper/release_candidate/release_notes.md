# Release Candidate Notes

## Package identity

- Package: `external-review-rc1`
- Source manuscript: `paper/manuscript.md`
- Branch intent: external technical review only

## What this package is for

- specialist section review
- bibliography and claim-scope review
- preprint-readiness editing
- venue-neutral technical feedback

## What this package is not for

- public repository launch
- automated outreach
- new experiments
- revised scientific claims beyond the current evidence atlas

## Known boundaries

- bibliography is substantially hardened but still needs final owner visual review
- the publication PDF pipeline now uses Pandoc, Tectonic, and deterministic qpdf normalization
- owner preprint-platform and venue decisions remain open
- dedicated history-aware secret scanning is still pending
- no public upload or outreach action was performed in this stage

## Recommended conversion path

The canonical reviewer PDF is built from `paper/manuscript.md` through the publication pipeline in `scripts/build_manuscript.py`. The release-candidate markdown bundle remains useful for technical review and source inspection before venue-specific packaging.
