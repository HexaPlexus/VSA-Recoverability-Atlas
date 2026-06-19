# Codebook-Compressed Residue Plane v0.1 protocol

- Protocol hash: `dad34b84db6baa5a120cc69bf1e27d5a55d207321efa2b60670e403effc9f447`
- Starting commit: `1f2808626ac94f158fe2cecda04d536e316b15a4`
- Normalization: `abs_accumulator_over_sqrtK`
- Tie policy: `sign(0)=+1; tie_weight=0`
- Block size: `8`

## Codebook construction

- selection: `top_frequency_block_patterns`
- distance: `L1`
- codebook sizes: `[4, 16]`
- shared across K: `True`

## Frozen cells

- `d1024_k7_n128_s0`: D=`1024`, K=`7`, N=`128`, atom_seed=`964100100`
- `d1024_k7_n256_s0`: D=`1024`, K=`7`, N=`256`, atom_seed=`964100100`
- `d1024_k15_n128_s0`: D=`1024`, K=`15`, N=`128`, atom_seed=`964100100`
- `d1024_k15_n256_s0`: D=`1024`, K=`15`, N=`256`, atom_seed=`964100100`
- `d1024_k31_n128_s0`: D=`1024`, K=`31`, N=`128`, atom_seed=`964100100`
- `d1024_k31_n256_s0`: D=`1024`, K=`31`, N=`256`, atom_seed=`964100100`
- `d1024_k7_n128_s1`: D=`1024`, K=`7`, N=`128`, atom_seed=`964100200`
- `d1024_k7_n256_s1`: D=`1024`, K=`7`, N=`256`, atom_seed=`964100200`
- `d1024_k15_n128_s1`: D=`1024`, K=`15`, N=`128`, atom_seed=`964100200`
- `d1024_k15_n256_s1`: D=`1024`, K=`15`, N=`256`, atom_seed=`964100200`
- `d1024_k31_n128_s1`: D=`1024`, K=`31`, N=`128`, atom_seed=`964100200`
- `d1024_k31_n256_s1`: D=`1024`, K=`31`, N=`256`, atom_seed=`964100200`

## Split counts

- discovery: `48`
- validation: `32`
- final: `64`
