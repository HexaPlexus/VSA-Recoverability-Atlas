from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.level3_0_audit import write_level3_0_artifacts


def main() -> None:
    write_level3_0_artifacts(ROOT)


if __name__ == "__main__":
    main()
