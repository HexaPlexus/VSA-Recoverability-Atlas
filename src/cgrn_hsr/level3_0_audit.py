from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEVEL3_0_SCHEMA_VERSION = "level3-0-substrate-audit-v1"
LEVEL3_0_CHECKPOINT_COMMIT = "b5bfa89ba0440d18c1ea803c02a015e231df1b96"
LEVEL3_0_DATE = "2026-06-15"
LEVEL3_RESEARCH_DIRECTORY = "research/level3"

PRIMARY_HYPOTHESIS = (
    "Does any existing native representation-decoder pair materially improve the "
    "recovery/capacity/noise Pareto frontier over dense MAP plus classic resonator "
    "under matched semantic payload, storage and compute budgets?"
)
NULL_HYPOTHESIS = (
    "No tested representation-decoder pair materially improves the Pareto frontier "
    "after native tuning and fair budget matching."
)

TASK_CONTRACTS: list[dict[str, Any]] = [
    {
        "task_id": "U0",
        "name": "Known-key cleanup",
        "status": "ACTIVE",
        "observation_contract": "Known role or key with bundled role-filler pairs; unbind then cleanup.",
        "output_contract": "One filler per known role/key, plus detected miss if cleanup fails.",
        "native_semantics": "Role-aware item-memory retrieval after native unbinding.",
        "included_in_primary_substrate_ranking": True,
        "notes": [
            "This is not blind factorization.",
            "Nearest-neighbour cleanup is the native MAP baseline.",
        ],
    },
    {
        "task_id": "U1",
        "name": "Blind single-product factorization",
        "status": "ACTIVE",
        "observation_contract": "All factors unknown; x = bind(f1, ..., fF).",
        "output_contract": "Exactly one prediction per factor domain.",
        "native_semantics": "Native factorizer must return a factor tuple, not an arbitrary target picked post hoc.",
        "included_in_primary_substrate_ranking": True,
        "notes": [
            "This is the direct descendant of the Level 1 single-product contract.",
            "Candidate domains must be identical across paired methods within a trial.",
        ],
    },
    {
        "task_id": "U2",
        "name": "Superposed tuple recovery",
        "status": "ACTIVE",
        "observation_contract": "x = bundle(bind(tuple_1), ..., bind(tuple_K)).",
        "output_contract": "Tuple set or histogram recovery, not an evaluator-chosen target tuple.",
        "native_semantics": "Methods must natively support tuple-set or histogram recovery to be ranked here.",
        "included_in_primary_substrate_ranking": True,
        "notes": [
            "Semantic distractor superposition belongs here, not inside U1.",
            "Methods that only return one tuple do not satisfy U2 without an explicit native set decoder.",
        ],
    },
    {
        "task_id": "U3",
        "name": "Continuous-value cleanup",
        "status": "SEPARATE_TRACK",
        "observation_contract": "Continuous or phase-valued encodings such as FHRR/SSP.",
        "output_contract": "Recovered continuous value or cleanup candidate under the native algebra.",
        "native_semantics": "Report separately from discrete tuple recovery.",
        "included_in_primary_substrate_ranking": False,
        "notes": [
            "Do not merge U3 into discrete U0/U1/U2 scoreboards.",
            "FHRR-specific cleanup and decoding live here.",
        ],
    },
    {
        "task_id": "U4",
        "name": "Nested structures",
        "status": "DEFERRED",
        "observation_contract": "Compositions containing nested bindings or recursively embedded structures.",
        "output_contract": "Structured tree or nested tuple recovery.",
        "native_semantics": "Only eligible after U0-U2 closure.",
        "included_in_primary_substrate_ranking": False,
        "notes": [
            "No Level 3.0 benchmark cell may include U4.",
        ],
    },
    {
        "task_id": "U5",
        "name": "Open-set factor",
        "status": "DEFERRED_SAFETY_TRACK",
        "observation_contract": "At least one factor may be absent from all known candidate domains.",
        "output_contract": "Recovered known factors plus detected unknown or abstention.",
        "native_semantics": "Safety track only; not part of the primary substrate ranking.",
        "included_in_primary_substrate_ranking": False,
        "notes": [
            "Do not fold open-set handling into core substrate ranking.",
        ],
    },
]

