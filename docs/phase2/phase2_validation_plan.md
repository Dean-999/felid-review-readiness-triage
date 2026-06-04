# Phase 2 Validation Plan

## Purpose

Phase 2 prepares the CzechLynx pilot for quantitative validation of the review-readiness triage rubric.

The goal is not to identify individual animals. The goal is to test whether images labeled as more review-ready behave more reliably when they later enter a controlled, known-ID Re-ID measurement workflow.

## Inputs

Phase 2 uses:

- `data/labels/czechlynx/czechlynx_pilot_triage_final.csv`
- `data/interim/czechlynx/czechlynx_pilot_internal_with_ids.csv`
- `data/interim/czechlynx/czechlynx_pilot_validation_table.csv`
- `data/interim/czechlynx/czechlynx_pilot_pairs.csv`
- neutral pilot review images under `data/interim/czechlynx/pilot_review_images/`

Raw CzechLynx images are not modified or used as review-facing inputs.

## Validation Table Role

The validation table restores `unique_name` only after blinded triage is finalized.

It links each neutral pilot image to:

- finalized triage labels;
- known CzechLynx individual ID for validation only;
- neutral image path;
- non-sensitive split fields needed for later checks.

This table is an internal validation artifact. It must not be used as a blinded review file.

## Pair Set Role

The pair set defines controlled same-individual and different-individual comparisons.

Same-individual pairs use images sharing the same `unique_name`. Different-individual pairs use images with different `unique_name` values and are sampled deterministically. Pair records retain triage readiness fields so later embedding similarity summaries can be grouped by review-readiness category.

## Q1 Reliability Validation Logic

Q1 asks whether images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images.

The validation logic is:

1. Use known CzechLynx IDs only after triage labels are finalized.
2. Compute later embedding similarity for same- and different-individual pairs.
3. Compare similarity behavior by `pair_readiness_group`.
4. Check whether review-ready pairs show better separation between same- and different-individual pairs than lower-readiness groups.

This is a reliability validation of the triage rubric, not an animal identification claim.

## What Phase 2 Can Claim

Phase 2 can support statements about:

- whether the pilot data are structurally ready for embedding-based validation;
- whether pair construction preserves known-ID same/different labels;
- whether later similarity measurements differ by triage readiness group;
- whether the rubric appears promising, limited, or unreliable on the CzechLynx pilot.

## What Phase 2 Cannot Claim

Phase 2 cannot claim:

- the project identifies true individual animals in deployment;
- a new Re-ID model was trained or proposed;
- a universal threshold across felid species;
- population size or abundance;
- WildTrax/UWIN or Marbled Cat identity validation;
- final scientific conclusions before embedding measurements and second-review consistency are complete.

## Dependency on Second-Review Consistency

The 30-image second-review subset has been prepared, but labeling is intentionally delayed.

Second-review consistency is needed to interpret rubric reliability. If intra-reviewer agreement is weak, Phase 2 embedding results should be treated as exploratory and may require rubric revision before stronger claims are made.

## Pass Criteria Before Embedding Execution

Before any embedding execution:

- final 200-image triage consistency audit has passed;
- validation table exists with exactly 200 rows;
- pair file exists with expected same/different pair counts;
- pair audit prints `RESULT: PASS`;
- embedding input audit prints `RESULT: PASS`;
- second-review waiting period is respected;
- chosen embedding baseline is documented;
- no raw data, second-review files, or blinded review files are modified.
