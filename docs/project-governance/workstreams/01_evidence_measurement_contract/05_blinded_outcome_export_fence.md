# Task 05: Blinded Outcome-Export Fence

Status: complete. Contract version: `pferi_v2_blinded_outcome_export_contract_v1`.

## Purpose

The v1 review interface exposed assignment-relevant information and therefore made the outcome vulnerable to detection bias. This task builds a field-level fence around v2 outcome review. Reviewers receive images through opaque rendered-asset tokens and a neutral packet identifier, while the canonical pair, source images, reviewer assignment, and batch linkage remain in a separate restricted file. The outcome is a judgement of reviewability, not a response to the model’s own score, route, rank, or identity condition.

## Reviewer, Response, and Restricted Data Boundaries

The reviewer packet has exactly five fields: a neutral packet identifier, two opaque rendered-asset tokens, instrument version, and form-schema version. Its form permits three decision values—`review_ready`, `not_review_ready`, and `uncertain`—and records a reason, confidence, optional note, timestamp, and technical-problem flag in a raw response export. A raw response does not contain the canonical pair identifier, a source image identifier, reviewer assignment, any feature, descriptor, score, rank, route, stratum, identity truth, prior response, majority label, adjudicated label, or model-ready recode.

The restricted linkage is the only place where packet identifier connects to canonical pair, image identifiers, reviewer assignment, and batch. First-pass reviewers and adjudicators receive no prior responses. Majority, adjudicated, recoded, and model-ready labels are derived analysis artifacts and may never be copied back into the raw response file or a reviewer-facing interface.

## Independent Leakage Audit

The machine validator enforces declared column boundaries, but it cannot prove that a browser is blind. Before every collection batch, a non-reviewer must inspect the rendered DOM, URLs and browser state, asset tokens and filenames, exported columns, search/sort/filter controls, network and hidden fields, and the resulting leak-disposition log. A visible or inferable forbidden condition invalidates the affected batch. The response must document exposed records, leakage source, remediation, retest, and final disposition; merely removing a column from an export does not repair a previously exposed outcome batch.

## Validation

`scripts/validate_v2_blinded_outcome_export_contract.py` validates the contract at `schemas/pferi_v2/blinded_outcome_export_contract_v1.json`. It rejects any extra reviewer-facing or raw-response field, including a feature value, candidate rank, canonical linkage, or a derived label. Passing this validator is necessary but not sufficient for collection; the independent rendered-interface audit remains mandatory.

```bash
python3 scripts/validate_v2_blinded_outcome_export_contract.py \
  --contract schemas/pferi_v2/blinded_outcome_export_contract_v1.json \
  --audit-json path/to/blinded_outcome_export_audit.json
```
