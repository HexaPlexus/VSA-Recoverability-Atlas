# Dependencies

Core environment is pinned in [pylock.toml](pylock.toml).  
`pylock.toml` is a Windows + CPython 3.14 specific resolution produced by the experimental `pip lock` command, so it is intentionally platform-dependent rather than a universal lock.  
The optional competitor environment is pinned separately in [pylock.competitors.toml](pylock.competitors.toml).  
The optional future `Level 3` dependency is pinned separately in [pylock.level3.toml](pylock.level3.toml).

| dependency | resolved version | license | upstream | purpose | decision | limitations |
| --- | --- | --- | --- | --- | --- | --- |
| PyTorch | 2.12.0+cpu | BSD-3-Clause | https://pytorch.org | Tensor runtime, deterministic seeding, CPU/CUDA capability checks, and the execution substrate required by TorchHD. | ADOPT | The validated Windows wheel is CPU-only on this host, so `torch.cuda.is_available()` is `False`. GPU remains optional and is not required for Level 0. |
| TorchHD (`torch-hd`) | 5.8.4 | MIT | https://github.com/hyperdimensional-computing/torchhd | Upstream VSA/HDC primitives, MAP hypervectors, binding, similarity, and the `torchhd.resonator` primitive used in smoke tests. | ADOPT | Pulls scientific transitive dependencies (`scipy`, `pandas`, `openpyxl`, `requests`, `tqdm`). It is a research library, not a CGRN-HSR runtime or verifier framework. |
| NumPy | 2.4.6 | BSD-3-Clause (wheel also bundles third-party notices) | https://numpy.org | Numerical base layer and deterministic seed coordination for smoke tests. | ADOPT | The wheel publishes a composite `License-Expression`; see bundled license notices in the installed distribution for third-party components. |
| galois | 0.4.11 | MIT | https://github.com/mhostetter/galois | Adopted finite-field algebra substrate for the Level 3.3 NeCo linear-code paper reproduction over `GF(2)`. | ADOPT | Covers arrays, rank, row-space and null-space operations, but the reproduction still uses a tiny local GF(2) rectangular unique-solve helper for the paper-specific `xB = c` path. |
| pytest | 9.1.0 | MIT | https://docs.pytest.org/en/latest/ | Minimal smoke-test runner for Level 0 validation only. | ADOPT | No CI was added; tests are local-only in this bootstrap stage. |
| HoloVec | 1.0.2 | Apache-2.0 | https://github.com/Twistient/HoloVec | Optional third-party attention-resonator competitor for Level 1F audit work. Paper basis: arXiv:2403.13218. | WRAP | Installed and importable on Windows + CPython 3.14 with the PyTorch backend, but the exposed factorization API accepts one shared flat codebook rather than separate factor domains. That blocks a fair drop-in shootout against the current multi-domain benchmark without rewriting the update rule. |
| MiniGrid | 3.1.0 | MIT | https://minigrid.farama.org/ | Optional future `Level 3` environment dependency and smoke target for import/reset/step validation. | ADOPT | Kept out of the core lock and pinned separately in `pylock.level3.toml`. It passed the optional Windows smoke test here, but deeper RL work may still be smoother in Linux/WSL due to the `pygame` stack. |

## Provenance Notes

- No dependency fork was required.
- `torchhd.resonator` is used directly from upstream; no local resonator implementation was added.
- Level 3.3 adopts `galois` for finite-field algebra instead of introducing a generic local GF(2) framework.
- `holovec` is kept out of the core lock and pinned separately in `pylock.competitors.toml` because it is an optional competitor dependency rather than part of the validated mainline environment.
- Level 1F stopped at the HoloVec audit boundary rather than forking or reimplementing an attention resonator.
- `pip lock .` against the local project path was rejected as the primary lock strategy because it encoded the repository as a `file://` requirement with hash verification issues in a clean environment. The reproducible fix was to lock the explicit dependency specifiers into `pylock.toml` and `pylock.level3.toml` instead.
