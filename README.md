# VSA Recoverability Atlas

Recoverability is not free.

This repository is a reproducible empirical atlas of capacity, factorization, repair, structured recovery, negative results, and abstention in Vector Symbolic Architectures.

## What This Repository Is

- A research atlas built from bounded experiments, audits, protocol work, and negative results.
- A reproducibility record for MAP/TorchHD baselines, substrate comparisons, context-conditioned search, exact-structure alternatives, and safety-first evaluation.
- A public-facing consolidation of the historically named `CGRN-HSR` repository.

The internal `cgrn_hsr` package name is retained for compatibility with historical experiments and reproducibility artifacts.

## What This Repository Is Not

- Not a single triumphant architecture.
- Not a proof of a universal impossibility theorem for VSA factorization.
- Not a production runtime, vector database, or AGI memory system.
- Not a claim that every negative result generalizes outside its explicit contract.

## Main Empirical Conclusion

Reliable recoverability always cost something in the tested envelopes:

- more exact structure,
- more bits or dimensions,
- more decoder compute,
- stronger routing priors,
- narrower coverage through abstention,
- or an exact fallback.

The repository does not prove a universal impossibility theorem for VSA factorization.

It records bounded empirical results and architectural stop conditions under explicit operation, substrate, compute, storage, and risk contracts.

## Research Philosophy

- Reuse prior art before writing custom mechanisms.
- Preserve negative results instead of burying them.
- Separate development evidence from held-out confirmation.
- Treat silent wrong acceptance as a first-class failure mode.
- Prefer typed abstention and exact fallback over unjustified confidence.

## Evidence Map

- Repository-wide evidence registry: [paper/evidence_registry.yaml](paper/evidence_registry.yaml)
- Hypothesis matrix: [paper/hypothesis_matrix.md](paper/hypothesis_matrix.md)
- Recoverability cost matrix: [paper/recoverability_cost_matrix.md](paper/recoverability_cost_matrix.md)
- Failure-mode atlas: [paper/failure_mode_atlas.md](paper/failure_mode_atlas.md)
- Claim ledger: [paper/claim_ledger.md](paper/claim_ledger.md)
- Prior-art atlas: [paper/prior_art_matrix.md](paper/prior_art_matrix.md)
- Preprint scaffold: [paper/manuscript.md](paper/manuscript.md)
- Public-release audit: [docs/PUBLIC_RELEASE_AUDIT.md](docs/PUBLIC_RELEASE_AUDIT.md)

## Key Reproduced Methods

- TorchHD MAP / resonator baselines and budget robustness.
- Level 1 context-conditioned candidate routing over unchanged native decoders.
- Scoped official IBM BCF audit and native-envelope reproduction.
- Clean U1 linear-code / NeCo paper reproduction.
- Exact first-order sidecar DAG replay.
- Exact packed binary scan as the current adopted trace-retrieval baseline at `N = 10,000`.

## Key Negative Results

- HoloVec as a fair drop-in competitor under the current factor-specific domain contract.
- Hierarchical warm continuation as a viable default runtime.
- Decoder-certified atomic codebook admission.
- Conflict-guided tagged-symbol repair.
- Inline packed manifest advantage over ordinary sidecar DAG.
- Block-codebook residue compression over scalar/equal-bit controls.
- Isolated exact capsule placement as an advantage over a plain typed field.

## Current Architectural Recommendation

Prefer exact or well-audited baselines first:

- MAP / TorchHD for historical blind factorization baselines.
- Exact sidecar DAG for preserved first-order structure.
- Exact packed binary scan for current semantic-to-trace retrieval at the tested `N = 10,000` scale.
- Typed abstention, explicit verification, and exact fallback wherever ambiguity remains.

## Repository Layout

- [src/cgrn_hsr](src/cgrn_hsr): historical package namespace and experiment helpers.
- [experiments](experiments): experiment entrypoints and stage runners.
- [results](results): frozen and development artifacts.
- [docs](docs): audit documents, closures, protocol notes, and research backlog.
- [paper](paper): evidence registry, matrices, claim ledger, prior-art atlas, and manuscript scaffold.
- [tests](tests): unit and artifact-validation tests.
- [scripts](scripts): lightweight atlas validators and table generators.

## Quick Start

Create a Python 3.14 environment and install the core package:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

Generate and validate the public evidence atlas:

```powershell
.\.venv\Scripts\python scripts\build_evidence_tables.py
.\.venv\Scripts\python scripts\validate_evidence_registry.py
```

Run the core smoke test:

```powershell
.\.venv\Scripts\python -m pytest -q tests/test_level0_smoke.py
```

Run the full local unit suite:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Optional extras:

- `.[competitors]` for HoloVec-related audit coverage.
- `.[retrieval]` for Faiss-based Stage A.2a tests.
- `.[level3]` for MiniGrid-related optional smoke coverage.

## Reproducing Results

Start with [REPRODUCIBILITY.md](REPRODUCIBILITY.md). It separates:

- CI validation,
- local unit validation,
- and full historical scientific reruns.

Historical result directories and protocol IDs are intentionally preserved and not renamed for public release.

## Scientific Status and Claim Limits

- Positive claims are limited by the [paper/claim_ledger.md](paper/claim_ledger.md).
- Deferred ideas remain in [docs/research](docs/research).
- Public-release blockers and limitations are documented in [docs/PUBLIC_RELEASE_AUDIT.md](docs/PUBLIC_RELEASE_AUDIT.md).

## Preprint Status

This repository now includes a public manuscript scaffold:

- [paper/manuscript.md](paper/manuscript.md)

Suggested title:

`Recoverability Has a Cost: An Empirical Atlas of Factorization, Repair, and Abstention in Vector Symbolic Architectures`

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff).

## License

The repository still requires an explicit owner license decision before public push.

See:

- [docs/LICENSE_DECISION.md](docs/LICENSE_DECISION.md)
- [docs/PUBLIC_RELEASE_AUDIT.md](docs/PUBLIC_RELEASE_AUDIT.md)
