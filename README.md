# VSA Recoverability Atlas

VSA Recoverability Atlas is a reproducible research repository about a simple question: when composite or structured information is recoverable from Vector Symbolic Architectures, what additional resource actually pays for that reliability?

The repository preserves bounded positive results, explicit negative results, protocol discipline, and historical artifacts from the earlier `CGRN-HSR` research line. The internal Python package name `cgrn_hsr` remains in place for compatibility with those artifacts.

## Scientific Question

Across the evaluated envelopes, recoverability improved only when the system paid in some identifiable currency: exact side information, more dimensions or bits, stronger native structure, more decoder compute, stronger routing priors, narrower coverage through abstention, or an exact fallback.

The repository does not claim a universal impossibility theorem for VSA factorization. Its claims are intentionally bounded to the tasks, contracts, and evidence recorded here.

## Main Contributions

- A machine-readable evidence registry and claim ledger for repository-wide results and scope limits.
- Reproduced baselines for MAP/TorchHD, context-conditioned search, linear-code recovery, and structured-code transfer.
- A public record of negative results and stop conditions that remained unsupported after full accounting.
- A manuscript draft that synthesizes the empirical atlas, failure modes, and resource-accounting view.

## Selected Results

- MAP resonator recovery shows a bounded intermediate regime under the tested clean U1 budgets.
- Context-conditioned search beat random narrowing in the tested Level 1 single-product setting.
- In the clean common `F=3` envelope, robust native BCF covered hard cases that defeated the tested MAP arms.
- Several repair and packaging ideas did not produce a new nondominated point once storage, compute, and verification costs were counted.
- Exact packed binary scan is the current adopted semantic-to-trace retrieval baseline at the tested `N = 10,000` scale.

## Repository Guide

- [paper/manuscript.md](paper/manuscript.md): current manuscript draft.
- [paper/evidence_registry.yaml](paper/evidence_registry.yaml): machine-readable evidence source of truth.
- [paper/claim_ledger.md](paper/claim_ledger.md): public claim boundaries and supporting evidence.
- [paper/failure_mode_atlas.md](paper/failure_mode_atlas.md): normalized failure modes and mitigations.
- [REPRODUCIBILITY.md](REPRODUCIBILITY.md): install, validation, and rerun guidance.
- [docs](docs): preserved protocol, audit, and research-lineage artifacts.
- [results](results): frozen and development result artifacts.

## Reproducibility

Start with [REPRODUCIBILITY.md](REPRODUCIBILITY.md). The minimal validation path is:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
.\.venv\Scripts\python -m pytest -q
```

Historical result directories, protocol IDs, and held-out artifacts are intentionally preserved rather than renamed.

## Manuscript

- Canonical draft: [paper/manuscript.md](paper/manuscript.md)
- Release-candidate mirror: [paper/release_candidate/manuscript_rc1.md](paper/release_candidate/manuscript_rc1.md)
- Suggested title: `Recoverability Has a Cost: An Empirical Atlas of Factorization, Repair, and Abstention in Vector Symbolic Architectures`

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff).

## License

The repository's current top-level license text is [LICENSE](LICENSE). Scope notes for scholarly assets and third-party materials are in [LICENSE_SCOPE.md](LICENSE_SCOPE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
