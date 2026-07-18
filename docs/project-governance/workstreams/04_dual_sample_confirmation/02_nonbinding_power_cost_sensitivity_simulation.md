# Task 02: Nonbinding Graph-Aware Power and Workload Sensitivity Simulation

Status: complete — outcome-free sensitivity results are archived; no official target, seed, or reviewer packet is authorized.  
Workstream: 04 — Dual-Sample Confirmatory Design.

## Aim

This task asks a bounded planning question: under explicitly synthetic assumptions, how do shared-image dependence, paired Brier-loss variability, practical-effect thresholds, analyzable confirmation size, completion, and reviewer workload alter the plausibility of a precise future primary comparison? It does not estimate PF-ERI’s v2 effect. In particular, the historical v1 model increment is not used as a v2 true effect, and no v2 reviewability label, model probability, calibration result, or reviewer response is read.

## Method

The simulation samples canonical unordered pairs from the frozen 85,182-pair graph. It models a future paired loss difference as Brier(active control) minus Brier(full automatic-evidence model). Two selected pairs that share an image receive correlated synthetic endpoint contributions, so the graph-specific design effect is calculated from sampled endpoint degrees rather than assuming pair rows are independent. A scenario reports the probability that the lower endpoint of a two-sided 95% normal-approximation graph-aware interval exceeds a stated practical Brier increment. The analysis is therefore a dependence-sensitive sensitivity calculation, not a final confidence-interval implementation.

The scenario file deliberately varies practical increments of 0.005 and 0.010, synthetic true increments of 0.010 and 0.020, paired-loss standard deviations of 0.080 and 0.120, joint image-variance fractions from 0.00 to 0.10, and analyzable confirmation counts from 250 to 800. These ranges are neither recommendations nor a hidden freeze. The workload calculation separately converts each analyzable count into a collection reserve under completion assumptions of 0.85, 0.90, and 0.95 and deliberately broad timing illustrations. It reports reviewer minutes and local-match compute minutes, not invented money values or a routing-benefit claim.

## Interpretation boundary

The generated outputs demonstrate how assumptions change required precision and an illustrative operational burden. They cannot determine the true v2 effect, identify the correct practical increment, certify that a particular total sample will succeed, or impose a time budget on the experiment. The later binding simulation must replace the scientific decision inputs with accepted pre-outcome values and make a dated numerical recommendation. Its historical timing columns remain nonbinding context only: the accepted experiment assigns no expected review duration, adjudication rate, total-hour requirement, or collection window. The 400 mechanism plus 800 deployment default is not endorsed, rejected, increased, or reduced here.

## Reproducibility

The nonbinding scenario configuration is `schemas/pferi_v2/nonbinding_power_cost_sensitivity_scenarios_v1.json`, and the executable is `scripts/simulate_ws04_power_cost_sensitivity.py`. Its audit, tables, prose report, and power-curve illustration are archived under `outputs/pferi_v2/dual_sample_confirmation/2026-07-14_nonbinding_power_cost_sensitivity_v1/`. The randomized graph draws use a nonofficial simulation seed and are not an allocation or sampling seed.
