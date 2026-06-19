# Clean-Checkout CI Repair

## Scope

This note documents the repair for the first public GitHub Actions failures after the external-review release branch was pushed. The goal of the repair is narrow:

- make `python scripts/validate_evidence_registry.py` pass from a clean Linux checkout;
- make `python -m pytest -q` pass from the same checkout;
- preserve frozen scientific artifacts, protocol hashes, raw trial data, and held-out status.

## Original failures

### 1. Unknown commit reference for historical evidence entries

- Symptom: the validator rejected multiple historical commit references.
- Root cause: GitHub Actions used the default shallow checkout, so historical ancestor commits were missing from the local object database.
- Fix: require full history in `.github/workflows/tests.yml` with `fetch-depth: 0`.
- Regression test: `test_workflow_uses_full_history_checkout`.
- Final status: fixed; audited historical references resolve as existing ancestors of `HEAD`.

### 2. Manuscript hardware scope marker missing

- Symptom: CI reported that the manuscript hardware section was missing the required scope guard.
- Root cause: the validator previously depended on brittle wording checks and the generated-manuscript path could drift away from the canonical manuscript.
- Fix:
  - keep `paper/manuscript.md` as the canonical source;
  - validate the presence of the semantic markers `literature-only` and `not measured in this repository`;
  - stop regenerating the canonical manuscript inside `scripts/build_evidence_tables.py`.
- Regression test: `test_hardware_scope_markers_present`.
- Final status: fixed.

### 3. Abstract word count out of range

- Symptom: CI saw a short abstract (`133` words).
- Root cause: `scripts/build_evidence_tables.py` overwrote the canonical manuscript with a generated scaffold, and the release candidate was then copied from that truncated file.
- Fix:
  - preserve `paper/manuscript.md` as the canonical full draft;
  - extract the abstract deterministically from the canonical manuscript during release-candidate generation;
  - validate the word count against the canonical manuscript, not a stale derivative copy.
- Regression tests:
  - `test_release_candidate_rebuild_and_manifest`
  - `test_word_counts_use_full_manuscript`
  - `test_build_evidence_tables_does_not_mutate_canonical_manuscript`
- Final status: fixed.

### 4. Manuscript full-draft word count too small

- Symptom: CI saw a truncated manuscript (`1981` words).
- Root cause: same as the abstract failure: canonical manuscript overwrite by `scripts/build_evidence_tables.py`.
- Fix: remove canonical manuscript generation from `scripts/build_evidence_tables.py` and rebuild the release candidate only from `paper/manuscript.md`.
- Regression tests:
  - `test_word_counts_use_full_manuscript`
  - `test_build_evidence_tables_does_not_mutate_canonical_manuscript`
- Final status: fixed.

### 5. Review packets reference missing manuscript sections

- Symptom: review packets referenced sections that CI could not resolve in the release candidate.
- Root cause: the release candidate had become a copy of the truncated generated manuscript rather than the canonical full draft.
- Fix:
  - rebuild `paper/release_candidate/manuscript_rc1.md` as a deterministic copy of the canonical manuscript;
  - resolve packet references against extracted Markdown headings from the rebuilt release candidate.
- Regression test: `test_review_packet_sections_resolve`.
- Final status: fixed.

### 6. Unknown generating_commit in release manifest

- Symptom: CI could not validate the manifest commit field.
- Root cause: the original field semantics were ambiguous and tied too closely to the artifact file that contained the manifest itself.
- Fix:
  - rename the field to `generated_from_commit`;
  - document its meaning as the clean ancestor commit whose tracked inputs were used to generate the release artifacts;
  - validate that the commit exists and is an ancestor of `HEAD`.
- Regression test: `test_release_candidate_rebuild_and_manifest`.
- Final status: fixed.

### 7. Release manifest hash mismatches for manuscript, claim ledger, evidence registry, supplement, and figures

- Symptom: all text-heavy release artifacts failed manifest hash validation at once.
- Root cause:
  - stale release manifest after manuscript drift; and
  - platform-sensitive hashing due to Windows/Linux newline differences.
- Fix:
  - add shared canonical text hashing in `src/cgrn_hsr/release_artifacts.py`;
  - normalize CRLF/CR to LF only for known text formats;
  - reuse the same helper in both release generation and validation;
  - rebuild the release manifest last.
- Regression tests:
  - `test_canonical_hash_is_line_ending_independent`
  - `test_release_candidate_rebuild_and_manifest`
- Final status: fixed.

## Deterministic rebuild order

The repaired release-validation order is:

1. build manuscript figures;
2. build release candidate;
3. build release manifest last as part of the release-candidate script;
4. validate;
5. run tests;
6. assert `git diff --exit-code`.

`scripts/build_evidence_tables.py` remains covered by regression tests, but it is no longer part of the clean-checkout release-validation path because this repair stage is about canonical manuscript / release artifacts / validator parity, not a repository-wide table refresh.

## Clean-checkout parity

The workflow now mirrors the clean local rebuild path:

1. full-history checkout;
2. Python setup and dependency install;
3. release artifact rebuild;
4. validator;
5. pytest;
6. final `git diff --exit-code`.

## Scientific integrity boundary

This repair does **not**:

- rerun experiments;
- change frozen results;
- alter raw trial data;
- modify held-out status;
- revise scientific verdicts;
- mutate protocol hashes.

The only manuscript change in scope is explicit clarification of literature-only hardware scope where needed for validator semantics.