REPRESENTATION_DECODER_PAIRS: list[dict[str, Any]] = [
    {
        "method_id": "dense_map_classic",
        "representation": "Dense MAP bipolar hypervectors",
        "native_decoder": "Classic resonator plus native item-memory cleanup",
        "supported_tasks": ["U0", "U1"],
        "task_contract": {
            "U0": "SUPPORTED",
            "U1": "SUPPORTED",
            "U2": "NO_NATIVE_SET_DECODER",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "clean capacity",
            "coordinate corruption via bit flips or sign corruption",
            "erasure if coordinates are masked",
        ],
        "public_implementation": {
            "available": True,
            "name": "TorchHD",
            "url": "https://github.com/hyperdimensional-computing/torchhd",
            "license": "MIT",
        },
        "dynamic_insertion": "Easy new atoms via random bipolar codebook extension.",
        "formal_guarantees": "Weak exact guarantees; empirical cleanup/factorization frontier only.",
        "confidence_failure_surface": "Margins and reconstruction similarity available in the current harness.",
        "memory_scaling": "Codebook O(F*M*D); observation O(D).",
        "compute_scaling": "Iterative factorization cost O(iter * F * M * D).",
        "reproduction_risk": "LOW",
        "verdict": "ADOPT_UPSTREAM",
        "implementation_notes": "Frozen baseline from Level 0/1; no new decoder work authorized.",
    },
    {
        "method_id": "ibm_bcf",
        "representation": "Distributed sparse block codes (GSBC / block code factorizer)",
        "native_decoder": "Official IBM block code factorizer",
        "supported_tasks": ["U1"],
        "task_contract": {
            "U0": "NOT_PRIMARY",
            "U1": "SUPPORTED",
            "U2": "TASK_MISMATCH_FOR_CURRENT_UPSTREAM_CONTRACT",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "clean capacity",
            "native coordinate/device noise",
            "published initialization-noise and iterative-noise variants",
        ],
        "public_implementation": {
            "available": True,
            "name": "IBM in-memory-factorizer",
            "url": "https://github.com/IBM/in-memory-factorizer",
            "license": "Apache-2.0",
            "pinned_commit": "a353f1e918dcb515cad4a89c8e47ce24668954a7",
        },
        "dynamic_insertion": "Possible only inside the native block-code construction; less trivial than MAP random insertion.",
        "formal_guarantees": "Published native-envelope results, but not a universal guarantee across arbitrary semantic payloads.",
        "confidence_failure_surface": "Limited in current upstream; factor-wise margins/final estimates are not exposed like the MAP harness.",
        "memory_scaling": "Sparse block codebooks with explicit block/alphabet structure.",
        "compute_scaling": "Iterative native factorizer; cost depends on blocks, alphabet, and cap/native stopping.",
        "reproduction_risk": "MEDIUM",
        "verdict": "WRAP_UPSTREAM",
        "implementation_notes": [
            "Level 1F.3 cap saturation reflected our frozen cap=16 shootout policy, not the native envelope.",
            "Upstream configs use uncapped or very high iteration budgets; native-envelope reproduction remains possible without modifying upstream.",
        ],
    },
    {
        "method_id": "holovec_attention",
        "representation": "Attention-cleanup shared codebook VSA",
        "native_decoder": "HoloVec AttentionResonatorCleanup",
        "supported_tasks": ["shared-codebook U1 only"],
        "task_contract": {
            "U0": "POSSIBLE_SHARED_CODEBOOK_CLEANUP",
            "U1": "BLOCKED_FACTOR_DOMAIN_MISMATCH",
            "U2": "NO_NATIVE_SET_DECODER",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "shared-codebook decomposition with softmax attention",
        ],
        "public_implementation": {
            "available": True,
            "name": "HoloVec",
            "url": "https://github.com/Twistient/HoloVec",
            "license": "Apache-2.0",
        },
        "dynamic_insertion": "Possible into one flat codebook, but not into separate factor-specific domains via the audited API.",
        "formal_guarantees": "Paper-level empirical claims only.",
        "confidence_failure_surface": "Top labels and scores only; factor-specific domain constraints absent in the public API.",
        "memory_scaling": "Shared codebook rather than factor-local domains.",
        "compute_scaling": "Attention-style iterative cleanup over one codebook.",
        "reproduction_risk": "HIGH_FOR_FAIR_PARITY",
        "verdict": "BLOCK_TASK_MISMATCH",
        "implementation_notes": "Previous audit already showed one flat codebook violates the current factor-specific domain contract.",
    },
    {
        "method_id": "coupled_diffusion",
        "representation": "Diffusion-based coupled inference",
        "native_decoder": "Published coupled diffusion decomposition",
        "supported_tasks": ["candidate U1"],
        "task_contract": {
            "U0": "NOT_PRIMARY",
            "U1": "PAPER_CANDIDATE",
            "U2": "UNKNOWN",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "paper-specific denoising schedule and inference noise",
        ],
        "public_implementation": {
            "available": False,
            "name": "Coupled Inference in Diffusion Models for Semantic Decomposition",
            "url": "https://arxiv.org/abs/2602.09983",
            "license": "UNKNOWN",
        },
        "dynamic_insertion": "Unknown until a public implementation and codebook contract are available.",
        "formal_guarantees": "Paper claims only; no audited upstream runtime in this repository.",
        "confidence_failure_surface": "Unknown without public code.",
        "memory_scaling": "Potentially heavy due to diffusion steps; exact native budget unresolved.",
        "compute_scaling": "Likely much higher than classic iterative cleanup; tuning burden unclear.",
        "reproduction_risk": "VERY_HIGH",
        "verdict": "DEFER_UPSTREAM",
        "implementation_notes": "Do not replicate during Level 3.0; reopen only if upstream code appears or a later isolated replication becomes necessary.",
    },
    {
        "method_id": "linear_code_hdc",
        "representation": "Linear-code HDC over F2",
        "native_decoder": "Exact or linear-system recovery under code/subcode assumptions",
        "supported_tasks": ["U0", "candidate U1", "candidate U2"],
        "task_contract": {
            "U0": "SUPPORTED_UNDER_PAPER_ASSUMPTIONS",
            "U1": "CANDIDATE_REQUIRES_DIRECT_SUM_DESIGN",
            "U2": "CANDIDATE_REQUIRES_LINEAR_SYSTEM_SOLVE",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "binary corruption and erasure under algebraic decoding assumptions",
        ],
        "public_implementation": {
            "available": False,
            "name": "Linear Codes for Hyperdimensional Computing",
            "url": "https://arxiv.org/search/?query=Linear+Codes+for+Hyperdimensional+Computing&searchtype=all",
            "license": "UNKNOWN",
        },
        "dynamic_insertion": "Constrained by code construction; not as free as MAP random insertion.",
        "formal_guarantees": "Stronger exact-recovery story is the main reason to evaluate it.",
        "confidence_failure_surface": "Likely algebraic success/failure rather than smooth margins.",
        "memory_scaling": "Depends on code length, subcode structure, and parity material.",
        "compute_scaling": "Linear algebra over F2 rather than iterative similarity search.",
        "reproduction_risk": "HIGH",
        "verdict": "REPLICATE_PAPER",
        "implementation_notes": {
            "minimal_boundary": "Only the paper-defined encoder/decoder needed for U0/U1/U2 benchmark cells.",
            "paper_curve_test": "Reproduce a paper-consistent exact/noisy recovery curve before any subject comparison.",
            "replacement_plan": "Delete or replace the local reproduction if the authors release a suitable upstream implementation.",
        },
    },
    {
        "method_id": "histogram_recovery",
        "representation": "Histogram-recovery VSA with Reed-Solomon/Hadamard structure",
        "native_decoder": "Histogram recovery decoder",
        "supported_tasks": ["U2"],
        "task_contract": {
            "U0": "NOT_PRIMARY",
            "U1": "NOT_NATIVE_PRIORITY",
            "U2": "SUPPORTED_IN_PRINCIPLE",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "superposition recovery under the paper's histogram/noise assumptions",
        ],
        "public_implementation": {
            "available": False,
            "name": "Efficient Vector Symbolic Architectures from Histogram Recovery",
            "url": "https://arxiv.org/search/?query=Efficient+Vector+Symbolic+Architectures+from+Histogram+Recovery&searchtype=all",
            "license": "UNKNOWN",
        },
        "dynamic_insertion": "Depends on structured codebook family rather than arbitrary random atom insertion.",
        "formal_guarantees": "Potentially strong for U2-style histogram recovery if assumptions hold.",
        "confidence_failure_surface": "Not yet audited in code.",
        "memory_scaling": "Structured codebooks may change the codebook-memory frontier materially.",
        "compute_scaling": "Decoder-specific; no audited runtime path in this repository yet.",
        "reproduction_risk": "MEDIUM_HIGH",
        "verdict": "DEFER_UPSTREAM",
        "implementation_notes": "Do not force into U1. Reopen only if U2 becomes a primary next-step target and no upstream implementation appears.",
    },
    {
        "method_id": "full_tensor_product",
        "representation": "Full tensor product",
        "native_decoder": "Exact tensor unbinding or enumeration oracle",
        "supported_tasks": ["U0", "U1", "U2"],
        "task_contract": {
            "U0": "ORACLE_SUPPORTED",
            "U1": "ORACLE_SUPPORTED",
            "U2": "ORACLE_SUPPORTED_TINY_ONLY",
            "U3": "NOT_APPLICABLE",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "exact algebraic baseline; practical noise story dominated by dimensional explosion",
        ],
        "public_implementation": {
            "available": True,
            "name": "Native tensor algebra / evaluator enumeration",
            "url": "",
            "license": "N/A",
        },
        "dynamic_insertion": "Trivial mathematically, impractical operationally due to dimensional blow-up.",
        "formal_guarantees": "Exact oracle where feasible.",
        "confidence_failure_surface": "Not needed as a practical decoder; serves as evaluator ceiling.",
        "memory_scaling": "Exponential in factor count.",
        "compute_scaling": "Explodes combinatorially except at tiny domains.",
        "reproduction_risk": "LOW",
        "verdict": "ORACLE_ONLY",
        "implementation_notes": "Use only as evaluator or tiny-domain reference, never as a practical latency claim.",
    },
    {
        "method_id": "fhrr_cleanup",
        "representation": "FHRR / SSP continuous-phase encodings",
        "native_decoder": "Improved cleanup and decoding of fractional power encodings",
        "supported_tasks": ["U3"],
        "task_contract": {
            "U0": "SEPARATE_CONTINUOUS_TRACK",
            "U1": "SEPARATE_CONTINUOUS_TRACK",
            "U2": "SEPARATE_CONTINUOUS_TRACK",
            "U3": "SUPPORTED_IN_SEPARATE_TRACK",
            "U4": "DEFERRED",
            "U5": "SAFETY_DEFERRED",
        },
        "noise_model": [
            "phase noise and continuous cleanup error",
        ],
        "public_implementation": {
            "available": False,
            "name": "Improved Cleanup and Decoding of Fractional Power Encodings",
            "url": "https://arxiv.org/search/?query=Improved+Cleanup+and+Decoding+of+Fractional+Power+Encodings&searchtype=all",
            "license": "UNKNOWN",
        },
        "dynamic_insertion": "Track-specific; not comparable to discrete-codebook insertion without a separate protocol.",
        "formal_guarantees": "Track-specific cleanup claims only.",
        "confidence_failure_surface": "Not yet audited in code.",
        "memory_scaling": "Continuous-phase storage; compare only inside U3.",
        "compute_scaling": "Track-specific cleanup rather than discrete factorization.",
        "reproduction_risk": "MEDIUM_HIGH",
        "verdict": "DEFER_UPSTREAM",
        "implementation_notes": "Keep entirely separate from U0-U2 rankings.",
    },
]

