# Building the Manuscript

The canonical manuscript source is [manuscript.md](manuscript.md). The publication pipeline is:

`Markdown -> Pandoc + citeproc -> LaTeX -> Tectonic -> qpdf normalization`

Required local tools:

- `pandoc 3.10` or compatible
- `tectonic 0.16+` or compatible
- `qpdf 12+` or compatible
- Python with `pypdf`

Primary command:

```powershell
python scripts/build_manuscript.py --profile reviewer-preprint --allow-dirty
```

Validation command:

```powershell
python scripts/validate_manuscript_pdf.py paper/release_candidate/VSA_Recoverability_Atlas_<short-sha>.pdf
```

Clean-checkout reproduction should omit `--allow-dirty`.
