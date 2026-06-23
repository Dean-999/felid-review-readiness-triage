#!/usr/bin/env python3
"""Finalize Phase 14 low-evidence stress sets from Colab MegaDetector detections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_low_evidence_package"
DEFAULT_DETECTIONS = DEFAULT_PACKAGE / "colab_returned/phase14_colab_megadetector_detections.csv"
DEFAULT_OUT = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def apply_high_conflict_gate(frame: pd.DataFrame) -> pd.DataFrame:
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
    out["md_high_evidence_conflict_gate"] = (
        out["md_detected"]
        & out["md_best_confidence"].ge(0.55)
        & out["md_area_fraction"].ge(0.035)
        & out["md_width_fraction"].ge(0.18)
        & out["md_height_fraction"].ge(0.10)
        & out["md_aspect_ratio"].between(0.70, 4.80)
        & ~out["md_edge_touch"]
    )
    out["md_low_evidence_validated"] = ~out["md_high_evidence_conflict_gate"]
    reasons = []
    for _, row in out.iterrows():
        if bool(row["md_high_evidence_conflict_gate"]):
            reasons.append("high_evidence_detector_conflict")
            continue
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
        reasons.append("|".join(bad) if bad else "manual_review_needed_no_failure_reason")
    out["md_low_evidence_reasons"] = reasons
    out["md_low_stress_score"] = (
        (1.0 - out["md_area_fraction"].clip(upper=1.0)) * 2.0
        + (1.0 - out["md_best_confidence"].clip(upper=1.0))
        + out["md_edge_touch"].astype(int) * 0.75
        + (out["md_width_fraction"].lt(0.18) | out["md_height_fraction"].lt(0.10)).astype(int) * 0.75
        + (1.0 - out["auto_evidence_score"].fillna(0).clip(upper=1.0))
    )
    return out


def select_low(frame: pd.DataFrame, dataset: str, target_count: int) -> pd.DataFrame:
    passed = frame[frame["dataset_label"].eq(dataset) & frame["md_low_evidence_validated"]].copy()
    passed = passed.sort_values(
        ["md_low_stress_score", "md_area_fraction", "md_best_confidence", "auto_evidence_score"],
        ascending=[False, True, True, True],
    )
    selected = passed.head(target_count).copy()
    selected.insert(0, "phase14_final_low_index", range(1, len(selected) + 1))
    selected["phase14_final_selection_role"] = f"{dataset}_megadetector_low_evidence_stress"
    selected["phase14_final_selection_status"] = (
        "target_met" if len(selected) >= target_count else "below_target_after_conflict_removal_do_not_force"
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
    gated = apply_high_conflict_gate(merged)
    gated.to_csv(out_dir / "phase14_colab_megadetector_all_low_evidence_gated_candidates.csv", index=False)

    bobcat = select_low(gated, "bobcat", args.target_count)
    czechlynx = select_low(gated, "czechlynx", args.target_count)
    bobcat.to_csv(out_dir / "phase14_bobcat_megadetector_low_evidence_stress_final.csv", index=False)
    czechlynx.to_csv(out_dir / "phase14_czechlynx_megadetector_low_evidence_stress_final.csv", index=False)
    gated[gated["md_high_evidence_conflict_gate"]].to_csv(
        out_dir / "phase14_low_evidence_rejected_high_conflict_or_review_required.csv",
        index=False,
    )

    summary = {
        "target_count_per_dataset": args.target_count,
        "input_manifest_rows": int(len(manifest)),
        "input_detection_rows": int(len(detections)),
        "low_evidence_validation_rule": {
            "validated_low_evidence": "not md_high_evidence_conflict_gate",
            "conflict_gate": {
                "md_best_confidence_min": 0.55,
                "md_area_fraction_min": 0.035,
                "md_width_fraction_min": 0.18,
                "md_height_fraction_min": 0.10,
                "md_aspect_ratio_range": [0.70, 4.80],
                "edge_touch_allowed": False,
            },
        },
        "validated_low_counts_by_dataset": {
            str(k): int(v)
            for k, v in gated[gated["md_low_evidence_validated"]]["dataset_label"].value_counts().sort_index().items()
        },
        "high_conflict_counts_by_dataset": {
            str(k): int(v)
            for k, v in gated[gated["md_high_evidence_conflict_gate"]]["dataset_label"]
            .value_counts()
            .sort_index()
            .items()
        },
        "final_selected_counts": {
            "bobcat": int(len(bobcat)),
            "czechlynx": int(len(czechlynx)),
        },
        "target_status": {
            "bobcat": "target_met" if len(bobcat) >= args.target_count else "below_target_after_conflict_removal_do_not_force",
            "czechlynx": "target_met"
            if len(czechlynx) >= args.target_count
            else "below_target_after_conflict_removal_do_not_force",
        },
        "outputs": {
            "all_low_evidence_gated_candidates": rel(
                out_dir / "phase14_colab_megadetector_all_low_evidence_gated_candidates.csv"
            ),
            "bobcat_final": rel(out_dir / "phase14_bobcat_megadetector_low_evidence_stress_final.csv"),
            "czechlynx_final": rel(out_dir / "phase14_czechlynx_megadetector_low_evidence_stress_final.csv"),
            "high_conflict_or_review_required": rel(
                out_dir / "phase14_low_evidence_rejected_high_conflict_or_review_required.csv"
            ),
        },
    }
    (out_dir / "phase14_colab_megadetector_low_evidence_final_selection_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 Colab MegaDetector low-evidence final selection "
        f"bobcat={len(bobcat)} czechlynx={len(czechlynx)} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
