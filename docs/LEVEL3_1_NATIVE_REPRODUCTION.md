# Level 3.1 Native Reproduction

Schema version: `level3-1-native-envelope-dev-v1`

## Source amendment

- HoloVec implementation verdict: `BLOCK_TASK_MISMATCH`
- Attention paper algorithm verdict: `DEFER_REPLICATION`

## MAP native reproduction

- Torch: `2.5.1+cu121`
- TorchHD: `5.8.4`
- Device: `cuda:0`

## IBM BCF native reproduction

- Upstream commit: `a353f1e918dcb515cad4a89c8e47ce24668954a7`
- Official smoke success: `True`
- Gate passed: `True`

## Cap amendment

- Level 3.1 uses the official main_capacity max-iteration formula M^(F-1)/F * iter.fac or explicit upstream iter.max, not the old Level 1F.3 cap=16 harness limit.

