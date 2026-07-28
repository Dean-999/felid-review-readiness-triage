# Task17 Confirmation Outcome Analysis

Status: **COMPLETE - FAIL_PRIMARY_CONFIRMATION; V2_NOT_CONFIRMED**

## Decision

Task17 performed the one permitted primary confirmation analysis after Task15N passed execution validation. The frozen Task15M contract defined the estimand as the Hajek-normalized inverse-probability-weighted difference `Brier(P3 calibrated) - Brier(P5 calibrated)`. Positive values favour P5. The prespecified success rule required the lower endpoint of the two-sided 95% dyadic cluster-robust interval to be greater than `0.005`.

The point estimate was `-0.201869782`. P3 weighted Brier was `0.307245886` and P5 weighted Brier was `0.509115668`. The dyadic cluster-robust 95% interval was `[-0.224671400, -0.179068163]`. The entire interval favours P3, and its lower endpoint is far below the practical threshold. The primary confirmation result is therefore `FAIL_PRIMARY_CONFIRMATION`, with scientific disposition `V2_NOT_CONFIRMED_PRIMARY_INCREMENT_NOT_MET`.

## Analysis Integrity

The analysis used exactly 252 supported Task15M pairs. The other 637 of the 889 candidate pairs were excluded before outcome opening by the frozen descriptor-taxonomy rule. Every supported anonymized Task15M pair mapped one-to-one through the frozen restricted linkage to a deployment-confirmation pair, formal sampling probability, accepted human outcome, and both calibrated P3/P5 predictions. The complete deployment outcome commitment covered all 889 deployment rows and matched its sealed SHA256 commitment. The primary analysis used 357 unique original physical image endpoints, with maximum endpoint degree seven, and calculated the interval from the prescribed shared-endpoint dyadic sandwich variance.

No Task15J coefficient, preprocessing parameter, lambda value, Task15L calibration parameter, pair membership, or outcome label was changed. The analysis was run once and the output is checksum-protected at `outputs/pferi_v2/models/confirmation/final_analysis/`.

## Claim Consequence

The Task15I development-screen pass remains a bounded development result. It does not survive as a claim of independent P5 superiority. PF-ERI v2 cannot claim that P5 improves reviewability prediction beyond P3 on the eligible external confirmation subset. It also cannot claim identity accuracy, deployment utility, workflow efficiency, or automatic identity assignment.

Workstream 05 exits as `v2_not_confirmed` for the primary model claim. The appropriate next project action is archival and a transparent negative-result manuscript or, if a substantively revised scientific question is desired, a new PF-ERI v3 protocol with new development and confirmation data. Retuning the v2 model, recalibrating after this confirmation result, replacing pairs, or repeating the analysis is prohibited.
