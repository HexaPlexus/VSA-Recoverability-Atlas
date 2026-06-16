# Level 3.5b Protocol Repair and Re-Freeze

- Old blocked checkpoint: `8fcef7e7123c4d5dd4d401a4521b51ca85af8e1d`
- Protocol repair verdict: `PROTOCOL_REPAIRED_AND_REFROZEN`
- Ready status: `READY_FOR_LEVEL_3_5B_HELDOUT_V2`
- Protocol v1 hash: `1166adeb42d72c270ee777aef1d6046fcb3cbe168822cc63383518ad955c2d29`
- Protocol v2 hash: `649a51d389967f9930f432f608a99b387f3bde96ba97e598b3f2df00ee1eadbf`

## Why Repair Was Required

- P1 `HELDOUT_SEED_LEAKAGE`: held-out ranges overlapped development ranges.
- P2 `TRIAL_COUNT_SEED_COUNT_MISMATCH`: protocol requested 64 trials but provided 16 seeds.
- P3 `MAP_CONFIG_UNDERSPECIFICATION`: held-out MAP config did not fully identify the richer frozen development arm.

> This is an administrative pre-execution repair, not a second chance after observing held-out outcomes.

## Lawfulness

- Zero held-out trial rows existed before repair.
- The blocked held-out attempt remains immutable evidence.
- Outcome-facing scientific choices were preserved; only protocol integrity defects were repaired.

## Immutable Scientific Fields

- Binary methods, cells, corruption points, BCH configurations, metrics and claim limits were preserved.
- MAP methods, cells, corruption points, metrics and claim limits were preserved.
- BCF remains blocked and unexecuted.
- Development transition points remain referenced by hash.

## What Changed

- Fresh non-overlapping held-out seed ranges were allocated for binary and MAP.
- Trial counts and seed counts were made consistent at 64 per binary cell and 64 per MAP cell.
- Complete MAP arm records and hashes were added so future held-out execution can validate the exact frozen arms.

## Remaining Claim Limits

- No substantive noise-frontier claim is authorized at this stage.
- No held-out benchmark execution occurred.
- No production promotion is authorized.
