# Phase 14 2x2 Working-Final Logic And Cleanup Status

Date: 2026-06-21

## Current 2x2 Working-Final Sets

Phase 14 now has four 3,000-row working-final image sets:

| Environment | Evidence role | Rows | Working-final table |
|---|---:|---:|---|
| urban/peri-urban bobcat | high-confidence evidence | 3,000 | `outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv` |
| urban/peri-urban bobcat | low-evidence stress | 3,000 | `outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_low_evidence_stress_3000_working_final_labels.csv` |
| wild CzechLynx | high-confidence evidence | 3,000 | `outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv` |
| wild CzechLynx | low-evidence stress | 3,000 | `outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv` |

All four working-final tables currently have local image references available. Within each environment, high-confidence and low-evidence stress paths have zero overlap.

## Provenance And Label Boundary

These are detector-first working-final evidence sets, not blinded human ground-truth labels.

Use them as:

- current Phase 14 image-level evidence distribution inputs;
- clean-vs-stress image pool for wild/urban comparison;
- source pool for later pair-level comparability and descriptor-evidence conflict analysis;
- candidate pool for targeted manual audit calibration.

Do not use them to claim:

- urban bobcat individual identity validation;
- population inference;
- universal Re-ID image-quality thresholds;
- final human-audited label truth.

## Logic Flow

The current Phase 14 logic is:

```text
image-level 2x2 evidence routing
  -> pair-level comparability construction
  -> descriptor-evidence conflict analysis
  -> retrieval/review contamination and risk-coverage modeling
```

The evidence roles remain separated:

- high-confidence sets support clean evidence comparison and, for CzechLynx, known-ID retrieval/pair construction;
- low-evidence stress sets support stress testing, review burden, defer/species-level-only behavior, and contamination analysis;
- low-evidence images must not silently enter core training.

## Cleanup Status

Completed cleanup actions:

- restored missing Bobcat high-confidence working-final images;
- restored missing Bobcat low-evidence working-final images;
- removed Colab upload zip files after returned detections were processed;
- updated `scripts/safe_phase14_disk_cleanup.py` so the cleanup whitelist is based on the four 3,000-row working-final tables;
- verified that current FCF image roots contain no non-whitelisted FCF image deletion candidates.

Current disk state after cleanup:

- `data`: about 22G
- `outputs`: about 2.3G
- `data/external/felidae_conservation_fund/images`: about 9.9G
- `data/raw/czechlynx/CzechLynx`: about 7.4G
- `outputs/phase14/phase14_final_2x2_working_labels`: about 47M

## CzechLynx Raw-Image Boundary

A dry-run found:

- CzechLynx raw total images: 39,760
- CzechLynx raw images referenced by current 2x2 working-final sets: 5,853
- CzechLynx raw images not referenced by current 2x2 working-final sets: 33,907
- estimated non-working-final CzechLynx raw image size: about 6.17G

These raw images were not deleted. They are original dataset material and may still be useful for future pair-level expansion, retrieval stress tests, or replacement sampling. Deleting them should be a separate explicit decision.

## Next Step

Proceed to the Phase 15 algorithmic layer:

```text
PF-ERI Evidence-Routed Review Layer
```

The image-level 2x2 evidence table, descriptor embeddings, pair comparability
table, descriptor-evidence conflict table, statistical analysis, and initial
risk-controlled review policy have been built. The next step is no longer
image discovery or simple filtering. It is query-level risk routing:

1. Build CzechLynx query-level candidate lists from existing MegaDescriptor
   embeddings.
2. Evaluate descriptor-only top-k behavior, positive retention, false-candidate
   burden, and query coverage.
3. Add PF-ERI pair comparability, weakest-image evidence, quality controls, and
   conflict score to each candidate pair.
4. Compare descriptor-only, quality-only, PF-ERI-only, and PF-ERI plus quality
   hybrid policies under matched coverage.
5. Emit routed review decisions:
   - accept;
   - review;
   - defer;
   - species-level only;
   - non-comparable.
