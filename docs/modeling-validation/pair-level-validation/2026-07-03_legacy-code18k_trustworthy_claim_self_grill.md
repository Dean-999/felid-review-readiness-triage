# legacy-code18k Trustworthy Claim Self-Grill

Date: 2026-07-03

## Purpose

This document resets legacy-code18k around the most trustworthy claim, not around
patching weak claims after results are known.

Locked primary claim:

```text
PF-ERI is a descriptor-agnostic, post-retrieval pair-level evidence governance
layer for patterned-felid Re-ID candidate review. Given a strong descriptor
candidate queue, PF-ERI estimates whether a candidate pair has admissible visual
identity evidence for human review, and whether that pair should be accepted for
review, reviewed cautiously, deferred as low evidence, or treated as
non-comparable. Its first-round validation target is reviewability and evidence
admissibility, not automatic identity assignment or descriptor-ranking
superiority.
```

Operational confidence rule:

```text
There is no literal 100% certainty in empirical science. Here, "factually 100%
confident" means every reasonable alternative explanation needed to reject the
primary claim has a prespecified control, audit, sensitivity analysis, or
claim-failure rule.
```

## Literature Guardrails

The claim should be evaluated like a post-retrieval prediction/decision-support
component, not like a new descriptor.

Relevant standards:

- Prediction-model reporting emphasizes discrimination, calibration, validation,
  and clear intended use; it is not enough to report one favorable AUC.
- Risk-of-bias tools for prediction models separate development data,
  validation data, outcome definition, predictor leakage, and applicability.
- Diagnostic/reporting standards distinguish an index test from the reference
  standard; here PF-ERI is the index signal and human reviewability is the
  reference construct, not identity truth.
- Inter-rater agreement is necessary when human labels define the reference
  construct, but agreement does not prove that the construct itself is perfect.
- Targeted mechanism samples are valid for probing mechanisms, but representative
  or stratified samples are needed for population-like claims.

Methodological sources checked during planning:

- Collins et al., TRIPOD statement for prediction-model reporting.
- Wolff et al., PROBAST risk-of-bias assessment for prediction models.
- Bossuyt et al., STARD diagnostic accuracy reporting.
- Landis and Koch, categorical observer agreement.
- Camera-trap individual-identification reporting guidance and wildlife Re-ID
  literature emphasizing human review, image-dependent uncertainty, and
  non-closed-set field workflows.

## Self-Grill Loop

### 1. Is the primary claim still too broad?

Attack:

```text
"Evidence governance layer" may sound like a product claim. It could imply that
PF-ERI is already validated across deployment settings, species, and expert
workflows.
```

Do I have 100% confidence in the current wording?

```text
No, not if readers miss the words "first-round validation" and
"candidate review."
```

Vulnerabilities:

- It could be misread as deployment-ready.
- It could be misread as identity validation.
- It could be misread as cross-species generalization.

Repair:

```text
Always bind the claim to strong-descriptor candidate queues, CzechLynx known-ID
validation, and reviewability/admissibility endpoints.
```

Factually defensible version:

```text
Under a CzechLynx known-ID validation contract after strong descriptor retrieval,
PF-ERI is tested as a pair-level evidence governance signal for human candidate
reviewability, not as a deployed identity system.
```

Confidence after repair:

```text
Factually 100% for scope clarity, because the claim now states the evaluation
contract and explicitly excludes deployment and identity assignment.
```

### 2. Does multi-reviewer labeling solve the human-label problem?

Attack:

```text
Three reviewers and kappa do not make labels true. Reviewability is subjective,
and reviewers may share the same bias.
```

Do I have 100% confidence in the strategy?

```text
No, not if the strategy stops at majority vote.
```

Vulnerabilities:

- Moderate kappa does not equal excellent reliability.
- Majority vote can hide unstable boundary cases.
- Reviewer instructions may define the construct inconsistently.
- Human reviewability is not identity ground truth.

Repair:

```text
Use a frozen annotation guideline, blind reviewers to truth and scores, report
agreement, adjudicate disagreement pairs, and analyze pre- and post-adjudication
labels.
```

Pass condition:

```text
The PF-ERI direction and core effect must remain under majority labels and
adjudicated labels. If not, the claim is mixed.
```

Confidence after repair:

```text
Factually 100% for "not a single-reviewer artifact." Not 100% for "human labels
are objective truth," so the claim must call them reviewability reference labels.
```

### 3. Does full-queue sampling solve the targeted-sample problem?

Attack:

```text
Targeted samples can manufacture a big effect by oversampling obvious cases.
Full-queue legacy-code18j is smaller and DINOv2 has a weaker same/false gap.
```

