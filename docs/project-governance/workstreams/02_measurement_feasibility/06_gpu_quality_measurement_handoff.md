# Task 03: GPU Automatic Quality Measurement Handoff

Status: execution complete; accepted as `measurement_ready_with_reduced_feature_set` at the automatic-quality branch level.

The local CPU reference environment was tested with the locked Mask R-CNN coverage extractor and found unable to maintain stable memory across the 305-image batch. This is an environment limitation, not a missing-value result and not evidence against the feature. No partial output table was retained. The completed CUDA result is archived at `work/pferi_v2/gpu/measurement_feasibility/automatic_quality/`.

The restricted package contains exactly the 305 unique images used by the 160-pair outcome-free pilot. Its audit is PASS with zero SHA256 failures. Upload the ZIP, `restricted_quality_execution_manifest.csv`, and `run_v2_pilot_quality_measurements.py` to a Colab or Kaggle GPU environment. Extract the ZIP without changing files, then run the script with `--image-root` pointing to `v2_descriptor_execution_package/images`, `--allow-weight-download`, and the same three input manifests. The script re-verifies every extracted file against the manifest before decoding.

The execution records the generic COCO cat-mask coverage proxy, native pixel count, Laplacian sharpness, and clipping fraction. It does not read outcome labels, identity truth, descriptor score, rank, route, or manual corrections. The completed run has exact input-hash coverage and no manual rescue. Native pixel count, sharpness, and clipping fraction pass their fixed measurement gates; the generic COCO cat-mask coverage proxy is valid for only 113 of 305 images and is excluded from the primary automatic feature set. The generic detector must not be represented as a validated CzechLynx segmenter.

The upload-ready code-and-manifest bundle is `artifacts/transfers/pferi_v2/automatic_quality_gpu_execution_bundle.zip`; its companion instructions are `automatic_quality_gpu_execution_README.md` in the same directory. Upload this small bundle and the separate immutable image ZIP together, extract both without renaming files, and return only the unmodified `PF_ERI_V2_AUTOMATIC_QUALITY_RESULTS/` directory after execution.

Do not upload or use historical image tables, v1 labels, pair scores, embeddings, or reviewer data in this environment.
