# Third-Party Notices

This repository primarily wraps, audits, or reproduces upstream methods rather than reimplementing them from scratch.

The repository's current top-level license text is Apache-2.0 in [LICENSE](LICENSE). Third-party code, papers, datasets, and documentation remain under their own terms.

## Core Dependencies

- `torch` - `BSD-3-Clause`
- `torch-hd` / TorchHD - `MIT`
- `numpy` - `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`
- `galois` - `MIT`
- `pytest` - `MIT`
- `Markdown` - `BSD-3-Clause`
- `matplotlib` - custom Matplotlib license text distributed by upstream; no single SPDX identifier was confirmed in this workspace
- `PyYAML` - `MIT`
- `pypdf` - `BSD-3-Clause`

## Optional / Audit Dependencies

- `holovec[torch]` - `Apache-2.0`
- `faiss-cpu` - optional retrieval dependency for Stage A.2a-style tests; SPDX identifier not locally confirmed in this workspace
- `minigrid` - `MIT`

## Repository Policy

- The atlas preserves references to upstream methods, papers, and official implementations.
- Historical competitor and audit artifacts are documented as such.
- This file does not replace the original license texts of third-party materials.
