from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.oracle_portfolio_complementarity import run_oracle_portfolio


def main() -> None:
    run_oracle_portfolio(ROOT)


if __name__ == "__main__":
    main()
