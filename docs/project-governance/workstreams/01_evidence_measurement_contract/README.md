# Workstream 01: Evidence Measurement Contract

Status: contract tasks complete; internal sign-off recorded 2026-07-11; rendered-interface audit remains pending before outcome collection.  
Primary dependency: Workstream 00.  
Exit dependency: Workstream 02 cannot pilot an undefined feature or a reviewer-contaminated construct.

## Purpose

PF-ERI v2 needs a measurement contract before it needs a model. The construct is pair-level evidential admissibility: whether two images contain sufficiently comparable visual evidence for responsible individual-level review. This is not equivalent to generic image quality, descriptor similarity, or an outcome reviewer’s informal impression. The contract turns the construct into observable feature families while preserving a strict separation between feature measurement and the blinded reviewability outcome.

## Procedure

The first step is to freeze a versioned data dictionary for the canonical unordered pair. It defines the two image identifiers, descriptor memberships, queue ranks, similarity values, image availability, source metadata, known identity information held outside the reviewer interface, and every planned feature. Each feature definition states its unit, direction, allowable range, missing-value code, computation method, expected inference-time availability, failure mode, and whether it is automatic, human structural annotation, or metadata. A feature is not accepted merely because it sounds plausible; it must have a measurement procedure that can be audited independently of outcome labels.

The second step is to define the automatic core. Candidate families include animal coverage, resolution, sharpness or exposure, illumination or infrared state, laterality and viewpoint compatibility, visible body-region overlap, visible patterned-area evidence, occlusion, local-match coverage, descriptor disagreement, and uncertainty or failure of the upstream inference component. The contract must name which measures are genuinely independent image-quality controls and which are pair-evidence variables. It may not place a constant proxy, an outcome-reviewer judgement, or a feature available only after expensive manual intervention inside the primary automatic model.

The third step is to define the blinded outcome instrument in semantic terms, not through score thresholds. Outcome reviewers classify a pair as review-ready, not review-ready, or uncertain after seeing only the image pair and neutral response fields. Feature annotators never choose this outcome. The two teams, their interfaces, exported files, and access permissions must be separate. This division is the central defence against the circular claim that PF-ERI predicts labels that its own features already encode.

Task 01 is complete at `01_canonical_unordered_pair_contract.md`. It provides the versioned canonical-pair, directed-membership, and restricted-identity manifests, together with a validator that rejects duplicate pair counting and forbidden outcome or route fields. Task 02 is complete at `02_feature_dictionary_and_failure_taxonomy.md`. It establishes the versioned feature dictionary and makes absence, failure, and low measurement distinct states while excluding oracle and provenance fields from the primary automatic model. Task 03 is complete at `03_independent_image_quality_control_contract.md`. It fixes four automatic image-level controls and their worst-side pair aggregation, excludes pair evidence and manual rescue, and retains infrared as context-only. Task 04 is complete at `04_automatic_pair_evidence_contract.md`. It allows only automatic order-invariant local-match coverage as a primary evidence candidate and reserves descriptor disagreement for diagnostic-only work. Task 05 is complete at `05_blinded_outcome_export_fence.md`. It fixes the reviewer packet and raw-response allowlists, holds linkage in a restricted manifest, and requires an independent rendered-interface leakage audit before any v2 outcome collection.

## Required Artifacts and Exit Decision

The workstream produces a versioned pair-schema document, a machine-readable feature dictionary, a missingness and failure taxonomy, a reviewer-visible outcome definition, and a blinding-field allowlist and denylist. The exit decision records whether every core feature is automatic or has a declared oracle-only role. Internal sign-off is recorded. Workstream 02 may conduct outcome-free feature feasibility work, while a real rendered-interface audit remains mandatory before any v2 outcome collection.
