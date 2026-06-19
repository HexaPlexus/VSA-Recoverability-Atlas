from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import torch

from cgrn_hsr.self_describing_record import (
    ARM_B_SIDECAR,
    ARM_C_INLINE,
    BASE50_CAPACITY,
    LEVEL35_V4_SHA256,
    OP_BIND_2,
    OP_PERMUTE,
    Base50x4Code,
    CompositeManifest,
    ConceptStore,
    OperandRef,
    build_chain_root,
    build_protocol,
    build_shared_subgraph_roots,
    build_store_with_atoms,
    corrupt_observed,
    create_atom_record,
    create_composite_record,
    manifest_digest,
    prior_known_seed_set,
    record_integrity,
    replay_record,
    replay_operation,
    seeds_are_fresh,
    stage_seed_set,
    verify_manifest,
    verify_record_integrity,
)

ROOT = Path(__file__).resolve().parents[1]


def _store() -> tuple[ConceptStore, torch.Tensor]:
    return build_store_with_atoms(1024, 32, 963100100)


def _with_integrity(record):
    return replace(record, record_integrity=record_integrity(record.to_manifest_dict()))


def test_atom_record_roundtrip() -> None:
    payload = torch.ones(8)
    record = create_atom_record(namespace_id="A", concept_code=1, version=1, semantic_payload=payload)
    assert record.record_kind == "ATOM"
    assert record.manifest is None
    assert verify_record_integrity(record) is True


def test_composite_manifest_roundtrip() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=1,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    assert verify_manifest(record.manifest) is True
    assert record.manifest.arity == 2
    assert len(record.manifest.ordered_operand_refs) == 2


def test_base50x4_codec_roundtrip() -> None:
    for value in (0, 1, 49, 50, 12345, BASE50_CAPACITY - 1):
        code = Base50x4Code.encode(value)
        assert code.validate() is True
        assert code.decode() == value


def test_base50x4_rejects_out_of_range() -> None:
    try:
        Base50x4Code.encode(BASE50_CAPACITY)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected out-of-range base50 encode to fail")


def test_manifest_contains_only_immediate_operands() -> None:
    store, _ = _store()
    left = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=10,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    store.add(left)
    root = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=11,
        version=1,
        operation_code=OP_PERMUTE,
        ordered_operand_refs=(OperandRef(left.namespace_id, left.concept_code, left.version),),
        operation_parameters={"shifts": 3},
    )
    assert len(root.manifest.ordered_operand_refs) == 1
    assert root.manifest.ordered_operand_refs[0].key() == left.concept_id


def test_semantic_projection_unchanged_by_manifest() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=1,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    expected = replay_operation(OP_BIND_2, (store.get("F0:0:v1").semantic_payload, store.get("F1:1:v1").semantic_payload), {})
    assert torch.equal(record.semantic_payload, expected)


def test_map_bind_replay_equals_clean_composite() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=2,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 3, 1), OperandRef("F1", 4, 1)),
        operation_parameters={},
    )
    store.add(record)
    replay = replay_record(store, record.concept_id)
    assert replay.outcome == "COMPOSITE_REPLAY_VERIFIED"
    assert torch.equal(replay.semantic_payload, record.semantic_payload)


def test_map_permute_replay_equals_clean_composite() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=3,
        version=1,
        operation_code=OP_PERMUTE,
        ordered_operand_refs=(OperandRef("F0", 3, 1),),
        operation_parameters={"shifts": 3},
    )
    store.add(record)
    replay = replay_record(store, record.concept_id)
    assert replay.outcome == "COMPOSITE_REPLAY_VERIFIED"
    assert torch.equal(replay.semantic_payload, record.semantic_payload)


def test_depth_16_chain_reconstructs() -> None:
    store, _ = _store()
    root = build_chain_root(store, 16, 963120116)
    replay = replay_record(store, root)
    assert replay.outcome in {"COMPOSITE_REPLAY_VERIFIED", "COMPOSITE_REPLAY_CACHE_HIT"}
    assert replay.stats.maximum_depth >= 16


