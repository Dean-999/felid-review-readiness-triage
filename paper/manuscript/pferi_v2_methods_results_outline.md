# PF-ERI v2 Methods and Results outline

Status: completed writing scaffold for the v2 manuscript draft
Evidence cutoff: frozen PF-ERI v2 evidence package through project closure
Display package: `paper/tables/pferi_v2/` and `paper/figures/pferi_v2/`

## Methods outline

### Study design and scientific object

- Define PF-ERI as a post-retrieval, pair-level evidence-admission framework.
- Separate single-image technical quality, directed descriptor similarity, descriptor-relation support, human visual reviewability, and identity truth.
- Define the two gates: same-direction dual-descriptor top-20 support, followed by human reviewability.
- State explicitly that identity accuracy and automatic identity assignment are outside the endpoint.

### Prospective stage separation

- Describe independent development, model freeze, calibration, outcome-free external execution, one-shot outcome analysis, and operational closure.
- State the permitted information and model action at each stage.
- Emphasize that execution PASS/operational CONFIRMED and independent P5 superiority are separate dispositions.

### Human endpoint

- Describe the three-category instrument and the binary mapping.
- Explain first-pass double review and formal adjudication.
- Retain the retrospective human-authorship acceptance and major protocol-deviation disclosure.
- Exclude timestamps from eligibility, time, cost, and statistical analyses.

### Models and preprocessing

- Define P3 as descriptor plus endpoint-quality active control.
- Define P5 as the strict P3 extension containing the local-match pair-evidence block.
- State fixed ridge logistic family, lambda 100, fold-local preprocessing, missing-state encoding, and target orientation.
- State that coefficients were frozen before calibration and confirmation.

### Development qualification

- Report 1,600 pairs, 400 endpoint-disjoint components, five outer folds, and fixed qualification rules.
- Define weighted Brier(P3)-Brier(P5), with positive values favoring P5.
- State the point-estimate and fold-direction requirements.

### Calibration

- Describe the independent 448-pair sample and stored intercept/slope transform.
- State that calibration did not change predictors, coefficients, lambda, or model selection and created no action threshold.

### External execution and support gate

- Describe 889 candidates and 815 images.
- Define `both_reciprocal`, `both_agreement`, and the exact unsupported reason.
- Restrict quality, local-match scoring, and calibrated prediction accounting to the frozen supported path.
- State that outcomes remained sealed during execution.

### Independent outcome analysis

- Restrict the estimand to 252 supported pairs.
- Use Hajek-normalized inverse-probability weighting.
- Use physical endpoint images as dyad members in the cluster-robust interval.
- Define the frozen success criterion as lower 95% interval endpoint greater than 0.005.
- State that no model or calibration parameter was recomputed.

### Reproducibility and reporting

- Link every paper claim to the hash-bound source manifest.
- Report editable tables, vector figures, deterministic builders, tests, and checksums.
- Use TRIPOD-style prediction-model reporting with STROBE-relevant sample-flow and provenance elements.

## Results outline

### Sample flow and human endpoint distribution

- Development: 448/1,600 review-ready.
- Calibration: 86/448 review-ready.
- Full external queue: 712/889 review-ready.
- Supported external subset: 218/252 review-ready.
- Distinguish the prevalence shift from a causal explanation.

### Human agreement and provenance

- Report stage-specific exact agreement, binary agreement, and binary kappa.
- State that low development agreement is a measurement limitation, not reviewer failure.
- State that formal disagreements were adjudicated.
- Disclose retrospective authorship acceptance and major protocol deviation.

### Development and freeze

- Report P3 and P5 weighted Brier scores, +0.005863 increment, and 5/5 nonnegative folds.
- Report P3/P5 freeze at lambda 100 and strict nesting.

### Calibration

- Report class balance, convergence, exact stored intercepts/slopes, valid probabilities, and 2,000 bootstrap replicates.
- Avoid external-performance language.

### External execution

- Report 252/889 supported, including 109 reciprocal and 143 same-direction agreement pairs.
- Report 637 unsupported pairs with the exact descriptor reason.
- Report 815 verified images, 252 complete local-match rows, and 504 predictions.

### Independent comparison

- Report P3 Brier 0.307246 and P5 Brier 0.509116.
- Report difference -0.201870 and dyadic 95% interval [-0.224671, -0.179068].
- State that the frozen success criterion failed and P5 superiority did not reproduce.

### Bounded disposition

- Preserve the development qualification as a development result.
- Report outcome comparison as negative.
- Report operational CONFIRMED/CLOSED only for external execution validation.
- Prohibit identity-accuracy, universal deployment-utility, automatic-assignment, and Bobcat-transfer claims.
