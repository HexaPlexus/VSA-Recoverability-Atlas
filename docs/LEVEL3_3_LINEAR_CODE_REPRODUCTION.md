# Level 3.3 Linear-Code Reproduction

- Reproduction verdict: `REPRODUCED`
- Common U1 verdict: `COMMON_U1_COMPATIBLE_WITH_CONSTRAINTS`

## Dependency path

- `GF(2) arrays, rank, row-space, null-space` -> `ADOPT` via `galois==0.4.11`: Mature finite-field algebra library explicitly used in the paper experiments.
- `Rectangular left-solve for xB = c over GF(2)` -> `WRAP` via `galois built-ins only`: The library provides rank and row reduction, but the reproduction needs a tiny paper-local Gauss-Jordan helper for a rectangular unique-solve path.
- `Generic finite-field framework` -> `BLOCK` via `custom framework`: Out of scope; only paper-specific assembly and solving are authorized.

## Custom implementation boundary

- Allowed custom code: paper-specific subcode construction, paper-specific recovery-system assembly, local GF(2) unique-solve helper, and reproduction harness.
- Forbidden custom code: generic finite-field framework, generic ECC framework, noise decoder, histogram/U2 logic, or production integration.

## Claim boundary

- Allowed: contract extraction, minimal clean recovery reproduction, exhaustive tiny-oracle agreement, paper-native approximate reproduction, and U1 compatibility assessment.
- Forbidden: superiority over MAP/BCF, noise claims, production readiness, universal factorization, or official-implementation claims.
