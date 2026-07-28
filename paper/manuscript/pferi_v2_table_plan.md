# PF-ERI v2 table plan

Status: manuscript planning scaffold
Date: 2026-07-28
Evidence map: `paper/supplement/source_data/pferi_v2/`

## Design principle

The tables should make the pair-level logic, information boundaries, and evidence strength readable without requiring the reader to reconstruct the Task15 sequence. The main manuscript should use six tables. Fourteen supplementary tables should preserve exact definitions, coefficients, agreement details, provenance, and reproducibility evidence. This is deliberately more complete than a minimal journal package; after a target journal is selected, tables can be combined without dropping source data.

Every table must distinguish three concepts: descriptor-relation support, human visual reviewability, and identity truth. The terms `supported` and `unsupported` must always identify the relevant gate. The 637 Task15M descriptor-unsupported pairs must never be presented as 637 human-not-review-ready pairs.

## Main manuscript tables

### Table 1. Prospective study architecture and information boundaries

Purpose: establish that development, model freeze, calibration, execution validation, and outcome confirmation had different roles. This table is the reader's map of the study.

Recommended columns:

| column | content |
| --- | --- |
| Stage | Development; model freeze; calibration; external execution; independent outcome analysis; operational closure |
| Scientific purpose | What question the stage answered |
| Pair source | Independent redevelopment reservoir, calibration partition, or deployment-confirmation queue |
| Pair count | Planned, available, supported, and analyzed counts where applicable |
| Outcome access | Sealed, available for fitting, or opened once for final analysis |
| Permitted model action | Fit, freeze, calibrate intercept/slope only, score only, or analyze only |
| Dependency control | Endpoint-disjoint components or dyadic endpoint-aware interval |
| Primary output | Exact frozen status or estimand |
| Permitted claim | Development qualification, calibration completion, execution integrity, or outcome confirmation |

Required rows:

1. Task15I development: 1,600 pairs in 400 endpoint-disjoint components.
2. Task15J freeze: P3/P5, lambda 100, fixed preprocessing.
3. Task15L calibration: 448 pairs; intercept/slope calibration only.
4. Task15M/15N execution: 889 candidates; 252 descriptor-supported; 637 descriptor-unsupported.
5. Independent outcome analysis: 252 supported pairs; one-shot frozen comparison.
6. Project closure: `CONFIRMED/CLOSED` on Task15M execution-validation scope.

Primary sources: `TASK15I_RESULT_FREEZE`, `TASK15J_MODEL_FREEZE`, `TASK15L_CALIBRATION_FREEZE`, `TASK15N_EXECUTION_FREEZE`, `PRIMARY_CONFIRMATION_RESULT`, and `PROJECT_CLOSURE_RECORD`.

Footnote requirement: operational `CONFIRMED` is not P5 superiority or identity validation.

### Table 2. The pair as the scientific object: two gates and adjacent concepts

Purpose: carry the central novelty. This table must show why single-image quality, descriptor similarity, pair support, reviewability, and identity truth are not interchangeable.

Recommended columns:

| column | content |
| --- | --- |
| Concept | Single-image technical quality; descriptor similarity; descriptor-relation support; visual reviewability; identity truth |
| Unit | Image, directed retrieval, unordered image pair, or known-identity relation |
| Information used | Pixels, descriptor ranks/scores, cross-descriptor direction, or blinded human visual evidence |
| Decision question | The exact question answered by the concept |
| Positive state | What a positive or supported state means |
| Negative state | What failure means |
| Role in PF-ERI | Predictor, eligibility gate, endpoint, or audit-only truth |
| Not equivalent to | The neighboring concept that must not be inferred |

Required distinctions:

1. Technical image quality asks whether an image can be decoded and measured.
2. Descriptor similarity asks whether one image retrieves another highly.
3. Gate 1 asks whether MegaDescriptor and DINOv2 form the frozen same-direction top-20 pair relation.
4. Gate 2 asks whether the two photographs contain comparable visual evidence for responsible human review.
5. Identity truth asks whether the images depict the same individual and is not the primary PF-ERI endpoint.

Primary sources: `PROJECT_RULES`, `REVIEWER_GUIDELINES`, `TASK15M_CONFIRMATION_CONTRACT`, and `TASK15M_DESCRIPTOR_PAIR_MEASUREMENTS`.

Footnote requirement: a different-identity pair may be review-ready when the visible evidence supports a responsible rejection.

