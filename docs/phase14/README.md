# Phase 14 Data Foundation

Phase 14 built the same-genus wild-to-urban evidence foundation.

Core design:

```text
environment axis: wild CzechLynx vs urban/peri-urban bobcat
evidence axis: high-confidence evidence vs low-evidence stress
```

Phase 14 is data construction plus first pair-risk diagnostics. It is not final Re-ID validation.

## Core Outputs

```text
outputs/phase14/phase14_final_2x2_working_labels/
outputs/phase14/phase14_algorithm_inputs/
outputs/phase14/phase14_descriptor_embeddings/
outputs/phase14/phase14_descriptor_conflict/
outputs/phase14/phase14_statistical_analysis/
outputs/phase14/phase14_risk_controlled_review_policy/
```

Flow:

```text
working labels
-> image evidence table
-> pair comparability table
-> MegaDescriptor embeddings
-> descriptor-evidence conflict
-> statistical analysis
-> risk-controlled review policy
```

## Scripts

Main builders:

```text
scripts/build_phase14_2x2_evidence_sets.py
scripts/build_phase14_2x2_image_evidence_table.py
scripts/build_phase14_2x2_pair_comparability_table.py
scripts/build_phase14_descriptor_evidence_conflict_table.py
scripts/build_phase14_statistical_analysis.py
scripts/build_phase14_risk_controlled_review_policy.py
```

Main packaging/finalization:

```text
scripts/prepare_phase14_colab_megadetector_package.py
scripts/finalize_phase14_colab_megadetector_selection.py
scripts/prepare_phase14_low_evidence_topup_colab_package.py
scripts/finalize_phase14_low_evidence_topup_selection.py
scripts/finalize_phase14_czechlynx_high_working_final.py
scripts/safe_phase14_disk_cleanup.py
```

## Findings

- High-confidence image sets needed stricter reconstruction; early labels were biased.
- Low-evidence sets are useful as stress-test data, not training waste.
- Pair-level comparability is core: image evidence shift becomes Re-ID risk through query-gallery pairs.
- PF-ERI alone should not be sold as better than quality filtering in every block. Severe low-evidence blocks require quality plus PF-ERI hybrid policy.
- CzechLynx known-ID pairs support positive-retention and false-candidate risk analysis.
- Bobcat lacks verified individual IDs, so Phase 14 bobcat outputs support review-readiness and evidence-risk stress testing, not identity accuracy.

## Boundaries

- No final identity assignment.
- No bobcat false-match accuracy.
- No universal threshold.
- No simple top-3000.
- Low-evidence images must be routed to stress tests, review-burden analysis, or species-level-only logic.

## Historical Notes

Old Phase 14 one-off interpretation files were merged into this README to keep the project English-only and concise.
