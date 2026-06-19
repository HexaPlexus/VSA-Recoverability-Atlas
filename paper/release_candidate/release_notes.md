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

- bibliography is hardened for external review but not fully venue-polished
- owner identity, license, repository URL, and preprint platform decisions remain open
- dedicated history-aware secret scanning is still pending
- no stable PDF pipeline was introduced in this stage

## Recommended conversion path

If a PDF is required later, prefer a thin, reproducible conversion step from `manuscript_rc1.md` after owner metadata is finalized. Do not introduce a heavy publishing framework until the owner chooses a target venue or preprint platform.
