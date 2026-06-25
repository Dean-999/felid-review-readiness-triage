#!/usr/bin/env python3
"""Build detector-first/proxy AI-assisted evidence admission for Phase 14."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, precision_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_detector_first_admission"
CALIBRATION_400 = PROJECT_ROOT / "outputs/phase14/phase14_2x2_manual_audit_400/phase14_2x2_manual_audit_400_calibrated_labels.csv"
VALIDATION_200 = Path("/Users/deanshen/Downloads/phase14_strict_2x2_validation_audit_200_manual_reviewed.csv")
CANDIDATE_POOL = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv"

TARGET_CLASSES = ["high_confidence", "low_evidence_stress", "review_limited_middle", "uncertain_excluded"]
CATEGORICAL_COLUMNS = [
    "dataset_role",
    "environment_context",
    "pool_source",
    "human_review_bucket",
    "human_review_confidence",
    "human_pattern_visibility",
    "human_side_flank_visibility",
    "human_body_visibility",
    "human_blur_level",
    "human_occlusion_level",
    "human_background_complexity",
    "human_modified_background",
    "strict_evidence_tier",
    "strict_training_eligible",
    "strict_stress_test_eligible",
    "evidence_tier",
    "training_eligible",
    "stress_test_eligible",
    "auto_blur_band",
    "auto_exposure_band",
    "auto_contrast_band",
    "auto_center_animal_signal",
    "auto_review_bucket",
]
NUMERIC_COLUMNS = [
    "auto_evidence_score",
    "auto_quality_score",
    "brightness_mean",
    "contrast_std",
    "blur_laplacian_var",
    "entropy",
    "edge_density",
    "center_contrast",
    "center_edge_density",
    "underexposed_fraction",
    "overexposed_fraction",
    "colorfulness",
]


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def entropy(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    prob = hist / max(hist.sum(), 1.0)
    prob = prob[prob > 0]
    return float(-(prob * np.log2(prob)).sum())


def colorfulness(rgb: np.ndarray) -> float:
    arr = rgb.astype(np.float32)
    rg = arr[:, :, 0] - arr[:, :, 1]
    yb = 0.5 * (arr[:, :, 0] + arr[:, :, 1]) - arr[:, :, 2]
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def crop_stats(rgb: np.ndarray) -> dict[str, float]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return {
        "proxy_crop_brightness": float(gray.mean()),
        "proxy_crop_contrast": float(gray.std()),
        "proxy_crop_blur_laplacian": float(lap.var()),
        "proxy_crop_entropy": entropy(gray),
        "proxy_crop_edge_density": float((edges > 0).mean()),
        "proxy_crop_underexposed_fraction": float((gray < 30).mean()),
        "proxy_crop_overexposed_fraction": float((gray > 225).mean()),
        "proxy_crop_colorfulness": colorfulness(rgb),
    }


def proxy_object_box(rgb: np.ndarray) -> tuple[int, int, int, int, dict[str, float]]:
    height, width = rgb.shape[:2]
    max_side = max(height, width)
    scale = 768.0 / max_side if max_side > 768 else 1.0
    small = cv2.resize(rgb, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else rgb
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    edges = cv2.Canny(blur, 35, 120)
    kernel = np.ones((9, 9), np.uint8)
    mask = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(80.0, 0.001 * small.shape[0] * small.shape[1])
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue
        cx = (x + w / 2) / small.shape[1]
        cy = (y + h / 2) / small.shape[0]
        center_penalty = math.sqrt((cx - 0.5) ** 2 + (cy - 0.5) ** 2)
        score = area / (1.0 + center_penalty)
        candidates.append((score, x, y, w, h))
    if candidates:
        _, x, y, w, h = max(candidates, key=lambda item: item[0])
    else:
        x, y, w, h = 0, 0, small.shape[1], small.shape[0]

    inv = 1.0 / scale
    x0 = max(0, int(x * inv))
    y0 = max(0, int(y * inv))
    x1 = min(width, int((x + w) * inv))
    y1 = min(height, int((y + h) * inv))
    if x1 <= x0 or y1 <= y0:
        x0, y0, x1, y1 = 0, 0, width, height
    bw = x1 - x0
    bh = y1 - y0
    edge_margin = 0.025
    features = {
        "proxy_detector_confidence": 0.35 if candidates else 0.0,
        "proxy_bbox_x0": x0 / max(width, 1),
        "proxy_bbox_y0": y0 / max(height, 1),
        "proxy_bbox_width_fraction": bw / max(width, 1),
        "proxy_bbox_height_fraction": bh / max(height, 1),
        "proxy_bbox_area_fraction": (bw * bh) / max(width * height, 1),
        "proxy_bbox_aspect_ratio": bw / max(bh, 1),
        "proxy_bbox_center_x": (x0 + bw / 2) / max(width, 1),
        "proxy_bbox_center_y": (y0 + bh / 2) / max(height, 1),
        "proxy_bbox_edge_touch": float(
            x0 <= edge_margin * width
            or y0 <= edge_margin * height
            or x1 >= (1 - edge_margin) * width
            or y1 >= (1 - edge_margin) * height
        ),
        "proxy_bbox_small_animal_risk": float((bw * bh) / max(width * height, 1) < 0.05),
        "proxy_bbox_extreme_crop_risk": float(
            x0 <= edge_margin * width
            or x1 >= (1 - edge_margin) * width
            or y0 <= edge_margin * height
            or y1 >= (1 - edge_margin) * height
        ),
        "proxy_bbox_candidate_count": float(len(candidates)),
    }
    return x0, y0, x1, y1, features


def image_proxy_features(path_text: object) -> dict[str, Any]:
    path = resolve(path_text)
    base: dict[str, Any] = {
        "detector_source": "local_cv_objectness_proxy_not_pretrained_detector",
        "image_read_status": "failed",
        "image_width": np.nan,
        "image_height": np.nan,
    }
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            rgb = np.asarray(img)
    except Exception as exc:
        base["image_error"] = repr(exc)
        return base
    height, width = rgb.shape[:2]
    x0, y0, x1, y1, bbox_features = proxy_object_box(rgb)
    crop = rgb[y0:y1, x0:x1]
    base.update({"image_read_status": "ok", "image_width": width, "image_height": height, "image_error": ""})
    base.update(bbox_features)
    base.update(crop_stats(crop if crop.size else rgb))
    return base


def build_manual_table() -> pd.DataFrame:
    first = pd.read_csv(CALIBRATION_400, low_memory=False)
    second = pd.read_csv(VALIDATION_200, low_memory=False)
    first["manual_source"] = "audit_400_calibrated"
    second["manual_source"] = "strict_validation_200"
    table = pd.concat([first, second], ignore_index=True, sort=False)
    table = table[table["manual_evidence_tier"].isin(TARGET_CLASSES)].copy()
    table["target_evidence_tier"] = table["manual_evidence_tier"].astype(str)
    return table


def feature_table(table: pd.DataFrame, cache_path: Path, limit: int | None = None, workers: int = 1) -> pd.DataFrame:
    if cache_path.exists():
        cached = pd.read_csv(cache_path, low_memory=False)
        if limit is None or len(cached) >= min(limit, len(table)):
            return cached.head(limit) if limit else cached
    source = table.head(limit).copy() if limit else table.copy()
    paths = source["evidence_image_path"].tolist()
    rows = []
    workers = max(1, int(workers))
    if workers == 1:
        iterator = map(image_proxy_features, paths)
    else:
        pool = ThreadPoolExecutor(max_workers=workers)
        iterator = pool.map(image_proxy_features, paths)
    try:
        for index, features in enumerate(iterator):
            features["evidence_image_path"] = paths[index]
            rows.append(features)
            if (index + 1) % 500 == 0 or (index + 1) == len(source):
                print(f"feature extraction {index + 1}/{len(source)}", flush=True)
    finally:
        if workers != 1:
            pool.shutdown(wait=True, cancel_futures=False)
    frame = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def model_matrix(frame: pd.DataFrame, fit_columns: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    data = frame.copy()
    for col in NUMERIC_COLUMNS:
        if col not in data.columns:
            data[col] = np.nan
        data[col] = pd.to_numeric(data[col], errors="coerce")
    numeric = data[NUMERIC_COLUMNS + [c for c in data.columns if c.startswith("proxy_")]].copy()
    numeric = numeric.apply(pd.to_numeric, errors="coerce").fillna(-1)
    categoricals = []
    for col in CATEGORICAL_COLUMNS + ["detector_source", "image_read_status"]:
        if col in data.columns:
            categoricals.append(col)
    cats = pd.get_dummies(data[categoricals].fillna("missing").astype(str), prefix=categoricals, dummy_na=False)
    matrix = pd.concat([numeric, cats], axis=1)
    if fit_columns is not None:
        matrix = matrix.reindex(columns=fit_columns, fill_value=0)
        return matrix, fit_columns
    return matrix, list(matrix.columns)


def choose_threshold(y_true: pd.Series, proba: np.ndarray, classes: np.ndarray, target_precision: float) -> dict[str, Any]:
    high_index = int(np.where(classes == "high_confidence")[0][0])
    stress_index = int(np.where(classes == "low_evidence_stress")[0][0])
    best = None
    for threshold in np.linspace(0.50, 0.95, 46):
        labels = []
        truth = []
        for i, true_label in enumerate(y_true):
            high_p = proba[i, high_index]
            stress_p = proba[i, stress_index]
            if high_p >= threshold and high_p >= stress_p:
                labels.append("high_confidence")
                truth.append(true_label)
            elif stress_p >= threshold and stress_p > high_p:
                labels.append("low_evidence_stress")
                truth.append(true_label)
        if not labels:
            continue
        precision = float(np.mean([pred == true for pred, true in zip(labels, truth)]))
        coverage = len(labels) / len(y_true)
        candidate = {"threshold": float(round(threshold, 3)), "precision": precision, "coverage": coverage, "auto_count": len(labels)}
        if precision >= target_precision:
            if best is None or candidate["coverage"] > best["coverage"]:
                best = candidate
    if best is None:
        threshold = 0.95
        labels = []
        truth = []
        for i, true_label in enumerate(y_true):
            high_p = proba[i, high_index]
            stress_p = proba[i, stress_index]
            if high_p >= threshold and high_p >= stress_p:
                labels.append("high_confidence")
                truth.append(true_label)
            elif stress_p >= threshold and stress_p > high_p:
                labels.append("low_evidence_stress")
                truth.append(true_label)
        best = {
            "threshold": threshold,
            "precision": float(np.mean([pred == true for pred, true in zip(labels, truth)])) if labels else 0.0,
            "coverage": len(labels) / len(y_true),
            "auto_count": len(labels),
            "target_met": False,
        }
    else:
        best["target_met"] = True
    return best


def route_predictions(frame: pd.DataFrame, proba: np.ndarray, classes: np.ndarray, threshold: float) -> pd.DataFrame:
    out = frame.copy()
    for i, cls in enumerate(classes):
        out[f"prob_{cls}"] = proba[:, i]
    max_idx = proba.argmax(axis=1)
    out["ai_predicted_tier"] = [str(classes[i]) for i in max_idx]
    out["ai_prediction_confidence"] = proba.max(axis=1)
    high_p = out.get("prob_high_confidence", pd.Series(0, index=out.index))
    stress_p = out.get("prob_low_evidence_stress", pd.Series(0, index=out.index))
    high_proxy_risk = (
        out.get("proxy_bbox_edge_touch", pd.Series(0, index=out.index)).astype(float).ge(1)
        | out.get("proxy_bbox_small_animal_risk", pd.Series(0, index=out.index)).astype(float).ge(1)
        | out.get("proxy_crop_blur_laplacian", pd.Series(np.inf, index=out.index)).astype(float).lt(12)
        | out.get("proxy_crop_contrast", pd.Series(np.inf, index=out.index)).astype(float).lt(12)
    )
    out["ai_route"] = "human_review_required"
    out["ai_high_route_blocked_by_proxy_risk"] = False
    high_auto_mask = (high_p >= threshold) & (high_p >= stress_p)
    stress_auto_mask = (stress_p >= threshold) & (stress_p > high_p)
    out.loc[high_auto_mask & ~high_proxy_risk, "ai_route"] = "ai_auto_high_confidence"
    out.loc[high_auto_mask & high_proxy_risk, "ai_high_route_blocked_by_proxy_risk"] = True
    out.loc[stress_auto_mask, "ai_route"] = "ai_auto_low_evidence_stress"
    out.loc[out["image_read_status"].ne("ok"), "ai_route"] = "excluded_unreadable"
    risk_flags = []
    for _, row in out.iterrows():
        flags = []
        if float(row.get("proxy_bbox_edge_touch", 0)) >= 1:
            flags.append("edge_touch")
        if float(row.get("proxy_bbox_small_animal_risk", 0)) >= 1:
            flags.append("small_animal_proxy")
        if bool(row.get("ai_high_route_blocked_by_proxy_risk", False)):
            flags.append("high_route_blocked_by_proxy_risk")
        if row.get("image_read_status") != "ok":
            flags.append("unreadable")
        if row.get("ai_prediction_confidence", 0) < threshold:
            flags.append("low_model_confidence")
        risk_flags.append("|".join(flags))
    out["ai_risk_flags"] = risk_flags
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--target-precision", type=float, default=0.75)
    parser.add_argument("--candidate-limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manual = build_manual_table()
    manual_features = feature_table(
        manual,
        out_dir / "phase14_detector_first_manual_image_proxy_features.csv",
        workers=args.workers,
    )
    train = pd.concat([manual.reset_index(drop=True), manual_features.drop(columns=["evidence_image_path"], errors="ignore")], axis=1)
    x, columns = model_matrix(train)
    y = train["target_evidence_tier"].astype(str)
    clf = RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=4,
        class_weight="balanced_subsample",
        random_state=20260619,
        n_jobs=-1,
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=20260619)
    cv_proba = cross_val_predict(clf, x, y, cv=cv, method="predict_proba", n_jobs=-1)
    clf.fit(x, y)
    classes = clf.classes_
    threshold_info = choose_threshold(y, cv_proba, classes, args.target_precision)
    cv_pred = np.array([classes[i] for i in cv_proba.argmax(axis=1)])
    cv_routed = route_predictions(train, cv_proba, classes, threshold_info["threshold"])
    cv_auto_mask = cv_routed["ai_route"].isin(["ai_auto_high_confidence", "ai_auto_low_evidence_stress"])
    if cv_auto_mask.any():
        route_to_tier = {
            "ai_auto_high_confidence": "high_confidence",
            "ai_auto_low_evidence_stress": "low_evidence_stress",
        }
        cv_auto_pred = cv_routed.loc[cv_auto_mask, "ai_route"].map(route_to_tier).astype(str)
        cv_auto_true = y.loc[cv_auto_mask].astype(str)
        cv_routed_precision = float((cv_auto_pred.to_numpy() == cv_auto_true.to_numpy()).mean())
    else:
        cv_routed_precision = 0.0
    evaluation = {
        "manual_rows": int(len(train)),
        "class_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "target_precision": args.target_precision,
        "selected_threshold": threshold_info,
        "risk_gated_cv_auto_precision": cv_routed_precision,
        "risk_gated_cv_auto_coverage": float(cv_auto_mask.mean()),
        "risk_gated_cv_route_counts": {
            str(k): int(v) for k, v in cv_routed["ai_route"].value_counts().sort_index().items()
        },
        "overall_cv_accuracy": float((cv_pred == y.to_numpy()).mean()),
        "classification_report": classification_report(y, cv_pred, labels=list(classes), output_dict=True, zero_division=0),
        "confusion_matrix_labels": [str(c) for c in classes],
        "confusion_matrix": confusion_matrix(y, cv_pred, labels=list(classes)).tolist(),
        "detector_source": "local_cv_objectness_proxy_not_pretrained_detector",
        "pretrained_detector_status": "not_yet_integrated_schema_ready",
        "claim_boundary": "first-pass conservative AI admission; auto-routes only above calibrated threshold",
    }
    (out_dir / "phase14_detector_first_model_evaluation.json").write_text(
        json.dumps(evaluation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    train.to_csv(out_dir / "phase14_detector_first_training_table.csv", index=False)

    candidates = pd.read_csv(CANDIDATE_POOL, low_memory=False)
    if args.candidate_limit:
        candidates = candidates.head(args.candidate_limit).copy()
    candidate_features = feature_table(
        candidates,
        out_dir / ("phase14_detector_first_candidate_image_proxy_features.csv" if not args.candidate_limit else f"phase14_detector_first_candidate_image_proxy_features_limit_{args.candidate_limit}.csv"),
        limit=args.candidate_limit,
        workers=args.workers,
    )
    scored_base = pd.concat([candidates.reset_index(drop=True), candidate_features.drop(columns=["evidence_image_path"], errors="ignore")], axis=1)
    x_candidates, _ = model_matrix(scored_base, columns)
    candidate_proba = clf.predict_proba(x_candidates)
    scored = route_predictions(scored_base, candidate_proba, classes, threshold_info["threshold"])
    scored.to_csv(out_dir / "phase14_detector_first_candidate_scores.csv", index=False)
    scored[scored["ai_route"].eq("ai_auto_high_confidence")].to_csv(
        out_dir / "phase14_detector_first_auto_high_candidates.csv",
        index=False,
    )
    scored[scored["ai_route"].eq("ai_auto_low_evidence_stress")].to_csv(
        out_dir / "phase14_detector_first_auto_stress_candidates.csv",
        index=False,
    )
    scored[scored["ai_route"].eq("human_review_required")].to_csv(
        out_dir / "phase14_detector_first_human_review_required.csv",
        index=False,
    )
    summary = {
        "candidate_rows": int(len(scored)),
        "route_counts": {str(k): int(v) for k, v in scored["ai_route"].value_counts().sort_index().items()},
        "threshold": threshold_info,
        "outputs": {
            "training_table": rel(out_dir / "phase14_detector_first_training_table.csv"),
            "evaluation": rel(out_dir / "phase14_detector_first_model_evaluation.json"),
            "candidate_scores": rel(out_dir / "phase14_detector_first_candidate_scores.csv"),
            "auto_high": rel(out_dir / "phase14_detector_first_auto_high_candidates.csv"),
            "auto_stress": rel(out_dir / "phase14_detector_first_auto_stress_candidates.csv"),
            "human_review": rel(out_dir / "phase14_detector_first_human_review_required.csv"),
        },
    }
    (out_dir / "phase14_detector_first_admission_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 detector-first AI admission "
        f"manual_rows={len(train)} candidate_rows={len(scored)} "
        f"threshold={threshold_info['threshold']} precision={threshold_info['precision']:.3f} "
        f"coverage={threshold_info['coverage']:.3f} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
