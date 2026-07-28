# Task 15I Conditional 90% Feasibility Analysis

Status: `FROZEN_CONDITIONAL_90PCT_FEASIBILITY_ANALYSIS`

This analysis isolates the question of what a scientifically independent redevelopment design would require to achieve a conditional probability above 90 percent. It does not estimate the chance that PF-ERI will actually pass. No raw development, calibration, deployment-confirmation, or mechanism-confirmation outcome was read. The calculation uses only the frozen Task 15I design record and stated synthetic assumptions: paired-loss-difference standard deviation 0.12, intracomponent correlation 0.10, four pairs per component, and a synthetic true P3-minus-P5 Brier increment of 0.01.

The first target is a development screen, defined as a design-weighted point estimate reaching the predeclared 0.005 Brier increment. Under the stated assumptions, the smallest independence-first design that exceeds 90 percent is 400 independent endpoint-image components and 1,600 analyzable pairs. Its design effect is 1.30, effective pair count is approximately 1,230.8, and its conditional point-threshold success probability is 0.9281. This is not a forecast that the model has a true increment of 0.01; it is the operating characteristic conditional on that assumption.

The second target is deliberately stricter: a nominal two-sided 95 percent lower confidence bound exceeding 0.005 under the same synthetic true increment. It requires 2,000 independent components and 8,000 analyzable pairs. The conditional lower-bound success probability is 0.9047. The substantial difference between this requirement and the 1,600-pair development screen demonstrates that a development qualification screen must not be described as confirmation power.

The analysis does not alter the Task 15I-A/B contract, which remains frozen at 300 components and 1,200 pairs. To adopt the 400-component, 1,600-pair screen design, the project must create a new prelabel redevelopment contract version and then show that a new image-disjoint and pair-disjoint photo reservoir can supply the required components, strata, component-size cap, and endpoint-degree cap. At least 800 new images are required even in the theoretical two-images-per-component minimum; the actual requirement may be larger. Existing development, calibration, and confirmation images may not be repurposed.

This is the honest route to a conditional development-screen probability above 90 percent. It cannot make a real effect larger. If the true P3-minus-P5 increment is below 0.005, increased sample size will make failure of the predeclared gate more certain rather than create a passing result. Calibration remains locked.

The immutable analysis package is stored at `archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_conditional_90pct_feasibility_analysis_v1/`.
