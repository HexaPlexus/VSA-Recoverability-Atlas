from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEVEL2B0_SCHEMA_VERSION = "level2b0-anti-nih-audit-v1"
LEVEL2B0_CHECKPOINT_COMMIT = "be8d7d9e4be07cb6665c6db744d49f5d6bafcb64"
LEVEL2B0_DATE = "2026-06-15"

PROBLEM_CLASSES: list[dict[str, Any]] = [
    {
        "problem_class": "A",
        "name": "Exact identity lookup",
        "input_contract": "Exact entity identifier or unambiguous canonical key.",
        "output_contract": "Single entity id or hard miss.",
        "uncertainty_representation": "Usually none beyond key existence.",
        "online_offline_behavior": "Online point lookup.",
        "exact_keys_exist": True,
        "entities_move_change": False,
        "new_entities_may_appear": False,
        "required_latency": "Sub-millisecond to low-millisecond.",
        "required_provenance": "Key source and last indexed update.",
        "failure_modes": [
            "missing key",
            "stale index",
            "schema drift",
        ],
        "existing_method": "Database index / hash map / primary key lookup.",
        "coverage": 1.0,
        "mismatch": "None for closed-world exact-id queries.",
        "verdict": "ADOPT",
        "why_not_scratch": "A custom resolver only recreates commodity indexing and risks regressions.",
        "required_adapter": "None beyond query-object to key extraction.",
    },
    {
        "problem_class": "B",
        "name": "Structured fuzzy entity resolution",
        "input_contract": "Partial or noisy structured attributes over a fixed canonical entity catalog.",
        "output_contract": "Ranked candidate entity ids with scores or unresolved.",
        "uncertainty_representation": "Match probability or ranked similarity score.",
        "online_offline_behavior": "Offline training plus online candidate lookup.",
        "exact_keys_exist": False,
        "entities_move_change": False,
        "new_entities_may_appear": True,
        "required_latency": "Low-latency query-time ranking after model setup.",
        "required_provenance": "Per-field evidence and candidate source catalog.",
        "failure_modes": [
            "false merge",
            "false split",
            "overconfident near-duplicate",
            "missing-field bias",
        ],
        "existing_method": "dedupe / Splink / probabilistic record linkage.",
        "coverage": 0.9,
        "mismatch": "Libraries expect tabular records and need a thin adapter from query-cue objects.",
        "verdict": "WRAP",
        "why_not_scratch": "Matching, calibration, and blocking are mature ER problems with extensive prior art.",
        "required_adapter": "Query cue to record dict conversion, thresholded unresolved wrapper, ranked-id handoff.",
    },
    {
        "problem_class": "C",
        "name": "Canonical gazetteer matching",
        "input_contract": "Messy record against a fixed canonical entity table.",
        "output_contract": "Top canonical matches with confidence.",
        "uncertainty_representation": "Per-match probabilities or scores.",
        "online_offline_behavior": "Pre-index canonical set, then online search.",
        "exact_keys_exist": False,
        "entities_move_change": False,
        "new_entities_may_appear": True,
        "required_latency": "Interactive search latency.",
        "required_provenance": "Returned candidate ids and match scores.",
        "failure_modes": [
            "forced low-confidence match",
            "index predicate recall loss",
            "ambiguous near-ties",
        ],
        "existing_method": "dedupe Gazetteer / StaticGazetteer.",
        "coverage": 0.95,
        "mismatch": "No first-class action-layer abstention label; unresolved must be wrapped around zero/low-score outputs.",
        "verdict": "ADOPT",
        "why_not_scratch": "Gazetteer matching is directly supported upstream, including indexing and scored search.",
        "required_adapter": "Optional abstention threshold and score normalization.",
    },
    {
        "problem_class": "D",
        "name": "Candidate blocking",
        "input_contract": "Large candidate table plus blocking policy.",
        "output_contract": "Reduced candidate set with measurable recall/reduction trade-off.",
        "uncertainty_representation": "Pair completeness, reduction ratio, candidate recall.",
        "online_offline_behavior": "Pre-match filtering before expensive scoring.",
        "exact_keys_exist": False,
        "entities_move_change": False,
        "new_entities_may_appear": True,
        "required_latency": "Must reduce downstream compute materially.",
        "required_provenance": "Blocking rule identity and exclusion statistics.",
        "failure_modes": [
            "truth dropped before scoring",
            "context-induced over-pruning",
            "opaque recall loss",
        ],
        "existing_method": "Splink blocking rules / dedupe fingerprinter / standard ER blocking.",
        "coverage": 0.95,
        "mismatch": "Context-generated blocking is not novel by itself and must be compared to ordinary blocking baselines.",
        "verdict": "ADAPT",
        "why_not_scratch": "Blocking is already a standard ER design axis with established metrics and tooling.",
        "required_adapter": "External policy chooses among upstream blocking rules and logs recall/reduction.",
    },
    {
        "problem_class": "E",
        "name": "Streaming observation-to-entity association",
        "input_contract": "Time-ordered observations with misses, clutter, and uncertain identity.",
        "output_contract": "Observation-to-track/entity associations with posterior confidence.",
        "uncertainty_representation": "Association probabilities and track posteriors.",
        "online_offline_behavior": "Online sequential update.",
        "exact_keys_exist": False,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Per-tick or per-observation online update.",
        "required_provenance": "Association hypothesis trace and missed-detection handling.",
        "failure_modes": [
            "identity swap",
            "track fragmentation",
            "premature deletion",
            "clutter attachment",
        ],
        "existing_method": "Stone Soup data association stack.",
        "coverage": 0.85,
        "mismatch": "Native interfaces are tracking-centric, so structured symbolic observations require a representation adapter.",
        "verdict": "WRAP",
        "why_not_scratch": "JPDA/MHT-style data association is a mature field with difficult corner cases.",
        "required_adapter": "Structured observation to Stone Soup measurement/state adapter.",
    },
    {
        "problem_class": "F",
        "name": "Multi-hypothesis identity tracking",
        "input_contract": "Ambiguous sequential observations under clutter or missed detections.",
        "output_contract": "Competing identity/track hypotheses with confidence or delayed commitment.",
        "uncertainty_representation": "Hypothesis probabilities and track existence evidence.",
        "online_offline_behavior": "Online recursive maintenance.",
        "exact_keys_exist": False,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Bounded online cost per step.",
        "required_provenance": "Hypothesis lineage and deletion/initiation reasons.",
        "failure_modes": [
            "identity coalescence",
            "hypothesis explosion",
            "incorrect hard commit",
        ],
        "existing_method": "Stone Soup JPDA / JPDA with LBP / initiator + deleter stack.",
        "coverage": 0.85,
        "mismatch": "Not a canonical tabular gazetteer matcher; best fit is sequential sensor-style association.",
        "verdict": "WRAP",
        "why_not_scratch": "Maintaining calibrated competing hypotheses is exactly what tracking libraries already solve.",
        "required_adapter": "Map symbolic events into tracking observations and keep native probabilities intact.",
    },
    {
        "problem_class": "G",
        "name": "Cue-based episodic retrieval",
        "input_contract": "Partial cue requesting a past episode or memory trace.",
        "output_contract": "Retrieved episode or retrieval failure.",
        "uncertainty_representation": "Retrieval threshold, activation, or abstention.",
        "online_offline_behavior": "Online retrieval over stored episodes.",
        "exact_keys_exist": "Sometimes",
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Interactive cognitive retrieval.",
        "required_provenance": "Episode identity, cue features, retrieval threshold.",
        "failure_modes": [
            "intrusion",
            "commission error",
            "omission",
            "stale retrieval",
        ],
        "existing_method": "Soar episodic memory / ACT-R declarative retrieval.",
        "coverage": 0.75,
        "mismatch": "Whole architectures are much larger than the current seam and do not natively satisfy typed external authority contracts.",
        "verdict": "ADAPT",
        "why_not_scratch": "Cue-based episodic retrieval and thresholded recall are classic cognitive-memory mechanisms.",
        "required_adapter": "Adopt retrieval-pattern ideas, not full architecture runtime.",
    },
    {
        "problem_class": "H",
        "name": "Context-biased declarative retrieval",
        "input_contract": "Cue plus active context or spreading-activation signal.",
        "output_contract": "Ranked retrieval candidates or thresholded miss.",
        "uncertainty_representation": "Activation, match score, or retrieval threshold.",
        "online_offline_behavior": "Online biased retrieval.",
        "exact_keys_exist": False,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Interactive selection under bounded compute.",
        "required_provenance": "Context source and retrieval threshold.",
        "failure_modes": [
            "context leakage",
            "context over-narrowing",
            "spurious activation",
        ],
        "existing_method": "ACT-R spreading activation and partial matching; Soar semantic/episodic cueing.",
        "coverage": 0.75,
        "mismatch": "Patterns exist, but not as a drop-in Python component for mixed ER/tracking pipelines.",
        "verdict": "ADAPT",
        "why_not_scratch": "Biased declarative retrieval is established; novelty cannot rest on 'adding context' alone.",
        "required_adapter": "External context must remain explicit and comparable against standard blocking/retrieval baselines.",
    },
    {
        "problem_class": "I",
        "name": "Temporal belief projection",
        "input_contract": "Observed event log plus association outputs.",
        "output_contract": "Current indexed belief state with support/conflict references.",
        "uncertainty_representation": "Confidence, stale flags, conflict sets, possible-unobserved-change markers.",
        "online_offline_behavior": "Streaming reducer over indexed events.",
        "exact_keys_exist": True,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Low-latency reducer update.",
        "required_provenance": "Supporting episode ids and supersession links.",
        "failure_modes": [
            "stale projection",
            "silent overwrite",
            "loss of conflict provenance",
        ],
        "existing_method": "Indexed event store + explicit reducer + optional tracker outputs.",
        "coverage": 0.8,
        "mismatch": "No single audited library owns both symbolic event provenance and downstream action authority.",
        "verdict": "COMPOSE",
        "why_not_scratch": "This is integration glue around already-understood indexing and tracking patterns, not a new matcher.",
        "required_adapter": "Reducer that preserves support/conflict references instead of inventing new memory math.",
    },
    {
        "problem_class": "J",
        "name": "Uncertainty-preserving commit authority",
        "input_contract": "Native matcher/tracker outputs plus downstream action stakes.",
        "output_contract": "Commit, abstain, or defer without erasing uncertainty.",
        "uncertainty_representation": "Thresholded confidence, unresolved state, conflict trace.",
        "online_offline_behavior": "Online gating between inference and action.",
        "exact_keys_exist": False,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Bounded runtime decision.",
        "required_provenance": "Why action was accepted, deferred, or rejected.",
        "failure_modes": [
            "silent false merge",
            "premature irreversible commit",
            "ground-truth leakage into action gate",
        ],
        "existing_method": "Thresholded retrieval and unresolved/no-match outputs exist across ER and cognitive-memory systems.",
        "coverage": 0.7,
        "mismatch": "Authority boundary across heterogeneous native systems is integration-specific, but not enough to justify a new matcher.",
        "verdict": "COMPOSE",
        "why_not_scratch": "The seam is decision policy and provenance retention, not reinvention of confidence scoring.",
        "required_adapter": "Normalize native confidence surfaces into commit/defer semantics while keeping source evidence.",
    },
    {
        "problem_class": "K",
        "name": "Open-world new-entity lifecycle",
        "input_contract": "Novel or unresolved observations that may refer to unseen entities.",
        "output_contract": "Deferred no-match, provisional identity, or new-track initiation.",
        "uncertainty_representation": "No-match probability, provisional state, merge risk.",
        "online_offline_behavior": "Streaming with delayed consolidation.",
        "exact_keys_exist": False,
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Online-safe deferral, slower offline consolidation acceptable.",
        "required_provenance": "Why a new entity was or was not created.",
        "failure_modes": [
            "false new entity",
            "false merge into existing entity",
            "premature canonicalization",
        ],
        "existing_method": "Partial coverage via Dedupe no-match behavior and Stone Soup track initiation.",
        "coverage": 0.55,
        "mismatch": "Full provisional-identity lifecycle crosses ER, tracking, and memory governance and is outside current benchmark scope.",
        "verdict": "BLOCK",
        "why_not_scratch": "It is a large product/runtime problem, not the next minimal research seam.",
        "required_adapter": "Defer entirely until a narrower claim is defined.",
    },
    {
        "problem_class": "L",
        "name": "Cross-mechanism routing and budget allocation",
        "input_contract": "Query/observation context plus a menu of native resolvers and blocking policies.",
        "output_contract": "Chosen native mechanism, candidate budget, fallback path, and abstention trace.",
        "uncertainty_representation": "Coverage-risk-compute trade-off plus preserved native uncertainty.",
        "online_offline_behavior": "Online controller over heterogeneous subsystems.",
        "exact_keys_exist": "Mixed",
        "entities_move_change": True,
        "new_entities_may_appear": True,
        "required_latency": "Must save compute without hiding uncertainty.",
        "required_provenance": "Which mechanism ran, which candidates were filtered, and why fallback occurred.",
        "failure_modes": [
            "ordinary blocking disguised as novelty",
            "context error causing truth exclusion",
            "budget bias causing silent wrong commit",
        ],
        "existing_method": "Composable but not closed by a single upstream system.",
        "coverage": 0.45,
        "mismatch": "Audited libraries expose native matchers or trackers, but none provides a shared external context/routing/budget interface with authority-preserving fallback across heterogeneous mechanisms.",
        "verdict": "BUILD",
        "why_not_scratch": "Only the controller seam is still plausibly novel; rebuilding matchers would duplicate prior art.",
        "required_adapter": "One small controller around adopted systems, tested against standard blocking and fallback baselines.",
    },
]

