# Fresh Descriptor Inference: Colab or Kaggle GPU Handoff

Status: ready for external execution.

The v2 descriptor queue must be generated afresh, not imported from Phase18 or any other historical embedding output. Use the restricted execution manifest at `work/pferi_v2/pipeline/descriptor_manifests/restricted_descriptor_execution_manifest.csv`. It includes only opaque v2 image identifiers, image paths relative to the project root, and content hashes. Do not expose this file, source images, scores, ranks, or queues to outcome reviewers.

In Colab or Kaggle, copy the frozen CzechLynx image directory and this manifest into the working storage, preserving the image-relative paths or remapping them with a documented image root. Install fixed versions of `torch`, `torchvision`, `timm`, `transformers`, `pillow`, and `numpy`. Run one fixed MegaDescriptor model and one fixed DINOv2 model without fine-tuning. For each run, record the model identifier, exact package versions, GPU type, input-manifest SHA-256, image root, preprocessing configuration, batch size, random seeds, successful and failed image counts, output checksum, and wall time.

The required outputs are one embedding matrix and one embedding manifest per descriptor. The embedding manifest must contain opaque image ID, row index, embedding dimension, model identifier, input content hash, extractor version, and status. It must not contain identity, review, route, or outcome columns. After both runs return, validate content-hash coverage against the restricted execution manifest, compute directed top-k queues under a separately frozen queue contract, and only then build v2 canonical pairs.

Do not choose a model, preprocessing rule, top-k depth, or failure policy after viewing reviewability outcomes. If an image fails inference, retain its explicit failure record; do not replace its embedding with a historical vector or a manual substitute.
