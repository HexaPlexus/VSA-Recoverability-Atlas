# License Decision

## Current State

The repository does not yet contain a top-level `LICENSE` file.

That is a public-release blocker.

## Decision Constraint

Do not guess the owner's preferred public license silently.

## Practical Options

| option | strengths | cautions |
| --- | --- | --- |
| `Apache-2.0` | permissive, explicit patent grant, common for research and infrastructure code | slightly longer text; owner must agree |
| `MIT` | short and common, simple for a public code release | no explicit patent grant |
| `BSD-3-Clause` | permissive, familiar to scientific Python users | also lacks Apache-style patent language |

## Recommended Default

If the owner wants an explicit patent grant and a conventional public research-code license, the most practical default is:

`Apache-2.0`

If the owner wants the shortest permissive option and is comfortable without an explicit patent grant:

`MIT`

## Why This Is Still Blocked

The repository contains:

- original research code,
- historical artifacts,
- public-facing manuscript scaffolding,
- and references to upstream methods.

That is enough public surface area that the top-level licensing choice should be intentional rather than inferred.
