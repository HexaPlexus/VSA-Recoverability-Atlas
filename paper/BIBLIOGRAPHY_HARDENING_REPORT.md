# Bibliography Hardening Report

This report records the bibliography hardening pass for the external-review release candidate. It focuses on external-review readiness, not final venue-style perfection.

| Citation key | Status before | Status after | Canonical source | Changes made | Remaining uncertainty |
| --- | --- | --- | --- | --- | --- |
| `plate1995hrr` | core entry complete | verified core | IEEE TNN article | kept title, author, venue, volume, issue, pages; retained stable URL | DOI not yet added |
| `kanerva2009hyperdimensional` | core entry complete | verified core | Cognitive Computation article | kept canonical journal metadata | DOI not yet added |
| `kleyko2022survey_part1` | partial author list | acceptable for RC | published survey + arXiv locator | retained journal and year; left shortened author list style | full author list may be expanded before venue submission |
| `kleyko2023survey_part2` | partial author list | acceptable for RC | published survey + arXiv locator | retained journal and year; left shortened author list style | full author list may be expanded before venue submission |
| `vsa_comparison_2022` | partial author list | acceptable for RC | published article + arXiv locator | retained venue and year | full author list and DOI still desirable |
| `frady2020resonator` | near-complete | verified core | Neural Computation paper | retained canonical title and venue | DOI/pages still desirable |
| `ibm_bcf_repo` | software-only metadata | acceptable for RC | official repository | kept as official implementation source instead of fabricating article metadata | repository citation format may need venue-specific normalization |
| `ibm_bcf_paper` | placeholder authors/venue lineage | unresolved non-core | IBM Research publication page | kept bounded as primary paper / publication page support | canonical author list and final publication metadata still needed |
| `neco_linear_codes` | placeholder author list and suspicious URL suffix | unresolved non-core | published Neural Computation article | kept as bounded literature source | exact canonical article URL and full authors still need confirmation |
| `factorizers_sparse_block_codes` | placeholder author list | unresolved non-core | arXiv primary paper | retained as literature-only structured-code anchor | full author list still needed |
| `gray1998quantization` | complete | verified core | IEEE TIT article | no material changes needed | none for RC |
| `chow_reject_option` | complete | verified core | IEEE TIT article | no material changes needed | none for RC |
| `satzilla2011` | near-complete | verified core | JAIR article | kept canonical title and author list | DOI optional |
| `selective_classification_survey` | venue vague | acceptable for RC | arXiv survey / primary source used in atlas | retained as survey source | final venue normalization still needed |
| `merkle_dag_git` | software/documentation source | acceptable for RC | Git documentation | preserved as official documentation rather than mislabeling as a paper | citation style depends on target venue |
| `concepts_semantic_pointers_2015` | title and venue lineage broad | acceptable for RC | primary paper / arXiv locator | kept as architectural background anchor | final bibliographic normalization still desirable |
| `gosmann2016_spiking_spa` | near-complete | verified core | PLOS ONE article | retained journal, volume, issue, stable URL | DOI can be added later |
| `mimhd_2021` | placeholder authors/venue | unresolved non-core | primary hardware paper | preserved as literature-only hardware source | canonical author list and venue details still needed |
| `fefet_multibit_2022` | placeholder authors | acceptable for RC | Nature Electronics article | retained strong venue and stable URL | full author list still desirable |
| `in_memory_hdc_review_2020` | placeholder authors | acceptable for RC | IEEE review article | retained venue and stable URL | full author list still desirable |
| `fach_fpga_2019` | placeholder authors and venue wording | unresolved non-core | ACM DOI landing page | preserved stable DOI URL | full canonical venue and author list still needed |
| `renner2022_hrn_scene` | placeholder “collaborators” author style | acceptable for RC | arXiv primary source | kept stable arXiv locator and year | full author list desirable |
| `renner2023_hrn_odometry` | placeholder “collaborators” author style | acceptable for RC | arXiv primary source | kept stable arXiv locator and year | full author list desirable |
| `orchard2023_spiking_phasors` | placeholder “collaborators” author style | acceptable for RC | arXiv primary source | kept stable arXiv locator and year | full author list desirable |
| `roodsari2025_nuecc_hdc` | partial metadata | acceptable for RC | Information Sciences DOI | retained journal and DOI | full pages/volume still desirable |
| `loihi2_2021` | hardware-platform note only | acceptable for RC | official Intel platform source used as bounded hardware reference | kept as bounded `@misc`-style hardware source | full publication metadata still desirable if a stable paper citation is chosen |
| `lava_docs_2026` | documentation citation | acceptable for RC | official Lava documentation | retained access date and official URL | final style may need conversion from `@online` |

## Summary

- Bibliographic entries checked: `27`
- Core entries verified for external technical review: MAP, resonator, BCF repository, core surveys, reject-option/portfolio methodology, and the main hardware-scope guards.
- Entries still not fully normalized for venue submission: `ibm_bcf_paper`, `neco_linear_codes`, `factorizers_sparse_block_codes`, `mimhd_2021`, `fach_fpga_2019`, plus several literature-only entries with shortened author lists.

## Release-candidate verdict

The bibliography is strong enough for **distributed technical review** and claim-audit use, but it is not yet fully venue-polished. That is why the final stage verdict remains `BIBLIOGRAPHY_PARTIAL` rather than claiming complete archival hardening.

