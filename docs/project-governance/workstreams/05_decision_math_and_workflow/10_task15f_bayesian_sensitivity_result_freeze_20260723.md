# Task 15F Bayesian Sensitivity Result Freeze

Status: **COMPLETE — FROZEN PASS WITHOUT FINAL MODEL SELECTION**
Date: 23 July 2026
Applies to: Workstream 05 / development Task 15F-C

## Scope and integrity

Task 15F-C freezes the completed development-only Bayesian and separation sensitivities without changing their registered scientific roles. The original ModelScope export has SHA256 `21f3bfdf8da574cccddf6ee74c6658bb94f0406f46ee2cc477a38ae5c3015334`. Its external checksum declaration, run summary, ZIP CRC, 55-member inventory, 54 internal checksums, 890 out-of-fold predictions, 445 unique development pairs, 116 endpoint-image components, ten posterior fits, five S4 marginalization records, and triggered S5 diagnostic were independently verified. The frozen execution contract hash matches the run audit, and the validation audit reports `PASS` with no failure. No calibration, deployment-confirmation, or mechanism-confirmation outcome was accessed.

## Posterior computation

All five S3 weak-prior fixed-effect fits and all five S4 crossed-endpoint-image fits passed on their first prespecified sampling attempt. Across the ten fits there were zero post-tuning divergences. The maximum fixed-parameter rank-normalized R-hat was 1.004418, the minimum fixed-parameter bulk effective sample size was 2,290.1, and the minimum fixed-parameter tail effective sample size was 2,861.1. The maximum image-offset R-hat was 1.004823. These values pass the frozen computational gates by substantial margins and support interpretation of the retained posterior summaries, although computational convergence does not establish external predictive validity.

## Predictive sensitivity

Independent recalculation reproduced the reported design-weighted proper scores. S3 obtained a Brier score of 0.122745395 and log loss of 0.393984317, whereas S4 obtained a Brier score of 0.123377950 and log loss of 0.393456322. The difference defined as S3 minus S4 was -0.000632555 for Brier score and 0.000527996 for log loss. S3 had lower Brier loss in three outer folds and S4 in two, while the pooled Brier and log-loss comparisons favored different models. Relative to the frozen Task 15E P5 values, S3 and S4 reduced development Brier descriptively by 12.456% and 12.005%, respectively. These changes show that weak-prior regularization materially alters development predictions, but the frozen Task 15F contract explicitly prohibits selecting a final model by the lowest sensitivity-analysis loss.

## Pair evidence and shared-image dependence

The standardized local-match coverage coefficient had a positive posterior mean in all ten model-by-fold summaries, but every 95% credible interval crossed zero. The posterior probability of a positive coefficient ranged from 0.640 to 0.867. The direction is therefore coherent across model families and folds, but the development data do not isolate a precise or fold-stable local-match increment. This result is consistent with the weak incremental pair-evidence contrast observed in Task 15E and does not promote the pair-evidence block to a confirmed contribution.

The S4 image-level standard deviation had posterior means from 1.115 to 1.335, with fold-specific 95% lower bounds from 0.560 to 0.845 under the frozen half-normal prior. Endpoint-image heterogeneity is therefore material within the registered model and must remain visible as a dependence limitation. However, population-marginal prediction for two previously unseen endpoints did not yield a stable Brier advantage over S3. The result supports dependence-aware uncertainty reporting, not automatic promotion of the crossed-image model.

## Separation diagnostic and binding decision

The prespecified S5 trigger produced 180 Firth/FLIC diagnostic predictions in outer folds 0 and 4. No S5 row was selection-eligible. The diagnostic confirms that classical unpenalized fitting encountered instability in the declared folds, whereas the weak-prior Bayesian models remained computationally stable. Because the numerical S5 thresholds were recorded after development outcomes opened, this result cannot participate in final route selection.

Task 15F is complete and must not be rerun, reprioritized, or selectively replaced in response to its observed results. S3, S4, and S5 remain mathematical sensitivities and are not confirmation-eligible. No final development model is selected, and calibration plus both confirmation stages remain locked. The immutable result freeze is stored at `archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1/`, where the source delivery, extracted results, independent recalculation, scientific disposition, builder snapshot, audit, and complete directory checksums are retained together.

## Next gate

The next authorized task is Task 15G. It must freeze an exact execution contract before fitting the already registered E1 explainable boosting machine, E2 shallow CatBoost model, or E3 fixed-version TabPFN model. These routes may estimate an exploratory development performance bound but remain `confirmation_eligible=false`. Task 15H must then apply qualification before performance and produce a validated `development_model_freeze_record.json` before the calibration outcome stage can open.
