# Level 2C Portable Context Policy

Schema version: `level2c-splink-context-policy-v1`

## Scope

- Native resolver: Splink probabilistic matcher.
- Policy seam: external context chooses blocking template, candidate budget, and safe fallback only.
- Forbidden: custom matcher, custom ER, broad controller framework, CNM runtime.

## Public Dataset

- FEBRL4a / FEBRL4b via Splink public datasets.
- Canonical table: `febrl4a` originals.
- Query table: `febrl4b` duplicates.
- Ground truth: `entity_id` recovered from `rec_id`.

## Arms

- `native_standard_blocking`
- `random_size_matched_blocking`
- `external_context_blocking`
- `external_context_blocking_with_safe_fallback`
- `oracle_blocking_ceiling`

## Context Contract

```text
ContextRoutingDecision:
    context_hypotheses
    context_confidence
    blocking_policy_id
    blocking_parameters
    candidate_budget
    fallback_policy
    provenance
```

## Notes

- Matcher parameters are frozen once and reused across all arms.
- Context error is injected only into routing metadata, never into labels or native records.
- Safe fallback re-runs Splink with a fresh broad blocking template.
