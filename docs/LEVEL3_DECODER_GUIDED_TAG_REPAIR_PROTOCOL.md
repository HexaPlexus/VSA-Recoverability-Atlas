# Decoder-Guided Minimal Representation Repair v0.1 protocol

- Protocol hash: `ba57e148f752a9d77a4982c1921bab732d0c8ea4d812bb4b8d61467f69ec2c28`
- Starting commit: `c6a24d7e16eef366bf03d78db306266a00c05e0c`
- Held-out execution allowed: `False`
- Long run authorized: `False`

## Representation contract

- Tagged alphabet: `NORMAL_NEG, NORMAL_POS, TAGGED_NEG, TAGGED_POS`
- Semantic projection preserved: `True`
- Marker score: `(D * semantic_score + effective_marker_bits * marker_score) / (D + effective_marker_bits)`

## Frozen cells

- `smoke_d512_m10`: D=`512`, M=`10`, seeds `962510100..962510100`.
- `transition_d1024_m22`: D=`1024`, M=`22`, seeds `962522100..962522100`.
- `transition_d1024_m31`: D=`1024`, M=`31`, seeds `962531100..962531100`.

## Arms

- `A_BASE_BINARY`
- `B_RANDOM_TAGS`
- `C_SHUFFLED_CONFLICT_TAGS`
- `D_RANDOM_PATCH_SEARCH`
- `E_CONFLICT_GUIDED_TAGS`
- `F_EQUAL_BIT_EXTRA_DIMENSIONS`

## Repair ladder

- `[0, 8, 16, 32]`

## Certificate

- verified exact recovery >= `0.9`
- conditional risk <= `0.05`
- silent wrong acceptance <= `0.0`
- accepted coverage >= `0.75`

## Scope limit

- Level 3.5b confirmatory closure is not complete; only audit, protocol, unit tests, and tiny smoke are lawful.
