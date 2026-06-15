from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.level3_1_experiment import run_level3_1


def main() -> None:
    run_level3_1(ROOT)


if __name__ == "__main__":
    main()
