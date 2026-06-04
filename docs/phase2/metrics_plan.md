# Phase 2 Metrics Plan

## Purpose

Phase 2 metrics will summarize whether CzechLynx pilot images labeled as more review-ready show more useful known-ID similarity behavior after embedding execution is authorized.

These metrics evaluate the triage workflow. They do not identify animals in deployment and do not establish a universal threshold.

## Same-Individual Similarity

Same-individual similarity uses pairs where both images share the same `unique_name`.

Expected behavior, if the triage rubric is useful, is that same-individual pairs with stronger readiness should tend to have higher similarity than low-readiness same-individual pairs.

## Different-Individual Similarity

Different-individual similarity uses pairs where the two images have different `unique_name` values.

These pairs provide the comparison background for false-positive risk proxies. They should be summarized overall and by `pair_readiness_group`.

## Separation Gap

The separation gap compares same-individual similarity against different-individual similarity.

Useful summaries may include:

- mean same-individual similarity minus mean different-individual similarity;
- median same-individual similarity minus median different-individual similarity;
- group-specific gaps by `pair_readiness_group`.

A larger gap suggests better measurement separation. A small or negative gap suggests the readiness label may not produce reliable Re-ID review inputs for that group.

## AUC If Feasible

If the pair set and score distribution support it, compute AUC using `same_individual` as the binary label and embedding similarity as the score.

AUC should be treated as a pilot validation statistic, not as deployment performance. If sample size or score behavior makes AUC unstable, report that limitation rather than forcing the metric.

## False Positive Proxy

At selected similarity thresholds, compute the share of different-individual pairs above the threshold.

This is a false positive proxy, not a confirmed field false-match rate. Thresholds should be described as pilot-specific and model-specific.

The threshold table should include:

- threshold;
- same-individual pairs above threshold;
- different-individual pairs above threshold;
- different-individual share above threshold;
- counts by `pair_readiness_group` where feasible.

## Pair Readiness Group Comparison

Summaries should compare:

- `ready_ready`;
- `ready_limited`;
- `ready_unidentifiable`;
- `limited_limited`;
- `limited_unidentifiable`;
- `unidentifiable_unidentifiable`.

The primary expectation is that `ready_ready` pairs should show the clearest same/different separation. Mixed or lower-readiness groups may show weaker or noisier separation.

## Interpreting Negative or Mixed Results

Negative or mixed results are scientifically useful.

Possible interpretations include:

- the rubric needs revision;
- some readiness fields are more predictive than the overall `triage_label`;
- the chosen embedding baseline is not sensitive to the visual cues used by reviewers;
- the 200-image pilot is too small or imbalanced for stable estimates;
- some image conditions create false-positive or false-negative risks even when images look review-ready.

Mixed results should not be hidden or converted into stronger claims. They should guide rubric refinement, second-review review, and cautious Phase 3 planning.
