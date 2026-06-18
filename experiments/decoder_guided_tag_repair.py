from __future__ import annotations

from pathlib import Path

from cgrn_hsr.decoder_guided_tag_repair import run_decoder_guided_tag_repair


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    run_decoder_guided_tag_repair(repo_root)


if __name__ == "__main__":
    main()
