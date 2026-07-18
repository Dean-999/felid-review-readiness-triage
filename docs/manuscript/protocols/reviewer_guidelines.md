# Phase18N Reviewer Guidelines

Date locked: 2026-07-10

## Reviewer Task

For each image pair, decide whether the pair contains enough comparable visual evidence for responsible individual-level review. You are not being asked to assign identity. You are judging whether the pair is admissible for review.

## What You Will See

Each row shows:

```text
query image
candidate image
reviewability decision field
reason fields
confidence field
notes field
```

You should not see descriptor scores, PF-ERI scores, same/different identity truth, or route labels.

## Decision Options

Use `review_ready` when the two images expose enough comparable visual evidence for a reviewer to make an individual-level comparison. This includes pairs where the animals are different individuals but the images allow a confident rejection.

Use `not_review_ready` when the pair lacks enough comparable evidence for responsible review.

Use `uncertain` when you cannot determine reviewability after inspecting the pair.

## Reason Options

Use `low_evidence` when at least one image is too weak, small, occluded, blurred, distant, overexposed, or low-evidence for reliable pair review.

Use `non_comparable` when the images are visible but cannot be compared because body region, side, pose, scale, viewpoint, or pattern evidence differs too much.

Use `both_low_evidence_and_non_comparable` when both problems are present.

Use `identity_uncertain_but_reviewable` only when the pair is review-ready but the identity decision would remain hard. In most cases, the reviewability decision should still be `review_ready`.

Use `other` only when none of the listed reasons fits, and add a note.

## Confidence

Use `high`, `medium`, or `low` for your confidence in the reviewability decision. Confidence is about the reviewability label, not identity.

## Do Not Use These Signals

Do not infer or search for:

```text
descriptor name
PF-ERI score
same-ID / different-ID truth
prior review labels
route assignment
file ordering as a hidden score
```

If you recognize a pair from prior review, label it from the visible evidence only and note that recognition occurred.

## Review Principle

The safest label is not always `not_review_ready`. A clear different-ID pair can be review-ready because the images allow a responsible rejection. A same-ID pair can be not-ready if the images do not expose comparable evidence.