6. Transfer the calibrated routing policy to bobcat as review-pressure and
   non-comparable-pressure stress testing only.

## Phase 15 Unit 1 Status

Completed:

- Built CzechLynx query-level fixed MegaDescriptor benchmark.
- Used all 6,000 CzechLynx working-final images as query/gallery material.
- Recovered identity labels from the CzechLynx working-final tables with full
  path coverage.
- Generated top-50 candidates per query, excluding the query image itself.
- Confirmed this step uses fixed embeddings only and performs no training.

Outputs:

- `outputs/phase15/query_level_benchmark/phase15_czechlynx_query_topk_candidates.csv`
- `outputs/phase15/query_level_benchmark/phase15_czechlynx_query_level_summary.csv`
- `outputs/phase15/query_level_benchmark/phase15_czechlynx_descriptor_topk_metrics.csv`
- `outputs/phase15/query_level_benchmark/phase15_czechlynx_query_benchmark_report.md`
- `outputs/phase15/query_level_benchmark/phase15_czechlynx_query_benchmark_audit.json`

Key descriptor-only baseline:

| Query group | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mean false@10 |
|---|---:|---:|---:|---:|---:|---:|
| all CzechLynx | 0.515 | 0.634 | 0.691 | 0.749 | 0.821 | 7.724 |
| high-confidence query | 0.564 | 0.693 | 0.741 | 0.794 | 0.850 | 7.372 |
| low-evidence query | 0.465 | 0.575 | 0.642 | 0.704 | 0.792 | 8.076 |

Interpretation:

The descriptor is strong enough to be a serious baseline, not a strawman.
However, top-k candidate lists still contain substantial false-candidate
burden, especially in low-evidence queries. This supports the next Phase 15
step: add PF-ERI pair comparability, weakest-image utility, quality controls,
and descriptor-evidence conflict to route candidate pairs rather than simply
ranking by descriptor similarity.

## Phase 15 Unit 2 Status

Completed:

- Built a CzechLynx candidate routing input table for the 300,000 descriptor
  top-50 candidate pairs.
- Added PF-ERI pair comparability, weakest-image utility, quality controls,
  descriptor-evidence conflict, admissibility bands, and preliminary route
  decisions.
- Evaluated descriptor-only, quality-only, PF-ERI-only, PF-ERI plus quality
  gate, and PF-ERI plus quality reranking policies.
- Confirmed this step still performs no model training.

Outputs:

- `outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv`
- `outputs/phase15/hybrid_routing_policy/phase15_czechlynx_hybrid_policy_evaluation.csv`
- `outputs/phase15/hybrid_routing_policy/phase15_czechlynx_hybrid_policy_pareto.csv`
- `outputs/phase15/hybrid_routing_policy/phase15_hybrid_routing_policy_report.md`
- `outputs/phase15/hybrid_routing_policy/phase15_hybrid_routing_policy_audit.json`

Key result:

Hand-written evidence gates are not strong enough to replace descriptor top-k.
Gate-style PF-ERI/quality filtering reduces review volume but loses too much
positive coverage. Evidence-aware reranking is more promising but currently
only gives small mid-k improvements:

| k | descriptor hit | best rerank hit | descriptor false/query | best rerank false/query |
|---:|---:|---:|---:|---:|
| 1 | 0.514 | 0.493 | 0.486 | 0.507 |
| 5 | 0.633 | 0.636 | 3.480 | 3.467 |
| 10 | 0.691 | 0.690 | 7.727 | 7.720 |
| 20 | 0.748 | 0.749 | 16.648 | 16.630 |

Interpretation:

This is a constructive boundary result. It shows that the current hand-written
PF-ERI/quality policy is not yet strong enough for a major claim, but it also
shows exactly where to upgrade: a held-out query-split calibrated ranker or
constrained monotonic tabular model. Any trained model must be compared against
descriptor-only, quality-only, PF-ERI-only, hand-written hybrid, and matched
controls before claiming improvement.
