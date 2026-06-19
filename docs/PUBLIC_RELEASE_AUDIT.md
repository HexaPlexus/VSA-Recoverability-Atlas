# Public Release Audit

## Current Audit Verdict

`READY_AFTER_OWNER_LICENSE_DECISION`

## 1. Secrets and Credentials

- `gitleaks`: not installed in the local release-prep environment
- `trufflehog`: not installed in the local release-prep environment
- Performed:
  - `git grep` over common token/key patterns
  - `git log -G` over common secret markers
- Result:
  - no live credential exposure was found in tracked files from the patterns audited
  - keyword hits in history were explainable by documentation text, status labels, or generic words such as `token`, `secret`, or `authorization`

Current classification:

- `P2_DOCUMENT_BEFORE_PUSH`
  - secret scanning used standard local grep/log heuristics because heavyweight scanners were unavailable

## 2. Personal and Machine-Specific Information

Baseline tracked issues included:

- absolute Windows and WSL paths in historical markdown and JSON artifacts
- local virtual-environment source paths
- local conda prefix in competitor environment lock metadata

Public-release hardening policy:

- convert public documentation links to repository-relative references
- replace machine-specific paths with generic placeholders or repository-relative paths where safe
- preserve scientific meaning while removing local layout leakage

Current classification:

- `P1_SHOULD_FIX_BEFORE_PUSH` at baseline
- target state after release hardening: resolved in tracked files, with any unavoidable archival exceptions documented

## 3. Large and Inappropriate Tracked Files

The repository contains large scientific result artifacts. They are not accidental caches.

| path | role | release decision |
| --- | --- | --- |
| `results/first_order_trace_coactivation/trial_results.jsonl` | required raw scientific artifact | keep |
| `results/lazy_trace_stage_a1/trial_results.jsonl` | required raw scientific artifact | keep |
| `results/lazy_trace_stage_a2a/trial_results.jsonl` | required raw scientific artifact | keep |
| `results/level2c/heldout_trials.jsonl` | historical held-out artifact | keep |
| `results/exact_capsule_contract/trial_results.jsonl` | required raw scientific artifact | keep |
| `results/codebook_residue_v0_1/raw_trials.jsonl` | required raw scientific artifact | keep |

Recommendations:

- keep scientific raw results in the repository for now
- consider a future GitHub Release or Zenodo mirror if public hosting size becomes a practical problem
- do not silently delete or rewrite raw evidence to make the repository prettier

Current classification:

- `P2_DOCUMENT_BEFORE_PUSH`

## 4. License and Third-Party Audit

- Top-level `LICENSE`: absent at baseline
- Third-party code ownership: upstream dependencies and official repositories remain separately licensed
- Third-party notices: captured in `THIRD_PARTY_NOTICES.md`

Current classification:

- `P0_PUBLICATION_BLOCKER`
  - owner must make an explicit license decision before public push

## 5. Reproducibility Audit

Release hardening adds:

- rewritten public README
- explicit reproducibility guide
- evidence registry and validators
- CI smoke workflow

Important boundaries:

- CI validation is not a full scientific rerun
- no new VSA experiments were introduced in this stage
- frozen Level 3.5 artifacts remain unchanged

Current classification:

- `P1_SHOULD_FIX_BEFORE_PUSH` at baseline because README and public instructions were incomplete
- target state after hardening: resolved

## 6. GitHub Presentation Audit

Required public-facing files targeted in this stage:

- `README.md`
- `REPRODUCIBILITY.md`
- `RESEARCH_STATUS.md`
- `RESEARCH_HISTORY.md`
- `CITATION.cff`
- `THIRD_PARTY_NOTICES.md`
- `.github/workflows/tests.yml`

Owner-dependent file:

- `LICENSE`

## 7. Public Release Blockers

| severity | issue | status |
| --- | --- | --- |
| `P0_PUBLICATION_BLOCKER` | missing explicit top-level license | unresolved owner decision required |
| `P1_SHOULD_FIX_BEFORE_PUSH` | absolute local paths in tracked docs/results | release hardening in progress |
| `P1_SHOULD_FIX_BEFORE_PUSH` | old README unsuitable for public release | fixed in this stage |
| `P2_DOCUMENT_BEFORE_PUSH` | large raw result artifacts need explicit explanation | documented |
| `P2_DOCUMENT_BEFORE_PUSH` | local secret audit used grep/log heuristics because dedicated scanners were unavailable | documented |
| `P3_OPTIONAL_POLISH` | no issue templates or extensive community boilerplate | intentionally deferred |

## 8. Final Public-Push Condition

The repository is ready for public push only if all of the following are true:

- no known exposed secrets
- no unresolved local-path or personal-data leakage in tracked public files
- explicit owner license decision is present
- public README and reproducibility instructions are consistent with actual commands
- atlas claims match the evidence registry and claim ledger
- frozen artifacts remain unchanged

As of this audit, the expected final verdict is:

`READY_AFTER_OWNER_LICENSE_DECISION`
