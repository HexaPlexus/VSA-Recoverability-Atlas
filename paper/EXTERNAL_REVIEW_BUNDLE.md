# External Review Bundle

## Default reviewer-facing contents

Send only the minimum package needed for the selected reviewer:

1. `paper/release_candidate/manuscript_rc1.md`
2. `paper/release_candidate/abstract.txt`
3. `paper/review_packets/01_TECHNICAL_ONE_PAGER.md`
4. the relevant specialist packet from `paper/review_packets/`
5. `paper/review_packets/REVIEW_RESPONSE_FORM.md`

## Optional additions

- `paper/review_packets/00_PLAIN_LANGUAGE_SYNOPSIS.md` for general readers
- `paper/release_candidate/figure_captions.md`
- `paper/release_candidate/table_captions.md`
- repository link, only after owner approval

## Do not send by default

- raw JSONL trial outputs
- the full supplementary evidence atlas
- complete Git history
- every protocol artifact in the repository
- any owner-private metadata placeholder

## Where deeper evidence lives if requested

- evidence registry: `paper/evidence_registry.yaml`
- claim ledger: `paper/claim_ledger.yaml`
- prior-art registry: `paper/prior_art_registry.yaml`
- reproducibility validators: `scripts/validate_evidence_registry.py`
- frozen scientific artifacts: `results/`

## Bundle purpose

The bundle is designed for modular, section-level external review rather than a request that any one reader verify the entire atlas.
