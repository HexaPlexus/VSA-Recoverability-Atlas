# Level 3.5a Noise Contracts

- Verdict: `READY_FOR_LEVEL_3_5B`
- Schema: `level3-5a-noise-audit-v1`
- Checkpoint: `9fa47d9bb9aded882dc20ba8b4438c74bd817b05`

## Frozen Frame

- Clean exact U1 no longer justifies a VSA or coding substrate by itself.
- Level 3.5b must therefore justify any substrate on noise, erasure, approximate observation, associative recall, or future U2 superposition rather than on clean tuple recovery alone.

## External vs Internal

- `external_corruption_spec`: lawful corruption applied to the already encoded observation.
- `internal_decoder_noise_spec`: stochasticity injected by the decoder dynamics themselves.
- These must remain separate in every trial record.
- Official IBM BCF initialization or iterative noise is not observation corruption.

## Noise Taxonomy

- `N0_CLEAN_REFERENCE`: clean non-regression anchor.
- `N1_BINARY_SYMMETRIC_COORDINATE_CORRUPTION`: binary or bipolar coordinate corruption inside a lawful serialization.
- `N2_COORDINATE_ERASURE`: coordinate erasure with an explicit mask.
- `N3_NATIVE_SYMBOL_OR_BLOCK_CORRUPTION`: native symbol or block corruption; compare only within compatible representations.
- `N4_SEMANTIC_FACTOR_CORRUPTION`: semantic source corruption before encoding; not a primary Level 3.5b channel.
- `N5_APPROXIMATE_PERCEPTUAL_OBSERVATION`: approximate perceptual observation; subject-relevant but deferred until N1/N2/N3 closure.
- `N6_SUPERPOSITION_INTERFERENCE`: superposition interference; belongs to U2, not U1.

## Mandatory Controls

- `uncoded packed tuple` remains the information lower bound and fragility sanity control.
- `packed tuple + BCH` is mandatory and must appear in at least low- and high-redundancy tiers.
- `generic full-rank linear mix` remains the anti-NIH algebraic control.
- `raw NeCo` stays clean-only unless a lawful noisy contract appears; no custom noisy decoder is authorized.
- `official IBM BCF` is evaluated only on native noisy-product or block-symbol tracks unless a shared binary channel is formalized.

## Guardrails

- Zero-fill must not be described as native erasure decoding.
- Equal raw bit-flip probability is not equal semantic damage across MAP, symbolic bits, and GSBC blocks.
- Histogram recovery remains deferred to U2/noisy composition.
- Level 3.5a adds no new decoder and executes no full benchmark.

## ECC Audit Snapshot

- `galois 0.4.11` exposes BCH and Reed-Solomon encode/decode APIs with optional erasures and typed error counts where requested.
- Direct shortened BCH constructors are not exposed in the local audit smoke, so shortened controls require a thin wrapper over parent codes.
- Reed-Solomon is deferred to symbol-native tracks rather than used as the default control for binary coordinate flips.

