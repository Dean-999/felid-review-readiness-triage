# legacy-code18i Evidence Confidence: Self-Grill and Literature Context

Date: 2026-07-02

## Bottom Line

The legacy-code18i result is **scientifically persuasive as targeted, exploratory
evidence**, but it is not yet a final validation study.

Recommended confidence statement:

```text
Moderate-to-strong evidence supports the claim that PF-ERI captures a
pair-level reviewability signal after strong descriptor retrieval.
```

Do not state:

```text
PF-ERI is fully validated.
PF-ERI automatically identifies individuals.
PF-ERI has Bobcat identity accuracy.
The human audit confirmed low-evidence/non-comparable mechanisms.
```

## Literature Context

The literature supports three framing choices we made:

1. Strong descriptors are an appropriate stress test.
   WildlifeDatasets/MegaDescriptor is explicitly presented as a broad animal
   re-identification foundation model and benchmark framework, not a weak
   baseline. DINOv2 is a strong general-purpose self-supervised visual feature
   model. This makes our test harder than comparing PF-ERI only against a weak
   local descriptor.

2. Re-identification systems are retrieval/decision aids, not replacements for
   evidence governance.
   Wildlife re-ID toolkits and Wildbook-style workflows are built around
   detection, retrieval, similarity, and downstream review. Our contribution
   fits as a post-retrieval review-readiness layer.

3. Human visual review has observer uncertainty and image-dependent failure
   modes.
   Camera-trap and felid-identification literature explicitly discusses
   observer variation, uncertainty, image quality, phenotype distinctiveness,
   and review difficulty. Therefore a pair-level reviewability layer is a
   scientifically plausible target, not just a convenience feature.

Key sources consulted:

- Čermák et al., 2024, WildlifeDatasets / MegaDescriptor, WACV.
- Oquab et al., 2023/2024, DINOv2.
- Reviews and applied work on animal individual identification from visual
  data.
- Observer-variance and camera-trap annotation reliability studies.
- Large-felid individual identification review literature noting uncertainty,
  bias, and image-quality constraints.

## Self-Grill

### Q1. Are we proving identity accuracy?

Recommended answer: no.

The strongest identity-related claim is limited to CzechLynx known-ID
same/different validation. Bobcat remains unlabeled transfer/readiness only.
legacy-code18i human labels are **reviewability labels**, not identity labels.

### Q2. Are the p-values enough to call this high confidence?

Recommended answer: p-values are strong, but confidence depends on design.

The pooled contrast is large:

```text
same-ID controls: 100/100 review_ready
high-similarity false candidates: 73/100 review_ready
risk difference: +0.27
row-level bootstrap 95% CI: [+0.18, +0.36]
Fisher exact p: 1.96e-09
```

But p-values do not solve construct validity, reviewer bias, or targeted-sample
selection. This is why the claim should be "targeted evidence" rather than
"final validation."

### Q3. Does the result replicate across descriptors?

Recommended answer: yes, directionally and materially.

| Descriptor | same-ID review-ready | false-candidate review-ready | Risk difference |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 50/50 | 35/50 | +0.30 |
| DINOv2 | 50/50 | 38/50 | +0.24 |
| Pooled | 100/100 | 73/100 | +0.27 |

The false-candidate ready-rate difference between DINOv2 and MegaDescriptor is
small:

```text
DINOv2 - MegaDescriptor false-candidate ready-rate difference: +0.06
bootstrap 95% CI: [-0.12, +0.24]
```

So there is no obvious cross-descriptor contradiction.

### Q4. Did row-level bootstrap overstate confidence because pairs are not independent?

Recommended answer: maybe slightly, but the effect survives stricter checks.

There are repeated query images and reciprocal/near-duplicate unordered pairs.
So row-level bootstrap is optimistic. I therefore ran query-cluster and
deduplicated unordered-pair sensitivity checks:

| Descriptor | Scope | Rows | Unique queries | Unique unordered pairs | Risk difference | Query-cluster CI |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MegaDescriptor | row-level | 100 | 60 | 75 | +0.300 | [+0.139, +0.378] |
| MegaDescriptor | dedup unordered pair | 75 | 40 | 75 | +0.306 | [+0.143, +0.385] |
| DINOv2 | row-level | 100 | 69 | 68 | +0.240 | [+0.115, +0.389] |
| DINOv2 | dedup unordered pair | 68 | 48 | 68 | +0.233 | [+0.103, +0.395] |
| Pooled | row-level | 200 | 92 | 143 | +0.270 | [+0.173, +0.355] |
| Pooled | dedup unordered pair | 143 | 77 | 143 | +0.272 | [+0.169, +0.356] |

This improves confidence. The effect is not just a row-duplication artifact.

### Q5. Are the human labels measuring what we claim?

Recommended answer: partially.

They clearly measure a human distinction between `review_ready` and
`uncertain`. But they do **not** yet confirm the narrower mechanism
`low_evidence` or `non_comparable`, because no such labels were assigned.

Therefore the valid construct is:

```text
reviewability degradation / uncertainty
```

not:

```text
confirmed low-evidence or confirmed non-comparability
```

### Q6. Could the reviewer have been biased?

Recommended answer: yes, this is a major limitation.

The Streamlit form was intended to be blind to truth and descriptor/PF-ERI
scores, but this is still a single-reviewer audit. It lacks:

