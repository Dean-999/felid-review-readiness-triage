# Review Utility And Photo Entry

Date: 2026-06-29

This layer validates review utility after the claim-lock decision.
It tests whether PF-ERI adds review utility after strong descriptor retrieval.
It is not a descriptor-replacement phase, not an automatic identity-assignment
phase, and not a Bobcat identity-accuracy validation phase.

## Locked Claim Boundary

Allowed review-utility claim:

```text
PF-ERI can be evaluated as a post-retrieval pair-level evidence reliability and
review-routing layer, using known-ID CzechLynx pairs to measure review utility,
false-candidate burden, positive retention, abstention/risk coverage, and
descriptor-evidence conflict.
```

Blocked review-utility claims:

```text
PF-ERI replaces MegaDescriptor, WildlifeTools, MiewID, or Wildbook/WBIA-style
identity matching.

PF-ERI improves top-k identity ranking over descriptor-only unless a later
leakage-controlled held-out validation directly supports that exact endpoint.

PF-ERI validates Bobcat identity accuracy without verified individual labels or
an audited same/different pair set.

Proxy review actions are human expert labels.
```

## CzechLynx Review Utility

Executable plan:

```text
docs/superpowers/plans/2026-06-29-legacy-code17a-czechlynx-review-utility.md
```

Script:

```text
python3 scripts/build_legacy-code17a_czechlynx_review_utility.py
```

Primary input:

```text
outputs/project-governance/safeguards-candidate-scoring/legacy-code16h_czechlynx_readiness_controls/legacy-code16h_czechlynx_scored_pair_table.csv
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17a_czechlynx_review_utility/
```

Tracked regression test:

```text
tests/test_legacy-code17a_czechlynx_review_utility.py
```

## What CzechLynx Review Utility Measures

The CzechLynx review-utility slice evaluates:

- fixed review-budget behavior;
- fixed positive-retention behavior;
- abstention and risk coverage;
- descriptor-evidence conflict enrichment;
- proxy review-action distribution.

The comparison policies are:

- descriptor-only;
- quality-only;
- evidence-only;
- conflict-penalized descriptor;
- diagnostic review-utility score.

## Current Interpretation

This result should be read conservatively:

- descriptor-only remains the stronger ranking-like k=10 baseline in the current
  CzechLynx snapshot;
- the diagnostic review-utility policy is useful only where it improves
  review-risk endpoints, such as reducing false retained pairs at a fixed
  positive-retention target;
- proxy review actions are routing diagnostics, not expert-agreement labels.

The result supports the claim-lock gap only if the manuscript stays focused on
review utility and evidence reliability rather than descriptor replacement.

## Bobcat Transfer Stress

Script:

```text
python3 scripts/build_legacy-code17b_bobcat_transfer_stress.py
```

Primary input:

```text
outputs/project-governance/safeguards-candidate-scoring/legacy-code16e_bobcat_score_analysis/legacy-code16e_bobcat_recalibrated_scores.csv
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17b_bobcat_transfer_stress/
```

Tracked regression test:

```text
tests/test_legacy-code17b_bobcat_transfer_stress.py
```

Bobcat transfer stress is unsupervised transfer-stress analysis because Bobcat does not yet
have verified individual labels or audited same/different pair labels. It uses
non-parametric effect sizes, bootstrap confidence intervals, source-tier routing
summaries, and stratified manual-audit queues. Its outputs support
review-readiness and expert-audit planning only.

Current interpretation:

- the 20,000-row Bobcat score table passes handoff integrity checks;
- Tier 1 and Tier 2 differ strongly in final score and MD geometry evidence;
- Tier 2 has slightly higher IQA but lower final review-readiness because it
  lacks geometry evidence, so it must be treated as top-up transfer stress, not
  a clean high-confidence pool;
- the manual-audit sheet is the next evidence gate before any stronger Bobcat
  claim.

## Bobcat Provisional 3000

Prototype command:

```text
python3 scripts/prototypes/prototype_legacy-code17c_bobcat_3000_logic.py
```

Script:

```text
python3 scripts/build_legacy-code17c_bobcat_provisional_3000.py
```

Primary input:

```text
outputs/project-governance/safeguards-candidate-scoring/legacy-code16e_bobcat_score_analysis/legacy-code16e_bobcat_recalibrated_scores.csv
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17c_bobcat_provisional_3000/
```

Tracked regression test:

```text
tests/test_legacy-code17c_bobcat_provisional_3000.py
```

