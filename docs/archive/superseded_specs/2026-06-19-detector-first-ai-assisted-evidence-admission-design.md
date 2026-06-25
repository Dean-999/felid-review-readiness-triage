# Detector-First AI-Assisted Evidence Admission Design

Date: 2026-06-19

## Purpose

The strict rule-only 2x2 validation failed to reach the desired precision. The next phase will not try to hand-tune rules further. It will build a detector-first, AI-assisted evidence admission pipeline.

Target operating point:

```text
AI auto-accept precision target: >=75%
human-review routing: remaining ~25% highest-risk or uncertain cases
```

This is a practical target for moving into modeling without pretending full automation is solved.

## Core Idea

A sample should not be labeled high-confidence merely because the animal is visible. The pipeline must first estimate:

```text
animal localization -> animal size -> edge/crop risk -> side/flank comparability -> crop-level visual evidence
```

Then it routes each image into:

```text
ai_auto_high_confidence
ai_auto_low_evidence_stress
review_limited_middle
human_review_required
excluded_unreadable
```

## Hybrid Route

The pipeline uses three layers:

1. Local measurable features:
   - image dimensions;
   - animal/object crop proxy;
   - crop area fraction;
   - edge-touching risk;
   - crop blur, exposure, contrast, entropy, edge density;
   - existing weak evidence labels.

2. Calibrated manual-audit model:
   - train on the 400-image audit and 200-image strict validation audit;
   - target manual evidence tier, training eligibility, and stress eligibility;
   - use held-out evaluation to estimate precision and uncertainty.

3. Optional VLM review:
   - used only for ambiguous or disagreement cases;
   - no raw sensitive metadata;
   - not the only source of labels.

## Pretrained Detector Plan

Preferred detector stack:

```text
MegaDetector / Pytorch-Wildlife for camera-trap animal bounding boxes
```

Fallback for the first implementation:

```text
detector schema + local crop/objectness proxy
```

The fallback is allowed only as a temporary bridge. It must clearly label its detector source as proxy, not pretrained detector output.

## Decision Rule

The first implemented system should be conservative:

```text
auto_accept only when model confidence is high and risk flags are low
manual_review_required when model confidence is low, detector/crop risk is high, or model disagrees with weak labels
```

If the model cannot reach the 75% target under held-out audit evaluation, it must not auto-accept broad sets. It should increase human-review coverage instead.

## Outputs

The implementation should create:

```text
outputs/phase14/phase14_detector_first_admission/
  phase14_detector_first_training_table.csv
  phase14_detector_first_model_evaluation.json
  phase14_detector_first_candidate_scores.csv
  phase14_detector_first_auto_high_candidates.csv
  phase14_detector_first_auto_stress_candidates.csv
  phase14_detector_first_human_review_required.csv
```

## Claim Boundary

This phase is an AI-assisted evidence-routing system, not final truth. It can support:

```text
AI can reduce manual review burden by auto-routing high-confidence low-risk cases.
```

It cannot claim:

```text
all images are correctly labeled automatically
full Re-ID evidence quality is solved without manual review
```

## Success Criteria

Minimum success:

```text
held-out auto-accept precision >=75%
human-review queue is explicitly defined
all auto-accepted outputs include confidence and risk flags
```

Preferred success:

```text
auto-accept precision >=80%
coverage >=50% for at least one useful class
clear failure modes documented
```
