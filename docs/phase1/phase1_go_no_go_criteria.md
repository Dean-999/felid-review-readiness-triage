# Phase 1 Go / No-Go Criteria

## Purpose

This document defines the decision gates for completing Phase 1 and deciding whether the project can move into embedding extraction and quantitative validation.

No model code, embedding extraction, or website work should begin until Phase 1 passes.

## Phase 1 Goal

Phase 1 goal:

```text
Data Access and Triage Rubric
```

Phase 1 must confirm:

- CzechLynx data can be legally and practically used;
- the review-readiness rubric is operational;
- CzechLynx sampling can support known-ID validation;
- UWIN/WildTrax can support field triage only;
- Marbled Cat remains future application only;
- risks and boundaries are documented.

## Required Phase 1 Files

Phase 1 is complete only when these files exist and are reviewed:

1. `triage_rubric.md`
2. `czechlynx_data_access_notes.md`
3. `czechlynx_sampling_plan.md`
4. `wildtrax_field_triage_plan.md`
5. `marbled_cat_application_readiness_note.md`
6. `phase1_go_no_go_criteria.md`

Recommended additional file:

7. `daily_work_log.md`

## Gate 1: CzechLynx Access

### Go

Proceed if:

- CzechLynx images are accessible;
- metadata is accessible;
- verified individual IDs are accessible;
- image paths can be mapped to metadata;
- license is located;
- citation is recorded;
- research use is permitted;
- enough repeated individuals exist for same-individual pairs.

### Conditional Go

Proceed only with limited pilot if:

- dataset is accessible but public display permission is unclear;
- some metadata is missing but image paths and IDs are usable;
- sample size must be reduced;
- split files are unavailable but ID labels are sufficient for pilot validation.

### No-Go

Stop if:

- individual IDs are unavailable;
- license cannot be located;
- license does not permit research use;
- image files cannot be joined to metadata;
- dataset access violates platform or author rules.

## Gate 2: Rubric Usability

### Go

Proceed if:

- three labels are defined;
- supporting fields are defined;
- labels can be assigned without viewing individual IDs;
- ambiguous cases can be handled as review-limited or uncertainty-flagged;
- the rubric can be applied to CzechLynx and WildTrax/UWIN images.

### Conditional Go

Proceed with revision if:

- labels work but some fields are unclear;
- many cases fall into review-limited;
- second-review disagreement is moderate but explainable;
- night IR or partial-body cases need more guidance.

### No-Go

Stop and revise if:

- review-ready is assigned based on vague impression;
- species-level tagging is confused with individual-level readiness;
- unidentifiable is used inconsistently;
- the reviewer cannot explain label decisions;
- individual ID is needed to assign readiness.

## Gate 3: CzechLynx Sampling

### Go

Proceed if:

- pilot sample includes 100-200 images if feasible;
- sample includes multiple individuals;
- sample includes repeated individuals;
- sample includes variation in lighting, view, occlusion, blur, body region, and pattern visibility;
- triage sheet hides individual IDs;
- second-review subset is defined.

### Conditional Go

Proceed with a reduced pilot if:

- only 50-100 images can be sampled initially;
- repeated individuals are fewer than expected;
- some metadata fields are missing but IDs are usable.

### No-Go

Stop and redesign if:

- sample has only clean images;
- sample has too few repeated individuals for later validation;
- individual IDs remain visible during triage;
- no low-readiness images are included.

## Gate 4: WildTrax/UWIN Field Triage

### Go

Proceed if:

- field images can be viewed;
- sample size target is defined;
- species labels are available;
- metadata availability is recorded;
- absence of verified individual IDs is documented;
- public display permission is tracked;
- output is limited to triage distribution and failure modes.

### Conditional Go

Proceed if:

- public display permission is unclear but internal review is allowed;
- sample is small but useful for field motivation;
- exact location metadata must be generalized.

### No-Go

Stop if:

- field images cannot be used even internally;
- project would need to claim identity validation from WildTrax;
- public display would violate project or platform rules.

## Gate 5: Marbled Cat Future Application

### Go

Proceed if:

- Marbled Cat is explicitly future application only;
- future data requirements are listed;
- no current validation claim is made;
- threshold transfer is rejected;
- species-specific calibration is required.

### No-Go

Stop and revise if:

- Marbled Cat is written as current validation;
- CzechLynx results are treated as directly transferable;
- population or identity claims are made.

## Final Phase 1 Decision Table

| Gate | Status | Decision |
|---|---|---|
| CzechLynx image files present | complete | GO |
| CzechLynx real metadata present | complete | GO |
| CzechLynx synthetic metadata present | complete | GO, but excluded from primary validation |
| Real metadata rows verified | complete: 39,760 rows | GO |
| Working individual ID field | complete: `unique_name`, pending documentation confirmation | CONDITIONAL GO |
| Unique working individual IDs | complete: 319 | GO |
| Metadata path matching | complete for first 1,000 paths | GO |
| Image readability | complete for first 100 images | GO |
| License verified | pending | NO-GO for public use |
| Public display permission verified | pending | NO-GO for public display |
| CzechLynx internal sampling | ready | CONDITIONAL GO |

Final decision:

```text
pending
```

Allowed final decisions:

- `GO`
- `CONDITIONAL GO`
- `NO-GO`

## Conditions for GO to Phase 2

The project may move to Phase 2 only if:

- CzechLynx access is Go or Conditional Go;
- rubric usability is Go;
- sampling plan is Go or Conditional Go;
- WildTrax/UWIN plan is Go or Conditional Go;
- Marbled Cat note is Go;
- daily work log is started;
- no forbidden claims remain in Phase 1 documents.

## What Phase 2 May Do After GO

If Phase 1 passes, Phase 2 may begin:

- create CzechLynx pilot triage CSV;
- label pilot images;
- run second-review subset;
- finalize rubric revisions;
- prepare for embedding extraction.

Phase 2 should still not claim final results.

## What Must Still Wait

Even after Phase 1, do not yet claim:

- review-ready images are more reliable;
- false-match proxy decreased;
- evidence loss was quantified;
- WildTrax identities were validated;
- Marbled Cat Re-ID is supported.

Those claims require later quantitative analysis.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| Moving to embeddings too early | Code may outrun research design | Require Phase 1 gates before analysis | All gates reviewed | Project is ready for pilot triage | Quantitative conclusion |
| Data access is assumed | License or metadata may block study | Complete access notes | Dataset status recorded | Data can be used under documented conditions | Use without license |
| Rubric remains vague | Labels cannot support validation | Use observable fields and second review | Rubric decisions are explainable | Rubric is operational | Triage is automatically correct |
| WildTrax becomes validation | No verified IDs | Restrict to field triage | No identity metrics reported | Field stress test is valid | True individual ID claim |
| Marbled Cat overclaim | No current data | Keep future-only note | Data requirements listed | Future application scenario | Current validation |

## Phase 1 Completion Statement

Use this statement only after Phase 1 passes:

Phase 1 confirms that the project has a legally and scientifically bounded validation path. CzechLynx will be used for known-ID validation, UWIN/WildTrax will be used for field-readiness stress testing only, and Marbled Cat will remain a future application case. The review-readiness rubric is operational enough to begin pilot triage, but no Re-ID reliability or false-match risk conclusion has been made yet.
