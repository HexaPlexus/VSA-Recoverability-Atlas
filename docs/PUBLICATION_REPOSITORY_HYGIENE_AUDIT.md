# Publication Repository Hygiene Audit

## Scope

This repair pass is limited to public repository hygiene for `publication/preprint-v1`:

- portable manuscript/PDF build tooling
- package metadata and dependency declaration
- CI coverage for the publication branch and reviewer PDF build
- devcontainer and clean-checkout bootstrap
- citation, license-scope, and security-policy clarification

It does not change scientific results, frozen result artifacts, raw trial data, protocol identifiers, evidence verdicts, numerical manuscript content, or experimental methods.

## Confirmed Findings

- `publication/preprint-v1` is ahead of `main` by seven commits with no reverse divergence.
- `pyproject.toml` used placeholder GitHub URLs and version `0.0.0`.
- `pyproject.toml` did not declare publication-tooling dependencies used by the manuscript and PDF scripts.
- `scripts/build_manuscript.py` depended on machine-local absolute Windows paths for `pandoc`, `tectonic`, and `qpdf`.
- `scripts/validate_manuscript_pdf.py` depended on a machine-local absolute Windows path for `qpdf`.
- `.github/workflows/tests.yml` did not run on `publication/**` and did not build the reviewer preprint PDF via the documented manuscript pipeline.
- The repository lacked `.python-version` and a devcontainer bootstrap contract.
- `CITATION.cff`, `LICENSE_SCOPE.md`, and `THIRD_PARTY_NOTICES.md` needed synchronization with the public preprint state and confirmed license metadata.

## External Metadata Limits

- Public unauthenticated GitHub API access in this environment did not expose Dependabot or code-scanning alert details.
- No open pull request targeting `publication/preprint-v1` was visible at audit time.
