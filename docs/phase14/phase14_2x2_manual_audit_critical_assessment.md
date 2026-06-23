# Phase 14 2x2 Manual Audit Critical Assessment

Date: 2026-06-19

## Bottom Line

The 400-image manual audit shows that the original AI-assisted 2x2 labels are not valid as clean experimental labels.

This is not a small random-label problem. It is a systematic threshold-bias problem:

```text
Bobcat high-confidence is over-permissive.
CzechLynx low-evidence stress is over-strict.
CzechLynx high-confidence is partially usable but mixed.
Bobcat low-evidence stress is the cleanest quadrant.
```

This does not invalidate the project. It strengthens the need for a risk-controlled evidence admission model. The project should now treat the original labels as weak labels and the 400-image audit as calibration evidence.

## Manual Audit Results

| Quadrant | Manual issue rate | Manual core-high | Manual clean-stress | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Bobcat high-confidence | 88% | 12/100 | 67/100 | Severe overestimation of Re-ID evidence |
| Bobcat low-evidence stress | 13% | 1/100 | 99/100 | Stress set is broadly reliable |
| CzechLynx high-confidence | 58% | 32/100 | 49/100 | Mixed high-evidence source; boundary filtering required |
| CzechLynx low-evidence stress | 82% | 28/100 | 72/100 | Stress set is too strict and contains usable Re-ID evidence |

The calibrated 400-row table is:

```text
outputs/phase14/phase14_2x2_manual_audit_400/phase14_2x2_manual_audit_400_calibrated_labels.csv
```

The calibration summary is:

```text
outputs/phase14/phase14_2x2_manual_audit_400/phase14_2x2_manual_audit_400_calibration_summary.json
```

## Scientific Interpretation

The original 2x2 construction was based on machine-derived visual proxies and rule-based confidence refinement. The audit shows those proxies do not measure individual Re-ID evidence equally across contexts:

- Bobcat images often contain a visible animal but insufficient side/flank/pattern evidence for individual Re-ID.
- CzechLynx stress images were penalized too strongly by exposure, crop, or quality features even when usable flank/body evidence remained.
- The same apparent image-quality score can imply different Re-ID evidence utility across species, camera geometry, and background context.

This is a construct-validity issue: the weak labels measured generic visibility too often, while the target construct is Re-ID evidence utility.

## Risk To Claims

Do not claim:

```text
The original high-confidence 3000 sets are clean training sets.
The original stress 3000 sets are clean low-evidence stress sets.
Bobcat and CzechLynx evidence differences are already validated by the current labels.
```

These claims would be vulnerable to reviewer criticism because the manual audit shows asymmetric labeling bias.

## Corrected Research Claim

The stronger and more defensible claim is:

```text
Weak visual labels alone are insufficient for reliable wild-urban Re-ID evidence admission.
Manual audit reveals context-dependent threshold bias, motivating a calibrated PF-ERI evidence admission model that separates clean identity evidence, limited evidence, and low-evidence stress cases under explicit risk control.
```

This turns the audit from a failure into the empirical motivation for the model.

## Required Method Upgrade

The next phase must build a calibrated evidence-admission model using the 400-image audit as the first calibration set.

Recommended target labels:

```text
core_high = manual_review_bucket == review_ready
            and manual_training_eligible == yes
            and manual_evidence_tier == high_confidence

clean_stress = manual_stress_test_eligible == yes
               and manual_review_bucket != review_ready
               and manual_evidence_tier == low_evidence_stress

middle_review = review_limited or uncertain boundary evidence
```

Recommended model family:

```text
calibrated monotonic / interpretable classifier first
then compare against simple rule baselines
```

The model should use image-level measurable features, not species labels as a shortcut. Species/context can be used only for calibration diagnostics and fairness/domain-shift reporting.

## Immediate Next Steps

1. Treat the original 2x2 3000 labels as weak labels.
2. Use the calibrated 400 audit table as manual calibration ground truth.
3. Fit or define a calibrated evidence admission model for:
   - core high-confidence admission;
   - clean stress admission;
   - middle/review routing.
4. Apply the calibrated model to the 18,000-image candidate pool.
5. Rebuild the final 2x2 sets from calibrated predictions, not from the original weak `human_*` labels.
6. Keep the original weak-label failure as a result: it demonstrates why risk-controlled evidence admission is necessary.

## Status

Proceed to algorithms and models, but not by training on the old 2x2 labels. The next algorithmic phase is calibration and evidence-admission modeling.