REQUIREMENT_MATRIX: list[dict[str, str]] = [
    {
        "requirement": "exact entity lookup",
        "existing_method": "Indexed key-value lookup",
        "coverage": "100%",
        "mismatch": "None in closed-world exact-id cases.",
        "verdict": "ADOPT",
        "why_not_scratch": "Commodity database/index problem.",
        "required_adapter": "Key extraction only.",
    },
    {
        "requirement": "noisy structured cue",
        "existing_method": "dedupe / Splink probabilistic ER",
        "coverage": "90%",
        "mismatch": "Need thin query-object adapter and abstention wrapper.",
        "verdict": "WRAP",
        "why_not_scratch": "Would re-implement fuzzy matching and calibration.",
        "required_adapter": "Cue-to-record conversion and ranked-id handoff.",
    },
    {
        "requirement": "canonical entity resolution",
        "existing_method": "dedupe Gazetteer",
        "coverage": "95%",
        "mismatch": "No explicit action-layer abstention token.",
        "verdict": "ADOPT",
        "why_not_scratch": "Gazetteer path already exists upstream.",
        "required_adapter": "Optional threshold to unresolved state.",
    },
    {
        "requirement": "context-dependent candidate restriction",
        "existing_method": "Splink blocking rules / Dedupe fingerprinter",
        "coverage": "95%",
        "mismatch": "Must benchmark against ordinary blocking; otherwise novelty collapses.",
        "verdict": "ADAPT",
        "why_not_scratch": "Blocking is standard ER tooling.",
        "required_adapter": "External policy picks among upstream blocking policies.",
    },
    {
        "requirement": "probabilistic ambiguity",
        "existing_method": "Splink probabilities / dedupe confidence / Stone Soup hypothesis weights",
        "coverage": "85%",
        "mismatch": "Need shared uncertainty handoff to downstream action policy.",
        "verdict": "COMPOSE",
        "why_not_scratch": "Native systems already score uncertainty.",
        "required_adapter": "Normalize scores, preserve provenance.",
    },
    {
        "requirement": "temporal continuity",
        "existing_method": "Stone Soup JPDA-style association",
        "coverage": "85%",
        "mismatch": "Requires observation adapter from symbolic events.",
        "verdict": "WRAP",
        "why_not_scratch": "Sequential association is established tracking prior art.",
        "required_adapter": "Observation/state translation layer.",
    },
    {
        "requirement": "possible unobserved change",
        "existing_method": "Tracking missed detections plus explicit belief reducer",
        "coverage": "80%",
        "mismatch": "Need explicit action-layer stale/conflict semantics.",
        "verdict": "COMPOSE",
        "why_not_scratch": "This is reducer logic, not a new retrieval algorithm.",
        "required_adapter": "Reducer with support/conflict references.",
    },
    {
        "requirement": "new entity initiation",
        "existing_method": "Stone Soup initiators / unresolved ER no-match",
        "coverage": "55%",
        "mismatch": "Full provisional identity lifecycle remains out of scope.",
        "verdict": "BLOCK",
        "why_not_scratch": "Too large and underspecified for current stage.",
        "required_adapter": "Defer until separate lifecycle benchmark exists.",
    },
    {
        "requirement": "provisional identity",
        "existing_method": "Partial overlap from MHT and unresolved ER",
        "coverage": "50%",
        "mismatch": "No audited system gives the exact cross-memory authority contract for provisional identities.",
        "verdict": "BLOCK",
        "why_not_scratch": "Would balloon into a lifecycle architecture project.",
        "required_adapter": "None until scope is narrowed.",
    },
    {
        "requirement": "false merge prevention",
        "existing_method": "Thresholded no-match + multi-hypothesis tracking",
        "coverage": "75%",
        "mismatch": "Requires authority policy spanning matcher and action layers.",
        "verdict": "COMPOSE",
        "why_not_scratch": "Confidence thresholds already exist upstream.",
        "required_adapter": "Shared abstain/defer contract.",
    },
    {
        "requirement": "evidence provenance",
        "existing_method": "Native scores plus explicit controller logs",
        "coverage": "70%",
        "mismatch": "No single library logs cross-mechanism decision provenance end to end.",
        "verdict": "COMPOSE",
        "why_not_scratch": "Provenance is glue around adopted tools.",
        "required_adapter": "Structured decision record.",
    },
    {
        "requirement": "rollback/non-commit",
        "existing_method": "Unresolved/no-match thresholds and deferred track initiation",
        "coverage": "70%",
        "mismatch": "Need explicit authority boundary, not just low score.",
        "verdict": "COMPOSE",
        "why_not_scratch": "Non-commit policy should wrap native scores, not replace them.",
        "required_adapter": "Thresholded abstain wrapper.",
    },
    {
        "requirement": "downstream action integration",
        "existing_method": "Controller layer over native matcher/tracker outputs",
        "coverage": "45%",
        "mismatch": "No upstream package owns context routing, budget control, and safe fallback across heterogeneous systems.",
        "verdict": "BUILD",
        "why_not_scratch": "This is the only plausible minimal seam left after prior-art overlap.",
        "required_adapter": "Small external controller with explicit ablations.",
    },
]