FAIRNESS_CONTRACT: dict[str, Any] = {
    "semantic_axes": {
        "F": "number of factors",
        "M": "candidates per factor",
        "K": "number of superposed tuples",
    },
    "native_axes_examples": [
        "dimension or code length",
        "alphabet",
        "sparsity or block count",
        "field size",
        "subcode dimensions",
    ],
    "must_match_within_task": [
        "same atomic identities",
        "same true factor indices or tuple set",
        "same semantic payload F/M/K",
        "same paired seed",
        "same clean/noisy trial intent",
        "same candidate domains inside comparable tasks",
    ],
    "must_be_reported": [
        "semantic payload",
        "observation bytes",
        "codebook bytes",
        "runtime-state bytes",
        "decode compute",
        "materialization time",
        "decode latency",
        "end-to-end latency",
        "peak RAM or VRAM",
    ],
    "forbidden_shortcuts": [
        "equal-D as the sole fairness rule",
        "mixing setup/materialization into native decode latency",
        "forcing a method into a task it does not natively solve",
        "smuggling context narrowing, semantic priors, or controller logic into Level 3 substrate ranking",
    ],
    "context_mechanisms_disabled": [
        "context policy",
        "CNM or H2",
        "semantic pruning",
        "authority controller",
        "warm state transfer",
        "search hierarchy",
    ],
    "phase_boundary_rule": {
        "material_effect_gate": [
            ">= 0.5 log10 gain in recoverable M^F",
            "materially higher noise or erasure boundary",
            "lower silent-wrong recovery at similar coverage",
            "same recovery with materially lower memory or compute",
            "new nondominated Pareto point",
        ],
        "non_effect_example": "Tiny isolated accuracy gains do not justify production promotion.",
    },
}

