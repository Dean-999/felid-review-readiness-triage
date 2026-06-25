# Phase 16E Colab Batch Execution

Phase 16E runs streaming candidate scoring. It does not freeze final 3000, does not simple top-3000, and does not modify Phase 16D.

## Modes

Base:

```text
IQA + OpenCLIP
```

Enhanced:

```text
IQA + OpenCLIP + optional SuperAnimal pose
```

SuperAnimal pose is optional. It estimates structural completeness and viewpoint proxies only. It does not prove identity and does not replace laterality/manual audit.

## Inputs

```text
outputs/phase16/phase16e_candidate_model_filter_colab_package/phase16e_candidate_model_filter_manifest.csv
outputs/phase16/phase16e_candidate_model_filter_colab_package/phase16e_candidate_model_filter_config.json
outputs/phase16/phase16e_candidate_model_filter_colab_package/run_phase16e_candidate_model_filter_colab.py
```

CzechLynx direct zip inputs:

```text
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_direct_zip_manifest.csv
```

## Base Command

```bash
pip install -q pyiqa open_clip_torch pandas pillow tqdm
python run_phase16e_candidate_model_filter_colab.py \
  --manifest phase16e_candidate_model_filter_manifest.csv \
  --output-dir outputs/phase16/phase16e_candidate_model_filter
```

## Pose Smoke Test

```bash
python run_phase16e_candidate_model_filter_colab.py \
  --manifest phase16e_candidate_model_filter_manifest.csv \
  --output-dir outputs/phase16/phase16e_candidate_model_filter_pose_test20 \
  --limit 20 \
  --target-quadrant wild_czechlynx_high_confidence \
  --source-mode packaged_local \
  --enable-superanimal-pose \
  --pose-model-name superanimal_quadruped_hrnetw32 \
  --pose-device cuda \
  --pose-failure-is-fatal false
```

Recommended default: `--pose-failure-is-fatal false`. Pose failure becomes row-level metadata and falls back to IQA + OpenCLIP scoring.

## Outputs

```text
phase16e_candidate_model_filter_scores.csv
phase16e_candidate_model_filter_audit.json
phase16e_candidate_model_filter_summary.md
debug_samples/
```

Do not use runner `selection_eligible` as final selection. Treat it as diagnostic only. Phase 16F must recompute soft eligibility.

See:

```text
docs/phase16/phase16e_result_acceptance_criteria.md
```
