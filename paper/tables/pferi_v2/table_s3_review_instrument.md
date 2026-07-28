# Table S3. Human review instrument and adjudication rules

The endpoint is visual reviewability, not identity truth.

| instrument_item | definition | reviewer_visible_information | role_in_eligibility | role_in_endpoint | analysis_treatment |
| --- | --- | --- | --- | --- | --- |
| review_ready | Pair contains comparable visual evidence for responsible review | Blinded pair imagery and review instrument | Positive Gate-2 state | Binary outcome 0 only when required rule is met | Review-ready |
| not_review_ready | Comparable evidence is insufficient | Blinded pair imagery | Negative Gate-2 state | Maps to outcome 1 | not_ready_or_uncertain |
| uncertain | Reviewer cannot responsibly resolve reviewability | Blinded pair imagery | Conservative non-admission | Maps to outcome 1 | not_ready_or_uncertain |
| reason codes | Structured rationale families | Allowed code list | Descriptive | No direct numerical role | Descriptive only |
| confidence | Reviewer-reported certainty | Low/medium/high field | None | None | Descriptive only |
| technical_problem_flag | Review could not be completed technically | Yes/no | Hard response eligibility | Excluded when yes | Eligibility audit |
| disagreement/adjudication | First-pass labels differ | Fresh blinded adjudication package | Triggers adjudication in formal review | Adjudicated final label | Final frozen outcome |
| timestamp | Submission metadata | Not a scientific criterion | Excluded | None | Descriptive only |