### Table 3. Pair inventories, support, and endpoint distributions by stage

Purpose: show the data flow and distribution shift numerically. This table supplies exact values corresponding to the study-flow and transport figures.

Recommended columns:

| column | content |
| --- | --- |
| Stage or subset | Development; calibration; Task15M full queue; descriptor-supported subset; descriptor-unsupported subset |
| Candidate pairs | All pairs entering that stage |
| Analyzable/scored pairs | Pairs with the stage's required data |
| Unique endpoint images | When available |
| Endpoint components | When applicable |
| `review_ready`, n (%) | Human endpoint count and percentage |
| `not_ready_or_uncertain`, n (%) | Human endpoint count and percentage |
| Descriptor-supported, n (%) | Gate 1 result |
| Descriptor-unsupported, n (%) | Gate 1 result |
| Sampling/weighting role | Development weight, calibration role, or deployment inclusion probability |

Known principal values:

- Development: 1,600 pairs; 448 review-ready; 1,152 not-ready-or-uncertain; 400 components.
- Calibration: 448 pairs; 86 review-ready and 362 not-ready-or-uncertain under the stored label orientation.
- Task15M queue: 889 candidate pairs.
- Task15M descriptor support: 252 supported and 637 unsupported.
- Supported confirmation outcomes: 218 review-ready and 34 not-ready-or-uncertain.

The full-queue and descriptor-unsupported human endpoint counts must be generated through the frozen Task15M linkage and independently audited before entering the table. They must not be inferred by subtraction without checking one-to-one linkage.

Primary sources: `TASK15I_PAIR_LABELS`, `TASK15L_CALIBRATION_FREEZE`, `TASK15M_DESCRIPTOR_PAIR_MEASUREMENTS`, `FINAL_ADJUDICATED_OUTCOMES`, and `PRIMARY_CONFIRMATION_RESULT`.

Footnote requirement: endpoint prevalence is descriptive and cannot by itself prove the cause of performance transport failure.

### Table 4. Nested P3 and P5 model specification

Purpose: demonstrate that P5 is a strict pair-evidence extension of the active P3 control rather than a differently tuned model.

Recommended columns:

| column | content |
| --- | --- |
| Feature family | Descriptor, independent image quality, pair evidence, missing-state indicators |
| Feature or transformed block | Exact frozen name or concise family name |
| Unit | Image, pair, rank, percentile, or measurement-failure state |
| P3 active control | Included or excluded |
| P5 full model | Included or excluded |
| Availability timing | Automatically available before human outcome review |
| Transformation | Standardization, indicator encoding, or frozen mapping |
| Missingness handling | Frozen explicit state or training-fold imputation |
| Interpretation | What information the feature contributes |

Required summary rows:

1. Descriptor similarity/rank representation: P3 and P5.
2. Descriptor support category: P3 and P5.
3. Independent endpoint quality percentiles: P3 and P5.
4. Quality stress/failure indicators: P3 and P5.
5. Local-match coverage and failure states: P5 only.
6. Model family and lambda: identical ridge logistic model; lambda 100.
7. Calibrated probability target: probability of `not_ready_or_uncertain`.

Primary sources: `TASK15J_MODEL_FREEZE`, `TASK15J_MODEL_BUNDLE`, and the frozen feature-preprocessing contract referenced by Task15J.

Footnote requirement: full coefficients belong in Table S7, not the main table.

### Table 5. Development, calibration, execution, and independent outcome results

Purpose: present the complete evidence sequence in one numerical table without treating all stages as equivalent performance tests.

Recommended columns:

| column | content |
| --- | --- |
| Stage | Task15I development, Task15L calibration, Task15M execution, independent outcome analysis |
| Sample | Pair count and relevant support restriction |
| P3 Brier | Report only where an outcome-performance estimate is authorized |
| P5 Brier | Report only where an outcome-performance estimate is authorized |
| P3-P5 Brier increment | Positive favors P5 |
| 95% interval | Use only when frozen and available |
| Decision threshold | Development point threshold or confirmation lower-bound threshold |
| Stability/coverage evidence | Fold direction or supported-pair count |
| Frozen result | Exact status |
| Interpretation | Development, calibration, execution, or confirmation scope |

Required numerical rows:

