# Phase 11 Experiment Digest

Date: 2026-06-17

Purpose: summarize Phase 11 pair-level PF-ERI metric-learning experiments and clarify what remains active for Phase 12.

## Phase 11 Role

Phase 11 is the first engineering scaffold for pair-level PF-ERI reliability-aware metric learning. It does not prove a scientific claim by itself.

The phase created:

- a deterministic pair reliability table;
- Colab training/evaluation scripts;
- positive-pair weighting variants;
- negative reliability-control variants;
- split-level diagnostics;
- conditional positive-rescue ablations.

## Pair Reliability Model

The current pair reliability score uses interpretable components:

```text
side comparability
pattern pair evidence
blur
occlusion
body visibility
viewpoint compatibility
```

The weakest-image principle remains central: a pair is weak if either image lacks comparable patterned-felid evidence.

## Main Experiment Families

### Phase 11 Base

Base Phase 11 tested positive-pair weighting and a more aggressive unreliable hard-negative control using the H3 image set.

### Phase 11B

Phase 11B tested softened positive-pair weighting:

```text
w_pos = R
w_pos = 0.5 + 0.5R
w_pos = sqrt(R)
w_pos = max(0.35, R)
```

The square-root rule became the strongest current reference because raw weighting may suppress too much valid same-identity variation.

### Phase 11C

Phase 11C tested parameterized global transforms and split diagnostics. The diagnostics showed that some apparent C3/H3 differences were not caused by different image sets in the current manifest, pushing attention toward pair structure and split-specific hard negatives.

### Phase 11D / 11D-R / 11D-R2

These variants test conditional positive rescue: low-reliability same-identity pairs are only rescued if they have descriptor support or meet target-rate selection rules.

The purpose is mechanism testing, not immediate claim support.

## Active Lessons

- Pair-level weighting is more aligned with Re-ID than image-only filtering.
- Raw reliability weights can be too aggressive for positives.
- Positive rescue must have nonzero, controlled activation to test the intended mechanism.
- Negative downweighting should remain conservative until diagnostics show a clear unreliable hard-negative pattern.
- Query coverage and false-candidate burden must be reported beside mAP/MRR.

## Current Claim Boundary

Phase 11 supports training readiness and ablation design only. It does not prove that PF-ERI improves metric learning.

A defensible RQ4 claim requires held-out evaluation showing improvement or stabilization against:

- uniform supervised contrastive learning;
- random matched controls;
- quality-proxy matched controls;
- image-level PF-ERI selection;
- no-training PF-ERI-aware reranking references.

## Phase 12 Hand-Off

Phase 12A should not start by adding more training variants. It should first build a unified pair/candidate analysis table with:

- pair reliability;
- descriptor similarity;
- descriptor disagreement;
- reciprocal or margin support;
- conflict score;
- same/different label for validation;
- split metadata;
- retrieval outcome flags.

That table becomes the common substrate for RQ1-RQ4.

## Canonical Source Files

- `phase11_pair_reliability_math_spec.md`
- `phase11_pair_level_pf_eri_metric_learning_implementation.md`
- `phase11b_positive_weighting_ablation.md`
- `phase11c_split_level_diagnostic_report.md`
- `phase11d_evidence_conditional_pair_weighting.md`
- `phase11dr_revised_positive_rescue.md`
- `phase11dr2_target_rate_positive_rescue.md`
