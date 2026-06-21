# Reproducibility Guide

## Scope

This repository distinguishes three layers of reproducibility:

1. `CI validation`
   Checks that the project installs, the atlas files generate, and the unit suite remains green.
2. `Local unit validation`
   Runs artifact validators and the full local pytest suite.
3. `Historical scientific reruns`
   Re-executes older development or held-out stages using the preserved protocols, seeds, and result contracts.

CI validation is intentionally smaller than a full scientific rerun.

## Supported Core Environment

- Python: `3.14`
- Core dependencies:
  - `torch`
  - `torch-hd`
  - `numpy`
  - `galois`

Windows install:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev,publication]"
```

Linux/macOS install:

```bash
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,publication]"
```

Devcontainer / workspace bootstrap:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,publication,competitors,level3]"
```

Optional extras:

- `.[dev]` for pytest and local repository-validation tooling.
- `.[publication]` for manuscript and PDF validation tooling.
- `.[competitors]` for HoloVec-related audit coverage.
- `.[retrieval]` for Faiss-based retrieval comparisons.
- `.[level3]` for MiniGrid optional smoke coverage.

## Minimal Validation Path

```powershell
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
.\.venv\Scripts\python -m pytest -q tests/test_level0_smoke.py
```

Linux/macOS equivalents:

```bash
python scripts/build_evidence_tables.py
python scripts/validate_evidence_registry.py
python -m pytest -q tests/test_level0_smoke.py
```

## Full Local Validation

```powershell
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
.\.venv\Scripts\python -m pytest -q
```

## Publication Toolchain

The reviewer preprint pipeline additionally requires:

- `pandoc`
- `tectonic`
- `qpdf`

On Debian/Ubuntu-style systems:

```bash
sudo apt-get update
sudo apt-get install -y pandoc qpdf tectonic
```

Tool resolution order for `scripts/build_manuscript.py` and `scripts/validate_manuscript_pdf.py` is:

1. explicit CLI path such as `--pandoc`, `--tectonic`, or `--qpdf`
2. environment variables `PANDOC`, `TECTONIC`, or `QPDF`
3. the executable found on `PATH`

Publication build:

```bash
python scripts/build_manuscript.py --profile reviewer-preprint
python scripts/validate_manuscript_pdf.py --release paper/release_candidate/VSA_Recoverability_Atlas_<commit>.pdf
```

## Historical Scientific Artifacts

- Historical result directories in [results](results) are preserved.
- Frozen protocol IDs, hashes, and held-out artifacts are not renamed during documentation cleanup.
- The internal package namespace `cgrn_hsr` is preserved for compatibility with those artifacts.

## Hardware Notes

- The core release target is CPU reproducibility.
- Some historical experiments used optional competitor environments or separate virtual environments.
- Faiss-based Stage A.2a tests are optional and depend on the `retrieval` extra.
- MiniGrid is optional and not required for the core atlas.

## Seed Discipline

- Documentation and manuscript-preparation work in this repository does not introduce new VSA experiments.
- Historical seeds remain documented in their original protocol artifacts.
- Level 3.5 held-out artifacts remain unchanged.

## Boundaries

- This guide does not promise full historical GPU parity on every host.
- It does not rewrite historical artifacts into a new schema.
- It does not turn development-only results into confirmatory claims.
