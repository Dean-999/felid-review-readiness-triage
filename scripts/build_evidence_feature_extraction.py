#!/usr/bin/env python3
"""Compute PF-ERI pair-level evidence features from constructed pair tables."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional strong-descriptor enhancement
    np = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_CONSTRUCTION_DIR = PROJECT_ROOT / "outputs/modeling-validation/pair-construction"
PAIR_INDEX_CSV = PAIR_CONSTRUCTION_DIR / "pair_construction_index.csv"
IMAGE_INDEX_CSV = PROJECT_ROOT / "outputs/modeling-validation/final-modeling-bootstrap/final_modeling_image_index.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/evidence-feature-extraction"
FEATURE_TABLE_CSV = OUTPUT_DIR / "pair_evidence_features.csv"
FEATURE_SCHEMA_JSON = OUTPUT_DIR / "pair_evidence_feature_schema.json"
AUDIT_JSON = OUTPUT_DIR / "pair_evidence_feature_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

MEGADESCRIPTOR_PAIR_SCORES = (
    PROJECT_ROOT
    / "outputs/modeling-validation/pair-level-validation/returned_strong_baselines/megadescriptor_l_384/pair_scores.csv"
)
DINOV2_PAIR_SCORES = (
    PROJECT_ROOT
    / "outputs/modeling-validation/pair-level-validation/returned_strong_baselines/dinov2_vitl14/pair_scores.csv"
)
MEGADESCRIPTOR_ROOT = PROJECT_ROOT / "outputs/modeling-validation/pair-level-validation/returned_strong_baselines/megadescriptor_l_384"
DINOV2_ROOT = PROJECT_ROOT / "outputs/modeling-validation/pair-level-validation/returned_strong_baselines/dinov2_vitl14"

CORE_FEATURES = [
    "visible_pattern_area_score",
    "viewpoint_side_compatibility",
    "body_part_overlap_score",
    "night_or_motion_blur_risk",
    "cross_descriptor_agreement_score",
    "source_domain_shift_score",
]

OUTPUT_COLUMNS = [
    "pair_id",
    "pair_family",
    "pair_scope",
    "construction_rule",
    "query_image_id",
    "candidate_image_id",
    "split_id",
    "split_role",
    "identity_relation",
    "same_identity_label",
    "target_label_role",
    *CORE_FEATURES,
    "query_visible_pattern_area_score",
    "candidate_visible_pattern_area_score",
    "query_subject_area_score",
    "candidate_subject_area_score",
    "query_blur_risk_score",
    "candidate_blur_risk_score",
    "pair_size_compatibility_score",
    "pair_domain_mismatch",
    "megadescriptor_similarity",
    "dinov2_similarity",
    "descriptor_score_source",
    "visible_pattern_area_source",
    "viewpoint_side_compatibility_source",
    "body_part_overlap_source",
    "night_or_motion_blur_risk_source",
    "cross_descriptor_agreement_source",
    "source_domain_shift_source",
    "predictor_field_set",
    "blocked_leakage_fields_present",
    "claim_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clamp01(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, value))


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def score_from_area_fraction(value: Any) -> float | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    return clamp01(numeric / 0.30)


def score_from_clarity(value: Any) -> float | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    return clamp01(numeric / 120.0)


def risk_from_clarity(value: Any) -> float | None:
    clarity = score_from_clarity(value)
    if clarity is None:
        return None
    return round(clamp01(1.0 - clarity), 6)


def first_nonempty(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def load_manifest_rows(image_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    manifests: dict[str, list[dict[str, str]]] = {}
    enriched: dict[str, dict[str, str]] = {}
    for image in image_rows:
        manifest_path = PROJECT_ROOT / image["source_manifest_path"]
        if str(manifest_path) not in manifests:
            manifests[str(manifest_path)] = read_csv(manifest_path)
        source_index = int(image["source_row_number"]) - 1
        source_row = manifests[str(manifest_path)][source_index]
        enriched[image["image_id"]] = {**image, **{f"source_{k}": v for k, v in source_row.items()}}
    return enriched


def legacy_phase18_id(image_id: str) -> str:
    if image_id.startswith("pferi_lynx_wild_"):
        return f"phase18a_czechlynx_{int(image_id.rsplit('_', 1)[1]):04d}"
    if image_id.startswith("pferi_bobcat_wild_"):
        return f"phase18a_bobcat_{int(image_id.rsplit('_', 1)[1]):04d}"
    return ""


def load_pair_score_lookup(path: Path) -> dict[tuple[str, str], float]:
    if not path.exists():
        return {}
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv(path):
        score = to_float(row.get("strong_descriptor_similarity"))
        if score is None:
            continue
        lookup[(row["query_image_id"], row["candidate_image_id"])] = score
    return lookup


def load_embedding_lookup(root: Path) -> dict[str, Any]:
    if np is None:
        return {}
    manifest = root / "embedding_manifest.csv"
    embeddings_path = root / "embeddings.npy"
    if not manifest.exists() or not embeddings_path.exists():
        return {}
    embeddings = np.load(embeddings_path).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms
    lookup: dict[str, Any] = {}
    for row in read_csv(manifest):
        lookup[row["phase18_image_id"]] = embeddings[int(row["embedding_row"])]
    return lookup


def embedding_similarity(lookup: dict[str, Any], query_id: str, candidate_id: str) -> float | None:
    if np is None:
        return None
    query = lookup.get(query_id)
    candidate = lookup.get(candidate_id)
    if query is None or candidate is None:
        return None
    cosine = float(np.dot(query, candidate))
    return round(clamp01((cosine + 1.0) / 2.0), 8)


def image_evidence(row: dict[str, str]) -> dict[str, Any]:
    scope = row["scope"]
    if scope == "bobcat-urban":
        area = score_from_area_fraction(row.get("source_md_area_fraction"))
        pattern = to_float(row.get("source_pattern_evidence_score"))
        side = to_float(row.get("source_side_flank_evidence_score"))
        body = to_float(row.get("source_body_visibility_score"))
        blur_evidence = to_float(row.get("source_blur_evidence_score"))
        risk = to_float(row.get("source_image_evidence_risk_score"))
        visible = clamp01((area if area is not None else 0.5) * (pattern if pattern is not None else 0.75))
        return {
            "subject_area_score": round(area if area is not None else 0.5, 6),
            "visible_pattern_area_score": round(visible, 6),
            "side_visibility_score": round(clamp01(side if side is not None else 0.65), 6),
            "body_visibility_score": round(clamp01(body if body is not None else 0.70), 6),
            "blur_risk_score": round(clamp01(risk if risk is not None else 1.0 - (blur_evidence if blur_evidence is not None else 0.78)), 6),
            "source": "detector_and_phase14_evidence_fields",
        }
    if scope == "bobcat-wild":
        area = score_from_area_fraction(row.get("source_phase19_area10_area_fraction"))
        clarity = score_from_clarity(row.get("source_phase19_clarity_second_pass_score"))
        if area is not None and clarity is not None:
            visible = clamp01(0.60 * area + 0.40 * clarity)
            risk = risk_from_clarity(row.get("source_phase19_clarity_second_pass_score"))
            source = "phase19_area10_and_clarity_fields"
        elif area is not None:
            visible = area
            risk = 0.22
            source = "phase19_area10_field_with_strict_freeze_blur_proxy"
        else:
            visible = 0.68
            risk = 0.20
            source = "human_clear_strict_freeze_proxy"
        return {
            "subject_area_score": round(area if area is not None else visible, 6),
            "visible_pattern_area_score": round(visible, 6),
            "side_visibility_score": round(0.68, 6),
            "body_visibility_score": round(0.76, 6),
            "blur_risk_score": round(clamp01(risk if risk is not None else 0.20), 6),
            "source": source,
        }
    return {
        "subject_area_score": 0.72,
        "visible_pattern_area_score": 0.74,
        "side_visibility_score": 0.70,
        "body_visibility_score": 0.78,
        "blur_risk_score": 0.18,
        "source": "czechlynx_strict_freeze_proxy",
    }


def size_compatibility(query: dict[str, str], candidate: dict[str, str]) -> float:
    q_width = to_float(query.get("image_width"))
    q_height = to_float(query.get("image_height"))
    c_width = to_float(candidate.get("image_width"))
    c_height = to_float(candidate.get("image_height"))
    if not all(value and value > 0 for value in [q_width, q_height, c_width, c_height]):
        return 0.6
    q_area = q_width * q_height  # type: ignore[operator]
    c_area = c_width * c_height  # type: ignore[operator]
    ratio = min(q_area, c_area) / max(q_area, c_area)
    return round(clamp01(math.sqrt(ratio)), 6)


def descriptor_agreement(
    pair: dict[str, str],
    megadescriptor_scores: dict[tuple[str, str], float],
    dinov2_scores: dict[tuple[str, str], float],
    megadescriptor_embeddings: dict[str, Any] | None = None,
    dinov2_embeddings: dict[str, Any] | None = None,
) -> tuple[float, str, str, str]:
    qid = legacy_phase18_id(pair["query_image_id"])
    cid = legacy_phase18_id(pair["candidate_image_id"])
    if not qid or not cid:
        return 0.5, "", "", "descriptor_scores_unavailable_for_current_scope"
    if megadescriptor_embeddings is not None and dinov2_embeddings is not None:
        md_embedding_score = embedding_similarity(megadescriptor_embeddings, qid, cid)
        dino_embedding_score = embedding_similarity(dinov2_embeddings, qid, cid)
        if md_embedding_score is not None and dino_embedding_score is not None:
            agreement = 1.0 - min(1.0, abs(md_embedding_score - dino_embedding_score))
            return (
                round(clamp01(agreement), 6),
                f"{md_embedding_score:.8f}",
                f"{dino_embedding_score:.8f}",
                "megadescriptor_and_dinov2_embedding_cosine",
            )
    md = megadescriptor_scores.get((qid, cid))
    dino = dinov2_scores.get((qid, cid))
    if md is None or dino is None:
        return 0.5, str(md or ""), str(dino or ""), "descriptor_pair_not_in_returned_topk_scores"
    agreement = 1.0 - min(1.0, abs(md - dino))
    return round(clamp01(agreement), 6), f"{md:.8f}", f"{dino:.8f}", "megadescriptor_and_dinov2_returned_pair_scores"


def source_domain_shift(pair: dict[str, str]) -> tuple[float, str]:
    if pair["query_species"] != pair["candidate_species"]:
        return 1.0, "species_mismatch"
    if pair["query_domain_label"] != pair["candidate_domain_label"]:
        return 0.85, "domain_mismatch"
    if pair["query_scope"] != pair["candidate_scope"]:
        return 0.55, "scope_mismatch_same_domain"
    if pair["query_scope"] == "lynx-wild":
        return 0.10, "same_scope_known_id_wild"
    if pair["query_scope"] == "bobcat-urban":
        return 0.35, "same_scope_urban_periurban_stress"
    return 0.20, "same_scope_wild_bobcat_transfer"


def enrich_pair(
    pair: dict[str, str],
    images_by_id: dict[str, dict[str, str]],
    megadescriptor_scores: dict[tuple[str, str], float],
    dinov2_scores: dict[tuple[str, str], float],
    megadescriptor_embeddings: dict[str, Any],
    dinov2_embeddings: dict[str, Any],
) -> dict[str, Any]:
    query = images_by_id[pair["query_image_id"]]
    candidate = images_by_id[pair["candidate_image_id"]]
    q_evidence = image_evidence(query)
    c_evidence = image_evidence(candidate)
    size_score = size_compatibility(query, candidate)
    visible = min(q_evidence["visible_pattern_area_score"], c_evidence["visible_pattern_area_score"])
    side = min(q_evidence["side_visibility_score"], c_evidence["side_visibility_score"])
    body = round(clamp01(min(q_evidence["body_visibility_score"], c_evidence["body_visibility_score"]) * size_score), 6)
    blur_risk = max(q_evidence["blur_risk_score"], c_evidence["blur_risk_score"])
    descriptor_score, md_score, dino_score, descriptor_source = descriptor_agreement(
        pair,
        megadescriptor_scores,
        dinov2_scores,
        megadescriptor_embeddings,
        dinov2_embeddings,
    )
    domain_shift, domain_source = source_domain_shift(pair)
    leakage_fields = [
        field
        for field in ["same_identity_label", "query_identity_label", "candidate_identity_label"]
        if str(pair.get(field, "")).strip()
    ]
    return {
        **pair,
        "target_label_role": "target_or_evaluation_label_not_predictor" if pair["identity_relation"] == "known" else "not_available",
        "visible_pattern_area_score": round(visible, 6),
        "viewpoint_side_compatibility": round(side, 6),
        "body_part_overlap_score": body,
        "night_or_motion_blur_risk": round(blur_risk, 6),
        "cross_descriptor_agreement_score": descriptor_score,
        "source_domain_shift_score": domain_shift,
        "query_visible_pattern_area_score": q_evidence["visible_pattern_area_score"],
        "candidate_visible_pattern_area_score": c_evidence["visible_pattern_area_score"],
        "query_subject_area_score": q_evidence["subject_area_score"],
        "candidate_subject_area_score": c_evidence["subject_area_score"],
        "query_blur_risk_score": q_evidence["blur_risk_score"],
        "candidate_blur_risk_score": c_evidence["blur_risk_score"],
        "pair_size_compatibility_score": size_score,
        "pair_domain_mismatch": pair["query_domain_label"] != pair["candidate_domain_label"],
        "megadescriptor_similarity": md_score,
        "dinov2_similarity": dino_score,
        "descriptor_score_source": descriptor_source,
        "visible_pattern_area_source": f"query:{q_evidence['source']}|candidate:{c_evidence['source']}",
        "viewpoint_side_compatibility_source": "minimum_side_visibility_proxy_from_image_evidence",
        "body_part_overlap_source": "minimum_body_visibility_x_pair_size_compatibility",
        "night_or_motion_blur_risk_source": "maximum_image_blur_or_evidence_risk",
        "cross_descriptor_agreement_source": descriptor_source,
        "source_domain_shift_source": domain_source,
        "predictor_field_set": ",".join(CORE_FEATURES),
        "blocked_leakage_fields_present": ";".join(leakage_fields),
        "claim_boundary": "PF-ERI evidence feature table; identity/reviewer/source-name labels are not predictor features.",
    }


def feature_schema() -> dict[str, Any]:
    fields: dict[str, dict[str, str]] = {}
    for field in CORE_FEATURES:
        fields[field] = {
            "role": "core_model_predictor",
            "range": "0..1",
            "description": "Prespecified PF-ERI evidence component.",
        }
    for field in ["same_identity_label", "query_identity_label", "candidate_identity_label"]:
        fields[field] = {
            "role": "target_or_label_not_predictor",
            "leakage_rule": "Must not be used as model input.",
        }
    for field in [
        "pair_family",
        "pair_scope",
        "construction_rule",
        "query_scope",
        "candidate_scope",
        "query_domain_label",
        "candidate_domain_label",
        "descriptor_score_source",
    ]:
        fields[field] = {
            "role": "groupwise_diagnostic_or_sensitivity",
            "leakage_rule": "Not part of the core prespecified model unless used in explicit sensitivity analysis.",
        }
    return {
        "built_at_utc": utc_now(),
        "core_model_predictors": CORE_FEATURES,
        "blocked_predictor_fields": [
            "same_identity_label",
            "query_identity_label",
            "candidate_identity_label",
            "reviewer_label",
            "human_final_decision",
            "source_dataset",
            "dataset_name",
        ],
        "fields": fields,
    }


def audit_features(rows: list[dict[str, Any]], schema: dict[str, Any]) -> dict[str, Any]:
    missing_by_feature = {
        feature: sum(str(row.get(feature, "")).strip() == "" for row in rows)
        for feature in CORE_FEATURES
    }
    range_violations = {
        feature: sum(
            (to_float(row.get(feature), -1.0) is None)
            or float(to_float(row.get(feature), -1.0)) < 0.0
            or float(to_float(row.get(feature), -1.0)) > 1.0
            for row in rows
        )
        for feature in CORE_FEATURES
    }
    blocked_predictor_intersections = sorted(
        set(schema["core_model_predictors"]).intersection(schema["blocked_predictor_fields"])
    )
    failures = []
    if any(missing_by_feature.values()):
        failures.append("core_feature_missing_values")
    if any(range_violations.values()):
        failures.append("core_feature_range_violations")
    if blocked_predictor_intersections:
        failures.append("blocked_fields_in_predictor_set")
    return {
        "built_at_utc": utc_now(),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "input_pair_index_csv": project_relative(PAIR_INDEX_CSV),
        "input_image_index_csv": project_relative(IMAGE_INDEX_CSV),
        "output_feature_table_csv": project_relative(FEATURE_TABLE_CSV),
        "output_schema_json": project_relative(FEATURE_SCHEMA_JSON),
        "pair_rows": len(rows),
        "pair_family_counts": dict(sorted(Counter(row["pair_family"] for row in rows).items())),
        "construction_rule_counts": dict(sorted(Counter(row["construction_rule"] for row in rows).items())),
        "descriptor_score_source_counts": dict(sorted(Counter(row["descriptor_score_source"] for row in rows).items())),
        "visible_pattern_area_source_counts": dict(sorted(Counter(row["visible_pattern_area_source"] for row in rows).items())),
        "missing_by_core_feature": missing_by_feature,
        "range_violations_by_core_feature": range_violations,
        "blocked_predictor_intersections": blocked_predictor_intersections,
        "rows_with_label_fields_present": sum(bool(row["blocked_leakage_fields_present"]) for row in rows),
        "claim_boundary": (
            "Core feature table supports evidence sufficiency modeling. Same/different labels, "
            "review labels, and source names are excluded from the core predictor set."
        ),
    }


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Evidence Feature Extraction",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module computes the prespecified PF-ERI pair-level evidence",
        "components from the pair-construction scaffold.",
        "",
        "## Core Predictors",
        "",
        *[f"- `{feature}`" for feature in CORE_FEATURES],
        "",
        "## Counts",
        "",
        f"- Pair rows: {audit['pair_rows']}",
        f"- Pair families: `{audit['pair_family_counts']}`",
        f"- Descriptor score source counts: `{audit['descriptor_score_source_counts']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    pair_rows = read_csv(PAIR_INDEX_CSV)
    image_rows = read_csv(IMAGE_INDEX_CSV)
    images_by_id = load_manifest_rows(image_rows)
    megadescriptor_scores = load_pair_score_lookup(MEGADESCRIPTOR_PAIR_SCORES)
    dinov2_scores = load_pair_score_lookup(DINOV2_PAIR_SCORES)
    megadescriptor_embeddings = load_embedding_lookup(MEGADESCRIPTOR_ROOT)
    dinov2_embeddings = load_embedding_lookup(DINOV2_ROOT)
    features = [
        enrich_pair(
            pair,
            images_by_id,
            megadescriptor_scores,
            dinov2_scores,
            megadescriptor_embeddings,
            dinov2_embeddings,
        )
        for pair in pair_rows
    ]
    schema = feature_schema()
    audit = audit_features(features, schema)
    write_csv(FEATURE_TABLE_CSV, features, OUTPUT_COLUMNS)
    write_json(FEATURE_SCHEMA_JSON, schema)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
