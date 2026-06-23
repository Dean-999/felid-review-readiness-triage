# 2x2 Risk-Controlled Wild-Urban Evidence Design

Date: 2026-06-19

## Purpose

This project now uses a two-axis evidence-risk design:

```text
environment axis: wild vs urban/peri-urban
evidence axis: high-confidence evidence vs low-evidence stress cases
```

The goal is not to remove difficult images from the project. The goal is to route each image or pair into the role where it can support the strongest valid claim.

High-confidence samples support training, retrieval evaluation, and clean wild-vs-urban evidence comparison. Low-evidence samples support risk-control, stress testing, contamination analysis, and evidence-failure modeling.

## Core Design

The project should maintain four explicit evidence quadrants:

| Context | High-confidence evidence | Low-evidence stress cases |
| --- | --- | --- |
| Wild CzechLynx | Known-ID training and retrieval validation | Wild camera-trap evidence-failure and false-candidate stress testing |
| Urban/peri-urban bobcat | Urban evidence-structure comparison and review-readiness modeling | Urban background, occlusion, night/IR, blur, and human-modified-scene stress testing |

This design upgrades the project from image filtering to risk-controlled evidence admission.

The main modeling question becomes:

```text
How does environment-mediated evidence degradation affect felid Re-ID reliability,
and can a risk-controlled evidence admission model preserve usable identity evidence
while isolating low-evidence stress cases?
```

## Data Roles

Each sample must be assigned an explicit role:

```text
core_training
retrieval_evaluation
wild_urban_clean_comparison
low_evidence_stress_test
manual_audit_calibration
excluded_non_felid_or_duplicate
```

The same image may support more than one compatible role, but low-evidence samples must not silently enter the core training set.

## Training Set Rule

CzechLynx and bobcat should each have a target high-confidence set of 3,000 images for the main wild-vs-urban comparison.

Eligibility should prioritize:

- clear or moderately clear body evidence;
- visible flank, side, or other individual-relevant body region;
- usable pattern or morphology evidence;
- low-to-moderate occlusion;
- low-to-moderate blur;
- valid species label;
- no obvious duplicate or unusable crop;
- for CzechLynx, preservation of identity balance and enough images per individual for pair construction.

Low-confidence or non-comparable images should be retained outside the clean training set as stress-test evidence.

## Risk-Control Rule

PF-ERI should be framed as an evidence admission and routing system:

```text
admit to clean training / retrieval
downweight
route to manual review
route to low-evidence stress set
exclude only with recorded reason
```

The mathematical objective is:

```text
maximize usable evidence coverage
subject to estimated evidence risk <= tau
```

Equivalent pair-level framing:

```text
select image/pair set S
to maximize expected evidence utility
while controlling false-comparison or training-contamination risk
```

## Why Low-Evidence Samples Stay

Low-evidence samples are scientifically useful because they test whether the system can identify and isolate evidence that would otherwise contaminate Re-ID. They should be used for:

- risk-coverage curves;
- review burden estimation;
- descriptor-evidence conflict enrichment;
- false-candidate pressure analysis in CzechLynx known-ID data;
- urban/wild evidence-shift analysis;
- calibration of manual-review thresholds;
- showing why high-confidence training admission is necessary.

Removing them entirely would make the project easier but weaker. Keeping them as a stress layer makes the risk-control contribution testable.

## Claim Boundaries

CzechLynx can support known-ID retrieval and pair-level false-candidate validation.

Bobcat can support urban/peri-urban evidence distribution, review-readiness, comparability, and stress testing. Bobcat cannot support true urban Re-ID identity accuracy unless verified individual labels or audited same/different pair labels are added.

The project must not claim:

- that high-confidence filtering alone is the contribution;
- that urban bobcat identity validation has been completed without verified IDs;
- that low-evidence images are useless;
- that improvements are due only to image quality rather than evidence utility and risk routing.

## Evaluation Structure

Report results at three levels:

1. Full candidate pool:
   shows the real evidence-risk distribution before admission.

2. Clean high-confidence set:
   supports training, retrieval, and controlled wild-vs-urban comparison.

3. Low-evidence stress set:
   tests whether PF-ERI identifies high-risk evidence and prevents contamination.

Required controls:

- random same-size selection;
- quality-only selection;
- matched coverage controls;
- for CzechLynx, held-out identity evaluation where applicable;
- for bobcat, review-readiness or pair-audit controls unless verified IDs exist.

## Implementation Implications

Future data-building scripts should produce explicit columns:

```text
environment_context
evidence_tier
evidence_role
training_eligible
stress_test_eligible
manual_audit_needed
exclusion_reason
risk_control_notes
```

Recommended evidence tiers:

```text
high_confidence
medium_reviewable
low_evidence_stress
excluded
```

Recommended environments:

```text
wild
urban_periurban
captivity_adjacent
unknown_context
```

## Success Standard

The design succeeds if the final analysis can show:

1. high-confidence evidence supports cleaner and more reliable Re-ID training or retrieval evaluation;
2. low-evidence samples produce measurable risk, review burden, or descriptor-evidence conflict;
3. PF-ERI separates usable evidence from stress evidence better than random or quality-only baselines;
4. wild and urban/peri-urban contexts differ not merely in image quality, but in the way image evidence propagates into pair comparability and retrieval/review risk.

This is the project rule going forward:

```text
Do not discard uncertainty; route it.
Do not train on low-evidence noise; stress-test with it.
Do not compare only clean data; report full-pool, clean-set, and stress-set behavior.
```
