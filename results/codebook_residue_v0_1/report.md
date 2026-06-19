# Codebook-Compressed Residue Plane v0.1

- Build verdict: `ADOPT_EXTRA_DIMENSIONS`
- Scientific verdict: `BLOCK_CODEBOOK_RECOVERY_ADVANTAGE_NOT_SUPPORTED`
- Protocol hash: `dad34b84db6baa5a120cc69bf1e27d5a55d207321efa2b60670e403effc9f447`

## Previous preserved verdicts

- `decoder_certified_codebook`: `BLOCK_DECODER_CERTIFICATION_LINE`
- `decoder_guided_tag_repair`: `BLOCK_TAGGED_SYMBOL_LINE`
- `self_describing_record`: `ADOPT_ORDINARY_SIDECAR_DAG / PACKAGING_ADVANTAGE_NOT_SUPPORTED`

## Codebooks

- `C=4` prototypes: `[[1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 2, 1], [1, 1, 1, 2, 1, 1, 1, 1], [1, 2, 1, 1, 1, 1, 1, 1]]`
- `C=16` prototypes: `[[1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 2, 1], [1, 1, 1, 2, 1, 1, 1, 1], [1, 2, 1, 1, 1, 1, 1, 1], [2, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 2, 1, 1], [1, 1, 1, 1, 1, 1, 1, 2], [1, 1, 1, 1, 2, 1, 1, 1], [1, 1, 2, 1, 1, 1, 1, 1], [1, 1, 1, 2, 2, 1, 1, 1], [1, 2, 1, 1, 1, 2, 1, 1], [1, 2, 1, 1, 1, 1, 1, 2], [1, 1, 1, 2, 1, 1, 2, 1], [1, 1, 1, 1, 2, 1, 1, 2], [1, 1, 1, 2, 1, 1, 1, 2], [1, 1, 2, 1, 1, 2, 1, 1]]`

## Final development arm summary

