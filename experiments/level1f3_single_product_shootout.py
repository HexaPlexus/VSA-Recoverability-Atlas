from __future__ import annotations

from pathlib import Path

from cgrn_hsr.single_product_shootout import run_level1f3


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_level1f3(root / "results" / "level1f3")


if __name__ == "__main__":
    main()
