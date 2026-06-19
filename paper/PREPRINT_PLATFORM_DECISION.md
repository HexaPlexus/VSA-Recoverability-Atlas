# Preprint Platform Decision

This is a comparison package only. No platform was selected automatically and no upload was performed.

## Evaluation criteria

- subject fit
- moderation or screening requirements
- versioning
- DOI support
- GitHub or software-archive fit
- file-size / asset practicality
- licensing posture
- discoverability for the likely audience
- review workflow compatibility

## Candidates

### 1. arXiv

- Official sources:
  - [About arXiv](https://arxiv.org/about)
  - [Submission guidance](https://info.arxiv.org/help/submit/index.html)
  - [Review article policy note](https://blog.arxiv.org/2025/10/31/joint-statement-on-arxiv-submission-criteria-and-moderation-practices/)
- Strengths:
  - best subject-fit discoverability for theoretical CS / AI / HDC-adjacent readers
  - strong versioning norm
  - widely recognized preprint venue in the target audience
- Risks:
  - as of the October 31, 2025 policy statement, arXiv explicitly says it does not accept review articles in computer science
  - this manuscript includes a systematic mapping component and may be interpreted as partly review-like unless framed clearly as an empirical atlas and design-framework paper
  - no DOI-centric archival positioning in the same sense as Zenodo
- Practical interpretation:
  - best discoverability if moderators accept the framing
  - highest policy risk if the manuscript is presented primarily as a review

### 2. OSF Preprints

- Official source:
  - [OSF Preprints help](https://help.osf.io/article/385-upload-preprints)
- Strengths:
  - general-purpose preprint workflow
  - flexible for independent researchers
  - easier fit for interdisciplinary work that is not cleanly aligned to one subject silo
- Risks:
  - weaker field-specific discoverability than arXiv for this audience
  - metadata, DOI, and moderation expectations should be rechecked at upload time because OSF workflows can vary by service layer
- Practical interpretation:
  - good fallback if arXiv fit is uncertain
  - less natural as the primary discovery surface for VSA/HDC specialists

### 3. Zenodo

- Official sources:
  - [About Zenodo](https://about.zenodo.org/)
  - [Zenodo help](https://help.zenodo.org/)
- Strengths:
  - DOI-centric archival workflow
  - excellent for versioned software, supplementary artifacts, and release snapshots
  - strong GitHub and artifact-release compatibility
- Risks:
  - weaker manuscript-first community discoverability than arXiv
  - better suited as an archival companion than as the only discussion-facing preprint surface
- Practical interpretation:
  - excellent archive of the repository snapshot and review package
  - probably best used together with, not instead of, a manuscript-centric preprint venue

### 4. Research Square

- Official sources:
  - [Research Square preprints](https://www.researchsquare.com/)
  - [Author help](https://help.researchsquare.com/)
- Strengths:
  - manuscript-centered workflow
  - visible preprint presentation and versioning
  - useful if later paired with a journal-integrated review path
- Risks:
  - less natural than arXiv for the target theoretical-computing readership
  - stronger publisher-workflow feel than a repository-first independent release
- Practical interpretation:
  - plausible manuscript host
  - not the obvious first choice for this project's likely specialist readership

## Current recommendation package

1. If the owner wants strongest field discoverability and the manuscript framing can clearly survive arXiv moderation, prefer `arXiv` plus an archival artifact mirror such as `Zenodo`.
2. If arXiv fit is uncertain because the mapping component reads too much like a review article, prefer `OSF Preprints` or `Research Square` for the manuscript and `Zenodo` for the archival repository snapshot.
3. Do not choose a platform before the owner decides:
   - public author identity
   - license package
   - public repository URL
   - whether the paper is being framed primarily as an empirical atlas, a scoping review, or both
