# Level 2B.0 Research Seam

## Verdict

`BUILD` is justified only for one seam: a thin external controller over adopted native systems.

## Candidate seam

> Existing systems already solve exact lookup, fuzzy structured entity resolution, canonical gazetteer matching, data association, cue-based episodic retrieval, and thresholded declarative retrieval. They do not provide a shared external context/routing/budget interface with preserved uncertainty and explicit non-commit authority across heterogeneous native systems. We therefore only allow building a minimal controller that chooses among adopted native resolvers or blocking policies without replacing their internal algorithms.

## What survives overlap audit

- `dedupe` or `Splink` should own structured entity matching.
- `Stone Soup` should own sequential association when temporal identity continuity is the real problem.
- Indexed event/belief stores should own exact temporal state.
- The controller may choose mechanism, candidate budget, fallback, and abstention semantics.

## What does not survive overlap audit

- A custom weighted attribute matcher.
- A custom probabilistic entity resolver.
- A custom multi-hypothesis tracker.
- A claim that 'contextual blocking' is novel without baseline blocking comparisons.
- A claim that cue-based retrieval is new without acknowledging Soar/ACT-R overlap.

## Exact next experiment

If Level 2B proceeds, it should compare:

```text
A. Native resolver with standard blocking
B. Native resolver with context-generated blocking
C. Native resolver with context-generated blocking + safe global fallback
D. Oracle blocking ceiling
E. Optional MAP/VSA blocker only for genuinely distributed non-tabular cues
```

The matcher and downstream indexed belief projection must remain unchanged across A/B/C/D.

## Gate

- If controller gains collapse to ordinary blocking, verdict becomes `ENGINEERING ONLY`.
- If uncertainty cannot survive the controller seam, verdict becomes `BLOCK LEVEL 2B RESEARCH`.
- Otherwise the only allowed build target is the controller seam in problem class `L`.
