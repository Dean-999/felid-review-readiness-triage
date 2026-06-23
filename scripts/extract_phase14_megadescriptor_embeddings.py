#!/usr/bin/env python3
"""Extract Phase 14 MegaDescriptor embeddings from a descriptor manifest.

Designed for Colab/GPU or another cloud runtime. It reads the manifest produced
by `prepare_phase14_descriptor_embedding_manifest.py` and writes the schema
required by `build_phase14_descriptor_evidence_conflict_table.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

MEGADESCRIPTOR_MODEL = "BVRA/MegaDescriptor-L-384"


def vector_to_text(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.9g}" for x in vector.tolist()) + "]"


def resolve_image_path(row: pd.Series, project_root: Path | None) -> Path:
    path_text = str(row.get("image_path", "")).strip()
    path = Path(path_text)
    if path.exists():
        return path
    cloud_relative = str(row.get("cloud_image_relpath", "")).strip()
    if project_root is not None and cloud_relative:
        candidate = project_root / cloud_relative
        if candidate.exists():
            return candidate
    relative = str(row.get("image_path_relative", "")).strip()
    if project_root is not None and relative:
        candidate = project_root / relative
        if candidate.exists():
            return candidate
    return path


def select_device(torch_module: Any) -> Any:
    if torch_module.cuda.is_available():
        return torch_module.device("cuda")
    if getattr(torch_module.backends, "mps", None) is not None and torch_module.backends.mps.is_available():
        return torch_module.device("mps")
    return torch_module.device("cpu")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--model", default=MEGADESCRIPTOR_MODEL)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import timm
    import torch

    manifest = pd.read_csv(args.manifest, low_memory=False)
    if args.limit is not None:
        manifest = manifest.head(args.limit).copy()
    required = {"phase14_image_evidence_id"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    if not {"image_path", "cloud_image_relpath", "image_path_relative"} & set(manifest.columns):
        raise ValueError("Manifest must contain one of image_path, cloud_image_relpath, or image_path_relative")

    device = select_device(torch)
    model = timm.create_model(f"hf_hub:{args.model}", pretrained=True, num_classes=0)
    model.eval().to(device)
    config = timm.data.resolve_model_data_config(model)
    transform = timm.data.create_transform(**config, is_training=False)

    rows = []
    batch_tensors = []
    batch_ids = []
    errors = []
    for _, row in manifest.iterrows():
        image_id = str(row["phase14_image_evidence_id"])
        image_path = resolve_image_path(row, args.project_root)
        try:
            with Image.open(image_path) as image:
                tensor = transform(image.convert("RGB"))
        except Exception as exc:
            errors.append({"phase14_image_evidence_id": image_id, "image_path": str(image_path), "error": repr(exc)})
            continue
        batch_tensors.append(tensor)
        batch_ids.append(image_id)
        if len(batch_tensors) >= args.batch_size:
            with torch.inference_mode():
                vectors = model(torch.stack(batch_tensors).to(device)).detach().cpu().float().numpy()
            for item_id, vector in zip(batch_ids, vectors):
                rows.append(
                    {
                        "phase14_image_evidence_id": item_id,
                        "embedding_model": args.model,
                        "embedding_dim": int(vector.shape[0]),
                        "embedding_vector": vector_to_text(vector),
                    }
                )
            batch_tensors = []
            batch_ids = []

    if batch_tensors:
        with torch.inference_mode():
            vectors = model(torch.stack(batch_tensors).to(device)).detach().cpu().float().numpy()
        for item_id, vector in zip(batch_ids, vectors):
            rows.append(
                {
                    "phase14_image_evidence_id": item_id,
                    "embedding_model": args.model,
                    "embedding_dim": int(vector.shape[0]),
                    "embedding_vector": vector_to_text(vector),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    audit_path = args.output.with_suffix(".audit.json")
    audit = {
        "manifest": str(args.manifest),
        "output": str(args.output),
        "model": args.model,
        "device": str(device),
        "input_rows": int(len(manifest)),
        "embedding_rows": int(len(rows)),
        "error_count": int(len(errors)),
        "errors": errors[:50],
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    if errors:
        raise SystemExit("Some images failed descriptor extraction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