BENCHMARK_MANIFEST: dict[str, Any] = {
    "schema_version": LEVEL3_0_SCHEMA_VERSION,
    "hypothesis_status": "HYPOTHESIS",
    "primary_hypothesis": PRIMARY_HYPOTHESIS,
    "null_hypothesis": NULL_HYPOTHESIS,
    "development_protocol": {
        "purpose": [
            "coarse search",
            "identify >90%, ~50%, and <10% regions",
        ],
        "trials_per_point": 16,
        "forbidden": [
            "full combinatorial grid",
            "held-out tuning",
        ],
    },
    "freeze_protocol": {
        "freeze_after_development": [
            "easy anchors",
            "boundary cells",
            "failure anchors",
            "selected noise cells",
        ],
        "held_out_trials_per_cell": "64-128 paired trials",
        "statistics": [
            "Wilson intervals",
            "bootstrap intervals where appropriate",
        ],
        "retuning_after_held_out": False,
    },
    "noise_categories": [
        "clean capacity",
        "native coordinate corruption",
        "erasure",
        "semantic distractor superposition",
    ],
    "mandatory_baselines": [
        "MAP + classic resonator",
        "native nearest-neighbour cleanup for U0",
        "exact enumeration for tiny domains",
        "full tensor product oracle where feasible",
    ],
    "context_and_controller_policy": "Disabled for the entire Level 3 substrate shootout.",
    "long_experiments_run_during_level3_0": False,
}

