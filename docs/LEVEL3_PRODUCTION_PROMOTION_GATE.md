# Level 3 Production Promotion Gate

Schema version: `level3-0-substrate-audit-v1`

A substrate may be proposed for the subject only if all of the following hold:

- wins or is nondominated on a subject-relevant task.
- implementation is reproducible and maintainable.
- license is acceptable.
- codebook supports required insertion or update semantics.
- failure can be detected or safely surfaced.
- memory and latency fit target hardware.
- beats non-VSA alternatives for that exact contract.

## Anti-NIH reminder

Non-VSA alternatives must be considered explicitly:

- exact indexed retrieval for exact-key cleanup.
- enumeration or algebraic oracle at tiny scale.
- non-VSA symbolic or linear-system baselines where the task contract makes them natural.

## Not enough

- one isolated easy-cell win.
- tiny non-robust accuracy lift.
- faster setup but slower decode.
- better equal-D score with worse byte or compute budget.

If the gate is not met, status stays `RESEARCH_ONLY`.
