# Level 3.1 Development Boundary

Schema version: `level3-1-native-envelope-dev-v1`

## U1 development boundary summary

| point | substrate | config | log10(search space) | exact recovery | mean iterations | mean decode time (s) | phase zone |
| --- | --- | --- | --- | --- | --- | --- | --- |
| u1_f3_m10 | BCF | bcf_d1024_f3_b4_m10 | 3.000 | 1.000 | 2.00 | 0.0320 | EASY |
| u1_f3_m10 | BCF | bcf_d256_f3_b4_m10 | 3.000 | 1.000 | 2.56 | 0.0322 | EASY |
| u1_f3_m10 | BCF | bcf_d512_f3_b4_m10 | 3.000 | 1.000 | 2.00 | 0.0292 | EASY |
| u1_f3_m10 | MAP | map_d1024 | 3.000 | 1.000 | 3.38 | 0.0047 | EASY |
| u1_f3_m10 | MAP | map_d256 | 3.000 | 0.750 | 6.38 | 0.0090 | INTERMEDIATE |
| u1_f3_m10 | MAP | map_d512 | 3.000 | 1.000 | 3.44 | 0.0051 | EASY |
| u1_f3_m22 | BCF | bcf_d1024_f3_b4_m22 | 4.027 | 1.000 | 3.00 | 0.0413 | EASY |
| u1_f3_m22 | BCF | bcf_d256_f3_b4_m22 | 4.027 | 1.000 | 7.75 | 0.1071 | EASY |
| u1_f3_m22 | BCF | bcf_d512_f3_b4_m22 | 4.027 | 1.000 | 4.19 | 0.0545 | EASY |
| u1_f3_m22 | MAP | map_d1024 | 4.027 | 0.688 | 7.12 | 0.0112 | INTERMEDIATE |
| u1_f3_m22 | MAP | map_d256 | 4.027 | 0.000 | 11.62 | 0.0176 | FAILURE |
| u1_f3_m22 | MAP | map_d512 | 4.027 | 0.375 | 9.44 | 0.0182 | BOUNDARY |
| u1_f3_m31 | BCF | bcf_d1024_f3_b4_m31 | 4.474 | 1.000 | 3.62 | 0.0503 | EASY |
| u1_f3_m31 | BCF | bcf_d256_f3_b4_m31 | 4.474 | 1.000 | 11.12 | 0.1834 | EASY |
| u1_f3_m31 | BCF | bcf_d512_f3_b4_m31 | 4.474 | 1.000 | 6.06 | 0.0828 | EASY |
| u1_f3_m31 | MAP | map_d1024 | 4.474 | 0.375 | 9.44 | 0.0198 | BOUNDARY |
| u1_f3_m31 | MAP | map_d256 | 4.474 | 0.000 | 12.00 | 0.0236 | FAILURE |
| u1_f3_m31 | MAP | map_d512 | 4.474 | 0.125 | 11.00 | 0.0218 | INTERMEDIATE |
| u1_f3_m49 | BCF | bcf_d1024_f3_b4_m49 | 5.071 | 1.000 | 11.12 | 0.1454 | EASY |
| u1_f3_m49 | BCF | bcf_d256_f3_b4_m49 | 5.071 | 1.000 | 39.81 | 0.5889 | EASY |
| u1_f3_m49 | BCF | bcf_d512_f3_b4_m49 | 5.071 | 1.000 | 15.62 | 0.2345 | EASY |
| u1_f3_m49 | MAP | map_d1024 | 5.071 | 0.125 | 11.50 | 0.0187 | INTERMEDIATE |
| u1_f3_m49 | MAP | map_d256 | 5.071 | 0.000 | 12.00 | 0.0208 | FAILURE |
| u1_f3_m49 | MAP | map_d512 | 5.071 | 0.000 | 12.00 | 0.0184 | FAILURE |
| u1_f3_m68 | BCF | bcf_d1024_f3_b4_m68 | 5.498 | 1.000 | 20.50 | 0.2826 | EASY |
| u1_f3_m68 | BCF | bcf_d256_f3_b4_m68 | 5.498 | 1.000 | 64.69 | 0.8542 | EASY |
| u1_f3_m68 | BCF | bcf_d512_f3_b4_m68 | 5.498 | 1.000 | 43.12 | 0.5987 | EASY |
| u1_f3_m68 | MAP | map_d1024 | 5.498 | 0.000 | 12.00 | 0.0195 | FAILURE |
| u1_f3_m68 | MAP | map_d256 | 5.498 | 0.000 | 12.00 | 0.0189 | FAILURE |
| u1_f3_m68 | MAP | map_d512 | 5.498 | 0.000 | 12.00 | 0.0187 | FAILURE |

## Pareto candidates

- `BCF / bcf_d1024_f3_b4_m10 / u1_f3_m10`: exact=1.000, zone=EASY.
- `BCF / bcf_d256_f3_b4_m10 / u1_f3_m10`: exact=1.000, zone=EASY.
- `BCF / bcf_d512_f3_b4_m10 / u1_f3_m10`: exact=1.000, zone=EASY.
- `MAP / map_d1024 / u1_f3_m10`: exact=1.000, zone=EASY.
- `MAP / map_d512 / u1_f3_m10`: exact=1.000, zone=EASY.
- `BCF / bcf_d1024_f3_b4_m22 / u1_f3_m22`: exact=1.000, zone=EASY.
- `BCF / bcf_d256_f3_b4_m22 / u1_f3_m22`: exact=1.000, zone=EASY.
- `BCF / bcf_d512_f3_b4_m22 / u1_f3_m22`: exact=1.000, zone=EASY.
- `BCF / bcf_d1024_f3_b4_m31 / u1_f3_m31`: exact=1.000, zone=EASY.
- `BCF / bcf_d256_f3_b4_m31 / u1_f3_m31`: exact=1.000, zone=EASY.
- `BCF / bcf_d512_f3_b4_m31 / u1_f3_m31`: exact=1.000, zone=EASY.
- `BCF / bcf_d1024_f3_b4_m49 / u1_f3_m49`: exact=1.000, zone=EASY.
- `BCF / bcf_d256_f3_b4_m49 / u1_f3_m49`: exact=1.000, zone=EASY.
- `BCF / bcf_d512_f3_b4_m49 / u1_f3_m49`: exact=1.000, zone=EASY.
- `BCF / bcf_d1024_f3_b4_m68 / u1_f3_m68`: exact=1.000, zone=EASY.
- `BCF / bcf_d256_f3_b4_m68 / u1_f3_m68`: exact=1.000, zone=EASY.
- `BCF / bcf_d512_f3_b4_m68 / u1_f3_m68`: exact=1.000, zone=EASY.
