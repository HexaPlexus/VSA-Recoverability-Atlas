from __future__ import annotations

from pathlib import Path

from cgrn_hsr.exact_capsule_contract_closure import run_exact_capsule_contract_closure


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    analysis = run_exact_capsule_contract_closure(repo_root)
    print(analysis["build_verdict"])
    print(analysis["scientific_verdict"])
    print(analysis["implementation_verdict"])


if __name__ == "__main__":
    main()
