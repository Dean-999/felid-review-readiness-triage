# Formal pair sampling freeze

Status: **FROZEN PASS**
Date: 20 July 2026
Formal manifest SHA256: `8c8407e155d92b0bc51d2300b365f4ab30f96bc70404f47217dba377ef0bdabf`
Outcome access: none
Reviewer packet created: no
Reroll: prohibited and not performed

## Decision and execution boundary

After the project owner explicitly authorized the one-time draw, the execution was bound to a separate checksum-protected authorization record. The authorized inputs were the accepted sampling contracts, official seed record, restricted 28,295-pair outcome-free master frame, frozen preselection quotas, and passing capacity audit. All seven authorized input hashes matched before the official draw. The final directory did not exist before execution and the sampler is configured to reject any overwrite.

The sampler used only the accepted HMAC-SHA256 ordering. It did not invoke a pseudo-random number generator, reroll, manual replacement, post-selection graph-degree optimization, identity field, reviewer response, or outcome. It built the result in a temporary directory. Before the atomic rename, a separate validator independently reconstructed every within-cell HMAC order, all first-stage selections, the 8,528-pair post-deployment frame, the mechanism hierarchy and disagreement midranks, the mechanism water-fill quotas, every selected mechanism pair, inclusion probabilities, and image degrees. The temporary result was frozen only after that independent reconstruction returned PASS.

## Frozen sample

The restricted formal manifest contains exactly 2,224 unique canonical unordered pairs:

| Formal stage | Source image role | Frozen pairs |
|---|---|---:|
| Development | development | 445 |
| Calibration | calibration | 445 |
| Deployment confirmation | confirmation | 889 |
| Mechanism confirmation | confirmation remainder after deployment | 445 |

Canonical-pair overlap across the four stages is zero. Development and calibration use their disjoint image partitions. Deployment and mechanism share the confirmation image partition but not a canonical pair; the 889 deployment IDs were removed before the mechanism frame was derived.

## Mechanism reconstruction

The immutable deployment draw leaves 8,528 confirmation pairs. Applying the accepted precedence hierarchy yields 18 nonempty challenge-by-rank cells. The 445-pair water-fill allocation contains:

- 9 automatic-measurement failures;
- 93 endpoint image-quality stress pairs;
- 92 local-correspondence bottom-quintile pairs;
- 92 descriptor-exclusive pairs;
- 66 dual-descriptor disagreement-top-quintile pairs;
- 93 ordinary-reference pairs.

The apparent imbalance is the correct consequence of capacity-bounded water filling. Three automatic-failure cells have capacities 3, 1, and 5 and are completely enumerated. One dual-descriptor disagreement cell has capacity 9 and is also completely enumerated; another has capacity 27 and is completely enumerated. Their conditional inclusion probability is therefore one. These saturated cells are deliberately challenge-enriched and cannot support prevalence claims.

Development contains 222 ordinary, 221 evidence-stress, and both observed development measurement-failure pairs. Calibration and deployment remain proportional retrieval-stratum samples. None of the eleven full-frame local-matcher failures happened to enter calibration or deployment; two enter development and all nine remaining confirmation failures enter mechanism by design. This allocation neither hides the failures nor implies that the deployment failure prevalence is exactly zero.

## Inclusion probabilities and dependence

Calibration first-order inclusion probabilities range from approximately 0.04348 to 0.04862 across frozen retrieval strata. Deployment probabilities range from approximately 0.08730 to 0.09899. Development and mechanism probabilities range up to one because small challenge cells are exhausted. Development probabilities are conditional on its frozen cells and are not prevalence weights. Mechanism probabilities are conditional on the immutable deployment draw and post-deployment mechanism cells and are not unconditional confirmation-frame probabilities.

The 2,224 pairs contain 2,047 unique images. The maximum observed formal-sample image degree is 13. No pair was changed to improve that degree distribution. The accepted dyadic cluster-robust analysis remains necessary because pair rows are not independent when they share an image.

## Frozen artifacts and verification

The formal artifacts are stored under `archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1/`:

- `restricted_formal_pair_sampling_manifest.csv`
- `mechanism_post_deployment_cell_capacity_and_quota.csv`
- `formal_sample_image_degree.csv`
- `formal_pair_sampling_execution_authorization_v1.json`
- `formal_selection_audit.json`
- `formal_sample_degree_audit.json`
- `immutable_input_hash_audit.json`
- `formal_sampling_freeze_record.json`
- `CHECKSUMS.sha256`

All listed artifact checksums pass. The independent validator returns 2,224 rows, 2,224 unique canonical pair IDs, the exact 445/445/889/445 stage counts, 18 mechanism cells, maximum image degree 13, and `independent_hmac_reconstruction: PASS`. The sampler and validator are `scripts/draw_v2_formal_pair_samples.py` and `scripts/validate_v2_formal_pair_samples.py`; their focused regression tests cover deterministic selection, mechanism precedence and remaining-frame percentile recomputation, overlap rejection, overwrite rejection, pre-freeze independent-validation failure, probability calculation, and checksum tampering.

## Claim boundary and next gate

This freeze establishes that the formal pair allocation is reproducible and contract-compliant. It does not establish PF-ERI accuracy, identity validity, reviewer agreement, model superiority, biological generalization, or deployment utility. The manifest is restricted analysis infrastructure and must not be exposed in the reviewer interface because cell names and measurement-failure indicators could unblind reviewers.

The next gate is blinded packet construction and reviewer-role assignment. It must map the frozen canonical pairs to opaque packet IDs, keep all sampling strata, probabilities, descriptor fields, measurements, and HMAC values out of reviewer-visible files, verify double-review and conflict-free adjudicator assignments, and pass a fresh real-interface leakage audit before any formal outcome is collected.