PRODUCTION_PROMOTION_GATE: dict[str, Any] = {
    "subject_promotion_requires": [
        "wins or is nondominated on a subject-relevant task",
        "implementation is reproducible and maintainable",
        "license is acceptable",
        "codebook supports required insertion or update semantics",
        "failure can be detected or safely surfaced",
        "memory and latency fit target hardware",
        "beats non-VSA alternatives for that exact contract",
    ],
    "non_vsa_alternatives_must_be_considered": [
        "exact indexed retrieval for exact-key cleanup",
        "enumeration or algebraic oracle at tiny scale",
        "non-VSA symbolic or linear-system baselines where the task contract makes them natural",
    ],
    "not_enough_for_promotion": [
        "one isolated easy-cell win",
        "tiny non-robust accuracy lift",
        "faster setup but slower decode",
        "better equal-D score with worse byte or compute budget",
    ],
    "status_if_not_promoted": "RESEARCH_ONLY",
}

CLAIMS: dict[str, Any] = {
    "schema_version": LEVEL3_0_SCHEMA_VERSION,
    "primary_status": "HYPOTHESIS",
    "primary_hypothesis": PRIMARY_HYPOTHESIS,
    "null_hypothesis": NULL_HYPOTHESIS,
    "forbidden_claims": [
        "one universal best VSA",
        "BCF or linear codes must solve every recovery task",
        "equal dimension alone proves fairness",
        "context mechanisms or authority control are part of this Level 3 shootout",
    ],
    "allowed_next_stage_claim": "Proceed to isolated native substrate evaluation only after the benchmark contract, task contracts, and implementation ladder are frozen.",
}