Do I have 100% confidence in the strategy?

```text
No, if legacy-code18i and legacy-code18j are pooled into one undifferentiated result.
```

Vulnerabilities:

- legacy-code18i is mechanism-enriched.
- legacy-code18j is broader but still only 100 pairs per descriptor.
- Same/false reviewability separation is not equally strong for both
  descriptors.

Repair:

```text
Keep targeted and full-queue results separate. Use targeted data only for
mechanism plausibility. Use full-queue stratified data for the main reviewability
validation. Report descriptor-specific results before pooled results.
```

Pass condition:

```text
The primary claim passes only if PF-ERI reviewability alignment holds in the
full-queue sample under both descriptors or the exception is stated as mixed.
Same/false separation is secondary, not the primary endpoint.
```

Confidence after repair:

```text
Factually 100% that targeted-sample inflation is not hidden, because the two
sampling purposes are separated and the claim does not rely on targeted
population estimates.
```

### 4. Is PF-ERI more than image quality filtering?

Attack:

```text
PF-ERI may simply downweight bad photos. If so, it is not a pair-level evidence
governance layer.
```

Do I have 100% confidence in the strategy?

```text
Not yet. Current results strongly weaken the quality-only explanation, but the
final proof should be formal.
```

Existing evidence:

```text
In legacy-code18j, weakest-image quality alone had weak AUC, while PF-ERI review score
had much stronger AUC. This argues against a pure quality-filter explanation.
```

Vulnerabilities:

- Quality may interact with descriptor similarity.
- A weak univariate quality control does not prove independent PF-ERI value.
- Quality features may be embedded indirectly inside PF-ERI.

Repair:

```text
Run quality-only and descriptor-plus-quality controls, then test whether PF-ERI
adds incremental reviewability utility beyond them.
```

Pass condition:

```text
PF-ERI must outperform quality-only and improve or remain meaningfully distinct
from descriptor-plus-quality under query-cluster bootstrap. If not, state that
PF-ERI is not distinguishable from quality/descriptor controls in this sample.
```

Confidence after repair:

```text
Factually 100% for the decision rule: the strategy cannot overclaim, because it
requires a formal control and has a predeclared failure state.
```

### 5. Is PF-ERI more than descriptor similarity?

Attack:

```text
This is the hardest critique. In full queues, descriptor similarity itself
predicts reviewability. PF-ERI might only repackage similarity.
```

Do I have 100% confidence in the current evidence?

```text
No. This is the largest unresolved threat to the primary claim.
```

Vulnerabilities:

- Descriptor similarity percentile had strong AUC in legacy-code18j.
- Full-queue low-rank candidates are naturally less review-ready.
- PF-ERI review score may correlate with descriptor percentile.

Repair:

```text
Run incremental utility analysis:
descriptor similarity only;
quality only;
PF-ERI only;
descriptor similarity + quality;
descriptor similarity + PF-ERI;
descriptor similarity + quality + PF-ERI.

Also run rank-bin stratified analysis and high-similarity-only analysis.
```

Pass condition:

```text
PF-ERI must add positive delta utility beyond descriptor similarity plus quality
or show stable within-rank-bin separation. If neither holds, the independent
pair-governance claim fails under current data.
```

Confidence after repair:

```text
Factually 100% in the strategy, not in the expected result. The strategy is
trustworthy because it allows PF-ERI to fail rather than protecting it by
wording.
```

### 6. Are low-evidence and non-comparable routes both validated?

Attack:

```text
Low evidence and non-comparable are different constructs. legacy-code18j elicited
low-evidence labels but did not elicit non-comparable labels.
```

Do I have 100% confidence in the strategy?

```text
No, if both routes are reported as equally validated.
```

Vulnerabilities:

- Non-comparable may be rare in the full-queue sample.
- Reviewers may not understand the distinction.
- A route can be algorithmically useful but empirically unvalidated.

Repair:

```text
Separate route claims. Low-evidence can be evaluated from legacy-code18j. Non-comparable
requires a dedicated enrichment packet with explicit label guidance, or else it
must remain an unvalidated route.
```

Pass condition:

```text
Low-evidence route passes only if reviewers use it and PF-ERI predicts it.
Non-comparable route passes only if reviewers actually assign non-comparable
labels in a suitable packet.
```

Confidence after repair:

```text
Factually 100% for preventing overclaim: non-comparable cannot be claimed unless
the corresponding labels exist.
```

legacy-code18k forward-assumption update:

