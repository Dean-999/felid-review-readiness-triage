# Manuscript Submission Readiness Issue Pack

Date: 2026-07-10

Status: `APPROVED_EXECUTION_ISSUE_PACK`

Parent artifacts:

```text
docs/manuscript/2026-07-09_pferi_pair_level_evidence_admission_manuscript_draft.md
archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/
```

Goal:

```text
Turn the current PF-ERI manuscript draft and generated display items into a
submission-ready package while preserving the locked scientific claim:
similarity is not admissibility, and PF-ERI is a post-retrieval pair-level
evidence admission layer for human reviewability / evidential admissibility.
```

Execution rule:

- Complete issues in dependency order.
- Each issue must produce a reviewable manuscript-facing artifact on its own.
- Do not introduce a new main claim.
- Do not convert PF-ERI into a descriptor, identity classifier, Bobcat identity
  validation, retrieval mAP/top-k improvement, or universal risk-control
  guarantee.
- Keep generated manuscript text in English.

## Issue 1: Finalize Display Captions And Table Notes

Status: `COMPLETE`

Completion artifact:

```text
docs/manuscript/2026-07-10_pferi_display_captions_and_table_notes.md
```

## What to build

Create final manuscript-ready captions for Figures 1-4 and notes for Tables
1-3. Each caption or table note must be self-contained enough for a reader to
understand the endpoint, sample scope, source artifact, and claim boundary
without needing the project history.

This issue is complete when the main manuscript draft references the generated
caption/note artifact and the display-item section no longer reads like a
planning checklist.

## Acceptance criteria

- [x] Captions exist for Figures 1-4.
- [x] Notes exist for Tables 1-3.
- [x] Captions identify the endpoint as human reviewability / evidential
  admissibility where relevant.
- [x] Figure 2 caption explicitly states that active-control increments over
  descriptor plus quality are small and descriptor-specific results are mixed.
- [x] Figure 3 caption explicitly preserves quality/similarity sensitivity
  boundaries, including descriptor-specific boundary behavior.
- [x] Figure 4 caption states that same-ID retention is a secondary known-ID
  audit, not identity assignment.
- [x] Table notes block identity accuracy, Bobcat identity accuracy, mAP, MRR,
  and top-k identity-improvement claims.
- [x] The manuscript draft links to the caption/note artifact.

## Blocked by

None - can start immediately.

## Issue 2: Align Results Text With Figures And Tables

Status: `COMPLETE`

## What to build

Revise the Results section so that each major result explicitly points to the
display item that supports it. The text should guide the reader through the
evidence chain: construct validity, model comparison, quality/similarity
sensitivity, review-budget utility, and Bobcat claim boundary.

## Acceptance criteria

- [x] Results text references Figure 2, Figure 3, Figure 4, Table 1, Table 2,
  and Table 3 at the appropriate points.
- [x] Results text reports the main numerical values without duplicating every
  table cell.
- [x] Mixed or boundary results remain visible in prose.
- [x] The Results section does not claim identity accuracy, retrieval mAP, MRR,
  top-k identity improvement, or Bobcat identity validation.

## Blocked by

- Issue 1: Finalize Display Captions And Table Notes.

## Issue 3: Build Source Data And Supplementary Display Package

Status: `COMPLETE`

Completion artifact:

```text
archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/
```

## What to build

Create a source-data and supplementary-display package that maps every
manuscript figure and table to its input CSV/JSON artifact, generation command,
and claim boundary. This gives reviewers a direct reproducibility trail from
display item to audited source data.

## Acceptance criteria

- [x] A source-data manifest exists for Figures 1-4 and Tables 1-3.
- [x] Each display item lists its input artifacts and generated output files.
- [x] The package includes or references the display-item build audit JSON.
- [x] A reproducibility command is documented for regenerating Figure 2-4 and
  Table 1-3.
- [x] Source-data notes preserve the CzechLynx/Bobcat claim boundary.

## Blocked by

- Issue 1: Finalize Display Captions And Table Notes.

## Issue 4: Harmonize Figure 1 With Manuscript Display Style

Status: `COMPLETE`

Completion artifact:

```text
docs/manuscript/2026-07-10_figure1_harmonization_note.md
```

## What to build

Inspect Figure 1 against the generated manuscript display style used for
Figures 2-4. If needed, revise or regenerate Figure 1 so the terminology,
colors, typography, and route labels match the manuscript's final claim
language.

## Acceptance criteria

- [x] Figure 1 uses the same endpoint language as the manuscript.
- [x] Figure 1 does not imply that PF-ERI replaces descriptors or assigns
  identity.
- [x] Figure 1 caption and display-item listing match the final file paths.
- [x] If Figure 1 is regenerated, SVG/PDF/PNG outputs and an audit JSON are
  produced.

## Blocked by

- Issue 1: Finalize Display Captions And Table Notes.

## Issue 5: Run Full Manuscript Claim-Boundary Consistency Pass

Status: `COMPLETE`

Completion artifact:

```text
docs/manuscript/2026-07-10_claim_boundary_consistency_audit.md
```

## What to build

Run a full claim-boundary consistency pass across the manuscript and
manuscript-facing display/support files. Remove or rewrite any statement that
could be read as PF-ERI being a descriptor, identity classifier, Bobcat identity
validation, retrieval mAP/top-k improvement, or universal guarantee.

## Acceptance criteria

- [x] A consistency audit artifact lists searched terms and decisions.
- [x] Unsafe positive claim lines are either removed or rewritten.
- [x] The final manuscript preserves the positive claim:
  post-retrieval pair-level evidence admission for human reviewability /
  evidential admissibility.
- [x] Remaining limitations are explicit rather than hidden.

## Blocked by

- Issue 2: Align Results Text With Figures And Tables.
- Issue 3: Build Source Data And Supplementary Display Package.

## Issue 6: Assemble Submission-Ready Manuscript Package

Status: `COMPLETE`

Completion artifact:

```text
archive/pferi_v1/outputs/manuscript/2026-07-10_submission_ready_package/
```

## What to build

Assemble a single submission-readiness folder containing the manuscript draft,
figures, tables, source-data package, build audits, and final checklist. The
package should be usable for a final human review before journal formatting or
conversion to Word/PDF.

## Acceptance criteria

- [x] Submission-readiness folder exists with a manifest.
- [x] Main manuscript, display items, tables, source-data files, and audit files
  are linked or copied according to the repository's reproducibility convention.
- [x] A final checklist states what is complete and what still requires human
  information, such as authors, affiliations, ethics, data availability, and
  target journal formatting.
- [x] The package preserves all claim boundaries.

## Blocked by

- Issue 5: Run Full Manuscript Claim-Boundary Consistency Pass.
