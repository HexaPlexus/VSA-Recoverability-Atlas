# CGRN-HSR

Bootstrap-only repository state for `Level 0: Dependency & Provenance Bootstrap`.

## Level 0

Install:

```powershell
py -3.14 -m venv .venv; .\.venv\Scripts\python -m pip install -r pylock.toml
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest -q -s
```

`MiniGrid` is declared as the optional `level3` extra for future work and is not required for the core Level 0 lock.

## ADRs

- [ADR-001](docs/adr/ADR-001-reject-stateful-hierarchical-resonator-continuation.md): reject stateful hierarchical resonator continuation; keep calibrated L2 acceptance with cold global fallback.
