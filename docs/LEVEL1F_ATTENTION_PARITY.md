# Level 1F Attention Parity Audit

## Verdict

`ADOPT` HoloVec as a third-party reference implementation and `WRAP` it only where the upstream API stays honest to the benchmark contract.

`BLOCK` a full Level 1F.1 shootout in the current repository state because HoloVec does not expose per-factor domains or factor-specific candidate masks.

## Upstream implementation audited

- Package: `holovec==1.0.2`
- Class: `holovec.utils.cleanup.attention.AttentionResonatorCleanup`
- Paper basis reviewed: [arXiv:2403.13218](https://arxiv.org/abs/2403.13218)
- Repository: [Twistient/HoloVec](https://github.com/Twistient/HoloVec)

## Paper-to-source mapping

- Attention logits from candidate similarities:
  HoloVec computes `similarities` against codebook vectors and then applies `_softmax(self.beta * similarities)`.
- Softmax inverse temperature:
  The class exposes `beta` and defaults it to `250.0`.
- Weighted update:
  The next estimate is the weighted sum of codebook vectors via `_weighted_combination(...)`.
- Resonator-style isolation:
  The update unbinds the query by the product of the other current estimates through `model.unbind(query, other_product)`.
- Normalization:
  HoloVec calls `model.normalize(new_estimate)` when available. For MAP this projects back into bipolar sign space.
- Stopping rule:
  The loop stops on either threshold convergence or patience-based lack of improvement.

## Differences from the paper-level idealization

- HoloVec is not the paper authors' official reference implementation.
- The public factorization API takes one flat `codebook: dict[str, Array]` plus `n_factors`.
- The public API does not expose final factor estimates.
- Iteration count is only inferable indirectly from `factorize_verbose(...).history`.
- Initialization is `mean(codebook)` for every factor estimate, which is explicit in source but not represented as a separate benchmark-facing hook.

## Difference from the TorchHD classic baseline

- TorchHD in this repository operates on explicit factor domains shaped `(F, M, D)`.
- HoloVec attention cleanup operates on one shared codebook and therefore cannot preserve factor-specific candidate subsets without internal masking or a rewritten update rule.
- Because of that mismatch, a direct global or L2 shootout would silently change the task rather than compare two factorizers on the same task.

## Reproducible blocker

Minimal reproduction is stored in [results/level1f/parity_report.json](/C:/Users/Thanatos/Desktop/CGRN-HSR/results/level1f/parity_report.json).

Observed behavior:

- with a shared flat codebook, HoloVec can assign the same label to multiple factor slots;
- this is legal for its API;
- it is not legal for the current benchmark contract, where each factor must decode inside its own domain.

## Decision

Do not write a custom attention resonator to patch around this.

If Level 1F is reopened later, the acceptable next step is one of:

1. find a published attention-resonator implementation with factor-specific domain support;
2. find upstream HoloVec support for per-factor codebooks;
3. redefine the benchmark contract explicitly around a shared-codebook task in a separate experiment line.
