#!/usr/bin/env python3
"""Promote Phase 14 bobcat detector-first high candidates to working final labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_expanded_high_confidence_candidates/"
    / "phase14_bobcat_high_confidence_candidate_3000_detector_first.csv"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    input_path = resolve(args.input)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(input_path, low_memory=False).copy()
    frame.insert(0, "phase14_working_final_index", range(1, len(frame) + 1))
    frame["source_dataset"] = "Felidae Conservation Fund 2020-2025"
    frame["species_label"] = "bobcat"
    frame["scientific_name"] = "Lynx rufus"
    frame["environment_context"] = "urban_periurban"
    frame["phase14_2x2_quadrant"] = "urban_bobcat_high_confidence"
    frame["strict_evidence_tier"] = "high_confidence"
    frame["strict_evidence_role"] = "core_training;wild_urban_clean_comparison;retrieval_evaluation"
    frame["strict_training_eligible"] = "yes"
    frame["strict_stress_test_eligible"] = "no"
    frame["manual_audit_needed"] = "no_for_current_working_label"
    frame["human_review_bucket"] = "review_ready"
    frame["human_review_confidence"] = "high"
    frame["human_training_eligible"] = "yes"
    frame["human_label_status"] = "working_final"
    frame["human_label_provenance"] = "detector_first_high_confidence_promoted_by_project_note"
    frame["human_notes"] = (
        "Promoted to current working final high-confidence label from detector-first evidence gate; "
        "user note records that later manual revision may update this label."
    )
    frame["phase14_final_label_version"] = "phase14_bobcat_high_working_final_v1_20260620"

    output_csv = out_dir / "phase14_bobcat_high_confidence_3000_working_final_labels.csv"
    frame.to_csv(output_csv, index=False)

    summary = {
        "input": rel(input_path),
        "output": rel(output_csv),
        "rows": int(len(frame)),
        "local_exists_count": int(frame["local_exists"].fillna(False).astype(bool).sum())
        if "local_exists" in frame.columns
        else None,
        "duplicate_image_id_count": int(frame["image_id"].duplicated().sum()) if "image_id" in frame.columns else None,
        "human_review_bucket_counts": {
            str(k): int(v) for k, v in frame["human_review_bucket"].value_counts(dropna=False).sort_index().items()
        },
        "human_review_confidence_counts": {
            str(k): int(v)
            for k, v in frame["human_review_confidence"].value_counts(dropna=False).sort_index().items()
        },
        "label_provenance": "detector_first_high_confidence_promoted_by_project_note",
        "claim_boundary": (
            "Operational working final label for Phase 14 modeling; retain provenance and avoid claiming "
            "independent blinded human audit unless later manual review replaces this label."
        ),
    }
    summary_path = out_dir / "phase14_bobcat_high_confidence_3000_working_final_labels_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS promoted bobcat detector-first high-confidence to working final labels "
        f"rows={len(frame)} output={rel(output_csv)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
