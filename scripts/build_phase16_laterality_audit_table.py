#!/usr/bin/env python3
"""Prepare a deterministic manual laterality audit table for Phase 16."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/laterality_audit"
OUTPUT_CSV = OUTPUT_DIR / "phase16_laterality_audit_candidates.csv"
OUTPUT_SCHEMA = OUTPUT_DIR / "phase16_laterality_schema.json"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_laterality_audit_summary.json"
RANDOM_SEED = 1601
SAMPLES_PER_QUADRANT = 150


def select_candidates(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "image_exists",
        "md_area_fraction",
        "human_review_bucket",
        "evidence_admissibility_band",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in {INPUT}: {missing}")

    eligible = df[df["image_exists"].astype(str).str.lower().eq("yes")].copy()
    groups = []
    for quadrant, group in eligible.groupby("source_quadrant", sort=True):
        n = min(SAMPLES_PER_QUADRANT, len(group))
        sampled = group.sample(n=n, random_state=RANDOM_SEED)
        groups.append(sampled)
    if not groups:
        raise ValueError("No image_exists=yes rows found for laterality audit candidates")

    out = pd.concat(groups, ignore_index=True)
    out = out.sort_values(["source_quadrant", "phase14_image_evidence_id"]).reset_index(drop=True)
    out.insert(0, "phase16_laterality_audit_index", range(1, len(out) + 1))
    out["manual_laterality"] = ""
    out["manual_laterality_confidence"] = ""
    out["manual_laterality_notes"] = ""
    keep = [
        "phase16_laterality_audit_index",
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "md_area_fraction",
        "human_review_bucket",
        "evidence_admissibility_band",
        "manual_laterality",
        "manual_laterality_confidence",
        "manual_laterality_notes",
    ]
    return out[keep]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT, low_memory=False)
    audit = select_candidates(df)
    audit.to_csv(OUTPUT_CSV, index=False)
    schema = {
        "manual_laterality_allowed_values": [
            "left",
            "right",
            "both",
            "frontal",
            "rear",
            "unknown",
        ],
        "manual_laterality_confidence_allowed_values": ["high", "medium", "low"],
        "rule": (
            "Label visible animal body side, not image-facing direction. "
            "Use unknown when side cannot be determined."
        ),
        "claim_boundary": (
            "blank laterality fields are manual audit targets, not model predictions"
        ),
    }
    OUTPUT_SCHEMA.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    summary = {
        "input": str(INPUT),
        "output": str(OUTPUT_CSV),
        "rows": int(len(audit)),
        "samples_per_quadrant_target": SAMPLES_PER_QUADRANT,
        "quadrant_counts": {
            str(key): int(value)
            for key, value in audit["source_quadrant"].value_counts().sort_index().items()
        },
        "claim_boundary": "manual laterality audit package; blank labels are not model output",
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PASS phase16 laterality audit candidates rows={len(audit)}")
    print(f"WROTE {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
