# Codebook-Compressed Residue Plane v0.1 audit

- Verdict: `ADOPT_EXISTING_QUANTIZATION_PRIMITIVES / WRAP / COMPARE`
- Status: `ADOPT_EXISTING_QUANTIZATION_PRIMITIVES / WRAP / PROTOTYPE / DEVELOPMENT_ONLY / NO_NOVELTY_CLAIM / NO_PRODUCTION_CLAIM`

## Previous preserved verdicts

- `decoder_certified_codebook`: `BLOCK_DECODER_CERTIFICATION_LINE`
- `decoder_guided_tag_repair`: `BLOCK_TAGGED_SYMBOL_LINE`
- `self_describing_record`: `ADOPT_ORDINARY_SIDECAR_DAG / PACKAGING_ADVANTAGE_NOT_SUPPORTED`

## Anti-NIH findings

- `vector quantization / block vector quantization / product quantization`: `ADOPT` coverage `0.9`. The stage uses a tiny deterministic dictionary over quantized residue blocks rather than claiming a new VQ method.
- `lookup-table quantization / dictionary coding`: `ADOPT` coverage `1.0`. Decoder-side LUT prototypes are ordinary lookup-table quantization primitives.
- `scalar quantization / bit-plane coding / entropy coding`: `COMPARE` coverage `0.8`. A scalar residue control and raw coarse-block control are mandatory because they may explain any apparent gain without block dictionary complexity.
- `soft-decision reliability quantization`: `ADOPT` coverage `0.8`. Soft cleanup weights are just quantized reliability surrogates derived from accumulator magnitude.
- `MAP-I exact accumulator and MAP-B sign-only cleanup`: `WRAP` coverage `1.0`. The experiment reuses the ordinary MAP accumulator observation and candidate cleanup scoring; it does not invent a new decoder.
- `learned quantizers / neural compression`: `BLOCK` coverage `0.0`. No learned VQ, residual VQ, or new decoder-side model is authorized in v0.1.

## Scope reduction

- kept dimensions: `[1024]`
- kept bundle widths: `[7, 15, 31]`
- dropped cells: `['D=512', 'K=3']`
- reason: Reduce scope to transition-like accumulator regimes and keep the development run bounded without weakening the causal comparison among scalar, block-LUT, and equal-bit controls.
