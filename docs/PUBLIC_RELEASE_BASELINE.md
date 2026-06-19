# Public Release Baseline

This document records the initial forensic snapshot captured before public-release hardening work began.

## Snapshot

- Original historical project name: `CGRN-HSR`
- Public target name: `VSA Recoverability Atlas`
- HEAD before release stage: `85b5334bcfeb0119ac2b786c7a0c6743bca3b57e`
- Branch before release stage: `codex/codebook-residue-v0_1`
- Working branch for this stage: `release/vsa-recoverability-atlas`
- `git status --short` before stage: clean
- `git remote -v`: no remotes configured
- `git tag`: none

## Environment

- Python: `3.14.5`
- Platform: `Windows-11-10.0.26100-SP0`
- Core package versions observed in the local release-prep environment:
  - `torch 2.12.0+cpu`
  - `torchhd 5.8.4`
  - `numpy 2.4.6`
  - `galois 0.4.11`
  - `pytest 9.1.0`

## Repository Size

- Tracked file count: `539`
- Approximate working-tree size excluding `.git`: `3,061,068,165 bytes`
- `git count-objects -vH` snapshot:
  - loose objects: `25,895`
  - loose-object size: `277.96 MiB`
  - packed objects: `939`
  - pack size: `20.31 MiB`

## Largest Tracked Files at Baseline

| path | size (bytes) | note |
| --- | ---: | --- |
| `results/first_order_trace_coactivation/trial_results.jsonl` | `104343028` | required raw development artifact |
| `results/lazy_trace_stage_a1/trial_results.jsonl` | `88886188` | required raw development artifact |
| `results/lazy_trace_stage_a2a/trial_results.jsonl` | `68188003` | required raw development artifact |
| `results/level2c/heldout_trials.jsonl` | `46696249` | historical held-out artifact |
| `results/exact_capsule_contract/trial_results.jsonl` | `31815861` | required raw development artifact |
| `results/codebook_residue_v0_1/raw_trials.jsonl` | `23540418` | required raw development artifact |

## Notes

- The internal Python namespace `src/cgrn_hsr` is intentionally retained for compatibility.
- Historical result directories, protocol IDs, and frozen artifact paths are not renamed during release preparation.
