# License Decision

## Current State

The repository still has **no top-level `LICENSE` file**. That remains a public-release blocker.

This document prepares the decision package only. It does not choose a license automatically.

## Decision Constraint

Do not guess the owner's preferred public license silently.

The repository now has two distinct licensing surfaces:

1. **source code**
2. **manuscript, original figures, and original tables**

These can be licensed differently.

## Source-code options

| Option | Reuse permissions | Attribution requirements | Patent treatment | Compatibility concerns | Effect on academic reuse |
| --- | --- | --- | --- | --- | --- |
| `Apache-2.0` | broad commercial and non-commercial reuse, modification, redistribution | preserve notice and license text; state changes | explicit patent grant and termination clause | longer text; some users prefer simpler permissive licenses | strong default for open research code where patent clarity matters |
| `MIT` | very broad reuse, modification, redistribution | preserve copyright and license notice | no explicit patent grant | simplest permissive choice but less explicit on patents | very common and friction-light for code reuse |
| `BSD-3-Clause` | broad reuse, modification, redistribution | preserve copyright and disclaimer; no endorsement | no explicit patent grant | slightly more text than MIT; still permissive | familiar to scientific Python ecosystems |

## Manuscript / figures / tables options

| Option | Reuse permissions | Attribution requirements | Compatibility concerns | Effect on academic reuse |
| --- | --- | --- | --- | --- |
| `CC BY 4.0` | broad reuse, redistribution, adaptation, including commercial reuse | attribution required | permissive; easiest for quotation, adaptation, and derivative review articles | strongest openness for scholarship and educational reuse |
| `CC BY-NC 4.0` | reuse and adaptation allowed for non-commercial purposes | attribution required | ambiguity around “commercial” can deter some educational or publisher reuse | more restrictive, but may feel safer to some authors |
| `All rights reserved` | no automatic reuse beyond fair use / quotation | citation still expected, but adaptation is restricted | may complicate figure reuse, repository bundling, and open preprint workflows | weakest open-science posture |

## Practical recommendation package

### If the owner wants the most conventional permissive research-code release

- Source code: `Apache-2.0`
- Manuscript/figures/tables: `CC BY 4.0`

Why:

- clear code reuse permissions
- explicit patent treatment for source code
- easy figure/table reuse with attribution
- aligns well with open academic review and preprint distribution

### If the owner wants the lightest-weight permissive code license

- Source code: `MIT`
- Manuscript/figures/tables: `CC BY 4.0`

Why:

- simple and common
- minimal friction for repository users
- still keeps manuscript assets openly reusable

### If the owner wants to allow code reuse but reserve tighter control over paper assets

- Source code: `Apache-2.0` or `MIT`
- Manuscript/figures/tables: `CC BY-NC 4.0` or `All rights reserved`

Tradeoff:

- lowers reuse convenience for pedagogical, industrial, or derivative scholarly packaging
- may reduce friction with personal comfort or future publication preferences

## Third-party note

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Upstream methods, dependencies, and official repositories remain separately licensed.

## Why This Is Still Blocked

The repository contains:

- original research code,
- public-facing manuscript assets,
- generated figures and tables,
- historical result artifacts,
- and references to upstream methods and implementations.

That is enough public surface area that the license decision must be explicit and owner-approved before public push.