LIBRARY_AUDIT: dict[str, dict[str, Any]] = {
    "splink": {
        "name": "Splink",
        "category": "Entity resolution / probabilistic record linkage",
        "upstream": "https://github.com/moj-analytical-services/splink",
        "docs": "https://moj-analytical-services.github.io/splink/",
        "license": "MIT",
        "requires_python": ">=3.9,<4.0",
        "local_smoke": {
            "install_on_windows_py314": True,
            "import_ok": True,
            "minimal_linker_ok": True,
            "local_version": "4.0.16",
        },
        "capabilities": [
            "probabilistic record linkage",
            "external blocking rules",
            "evaluation and threshold tooling",
            "incremental matching to new records",
        ],
        "limitations": [
            "tabular structured-record matcher rather than temporal tracker",
            "no built-in downstream action authority layer",
        ],
        "activity_status": "Active open-source project with documented releases and substantial community usage.",
    },
    "dedupe": {
        "name": "dedupe",
        "category": "Entity resolution / gazetteer / fuzzy matching",
        "upstream": "https://github.com/dedupeio/dedupe",
        "docs": "https://docs.dedupe.io/en/latest/API-documentation.html",
        "license": "MIT",
        "requires_python": ">=3.8",
        "local_smoke": {
            "install_on_windows_py314": True,
            "import_ok": True,
            "gazetteer_object_ok": True,
            "local_version": "3.0.3",
        },
        "capabilities": [
            "gazetteer and record-link workflows",
            "ranked matches with confidence",
            "blocking/fingerprinter primitives",
            "active-learning training path",
        ],
        "limitations": [
            "training-oriented workflow adds setup cost",
            "Windows multiprocessing requires __main__ guard",
            "no first-class action-layer unresolved taxonomy",
        ],
        "activity_status": "Mature, widely used Python ER library with long commit history and maintained docs.",
    },
    "stonesoup": {
        "name": "Stone Soup",
        "category": "Tracking / data association / state estimation",
        "upstream": "https://github.com/dstl/Stone-Soup",
        "docs": "https://stonesoup.readthedocs.io/en/latest/",
        "license": "MIT",
        "requires_python": ">=3.10",
        "local_smoke": {
            "install_on_windows_py314": True,
            "import_ok": True,
            "association_classes_ok": True,
            "local_version": "1.8",
        },
        "capabilities": [
            "PDA and JPDA data association",
            "track initiation and deletion",
            "multiple competing hypotheses",
            "missed-detection handling",
        ],
        "limitations": [
            "tracking-centric abstractions rather than canonical gazetteer matching",
            "symbolic/tabular entities require observation adapters",
        ],
        "activity_status": "Active tracking framework with examples, tutorials, and recent release history.",
    },
    "bayesian_er_public_code": {
        "name": "dblink / exchanger family",
        "category": "Bayesian entity resolution",
        "upstream": "https://github.com/cleanzr/dblink",
        "docs": "https://github.com/cleanzr/exchanger",
        "license": "GPL-3.0 family",
        "requires_python": "Not primary Python-first path; Spark/Scala or R ecosystems dominate.",
        "local_smoke": {
            "install_on_windows_py314": False,
            "import_ok": False,
            "reason": "Not a thin Python drop-in for the current repo contracts.",
        },
        "capabilities": [
            "Bayesian uncertainty over entity assignments",
            "distributed Bayesian ER in Spark",
            "public code exists",
        ],
        "limitations": [
            "ecosystem mismatch for the current Python-only audit seam",
            "heavier runtime and licensing trade-offs than Splink/dedupe",
        ],
        "activity_status": "Useful audit reference, but not the preferred near-term integration substrate.",
    },
    "soar": {
        "name": "Soar",
        "category": "Cognitive architecture",
        "upstream": "https://soar.eecs.umich.edu/",
        "docs": "https://soar.eecs.umich.edu/",
        "license": "Architecture/runtime audit only; full integration not pursued here.",
        "requires_python": "Not audited as a Python package for this stage.",
        "local_smoke": None,
        "capabilities": [
            "episodic memory",
            "semantic memory",
            "working-memory driven retrieval",
        ],
        "limitations": [
            "whole-architecture adoption is much broader than the Level 2B seam",
            "does not directly solve our Python-side authority/routing contract",
        ],
        "activity_status": "Long-lived architecture with tutorials and manuals.",
    },
    "actr": {
        "name": "ACT-R",
        "category": "Cognitive architecture / declarative retrieval theory",
        "upstream": "https://act-r.psy.cmu.edu/",
        "docs": "https://act-r.psy.cmu.edu/",
        "license": "Architecture/runtime audit only; no adoption attempt here.",
        "requires_python": "Not audited as a Python package for this stage.",
        "local_smoke": None,
        "capabilities": [
            "partial matching",
            "spreading activation",
            "retrieval threshold",
        ],
        "limitations": [
            "theory/pattern source, not a direct plug-in resolver for our repo",
            "does not provide the typed cross-mechanism authority seam by itself",
        ],
        "activity_status": "Canonical cognitive-memory prior art.",
    },
    "coala": {
        "name": "CoALA",
        "category": "Memory/action decomposition framework",
        "upstream": "https://arxiv.org/abs/2309.02427",
        "docs": "https://openreview.net/forum?id=1i6ZCvflQJ",
        "license": "Paper/framework audit only.",
        "requires_python": "Not applicable.",
        "local_smoke": None,
        "capabilities": [
            "working/episodic/semantic/procedural decomposition",
            "structured internal/external action framing",
        ],
        "limitations": [
            "taxonomy rather than a ready-made resolver or tracker",
            "does not remove the need to evaluate ordinary blocking/routing baselines",
        ],
        "activity_status": "Useful architectural taxonomy, not a closed implementation.",
    },
}