1. Task15I pooled development: P3 0.194909; P5 0.189046; increment 0.005863; five of five fold increments nonnegative.
2. Task15I folds 0-4: optional compact subrows or refer to Table S5.
3. Task15L calibration: status `PASS`; no external P3-versus-P5 performance claim.
4. Task15M execution: 889 candidates; 252 supported; 637 unsupported; 504 predictions; status `PASS_TASK15M_EXECUTION_VALIDATION`.
5. Independent outcome analysis: P3 0.307246; P5 0.509116; increment -0.201870; dyadic 95% interval [-0.224671, -0.179068].

Primary sources: `TASK15I_RESULT_FREEZE`, `TASK15I_FOLD_RESULTS`, `TASK15L_CALIBRATION_FREEZE`, `TASK15N_EXECUTION_FREEZE`, and `PRIMARY_CONFIRMATION_RESULT`.

Footnote requirements: Brier score is lower-is-better; the reported increment is Brier(P3)-Brier(P5), so positive values favor P5. Blank calibration and execution performance cells must be displayed as `not an outcome-performance stage`, not zero or missing.

### Table 6. Evidence-to-claim matrix

Purpose: end the main Results or begin the Discussion with a transparent statement of what the study establishes.

Recommended columns:

| column | content |
| --- | --- |
| Claim | Concise manuscript-facing claim |
| Evidence stage | Task or source group |
| Disposition | Supported, supported with boundary, supported negative result, or prohibited |
| Quantitative basis | The central number or audit result |
| Permitted wording | Sentence that may appear in the paper |
| Prohibited extension | Stronger statement not supported by evidence |

Required rows:

1. Candidate pair is the scientific object.
2. Descriptor support and visual reviewability are distinct pair gates.
3. P5 passed Task15I development qualification.
4. P3/P5 models and calibration were frozen reproducibly.
5. Task15M execution and pair-support accounting passed.
6. P5's development increment did not reproduce in the independent comparison.
7. Human outcomes are accepted with a major protocol-deviation disclosure.
8. Identity accuracy, deployment utility, universal risk control, and Bobcat validation are not established.
9. Project closure is operationally confirmed within the Task15M execution-validation scope.

Primary source: `claim_evidence_map.csv`, backed by its 26 hash-bound source files.

## Supplementary tables

### Table S1. Dataset provenance, licenses, and access restrictions

Columns: dataset or reservoir, species, source institution, license, image count, identity availability, geographic sensitivity, publication permission, repository access class, and manuscript role. This table must separate public metadata, restricted imagery, and internal identity linkage.

### Table S2. Pair sampling frames and non-overlap checks

Columns: stage, source reservoir, selection rule, pair count, endpoint-image count, component count, pair overlap with earlier stages, endpoint overlap, identity overlap where auditable, seed, sampling probability, and audit status. This table supports the claim that development, calibration, and confirmation roles were not row-random splits.

### Table S3. Human review instrument and adjudication rules

Rows: `review_ready`, `not_review_ready`, `uncertain`, reason-code families, confidence field, technical-problem flag, disagreement trigger, adjudication rule, timestamp policy, and final binary mapping. Columns should include definition, reviewer-visible information, role in eligibility, role in endpoint construction, and analysis treatment.

### Table S4. Reviewer agreement and endpoint reliability by stage

Columns: stage, pair count, first-pass response count, three-category exact agreement, binary agreement, chance-corrected agreement, confidence interval if prespecified, disagreement count, adjudication count, and interpretation. Task15I, Task15L, and formal confirmation must be shown separately. Any currently recomputed agreement values require a new deterministic derivation script and hash-bound audit before inclusion.

### Table S5. Task15I component-disjoint fold results

Columns: outer fold, validation pair count, validation component count, P3 Brier, P5 Brier, P3-P5 increment, direction, endpoint leakage count, and fixed lambda. Include all five folds and the pooled row. This table is the exact numerical companion to Figure 3.

### Table S6. Complete predictor and preprocessing dictionary

Columns: source field, scientific family, unit, raw type, transformation, training-fold statistic, missing-state encoding, P3 inclusion, P5 inclusion, outcome availability prohibition, and interpretation boundary. This should be generated from the frozen feature contract rather than manually copied.

### Table S7. Frozen P3 and P5 coefficients

Columns: model, transformed feature, coefficient, intercept indicator, lambda, coefficient scale, source bundle field, and interpretation note. Coefficients should be reported exactly enough for reproducibility but should not be interpreted causally.

