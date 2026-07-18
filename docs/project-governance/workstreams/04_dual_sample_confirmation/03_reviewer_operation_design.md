# Pre-Outcome Reviewer-Operation Design

Status: accepted by the project owner pre-outcome on 15 July 2026.  
Applies to: Workstream 04 Task 03.  
Prepared: 15 July 2026 before any v2 outcome packet or outcome review.

## Accepted experimental structure

Every one of the 2,224 prepared unique unordered pairs will receive two first-pass judgements from two different people working independently. This rule applies without reduction to the development, calibration, mechanism-confirmation, and deployment-confirmation blocks. The experiment does not assign an expected number of minutes to a judgement, an expected adjudication rate, a total-hour budget, or a collection window.

When the two first-pass judgements disagree under the frozen response-comparison rule, the pair will be sent to a third person for adjudication. The adjudicator must not have supplied either first-pass judgement for that pair. Agreement does not trigger adjudication. The actual number and proportion of adjudicated pairs will be reported from the immutable response logs rather than assumed in advance.

## Blinding and role separation

The first-pass interface must not expose the other reviewer's decision, model output, descriptor score, quality score, candidate rank, identity metadata, pair stratum, analytical role, or confirmation role. Reviewer identities may be represented by opaque role codes in the response log, while a restricted assignment record maps each code to one accountable person and verifies that the two first-pass roles are held by different people.

Adjudication begins only after both first-pass responses are immutable. The adjudicator may see the two conflicting responses and the permitted neutral reasons needed to resolve the disagreement, but must remain blinded to model outputs, descriptor scores, rankings, hidden strata, and analytical role. The packet builder must enforce the rule that no person adjudicates a pair on which that person served as a first-pass reviewer.

The packet builder or data steward should be operationally separate from semantic review whenever feasible because that role can access hidden assignment and analysis metadata. If one person must occupy more than one project role, the restricted assignment audit must demonstrate that no prohibited information is available while that person acts as a reviewer or adjudicator. At least three distinct eligible people must be available for the assignment graph, but the protocol does not estimate their hours or impose a calendar window.

## Observed operational reporting

The review system will record start time, submission time, elapsed time, completion status, technical interruption, first-pass role, and adjudication status for each task. These fields are operational measurements and are not model inputs or reviewer-facing information. After collection, the project owner may provide the actual time used, and the analysis will report the observed distribution without comparing it with an invented expected duration.

The timed outcome-free rehearsal remains evidence that the interface and logging path operated, but its observed seconds are not semantic-review times and do not define an experimental threshold. Actual semantic-review time, disagreement frequency, adjudication frequency, missingness, and technical failure will be descriptive outcomes of the implemented experiment.

## Execution gate

Before an outcome packet is released, the restricted role-assignment record must pass three checks. Every pair must have two different first-pass reviewers; every possible adjudication must have at least one eligible third person who did not first-pass that pair; and no reviewer-facing or adjudicator-facing interface may expose prohibited hidden information. No estimated-time, total-hour, or collection-window check is required.

The project owner accepted this full-strength reviewer-operation design on 15 July 2026 before any v2 outcome packet or outcome review. The next design decision is the immutable sampling strata rule, followed by the official seed, actual role assignment, and final outcome-free packet audits.
