# Recoverability Cost Matrix

| Method | More dimensions | More bits per coordinate | Exact side information | Structured code | More decoder compute | Restricted search domain | External context | Reduced coverage / abstention | Exact fallback | Observed benefit | Observed limitation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAP resonator baseline | no | no | no | no | yes | optional | optional | yes | optional | bounded recoverability in intermediate region | capacity collapse and compute saturation |
| Level 1 semantic context routing | no | no | no | no | sometimes less | yes | yes | yes | yes | beats random subsets in tested envelope | needs fallback and bounded claims |
| NeCo / generic linear clean U1 | not primary mechanism | no | no | yes | GF(2) solve cost | yes | no | task-limited | no | clean U1 exact recovery | no noisy superiority claim |
| Symbolic exact baseline | no | exact tuple storage | yes | yes | low | exact | no | no | built in | dominates clean U1 | changes the task by preserving exact structure |
| Semantic LSH trace routing | no | no | trace sidecar for validation | routing projections | routing + reranking | yes | no | yes | yes | useful trace-neighborhood locality | loses to exact packed scan at N=10k |
| Exact packed binary scan | no | packed bits only | trace sidecar for validation | no | exact scan cost | no | no | ambiguity only | n/a | best practical frontier at tested N=10k | may lose at larger scale; not evaluated there yet |
| Cross-substrate MAP/BCF portfolio | no | no | no | dual native encodings | sometimes cumulative | static threshold or cascade | no | yes | no | easy-cell latency trimming through a trivial static route | BCF dominated the hard/non-easy frontier, so no residual instance-level oracle value survived |
| Exact first-order sidecar DAG | no | manifest bytes | yes | exact DAG | recursive replay | exact | no | typed failures only | yes | safe exact replay after record retrieval | does not solve initial record localization |
| Inline packed manifest | possibly if fixed-total | manifest bytes | yes | exact DAG | recursive replay | exact | no | typed failures only | yes | no extra scientific benefit over sidecar | packaging alone did not justify itself |
| Exact carried trace token | optional trace dims | exact token bits | yes | exact token / ECC | low | exact | no | yes under corruption | optional | helps detached activation | placement-specific capsule advantage not supported |
| Conflict-guided tags | sometimes | yes | no | weak sign hints only | repair search | no | no | no | no | none that survived controls | equal-bit extra dimensions dominated |
| Decoder-certified atomic admission | no | no | no | candidate-pool selection | high offline insertion cost | indirectly | no | possible no-commit | no | not stably supported | causal advantage not confirmed |
| Block-LUT residue plane | no | quantized residue tokens | MAP-I upper bound only | block dictionary | soft LUT weighting | no | no | possible thresholding | no | soft information beats sign-only | dictionary complexity lost to equal-bit extra dimensions |
