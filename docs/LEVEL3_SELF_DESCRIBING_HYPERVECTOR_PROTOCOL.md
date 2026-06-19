# Self-Describing Recursive Hypervector Record v0.1 protocol

- Protocol hash: `a0d3674810dd041370c14da3474b3bdf976bb4a9b39a971259d6c251b2a6b69a`
- Starting commit: `19bcb16454a400a9fa67f00eafb6f889a92f2181`
- Identity format: `namespace_id + uint32 local concept_code + version`
- Base-50 codec primary path: `uint32 local concept_code`

## Operation registry

- `MAP_BIND_2`
- `MAP_PERMUTE`

## Replay contract

- memoization: `True`
- cycle_detection: `True`
- max_depth: `128`
- max_unique_nodes: `4096`

## Workloads

- flat_bind_records: `12`
- recursive_chain_depths: `[1, 2, 4, 8, 16]`
- balanced_tree_depths: `[2, 4, 6]`
- repeated_reads: `[1, 10, 100, 1000]`

## Scope limit

- No locator, ANN, BCF, linear codes, runtime manager, or production storage stack in this stage.
