# Upstream Reservoir Step: Neutral V2 Image Context

Status: complete.

The v2 neutral image-context manifest was generated from the 3,000-row CzechLynx final-freeze manifest. Each output row has an opaque content-hash-derived image identifier, decode status, illumination metadata status, and source-camera-context status. Identity labels, source paths, filenames, licenses, and other source provenance are excluded from the output. The source manifest reported 3,000 available, decodable, content-unique images, and the neutral export contains 3,000 rows.

The output is `outputs/pferi_v2/czechlynx_v2_image_context.csv`, with an audit at `outputs/pferi_v2/czechlynx_v2_image_context_audit.json`. It establishes image availability for a future v2 descriptor queue only. It is not a pair set, feature table, review packet, or outcome dataset.

The next upstream step remains blocked on fresh fixed-descriptor inference. Existing MegaDescriptor and DINOv2 embeddings and score tables are historical outputs and are prohibited from serving as the v2 queue. A fresh run must record the exact model, weights, preprocessing, runtime environment, input-context checksum, output checksum, and top-k queue construction rule before its directed memberships may be converted into canonical pairs.
