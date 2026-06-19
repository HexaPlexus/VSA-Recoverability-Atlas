# Codebook-Compressed Residue Plane v0.1 execution plan

- starting_commit: `1f2808626ac94f158fe2cecda04d536e316b15a4`
- branch: `codex/codebook-residue-v0_1`
- git_status: `clean_expected`
- selected_cells: `[(1024, 7, 128), (1024, 7, 256), (1024, 15, 128), (1024, 15, 256), (1024, 31, 128), (1024, 31, 256), (1024, 7, 128), (1024, 7, 256), (1024, 15, 128), (1024, 15, 256), (1024, 31, 128), (1024, 31, 256)]`
- block_size: `8`
- codebook_sizes: `[4, 16]`
- discovery_bundles_per_cell: `48`
- validation_bundles_per_cell: `32`
- final_bundles_per_cell: `64`
- codebook_seeds: `[964100100, 964100200]`
- estimated_trials: `12672`
- estimated_runtime: `bounded CPU development run, low-minute envelope`
- selected_device: `cpu`
- output_path: `results/codebook_residue_v0_1`

Execution order: audit -> protocol -> scalar/block implementation -> tests -> smoke -> bit accounting -> paired run -> final development evaluation -> report.
