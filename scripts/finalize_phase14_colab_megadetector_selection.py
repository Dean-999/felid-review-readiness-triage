#!/usr/bin/env python3
"""Finalize Phase 14 high-confidence sets from Colab MegaDetector detections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_package"
DEFAULT_DETECTIONS = DEFAULT_PACKAGE / "colab_returned/phase14_colab_megadetector_detections.csv"
DEFAULT_OUT = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_final_selection"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def apply_gate(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in [
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_aspect_ratio",
        "auto_evidence_score",
        "auto_quality_score",
        "blur_laplacian_var",
        "contrast_std",
    ]:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    out["md_detected"] = out["md_detected"].fillna(False).astype(bool)
    out["md_edge_touch"] = out["md_edge_touch"].fillna(False).astype(bool)
    out["md_high_evidence_gate"] = (
        out["md_detected"]
        & out["md_best_confidence"].ge(0.55)
        & out["md_area_fraction"].ge(0.035)
        & out["md_width_fraction"].ge(0.18)
        & out["md_height_fraction"].ge(0.10)
        & out["md_aspect_ratio"].between(0.70, 4.80)
        & ~out["md_edge_touch"]
    )
    reasons = []
    for _, row in out.iterrows():
        bad = []
        if not bool(row["md_detected"]):
            bad.append("no_md_detection")
        if float(row["md_best_confidence"]) < 0.55:
            bad.append("low_md_confidence")
        if float(row["md_area_fraction"]) < 0.035:
            bad.append("animal_too_small")
        if float(row["md_width_fraction"]) < 0.18 or float(row["md_height_fraction"]) < 0.10:
            bad.append("insufficient_bbox_span")
        if bool(row["md_edge_touch"]):
            bad.append("edge_touch")
        if not (0.70 <= float(row["md_aspect_ratio"]) <= 4.80):
            bad.append("extreme_aspect_ratio")
        reasons.append("|".join(bad) if bad else "pass")
    out["md_gate_reasons"] = reasons
    out["md_selection_score"] = (
        out["md_best_confidence"] * 2.0
        + out["md_area_fraction"] * 3.0
        + out["auto_evidence_score"].fillna(0)
        + out["auto_quality_score"].fillna(0) * 0.5
        + out["blur_laplacian_var"].clip(upper=2000) / 4000
        + out["contrast_std"].clip(upper=100) / 200
    )
    return out


def select_top(frame: pd.DataFrame, dataset: str, target_count: int) -> pd.DataFrame:
    passed = frame[frame["dataset_label"].eq(dataset) & frame["md_high_evidence_gate"]].copy()
    sort_cols = ["md_selection_score", "md_area_fraction", "md_best_confidence", "auto_evidence_score"]
    passed = passed.sort_values(sort_cols, ascending=[False, False, False, False])
    selected = passed.head(target_count).copy()
    selected.insert(0, "phase14_final_high_index", range(1, len(selected) + 1))
    selected["phase14_final_selection_role"] = f"{dataset}_megadetector_high_confidence"
    selected["phase14_final_selection_status"] = (
        "target_met" if len(selected) >= target_count else "below_target_do_not_force"
    )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--detections", default=str(DEFAULT_DETECTIONS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--target-count", type=int, default=3000)
    args = parser.parse_args()

    package_dir = resolve(args.package_dir)
    detections_path = resolve(args.detections)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(package_dir / "phase14_colab_megadetector_manifest.csv", low_memory=False)
    detections = pd.read_csv(detections_path, low_memory=False)
    merged = manifest.merge(
        detections.drop(columns=["dataset_label"], errors="ignore"),
        on="phase14_md_candidate_id",
        how="left",
        validate="one_to_one",
    )
    gated = apply_gate(merged)
    gated.to_csv(out_dir / "phase14_colab_megadetector_all_gated_candidates.csv", index=False)
    bobcat = select_top(gated, "bobcat", args.target_count)
    czechlynx = select_top(gated, "czechlynx", args.target_count)
    bobcat.to_csv(out_dir / "phase14_bobcat_megadetector_high_confidence_final.csv", index=False)
    czechlynx.to_csv(out_dir / "phase14_czechlynx_megadetector_high_confidence_final.csv", index=False)
    gated[~gated["md_high_evidence_gate"]].to_csv(
        out_dir / "phase14_megadetector_high_confidence_rejected_or_review_required.csv",
        index=False,
    )
    summary = {
        "target_count_per_dataset": args.target_count,
        "input_manifest_rows": int(len(manifest)),
        "input_detection_rows": int(len(detections)),
        "gate": {
            "md_best_confidence_min": 0.55,
            "md_area_fraction_min": 0.035,
            "md_width_fraction_min": 0.18,
            "md_height_fraction_min": 0.10,
            "md_aspect_ratio_range": [0.70, 4.80],
            "edge_touch_allowed": False,
        },
        "passed_counts_by_dataset": {
            str(k): int(v)
            for k, v in gated[gated["md_high_evidence_gate"]]["dataset_label"].value_counts().sort_index().items()
        },
        "final_selected_counts": {
            "bobcat": int(len(bobcat)),
            "czechlynx": int(len(czechlynx)),
        },
        "target_status": {
            "bobcat": "target_met" if len(bobcat) >= args.target_count else "below_target_do_not_force",
            "czechlynx": "target_met" if len(czechlynx) >= args.target_count else "below_target_do_not_force",
        },
        "outputs": {
            "all_gated_candidates": rel(out_dir / "phase14_colab_megadetector_all_gated_candidates.csv"),
            "bobcat_final": rel(out_dir / "phase14_bobcat_megadetector_high_confidence_final.csv"),
            "czechlynx_final": rel(out_dir / "phase14_czechlynx_megadetector_high_confidence_final.csv"),
            "rejected_or_review_required": rel(
                out_dir / "phase14_megadetector_high_confidence_rejected_or_review_required.csv"
            ),
        },
    }
    (out_dir / "phase14_colab_megadetector_final_selection_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 Colab MegaDetector final selection "
        f"bobcat={len(bobcat)} czechlynx={len(czechlynx)} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
