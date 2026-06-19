from __future__ import annotations

from pathlib import Path

from cgrn_hsr.codebook_residue import run_codebook_residue


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    run_codebook_residue(repo_root)


if __name__ == "__main__":
    main()
