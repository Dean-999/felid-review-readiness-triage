# PF-ERI v2 local-match execution

This directory contains the one active local-evidence algorithm and its execution
engineering. The scientific core is `local_match_runner_v2.py`: Mask R-CNN
animal-region selection with full-image fallback, SuperPoint keypoints,
LightGlue matching, RANSAC geometric verification, two-direction coverage, and
two predeclared retry levels. `full_frame_local_match_runner.py` applies that
unchanged core to the frozen within-role pair inventory.

The current full-frame run contains 30 inventory-declared shards and 28,295
unique unordered pairs. It does not select the 2,224 human-review pairs, access
outcome labels, or access identity truth.

## Canonical files

- `local_match_runner_v2.py`: frozen scientific matcher.
- `full_frame_local_match_runner.py`: freeze, smoke, checkpoint, and shard wrapper.
- `full_frame_execution_orchestrator.py`: inventory-driven fresh-run scheduler.
- `validate_full_frame_results.py`: independent global validation.
- `merge_full_frame_results.py`: deterministic validation-gated merge.
- `build_final_export.py`: one checksum-protected final export.
- `local_match_execution_protocol_v2.json`: frozen protocol contract.
- `requirements.txt`: cloud execution dependencies.

Build only `PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip`, using
`scripts/build_v2_full_frame_local_match_control_package.py`. Platform changes
do not create another builder, README, or version-suffixed control ZIP.

## Required inputs

Place these two private inputs in the chosen cloud service:

1. `PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip`.
2. `v2_czechlynx_fresh_descriptor_images.zip`, containing the 3,000
   byte-verified images. Its frozen SHA-256 is
   `540912351ff958b0d4395c0a8fec3ab8e129995f0d0f355656e673599f018bc0`.

Never upload `restricted_pair_execution_linkage.csv` to a reviewer-facing or
public dataset. The control ZIP contains code and opaque pair manifests only.

## Google Colab execution

Mount Drive, then define persistent result/export roots and disposable VM roots:

```python
from google.colab import drive
drive.mount('/content/drive')

import os
os.environ.update({
  "INPUT_ROOT": "/content/drive/MyDrive/PF_ERI_INPUTS",
  "CONTROL_ROOT": "/content/pferi_control",
  "IMAGE_STAGE": "/content/pferi_images",
  "IMAGE_ROOT": "/content/pferi_images/v2_descriptor_execution_package/images",
  "RESULT_ROOT": "/content/drive/MyDrive/PF_ERI_FULL_FRAME_RESULTS",
  "EXPORT_ROOT": "/content/drive/MyDrive/PF_ERI_FULL_FRAME_EXPORT",
})
os.environ["CONTROL_ZIP"] = os.environ["INPUT_ROOT"] + "/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip"
os.environ["IMAGE_ZIP"] = os.environ["INPUT_ROOT"] + "/v2_czechlynx_fresh_descriptor_images.zip"
```

Preflight the two inputs, GPU, and Drive write access:

```bash
set -euo pipefail
test -f "${CONTROL_ZIP}"
test -f "${IMAGE_ZIP}"
nvidia-smi
mkdir -p "${RESULT_ROOT}" "${EXPORT_ROOT}"
probe="${RESULT_ROOT}/.write_probe"; date -u > "${probe}"; test -s "${probe}"; rm "${probe}"
```

Extract the immutable inputs into the VM and verify the package checksums:

```bash
set -euo pipefail
rm -rf "${CONTROL_ROOT}" "${IMAGE_STAGE}"
mkdir -p "${CONTROL_ROOT}" "${IMAGE_STAGE}"
unzip -q "${CONTROL_ZIP}" -d "${CONTROL_ROOT}"
(cd "${CONTROL_ROOT}" && sha256sum -c CHECKSUMS.sha256)
unzip -q "${IMAGE_ZIP}" -d "${IMAGE_STAGE}"
test -d "${IMAGE_ROOT}"
python -m pip install -r "${CONTROL_ROOT}/requirements.txt"
```

