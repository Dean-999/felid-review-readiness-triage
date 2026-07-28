# PF-ERI v2 Introduction and Discussion outline

Status: completed literature-backed writing scaffold
Literature verification: `sources/2026-07-28_pferi_v2_literature_verification.md`

## Introduction outline

### Context

- Camera traps and large image collections make individual-animal identification important but operationally difficult.
- Modern animal Re-ID provides strong descriptors, toolkits, fusion methods, and expanding benchmarks.
- Identity ranking performance does not by itself determine whether a particular pair contains comparable evidence for human review.

### Adjacent concepts and gap

- Biometric quality usually evaluates sample utility; visibility-aware Re-ID models common visible regions; selective prediction provides abstention and risk-coverage concepts.
- These established ideas motivate PF-ERI but do not make descriptor support, pair reviewability, and identity truth equivalent.
- Avoid an absolute first claim; state that targeted searches found no direct equivalent principal endpoint.

### Study contribution and questions

- Define the pair-level evidence-admission task and two gates.
- Compare strict nested P3/P5 models.
- Separate development, freeze, calibration, external execution, and one-shot independent outcome analysis.
- Ask whether pair evidence qualifies in development, executes reproducibly, and reproduces independently.

## Discussion outline

### Principal findings

- Pair-level task and execution framework were successfully operationalized.
- P5 achieved a small, stable development increment.
- Independent result strongly favored P3; superiority did not reproduce.
- Execution validation and independent performance must remain separate.

### Interpretation relative to literature

- PF-ERI complements rather than replaces MegaDescriptor, DINOv2, WildFusion, and benchmarks.
- PF-ERI is related to sample quality and visibility-aware Re-ID but treats reviewability as a pair endpoint.
- PF-ERI resembles reject-option systems in workflow role but does not provide formal risk guarantees.

### Possible explanations, not causal findings

- Outcome prevalence changed substantially.
- External analysis was restricted to 252 descriptor-supported pairs.
- Calibration and feature distributions may have transported poorly.
- Low development agreement indicates endpoint uncertainty.
- Do not select one explanation post hoc as proven.

### Strengths

- Strict nesting, fixed lambda, stage isolation, endpoint-aware folds and intervals, one-shot outcome opening, hashes, deterministic tables and figures.
- Transparent reporting of negative independent result and provenance deviations.

### Limitations

- Human endpoint uncertainty and retrospective provenance resolution.
- Only 28.3% of external candidates entered the supported scoring path.
- No identity-accuracy or downstream ecological endpoint.
- No causal transport analysis, no Bobcat transfer evidence, no deployment-utility study.

### Implications and next study

- Retain the task definition; do not retain a P5 superiority claim.
- Improve endpoint definition and reviewer training while modeling disagreement explicitly.
- Broaden descriptor-support coverage or specify deferral as an explicit workflow action.
- Predefine recalibration/transport diagnostics and power an independent study around the external prevalence.
