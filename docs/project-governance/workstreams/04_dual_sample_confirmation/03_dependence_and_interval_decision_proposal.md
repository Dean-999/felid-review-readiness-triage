# Pre-Outcome Dependence and Interval Decision Proposal

Status: accepted by the project owner pre-outcome on 15 July 2026; incorporated into the working numerical decision record, but not by itself a complete design freeze.  
Applies to: Workstream 04 Task 03.  
Prepared: 15 July 2026 before any v2 outcome packet or outcome review.

## Decision being proposed

The binding planning calculation should use a paired Brier-loss-difference standard deviation of 0.120 and a joint image-endpoint variance fraction of 0.10. Under the existing transparent planning model, two pair observations that share one image then have an induced correlation of 0.05. These values are the conservative edges of the ranges already declared in the outcome-free sensitivity configuration. They are not estimates from v1, anticipated v2 performance, or values selected because they produce a favourable success probability.

The primary deployment estimand should remain the paired difference between the active-control Brier loss and the full automatic-evidence-model Brier loss on identical deployment-confirmation pairs. When the deployment queue uses unequal inclusion probabilities, the point estimate should be the Hájek-normalized inverse-probability-weighted mean of the pair-level loss differences. If the final deployment sample is self-weighting, the same expression reduces to the ordinary paired mean. Mechanism-confirmation observations must not be pooled into this primary deployment estimate.

The primary 95% interval should use the dyadic cluster-robust sandwich variance estimator of Aronow, Samii, and Assenova, with physical image IDs as the shared dyad members. This estimator directly represents the dependence created when one image appears in several canonical pairs and supports weighted observations. The implementation must use the published dyadic inclusion structure rather than ordinary row-level heteroskedasticity correction, row bootstrap, fold bootstrap, or arbitrary two-way clustering on canonical endpoint columns. The success rule remains unchanged: the lower endpoint of this pre-specified graph-aware interval must be greater than 0.005.

The interval is asymptotic in the number of distinct image nodes contributing to the deployment sample. The implementation should therefore report the number of unique image nodes, pair-degree distribution, maximum node degree, effective pair count, and the ratio of dyadic-robust to independent-row standard errors. A conventional independent-row interval may be reported only as a labelled anti-conservative diagnostic. A restricted identity-cluster sensitivity and camera/site sensitivity should be added when those fields are available, because dyadic image clustering does not protect against higher-order dependence that persists across different images of the same identity, camera, or site.

## Precision implication of the accepted 800-pair deployment sample

The conservative outcome-free planning row for 800 analyzable deployment pairs has a mean graph design effect of 1.0583 and a mean effective pair count of approximately 755.9. With a paired-loss standard deviation of 0.120, the corresponding planning standard error is approximately 0.00436. Under the normal planning approximation, 800 pairs provide approximately 20.8% probability of passing the lower-bound rule if the true Brier improvement is 0.010, but approximately 93.0% if the true improvement is 0.020. These are synthetic operating characteristics, not forecasts of PF-ERI performance.

Equivalently, the approximate true improvement required for 80% probability of exceeding the 0.005 lower-bound threshold is 0.0172 under this conservative scenario. Detecting a true improvement of 0.010 with 80% probability under the same approximation would require roughly 4,785 analyzable deployment pairs. That workload is inconsistent with the accepted programme and current review resources. The scientifically defensible interpretation is therefore that the 800-pair confirmation is designed to confirm a moderate practical advantage with useful precision; failure to cross the primary threshold would remain inconclusive between a small positive effect and no useful effect, rather than proving exact equality.

## Scientific rationale and limitations

Choosing the most conservative predeclared variability and dependence values reduces the risk that the design is justified by an optimistic sensitivity row. It also exposes an important limitation before data collection: the accepted design is not highly powered for an improvement only slightly above the 0.005 practical threshold. This limitation should be reported rather than hidden by changing the effect assumption, weakening the success rule, or treating 2,000 pairs from different analytical roles as one confirmation sample.

The dyadic variance estimator is the closest match to the observed graph structure because PF-ERI pairs share image nodes. Aronow, Samii, and Assenova show that ignoring shared-member dependence can make confidence intervals substantially too narrow and extend their estimator to weighted observations ([DOI 10.1093/pan/mpv018](https://doi.org/10.1093/pan/mpv018)). The method does not solve model misspecification, selection bias, missing outcomes, or higher-order identity and camera dependence. Those threats remain separate design and sensitivity obligations.

## Acceptance consequence

The project owner accepted this proposal on 15 July 2026 before creation of any v2 outcome packet. The accepted planning values are a paired-loss standard deviation of 0.120 and a joint image-endpoint variance fraction of 0.10, corresponding to an induced correlation of 0.05 for two pairs sharing one image under the declared planning model. The accepted primary interval family is the dyadic cluster-robust sandwich variance estimator with physical image IDs as dyad members. The accepted point estimate is the Hájek-normalized inverse-probability-weighted paired Brier difference when sampling probabilities are unequal and the ordinary paired mean when the deployment sample is self-weighting.

This acceptance resolves the dependence-and-interval decision only. The reviewer-operation design is recorded separately and does not use estimated time or a collection window. The project must still refrain from choosing an official seed, generating a real split, or creating an outcome packet until the immutable strata rule and role-assignment safeguards are completed.
