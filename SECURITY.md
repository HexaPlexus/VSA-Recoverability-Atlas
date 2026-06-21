# Security Policy

This repository is a public research codebase, not a production service.

## Reporting

- Do not open a public issue containing credentials, tokens, private paths, or other sensitive material.
- Use GitHub Private Vulnerability Reporting or GitHub Security Advisories when that reporting path is available for the repository.
- Otherwise, report potential vulnerabilities privately through GitHub rather than a public issue.
- If you find a secret or personal-data leak in tracked files or history, report it privately to the repository owner and classify it as a public-release blocker.

## Scope

The most important security issues for this repository are:

- exposed credentials,
- personal or machine-specific path leakage,
- unsafe public claims about artifact provenance,
- and silent corruption of frozen scientific artifacts.

## Out of Scope

- Production-service hardening claims.
- Vulnerability bounty expectations.
- Security promises for third-party dependencies beyond their own disclosures.
