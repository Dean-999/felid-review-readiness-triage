#!/usr/bin/env python3
"""Finalize CzechLynx 3,000 high-confidence working labels with detector-gated top-up."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXISTING = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_final_selection/phase14_czechlynx_megadetector_high_confidence_final.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup/phase14_czechlynx_high_topup_candidate_manifest.csv"
DEFAULT_DETECTIONS = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup/phase14_czechlynx_high_topup_megadetector_detections.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels"


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
        "phase14_czechlynx_topup_score",
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
    out["md_selection_score"] = (
        out["md_best_confidence"] * 2.0
        + out["md_area_fraction"] * 3.0
        + out["auto_evidence_score"]
        + out["auto_quality_score"] * 0.5
        + out["blur_laplacian_var"].clip(upper=2000) / 4000
        + out["contrast_std"].clip(upper=100) / 200
    )
    return out


def normalize_existing(existing: pd.DataFrame) -> pd.DataFrame:
    col = "candidate_source_path" if "candidate_source_path" in existing.columns else "evidence_image_path"
    out = existing.copy()
    out["candidate_source_path"] = out[col].astype(str)
    out["source_component"] = "existing_czechlynx_colab_detector_high_final_2220"
    return out


def add_working_label_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "phase14_working_final_index", range(1, len(out) + 1))
    out["source_dataset"] = "CzechLynx"
    out["species_label"] = "Eurasian lynx"
    out["scientific_name"] = "Lynx lynx"
    out["environment_context"] = "wild"
    out["phase14_2x2_quadrant"] = "wild_czechlynx_high_confidence"
    out["strict_evidence_tier"] = "high_confidence"
    out["strict_evidence_role"] = "core_training;wild_urban_clean_comparison;retrieval_evaluation"
    out["strict_training_eligible"] = "yes"
    out["strict_stress_test_eligible"] = "no"
    out["manual_audit_needed"] = "no_for_current_working_label"
    out["human_review_bucket"] = "review_ready"
    out["human_review_confidence"] = "high"
    out["human_training_eligible"] = "yes"
    out["human_label_status"] = "working_final"
    out["human_label_provenance"] = "detector_first_high_confidence_promoted_by_project_note"
    out["human_notes"] = (
        "Promoted to current working final high-confidence label from detector-first evidence gate; "
        "user note records that later manual revision may update this label."
    )
    out["phase14_final_label_version"] = "phase14_czechlynx_high_working_final_v1_20260620"
    out["local_exists"] = out["candidate_source_path"].map(lambda p: resolve(p).exists())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing", default=str(DEFAULT_EXISTING))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--detections", default=str(DEFAULT_DETECTIONS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--target-count", type=int, default=3000)
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = normalize_existing(pd.read_csv(resolve(args.existing), low_memory=False))
    manifest = pd.read_csv(resolve(args.manifest), low_memory=False)
    detections = pd.read_csv(resolve(args.detections), low_memory=False)
    topup = manifest.merge(
        detections.drop(columns=["dataset_label", "candidate_source_path"], errors="ignore"),
        on="phase14_md_candidate_id",
        how="left",
        validate="one_to_one",
    )
    topup = apply_gate(topup)
    topup_gated_path = out_dir / "phase14_czechlynx_high_topup_all_gated_candidates.csv"
    topup.to_csv(topup_gated_path, index=False)

    used_paths = set(existing["candidate_source_path"].astype(str))
    topup_passed = topup[topup["md_high_evidence_gate"] & ~topup["candidate_source_path"].astype(str).isin(used_paths)].copy()
    topup_passed["source_component"] = "czechlynx_middle_reviewable_detector_gated_topup"
    topup_passed = topup_passed.sort_values(
        ["md_selection_score", "md_area_fraction", "md_best_confidence", "phase14_czechlynx_topup_score"],
        ascending=[False, False, False, False],
    )
    needed = max(args.target_count - len(existing), 0)
    selected_topup = topup_passed.head(needed).copy()

    combined = pd.concat([existing, selected_topup], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["candidate_source_path"], keep="first").head(args.target_count).copy()
    working = add_working_label_columns(combined)
    output_csv = out_dir / "phase14_czechlynx_high_confidence_3000_working_final_labels.csv"
    working.to_csv(output_csv, index=False)
    selected_topup.to_csv(out_dir / "phase14_czechlynx_high_confidence_selected_topup.csv", index=False)
    topup_passed.to_csv(out_dir / "phase14_czechlynx_high_topup_passed_pool.csv", index=False)

    identity_counts = (
        working["identity_label"].dropna().astype(str).value_counts()
        if "identity_label" in working.columns
        else pd.Series(dtype=int)
    )
    summary = {
        "target_count": args.target_count,
        "existing_detector_high_rows": int(len(existing)),
        "topup_processed_rows": int(len(topup)),
        "topup_passed_rows": int(len(topup_passed)),
        "topup_needed": int(needed),
        "topup_selected_rows": int(len(selected_topup)),
        "combined_rows": int(len(working)),
        "target_status": "target_met" if len(working) >= args.target_count else "below_target_do_not_force",
        "local_exists_count": int(working["local_exists"].sum()),
        "duplicate_source_path_count": int(working["candidate_source_path"].duplicated().sum()),
        "identity_count": int(identity_counts.size),
        "identities_with_at_least_2_images": int((identity_counts >= 2).sum()) if not identity_counts.empty else 0,
        "identities_with_at_least_3_images": int((identity_counts >= 3).sum()) if not identity_counts.empty else 0,
        "label_provenance": "detector_first_high_confidence_promoted_by_project_note",
        "outputs": {
            "working_final": rel(output_csv),
            "selected_topup": rel(out_dir / "phase14_czechlynx_high_confidence_selected_topup.csv"),
            "topup_passed_pool": rel(out_dir / "phase14_czechlynx_high_topup_passed_pool.csv"),
            "topup_all_gated": rel(topup_gated_path),
        },
    }
    summary_path = out_dir / "phase14_czechlynx_high_confidence_3000_working_final_labels_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS finalized CzechLynx high-confidence working labels "
        f"rows={len(working)} topup_selected={len(selected_topup)} status={summary['target_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
