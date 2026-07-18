# PF-ERI v2 Pre-Specified Analysis Plan

Status: v2 design draft; numerical gates must be frozen before any v2 outcome review.  
Date: 2026-07-10

This plan is governed by `PROJECT_RULES.md` and applies only to newly collected PF-ERI v2 data. Historical v1 data may inform simulations and feature design but cannot be combined with a v2 estimate, calibration, or confirmation result.

## Endpoint and Label Construction

The primary endpoint is blinded human reviewability, expressed as `review_ready` versus `not_ready_or_uncertain`. A review-ready pair contains sufficient comparable visual evidence for responsible individual-level comparison, including a confident visual rejection of a different individual. The primary outcome is the majority label of the two independent reviewers when they agree; specified disagreements receive a third independent blinded adjudication. The adjudicated endpoint, alternate treatment of `uncertain`, reason-family outcomes, reviewer confidence, and elapsed review time are secondary analyses.

The analysis reports raw agreement, pairwise agreement, an appropriate chance-corrected agreement measure with its limitations, and reason-family agreement. These values describe the measurement process rather than certify it by themselves. The analysis is stopped and reported as a measurement failure if the blinded review logs, reviewer assignment, or interface audit are incomplete or indicate material leakage.

## Model Families and Primary Comparison

The primary model is a regularized interpretable probabilistic model of the probability that a pair is review-ready. The descriptor-only model uses only the locked descriptor-similarity representation. The independent-quality control uses automatic single-image quality variables that are nonconstant and not derived from outcome-review labels. The evidence model uses only automatic pair-evidence variables that passed the measurement gate. The active control combines descriptor similarity and independent quality, and the full model combines descriptor similarity, independent quality, and automatic pair evidence.

The sole primary incremental comparison is full model versus active control on the locked confirmation partition and identical rows. The primary performance quantity is the full-minus-control change in Brier score, with a graph-aware 95% uncertainty interval. Before review starts, the project will freeze a minimum practical increment, an associated superiority or noninferiority decision rule, a power simulation, and the treatment of missing automatic features. Those values must be stored in the versioned pre-registration manifest and must not be selected after outcome labels are visible. A pre-specified nonlinear model, descriptor-specific fits, and human-oracle feature fits are secondary analyses; an oracle fit cannot be presented as a deployable system.

AUROC, AUPRC, log loss, calibration curves, calibration error, slope and intercept, and decision-curve summaries are secondary or descriptive measures. They will be presented with appropriate uncertainty and no claim will be elevated because one secondary metric is favourable while the primary comparison fails. Model coefficients, transformations, regularization, calibration procedure, seeds, input schema, and software versions must be archived before confirmation is opened.

## Dependence, Sampling, and Generalization

The primary uncertainty procedure resamples the relevant image-pair graph components or another pre-specified cluster unit justified by the final graph audit. The analysis also reports a canonical-unordered-pair sensitivity, a query-direction sensitivity where appropriate, an identity-disjoint sensitivity when the identity graph supports it, and descriptor-specific estimates. No bootstrap may treat duplicate directions or shared images as independent without explicitly modelling that dependence.

The 400-pair mechanism sample and 800-pair deployment-queue sample answer different questions. Conditional feature effects and measurement-failure mechanisms are estimated in the mechanism sample. Calibration, risk, coverage, review-budget, and human-time outcomes are estimated only in the probability-sampled deployment queue, with retained inclusion probabilities used when required. The two samples are never pooled without an explicitly pre-specified estimand and weighting scheme.

## Calibration, Actions, and Utility

Calibration is fit on the calibration partition only. The locked policy maps probabilities to `admit`, `expert_review`, and `defer` using an explicit asymmetric loss. The pre-registration manifest states the primary cost ratio, the single principal review-budget or cost region, and the maximum acceptable risk before any outcome review begins. Costs include automated feature computation, observed failure rate, human correction where required, expert-review minutes, defer cost, and incorrect-admission cost. The study may report a sensitivity surface over transparent relative costs but will not invent a field-economic value.

The deployment-queue analysis compares the locked PF-ERI policy with a descriptor-based active policy at the same budget or cost region. It reports coverage, review-ready rate, not-ready or uncertain burden, false-candidate burden as a secondary audit, deferred-pair concentration, measured human minutes, and the uncertainty of each relevant contrast. A policy that appears favourable only in the mechanism sample is not workflow evidence. A policy that lowers invalid reviews but costs more total human time or produces unacceptable admitted-pair risk is reported as a trade-off, not a success.

## Consequential Validity Study

An independent blinded reviewer group assesses a pre-specified deployment-queue subset using a known-identity same/different task, with correctness, confidence, and elapsed time logged. These reviewers do not create the primary reviewability endpoint and do not see route labels. The planned comparison tests whether the locked route states are associated with different human judgement reliability, confidence, or time. The study reports effect sizes and uncertainty, respects pair dependence, and does not interpret this task as automated identity performance.

## Success, Failure, and Reporting

The highest v2 claim requires an auditable measurement gate, successful blind-review audit, a primary full-versus-active-control result that meets the pre-registered Brier-score rule in the confirmation partition, acceptable locked calibration and route performance in the deployment queue, and no unreported reversal in planned dependency or identity-disjoint sensitivity analyses. Descriptor, rank, same/different identity, camera/site, day/night or infrared, laterality, reviewer, and feature-missingness heterogeneity are reported whenever data permit. A pooled result cannot conceal a pre-specified important failure.

The study is `v2_mixed` or `v2_not_confirmed` when the feature measurement fails, the construct is unstable, the primary incremental comparison fails, calibration or risk conditions fail, the representative queue does not show the required utility, or full costs erase the value of routing. The report will distinguish a failed model from a failed measurement. It may describe the negative result and its mechanism, but it may not retune the confirmation set or rename a secondary finding as the primary success. Any such redesign begins PF-ERI v3 with new confirmation data.
