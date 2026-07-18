# Fresh DINOv2 Inference Handoff

Status: ready for external GPU execution.

Use the existing immutable image package and the same restricted execution manifest used for the accepted MegaDescriptor run. Do not resample, edit, or repackage images. Run a fixed pretrained DINOv2 ViT-L/14 descriptor without fine-tuning. The returned run must contain `embeddings.npy`, `embedding_manifest.csv`, `embedding_manifest_v2.csv`, `pair_scores.csv`, and `run_audit.json` under `outputs/pferi_v2/fresh_descriptor_runs/dinov2_vitl14/`.

The DINOv2 v2 manifest must have exactly one row per input image with `image_id`, `row_index`, `embedding_dim`, `content_sha256`, `model_id`, `extractor_version`, and `status`. It must preserve the restricted manifest order and content hashes. The audit must record the restricted input-manifest SHA-256, model and weight source, framework and package versions, GPU, preprocessing, normalization, timestamp, success and failure counts, output dimensions, runtime, and SHA-256 values for every returned output. Pair scores must be directed top-20 cosine similarities, exclude self-pairs, contain no duplicate directed pair, and be derived only from the returned DINOv2 embeddings.

No reviewer outcome, identity truth, PF-ERI value, quality measurement, route, or historical embedding may enter this run. On return, the project will validate the same coverage, row binding, hash, normalization, and score-recomputation conditions used for MegaDescriptor before it freezes the two-descriptor candidate queue.
