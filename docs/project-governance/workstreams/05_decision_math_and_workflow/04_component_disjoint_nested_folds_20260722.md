# Task 04: Endpoint-Component-Disjoint Nested Folds

Status: **COMPLETE — FROZEN PASS WITH DECLARED RARE-LEVEL LIMITATION**
Date: 22 July 2026
Applies to: Workstream 05 / development Task 15C

## Purpose

The formal development sample contains pairs, but pairs sharing an endpoint image are not independent. Row-random cross-validation would allow the same image to appear in both training and validation data, inflate apparent generalization, and count graph-linked observations as independent evidence. The correct resampling unit is therefore the complete transitive connected component of endpoint image IDs.

This task creates the registered five-fold outer and four-fold inner resampling structure before any development outcome is read for model comparison. It does not fit a model, calculate a performance measure, or unlock another analysis stage.

## Frozen construction

The 445 formal development pairs were joined only to the outcome-free master derivation frame. Endpoint pairs were converted into an undirected graph, and every transitive connected component was treated as indivisible. Complete components were assigned to five outer validation folds. For each outer fold, components in the remaining outer-training set were independently reassigned to four inner validation folds.

Assignment used a frozen deterministic largest-component-first greedy objective followed by deterministic improving component moves. The objective balanced pair count, component count, development sampling cells, descriptor-support category, evidence state, rank band, matcher-failure state, quality-failure state, and inclusion-probability bins. No outcome was available to the objective. A second full construction was required to reproduce the first assignment byte-for-byte.

## Graph structure

- Formal development pairs: 445.
- Unique endpoint images: 551.
- Transitive endpoint components: 116.
- Largest component: 68 pairs and 67 endpoint images.
- Outer folds: 5.
- Inner folds inside each outer-training context: 4.
- Outer assignment rows: 445.
- Nested assignment rows: 1,780, because every pair belongs to the outer-training set in four of five outer contexts.

Strict component isolation was feasible. The largest component is substantial but does not dominate an outer fold.

## Validation result

The fold gate passed:

- endpoint leakage across all five outer splits: zero;
- endpoint leakage across all twenty conditional inner splits: zero;
- components split across outer or inner folds: zero;
- outer validation sizes: 88, 88, 89, 89, and 91 pairs;
- outer ideal size: 89 pairs;
- inner validation sizes across all contexts: 88–91 pairs;
- every outer and inner validation fold contains all three descriptor-support categories;
- deterministic reconstruction: exact hash match;
- real outcome columns read: zero;
- calibration or confirmation inputs read: false;
- generated-artifact checksum verification: 8/8 PASS.

## Structural rare-level limitation

Only two development pairs have `local_match_measurement_failure=True`, and each belongs to a different component. Five-fold allocation cannot place that state in every validation fold. In some nested contexts, excluding one outer component leaves only one failure component; the inner validation fold containing that component necessarily leaves an inner-training split with no observed failure example.

This limitation cannot be repaired honestly by splitting endpoint components, duplicating rows, changing the formal sample, reading outcomes, or manufacturing synthetic failure observations. Downstream preprocessing must tolerate absent training levels using the frozen unknown/missing-level policy, and model reports must show fold-wise feature support. Performance for the rare failure state cannot be estimated reliably from the development sample alone.

## Critical interpretation

### What passed

The resampling geometry is reproducible, component-disjoint, and sufficiently pair-balanced for registered nested development comparison. It removes direct shared-image leakage and prevents row-level pseudoreplication from entering cross-validation.

### What did not pass merely because folds exist

This result says nothing about PF-ERI discrimination, calibration, Brier improvement, identity matching, conservation utility, or cross-species transfer. It also does not remove all possible dependence: different images may still share an individual animal, camera site, capture event, or acquisition condition if those identities are not available as grouping variables. Claims must remain bounded to endpoint-image disjointness.

### Remaining risks

- The selected square-root-IPW route from Task 15B remains near its synthetic calibration threshold and must now survive real development comparison.
- Component counts vary from 21 to 25 across outer folds even though pair counts are nearly equal; component-level summaries must accompany row-level metrics.
- Two matcher-failure observations cannot support a stable subgroup-performance estimate.
- Endpoint-component disjointness does not imply individual-, event-, or site-disjointness unless those identifiers are independently verified.

## Artifacts

- Fold design registry: `schemas/pferi_v2/component_disjoint_fold_design_v1.json`
- Builder and validator: `scripts/build_pferi_v2_component_disjoint_folds.py`
- Focused tests: `tests/test_build_pferi_v2_component_disjoint_folds.py`
- Frozen output: `archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/`

The output directory contains the frozen registry, endpoint-component inventory, outer assignments, conditional nested assignments, balance summary, validation audit, report, runner snapshot, and SHA256 manifest.

## Verification

- Python compilation: PASS.
- Focused tests: 5/5 PASS.
- Focused branch-aware coverage: 82%.
- Assignment validation: PASS.
- Endpoint leakage count: 0.
- Deterministic reproduction: PASS.
- Outcome columns read: 0.
- Checksums: 8/8 PASS.

## Next gate

Task 15D must freeze executable feature lineage and fold-train preprocessing before any registered model is compared. Task 15E may then use the open 445-row development outcome file, the frozen candidate registry, the conditionally selected square-root-IPW strategy, and these exact nested folds. Calibration, deployment-confirmation, and mechanism-confirmation outcomes remain locked. A `development_model_freeze_record.json` may be produced only after the later model, sensitivity, and challenger gates pass.
