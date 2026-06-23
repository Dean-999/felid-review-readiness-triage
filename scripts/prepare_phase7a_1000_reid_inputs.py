#!/usr/bin/env python3
"""Prepare Phase 7A 1000-image identity and embedding manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE4_IDENTITY = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
PHASE6_MAPPING = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase6_unique_500_v2_balanced_review_mapping_internal.csv"
PHASE7A_ANNOTATIONS = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a"
OUT_IDENTITY = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase7a_1000_internal_with_ids.csv"
OUT_MANIFEST = OUT_DIR / "czechlynx_phase7a_1000_embedding_input_manifest.csv"
OUT_PHASE6_MANIFEST = OUT_DIR / "czechlynx_phase6_v2_500_embedding_input_manifest.csv"
OUT_AUDIT = OUT_DIR / "phase7a_1000_reid_input_preparation_audit.json"


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def path_exists(path_text: object) -> bool:
    path = Path(str(path_text))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.exists()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    phase4 = pd.read_csv(PHASE4_IDENTITY)
    phase6 = pd.read_csv(PHASE6_MAPPING)
    annotations = pd.read_csv(PHASE7A_ANNOTATIONS)

    phase4_required = [
        "expanded_image_id",
        "review_image_filename",
        "review_image_path",
        "working_individual_id",
        "source",
        "date",
        "encounter",
        "path",
        "local_image_path",
        "image_exists",
        "relative_age",
        "coat_pattern",
    ]
    phase6_required = [
        "expanded_image_id",
        "review_image_path_local",
        "unique_name",
        "source",
        "date",
        "encounter",
        "path",
        "local_image_path",
        "relative_age",
        "coat_pattern",
    ]
    missing_phase4 = sorted(set(phase4_required) - set(phase4.columns))
    missing_phase6 = sorted(set(phase6_required) - set(phase6.columns))
    if missing_phase4 or missing_phase6:
        raise ValueError(f"missing columns phase4={missing_phase4} phase6={missing_phase6}")

    p4 = phase4[phase4_required].copy()
    p4["review_image_path_local"] = p4["review_image_path"]
    p4["source_phase"] = "phase4_original_500"

    p6 = phase6[phase6_required].copy()
    p6["review_image_filename"] = p6["expanded_image_id"].astype(str) + ".jpg"
    p6["review_image_path"] = p6["review_image_path_local"]
    p6["working_individual_id"] = p6["unique_name"]
    p6["image_exists"] = p6["review_image_path_local"].map(path_exists)
    p6["source_phase"] = "phase6_v2_balanced_500"
    p6 = p6[
        [
            "expanded_image_id",
            "review_image_filename",
            "review_image_path",
            "working_individual_id",
            "source",
            "date",
            "encounter",
            "path",
            "local_image_path",
            "image_exists",
            "relative_age",
            "coat_pattern",
            "review_image_path_local",
            "source_phase",
        ]
    ].copy()

    p4 = p4[
        [
            "expanded_image_id",
            "review_image_filename",
            "review_image_path",
            "working_individual_id",
            "source",
            "date",
            "encounter",
            "path",
            "local_image_path",
            "image_exists",
            "relative_age",
            "coat_pattern",
            "review_image_path_local",
            "source_phase",
        ]
    ].copy()

    identity = pd.concat([p4, p6], ignore_index=True)
    if identity["expanded_image_id"].duplicated().any():
        dupes = identity.loc[identity["expanded_image_id"].duplicated(), "expanded_image_id"].tolist()
        raise ValueError(f"duplicate expanded_image_id values: {dupes[:5]}")

    annotation_ids = set(annotations["expanded_image_id"].astype(str))
    identity_ids = set(identity["expanded_image_id"].astype(str))
    if identity_ids != annotation_ids:
        raise ValueError(
            "identity and annotation IDs differ: "
            f"identity_only={len(identity_ids - annotation_ids)} annotation_only={len(annotation_ids - identity_ids)}"
        )

    manifest = identity[["expanded_image_id", "review_image_path_local", "source_phase"]].copy()
    phase6_manifest = manifest[manifest["source_phase"].eq("phase6_v2_balanced_500")].copy()

    identity.to_csv(OUT_IDENTITY, index=False)
    manifest.to_csv(OUT_MANIFEST, index=False)
    phase6_manifest.to_csv(OUT_PHASE6_MANIFEST, index=False)

    counts = identity["working_individual_id"].astype(str).value_counts()
    audit: dict[str, Any] = {
        "identity_csv": rel(OUT_IDENTITY),
        "embedding_manifest_csv": rel(OUT_MANIFEST),
        "phase6_embedding_manifest_csv": rel(OUT_PHASE6_MANIFEST),
        "row_count": int(len(identity)),
        "unique_image_ids": int(identity["expanded_image_id"].nunique()),
        "source_phase_counts": {str(k): int(v) for k, v in identity["source_phase"].value_counts().sort_index().items()},
        "unique_identity_count": int(identity["working_individual_id"].astype(str).nunique()),
        "identities_with_at_least_2_images": int((counts >= 2).sum()),
        "singleton_identity_count": int((counts == 1).sum()),
        "review_image_paths_exist": int(identity["review_image_path_local"].map(path_exists).sum()),
        "local_image_paths_exist": int(identity["local_image_path"].map(path_exists).sum()),
        "phase7a_annotation_overlap": int(len(identity_ids & annotation_ids)),
    }
    OUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote {rel(OUT_IDENTITY)} rows={len(identity)}")
    print(f"Wrote {rel(OUT_MANIFEST)}")
    print(f"Wrote {rel(OUT_PHASE6_MANIFEST)}")
    print(f"Wrote {rel(OUT_AUDIT)}")


if __name__ == "__main__":
    main()
