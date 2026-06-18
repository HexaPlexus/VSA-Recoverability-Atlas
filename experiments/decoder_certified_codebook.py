from __future__ import annotations

from pathlib import Path

from cgrn_hsr.decoder_certified_codebook import run_decoder_certified_codebook


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    run_decoder_certified_codebook(repo_root)


if __name__ == "__main__":
    main()
