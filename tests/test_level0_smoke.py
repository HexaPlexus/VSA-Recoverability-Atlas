from __future__ import annotations

import random
from functools import reduce

import numpy as np
import pytest
import torch
import torchhd


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _build_resonator_case(seed: int, dimensions: int = 1000) -> dict[str, torch.Tensor]:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)

    domains = torch.stack(
        [torchhd.random(5, dimensions, "MAP", generator=generator) for _ in range(3)],
        dim=0,
    )
    target_indices = torch.tensor([1, 2, 3], dtype=torch.long)
    targets = torch.stack([domains[i, idx] for i, idx in enumerate(target_indices)], dim=0)
    composite = reduce(torchhd.bind, targets)
    estimates = torch.stack([torchhd.multiset(domains[i]) for i in range(domains.size(0))], dim=0)
    next_estimates = torchhd.resonator(composite, estimates, domains)
    similarities = torchhd.dot_similarity(next_estimates.unsqueeze(-2), domains).squeeze(-2)
    predicted_indices = similarities.argmax(dim=-1)

    return {
        "domains": domains,
        "target_indices": target_indices,
        "targets": targets,
        "composite": composite,
        "estimates": estimates,
        "next_estimates": next_estimates,
        "similarities": similarities,
        "predicted_indices": predicted_indices,
    }


def test_torch_import_tensor_op_and_runtime_info() -> None:
    info = {
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_build": torch.version.cuda,
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_built": torch.backends.cuda.is_built(),
    }
    print("runtime_info=", info)

    x = torch.arange(6, dtype=torch.float32).reshape(2, 3)
    y = (x + 1.0) * 2.0

    assert y.shape == (2, 3)
    assert y.tolist() == [[2.0, 4.0, 6.0], [8.0, 10.0, 12.0]]
    assert torch.isfinite(y).all().item()


def test_torchhd_map_bind_and_resonator_step() -> None:
    _seed_everything(7)
    case = _build_resonator_case(seed=7)

    print("resonator_prediction=", case["predicted_indices"].tolist())
    print("similarities_shape=", tuple(case["similarities"].shape))

    assert tuple(case["domains"].shape) == (3, 5, 1000)
    assert tuple(case["targets"].shape) == (3, 1000)
    assert tuple(case["composite"].shape) == (1000,)
    assert tuple(case["estimates"].shape) == (3, 1000)
    assert tuple(case["next_estimates"].shape) == (3, 1000)
    assert tuple(case["similarities"].shape) == (3, 5)
    assert torch.isfinite(case["next_estimates"]).all().item()
    assert not torch.isnan(case["next_estimates"]).any().item()
    assert not torch.isinf(case["next_estimates"]).any().item()
    assert torch.equal(case["predicted_indices"], case["target_indices"])


def test_seeded_reproducibility() -> None:
    _seed_everything(11)
    first = _build_resonator_case(seed=11)

    _seed_everything(11)
    second = _build_resonator_case(seed=11)

    assert torch.equal(first["domains"], second["domains"])
    assert torch.equal(first["composite"], second["composite"])
    assert torch.equal(first["next_estimates"], second["next_estimates"])
    assert torch.equal(first["predicted_indices"], second["predicted_indices"])


@pytest.mark.optional
def test_optional_minigrid_smoke() -> None:
    pytest.importorskip("minigrid", reason="Install the optional level3 extra to enable MiniGrid smoke tests.")
    gym = pytest.importorskip("gymnasium")

    env = gym.make("MiniGrid-Empty-5x5-v0")
    try:
        observation, info = env.reset(seed=123)
        action = env.action_space.sample()
        next_observation, reward, terminated, truncated, step_info = env.step(action)

        print("minigrid_action=", action)
        print("minigrid_reward=", reward)

        assert isinstance(observation, dict)
        assert isinstance(next_observation, dict)
        assert isinstance(info, dict)
        assert isinstance(step_info, dict)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
    finally:
        env.close()