SMOKE_RESULTS: dict[str, Any] = {
    "environment": {
        "python": "3.14 (temporary audit venv on Windows)",
        "core_repo_environment_modified": False,
        "bcf_invoked": False,
    },
    "splink": {
        "install": "success",
        "version": "4.0.16",
        "import": "success",
        "minimal_smoke": "Created a Linker over a tiny pandas DataFrame with external blocking rules and DuckDB backend.",
        "observed_api": [
            "Linker(..., settings, db_api=...)",
            "linker.inference.predict(...)",
            "linker.inference.find_matches_to_new_records(...)",
            "linker.training.*",
            "linker.evaluation.*",
        ],
    },
    "dedupe": {
        "install": "success",
        "version": "3.0.3",
        "import": "success",
        "minimal_smoke": "Instantiated a Gazetteer with structured String variables and inspected search/index signatures.",
        "observed_api": [
            "Gazetteer.index(data)",
            "Gazetteer.search(data, threshold=0.0, n_matches=1, generator=False)",
            "StaticGazetteer.search(...)",
            "uncertain_pairs()",
        ],
        "windows_note": "Docs require __main__ guard for multiprocessing on Windows and macOS.",
    },
    "stonesoup": {
        "install": "success",
        "version": "1.8",
        "import": "success",
        "minimal_smoke": "Imported PDA, JPDA, PDAHypothesiser, MultiMeasurementInitiator, and UpdateTimeDeleter.",
        "observed_api": [
            "PDA(hypothesiser)",
            "JPDA(hypothesiser)",
            "PDAHypothesiser(...)",
            "MultiMeasurementInitiator(...)",
            "UpdateTimeDeleter(...)",
        ],
    },
    "bayesian_er_public_code": {
        "install": "not_attempted_locally",
        "reason": "Audited as public prior art, but ecosystem mismatch kept it out of thin-smoke integration on this stage.",
    },
}

