# Level 3.5b Held-out Protocol

- Schema: `level3-5b-dev-native-noise-frontiers-v1`
- Executed: `False`

## Binary Track

- Methods: `uncoded_packed_tuple, packed_tuple_bch_low_redundancy, packed_tuple_bch_high_redundancy, generic_full_rank_linear_mix, raw_neco_algebraic_recovery`
- Trial count per selected point: `64`

## MAP Track

- Methods: `map_d1024, map_d1024_step32_r4_best_native_reconstruction`
- Trial count per selected point: `64`

## BCF Track

- Status: `BCF_TRACK_BLOCKED_BY_CONTRACT_AMBIGUITY`
- Reason: Official upstream and pinned paper artifacts expose native internal noise sweeps, but do not unambiguously freeze an external corruption channel for the blockcodefactorizer path comparable to the Level 3.5b contract.
