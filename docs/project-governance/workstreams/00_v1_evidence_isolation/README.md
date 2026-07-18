# Workstream 00: V1 Evidence Isolation

Status: `isolated_with_provenance_pending`.  
Primary dependency: none.  
Exit dependency: Workstreams 01–05 may not use v1 labels or v1 outcomes as prospective evidence.

## Purpose

This workstream protects the credibility of PF-ERI v2 by separating exploratory v1 evidence from prospective v2 evidence. The historical 400-row review table contains valuable clues about failure modes, but it has known weaknesses: non-strict blinding, duplicated physical pairs, incomplete feature variation, and unreliable provenance for some reported agreement results. The correct scientific response is preservation with quarantine, not deletion or retrospective relabelling.

## Procedure

First, create a read-only v1 inventory that names every historical candidate-pair table, raw review form, derived label table, model output, route output, figure, reviewer-agreement result, and manuscript paragraph that depends on the 400-row material. Every item receives an immutable identifier, cryptographic hash where practical, origin path, date, and one of three roles: source record, exploratory analysis, or presentation copy. The inventory must explicitly distinguish raw reviewer records from derived majority labels.

Second, add a visible `v1_exploratory_not_confirmatory` marker to every currently active entry point that could otherwise be read as a final result. The marker must state that v1 may inform feature design, sampling simulations, and historical narrative but cannot enter a v2 development, calibration, confirmation, reviewer-reliability, workflow-utility, or external-validation estimate. Existing numbers are not rewritten to look less problematic; they are retained with their original provenance and limitations.

Third, produce a provenance-resolution register for the synthetic reliability result and the claimed external-review result. The synthetic result is permanently excluded from claims about human agreement. The external-review result remains `provenance_pending` until a reviewer attestation, raw submitted form, timestamp record, interface version, and exact reviewed-pair linkage are independently checked. Missing provenance is a finding, not an invitation to reconstruct certainty.

## Required Artifacts and Exit Decision

The workstream requires an immutable v1 inventory, a claim-bearing-file audit, a provenance-resolution register, and a scan confirming that current project entry points use the correct v1 status. These artifacts now exist in this directory. Run `verify_v1_evidence_inventory.sh` from the repository root or from this folder before relying on the inventory; it verifies the stored SHA-256 anchors without altering any source record. The exit decision is `isolated`, `isolated_with_provenance_pending`, or `blocked_by_missing_source_records`. The current decision is `isolated_with_provenance_pending`: reviewer-2 provenance remains unresolved, but no v1-derived outcome or apparent success result is positioned as a v2 prerequisite. Workstream 01 may begin.