OVERLAP_ROWS: list[dict[str, str]] = [
    {
        "proposed_component": "Exact entity lookup",
        "existing_pattern": "Database index / key-value store",
        "status": "Not new",
        "note": "Use indexed lookup directly for exact-id queries; VSA should not be on this path.",
    },
    {
        "proposed_component": "Structured fuzzy entity matching",
        "existing_pattern": "dedupe / Splink",
        "status": "Not new",
        "note": "Standard structured ER already covers noisy tabular identity matching and ranking.",
    },
    {
        "proposed_component": "Context-biased candidate restriction",
        "existing_pattern": "Standard blocking in ER",
        "status": "Weak novelty",
        "note": "Only defensible if evaluated as external policy over unchanged native matchers.",
    },
    {
        "proposed_component": "Sequential association under misses/clutter",
        "existing_pattern": "Stone Soup PDA/JPDA/MHT family",
        "status": "Not new",
        "note": "Do not hand-roll trackers or hypothesis maintenance.",
    },
    {
        "proposed_component": "Cue-based episodic retrieval",
        "existing_pattern": "Soar episodic memory",
        "status": "Not new",
        "note": "Architecture pattern exists; do not present retrieval-by-cue as a fresh mechanism.",
    },
    {
        "proposed_component": "Partial matching and thresholded declarative retrieval",
        "existing_pattern": "ACT-R declarative memory",
        "status": "Not new",
        "note": "Partial matching, spreading activation, and retrieval thresholds are established.",
    },
    {
        "proposed_component": "Memory/action decomposition",
        "existing_pattern": "CoALA",
        "status": "Not new",
        "note": "The high-level split between memory systems and actions is already a named pattern.",
    },
    {
        "proposed_component": "Authority-preserving controller across heterogeneous native systems",
        "existing_pattern": "No single audited upstream package closed this seam",
        "status": "Possible seam",
        "note": "Only survives if compared against ordinary blocking/routing and if native uncertainty remains intact.",
    },
]


