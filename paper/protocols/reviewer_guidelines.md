# PF-ERI v2 Reviewer Guidelines

Version: v2 design draft. These instructions become reviewer-facing only after the interface and blinding audit pass.  
Date: 2026-07-10

These instructions implement the blinded-outcome-review requirement in `PROJECT_RULES.md`. They apply only to a newly generated v2 packet and not to any historical Phase18 review form.

## Your Task

For each image pair, decide whether the two images contain enough comparable visual evidence for a responsible person to conduct an individual-level comparison. You are not being asked to decide whether the animals are the same individual. You are judging whether the available visual evidence is adequate for such a comparison. A pair showing different animals may still be review-ready when the visible evidence makes a confident rejection possible.

Choose `review_ready` when the pair has sufficiently comparable visible evidence to support a responsible individual-level comparison. Choose `not_review_ready` when the pair lacks enough comparable visual evidence because the animal is too small, blurred, occluded, poorly exposed, shown from an incompatible view, missing the relevant patterned region, or otherwise unsuitable for comparison. Choose `uncertain` only when you cannot responsibly decide between the first two options. Select the reason or reasons that best explain a not-ready or uncertain decision, record your confidence, and use the optional note only to describe visible evidence or a problem with the image display.

## What You Will and Will Not See

You will see the two images, a neutral pair identifier, the decision field, reason fields, confidence, an optional note, and the time of your response. You will not see the descriptor system, descriptor similarity, candidate rank, PF-ERI score, quality score, feature labels, route, known identity information, earlier reviewer decisions, or sampling group. Do not try to infer those hidden values from filenames, browser tools, or communication with other reviewers. If you notice information that appears to reveal a hidden condition, stop reviewing that pair and report the issue without entering a decision.

## Review Discipline

Review each pair independently and do not discuss individual pairs with another reviewer during first-pass assessment. Judge only the images currently displayed; do not search for source images, use external metadata, or rely on memory of an animal from another task. Do not mark a pair review-ready merely because it appears visually similar, and do not mark it not-ready merely because you are personally unable to decide identity. The question is whether the pair offers sufficiently comparable evidence for responsible review.

## Handling Uncertainty and Technical Problems

Use the `uncertain` option when the image evidence does not permit you to make a defensible reviewability judgement. Do not use it as a substitute for a technical problem. If an image fails to load, appears duplicated, contains an obvious rendering error, or the interface displays a hidden score or metadata, report the problem through the provided channel and leave the record for the study coordinator. Your raw response, timestamp, and any reported problem remain part of the study audit trail.
