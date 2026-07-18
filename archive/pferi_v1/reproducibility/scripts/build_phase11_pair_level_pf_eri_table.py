#!/usr/bin/env python3
"""Build Phase 11 pair-level PF-ERI reliability table.

The table is a training scaffold for pair-level metric-learning experiments.
It uses Phase 10-Lite Plus train-only manifests, Phase 4/7 visual factor
annotations, and fixed MegaDescriptor embeddings. It does not train a model.
"""

from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE10_MANIFEST = PROJECT_ROOT / "outputs/czechlynx/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv"
VISUAL_FACTORS = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv"
FALLBACK_VISUAL_FACTORS = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
EMBEDDINGS = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase11"
PAIR_TABLE = OUT_DIR / "phase11_pair_level_pf_eri_table.csv"
SCORE_SUMMARY = OUT_DIR / "phase11_pair_level_pf_eri_score_summary.csv"
FIELD_AUDIT = OUT_DIR / "phase11_pair_level_pf_eri_field_audit.json"

PAIR_SCORE_WEIGHTS = {
    "side_comparability_score": 0.30,
    "pattern_pair_score": 0.25,
    "blur_pair_score": 0.15,
    "occlusion_pair_score": 0.10,
    "body_visibility_pair_score": 0.10,
    "viewpoint_compatibility_score": 0.10,
}

QUALITY_BUCKET_SCORE = {
    "high": 1.0,
    "medium_high": 0.75,
    "medium": 0.67,
    "medium_low": 0.50,
    "low": 0.25,
}
PATTERN_SCORE = {"high": 1.0, "medium": 0.67, "low": 0.33, "none": 0.0, "not_available": 0.5}
SIDE_EVIDENCE_SCORE = {"high": 1.0, "medium": 0.67, "low": 0.33, "none": 0.0, "not_available": 0.5}
BLUR_SCORE = {"none": 1.0, "mild": 0.67, "moderate": 0.33, "severe": 0.0, "not_available": 0.5}
OCCLUSION_SCORE = {"none": 1.0, "mild": 0.67, "moderate": 0.33, "severe": 0.0, "not_available": 0.5}
BODY_SCORE = {"76_100": 1.0, "51_75": 0.67, "26_50": 0.33, "0_25": 0.0, "not_available": 0.5}
SIDE_VALUES = {"left", "right"}


def clamp01(value: float) -> float:
    if pd.isna(value):
        return 0.5
    return float(min(1.0, max(0.0, value)))


def score_map(value: object, mapping: dict[str, float], default: float = 0.5) -> float:
    key = str(value).strip().lower()
    return float(mapping.get(key, default))


def parse_embedding_vector(value: object) -> np.ndarray:
    if isinstance(value, str):
        return np.asarray(ast.literal_eval(value), dtype=np.float32)
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value, dtype=np.float32)
    raise ValueError(f"unsupported embedding vector value type: {type(value)!r}")


