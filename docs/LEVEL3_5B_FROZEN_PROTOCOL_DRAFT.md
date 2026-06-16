# Level 3.5b Frozen Protocol Draft

## Scope

- U1 noisy single-product only.
- No context, CNM, routing, pruning, or controller logic.
- No held-out execution is authorized by this document.

## Candidate Semantic Cells

- `u1_f3_m10`: easy non-regression (`payload_bits=12`)
- `u1_f3_m31`: MAP intermediate boundary (`payload_bits=15`)
- `u1_f3_m68`: BCF separation/high-capacity anchor (`payload_bits=21`)

## Development Search Policy

- Use adaptive phase-boundary search, not a dense universal probability grid.
- Development coarse pass: `16 trials per corruption point`.
- Freeze per lawful track: `2 easy points`, `2 boundary points`, `1 failure point`.
- Hold-out remains blocked until corruption ranges are audited and frozen.

## Lawful Track Separation

- `binary_channel_controls`: uncoded packed, BCH low/high, generic linear mix, raw NeCo, tiny oracle on N0/N1/N2.
- `map_sign_flip`: frozen MAP arms on N0 and native sign-flip corruption, with any erasure handling logged as a separate wrapped contract.
- `bcf_native_block_or_symbol`: official IBM BCF on N0 and native N3 block or symbol corruption, with internal stochasticity logged separately.

## Mandatory Outputs

- Exact recovery, silent wrong recovery, detected failure, and failure coverage.
- Redundancy, persistent bytes, runtime bytes, and decode latency.
- Channel-specific corruption descriptors rather than one universal raw percentage.

## Claims Blocked

- No substrate winner claim is authorized by the draft alone.
- No shared binary-vs-GSBC raw-p frontier is authorized without a formal serialization contract.