Before using the GPU, require a structural dry-run pass with 30 shards, 28,295
pairs, and `calibration_shard_001` as the first scheduled shard:

```bash
python "${CONTROL_ROOT}/full_frame_execution_orchestrator.py" \
  --control-root "${CONTROL_ROOT}" --image-root "${IMAGE_ROOT}" \
  --result-root "${RESULT_ROOT}" --export-root "${EXPORT_ROOT}" \
  --max-shards-per-run 1 --dry-run
```

Launch one new shard per session. The first invocation performs freeze, delayed
weight inventory, the five-pair smoke gate, and the first shard. Later invocations
validate and skip completed shards before selecting the next inventory entry.

```bash
python "${CONTROL_ROOT}/full_frame_execution_orchestrator.py" \
  --control-root "${CONTROL_ROOT}" --image-root "${IMAGE_ROOT}" \
  --result-root "${RESULT_ROOT}" --export-root "${EXPORT_ROOT}" \
  --max-shards-per-run 1
```

`BATCH_COMPLETE` means persisted progress remains; `RUN_COMPLETE` means all 30
shards are structurally complete. Never edit `_control`, checkpoint, binding,
freeze, or inventory files between sessions.

After `RUN_COMPLETE`, validate, merge, and export:

```bash
python "${CONTROL_ROOT}/validate_full_frame_results.py" \
  --control-root "${CONTROL_ROOT}" --result-root "${RESULT_ROOT}"
python "${CONTROL_ROOT}/merge_full_frame_results.py" \
  --control-root "${CONTROL_ROOT}" --result-root "${RESULT_ROOT}"
python "${CONTROL_ROOT}/build_final_export.py" \
  --control-root "${CONTROL_ROOT}" --result-root "${RESULT_ROOT}" \
  --export-root "${EXPORT_ROOT}"
```

Download exactly `PF_ERI_FINAL_EXPORT.zip`.

## Kaggle execution

Kaggle may run the same canonical package; it is not a separate algorithm or
package version. Extract both inputs under `/kaggle/working`, install
`requirements.txt`, and invoke the same orchestrator with Kaggle-specific root
arguments. Preserve the result root as a Kaggle output after every shard. The
current accepted plan is a fresh single-environment run; do not combine old
Kaggle shards with a new Colab fingerprint unless a separate migration protocol
is approved.

## Validation semantics

`PARTIAL` is a completed scientific execution when every expected row and binding
is present but a pre-specified matcher failure such as `insufficient_matches` is
retained. `FAIL` is an engineering failure. Global validation requires all 30
shards, 28,295 unique pairs, both directions, exact schemas and order, manifest
hashes, one execution fingerprint, the frozen environment, image/weight
inventories, and the bound smoke report.

An engineering pass establishes completeness, binding integrity, and
reproducibility. It does not establish re-identification accuracy, biological
truth, or reviewability validity.

## Iteration history

- **2026-07-14 — pilot Kaggle package.** A five-pair smoke gate and 160-pair
  feasibility run established the basic interface. It did not cover the frozen
  full-frame inventory.
- **2026-07-16 — first full-frame Kaggle attempt.** The wrapper incorrectly
  inferred a nonexistent `calibration_shard_011` after the tenth calibration
  shard. The completed work demonstrated an orchestration defect, not a missing
  scientific shard.
- **2026-07-18 — attempted Kaggle-to-Colab continuation.** A start-index design
  would have scheduled the remaining shards while expecting earlier Kaggle
  outputs. It was abandoned because cross-platform fingerprints and incomplete
  result migration could not support a single clean execution claim.
- **2026-07-18 onward — accepted fresh run.** The complete first design was
  retained, the scheduler became inventory-only, roots became configurable,
  execution binding/global validation/deterministic merge were added, and the
  default became one shard from `calibration_shard_001` in a new result root.
  This is the only current package and execution path.
