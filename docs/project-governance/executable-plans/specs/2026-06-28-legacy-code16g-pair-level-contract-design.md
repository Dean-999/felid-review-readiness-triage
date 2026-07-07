# legacy-code16g Pair-Level Evidence Contract Design

Date: 2026-06-28

## Decision

legacy-code16g is a pair-level evidence-table contract and CzechLynx known-ID prototype, not the final calibrated review-router training phase.

The corrected phase boundary is:

```text
legacy-code16e full scoring
-> result acceptance
-> legacy-code16f soft eligibility and constrained selection
-> manual audit calibration
-> final 3000 freeze
-> legacy-code16g pair-level contract and CzechLynx prototype
-> legacy-code16h calibrated review-router modeling
```

legacy-code16g may build deterministic tables, audits, controls, and a CzechLynx-only validation-ready prototype. It must not claim a final model, Bobcat identity accuracy, or automatic identity assignment.

## Why This Matches The Active Plan

The active project line is:

```text
strong descriptor retrieval
-> PF-ERI pair-level evidence utility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

legacy-code16e and legacy-code16f prepare image-level and candidate-level evidence foundations. They do not freeze the final scientific dataset alone. Project rules say individual Re-ID is a pairwise evidence problem, so the next defensible modeling unit is a pair-level table that connects image evidence to candidate comparison risk.

legacy-code15 showed that calibrated nonlinear candidate/ranker features contain signal beyond descriptor-only baselines, but also that hand-written gates and simple top-k improvements are not enough for the final claim. legacy-code16g therefore prepares the data contract, controls, and split discipline needed before legacy-code16h model training.

## Scope

### In Scope

- Define a stable pair-level schema for CzechLynx and Bobcat.
- Build a CzechLynx known-ID prototype table plan.
- Preserve descriptor-only, quality-only, and random same-size controls.
- Preserve laterality, source-tier, duplicate, near-duplicate, and leakage-pressure diagnostics.
- Separate image-level evidence, pair-level comparability, descriptor support, descriptor-evidence conflict, labels, and review actions.
- Mark Bobcat outputs as transfer-stress and review-readiness only unless verified labels or audited same/different pairs exist.
- Define acceptance gates for moving from legacy-code16g to legacy-code16h.

### Out Of Scope

- Training a final calibrated review-router.
- Training a new Re-ID descriptor.
- Metric learning or projection-head training.
- Bobcat identity accuracy, mAP, hit@k, or false-match accuracy without labels.
- Freezing final 3000 before manual audit calibration.
- Weakening high-confidence evidence definitions to fill target counts.

## legacy-code16g Components

### legacy-code16g-A: Pair Feature Contract

Produce a machine-readable schema and a deterministic builder interface for pair-level rows.

Required conceptual columns:

```text
pair_id
dataset_role
species_context
query_image_id
candidate_image_id
query_source_tier
candidate_source_tier
query_legacy-code16f_tier
candidate_legacy-code16f_tier
query_evidence_band
candidate_evidence_band
pair_evidence_band
query_load_success
candidate_load_success
query_iqa_score
candidate_iqa_score
weakest_iqa_score
query_side_probability
candidate_side_probability
side_compatibility
laterality_relation
query_pose_completeness
candidate_pose_completeness
weakest_pose_completeness
descriptor_similarity
descriptor_rank
descriptor_margin
reciprocal_rank_flag
descriptor_support_band
visual_support_band
descriptor_evidence_conflict_flag
duplicate_or_near_duplicate_flag
source_leakage_pressure_flag
manual_audit_status
review_action_label
same_identity_label
label_source
label_allowed_for_modeling
split_group
```

Column groups must remain separable:

```text
image_evidence_features
pair_comparability_features
descriptor_features
conflict_features
control_features
label_fields
audit_fields
split_fields
```

This separation prevents PF-ERI from becoming a single opaque hybrid score and preserves the paper claim boundary.

### legacy-code16g-B: CzechLynx Known-ID Prototype

Build a CzechLynx pair table from legacy-code16f-selected candidates plus designated low-evidence stress rows when available.

The CzechLynx prototype may use known identity labels for validation only:

```text
same_identity_label = true if query and candidate share known CzechLynx identity
same_identity_label = false if query and candidate have different known CzechLynx identities
label_source = czechlynx_known_id
label_allowed_for_modeling = true
```

Required outputs:

```text
outputs/legacy-code16/legacy-code16g_pair_contract/legacy-code16g_pair_feature_schema.json
outputs/legacy-code16/legacy-code16g_czechlynx_pair_prototype/legacy-code16g_czechlynx_pair_table.csv
outputs/legacy-code16/legacy-code16g_czechlynx_pair_prototype/legacy-code16g_czechlynx_pair_audit.json
outputs/legacy-code16/legacy-code16g_czechlynx_pair_prototype/legacy-code16g_czechlynx_control_summary.csv
outputs/legacy-code16/legacy-code16g_czechlynx_pair_prototype/legacy-code16g_czechlynx_split_summary.csv
```

Required controls:

```text
descriptor_only
quality_only
random_same_size
legacy-code16f_selected
low_evidence_stress
```

Required split discipline:

```text
query-level split
identity-aware split
no random image-row split
duplicate and near-duplicate exclusion from clean validation
source/leakage-pressure flags retained for analysis
```

### legacy-code16g-C: Bobcat Transfer-Stress Receiver

After Bobcat legacy-code16e and legacy-code16f are complete, build a Bobcat pair table using the same schema.

Bobcat label rules:

```text
same_identity_label = empty unless verified identity labels or audited same/different pair labels exist
label_source = none, verified_bobcat_id, or manual_pair_audit
label_allowed_for_modeling = false unless label_source supports identity or pair-comparison validation
```

Bobcat outputs may support:

```text
review-readiness pressure
pair comparability pressure
descriptor-evidence conflict frequency
defer/species-level-only/non-comparable pressure
source-tier shift
wild-to-urban evidence-risk shift
```

Bobcat outputs must not support:

```text
identity accuracy
hit@k
mAP
false-match accuracy
population estimation
automatic identity assignment
```

## Acceptance Gates Before legacy-code16h

legacy-code16h calibrated review-router modeling may start only after these gates pass:

1. legacy-code16g schema is stable and versioned.
2. CzechLynx pair table passes audit for required columns, unique pair IDs, valid labels, and no split leakage.
3. Descriptor-only, quality-only, and random same-size controls are available.
4. CzechLynx validation splits are query-level and identity-aware.
5. Bobcat table is explicitly marked as transfer-stress unless verified labels exist.
6. Manual audit fields exist even if not all audit rows are complete.
7. Documentation states that legacy-code16g is not identity assignment and not final review-router training.

## Algorithm Basis For legacy-code16h

When legacy-code16h begins, the preferred model family should be calibrated, interpretable, and control-friendly:

```text
primary: logistic regression / monotonic constrained model / histogram gradient boosting
secondary: GAM-like additive model if available
diagnostic only: metric learning or projection heads
```

The target should not be "identity prediction" as a standalone product. The target should be pair-level review routing:

```text
accept_for_expert_review
review
defer
species_level_only
non_comparable
```

For CzechLynx, supervised validation may use known identity labels to estimate false-candidate burden and positive retention. For Bobcat, review routing may only be validated against manual audit labels unless verified individual IDs exist.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Premature model training | Keep legacy-code16g to schema, table builder, audits, and controls. |
| Bobcat overclaiming | Use transfer-stress labels only; block identity metrics without verified labels. |
| Easier-sample bias | Preserve low-evidence stress rows and random/quality controls. |
| Leakage through identity/source paths | Use identity-aware splits and retain source leakage-pressure flags. |
| PF-ERI becomes generic quality filtering | Keep pair comparability and descriptor-evidence conflict as first-class columns. |
| Final 3000 treated as frozen too early | Require manual audit calibration before final freeze language. |

## Self-Review

- The design follows the active legacy-code16 plan by keeping legacy-code16g after legacy-code16f and before legacy-code16h.
- It preserves the project claim boundary: PF-ERI is pair-level evidence reliability and review routing, not identity assignment.
- It includes required controls from the legacy-code16 strategy: descriptor-only, quality-only, random same-size, laterality/source-tier/duplicate diagnostics, and manual audit hooks.
- It separates CzechLynx known-ID validation from Bobcat transfer-stress analysis.
- It does not introduce model training code or metric-learning claims.
