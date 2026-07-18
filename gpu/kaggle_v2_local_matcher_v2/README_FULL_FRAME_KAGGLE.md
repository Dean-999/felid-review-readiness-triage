# PF-ERI v2 Full-Frame Local Evidence on Kaggle

This run measures every one of the 28,295 frozen within-role pairs. It does not
select the 2,224 formal review pairs and it does not access outcomes or identity
truth. The scientific core remains the frozen SuperPoint + LightGlue + RANSAC
pipeline in `local_match_runner_v2.py`.

## Upload once

Upload these two project artifacts as private Kaggle datasets:

1. `v2_czechlynx_fresh_descriptor_images.zip` — 3,000 byte-verified images,
   SHA256 `540912351ff958b0d4395c0a8fec3ab8e129995f0d0f355656e673599f018bc0`.
2. The full-frame control package containing the runner, protocol, requirements,
   and `public_pair_manifests/`.

Never upload `restricted_pair_execution_linkage.csv` to a reviewer-facing or
public dataset. It is needed locally only when the completed automatic results
are merged back to canonical pair IDs.

## Environment and extraction

Enable a GPU and Internet for dependency/model-weight installation. Then run:

```bash
pip install -r /kaggle/input/pferi-v2-full-frame-control/requirements.txt
mkdir -p /kaggle/working/pferi_images
unzip -q /kaggle/input/pferi-v2-images/v2_czechlynx_fresh_descriptor_images.zip -d /kaggle/working/pferi_images
```

The image directory is:

```text
/kaggle/working/pferi_images/v2_descriptor_execution_package/images
```

## Mandatory order

Freeze once, then smoke-test the first shard:

```bash
cd /kaggle/input/pferi-v2-full-frame-control
python full_frame_local_match_runner.py freeze \
  --control-dir /kaggle/working/PF_ERI_FULL_FRAME_CONTROL

python full_frame_local_match_runner.py smoke \
  --pair-manifest public_pair_manifests/development_shard_001.csv \
  --image-dir /kaggle/working/pferi_images/v2_descriptor_execution_package/images \
  --control-dir /kaggle/working/PF_ERI_FULL_FRAME_CONTROL
```

Do not start a shard unless smoke returns `PASS`.

Run one shard at a time. Example:

```bash
SHARD=development_shard_001
python full_frame_local_match_runner.py run-shard \
  --pair-manifest public_pair_manifests/${SHARD}.csv \
  --image-dir /kaggle/working/pferi_images/v2_descriptor_execution_package/images \
  --control-dir /kaggle/working/PF_ERI_FULL_FRAME_CONTROL \
  --output-dir /kaggle/working/PF_ERI_FULL_FRAME_RESULTS/${SHARD}
```

There are 30 manifests in `shard_inventory.json`. Each is at most 1,000 pairs.
The runner writes one atomic JSON checkpoint per completed pair. If Kaggle stops,
rerun the same command against the preserved output directory; completed pair
checkpoints are skipped. Do not delete or edit checkpoints and do not replace the
freeze or smoke records.

After each shard, preserve the whole shard directory. `PASS` means every pair had
a valid measurement. `PARTIAL` is also a completed scientific execution when all
row-count/freeze checks pass but some pairs retain `insufficient_matches`,
`insufficient_inliers`, or another pre-specified failure code. `FAIL` is not
eligible for merging.
