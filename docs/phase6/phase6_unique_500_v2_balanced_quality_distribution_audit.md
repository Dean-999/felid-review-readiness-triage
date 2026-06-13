# Phase 6 Unique-500 v2 Balanced Quality Distribution Audit

## Result

The v2 balanced quality distribution passes the requested constraints.

## Overall Distribution

| Bucket | Count | Target |
|---|---:|---|
| high_evidence_proxy | 150 | 125-175 |
| medium_evidence_proxy | 175 | 150-200 |
| low_but_annotatable_proxy | 110 | 100-125 |
| extreme_hard_proxy | 65 | 50-75 maximum |

Near-black, eye-shine-only, or almost-empty proxy count:

```text
38
```

This is below the full-set 15 percent cap.

## Batch-Level Cap

No batch has more than 10 extreme-hard images.

No batch has more than 10 near-black, eye-shine-only, or almost-empty proxy images.

No batch is dominated by black or extreme-hard images.

## Why This Matters

PF-ERI factor-to-risk modeling needs a controlled evidence-quality gradient. If the set is dominated by extreme hard cases, the analysis mainly measures exclusion/defer behavior rather than the relationship between visual evidence factors and Re-ID review utility.

The v2 set keeps extreme hard images for policy relevance but restores enough clear and medium evidence to support meaningful factor-to-risk modeling.
