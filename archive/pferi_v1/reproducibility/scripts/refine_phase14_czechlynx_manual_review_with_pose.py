#!/usr/bin/env python3
"""Use CzechLynx pose metadata to refine low-confidence Phase 14 labels."""

from __future__ import annotations

import argparse
import ast
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOW = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_3000_refined_needs_manual_check.csv"
DEFAULT_META = PROJECT_ROOT / "data/raw/czechlynx/CzechLynxDataset-Metadata-Real.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUT = OUT_DIR / "czechlynx_phase14_1341_pose_refined_review_labels.csv"
DEFAULT_REMAINING = OUT_DIR / "czechlynx_phase14_1341_pose_refined_still_needs_manual_check.csv"
DEFAULT_PROMOTED = OUT_DIR / "czechlynx_phase14_1341_pose_refined_promoted.csv"
DEFAULT_AUDIT = OUT_DIR / "czechlynx_phase14_1341_pose_refinement_audit.json"

FRONT_KEYS = {"nose", "left-eye", "right-eye", "left-earbase", "right-earbase", "throat"}
TORSO_KEYS = {"withers", "tailbase", "R-B-knee", "L-B-knee", "R-F-elbow", "L-F-elbow"}
PAW_KEYS = {"R-B-paw", "L-B-paw", "R-F-paw", "L-F-paw", "R-B-ankle", "L-B-ankle", "R-F-wrist", "L-F-wrist"}
LEFT_KEYS = {"L-B-knee", "L-F-elbow", "L-B-paw", "L-F-paw", "L-B-ankle", "L-F-wrist", "left-eye", "left-earbase"}
RIGHT_KEYS = {"R-B-knee", "R-F-elbow", "R-B-paw", "R-F-paw", "R-B-ankle", "R-F-wrist", "right-eye", "right-earbase"}


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_pose(value: object) -> dict[str, list[float]]:
    if pd.isna(value):
        return {}
    text = str(value)
    if not text or text == "nan":
        return {}
    try:
        parsed = ast.literal_eval(text)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    pose: dict[str, list[float]] = {}
    for key, coords in parsed.items():
        if isinstance(coords, (list, tuple)) and len(coords) == 2:
            try:
                x = float(coords[0])
                y = float(coords[1])
            except Exception:
                continue
            if math.isfinite(x) and math.isfinite(y):
                pose[str(key)] = [x, y]
    return pose


def pose_features(pose: dict[str, list[float]], width: float, height: float) -> dict[str, Any]:
    keys = set(pose)
    visible = len(keys)
    front = len(keys & FRONT_KEYS)
    torso = len(keys & TORSO_KEYS)
    paws = len(keys & PAW_KEYS)
    left = len(keys & LEFT_KEYS)
    right = len(keys & RIGHT_KEYS)
    xs = [xy[0] for xy in pose.values()]
    ys = [xy[1] for xy in pose.values()]
    bbox_w = (max(xs) - min(xs)) / max(width, 1.0) if xs else 0.0
    bbox_h = (max(ys) - min(ys)) / max(height, 1.0) if ys else 0.0
    bbox_area = bbox_w * bbox_h
    if torso >= 4 and visible >= 12 and bbox_area >= 0.15:
        body = "76_100"
    elif torso >= 3 and visible >= 8 and bbox_area >= 0.08:
        body = "51_75"
    elif visible >= 4 and bbox_area >= 0.03:
        body = "26_50"
    elif visible:
        body = "0_25"
    else:
        body = "unknown"

    if left >= 3 and right >= 3:
        side = "both"
    elif left >= 3:
        side = "left"
    elif right >= 3:
        side = "right"
    elif front >= 4:
        side = "frontal"
    elif "tailbase" in keys and front <= 1:
        side = "rear"
    else:
        side = "unknown"

    return {
        "pose_keypoint_count": visible,
        "pose_front_keypoint_count": front,
        "pose_torso_keypoint_count": torso,
        "pose_paw_keypoint_count": paws,
        "pose_left_keypoint_count": left,
        "pose_right_keypoint_count": right,
        "pose_bbox_area_fraction": bbox_area,
        "pose_body_visibility": body,
        "pose_side_flank_visibility": side,
    }


def refined_pattern(row: pd.Series, features: dict[str, Any]) -> str:
    current = str(row["human_pattern_visibility"])
    contrast = str(row["auto_contrast_band"])
    blur = str(row["auto_blur_band"])
    if features["pose_body_visibility"] in {"76_100", "51_75"} and contrast in {"medium", "high"} and blur in {"none", "mild"}:
        if current in {"none", "low"}:
            return "medium"
    return current


def refined_bucket(row: pd.Series, pattern: str, side: str, body: str) -> str:
    blur = str(row["auto_blur_band"])
    exposure = str(row["auto_exposure_band"])
    contrast = str(row["auto_contrast_band"])
    night = str(row["auto_night_ir"])
    if night == "yes" and pattern in {"none", "low"}:
        return "species_level_only"
    if pattern in {"high", "medium"} and side in {"left", "right", "both"} and body in {"51_75", "76_100"} and blur in {"none", "mild"} and exposure != "poor":
        return "review_ready" if contrast in {"medium", "high"} else "review_limited"
    if body in {"26_50", "51_75", "76_100"} and side != "unknown" and pattern in {"medium", "low"}:
        return "review_limited"
    if body == "0_25" or pattern == "none":
        return "species_level_only"
    return str(row["human_review_bucket"])


