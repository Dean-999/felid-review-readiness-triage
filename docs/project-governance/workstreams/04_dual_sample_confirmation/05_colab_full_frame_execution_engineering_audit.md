# Full-Frame Local-Match Execution Engineering Audit

Status: canonical fresh-run engineering layer implemented; full GPU execution pending.  
Scientific scope: 30 frozen shards and 28,295 within-role pairs.  
Claim boundary: engineering integrity only; no matcher-accuracy, biological-validity, or reviewability result.

## Current decision

Use one canonical control artifact:

`artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip`

Build it only with `scripts/build_v2_full_frame_local_match_control_package.py`.
The archive starts a fresh inventory-driven run at `calibration_shard_001`,
launches one pending shard per invocation by default, and resumes only from
outputs bound to the same inventory, code, protocol, images, model weights, and
smoke gate. Kaggle and Colab are execution environments for this same package;
they are not separate algorithm versions.

The scientific matcher remains the frozen Mask R-CNN region selection with
full-image fallback, SuperPoint, LightGlue, RANSAC, two-direction coverage, and
two retry levels. The consolidation changed packaging and documentation only.

## Iteration history

### 2026-07-16: first full-frame Kaggle attempt

The execution wrapper inferred a nonexistent `calibration_shard_011` after the
tenth calibration shard. The frozen inventory actually contains ten calibration,
ten confirmation, and ten development shards. This was an orchestration failure,
not evidence that a manifest or scientific shard was missing.

Retained: all 30 manifests, pair IDs, matcher logic, protocol, freeze/smoke gates,
and completed raw evidence. Changed: shard discovery became inventory-only and
archive-relative paths replaced inferred numeric ranges.

### 2026-07-18: attempted Kaggle-to-Colab continuation

A second package introduced `--start-index 10` and treated the first ten shards
as externally expected Kaggle results. It was not adopted as the final design.
Cross-platform execution fingerprints and incomplete migration made a combined
single-run claim unsafe; excluding early indices from scheduling also created a
second execution path that was difficult to audit.

Retained: configurable roots, resume checks, live logs, global validation,
deterministic merge, and the checksum-protected export. Removed: continuation
defaults, external-result state, the second builder, the second ZIP, and its
parallel README/audit document.

### 2026-07-18 onward: accepted fresh run

The complete original design was copied forward and revised in place. A new,
empty persistent result root covers the entire 30-shard inventory from
`calibration_shard_001`; one shard runs per cloud session by default. The same
control ZIP may be executed on Colab or Kaggle, but a run must keep one execution
fingerprint and one result root throughout.

## Implemented controls

| Failure mode | Current control |
|---|---|
| Inferred or nonexistent shard | Inventory is the only source of shard IDs and order. |
| Missing/corrupt manifest | Exact schema, SHA-256, row count, pair IDs, and asset names are checked before execution. |
| Cross-shard duplicate pair | Global inventory loading rejects overlap. |
| Missing/corrupt image | Every referenced image is hashed before model invocation. |
| CPU selected accidentally | Freeze requires CUDA. |
| Stale code/protocol/freeze | Runner, wrapper, protocol, environment, image set, and weights enter the execution fingerprint. |
| Stale smoke result | The smoke report is bound to the same fingerprint and input manifest. |
| Cloud interruption | Atomic pair checkpoints support same-fingerprint resume. |
| Stale shard silently skipped | A shard is skipped only after schema, count, order, binding, and checksum validation. |
| Mixed environments | Global validation requires one execution fingerprint. |
| Partial or nondeterministic merge | Merge reruns validation and follows inventory/pair/direction order. |
| Corrupt or leaking export | One atomic ZIP has an allowlist, member checksums, and no images, restricted linkage, or checkpoints. |

`PARTIAL` remains a scientifically completed shard when all structural checks
pass and pre-specified matcher failures are retained. `FAIL` is not mergeable.
Only `RUN_COMPLETE` plus a fresh global validation pass permits merge/export.

## Canonical interfaces

- `gpu/kaggle_v2_local_matcher_v2/README.md`: algorithm and both cloud environments.
- `gpu/kaggle_v2_local_matcher_v2/full_frame_execution_orchestrator.py`: fresh-run scheduling and resume.
- `gpu/kaggle_v2_local_matcher_v2/validate_full_frame_results.py`: global structural validation.
- `gpu/kaggle_v2_local_matcher_v2/merge_full_frame_results.py`: deterministic merge.
- `gpu/kaggle_v2_local_matcher_v2/build_final_export.py`: final export.
- `scripts/build_v2_full_frame_local_match_control_package.py`: sole package builder.

## Required verification before cloud execution

The package is eligible for upload only when all of the following pass in the
same working tree:

1. Python compilation of the builder and packaged modules.
2. `tests/test_full_frame_execution_engineering.py`.
3. Real inventory load with 30 shards, 28,295 unique pairs, and the expected
   first/last shard.
4. ZIP decompression and every `CHECKSUMS.sha256` entry.
5. Confirmation that the ZIP contains no images, NumPy arrays, restricted
   linkage, prior results, caches, logs, or checkpoints.

External service availability, GPU runtime stability, and dependency downloads
remain operational risks. Scientific confidence must come from the completed
measurements and later blinded outcome analysis.
