from __future__ import annotations

from pathlib import Path

from cgrn_hsr.self_describing_record import run_self_describing_record


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    run_self_describing_record(repo_root)


if __name__ == "__main__":
    main()
