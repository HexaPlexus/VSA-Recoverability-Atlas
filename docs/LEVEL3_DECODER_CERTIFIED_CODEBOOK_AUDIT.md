# Decoder-Certified Codebook Construction v0.1 audit

- Verdict: `COMPOSE`
- Status: `PROTOTYPE / DEVELOPMENT_ONLY / NO_PRODUCTION_CLAIM`

## Prior art

- `max-min Hamming / spherical code placement`: `ADOPT` with estimated coverage `0.6`. Directly covered by the distance-maxmin baseline; no need to reinvent a packing objective.
- `vector quantization / codebook search`: `ADAPT` with estimated coverage `0.5`. Similar search-over-codebook idea exists, but not as online factor-domain admission with the repository's blind MAP resonator in the loop.
- `learned encoder-decoder codebooks`: `BLOCK` with estimated coverage `0.2`. Out of scope here because this stage forbids a new decoder, learned scorer, or full training loop.
- `decoder-aware quantization / admission control`: `PROTOTYPE` with estimated coverage `0.4`. Motivational overlap exists, but no drop-in open-world MAP factor-codebook admission primitive is already present in the repo.
- `existing repo primitives`: `WRAP` with estimated coverage `1.0`. Reuse baseline.py and level3_2 confirmation MAP resonator path instead of building a new benchmark framework.

## Why not scratch

- The repository already contains deterministic MAP domain generation, upstream TorchHD resonator calls, candidate ranking margins, and seed discipline.
- A new benchmark framework, optimizer, or learned codebook trainer would answer a different question than this narrow causal admission audit.
- This stage only needs a small wrapper around candidate-pool generation, decoder-in-the-loop certification, and split-aware evaluation.

## Minimal path

- Reuse the existing MAP/TorchHD resonator harness and factor-domain generation utilities.
- Add only a thin candidate-pool, certification, shuffled-control, and split-aware smoke runner.
- Freeze tiny smoke cells now; defer any long development run until Level 3.5b confirmatory closure is complete.

## AGI claim gate

- Claim: `operation-aware online codeword admission for an open-world VSA codebook, using the actual blinded factor decoder and explicit non-commit`.
- Authority boundary: decoder sees only lawful read-time information; verifier sees ground truth only after decode.
- Failure criterion: if decoder-certified selection fails against distance-only or shuffled budget-matched control on unseen development evaluation, block the line.
