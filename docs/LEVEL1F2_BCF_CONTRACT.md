# Level 1F.2 BCF Contract Audit

Verdict: `WRAP`

Gate verdict: `PIVOT`

The official IBM BCF implementation is usable without a fork for single-product factorization with factor-specific domains and hard candidate subsets. It is not a clean drop-in for the full query-aware structured-mixture harness because the native BCF input contract is a single product vector, not a bundled multi-source observation.

## Main question

Can MAP-resonator and BCF be compared on the same abstract task, using each native representation, without changing the algorithms?

- Single-product tasks: `SUPPORTED`
- Hard context subsets on the same single-product task: `WRAPPABLE`
- Query-aware structured mixtures with multiple injected composites in one observation: `TASK_MISMATCH`

## Representation

1. SBC/GSBC vectors: `SUPPORTED`
   Native representation is a sparse block code with `B` blocks and `L = D / B` active positions. The codebook is materialized as integer block positions `IM[F, M, B]` and one-hot block tensors `matIM[F, M, B, L]`.
2. Factor count `F`, domain size `M`, dimension `D`, blocks `B`, active positions: `SUPPORTED`
3. Native bind/unbind: `SUPPORTED`
   Binding is block-wise circular convolution; unbinding is block-wise circular correlation.
4. Similarity: `SUPPORTED`
   Upstream exposes `dotp`, `l1`, and `inf`. `200a_bcf` uses `inf`.
5. Input semantics: `TASK_MISMATCH` for mixtures
   Upstream experiments generate one encoded product vector. The audited official path does not define bundled-mixture decoding as a first-class contract.

## Factor domains

6. Separate codebooks per factor position: `SUPPORTED`
7. Same atom index value across different factor domains without merged identity: `SUPPORTED`
8. Exactly one prediction per factor domain: `SUPPORTED`
9. Duplicate predictions: `SUPPORTED`
   Duplicates are domain-local integer ids, not a shared flat label space.

## External task injection

10. External abstract task injection: `WRAPPABLE`
   For single-product tasks, external factor indices, external factor codebooks, native product vectors, and externally perturbed native observations are all usable without modifying the update rule.
11. Fixed seed: `SUPPORTED`
12. Reuse the same task for multiple candidate subsets: `WRAPPABLE`
   Reusing the same observation is possible by slicing factor-local codebooks and rebuilding the official factorizer with a smaller `Mx`.

## Outputs

13. Accessible outputs:
   Predicted factor indices: `SUPPORTED`
   Iteration count: `SUPPORTED`
   Runtime: `WRAPPABLE`
   Final estimates: `UPSTREAM_MODIFICATION_REQUIRED`
   Score or margin per factor: `UPSTREAM_MODIFICATION_REQUIRED`
   Convergence/failure state: `WRAPPABLE`
14. Stable-wrong vs unsettled distinction: `UPSTREAM_MODIFICATION_REQUIRED`
   The public API exposes `conv_idx`, but not a per-iteration prediction trace or final estimate state needed for the repo's stronger stability taxonomy.
15. Maximum iterations: `SUPPORTED`

## Context compatibility

16. Full global domains + hard L2 subsets + external context metadata: `WRAPPABLE`
   Context can stay fully external to geometry. Candidate subsets are realized by factor-local codebook slicing.
17. Different candidate subsets for the same abstract task: `WRAPPABLE`
18. Subset requires shape or compile changes: `WRAPPABLE`
   `Mx` changes, but no compiler or kernel rebuild was needed in the audited official path.

## Limitations that matter for a fair shootout

- The official README mentions `environment.yml`, but the pinned commit does not contain that file.
- The README also mentions CUDA kernel compilation and Nvidia SDK requirements, but the audited commit exposed no custom CUDA extension build path; BCF ran as pure PyTorch on CUDA.
- Hard subsets are technically feasible, but changing `Mx` can invalidate hyperparameters tuned for a different search space. Any future shootout must declare whether BCF hyperparameters are frozen or retuned for subset sizes.
- The public BCF API does not expose final estimates or factor-wise margins, so parity with MAP evidence logging is incomplete without extra upstream support.
- Structured-mixture parity is not honest without changing the task definition or going beyond native upstream semantics.

## Practical next step

Proceed only with a narrowed Level 1F.3 shootout:

- honest scope: single-product global vs single-product hard-subset comparisons;
- out of scope for now: structured mixtures and query-equivalent multi-source semantics.
