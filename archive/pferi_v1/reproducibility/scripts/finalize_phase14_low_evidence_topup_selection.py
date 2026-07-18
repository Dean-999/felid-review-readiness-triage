#!/usr/bin/env python3
"""Finalize Phase 14 low-evidence working labels after top-up MD screening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOPUP_PACKAGE = PROJECT_ROOT / "outputs/phase14/phase14_low_evidence_topup_colab_package"
TOPUP_DETECTIONS = TOPUP_PACKAGE / "colab_returned/phase14_colab_megadetector_detections.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels"
BOBCAT_EXISTING_LOW = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/phase14_bobcat_megadetector_low_evidence_stress_final.csv"
)
CZECH_EXISTING_LOW = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/phase14_czechlynx_megadetector_low_evidence_stress_final.csv"
)
BOBCAT_HIGH = OUT_DIR / "phase14_bobcat_high_confidence_3000_working_final_labels.csv"
CZECH_HIGH = OUT_DIR / "phase14_czechlynx_high_confidence_3000_working_final_labels.csv"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_paths(frame: pd.DataFrame) -> set[str]:
    paths: set[str] = set()
    for col in ["candidate_source_path", "local_image_path", "review_image_path_local", "local_relative_path", "path"]:
        if col in frame.columns:
            paths.update(frame[col].dropna().astype(str))
    return {p for p in paths if p and p.lower() != "nan"}


def apply_high_conflict_gate(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in [
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_aspect_ratio",
        "auto_evidence_score",
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
    out["md_low_stress_score"] = (
        (1.0 - out["md_area_fraction"].clip(upper=1.0)) * 2.0
        + (1.0 - out["md_best_confidence"].clip(upper=1.0))
        + out["md_edge_touch"].astype(int) * 0.75
        + (out["md_width_fraction"].lt(0.18) | out["md_height_fraction"].lt(0.10)).astype(int) * 0.75
        + (1.0 - out["auto_evidence_score"].clip(upper=1.0))
    )
    return out


def normalize_low(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = frame.copy()
    out["dataset_label"] = dataset
    if "candidate_source_path" not in out.columns:
        out["candidate_source_path"] = ""
        for col in ["evidence_image_path", "local_image_path", "review_image_path_local", "local_relative_path", "path"]:
            if col in out.columns:
                empty = out["candidate_source_path"].eq("")
                out.loc[empty, "candidate_source_path"] = out.loc[empty, col].fillna("").astype(str)
    out["source_component"] = f"existing_{dataset}_low_evidence_final"
    return out


def add_low_working_columns(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "phase14_working_final_index", range(1, len(out) + 1))
    if dataset == "bobcat":
        out["source_dataset"] = "Felidae Conservation Fund 2020-2025"
        out["species_label"] = "bobcat"
        out["scientific_name"] = "Lynx rufus"
        out["environment_context"] = "urban_periurban"
        out["phase14_2x2_quadrant"] = "urban_bobcat_low_evidence_stress"
    else:
        out["source_dataset"] = "CzechLynx"
        out["species_label"] = "Eurasian lynx"
        out["scientific_name"] = "Lynx lynx"
        out["environment_context"] = "wild"
        out["phase14_2x2_quadrant"] = "wild_czechlynx_low_evidence_stress"
    out["strict_evidence_tier"] = "low_evidence_stress"
    out["strict_evidence_role"] = "low_evidence_stress_test;manual_audit_calibration"
    out["strict_training_eligible"] = "no"
    out["strict_stress_test_eligible"] = "yes"
    out["manual_audit_needed"] = "audit_sample_required_before_final_claim"
    out["human_label_status"] = "working_final"
    out["human_label_provenance"] = "detector_first_low_evidence_topup_validated"
    out["phase14_final_label_version"] = f"phase14_{dataset}_low_working_final_v1_20260621"
    return out


def finalize_dataset(
    existing: pd.DataFrame,
    topup: pd.DataFrame,
    high_paths: set[str],
    dataset: str,
    target_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    existing = normalize_low(existing, dataset)
    existing = existing[~existing["candidate_source_path"].astype(str).isin(high_paths)].copy()
    existing = existing.drop_duplicates(subset=["candidate_source_path"], keep="first").copy()
    used = set(existing["candidate_source_path"].astype(str))
    passed = topup[
        topup["dataset_label"].eq(dataset)
        & topup["md_low_evidence_validated"]
        & ~topup["candidate_source_path"].astype(str).isin(used)
        & ~topup["candidate_source_path"].astype(str).isin(high_paths)
    ].copy()
    passed = passed.sort_values(
        ["md_low_stress_score", "md_area_fraction", "md_best_confidence", "auto_evidence_score"],
        ascending=[False, True, True, True],
    )
    needed = max(target_count - len(existing), 0)
    selected_topup = passed.head(needed).copy()
    selected_topup["source_component"] = f"topup_{dataset}_low_evidence_detector_validated"
    combined = pd.concat([existing, selected_topup], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["candidate_source_path"], keep="first").head(target_count).copy()
    return add_low_working_columns(combined, dataset), selected_topup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", default=str(TOPUP_PACKAGE))
    parser.add_argument("--detections", default=str(TOPUP_DETECTIONS))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--target-count", type=int, default=3000)
    args = parser.parse_args()

    package_dir = resolve(args.package_dir)
    detections_path = resolve(args.detections)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not detections_path.exists():
        raise FileNotFoundError(f"Missing topup detections: {rel(detections_path)}")

    manifest = pd.read_csv(package_dir / "phase14_colab_megadetector_manifest.csv", low_memory=False)
    detections = pd.read_csv(detections_path, low_memory=False)
    topup = manifest.merge(
        detections.drop(columns=["dataset_label"], errors="ignore"),
        on="phase14_md_candidate_id",
        how="left",
        validate="one_to_one",
    )
    topup = apply_high_conflict_gate(topup)
    topup.to_csv(out_dir / "phase14_low_evidence_topup_all_gated_candidates.csv", index=False)

    bob_high_paths = collect_paths(pd.read_csv(BOBCAT_HIGH, low_memory=False))
    czech_high_paths = collect_paths(pd.read_csv(CZECH_HIGH, low_memory=False))
    bob_working, bob_selected = finalize_dataset(
        pd.read_csv(BOBCAT_EXISTING_LOW, low_memory=False),
        topup,
        bob_high_paths,
        "bobcat",
        args.target_count,
    )
    czech_working, czech_selected = finalize_dataset(
        pd.read_csv(CZECH_EXISTING_LOW, low_memory=False),
        topup,
        czech_high_paths,
        "czechlynx",
        args.target_count,
    )

    outputs = {
        "bobcat_working_low": out_dir / "phase14_bobcat_low_evidence_stress_3000_working_final_labels.csv",
        "czechlynx_working_low": out_dir / "phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv",
        "bobcat_selected_topup": out_dir / "phase14_bobcat_low_evidence_selected_topup.csv",
        "czechlynx_selected_topup": out_dir / "phase14_czechlynx_low_evidence_selected_topup.csv",
    }
    bob_working.to_csv(outputs["bobcat_working_low"], index=False)
    czech_working.to_csv(outputs["czechlynx_working_low"], index=False)
    bob_selected.to_csv(outputs["bobcat_selected_topup"], index=False)
    czech_selected.to_csv(outputs["czechlynx_selected_topup"], index=False)

    summary = {
        "target_count": args.target_count,
        "topup_manifest_rows": int(len(manifest)),
        "topup_detection_rows": int(len(detections)),
        "validated_topup_counts_by_dataset": {
            str(k): int(v)
            for k, v in topup[topup["md_low_evidence_validated"]]["dataset_label"].value_counts().sort_index().items()
        },
        "high_conflict_topup_counts_by_dataset": {
            str(k): int(v)
            for k, v in topup[topup["md_high_evidence_conflict_gate"]]["dataset_label"].value_counts().sort_index().items()
        },
        "final_selected_counts": {
            "bobcat": int(len(bob_working)),
            "czechlynx": int(len(czech_working)),
        },
        "topup_selected_counts": {
            "bobcat": int(len(bob_selected)),
            "czechlynx": int(len(czech_selected)),
        },
        "target_status": {
            "bobcat": "target_met" if len(bob_working) >= args.target_count else "below_target_do_not_force",
            "czechlynx": "target_met" if len(czech_working) >= args.target_count else "below_target_do_not_force",
        },
        "outputs": {key: rel(path) for key, path in outputs.items()},
    }
    (out_dir / "phase14_low_evidence_stress_3000_working_final_labels_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS finalized low-evidence topup working labels "
        f"bobcat={len(bob_working)} czechlynx={len(czech_working)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
