# Workstream 05: Decision Mathematics and Workflow Validity

Status: not started.  
Primary dependency: Workstream 04 must be `v2_design_locked` before confirmation analysis.  
Exit dependency: Workstream 06 may use only a confirmed and bounded core interface.

## Purpose

This workstream establishes the project’s applied-mathematics contribution without turning PF-ERI into a collection of fashionable algorithms. The model estimates the probability that a pair is review-ready. The decision problem then uses that probability to decide whether to admit the pair, send it to expert review, or defer it. The scientific question is whether this decision improves a specified proper-score and workflow objective beyond descriptor similarity and independent image-quality controls.

## Procedure

Before confirmation labels are opened, freeze the interpretable regularized probability model, its transformations, the independent-quality active control, the automatic pair-evidence inputs that passed Workstream 02, the calibration procedure, and the cluster-aware uncertainty method. The only primary incremental comparison is the full model against descriptor similarity plus independent image quality on identical confirmation rows. The primary measure is change in Brier score, accompanied by its graph-aware 95% interval and the pre-specified minimum practical increment. AUROC, AUPRC, log loss, calibration displays, descriptor-specific estimates, nonlinear models, and oracle-feature comparisons remain secondary unless promoted before review begins.

Next, lock the three-action asymmetric loss for `admit`, `expert_review`, and `defer`. It must count incorrect admission, unnecessary review, unnecessary defer, automatic inference time, feature failure, manual correction where used, and human-review minutes. The project reports transparent relative-cost sensitivity and observed time; it does not invent a conservation monetary value. A claim of conformal or distribution-free risk control is forbidden unless the required calibration split, loss definition, coverage meaning, assumptions, and finite-sample guarantee are actually satisfied.

Finally, run a consequential-validity study on a pre-specified deployment-queue subset. New blinded reviewers complete a known-identity same/different judgement with confidence and elapsed time, without generating the reviewability label or seeing routes. The analysis tests whether locked route states differ in human judgement reliability, confidence, or time. It connects the latent evidence-admission construct to a real human decision while preserving the boundary that PF-ERI itself does not assign identity.

## Required Artifacts and Exit Decision

The workstream produces a frozen modelling specification, a calibration record, action-loss specification, cost and budget sensitivity register, graph-aware inference plan, confirmation report, and consequential-validity analysis. Its exit decision is `v2_confirmed_with_boundaries`, `v2_mixed`, or `v2_not_confirmed`. A route may be called efficient only if the representative deployment sample shows its pre-specified benefit after full feature-acquisition and human-time costs are counted.
