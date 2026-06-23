# Phase 13 Interpretation and Next Upgrade

Date: 2026-06-17

## Short Judgment

Phase 13 is a good update, not a bad update.

It is not a simple breakthrough claim. It is a model-upgrade result with a clear boundary:

```text
Learned PF-ERI is clearly better than fixed PF-ERI.
Learned PF-ERI is not consistently better than learned quality-control.
```

This means the project should not retreat, but it also should not overclaim that PF-ERI reranking alone is the final contribution. The correct next move is to use PF-ERI where it is theoretically strongest: reliability-aware pair weighting, unreliable hard-negative control, and descriptor-evidence conflict handling during metric learning.

## What Is Positive

Against fixed PF-ERI candidate utility, learned PF-ERI gives consistent held-out improvement:

- MegaDescriptor: learned PF-ERI full improves candidate average precision by about 0.112 and reduces eligible false top-1 risk by about 0.013.
- ResNet50: learned PF-ERI full improves candidate average precision by about 0.206 and reduces eligible false top-1 risk by about 0.011.
- Monotonic nonlinear PF-ERI also beats fixed PF-ERI on both descriptors.

This supports a real upgrade:

```text
Fixed hand-written evidence utility is underpowered.
Held-out learned candidate utility extracts more signal from the same PF-ERI feature family.
```

## What Is Mixed

Against learned quality-control, the result is mixed:

- MegaDescriptor: learned PF-ERI full is slightly worse than learned quality-control on eligible top-1 risk and candidate average precision.
- ResNet50: learned PF-ERI full is better on candidate average precision, but its eligible top-1 risk gain over quality-control is small and uncertain.

This does not invalidate PF-ERI. It shows that a substantial part of the current PF-ERI reranking signal overlaps with image quality and visual utility proxies.

## Phase 13B Boundary Diagnosis

Phase 13B compares query-level rescues and harms.

Learned PF-ERI full vs fixed PF-ERI:

- MegaDescriptor: more rescues than harms, net top-1 gain about 0.012.
- ResNet50: more rescues than harms, net top-1 gain about 0.010.

Learned PF-ERI full vs learned quality-control:

- MegaDescriptor: fewer rescues than harms, net top-1 gain about -0.004.
- ResNet50: slightly more rescues than harms, net top-1 gain about 0.002.

Important feature contrast:

- For MegaDescriptor, PF-ERI rescues have higher pair reliability, higher visual evidence, better image quality, and lower descriptor-evidence conflict than harms.
- For ResNet50, PF-ERI rescues are strongly driven by descriptor support and candidate AP improves, but the conflict pattern is less clean.

Interpretation:

```text
PF-ERI has real evidence signal, but the current reranking endpoint lets quality-control absorb much of that signal.
The sharper use case is not generic reranking; it is controlling which positive and negative pairs should influence learning.
```

## External Method Direction

The relevant external method pattern is consistent with this diagnosis:

- Hard negatives can improve metric learning only when false or unreliable negatives are controlled.
- Noisy or low-reliability samples are commonly handled through weighting, filtering, confidence calibration, or robust objectives.
- Animal Re-ID work increasingly relies on strong fixed baselines such as MegaDescriptor and careful split/control design, so a new contribution needs to beat quality and random controls, not only raw retrieval.

This supports moving from:

```text
PF-ERI as a reranking score
```

to:

```text
PF-ERI as a reliability-aware pair-learning control signal
```

## Next Upgrade: Phase 13C / RQ4

Phase 13C should implement a training-control table and experimental plan for RQ4.

Core design:

1. Use identities with at least two images for positive-pair training.
2. Keep singleton identities as gallery noise, distractors, and hard-negative context, not as positive-pair sources.
3. Weight positive pairs by admissible pair evidence, not just image quality.
4. Down-weight high-similarity low-admissibility negatives to reduce unsafe hard-negative learning.
5. Keep matched controls:
   - descriptor-only learning;
   - random matched pairs;
   - quality-control weighted pairs;
   - PF-ERI weighted pairs;
   - PF-ERI plus conflict-aware negative control.

Primary evidence needed:

- Does PF-ERI weighting improve held-out retrieval beyond quality weighting?
- Does it reduce false-candidate burden or hard-negative exposure?
- Does it stabilize training across splits?
- Does it improve the risk-coverage frontier even if raw top-1 gain is small?

## Claim Boundary

The current defensible claim after Phase 13 is:

```text
PF-ERI features contain learnable evidence-utility signal and clearly improve over fixed hand-written utility. However, reranking alone does not yet establish PF-ERI as independent of learned quality-control. The strongest next test is reliability-aware metric learning, where PF-ERI can control admissible positives and unsafe hard negatives rather than merely reorder descriptor candidates.
```

This is an upgrade path, not a downgrade.

## Phase 13C Status

Phase 13C has now built the RQ4 training-control manifest.

Key outputs:

- `outputs/czechlynx/phase13/rq4_training_control_manifest/phase13c_rq4_pair_training_control_manifest.csv`
- `outputs/czechlynx/phase13/rq4_training_control_manifest/phase13c_rq4_image_training_roles.csv`
- `outputs/czechlynx/phase13/rq4_training_control_manifest/phase13c_rq4_control_summary.csv`
- `outputs/czechlynx/phase13/rq4_training_control_manifest/phase13c_rq4_policy_comparison_summary.csv`

Audit:

```text
Phase 13C RQ4 training-control audit: PASS=32 FAIL=0
```

Important design results:

- 1000 images are represented.
- 909 images can contribute positive pairs.
- 91 singleton images are retained only as distractors / negative context and are not used as positive-pair sources.
- Evaluation split MegaDescriptor averages about 293 eligible positive candidate pairs and about 485 unsafe hard negatives per split.
- Evaluation split ResNet50 averages about 253 eligible positive candidate pairs and about 438 unsafe hard negatives per split.
- PF-ERI positive weights are higher than quality-only positive weights on average, because they include pair reliability, visual evidence, margin confidence, and conflict penalty.
- PF-ERI conflict-aware negative control reduces unsafe hard-negative weight from 1.0 to 0.35 while leaving ordinary negatives unchanged.

Policy set now prepared for RQ4:

```text
descriptor_only
random_control
quality_control
pf_eri_positive
pf_eri_conflict_aware
```

This turns the Phase 13 boundary finding into an executable RQ4 design. The next empirical test should be whether `pf_eri_positive` or `pf_eri_conflict_aware` improves held-out retrieval, false-candidate burden, training stability, or risk-coverage relative to `quality_control` and `random_control`.