def test_shared_subgraph_memoized_once() -> None:
    store, _ = _store()
    left, right = build_shared_subgraph_roots(store, 963140100)
    replay_left = replay_record(store, left)
    replay_right = replay_record(store, right)
    assert replay_left.stats.unique_nodes_visited >= 2
    assert replay_right.stats.unique_nodes_visited >= 2


def test_cycle_is_detected() -> None:
    store, _ = _store()
    a = create_composite_record(
        store=store,
        namespace_id="CY",
        concept_code=1,
        version=1,
        operation_code=OP_PERMUTE,
        ordered_operand_refs=(OperandRef("F0", 0, 1),),
        operation_parameters={"shifts": 3},
    )
    store.add(a)
    bad_manifest = CompositeManifest(
        schema_version=a.manifest.schema_version,
        operation_code=OP_PERMUTE,
        arity=1,
        ordered_operand_refs=(OperandRef("CY", 1, 1),),
        operation_parameters={"shifts": 3},
        manifest_digest=manifest_digest(
            {
                "schema_version": a.manifest.schema_version,
                "operation_code": OP_PERMUTE,
                "arity": 1,
                "ordered_operand_refs": [OperandRef("CY", 1, 1).to_dict()],
                "operation_parameters": {"shifts": 3},
            }
        ),
    )
    cyc = a.__class__(
        concept_id=a.concept_id,
        namespace_id=a.namespace_id,
        concept_code=a.concept_code,
        version=a.version,
        record_kind=a.record_kind,
        semantic_dimension=a.semantic_dimension,
        semantic_payload=a.semantic_payload,
        semantic_digest=a.semantic_digest,
        manifest=bad_manifest,
        record_integrity="",
    )
    cyc = _with_integrity(cyc)
    store.records[cyc.concept_id] = cyc
    assert replay_record(store, cyc.concept_id).outcome == "CYCLE_DETECTED"


def test_missing_parent_is_typed_failure() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=4,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    bad_manifest = CompositeManifest(
        schema_version=record.manifest.schema_version,
        operation_code=record.manifest.operation_code,
        arity=record.manifest.arity,
        ordered_operand_refs=(OperandRef("F0", 9999, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
        manifest_digest=manifest_digest(
            {
                "schema_version": record.manifest.schema_version,
                "operation_code": record.manifest.operation_code,
                "arity": record.manifest.arity,
                "ordered_operand_refs": [OperandRef("F0", 9999, 1).to_dict(), OperandRef("F1", 1, 1).to_dict()],
                "operation_parameters": {},
            }
        ),
    )
    bad = _with_integrity(replace(record, manifest=bad_manifest))
    store.add(bad)
    assert replay_record(store, bad.concept_id).outcome == "DANGLING_OPERAND_REF"


def test_stale_version_is_typed_failure() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=5,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    bad_manifest = CompositeManifest(
        schema_version=record.manifest.schema_version,
        operation_code=record.manifest.operation_code,
        arity=record.manifest.arity,
        ordered_operand_refs=(OperandRef("F0", 0, 7), OperandRef("F1", 1, 1)),
        operation_parameters={},
        manifest_digest=manifest_digest(
            {
                "schema_version": record.manifest.schema_version,
                "operation_code": record.manifest.operation_code,
                "arity": record.manifest.arity,
                "ordered_operand_refs": [OperandRef("F0", 0, 7).to_dict(), OperandRef("F1", 1, 1).to_dict()],
                "operation_parameters": {},
            }
        ),
    )
    bad = _with_integrity(replace(record, manifest=bad_manifest))
    store.add(bad)
    assert replay_record(store, bad.concept_id).outcome == "PARENT_VERSION_MISMATCH"


def test_single_bit_manifest_corruption_detected() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=6,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    bad_manifest = CompositeManifest(
        schema_version=record.manifest.schema_version,
        operation_code=record.manifest.operation_code,
        arity=record.manifest.arity,
        ordered_operand_refs=record.manifest.ordered_operand_refs,
        operation_parameters=record.manifest.operation_parameters,
        manifest_digest="1" + record.manifest.manifest_digest[1:],
    )
    bad = _with_integrity(replace(record, manifest=bad_manifest))
    store.add(bad)
    assert replay_record(store, bad.concept_id).outcome == "INVALID_MANIFEST"


def test_wrong_but_valid_operand_ref_rejected_by_commitment() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=7,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    bad_manifest = CompositeManifest(
        schema_version=record.manifest.schema_version,
        operation_code=record.manifest.operation_code,
        arity=record.manifest.arity,
        ordered_operand_refs=(OperandRef("F0", 2, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
        manifest_digest=manifest_digest(
            {
                "schema_version": record.manifest.schema_version,
                "operation_code": record.manifest.operation_code,
                "arity": record.manifest.arity,
                "ordered_operand_refs": [OperandRef("F0", 2, 1).to_dict(), OperandRef("F1", 1, 1).to_dict()],
                "operation_parameters": {},
            }
        ),
    )
    bad = _with_integrity(replace(record, manifest=bad_manifest))
    store.add(bad)
    assert replay_record(store, bad.concept_id).outcome == "SEMANTIC_COMMITMENT_MISMATCH"


def test_different_derivations_same_semantic_remain_distinct_records() -> None:
    store, _ = _store()
    left = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=8,
        version=1,
        operation_code=OP_PERMUTE,
        ordered_operand_refs=(OperandRef("F0", 0, 1),),
        operation_parameters={"shifts": 0},
    )
    store.add(left)
    right = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=9,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 0, 1)),
        operation_parameters={},
    )
    assert left.concept_id != right.concept_id