- `A_MAP_B_HARD` / `sign_only` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1051.00`, cold_latency=`0.000217s`.
- `A_MAP_B_HARD` / `sign_only` / `K=15`: full_recall=`0.9961`, precision=`0.9997`, fp_rate=`0.0000`, bits=`1051.00`, cold_latency=`0.000149s`.
- `A_MAP_B_HARD` / `sign_only` / `K=31`: full_recall=`0.4844`, precision=`0.9811`, fp_rate=`0.0039`, bits=`1051.00`, cold_latency=`0.000213s`.
- `B_TERNARY_TIE_AWARE` / `sign_plus_tie_mask` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`2075.00`, cold_latency=`0.000184s`.
- `B_TERNARY_TIE_AWARE` / `sign_plus_tie_mask` / `K=15`: full_recall=`0.9961`, precision=`0.9997`, fp_rate=`0.0000`, bits=`2075.00`, cold_latency=`0.000105s`.
- `B_TERNARY_TIE_AWARE` / `sign_plus_tie_mask` / `K=31`: full_recall=`0.4844`, precision=`0.9811`, fp_rate=`0.0039`, bits=`2075.00`, cold_latency=`0.000137s`.
- `C_SCALAR_RESIDUE_EQUAL_RATE` / `scalar_zlib_4level` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`2869.41`, cold_latency=`0.000160s`.
- `C_SCALAR_RESIDUE_EQUAL_RATE` / `scalar_zlib_4level` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`2883.28`, cold_latency=`0.000105s`.
- `C_SCALAR_RESIDUE_EQUAL_RATE` / `scalar_zlib_4level` / `K=31`: full_recall=`0.9062`, precision=`0.9970`, fp_rate=`0.0006`, bits=`2915.03`, cold_latency=`0.000125s`.
- `D_BLOCK_CODEBOOK_C4` / `C4` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1307.00`, cold_latency=`0.000124s`.
- `D_BLOCK_CODEBOOK_C4` / `C4` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1307.00`, cold_latency=`0.000085s`.
- `D_BLOCK_CODEBOOK_C4` / `C4` / `K=31`: full_recall=`0.5547`, precision=`0.9837`, fp_rate=`0.0033`, bits=`1307.00`, cold_latency=`0.000126s`.
- `E_BLOCK_CODEBOOK_C16` / `C16` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1563.00`, cold_latency=`0.000254s`.
- `E_BLOCK_CODEBOOK_C16` / `C16` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1563.00`, cold_latency=`0.000123s`.
- `E_BLOCK_CODEBOOK_C16` / `C16` / `K=31`: full_recall=`0.6055`, precision=`0.9868`, fp_rate=`0.0027`, bits=`1563.00`, cold_latency=`0.000120s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C16_shuffled` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1563.00`, cold_latency=`0.000141s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C16_shuffled` / `K=15`: full_recall=`0.9961`, precision=`0.9997`, fp_rate=`0.0000`, bits=`1563.00`, cold_latency=`0.000115s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C16_shuffled` / `K=31`: full_recall=`0.3672`, precision=`0.9739`, fp_rate=`0.0055`, bits=`1563.00`, cold_latency=`0.000154s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C4_shuffled` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1307.00`, cold_latency=`0.000299s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C4_shuffled` / `K=15`: full_recall=`0.9961`, precision=`0.9997`, fp_rate=`0.0000`, bits=`1307.00`, cold_latency=`0.000189s`.
- `F_SHUFFLED_BLOCK_TOKENS` / `C4_shuffled` / `K=31`: full_recall=`0.3945`, precision=`0.9754`, fp_rate=`0.0051`, bits=`1307.00`, cold_latency=`0.000110s`.
- `G_MAP_I_EXACT_ACCUMULATOR` / `exact_accumulator_k15` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`5147.00`, cold_latency=`0.000081s`.
- `G_MAP_I_EXACT_ACCUMULATOR` / `exact_accumulator_k31` / `K=31`: full_recall=`0.9414`, precision=`0.9981`, fp_rate=`0.0004`, bits=`6171.00`, cold_latency=`0.000140s`.
- `G_MAP_I_EXACT_ACCUMULATOR` / `exact_accumulator_k7` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`4123.00`, cold_latency=`0.000115s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C16` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1590.00`, cold_latency=`0.000130s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C16` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1590.00`, cold_latency=`0.000123s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C16` / `K=31`: full_recall=`0.9414`, precision=`0.9981`, fp_rate=`0.0004`, bits=`1590.00`, cold_latency=`0.000112s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C4` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1334.00`, cold_latency=`0.000135s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C4` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`1334.00`, cold_latency=`0.000123s`.
- `H_EQUAL_TOTAL_BIT_MAP_B` / `equal_bits_for_C4` / `K=31`: full_recall=`0.7930`, precision=`0.9928`, fp_rate=`0.0013`, bits=`1334.00`, cold_latency=`0.000112s`.
- `I_RAW_BLOCK_STORAGE` / `raw_block_symbols` / `K=7`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`3099.00`, cold_latency=`0.000134s`.
- `I_RAW_BLOCK_STORAGE` / `raw_block_symbols` / `K=15`: full_recall=`1.0000`, precision=`1.0000`, fp_rate=`0.0000`, bits=`3099.00`, cold_latency=`0.000092s`.
- `I_RAW_BLOCK_STORAGE` / `raw_block_symbols` / `K=31`: full_recall=`0.9062`, precision=`0.9970`, fp_rate=`0.0006`, bits=`3099.00`, cold_latency=`0.000107s`.

## Gate outcomes

- `Gate 1 - Soft-information value`: `PASS`
- `Gate 2 - Dictionary value`: `FAIL`
- `Gate 3 - Correct mapping`: `PASS`
- `Gate 4 - Equal-bit frontier`: `FAIL`
- `Gate 5 - Cross-K generalization`: `PASS`
- `Gate 6 - Codebook utilization`: `PASS`
- `Gate 7 - No hidden identity`: `PASS`