def refine_row(row: pd.Series, meta_row: pd.Series | None) -> dict[str, Any]:
    result = row.to_dict()
    result["pose_refinement_action"] = "unchanged"
    result["pose_refinement_reason"] = "no_pose_metadata"
    result["pose_refinement_confidence_basis"] = ""
    if meta_row is None:
        return result

    pose = parse_pose(meta_row.get("pose"))
    features = pose_features(
        pose,
        width=float(row.get("original_image_width", row.get("image_width", 1))),
        height=float(row.get("original_image_height", row.get("image_height", 1))),
    )
    result.update(features)
    if features["pose_keypoint_count"] == 0:
        result["pose_refinement_reason"] = "pose_unavailable_or_unparseable"
        return result

    new_side = features["pose_side_flank_visibility"]
    new_body = features["pose_body_visibility"]
    new_pattern = refined_pattern(row, features)
    new_bucket = refined_bucket(row, new_pattern, new_side, new_body)

    changed = []
    if new_side != "unknown" and str(row["human_side_flank_visibility"]) == "unknown":
        result["human_side_flank_visibility"] = new_side
        changed.append("side")
    if new_body != "unknown" and str(row["human_body_visibility"]) in {"unknown", "0_25", "26_50"}:
        result["human_body_visibility"] = new_body
        changed.append("body")
    if new_pattern != str(row["human_pattern_visibility"]):
        result["human_pattern_visibility"] = new_pattern
        changed.append("pattern")
    if new_bucket != str(row["human_review_bucket"]):
        result["human_review_bucket"] = new_bucket
        changed.append("bucket")

    strong_pose = features["pose_keypoint_count"] >= 8 and features["pose_torso_keypoint_count"] >= 3
    still_risky = any(
        token in str(row["human_notes"])
        for token in ["night_ir", "possible_exposure_issue", "low_contrast", "pattern_review_conflict"]
    )
    if strong_pose and not still_risky and new_bucket in {"review_ready", "review_limited"}:
        result["human_review_confidence"] = "medium"
        result["needs_manual_check"] = "no"
        changed.append("confidence")

    if changed:
        result["pose_refinement_action"] = "pose_refined"
        result["pose_refinement_reason"] = ";".join(sorted(set(changed)))
        result["pose_refinement_confidence_basis"] = (
            f"keypoints={features['pose_keypoint_count']};"
            f"torso={features['pose_torso_keypoint_count']};"
            f"bbox_area={features['pose_bbox_area_fraction']:.3f}"
        )
        result["human_notes"] = str(result["human_notes"]) + ";pose_refined"
    else:
        result["pose_refinement_reason"] = "pose_did_not_resolve_low_confidence"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_LOW))
    parser.add_argument("--metadata", default=str(DEFAULT_META))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--remaining-output", default=str(DEFAULT_REMAINING))
    parser.add_argument("--promoted-output", default=str(DEFAULT_PROMOTED))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    low = pd.read_csv(resolve(args.input))
    meta = pd.read_csv(resolve(args.metadata), usecols=["path", "pose"]).set_index("path")
    rows: list[dict[str, Any]] = []
    for _, row in low.iterrows():
        path = str(row["path"])
        meta_row = meta.loc[path] if path in meta.index else None
        rows.append(refine_row(row, meta_row))
    refined = pd.DataFrame(rows)
    remaining = refined[refined["needs_manual_check"].eq("yes")].copy()
    promoted = refined[refined["pose_refinement_action"].eq("pose_refined") & refined["needs_manual_check"].eq("no")].copy()

    output = resolve(args.output)
    remaining_output = resolve(args.remaining_output)
    promoted_output = resolve(args.promoted_output)
    audit_path = resolve(args.audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    refined.to_csv(output, index=False)
    remaining.to_csv(remaining_output, index=False)
    promoted.to_csv(promoted_output, index=False)
    audit = {
        "input": str(resolve(args.input).relative_to(PROJECT_ROOT)),
        "output": str(output.relative_to(PROJECT_ROOT)),
        "row_count": int(len(refined)),
        "pose_refined_count": int(refined["pose_refinement_action"].eq("pose_refined").sum()),
        "promoted_no_manual_check_count": int(len(promoted)),
        "remaining_needs_manual_check_count": int(len(remaining)),
        "remaining_reason_counts": {
            str(k): int(v)
            for k, v in remaining["confidence_refinement_reason"].value_counts().sort_index().items()
        },
        "claim_boundary": "pose_refined_labels_are_algorithmic_not_human_ground_truth",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 CzechLynx pose refinement "
        f"rows={len(refined)} pose_refined={audit['pose_refined_count']} "
        f"promoted={len(promoted)} remaining={len(remaining)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
