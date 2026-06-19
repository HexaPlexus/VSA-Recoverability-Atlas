# Secret Scan Preparation

## Tool availability

- `gitleaks`: not available in the current local environment
- `trufflehog`: not available in the current local environment

No new binaries were installed automatically for this stage.

## Current status

`PUBLIC_RELEASE_P2_SECRET_SCAN_PENDING`

## Safe local commands to run later

### Gitleaks

```powershell
gitleaks git --report-format json --report-path gitleaks-report.json .
```

### TruffleHog

```powershell
trufflehog git file://. --json > trufflehog-report.json
```

## Minimal fallback heuristics already used historically

These do **not** replace a dedicated history-aware scan:

```powershell
git grep -n -I -E "AKIA|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|ghp_|hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Authorization:|x-api-key|password="

git log -G "AKIA|ghp_|hf_|sk-|Authorization:|x-api-key|password=" --all --oneline
```

## If a real credential is found

Do not print the credential into logs or commit messages.

Required status:

- `BLOCK_PUBLIC_RELEASE`
- `REQUIRE_CREDENTIAL_ROTATION`
- `REQUIRE_HISTORY_SANITIZATION`

## Release interpretation

External private review of the manuscript can proceed without a public push, but public repository release should remain blocked until a dedicated history-aware secret scan is completed.
