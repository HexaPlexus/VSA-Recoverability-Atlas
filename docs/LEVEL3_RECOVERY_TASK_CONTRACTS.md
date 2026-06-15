# Level 3 Recovery Task Contracts

Schema version: `level3-0-substrate-audit-v1`

## Primary question

> Does any existing native representation-decoder pair materially improve the recovery/capacity/noise Pareto frontier over dense MAP plus classic resonator under matched semantic payload, storage and compute budgets?

## Task decomposition

| Task | Name | Status | Observation contract | Output contract | Primary ranking? |
| --- | --- | --- | --- | --- | --- |
| U0 | Known-key cleanup | ACTIVE | Known role or key with bundled role-filler pairs; unbind then cleanup. | One filler per known role/key, plus detected miss if cleanup fails. | yes |
| U1 | Blind single-product factorization | ACTIVE | All factors unknown; x = bind(f1, ..., fF). | Exactly one prediction per factor domain. | yes |
| U2 | Superposed tuple recovery | ACTIVE | x = bundle(bind(tuple_1), ..., bind(tuple_K)). | Tuple set or histogram recovery, not an evaluator-chosen target tuple. | yes |
| U3 | Continuous-value cleanup | SEPARATE_TRACK | Continuous or phase-valued encodings such as FHRR/SSP. | Recovered continuous value or cleanup candidate under the native algebra. | no |
| U4 | Nested structures | DEFERRED | Compositions containing nested bindings or recursively embedded structures. | Structured tree or nested tuple recovery. | no |
| U5 | Open-set factor | DEFERRED_SAFETY_TRACK | At least one factor may be absent from all known candidate domains. | Recovered known factors plus detected unknown or abstention. | no |

## Hard rules

- U0, U1, U2, and U3 remain explicitly separated.
- U2 must recover a tuple set or histogram; selecting one evaluator-preferred tuple is not allowed.
- U3 is a separate continuous-value track and does not share a scoreboard with U0-U2.
- U4 and U5 stay deferred until U0-U2 are closed.
