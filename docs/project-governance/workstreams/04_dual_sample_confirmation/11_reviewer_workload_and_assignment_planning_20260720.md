# Reviewer workload and assignment planning

Status: **PASS PROVISIONAL — NOT RELEASED**
Date: 20 July 2026
Formal pair count: 2,224
First-pass decisions required: 4,448
Outcome collection started: no

## Reviewer task

For every assigned pair, the reviewer answers one question: whether the two displayed images contain enough comparable visible evidence for a responsible individual-level comparison. The reviewer does not decide whether the animals are the same individual. A visibly different animal pair can be `review_ready` when the images support a responsible rejection; an apparently similar pair can be `not_review_ready` when the comparable evidence is inadequate.

The allowed decisions are `review_ready`, `not_review_ready`, and `uncertain`. A not-ready or uncertain response requires one or more visible-evidence reason codes. Every semantic response records confidence in the reviewability decision, not confidence in identity. A display or loading problem is a technical incident, not a semantic label, and leaves the task unresolved until repaired or re-presented.

During first pass, reviewers must work independently. They must not search for source images, inspect source filenames or metadata, discuss individual tasks, use another reviewer’s answer, or try to infer descriptors, scores, ranks, PF-ERI values, identity truth, sampling stage, or hidden strata. Suspected leakage requires immediate suspension of the affected task and incident reporting.

## Exact workload

Every one of 2,224 formal pairs requires two independent first-pass decisions, giving exactly 4,448 first-pass decisions before adjudication. Adjudication volume cannot be known before the immutable first-pass disagreement audit and is therefore not estimated.

| Distinct eligible people | First-pass tasks per person | Eligible adjudicators per pair |
|---:|---:|---:|
| 3 | 1,482–1,483 | 1 |
| 4 | 1,112 exactly | 2 |
| 5 | 889–890 | 3 |
| 6 | 741–742 | 4 |
| 7 | 635–636 | 5 |
| 8 | 556 exactly | 6 |

Four people are the recommended minimum operational configuration. It gives every person exactly 1,112 first-pass tasks and leaves two eligible third people for every possible disagreement. Three people are scientifically valid under the accepted minimum but leave only one possible adjudicator for each pair and concentrate more first-pass work on each person. No time estimate or collection window is imposed.

## Adjudication rule consolidation

An older narrative sentence allowed an adjudicator to see the conflicting first-pass responses, while the frozen blinded-export contract and active confirmatory protocol require adjudicators to receive no prior responses. The implementation follows the stricter machine-verifiable boundary: any exact disagreement across the three decision values triggers a third-person task; the third person did not first-pass the pair, sees the same neutral images, does not see prior answers, and supplies a fresh blinded adjudication decision. That decision is the final three-category adjudicated value for the disagreed pair, while all three raw responses remain immutable.

## Generated planning artifacts

The consolidated planning directory is `archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_reviewer_assignment_planning/`, with `current/` pointing to `iterations/v3/`. It contains workload scenarios, a balanced four-code provisional assignment, a pair-level adjudicator-eligibility table, a restricted roster template, a Chinese reviewer guide, an audit, and checksums. Earlier v1 and v2 planning drafts were never released: v1 balanced only total load, while v2 balanced total and stage load but left reviewer-dyad frequencies uneven. The v3 plan corrects both defects before outcome access.

The four-code provisional plan contains 4,448 unique assignment packet IDs over 2,224 pairs. Every pair has two distinct first-pass codes and two eligible adjudicator codes. Each provisional code has exactly 1,112 first-pass tasks. Every sampling stage differs by at most one task per person, and the six reviewer dyads differ by at most one shared pair globally and within every stage. These are opaque planning codes only; the plan remains `provisional_not_released` until four distinct accountable people are mapped to them, training is confirmed, conflicts are attested, and a fresh interface audit passes.

The project owner confirmed on 20 July 2026 that four distinct people are available. The resulting frozen-count workload is:

| Opaque reviewer code | Development | Calibration | Deployment confirmation | Mechanism confirmation | Total first pass |
|---|---:|---:|---:|---:|---:|
| `rv_49b92f627e` | 222 | 223 | 445 | 222 | 1,112 |
| `rv_587d8ff16a` | 222 | 223 | 444 | 223 | 1,112 |
| `rv_6bcc6fbef5` | 223 | 222 | 445 | 222 | 1,112 |
| `rv_be918645bc` | 223 | 222 | 444 | 223 | 1,112 |

This balance is an assignment property, not an expected label distribution or an individual performance target. No reviewer is expected to produce a particular proportion of `review_ready`, `not_review_ready`, or `uncertain` decisions. Adjudication work remains outcome-dependent and is not included in the 1,112 first-pass total.

## Remaining release gate

The four-person count is now fixed for this assignment design, but the restricted identity-to-code roster is not yet complete. Therefore no reviewer-visible image package or response collection interface has been released by this planning step.

The next implementation must bind the four actual people to the restricted opaque-code roster, document training and conflicts, produce lossless metadata-stripped opaque image rendering, construct per-reviewer packet views, verify exact two-person coverage and third-person eligibility, and send the exact final interface code through a fresh independent non-reviewer browser leakage audit. Only an all-pass audit can change packet release and outcome collection from false to true. The project owner may perform final statistical and governance review, but anyone exposed to restricted sampling, feature, model, or prior-response information must not act as a semantic adjudicator for an affected pair.
