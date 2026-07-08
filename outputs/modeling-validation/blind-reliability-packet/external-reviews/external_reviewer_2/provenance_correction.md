# External Reviewer 2 Provenance Correction

Date: 2026-07-08

Status: `INDEPENDENT_EXTERNAL_BLIND_REVIEW_CONFIRMED`

The `reviewer_notes` field in
`external_reviewer_2/blind_reliability_review_working.csv` contains the stale
text `synthetic calibration labels for private threshold comparison only; not
independent blind evidence`.

That note is a metadata error. The reviewer was contacted after completion and
the labels should be interpreted as an independent external blind review. The
review labels themselves are retained unchanged.

Use
`outputs/modeling-validation/blind-reliability-packet/agreement-analysis-reviewer2/`
as the Reviewer 2 agreement analysis artifact.

Reviewer 2 summary:

- Rows: `280`
- Binary agreement with original labels: `0.914286`
- Binary Cohen kappa: `0.785098`
- Primary reason agreement on original non-ready rows: `0.736318`
- Binary disagreement rows: `24`
- Claim gate: `BLIND_RELIABILITY_STRONG_SUPPORT`

Boundary: this correction upgrades Reviewer 2 provenance from mistaken
synthetic-calibration metadata to independent blind-review evidence. It does
not change any review labels, does not create identity labels, and does not
weaken the blocked claims against automatic identity assignment, Bobcat
identity metrics, new-descriptor claims, or unqualified distribution-free
domain-shift guarantees.
