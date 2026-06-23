# Phase 14 MegaDetector Colab Selection

This Colab workflow screens Phase 14 bobcat and CzechLynx strict high-confidence candidates and low-evidence stress candidates with MegaDetector.

It does not change the high-confidence rule. It only processes more candidates with the fixed detector gate.

## Local Preparation

Run locally:

```bash
python3 scripts/prepare_phase14_colab_megadetector_package.py --chunk-size 1000
```

This creates:

```text
outputs/phase14/phase14_colab_megadetector_package/
  phase14_colab_megadetector_manifest.csv
  phase14_colab_megadetector_packaged_manifest.csv
  phase14_colab_megadetector_zip_index.csv
  phase14_md_czechlynx_images_part_*.zip
```

Bobcat images are not zipped because they are large and have public LILA `download_url` values in the manifest. Colab downloads them directly.

CzechLynx images must be uploaded as zip files because they are local project images.

## Upload To Google Drive

Create this Drive folder:

```text
MyDrive/phase14_colab_megadetector/
```

Upload:

```text
phase14_colab_megadetector_manifest.csv
phase14_md_czechlynx_images_part_*.zip
run_phase14_megadetector_colab.py
```

In Colab, unzip the CzechLynx packages:

```bash
mkdir -p /content/drive/MyDrive/phase14_colab_megadetector
cd /content/drive/MyDrive/phase14_colab_megadetector
unzip -n 'phase14_md_czechlynx_images_part_*.zip'
```

## Colab Setup

Use a GPU runtime.

```bash
pip install PytorchWildlife soundfile librosa 'setuptools<81'
```

Run:

```bash
python /content/drive/MyDrive/phase14_colab_megadetector/run_phase14_megadetector_colab.py \
  --input-dir /content/drive/MyDrive/phase14_colab_megadetector \
  --output-dir /content/drive/MyDrive/phase14_colab_megadetector_outputs \
  --device cuda
```

Expected output:

```text
MyDrive/phase14_colab_megadetector_outputs/
  phase14_colab_megadetector_detections.csv
  phase14_colab_megadetector_detection_summary.json
```

## Local Finalization

Download `phase14_colab_megadetector_detections.csv` into:

```text
outputs/phase14/phase14_colab_megadetector_package/colab_returned/
```

Then run locally:

```bash
python3 scripts/finalize_phase14_colab_megadetector_selection.py
```

Final outputs:

```text
outputs/phase14/phase14_colab_megadetector_final_selection/
  phase14_bobcat_megadetector_high_confidence_final.csv
  phase14_czechlynx_megadetector_high_confidence_final.csv
  phase14_colab_megadetector_final_selection_summary.json
```

Each dataset is capped at 3,000 selected high-confidence images. If fewer than 3,000 pass, the script keeps the smaller number and marks the status as `below_target_do_not_force`.

## Low-Evidence Stress Package

Run locally:

```bash
python3 scripts/prepare_phase14_colab_megadetector_low_evidence_package.py --chunk-size 1000
```

This creates:

```text
outputs/phase14/phase14_colab_megadetector_low_evidence_package/
  phase14_colab_megadetector_manifest.csv
  phase14_colab_megadetector_packaged_manifest.csv
  phase14_colab_megadetector_zip_index.csv
  phase14_md_low_czechlynx_images_part_*.zip
  run_phase14_megadetector_colab.py
```

Use a separate Drive folder so high-confidence and low-evidence outputs do not overwrite each other:

```text
MyDrive/phase14_colab_megadetector_low_evidence/
```

Upload:

```text
phase14_colab_megadetector_manifest.csv
phase14_md_low_czechlynx_images_part_*.zip
run_phase14_megadetector_colab.py
```

In Colab, unzip:

```bash
mkdir -p /content/drive/MyDrive/phase14_colab_megadetector_low_evidence
cd /content/drive/MyDrive/phase14_colab_megadetector_low_evidence
unzip -n 'phase14_md_low_czechlynx_images_part_*.zip'
```

Run:

```bash
python /content/drive/MyDrive/phase14_colab_megadetector_low_evidence/run_phase14_megadetector_colab.py \
  --input-dir /content/drive/MyDrive/phase14_colab_megadetector_low_evidence \
  --output-dir /content/drive/MyDrive/phase14_colab_megadetector_low_evidence_outputs \
  --device cuda
```

Download `phase14_colab_megadetector_detections.csv` into:

```text
outputs/phase14/phase14_colab_megadetector_low_evidence_package/colab_returned/
```

Then run locally:

```bash
python3 scripts/finalize_phase14_colab_megadetector_low_evidence_selection.py
```

The low-evidence finalizer uses the same fixed detector gate as the high-confidence finalizer, but in reverse. Rows that pass the high-evidence detector gate are removed from the stress set and written to `phase14_low_evidence_rejected_high_conflict_or_review_required.csv`.
