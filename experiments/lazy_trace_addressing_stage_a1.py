from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.lazy_trace_addressing_stage_a1 import run_stage_a1


def main() -> None:
    payload = run_stage_a1(ROOT)
    print(json.dumps(payload["analysis"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