def load_embeddings(path: Path) -> dict[str, np.ndarray]:
    frame = pd.read_csv(path)
    required = {"expanded_image_id", "embedding_vector"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    embeddings: dict[str, np.ndarray] = {}
    for _, row in frame.iterrows():
        vec = parse_embedding_vector(row["embedding_vector"])
        norm = float(np.linalg.norm(vec))
        if norm <= 0:
            continue
        embeddings[str(row["expanded_image_id"])] = vec / norm
    return embeddings


def cosine_similarity(image_a: str, image_b: str, embeddings: dict[str, np.ndarray]) -> float:
    if image_a not in embeddings or image_b not in embeddings:
        return float("nan")
    return float(np.dot(embeddings[image_a], embeddings[image_b]))


def load_visual_factors() -> tuple[pd.DataFrame, dict[str, Any]]:
    audit: dict[str, Any] = {"visual_source": None, "missing_fields": [], "fallbacks": []}
    if VISUAL_FACTORS.exists():
        visual = pd.read_csv(VISUAL_FACTORS)
        audit["visual_source"] = str(VISUAL_FACTORS.relative_to(PROJECT_ROOT))
    elif FALLBACK_VISUAL_FACTORS.exists():
        visual = pd.read_csv(FALLBACK_VISUAL_FACTORS)
        audit["visual_source"] = str(FALLBACK_VISUAL_FACTORS.relative_to(PROJECT_ROOT))
        audit["fallbacks"].append("used_phase7a_1000_annotations_because_full_visual_factor_file_missing")
    else:
        visual = pd.DataFrame(columns=["expanded_image_id"])
        audit["visual_source"] = "none"
        audit["fallbacks"].append("visual_factor_files_missing; component scores fall back to phase10 image proxies")

    if "expanded_image_id" not in visual.columns:
        if "source_image_id" in visual.columns:
            visual["expanded_image_id"] = visual["source_image_id"]
            audit["fallbacks"].append("used_source_image_id_as_expanded_image_id")
        else:
            raise ValueError("visual factor table must contain expanded_image_id or source_image_id")
    return visual.drop_duplicates("expanded_image_id").copy(), audit


def build_image_scores(manifest: pd.DataFrame, visual: pd.DataFrame, audit: dict[str, Any]) -> pd.DataFrame:
    image_frame = manifest.drop_duplicates("image_id").copy()
    merged = image_frame.merge(
        visual,
        how="left",
        left_on="image_id",
        right_on="expanded_image_id",
        suffixes=("", "_visual"),
    )

    def fallback_quality(row: pd.Series) -> float:
        if "pf_eri_image_score" in row and not pd.isna(row["pf_eri_image_score"]):
            return clamp01(float(row["pf_eri_image_score"]))
        return score_map(row.get("quality_bucket", "not_available"), QUALITY_BUCKET_SCORE)

    needed = [
        "pattern_visibility",
        "side_visibility",
        "side_evidence_quality",
        "blur_level",
        "occlusion_level",
        "body_fraction_visible",
        "frontal_or_rear_view",
        "silhouette_only",
    ]
    for column in needed:
        if column not in merged.columns:
            audit["missing_fields"].append(column)

    merged["image_pattern_score"] = merged.apply(
        lambda r: score_map(r.get("pattern_visibility", "not_available"), PATTERN_SCORE, fallback_quality(r)), axis=1
    )
    merged["image_side_evidence_score"] = merged.apply(
        lambda r: score_map(r.get("side_evidence_quality", "not_available"), SIDE_EVIDENCE_SCORE, fallback_quality(r)),
        axis=1,
    )
    merged["image_blur_score"] = merged.apply(
        lambda r: score_map(r.get("blur_level", "not_available"), BLUR_SCORE, fallback_quality(r)), axis=1
    )
    merged["image_occlusion_score"] = merged.apply(
        lambda r: score_map(r.get("occlusion_level", "not_available"), OCCLUSION_SCORE, fallback_quality(r)), axis=1
    )
    merged["image_body_visibility_score"] = merged.apply(
        lambda r: score_map(r.get("body_fraction_visible", "not_available"), BODY_SCORE, fallback_quality(r)), axis=1
    )
    merged["side_visibility_norm"] = merged.get("side_visibility", pd.Series(["not_available"] * len(merged))).astype(str).str.lower()
    merged["frontal_or_rear_norm"] = merged.get("frontal_or_rear_view", pd.Series(["no"] * len(merged))).astype(str).str.lower()
    merged["silhouette_norm"] = merged.get("silhouette_only", pd.Series(["no"] * len(merged))).astype(str).str.lower()
    return merged.set_index("image_id", drop=False)


def pair_side_comparability(a: pd.Series, b: pd.Series) -> float:
    side_a = str(a.get("side_visibility_norm", "not_available")).lower()
    side_b = str(b.get("side_visibility_norm", "not_available")).lower()
    evidence = min(clamp01(float(a["image_side_evidence_score"])), clamp01(float(b["image_side_evidence_score"])))
    if side_a in SIDE_VALUES and side_b in SIDE_VALUES:
        side_match = 1.0 if side_a == side_b else 0.25
    elif side_a == side_b and side_a not in {"not_available", "nan", ""}:
        side_match = 0.50
    else:
        side_match = 0.40
    return clamp01(evidence * side_match)


def pair_viewpoint_compatibility(a: pd.Series, b: pd.Series) -> float:
    penalty = 0.0
    if str(a.get("frontal_or_rear_norm", "no")) == "yes":
        penalty += 0.30
    if str(b.get("frontal_or_rear_norm", "no")) == "yes":
        penalty += 0.30
    if str(a.get("silhouette_norm", "no")) == "yes":
        penalty += 0.50
    if str(b.get("silhouette_norm", "no")) == "yes":
        penalty += 0.50
    return clamp01(1.0 - penalty)


def weighted_pair_score(row: dict[str, Any]) -> float:
    return clamp01(sum(PAIR_SCORE_WEIGHTS[key] * float(row[key]) for key in PAIR_SCORE_WEIGHTS))


def build_pairs_for_group(
    split_id: int,
    group_name: str,
    group_frame: pd.DataFrame,
    image_scores: pd.DataFrame,
    embeddings: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = group_frame.sort_values(["identity_label_internal", "image_id"]).reset_index(drop=True)
    for idx_a, idx_b in itertools.combinations(range(len(ordered)), 2):
        ra = ordered.iloc[idx_a]
        rb = ordered.iloc[idx_b]
        image_a = str(ra["image_id"])
        image_b = str(rb["image_id"])
        ia = image_scores.loc[image_a]
        ib = image_scores.loc[image_b]
        identity_a = str(ra["identity_label_internal"])
        identity_b = str(rb["identity_label_internal"])
        same_identity = identity_a == identity_b
        record: dict[str, Any] = {
            "split_id": int(split_id),
            "group_name": group_name,
            "image_id_a": image_a,
            "image_id_b": image_b,
            "identity_a": identity_a,
            "identity_b": identity_b,
            "same_identity": bool(same_identity),
            "role": "train_pair",
            "descriptor_similarity": cosine_similarity(image_a, image_b, embeddings),
            "side_comparability_score": pair_side_comparability(ia, ib),
            "pattern_pair_score": min(float(ia["image_pattern_score"]), float(ib["image_pattern_score"])),
            "blur_pair_score": min(float(ia["image_blur_score"]), float(ib["image_blur_score"])),
            "occlusion_pair_score": min(float(ia["image_occlusion_score"]), float(ib["image_occlusion_score"])),
            "body_visibility_pair_score": min(float(ia["image_body_visibility_score"]), float(ib["image_body_visibility_score"])),
            "viewpoint_compatibility_score": pair_viewpoint_compatibility(ia, ib),
            "source_manifest_path": str(PHASE10_MANIFEST.relative_to(PROJECT_ROOT)),
        }
        record["pair_reliability_score"] = weighted_pair_score(record)
        record["positive_pair_weight"] = record["pair_reliability_score"] if same_identity else 0.0
        record["negative_pair_weight"] = 0.0 if same_identity else 1.0
        record["hard_negative_flag"] = False
        record["pf_eri_pair_penalty"] = 1.0 - float(record["pair_reliability_score"])
        rows.append(record)
    return rows


def add_hard_negative_weights(pair_table: pd.DataFrame) -> pd.DataFrame:
    pair_table = pair_table.copy()
    negative = pair_table[~pair_table["same_identity"].astype(bool)].copy()
    if negative.empty:
        pair_table["hard_negative_flag"] = False
        return pair_table
    valid_similarity = pd.to_numeric(negative["descriptor_similarity"], errors="coerce").dropna()
    high_similarity_threshold = float(valid_similarity.quantile(0.90)) if len(valid_similarity) else 0.8
    low_reliability_threshold = 0.40
    mask = (
        (~pair_table["same_identity"].astype(bool))
        & (pd.to_numeric(pair_table["descriptor_similarity"], errors="coerce") >= high_similarity_threshold)
        & (pd.to_numeric(pair_table["pair_reliability_score"], errors="coerce") <= low_reliability_threshold)
    )
    pair_table.loc[mask, "hard_negative_flag"] = True
    pair_table.loc[mask, "negative_pair_weight"] = 0.25
    pair_table.attrs["hard_negative_similarity_threshold"] = high_similarity_threshold
    pair_table.attrs["hard_negative_reliability_threshold"] = low_reliability_threshold
    return pair_table


def write_score_summary(pair_table: pd.DataFrame, field_audit: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for group_cols in [["split_id"], ["split_id", "group_name"], ["group_name"]]:
        grouped = pair_table.groupby(group_cols, dropna=False)
        for keys, frame in grouped:
            if not isinstance(keys, tuple):
                keys = (keys,)
            row: dict[str, Any] = {col: val for col, val in zip(group_cols, keys)}
            score = pd.to_numeric(frame["pair_reliability_score"], errors="coerce")
            row.update(
                {
                    "pair_count": int(len(frame)),
                    "same_pair_count": int(frame["same_identity"].astype(bool).sum()),
                    "different_pair_count": int((~frame["same_identity"].astype(bool)).sum()),
                    "hard_negative_count": int(frame["hard_negative_flag"].astype(bool).sum()),
                    "score_min": float(score.min()),
                    "score_q25": float(score.quantile(0.25)),
                    "score_mean": float(score.mean()),
                    "score_q75": float(score.quantile(0.75)),
                    "score_max": float(score.max()),
                }
            )
            rows.append(row)
    rows.append(
        {
            "split_id": "ALL",
            "group_name": "ALL",
            "pair_count": int(len(pair_table)),
            "same_pair_count": int(pair_table["same_identity"].astype(bool).sum()),
            "different_pair_count": int((~pair_table["same_identity"].astype(bool)).sum()),
            "hard_negative_count": int(pair_table["hard_negative_flag"].astype(bool).sum()),
            "score_min": float(pair_table["pair_reliability_score"].min()),
            "score_q25": float(pair_table["pair_reliability_score"].quantile(0.25)),
            "score_mean": float(pair_table["pair_reliability_score"].mean()),
            "score_q75": float(pair_table["pair_reliability_score"].quantile(0.75)),
            "score_max": float(pair_table["pair_reliability_score"].max()),
        }
    )
    pd.DataFrame(rows).to_csv(SCORE_SUMMARY, index=False)
    FIELD_AUDIT.write_text(json.dumps(field_audit, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(PHASE10_MANIFEST)
    required = {"split_id", "phase10_lite_plus_group", "image_id", "identity_label_internal", "train_val_test_role"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Phase 10 manifest missing columns: {sorted(missing)}")
    roles = sorted(manifest["train_val_test_role"].astype(str).str.lower().unique())
    if roles != ["train"]:
        raise ValueError(f"Phase 11 pair table must use train-only Phase 10 rows; observed roles={roles}")

    visual, field_audit = load_visual_factors()
    image_scores = build_image_scores(manifest, visual, field_audit)
    embeddings = load_embeddings(EMBEDDINGS)
    missing_embeddings = sorted(set(manifest["image_id"].astype(str)) - set(embeddings))
    field_audit["missing_embedding_count"] = len(missing_embeddings)
    field_audit["missing_embedding_first_10"] = missing_embeddings[:10]

    rows: list[dict[str, Any]] = []
    for (split_id, group_name), group_frame in manifest.groupby(["split_id", "phase10_lite_plus_group"], sort=True):
        rows.extend(build_pairs_for_group(int(split_id), str(group_name), group_frame, image_scores, embeddings))

    pair_table = pd.DataFrame(rows)
    pair_table = add_hard_negative_weights(pair_table)
    field_audit["hard_negative_similarity_threshold"] = pair_table.attrs.get("hard_negative_similarity_threshold")
    field_audit["hard_negative_reliability_threshold"] = pair_table.attrs.get("hard_negative_reliability_threshold")
    pair_table = pair_table.sort_values(["split_id", "group_name", "identity_a", "identity_b", "image_id_a", "image_id_b"])
    pair_table.to_csv(PAIR_TABLE, index=False)
    write_score_summary(pair_table, field_audit)
    print(f"Wrote {PAIR_TABLE.relative_to(PROJECT_ROOT)} rows={len(pair_table)}")
    print(f"Wrote {SCORE_SUMMARY.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {FIELD_AUDIT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