### Table S8. Task15L calibration details

Columns: model, calibration pair count, class counts, raw probability range, intercept, slope, convergence status, bootstrap replicates, calibrated-probability validity, model refit, feature change, lambda change, and threshold creation. This table must explicitly state that no action threshold was created.

### Table S9. Task15M descriptor pair-support taxonomy

Rows: `both_reciprocal`, `both_agreement`, and `unsupported`. Columns: formal definition, required directed top-20 relation, pair count, percentage of 889, scoring eligibility, local-match measurement eligibility, prediction count, and interpretation. The unsupported reason should be reported exactly as `no_same_direction_dual_descriptor_top20_consensus`.

### Table S10. Technical measurement completeness and failure inventory

Columns: measurement family, expected unit, expected count, observed count, missing count, failure-code distribution, hash audit, shape audit, and downstream consequence. Rows should include image decode/quality, MegaDescriptor embeddings and scores, DINOv2 embeddings and scores, local matching, score inputs, and calibrated predictions.

### Table S11. Endpoint prevalence and transport diagnostics

Columns: stage/subset, pair count, review-ready count and percentage, not-ready-or-uncertain count and percentage, descriptor-support composition, median P3 probability, median P5 probability, probability range, and role in analysis. This table is descriptive. It must not present base-rate shift as a proven causal mediation analysis.

### Table S12. Pair-level confirmation loss diagnostics

Columns: summary group, pair count, weighted mean P3 loss, weighted mean P5 loss, P3-P5 difference, number of pairs favoring P3, number favoring P5, inclusion-weight effective sample size, endpoint count, maximum endpoint degree, independent-row SE diagnostic, and dyadic SE. Preplanned primary results must be visually separated from post hoc diagnostics.

### Table S13. Human provenance and protocol-deviation register

Columns: issue, stage detected, original audit disposition, retained evidence, retrospective resolution, fields accepted, fields excluded, effect on analysis, disclosure wording, and whether fully clean preregistered confirmation is authorized. This table should include release authorization timing, browser-audit version mismatch, timestamp exclusion, and retrospective authorship attestations.

### Table S14. Reproducibility environment and artifact integrity

Columns: component, script, environment/runtime, dependency version, input contract, input SHA-256, output artifact, output SHA-256, deterministic seed where applicable, automated test, and verification status. Include the manuscript source manifest itself and the exact command used to regenerate each display item.

## Optional extended tables

If the journal permits extensive online supplements, add two further tables.

### Table S15. Sensitivity and alternative-analysis registry

List every planned and exploratory sensitivity, its information-access timing, eligibility for primary inference, result status, and reason for inclusion or exclusion. Historical v1, Task15F Bayesian models, Task15G exploratory models, and any unweighted confirmation diagnostic must be clearly labelled non-primary.

### Table S16. Manuscript number-to-source trace

Columns: manuscript section, paragraph or display item, reported number, exact JSON field or CSV aggregation, source ID, source path, SHA-256, generation command, and verification status. This is primarily an internal submission audit but can be shared as an open-science supplement.

## Table production order

1. Produce Table 1 and Table 2 first because they freeze terminology and the scientific story.
2. Generate Table 3 from the linked stage inventories and outcomes; independently audit every count.
3. Generate Table 4 and Tables S6-S8 directly from frozen model and calibration artifacts.
4. Generate Table 5 and Table S5 from the frozen Task15I and independent outcome records without refitting.
5. Generate Tables S9-S12 from Task15M pair-support, prediction, outcome, and loss files.
6. Generate Table 6 from the hash-bound claim evidence map.
7. Complete provenance, reproducibility, and traceability Tables S1-S4 and S13-S16.

## Formatting rules

Use six decimal places for primary Brier values and intervals in source tables, with three to six decimals in the main manuscript according to journal style. Always state that lower Brier is better and that P3-minus-P5 positive values favor P5. Report counts with percentages using the count as the denominator anchor. Use `not applicable` for metrics that were not authorized at a stage; do not use zero. Define P3, P5, PF-ERI, CI, and effective sample size in every table where they appear. Tables must remain editable CSV/Markdown or journal-table source, not raster images.

## Journal compression option

If the target journal permits only four main tables, combine Table 1 with Table 3, and combine Table 5 with Table 6. Do not combine Table 2 with the model-specification table: the scientific construct and the predictive implementation are different contributions and should remain visibly separate.
