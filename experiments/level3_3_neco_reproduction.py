from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.level3_3_neco_reproduction import run_level3_3


def main() -> None:
    run_level3_3(ROOT)


if __name__ == "__main__":
    main()
