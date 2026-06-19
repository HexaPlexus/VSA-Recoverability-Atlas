# Contributing

This repository is evidence-first and reproducibility-first.

## Before Opening a Change

- Read [README.md](README.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md), and [RESEARCH_STATUS.md](RESEARCH_STATUS.md).
- Do not reinterpret negative results as soft wins.
- Do not mutate frozen held-out artifacts, protocol hashes, or historical result directories casually.

## Preferred Contribution Types

- Documentation fixes.
- Public-release hygiene.
- Reproducibility improvements.
- Validator improvements.
- Bug fixes that preserve historical scientific meaning.

## Changes That Need Extra Care

- Anything touching `results/level3_5*`.
- Anything that changes historical verdict wording.
- Anything that changes seed discipline or protocol hashes.
- Anything that would require rerunning held-out experiments.

## Pull Request Expectations

- Keep claims within the claim ledger.
- Prefer wrapping prior art over new custom frameworks.
- Add or update tests when behavior changes.
- Explain whether a change is:
  - metadata-only,
  - reproducibility-only,
  - protocol-only,
  - or scientific.
