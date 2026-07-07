# legacy-code18 Algorithm And Modeling Readiness Report

Date: 2026-07-06

## Executive Decision

The project is ready to enter the algorithm/modeling phase, with a strict scope:

```text
Proceed to PF-ERI pair-level evidence-governance modeling.
Do not proceed to descriptor training, automatic identity recognition, or Bobcat identity-accuracy modeling.
```

The evidence base is now strong enough to justify building an explicit
algorithmic layer that predicts pair-level reviewability / evidential
admissibility after strong descriptor retrieval.

The strongest supported claim is:

```text
PF-ERI is a post-retrieval pair-level evidence governance layer.
It predicts human uncertain/not-ready reviewability after descriptor family,
descriptor similarity, and known same/different identity stratum are controlled.
```

## Current Evidence State

### Strong Descriptor Context

legacy-code18 has external strong descriptor artifacts for:

```text
megadescriptor_l_384
dinov2_vitl14
```

This removes the weak-baseline vulnerability. PF-ERI is no longer being tested
only against a local lightweight descriptor.

### legacy-code18k Status

legacy-code18k originally asked whether the highest-goal claim was supported under
full controls. Its gate was:

```text
NEEDS_MORE_EVIDENCE
```

The reason was not image quality and not reviewer instability. The key concern
was whether PF-ERI was acting as a proxy for descriptor similarity.

legacy-code18l and legacy-code18m were built specifically to address this.

### legacy-code18l Descriptor-Controlled Result

legacy-code18l matched high- and low-admissibility pairs under high descriptor
similarity.

Result:

```text
MegaDescriptor: strong positive result
DINOv2: directional but weak under majority vote
Pooled: positive
```

This showed that PF-ERI admissibility was not simply image quality, but legacy-code18l
still had an identity-composition concern: high PF-ERI had more same-ID pairs,
and low PF-ERI had more different-ID pairs.

### legacy-code18m Identity-Balanced Result

legacy-code18m directly fixed the legacy-code18l identity-confounding issue by balancing:

```text
same-ID + high PF-ERI admissibility
same-ID + low PF-ERI admissibility
different-ID + high PF-ERI admissibility
different-ID + low PF-ERI admissibility
```

Current status:

```text
BLIND_CONFIRMED_IDENTITY_BALANCED_PASS
```

Majority-vote effects:

| Descriptor | Identity stratum | High uncertain/not-ready | Low uncertain/not-ready | Difference | 95% CI |
| --- | --- | ---: | ---: | ---: | --- |
| MegaDescriptor | same-ID | 0.020 | 0.180 | +0.160 | [+0.060, +0.280] |
| MegaDescriptor | different-ID | 0.200 | 0.640 | +0.440 | [+0.260, +0.620] |
| DINOv2 | same-ID | 0.020 | 0.400 | +0.380 | [+0.240, +0.520] |
| DINOv2 | different-ID | 0.300 | 0.740 | +0.440 | [+0.260, +0.600] |

All four descriptor x identity-stratum checks pass with positive confidence
interval lower bounds.

Reviewer agreement is adequate for modeling entry:

```text
minimum binary pairwise kappa = 0.423
```

## Readiness Judgment

### Ready

The project is ready to build:

1. a supervised PF-ERI pair-level reviewability model;
2. an evidence-only / descriptor-controlled PF-ERI score;
3. a calibrated review-router policy;
4. threshold curves for review budget, positive retention, and defer routing;
5. model cards and claim gates tied to CzechLynx known-ID validation.

### Not Ready

The project is not ready to claim:

1. PF-ERI is a new descriptor;
2. PF-ERI automatically identifies individual animals;
3. PF-ERI improves universal top-k / mAP across all settings;
4. Bobcat identity accuracy;

The project is now ready to claim blind-confirmed legacy-code18m status because the
blind artifacts exist and the legacy-code18m claim gate has PASS status.

## Recommended Algorithm Phase

The next phase should be:

