from __future__ import annotations

import json
from pathlib import Path


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


def build_hypothesis_matrix() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entry in EVIDENCE_ENTRIES:
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
    for entry in PRIOR_ART:
        rows.append(
            {
                "Citation": entry["citation_key"],
                "Title": entry["title"],
                "Year": entry["year"],
                "Category": entry["method_category"],
                "Substrate": entry["substrate"],
                "Task": entry["task"],
                "Repo transfer": entry["what_repo_reproduced"],
                "Transfer limit": entry["transfer_limit"],
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
    for claim in CLAIMS:
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
    for item in FAILURE_MODES:
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
    for entry in PRIOR_ART:
        rows.append(
            {
                "Prior work": entry["title"],
                "Original demonstrated task": entry["task"],
                "Original substrate": entry["substrate"],
                "Original scale": entry["reported_scale"],
                "Our closest experiment": ", ".join(entry["closest_repo_hypotheses"]),
                "What transferred": entry["what_repo_reproduced"],
                "What failed to transfer": entry["what_repo_did_not_reproduce"],
                "Reason": entry["contract_mismatch"],
                "Final interpretation": entry["anti_nih_verdict"],
            }
        )
    return "# Literature Transfer Matrix\n\n" + render_table(rows, columns)


def render_manuscript() -> str:
    return """# Recoverability Has a Cost:

## An Empirical Atlas of Factorization, Repair, and Abstention in Vector Symbolic Architectures

## Abstract

This manuscript scaffold summarizes a repository-wide empirical atlas rather than a single winning hypothesis. The central synthesis is practical rather than theorem-level: reliable recoverability was never free in the measured repository envelopes. Gains came from paying cost somewhere else: more exact structure, more bits, more dimensions, more compute, stronger routing priors, narrower task contracts, selective abstention, or exact fallback. The atlas therefore records both bounded successes and stop conditions. It does not claim a universal impossibility theorem for VSA factorization, universal superiority of any single substrate, or production readiness of the experimental lines. Instead it turns a historically single-hypothesis repository into a reproducible record of what transferred, what failed, what remained ambiguous, and what engineering baselines survived.

## 1. Introduction

The repository historically called `CGRN-HSR` began as a hypothesis about context-guided recovery in Vector Symbolic Architectures. It is no longer scientifically honest to present it as one monolithic idea. The evidence now spans:

- MAP / resonator baselines and capacity limits
- context-conditioned search and fallback
- substrate audits and paper reproductions
- cross-substrate portfolio and cascade stop conditions
- noise-contract repair and confirmatory protocol discipline
- exact-structure alternatives
- soft-information and codebook experiments
- negative results and blocked lines

The public framing adopted here is therefore **VSA Recoverability Atlas**.

## 2. Recoverability Accounting Principle

The repository adopts a non-novel but operationally useful proposition:

> If multiple distinguishable source structures map to the same stored representation under the available observation and prior, then no decoder receiving only that representation can always recover the original source. Reliable recovery therefore requires paying cost somewhere else: additional stored information, stronger structural assumptions, external evidence, more search or computation, reduced coverage through abstention, or an exact fallback.

The atlas uses this proposition descriptively. It is not presented as a new theorem.

## 3. Background and Terminology

The atlas distinguishes:

- semantic payloads versus exact structural metadata
- approximate retrieval signals versus exact identity
- development evidence versus held-out confirmation
- lawful abstention versus silent wrong acceptance
- adopted baselines versus still-open research hypotheses

## 4. Research Questions

The normalized research questions across the repository are:

1. How far can blind MAP/resonator factorization be pushed before recoverability cost dominates?
2. When does context-conditioned search help more than it harms?
3. Which alternative substrates or code structures survive equal-information comparison?
4. When is exact side information simply the honest solution?
5. Which negative results genuinely close a line rather than merely fail to tune it?
6. What protocol discipline is necessary before any confirmatory noise claim becomes lawful?

## 5. Reproducibility and Protocol Discipline

The repository now treats reproducibility and protocol discipline as first-class evidence. The strongest protocol conclusion is from Level 3.5:

- noise comparisons require typed external-vs-native corruption contracts;
- confirmatory gates must be fully serialized before the first held-out observation;
- zero-trial integrity blocks are positive evidence of lawful non-execution, not administrative noise.

## 6. Baseline MAP/Resonator Results

The MAP line survived as a bounded baseline, not as a universal winner. Context-conditioned search improved over random subsets in tested Level 1 single-product settings, and Level 3.2/3.2b showed a bounded intermediate recoverability region rather than unlimited clean factorization.

## 7. Context-Conditioned Search

The strongest surviving early result is narrow: external semantic context can improve candidate routing and reduce bad commitments when:

- the task stays within a bounded contract,
- fallback remains available,
- selective acceptance remains explicit,
- the context controller is not mistaken for a new substrate.

This is a search-and-safety result, not a new VSA algebra.

## 8. Native Alternative Substrates

Three substrate conclusions matter:

- the official IBM BCF implementation can be wrapped for scoped single-product audits, but broad parity claims remain unresolved;
- the NeCo clean-U1 paper contract can be reproduced under explicit GF(2) constraints;
- on clean U1, the symbolic exact tuple baseline dominates the task envelope;
- in the paired clean common F=3 envelope, BCF dominates the hard/non-easy instances and a trivial threshold over `M` captures the only practical portfolio value.

## 9. Encoder and Codebook Adaptation

Two encoder-side lines were explicitly blocked:

- decoder-certified atomic admission;
- conflict-guided tagged-symbol repair.

In both cases, the line failed because a more complicated mechanism did not survive causal or equal-bit controls strongly enough to justify architecture growth.

## 10. Representation Repair and Soft Information

The residue-plane work shows a recurring pattern in the atlas: useful information may exist, but a proposed mechanism for storing it can still lose. Soft residue information helped relative to sign-only cleanup, yet the block-LUT dictionary line lost to scalar/equal-bit controls and the surviving engineering recommendation became extra dimensions rather than a custom compressed residue plane.

## 11. Exact Structural Preservation

The strongest exact-structure conclusion is conservative:

- exact first-order manifests can safely support recursive replay after record retrieval;
- ordinary sidecar DAG storage is the honest baseline;
- inline packing did not show a packaging advantage;
- carried exact trace handles helped detached activation, but isolated capsule placement itself did not.

## 12. Noise Contracts and Safety

The atlas repeatedly converged on the same safety lesson: silent wrong recovery is the key failure mode. Typed abstention, exact verification, ambiguity handling, and explicit no-commit policies survive across otherwise unrelated lines.

## 13. Recoverability Cost Atlas

The recoverability cost matrix shows that the repository's surviving methods buy reliability through different currencies:

- more compute
- structured codes
- exact side information
- external context
- more dimensions or bits
- reduced coverage through abstention
- exact fallback

No line demonstrated free recoverability.

The cross-substrate portfolio audit sharpened this point: once dual representation cost, verifier acceptance, and cumulative cascade latency were counted honestly, the hard-cell frontier collapsed to a dominant single method rather than a deployable oracle portfolio.

## 14. Failure-Mode Atlas

The failure-mode atlas includes:

- capacity collapse
- false attractors and false consensus
- context exclusion and misrouting
- certification overfit
- silent wrong acceptance
- storage and compute non-dominance
- packaging without benefit
- wrong-but-valid handles
- protocol leakage

These are not footnotes; they are the main architectural constraints.

## 15. Abstention-First Architecture

The strongest architecture recommendation the atlas can currently support is modest:

> Prefer exact or well-audited baselines, add context or approximate routing only when it demonstrably improves a bounded frontier, keep an explicit verifier, preserve abstention, use exact fallbacks when the task contract already grants exact structural information, and stop portfolio escalation when a dominant single method or trivial static threshold already explains the observed gain.

## 16. Threats to Validity

Major threats remain:

- many positive lines are development-only rather than confirmatory;
- some early historical artifacts used narrower contracts than a public reader might assume;
- optional dependencies and hardware differences matter for reproduction;
- the repository contains more negative and boundary-setting evidence than final architecture wins;
- the cross-substrate portfolio result is still clean-only and does not authorize noise or held-out routing claims;
- not all literature categories have yet been transferred into direct empirical baselines.

## 17. Reproducibility

The public release should distinguish:

- CI validation and smoke tests
- local unit-suite validation
- full historical scientific reruns

The paper tables should cite exact result paths, protocol hashes, and commit references through the evidence registry.

## 18. Conclusion

The atlas does not show that recoverability is impossible. It shows that recoverability is expensive, contract-dependent, and easily overclaimed. The public value of the repository is therefore not a single triumphant mechanism, but a reproducible map of what had to be paid, what failed to pay off, and where exact structure or abstention were the more honest answers.
"""


def render_supplementary_atlas() -> str:
    lines = [
        "# Supplementary Evidence Atlas",
        "",
        "This atlas is generated from the machine-readable registries and summarizes all normalized hypotheses.",
        "",
    ]
    for entry in EVIDENCE_ENTRIES:
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
        "entries": EVIDENCE_ENTRIES,
    }
    claim_payload = {
        "schema_version": "vsa-recoverability-atlas-claims-v1",
        "claims": CLAIMS,
    }
    failure_payload = {
        "schema_version": "vsa-recoverability-atlas-failures-v1",
        "failures": FAILURE_MODES,
    }
    prior_payload = {
        "schema_version": "vsa-recoverability-atlas-prior-art-v1",
        "entries": PRIOR_ART,
    }

    write_json_yaml(PAPER_DIR / "evidence_registry.yaml", evidence_payload)
    write_json_yaml(PAPER_DIR / "claim_ledger.yaml", claim_payload)
    write_json_yaml(PAPER_DIR / "failure_mode_atlas.yaml", failure_payload)
    write_json_yaml(PAPER_DIR / "prior_art_registry.yaml", prior_payload)

    hypothesis_rows = build_hypothesis_matrix()
    prior_rows = build_prior_art_matrix()

    hypothesis_columns = list(hypothesis_rows[0].keys())
    prior_columns = list(prior_rows[0].keys())
    cost_columns = list(COST_MATRIX_ROWS[0].keys())

    write_text(PAPER_DIR / "hypothesis_matrix.csv", csv_from_rows(hypothesis_rows, hypothesis_columns))
    write_text(PAPER_DIR / "hypothesis_matrix.md", "# Hypothesis Matrix\n\n" + render_table(hypothesis_rows, hypothesis_columns))

    write_text(PAPER_DIR / "recoverability_cost_matrix.csv", csv_from_rows(COST_MATRIX_ROWS, cost_columns))
    write_text(PAPER_DIR / "recoverability_cost_matrix.md", "# Recoverability Cost Matrix\n\n" + render_table(COST_MATRIX_ROWS, cost_columns))

    write_text(PAPER_DIR / "prior_art_matrix.csv", csv_from_rows(prior_rows, prior_columns))
    write_text(PAPER_DIR / "prior_art_matrix.md", "# Prior-Art Matrix\n\n" + render_table(prior_rows, prior_columns))

    write_text(PAPER_DIR / "claim_ledger.md", render_claim_ledger_md())
    write_text(PAPER_DIR / "failure_mode_atlas.md", render_failure_atlas_md())
    write_text(PAPER_DIR / "literature_transfer_matrix.md", render_literature_transfer_md())
    write_text(PAPER_DIR / "manuscript.md", render_manuscript())
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