def _dependency_audit() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_0_SCHEMA_VERSION,
        "generated_on": LEVEL3_0_DATE,
        "checkpoint_commit": LEVEL3_0_CHECKPOINT_COMMIT,
        "repo_level3_directory": LEVEL3_RESEARCH_DIRECTORY,
        "host_lock_versions": {
            "python_contract": "CPython 3.14 on Windows host for the core repo",
            "numpy": "2.4.6",
            "torch": "2.12.0",
            "torch_hd": "5.8.4",
        },
        "baseline_and_candidates": [
            {
                "method_id": "dense_map_classic",
                "upstream": "https://github.com/hyperdimensional-computing/torchhd",
                "license": "MIT",
                "status": "ADOPT_BASELINE",
            },
            {
                "method_id": "ibm_bcf",
                "upstream": "https://github.com/IBM/in-memory-factorizer",
                "license": "Apache-2.0",
                "pinned_commit": "a353f1e918dcb515cad4a89c8e47ce24668954a7",
                "status": "ADOPT_OR_WRAP",
                "native_envelope_note": (
                    "Upstream configs such as 200a_bcf and 100e_* use uncapped or very high "
                    "iteration budgets. The earlier cap=16 saturation was a harness choice, "
                    "not an upstream algorithm limit."
                ),
            },
            {
                "method_id": "holovec_attention",
                "upstream": "https://github.com/Twistient/HoloVec",
                "license": "Apache-2.0",
                "status": "BLOCK_TASK_MISMATCH",
            },
            {
                "method_id": "coupled_diffusion",
                "upstream": "https://arxiv.org/abs/2602.09983",
                "license": "UNKNOWN",
                "status": "DEFER_UPSTREAM",
            },
            {
                "method_id": "linear_code_hdc",
                "upstream": "paper-only audited; no upstream code pinned in repo",
                "license": "UNKNOWN",
                "status": "REPLICATE_MINIMAL_CANDIDATE",
            },
            {
                "method_id": "histogram_recovery",
                "upstream": "paper-only audited; upstream implementation not pinned in repo",
                "license": "UNKNOWN",
                "status": "DEFER_UPSTREAM",
            },
            {
                "method_id": "fhrr_cleanup",
                "upstream": "paper-only audited; separate U3 track",
                "license": "UNKNOWN",
                "status": "SEPARATE_TRACK",
            },
        ],
    }


def _task_support_matrix() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_0_SCHEMA_VERSION,
        "generated_on": LEVEL3_0_DATE,
        "tasks": TASK_CONTRACTS,
        "methods": [
            {
                "method_id": row["method_id"],
                "representation": row["representation"],
                "native_decoder": row["native_decoder"],
                "task_contract": row["task_contract"],
            }
            for row in REPRESENTATION_DECODER_PAIRS
        ],
    }


def _implementation_ladder() -> dict[str, Any]:
    ladder_rows = []
    for row in REPRESENTATION_DECODER_PAIRS:
        entry: dict[str, Any] = {
            "method_id": row["method_id"],
            "representation": row["representation"],
            "verdict": row["verdict"],
            "why": row["implementation_notes"],
        }
        if row["verdict"] == "REPLICATE_PAPER":
            entry["replacement_plan"] = row["implementation_notes"]["replacement_plan"]
            entry["paper_curve_test"] = row["implementation_notes"]["paper_curve_test"]
            entry["minimal_boundary"] = row["implementation_notes"]["minimal_boundary"]
        ladder_rows.append(entry)

    return {
        "schema_version": LEVEL3_0_SCHEMA_VERSION,
        "generated_on": LEVEL3_0_DATE,
        "allowed_verdicts": [
            "ADOPT_UPSTREAM",
            "WRAP_UPSTREAM",
            "REPLICATE_PAPER",
            "ORACLE_ONLY",
            "DEFER_UPSTREAM",
            "BLOCK_TASK_MISMATCH",
        ],
        "methods": ladder_rows,
    }


def _fairness_contract() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_0_SCHEMA_VERSION,
        "generated_on": LEVEL3_0_DATE,
        **FAIRNESS_CONTRACT,
    }


def _analysis() -> dict[str, Any]:
    return {
        "schema_version": LEVEL3_0_SCHEMA_VERSION,
        "generated_on": LEVEL3_0_DATE,
        "checkpoint_commit": LEVEL3_0_CHECKPOINT_COMMIT,
        "git_status_at_start": "clean",
        "level1_level2_cnm_artifacts_modified": False,
        "new_decoder_added": False,
        "long_benchmark_run_added": False,
        "context_mechanisms_disabled": True,
        "bcf_cap_audit": {
            "prior_shootout_cap": 16,
            "reason_for_saturation": (
                "The Level 1F.3 shootout intentionally used a short frozen cap for fair paired "
                "single-product comparison. IBM upstream native configs instead run uncapped or "
                "with much larger iteration ceilings, so cap saturation does not falsify the native method."
            ),
            "native_envelope_reproduction_possible_without_upstream_modification": True,
        },
        "recommended_next_stage": {
            "name": "Level 3.1 native-envelope reproduction and tiny development search",
            "allowed_actions": [
                "reproduce the MAP U0/U1 baseline under the frozen protocol",
                "reproduce IBM BCF in its native U1 envelope on development cells",
                "decide whether linear-code HDC minimal replication is necessary",
            ],
            "forbidden_actions": [
                "long held-out benchmark before development freeze",
                "new decoder invention",
                "context/controller reintroduction",
                "task-contract drift",
            ],
        },
        "limitation": (
            "Code availability and licensing were frozen at audit time, but unsupported paper-only "
            "methods remain unverified until a dedicated reproduction stage."
        ),
    }


