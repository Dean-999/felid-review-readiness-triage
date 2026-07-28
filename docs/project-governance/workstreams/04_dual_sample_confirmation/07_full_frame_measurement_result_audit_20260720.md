# PF-ERI v2 full-frame measurement result audit — 20 July 2026

## Decision

The fresh full-frame automatic-measurement execution is accepted as an engineering-complete and analysis-usable input to the next outcome-free Workstream 04 gate.

This decision means that all inventory-declared pairs received either a valid frozen local-correspondence measurement or a prespecified scientific failure state. It does **not** mean that PF-ERI identity discrimination, calibration, biological validity, or deployment utility has passed. Those claims require the later blinded outcome data and the frozen role-specific analyses.

## Immutable source record

The received artifacts are archived at `archive/pferi_v2/task_runs/measurements/local_match/`. The final export SHA-256 is `b7825aceb21777eb6b1c199cd2db1d67deebd2babd2cb49797caf15fb3ea95e2`. The first-15-shard backup SHA-256 is `a5cc67cbbf723169e732258962c048a66e79e5aadf529b441fee89607182ee6d`. Two independently located copies of that backup were byte-identical and agreed with the supplied checksum.

The final ZIP passed safe-path and symlink screening, ZIP CRC testing, all 241 internal SHA-256 checks, and independent verification of all 239 `export_manifest.csv` payload records. The embedded validator reported 30/30 shards, 28,295/28,295 canonical rows, 28,295 unique pair identifiers, no unexpected shard directories, no error codes, and one execution fingerprint: `d228a2a080b3802690aeb0d44db30785310bb2a2514e3744cc83d3fbe2eb5a86`.

The model-weight inventory contains the detector, SuperPoint, and LightGlue checkpoints. The execution was bound to one 3,000-image inventory, one weight-set hash, one protocol/runner set, one NVIDIA A10 environment, and a passing five-pair smoke gate. No manual rescue was recorded.

The first-15 backup was also compared directly with the final export: all 90 corresponding final shard files (15 shards × six core output files) are byte-identical. The embedded scientific core runner and protocol hashes match the current project copies. The embedded execution wrapper hash is `5d2be74608736346390a368078c34ea1b920b8c08ac685fbe119fe1ffec33a3e`, whereas the current uncommitted workspace wrapper has changed. Therefore the embedded software, not the later working copy, is the authoritative reproduction source for this run.

## Descriptive result

| Quantity | Result |
|---|---:|
| Canonical pairs | 28,295 |
| Directional measurements | 56,590 |
| Valid canonical measurements | 28,284 (99.9611%) |
| Prespecified pair-level failures | 11 (0.0389%) |
| `insufficient_matches` | 8 pairs |
| `insufficient_inliers` | 3 pairs |
| `model_runtime_error` | 0 terminal pairs |
| Calibration valid | 9,433 / 9,433 (100%) |
| Confirmation valid | 9,408 / 9,417 (99.9044%) |
| Development valid | 9,443 / 9,445 (99.9788%) |
| Median canonical coverage among valid pairs | 0.001600925 |
| Mean canonical coverage among valid pairs | 0.0111142 |
| Valid-pair coverage IQR | 0.000643538–0.00392873 |
| Valid-pair coverage 95th / 99th percentile | 0.0690205 / 0.203464 |
| Median pair runtime | 0.587239 s |
| Sum of recorded pair runtimes | 4.858 h |

Coverage is strongly right-skewed; the mean is about seven times the median. Normal-model summaries and untransformed Gaussian tests are therefore inappropriate. The analysis should retain robust quantiles and treat zero coverage explicitly.

The canonical formula was independently checked: all 28,284 valid canonical values equal the minimum of A-to-B and B-to-A coverage within output precision. Directional coverage has high Pearson association (`r = 0.9657`) but only moderate rank agreement (Spearman `rho = 0.5708`), consistent with strong scale agreement plus substantial low-end rank instability. These correlations are descriptive, not inferential, because pairs share images.

There are 1,266 valid pairs (4.4760%) with canonical coverage serialized as zero. Of these, 1,224 have one zero direction and one positive direction; 42 have zero in both directions. They are not missing—the associated rows contain sufficient verified inliers—but the conservative minimum rule maps spatially degenerate or below-output-precision evidence to zero. Downstream modeling must preserve this point mass, must not add an arbitrary positive value without a frozen sensitivity analysis, and should consider a two-part or zero-aware transformation rather than pretending the distribution is continuous Gaussian.

## Robustness and failure audit

Final region sources across the 56,590 directions were detector 21,330 (37.6922%), fallback bounding box 35,160 (62.1311%), and full image 100 (0.1767%). All 100 full-image directions completed successfully. Thus detector failure was not treated as pair invalid, and fallback behavior materially increased execution coverage.

The final retry levels were level 1 for 56,512 directions, level 2 for 56, and level 3 for 22. The attempt log contains 100 scientific measurement-gate records: 56 correspond to directions later recovered successfully and 44 are the repeated attempt records for the 22 terminal directional failures. There are no terminal execution exceptions. The distinction between recovered attempts, final measurement failure, and runtime crash must remain explicit in later reporting.

Nine of the eleven failed pairs share `czechlynx_2973__p16e_029378.jpg`. Direct inspection shows that this asset is almost entirely overexposed or corrupted, with little usable felid texture. The concentration (81.8% of terminal pair failures) therefore supports an asset-level applicability limitation rather than a system-wide matcher failure. The remaining two failures involve severe view/body-part or occlusion mismatch and are compatible with the prespecified insufficient-match/inlier taxonomy. These eleven rows must remain in the frame with their original failure codes; they must not be silently deleted, imputed, or rerun under outcome-informed thresholds.

## Critical interpretation

The 99.9611% figure is **measurement availability**, not re-identification accuracy. The current data contain no blinded identity outcome in the export, so sensitivity, specificity, AUROC, AUPRC, calibration, Brier score, or decision utility cannot yet be estimated. Likewise, the small differences in coverage summaries across calibration, confirmation, and development are not evidence of superior performance in any role: roles share the same finite image graph, images recur a median of 17 times (range 4–68), and ordinary independent-pair p-values would be anti-conservative.

The evidence quality for engineering completeness is high: complete census of the frozen frame, exact hashes, one execution binding, deterministic merge, and explicit failures. Evidence quality for predictive or biological claims remains unavailable until blinded outcomes are collected. External validity beyond these 3,000 CzechLynx images remains untested.

## Authorized next step

Use the immutable merged measurements from this export to run the already specified post-allocation capacity/strata audit and then the one-time formal role-specific pair sampling. Record the eleven scientific failures and the zero-coverage point mass as prespecified measurement states. Do not tune the matcher, redefine coverage, exclude the corrupted image retrospectively, or inspect identity outcomes during this step. Only after the outcome-free sampling manifest and reviewer packet pass their freeze and leakage gates may formal outcome collection begin.
