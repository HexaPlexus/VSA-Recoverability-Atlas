# Level 2B Research Closure

Checkpoint: `8b7b24ab72962873075631d8dfd7d6def3e51f73`

Status: documentation-only closure for `Level 2B.0.1`

## Verdict

Level 2B entity-resolution research: `BLOCKED / ADOPT EXISTING`

General mechanism routing: `ADAPT EXISTING METAREASONING`

Typed authority seam: `ENGINEERING COMPOSE + PROVISIONAL THIN BUILD`

Portable external context controller: `RESEARCH HYPOTHESIS`

CNM: `DEFERRED`

## L1-L10 Verdict Table

| Seam | Verdict | Prior art overlap | Why broad BUILD is rejected |
| --- | --- | --- | --- |
| L1 mechanism selection | `ADOPT` | Rice algorithm selection problem, portfolio methods, SATzilla | Already a mature problem class. |
| L2 portfolio scheduling | `ADOPT` | Algorithm portfolios and schedule selection | Portfolio construction is established prior art. |
| L3 budget allocation | `ADAPT` | Rational metareasoning, value of computation, bounded optimality | Budgeting should reuse known metareasoning principles. |
| L4 continue/stop/fallback | `ADAPT` | Anytime algorithms, interruptible computation, stopping under deadlines | Stop/continue logic is not new science here. |
| L5 cost-aware objective | `ADOPT` | Resource-rational and utility-aware computation allocation | Objective shaping belongs to existing theory. |
| L6 native uncertainty normalization | `COMPOSE` | Native confidence outputs already exist in ER/tracking systems | Only a typed glue layer is needed. |
| L7 authority-controlled non-commit | `COMPOSE` | Unresolved/no-match thresholds and deferred commitment already exist | Novelty can only be in integration across mechanisms. |
| L8 cross-mechanism provenance | `COMPOSE` | Provenance logging is engineering, not a new inference algorithm | Requires normalized records, not new theory. |
| L9 shared external context interface | `COMPOSE` | Existing systems expose inputs, scores, and costs, but not a shared interface | A typed adapter is integration work. |
| L10 portable context policy across heterogeneous mechanisms | `BUILD` (thin, hypothesis-only) | No audited system directly supplied this exact portable context-and-authority seam | Only allowed as a narrow research prototype, not as a broad controller framework. |

## Prior-Art Closure

### Per-instance algorithm selection

- Rice's algorithm selection formulation already covers instance features, mechanism selection, and predicted performance.
- Portfolio systems such as SATzilla already cover fallback/default algorithm choice, overhead trade-offs, and schedule selection.
- Therefore Level 2B must not claim novelty for choosing between native mechanisms based on features alone.

### Rational metareasoning

- Russell and Wefald already cover value of computation and the choice of which computation to perform.
- Metalevel MDP and bounded-optimality lines already cover finite budget allocation, continue-vs-terminate decisions, and metareasoning cost.
- Therefore Level 2B must not claim novelty for cost-aware routing or compute allocation alone.

### Anytime and adaptive computation

- Interruptible anytime computation and performance-profile literature already cover quality as a function of compute and stopping under deadlines.
- Adaptive Computation Time covers dynamic allocation of compute depth/steps.
- Therefore Level 2B must not claim novelty for adaptive stopping or compute-quality trade-offs alone.

## Engineering Versus Research

| Component | Existing prior art | Required integration | New measurable claim | Classification |
| --- | --- | --- | --- | --- |
| Exact ID lookup | Indexed retrieval | Query-to-key handoff | None | `ADOPTED SCIENCE` |
| Fuzzy ER / Gazetteer | dedupe, Splink | Record adapter | None | `ADOPTED SCIENCE` |
| Candidate blocking | Standard ER blocking | Context-to-block-rule adapter | Only if compared against standard blocking | `ENGINEERING INTEGRATION` |
| Temporal data association | Stone Soup PDA/JPDA/MHT | Observation/state adapter | None | `ADOPTED SCIENCE` |
| Typed adapter surface | Existing native APIs | Shared return schema | None by itself | `ENGINEERING INTEGRATION` |
| Uncertainty normalization | Native scores/confidences | Scale and provenance normalization | None by itself | `ENGINEERING INTEGRATION` |
| Authority-controlled non-commit | No-match thresholds, deferred commitment | Commit/abstain authorization layer | Only if safety benefit is isolated experimentally | `ENGINEERING INTEGRATION` |
| Portable external context policy | No exact audited drop-in equivalent across heterogeneous native mechanisms | One narrow policy seam over unchanged native systems | Yes, if it improves utility while preserving uncertainty under context error | `RESEARCH PROTOTYPE` |
| CNM / dynamic H2 context handles | Multiple adjacent paradigms exist, but no accepted internal contract here | None yet | Not yet framed as a bounded seam | `BLOCKED NIH` |

## Allowed Thin Build Seam

```text
MechanismAdapter
    native candidates
    native uncertainty
    provenance
    estimated or observed cost

AuthorityController
    provisional acceptance
    request expansion
    switch mechanism
    abstain
    transactional commit authorization
```

Constraints:

- Must not reimplement matcher, tracker, factorizer, scheduler, confidence model, or value-of-computation theory.
- Must treat native algorithms as opaque mechanisms with explicit inputs/outputs.
- Must count controller overhead in total compute.

## Final Surviving Hypothesis

Status: `HYPOTHESIS`

> A shared external context representation may portably control candidate fields and resource allocation across heterogeneous native mechanisms while preserving native uncertainty and preventing irreversible belief commit under context error.

This is not confirmed novelty. It is only the narrow remaining hypothesis after prior-art closure.

## Future Experiment Contract

Design only, not executed here:

```text
A. native mechanism with its standard selection or blocking
B. native mechanism with external context policy
C. external context policy plus safe broad fallback
D. oracle routing or budget ceiling
```

Native algorithms must remain unchanged.

Primary metrics:

- downstream utility
- false commit rate
- coverage
- candidate recall
- fallback rate
- mechanism-switch rate
- total compute including controller overhead

Mandatory ablations:

- context only
- algorithm-selection baseline
- value-of-computation baseline
- context plus authority boundary

The experiment must distinguish ordinary algorithm-selection benefit from authority-preserving context-controller benefit.

## Adopted

- exact identity lookup
- fuzzy ER and gazetteer matching
- candidate blocking
- temporal data association
- multi-hypothesis tracking
- cue-based retrieval
- temporal belief projection patterns
- algorithm selection
- rational budget allocation
- stopping and anytime principles

## Integration Work Only

- wrapping native outputs
- normalizing provenance
- invoking resolvers
- indexed belief lookup
- typed adapters

## Remaining Hypothesis

- shared context representation across heterogeneous mechanisms
- uncertainty-preserving authority boundary
- safe expansion under context error
- transactional non-commit

## Deferred

- Context Navigation Memory specification
- dynamic H2 context handles
- open-world context formation
- context consolidation
- publication-grade BCF confirmation

## Closure Path

Level 2B should not proceed as custom entity-resolution research. If resumed, it should resume only as a narrow controller experiment over adopted native mechanisms, or stay blocked as pure integration.