```text
legacy-code19: PF-ERI Pair-Level Evidence Governance Model
```

Primary endpoint:

```text
human reviewability / evidential admissibility
```

Secondary utility endpoints:

```text
same-ID candidate retention at fixed review budget
false-candidate burden at fixed same-ID retention
defer / uncertain concentration
quality-control sensitivity
descriptor-specific transfer stability
```

## Modeling Target

The first model should predict:

```text
review_ready vs uncertain/not_ready
```

using pair-level evidence features:

```text
weakest_image_quality_score
pair_geometry_score
pair_size_compatibility_score
pair_aspect_compatibility_score
descriptor_evidence_conflict_score
pf_eri_admissibility_score
candidate_rank_descriptor
descriptor_similarity_percentile as an active control, not the innovation
descriptor_name
identity-stratum only for evaluation/sensitivity, not as an input feature
```

The model must not use:

```text
same_identity_known_id as a feature
identity_label as a feature
Bobcat identity labels unless independently verified
```

## First Modeling Architecture

Use a conservative, auditable model stack before any complex model:

```text
baseline_0: descriptor similarity only
baseline_1: image quality only
baseline_2: descriptor similarity + image quality
model_1: PF-ERI evidence-only logistic model
model_2: descriptor similarity + quality + PF-ERI evidence model
model_3: calibrated review-router thresholds using model_2 score
```

Recommended first model:

```text
regularized logistic regression or calibrated shallow tree ensemble
```

Reason:

```text
The project's current scientific risk is overclaiming, not underfitting.
The first algorithm must be transparent, reproducible, and easy to audit.
```

## Required Split Discipline

All modeling must use:

```text
query_image_id clustered split or bootstrap
descriptor-specific evaluation
pooled evaluation
unordered-pair dedup sensitivity
identity-cluster sensitivity if available
```

Training/selection must never tune thresholds on the same rows used for final
claim reporting.

Minimum split structure:

```text
calibration queries -> fit model / thresholds
evaluation queries -> report locked metrics
```

## Success Criteria For legacy-code19

legacy-code19 can claim algorithm readiness only if:

1. PF-ERI model improves reviewability prediction over descriptor similarity +
   quality controls.
2. The effect is stable for MegaDescriptor and DINOv2 separately.
3. The effect survives query-cluster bootstrap.
4. Same-ID candidate retention is not materially sacrificed.
5. False-candidate burden or uncertain/defer concentration improves at fixed
   retention or fixed review budget.
6. The model remains interpretable enough to explain evidence governance.
7. Blind legacy-code18m confirmation is completed before the strongest manuscript
   wording is used.

## Immediate Next Implementation Plan

1. Build `scripts/build_legacy-code19_pair_level_modeling_dataset.py`.
   - Inputs: legacy-code18m majority labels, legacy-code18m packet, legacy-code18d strong
     PF-ERI features.
   - Output: one row per reviewed pair with labels, descriptor controls,
     evidence features, and split metadata.

2. Build `scripts/train_legacy-code19_reviewability_model.py`.
   - Fit descriptor-only, quality-only, descriptor+quality, PF-ERI-only, and
     full PF-ERI models.
   - Use deterministic splits and fixed seed.

3. Build `scripts/evaluate_legacy-code19_review_router.py`.
   - Report AUC, average precision, calibration, fixed-budget utility,
     fixed-retention false burden, and defer concentration.

4. Add tests to `tests/test_legacy-code18_pipeline.py` or create
   `tests/test_legacy-code19_pair_level_modeling.py`.

5. Write `docs/legacy-code19/README.md` and a model-card style report.

## Final Recommendation

Proceed to algorithm/modeling now.

But the algorithm phase must be framed as:

```text
PF-ERI pair-level reviewability and evidence-governance modeling
```

not as:

```text
identity recognition
descriptor replacement
universal ranking improvement
Bobcat identity validation
```

This is the right moment to move from validation-only analysis into a real,
auditable algorithm layer.
