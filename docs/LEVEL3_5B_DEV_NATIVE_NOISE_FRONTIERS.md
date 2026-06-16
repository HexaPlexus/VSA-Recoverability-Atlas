# Level 3.5b-dev Native Noise Frontiers

- Schema: `level3-5b-dev-native-noise-frontiers-v1`
- Checkpoint: `d6f222f5417a24c03c5b282d0cd4f4f5578a43b6`
- Binary exact-record verdict: `BCH_DOMINATES_BINARY_EXACT_RECORD_DEV`
- MAP verdict: `MAP_SILENT_COLLAPSE_DEV`
- BCF verdict: `BLOCK_BCF_TRACK`

## Scope

- Development only; no held-out execution.
- Binary exact-record channel, MAP sign-flip channel, and a separate BCF native-contract decision.
- No new decoder, no context/meta-control layer, no U2, and no universal raw-p comparison.

## Main Takeaways

- BCH remains the mandatory exact-record control in the binary track.
- Raw NeCo is evaluated only via the unchanged clean algebraic decoder under external corruption.
- MAP is evaluated only with post-product sign flips and frozen Level 3.2b envelopes.
- BCF track status: `BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY`.

## Guardrails

- Equal corruption percentages across incompatible channels are not interpreted as equal semantic damage.
- Any held-out protocol must remain track-specific and corruption-contract specific.