- independent second reviewer;
- inter-rater reliability;
- adjudication protocol;
- randomized replicate pairs for intra-rater consistency.

This is the biggest remaining confidence gap.

### Q7. Could the targeted sample design inflate the apparent effect?

Recommended answer: yes, by design.

legacy-code18i sampled high-similarity false candidates and high-similarity same-ID
controls from the legacy-code18h mechanism packet. This is good for mechanism probing
but not a population estimate of all candidate pairs. The result should be
reported as a **targeted mechanism audit**, not as the average effect in the
full retrieval queue.

### Q8. Is PF-ERI doing more than image-quality filtering?

Recommended answer: yes, likely.

Across both descriptors, weakest-image-quality differences between
`review_ready` and `uncertain` are small and confidence intervals cross zero or
remain near zero:

```text
MegaDescriptor quality difference: +0.016, CI [-0.005, +0.045]
DINOv2 quality difference: +0.006, CI [-0.002, +0.016]
```

PF-ERI admissibility and pair geometry are stronger:

```text
MegaDescriptor admissibility difference: +0.062, CI [+0.037, +0.090]
DINOv2 admissibility difference: +0.043, CI [+0.025, +0.062]
MegaDescriptor geometry difference: +0.160, CI [+0.107, +0.211]
DINOv2 geometry difference: +0.127, CI [+0.072, +0.180]
```

This supports the claim that PF-ERI is not merely a quality-only filter.

### Q9. Does conflict behave as expected?

Recommended answer: not cleanly.

MegaDescriptor showed higher conflict in uncertain pairs, but DINOv2 did not.
This matches the earlier legacy-code18h caution: high conflict alone should not be
the headline mechanism.

The safer mechanism is:

```text
admissibility / geometry / reviewability degradation
```

not:

```text
high conflict means false candidate
```

### Q10. Would a skeptical reviewer be convinced?

Recommended answer: convinced enough to see a promising mechanism, not enough
to accept a final system claim.

What is convincing:

- two strong descriptors;
- balanced same-ID vs false-candidate targeted packets;
- complete labels for 200 pairs;
- same direction across descriptors;
- effect survives query-cluster and dedup sensitivity checks;
- quality-only control is weak.

What remains vulnerable:

- one reviewer;
- targeted, non-random sample;
- no inter-rater reliability;
- no preregistered human-audit protocol before labels;
- no full-queue population estimate of human reviewability;
- no Bobcat identity labels.

## Confidence Grade

| Claim | Confidence | Rationale |
| --- | --- | --- |
| Strong descriptor queues still contain reviewability-risk false candidates | Moderate-high | Replicated across MegaDescriptor and DINOv2 targeted samples. |
| PF-ERI admissibility tracks human reviewability | Moderate-high | Same direction and positive CIs across descriptors. |
| PF-ERI is not just image quality filtering | Moderate | Quality-only differences are weak; geometry/admissibility stronger. |
| High conflict is the core mechanism | Low-moderate | Inconsistent and previously contradicted by legacy-code18h. |
| Results generalize to the full retrieval queue | Moderate-low | Targeted sample, not population sample. |
| Results support Bobcat identity accuracy | None | Bobcat is unlabeled transfer/readiness only. |
| Results are paper-ready final validation | Moderate-low | Needs second reviewer/adjudication and broader sample. |

## Recommended Claim Wording

Strong but safe:

```text
Across MegaDescriptor and DINOv2 candidate queues, targeted human review of
high-similarity pairs showed that same-ID controls remained consistently
review-ready, while false-candidate pairs contained a reproducible uncertain
reviewability subset. PF-ERI admissibility and pair geometry tracked this
reviewability degradation, whereas image quality alone did not explain it.
```

Even safer:

```text
These results provide targeted evidence that PF-ERI captures pair-level
review-readiness information that is not reducible to descriptor similarity or
single-image quality.
```

## Minimum Next Step for Higher Confidence

1. Add a second blinded reviewer for the same 200 pairs.
2. Compute agreement:
   - percent agreement;
   - Cohen's kappa for `review_ready` vs `uncertain/non-ready`;
   - adjudicated label set.
3. Add a random sample from the full top-k queue, not only legacy-code18h targeted
   cases.
4. Re-run the same cluster/dedup sensitivity analysis.

If those pass, the confidence can move from "moderate-to-strong targeted
evidence" to "strong evidence for pair-level reviewability utility."

## Sources

- Čermák, V., Picek, L., Adam, L., & Papafitsoros, K. WildlifeDatasets: An
  Open-Source Toolkit for Animal Re-Identification. WACV 2024.
- Oquab, M. et al. DINOv2: Learning Robust Visual Features without
  Supervision. arXiv/OpenReview, 2023/2024.
- Schneider et al. / related review literature on individual animal
  identification from biology and computer vision.
- Observer-variance studies in camera-trap image annotation.
- Large-felid individual identification review literature discussing observer
  bias and uncertainty.

## Artifacts

Sensitivity output:

```text
outputs/legacy-code18/legacy-code18i_reviewability_analysis/legacy-code18i_confidence_sensitivity.csv
```

Cross-descriptor summary:

```text
outputs/legacy-code18/legacy-code18i_reviewability_analysis/legacy-code18i_cross_descriptor_summary.csv
```
