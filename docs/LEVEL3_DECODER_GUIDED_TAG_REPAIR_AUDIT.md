# Decoder-Guided Minimal Representation Repair v0.1 audit

- Verdict: `PROTOTYPE / COMPOSE`
- Status: `PROTOTYPE / DEVELOPMENT_ONLY / NEW_HYPOTHESIS / NO_PRODUCTION_CLAIM`

## Previous blocked line

- commit: `c6a24d7e16eef366bf03d78db306266a00c05e0c`
- scientific verdict: `DECODER_CERTIFIED_RECOVERY_ADVANTAGE_NOT_SUPPORTED`
- kill gate: `BLOCK_DECODER_CERTIFICATION_LINE`

## Prior art

- `q-ary / erasure symbols`: `ADAPT` with estimated coverage `0.4`. Tagged four-symbol repair overlaps with enriched alphabets and erasure-style side information, but this stage keeps semantic MAP bits unchanged and uses tags only as sparse recovery evidence.
- `error-correcting output codes / reliability weighting`: `ADAPT` with estimated coverage `0.5`. The causal idea resembles decoder-informed selective redundancy, but no existing repo primitive already performs conflict-localized sparse repair on open-world factor domains.
- `sparse codes / sparse block codes / spreading codes`: `COMPARE` with estimated coverage `0.3`. These are the honest redundancy controls; Arm F and random-tag controls are included so the stage cannot claim victory from generic extra bits.
- `Bloom-filter-like membership sketches / confidence masks`: `COMPARE` with estimated coverage `0.3`. Marker overlays act like sparse confidence hints, not canonical identity or pointer payloads.
- `existing MAP/TorchHD resonator harness`: `WRAP` with estimated coverage `1.0`. Reuse the native semantic decoder and only add a thin marker-aware cleanup wrapper, conflict attribution, and patch protocol.

## Why not scratch

- A new resonator, new VSA algebra, or learned encoder would answer a different question than the narrow causal repair hypothesis.
- The repository already contains deterministic MAP domain generation, resonator iteration budgets, and exact reconstruction checks.
- This stage only needs a versioned recovery view, conflict accounting, sparse tag placement, and matched controls.

## Minimal path

- Reuse the current MAP/TorchHD semantic decoder.
- Add only a bit-exact tagged recovery view, marker merge, conflict attribution, and matched controls.
- Keep exact fallback as a typed outcome only; do not implement a runtime router, ANN, DAG, or pointer layer.

## AGI claim gate

- Claim boundary: decoder-derived stable conflict attribution driving minimal sparse tagged-symbol repair in an open-world VSA recovery view.
- Authority boundary: semantic MAP state remains native; marker evidence only changes candidate cleanup/ranking.
- Failure criterion: if guided placement does not beat shuffled/random controls or is dominated by equal-bit extra dimensions, block the line.