def build_prior_art_matrix_markdown() -> str:
    lines = [
        "# Level 2B.0 Prior-Art Matrix",
        "",
        f"Schema version: `{LEVEL2B0_SCHEMA_VERSION}`",
        "",
        "| Requirement | Existing method/library | Coverage | Mismatch | Verdict | Why not scratch | Required adapter |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in REQUIREMENT_MATRIX:
        lines.append(
            "| {requirement} | {existing_method} | {coverage} | {mismatch} | {verdict} | {why_not_scratch} | {required_adapter} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def build_architecture_overlap_markdown() -> str:
    lines = [
        "# Level 2B.0 Architecture Overlap",
        "",
        "## Proposed path",
        "",
        "```text",
        "partial/noisy cue",
        "    -> candidate restriction",
        "    -> native matcher or tracker",
        "    -> indexed belief projection",
        "    -> commit / abstain / fallback",
        "```",
        "",
        "## Overlap map",
        "",
        "| Proposed component | Existing pattern | Status | Note |",
        "| --- | --- | --- | --- |",
    ]
    for row in OVERLAP_ROWS:
        lines.append(
            "| {proposed_component} | {existing_pattern} | {status} | {note} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Read-through",
            "",
            "- Splink already covers probabilistic matching, explicit blocking, and evaluation over structured records.",
            "- dedupe already covers gazetteer-style canonical matching over noisy structured inputs.",
            "- Stone Soup already covers association hypotheses, missed detections, initiators, and deleters.",
            "- Soar and ACT-R already cover cue-based episodic/declarative retrieval patterns and thresholded recall.",
            "- CoALA already names the memory/action decomposition at the architecture level.",
            "- The only seam still plausibly worth building is a very small external controller that chooses among adopted native mechanisms while preserving uncertainty and non-commit authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_research_seam_markdown() -> str:
    return "\n".join(
        [
            "# Level 2B.0 Research Seam",
            "",
            "## Verdict",
            "",
            "`BUILD` is justified only for one seam: a thin external controller over adopted native systems.",
            "",
            "## Candidate seam",
            "",
            "> Existing systems already solve exact lookup, fuzzy structured entity resolution, canonical gazetteer matching, data association, cue-based episodic retrieval, and thresholded declarative retrieval. They do not provide a shared external context/routing/budget interface with preserved uncertainty and explicit non-commit authority across heterogeneous native systems. We therefore only allow building a minimal controller that chooses among adopted native resolvers or blocking policies without replacing their internal algorithms.",
            "",
            "## What survives overlap audit",
            "",
            "- `dedupe` or `Splink` should own structured entity matching.",
            "- `Stone Soup` should own sequential association when temporal identity continuity is the real problem.",
            "- Indexed event/belief stores should own exact temporal state.",
            "- The controller may choose mechanism, candidate budget, fallback, and abstention semantics.",
            "",
            "## What does not survive overlap audit",
            "",
            "- A custom weighted attribute matcher.",
            "- A custom probabilistic entity resolver.",
            "- A custom multi-hypothesis tracker.",
            "- A claim that 'contextual blocking' is novel without baseline blocking comparisons.",
            "- A claim that cue-based retrieval is new without acknowledging Soar/ACT-R overlap.",
            "",
            "## Exact next experiment",
            "",
            "If Level 2B proceeds, it should compare:",
            "",
            "```text",
            "A. Native resolver with standard blocking",
            "B. Native resolver with context-generated blocking",
            "C. Native resolver with context-generated blocking + safe global fallback",
            "D. Oracle blocking ceiling",
            "E. Optional MAP/VSA blocker only for genuinely distributed non-tabular cues",
            "```",
            "",
            "The matcher and downstream indexed belief projection must remain unchanged across A/B/C/D.",
            "",
            "## Gate",
            "",
            "- If controller gains collapse to ordinary blocking, verdict becomes `ENGINEERING ONLY`.",
            "- If uncertainty cannot survive the controller seam, verdict becomes `BLOCK LEVEL 2B RESEARCH`.",
            "- Otherwise the only allowed build target is the controller seam in problem class `L`.",
        ]
    ) + "\n"


def _capability_matrix() -> dict[str, Any]:
    return {
        "schema_version": LEVEL2B0_SCHEMA_VERSION,
        "generated_on": LEVEL2B0_DATE,
        "problem_classes": PROBLEM_CLASSES,
        "requirement_matrix": REQUIREMENT_MATRIX,
    }


def _verdicts() -> dict[str, Any]:
    return {
        "schema_version": LEVEL2B0_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL2B0_CHECKPOINT_COMMIT,
        "overall_verdict": "BUILD",
        "overall_interpretation": "Only the cross-mechanism controller seam survives; native matchers and trackers should be adopted or wrapped.",
        "component_verdicts": {
            row["problem_class"]: {
                "name": row["name"],
                "verdict": row["verdict"],
                "mismatch": row["mismatch"],
            }
            for row in PROBLEM_CLASSES
        },
        "next_stage_gate": "GO_BUILD_CONTROLLER",
        "disallowed_builds": [
            "custom weighted attribute matcher",
            "custom fuzzy entity resolver",
            "custom tracker",
            "custom episodic database",
            "custom spreading-activation memory",
        ],
    }


def _analysis() -> dict[str, Any]:
    return {
        "schema_version": LEVEL2B0_SCHEMA_VERSION,
        "checkpoint_commit": LEVEL2B0_CHECKPOINT_COMMIT,
        "git_status_at_start": "clean",
        "aborted_pre_audit_level2b": {
            "active_mainline_detected": False,
            "patch_saved": False,
            "note": "No active uncommitted Level 2B runtime code was detected in the worktree, so no abort patch was required.",
        },
        "bcf_invoked": False,
        "level2a_artifacts_modified": False,
        "surviving_research_seam": "External context controls resolver selection, blocking policy, and compute budget across heterogeneous native systems while preserving uncertainty and non-commit authority.",
        "research_risk": "High overlap with ordinary blocking/routing; future experiments must isolate controller benefit from standard ER heuristics.",
        "exact_next_experiment": {
            "native_matcher": "Keep matcher fixed.",
            "compare": [
                "standard blocking",
                "context-generated blocking",
                "context-generated blocking plus safe global fallback",
                "oracle blocking ceiling",
                "optional MAP/VSA blocker only for genuinely distributed cues",
            ],
            "freeze": [
                "no custom matcher",
                "no custom tracker",
                "indexed belief projection remains explicit",
            ],
        },
        "recommended_status": "GO_BUILD_CONTROLLER",
    }


def write_level2b0_artifacts(root: Path) -> dict[str, Any]:
    docs_dir = root / "docs"
    results_dir = root / "results" / "level2b0"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "LEVEL2B0_PRIOR_ART_MATRIX.md").write_text(
        build_prior_art_matrix_markdown(),
        encoding="utf-8",
    )
    (docs_dir / "LEVEL2B0_ARCHITECTURE_OVERLAP.md").write_text(
        build_architecture_overlap_markdown(),
        encoding="utf-8",
    )
    (docs_dir / "LEVEL2B0_RESEARCH_SEAM.md").write_text(
        build_research_seam_markdown(),
        encoding="utf-8",
    )

    payloads = {
        "dependency_audit.json": {
            "schema_version": LEVEL2B0_SCHEMA_VERSION,
            "generated_on": LEVEL2B0_DATE,
            "libraries": LIBRARY_AUDIT,
        },
        "capability_matrix.json": _capability_matrix(),
        "smoke_results.json": {
            "schema_version": LEVEL2B0_SCHEMA_VERSION,
            "generated_on": LEVEL2B0_DATE,
            **SMOKE_RESULTS,
        },
        "verdicts.json": _verdicts(),
        "analysis.json": _analysis(),
    }
    for file_name, payload in payloads.items():
        (results_dir / file_name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return payloads
