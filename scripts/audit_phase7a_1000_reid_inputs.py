#!/usr/bin/env python3
"""Audit Phase 7A 1000-image Re-ID inputs."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a"
IDENTITY = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase7a_1000_internal_with_ids.csv"
ANNOTATIONS = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
MANIFEST = OUT_DIR / "czechlynx_phase7a_1000_embedding_input_manifest.csv"
PHASE6_MANIFEST = OUT_DIR / "czechlynx_phase6_v2_500_embedding_input_manifest.csv"
MEGA = OUT_DIR / "czechlynx_phase7a_1000_megadescriptor_embeddings.csv"
RESNET = OUT_DIR / "czechlynx_phase7a_1000_resnet50_embeddings.csv"
PREP_AUDIT = OUT_DIR / "phase7a_1000_reid_input_preparation_audit.json"
EMBEDDING_AUDIT = OUT_DIR / "phase7a_1000_embedding_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase7a_1000_reid_inputs_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def resolve_path(path_text: object) -> Path:
    path = Path(str(path_text))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def parse_vector(value: object) -> np.ndarray:
    return np.asarray(ast.literal_eval(str(value)), dtype=np.float32)


def embedding_checks(rows: list[dict[str, object]], path: Path, expected_dim: int, label: str) -> None:
    add(rows, f"{label}_exists", path.exists(), str(path))
    if not path.exists():
        return
    frame = pd.read_csv(path)
    required = {"expanded_image_id", "embedding_model", "embedding_dim", "embedding_vector"}
    missing = sorted(required - set(frame.columns))
    add(rows, f"{label}_columns", not missing, f"missing={missing}")
    if missing:
        return
    add(rows, f"{label}_row_count_1000", len(frame) == 1000, f"rows={len(frame)}")
    add(rows, f"{label}_unique_ids_1000", frame["expanded_image_id"].astype(str).nunique() == 1000, f"unique={frame['expanded_image_id'].astype(str).nunique()}")
    dims = set(pd.to_numeric(frame["embedding_dim"], errors="coerce").dropna().astype(int))
    add(rows, f"{label}_dim", dims == {expected_dim}, f"dims={sorted(dims)}")
    try:
        vectors = np.vstack([parse_vector(value) for value in frame["embedding_vector"].head(10)])
        valid = vectors.shape[1] == expected_dim and np.isfinite(vectors).all()
    except Exception as exc:  # noqa: BLE001 - audit should report parse failures.
        valid = False
        add(rows, f"{label}_sample_vectors_valid", False, f"{type(exc).__name__}: {exc}")
    else:
        add(rows, f"{label}_sample_vectors_valid", valid, f"shape={vectors.shape}")


def main() -> None:
    rows: list[dict[str, object]] = []
    for path, label in [
        (IDENTITY, "identity_csv"),
        (ANNOTATIONS, "annotation_csv"),
        (MANIFEST, "embedding_manifest"),
        (PHASE6_MANIFEST, "phase6_embedding_manifest"),
    ]:
        add(rows, f"{label}_exists", path.exists(), str(path))

    if IDENTITY.exists() and ANNOTATIONS.exists() and MANIFEST.exists() and PHASE6_MANIFEST.exists():
        identity = pd.read_csv(IDENTITY)
        annotations = pd.read_csv(ANNOTATIONS)
        manifest = pd.read_csv(MANIFEST)
        phase6_manifest = pd.read_csv(PHASE6_MANIFEST)
        identity_ids = set(identity["expanded_image_id"].astype(str))
        annotation_ids = set(annotations["expanded_image_id"].astype(str))
        manifest_ids = set(manifest["expanded_image_id"].astype(str))
        phase6_ids = set(phase6_manifest["expanded_image_id"].astype(str))
        add(rows, "identity_row_count_1000", len(identity) == 1000, f"rows={len(identity)}")
        add(rows, "identity_unique_ids_1000", len(identity_ids) == 1000, f"unique={len(identity_ids)}")
        add(rows, "identity_annotation_id_match", identity_ids == annotation_ids, f"identity_only={len(identity_ids - annotation_ids)} annotation_only={len(annotation_ids - identity_ids)}")
        add(rows, "identity_manifest_id_match", identity_ids == manifest_ids, f"identity_only={len(identity_ids - manifest_ids)} manifest_only={len(manifest_ids - identity_ids)}")
        add(rows, "phase6_manifest_row_count_500", len(phase6_manifest) == 500, f"rows={len(phase6_manifest)}")
        add(rows, "phase6_manifest_unique_ids_500", len(phase6_ids) == 500, f"unique={len(phase6_ids)}")
        source_counts = identity["source_phase"].astype(str).value_counts().to_dict()
        add(rows, "two_500_halves_present", source_counts == {"phase4_original_500": 500, "phase6_v2_balanced_500": 500}, f"source_counts={source_counts}")
        path_count = int(manifest["review_image_path_local"].map(lambda p: resolve_path(p).exists()).sum())
        add(rows, "manifest_image_paths_exist", path_count == 1000, f"existing={path_count}")
        id_counts = identity["working_individual_id"].astype(str).value_counts()
        add(rows, "multi_image_identities_available", int((id_counts >= 2).sum()) >= 200, f"ids_ge_2={int((id_counts >= 2).sum())}")

    embedding_checks(rows, MEGA, 768, "megadescriptor_1000")
    embedding_checks(rows, RESNET, 2048, "resnet50_1000")

    for path, label in [(PREP_AUDIT, "prep_audit_json"), (EMBEDDING_AUDIT, "embedding_audit_json")]:
        exists = path.exists()
        add(rows, f"{label}_exists", exists, str(path))
        if exists:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                add(rows, f"{label}_valid_json", False, str(exc))
            else:
                add(rows, f"{label}_valid_json", True, "valid")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 7A 1000 Re-ID input audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