The provisional Bobcat 3000 slice builds the provisional Bobcat 3000 algorithm-prep manifest. The default
policy selects 2700 Tier 1 strict clean-backbone rows and 300 Tier 2 strict
transfer-sentinel rows, with a hashed balance-group cap. Broad and low-score
rows are excluded from the provisional 3000 and sampled separately for manual
audit.

Current interpretation:

- The provisional Bobcat 3000 is ready as a provisional review-readiness manifest;
- it is not a final Bobcat high-confidence identity set;
- the 300 Tier 2 sentinel rows are included to preserve transfer-stress
  visibility before algorithm design;
- the next gate is manual audit of the expansion sheet and an agreement
  analysis before any final freeze.

## Bobcat Clarity Gate

Script:

```text
python3 scripts/build_legacy-code17k_bobcat_clarity_gate.py
```

Streamlit review app:

```text
streamlit run scripts/streamlit_legacy-code17k_bobcat_clarity_gate_app.py
```

Primary input:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17e_external_source_probe/prototype_legacy-code17e_inat_research_grade_bobcat_organism_candidates.csv
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17k_bobcat_clarity_gate/
```

The Bobcat clarity gate is now the binding Bobcat algorithm-entry gate. It exists because
Earlier metadata-first queues showed that iNaturalist `research_grade`, `organism`,
`alive`, place specificity, and human-calibrated source exclusions still do not
guarantee visual comparability. The project must therefore separate source
discovery from algorithm-entry eligibility.

Hard rule:

```text
Only legacy-code17k_clarity_gate_decision=clear may enter the final Bobcat 3000.
```

Clear means the bobcat is sharp and visible enough for individual-review
comparison. Tiny/far subjects, blur, motion smear, severe occlusion, dead or
sign-only evidence, and species-level-only photos are `not_clear`. When unsure,
reject.

Current interpretation:

- The earlier metadata-first queues are diagnostic failed metadata-first attempts, not final
  Bobcat 3000 manifests;
- The Bobcat clarity gate is required before model construction or algorithm design;
- rejected rows can still support low-evidence stress tests and review-burden
  analysis, but cannot enter clean algorithm training or algorithm-entry 3000.

## Multisource Strict Clarity Queue

Prototype command:

```text
python3 scripts/prototypes/prototype_legacy-code17l_multisource_bobcat_strict_clarity_queue.py --sources inat gbif commons --target-count 5000
```

Streamlit review app:

```text
streamlit run scripts/streamlit_legacy-code17l_bobcat_strict_clarity_review_app.py
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17l_multisource_strict_clarity_queue/
```

Review working directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17l_multisource_strict_clarity_review/
```

The multisource strict clarity queue answers a prototype question: can multiple open image sources produce
a stricter Bobcat review queue than iNaturalist alone? It combines iNaturalist,
GBIF occurrence media, and Wikimedia Commons, removes known bad human labels,
deduplicates image/source records, downloads the actual image pixels, and ranks
candidates using strict visual proxy metrics:

- image dimensions and megapixels;
- file size;
- contrast standard deviation;
- gradient edge strength;
- Laplacian sharpness proxy;
- entropy;
- dark/bright clipping fraction.

Current result:

- candidate rows before dedupe: 33,253;
- candidate rows after dedupe: 15,745;
- image rows successfully scored: 14,225;
- download/decode failures: 1,520;
- final review queue: 5,000;
- final queue source counts: GBIF 3,535, iNaturalist 1,463, Wikimedia Commons 2;
- final queue proxy tiers: strict_pass 1,496, near_strict 3,504.

Current interpretation:

- This queue is stronger than the legacy-code17h/17J metadata-first queues because every
  selected row has image-level pixel proxy evidence;
- This queue still does not automatically certify visual comparability, especially
  subject size in the frame;
- final algorithm entry still requires manual `legacy-code17l_clarity_gate_decision=clear`;
- if the first 200 multisource strict clarity rows still have poor CLEAR yield, the next required
  step is object/vision-model gating rather than more metadata filtering.

## iNaturalist Annotation-Aware Strict Queue

Prototype command:

```text
python3 scripts/prototypes/prototype_legacy-code17m_inat_annotation_aware_strict_clarity_queue.py --target-count 5000
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17m_inat_annotation_aware_strict_clarity_queue/
```

