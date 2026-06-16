from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cgrn_hsr.level3_5a_noise_audit import environment_snapshot, generate_level3_5a_artifacts


def main() -> None:
    summary = generate_level3_5a_artifacts(ROOT)
    summary["environment"] = environment_snapshot()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

