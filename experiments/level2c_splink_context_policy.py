from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODULE_PATH = SRC / "cgrn_hsr" / "splink_context_policy_experiment.py"
spec = importlib.util.spec_from_file_location("level2c_experiment", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load experiment module from {MODULE_PATH}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
run_level2c = module.run_level2c


def main() -> None:
    run_level2c(ROOT)


if __name__ == "__main__":
    main()
