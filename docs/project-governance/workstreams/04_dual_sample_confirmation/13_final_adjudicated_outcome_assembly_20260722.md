# Final adjudicated outcome assembly

Status: **PASS — FORMAL OUTCOMES ACCEPTED AND FROZEN**
Date: 22 July 2026
Applies to: Workstream 04 Task 13

## Purpose and decision

Task 13 converted the completed human response records into one auditable endpoint for each frozen canonical pair. The study owner accepted the returned comma-separated value files as independent human judgements and determined that use of the supplied Streamlit application was not an outcome-admission requirement. Outcome admission therefore depended on exact packet coverage, valid response semantics, preserved assignment and adjudication linkage, and the absence of unresolved technical-problem records. Submission timestamps were excluded from the analytical table and no time, throughput, or cost result was derived from them.

The accepted source contained 4,448 unique first-pass responses covering all 2,224 formal pairs. Every pair had exactly two assigned first-pass responses. The comparison of the three-category decisions identified 250 disagreements, and the adjudication return contained exactly 250 unique responses linked one-to-one to those disagreements. No assigned response was missing, duplicated, or replaced; no unexpected packet was present; every decision, reason, and confidence value satisfied the response schema; and no row retained a technical-problem flag.

## Endpoint derivation

The endpoint derivation followed one deterministic rule. A pair with exact first-pass agreement inherited the agreed three-category decision. A pair with different first-pass decisions inherited the fresh third-person adjudication decision. The final three-category endpoint was then mapped to the primary binary endpoint by assigning `review_ready` to one and grouping `not_review_ready` and `uncertain` as `not_ready_or_uncertain`, assigned to zero for review readiness. The derivation retained both first-pass records, the adjudication record where required, endpoint image identifiers, formal sampling stage, sampling cell, and first-order inclusion probability. It did not retain submission time in the final analytical table.

This procedure produced 2,224 unique final outcomes. The final three-category distribution comprised 1,805 `review_ready`, 321 `not_review_ready`, and 98 `uncertain` pairs. The stage counts remained identical to the formal sampling freeze: 445 development, 445 calibration, 889 deployment-confirmation, and 445 mechanism-confirmation pairs. These counts describe the accepted endpoint data. They do not estimate model accuracy, identity correctness, PF-ERI superiority, calibration, or deployment utility.

## Frozen artifacts and reproducibility

The accepted output is stored at `archive/pferi_v2/task_runs/review/adjudicated_outcomes/`. The file `final_adjudicated_outcomes.csv` contains the 2,224 pair-level endpoints and their response lineage. The file `adjudication_acceptance_disposition.json` records the study-owner acceptance decision, authorizes formal outcome use and model analysis, and declares the collection interface nonbinding. The file `final_outcome_audit.json` records source hashes, row counts, label counts, and the passed integrity checks. `CHECKSUMS.sha256` binds all three outputs. A reproducible builder, `scripts/finalize_v2_adjudication_outcomes.py`, rejects incomplete coverage, duplicate records, invalid decision–reason combinations, unresolved technical problems, inconsistent sampling linkage, or an attempted overwrite.

The outcome assembly passed compilation, focused regression tests, checksum verification, unique-pair reconstruction, adjudication-count verification, and an explicit check that `submitted_at_utc` is absent from the final table. The final disposition is `PASS_OWNER_ACCEPTED_HUMAN_ADJUDICATION`, with `formal_outcome_use_authorized` and `model_analysis_authorized` both set to true.

## Scientific boundary and next gate

Task 13 establishes a reproducible human reviewability endpoint. It does not authorize fitting one model to all 2,224 labels, because the four stages have different information roles. Development outcomes may support model construction; calibration outcomes may be used only after the development specification is frozen; and both confirmation outcome sets must remain excluded from feature engineering, regularization selection, and probability calibration. Task 14 therefore creates stage-isolated analysis inputs before any outcome model is fitted.
