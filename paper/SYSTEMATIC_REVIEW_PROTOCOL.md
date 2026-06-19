# Systematic Recoverability Mapping Protocol v0.1

## Review Type

This stage is a **systematic mapping / scoping review**, not a numerical meta-analysis.

Reason:

- VSA/HDC papers use different algebras, dimensions, codebooks, task contracts, noise models, and hardware assumptions.
- Repository experiments span clean factorization, context-conditioned search, side-information preservation, trace retrieval, and exact replay.
- Cross-paper accuracy, latency, and memory values are not lawful to collapse into a single global leaderboard without a common reproduction contract.

## Research Questions

### RQ1

Which VSA/HDC representations, algebras, and decoders are used for recovery, cleanup, unbinding, and factorization?

### RQ2

Which additional resources are used to improve recoverability?

### RQ3

Which metrics and task contracts are reported, and how comparable are they?

### RQ4

Which failure modes are observed or reported?

### RQ5

Which methods create explicit trade-offs among capacity, accuracy, silent error, latency, memory, energy, preprocessing, and coverage?

### RQ6

Which hardware approaches change the practical cost of dimension, precision, temporal state, or materialization?

### RQ7

Which mechanisms are used for verification, abstention, fallback, exact side information, context restriction, and algorithm selection?

## Search Date

- Frozen search date: `2026-06-19`

## Search Sources

- General web search for primary-source discovery
- arXiv
- ACM Digital Library
- IEEE Xplore
- JAIR / JMLR
- IBM Research publication pages
- official GitHub repositories
- official project documentation pages

## Query Families

### VSA/HDC foundations

- `vector symbolic architecture`
- `hyperdimensional computing`
- `holographic reduced representation`
- `binary spatter code`
- `multiply-add-permute`
- `semantic pointer architecture`

### Recovery and factorization

- `resonator network`
- `hypervector factorization`
- `vector factorization`
- `cleanup memory`
- `unbinding`
- `product recovery`

### Structured recovery

- `block code factorizer`
- `generalized sparse block code`
- `linear code hyperdimensional computing`

### Precision and soft information

- `multi-bit HDC`
- `quantized HDC`
- `integer accumulator HDC`
- `soft-decision decoding hyperdimensional`

### Hardware

- `FPGA hyperdimensional computing`
- `in-memory HDC`
- `neuromorphic VSA`
- `spiking semantic pointer`
- `Loihi VSA`
- `procedural hypervector generation`

### Safety and allocation

- `selective prediction`
- `reject option`
- `algorithm portfolio`
- `per-instance algorithm selection`
- `early exit`
- `budgeted inference`
- `cascade`

## Inclusion Criteria

Include a paper or official implementation if it contains at least one of:

- explicit VSA/HDC representation details
- recovery, cleanup, unbinding, or factorization evidence
- capacity, noise, or scaling analysis relevant to recoverability
- hardware implementation, synthesis, or energy/latency evidence for HDC/VSA
- multi-bit, analog, temporal, or structured-code representations
- verification, abstention, fallback, or portfolio mechanisms relevant to recovery

## Exclusion Criteria

Exclude:

- pure application papers with no extractable recoverability contract
- duplicate conference/journal versions with no new recoverability evidence
- marketing-only hardware pages
- papers with no extractable task contract
- secondary summaries when a primary source is available
- methods using unrelated embeddings only

All exclusions must receive a typed reason in `paper/literature_screening.csv`.

## Duplicate Policy

- Prefer the most information-complete primary source.
- Keep an official repository in addition to the paper only when it materially clarifies implementation fidelity or licensing.
- Conference/journal duplicate pairs are collapsed unless the later version adds new recoverability evidence.

## Primary-Source Policy

- Use original papers, official preprints, official repositories, official hardware documentation, or standards whenever available.
- Secondary surveys may be used for discovery, but not as sole evidence for a scientific claim when the primary source is accessible.

## Quality Assessment

For each included item record:

- task contract extractability
- representation/algebra specificity
- decoder and stopping-rule specificity
- metric specificity
- cost-reporting completeness
- failure-mode extractability
- comparability class

## Data Extraction Schema

Each included item should provide, when available:

- citation metadata
- VSA family, algebra, representation, precision, sparsity
- task category and task contract
- dimension, factor count, candidate domains, noise contract
- decoder, iteration/restart/stopping behavior
- side information, external priors, exact metadata
- reported accuracy / latency / memory / energy / hardware
- resource-location tags
- failure modes and limits
- comparability class
- transferable and non-transferable claims

## Comparability Rule

Only `DIRECT_COMMON_HARNESS` entries are lawful for direct numeric ranking against each other.

All other classes are descriptive or contrastive only:

- `CLOSE_TASK_DIFFERENT_IMPLEMENTATION`
- `SAME_MECHANISM_DIFFERENT_CONTRACT`
- `TAXONOMIC_ONLY`
- `HARDWARE_ONLY`
- `THEORETICAL_ONLY`

## Output Artifacts

- `paper/literature_search_log.csv`
- `paper/literature_screening.csv`
- `paper/prior_art_registry.yaml`
- `paper/prior_art_matrix.csv`
- `paper/prior_art_matrix.md`
- `paper/method_resource_atlas.csv`
- `paper/method_resource_atlas.md`

## Frozen Scope Limits

- No new VSA experiments
- No new decoder
- No router
- No FPGA or Lava implementation
- No new held-out execution