```text
For immediate legacy-code18k planning, non-comparable is treated as a future
obtainable label rather than a current blocker. This allows the schema and review
router to retain a non-comparable route. It does not convert non-comparable into
a current empirical result.
```

### 7. Does same-ID versus false-candidate reviewability prove the main claim?

Attack:

```text
The same/false gap is biologically plausible but not guaranteed. Some false
candidates are easy to reject and thus review-ready. Some same-ID pairs are poor
evidence and not review-ready.
```

Do I have 100% confidence in this as the main endpoint?

```text
No. It should not be the main endpoint.
```

Vulnerabilities:

- DINOv2 same/false gap is directionally positive but inconclusive in legacy-code18j.
- Same/false labels answer identity relationship, while PF-ERI targets
  evidential admissibility.
- A review-ready false candidate is not a failure if it can be confidently
  rejected.

Repair:

```text
Make human reviewability/admissibility the primary endpoint. Report same-ID
retention and false-candidate burden as secondary review-utility endpoints.
```

Pass condition:

```text
The main claim can pass even if same/false separation is mixed, provided PF-ERI
predicts reviewability and controls false-candidate burden at fixed retention.
```

Confidence after repair:

```text
Factually 100% that the endpoint matches the claim. It no longer confuses
reviewability with identity truth.
```

### 8. Are dependence and leakage controlled well enough?

Attack:

```text
Repeated queries, reciprocal pairs, same identity clusters, and descriptor
selection can inflate confidence intervals.
```

Do I have 100% confidence in the current strategy?

```text
No, not unless all dependence checks are documented and the resampling unit is
explicit.
```

Vulnerabilities:

- Row-level bootstrap is optimistic.
- Same query images can recur.
- Identity, camera, date, or site clusters may remain.
- Human review samples may include near duplicates.

Repair:

```text
Use query-image clustered bootstrap as the default. Add unordered-pair
deduplication sensitivity. If identity/site/date fields are available, add
identity or site sensitivity. Keep row-level results only as descriptive.
```

Pass condition:

```text
The effect must remain directionally stable under query-cluster and dedup
sensitivity. If strict cluster sensitivity erases the effect, the claim becomes
mixed.
```

Confidence after repair:

```text
Factually 100% for the resampling rule. Not 100% for all hidden ecological
correlation, so any unavailable clustering dimension must be listed as residual
risk.
```

### 9. Is Bobcat evidence allowed in the primary claim?

Attack:

```text
Bobcat lacks identity labels. Any identity-performance claim would be invalid.
```

Do I have 100% confidence in the strategy?

```text
Yes, if Bobcat is excluded from identity validation.
```

Vulnerabilities:

- Readers may interpret transfer/readiness as identity accuracy.
- Bobcat route distributions may be interesting but not validating.

Repair:

```text
Bobcat can only support unlabeled transfer/readiness stress testing: evidence
distribution, route burden, defer pressure, and review-readiness shift. It cannot
support same/different accuracy unless audited identity labels are added.
```

Pass condition:

```text
No Bobcat identity accuracy, mAP, top-k, same-ID retention, or false-candidate
burden claim appears without verified identity labels.
```

Confidence after repair:

```text
Factually 100% because the rule is binary and auditable.
```

legacy-code18k forward-assumption update:

```text
For immediate legacy-code18k planning, future Bobcat identity labels or audited
same/different pair labels are treated as obtainable. This allows the roadmap to
reserve a Bobcat identity-validation layer. It does not change the current
artifact state: current Bobcat outputs remain transfer/readiness only until the
future label artifact exists.
```

## Final legacy-code18k Strategy

The most trustworthy strategy is:

```text
1. Freeze the primary claim and forbidden claims in PROJECT_RULES.md.
2. Use legacy-code18j full-queue multi-reviewer labels as the main validation set.
3. Run incremental utility analysis against descriptor similarity, quality, and
   descriptor-plus-quality controls.
4. Build disagreement adjudication only for reviewer-disagreement pairs.
5. Re-run reviewability alignment before and after adjudication.
6. Run query-cluster and unordered-pair sensitivity.
7. Keep same/false retention and false-candidate burden as secondary utility
   metrics.
8. Keep low-evidence and non-comparable as separate route claims; treat
   non-comparable as a future-artifact assumption for planning, not a current
   result.
9. Reserve a future Bobcat identity-validation layer, while reporting current
   Bobcat artifacts only as transfer/readiness until identity labels exist.
```

This strategy has factually 100% confidence as a scientific strategy because it
does not require PF-ERI to win. It requires PF-ERI to survive the exact
alternative explanations that would invalidate the locked primary claim. If it
does not survive, the claim state becomes mixed or not supported under the
contract.
