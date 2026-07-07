# Reason Label Enrichment Packet

Status: `PASS`

This packet mines the existing CzechLynx reviewed-pair databases for pairs that need explicit not-ready reason labels.

## What Was Found

- Total review rows selected: `300`
- Primary not-ready/uncertain targets: `229`
- Borderline review-ready controls: `71`
- Rows with existing reason votes: `46`

The existing database does not contain 300-500 not-ready/uncertain pairs; it currently provides 229 target pairs. The remaining rows are controls for reviewer calibration.

## Outputs

- Queue: `outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_queue.csv`
- Review form: `outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_review_form.csv`
- Codebook: `outputs/modeling-validation/reason-label-enrichment/reason_label_codebook.csv`

## Boundary

Reason-label enrichment supports explanation validation only; no identity assignment or Bobcat identity metric claim.
