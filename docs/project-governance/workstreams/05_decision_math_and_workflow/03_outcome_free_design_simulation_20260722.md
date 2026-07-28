# Task 03: Outcome-Free Three-Stage Design Simulation

Status: **COMPLETE — EXECUTION PASS; CONDITIONAL STRATEGY SELECTED; NO REAL MODEL FIT**
Date: 22 July 2026
Applies to: Workstream 05 / development Task 15B

## Scientific question

This task asks a design question, not an outcome question: under declared synthetic mechanisms, which registered training-weight strategy is least fragile when the complete PF-ERI workflow is reproduced? The workflow is three-stage by construction. Synthetic development outcomes fit the candidate models, separately generated synthetic calibration outcomes fit intercept-and-slope recalibrators, and the calibrated probabilities are evaluated against known synthetic truth over the confirmation-role covariate frame.

The simulation does not estimate PF-ERI performance. It does not use an observed reviewability label, select a fitted real-data model, open a locked outcome stage, or establish that any synthetic mechanism is true.

## Why all 28,295 pairs are used

The outcome-free master frame contains 28,295 within-role pairs: 9,445 development, 9,433 calibration, and 9,417 confirmation. Formal selection contributes 445 development and 445 calibration rows. Each replicate therefore:

1. generates synthetic truth over the full 28,295-row covariate frame;
2. fits active-control and full candidate models on the 445 formally selected development rows;
3. fits independent logistic recalibrators on the 445 formally selected calibration rows; and
4. evaluates calibrated predictions against synthetic truth on all 9,417 confirmation-role rows.

The first implementation (`v1`) evaluated raw development-fit probabilities against a development target. It is retained as a diagnostic artifact, but its calibration-slope gate did not represent the registered independent-calibration workflow. The corrected `v2` does not overwrite or reinterpret that run.

## Frozen stress design

Ten mechanisms were evaluated with 40 independently seeded replicates and five registered routes, giving 2,000 route–scenario–replicate rows. The mechanisms cover null, weak and moderate evidence increments, smooth nonlinearity, descriptor/evidence redundancy, a quality-by-evidence interaction, quasi-separation, informative matcher failure, shared-image random effects, and sampling-cell calibration shift.

Qualification precedes performance comparison. A route must satisfy the frozen fit-failure, null false-promotion, and worst-scenario median calibration-slope gates. Only qualified ridge routes may enter the minimax Brier-regret decision. Restricted splines remain challengers and cannot replace the primary family.

## Result

The execution audit passed:

- 28,295 outcome-free rows read;
- 445 synthetic-development training rows;
- 445 independent synthetic-calibration rows;
- 9,417 confirmation-role evaluation rows;
- 2,000 of 2,000 expected metric rows written;
- zero recorded fit failures;
- zero observed outcome columns read;
- checksum verification passed for every generated artifact.

The frozen rule selected `ridge_sqrt_ipw_sensitivity`, corresponding to square-root inverse-probability training weights within the frozen ridge family. Its worst-scenario median Brier regret was 0.0256831, its worst-scenario median absolute calibration-slope error was 0.342732, and its null false-promotion rate was 0. The calibration-slope limit was 0.35. It was the only registered primary-pool route to qualify: unweighted ridge had slope error 0.410503, and Hájek-IPW ridge had 0.466326.

This is a conditional design selection, not proof that square-root weighting is truly superior. The qualifying margin is only 0.007268 below the slope-error boundary, and the registry uses 40 Monte Carlo replicates. Individual-replicate calibration estimates also have extreme tails even though the frozen decision uses scenario medians. These facts make the choice appropriate for the next registered development comparison, but too fragile to support a standalone performance claim.

## Adversarial appraisal

### Strengths

- The complete development–calibration–confirmation logic is simulated instead of judging raw training predictions.
- The actual covariate, missingness, sampling-probability, sampling-cell, and shared-endpoint structure is preserved without reading labels.
- Null-increment and failure mechanisms directly challenge spurious evidence promotion.
- The primary family cannot be displaced by a flexible challenger after seeing favorable results.
- Source registries, runner snapshot, input hashes, outputs, audit, and checksums are retained together.

### Critical claim boundary

Synthetic truth is an assumption-defined counterfactual. Passing it cannot demonstrate real discrimination, calibration, causal validity, conservation benefit, cross-species transfer, or deployment utility. Those claims require the locked real-data stages.

### Important weaknesses

- The selected route is close to the frozen calibration threshold; Task 15C and the real development comparison must treat the weighting choice as a registered candidate strategy, not as a proven winner.
- Forty replicates provide a reproducible design screen but do not eliminate Monte Carlo uncertainty around a near-boundary qualification.
- The scenario registry is broad but not exhaustive. Unrepresented shifts or measurement errors may reverse the ranking.
- Extreme individual-replicate calibration slopes show that median qualification can coexist with unstable tails. Tail diagnostics must remain visible in later reporting.

### Minor engineering observation

The optimizer emitted floating-point boundary warnings during some internal line-search proposals. Final stored numeric metrics were finite, all 2,000 rows completed, and checksum validation passed. The frozen runner snapshot preserves this behavior for audit. These warnings should not be misreported as fit failures, but later production code should silence only expected exploratory warnings or record optimizer diagnostics without changing the mathematical objective.

## Artifacts

- DGP base registry: `schemas/pferi_v2/model_design_dgp_registry_v1.json`
- Three-stage overlay: `schemas/pferi_v2/model_design_dgp_registry_v2.json`
- Runner: `scripts/simulate_pferi_v2_model_design.py`
- Tests: `tests/test_simulate_pferi_v2_model_design.py`
- Consolidated task: `archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/`
- Corrected frozen run: `archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/current/`
- Retained diagnostic run: `archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/iterations/v1/`

## Verification

- Python compilation: PASS.
- Focused tests: 8/8 PASS.
- Focused branch-aware coverage: 83%.
- Full simulation row-count audit: PASS, 2,000/2,000.
- Final numeric metric finiteness: PASS.
- Generated-artifact checksum audit: PASS, 8/8.
- Real outcomes used: false.

## Next gate

Task 15C must construct deterministic endpoint-component-disjoint nested folds for the 445 development pairs. No row-random split is allowed. The selected square-root-IPW ridge strategy may proceed into the registered comparison, but it cannot bypass fold feasibility, feature-support, stability, or real-development qualification gates. Calibration and confirmation outcomes remain locked.
