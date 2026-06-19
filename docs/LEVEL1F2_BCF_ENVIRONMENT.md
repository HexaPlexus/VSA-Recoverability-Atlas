# Level 1F.2 BCF Environment

This audit intentionally kept the core repo environment unchanged:

- Windows host: CPython `3.14.5`, `torch 2.12.0+cpu`
- Core lock: [`pylock.toml`](../pylock.toml)
- Competitor environment: separate WSL2 Ubuntu Conda env

## Upstream

- Repository: [IBM/in-memory-factorizer](https://github.com/IBM/in-memory-factorizer)
- Pinned commit: `a353f1e918dcb515cad4a89c8e47ce24668954a7`
- License: Apache-2.0

## Chosen environment

Preferred route `WSL2/Ubuntu + conda Python 3.11 + CUDA` was viable on this machine:

- WSL distro: Ubuntu `24.04.4 LTS`
- Python: `3.11.15`
- PyTorch: `2.5.1+cu121`
- GPU: `NVIDIA GeForce RTX 3060`

The first attempt using the upstream-style `conda install pytorch torchvision pytorch-cuda=12.1 -c pytorch -c nvidia` created an env where `import torch` failed with:

```text
undefined symbol: iJIT_NotifyEvent
```

That was treated as an environment packaging issue, not an upstream algorithm blocker. The final reproducible competitor env stayed in the same preferred class, but used the official CUDA 12.1 PyTorch wheels inside the separate conda env.

## Reproduction commands

Create the competitor env:

```bash
conda create -y -n ibm-bcf-audit-cu121 python=3.11 pip
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r "${REPO_ROOT}/competitors/ibm_in_memory_factorizer/requirements.txt"
```

Validate CUDA from inside WSL:

```bash
"${BCF_AUDIT_PYTHON}" -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

Run the official tiny smoke from the pinned upstream clone:

```bash
cd "${REPO_ROOT}/competitors/ibm_in_memory_factorizer"
"${BCF_AUDIT_PYTHON}" main_capacity.py --custom-config "${REPO_ROOT}/competitors/ibm_in_memory_factorizer/.audit_runtime/200a_bcf_smoke_config.json"
```

## Environment record

The audited competitor environment was exported to:

- [`competitors/ibm_bcf/environment.lock.yml`](../competitors/ibm_bcf/environment.lock.yml)

This file is intentionally separate from the core Windows lock and must not be merged into `pylock.toml`.