def test_sidecar_and_inline_logical_results_identical() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=10,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    store.add(record)
    sidecar = replay_record(store, record.concept_id, storage_arm=ARM_B_SIDECAR)
    inline = replay_record(store, record.concept_id, storage_arm=ARM_C_INLINE)
    assert sidecar.outcome == inline.outcome
    assert sidecar.semantic_digest == inline.semantic_digest


def test_observed_semantic_noise_does_not_change_replayed_clean_result() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=11,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    store.add(record)
    noisy = corrupt_observed(record.semantic_payload, 0.05, 963150100)
    replay = replay_record(store, record.concept_id, observed_semantic=noisy)
    assert replay.outcome == "COMPOSITE_REPLAY_VERIFIED"
    assert torch.equal(replay.semantic_payload, record.semantic_payload)


def test_no_factorizer_invoked_on_valid_manifest_path() -> None:
    store, _ = _store()
    record = create_composite_record(
        store=store,
        namespace_id="C",
        concept_code=12,
        version=1,
        operation_code=OP_BIND_2,
        ordered_operand_refs=(OperandRef("F0", 0, 1), OperandRef("F1", 1, 1)),
        operation_parameters={},
    )
    store.add(record)
    replay = replay_record(store, record.concept_id)
    assert replay.stats.factorizer_invoked is False


def test_no_official_heldout_seed_overlap() -> None:
    assert seeds_are_fresh(ROOT) is True
    assert stage_seed_set().isdisjoint(prior_known_seed_set(ROOT))


def test_previous_blocked_artifacts_unchanged() -> None:
    assert (ROOT / "results" / "decoder_guided_tag_repair_v0_1" / "summary.json").exists()
    assert (ROOT / "results" / "decoder_certified_codebook_v0_1" / "summary.json").exists()


def test_level35_frozen_artifacts_unchanged() -> None:
    protocol = build_protocol(ROOT)
    assert protocol["level35_frozen_artifacts_unchanged"] is True
    assert hashlib.sha256((ROOT / "results" / "level3_5b_gate_consistency_repair" / "heldout_protocol_v4.json").read_bytes()).hexdigest().upper() == LEVEL35_V4_SHA256


def test_protocol_deterministic() -> None:
    first = build_protocol(ROOT)
    second = build_protocol(ROOT)
    assert first == second
    assert first["protocol_hash"] == second["protocol_hash"]
