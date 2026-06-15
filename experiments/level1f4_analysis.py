from pathlib import Path

from cgrn_hsr.level1f4_analysis import build_level1f4


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    build_level1f4(root)
