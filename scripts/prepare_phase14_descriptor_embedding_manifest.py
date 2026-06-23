#!/usr/bin/env python3
"""Prepare Phase 14 image manifest for cloud descriptor extraction.

This script does not copy or zip images by default. It creates a stable
12000-image manifest, chunk manifests, and a README describing the expected
embedding return schema. This keeps disk use low while making the GPU extraction
step reproducible.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALGO_DIR = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs"
IMAGE_TABLE = ALGO_DIR / "phase14_2x2_image_evidence_table.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_package"
OUT_MANIFEST = OUT_DIR / "phase14_2x2_descriptor_embedding_manifest.csv"
OUT_AUDIT = OUT_DIR / "phase14_2x2_descriptor_embedding_manifest_audit.json"
OUT_README = OUT_DIR / "README.md"

RETURN_SCHEMA = [
    "phase14_image_evidence_id",
    "embedding_model",
    "embedding_dim",
    "embedding_vector",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def manifest_columns(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "phase14_image_evidence_index",
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "image_exists",
        "identity_label_available_for_validation",
        "image_evidence_utility_score",
        "pair_admissibility_band",
    ]
    # `pair_admissibility_band` is not image-level; keep a stable schema if a
    # previous experimental table contained it, but do not require it.
    keep = [column for column in keep if column in frame.columns]
    out = frame[keep].copy()
    out["image_path_relative"] = out["image_path"].map(lambda value: rel(Path(str(value))))
    out["descriptor_extraction_status"] = "pending"
    return out


def write_chunks(manifest: pd.DataFrame, out_dir: Path, chunk_size: int) -> list[dict[str, Any]]:
    chunk_dir = out_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for start in range(0, len(manifest), chunk_size):
        index = len(rows) + 1
        chunk = manifest.iloc[start : start + chunk_size].copy()
        path = chunk_dir / f"phase14_descriptor_manifest_part_{index:02d}.csv"
        chunk.to_csv(path, index=False)
        rows.append({"chunk_index": index, "path": rel(path), "row_count": int(len(chunk))})
    return rows


def readme_text(manifest: pd.DataFrame, chunks: list[dict[str, Any]]) -> str:
    return f"""# Phase 14 Descriptor Embedding Package

This package prepares the 12000 Phase 14 2x2 images for cloud/GPU descriptor extraction.

## Inputs

- Manifest: `phase14_2x2_descriptor_embedding_manifest.csv`
- Chunk manifests: `chunks/phase14_descriptor_manifest_part_*.csv`
- Image paths are local paths relative to the project root where possible.

## Expected Return File

Return one CSV per descriptor model, or one combined CSV, with exactly these columns:

```text
{", ".join(RETURN_SCHEMA)}
```

Recommended output path after copying back into the project:

```text
outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv
```

Each `embedding_vector` should be a JSON-style list of floats, for example:

```text
[0.0123,-0.0456,...]
```

## Recommended Model

Use a fixed, pretrained animal Re-ID descriptor, preferably MegaDescriptor from the WildlifeDatasets/WildlifeTools ecosystem. Do not fine-tune in this step. The scientific claim depends on fixed descriptor support plus PF-ERI evidence admissibility, not a newly trained descriptor.

## Counts

- Total images: {len(manifest)}
- Chunks: {len(chunks)}

## Boundary

This package only extracts image descriptors. It does not infer identity and does not validate bobcat false matches without verified bobcat individual labels.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-table", type=Path, default=IMAGE_TABLE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image_table.exists():
        raise FileNotFoundError(f"Missing image evidence table: {args.image_table}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.image_table, low_memory=False)
    manifest = manifest_columns(frame)
    manifest.to_csv(args.out_dir / OUT_MANIFEST.name, index=False)
    chunks = write_chunks(manifest, args.out_dir, args.chunk_size)
    readme = readme_text(manifest, chunks)
    (args.out_dir / OUT_README.name).write_text(readme, encoding="utf-8")

    audit = {
        "input_image_table": rel(args.image_table),
        "manifest": rel(args.out_dir / OUT_MANIFEST.name),
        "readme": rel(args.out_dir / OUT_README.name),
        "row_count": int(len(manifest)),
        "unique_phase14_image_evidence_id": int(manifest["phase14_image_evidence_id"].nunique()),
        "missing_images": int(manifest["image_exists"].ne("yes").sum()),
        "chunk_size": int(args.chunk_size),
        "chunks": chunks,
        "expected_return_schema": RETURN_SCHEMA,
    }
    (args.out_dir / OUT_AUDIT.name).write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    if audit["row_count"] != 12000:
        raise SystemExit("Expected 12000 images for descriptor extraction")
    if audit["missing_images"] != 0:
        raise SystemExit("Manifest contains missing images")
    if audit["unique_phase14_image_evidence_id"] != 12000:
        raise SystemExit("Manifest image IDs are not unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
