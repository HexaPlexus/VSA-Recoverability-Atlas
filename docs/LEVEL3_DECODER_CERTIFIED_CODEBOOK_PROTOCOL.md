# Decoder-Certified Codebook Construction v0.1 protocol

- Protocol hash: `c38252c5823def1ea86454146f62b8e3c55bcec6beaf10cbf94985800734a4f1`
- Starting commit: `52060ef73c41bbde2110b479120710a4f1750bb7`
- Long run authorized: `False`
- Held-out execution allowed: `False`

## Frozen substrate

- Family: `MAP`
- Decoder: `TorchHD resonator`
- Task contract: `U1_blind_single_product_factorization`
- Factor count: `3`
- Max iterations: `12`
- Stable patience: `3`
- Corruption contract: `clean_only`

## Frozen cells

- `smoke_d512_m10`: D=`512`, initial M=`8`, final M=`10`, seeds `961510100..961510100`.
- `transition_d1024_m22`: D=`1024`, initial M=`20`, final M=`22`, seeds `961522100..961522101`.
- `transition_d1024_m31`: D=`1024`, initial M=`29`, final M=`31`, seeds `961531100..961531101`.

## Arms

- `A_RANDOM_FIRST`
- `B_DISTANCE_MAXMIN`
- `C_DECODER_CERTIFIED`
- `D_SHUFFLED_CERTIFICATION_CONTROL`

## Split separation

- Certification drives candidate selection only.
- Development validation and final development evaluation remain seed-disjoint from certification.
- Candidate pool, certification, validation, final evaluation, and shuffle controls use frozen offset namespaces.

## Selection rule

- exclude candidates that violate silent-error gate
- maximize exact factor recovery
- maximize verified reconstruction
- maximize top1-top2 margin
- minimize decoder iterations
- deterministic candidate-index tie-break

## Scope limit

- Level 3.5b confirmatory closure is not complete; only audit, protocol, tests, and tiny smoke are lawful.
