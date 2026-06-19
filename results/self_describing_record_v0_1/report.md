# Self-Describing Recursive Hypervector Record v0.1

- Build verdict: `ADOPT_ORDINARY_SIDECAR_DAG`
- Engineering verdict: `ADOPT_ORDINARY_SIDECAR_DAG`
- Scientific status: `PACKAGING_ADVANTAGE_NOT_SUPPORTED`
- Protocol hash: `a0d3674810dd041370c14da3474b3bdf976bb4a9b39a971259d6c251b2a6b69a`

## Arm snapshot

- `B_ORDINARY_SIDECAR_DAG`: exact `1.0000`, latency `0.000612s`, lookups `12.17`, bytes `4309.82`.
- `C_INLINE_PACKED_MANIFEST`: exact `1.0000`, latency `0.000614s`, lookups `6.09`, bytes `4309.82`.
- `A_MAP_FACTORIZATION_BASELINE`: exact `1.0000`, latency `0.002290s`, lookups `0.00`, bytes `4096.00`.

## Corruption outcomes

- `manifest_bitflip`: `MANIFEST_INTEGRITY_FAILURE`
- `wrong_valid_handle`: `SEMANTIC_COMMITMENT_MISMATCH`
- `dangling_parent`: `DANGLING_OPERAND_REF`
- `stale_parent_version`: `PARENT_VERSION_MISMATCH`
- `cycle_detected`: `CYCLE_DETECTED`
