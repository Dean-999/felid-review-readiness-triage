# legacy-code18 Strong-Baseline Pair-Level Results

Date: 2026-07-02

## Question

Does PF-ERI still add value after a strong descriptor has already generated the
candidate queue?

The claim tested here is not descriptor replacement. The tested claim is:

```text
strong descriptor queue
-> pair-level PF-ERI evidence admissibility and conflict features
-> review-utility routing
```

In plain terms: a strong descriptor answers which images look similar. PF-ERI
asks whether each retrieved pair is evidentially admissible, review-ready,
conflicting, or better deferred.

## Inputs And Audit Status

External strong descriptor artifacts were returned under:

```text
outputs/legacy-code18/returned_strong_baselines/
```

Both returned descriptor packages passed local receiver audits:

| Descriptor | Embedding rows | Dim | CzechLynx pair-score rows | Species counts | Receiver status |
| --- | ---: | ---: | ---: | --- | --- |
| `megadescriptor_l_384` | 6,000 | 1,536 | 60,000 | Bobcat 3,000; CzechLynx 3,000 | PASS |
| `dinov2_vitl14` | 6,000 | 1,024 | 60,000 | Bobcat 3,000; CzechLynx 3,000 | PASS |

legacy-code18g is now:

```text
READY_FOR_STRONG_BASELINE_EVALUATION
```

This means strong descriptor artifacts are available for evaluation. It is not
a final identity-assignment claim.

## CzechLynx Known-ID Pair Results

Both strong descriptor runs used the same frozen CzechLynx known-ID carrier:

| Descriptor | Known-ID images | Identities | Top-k | Pair rows | Same-ID pairs | Descriptor mAP@20 | Descriptor MRR@20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `megadescriptor_l_384` | 3,000 | 235 | 20 | 60,000 | 17,491 | 0.5781 | 0.6869 |
| `dinov2_vitl14` | 3,000 | 235 | 20 | 60,000 | 15,791 | 0.5476 | 0.6621 |

The two descriptors are credible strong upstream candidate generators. PF-ERI is
therefore being evaluated in the intended post-retrieval setting.

## Review-Router Evaluation

Evaluation split, top-5 review queue metrics:

| Descriptor | Policy | mAP@5 | MRR@5 | Top-1 | Positive present@5 | False candidates@5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MegaDescriptor | descriptor only | 0.7277 | 0.7426 | 0.7079 | 0.7974 | 2.2053 |
| MegaDescriptor | PF-ERI review router | 0.7317 | 0.7475 | 0.7132 | 0.8039 | 2.1789 |
| MegaDescriptor | conflict-penalized descriptor | 0.7296 | 0.7461 | 0.7132 | 0.7987 | 2.1974 |
| DINOv2 | descriptor only | 0.7079 | 0.7272 | 0.6855 | 0.7961 | 2.3079 |
| DINOv2 | PF-ERI review router | 0.7085 | 0.7284 | 0.6829 | 0.8026 | 2.2895 |
| DINOv2 | conflict-penalized descriptor | 0.7071 | 0.7266 | 0.6842 | 0.7974 | 2.3000 |

Against descriptor-only, the PF-ERI review router changed evaluation metrics as
follows:

| Descriptor | Delta mAP@5 | Delta MRR@5 | Delta top-1 | Delta positive present@5 | Delta false candidates@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| MegaDescriptor | +0.0040 | +0.0049 | +0.0053 | +0.0066 | -0.0263 |
| DINOv2 | +0.0006 | +0.0012 | -0.0026 | +0.0066 | -0.0184 |

The strongest observed result is not a large ranking gain. The strongest result
is reduced false-candidate review burden while preserving, and slightly
improving, positive-present coverage.

## Bootstrap Confidence

Query-level paired bootstrap was run with:

```text
resampling unit: query_image_id
iterations: 5,000
seed: 20260702
```

Key evaluation-split bootstrap results:

| Descriptor | Comparison | Metric | Estimate | 95% CI | Direction |
| --- | --- | --- | ---: | --- | --- |
| MegaDescriptor | PF-ERI review router vs descriptor only | false candidates@5 | -0.0263 | [-0.0461, -0.0079] | improves review utility |
| MegaDescriptor | PF-ERI review router vs descriptor only | positive present@5 | +0.0066 | [-0.0026, +0.0158] | mixed/uncertain |
| MegaDescriptor | PF-ERI review router vs descriptor only | mAP@5 | +0.0040 | [-0.0022, +0.0102] | mixed/uncertain |
| DINOv2 | PF-ERI review router vs descriptor only | false candidates@5 | -0.0184 | [-0.0461, +0.0118] | mixed/uncertain |
| DINOv2 | PF-ERI review router vs descriptor only | positive present@5 | +0.0066 | [-0.0053, +0.0184] | mixed/uncertain |
| DINOv2 | PF-ERI review router vs descriptor only | mAP@5 | +0.0006 | [-0.0093, +0.0106] | mixed/uncertain |

Interpretation:

- MegaDescriptor supports the pair-level review-utility claim: false-candidate
  burden decreases with a confidence interval that does not cross zero.
- DINOv2 is directionally compatible but statistically mixed under this first
  query-level bootstrap.
- The evidence does not support claiming broad descriptor replacement or a large
  top-k ranking improvement.

## Negative And Boundary Results

`pf_eri_admissibility` alone performs poorly as a ranking policy. On the
evaluation split, it reduces mAP/top-1 and increases false candidates relative
to descriptor-only for both strong descriptors.

This is scientifically useful. It shows PF-ERI should not be described as a
standalone similarity or ranking replacement. Its current value is as a
review-routing and conflict-aware layer that operates with descriptor evidence,
not instead of it.

Bobcat outputs remain transfer-readiness only:

| Descriptor | Bobcat images | Review-ready images | Manual-review images | Deferred images |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 3,000 | 2,814 | 145 | 41 |
| DINOv2 | 3,000 | 2,925 | 61 | 14 |

These are not Bobcat identity-accuracy results.

## Current Claim Status

Supported:

```text
PF-ERI has evidence as a descriptor-agnostic, post-retrieval, pair-level
review-utility layer. Under MegaDescriptor, it reduces evaluation-split
top-5 false-candidate burden while maintaining positive-present coverage.
```

Mixed:

```text
DINOv2 shows the same direction on false-candidate burden and positive-present
coverage, but the bootstrap confidence interval crosses zero.
```

Not supported:

```text
PF-ERI as a descriptor replacement.
PF-ERI as an automatic identity-assignment system.
PF-ERI as Bobcat identity-accuracy validation.
PF-ERI as a universal top-k ranking improvement claim.
```

## Recommended Next Step

The next step should be a mechanism-focused legacy-code18h analysis, not another broad
reranking attempt.

Recommended legacy-code18h:

```text
strong descriptor false-candidate cases
-> descriptor-evidence conflict enrichment
-> representative failure/conflict samples
-> optional small human-review audit packet
```

Required outputs:

- conflict-enrichment table: are high-similarity, low-evidence pairs enriched
  among false candidates?
- threshold operating table: at fixed positive retention, how much false
  candidate burden is removed?
- failure-case sample sheet: top high-similarity false candidates with PF-ERI
  conflict/admissibility fields;
- small review packet: optional, second-stage human audit for high-conflict
  pairs and matched controls.

This would turn the current statistical result into a stronger scientific story:
PF-ERI works because it identifies a real pair-level failure mode in strong
descriptor queues, not because it is another descriptor.
