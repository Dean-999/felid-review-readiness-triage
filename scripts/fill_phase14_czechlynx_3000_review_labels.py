#!/usr/bin/env python3
"""Fill Phase 14 CzechLynx 3000 review labels from existing human labels plus AI first pass."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from fill_phase14_fcf_bobcat_review_labels import fill_row  # noqa: E402

DEFAULT_PREFEATURES = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_3000_auto_prefeatures.csv"
DEFAULT_HUMAN = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUT = OUT_DIR / "czechlynx_phase14_3000_review_labels.csv"
DEFAULT_MANUAL = OUT_DIR / "czechlynx_phase14_3000_needs_manual_check.csv"
DEFAULT_AUDIT = OUT_DIR / "czechlynx_phase14_3000_review_labels_audit.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def map_human_bucket(row: pd.Series) -> str:
    if row["annotation_status"] == "needs_review" or row["uncertainty_flag"] == "yes":
        return "uncertain"
    pattern = str(row["pattern_visibility"])
    side = str(row["side_visibility"])
    body = str(row["body_fraction_visible"])
    blur = str(row["blur_level"])
    occlusion = str(row["occlusion_level"])
    if pattern in {"high", "medium"} and side in {"left", "right", "both"} and body in {"51_75", "76_100"} and blur in {"none", "mild"} and occlusion in {"none", "partial"}:
        return "review_ready"
    if pattern in {"medium", "low"} or side in {"left", "right", "both"} or body in {"26_50", "51_75", "76_100"}:
        return "review_limited"
    if pattern == "none" or body == "0_25" or str(row["silhouette_only"]) == "yes":
        return "species_level_only"
    return "uncertain"


def human_confidence(row: pd.Series, bucket: str) -> str:
    if row["annotation_status"] == "needs_review" or row["uncertainty_flag"] == "yes" or bucket == "uncertain":
        return "low"
    if str(row["primary_limiting_factor"]) not in {"none", "not_available", "other"}:
        return "medium"
    return "high"


def from_human(row: pd.Series) -> dict[str, str]:
    bucket = map_human_bucket(row)
    confidence = human_confidence(row, bucket)
    needs = "yes" if confidence == "low" else "no"
    return {
        "human_pattern_visibility": str(row["pattern_visibility"]),
        "human_side_flank_visibility": str(row["side_visibility"]),
        "human_body_visibility": str(row["body_fraction_visible"]),
        "human_blur_level": str(row["blur_level"]),
        "human_occlusion_level": str(row["occlusion_level"]),
        "human_background_complexity": "unknown",
        "human_modified_background": "uncertain",
        "human_review_bucket": bucket,
        "human_review_confidence": confidence,
        "human_notes": str(row.get("annotator_notes", "")) or "existing_human_label",
        "needs_manual_check": needs,
        "ai_fill_status": "existing_human_label_mapped",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefeatures", default=str(DEFAULT_PREFEATURES))
    parser.add_argument("--human-labels", default=str(DEFAULT_HUMAN))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--manual-output", default=str(DEFAULT_MANUAL))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    pre = pd.read_csv(resolve(args.prefeatures))
    human = pd.read_csv(resolve(args.human_labels)).set_index("expanded_image_id")

    rows: list[dict[str, Any]] = []
    for _, row in pre.iterrows():
        item = row.to_dict()
        expanded_id = str(row["expanded_image_id"])
        if expanded_id in human.index:
            labels = from_human(human.loc[expanded_id])
        else:
            labels = fill_row(row)
            labels["ai_fill_status"] = "ai_first_pass"
        item.update(labels)
        rows.append(item)
    filled = pd.DataFrame(rows)
    manual = filled[filled["needs_manual_check"].eq("yes")].copy()

    output = resolve(args.output)
    manual_output = resolve(args.manual_output)
    audit_path = resolve(args.audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    filled.to_csv(output, index=False)
    manual.to_csv(manual_output, index=False)
    audit = {
        "output": str(output.relative_to(PROJECT_ROOT)),
        "manual_output": str(manual_output.relative_to(PROJECT_ROOT)),
        "row_count": int(len(filled)),
        "existing_human_label_mapped": int(filled["ai_fill_status"].eq("existing_human_label_mapped").sum()),
        "ai_first_pass": int(filled["ai_fill_status"].eq("ai_first_pass").sum()),
        "needs_manual_check_count": int(len(manual)),
        "review_bucket_counts": {
            str(k): int(v)
            for k, v in filled["human_review_bucket"].value_counts().sort_index().items()
        },
        "confidence_counts": {
            str(k): int(v)
            for k, v in filled["human_review_confidence"].value_counts().sort_index().items()
        },
        "claim_boundary": "existing_1000_human_labels_plus_2000_ai_first_pass_not_all_ground_truth",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 CzechLynx 3000 review labels "
        f"rows={len(filled)} manual={len(manual)} output={output.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
