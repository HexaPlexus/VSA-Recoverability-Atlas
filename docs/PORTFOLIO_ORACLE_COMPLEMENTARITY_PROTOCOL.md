# Cross-Substrate Oracle Complementarity Protocol v0.1

## Scope

- Stage: `Cross-Substrate Oracle Complementarity Audit v0.1`
- Status:
  - `ADOPT_EXISTING_METHODS`
  - `COMMON_HARNESS`
  - `PAIRED_DEVELOPMENT_EVALUATION`
  - `ORACLE_PORTFOLIO_AUDIT`
  - `NO_ROUTER_YET`
  - `NO_HARDWARE_YET`
  - `NO_NEW_VSA_HYPOTHESIS`

## Common Task Contract

- Clean single-product factorization only
- `F = 3`
- Factor-specific domains
- Ordered designated target tuple
- Same semantic factor IDs, tuple IDs, trial seeds and metadata across methods
- Each substrate receives its own lawful native encoding

## Frozen Cells

- `M = 10`
- `M = 22`
- `M = 31`
- `M = 68`

## Frozen Methods

- `MAP_D512_FAST`
- `MAP_D1024_FAST`
- `MAP_D1024_ROBUST`
- `BCF_NATIVE`
- `ABSTAIN`

Optional linear-code comparison is excluded in v0.1 because this stage is restricted to already-integrated MAP/BCF factorization adapters under the common clean `F=3` harness.

## Splits

- `PILOT_RUNTIME`: 16 paired trials per cell
- `PORTFOLIO_CALIBRATION`: 32 paired trials per cell
- `FINAL_DEVELOPMENT_EVALUATION`: 64 paired trials per cell

Pilot outcomes are not used to retune methods, thresholds, or route families.

## Verifier Contract

- `VERIFIED_ACCEPT`
- `VERIFIED_REJECT`
- `INSUFFICIENT_EVIDENCE`
- `METHOD_EXCEPTION`
- `BUDGET_EXHAUSTED`

The audit tracks:

- ground-truth correctness
- verifier acceptance
- correct-and-accepted
- wrong-and-accepted
- correct-but-rejected

## Cost Modes

- `PREMATERIALIZED_ALL_VIEWS`
- `LAZY_FALLBACK_VIEW`

Dual native representation cost is counted explicitly whenever a portfolio can invoke more than one substrate family.

## Prospective Gates

- Oracle gain threshold: absolute `0.05`
- Rescue-rate threshold: `0.10`
- Rescue-count threshold: `4`
- Verifier-constrained deployable gain threshold: absolute `0.03`
- Static-route sufficiency:
  - closes at least `90%` of oracle gain, or
  - leaves at most `0.02` residual absolute regret

## Forbidden Moves

- learned router
- practical instance router before oracle evidence
- hidden-state handoff between incompatible substrates
- hardware modelling
- held-out execution
