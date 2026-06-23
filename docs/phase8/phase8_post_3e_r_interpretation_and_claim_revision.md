# Phase 8 Post-3E-R Interpretation and Claim Revision

## Phase 9 Supersession Note

This document remains the correct boundary for Phase 8 accuracy claims: PF-ERI did not robustly improve fixed-descriptor mAP under held-out query-level evaluation. Phase 9 does not erase that result. It reinterprets the result as evidence that simple hard filtering is insufficient and motivates a new test of PF-ERI as an automated image/pair/candidate evidence utility model for fixed-descriptor reranking.

## 1. Reason for Reframing

Phase 8 Slice 3E initially gave conditional support for PF-ERI-selected evidence improving fixed-descriptor Re-ID metrics beyond repeated random same-size controls. That interpretation was intentionally provisional because Slice 3E did not complete query-level held-out calibration/evaluation.

Slice 3E-R completed that stricter evaluation. The final decision was:

```text
held_out_reid_accuracy_improvement_not_robust
```

Therefore, the project should no longer claim or imply that PF-ERI robustly improves fixed-descriptor Re-ID accuracy. The stronger defensible framing is that PF-ERI provides a patterned-felid evidence-control and review-prioritization framework that reduces false-candidate review burden under held-out query-level evaluation.

## 2. Slice 3E Conditional Result Summary

Slice 3E tested PF-ERI-selected images and descriptor-generated candidate policies against all-images retrieval, raw descriptor ranking, and repeated random same-size baselines.

The original full-carrier decision was:

```text
conditional_reid_accuracy_improvement_supported_for_czechlynx_fixed_descriptor_setting
```

That result was useful because it showed that stricter evidence selection could change retrieval, coverage, retention, and workload metrics. However, it remained conditional because selected policies could still be benefiting from easier-sample selection or calibration/evaluation leakage if not tested at held-out query level.

## 3. Slice 3E-R Held-Out Result Summary

Slice 3E-R used deterministic identity-aware query-level calibration/evaluation splits.

Key results:

- query-level split count: `20`;
- random repeats per split: `200`;
- `v4_0636` selected in `14/20` splits;
- `candidate_f` selected in `6/20` splits;
- selected policies beat random same-size controls on false reviewed candidate burden in `20/20` splits;
- selected policies beat random same-size controls on mAP in only `3/20` splits.

The held-out result supports false-candidate burden reduction, not robust mAP improvement.

## 4. Why the Accuracy-Improvement Claim Must Be Weakened

The stronger claim would require PF-ERI-selected policies to improve fixed-descriptor retrieval accuracy beyond repeated random same-size controls under held-out query-level evaluation while preserving acceptable query coverage and positive retention.

That condition was not met. The policies selected on calibration queries did not reliably outperform random same-size controls on held-out mAP. This means the apparent Slice 3E improvement may partly reflect easier-sample selection, policy instability, or tradeoffs where accuracy-looking gains are purchased by reduced positive retention.

The project should therefore avoid:

```text
PF-ERI robustly improves Re-ID accuracy.
```

## 5. What Remains Scientifically Meaningful

The held-out result remains scientifically meaningful because it separates workflow reliability control from raw identity-discrimination performance.

PF-ERI did reduce false-candidate review burden relative to repeated random same-size controls across all held-out splits. This is useful for patterned-felid Re-ID review because review burden and false candidates are practical workflow costs, even when descriptor mAP does not improve robustly.

The meaningful contribution is:

- explicit visual evidence gating;
- fixed descriptor support kept separate from evidence quality;
- query-level held-out policy evaluation;
- random same-size safeguards against easier-sample artifacts;
- false-candidate burden reduction;
- transparent review/defer/exclude policy interpretation.

## 6. Revised Main Contribution

Revised main contribution:

```text
PF-ERI Control is a patterned-felid Re-ID evidence-control and review-prioritization framework that uses visual evidence admissibility, fixed descriptor support, calibration, and review policies to reduce false-candidate review burden under imperfect camera-trap evidence.
```

PF-ERI is not a Re-ID model, not an identity decision system, and not a standalone fixed-descriptor accuracy-improvement method.

## 7. Supported Claims

Supported claims:

- PF-ERI reduces false-candidate review burden under CzechLynx query-level held-out evaluation.
- PF-ERI makes evidence quality, descriptor uncertainty, and review tradeoffs explicit.
- PF-ERI supports patterned-felid Re-ID review prioritization under imperfect camera-trap evidence.
- PF-ERI can be evaluated with strict random same-size controls and query-level held-out splits.
- PF-ERI does not robustly improve fixed-descriptor mAP beyond random same-size controls in the current CzechLynx evaluation.

## 8. Unsupported Claims

Unsupported claims:

- PF-ERI is a new Re-ID model.
- PF-ERI identifies true individual animals.
- PF-ERI robustly improves Re-ID accuracy.
- PF-ERI is validated across felids.
- PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- PF-ERI is ready for field deployment.
- PF-ERI supports population estimation.
- PF-ERI solves animal Re-ID.

## 9. Candidate F Interpretation

Candidate F remains the review-control reference because it preserves stronger positive retention and query coverage than stricter variants.

Candidate F should be described as:

```text
the main review-control reference policy that preserves evidence coverage while making descriptor-disagreement caution visible.
```

Do not claim Candidate F improves Re-ID accuracy.

## 10. v4_0636 Interpretation

`v4_0636` is the strongest operational refinement reference because it was selected most often in query-level calibration and reduced false-candidate burden.

It should be described with its tradeoff:

```text
v4_0636 lowers false-candidate burden but also lowers positive retention and query coverage relative to Candidate F.
```

Do not promote `v4_0636` as the final main policy unless the manuscript explicitly states this lower-burden/lower-retention tradeoff.

## 11. Expected Utility Interpretation

Expected utility policies remain sensitivity and confidence-control layers. They are useful for testing how review values change when workload, confidence, visual evidence, or descriptor support are weighted differently.

Do not call expected utility policies:

- identity scores;
- safety scores;
- final policies.

## 12. Final Phase 8 Claim Boundary

Final Phase 8 claim boundary:

```text
PF-ERI is a CzechLynx-tested evidence-control and review-prioritization framework for patterned-felid Re-ID review. It reduces false-candidate review burden under held-out query-level evaluation, but current evidence does not support robust fixed-descriptor Re-ID accuracy improvement beyond repeated random same-size controls.
```

## 13. Recommended Manuscript Language

Recommended paragraph:

```text
The held-out query-level evaluation clarified the role of PF-ERI. While PF-ERI-selected policies reduced false-candidate review burden relative to repeated random same-size controls across all held-out splits, they did not robustly improve fixed-descriptor retrieval accuracy measured by mAP. Therefore, PF-ERI should be interpreted as an evidence-control and review-prioritization layer rather than a replacement for descriptor-based Re-ID or a standalone accuracy-improvement method. This finding is important because it distinguishes workflow reliability control from raw identity-discrimination performance.
```

## 14. Recommended Next Research Step

Recommended primary next step:

```text
Phase 8 Slice 3F — Downstream Ecological Sensitivity Simulation
```

Reason:

```text
PF-ERI's robust supported value is not raw Re-ID accuracy improvement; it is reducing false-candidate burden. The next logical question is whether that reduction meaningfully reduces downstream ecological record contamination.
```

This should be a conservative simulation, not a population-estimation claim and not a field-deployment claim.

## 15. Confirmation

This revision is documentation-only.

No code was implemented. No model was trained. No external data were downloaded. No frozen data were modified. No files were staged or committed.
