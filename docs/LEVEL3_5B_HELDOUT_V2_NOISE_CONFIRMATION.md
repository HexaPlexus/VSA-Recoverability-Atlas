# Level 3.5b Held-Out Native Noise Frontier Confirmation v2

- Schema: `level3-5b-heldout-v2-confirmation-v1`
- Required checkpoint: `6aeafedb0b4025afbf9cbce9ff02e4b9aa10a32e`
- Current commit at execution attempt: `6aeafedb0b4025afbf9cbce9ff02e4b9aa10a32e`
- Overall verdict: `BLOCKED_BY_V2_PROTOCOL_INTEGRITY_FAILURE`

## Pre-Execution Integrity

- Protocol v2 hash expected: `649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf`
- Protocol v2 canonical hash observed: `649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf`
- Protocol v2 file SHA-256 observed: `99aefc15db00bf527cca0b6fdcdbebd151bd3be393af2e7629c005c0db12f3e9`
- BCH hash observed: `7974133f002cbba795ae4655f7ab8b75bc6621f86991c13bd1e4d97d3ba733f3`
- MAP hashes observed: `{"map_d1024": "11fd00e0f0ed8bd4341e51169ca7bde135299d69e11798ad4a97b96ed96e5ff9", "map_d1024_step32_r4_best_native_reconstruction": "b32e989b0016c44e0d8cac61d0aead60edd43efc7ff686d1ff76e779c5747bff"}`
- Seed audit PASS: `True`
- Old blocked artifacts unchanged: `True`
- Repair artifacts unchanged: `True`

## Blocking Reason

- No held-out trials were executed.
- The repaired v2 protocol preserves frozen methods, cells, points, seeds and hashes.
- However, the confirmatory gate layer remains underspecified for execution.
- `gates` serializes only allowed disposition labels, not executable decision rules.
- Under the frozen-protocol contract, the runner cannot invent confirmatory thresholds or verdict logic.

## Claim Boundary

- This is a pre-trial integrity block, not a scientific outcome.
- No binary, BCH, NeCo, generic-linear, MAP or BCF held-out result was observed in this v2 attempt.
