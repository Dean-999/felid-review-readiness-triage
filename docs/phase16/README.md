# Phase 16: Balanced PF-ERI 2.0 Strategy

Date: 2026-06-23

Phase 16 is the next active strategy layer. It keeps PF-ERI modeling at the
center and adds data-governance and benchmark safeguards around it.

## Core Modeling Line

```text
strong descriptor retrieval
-> PF-ERI pair-level evidence utility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

## What Phase 16 Adds

Phase 16 does not replace the PF-ERI main line. It adds safeguards that make the
model harder to criticize:

1. dataset-foundation audit before core model claims;
2. laterality-aware sampling and pair audit;
3. background/site leakage-pressure diagnostics;
4. strong-model benchmark preparation;
5. optional later extensions for ecological priors, augmentation robustness, and
   captive calibration.

## Dataset Foundation Gate

The current 3000 x 4 image foundation must pass a conservative readiness audit
before it is treated as a clean training or clean comparison base. Use:

```text
python3 scripts/build_phase16_dataset_foundation_audit.py
```

Primary outputs:

```text
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_quadrant_summary.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_issue_detail.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_manual_audit_candidates.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_audit_report_cn.md
```

Interpretation rule:

```text
If high-confidence quadrants do not reach the 90% readiness target, do not
weaken the definition of high-confidence evidence. First run targeted manual
audit, then rebuild or top up only the failing evidence categories.
```

## High-Confidence Quality + Viewpoint Rescore

If high-confidence quadrants fail the foundation gate, rescore candidates with
pretrained quality and viewpoint models before rebuilding Dataset v1:

```text
python3 scripts/package_phase16_high_confidence_quality_viewpoint_rescore.py
```

Design note:

```text
docs/phase16/phase16b_high_confidence_quality_viewpoint_plan_cn.md
```

This step uses pretrained no-reference IQA and CLIP-style viewpoint scoring as
cloud-side prefilters. It does not replace manual calibration and does not prove
identity evidence by itself.

## External Clean Dataset Strategy

Curated external Re-ID datasets can help train or calibrate high-confidence
quality/viewpoint selectors, but they should not silently enter the final
wild-vs-urban comparison:

```text
docs/phase16/phase16c_external_clean_dataset_source_strategy_cn.md
```

Operating rule:

```text
Use same-domain Lynx/bobcat images for the final 3000-per-quadrant datasets
whenever possible. Use external clean Re-ID datasets mainly for selector
training, viewpoint calibration, and benchmark context.
```

## Expanded High-Confidence Candidate Pool

The high-confidence clean sets should be selected from larger same-domain pools,
not repaired only from the current 3000-image working labels:

```text
python3 scripts/package_phase16_expanded_high_confidence_candidate_pool.py
```

Design note:

```text
docs/phase16/phase16d_expanded_high_candidate_pool_cn.md
```

Current candidate counts:

```text
urban_bobcat_high_confidence: 6412 FCF bobcat candidates passing LILA MegaDetector high-geometry prefilter
wild_czechlynx_high_confidence: 39760 CzechLynx real-image candidates
```

## Active Plan

Use:

```text
docs/superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md
```

Archived Phase 14/15 design specs are preserved under `docs/archive/`, but they
are not the current roadmap.

## Claim Boundary

Phase 16 may claim that PF-ERI evaluates admissible pair evidence and routes
candidate comparisons under risk constraints. It must not claim automatic
identity assignment, bobcat identity accuracy without verified labels,
urbanization causality, or a new Re-ID descriptor.
