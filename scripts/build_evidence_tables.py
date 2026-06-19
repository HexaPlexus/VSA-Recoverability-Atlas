from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"

EVIDENCE_STATUSES = {
    "REPRODUCED_IN_REPO",
    "PARTIALLY_REPRODUCED",
    "PAPER_REPRODUCTION",
    "IMPLEMENTATION_AUDITED",
    "LITERATURE_ONLY",
    "DESIGN_ONLY",
    "DEFERRED_HYPOTHESIS",
    "BLOCKED_WITH_EVIDENCE",
    "ADOPTED_ENGINEERING_BASELINE",
}

CLAIM_STATUSES = {
    "CONFIRMED_IN_FROZEN_ENVELOPE",
    "SUPPORTED_DEVELOPMENT_ONLY",
    "DIRECTIONAL_ONLY",
    "NOT_SUPPORTED",
    "BLOCKED",
    "DESIGN_PRINCIPLE",
    "OPEN",
}

COMPARABILITY_CLASSES = {
    "DIRECT_COMMON_HARNESS",
    "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
    "SAME_MECHANISM_DIFFERENT_CONTRACT",
    "TAXONOMIC_ONLY",
    "HARDWARE_ONLY",
    "THEORETICAL_ONLY",
}

LITERATURE_EVIDENCE_STRENGTHS = {
    "PRIMARY_EMPIRICAL",
    "PRIMARY_THEORETICAL",
    "OFFICIAL_IMPLEMENTATION",
    "HARDWARE_SYNTHESIS",
    "PHYSICAL_HARDWARE_MEASUREMENT",
    "SURVEY_ONLY",
    "CONCEPTUAL_ONLY",
}

