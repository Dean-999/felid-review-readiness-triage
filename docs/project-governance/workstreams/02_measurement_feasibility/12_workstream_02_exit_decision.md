# Workstream 02 Exit Decision

Date: 2026-07-14
Decision: `measurement_ready_with_reduced_feature_set`

## Basis for the decision

The outcome-free 160-pair measurement-feasibility pilot completed its required branches:

- Structural-oracle measurements passed their pre-specified reliability gates, but remain oracle-only and are excluded from the primary automatic model.
- Frozen SuperPoint–LightGlue–RANSAC local-match coverage completed with valid measurements for all 160 canonical pairs, zero manual rescues, and the pre-specified runtime and variation gates met. This is a feasibility result, not an identity-performance claim.
- Automatic image-quality measurement retains native pixel count, sharpness, and channel-extreme clipping. Generic COCO cat-mask coverage is excluded: its 37.0% valid-output rate failed the pre-specified 90% gate.
- The 12-pair blinded reviewer-interface dry run passed the machine static audit and independent browser audit. The completed `A001` return documented no prohibited exposure in all eight required checks. Its returned public reviewer view is byte-identical to the official v3 reviewer-visible release.

## Audit evidence

The completed external audit is archived at:

`work/pferi_v2/review/interface_dry_run/independent_browser_audit/returned_audits/2026-07-14_a001_completed/`

The raw returned ZIP SHA-256 is:

`0d16fa193502f4277e066c1f47ccc0cd6aac0b0e0e0ae3d1bb3164f9fcf63962`

The consolidated final gate record is `interface_dry_run_final_gate_audit.json` in that same directory.

## Scope and remaining boundary

This decision means only that the retained automatic variables and blinded reviewer interface are suitable to proceed to the next protocol stages. It does **not** establish Re-ID accuracy, identity discrimination, conservation deployment value, or final predictive performance. It does **not** change the project-wide status from `v2_protocol_prelock`.

Workstream 03 must now establish graph-aware development, calibration, and confirmation partitions before any real outcome review packet can be constructed. Any future packet must still pass its own packet-specific preflight and access-control checks.
