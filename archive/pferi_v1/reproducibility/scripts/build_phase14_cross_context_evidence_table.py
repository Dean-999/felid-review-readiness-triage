#!/usr/bin/env python3
"""Build Phase 14 shared CzechLynx/UWIN evidence table.

The current implementation supports a CzechLynx-only dry run and optional UWIN
tabular input once local metadata are available. Missing features are recorded
as unavailable rather than encoded as low evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CZECHLYNX = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
DEFAULT_UWIN = None
OUT_DIR = PROJECT_ROOT / "outputs/phase14"
DEFAULT_OUTPUT = OUT_DIR / "phase14_cross_context_evidence_table.csv"
DEFAULT_AUDIT = OUT_DIR / "phase14_cross_context_evidence_table_build_audit.json"

OUTPUT_COLUMNS = [
    "row_id",
    "context",
    "species",
    "source_dataset",
    "image_key_blinded",
    "has_identity_label",
    "identity_label_available_for_validation",
    "pf_eri_image_score",
    "pattern_visibility",
    "side_flank_visibility",
    "body_visibility",
    "blur_level",
    "occlusion_level",
    "night_ir",
    "background_complexity",
    "human_modified_background",
    "descriptor_confidence",
    "descriptor_evidence_conflict",
    "feature_available_flags",
]

SENSITIVE_HINTS = {
    "path",
    "local",
    "source_review",
    "unique_name",
    "working_individual",
    "identity",
    "lat",
    "lon",
    "longitude",
    "latitude",
    "trap",
    "camera",
    "site",
    "location",
    "cell",
}


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def stable_key(value: object, prefix: str) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def normalize_level(series: pd.Series, mapping: dict[str, float]) -> pd.Series:
    lower = series.astype(str).str.strip().str.lower()
    return lower.map(mapping).astype("float64")


def yes_no_from_bool(series: pd.Series) -> pd.Series:
    return np.where(series.fillna(False).astype(bool), "yes", "no")


def score_czechlynx_image(frame: pd.DataFrame) -> pd.Series:
    pattern = normalize_level(
        frame["pattern_visibility"],
        {
            "high": 1.0,
            "medium": 0.7,
            "low": 0.35,
            "clear": 1.0,
            "partial": 0.6,
            "weak": 0.35,
            "none": 0.0,
            "not_visible": 0.0,
        },
    )
    side = normalize_level(
        frame["side_visibility"],
        {
            "left": 1.0,
            "right": 1.0,
            "both": 1.0,
            "frontal": 0.25,
            "rear": 0.25,
            "unknown": 0.1,
            "clear_side": 1.0,
            "partial_side": 0.65,
            "front_rear": 0.25,
            "unclear": 0.2,
            "none": 0.0,
        },
    )
    body = normalize_level(
        frame["body_fraction_visible"],
        {
            "76_100": 1.0,
            "51_75": 0.7,
            "26_50": 0.4,
            "0_25": 0.15,
            "unknown": np.nan,
        },
    )
    blur = normalize_level(frame["blur_level"], {"none": 1.0, "mild": 0.75, "moderate": 0.45, "severe": 0.1})
    occlusion = normalize_level(
        frame["occlusion_level"],
        {"none": 1.0, "mild": 0.75, "partial": 0.65, "moderate": 0.45, "major": 0.2, "severe": 0.1},
    )
    components = pd.concat([pattern, side, body, blur, occlusion], axis=1)
    return components.mean(axis=1, skipna=True).clip(0, 1)


def availability_flags(row: pd.Series) -> str:
    flags = {
        column: "yes" if pd.notna(row[column]) and str(row[column]) != "" else "no"
        for column in [
            "pf_eri_image_score",
            "pattern_visibility",
            "side_flank_visibility",
            "body_visibility",
            "blur_level",
            "occlusion_level",
            "night_ir",
            "background_complexity",
            "human_modified_background",
            "descriptor_confidence",
            "descriptor_evidence_conflict",
        ]
    }
    return json.dumps(flags, sort_keys=True)


def build_czechlynx(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    required = {
        "phase7_image_id",
        "source_phase",
        "pattern_visibility",
        "side_visibility",
        "body_fraction_visible",
        "blur_level",
        "occlusion_level",
        "night_ir_artifact",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"CzechLynx table missing required columns: {missing}")

    out = pd.DataFrame()
    out["row_id"] = ["czechlynx_" + str(i).zfill(5) for i in range(len(source))]
    out["context"] = "wild_known_id"
    out["species"] = "Lynx lynx"
    out["source_dataset"] = "CzechLynx"
    out["image_key_blinded"] = source["phase7_image_id"].map(lambda value: stable_key(value, "czlx"))
    out["has_identity_label"] = "yes"
    out["identity_label_available_for_validation"] = "yes"
    out["pf_eri_image_score"] = score_czechlynx_image(source)
    out["pattern_visibility"] = source["pattern_visibility"]
    out["side_flank_visibility"] = source["side_visibility"]
    out["body_visibility"] = normalize_level(
        source["body_fraction_visible"],
        {
            "76_100": 1.0,
            "51_75": 0.7,
            "26_50": 0.4,
            "0_25": 0.15,
            "unknown": np.nan,
        },
    )
    out["blur_level"] = source["blur_level"]
    out["occlusion_level"] = source["occlusion_level"]
    out["night_ir"] = source["night_ir_artifact"]
    out["background_complexity"] = pd.NA
    out["human_modified_background"] = pd.NA
    out["descriptor_confidence"] = pd.NA
    out["descriptor_evidence_conflict"] = pd.NA
    out = out[OUTPUT_COLUMNS[:-1]].copy()
    out["feature_available_flags"] = out.apply(availability_flags, axis=1)
    return out[OUTPUT_COLUMNS]


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {column.lower().replace(" ", "_"): column for column in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def build_uwin(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    columns = list(source.columns)
    image_col = find_column(columns, ["image_id", "image_key", "filename", "file_name", "media_id", "record_id"])
    species_col = find_column(columns, ["species", "common_name", "scientific_name"])
    if image_col is None:
        raise ValueError("UWIN table must contain an image_id/image_key/filename/media_id/record_id column")

    def optional(candidates: list[str]) -> pd.Series:
        column = find_column(columns, candidates)
        if column is None:
            return pd.Series([pd.NA] * len(source))
        return source[column]

    out = pd.DataFrame()
    out["row_id"] = ["uwin_bobcat_" + str(i).zfill(5) for i in range(len(source))]
    out["context"] = "urban_stress"
    out["species"] = source[species_col].astype(str) if species_col else "Lynx rufus"
    out["source_dataset"] = "UWIN_bobcat"
    out["image_key_blinded"] = source[image_col].map(lambda value: stable_key(value, "uwin_bobcat"))
    identity = optional(["individual_id", "animal_id", "identity", "identity_id"])
    out["has_identity_label"] = yes_no_from_bool(identity.notna() & identity.astype(str).str.strip().ne(""))
    out["identity_label_available_for_validation"] = out["has_identity_label"]
    out["pf_eri_image_score"] = pd.to_numeric(optional(["pf_eri_image_score", "visual_eri", "image_utility_score"]), errors="coerce")
    out["pattern_visibility"] = optional(["pattern_visibility", "pattern_visible"])
    out["side_flank_visibility"] = optional(["side_flank_visibility", "side_visibility", "flank_visibility"])
    out["body_visibility"] = pd.to_numeric(optional(["body_visibility", "body_fraction_visible", "animal_visibility"]), errors="coerce")
    out["blur_level"] = optional(["blur_level", "blur"])
    out["occlusion_level"] = optional(["occlusion_level", "occlusion"])
    out["night_ir"] = optional(["night_ir", "night_ir_artifact", "ir", "infrared"])
    out["background_complexity"] = optional(["background_complexity", "background"])
    out["human_modified_background"] = optional(["human_modified_background", "urban_background", "built_background"])
    out["descriptor_confidence"] = pd.to_numeric(optional(["descriptor_confidence", "margin_confidence", "retrieval_confidence"]), errors="coerce")
    out["descriptor_evidence_conflict"] = pd.to_numeric(
        optional(["descriptor_evidence_conflict", "descriptor_evidence_conflict_score", "conflict_score"]),
        errors="coerce",
    )
    out = out[OUTPUT_COLUMNS[:-1]].copy()
    out["feature_available_flags"] = out.apply(availability_flags, axis=1)
    return out[OUTPUT_COLUMNS]


def audit_output(table: pd.DataFrame, inputs: dict[str, str | None]) -> dict[str, Any]:
    forbidden_headers = [
        column
        for column in table.columns
        if any(hint in column.lower() for hint in SENSITIVE_HINTS)
        and column not in {"image_key_blinded", "has_identity_label", "identity_label_available_for_validation"}
    ]
    return {
        "inputs": inputs,
        "row_count": int(len(table)),
        "context_counts": {str(k): int(v) for k, v in table["context"].value_counts(dropna=False).items()},
        "source_dataset_counts": {str(k): int(v) for k, v in table["source_dataset"].value_counts(dropna=False).items()},
        "column_count": int(len(table.columns)),
        "forbidden_output_headers": forbidden_headers,
        "uwin_rows_present": bool(table["source_dataset"].astype(str).eq("UWIN_bobcat").any()),
        "czechlynx_only_dry_run": not bool(table["source_dataset"].astype(str).eq("UWIN_bobcat").any()),
        "claim_boundary": (
            "cross_context_ready"
            if bool(table["source_dataset"].astype(str).eq("UWIN_bobcat").any())
            else "schema_dry_run_only_until_uwin_local_data_available"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--czechlynx-table", default=str(DEFAULT_CZECHLYNX))
    parser.add_argument("--uwin-table", default=DEFAULT_UWIN)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    czechlynx_path = Path(args.czechlynx_table)
    output = Path(args.output)
    audit_path = Path(args.audit)
    if not czechlynx_path.is_absolute():
        czechlynx_path = PROJECT_ROOT / czechlynx_path
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if not audit_path.is_absolute():
        audit_path = PROJECT_ROOT / audit_path

    frames = [build_czechlynx(czechlynx_path)]
    uwin_input = None
    if args.uwin_table:
        uwin_path = Path(args.uwin_table)
        if not uwin_path.is_absolute():
            uwin_path = PROJECT_ROOT / uwin_path
        uwin_input = rel(uwin_path)
        frames.append(build_uwin(uwin_path))

    table = pd.concat(frames, ignore_index=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)

    audit = audit_output(table, {"czechlynx_table": rel(czechlynx_path), "uwin_table": uwin_input})
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "PASS phase14 cross-context evidence table "
        f"rows={len(table)} contexts={','.join(sorted(table['context'].astype(str).unique()))} "
        f"dry_run={audit['czechlynx_only_dry_run']} output={rel(output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