Review working directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17m_inat_annotation_aware_strict_clarity_review/
```

The annotation-aware strict queue responds to the legacy-code17l spot-review failure mode: many GBIF rows were
iNaturalist photo mirrors that lacked the direct iNaturalist observation
annotation gates used to remove scat, track, dead, and non-organism evidence.
GBIF improved volume but weakened semantic safety.

The annotation-aware strict queue therefore:

- drops GBIF mirror rows from the preferred review queue;
- uses only direct iNaturalist rows with `evidence_organism=yes`,
  `evidence_scat!=yes`, `evidence_track!=yes`, `alive_dead!=dead`, and
  `captive!=true`;
- carries forward prior human `not_clear` labels as exclusions;
- allows multiple photos per observation for review, then deduplicates by image
  URI and photo ID;
- preserves the same pixel-level strict/near-strict scoring as legacy-code17l.

Current result:

- input iNaturalist photo rows: 11,378;
- rows after annotation and prior-label filters: 10,229;
- scored rows: 10,229;
- deduplicated strict-or-near rows available: 5,220;
- final review queue: 5,000;
- final queue proxy tiers: strict_pass 945, near_strict 4,055;
- duplicate image URI count in selected queue: 0;
- duplicate photo ID count in selected queue: 0.

Current interpretation:

- The annotation-aware strict queue supersedes legacy-code17l as the preferred review queue when scat/track/dead
  leakage is the main problem;
- legacy-code17l remains useful as evidence that cross-source expansion is possible,
  but GBIF mirrors should not be used as the main clean queue unless their
  source observations are rehydrated with direct annotation metadata;
- if legacy-code17m still has poor CLEAR yield, the remaining bottleneck is subject
  size/comparability and should be handled with object-detection or a vision
  model gate.

## Bobcat Final-3000 Human-Clear Seed

Script:

```text
python3 scripts/build_legacy-code17n_bobcat_final3000_seed_from_human_clear.py
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17n_bobcat_final3000_seed/
```

The final-3000 human-clear seed is the locked inclusion seed for the eventual Bobcat final 3000. It
collects all prior human-confirmed `YES` / `CLEAR` rows from legacy-code17e/F/G/H/J/K/L/M
working CSVs, deduplicates by canonical image URI and photo ID, and writes them
into the final-3000 seed manifest.

Current result:

- raw positive rows found across previous review files: 346;
- deduplicated human-confirmed clear photos: 137;
- duplicate canonical image keys: 0;
- duplicate photo IDs: 0;
- remaining clear rows needed before final 3000 freeze: 2,863.

Rule:

```text
Every final-seed row is locked into the final Bobcat 3000 candidate set.
Future top-up selection may add rows, but must not remove or replace these
human-confirmed clear seed rows unless the user explicitly reverses a label.
```

## Bobcat Manual-Audit Gate

Prototype command:

```text
python3 scripts/prototypes/prototype_legacy-code17d_manual_audit_gate.py
```

Script:

```text
python3 scripts/build_legacy-code17d_bobcat_manual_audit_gate.py
```

Primary input:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17c_bobcat_provisional_3000/legacy-code17c_bobcat_manual_audit_expansion_sheet.csv
```

Primary output directory:

```text
outputs/photo-selection/photo-entry-gates/legacy-code17d_bobcat_manual_audit_gate/
```

Tracked regression test:

```text
tests/test_legacy-code17d_bobcat_manual_audit_gate.py
```

The manual-audit gate turns manual-audit outcomes into a final-freeze recommendation. It
supports four states:

- `BLOCKED_PENDING_AUDIT` when required audit fields are blank or sparse;
- `PASS` when clean backbone and transfer sentinels both clear their gates;
- `PASS_WITH_SPLIT` when clean backbone clears the gate but transfer sentinels
  should move to a separate stress-test split;
- `REVISE` when the clean backbone fails the audit gate.

Current interpretation:

- the manual-audit gate is implemented and runnable;
- the current real legacy-code17c audit sheet is still blank, so the current decision
  is `BLOCKED_PENDING_AUDIT`;
- this is the correct conservative state and prevents accidentally treating the
  provisional 3000 as a final algorithm-entry set.

## Next Review-Utility And Photo-Entry Work

Before broadening any claim, this layer should add one or more of:

1. complete the provisional-3000/manual-audit manual-audit fields for enough clean-backbone and
   transfer-sentinel rows;
2. rerun the manual-audit gate and act on `PASS`, `PASS_WITH_SPLIT`, or `REVISE`;
3. stronger descriptor/model comparators as upstream candidate generators;
4. reserve-set or full-gallery sensitivity for CzechLynx selected-set bias;
5. a shared review-utility metric helper if later review-utility steps repeat the same
   evaluation blocks.