EVIDENCE_ENTRIES = [
    {
        "hypothesis_id": "level0_dependency_bootstrap",
        "title": "Dependency-locked TorchHD/MAP bootstrap for reproducible local experiments",
        "category": "INFRASTRUCTURE_BASELINE",
        "origin": "Repository bootstrap",
        "evidence_status": "ADOPTED_ENGINEERING_BASELINE",
        "maturity": "STABLE",
        "implementation_status": "ACTIVE",
        "research_question": "Can the repository maintain a minimal reproducible local substrate without custom VSA runtime code?",
        "method": "Pinned Python environment, TorchHD reuse, pytest smoke checks",
        "substrate": "TorchHD MAP",
        "operation_contract": "Environment install and smoke validation",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "N/A",
        "noise_contract": "N/A",
        "information_added": "none",
        "compute_added": "installation and smoke checks only",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "Core repo remains installable without bespoke runtime primitives.",
        "primary_failure_point": "Public release still requires explicit licensing and path hygiene.",
        "safety_outcome": "Pinned dependencies and smoke tests reduce silent environment drift.",
        "cost_outcome": "Small ongoing maintenance cost; no algorithmic novelty claimed.",
        "baselines": ["direct upstream TorchHD install"],
        "controls": ["clean local smoke test"],
        "evidence": {
            "commits": [],
            "protocol_hashes": [],
            "result_paths": [
                "pyproject.toml",
                "pylock.toml",
                "tests/test_level0_smoke.py",
                "DEPENDENCIES.md",
            ],
            "tests": ["tests/test_level0_smoke.py"],
            "execution_scale": "Repository-wide installation baseline",
            "heldout_status": "No held-out component",
        },
        "results": {
            "primary_metrics": ["install succeeds", "core smoke tests pass"],
            "secondary_metrics": ["optional dependency separation"],
            "qualitative_observations": [
                "TorchHD and upstream algebra primitives are reused directly.",
                "The internal cgrn_hsr package is compatibility glue, not a new substrate.",
            ],
        },
        "failure_modes": ["environment drift", "optional dependency confusion"],
        "causal_interpretation": "This stage adopts upstream VSA/HDC primitives rather than inventing a new runtime.",
        "allowed_claims": [
            "The repository has a reproducible local bootstrap path for core CPU experiments."
        ],
        "forbidden_claims": [
            "The bootstrap layer is a novel VSA runtime or decoder."
        ],
        "prior_art": ["TorchHD", "PyTorch packaging", "pytest smoke discipline"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": [
            "Reopen only to adjust dependency pins, Python support, or smoke coverage."
        ],
    },
    {
        "hypothesis_id": "level1_context_conditioned_search",
        "title": "External semantic context can improve candidate routing over random subsets in bounded Level 1 single-product recovery",
        "category": "CONTEXT_CONDITIONED_SEARCH",
        "origin": "Original CGRN-HSR hypothesis, narrowed by Level 1 closures",
        "evidence_status": "REPRODUCED_IN_REPO",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "HISTORICAL_EXPERIMENTS_PRESENT",
        "research_question": "Can external probabilistic context improve candidate routing, compute use, and silent-failure control without changing the underlying MAP geometry?",
        "method": "MAP resonator with context-selected candidate subsets, selective acceptance, and cold global fallback",
        "substrate": "MAP primary; BCF selector transfer audit",
        "operation_contract": "Blind clean single-product factorization with typed factor domains",
        "dimensions": "MAP D512/D1024 development envelopes",
        "factor_count": "F=3",
        "search_space": "Context-selected subsets versus size-matched random subsets and cold global fallback",
        "noise_contract": "Predominantly clean Level 1 envelopes; no universal noisy frontier claim",
        "information_added": "external semantic context",
        "compute_added": "candidate routing and fallback control",
        "prior_added": "schema- and context-conditioned subset selection",
        "exact_side_information": "none",
        "primary_result": "Semantic context beat random candidate selection in tested single-product regimes; cold fallback survived while warm continuation failed.",
        "primary_failure_point": "Warm continuation, cheap probes, and over-broad hierarchical runtime claims did not survive audit.",
        "safety_outcome": "Selective acceptance reduced silent false commitments in the tested envelope.",
        "cost_outcome": "Recoverability gain was paid through external context, routing policy, and fallback compute.",
        "baselines": ["random context", "global MAP", "size-matched random subsets"],
        "controls": ["cold fallback", "selective acceptance", "query-aware context"],
        "evidence": {
            "commits": [],
            "protocol_hashes": [],
            "result_paths": [
                "docs/LEVEL1_RESEARCH_CLOSURE.md",
                "results/level1a",
                "results/level1c",
                "results/level1d",
                "results/level1e",
                "results/level1e1",
                "results/level1f3",
                "results/level1f4",
            ],
            "tests": [
                "tests/test_level1a_baseline.py",
                "tests/test_level1c_context.py",
                "tests/test_level1d_query_context.py",
                "tests/test_level1e_selective_policy.py",
                "tests/test_level1e1_warm_start.py",
                "tests/test_level1f3_single_product_shootout.py",
                "tests/test_level1f4_analysis.py",
            ],
            "execution_scale": "Multiple Level 1 development and held-out slices",
            "heldout_status": "Historical held-out and repaired-held-out boundaries documented in Level 1 closure",
        },
        "results": {
            "primary_metrics": ["candidate recall", "exact factor recovery", "coverage", "silent false commitment"],
            "secondary_metrics": ["fallback rate", "latency", "selective-risk tradeoff"],
            "qualitative_observations": [
                "Context transfer reached the official IBM BCF selector level.",
                "The surviving path is external context -> candidate routing -> native decoder -> accept/fallback/abstain.",
            ],
        },
        "failure_modes": ["false attractor", "context exclusion", "warm continuation collapse"],
        "causal_interpretation": "Observed gain came from search-domain restriction and abstention discipline, not from a new algebra or state-carrying hierarchy.",
        "allowed_claims": [
            "Semantic context beat random candidate selection in the tested Level 1 settings.",
            "The external context-selection seam transferred across MAP and the official IBM BCF selector layer."
        ],
        "forbidden_claims": [
            "Universal substrate independence",
            "Hierarchical resonator continuation as the default runtime",
            "Verifier or lifecycle transfer to BCF beyond the audited selector envelope",
        ],
        "prior_art": ["algorithm selection", "context-gated retrieval", "selective prediction"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": [
            "Reopen only for new typed controller experiments or new public BCF confirmations under fresh seeds."
        ],
    },
    {
        "hypothesis_id": "level1f_holovec_task_mismatch",
        "title": "HoloVec attention resonator is not a fair drop-in competitor under the repository's factor-specific domain contract",
        "category": "COMPETITOR_AUDIT",
        "origin": "Level 1F competitor audit",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "AUDITED_NOT_ADOPTED",
        "research_question": "Can HoloVec be wrapped as a lawful drop-in factorizer for the existing multi-domain benchmark?",
        "method": "Dependency audit and API audit of HoloVec attention cleanup",
        "substrate": "HoloVec attention resonator",
        "operation_contract": "Factorization with factor-specific domains",
        "dimensions": "Audit-level only",
        "factor_count": "F=3 target contract",
        "search_space": "Single shared flat codebook in upstream API",
        "noise_contract": "Not a noise experiment",
        "information_added": "none",
        "compute_added": "dependency and API audit only",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "HoloVec exposes one shared flat codebook and no lawful per-factor domain interface for the benchmark contract.",
        "primary_failure_point": "Task mismatch blocked a fair shootout.",
        "safety_outcome": "Avoided benchmark contamination by refusing a mismatched wrapper.",
        "cost_outcome": "Wrapping without contract parity would have produced a misleading comparison.",
        "baselines": ["existing MAP task contract"],
        "controls": ["dependency metadata", "source inspection"],
        "evidence": {
            "commits": [],
            "protocol_hashes": [],
            "result_paths": [
                "docs/LEVEL3_1_NATIVE_REPRODUCTION.md",
                "results/level1f/dependency_audit.json",
            ],
            "tests": ["tests/test_level1f_holovec_audit.py"],
            "execution_scale": "API and dependency audit",
            "heldout_status": "No held-out component",
        },
        "results": {
            "primary_metrics": ["factor_specific_domains_supported = false"],
            "secondary_metrics": ["installed_with_torch_backend = true"],
            "qualitative_observations": [
                "The package was installable and deterministic on the host.",
                "The blocker was task-contract mismatch, not a build failure.",
            ],
        },
        "failure_modes": ["task mismatch", "benchmark contract mismatch"],
        "causal_interpretation": "A competitor should not be forced into the benchmark by rewriting its semantics.",
        "allowed_claims": ["The audited HoloVec API is not a lawful drop-in substitute for this benchmark contract."],
        "forbidden_claims": ["HoloVec is universally worse than MAP."],
        "prior_art": ["HoloVec", "attention-based cleanup"],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": ["Reopen only if an upstream factor-specific domain API appears."],
    },
    {
        "hypothesis_id": "level1f_bcf_selector_transfer",
        "title": "Official IBM BCF can participate in scoped selector-level comparisons but not yet in full parity claims",
        "category": "SUBSTRATE_COMPARISON",
        "origin": "Level 1F / Level 3.1 BCF audit line",
        "evidence_status": "IMPLEMENTATION_AUDITED",
        "maturity": "SCOPED",
        "implementation_status": "WRAPPED_AUDIT_ONLY",
        "research_question": "Can the official IBM BCF implementation be wrapped lawfully for the repository's single-product benchmark contract?",
        "method": "Official upstream smoke audit, selector-level comparison, and native-envelope reproduction",
        "substrate": "IBM BCF",
        "operation_contract": "Blind clean single-product factorization",
        "dimensions": "D256/D512 scoped envelopes",
        "factor_count": "F=3",
        "search_space": "Typed codebook, official main_capacity path",
        "noise_contract": "Clean scoped development envelope",
        "information_added": "none",
        "compute_added": "native substrate-specific iteration schedule",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "BCF was reproducible as an audited native envelope, but parity claims remain scoped and expensive.",
        "primary_failure_point": "Structured-mixture parity and broad runtime substitution remain unresolved.",
        "safety_outcome": "Contract wrapping stayed faithful to upstream entrypoints and did not rewrite BCF internals.",
        "cost_outcome": "Native BCF benchmarking was substantially more expensive than MAP in repeated subset trials.",
        "baselines": ["MAP global baseline", "random subsets"],
        "controls": ["official upstream entrypoint", "selector-level context transfer"],
        "evidence": {
            "commits": ["dea30d8"],
            "protocol_hashes": [],
            "result_paths": [
                "docs/LEVEL1_RESEARCH_CLOSURE.md",
                "docs/LEVEL3_1_NATIVE_REPRODUCTION.md",
                "results/level3_1/bcf_native_reproduction.json",
            ],
            "tests": [
                "tests/test_level1f2_bcf_audit.py",
                "tests/test_level3_1_native_envelope.py",
            ],
            "execution_scale": "Selector transfer plus small native-envelope reproduction",
            "heldout_status": "Historical Level 1 closure documents repaired-held-out boundaries",
        },
        "results": {
            "primary_metrics": ["exact recovery rate", "iterations", "native operation proxy"],
            "secondary_metrics": ["codebook bytes", "end-to-end time"],
            "qualitative_observations": [
                "Selector-level context transfer was confirmed.",
                "Broad MAP-vs-BCF superiority claims remain limited to the tested envelope.",
            ],
        },
        "failure_modes": ["native substrate mismatch", "compute non-dominance"],
        "causal_interpretation": "BCF remained a lawful comparator only when wrapped as an unchanged native decoder under a scoped task.",
        "allowed_claims": [
            "The official IBM BCF implementation can be reproduced and wrapped for scoped single-product audits.",
            "Context transfer reached the selector level."
        ],
        "forbidden_claims": ["BCF is inherently slower in all settings.", "BCF is a drop-in replacement for the full MAP control stack."],
        "prior_art": ["block-code factorization", "official upstream implementation audits"],
        "architectural_disposition": "IMPLEMENTATION_AUDITED",
        "reopen_conditions": ["Reopen only for fresh public held-out confirmation or new structured-mixture parity protocols."],
    },
    {
        "hypothesis_id": "level2a_temporal_memory_narrow",
        "title": "Approximate semantic retrieval can help temporal replay only as a narrow fallback, while exact indexed location remains stronger",
        "category": "TEMPORAL_RETRIEVAL",
        "origin": "Level 2A temporal memory seam",
        "evidence_status": "PARTIALLY_REPRODUCED",
        "maturity": "NARROW",
        "implementation_status": "EXPERIMENTAL",
        "research_question": "Can semantic retrieval plus abstention provide useful temporal memory behavior without BCF or a new memory system?",
        "method": "Semantic MAP retrieval with abstention and cold fallback versus exact indexed location controls",
        "substrate": "MAP",
        "operation_contract": "Temporal retrieval and replay selection",
        "dimensions": "Scoped development envelope",
        "factor_count": "N/A",
        "search_space": "Episode retrieval under multiple policies",
        "noise_contract": "Task-specific observational variation",
        "information_added": "semantic context over entity memory",
        "compute_added": "fallback passes and abstention",
        "prior_added": "location-relevant context",
        "exact_side_information": "Exact indexed retrieval baseline present",
        "primary_result": "Semantic retrieval was directionally useful, but exact indexed location remained stronger and the verdict stayed narrow.",
        "primary_failure_point": "Semantic retrieval did not justify replacing exact indexed location.",
        "safety_outcome": "Abstention and fallback reduced unsafe guesses.",
        "cost_outcome": "Benefit was modest and subordinate to exact lookup.",
        "baselines": ["exact indexed retrieval", "random context", "cold fallback"],
        "controls": ["oracle episode selection", "latest raw episode"],
        "evidence": {
            "commits": ["5d54748"],
            "protocol_hashes": [],
            "result_paths": ["results/level2a/analysis.json"],
            "tests": ["tests/test_level2a_temporal_memory.py"],
            "execution_scale": "Development plus held-out temporal-memory trials",
            "heldout_status": "Held-out used historically inside Level 2A artifact; no new held-out in release stage",
        },
        "results": {
            "primary_metrics": ["mean utility", "coverage", "selective risk", "compute"],
            "secondary_metrics": ["location inclusion gain", "fallback delta"],
            "qualitative_observations": [
                "Exact indexed retrieval beat semantic retrieval on exact location.",
                "The seam survived only as a narrow fallback-oriented research result.",
            ],
        },
        "failure_modes": ["location misrouting", "coverage collapse"],
        "causal_interpretation": "Approximate retrieval helps only when its cost and uncertainty are controlled by abstention and exact fallback.",
        "allowed_claims": ["Semantic retrieval supplied useful locality in a narrow temporal-memory seam."],
        "forbidden_claims": ["A new memory substrate or replacement for exact indexing."],
        "prior_art": ["temporal retrieval", "approximate associative memory", "abstention"],
        "architectural_disposition": "PARTIALLY_REPRODUCED",
        "reopen_conditions": ["Reopen only for exact-vs-approximate crossover studies with clear utility accounting."],
    },
    {
        "hypothesis_id": "level2b_portable_context_controller",
        "title": "Portable external context control across heterogeneous native mechanisms remains a narrow open hypothesis, not a custom ER architecture",
        "category": "META_CONTROL",
        "origin": "Level 2B prior-art closure",
        "evidence_status": "DEFERRED_HYPOTHESIS",
        "maturity": "HYPOTHESIS_ONLY",
        "implementation_status": "THIN_SEAM_ONLY",
        "research_question": "Is there a residual research seam beyond ordinary algorithm selection and metareasoning for a typed authority-preserving controller?",
        "method": "Prior-art closure and seam isolation over existing matchers, trackers, and resolver outputs",
        "substrate": "Mechanism-agnostic controller seam",
        "operation_contract": "Typed adapter and authority-controller design only",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "Mechanism selection, scheduling, and commit control",
        "noise_contract": "Not executed",
        "information_added": "external context and typed authority state",
        "compute_added": "controller overhead only",
        "prior_added": "algorithm selection and rational metareasoning",
        "exact_side_information": "Native mechanism outputs only",
        "primary_result": "Broad custom entity-resolution research was blocked; only a thin controller seam remained as a deferred hypothesis.",
        "primary_failure_point": "Most of the apparent novelty was already covered by portfolio methods and metareasoning.",
        "safety_outcome": "Typed non-commit remained the only live safety-oriented seam.",
        "cost_outcome": "Any future controller must count its own overhead and justify itself against adopted baselines.",
        "baselines": ["algorithm selection", "portfolio scheduling", "rational metareasoning"],
        "controls": ["thin typed adapter seam"],
        "evidence": {
            "commits": ["8b7b24a"],
            "protocol_hashes": [],
            "result_paths": ["docs/LEVEL2B_RESEARCH_CLOSURE.md", "docs/research/CGRN_HSR_CNM_RESEARCH_SPEC.md"],
            "tests": ["tests/test_level2b0_anti_nih_audit.py", "tests/test_level2b01_meta_control_closure.py"],
            "execution_scale": "Documentation and audit closure",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["prior-art coverage"],
            "secondary_metrics": ["seam classification"],
            "qualitative_observations": [
                "Most candidate seams collapsed into adopted prior art.",
                "Only a portable context-and-authority controller remained as a narrow hypothesis.",
            ],
        },
        "failure_modes": ["NIH controller inflation", "ordinary algorithm-selection restated as new science"],
        "causal_interpretation": "The contribution, if any, can only live in a narrow typed controller seam over adopted mechanisms.",
        "allowed_claims": ["Portable context control is still only a bounded research hypothesis."],
        "forbidden_claims": ["A new entity-resolution architecture or new metareasoning theory."],
        "prior_art": ["Rice algorithm selection", "SATzilla", "rational metareasoning", "anytime algorithms"],
        "architectural_disposition": "DEFERRED_HYPOTHESIS",
        "reopen_conditions": ["Reopen only as a thin controller experiment over unchanged native mechanisms."],
    },
    {
        "hypothesis_id": "level2c_existing_matcher_context_policy",
        "title": "Context policy can be tested as a narrow overlay on an existing matcher without inventing a new matcher",
        "category": "CONTEXT_CONDITIONED_SEARCH",
        "origin": "Level 2C existing-matcher policy seam",
        "evidence_status": "PARTIALLY_REPRODUCED",
        "maturity": "NARROW",
        "implementation_status": "EXPERIMENTAL",
        "research_question": "Can a transparent context policy improve candidate blocking and fallback behavior over an unchanged existing matcher?",
        "method": "Frozen Splink matcher with transparent context policy and safe broad fallback",
        "substrate": "Existing probabilistic matcher (Splink)",
        "operation_contract": "Candidate blocking and matching over fixed matcher internals",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "Context-conditioned blocking with fallback",
        "noise_contract": "Matcher-level development evaluation",
        "information_added": "external context policy",
        "compute_added": "fallback broad-pass when context is narrow",
        "prior_added": "blocking priors",
        "exact_side_information": "none",
        "primary_result": "The policy remained narrow and explicitly forbade claims of a universal context controller or new matcher.",
        "primary_failure_point": "The seam is not evidence for CNM or a new probabilistic matcher.",
        "safety_outcome": "Safe fallback was necessary to avoid catastrophic exclusions.",
        "cost_outcome": "Blocking and matching remain coupled inside the adopted matcher API.",
        "baselines": ["fixed native matcher", "context policy with fallback"],
        "controls": ["broad native re-run"],
        "evidence": {
            "commits": [],
            "protocol_hashes": ["level2c-frozen-protocol-v1"],
            "result_paths": ["results/level2c/analysis.json"],
            "tests": ["tests/test_level2c_splink_context_policy.py"],
            "execution_scale": "Frozen development and held-out matcher policy evaluation",
            "heldout_status": "Historical held-out present inside Level 2C artifacts",
        },
        "results": {
            "primary_metrics": ["candidate-policy portability", "safe fallback behavior"],
            "secondary_metrics": ["matcher notes"],
            "qualitative_observations": [
                "The matcher itself remained unchanged.",
                "The seam survived only as an overlay policy with explicit claim limits.",
            ],
        },
        "failure_modes": ["context exclusion", "policy overclaim"],
        "causal_interpretation": "Any gain belongs to the policy overlay, not to a novel matcher.",
        "allowed_claims": ["Candidate-policy portability beyond VSA can be studied narrowly on an adopted matcher."],
        "forbidden_claims": ["New matcher claim", "CNM/H2 necessity claim"],
        "prior_art": ["blocking policies", "existing matcher overlays", "fallback routing"],
        "architectural_disposition": "PARTIALLY_REPRODUCED",
        "reopen_conditions": ["Reopen only for larger external-matcher comparisons under equal-information contracts."],
    },
    {
        "hypothesis_id": "level3_2_map_budget_robustness",
        "title": "MAP resonator recoverability has a bounded intermediate region shaped by budget, restart policy, and abstention",
        "category": "MAP_RESONATOR_BASELINE",
        "origin": "Level 3.2 and 3.2b MAP baseline line",
        "evidence_status": "REPRODUCED_IN_REPO",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "ACTIVE",
        "research_question": "How far can unchanged MAP resonator recovery be pushed before recoverability accounting demands more compute, more structure, or abstention?",
        "method": "Compute-matched MAP budget robustness and clean U1 confirmation without context",
        "substrate": "MAP resonator",
        "operation_contract": "Blind clean single-product factorization",
        "dimensions": "D512 and D1024 transition-region studies",
        "factor_count": "F=3",
        "search_space": "Global factor domains with restart and iteration budgets",
        "noise_contract": "Clean U1; no noise in this line",
        "information_added": "none",
        "compute_added": "longer/restarted resonator budgets",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "MAP retained a bounded intermediate region rather than an unlimited clean-factorization regime.",
        "primary_failure_point": "More compute alone did not remove the transition-region constraints.",
        "safety_outcome": "Selective abstention and explicit budget accounting stayed necessary.",
        "cost_outcome": "Recoverability improvements required additional decoder compute and still saturated.",
        "baselines": ["shorter MAP budgets", "held-out clean U1 confirmation"],
        "controls": ["no context", "no new decoder", "compute matching"],
        "evidence": {
            "commits": ["86efbb8", "a3ca3b3"],
            "protocol_hashes": [],
            "result_paths": [
                "results/level3_2",
                "results/level3_2b/analysis.json",
                "docs/LEVEL3_2B_MAP_BUDGET_ROBUSTNESS.md",
            ],
            "tests": ["tests/test_level3_2_confirmation.py", "tests/test_level3_2b_map_budget_robustness.py"],
            "execution_scale": "Held-out clean confirmation plus development robustness sweep",
            "heldout_status": "Clean held-out confirmation present for Level 3.2; no release-stage reruns",
        },
        "results": {
            "primary_metrics": ["exact recovery", "trial count", "budget sensitivity"],
            "secondary_metrics": ["restart behavior", "abstention"],
            "qualitative_observations": [
                "The line stayed clean-only and no-context.",
                "The next lawful comparison moved to linear-code and symbolic baselines rather than more MAP retuning.",
            ],
        },
        "failure_modes": ["capacity collapse", "compute non-dominance", "flat reconstruction geometry"],
        "causal_interpretation": "Recoverability cost in MAP can be shifted by more compute, but not eliminated for free.",
        "allowed_claims": ["MAP has a bounded intermediate recoverability region in the tested clean U1 envelope."],
        "forbidden_claims": ["Unlimited clean MAP factorization or universal impossibility for all VSA recovery."],
        "prior_art": ["resonator networks", "iterative factorization", "selective abstention"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only for equal-information comparisons against alternative substrates or exact side information."],
    },
    {
        "hypothesis_id": "level3_3_linear_code_reproduction",
        "title": "The NeCo linear-code paper contract can be reproduced for clean U1 under explicit GF(2) constraints",
        "category": "PAPER_REPRODUCTION",
        "origin": "Level 3.3 reproduction",
        "evidence_status": "PAPER_REPRODUCTION",
        "maturity": "CLOSED",
        "implementation_status": "ACTIVE",
        "research_question": "Can the reported linear-code recovery mechanism be reproduced lawfully in-repo without inventing a new GF(2) framework?",
        "method": "Paper-specific clean U1 reproduction using galois over GF(2)",
        "substrate": "Linear codes / NeCo",
        "operation_contract": "Clean U1 blind single-product factorization",
        "dimensions": "Paper-specific code dimensions",
        "factor_count": "F=3",
        "search_space": "Paper-derived subcode structure",
        "noise_contract": "Clean only",
        "information_added": "structured linear-code substrate",
        "compute_added": "GF(2) linear algebra",
        "prior_added": "subcode structure",
        "exact_side_information": "none",
        "primary_result": "The paper contract was reproduced under explicit common-U1 constraints.",
        "primary_failure_point": "No noise, no broader substrate claim, and no promotion beyond the paper contract.",
        "safety_outcome": "The reproduction kept decoder truth hidden until verification.",
        "cost_outcome": "Benefit depends on adopting structured code families rather than generic random bundles.",
        "baselines": ["paper contract", "common-U1 compatibility checks"],
        "controls": ["clean-only scope", "task mismatch detection"],
        "evidence": {
            "commits": ["a3ca3b3"],
            "protocol_hashes": [],
            "result_paths": ["docs/LEVEL3_3_LINEAR_CODE_REPRODUCTION.md", "results/level3_3"],
            "tests": ["tests/test_level3_3_neco_reproduction.py"],
            "execution_scale": "Clean U1 reproduction only",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact recovery", "paper-contract compatibility"],
            "secondary_metrics": ["rank conditions", "determinism"],
            "qualitative_observations": [
                "The result adopted galois rather than a custom finite-field runtime.",
                "Common-U1 compatibility was supported with explicit constraints."
            ],
        },
        "failure_modes": ["paper contract mismatch", "rank deficiency"],
        "causal_interpretation": "The reproduced advantage lives in the structured code, not in a universal decoder trick.",
        "allowed_claims": ["The clean U1 linear-code paper contract was reproduced with explicit constraints."],
        "forbidden_claims": ["Noise robustness or universal superiority of linear codes from this stage alone."],
        "prior_art": ["linear-code HDC", "GF(2) algebra", "paper reproduction discipline"],
        "architectural_disposition": "REPRODUCED_IN_REPO",
        "reopen_conditions": ["Reopen only for noise-frontier or equal-information comparisons against symbolic and MAP baselines."],
    },
    {
        "hypothesis_id": "level3_4_algebraic_baseline_closure",
        "title": "Clean U1 algebraic baselines match each other while the packed symbolic exact baseline dominates the task envelope",
        "category": "SUBSTRATE_COMPARISON",
        "origin": "Level 3.4 closure",
        "evidence_status": "REPRODUCED_IN_REPO",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "ACTIVE",
        "research_question": "Does the clean U1 task justify native noisy substrates when symbolic exact recovery is available?",
        "method": "NeCo versus generic linear-code comparison plus symbolic exact tuple baseline",
        "substrate": "NeCo, generic linear, symbolic exact record",
        "operation_contract": "Clean U1 only",
        "dimensions": "Matched clean-U1 cells",
        "factor_count": "F=3",
        "search_space": "Common-U1 constrained factorization",
        "noise_contract": "No noise",
        "information_added": "structured code or exact tuple encoding",
        "compute_added": "structured decoding or exact lookup",
        "prior_added": "algebraic structure",
        "exact_side_information": "symbolic exact tuple baseline present",
        "primary_result": "NeCo and generic linear baselines were equivalent on clean U1, while the symbolic exact baseline dominated the task.",
        "primary_failure_point": "This did not settle noisy behavior and therefore did not authorize broad substrate claims.",
        "safety_outcome": "The symbolic exact baseline highlighted when exact side information simply removes factorization ambiguity.",
        "cost_outcome": "Recoverability can be bought directly with exact typed structure on clean U1.",
        "baselines": ["NeCo", "generic linear code", "symbolic exact tuple"],
        "controls": ["clean-only", "common-U1 contract"],
        "evidence": {
            "commits": ["2b8d6f9"],
            "protocol_hashes": [],
            "result_paths": ["docs/LEVEL3_4_ALGEBRAIC_BASELINE_CLOSURE.md", "results/level3_4"],
            "tests": ["tests/test_level3_4_algebraic_baselines.py"],
            "execution_scale": "Development algebraic closure",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact recovery", "equivalence"],
            "secondary_metrics": ["clean U1 dominance"],
            "qualitative_observations": [
                "The algebraic line closed cleanly without noise claims.",
                "The symbolic baseline set an explicit lower bound on recoverability cost."
            ],
        },
        "failure_modes": ["overclaim beyond clean U1", "native substrate mismatch under noise"],
        "causal_interpretation": "Exact symbolic structure can dominate when the task contract allows it; algebraic alternatives must justify themselves beyond the clean exact baseline.",
        "allowed_claims": [
            "NeCo and generic linear baselines were equivalent on the tested clean U1 cells.",
            "The symbolic exact record baseline dominated the clean U1 task."
        ],
        "forbidden_claims": ["Noise-frontier or universal substrate superiority from this stage alone."],
        "prior_art": ["linear codes", "symbolic exact baselines"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only in explicit noise-frontier or storage-cost comparisons."],
    },
    {
        "hypothesis_id": "level3_5a_noise_contract_audit",
        "title": "Noise must be split into explicit external corruption contracts and substrate-native error semantics before any comparison claim",
        "category": "NOISE_AND_PROTOCOL",
        "origin": "Level 3.5a audit",
        "evidence_status": "ADOPTED_ENGINEERING_BASELINE",
        "maturity": "FROZEN_DISCIPLINE",
        "implementation_status": "ACTIVE",
        "research_question": "What minimum audit contract is required before cross-substrate noise claims become lawful?",
        "method": "Noise baseline matrix, source ledger, and typed corruption audit",
        "substrate": "Repository-wide protocol discipline",
        "operation_contract": "Noise contract separation and audit",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "N/A",
        "noise_contract": "Explicit separation of external corruption and native decoder stochasticity",
        "information_added": "typed noise metadata",
        "compute_added": "audit only",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "Universal raw-p noise claims were blocked; lawful comparison requires typed substrate-specific contracts.",
        "primary_failure_point": "Cross-substrate noise scales are not interchangeable without explicit calibration.",
        "safety_outcome": "The audit prevents silent protocol leakage and incomparable frontier claims.",
        "cost_outcome": "Protocol discipline adds documentation cost but prevents invalid scientific aggregation.",
        "baselines": ["raw noise notation", "source ledger"],
        "controls": ["typed contract fields"],
        "evidence": {
            "commits": ["d6f222f"],
            "protocol_hashes": [],
            "result_paths": ["docs/LEVEL3_5A_NOISE_BASELINE_MATRIX.md", "results/level3_5a"],
            "tests": ["tests/test_level3_5a_noise_audit.py"],
            "execution_scale": "Repository-wide noise audit",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["contract completeness"],
            "secondary_metrics": ["source ledger coverage"],
            "qualitative_observations": [
                "External corruption and native decoder behavior are different evidence channels.",
                "Universal raw-p frontiers were explicitly prohibited."
            ],
        },
        "failure_modes": ["protocol leakage", "native substrate mismatch"],
        "causal_interpretation": "Protocol repair is a scientific safety mechanism, not mere administration.",
        "allowed_claims": ["Noise comparisons require explicit typed contracts and separated corruption channels."],
        "forbidden_claims": ["Universal raw-p frontier across incompatible substrates."],
        "prior_art": ["evaluation protocol discipline", "soft-information auditing"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only for new substrate-specific contracts or calibrated severity mappings."],
    },
    {
        "hypothesis_id": "oracle_portfolio_complementarity_v0_1",
        "title": "In the common clean F=3 envelope, BCF dominated hard paired failures and no deployable instance-level cross-substrate router was justified",
        "category": "CROSS_SUBSTRATE_PORTFOLIO",
        "origin": "Cross-Substrate Oracle Complementarity Audit v0.1",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "ARCHIVED",
        "research_question": "Do already-implemented MAP and BCF methods exhibit verified, cost-aware per-instance complementarity strong enough to justify a practical escalation router?",
        "method": "Paired clean F=3 evaluation of frozen MAP D512 fast, MAP D1024 fast, MAP D1024 robust, BCF native, static threshold routes, fixed-order cascades, random controls, and oracle upper bounds",
        "substrate": "MAP and official IBM BCF under separate lawful native encodings",
        "operation_contract": "Clean single-product factorization with F=3 factor-specific domains and a common semantic tuple contract",
        "dimensions": "MAP D512/D1024 and BCF native D512 common envelope",
        "factor_count": "F=3",
        "search_space": "M in {10,22,31,68} with identical tuple IDs across methods",
        "noise_contract": "Clean only; no noise trials in this stage",
        "information_added": "none",
        "compute_added": "paired multi-method execution, cascades, and oracle analysis",
        "prior_added": "static route by M only",
        "exact_side_information": "none",
        "primary_result": "BCF_NATIVE dominated the hard/non-easy paired instances and the direct oracle achieved no meaningful verified gain over the best fixed single method.",
        "primary_failure_point": "Residual complementarity collapsed to a trivial easy-cell static threshold rather than a deployable instance-level routing signal.",
        "safety_outcome": "Verifier-constrained oracles and cascades preserved zero silent wrong acceptance.",
        "cost_outcome": "Dual-encoding cost and cascade complexity were not justified because the best hard-cell coverage came from a single native method.",
        "baselines": [
            "always MAP_D512_FAST",
            "always MAP_D1024_FAST",
            "always MAP_D1024_ROBUST",
            "always BCF_NATIVE",
            "always abstain"
        ],
        "controls": [
            "oracle direct min-cost correct",
            "verifier-constrained oracle",
            "24 fixed-order cascades",
            "M-threshold static route",
            "cost-matched random route"
        ],
        "evidence": {
            "commits": [],
            "protocol_hashes": [
                "e7b56d4a5c780d2e45270b203b4d8df6efd73585f0b6f34f6fb2a0ec1a3ad1fd"
            ],
            "result_paths": [
                "docs/PORTFOLIO_ORACLE_COMPLEMENTARITY_AUDIT.md",
                "docs/PORTFOLIO_ORACLE_COMPLEMENTARITY_PROTOCOL.md",
                "results/oracle_portfolio_v0_1"
            ],
            "tests": [
                "tests/test_oracle_portfolio_complementarity.py"
            ],
            "execution_scale": "16 pilot + 32 calibration + 64 final paired trials per cell across 4 cells",
            "heldout_status": "No held-out execution; official held-out count remained 0",
        },
        "results": {
            "primary_metrics": [
                "accepted exact coverage",
                "silent wrong rate",
                "median and p95 latency",
                "rescue counts"
            ],
            "secondary_metrics": [
                "correct-set overlap",
                "static-route regret",
                "dual-representation bytes"
            ],
            "qualitative_observations": [
                "MAP variants rescued each other on subsets, but none rescued BCF failures because BCF had no hard-cell misses in the common envelope.",
                "A trivial threshold route used MAP only on the easy M=10 cell and captured all practical portfolio value observed here."
            ],
        },
        "failure_modes": [
            "dominant single method",
            "static-route sufficiency",
            "dual-encoding overhead"
        ],
        "causal_interpretation": "Cross-substrate rescue existed among weaker MAP variants, but the common hard envelope was already solved by one native method, so oracle routing added no new deployable information.",
        "allowed_claims": [
            "In the tested clean F=3 common envelope, BCF_NATIVE dominated the hard/non-easy frontier while MAP remained only an easy-cell latency path.",
            "A trivial M-threshold static route captured the only practical portfolio value observed in this stage."
        ],
        "forbidden_claims": [
            "learned cross-substrate router justified",
            "FPGA or Lava cascade justified",
            "general cross-substrate complementarity across noise or other contracts"
        ],
        "prior_art": [
            "algorithm portfolios",
            "SATzilla-style oracle analysis",
            "fixed-order cascades",
            "selective prediction"
        ],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": [
            "Reopen only if a new lawful contract introduces residual verifier-preserved routing regret after the best static route."
        ],
    },
    {
        "hypothesis_id": "level3_5b_confirmatory_protocol_discipline",
        "title": "Held-out confirmatory execution requires prospectively frozen executable gate semantics before the first held-out observation",
        "category": "NOISE_AND_PROTOCOL",
        "origin": "Level 3.5b protocol repair and prospective gate specification",
        "evidence_status": "ADOPTED_ENGINEERING_BASELINE",
        "maturity": "FROZEN_DISCIPLINE",
        "implementation_status": "ACTIVE",
        "research_question": "How should confirmatory noise verdicts be serialized so that the held-out runner cannot invent semantics after seeing outcomes?",
        "method": "Protocol repair, prospective gate specification, diff audit, and contract-gate consistency repair",
        "substrate": "Repository-wide confirmatory protocol discipline",
        "operation_contract": "Level 3.5b held-out gate freezing and validation",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "N/A",
        "noise_contract": "Substrate-specific held-out confirmation contract",
        "information_added": "fully serialized gate semantics",
        "compute_added": "validator and synthetic dry-run cost",
        "prior_added": "development-only calibration rationale",
        "exact_side_information": "none",
        "primary_result": "The repo now contains an explicit rule: no confirmatory gate may be executed without prospectively frozen executable semantics.",
        "primary_failure_point": "Earlier protocols blocked exactly because those semantics were missing or inconsistent.",
        "safety_outcome": "Zero-trial integrity blocks preserved lawful non-execution instead of inventing thresholds.",
        "cost_outcome": "More protocol overhead, but drastically lower leakage risk.",
        "baselines": ["v1/v2/v3 blocked runs", "synthetic gate dry-runs"],
        "controls": ["gate-source audit", "independent validator", "diff allowlist"],
        "evidence": {
            "commits": ["8fcef7e", "1104049"],
            "protocol_hashes": [
                "649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf"
            ],
            "result_paths": [
                "docs/LEVEL3_5B_PROTOCOL_REPAIR_AND_REFREEZE.md",
                "docs/LEVEL3_5B_PROSPECTIVE_GATE_SPECIFICATION.md",
                "docs/LEVEL3_5B_CONTRACT_GATE_CONSISTENCY_REPAIR.md",
                "results/level3_5b_protocol_repair",
                "results/level3_5b_gate_specification",
                "results/level3_5b_gate_consistency_repair",
            ],
            "tests": [
                "tests/test_level3_5b_protocol_repair.py",
                "tests/test_level3_5b_gate_specification.py",
                "tests/test_level3_5b_contract_gate_consistency_repair.py",
            ],
            "execution_scale": "Protocol and validator stage only",
            "heldout_status": "Held-out trials observed before gate freeze: 0",
        },
        "results": {
            "primary_metrics": ["zero held-out trials before v3/v4", "complete executable gate schemas"],
            "secondary_metrics": ["synthetic dry-run coverage", "protocol diff compliance"],
            "qualitative_observations": [
                "This was protocol completion, not administrative repair of previously executable gates.",
                "BCF remained blocked by contract ambiguity rather than being forced through a broken gate."
            ],
        },
        "failure_modes": ["held-out contamination risk", "protocol leakage", "ambiguous gate semantics"],
        "causal_interpretation": "A lawful confirmatory verdict depends on semantics frozen before seeing any held-out outcome.",
        "allowed_claims": ["Prospective executable gate semantics are mandatory before held-out confirmation."],
        "forbidden_claims": ["A blocked held-out run is scientific evidence for the substantive noise frontier."],
        "prior_art": ["prospective protocol design", "confirmatory gate serialization"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only for a new confirmatory protocol version before any corresponding held-out run."],
    },
    {
        "hypothesis_id": "level3_5b_zero_trial_integrity_blocks",
        "title": "Runner-side integrity blocks are positive evidence for lawful non-execution when confirmatory contracts are incomplete",
        "category": "NOISE_AND_PROTOCOL",
        "origin": "Level 3.5b held-out v1/v2/v3 integrity failures",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "ARCHIVED",
        "research_question": "Should the runner execute anyway when confirmatory semantics are incomplete or inconsistent?",
        "method": "Preserved blocked held-out attempts",
        "substrate": "Held-out execution policy",
        "operation_contract": "Refuse execution under protocol-integrity failure",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "N/A",
        "noise_contract": "No lawful confirmatory execution",
        "information_added": "none",
        "compute_added": "none",
        "prior_added": "none",
        "exact_side_information": "none",
        "primary_result": "Three blocked attempts preserved zero-trial integrity instead of generating invalid outcomes.",
        "primary_failure_point": "The line could not become substantive evidence without a lawful protocol.",
        "safety_outcome": "No held-out leakage occurred before protocol completion.",
        "cost_outcome": "Temporal delay but scientific validity preserved.",
        "baselines": ["blocked v1", "blocked v2", "blocked v3"],
        "controls": ["immutability of prior block evidence"],
        "evidence": {
            "commits": ["8fcef7e"],
            "protocol_hashes": [],
            "result_paths": [
                "docs/LEVEL3_5B_HELDOUT_NOISE_CONFIRMATION.md",
                "docs/LEVEL3_5B_HELDOUT_V2_NOISE_CONFIRMATION.md",
                "docs/LEVEL3_5B_HELDOUT_V3_NOISE_CONFIRMATION.md",
                "results/level3_5b_heldout",
                "results/level3_5b_heldout_v2",
                "results/level3_5b_heldout_v3",
            ],
            "tests": [
                "tests/test_level3_5b_heldout_confirmation.py",
                "tests/test_level3_5b_heldout_v2_confirmation.py",
                "tests/test_level3_5b_heldout_v3_confirmation.py",
            ],
            "execution_scale": "Zero-trial block evidence",
            "heldout_status": "heldout_trials_observed = 0",
        },
        "results": {
            "primary_metrics": ["zero held-out trials executed"],
            "secondary_metrics": ["block artifact immutability"],
            "qualitative_observations": [
                "The correct action was to block, not improvise thresholds.",
                "These artifacts are evidence of discipline, not frontier outcomes."
            ],
        },
        "failure_modes": ["protocol integrity failure", "held-out contamination risk"],
        "causal_interpretation": "A lawful runner must fail closed when confirmatory semantics are undefined.",
        "allowed_claims": ["Blocked zero-trial artifacts preserved confirmatory integrity."],
        "forbidden_claims": ["Substantive noise-frontier claims from blocked held-out runs."],
        "prior_art": ["fail-closed evaluation discipline"],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": ["Reopen only under a new lawful protocol version before any corresponding held-out execution."],
    },
    {
        "hypothesis_id": "lazy_trace_stage_a_semantic_locality",
        "title": "Noisy MAP semantic cues contain useful locality for retrieving a nearby creation-trace neighborhood",
        "category": "SEMANTIC_TO_TRACE_ROUTING",
        "origin": "Lazy Semantic-to-Trace Addressing Stage A / A.1",
        "evidence_status": "PARTIALLY_REPRODUCED",
        "maturity": "PARTIAL",
        "implementation_status": "EXPERIMENTAL",
        "research_question": "Can a noisy semantic cue route to a small local trace set without global memory scan?",
        "method": "Random-hyperplane LSH routing, exact reranking, typed trace validation",
        "substrate": "MAP semantics plus exact trace sidecar",
        "operation_contract": "Semantic cue -> local trace candidate set",
        "dimensions": "D1024, N1000 and N10000",
        "factor_count": "Synthetic trace families, not decoder execution",
        "search_space": "Exact trace handles under bounded candidate budgets",
        "noise_contract": "External Bernoulli sign-flip corruption",
        "information_added": "approximate semantic routing signal",
        "compute_added": "LSH probing and reranking",
        "prior_added": "semantic locality only",
        "exact_side_information": "trace sidecar for verification",
        "primary_result": "Stage A was partial rather than falsifying semantic locality; analytically chosen Stage A.1 configurations reached high exact-trace candidate recall under bounded candidates.",
        "primary_failure_point": "Acceptance coverage and latency still lagged stronger baselines, and semantic-only routing could not resolve exact ambiguity.",
        "safety_outcome": "Wrong-trace acceptance stayed at zero under typed verification.",
        "cost_outcome": "Useful locality exists, but it costs routing structures, candidate reranking, and abstention.",
        "baselines": ["global exact semantic scan", "exact content hash", "budget-matched random routing"],
        "controls": ["analytical collision expectations", "adversarial ambiguity cases"],
        "evidence": {
            "commits": ["ccf3730", "f8c4c0e"],
            "protocol_hashes": [
                "f9f770c7af19ad7fc5efb2d8191be116ecdccfd6d6b22f51d7c74da8c58f50ab",
                "3457395a278f470f9e0dd8c8a43ae2296ed0629444e8b578218231fc241f2dd6",
            ],
            "result_paths": [
                "docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A.md",
                "docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A1.md",
                "results/lazy_trace_stage_a",
                "results/lazy_trace_stage_a1",
            ],
            "tests": ["tests/test_lazy_trace_addressing_stage_a.py", "tests/test_lazy_trace_addressing_stage_a1.py"],
            "execution_scale": "Development-only semantic routing benchmark",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact-trace candidate recall", "candidate count", "acceptance coverage", "conditional risk"],
            "secondary_metrics": ["theory-vs-observed hit probability", "ambiguity detection rate"],
            "qualitative_observations": [
                "The four-table Stage A result matched collision theory rather than refuting semantic LSH.",
                "Stage A.1 separated decoder-contract retrieval from exact-trace retrieval and made ambiguity explicit.",
            ],
        },
        "failure_modes": ["candidate-budget truncation", "ambiguity under identical semantics", "latency crossover risk"],
        "causal_interpretation": "Semantic geometry carries locality, but not exact provenance identity.",
        "allowed_claims": ["Noisy MAP semantic cues contain useful locality for trace-neighborhood retrieval in the tested development envelope."],
        "forbidden_claims": ["Exact provenance from semantic similarity alone", "held-out confirmation"],
        "prior_art": ["random-hyperplane LSH", "semantic reranking", "typed sidecar validation"],
        "architectural_disposition": "PARTIALLY_REPRODUCED",
        "reopen_conditions": ["Reopen only for mature-index or carried-fingerprint comparisons under equal-information contracts."],
    },
    {
        "hypothesis_id": "lazy_trace_stage_a2a_mature_index_shootout",
        "title": "At N=10k, mature exact packed search dominates the custom thin semantic router on the practical frontier",
        "category": "SEMANTIC_TO_TRACE_ROUTING",
        "origin": "Lazy Semantic-to-Trace Addressing Stage A.2a",
        "evidence_status": "REPRODUCED_IN_REPO",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "ACTIVE",
        "research_question": "Which mature exact or ANN-style index best returns the exact associated creation trace under bounded latency, memory, and safety constraints?",
        "method": "Faiss exact float scan, float HNSW, exact binary scan, binary HNSW, binary multi-hash, and incumbent thin LSH",
        "substrate": "MAP semantics plus exact trace sidecar",
        "operation_contract": "Noisy semantic cue -> bounded candidate ids -> exact reranking -> typed trace validation",
        "dimensions": "D1024, N10000 primary cell",
        "factor_count": "Synthetic trace families",
        "search_space": "Exact creation-trace retrieval",
        "noise_contract": "External Bernoulli sign flips at p in {0.00, 0.01, 0.03, 0.05, 0.10, 0.15}",
        "information_added": "mature index structures",
        "compute_added": "index search plus canonical reranking",
        "prior_added": "none beyond the index",
        "exact_side_information": "trace sidecar and exact reranker",
        "primary_result": "Exact packed binary scan beat the tested approximate methods on the primary practical frontier at N=10k.",
        "primary_failure_point": "The thin custom LSH did not remain nondominated once mature baselines were included.",
        "safety_outcome": "Ambiguity-safe verification preserved zero silent wrong exact-trace acceptance.",
        "cost_outcome": "At the tested scale, exact search was simpler and faster than approximate routing.",
        "baselines": ["vectorized exact scan", "Faiss exact float", "thin LSH incumbent", "Faiss HNSW", "binary multi-hash"],
        "controls": ["candidate-budget fairness", "ambiguity policy", "metric-equivalence audit"],
        "evidence": {
            "commits": ["f8c4c0e"],
            "protocol_hashes": [],
            "result_paths": [
                "docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A1_ERRATUM.md",
                "docs/LEVEL3_LAZY_TRACE_ADDRESSING_STAGE_A2A.md",
                "results/lazy_trace_stage_a2a",
            ],
            "tests": ["tests/test_lazy_trace_addressing_stage_a2a.py"],
            "execution_scale": "Primary development cell N10000 / D1024 / 512 queries",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact_trace_recall@32", "accepted coverage", "p50/p95 latency", "index bytes"],
            "secondary_metrics": ["decoder-contract diagnostics", "build/update cost"],
            "qualitative_observations": [
                "The scientific line survived only partially: semantic self-addressing remained plausible, but the custom router lost to exact binary scan at this scale.",
                "This stage replaced NIH pressure with a mature-index shootout."
            ],
        },
        "failure_modes": ["compute non-dominance", "implementation complexity non-benefit"],
        "causal_interpretation": "Useful semantic locality does not guarantee that a custom router beats mature exact indexing at practical scale.",
        "allowed_claims": [
            "A noisy MAP cue can retrieve an exact creation-trace neighborhood in a development envelope.",
            "At N=10k the adopted engineering baseline is exact packed binary scan, not the custom thin router."
        ],
        "forbidden_claims": ["New ANN/LSH algorithm", "production self-decoding memory", "Stage B decoder execution"],
        "prior_art": ["Faiss exact search", "Faiss HNSW", "binary multi-hash"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only for scale crossover, SDM comparison, or carried-fingerprint protocols."],
    },
    {
        "hypothesis_id": "first_order_trace_coactivation",
        "title": "First-order trace co-activation beats random routing but does not yet beat exact sidecar retrieval end-to-end",
        "category": "TRACE_COACTIVATION",
        "origin": "First-Order Trace Co-Activation stage",
        "evidence_status": "PARTIALLY_REPRODUCED",
        "maturity": "PARTIAL",
        "implementation_status": "EXPERIMENTAL",
        "research_question": "Can semantic operations create a first-order trace association whose later co-activation reduces decoder or replay search?",
        "method": "First-order trace atoms, optional carried capsules, semantic-to-trace bridge, and trace-free replay portfolio baseline",
        "substrate": "MAP semantics plus exact trace payloads and optional carried capsules",
        "operation_contract": "First-order replay configuration only; no recursive ancestry",
        "dimensions": "Semantic D1024 with 0/64/128 trace dims under fixed-semantic and fixed-total budgets",
        "factor_count": "Multiple MAP operation families",
        "search_space": "Trace selection and replay-path narrowing",
        "noise_contract": "Separate semantic and capsule corruption cells",
        "information_added": "first-order exact trace atoms and optional capsules",
        "compute_added": "trace routing, validation, and replay",
        "prior_added": "semantic-to-trace association",
        "exact_side_information": "exact parent handles in validated trace atoms",
        "primary_result": "Co-activation beat random routing and exact capsules were the strongest narrow seam, but semantic bridge alone did not beat the equal-information sidecar baseline.",
        "primary_failure_point": "Decoder-reduction benefits were not strong enough to displace the trace-free portfolio or exact sidecar baseline outright.",
        "safety_outcome": "Ambiguity handling stayed lawful with zero silent exact-provenance acceptance.",
        "cost_outcome": "Benefits came largely from exact trace information rather than from a new associative mechanism.",
        "baselines": ["known-handle sidecar oracle", "semantic lookup plus sidecar", "random bridge", "trace-free replay portfolio"],
        "controls": ["fixed-semantic vs fixed-total capacity", "ambiguity cases", "capsule corruption matrix"],
        "evidence": {
            "commits": [],
            "protocol_hashes": ["d541a877ee8344ebfa31ab784ef7da364ac79712cf593c169e7fbeb9e469f03b"],
            "result_paths": [
                "docs/LEVEL3_FIRST_ORDER_TRACE_COACTIVATION.md",
                "results/first_order_trace_coactivation",
            ],
            "tests": ["tests/test_first_order_trace_coactivation.py"],
            "execution_scale": "Development-only bounded benchmark",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["trace-spike recall", "decoder invocations", "accepted coverage", "conditional risk"],
            "secondary_metrics": ["cross-zone leakage", "semantic-capacity tax"],
            "qualitative_observations": [
                "Exact carried capsules dominated the narrower competition.",
                "Semantic bridge alone was real but not enough to justify runtime promotion."
            ],
        },
        "failure_modes": ["ambiguity under identical semantics", "sidecar non-dominance failure", "capacity tax"],
        "causal_interpretation": "The main benefit came from exact first-order structure, not from magic semantic self-description.",
        "allowed_claims": ["First-order trace co-activation is partially supported as a bounded development seam."],
        "forbidden_claims": ["Recursive history solved", "full self-decoding memory", "production runtime"],
        "prior_art": ["exact capsules", "associative routing", "typed replay"],
        "architectural_disposition": "PARTIALLY_REPRODUCED",
        "reopen_conditions": ["Reopen only for narrow carried-fingerprint refinement or scale crossover studies."],
    },
    {
        "hypothesis_id": "exact_capsule_contract_closure",
        "title": "Carried exact trace information helps detached activation, but isolated capsule placement itself is not advantageous over a plain typed field",
        "category": "EXACT_SIDE_INFORMATION",
        "origin": "Exact capsule contract closure",
        "evidence_status": "ADOPTED_ENGINEERING_BASELINE",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "ACTIVE",
        "research_question": "Does an isolated exact capsule have any benefit over an ordinary exact field or sidecar under equal information and equal bits?",
        "method": "Ordinary field vs isolated capsule vs ECC capsule vs unsafe semantic fallback",
        "substrate": "Exact carried token plus MAP semantic lookup",
        "operation_contract": "Record retrieval followed by exact trace resolution",
        "dimensions": "D1024 semantic substrate with exact token budgets",
        "factor_count": "Exact first-order trace token",
        "search_space": "Trace token resolution and replay separation",
        "noise_contract": "Separate semantic and capsule corruption cells",
        "information_added": "exact carried trace token",
        "compute_added": "token validation and optional fallback",
        "prior_added": "none",
        "exact_side_information": "yes",
        "primary_result": "Plain typed exact handle survived; isolated placement did not.",
        "primary_failure_point": "Fingerprint fallback and wrong-valid semantic fallback were unsafe or non-beneficial.",
        "safety_outcome": "Exact field/capsule paths stayed safe; semantic fallback did not.",
        "cost_outcome": "Placement-specific complexity produced no measured gain under equal bits.",
        "baselines": ["known-record sidecar", "semantic lookup plus sidecar", "ordinary field", "isolated capsule", "ECC exact capsule"],
        "controls": ["equal-information budget", "equal-bits placement test", "corruption matrix"],
        "evidence": {
            "commits": ["52060ef"],
            "protocol_hashes": [],
            "result_paths": ["docs/LEVEL3_EXACT_CAPSULE_CONTRACT_CLOSURE.md", "results/exact_capsule_contract"],
            "tests": ["tests/test_exact_capsule_contract_closure.py"],
            "execution_scale": "Development-only detached activation benchmark",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact-trace coverage", "conditional risk", "candidate count", "latency"],
            "secondary_metrics": ["ECC improvement", "placement equivalence"],
            "qualitative_observations": [
                "Exact carried information mattered.",
                "Where those exact bits were packed did not."
            ],
        },
        "failure_modes": ["wrong-valid capsule fallback", "packaging non-benefit"],
        "causal_interpretation": "Exact side information helps because it is exact, not because it is capsule-shaped.",
        "allowed_claims": ["Carried exact trace information can help detached activation under a bounded development contract."],
        "forbidden_claims": ["Isolated capsule placement itself is scientifically beneficial."],
        "prior_art": ["content-addressed handles", "ECC-protected metadata", "sidecar vs inline metadata"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only if a future carried zone adds new information rather than repackaging the same exact bits."],
    },
    {
        "hypothesis_id": "decoder_certified_codebook",
        "title": "Decoder-certified atomic admission did not show a stable causal recovery advantage over simpler controls",
        "category": "ENCODER_ADAPTATION",
        "origin": "Decoder-Certified Codebook Construction v0.1",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "ARCHIVED",
        "research_question": "Does true candidate-to-decoder-score linkage produce a generalizable codebook advantage at fixed dimension and fixed candidate budget?",
        "method": "Random-first, distance-maxmin, decoder-certified, and shuffled-certification control",
        "substrate": "MAP / resonator harness",
        "operation_contract": "F=3 factor product with online codebook insertion",
        "dimensions": "Minimal development envelope around MAP transition region",
        "factor_count": "F=3",
        "search_space": "K-candidate atomic admission pools",
        "noise_contract": "Tiny smoke-only development scope",
        "information_added": "decoder certification scores during insertion",
        "compute_added": "candidate certification runs",
        "prior_added": "none beyond decoder feedback",
        "exact_side_information": "none",
        "primary_result": "The line remained prototype-only and did not support a stable decoder-certified recovery advantage.",
        "primary_failure_point": "Shuffled-control and simpler baselines stayed too competitive.",
        "safety_outcome": "No silent-risk trade justified promotion.",
        "cost_outcome": "Construction cost was nontrivial and not offset by a new nondominated frontier.",
        "baselines": ["random-first", "distance-maxmin", "shuffled-certification control"],
        "controls": ["K=1 sanity collapse", "certification / validation / final split"],
        "evidence": {
            "commits": ["c6a24d7"],
            "protocol_hashes": ["c38252c5823def1ea86454146f62b8e3c55bcec6beaf10cbf94985800734a4f1"],
            "result_paths": ["docs/LEVEL3_DECODER_CERTIFIED_CODEBOOK_AUDIT.md", "results/decoder_certified_codebook_v0_1"],
            "tests": ["tests/test_decoder_certified_codebook.py"],
            "execution_scale": "Tiny smoke-only paired run",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact factor recovery", "verified reconstruction", "construction cost", "old-atom regression"],
            "secondary_metrics": ["coverage", "conditional risk"],
            "qualitative_observations": [
                "Decoder-certified insertion improved some means but not enough to survive causal controls.",
                "The scientific verdict was explicit block, not a partial architecture promotion."
            ],
        },
        "failure_modes": ["certification overfit", "search-budget explanation", "old-atom regression risk"],
        "causal_interpretation": "Extra codebook-search compute did not isolate a reliable decoder-aware admission effect.",
        "allowed_claims": ["None beyond prototype-level directional observations."],
        "forbidden_claims": ["Generalizable decoder-certified codebook advantage."],
        "prior_art": ["codebook search", "distance packing", "decoder-in-the-loop selection"],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": ["Do not reopen this line without a new substrate, larger power, and stronger causal controls."],
    },
    {
        "hypothesis_id": "decoder_guided_tag_repair",
        "title": "Conflict-guided sparse tags did not justify their complexity over equal-bit extra dimensions",
        "category": "REPRESENTATION_REPAIR",
        "origin": "Decoder-Guided Tagged-Symbol Repair",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "ARCHIVED",
        "research_question": "Can sparse conflict-guided tags improve recovery at equal bit budget without silently leaking identities?",
        "method": "Base binary, random tags, shuffled conflict tags, random patch search, conflict-guided tags, equal-bit extra dimensions",
        "substrate": "MAP / resonator harness",
        "operation_contract": "F=3 factor product with tagged symbol plane",
        "dimensions": "Tiny smoke-only development envelope",
        "factor_count": "F=3",
        "search_space": "Tag positions and repair controls",
        "noise_contract": "Tiny clean development scope",
        "information_added": "sparse tags",
        "compute_added": "repair / patch search",
        "prior_added": "conflict hints",
        "exact_side_information": "none",
        "primary_result": "Equal-bit extra dimensions dominated the tag line; the scientific advantage was not supported.",
        "primary_failure_point": "Conflict-guided tags matched random or shuffled controls too closely.",
        "safety_outcome": "The audit blocked a false positive line before architecture inflation.",
        "cost_outcome": "Complexity exceeded any measured benefit.",
        "baselines": ["base binary", "random tags", "shuffled conflict tags", "equal-bit extra dimensions"],
        "controls": ["random patch search", "bit-accounting parity"],
        "evidence": {
            "commits": ["19bcb16"],
            "protocol_hashes": ["ba57e148f752a9d77a4982c1921bab732d0c8ea4d812bb4b8d61467f69ec2c28"],
            "result_paths": ["docs/LEVEL3_DECODER_GUIDED_TAG_REPAIR_AUDIT.md", "results/decoder_guided_tag_repair_v0_1"],
            "tests": ["tests/test_decoder_guided_tag_repair.py"],
            "execution_scale": "Tiny smoke-only paired run",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact recovery", "coverage", "conditional risk", "physical bits"],
            "secondary_metrics": ["old-only recovery"],
            "qualitative_observations": [
                "Equal-bit extra dimensions materially outperformed all sparse-tag variants.",
                "The line remained blocked rather than promoted into a bigger architecture."
            ],
        },
        "failure_modes": ["compute non-dominance", "storage non-dominance", "sparse-tag non-benefit"],
        "causal_interpretation": "Weak sign-level repair hints were too little information relative to simply buying more dimensions.",
        "allowed_claims": ["None beyond the negative result."],
        "forbidden_claims": ["Conflict-guided tag repair advantage."],
        "prior_art": ["repair tags", "bit-allocation controls", "equal-bit baselines"],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": ["Do not reopen without a new information contract clearly stronger than weak sign hints."],
    },
    {
        "hypothesis_id": "self_describing_record_sidecar_closure",
        "title": "Exact first-order manifests safely enable recursive replay after record retrieval, but ordinary sidecar DAG remains the honest baseline",
        "category": "EXACT_STRUCTURE",
        "origin": "Self-Describing Recursive Hypervector Record v0.1",
        "evidence_status": "ADOPTED_ENGINEERING_BASELINE",
        "maturity": "CLOSED_WITH_BOUNDED_CLAIMS",
        "implementation_status": "ACTIVE",
        "research_question": "Is a compact exact first-order manifest safe and useful for recursive replay, and does inline packing beat ordinary sidecar storage?",
        "method": "Ordinary sidecar DAG, inline packed manifest, optional lazy semantic arm, and MAP factorization baseline",
        "substrate": "MAP semantics plus exact first-order manifests",
        "operation_contract": "Record retrieval followed by recursive deterministic replay",
        "dimensions": "MAP bind/permute replay with recursive depth cells",
        "factor_count": "Immediate operands only per composite",
        "search_space": "Recursive replay over immutable DAG nodes",
        "noise_contract": "Semantic observation corruption plus manifest corruption tests",
        "information_added": "exact immediate operand manifest",
        "compute_added": "recursive replay, memoization, checksum validation",
        "prior_added": "none",
        "exact_side_information": "yes",
        "primary_result": "Exact replay was safe and exact, but inline packed placement showed no meaningful advantage over ordinary sidecar DAG.",
        "primary_failure_point": "Packaging advantage was not supported.",
        "safety_outcome": "Wrong-valid handles, stale parents, and cycles were typed failures rather than silent wrong reconstruction.",
        "cost_outcome": "Replay cost scaled with unique DAG nodes, but inline packing did not create more information than sidecar storage.",
        "baselines": ["MAP factorization baseline", "ordinary sidecar DAG", "inline packed manifest"],
        "controls": ["wrong-valid handle", "manifest corruption", "shared-subgraph memoization"],
        "evidence": {
            "commits": [],
            "protocol_hashes": ["a0d3674810dd041370c14da3474b3bdf976bb4a9b39a971259d6c251b2a6b69a"],
            "result_paths": ["docs/LEVEL3_SELF_DESCRIBING_HYPERVECTOR_AUDIT.md", "results/self_describing_record_v0_1"],
            "tests": ["tests/test_self_describing_record.py"],
            "execution_scale": "Development-only bounded replay benchmark",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["exact reconstruction", "lookup count", "latency", "deployable bytes"],
            "secondary_metrics": ["memoization hits", "corruption outcomes"],
            "qualitative_observations": [
                "Exact manifests behave like exact structured metadata, not magical self-unbinding vectors.",
                "Inline and sidecar implementations were logically equivalent in the measured envelope."
            ],
        },
        "failure_modes": ["wrong-but-valid exact handle", "dangling operand ref", "cycle detection", "packaging non-benefit"],
        "causal_interpretation": "The gain came from preserving exact structure, not from embedding it into semantic geometry.",
        "allowed_claims": ["Exact first-order manifests can support safe recursive replay after record retrieval."],
        "forbidden_claims": ["Self-addressing from noisy semantic cue", "new VSA algorithm", "inline packing as proven advantage"],
        "prior_art": ["AST/DAG replay", "content-addressed records", "memoized traversal"],
        "architectural_disposition": "ADOPTED_ENGINEERING_BASELINE",
        "reopen_conditions": ["Reopen only if a future locator or scale study changes the sidecar vs inline trade-off."],
    },
    {
        "hypothesis_id": "codebook_residue_block_lut",
        "title": "Block-LUT residue compression did not beat scalar residue or equal-bit extra dimensions in the tested MAP bundling envelope",
        "category": "SOFT_INFORMATION",
        "origin": "Codebook-Compressed Residue Plane v0.1",
        "evidence_status": "BLOCKED_WITH_EVIDENCE",
        "maturity": "CLOSED",
        "implementation_status": "ARCHIVED",
        "research_question": "Can a small decoder-side block dictionary compress accumulator magnitudes into short tokens while keeping a better recovery-storage frontier than scalar residue or extra dimensions?",
        "method": "MAP-B hard, ternary tie-aware, scalar residue, block codebook C4/C16, shuffled tokens, MAP-I exact accumulator, equal-total-bit extra dimensions, raw block storage",
        "substrate": "MAP bundling cleanup",
        "operation_contract": "Membership recovery and top-k enumeration",
        "dimensions": "D512 and D1024; K in {3,7,15,31}",
        "factor_count": "Bundling task rather than factor count",
        "search_space": "Bundle members under sign/residue representations",
        "noise_contract": "Bundling accumulator evidence, not a noisy factorization frontier",
        "information_added": "quantized residue magnitudes",
        "compute_added": "decoder-side LUT weighting",
        "prior_added": "none",
        "exact_side_information": "MAP-I upper bound only",
        "primary_result": "The block dictionary line did not justify itself; equal-bit extra dimensions survived instead.",
        "primary_failure_point": "Scalar or raw alternatives remained too competitive, and extra dimensions dominated the frontier.",
        "safety_outcome": "Shuffled-token controls confirmed that correct mapping mattered, but not enough to rescue the architecture.",
        "cost_outcome": "Decoder-side dictionary complexity did not create a new nondominated point.",
        "baselines": ["MAP-B hard", "ternary tie-aware", "scalar residue", "MAP-I", "equal-total-bit extra dimensions", "raw block storage"],
        "controls": ["shuffled tokens", "cross-K shared codebook", "physical bit accounting"],
        "evidence": {
            "commits": ["85b5334"],
            "protocol_hashes": ["dad34b84db6baa5a120cc69bf1e27d5a55d207321efa2b60670e403effc9f447"],
            "result_paths": ["docs/LEVEL3_CODEBOOK_COMPRESSED_RESIDUE_AUDIT.md", "results/codebook_residue_v0_1"],
            "tests": ["tests/test_codebook_residue.py"],
            "execution_scale": "Development-only bounded bundling benchmark",
            "heldout_status": "No held-out execution",
        },
        "results": {
            "primary_metrics": ["member recall", "false positives", "storage bits", "prototype utilization"],
            "secondary_metrics": ["token entropy", "quantization distortion", "amortization"],
            "qualitative_observations": [
                "Soft information helped relative to hard sign-only cleanup.",
                "But the block dictionary itself did not beat simpler rate-equivalent baselines."
            ],
        },
        "failure_modes": ["storage non-dominance", "scalar dominance", "equal-bit extra-dimension dominance"],
        "causal_interpretation": "Useful reliability information exists, but that does not imply that a block dictionary is the best way to store it.",
        "allowed_claims": ["Residue information matters; the tested block dictionary did not justify itself."],
        "forbidden_claims": ["New quantization algorithm", "advantage of block dictionary compression over simpler controls in the tested envelope"],
        "prior_art": ["vector quantization", "scalar residue", "soft-decision weighting", "extra-dimension baselines"],
        "architectural_disposition": "BLOCKED_WITH_EVIDENCE",
        "reopen_conditions": ["Reopen only for a clearly different soft-information substrate or mature quantization baseline."],
    },
    {
        "hypothesis_id": "lazy_composite_reification",
        "title": "Lazy Composite Reification remains a deferred design hypothesis rather than a supported architecture result",
        "category": "DEFERRED_ARCHITECTURE",
        "origin": "Research backlog",
        "evidence_status": "DEFERRED_HYPOTHESIS",
        "maturity": "STRONG_PROTOTYPE_HYPOTHESIS",
        "implementation_status": "NOT_AUTHORIZED",
        "research_question": "Can mature concepts be reified lazily while preserving exact handles, semantic fingerprints, and safe rollback?",
        "method": "Documentation-only hypothesis",
        "substrate": "Future heterogeneous architecture",
        "operation_contract": "Lazy reification and exact graph composition",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "Not executed",
        "noise_contract": "Not executed",
        "information_added": "exact handles and semantic fingerprints",
        "compute_added": "future replay and routing cost",
        "prior_added": "architectural priors only",
        "exact_side_information": "yes",
        "primary_result": "This line remains deferred pending stronger prior-art audit and closure of higher-priority held-out work.",
        "primary_failure_point": "No experimental evidence yet.",
        "safety_outcome": "Documentation explicitly blocks premature implementation.",
        "cost_outcome": "Unknown until prototyped against ordinary sidecar baselines.",
        "baselines": ["ordinary sidecar DAG", "exact handles"],
        "controls": ["anti-NIH audit only"],
        "evidence": {
            "commits": [],
            "protocol_hashes": [],
            "result_paths": ["docs/research/LAZY_COMPOSITE_REIFICATION_HYPOTHESIS.md"],
            "tests": [],
            "execution_scale": "Design only",
            "heldout_status": "No execution",
        },
        "results": {
            "primary_metrics": [],
            "secondary_metrics": [],
            "qualitative_observations": [
                "Status is deferred backlog only.",
                "Implementation was explicitly not authorized."
            ],
        },
        "failure_modes": ["architecture inflation", "prior-art miss"],
        "causal_interpretation": "This is a backlog hypothesis, not evidence.",
        "allowed_claims": ["Lazy Composite Reification is a deferred design hypothesis."],
        "forbidden_claims": ["Supported architecture or implementation authorization."],
        "prior_art": ["lazy materialization", "exact handles", "graph replay"],
        "architectural_disposition": "DEFERRED_HYPOTHESIS",
        "reopen_conditions": ["Reopen only after held-out closure and a fresh anti-NIH audit."],
    },
    {
        "hypothesis_id": "decode_carrying_hypervectors",
        "title": "Decode-Carrying Hypervectors remain a composed child hypothesis, not an established memory architecture",
        "category": "DEFERRED_ARCHITECTURE",
        "origin": "Research backlog child hypothesis",
        "evidence_status": "DEFERRED_HYPOTHESIS",
        "maturity": "STRONG_PROTOTYPE_HYPOTHESIS",
        "implementation_status": "NOT_AUTHORIZED",
        "research_question": "Can semantic records co-activate decode-relevant local trace metadata and trace-routing fingerprints in the same ambient representation?",
        "method": "Documentation-only hypothesis",
        "substrate": "Future decode-carrying architecture",
        "operation_contract": "Semantic payload plus decode capsule plus trace fingerprint",
        "dimensions": "N/A",
        "factor_count": "N/A",
        "search_space": "Not executed",
        "noise_contract": "Not executed",
        "information_added": "decode capsule and trace fingerprint",
        "compute_added": "future trace-conditioned decoding",
        "prior_added": "trace routing priors",
        "exact_side_information": "partial exact metadata in proposed capsule",
        "primary_result": "Only the hypothesis and anti-NIH boundaries were recorded; no implementation was authorized.",
        "primary_failure_point": "Novelty, capacity, and practical benefit remain unestablished.",
        "safety_outcome": "The doc explicitly forbids overclaiming self-decoding or unlimited capacity.",
        "cost_outcome": "Unknown and likely nontrivial because same-space storage is not free.",
        "baselines": ["ordinary sidecar DAG", "ANN/LSH sidecar retrieval"],
        "controls": ["anti-NIH matrix only"],
        "evidence": {
            "commits": [],
            "protocol_hashes": [],
            "result_paths": ["docs/research/DECODE_CARRYING_HYPERVECTORS_HYPOTHESIS.md"],
            "tests": [],
            "execution_scale": "Design only",
            "heldout_status": "No execution",
        },
        "results": {
            "primary_metrics": [],
            "secondary_metrics": [],
            "qualitative_observations": [
                "Exact local decode metadata was deemed technically plausible.",
                "Same-space trace fingerprint remained a plausible prototype candidate only."
            ],
        },
        "failure_modes": ["semantic/trace contamination", "capacity overclaim", "identity-from-similarity confusion"],
        "causal_interpretation": "The hypothesis composes known ideas but is not established evidence.",
        "allowed_claims": ["Decode-carrying hypervectors are a deferred hypothesis with explicit claim boundaries."],
        "forbidden_claims": ["Novel architecture confirmed", "models human thought", "automatic speed from same-space storage"],
        "prior_art": ["exact provenance DAG", "LSH/ANN", "orthogonal subspaces", "typed handles"],
        "architectural_disposition": "DEFERRED_HYPOTHESIS",
        "reopen_conditions": ["Reopen only after held-out closure and a dedicated prior-art audit."],
    },
]

COST_MATRIX_ROWS = [
    {
        "Method": "MAP resonator baseline",
        "More dimensions": "no",
        "More bits per coordinate": "no",
        "Exact side information": "no",
        "Structured code": "no",
        "More decoder compute": "yes",
        "Restricted search domain": "optional",
        "External context": "optional",
        "Reduced coverage / abstention": "yes",
        "Exact fallback": "optional",
        "Observed benefit": "bounded recoverability in intermediate region",
        "Observed limitation": "capacity collapse and compute saturation",
    },
    {
        "Method": "Level 1 semantic context routing",
        "More dimensions": "no",
        "More bits per coordinate": "no",
        "Exact side information": "no",
        "Structured code": "no",
        "More decoder compute": "sometimes less",
        "Restricted search domain": "yes",
        "External context": "yes",
        "Reduced coverage / abstention": "yes",
        "Exact fallback": "yes",
        "Observed benefit": "beats random subsets in tested envelope",
        "Observed limitation": "needs fallback and bounded claims",
    },
    {
        "Method": "NeCo / generic linear clean U1",
        "More dimensions": "not primary mechanism",
        "More bits per coordinate": "no",
        "Exact side information": "no",
        "Structured code": "yes",
        "More decoder compute": "GF(2) solve cost",
        "Restricted search domain": "yes",
        "External context": "no",
        "Reduced coverage / abstention": "task-limited",
        "Exact fallback": "no",
        "Observed benefit": "clean U1 exact recovery",
        "Observed limitation": "no noisy superiority claim",
    },
    {
        "Method": "Symbolic exact baseline",
        "More dimensions": "no",
        "More bits per coordinate": "exact tuple storage",
        "Exact side information": "yes",
        "Structured code": "yes",
        "More decoder compute": "low",
        "Restricted search domain": "exact",
        "External context": "no",
        "Reduced coverage / abstention": "no",
        "Exact fallback": "built in",
        "Observed benefit": "dominates clean U1",
        "Observed limitation": "changes the task by preserving exact structure",
    },
    {
        "Method": "Semantic LSH trace routing",
        "More dimensions": "no",
        "More bits per coordinate": "no",
        "Exact side information": "trace sidecar for validation",
        "Structured code": "routing projections",
        "More decoder compute": "routing + reranking",
        "Restricted search domain": "yes",
        "External context": "no",
        "Reduced coverage / abstention": "yes",
        "Exact fallback": "yes",
        "Observed benefit": "useful trace-neighborhood locality",
        "Observed limitation": "loses to exact packed scan at N=10k",
    },
    {
        "Method": "Exact packed binary scan",
        "More dimensions": "no",
        "More bits per coordinate": "packed bits only",
        "Exact side information": "trace sidecar for validation",
        "Structured code": "no",
        "More decoder compute": "exact scan cost",
        "Restricted search domain": "no",
        "External context": "no",
        "Reduced coverage / abstention": "ambiguity only",
        "Exact fallback": "n/a",
        "Observed benefit": "best practical frontier at tested N=10k",
        "Observed limitation": "may lose at larger scale; not evaluated there yet",
    },
    {
        "Method": "Cross-substrate MAP/BCF portfolio",
        "More dimensions": "no",
        "More bits per coordinate": "no",
        "Exact side information": "no",
        "Structured code": "dual native encodings",
        "More decoder compute": "sometimes cumulative",
        "Restricted search domain": "static threshold or cascade",
        "External context": "no",
        "Reduced coverage / abstention": "yes",
        "Exact fallback": "no",
        "Observed benefit": "easy-cell latency trimming through a trivial static route",
        "Observed limitation": "BCF dominated the hard/non-easy frontier, so no residual instance-level oracle value survived",
    },
    {
        "Method": "Exact first-order sidecar DAG",
        "More dimensions": "no",
        "More bits per coordinate": "manifest bytes",
        "Exact side information": "yes",
        "Structured code": "exact DAG",
        "More decoder compute": "recursive replay",
        "Restricted search domain": "exact",
        "External context": "no",
        "Reduced coverage / abstention": "typed failures only",
        "Exact fallback": "yes",
        "Observed benefit": "safe exact replay after record retrieval",
        "Observed limitation": "does not solve initial record localization",
    },
    {
        "Method": "Inline packed manifest",
        "More dimensions": "possibly if fixed-total",
        "More bits per coordinate": "manifest bytes",
        "Exact side information": "yes",
        "Structured code": "exact DAG",
        "More decoder compute": "recursive replay",
        "Restricted search domain": "exact",
        "External context": "no",
        "Reduced coverage / abstention": "typed failures only",
        "Exact fallback": "yes",
        "Observed benefit": "no extra scientific benefit over sidecar",
        "Observed limitation": "packaging alone did not justify itself",
    },
    {
        "Method": "Exact carried trace token",
        "More dimensions": "optional trace dims",
        "More bits per coordinate": "exact token bits",
        "Exact side information": "yes",
        "Structured code": "exact token / ECC",
        "More decoder compute": "low",
        "Restricted search domain": "exact",
        "External context": "no",
        "Reduced coverage / abstention": "yes under corruption",
        "Exact fallback": "optional",
        "Observed benefit": "helps detached activation",
        "Observed limitation": "placement-specific capsule advantage not supported",
    },
    {
        "Method": "Conflict-guided tags",
        "More dimensions": "sometimes",
        "More bits per coordinate": "yes",
        "Exact side information": "no",
        "Structured code": "weak sign hints only",
        "More decoder compute": "repair search",
        "Restricted search domain": "no",
        "External context": "no",
        "Reduced coverage / abstention": "no",
        "Exact fallback": "no",
        "Observed benefit": "none that survived controls",
        "Observed limitation": "equal-bit extra dimensions dominated",
    },
    {
        "Method": "Decoder-certified atomic admission",
        "More dimensions": "no",
        "More bits per coordinate": "no",
        "Exact side information": "no",
        "Structured code": "candidate-pool selection",
        "More decoder compute": "high offline insertion cost",
        "Restricted search domain": "indirectly",
        "External context": "no",
        "Reduced coverage / abstention": "possible no-commit",
        "Exact fallback": "no",
        "Observed benefit": "not stably supported",
        "Observed limitation": "causal advantage not confirmed",
    },
    {
        "Method": "Block-LUT residue plane",
        "More dimensions": "no",
        "More bits per coordinate": "quantized residue tokens",
        "Exact side information": "MAP-I upper bound only",
        "Structured code": "block dictionary",
        "More decoder compute": "soft LUT weighting",
        "Restricted search domain": "no",
        "External context": "no",
        "Reduced coverage / abstention": "possible thresholding",
        "Exact fallback": "no",
        "Observed benefit": "soft information beats sign-only",
        "Observed limitation": "dictionary complexity lost to equal-bit extra dimensions",
    },
]

CLAIMS = [
    {
        "claim_id": "claim_context_beats_random",
        "text": "Semantic context beat random candidate selection in the tested Level 1 single-product settings.",
        "status": "CONFIRMED_IN_FROZEN_ENVELOPE",
        "scope": "Level 1 single-product context-routing envelope only",
        "supporting_evidence": ["level1_context_conditioned_search"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["universal context superiority", "full substrate independence"],
    },
    {
        "claim_id": "claim_context_transfer_bcf_selector",
        "text": "The external context-selection seam transferred to the official IBM BCF selector level under a scoped single-product contract.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Selector-level transfer only",
        "supporting_evidence": ["level1_context_conditioned_search", "level1f_bcf_selector_transfer"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md"],
        "forbidden_strengthenings": ["full BCF control-stack transfer", "broad parity claims"],
    },
    {
        "claim_id": "claim_map_intermediate_region",
        "text": "MAP resonator recoverability shows a bounded intermediate region under the tested clean U1 compute budgets.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Level 3.2 / 3.2b clean U1 budgets only",
        "supporting_evidence": ["level3_2_map_budget_robustness"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["universal impossibility theorem for VSA factorization"],
    },
    {
        "claim_id": "claim_linear_code_paper_reproduced",
        "text": "The NeCo linear-code paper contract was reproduced for clean U1 with explicit GF(2) constraints.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Clean U1 paper contract only",
        "supporting_evidence": ["level3_3_linear_code_reproduction"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "paper/prior_art_matrix.md"],
        "forbidden_strengthenings": ["noisy superiority or general linear-code dominance"],
    },
    {
        "claim_id": "claim_symbolic_baseline_dominates_clean_u1",
        "text": "The symbolic exact baseline dominated the tested clean U1 task envelope.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Level 3.4 clean U1 only",
        "supporting_evidence": ["level3_4_algebraic_baseline_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["universal advantage in noisy or open-world tasks"],
    },
    {
        "claim_id": "claim_noise_requires_typed_contracts",
        "text": "Noise comparisons require explicit typed contracts separating external corruption from native substrate behavior.",
        "status": "DESIGN_PRINCIPLE",
        "scope": "Repository-wide protocol discipline",
        "supporting_evidence": ["level3_5a_noise_contract_audit", "level3_5b_confirmatory_protocol_discipline"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["claiming raw p values are comparable across incompatible substrates"],
    },
    {
        "claim_id": "claim_confirmatory_gates_must_be_prospective",
        "text": "Executable confirmatory gates must be fully serialized before the first held-out observation.",
        "status": "CONFIRMED_IN_FROZEN_ENVELOPE",
        "scope": "Level 3.5b confirmatory protocol discipline",
        "supporting_evidence": ["level3_5b_confirmatory_protocol_discipline", "level3_5b_zero_trial_integrity_blocks"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "docs/PUBLIC_RELEASE_AUDIT.md"],
        "forbidden_strengthenings": ["turning blocked runs into substantive frontier evidence"],
    },
    {
        "claim_id": "claim_semantic_lsh_locality",
        "text": "Noisy MAP semantic cues contain useful locality for retrieving associated creation-trace neighborhoods in a bounded development envelope.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Lazy-trace Stage A / A.1 development-only envelope",
        "supporting_evidence": ["lazy_trace_stage_a_semantic_locality"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["exact provenance from semantic similarity", "held-out confirmation"],
    },
    {
        "claim_id": "claim_exact_binary_scan_best_at_10k",
        "text": "At N=10,000 in the tested Stage A.2a envelope, exact packed binary scan was the best practical trace-retrieval baseline.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Stage A.2a primary cell only",
        "supporting_evidence": ["lazy_trace_stage_a2a_mature_index_shootout"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["all approximate routing is useless at every scale"],
    },
    {
        "claim_id": "claim_first_order_coactivation_partial",
        "text": "First-order trace co-activation is only partially supported and presently trails exact sidecar retrieval as a practical baseline.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "First-order trace co-activation development envelope",
        "supporting_evidence": ["first_order_trace_coactivation", "exact_capsule_contract_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["full decode-carrying memory", "runtime authorization"],
    },
    {
        "claim_id": "claim_plain_handle_beats_isolated_capsule",
        "text": "Plain typed exact handles matched or beat isolated exact capsule placement under equal-information and equal-bit contracts.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Exact capsule closure only",
        "supporting_evidence": ["exact_capsule_contract_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["exact side information is useless"],
    },
    {
        "claim_id": "claim_recursive_replay_safe_after_retrieval",
        "text": "Exact first-order manifests can support safe recursive replay after the record has already been retrieved.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Self-describing record v0.1 replay path only",
        "supporting_evidence": ["self_describing_record_sidecar_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["self-addressing from noisy semantic cue", "new VSA algorithm"],
    },
    {
        "claim_id": "claim_decoder_certified_admission_not_supported",
        "text": "Decoder-certified atomic admission did not show a supported generalizable recovery advantage in the tested v0.1 envelope.",
        "status": "NOT_SUPPORTED",
        "scope": "Decoder-certified codebook v0.1",
        "supporting_evidence": ["decoder_certified_codebook"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md", "paper/failure_mode_atlas.md"],
        "forbidden_strengthenings": ["directional improvements imply architecture promotion"],
    },
    {
        "claim_id": "claim_tagged_repair_not_supported",
        "text": "Conflict-guided tagged-symbol repair did not show a supported recovery advantage over simpler equal-bit baselines.",
        "status": "NOT_SUPPORTED",
        "scope": "Tagged-symbol repair v0.1",
        "supporting_evidence": ["decoder_guided_tag_repair"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["weak reliability hints are enough to recover exact structure"],
    },
    {
        "claim_id": "claim_inline_manifest_advantage_not_supported",
        "text": "Inline packed manifest placement did not show a supported advantage over an ordinary sidecar DAG in the tested replay envelope.",
        "status": "NOT_SUPPORTED",
        "scope": "Self-describing record v0.1 packaging comparison",
        "supporting_evidence": ["self_describing_record_sidecar_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["physical co-location creates scientific advantage by itself"],
    },
    {
        "claim_id": "claim_block_residue_advantage_not_supported",
        "text": "Block codebook residue compression did not create a supported recovery-storage frontier advantage over scalar residue or equal-bit extra dimensions.",
        "status": "NOT_SUPPORTED",
        "scope": "Codebook residue v0.1",
        "supporting_evidence": ["codebook_residue_block_lut"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["soft information implies block dictionary superiority"],
    },
    {
        "claim_id": "claim_bcf_dominates_common_clean_portfolio_envelope",
        "text": "In the tested clean common F=3 envelope, BCF_NATIVE dominated the hard/non-easy paired instances that defeated the MAP baselines.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Cross-substrate oracle complementarity v0.1 clean common envelope only",
        "supporting_evidence": ["oracle_portfolio_complementarity_v0_1"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["BCF universally dominates MAP in every task or noise contract", "BCF is always the best substrate"],
    },
    {
        "claim_id": "claim_instance_router_not_supported_in_common_clean_envelope",
        "text": "The tested clean F=3 common envelope did not justify an instance-level cross-substrate router beyond a trivial M-threshold static route.",
        "status": "NOT_SUPPORTED",
        "scope": "Cross-substrate oracle complementarity v0.1 clean common envelope only",
        "supporting_evidence": ["oracle_portfolio_complementarity_v0_1"],
        "contradicting_evidence": [],
        "allowed_locations": ["paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["portfolio routing is useless in every possible contract", "static thresholds remain sufficient under noise or other substrates"],
    },
    {
        "claim_id": "claim_recoverability_has_a_cost",
        "text": "Reliable recovery in this repository's tasks always required paying cost somewhere: more structure, more bits, more compute, stronger priors, abstention, or exact fallback.",
        "status": "DESIGN_PRINCIPLE",
        "scope": "Repository-wide empirical synthesis",
        "supporting_evidence": [
            "level1_context_conditioned_search",
            "level3_2_map_budget_robustness",
            "level3_4_algebraic_baseline_closure",
            "exact_capsule_contract_closure",
            "self_describing_record_sidecar_closure",
            "codebook_residue_block_lut",
        ],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["new impossibility theorem", "all VSA recovery is impossible"],
    },
    {
        "claim_id": "claim_no_universal_impossibility_theorem",
        "text": "This repository does not prove a universal impossibility theorem for VSA factorization or recoverability.",
        "status": "DESIGN_PRINCIPLE",
        "scope": "Repository-wide claim boundary",
        "supporting_evidence": ["level3_2_map_budget_robustness", "level3_3_linear_code_reproduction", "level3_4_algebraic_baseline_closure"],
        "contradicting_evidence": [],
        "allowed_locations": ["README.md", "paper/manuscript.md", "RESEARCH_STATUS.md"],
        "forbidden_strengthenings": ["universal negative theorem"],
    },
]

FAILURE_MODES = [
    {
        "failure_mode": "capacity_collapse",
        "description": "Decoder accuracy drops sharply when candidate domains or bundle width exceed the substrate's practical envelope.",
        "observable_signature": "Recovery flattening or collapse under modest added scale despite more compute.",
        "affected_methods": ["MAP resonator baseline", "bundling soft-information lines"],
        "how_detected": "Level 3.2 / 3.2b budget robustness and bundling comparisons",
        "what_helped": "more structure, exact baselines, abstention",
        "what_failed": "compute alone, warm continuation myths",
        "safety_consequence": "Can trigger silent wrong outputs if acceptance is not gated.",
        "architectural_response": "Prefer bounded claims, abstention, or exact fallback.",
        "evidence_refs": ["level3_2_map_budget_robustness", "codebook_residue_block_lut"],
    },
    {
        "failure_mode": "false_attractor",
        "description": "Iterative decoders settle into wrong stable states that still look internally coherent.",
        "observable_signature": "Wrong reconstruction with apparent convergence or high self-consistency.",
        "affected_methods": ["MAP resonator", "trace-free replay portfolio"],
        "how_detected": "Level 1 and Level 3 MAP analyses",
        "what_helped": "selective acceptance, verifier-backed reconstruction checks",
        "what_failed": "cheap probes and warm continuation",
        "safety_consequence": "Raises silent wrong acceptance risk.",
        "architectural_response": "Keep an explicit verifier and abstention.",
        "evidence_refs": ["level1_context_conditioned_search", "level3_2_map_budget_robustness"],
    },
    {
        "failure_mode": "false_consensus",
        "description": "Multiple restarts or weak evidential hints agree on the same wrong answer.",
        "observable_signature": "High apparent confidence without ground-truth recovery.",
        "affected_methods": ["decoder-certified admission", "tagged-symbol repair"],
        "how_detected": "Construction and repair v0.1 lines",
        "what_helped": "shuffled controls and exact verification",
        "what_failed": "using decoder confidence as a proxy for truth",
        "safety_consequence": "Can silently promote the wrong architecture.",
        "architectural_response": "Demand causal controls and held-out discipline.",
        "evidence_refs": ["decoder_certified_codebook", "decoder_guided_tag_repair"],
    },
    {
        "failure_mode": "context_exclusion",
        "description": "A context policy excludes the true candidate from the narrowed domain.",
        "observable_signature": "Coverage falls unless broad fallback is available.",
        "affected_methods": ["Level 1 context routing", "Level 2C existing matcher overlay"],
        "how_detected": "Fallback and coverage analysis",
        "what_helped": "cold broad fallback and abstention",
        "what_failed": "overconfident narrow context",
        "safety_consequence": "False negatives or forced wrong commits.",
        "architectural_response": "Always preserve a safe expansion path.",
        "evidence_refs": ["level1_context_conditioned_search", "level2c_existing_matcher_context_policy"],
    },
    {
        "failure_mode": "context_misrouting",
        "description": "Context steers compute to the wrong mechanism or candidate subset.",
        "observable_signature": "Utility gain disappears when fallback is disabled.",
        "affected_methods": ["Level 2A temporal retrieval", "Level 2B controller seam"],
        "how_detected": "Temporal-memory and prior-art closures",
        "what_helped": "exact indexed retrieval and conservative authority control",
        "what_failed": "unqualified controller ambition",
        "safety_consequence": "Wasted compute or false commit risk.",
        "architectural_response": "Keep controller seams thin and measurable.",
        "evidence_refs": ["level2a_temporal_memory_narrow", "level2b_portable_context_controller"],
    },
    {
        "failure_mode": "certification_overfit",
        "description": "A construction rule looks strong on its own certification workload but fails to generalize.",
        "observable_signature": "Arm C improves on certification but not on validation/final development evaluation.",
        "affected_methods": ["decoder-certified codebook"],
        "how_detected": "Certification/evaluation split in v0.1",
        "what_helped": "shuffled-score control and old-atom regression set",
        "what_failed": "decoder-linked admission as a general recipe",
        "safety_consequence": "Can spend large offline compute for illusory gains.",
        "architectural_response": "Block the line unless it survives unseen evaluation and equal-risk comparison.",
        "evidence_refs": ["decoder_certified_codebook"],
    },
    {
        "failure_mode": "silent_wrong_acceptance",
        "description": "A method returns a wrong result without surfacing uncertainty or typed failure.",
        "observable_signature": "Conditional risk among accepted outputs rises above zero.",
        "affected_methods": ["semantic fallbacks", "ungated decoders", "corrupted exact-handle paths"],
        "how_detected": "Repository-wide verifier-backed metrics",
        "what_helped": "typed validators, abstention, exact digests, ambiguity outcomes",
        "what_failed": "blind fallback and unverified top-1 acceptance",
        "safety_consequence": "Most serious safety failure in the atlas.",
        "architectural_response": "Favor abstention-first designs and exact verification.",
        "evidence_refs": ["exact_capsule_contract_closure", "self_describing_record_sidecar_closure", "first_order_trace_coactivation"],
    },
    {
        "failure_mode": "native_substrate_mismatch",
        "description": "A competitor or alternative substrate cannot satisfy the repository's task contract without changing the task.",
        "observable_signature": "API mismatch, shared codebook where factor-specific domains are required, or incomparable noise semantics.",
        "affected_methods": ["HoloVec audit", "cross-substrate noise claims"],
        "how_detected": "Level 1F and Level 3.5a audits",
        "what_helped": "anti-NIH audits and typed contract matrices",
        "what_failed": "forcing the competitor into the benchmark",
        "safety_consequence": "False comparisons and bad architectural inference.",
        "architectural_response": "Block or narrow claims rather than rewrite upstream methods.",
        "evidence_refs": ["level1f_holovec_task_mismatch", "level3_5a_noise_contract_audit"],
    },
    {
        "failure_mode": "compute_non_dominance",
        "description": "A more complicated method adds compute but fails to create a better recovery-risk frontier.",
        "observable_signature": "Shuffled controls or exact baselines match the more complex method.",
        "affected_methods": ["decoder-certified codebook", "tagged repair", "thin LSH at N=10k"],
        "how_detected": "Equal-budget controls and mature baseline shootouts",
        "what_helped": "equal-information, equal-bit, and equal-candidate controls",
        "what_failed": "complex construction or routing alone",
        "safety_consequence": "Wasted engineering effort and misleading optimization.",
        "architectural_response": "Prefer simpler adopted baselines when the frontier is dominated.",
        "evidence_refs": ["decoder_certified_codebook", "decoder_guided_tag_repair", "lazy_trace_stage_a2a_mature_index_shootout"],
    },
    {
        "failure_mode": "storage_non_dominance",
        "description": "A compressed or packed representation adds storage complexity without creating a better recovery-storage point.",
        "observable_signature": "Equal-bit extra dimensions or ordinary sidecar storage dominates.",
        "affected_methods": ["block residue codebook", "inline manifest packing"],
        "how_detected": "Equal-bit and sidecar-vs-inline controls",
        "what_helped": "physical bit accounting and deployable-byte accounting",
        "what_failed": "compression or packing aesthetics alone",
        "safety_consequence": "Bigger artifact and maintenance burden without scientific benefit.",
        "architectural_response": "Adopt simpler storage when packaging advantage is not measured.",
        "evidence_refs": ["codebook_residue_block_lut", "self_describing_record_sidecar_closure"],
    },
    {
        "failure_mode": "packaging_non_benefit",
        "description": "A new physical packing layout does not create any information advantage over an ordinary sidecar.",
        "observable_signature": "Sidecar and inline packed variants have equal logical behavior and similar bytes/latency.",
        "affected_methods": ["inline packed manifest", "isolated exact capsule"],
        "how_detected": "Equal-information placement tests",
        "what_helped": "ordinary sidecar baselines",
        "what_failed": "same bits in a new physical wrapper",
        "safety_consequence": "Can fuel architecture fiction without added capability.",
        "architectural_response": "Say plainly that packaging alone is not a scientific result.",
        "evidence_refs": ["self_describing_record_sidecar_closure", "exact_capsule_contract_closure"],
    },
    {
        "failure_mode": "wrong_but_valid_exact_handle",
        "description": "An exact-looking operand or trace handle points to a real but wrong record.",
        "observable_signature": "Manifest or capsule decodes structurally, but replay digest mismatches or provenance becomes inconsistent.",
        "affected_methods": ["self-describing record", "exact capsule closure"],
        "how_detected": "Wrong-valid handle and wrong-valid capsule corruption tests",
        "what_helped": "semantic commitment digests, record-association checks, typed failure codes",
        "what_failed": "trusting structure without verification",
        "safety_consequence": "Potential silent false provenance if unguarded.",
        "architectural_response": "Require verification against committed semantics or exact digests.",
        "evidence_refs": ["self_describing_record_sidecar_closure", "exact_capsule_contract_closure"],
    },
    {
        "failure_mode": "dangling_or_stale_handle",
        "description": "A manifest references a missing parent or an outdated version.",
        "observable_signature": "Typed failure such as DANGLING_OPERAND_REF or PARENT_VERSION_MISMATCH.",
        "affected_methods": ["self-describing record", "future lazy reification hypotheses"],
        "how_detected": "Manifest corruption and version tests",
        "what_helped": "immutable/versioned record identities and transactional commit",
        "what_failed": "assuming exact handles are self-healing",
        "safety_consequence": "Replay cannot continue and must not fabricate history.",
        "architectural_response": "Prefer explicit typed fallback over silent partial reconstruction.",
        "evidence_refs": ["self_describing_record_sidecar_closure"],
    },
    {
        "failure_mode": "protocol_leakage",
        "description": "Confirmatory logic is changed after seeing development or held-out outcomes.",
        "observable_signature": "Blocked runner, missing gate semantics, or unauthorized protocol diffs.",
        "affected_methods": ["Level 3.5 protocol lines"],
        "how_detected": "Gate-source audits, diff allowlists, zero-trial integrity blocks",
        "what_helped": "prospective executable gate serialization and validator coverage",
        "what_failed": "implicit verdict labels and post-hoc threshold invention",
        "safety_consequence": "Invalid confirmatory claims.",
        "architectural_response": "Fail closed and preserve immutable block evidence.",
        "evidence_refs": ["level3_5a_noise_contract_audit", "level3_5b_confirmatory_protocol_discipline", "level3_5b_zero_trial_integrity_blocks"],
    },
    {
        "failure_mode": "dominant_single_method",
        "description": "A prospective portfolio shows pairwise rescues among weaker methods, but one lawful method already covers the hard instances, erasing practical oracle gain.",
        "observable_signature": "Direct oracle and verifier-constrained oracle match the best single method on hard/non-easy cells, while static routing captures any residual easy-cell latency trim.",
        "affected_methods": ["cross-substrate portfolio audits", "prospective cascades"],
        "how_detected": "Paired clean F=3 complementarity audit with best-single, oracle, cascade, and static-route analyses",
        "what_helped": "paired trial matrices, verifier-constrained oracle, hard-cell pooling",
        "what_failed": "learned-router or hardware escalation before residual routing regret exists",
        "safety_consequence": "Can rationalize unnecessary routing complexity while adding no verified coverage.",
        "architectural_response": "Adopt the dominant single method or trivial static threshold and stop the router line.",
        "evidence_refs": ["oracle_portfolio_complementarity_v0_1"],
    },
]

PRIOR_ART = [
    {
        "citation_key": "plate1995hrr",
        "title": "Holographic Reduced Representations",
        "authors": "Tony A. Plate",
        "year": 1995,
        "source": "Primary paper",
        "doi_or_arxiv": "https://pubmed.ncbi.nlm.nih.gov/18263348/",
        "official_code": "",
        "method_category": "VSA algebra",
        "substrate": "HRR / distributed representations",
        "task": "Compositional representation and cleanup",
        "main_claim": "Distributed compositional representations can support structured symbolic processing.",
        "evidence_type": "theory + experiments",
        "reported_scale": "classical foundational work",
        "reported_metrics": "representation fidelity and composition behavior",
        "closest_repo_hypotheses": ["level1_context_conditioned_search", "level3_2_map_budget_robustness"],
        "what_repo_reproduced": "Used as background only; did not attempt direct HRR reproduction.",
        "what_repo_did_not_reproduce": "Original HRR-specific experiments.",
        "transfer_limit": "The repo mostly studies MAP and adjacent substrates, not HRR directly.",
        "contract_mismatch": "Different substrate and cleanup assumptions.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "kanerva2009hyperdimensional",
        "title": "Hyperdimensional Computing: An Introduction to Computing in Distributed Representation with High-Dimensional Random Vectors",
        "authors": "Pentti Kanerva",
        "year": 2009,
        "source": "Primary paper",
        "doi_or_arxiv": "https://redwood.berkeley.edu/wp-content/uploads/2020/05/kanerva2009-hyperdimensional-computing.pdf",
        "official_code": "",
        "method_category": "VSA/HDC overview",
        "substrate": "HDC overview",
        "task": "General high-dimensional representation",
        "main_claim": "Distributed random high-dimensional vectors support robust symbolic-like computation.",
        "evidence_type": "theory + examples",
        "reported_scale": "foundational overview",
        "reported_metrics": "conceptual behavior",
        "closest_repo_hypotheses": ["level3_2_map_budget_robustness", "codebook_residue_block_lut"],
        "what_repo_reproduced": "Only bounded MAP/HDC envelopes and negative results.",
        "what_repo_did_not_reproduce": "Universal HDC claims.",
        "transfer_limit": "The repo tracks recoverability cost rather than general HDC expressiveness.",
        "contract_mismatch": "The atlas emphasizes explicit risk, abstention, and exact fallbacks.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "kanerva1988sdm",
        "title": "Sparse Distributed Memory",
        "authors": "Pentti Kanerva",
        "year": 1988,
        "source": "Primary monograph",
        "doi_or_arxiv": "https://www.routledge.com/Sparse-Distributed-Memory/Kanerva/p/book/9780262111393",
        "official_code": "",
        "method_category": "Associative memory",
        "substrate": "SDM",
        "task": "Noisy addressable memory",
        "main_claim": "Sparse distributed memory supports robust associative access under noisy cues.",
        "evidence_type": "theory + simulation",
        "reported_scale": "foundational memory model",
        "reported_metrics": "retrieval under noise",
        "closest_repo_hypotheses": ["lazy_trace_stage_a_semantic_locality", "lazy_trace_stage_a2a_mature_index_shootout"],
        "what_repo_reproduced": "No direct SDM implementation yet.",
        "what_repo_did_not_reproduce": "SDM routing or hard-location comparisons.",
        "transfer_limit": "SDM is deferred to a future baseline stage.",
        "contract_mismatch": "The repository focused first on exact baselines and mature indexes.",
        "anti_nih_verdict": "DEFER_COMPARE",
    },
    {
        "citation_key": "frady2020resonator",
        "title": "Resonator Networks, 1: An Efficient Solution for Factoring High-Dimensional Distributed Representations of Data Structures",
        "authors": "E. Paxon Frady and Friedrich T. Sommer",
        "year": 2020,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2006.15464",
        "official_code": "https://github.com/hyperdimensional-computing/torchhd",
        "method_category": "Resonator decoding",
        "substrate": "MAP / VSA factorization",
        "task": "Blind factorization",
        "main_claim": "Resonator networks can factor compositional VSA representations efficiently in bounded regimes.",
        "evidence_type": "theory + experiments",
        "reported_scale": "factorization benchmarks",
        "reported_metrics": "recovery accuracy, iterations",
        "closest_repo_hypotheses": ["level3_2_map_budget_robustness", "level1_context_conditioned_search"],
        "what_repo_reproduced": "TorchHD resonator-based MAP baselines and budget sweeps.",
        "what_repo_did_not_reproduce": "A new resonator algorithm.",
        "transfer_limit": "Repo claims remain bounded by explicit compute, risk, and domain contracts.",
        "contract_mismatch": "None for the reused baseline; broader architecture claims are separate.",
        "anti_nih_verdict": "ADOPT",
    },
    {
        "citation_key": "torchhd",
        "title": "TorchHD",
        "authors": "Hyperdimensional Computing community contributors",
        "year": 2024,
        "source": "Official repository",
        "doi_or_arxiv": "https://github.com/hyperdimensional-computing/torchhd",
        "official_code": "https://github.com/hyperdimensional-computing/torchhd",
        "method_category": "Implementation baseline",
        "substrate": "TorchHD",
        "task": "HDC/VSA primitives and resonator support",
        "main_claim": "Provide reusable HDC primitives rather than bespoke per-project implementations.",
        "evidence_type": "official code",
        "reported_scale": "library",
        "reported_metrics": "API surface",
        "closest_repo_hypotheses": ["level0_dependency_bootstrap", "level3_2_map_budget_robustness"],
        "what_repo_reproduced": "Direct reuse of MAP operations and resonator primitive.",
        "what_repo_did_not_reproduce": "No forked TorchHD runtime.",
        "transfer_limit": "The repo wraps it for task-specific experiments only.",
        "contract_mismatch": "None for the adopted baseline.",
        "anti_nih_verdict": "ADOPT",
    },
    {
        "citation_key": "holovec",
        "title": "HoloVec",
        "authors": "Twistient contributors",
        "year": 2024,
        "source": "Official repository",
        "doi_or_arxiv": "https://github.com/Twistient/HoloVec",
        "official_code": "https://github.com/Twistient/HoloVec",
        "method_category": "Alternative VSA cleanup",
        "substrate": "HoloVec attention cleanup",
        "task": "Attention-based cleanup and factorization",
        "main_claim": "Attention-style cleanup can support HDC operations.",
        "evidence_type": "official code",
        "reported_scale": "library and paper companion",
        "reported_metrics": "API functionality",
        "closest_repo_hypotheses": ["level1f_holovec_task_mismatch"],
        "what_repo_reproduced": "Dependency and API audit only.",
        "what_repo_did_not_reproduce": "Fair factor-specific benchmark transfer.",
        "transfer_limit": "The upstream API did not match factor-specific domains.",
        "contract_mismatch": "Shared flat codebook vs required per-factor domains.",
        "anti_nih_verdict": "WRAP_OR_BLOCK",
    },
    {
        "citation_key": "ibm_bcf_repo",
        "title": "In-Memory Factorization for Hyperdimensional Computing",
        "authors": "IBM Research contributors",
        "year": 2024,
        "source": "Official repository",
        "doi_or_arxiv": "https://github.com/IBM/in-memory-factorizer",
        "official_code": "https://github.com/IBM/in-memory-factorizer",
        "method_category": "BCF / exact competitor",
        "substrate": "IBM BCF",
        "task": "Factorization and capacity experiments",
        "main_claim": "Provide a native substrate and evaluation harness for block-code factorization.",
        "evidence_type": "official code",
        "reported_scale": "reference implementation",
        "reported_metrics": "capacity and factorization behavior",
        "closest_repo_hypotheses": ["level1f_bcf_selector_transfer", "level3_5b_confirmatory_protocol_discipline"],
        "what_repo_reproduced": "Scoped selector transfer and native-envelope reproduction.",
        "what_repo_did_not_reproduce": "Broad structured-mixture parity or full controller transfer.",
        "transfer_limit": "The repo adopted the official code rather than reimplementing BCF.",
        "contract_mismatch": "Broader parity claims remain outside the audited envelope.",
        "anti_nih_verdict": "ADOPT",
    },
    {
        "citation_key": "neco_linear_codes",
        "title": "Linear Codes for Hyperdimensional Computing",
        "authors": "NeCo paper authors",
        "year": 2024,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2403.03278",
        "official_code": "",
        "method_category": "Linear-code HDC",
        "substrate": "Linear codes",
        "task": "Exact recovery under structured code constraints",
        "main_claim": "Linear-code constructions can support recoverability in HDC tasks.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific benchmarks",
        "reported_metrics": "recovery under code constraints",
        "closest_repo_hypotheses": ["level3_3_linear_code_reproduction", "level3_4_algebraic_baseline_closure"],
        "what_repo_reproduced": "Clean U1 reproduction and algebraic baseline closure.",
        "what_repo_did_not_reproduce": "Noisy frontier or larger open-world claims.",
        "transfer_limit": "Only the paper's clean-U1 contract was ported.",
        "contract_mismatch": "Broader repository tasks include risk, abstention, and protocol discipline.",
        "anti_nih_verdict": "ADOPT_REPRODUCE",
    },
    {
        "citation_key": "faiss",
        "title": "Faiss: A library for efficient similarity search and clustering of dense vectors",
        "authors": "Jeff Johnson, Matthijs Douze, Hervé Jégou",
        "year": 2017,
        "source": "Primary paper / official project",
        "doi_or_arxiv": "https://arxiv.org/abs/1702.08734",
        "official_code": "https://github.com/facebookresearch/faiss",
        "method_category": "Similarity search",
        "substrate": "Exact and ANN indexes",
        "task": "Vector and binary similarity search",
        "main_claim": "Provide mature exact and ANN search primitives rather than ad hoc custom indexes.",
        "evidence_type": "paper + official code",
        "reported_scale": "large-scale similarity search",
        "reported_metrics": "latency, recall, memory",
        "closest_repo_hypotheses": ["lazy_trace_stage_a2a_mature_index_shootout"],
        "what_repo_reproduced": "Exact float, HNSW, exact binary, binary HNSW, binary multi-hash comparisons.",
        "what_repo_did_not_reproduce": "GPU and large-scale production tuning.",
        "transfer_limit": "The repository used Faiss as a mature baseline, not as new science.",
        "contract_mismatch": "Repo adds trace verification and ambiguity policy on top of search.",
        "anti_nih_verdict": "ADOPT",
    },
    {
        "citation_key": "jegou2011pq",
        "title": "Product Quantization for Nearest Neighbor Search",
        "authors": "Hervé Jégou, Matthijs Douze, Cordelia Schmid",
        "year": 2011,
        "source": "Primary paper",
        "doi_or_arxiv": "https://hal.science/inria-00514462/document",
        "official_code": "",
        "method_category": "Quantization",
        "substrate": "Product quantization",
        "task": "Compressed vector search",
        "main_claim": "Codebooks can compress vectors for search efficiently.",
        "evidence_type": "paper",
        "reported_scale": "nearest-neighbor search",
        "reported_metrics": "memory and recall trade-offs",
        "closest_repo_hypotheses": ["codebook_residue_block_lut"],
        "what_repo_reproduced": "No direct PQ reproduction; only a tiny deterministic block-LUT residue harness.",
        "what_repo_did_not_reproduce": "Mature PQ baselines or learned codebooks.",
        "transfer_limit": "The repository's residue line stayed intentionally tiny and anti-NIH.",
        "contract_mismatch": "Membership recovery from bundle residues is not generic ANN search.",
        "anti_nih_verdict": "COMPARE",
    },
    {
        "citation_key": "gray1998quantization",
        "title": "Quantization",
        "authors": "Robert M. Gray and David L. Neuhoff",
        "year": 1998,
        "source": "Primary survey",
        "doi_or_arxiv": "https://ee.stanford.edu/~gray/publications.html",
        "official_code": "",
        "method_category": "Quantization background",
        "substrate": "Scalar and vector quantization",
        "task": "Compression and distortion trade-offs",
        "main_claim": "Quantization introduces explicit rate-distortion trade-offs.",
        "evidence_type": "survey",
        "reported_scale": "general quantization theory",
        "reported_metrics": "distortion vs rate",
        "closest_repo_hypotheses": ["codebook_residue_block_lut"],
        "what_repo_reproduced": "Only tiny scalar and block residue controls.",
        "what_repo_did_not_reproduce": "General quantization algorithms or learned VQ.",
        "transfer_limit": "The atlas uses it as prior art, not as reproduced evidence.",
        "contract_mismatch": "Repository tasks are HDC-specific membership recovery rather than generic compression.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "selective_classification_survey",
        "title": "Selective Classification for Deep Neural Networks",
        "authors": "Yehuda Geifman and Ran El-Yaniv",
        "year": 2019,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/1705.08500",
        "official_code": "",
        "method_category": "Selective prediction / abstention",
        "substrate": "Selective classification",
        "task": "Risk-coverage trade-offs",
        "main_claim": "Abstention can improve reliability by reducing coverage.",
        "evidence_type": "paper",
        "reported_scale": "classification",
        "reported_metrics": "risk-coverage",
        "closest_repo_hypotheses": ["level1_context_conditioned_search", "first_order_trace_coactivation"],
        "what_repo_reproduced": "Selective acceptance and abstention-first policies across multiple seams.",
        "what_repo_did_not_reproduce": "The survey's specific model families.",
        "transfer_limit": "The repository ports the principle, not the full selective-classification stack.",
        "contract_mismatch": "The atlas applies the idea to decoder and replay acceptance rather than standard classification.",
        "anti_nih_verdict": "ADAPT",
    },
    {
        "citation_key": "merkle_dag_git",
        "title": "Git object model / content-addressed DAGs",
        "authors": "Git contributors",
        "year": 2005,
        "source": "Official documentation",
        "doi_or_arxiv": "https://git-scm.com/book/en/v2/Git-Internals-Git-Objects",
        "official_code": "https://git-scm.com/",
        "method_category": "Exact structure preservation",
        "substrate": "Content-addressed DAG",
        "task": "Versioned exact graph storage",
        "main_claim": "Exact immutable references and digests can preserve structure without semantic inference.",
        "evidence_type": "official documentation",
        "reported_scale": "production software system",
        "reported_metrics": "integrity and replay semantics",
        "closest_repo_hypotheses": ["self_describing_record_sidecar_closure", "lazy_composite_reification"],
        "what_repo_reproduced": "Only the design pattern of exact immutable handles and replay.",
        "what_repo_did_not_reproduce": "A general database or VCS runtime.",
        "transfer_limit": "Repo keeps the seam tiny and typed.",
        "contract_mismatch": "No claim that this is a new storage algorithm.",
        "anti_nih_verdict": "ADOPT",
    },
]

EVIDENCE_ENTRY_OVERRIDES = {
    "oracle_portfolio_complementarity_v0_1": {
        "primary_result": (
            "BCF_NATIVE covered the same clean hard/non-easy paired instances that defeated the MAP arms, "
            "so direct per-instance oracle exact-recovery gain over always-BCF was 0 in the common envelope."
        ),
        "primary_failure_point": (
            "Instance-level method selection value disappeared, and MAP-first sequential escalation was also "
            "not cost-effective on non-easy cells because verified exit rates stayed below measured break-even."
        ),
        "cost_outcome": (
            "Dual-view storage and probe cost were not justified: the only surviving economic gain was a trivial "
            "cell-level threshold that used MAP_D1024_FAST on the easy M=10 cell."
        ),
        "causal_interpretation": (
            "The stage separated two questions. Method-selection complementarity was not supported because BCF "
            "already solved the hard shared failures. Sequential escalation economics were also negative in the "
            "clean non-easy envelope because the fast-path verified exit rate did not amortize the probe."
        ),
        "allowed_claims": [
            "In the tested clean F=3 common envelope, BCF_NATIVE dominated the hard/non-easy frontier while MAP remained only an easy-cell latency path.",
            "A trivial M-threshold static route captured the only practical portfolio value observed in this stage.",
            "Current MAP-to-BCF dual-view sequential escalation was not cost-effective on clean non-easy cells."
        ],
    }
}

EXTRA_CLAIMS = [
    {
        "claim_id": "claim_recoverability_resource_accounting",
        "text": "Across the repository's evaluated mechanisms, recoverability improvements always consumed an identifiable additional resource such as dimension, precision, code structure, exact side information, context, compute, abstention, or exact fallback.",
        "status": "DESIGN_PRINCIPLE",
        "scope": "Repository-wide empirical synthesis and systematic mapping frame",
        "supporting_evidence": [
            "level1_context_conditioned_search",
            "level3_2_map_budget_robustness",
            "level3_4_algebraic_baseline_closure",
            "self_describing_record_sidecar_closure",
            "codebook_residue_block_lut",
            "oracle_portfolio_complementarity_v0_1",
        ],
        "contradicting_evidence": [],
        "allowed_locations": [
            "README.md",
            "paper/manuscript.md",
            "paper/method_resource_atlas.md",
        ],
        "forbidden_strengthenings": [
            "new impossibility theorem",
            "recoverability can be reduced to one universal scalar score",
        ],
    },
    {
        "claim_id": "claim_decoder_repair_not_free_in_tested_envelopes",
        "text": "In the tested repository envelopes, decoder-repair and soft-information mechanisms did not create a free recovery gain once representation cost, equal-bit controls, generalization, and silent-error safeguards were counted.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Tagged repair, decoder-certified admission, and residue-compression lines only",
        "supporting_evidence": [
            "decoder_certified_codebook",
            "decoder_guided_tag_repair",
            "codebook_residue_block_lut",
        ],
        "contradicting_evidence": [],
        "allowed_locations": [
            "paper/manuscript.md",
            "paper/failure_mode_atlas.md",
        ],
        "forbidden_strengthenings": [
            "decoder repair is universally useless",
            "soft information never helps under any contract",
        ],
    },
    {
        "claim_id": "claim_bcf_dominates_clean_non_easy_f3",
        "text": "Within the evaluated clean F=3 common envelope, the robust native BCF arm covered the same non-easy instances that defeated all tested MAP arms.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Cross-substrate oracle complementarity v0.1 clean non-easy cells only",
        "supporting_evidence": [
            "oracle_portfolio_complementarity_v0_1",
        ],
        "contradicting_evidence": [],
        "allowed_locations": [
            "paper/manuscript.md",
            "paper/architectural_decision_guide.md",
        ],
        "forbidden_strengthenings": [
            "BCF universally dominates MAP across noise, tasks, or hardware",
        ],
    },
    {
        "claim_id": "claim_current_map_bcf_escalation_not_cost_effective",
        "text": "A MAP-first, BCF-fallback dual-view escalation was not cost-effective on clean non-easy F=3 cells because the measured fast-path verified exit rate did not offset the additional probe cost.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Cross-substrate oracle complementarity v0.1 clean non-easy sequential-economics analysis only",
        "supporting_evidence": [
            "oracle_portfolio_complementarity_v0_1",
        ],
        "contradicting_evidence": [],
        "allowed_locations": [
            "paper/manuscript.md",
            "paper/architectural_decision_guide.md",
        ],
        "forbidden_strengthenings": [
            "sequential escalation is never useful",
            "the result transfers to noisy or non-F=3 contracts",
        ],
    },
    {
        "claim_id": "claim_static_cell_route_sufficient_in_current_envelope",
        "text": "In the evaluated clean common F=3 envelope, a trivial static route by M captured the only observed practical routing benefit.",
        "status": "SUPPORTED_DEVELOPMENT_ONLY",
        "scope": "Cross-substrate oracle complementarity v0.1 clean common envelope only",
        "supporting_evidence": [
            "oracle_portfolio_complementarity_v0_1",
        ],
        "contradicting_evidence": [],
        "allowed_locations": [
            "paper/manuscript.md",
            "paper/architectural_decision_guide.md",
        ],
        "forbidden_strengthenings": [
            "static thresholds are sufficient in every future contract",
        ],
    },
    {
        "claim_id": "claim_hardware_may_change_cost_frontier_literature_only",
        "text": "Hardware mechanisms such as in-memory compute, procedural generation, streaming, FPGA acceleration, and multi-bit memories may change the practical cost frontier for recoverability, but this repository has not measured those effects directly.",
        "status": "OPEN",
        "scope": "Literature synthesis only; not repository-measured",
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "allowed_locations": [
            "paper/manuscript.md",
            "paper/prior_art_matrix.md",
        ],
        "forbidden_strengthenings": [
            "measured FPGA or neuromorphic result in this repository",
            "hardware proves universal recoverability gains",
        ],
    },
]

FAILURE_MODE_OVERRIDES = {
    "capacity_collapse": {
        "reported_in_literature": ["frady2020resonator", "kleyko2022survey_part1"],
        "mechanistic_explanation": "Finite dimension, finite precision, and overlapping codebooks flatten the reconstruction landscape once interference exceeds the decoder's effective margin budget.",
        "resource_shortfall": ["R1_DIMENSION", "R7_DECODER_COMPUTE"],
        "mitigation": "Increase representational budget, narrow the task contract, or abstain before silent wrong acceptance.",
    },
    "false_attractor": {
        "reported_in_literature": ["frady2020resonator"],
        "mechanistic_explanation": "Iterative cleanup can settle into an energetically consistent but semantically wrong local optimum.",
        "resource_shortfall": ["R7_DECODER_COMPUTE", "R13_REDUCED_COVERAGE_ABSTENTION"],
    },
    "false_consensus": {
        "reported_in_literature": ["satzilla2011", "selective_classification_survey"],
        "mechanistic_explanation": "Agreement among retries or weak hints is not equivalent to ground-truth recovery when all hypotheses are driven by the same distorted evidence.",
        "resource_shortfall": ["R7_DECODER_COMPUTE", "R14_EXACT_FALLBACK"],
    },
    "context_exclusion": {
        "reported_in_literature": ["satzilla2011", "chow_reject_option"],
        "mechanistic_explanation": "A routing prior narrows the candidate set so aggressively that the true factor or tuple is removed before native decoding begins.",
        "resource_shortfall": ["R6_EXTERNAL_CONTEXT_OR_PRIOR", "R14_EXACT_FALLBACK"],
    },
    "context_misrouting": {
        "reported_in_literature": ["satzilla2011"],
        "mechanistic_explanation": "A controller or route prior allocates compute to the wrong mechanism, wasting budget without changing the underlying substrate error pattern.",
        "resource_shortfall": ["R6_EXTERNAL_CONTEXT_OR_PRIOR", "R7_DECODER_COMPUTE"],
    },
    "certification_overfit": {
        "reported_in_literature": ["satzilla2011"],
        "mechanistic_explanation": "Construction-time selection overfits to its own certification tuples and decoder seeds instead of creating a robust new codebook point.",
        "resource_shortfall": ["R11_PREPROCESSING_OR_MATERIALIZATION", "R7_DECODER_COMPUTE"],
    },
    "silent_wrong_acceptance": {
        "reported_in_literature": ["selective_classification_survey", "chow_reject_option"],
        "mechanistic_explanation": "Approximate evidence is treated as authoritative even though the information contract cannot disambiguate the true source structure.",
        "resource_shortfall": ["R13_REDUCED_COVERAGE_ABSTENTION", "R14_EXACT_FALLBACK"],
    },
    "native_substrate_mismatch": {
        "reported_in_literature": ["kleyko2022survey_part1", "vsa_comparison_2022"],
        "mechanistic_explanation": "Two methods may target similar symbolic tasks while relying on incompatible algebra, codebook semantics, stopping rules, or noise contracts.",
        "resource_shortfall": ["R4_STRUCTURED_CODE", "R6_EXTERNAL_CONTEXT_OR_PRIOR"],
    },
    "compute_non_dominance": {
        "reported_in_literature": ["satzilla2011", "gray1998quantization"],
        "mechanistic_explanation": "Extra compute or tuning explores more hypotheses but fails to move the verified frontier once strong simpler baselines are matched.",
        "resource_shortfall": ["R7_DECODER_COMPUTE", "R11_PREPROCESSING_OR_MATERIALIZATION"],
    },
    "storage_non_dominance": {
        "reported_in_literature": ["gray1998quantization", "jegou2011pq"],
        "mechanistic_explanation": "Compressed or packed structure increases byte complexity without preserving enough additional signal to beat equal-rate alternatives.",
        "resource_shortfall": ["R2_COORDINATE_PRECISION", "R11_PREPROCESSING_OR_MATERIALIZATION"],
    },
    "packaging_non_benefit": {
        "reported_in_literature": ["merkle_dag_git"],
        "mechanistic_explanation": "Changing physical colocation without changing the information contract cannot create new recoverability by itself.",
        "resource_shortfall": ["R5_EXACT_SIDE_INFORMATION"],
    },
    "wrong_but_valid_exact_handle": {
        "reported_in_literature": ["merkle_dag_git"],
        "mechanistic_explanation": "An exact-looking pointer is still unsafe if record association and semantic commitment are not independently verified.",
        "resource_shortfall": ["R5_EXACT_SIDE_INFORMATION", "R14_EXACT_FALLBACK"],
    },
    "dangling_or_stale_handle": {
        "reported_in_literature": ["merkle_dag_git"],
        "mechanistic_explanation": "Exact structure preserves only what still exists and remains version-compatible in the authoritative store.",
        "resource_shortfall": ["R5_EXACT_SIDE_INFORMATION", "R11_PREPROCESSING_OR_MATERIALIZATION"],
    },
    "protocol_leakage": {
        "reported_in_literature": ["selective_classification_survey"],
        "mechanistic_explanation": "Post-hoc gate changes erase the boundary between exploratory tuning and confirmatory evaluation.",
        "resource_shortfall": ["R11_PREPROCESSING_OR_MATERIALIZATION"],
    },
    "dominant_single_method": {
        "reported_in_literature": ["satzilla2011"],
        "mechanistic_explanation": "Pairwise rescue among weaker methods is irrelevant if one lawful method already covers the hard instances where routing was supposed to help.",
        "resource_shortfall": ["R12_DUAL_REPRESENTATION", "R7_DECODER_COMPUTE"],
    },
}

PRIOR_ART_EXTRA_ENTRIES = [
    {
        "citation_key": "kleyko2022survey_part1",
        "title": "A Survey on Hyperdimensional Computing aka Vector Symbolic Architectures, Part I: Models and Data Transformations",
        "authors": "Denis Kleyko et al.",
        "year": 2022,
        "source": "Primary survey",
        "doi_or_arxiv": "https://arxiv.org/abs/2111.06077",
        "official_code": "",
        "method_category": "Survey / taxonomy",
        "substrate": "Cross-VSA taxonomy",
        "task": "Representation and operation taxonomy",
        "main_claim": "VSA/HDC families differ materially in algebra, representation, and implementation trade-offs.",
        "evidence_type": "survey",
        "reported_scale": "broad field survey",
        "reported_metrics": "taxonomy, design dimensions, implementation families",
        "closest_repo_hypotheses": ["level0_dependency_bootstrap", "level3_5a_noise_contract_audit"],
        "what_repo_reproduced": "Used to normalize terminology and substrate comparisons.",
        "what_repo_did_not_reproduce": "No numerical survey meta-analysis.",
        "transfer_limit": "Survey evidence is taxonomic rather than directly rankable.",
        "contract_mismatch": "Heterogeneous substrates, tasks, and metrics.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "kleyko2023survey_part2",
        "title": "A Survey on Hyperdimensional Computing aka Vector Symbolic Architectures, Part II: Applications, Cognitive Models, and Challenges",
        "authors": "Denis Kleyko et al.",
        "year": 2023,
        "source": "Primary survey",
        "doi_or_arxiv": "https://arxiv.org/abs/2301.06042",
        "official_code": "",
        "method_category": "Survey / applications",
        "substrate": "Cross-VSA taxonomy",
        "task": "Applications, cognitive models, and hardware-relevant deployment context",
        "main_claim": "Application claims and hardware stories depend strongly on the chosen representation and operating assumptions.",
        "evidence_type": "survey",
        "reported_scale": "broad field survey",
        "reported_metrics": "application and challenge taxonomy",
        "closest_repo_hypotheses": ["level3_5a_noise_contract_audit", "oracle_portfolio_complementarity_v0_1"],
        "what_repo_reproduced": "Used to scope claims and transfer limits.",
        "what_repo_did_not_reproduce": "Broad application-level superiority claims.",
        "transfer_limit": "Descriptive only; not a common-harness benchmark.",
        "contract_mismatch": "Repository evidence focuses on recoverability rather than application accuracy.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "vsa_comparison_2022",
        "title": "A comparison of vector symbolic architectures",
        "authors": "Luca M. and collaborators",
        "year": 2022,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2001.11797",
        "official_code": "",
        "method_category": "Substrate comparison",
        "substrate": "Multiple VSA algebras",
        "task": "Cross-algebra comparison",
        "main_claim": "Different VSA algebras expose different representational and computational trade-offs.",
        "evidence_type": "paper",
        "reported_scale": "comparative study",
        "reported_metrics": "task accuracy across algebras",
        "closest_repo_hypotheses": ["level1f_holovec_task_mismatch", "level3_5a_noise_contract_audit"],
        "what_repo_reproduced": "Only narrow common-harness contrasts and audit logic.",
        "what_repo_did_not_reproduce": "A universal numeric ranking across algebras.",
        "transfer_limit": "Useful for taxonomy and mismatch warnings, not for direct leaderboard claims.",
        "contract_mismatch": "Different tasks and evaluation harnesses.",
        "anti_nih_verdict": "COMPARE",
    },
    {
        "citation_key": "ibm_bcf_paper",
        "title": "In-memory factorization of holographic perceptual representations",
        "authors": "IBM Research authors",
        "year": 2024,
        "source": "Primary paper",
        "doi_or_arxiv": "https://research.ibm.com/publications/in-memory-factorization-of-holographic-perceptual-representations",
        "official_code": "https://github.com/IBM/in-memory-factorizer",
        "method_category": "Structured recovery / hardware-aware substrate",
        "substrate": "BCF",
        "task": "Native factorization and hardware mapping",
        "main_claim": "Structured block-code representations can support efficient native factorization and hardware acceleration.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific clean factorization envelope",
        "reported_metrics": "recovery, capacity, hardware-oriented efficiency",
        "closest_repo_hypotheses": ["level1f_bcf_selector_transfer", "oracle_portfolio_complementarity_v0_1"],
        "what_repo_reproduced": "Scoped clean-envelope BCF comparisons and portfolio audit.",
        "what_repo_did_not_reproduce": "Measured hardware deployment.",
        "transfer_limit": "Repository BCF claims remain restricted to the audited clean common envelope.",
        "contract_mismatch": "Native substrate differs from MAP and requires dual-view accounting in portfolios.",
        "anti_nih_verdict": "ADOPT",
    },
    {
        "citation_key": "factorizers_sparse_block_codes",
        "title": "Factorizers for Distributed Sparse Block Codes",
        "authors": "Sparse block code factorization authors",
        "year": 2024,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2303.13957",
        "official_code": "",
        "method_category": "Structured recovery",
        "substrate": "SBC / GSBC",
        "task": "Structured sparse block code factorization",
        "main_claim": "Sparse block structure changes the recoverability frontier by adding code structure and native decoder assumptions.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific structured-code envelope",
        "reported_metrics": "factor recovery and capacity behavior",
        "closest_repo_hypotheses": ["level1f_bcf_selector_transfer", "level3_5a_noise_contract_audit"],
        "what_repo_reproduced": "Taxonomic comparison only.",
        "what_repo_did_not_reproduce": "No direct GSBC reproduction in this repository stage.",
        "transfer_limit": "Useful as structured-code prior art, not as a reproduced result.",
        "contract_mismatch": "Different substrate, different code structure, and no common harness here.",
        "anti_nih_verdict": "COMPARE",
    },
    {
        "citation_key": "satzilla2011",
        "title": "SATzilla: Portfolio-based Algorithm Selection for SAT",
        "authors": "Lars Kotthoff, Holger H. Hoos and collaborators",
        "year": 2011,
        "source": "Primary paper",
        "doi_or_arxiv": "https://www.cs.ubc.ca/labs/algorithms/Projects/SATzilla/",
        "official_code": "",
        "method_category": "Algorithm portfolio",
        "substrate": "Portfolio methodology",
        "task": "Per-instance algorithm selection",
        "main_claim": "Oracle analysis, static features, and cost-aware portfolio accounting are necessary before deploying a router.",
        "evidence_type": "paper",
        "reported_scale": "portfolio benchmark",
        "reported_metrics": "runtime, oracle gain, selection regret",
        "closest_repo_hypotheses": ["oracle_portfolio_complementarity_v0_1"],
        "what_repo_reproduced": "Paired oracle analysis, static-route baseline, and cost-aware cascade evaluation.",
        "what_repo_did_not_reproduce": "A learned per-instance router.",
        "transfer_limit": "The repository stops at oracle and static-route semantics.",
        "contract_mismatch": "SAT runtime selection is only an analogy, not the same substrate.",
        "anti_nih_verdict": "ADOPT_METHODOLOGY",
    },
    {
        "citation_key": "chow_reject_option",
        "title": "The reject option in statistical decision problems",
        "authors": "C. K. Chow lineage",
        "year": 1970,
        "source": "Primary theoretical paper",
        "doi_or_arxiv": "https://ieeexplore.ieee.org/document/1054147",
        "official_code": "",
        "method_category": "Reject option",
        "substrate": "Decision theory",
        "task": "Abstention under uncertainty",
        "main_claim": "Abstention is a lawful decision outcome when the available evidence is insufficient for safe commitment.",
        "evidence_type": "theory",
        "reported_scale": "decision-theoretic",
        "reported_metrics": "coverage and error trade-offs",
        "closest_repo_hypotheses": ["level1_context_conditioned_search", "level3_5b_confirmatory_protocol_discipline"],
        "what_repo_reproduced": "Typed abstention and reject-option framing.",
        "what_repo_did_not_reproduce": "A formal optimal abstention derivation for every repo task.",
        "transfer_limit": "Decision-theoretic background only.",
        "contract_mismatch": "Repository tasks are structured recovery rather than ordinary classification.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "mimhd_2021",
        "title": "MIMHD: Accurate and Efficient Hyperdimensional Inference Using Multi-Bit In-Memory Computing",
        "authors": "MIMHD authors",
        "year": 2021,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2106.12029",
        "official_code": "",
        "method_category": "Hardware / multi-bit precision",
        "substrate": "In-memory multi-bit HDC",
        "task": "Inference with multi-bit coordinates",
        "main_claim": "Coordinate precision and hardware locality can shift the cost frontier for HDC inference.",
        "evidence_type": "paper",
        "reported_scale": "hardware synthesis",
        "reported_metrics": "accuracy, energy, area, latency",
        "closest_repo_hypotheses": ["codebook_residue_block_lut"],
        "what_repo_reproduced": "Only literature-level framing for precision as a recoverability resource.",
        "what_repo_did_not_reproduce": "Measured multi-bit hardware.",
        "transfer_limit": "Hardware-only evidence in this repository stage.",
        "contract_mismatch": "No physical in-memory platform in repo.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "fefet_multibit_2022",
        "title": "Achieving Software-Equivalent Accuracy for Hyperdimensional Computing with Ferroelectric Multi-Bit Content-Addressable Memories",
        "authors": "FeFET multi-bit authors",
        "year": 2022,
        "source": "Primary paper",
        "doi_or_arxiv": "https://ieeexplore.ieee.org/document/9871234",
        "official_code": "",
        "method_category": "Hardware / multi-bit memories",
        "substrate": "FeFET multi-bit CAM",
        "task": "Associative retrieval with multi-bit cells",
        "main_claim": "Multi-bit physical memory can preserve soft evidence with practical hardware trade-offs.",
        "evidence_type": "paper",
        "reported_scale": "physical-hardware-oriented evaluation",
        "reported_metrics": "accuracy, latency, energy",
        "closest_repo_hypotheses": ["codebook_residue_block_lut"],
        "what_repo_reproduced": "None; literature synthesis only.",
        "what_repo_did_not_reproduce": "Measured physical memory advantages.",
        "transfer_limit": "Hardware synthesis / device evidence only.",
        "contract_mismatch": "No multi-bit CAM implementation in repo.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "fach_fpga_2019",
        "title": "FACH: FPGA-based Acceleration of Hyperdimensional Computing",
        "authors": "FACH authors",
        "year": 2019,
        "source": "Primary paper",
        "doi_or_arxiv": "https://dl.acm.org/doi/10.1145/3287624.3287667",
        "official_code": "",
        "method_category": "Hardware / FPGA",
        "substrate": "FPGA HDC",
        "task": "Accelerated HDC inference",
        "main_claim": "Physical parallelism and streaming can change the latency-area trade-off for HDC workloads.",
        "evidence_type": "paper",
        "reported_scale": "hardware synthesis",
        "reported_metrics": "latency, throughput, area",
        "closest_repo_hypotheses": ["oracle_portfolio_complementarity_v0_1"],
        "what_repo_reproduced": "None; only hardware frontier discussion.",
        "what_repo_did_not_reproduce": "Measured FPGA deployment.",
        "transfer_limit": "Hardware-only literature layer.",
        "contract_mismatch": "No FPGA synthesis or RTL in this repository stage.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "in_memory_hdc_review_2020",
        "title": "In-Memory Hyperdimensional Computing",
        "authors": "In-memory HDC review authors",
        "year": 2020,
        "source": "Primary review",
        "doi_or_arxiv": "https://doi.org/10.1038/s41928-020-0410-3",
        "official_code": "",
        "method_category": "Hardware review",
        "substrate": "In-memory HDC",
        "task": "Hardware implementation taxonomy",
        "main_claim": "Physical co-location, analog state, and memory hierarchy can change implementation cost without changing the underlying accounting principle.",
        "evidence_type": "review",
        "reported_scale": "hardware review",
        "reported_metrics": "energy, area, latency taxonomy",
        "closest_repo_hypotheses": ["codebook_residue_block_lut", "oracle_portfolio_complementarity_v0_1"],
        "what_repo_reproduced": "Hardware frontier framing only.",
        "what_repo_did_not_reproduce": "Direct hardware experiments.",
        "transfer_limit": "Literature synthesis only.",
        "contract_mismatch": "No hardware measurements in repo.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "concepts_semantic_pointers_2015",
        "title": "Concepts as Semantic Pointers: A Framework and Computational Model",
        "authors": "Chris Eliasmith",
        "year": 2015,
        "source": "Primary paper",
        "doi_or_arxiv": "https://doi.org/10.1111/cogs.12265",
        "official_code": "",
        "method_category": "Semantic Pointer Architecture",
        "substrate": "SPA",
        "task": "Structured cognitive representation",
        "main_claim": "Semantic pointers provide a neurally grounded structured representation framework with explicit binding, compression, and control assumptions.",
        "evidence_type": "paper",
        "reported_scale": "cognitive architecture framing",
        "reported_metrics": "conceptual and computational modeling evidence",
        "closest_repo_hypotheses": ["self_describing_record_sidecar_closure", "level1_context_conditioned_search"],
        "what_repo_reproduced": "Only the architectural distinction between semantic payload and exact structure.",
        "what_repo_did_not_reproduce": "A full SPA cognitive architecture.",
        "transfer_limit": "Used for architectural framing, not as a direct factorization baseline.",
        "contract_mismatch": "Repository tasks are narrower recoverability contracts rather than whole-cognition models.",
        "anti_nih_verdict": "ADOPT_BACKGROUND",
    },
    {
        "citation_key": "gosmann2016_spiking_spa",
        "title": "Optimizing Semantic Pointer Representations for Symbol-Like Processing in Spiking Neural Networks",
        "authors": "Jan Gosmann and Chris Eliasmith",
        "year": 2016,
        "source": "Primary paper",
        "doi_or_arxiv": "https://doi.org/10.1371/journal.pone.0149928",
        "official_code": "",
        "method_category": "Spiking semantic pointers",
        "substrate": "SPA / spiking neural implementation",
        "task": "Symbol-like processing in spiking semantic-pointer systems",
        "main_claim": "Spiking SPA implementations can trade representational optimization against accumulated transformation noise.",
        "evidence_type": "paper",
        "reported_scale": "spiking neural benchmark",
        "reported_metrics": "accuracy and noise accumulation in common SPA operations",
        "closest_repo_hypotheses": ["oracle_portfolio_complementarity_v0_1", "level3_5a_noise_contract_audit"],
        "what_repo_reproduced": "None directly; used to anchor the hardware/temporal-state literature layer.",
        "what_repo_did_not_reproduce": "Spiking or NEF-based implementation details.",
        "transfer_limit": "Literature-only for this repository stage.",
        "contract_mismatch": "Different substrate, temporal state, and cognitive-model scope.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "improved_cleanup_fhrr_2024",
        "title": "Improved Cleanup and Decoding of Fractional Power Encodings",
        "authors": "FHRR cleanup authors",
        "year": 2024,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2412.00488",
        "official_code": "",
        "method_category": "FHRR cleanup",
        "substrate": "FHRR / fractional power encoding",
        "task": "Cleanup and decoding of continuous-value FHRR vectors",
        "main_claim": "Cleanup quality in FHRR can be improved with iterative optimization tailored to phase-valued encodings.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific cleanup studies",
        "reported_metrics": "cleanup accuracy and convergence behavior",
        "closest_repo_hypotheses": ["level3_2_map_budget_robustness"],
        "what_repo_reproduced": "Not reproduced; used to widen family coverage beyond MAP and BCF.",
        "what_repo_did_not_reproduce": "FHRR-native cleanup in a common harness.",
        "transfer_limit": "Different algebra and cleanup contract.",
        "contract_mismatch": "Repository common-harness results are MAP/BCF-centric.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "renner2022_hrn_scene",
        "title": "Neuromorphic Visual Scene Understanding with Resonator Networks",
        "authors": "Arianna Renner et al.",
        "year": 2022,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2208.05373",
        "official_code": "",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "vsa_family": "Hierarchical resonator networks",
        "algebra": "Resonator network over partitioned VSA-like factors",
        "representation": "Partitioned semantic scene representation with resonator-driven factor recovery",
        "coordinate_precision": "spiking / temporal state",
        "sparsity": "NR",
        "binding_operation": "Task-specific factor composition with resonator feedback",
        "bundling_operation": "Task-specific composition",
        "similarity_operation": "Resonator consistency dynamics",
        "task_category": "Hierarchical structured recovery",
        "task_contract": "Neuromorphic visual scene understanding with multi-factor scene variables",
        "factor_count": "multiple scene variables",
        "candidate_domain": "scene-factor candidates",
        "dimension": "NR",
        "noise_contract": "sensor and event-stream variation, not repo common noise contract",
        "decoder": "Hierarchical resonator network",
        "iterations": "NR",
        "restarts": "NR",
        "stopping_rule": "Convergence / task-specific criterion",
        "side_information": "Scene-factor structure",
        "external_prior": "Task-specific hierarchy",
        "exact_metadata": "no",
        "reported_accuracy": "reported in primary paper",
        "reported_latency": "reported in primary paper",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "Loihi deployment context",
        "cost_location": {
            "dimension": "yes",
            "precision": "yes",
            "structured_code": "yes",
            "compute": "yes",
            "context": "yes",
            "side_information": "no",
            "hardware": "yes",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": [
            "task-specific scene hierarchy",
            "not a common-harness MAP to BCF cascade",
        ],
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "method_category": "Hierarchical resonator recovery",
        "substrate": "Spiking / resonator scene representation",
        "task": "Neuromorphic visual scene understanding",
        "main_claim": "Hierarchical resonator dynamics can solve structured scene-variable recovery when the hierarchy is built into the substrate and task.",
        "evidence_type": "paper",
        "reported_scale": "task-specific neuromorphic scene benchmark",
        "reported_metrics": "task accuracy and neuromorphic deployment metrics",
        "closest_repo_hypotheses": [
            "level3_2_map_budget_robustness",
            "oracle_portfolio_complementarity_v0_1",
        ],
        "transferable_claim": "Supports literature coverage for hierarchical resonator recovery and representation partitioning as resource-bearing structure.",
        "non_transferable_claim": "A direct justification for heterogeneous MAP to BCF escalation or for arbitrary recursive factorization.",
        "what_repo_reproduced": "No direct reproduction; used to close the hierarchical resonator literature gap and to separate hierarchy from cross-substrate fallback.",
        "what_repo_did_not_reproduce": "Task-specific scene architecture and neuromorphic deployment.",
        "transfer_limit": "The paper embeds hierarchy directly into the model and task contract.",
        "contract_mismatch": "Repository common-harness evidence studies clean F=3 factorization, not scene-level hierarchical recovery.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "renner2023_hrn_odometry",
        "title": "Visual Odometry with Neuromorphic Resonator Networks",
        "authors": "Arianna Renner et al.",
        "year": 2023,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2311.14348",
        "official_code": "",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "vsa_family": "Hierarchical resonator networks",
        "algebra": "Resonator network with staged structured state",
        "representation": "Neuromorphic odometry representation with resonator-mediated latent variables",
        "coordinate_precision": "spiking / temporal state",
        "sparsity": "NR",
        "binding_operation": "Task-specific composition",
        "bundling_operation": "Task-specific composition",
        "similarity_operation": "Resonator consistency dynamics",
        "task_category": "Hierarchical structured recovery",
        "task_contract": "Visual odometry with structured latent recovery",
        "factor_count": "multi-stage latent variables",
        "candidate_domain": "task-specific latent domains",
        "dimension": "NR",
        "noise_contract": "event and sensor variation",
        "decoder": "Neuromorphic resonator network",
        "iterations": "NR",
        "restarts": "NR",
        "stopping_rule": "Convergence / task-specific criterion",
        "side_information": "Task hierarchy and latent state factoring",
        "external_prior": "Odometry structure",
        "exact_metadata": "no",
        "reported_accuracy": "reported in primary paper",
        "reported_latency": "reported in primary paper",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "neuromorphic deployment context",
        "cost_location": {
            "dimension": "yes",
            "precision": "yes",
            "structured_code": "yes",
            "compute": "yes",
            "context": "yes",
            "side_information": "no",
            "hardware": "yes",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": [
            "task-specific latent dynamics",
            "no common-harness parity with repo factorization cells",
        ],
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "method_category": "Hierarchical resonator recovery",
        "substrate": "Neuromorphic resonator latent-state model",
        "task": "Visual odometry",
        "main_claim": "Neuromorphic resonator networks can be stacked over structured latent variables for a sequential visual task.",
        "evidence_type": "paper",
        "reported_scale": "task-specific odometry benchmark",
        "reported_metrics": "task performance and deployment metrics",
        "closest_repo_hypotheses": [
            "level3_2_map_budget_robustness",
            "oracle_portfolio_complementarity_v0_1",
        ],
        "transferable_claim": "Strengthens the literature case that hierarchical resonator designs buy recovery with explicit staged state and temporal budget.",
        "non_transferable_claim": "Any direct implication for a practical cross-substrate cascade in this repository.",
        "what_repo_reproduced": "No direct reproduction; used to bound what hierarchical resonator evidence can and cannot imply for the atlas.",
        "what_repo_did_not_reproduce": "Visual odometry task, temporal sensor stream, and deployment stack.",
        "transfer_limit": "Different task, hierarchy semantics, and temporal deployment assumptions.",
        "contract_mismatch": "Repository evidence does not include continuous odometry or event-stream workloads.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "orchard2023_spiking_phasors",
        "title": "Hyperdimensional Computing with Spiking-Phasor Neurons",
        "authors": "Garrick Orchard et al.",
        "year": 2023,
        "source": "Primary paper",
        "doi_or_arxiv": "https://arxiv.org/abs/2305.18809",
        "official_code": "",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "vsa_family": "Spiking VSA / temporal hypervectors",
        "algebra": "HDC with spiking-phasor neurons",
        "representation": "Temporal or phasor-like spiking hypervectors",
        "coordinate_precision": "temporal state",
        "sparsity": "NR",
        "binding_operation": "Task-specific phasor composition",
        "bundling_operation": "Task-specific phasor superposition",
        "similarity_operation": "Spike-phase or temporal similarity",
        "task_category": "Spiking VSA recovery",
        "task_contract": "Hypervector representation and inference with temporal spike state",
        "factor_count": "NR",
        "candidate_domain": "NR",
        "dimension": "NR",
        "noise_contract": "paper-specific",
        "decoder": "spiking phasor dynamics",
        "iterations": "NR",
        "restarts": "NR",
        "stopping_rule": "task-specific",
        "side_information": "NR",
        "external_prior": "NR",
        "exact_metadata": "NR",
        "reported_accuracy": "reported in primary paper",
        "reported_latency": "reported in primary paper",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "simulation / neuromorphic relevance",
        "cost_location": {
            "dimension": "yes",
            "precision": "yes",
            "structured_code": "no",
            "compute": "yes",
            "context": "no",
            "side_information": "no",
            "hardware": "yes",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": ["not a common-harness factorization benchmark"],
        "comparability_class": "HARDWARE_ONLY",
        "method_category": "Temporal or spiking hypervectors",
        "substrate": "Spiking-phasor HDC",
        "task": "Temporal hypervector inference",
        "main_claim": "Temporal spike phase can carry hypervector state and recoverability-relevant evidence that is not free in static binary views.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific spiking HDC experiments",
        "reported_metrics": "task accuracy and temporal implementation characteristics",
        "closest_repo_hypotheses": [
            "codebook_residue_block_lut",
            "oracle_portfolio_complementarity_v0_1",
        ],
        "transferable_claim": "Literature evidence that temporal local state can act as an additional recoverability resource distinct from static sign-only vectors.",
        "non_transferable_claim": "A measured advantage for repository tasks or for direct MAP or BCF substitution.",
        "what_repo_reproduced": "No direct reproduction; used only in the literature-only hardware and temporal-state section.",
        "what_repo_did_not_reproduce": "Spiking-phasor model and task-specific implementation.",
        "transfer_limit": "Different substrate and temporal dynamics.",
        "contract_mismatch": "Repository tasks mainly use static MAP and structured-code views.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "loihi2_2021",
        "title": "Loihi 2: A Neuromorphic Manycore Processor with On-Chip Learning",
        "authors": "Mike Davies et al.",
        "year": 2021,
        "source": "Primary paper",
        "doi_or_arxiv": "https://www.intel.com/content/www/us/en/research/neuromorphic-computing.html",
        "official_code": "",
        "evidence_strength": "HARDWARE_SYNTHESIS",
        "vsa_family": "Neuromorphic hardware platform",
        "algebra": "Platform-level",
        "representation": "Loihi 2 manycore neuromorphic state",
        "coordinate_precision": "event-driven temporal state",
        "sparsity": "hardware dependent",
        "binding_operation": "NR",
        "bundling_operation": "NR",
        "similarity_operation": "NR",
        "task_category": "Hardware platform",
        "task_contract": "Neuromorphic execution platform for temporal and event-driven models",
        "factor_count": "NA",
        "candidate_domain": "NA",
        "dimension": "NA",
        "noise_contract": "NA",
        "decoder": "NA",
        "iterations": "NA",
        "restarts": "NA",
        "stopping_rule": "NA",
        "side_information": "NA",
        "external_prior": "NA",
        "exact_metadata": "NA",
        "reported_accuracy": "NR",
        "reported_latency": "reported by platform literature",
        "reported_memory": "reported by platform literature",
        "reported_energy": "reported by platform literature",
        "reported_hardware": "Loihi 2",
        "cost_location": {
            "dimension": "yes",
            "precision": "yes",
            "structured_code": "no",
            "compute": "yes",
            "context": "no",
            "side_information": "no",
            "hardware": "yes",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": ["platform evidence, not a direct VSA recovery benchmark"],
        "comparability_class": "HARDWARE_ONLY",
        "method_category": "Hardware platform",
        "substrate": "Loihi 2",
        "task": "Neuromorphic execution platform",
        "main_claim": "Loihi 2 changes the practical cost envelope for event-driven state and parallel search.",
        "evidence_type": "hardware platform paper",
        "reported_scale": "platform-level hardware report",
        "reported_metrics": "device capabilities and deployment envelope",
        "closest_repo_hypotheses": ["oracle_portfolio_complementarity_v0_1"],
        "transferable_claim": "Used only to ground the hardware section's statements about temporal state and event-driven execution resources.",
        "non_transferable_claim": "Any measured recoverability result for this repository.",
        "what_repo_reproduced": "Nothing directly; literature-only hardware framing.",
        "what_repo_did_not_reproduce": "Hardware deployment.",
        "transfer_limit": "Platform evidence only.",
        "contract_mismatch": "Repository has no physical hardware measurements.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "lava_docs_2026",
        "title": "Lava documentation and official tutorials",
        "authors": "Lava maintainers",
        "year": 2026,
        "source": "Official documentation",
        "doi_or_arxiv": "https://lava-nc.org/",
        "official_code": "https://github.com/lava-nc/lava",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "vsa_family": "Neuromorphic runtime",
        "algebra": "Runtime / implementation layer",
        "representation": "Lava process-model abstractions for Loihi-class deployment",
        "coordinate_precision": "event-driven temporal state",
        "sparsity": "runtime dependent",
        "binding_operation": "NA",
        "bundling_operation": "NA",
        "similarity_operation": "NA",
        "task_category": "Official implementation",
        "task_contract": "Neuromorphic model construction and deployment runtime",
        "factor_count": "NA",
        "candidate_domain": "NA",
        "dimension": "NA",
        "noise_contract": "NA",
        "decoder": "NA",
        "iterations": "NA",
        "restarts": "NA",
        "stopping_rule": "NA",
        "side_information": "NA",
        "external_prior": "NA",
        "exact_metadata": "NA",
        "reported_accuracy": "NR",
        "reported_latency": "NR",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "Loihi-compatible runtime",
        "cost_location": {
            "dimension": "no",
            "precision": "yes",
            "structured_code": "no",
            "compute": "yes",
            "context": "no",
            "side_information": "no",
            "hardware": "yes",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": [
            "documentation and official runtime, not a direct empirical common-harness result",
        ],
        "comparability_class": "HARDWARE_ONLY",
        "method_category": "Official implementation",
        "substrate": "Lava / Loihi runtime",
        "task": "Neuromorphic runtime and deployment support",
        "main_claim": "Lava is the official software/runtime layer rather than an empirical recovery result in this repository.",
        "evidence_type": "official docs and code",
        "reported_scale": "official runtime stack",
        "reported_metrics": "implementation scope and deployment targets",
        "closest_repo_hypotheses": ["oracle_portfolio_complementarity_v0_1"],
        "transferable_claim": "Official implementation status exists for neuromorphic execution stacks discussed in the manuscript.",
        "non_transferable_claim": "Any direct recovery advantage on repository tasks.",
        "what_repo_reproduced": "No implementation; documentation only.",
        "what_repo_did_not_reproduce": "Lava-based runtime or neuromorphic execution.",
        "transfer_limit": "Implementation status only.",
        "contract_mismatch": "This stage forbids hardware implementation.",
        "anti_nih_verdict": "LITERATURE_ONLY",
    },
    {
        "citation_key": "roodsari2025_nuecc_hdc",
        "title": "Non-Uniform Error Correction for Hyperdimensional Computing",
        "authors": "Mohammad Roodsari et al.",
        "year": 2025,
        "source": "Primary paper",
        "doi_or_arxiv": "https://doi.org/10.1016/j.ins.2025.123618",
        "official_code": "",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "vsa_family": "ECC-guided HDC",
        "algebra": "HDC with non-uniform error correction",
        "representation": "Error-corrected hyperdimensional representations",
        "coordinate_precision": "multi-level correction logic",
        "sparsity": "NR",
        "binding_operation": "task dependent",
        "bundling_operation": "task dependent",
        "similarity_operation": "task dependent",
        "task_category": "Channel-style correction and classification robustness",
        "task_contract": "Error correction under HDC classification or retrieval conditions",
        "factor_count": "NR",
        "candidate_domain": "NR",
        "dimension": "NR",
        "noise_contract": "paper-specific channel or corruption model",
        "decoder": "ECC or correction logic",
        "iterations": "NR",
        "restarts": "NR",
        "stopping_rule": "task-specific",
        "side_information": "structured code and correction metadata",
        "external_prior": "NR",
        "exact_metadata": "NR",
        "reported_accuracy": "reported in primary paper",
        "reported_latency": "NR",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "NR",
        "cost_location": {
            "dimension": "yes",
            "precision": "yes",
            "structured_code": "yes",
            "compute": "yes",
            "context": "no",
            "side_information": "yes",
            "hardware": "no",
            "abstention": "no",
        },
        "failure_modes": [],
        "limitations": ["channel or classifier correction is not arbitrary factorization"],
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "method_category": "ECC-guided HDC",
        "substrate": "Error-corrected HDC",
        "task": "Channel-style correction and robustness",
        "main_claim": "Non-uniform error correction can improve HDC robustness when the correction contract is explicit.",
        "evidence_type": "paper",
        "reported_scale": "paper-specific robustness study",
        "reported_metrics": "accuracy and robustness under the paper's corruption contract",
        "closest_repo_hypotheses": [
            "level3_3_linear_code_reproduction",
            "codebook_residue_block_lut",
        ],
        "transferable_claim": "Structured coding can improve robustness when the task contract includes correction metadata and code structure.",
        "non_transferable_claim": "Direct support for blind VSA factorization or for arbitrary recursive recovery.",
        "what_repo_reproduced": "No direct reproduction; used to separate channel correction from factorization and residue coding claims.",
        "what_repo_did_not_reproduce": "The paper's correction pipeline and task-specific evaluation.",
        "transfer_limit": "Correction-style evidence is not equivalent to arbitrary factor recovery.",
        "contract_mismatch": "Repository negative repair lines test different contracts and different ground-truth authority.",
        "anti_nih_verdict": "COMPARE",
    },
]

PRIOR_ART_OVERRIDES = {
    "plate1995hrr": {
        "comparability_class": "THEORETICAL_ONLY",
        "evidence_strength": "PRIMARY_THEORETICAL",
        "algebra": "HRR",
        "representation": "Real-valued distributed vectors",
        "binding_operation": "Circular convolution",
        "bundling_operation": "Superposition",
        "similarity_operation": "Dot/cosine style similarity",
        "cost_location": {"dimension": "yes", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
    },
    "kanerva2009hyperdimensional": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "PRIMARY_THEORETICAL",
        "algebra": "Mixed HDC overview",
        "representation": "High-dimensional random vectors",
        "binding_operation": "Family-dependent",
        "bundling_operation": "Superposition / majority",
        "similarity_operation": "Family-dependent",
    },
    "kanerva1988sdm": {
        "comparability_class": "THEORETICAL_ONLY",
        "evidence_strength": "PRIMARY_THEORETICAL",
        "vsa_family": "Sparse Distributed Memory",
        "representation": "Addressed sparse memory locations",
        "cost_location": {"dimension": "yes", "precision": "no", "structured_code": "yes", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "frady2020resonator": {
        "comparability_class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "algebra": "MAP / resonator networks",
        "binding_operation": "MAP binding",
        "bundling_operation": "MAP bundling",
        "similarity_operation": "Dot-product cleanup",
        "task_category": "Blind factorization",
        "factor_count": "F=2/F=3 style factorizations",
        "cost_location": {"dimension": "yes", "precision": "no", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
        "failure_modes": ["capacity_collapse", "false_attractor"],
        "limitations": ["Task-specific codebooks", "bounded by compute and dimension"],
    },
    "torchhd": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "vsa_family": "TorchHD",
        "representation": "Multi-family VSA library",
    },
    "holovec": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "vsa_family": "Attention-style cleanup",
        "decoder": "Attention cleanup",
        "limitations": ["Shared flat codebook mismatched factor-specific-domain contract"],
    },
    "ibm_bcf_repo": {
        "comparability_class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "algebra": "BCF",
        "representation": "Structured block code",
        "binding_operation": "Native structured composition",
        "bundling_operation": "Native substrate-specific aggregation",
        "similarity_operation": "Native factorizer evidence",
        "task_category": "Structured factorization",
        "factor_count": "F=3 common-envelope audit",
        "cost_location": {"dimension": "yes", "precision": "no", "structured_code": "yes", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "neco_linear_codes": {
        "comparability_class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "algebra": "Linear code / GF(2)",
        "representation": "Structured coded hypervectors",
        "binding_operation": "GF(2) linear composition",
        "bundling_operation": "Task-specific",
        "similarity_operation": "Exact symbolic/code checks",
        "cost_location": {"dimension": "yes", "precision": "no", "structured_code": "yes", "compute": "moderate", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
    },
    "faiss": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "representation": "Exact and ANN dense/binary indexes",
        "task_category": "Similarity search",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "yes", "hardware": "optional", "abstention": "no"},
    },
    "jegou2011pq": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "representation": "Product quantized compressed vectors",
        "task_category": "Compressed search",
        "cost_location": {"dimension": "no", "precision": "yes", "structured_code": "yes", "compute": "yes", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
    },
    "gray1998quantization": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "SURVEY_ONLY",
        "representation": "Scalar and vector quantization background",
        "cost_location": {"dimension": "no", "precision": "yes", "structured_code": "yes", "compute": "yes", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
    },
    "merkle_dag_git": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "OFFICIAL_IMPLEMENTATION",
        "representation": "Immutable exact content-addressed DAG",
        "task_category": "Exact structural preservation",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "yes", "compute": "yes", "context": "no", "side_information": "yes", "hardware": "no", "abstention": "no"},
    },
    "kleyko2022survey_part1": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "SURVEY_ONLY",
        "representation": "Cross-family VSA taxonomy",
    },
    "kleyko2023survey_part2": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "SURVEY_ONLY",
        "representation": "Applications and challenges taxonomy",
    },
    "vsa_comparison_2022": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "representation": "Multiple VSA algebras",
    },
    "ibm_bcf_paper": {
        "comparability_class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "evidence_strength": "HARDWARE_SYNTHESIS",
        "algebra": "BCF",
        "representation": "Structured block code + hardware mapping",
        "reported_hardware": "Yes",
    },
    "factorizers_sparse_block_codes": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "algebra": "Sparse block code factorization",
        "representation": "SBC / GSBC",
        "structured_code": "yes",
    },
    "satzilla2011": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "representation": "Algorithm portfolio methodology",
        "task_category": "Per-instance selection",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "no", "compute": "yes", "context": "yes", "side_information": "no", "hardware": "no", "abstention": "yes"},
    },
    "selective_classification_survey": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "SURVEY_ONLY",
        "representation": "Reject-option / selective prediction",
        "task_category": "Coverage-risk control",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "no", "compute": "moderate", "context": "no", "side_information": "no", "hardware": "no", "abstention": "yes"},
    },
    "chow_reject_option": {
        "comparability_class": "THEORETICAL_ONLY",
        "evidence_strength": "PRIMARY_THEORETICAL",
        "representation": "Decision-theoretic reject option",
        "task_category": "Abstention theory",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "no", "compute": "no", "context": "no", "side_information": "no", "hardware": "no", "abstention": "yes"},
    },
    "mimhd_2021": {
        "comparability_class": "HARDWARE_ONLY",
        "evidence_strength": "HARDWARE_SYNTHESIS",
        "representation": "Multi-bit in-memory HDC",
        "reported_hardware": "In-memory compute",
        "cost_location": {"dimension": "no", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "fefet_multibit_2022": {
        "comparability_class": "HARDWARE_ONLY",
        "evidence_strength": "PHYSICAL_HARDWARE_MEASUREMENT",
        "representation": "FeFET multi-bit CAM",
        "reported_hardware": "Physical memory measurements",
        "cost_location": {"dimension": "no", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "fach_fpga_2019": {
        "comparability_class": "HARDWARE_ONLY",
        "evidence_strength": "HARDWARE_SYNTHESIS",
        "representation": "FPGA HDC accelerator",
        "reported_hardware": "FPGA synthesis",
        "cost_location": {"dimension": "no", "precision": "no", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "in_memory_hdc_review_2020": {
        "comparability_class": "HARDWARE_ONLY",
        "evidence_strength": "SURVEY_ONLY",
        "representation": "In-memory HDC review",
        "reported_hardware": "Review / taxonomy",
        "cost_location": {"dimension": "no", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "concepts_semantic_pointers_2015": {
        "comparability_class": "TAXONOMIC_ONLY",
        "evidence_strength": "PRIMARY_THEORETICAL",
        "algebra": "Semantic Pointer Architecture",
        "representation": "Semantic pointers",
        "binding_operation": "Convolution-style structured binding",
        "bundling_operation": "Superposition",
        "similarity_operation": "Dot/cosine style similarity",
    },
    "gosmann2016_spiking_spa": {
        "comparability_class": "HARDWARE_ONLY",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "algebra": "SPA / spiking neural implementation",
        "representation": "Spiking semantic pointers",
        "reported_hardware": "Spiking neural implementation",
        "cost_location": {"dimension": "yes", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "yes", "abstention": "no"},
    },
    "improved_cleanup_fhrr_2024": {
        "comparability_class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "evidence_strength": "PRIMARY_EMPIRICAL",
        "algebra": "FHRR",
        "representation": "Phase-valued FHRR vectors",
        "binding_operation": "Circular convolution / phase composition",
        "bundling_operation": "Complex superposition",
        "similarity_operation": "Phase/cosine cleanup",
        "cost_location": {"dimension": "yes", "precision": "yes", "structured_code": "no", "compute": "yes", "context": "no", "side_information": "no", "hardware": "no", "abstention": "no"},
    },
}

METHOD_RESOURCE_ROWS = [
    {
        "Method": "MAP resonator D512 fast",
        "Evidence source": "Repository",
        "Task contract": "Clean F=3 single-product with factor-specific domains",
        "Representation": "MAP bipolar HVs",
        "Recovery target": "Exact tuple",
        "Added resource": "R1_DIMENSION; R7_DECODER_COMPUTE",
        "Persistent cost": "Moderate codebook bytes",
        "Transient cost": "Iterative state",
        "Compute cost": "Low relative to other tested repo factorizers",
        "Latency": "Low in common clean envelope",
        "Energy": "NR",
        "Preprocessing": "None beyond codebook materialization",
        "Exact recovery": "Bounded and capacity-limited",
        "Silent error": "0 under verifier acceptance",
        "Coverage": "Low on non-easy common F=3 cells",
        "Noise tolerance": "NC in this mapping stage",
        "Scaling limitation": "Capacity collapse and false attractors",
        "Main benefit": "Cheap fast path in easy cells",
        "Main failure": "Hard-cell misses",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Fast baseline / easy-cell route",
    },
    {
        "Method": "MAP resonator D1024 robust",
        "Evidence source": "Repository",
        "Task contract": "Clean F=3 single-product with factor-specific domains",
        "Representation": "MAP bipolar HVs",
        "Recovery target": "Exact tuple",
        "Added resource": "R1_DIMENSION; R7_DECODER_COMPUTE; R8_RESTARTS_OR_SEARCH",
        "Persistent cost": "Higher codebook bytes than D512",
        "Transient cost": "Longer iterative state",
        "Compute cost": "High within MAP family",
        "Latency": "Higher than BCF on non-easy cells",
        "Energy": "NR",
        "Preprocessing": "None beyond codebook materialization",
        "Exact recovery": "Improved over fast MAP but still below BCF in common clean envelope",
        "Silent error": "0 under verifier acceptance",
        "Coverage": "Intermediate",
        "Noise tolerance": "NC in this mapping stage",
        "Scaling limitation": "Compute non-dominance on hard cells",
        "Main benefit": "Best native MAP recovery in clean F=3 audits",
        "Main failure": "Still does not rescue BCF failures",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "High-compute MAP baseline",
    },
    {
        "Method": "BCF native",
        "Evidence source": "Repository + official upstream",
        "Task contract": "Clean F=3 single-product common semantic tuple contract",
        "Representation": "Native BCF / structured block code",
        "Recovery target": "Exact tuple",
        "Added resource": "R4_STRUCTURED_CODE; R11_PREPROCESSING_OR_MATERIALIZATION; R12_DUAL_REPRESENTATION",
        "Persistent cost": "Separate native BCF view",
        "Transient cost": "Moderate temporary state",
        "Compute cost": "Higher than MAP fast, lower than MAP robust on hard common cells",
        "Latency": "Best hard-cell deployed baseline in common clean envelope",
        "Energy": "NR in repo; reported in literature only",
        "Preprocessing": "Native view construction required",
        "Exact recovery": "1.0 in tested common clean F=3 envelope",
        "Silent error": "0 under verifier acceptance",
        "Coverage": "1.0 in common clean envelope",
        "Noise tolerance": "NC in this mapping stage",
        "Scaling limitation": "Different native contract and materialization cost",
        "Main benefit": "Dominant hard-cell recovery in current common contract",
        "Main failure": "No direct evidence yet for shared raw-noise contracts",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Current hard-cell baseline",
    },
    {
        "Method": "Context-conditioned MAP search",
        "Evidence source": "Repository",
        "Task contract": "Single-product factorization with external context subsets",
        "Representation": "MAP + external routing prior",
        "Recovery target": "Candidate routing and exact tuple",
        "Added resource": "R6_EXTERNAL_CONTEXT_OR_PRIOR; R13_REDUCED_COVERAGE_ABSTENTION; R14_EXACT_FALLBACK",
        "Persistent cost": "Minimal controller metadata",
        "Transient cost": "Subset selection and fallback bookkeeping",
        "Compute cost": "Reduced average compute when context is helpful",
        "Latency": "Lower than broad search in bounded envelopes",
        "Energy": "NR",
        "Preprocessing": "Context construction",
        "Exact recovery": "Improved over random subsets in tested Level 1 settings",
        "Silent error": "Controlled via selective acceptance",
        "Coverage": "Depends on fallback policy",
        "Noise tolerance": "Limited; no universal noisy frontier claim",
        "Scaling limitation": "Context exclusion and misrouting",
        "Main benefit": "Search narrowing without new algebra",
        "Main failure": "Needs safe expansion path",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Adopted search controller seam",
    },
    {
        "Method": "Exact binary scan at N=10k",
        "Evidence source": "Repository + Faiss baseline audit",
        "Task contract": "Semantic-to-trace retrieval after record creation",
        "Representation": "Packed binary exact search over MAP signs",
        "Recovery target": "Exact trace neighborhood after lookup",
        "Added resource": "R5_EXACT_SIDE_INFORMATION; R11_PREPROCESSING_OR_MATERIALIZATION",
        "Persistent cost": "Packed index plus canonical payload store",
        "Transient cost": "Exact scan buffer",
        "Compute cost": "Exact but vectorized",
        "Latency": "Best practical baseline at tested N=10,000",
        "Energy": "NR",
        "Preprocessing": "Packing and index creation",
        "Exact recovery": "Best measured practical trace retrieval baseline in Stage A.2a",
        "Silent error": "0 under verifier acceptance",
        "Coverage": "High in tested development envelope",
        "Noise tolerance": "Moderate under tested semantic locality contract",
        "Scaling limitation": "May lose at larger untested scale",
        "Main benefit": "Simplicity and exactness",
        "Main failure": "Does not solve initial localization theory beyond tested scale",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Adopted exact retrieval baseline",
    },
    {
        "Method": "Ordinary sidecar DAG + recursive replay",
        "Evidence source": "Repository",
        "Task contract": "Known retrieved record ID with exact first-order manifest",
        "Representation": "Semantic payload plus exact sidecar manifest",
        "Recovery target": "Exact replay after retrieval",
        "Added resource": "R5_EXACT_SIDE_INFORMATION; R11_PREPROCESSING_OR_MATERIALIZATION; R14_EXACT_FALLBACK",
        "Persistent cost": "Manifest bytes and canonical parent store",
        "Transient cost": "Recursive replay session cache",
        "Compute cost": "Linear in reachable unique DAG nodes",
        "Latency": "Replay cost dominates after retrieval",
        "Energy": "NR",
        "Preprocessing": "Manifest commit and digesting",
        "Exact recovery": "1.0 with intact manifests and parents",
        "Silent error": "0 under integrity checks",
        "Coverage": "Full for intact retrieved records",
        "Noise tolerance": "Observed semantic noise irrelevant once exact structure is loaded",
        "Scaling limitation": "Does not solve initial record localization",
        "Main benefit": "Honest exact structural preservation",
        "Main failure": "Packaging advantage for inline form not supported",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Adopted exact-structure baseline",
    },
    {
        "Method": "Equal-bit extra dimensions",
        "Evidence source": "Repository",
        "Task contract": "Bundling cleanup and membership recovery under equal physical storage",
        "Representation": "More MAP sign dimensions",
        "Recovery target": "Cleanup and membership",
        "Added resource": "R1_DIMENSION",
        "Persistent cost": "More semantic bits",
        "Transient cost": "Small",
        "Compute cost": "Similar decoder form",
        "Latency": "Low",
        "Energy": "NR",
        "Preprocessing": "None",
        "Exact recovery": "Best surviving equal-bit control in residue lines",
        "Silent error": "Controlled by existing verifier contract",
        "Coverage": "Higher than block-LUT residue in tested cells",
        "Noise tolerance": "Limited to tested bundle tasks",
        "Scaling limitation": "Still pays through larger representation",
        "Main benefit": "Simple surviving frontier point",
        "Main failure": "No compression story",
        "Comparability class": "DIRECT_COMMON_HARNESS",
        "Architectural role": "Adopted baseline against compressed residue ideas",
    },
    {
        "Method": "NeCo linear-code clean-U1 reproduction",
        "Evidence source": "Repository + paper reproduction",
        "Task contract": "Clean U1 paper contract with explicit GF(2) constraints",
        "Representation": "Linear-code structured representation",
        "Recovery target": "Exact clean-U1 recovery",
        "Added resource": "R4_STRUCTURED_CODE",
        "Persistent cost": "Structured code constraints",
        "Transient cost": "Small in reproduced contract",
        "Compute cost": "Low-to-moderate",
        "Latency": "NR",
        "Energy": "NR",
        "Preprocessing": "Code construction",
        "Exact recovery": "Paper contract reproduced",
        "Silent error": "0 in clean reproduced envelope",
        "Coverage": "Full in scoped clean contract",
        "Noise tolerance": "Not established",
        "Scaling limitation": "Transfer outside paper contract not established",
        "Main benefit": "Shows structured code can preserve information honestly",
        "Main failure": "Not a universal replacement for blind MAP factorization",
        "Comparability class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "Architectural role": "Structured-code comparative point",
    },
    {
        "Method": "Resonator networks (paper)",
        "Evidence source": "Literature + TorchHD adoption",
        "Task contract": "Factorization of distributed representations",
        "Representation": "MAP/related distributed vectors",
        "Recovery target": "Factor recovery",
        "Added resource": "R7_DECODER_COMPUTE; R8_RESTARTS_OR_SEARCH",
        "Persistent cost": "Codebooks",
        "Transient cost": "Iterative resonator state",
        "Compute cost": "Iterative",
        "Latency": "Reported; not directly comparable outside common harness",
        "Energy": "NR",
        "Preprocessing": "Codebook creation",
        "Exact recovery": "Reported positive in paper envelope",
        "Silent error": "NR",
        "Coverage": "NR",
        "Noise tolerance": "Reported per paper contract",
        "Scaling limitation": "Dependent on task contract and codebook size",
        "Main benefit": "Canonical blind factorization baseline",
        "Main failure": "Can exhibit false attractors and bounded capacity",
        "Comparability class": "CLOSE_TASK_DIFFERENT_IMPLEMENTATION",
        "Architectural role": "Foundational decoder prior art",
    },
    {
        "Method": "SDM",
        "Evidence source": "Literature only",
        "Task contract": "Noisy associative retrieval",
        "Representation": "Sparse distributed memory",
        "Recovery target": "Addressed retrieval",
        "Added resource": "R3_SPARSITY_OR_BLOCK_STRUCTURE; R10_PHYSICAL_PARALLELISM",
        "Persistent cost": "Address locations and memory matrix",
        "Transient cost": "Address activation",
        "Compute cost": "Address match plus readout",
        "Latency": "NR",
        "Energy": "NR",
        "Preprocessing": "Memory allocation",
        "Exact recovery": "NR for this repository's factorization tasks",
        "Silent error": "NR",
        "Coverage": "NR",
        "Noise tolerance": "Core literature motivation",
        "Scaling limitation": "Not reproduced in repo and not directly comparable",
        "Main benefit": "Associative noisy access prior art",
        "Main failure": "No direct repo evidence under common factorization contract",
        "Comparability class": "THEORETICAL_ONLY",
        "Architectural role": "Deferred baseline family",
    },
    {
        "Method": "Product quantization / vector quantization",
        "Evidence source": "Literature only",
        "Task contract": "Compressed similarity search",
        "Representation": "Codebook-compressed blocks",
        "Recovery target": "Nearest-neighbor retrieval",
        "Added resource": "R2_COORDINATE_PRECISION; R11_PREPROCESSING_OR_MATERIALIZATION",
        "Persistent cost": "Shared codebook plus compressed codes",
        "Transient cost": "Decoder-side LUT lookup",
        "Compute cost": "Low per query",
        "Latency": "Reported for search tasks",
        "Energy": "NR",
        "Preprocessing": "Codebook discovery/training",
        "Exact recovery": "NA",
        "Silent error": "NR",
        "Coverage": "NR",
        "Noise tolerance": "Task-dependent",
        "Scaling limitation": "Not the same task as bundle cleanup or factorization",
        "Main benefit": "Explains compression prior art behind block-LUT residue ideas",
        "Main failure": "Does not imply a win on VSA recovery tasks",
        "Comparability class": "SAME_MECHANISM_DIFFERENT_CONTRACT",
        "Architectural role": "Quantization contrast class",
    },
    {
        "Method": "MIMHD / multi-bit in-memory HDC",
        "Evidence source": "Literature only",
        "Task contract": "HDC inference with multi-bit coordinates",
        "Representation": "Multi-bit analog / in-memory state",
        "Recovery target": "Inference and retrieval",
        "Added resource": "R2_COORDINATE_PRECISION; R10_PHYSICAL_PARALLELISM",
        "Persistent cost": "Specialized memory cells",
        "Transient cost": "Device-specific",
        "Compute cost": "Shifted into physical substrate",
        "Latency": "Reported in paper only",
        "Energy": "Reported in paper only",
        "Preprocessing": "Hardware co-design",
        "Exact recovery": "NC",
        "Silent error": "NR",
        "Coverage": "NR",
        "Noise tolerance": "Task-specific",
        "Scaling limitation": "No repo hardware measurement",
        "Main benefit": "Shows hardware can change the frontier, not the accounting principle",
        "Main failure": "Literature-only in this repository",
        "Comparability class": "HARDWARE_ONLY",
        "Architectural role": "Hardware frontier context",
    },
]

ARCHITECTURAL_DECISION_ROWS = [
    {
        "Scenario": "Known exact structure",
        "Recommended representation": "Semantic payload + exact first-order sidecar manifest",
        "Recommended recovery path": "Recursive replay with memoization",
        "Required verifier": "Digest / record-integrity check",
        "Fallback": "Typed failure and abstention",
        "Main cost": "R5 exact side information; replay latency",
        "Main risk": "Wrong-but-valid or stale handles",
        "Evidence status": "ADOPTED_ENGINEERING_BASELINE",
    },
    {
        "Scenario": "Approximate semantic lookup",
        "Recommended representation": "MAP semantic payload + mature exact packed baseline",
        "Recommended recovery path": "Exact binary scan or adopted mature index before any structure readout",
        "Required verifier": "Exact trace / record association check",
        "Fallback": "Broader exact scan or abstain",
        "Main cost": "R11 preprocessing and index bytes",
        "Main risk": "Similarity != exact provenance",
        "Evidence status": "SUPPORTED_DEVELOPMENT_ONLY",
    },
    {
        "Scenario": "Clean single-product factorization",
        "Recommended representation": "Use the dominant native substrate for the current lawful contract",
        "Recommended recovery path": "BCF native in the tested common clean F=3 envelope; MAP only as easy-cell fast path",
        "Required verifier": "Tuple reconstruction verifier",
        "Fallback": "Exact abstain or selected stronger native method",
        "Main cost": "R4 structured code or R7 decoder compute",
        "Main risk": "Contract overclaim outside clean F=3",
        "Evidence status": "SUPPORTED_DEVELOPMENT_ONLY",
    },
    {
        "Scenario": "Unknown composite after retrieval",
        "Recommended representation": "Ordinary sidecar DAG",
        "Recommended recovery path": "Exact replay, not blind factorization",
        "Required verifier": "Manifest and semantic digest validation",
        "Fallback": "Typed failure",
        "Main cost": "R5 exact side information",
        "Main risk": "Does not solve initial localization",
        "Evidence status": "ADOPTED_ENGINEERING_BASELINE",
    },
    {
        "Scenario": "Noisy symbolic channel",
        "Recommended representation": "Typed corruption contract + explicit abstention",
        "Recommended recovery path": "Substrate-specific evaluation only; do not merge raw p across substrates",
        "Required verifier": "Typed protocol gates and held-out discipline",
        "Fallback": "Do not claim unmatched noise frontier",
        "Main cost": "Protocol and evaluation overhead",
        "Main risk": "Protocol leakage",
        "Evidence status": "CONFIRMED_IN_FROZEN_ENVELOPE",
    },
    {
        "Scenario": "Deep recursive structure",
        "Recommended representation": "Exact sidecar DAG with memoized replay",
        "Recommended recovery path": "Traverse unique reachable nodes only",
        "Required verifier": "Cycle / stale-parent detection",
        "Fallback": "Replay budget exhaustion",
        "Main cost": "Replay latency and cache state",
        "Main risk": "Deep latency if uncached",
        "Evidence status": "SUPPORTED_DEVELOPMENT_ONLY",
    },
    {
        "Scenario": "Memory-constrained workspace",
        "Recommended representation": "Prefer exact baselines or equal-bit controls before custom compressed side channels",
        "Recommended recovery path": "Compare against extra dimensions and scalar quantization first",
        "Required verifier": "Physical byte accounting",
        "Fallback": "Adopt simpler baseline if frontier is dominated",
        "Main cost": "R1 versus R2 trade-off",
        "Main risk": "Storage non-dominance",
        "Evidence status": "SUPPORTED_DEVELOPMENT_ONLY",
    },
    {
        "Scenario": "Latency-critical workspace",
        "Recommended representation": "Use trivial static route only if it captures the measured benefit",
        "Recommended recovery path": "Easy-cell MAP fast path, otherwise BCF or exact baseline",
        "Required verifier": "Zero silent-wrong acceptance",
        "Fallback": "Always use dominant single method",
        "Main cost": "Probe latency and dual-view storage",
        "Main risk": "Non-cost-effective early exit",
        "Evidence status": "SUPPORTED_DEVELOPMENT_ONLY",
    },
    {
        "Scenario": "Safety-critical decision",
        "Recommended representation": "Verifier-first with abstention and exact fallback",
        "Recommended recovery path": "Accepted output only after typed verification",
        "Required verifier": "Mandatory",
        "Fallback": "ABSTAIN / exact fallback",
        "Main cost": "Reduced coverage",
        "Main risk": "Silent wrong acceptance",
        "Evidence status": "DESIGN_PRINCIPLE",
    },
    {
        "Scenario": "Hardware-limited deployment",
        "Recommended representation": "Consult literature-only hardware frontier separately",
        "Recommended recovery path": "Do not infer hardware gains from repo CPU experiments",
        "Required verifier": "Comparability-class discipline",
        "Fallback": "Stay with software baseline",
        "Main cost": "R10 physical parallelism; hardware co-design",
        "Main risk": "Speculative transfer",
        "Evidence status": "LITERATURE_ONLY",
    },
]

REVIEWER_RISK_ROWS = [
    {
        "Likely criticism": "The scope is too broad for one paper.",
        "Why it is plausible": "The repository contains many hypotheses, baselines, and negative lines.",
        "Current defense": "The paper is framed as a systematic mapping plus evidence atlas, not a single benchmark leaderboard.",
        "Missing evidence": "A tighter visual summary of inclusion boundaries may still help.",
        "Required wording": "Use 'mapping' and 'atlas' language consistently.",
        "Claim to weaken": "Any language implying complete field coverage.",
    },
    {
        "Likely criticism": "The review is not systematic enough.",
        "Why it is plausible": "Repository-driven reviews often drift into narrative selection.",
        "Current defense": "Frozen review protocol, search log, screening CSV, and typed comparability classes are added.",
        "Missing evidence": "Could still add PRISMA-style counts later.",
        "Required wording": "Describe this as a scoping/systematic mapping review, not a meta-analysis.",
        "Claim to weaken": "Any claim of exhaustive literature coverage.",
    },
    {
        "Likely criticism": "Methods are not directly comparable.",
        "Why it is plausible": "Different algebras, task contracts, and hardware assumptions are mixed in the field.",
        "Current defense": "Comparability classes and common-harness restrictions prevent unlawful numeric ranking.",
        "Missing evidence": "More explicit table footnotes may still help.",
        "Required wording": "Only DIRECT_COMMON_HARNESS rows are directly ranked.",
        "Claim to weaken": "Any cross-paper global frontier claim.",
    },
    {
        "Likely criticism": "Too many results are development-only.",
        "Why it is plausible": "Many repository lines stopped at audited development evidence.",
        "Current defense": "Claim ledger restricts scope and marks development-only claims explicitly.",
        "Missing evidence": "More held-out confirmations would be needed for stronger empirical claims.",
        "Required wording": "Use 'within the evaluated envelopes' and 'development-only' frequently.",
        "Claim to weaken": "Any universal positive or negative conclusion.",
    },
    {
        "Likely criticism": "BCF contract favors BCF.",
        "Why it is plausible": "BCF is a native structured-code substrate with its own strengths.",
        "Current defense": "The paper explicitly limits the conclusion to the clean common F=3 envelope and dual-view accounting.",
        "Missing evidence": "Shared raw-noise contracts remain unmeasured.",
        "Required wording": "Do not generalize beyond the tested clean common contract.",
        "Claim to weaken": "BCF is the best substrate overall.",
    },
    {
        "Likely criticism": "Negative results lack generality.",
        "Why it is plausible": "Blocked lines may have only one or two envelopes.",
        "Current defense": "The manuscript reframes them as bounded stop conditions, not impossibility theorems.",
        "Missing evidence": "Broader reproduction across workloads would be needed for stronger closure.",
        "Required wording": "Use 'not supported in the tested envelope' rather than 'disproved'.",
        "Claim to weaken": "Strong global negatives.",
    },
    {
        "Likely criticism": "The hardware section is speculative.",
        "Why it is plausible": "No physical hardware is measured in this repository.",
        "Current defense": "The section is explicitly labeled literature synthesis only.",
        "Missing evidence": "Actual FPGA or in-memory measurements.",
        "Required wording": "Hardware changes the frontier, not the accounting; not evaluated here.",
        "Claim to weaken": "Any measured hardware implication.",
    },
    {
        "Likely criticism": "The repository is too large and heterogeneous.",
        "Why it is plausible": "Historical research accreted over multiple stages.",
        "Current defense": "Evidence registry, hypothesis matrix, and failure atlas normalize the heterogeneity.",
        "Missing evidence": "Optional pruning or archival packaging may still help for readers.",
        "Required wording": "Describe the repository as an atlas, not a single polished system.",
        "Claim to weaken": "Any implication that every directory is equally central.",
    },
    {
        "Likely criticism": "Single-author bias affects method selection and interpretation.",
        "Why it is plausible": "The repository reflects one research program.",
        "Current defense": "Anti-NIH audits, adopted baselines, and explicit blocked verdicts are preserved rather than rewritten away.",
        "Missing evidence": "Independent reproductions by others.",
        "Required wording": "Acknowledge researcher degrees of freedom in threats to validity.",
        "Claim to weaken": "Any overly triumphant architectural interpretation.",
    },
    {
        "Likely criticism": "Utility weights in the portfolio section are arbitrary.",
        "Why it is plausible": "Any scalar utility profile imposes scenario assumptions.",
        "Current defense": "The manuscript now makes Pareto analysis primary and utility profiles illustrative only.",
        "Missing evidence": "Domain-specific deployment workloads.",
        "Required wording": "Utility profiles are scenario assumptions, not universal scores.",
        "Claim to weaken": "Any one-number method ranking.",
    },
    {
        "Likely criticism": "There is no end-to-end workload.",
        "Why it is plausible": "Most repo tasks are synthetic but controlled contracts.",
        "Current defense": "The paper positions the work as recoverability accounting under explicit contracts, not application-level benchmarking.",
        "Missing evidence": "A domain workload with external validity.",
        "Required wording": "Synthetic tasks are deliberate stress contracts for recoverability.",
        "Claim to weaken": "Direct application superiority.",
    },
]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json_yaml(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(md_escape(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def patched_entries(
    entries: list[dict[str, object]],
    key: str,
    overrides: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    patched: list[dict[str, object]] = []
    for entry in entries:
        merged = dict(entry)
        entry_key = str(entry[key])
        if entry_key in overrides:
            merged.update(overrides[entry_key])
        patched.append(merged)
    return patched


def normalize_prior_art_entry(entry: dict[str, object]) -> dict[str, object]:
    normalized = {
        "venue": str(entry.get("source", "NR")),
        "source_url_or_doi": str(entry.get("doi_or_arxiv", "NR")),
        "evidence_strength": "CONCEPTUAL_ONLY",
        "vsa_family": str(entry.get("substrate", "NR")),
        "algebra": "NR",
        "representation": str(entry.get("substrate", "NR")),
        "coordinate_precision": "NR",
        "sparsity": "NR",
        "binding_operation": "NR",
        "bundling_operation": "NR",
        "similarity_operation": "NR",
        "task_category": str(entry.get("method_category", "NR")),
        "task_contract": str(entry.get("task", "NR")),
        "factor_count": "NR",
        "candidate_domain": "NR",
        "dimension": "NR",
        "noise_contract": "NR",
        "decoder": "NR",
        "iterations": "NR",
        "restarts": "NR",
        "stopping_rule": "NR",
        "side_information": "NR",
        "external_prior": "NR",
        "exact_metadata": "NR",
        "reported_accuracy": "NR",
        "reported_latency": "NR",
        "reported_memory": "NR",
        "reported_energy": "NR",
        "reported_hardware": "NR",
        "cost_location": {
            "dimension": "NR",
            "precision": "NR",
            "structured_code": "NR",
            "compute": "NR",
            "context": "NR",
            "side_information": "NR",
            "hardware": "NR",
            "abstention": "NR",
        },
        "failure_modes": [],
        "limitations": [],
        "comparability_class": "TAXONOMIC_ONLY",
        "closest_repo_evidence": ", ".join(entry.get("closest_repo_hypotheses", [])),
        "transferable_claim": entry.get("what_repo_reproduced", "NR"),
        "non_transferable_claim": entry.get("what_repo_did_not_reproduce", "NR"),
    }
    merged = dict(normalized)
    merged.update(entry)
    return merged


def normalize_failure_mode(entry: dict[str, object]) -> dict[str, object]:
    normalized = {
        "observed_in_repo": True,
        "reported_in_literature": [],
        "mechanistic_explanation": str(entry["description"]),
        "resource_shortfall": [],
        "detection_signal": str(entry["observable_signature"]),
        "mitigation": str(entry["what_helped"]),
        "remaining_risk": str(entry["safety_consequence"]),
    }
    merged = dict(normalized)
    merged.update(entry)
    return merged


ALL_EVIDENCE_ENTRIES = patched_entries(EVIDENCE_ENTRIES, "hypothesis_id", EVIDENCE_ENTRY_OVERRIDES)
ALL_CLAIMS = CLAIMS + EXTRA_CLAIMS
ALL_FAILURE_MODES = [
    normalize_failure_mode(entry)
    for entry in patched_entries(FAILURE_MODES, "failure_mode", FAILURE_MODE_OVERRIDES)
]
ALL_PRIOR_ART = [
    normalize_prior_art_entry(entry)
    for entry in patched_entries(PRIOR_ART + PRIOR_ART_EXTRA_ENTRIES, "citation_key", PRIOR_ART_OVERRIDES)
]


def build_hypothesis_matrix() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entry in ALL_EVIDENCE_ENTRIES:
        rows.append(
            {
                "Hypothesis": entry["title"],
                "Category": entry["category"],
                "Origin": entry["origin"],
                "Substrate": entry["substrate"],
                "Information added": entry["information_added"],
                "Compute added": entry["compute_added"],
                "Prior added": entry["prior_added"],
                "Exact side information": entry["exact_side_information"],
                "Task": entry["operation_contract"],
                "Repo evidence": entry["evidence_status"],
                "Scale": entry["evidence"]["execution_scale"],
                "Primary result": entry["primary_result"],
                "Failure point": entry["primary_failure_point"],
                "Safety outcome": entry["safety_outcome"],
                "Cost outcome": entry["cost_outcome"],
                "Verdict": entry["architectural_disposition"],
                "Architectural role": entry["architectural_disposition"],
                "Prior art": "; ".join(entry["prior_art"]),
                "Reopen condition": entry["reopen_conditions"][0],
            }
        )
    return rows


def build_prior_art_matrix() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entry in ALL_PRIOR_ART:
        rows.append(
            {
                "Citation": entry["citation_key"],
                "Title": entry["title"],
                "Year": entry["year"],
                "Venue": entry["venue"],
                "Category": entry["method_category"],
                "Strength": entry["evidence_strength"],
                "Substrate": entry["substrate"],
                "Task": entry["task"],
                "Comparability": entry["comparability_class"],
                "Repo transfer": entry["what_repo_reproduced"],
                "Transfer limit": entry["what_repo_did_not_reproduce"],
                "Anti-NIH verdict": entry["anti_nih_verdict"],
            }
        )
    return rows


def render_claim_ledger_md() -> str:
    lines = [
        "# Claim Ledger",
        "",
        "This file is generated from `paper/claim_ledger.yaml`. Status values are intentionally conservative.",
        "",
    ]
    for claim in ALL_CLAIMS:
        lines.extend(
            [
                f"## {claim['claim_id']}",
                "",
                f"- Status: `{claim['status']}`",
                f"- Scope: {claim['scope']}",
                f"- Text: {claim['text']}",
                f"- Supporting evidence: {', '.join(claim['supporting_evidence']) or 'None'}",
                f"- Contradicting evidence: {', '.join(claim['contradicting_evidence']) or 'None'}",
                f"- Allowed locations: {', '.join(claim['allowed_locations'])}",
                f"- Forbidden strengthenings: {', '.join(claim['forbidden_strengthenings'])}",
                "",
            ]
        )
    return "\n".join(lines)


def render_failure_atlas_md() -> str:
    lines = [
        "# Failure-Mode Atlas",
        "",
        "This atlas normalizes the main failure signatures observed across the repository.",
        "",
    ]
    for item in ALL_FAILURE_MODES:
        lines.extend(
            [
                f"## {item['failure_mode']}",
                "",
                f"- Description: {item['description']}",
                f"- Observable signature: {item['observable_signature']}",
                f"- Affected methods: {item['affected_methods']}",
                f"- How detected: {item['how_detected']}",
                f"- What helped: {item['what_helped']}",
                f"- What failed: {item['what_failed']}",
                f"- Safety consequence: {item['safety_consequence']}",
                f"- Architectural response: {item['architectural_response']}",
                f"- Observed in repo: {item['observed_in_repo']}",
                f"- Reported in literature: {', '.join(item['reported_in_literature']) or 'None explicitly mapped'}",
                f"- Mechanistic explanation: {item['mechanistic_explanation']}",
                f"- Resource shortfall: {', '.join(item['resource_shortfall']) or 'Not localized'}",
                f"- Detection signal: {item['detection_signal']}",
                f"- Mitigation: {item['mitigation']}",
                f"- Remaining risk: {item['remaining_risk']}",
                f"- Evidence refs: {item['evidence_refs']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_literature_transfer_md() -> str:
    columns = [
        "Prior work",
        "Original demonstrated task",
        "Original substrate",
        "Original scale",
        "Our closest experiment",
        "What transferred",
        "What failed to transfer",
        "Reason",
        "Final interpretation",
    ]
    rows: list[dict[str, object]] = []
    for entry in ALL_PRIOR_ART:
        rows.append(
            {
                "Prior work": entry["title"],
                "Original demonstrated task": entry["task"],
                "Original substrate": entry["substrate"],
                "Original scale": entry["reported_scale"],
                "Our closest experiment": entry["closest_repo_evidence"],
                "What transferred": entry["transferable_claim"],
                "What failed to transfer": entry["non_transferable_claim"],
                "Reason": entry["contract_mismatch"],
                "Final interpretation": entry["anti_nih_verdict"],
            }
        )
    return "# Literature Transfer Matrix\n\n" + render_table(rows, columns)


def render_method_resource_atlas_md() -> str:
    columns = list(METHOD_RESOURCE_ROWS[0].keys())
    return "# Method Resource Atlas\n\n" + render_table(METHOD_RESOURCE_ROWS, columns)


def render_architectural_decision_guide_md() -> str:
    columns = list(ARCHITECTURAL_DECISION_ROWS[0].keys())
    return "# Architectural Decision Guide\n\n" + render_table(ARCHITECTURAL_DECISION_ROWS, columns)


def render_reviewer_risk_register_md() -> str:
    columns = list(REVIEWER_RISK_ROWS[0].keys())
    return "# Reviewer Risk Register\n\n" + render_table(REVIEWER_RISK_ROWS, columns)


def render_manuscript() -> str:
    return dedent(
        """\
        # Recoverability Has a Cost:

        ## An Empirical Atlas and Resource-Aware Design Framework for Vector Symbolic Architectures

        ## Abstract

        This manuscript presents a bounded empirical atlas and a systematic mapping of recoverability mechanisms in Vector Symbolic Architectures (VSAs) and Hyperdimensional Computing (HDC). The central result is not a universal impossibility theorem and not a universal BCF claim. Instead, within the evaluated repository envelopes and the mapped literature, recoverability improvements consistently required an identifiable additional resource: more dimensions, more coordinate precision, more code structure, exact side information, stronger contextual priors, more inference compute, hardware state, reduced coverage through abstention, or an exact fallback. Several mechanisms preserved genuine information or improved local recovery, but many failed to create a new nondominated operating point after accounting for representation cost, compute, verification, generalization, and silent-error risk. We therefore propose a resource-aware interpretation of recoverability rather than a single-method leaderboard. [claim:claim_recoverability_resource_accounting] [claim:claim_hardware_may_change_cost_frontier_literature_only]

        ## 1. Introduction

        The repository historically called `CGRN-HSR` has become a heterogeneous empirical record of recoverability hypotheses, reproductions, negative results, and architectural stop conditions. It is more accurate to frame it as **VSA Recoverability Atlas** than as one monolithic theory. The paper answers a narrower and more honest question than "which decoder is best?":

        > Which resources pay for recoverability, which failure modes recur, and when does extra architectural complexity create or fail to create a new nondominated operating point?

        The contribution is therefore a systematic mapping/scoping review plus a reproducible in-repository evidence atlas, not a numerical meta-analysis and not a new decoder.

        ## 2. Scope and Contributions

        The paper contributes:

        - a systematic mapping protocol with typed inclusion, exclusion, and comparability classes;
        - a repository-wide evidence registry linking hypotheses, protocols, commits, tests, and bounded claims;
        - a recoverability budget framework for locating the resource cost of each mechanism;
        - a failure-mode atlas spanning both repository evidence and mapped literature;
        - an architectural decision guide describing when to adopt exact side information, abstention, stronger native substrates, or stop a line entirely.

        The paper does **not** claim:

        - a universal impossibility theorem for VSA factorization or recoverability;
        - a universal superiority result for BCF, MAP, or any other substrate;
        - a production architecture;
        - a measured hardware result.

        ## 3. Systematic Mapping Protocol

        We treat the literature component as a **systematic mapping / scoping review**. The relevant papers span incompatible algebras, tasks, dimensions, noise contracts, hardware targets, and cost-reporting conventions, so a pooled meta-analysis would be misleading. The frozen protocol (`paper/SYSTEMATIC_REVIEW_PROTOCOL.md`) records:

        - research questions RQ1-RQ7;
        - search-source families;
        - query families for VSA/HDC foundations, recovery, structured codes, precision, hardware, and abstention/portfolio work;
        - typed inclusion/exclusion criteria;
        - duplicate policy;
        - primary-source policy;
        - data-extraction schema and comparability classes.

        Only `DIRECT_COMMON_HARNESS` entries are used for direct numeric ranking. All other literature is descriptive, contrastive, or hardware-contextual only.

        ## 4. VSA Recovery Contracts and Terminology

        The atlas distinguishes:

        - semantic payload versus exact structural metadata;
        - approximate routing signal versus authoritative identity;
        - development evidence versus held-out confirmation;
        - lawful abstention versus silent wrong acceptance;
        - common-harness direct comparison versus taxonomic or hardware-only comparison.

        It also keeps task contracts explicit. For example, clean F=3 single-product factorization, semantic-to-trace retrieval after record creation, and exact recursive replay after record retrieval are different problems and remain distinct throughout the paper.

        ## 5. Recoverability Budget Framework

        The paper's constructive synthesis is a non-novel but operationally useful accounting rule:

        > If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always identify the original source. Reliable recovery therefore requires paying cost somewhere else.

        We map that cost into the following resource ontology:

        - `R1_DIMENSION`
        - `R2_COORDINATE_PRECISION`
        - `R3_SPARSITY_OR_BLOCK_STRUCTURE`
        - `R4_STRUCTURED_CODE`
        - `R5_EXACT_SIDE_INFORMATION`
        - `R6_EXTERNAL_CONTEXT_OR_PRIOR`
        - `R7_DECODER_COMPUTE`
        - `R8_RESTARTS_OR_SEARCH`
        - `R9_TEMPORAL_BUDGET`
        - `R10_PHYSICAL_PARALLELISM`
        - `R11_PREPROCESSING_OR_MATERIALIZATION`
        - `R12_DUAL_REPRESENTATION`
        - `R13_REDUCED_COVERAGE_ABSTENTION`
        - `R14_EXACT_FALLBACK`

        The workflow recommended by the atlas is:

        `define task and risk contract -> select authoritative exact state -> choose approximate representation -> allocate dimension/precision -> select native decoder -> specify verification -> measure silent error -> add fallback only if nondominated -> abstain if budget is insufficient`

        [claim:claim_recoverability_resource_accounting]

        ## 6. Repository Evidence Base

        The repository evidence base now includes:

        - MAP / resonator baselines and budget sweeps;
        - context-conditioned search and selective fallback;
        - official IBM BCF audits and common-envelope comparisons;
        - a clean-U1 linear-code reproduction;
        - exact symbolic and exact-structure baselines;
        - blocked lines for decoder-certified admission, tagged repair, and block-codebook residue compression;
        - protocol-discipline artifacts for noise and held-out execution.

        The atlas therefore values negative results and architectural stop conditions as evidence, not as clutter.

        ## 7. Capacity and Dimensional Allocation

        The MAP line remained a bounded baseline rather than a universal decoder. In the tested clean envelopes, MAP resonator behavior exhibited a practical intermediate region rather than unlimited factorization capacity. More dimension and more restart budget could improve recovery in some regimes, but not for free. Capacity collapse and false attractors remained recurrent failure modes once codebooks or bundle widths crossed the practical margin budget. [claim:claim_map_intermediate_region]

        ## 8. Structured Recovery and Native Substrates

        The repository reproduced or audited several structured alternatives:

        - the official IBM BCF implementation as a lawful native competitor under a scoped common contract;
        - the NeCo linear-code clean-U1 paper contract under explicit GF(2) rules;
        - exact symbolic baselines on clean U1.

        The strongest current common-envelope result is narrow:

        > In the evaluated clean F=3 common envelope, the robust native BCF arm covered the same non-easy instances that defeated all tested MAP arms. [claim:claim_bcf_dominates_clean_non_easy_f3]

        This is not a universal BCF claim. It is restricted to:

        - clean only;
        - F=3 only;
        - single product;
        - known factor-specific domains;
        - dual native views;
        - no shared raw-noise contract.

        ## 9. Decoder Repair and Soft Information

        Several lines explored whether weak or compressed side evidence could create a better frontier:

        - decoder-certified codebook admission;
        - conflict-guided tagged-symbol repair;
        - block-codebook residue compression.

        These lines did not support a strong architectural upgrade once equal-bit controls, generalization, certification shuffles, and silent-error safeguards were counted. The repeated pattern was not that no local signal existed, but that the extra mechanism failed to create a new nondominated operating point after full accounting. [claim:claim_decoder_repair_not_free_in_tested_envelopes]

        ## 10. Exact Structural Preservation

        The exact-structure lines support a different conclusion from noisy factorization:

        - exact first-order manifests can safely enumerate immediate operands after record retrieval;
        - recursive replay can reconstruct the clean semantic result with memoization and typed failure handling;
        - ordinary sidecar DAG storage is the honest engineering baseline;
        - inline packing alone did not show a packaging advantage.

        This is not "semantic geometry contains its own exact history." It is exact structural preservation plus deterministic replay after retrieval. [claim:claim_recursive_replay_safe_after_retrieval] [claim:claim_inline_manifest_advantage_not_supported]

        ## 11. Verification, Abstention, and Sequential Escalation

        Verification and abstention recur across otherwise unrelated lines. The repository repeatedly found that the main safety failure is silent wrong acceptance, not mere inaccuracy. This leads to two portfolio conclusions that must remain separate.

        ### 11.1 Method-selection complementarity

        The question here is whether different methods solve different trials in a way that justifies per-instance selection. In the clean common F=3 envelope, BCF rescued MAP failures, but MAP did not rescue BCF failures on the hard shared cells. Direct oracle exact-recovery gain over always-BCF was therefore zero. The lawful conclusion is:

        > `INSTANCE_LEVEL_METHOD_SELECTION_NOT_SUPPORTED` in the tested clean F=3 envelope. [claim:claim_instance_router_not_supported_in_common_clean_envelope]

        ### 11.2 Sequential escalation economics

        A different question is whether a cheap fast path can still be worthwhile if an expensive fallback is invoked only after verifier rejection. For a fast path `A` and fallback `B`, the simplified expected cost is:

        `E[C_cascade] = C_A + (1 - p_exit) * C_B`

        with break-even condition:

        `p_exit > C_A / C_B`

        In the measured clean non-easy common F=3 cells:

        - `C_A` for `MAP_D1024_FAST` was about `0.00972 s`;
        - `C_B` for `BCF_NATIVE` was about `0.03717 s`;
        - break-even exit rate was therefore about `0.261`;
        - actual verified exit rate was `0.25`.

        So current MAP-first to BCF dual-view escalation was not cost-effective on clean non-easy cells. The only practical benefit came from a trivial cell-level threshold that sends the easy `M=10` cell to MAP and everything else to BCF. [claim:claim_current_map_bcf_escalation_not_cost_effective] [claim:claim_static_cell_route_sufficient_in_current_envelope]

        This does **not** use reverse rescue as an argument against sequential early exit. Reverse rescue is irrelevant to early exit. The negative result is economic: the verified exit rate did not amortize the probe in the tested envelope.

        ## 12. Failure-Mode Atlas

        The failure-mode atlas is central, not decorative. The recurrent modes include:

        - capacity collapse;
        - false attractors;
        - false consensus;
        - context exclusion and context misrouting;
        - certification overfit;
        - silent wrong acceptance;
        - native substrate mismatch;
        - compute non-dominance;
        - storage non-dominance;
        - packaging non-benefit;
        - wrong-but-valid exact handles;
        - dangling or stale handles;
        - protocol leakage;
        - dominant single-method portfolios.

        Each mode is linked to:

        - an observable signature;
        - a mechanistic explanation;
        - a resource shortfall;
        - what helped;
        - what failed;
        - the remaining risk.

        ## 13. Hardware Changes the Frontier, Not the Accounting

        This section is **literature synthesis only, not repository evidence**. **All hardware results discussed in this section are literature-only and were not measured in this repository.**

        Hardware work suggests that the practical cost frontier may shift when recoverability is paid through:

        - procedural hypervector generation;
        - streaming high-dimensional computation;
        - FPGA area/latency trade-offs;
        - in-memory compute;
        - analog or multi-bit coordinates;
        - spiking or temporal local state.

        The atlas therefore does not say hardware is irrelevant. It says hardware may change the frontier while leaving the accounting principle intact: the cost is still paid somewhere, just often in physical parallelism, device precision, or memory architecture instead of software-visible bytes or latency. [claim:claim_hardware_may_change_cost_frontier_literature_only]

        ## 14. Resource-Aware Architectural Guide

        The architectural guide consolidates the current engineering advice:

        - use exact first-order manifests when exact structure is already known at write time;
        - use ordinary sidecar DAG storage unless inline placement shows a measured packaging win;
        - treat context-conditioned search as a search controller seam, not a new algebra;
        - use the dominant native substrate for the current lawful common contract;
        - stop complex routing when a dominant single method or trivial static threshold already explains the gain;
        - keep exact fallbacks and typed abstention when the information contract is insufficient.

        ## 15. Threats to Validity

        The main threats are:

        ### Internal validity

        - many positive lines remain development-only;
        - some early historical runs predate today's stricter public-release framing.

        ### Construct validity

        - task contracts vary substantially across repository stages;
        - some lines test retrieval after record creation or retrieval after exact lookup rather than blind factorization.

        ### External validity

        - the cross-substrate portfolio result is clean-only and F=3 only;
        - no physical hardware measurements are present;
        - synthetic recoverability tasks are not application workloads.

        ### Statistical conclusion validity

        - several stages use modest trial counts and bounded development envelopes;
        - not every negative result has a large confirmatory sample.

        ### Implementation fidelity

        - some literature methods were audited or wrapped rather than reimplemented from scratch, by design;
        - direct numeric comparison is limited to common-harness entries.

        ### Publication and search bias

        - this is a repository-anchored systematic mapping, not an exhaustive field-wide census.

        ### Researcher degrees of freedom

        - the same single-author program designed most repository stages, even though blocked verdicts and anti-NIH baselines were preserved.

        ### Hardware transfer validity

        - hardware literature may shift practical costs, but not every device-level result transfers to software or CPU experiments.

        ## 16. Reproducibility

        The paper distinguishes:

        - CI validation and smoke tests;
        - local unit and validator runs;
        - full historical scientific reruns.

        All empirical claims are tied back to:

        - `paper/evidence_registry.yaml`;
        - `paper/claim_ledger.yaml`;
        - protocol hashes;
        - concrete result directories;
        - tests where locally available.

        ## 17. Conclusion

        The repeated negative result of the atlas was not that recovery could never be improved. It was that the improvement ceased to be free once all relevant resources were counted. Within the evaluated envelopes, some mechanisms preserved real information, some improved bounded local recovery, and several were worth adopting as engineering baselines. Others failed because the same benefit could be achieved more honestly with exact structure, a stronger native substrate, extra dimensions, abstention, or a simpler static policy. That is the paper's main message. [claim:claim_recoverability_has_a_cost] [claim:claim_no_universal_impossibility_theorem]
        """
    )


def render_supplementary_atlas() -> str:
    lines = [
        "# Supplementary Evidence Atlas",
        "",
        "This atlas is generated from the machine-readable registries and summarizes all normalized hypotheses.",
        "",
        "The main manuscript intentionally keeps only compact tables, figures, and bounded claims in the main text. This supplement retains the full evidence-oriented material:",
        "",
        "- all normalized repository hypotheses;",
        "- all current evidence statuses and architectural dispositions;",
        "- full protocol-hash and result-path references where available;",
        "- the full prior-art matrix and transfer limits;",
        "- the full claim ledger and reopen conditions.",
        "",
        "Use this document together with:",
        "",
        "- [CLAIM_TRACEABILITY.md](CLAIM_TRACEABILITY.md)",
        "- [CITATION_AUDIT.md](CITATION_AUDIT.md)",
        "- [LITERATURE_SCREENING_AUDIT.md](LITERATURE_SCREENING_AUDIT.md)",
        "",
    ]
    for entry in ALL_EVIDENCE_ENTRIES:
        lines.extend(
            [
                f"## {entry['hypothesis_id']}",
                "",
                f"- Title: {entry['title']}",
                f"- Category: `{entry['category']}`",
                f"- Evidence status: `{entry['evidence_status']}`",
                f"- Architectural disposition: `{entry['architectural_disposition']}`",
                f"- Research question: {entry['research_question']}",
                f"- Method: {entry['method']}",
                f"- Result paths: {', '.join(entry['evidence']['result_paths'])}",
                f"- Protocol hashes: {', '.join(entry['evidence']['protocol_hashes']) or 'None recorded'}",
                f"- Key result: {entry['primary_result']}",
                f"- Main failure point: {entry['primary_failure_point']}",
                f"- Allowed claims: {', '.join(entry['allowed_claims'])}",
                f"- Forbidden claims: {', '.join(entry['forbidden_claims'])}",
                f"- Reopen conditions: {', '.join(entry['reopen_conditions'])}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)

    evidence_payload = {
        "schema_version": "vsa-recoverability-atlas-evidence-v1",
        "project_title": "VSA Recoverability Atlas",
        "legacy_internal_namespace": "cgrn_hsr",
        "entries": ALL_EVIDENCE_ENTRIES,
    }
    claim_payload = {
        "schema_version": "vsa-recoverability-atlas-claims-v1",
        "claims": ALL_CLAIMS,
    }
    failure_payload = {
        "schema_version": "vsa-recoverability-atlas-failures-v1",
        "failures": ALL_FAILURE_MODES,
    }
    prior_payload = {
        "schema_version": "vsa-recoverability-atlas-prior-art-v1",
        "entries": ALL_PRIOR_ART,
    }

    write_json_yaml(PAPER_DIR / "evidence_registry.yaml", evidence_payload)
    write_json_yaml(PAPER_DIR / "claim_ledger.yaml", claim_payload)
    write_json_yaml(PAPER_DIR / "failure_mode_atlas.yaml", failure_payload)
    write_json_yaml(PAPER_DIR / "prior_art_registry.yaml", prior_payload)

    hypothesis_rows = build_hypothesis_matrix()
    prior_rows = build_prior_art_matrix()
    method_resource_rows = METHOD_RESOURCE_ROWS

    hypothesis_columns = list(hypothesis_rows[0].keys())
    prior_columns = list(prior_rows[0].keys())
    cost_columns = list(COST_MATRIX_ROWS[0].keys())
    method_resource_columns = list(method_resource_rows[0].keys())

    write_text(PAPER_DIR / "hypothesis_matrix.csv", csv_from_rows(hypothesis_rows, hypothesis_columns))
    write_text(PAPER_DIR / "hypothesis_matrix.md", "# Hypothesis Matrix\n\n" + render_table(hypothesis_rows, hypothesis_columns))

    write_text(PAPER_DIR / "recoverability_cost_matrix.csv", csv_from_rows(COST_MATRIX_ROWS, cost_columns))
    write_text(PAPER_DIR / "recoverability_cost_matrix.md", "# Recoverability Cost Matrix\n\n" + render_table(COST_MATRIX_ROWS, cost_columns))

    write_text(PAPER_DIR / "prior_art_matrix.csv", csv_from_rows(prior_rows, prior_columns))
    write_text(PAPER_DIR / "prior_art_matrix.md", "# Prior-Art Matrix\n\n" + render_table(prior_rows, prior_columns))
    write_text(PAPER_DIR / "method_resource_atlas.csv", csv_from_rows(method_resource_rows, method_resource_columns))
    write_text(PAPER_DIR / "method_resource_atlas.md", render_method_resource_atlas_md())

    write_text(PAPER_DIR / "claim_ledger.md", render_claim_ledger_md())
    write_text(PAPER_DIR / "failure_mode_atlas.md", render_failure_atlas_md())
    write_text(PAPER_DIR / "literature_transfer_matrix.md", render_literature_transfer_md())
    write_text(PAPER_DIR / "architectural_decision_guide.md", render_architectural_decision_guide_md())
    write_text(PAPER_DIR / "REVIEWER_RISK_REGISTER.md", render_reviewer_risk_register_md())
    write_text(PAPER_DIR / "supplementary_evidence_atlas.md", render_supplementary_atlas())


def csv_from_rows(rows: list[dict[str, object]], columns: list[str]) -> str:
    escaped_header = ",".join(csv_escape(column) for column in columns)
    lines = [escaped_header]
    for row in rows:
        lines.append(",".join(csv_escape(row.get(column, "")) for column in columns))
    return "\n".join(lines)


def csv_escape(value: object) -> str:
    text = str(value)
    if any(token in text for token in [",", '"', "\n"]):
        text = '"' + text.replace('"', '""') + '"'
    return text


if __name__ == "__main__":
    main()
