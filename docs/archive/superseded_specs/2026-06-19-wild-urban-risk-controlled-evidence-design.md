# Wild-Urban Risk-Controlled Evidence Design

## Core Direction

The project is reframed as a 2 x 2 risk-controlled evidence framework for felid Re-ID:

- Environment axis: wild CzechLynx vs urban/peri-urban bobcat.
- Evidence axis: high-confidence Re-ID evidence vs low-evidence stress cases.

The goal is not to simply remove bad images. The goal is to estimate whether each image or candidate pair should be admitted, downweighted, routed to review, or retained only for stress testing.

## Four Evidence Quadrants

| Environment | High-confidence evidence | Low-evidence stress cases |
| --- | --- | --- |
| Wild CzechLynx | Core known-ID training and retrieval evaluation | Wild evidence-failure and false-candidate stress testing |
| Urban bobcat | Urban evidence-structure comparison and transferable evidence screening | Urban evidence-risk, background interference, occlusion, night/modified-scene stress testing |

## Dataset Roles

Every image should receive an explicit role. No sample should disappear without a recorded reason.

- `core_training`: high-confidence evidence, suitable for training or retrieval experiments.
- `retrieval_evaluation`: suitable for evaluation, especially known-ID CzechLynx comparisons.
- `stress_test_low_evidence`: weak, ambiguous, occluded, blurred, small, or poorly comparable evidence retained for risk analysis.
- `manual_audit_calibration`: uncertain samples reserved for human review and threshold calibration.
- `excluded_non_target_or_duplicate`: unusable because it is non-target, duplicate, corrupt, or outside scope.

## Data Targets

The project should aim for:

- CzechLynx high-confidence set: 3000 images if enough known-ID and visually admissible images are available.
- Bobcat high-confidence set: 3000 images if enough urban/peri-urban bobcat candidates can be sourced and screened.
- CzechLynx low-evidence stress set: retained separately from the high-confidence training set.
- Bobcat low-evidence stress set: retained separately from the high-confidence comparison set.

The low-evidence sets are not failures. They are required for showing that the model controls evidence risk instead of cherry-picking clean images.

## Risk-Control Objective

The mathematical decision problem is:

```text
maximize usable evidence coverage
subject to estimated evidence risk <= tau
```

For pair-level retrieval:

```text
select or weight candidate pairs
to maximize expected evidence utility
while controlling false-comparison and contamination risk
```

## Main Claims Allowed

Allowed:

- PF-ERI separates training-eligible evidence from low-evidence stress cases.
- Urban and wild sources differ in evidence availability, comparability, and risk structure.
- Risk-controlled admission can improve review/retrieval reliability compared with raw descriptor ranking, random filtering, or quality-only filtering.
- Low-evidence cases reveal where Re-ID systems are likely to generate unreliable candidate comparisons.

Not allowed unless additional labels support it:

- Claiming urban bobcat individual Re-ID accuracy without verified individual IDs or audited same/different pair labels.
- Claiming that removing all hard images alone proves model improvement.
- Treating low-evidence images as useless; they are stress-test evidence.

## Implementation Standard

Before any new final dataset is declared, the project must report:

- Candidate pool size.
- Number admitted to high-confidence set.
- Number routed to stress set.
- Number requiring manual audit.
- Exclusion reasons.
- Environment split.
- Evidence-role split.
- Whether individual IDs are known, inferred, or unavailable.

The final design standard is:

```text
urban/wild evidence shift -> image-level admission risk -> pair-level comparability risk -> retrieval/review contamination
```