def build_recovery_task_contracts_markdown() -> str:
    lines = [
        "# Level 3 Recovery Task Contracts",
        "",
        f"Schema version: `{LEVEL3_0_SCHEMA_VERSION}`",
        "",
        "## Primary question",
        "",
        f"> {PRIMARY_HYPOTHESIS}",
        "",
        "## Task decomposition",
        "",
        "| Task | Name | Status | Observation contract | Output contract | Primary ranking? |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in TASK_CONTRACTS:
        lines.append(
            "| {task_id} | {name} | {status} | {observation_contract} | {output_contract} | {included} |".format(
                task_id=row["task_id"],
                name=row["name"],
                status=row["status"],
                observation_contract=row["observation_contract"],
                output_contract=row["output_contract"],
                included="yes" if row["included_in_primary_substrate_ranking"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Hard rules",
            "",
            "- U0, U1, U2, and U3 remain explicitly separated.",
            "- U2 must recover a tuple set or histogram; selecting one evaluator-preferred tuple is not allowed.",
            "- U3 is a separate continuous-value track and does not share a scoreboard with U0-U2.",
            "- U4 and U5 stay deferred until U0-U2 are closed.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_prior_art_matrix_markdown() -> str:
    lines = [
        "# Level 3 Substrate Prior-Art Matrix",
        "",
        f"Schema version: `{LEVEL3_0_SCHEMA_VERSION}`",
        "",
        "| representation | native decoder | supported task U0/U1/U2/U3 | noise model | public implementation | license | dynamic insertion | formal guarantees | confidence/failure surface | memory scaling | compute scaling | reproduction risk | verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in REPRESENTATION_DECODER_PAIRS:
        lines.append(
            "| {representation} | {native_decoder} | {supported_tasks} | {noise_model} | {implementation} | {license} | {dynamic_insertion} | {formal_guarantees} | {confidence_failure_surface} | {memory_scaling} | {compute_scaling} | {reproduction_risk} | {verdict} |".format(
                representation=row["representation"],
                native_decoder=row["native_decoder"],
                supported_tasks=", ".join(row["supported_tasks"]),
                noise_model="; ".join(row["noise_model"]),
                implementation=row["public_implementation"]["name"],
                license=row["public_implementation"]["license"],
                dynamic_insertion=row["dynamic_insertion"],
                formal_guarantees=row["formal_guarantees"],
                confidence_failure_surface=row["confidence_failure_surface"],
                memory_scaling=row["memory_scaling"],
                compute_scaling=row["compute_scaling"],
                reproduction_risk=row["reproduction_risk"],
                verdict=row["verdict"],
            )
        )
    lines.extend(
        [
            "",
            "## Read-through",
            "",
            "- Dense MAP plus classic resonator is the frozen baseline, not a moving target.",
            "- IBM BCF remains the strongest official non-MAP U1 candidate because it has a real upstream implementation and published native noise variants.",
            "- HoloVec attention remains blocked for the current factor-specific-domain contract.",
            "- Linear-code HDC is the only paper-only candidate that currently justifies a minimal future reproduction path.",
            "- Histogram recovery and FHRR cleanup stay task-specific rather than universal challengers.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_frozen_benchmark_protocol_markdown() -> str:
    lines = [
        "# Level 3 Frozen Benchmark Protocol",
        "",
        f"Schema version: `{LEVEL3_0_SCHEMA_VERSION}`",
        "",
        "## Frozen semantics",
        "",
        "- Semantic payload axes: `F`, `M`, `K`.",
        "- Native representation axes are separate: dimension/code length, alphabet, sparsity/block count, field size, and subcode dimensions.",
        "- Equal `D` is not sufficient fairness on its own.",
        "",
        "## Noise categories",
        "",
        "1. Clean capacity.",
        "2. Native coordinate corruption.",
        "3. Erasure.",
        "4. Semantic distractor superposition.",
        "",
        "## Phase-boundary protocol",
        "",
        "- Development uses coarse search with `16` trials per point only to identify easy, boundary, and failure regions.",
        "- Freeze easy anchors, boundary cells, failure anchors, and selected noise cells before held-out.",
        "- Held-out uses `64-128` paired trials per frozen cell with no tuning after inspection.",
        "",
        "## Timing and memory",
        "",
        "- Report materialization time, decode latency, and end-to-end latency separately.",
        "- Report observation bytes, codebook bytes, runtime-state bytes, and peak RAM/VRAM.",
        "",
        "## Disabled mechanisms",
        "",
        "- Context policy, CNM/H2, semantic pruning, authority controller, hierarchy, and warm transfer are disabled for the whole Level 3 shootout.",
        "",
        "## Effect gate",
        "",
        "- A substrate is materially stronger only if it creates a new nondominated Pareto point or crosses one of the frozen material-effect thresholds.",
        "- Tiny isolated wins do not authorize production promotion.",
        "",
        "## Held-out discipline",
        "",
        "- Level 3.0 is audit/design only. No long held-out substrate run is authorized here.",
        "",
    ]
    return "\n".join(lines)


def build_production_promotion_gate_markdown() -> str:
    lines = [
        "# Level 3 Production Promotion Gate",
        "",
        f"Schema version: `{LEVEL3_0_SCHEMA_VERSION}`",
        "",
        "A substrate may be proposed for the subject only if all of the following hold:",
        "",
    ]
    for item in PRODUCTION_PROMOTION_GATE["subject_promotion_requires"]:
        lines.append(f"- {item}.")
    lines.extend(
        [
            "",
            "## Anti-NIH reminder",
            "",
            "Non-VSA alternatives must be considered explicitly:",
            "",
        ]
    )
    for item in PRODUCTION_PROMOTION_GATE["non_vsa_alternatives_must_be_considered"]:
        lines.append(f"- {item}.")
    lines.extend(
        [
            "",
            "## Not enough",
            "",
        ]
    )
    for item in PRODUCTION_PROMOTION_GATE["not_enough_for_promotion"]:
        lines.append(f"- {item}.")
    lines.extend(
        [
            "",
            f"If the gate is not met, status stays `{PRODUCTION_PROMOTION_GATE['status_if_not_promoted']}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_level3_0_artifacts(root: Path) -> dict[str, Any]:
    docs_dir = root / "docs"
    research_dir = root / "research" / "level3"
    results_dir = root / "results" / "level3_0"
    docs_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "LEVEL3_RECOVERY_TASK_CONTRACTS.md").write_text(
        build_recovery_task_contracts_markdown(),
        encoding="utf-8",
    )
    (docs_dir / "LEVEL3_SUBSTRATE_PRIOR_ART_MATRIX.md").write_text(
        build_prior_art_matrix_markdown(),
        encoding="utf-8",
    )
    (docs_dir / "LEVEL3_FROZEN_BENCHMARK_PROTOCOL.md").write_text(
        build_frozen_benchmark_protocol_markdown(),
        encoding="utf-8",
    )
    (docs_dir / "LEVEL3_PRODUCTION_PROMOTION_GATE.md").write_text(
        build_production_promotion_gate_markdown(),
        encoding="utf-8",
    )
    (research_dir / "README.md").write_text(
        "\n".join(
            [
                "# Level 3 Research Staging",
                "",
                "This directory is reserved for Level 3 substrate-selection research artifacts.",
                "",
                "- Status: audit/design only during Level 3.0.",
                "- Context policy, CNM, semantic pruning, and authority control remain disabled here.",
                "- No decoder implementation or long benchmark run is authorized in this stage.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payloads = {
        "dependency_audit.json": _dependency_audit(),
        "representation_decoder_matrix.json": {
            "schema_version": LEVEL3_0_SCHEMA_VERSION,
            "generated_on": LEVEL3_0_DATE,
            "methods": REPRESENTATION_DECODER_PAIRS,
        },
        "task_support_matrix.json": _task_support_matrix(),
        "implementation_ladder.json": _implementation_ladder(),
        "benchmark_manifest.json": BENCHMARK_MANIFEST,
        "fairness_contract.json": _fairness_contract(),
        "claims.json": CLAIMS,
        "analysis.json": _analysis(),
    }

    for file_name, payload in payloads.items():
        (results_dir / file_name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return payloads
