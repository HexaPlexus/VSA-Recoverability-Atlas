from __future__ import annotations

from pathlib import Path

from cgrn_hsr.temporal_memory import run_level2a


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_level2a(root)


if __name__ == "__main__":
    main()
