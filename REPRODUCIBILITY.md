# Reproducibility Guide

## Scope

This repository now distinguishes three layers of reproducibility:

1. `CI validation`
   Checks that the project installs, the atlas files generate, and the unit suite remains green.
2. `Local unit validation`
   Runs artifact validators and the full local pytest suite.
3. `Historical scientific reruns`
   Re-executes older development or held-out stages using the preserved protocols, seeds, and result contracts.

CI validation is intentionally smaller than full scientific reproduction.

## Supported Core Environment

- Python: `3.14`
- Core dependencies:
  - `torch`
  - `torch-hd`
  - `numpy`
  - `galois`
  - `pytest`

Install:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

Optional extras:

- `.[competitors]` for HoloVec-related audit coverage.
- `.[retrieval]` for Faiss-based retrieval comparisons.
- `.[level3]` for MiniGrid optional smoke coverage.

## Minimal Public Smoke Path

```powershell
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
.\.venv\Scripts\python -m pytest -q tests/test_level0_smoke.py
```

## Full Local Validation

```powershell
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
.\.venv\Scripts\python -m pytest -q
```

## Historical Scientific Artifacts

- Historical result directories in [results](results) are preserved.
- Frozen protocol IDs, hashes, and held-out artifacts are not renamed during public-release cleanup.
- The internal package namespace `cgrn_hsr` is preserved for compatibility with those artifacts.

## Hardware Notes

- The core release target is CPU reproducibility.
- Some historical experiments used optional competitor environments or separate virtual environments.
- Faiss-based Stage A.2a tests are optional and depend on the `retrieval` extra.
- MiniGrid is optional and not required for the core atlas.

## Seed Discipline

- Release-preparation work in this stage does not introduce new VSA experiments.
- Historical seeds remain documented in their original protocol artifacts.
- Level 3.5 held-out artifacts remain unchanged.

## What This Guide Does Not Promise

- It does not promise full historical GPU parity on every host.
- It does not rewrite historical artifacts into a new schema.
- It does not turn development-only results into confirmatory claims.
