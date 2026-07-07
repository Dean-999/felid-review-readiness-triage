#!/usr/bin/env python3
"""Build Phase18B local descriptor-control embeddings from Phase18A images."""

from __future__ import annotations

import argparse
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PHASE18B_DIR,
        PHASE18B_EMBEDDINGS,
        PHASE18B_MANIFEST,
        l2_normalize,
        now_utc,
        project_relative,
        read_csv,
        resolve_project_path,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PHASE18B_DIR,
        PHASE18B_EMBEDDINGS,
        PHASE18B_MANIFEST,
        l2_normalize,
        now_utc,
        project_relative,
        read_csv,
        resolve_project_path,
        write_csv,
        write_json,
    )


OUTPUT_COLUMNS = [
    "embedding_row",
    "phase18_image_id",
    "species",
    "freeze_rank",
    "modeling_role",
    "train_eval_eligible",
    "has_known_identity",
    "identity_label",
    "frozen_image_path",
    "decode_width",
    "decode_height",
    "megapixels",
    "min_dimension",
    "max_dimension",
    "aspect_ratio",
    "sha256",
    "descriptor_name",
    "descriptor_dim",
    "descriptor_status",
    "claim_boundary",
]


def dependency_status() -> dict[str, bool]:
    return {
        "torch": importlib.util.find_spec("torch") is not None,
        "timm": importlib.util.find_spec("timm") is not None,
        "wildlife_tools": importlib.util.find_spec("wildlife_tools") is not None,
    }


def local_descriptor(path: Path, image_size: int = 16) -> np.ndarray:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        small = image.resize((image_size, image_size), Image.Resampling.BILINEAR)
        arr = np.asarray(small, dtype=np.float32) / 255.0
        flat = arr.reshape(-1)
        hist_parts = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel], bins=16, range=(0.0, 1.0), density=False)
            hist = hist.astype(np.float32)
            hist_parts.append(hist / max(float(hist.sum()), 1.0))
        means = arr.mean(axis=(0, 1))
        stds = arr.std(axis=(0, 1))
    return np.concatenate([flat, *hist_parts, means, stds]).astype(np.float32)


def build_phase18b(input_csv: Path, output_dir: Path) -> dict[str, Any]:
    rows = read_csv(input_csv)
    vectors: list[np.ndarray] = []
    manifest_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        image_path = resolve_project_path(row["frozen_image_path"])
        vector = local_descriptor(image_path)
        vectors.append(vector)
        manifest_rows.append(
            {
                "embedding_row": idx,
                "phase18_image_id": row["phase18_image_id"],
                "species": row["species"],
                "freeze_rank": row["freeze_rank"],
                "modeling_role": row["modeling_role"],
                "train_eval_eligible": row["train_eval_eligible"],
                "has_known_identity": row["has_known_identity"],
                "identity_label": row["identity_label"],
                "frozen_image_path": row["frozen_image_path"],
                "decode_width": row["decode_width"],
                "decode_height": row["decode_height"],
                "megapixels": row["megapixels"],
                "min_dimension": row["min_dimension"],
                "max_dimension": row["max_dimension"],
                "aspect_ratio": row["aspect_ratio"],
                "sha256": row["sha256"],
                "descriptor_name": "phase18b_local_pixel_histogram_control_v1",
                "descriptor_dim": len(vector),
                "descriptor_status": "local_control_not_strong_model",
                "claim_boundary": (
                    "Local descriptor-control only. This does not replace the "
                    "required MegaDescriptor/WildFusion/foundation baselines."
                ),
            }
        )
    matrix = l2_normalize(np.vstack(vectors))
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / PHASE18B_EMBEDDINGS.name, matrix)
    write_csv(output_dir / PHASE18B_MANIFEST.name, manifest_rows, OUTPUT_COLUMNS)
    deps = dependency_status()
    audit = {
        "built_at_utc": now_utc(),
        "input_csv": project_relative(input_csv),
        "output_manifest": project_relative(output_dir / PHASE18B_MANIFEST.name),
        "output_embeddings": project_relative(output_dir / PHASE18B_EMBEDDINGS.name),
        "row_count": len(manifest_rows),
        "embedding_shape": list(matrix.shape),
        "species_counts": dict(sorted(Counter(row["species"] for row in manifest_rows).items())),
        "descriptor_name": "phase18b_local_pixel_histogram_control_v1",
        "descriptor_status": "LOCAL_CONTROL_BASELINE_ONLY",
        "strong_model_dependency_status": deps,
        "strong_model_ready": bool(deps["torch"] and deps["timm"]),
        "claim_boundary": (
            "Automated Phase18 can proceed with this local control baseline, but "
            "scientific claims still require strong descriptor baselines."
        ),
    }
    write_json(output_dir / "phase18b_local_descriptor_control_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18B Local Descriptor Control\n\n"
        "This output is an automated descriptor-control baseline derived from the "
        "frozen images. It is intentionally claim-limited because torch/timm are "
        "not available in the current runtime.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=PHASE18A_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=PHASE18B_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18b(args.input_csv, args.output_dir)
    print("PASS phase18b local descriptor control")
    print(f"row_count={audit['row_count']}")
    print(f"embedding_shape={audit['embedding_shape']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
