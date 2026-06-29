#!/usr/bin/env python3
"""Run Phase16G CzechLynx pair-table construction on real repository outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_phase16g_czechlynx_pair_prototype import build_pair_rows, write_outputs
from scripts.build_phase16g_pair_feature_schema import write_schema


DEFAULT_SELECTED = Path(
    "outputs/phase16/phase16f_czechlynx_constrained_selection/"
    "phase16f_czechlynx_selected_3000_manifest.csv"
)
DEFAULT_ROUTING = Path(
    "outputs/phase15/hybrid_routing_policy/"
    "phase15_czechlynx_candidate_routing_input.csv"
)
DEFAULT_LEAKAGE = Path(
    "outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv"
)
DEFAULT_LATERALITY = Path(
    "outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv"
)
DEFAULT_OUTPUT_DIR = Path("outputs/phase16/phase16g_czechlynx_real_pair_table")


def normalize_czechlynx_key(value: object) -> str:
    text = str(value).replace("\\", "/")
    marker = "CzechLynx/"
    if marker in text:
        return marker + text.split(marker, 1)[1]
    return text.lstrip("/")


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _string(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="object")
    return frame[column].fillna(default).astype(str)


def build_selected_image_table(selected: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=selected.index)
    out["image_id"] = _string(selected, "image_key").map(normalize_czechlynx_key)
    out["candidate_id"] = _string(selected, "candidate_id")
    out["identity_id"] = _string(selected, "phase16f_balance_group")
    out["phase16f_tier"] = _string(selected, "phase16f_selection_bucket")
    out["iqa_score"] = _numeric(selected, "iqa_quality_proxy_score")
    out["side_probability"] = _numeric(selected, "clip_side_view_score")
    out["pose_completeness"] = _numeric(selected, "pose_completeness")
    out["clip_viewpoint_label"] = _string(selected, "clip_viewpoint_label", "unknown")
    out["source_name"] = _string(selected, "source_name", "czechlynx")
    out["phase16f_selection_rank"] = _numeric(selected, "phase16f_selection_rank")

    if out["image_id"].duplicated().any():
        duplicate_count = int(out["image_id"].duplicated().sum())
        raise ValueError(f"Phase16F selected image_id must be unique; duplicate_count={duplicate_count}")
    if out["identity_id"].eq("").any():
        missing_count = int(out["identity_id"].eq("").sum())
        raise ValueError(f"Phase16F selected rows missing phase16f_balance_group; missing_count={missing_count}")
    return out


def _pair_key(frame: pd.DataFrame) -> pd.Series:
    return frame["query_image_id"].astype(str) + "||" + frame["candidate_image_id"].astype(str)


def _optional_pair_flags(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["pair_join_key"])
    out = pd.DataFrame(index=frame.index)
    out["query_image_id"] = _string(frame, "query_image_path").map(normalize_czechlynx_key)
    out["candidate_image_id"] = _string(frame, "candidate_image_path").map(normalize_czechlynx_key)
    out["pair_join_key"] = _pair_key(out)
    for column in [
        "phase16_site_leakage_pressure",
        "phase16_pair_side_relation",
        "side_direction_compatibility",
    ]:
        if column in frame.columns:
            out[column] = frame[column]
    return out.drop_duplicates("pair_join_key")


def build_descriptor_pairs_for_selected(
    routing: pd.DataFrame,
    selected_images: pd.DataFrame,
    leakage: pd.DataFrame | None = None,
    laterality: pd.DataFrame | None = None,
) -> pd.DataFrame:
    selected_ids = set(selected_images["image_id"].astype(str))
    out = pd.DataFrame(index=routing.index)
    out["query_image_id"] = _string(routing, "query_image_path").map(normalize_czechlynx_key)
    out["candidate_image_id"] = _string(routing, "candidate_image_path").map(normalize_czechlynx_key)
    out["descriptor_similarity"] = _numeric(routing, "descriptor_similarity")
    out["descriptor_rank"] = _numeric(routing, "rank").astype(int)
    out["descriptor_margin"] = _numeric(routing, "descriptor_evidence_support_score")
    out["reciprocal_rank_flag"] = False
    out["duplicate_or_near_duplicate_flag"] = False
    out["source_leakage_pressure_flag"] = False
    out["laterality_relation"] = "unknown"
    out["side_compatibility"] = "unknown"
    out["split_group"] = "query::" + _string(routing, "query_identity_label", "unknown")

    if "descriptor_evidence_conflict_score" in routing.columns:
        out["descriptor_margin"] = pd.to_numeric(
            routing["descriptor_evidence_conflict_score"],
            errors="coerce",
        ).fillna(0.0)

    out = out[
        out["query_image_id"].isin(selected_ids)
        & out["candidate_image_id"].isin(selected_ids)
        & out["query_image_id"].ne(out["candidate_image_id"])
    ].copy()

    out["pair_join_key"] = _pair_key(out)

    leakage_flags = _optional_pair_flags(leakage)
    if not leakage_flags.empty and "phase16_site_leakage_pressure" in leakage_flags.columns:
        out = out.merge(
            leakage_flags[["pair_join_key", "phase16_site_leakage_pressure"]],
            on="pair_join_key",
            how="left",
        )
        out["source_leakage_pressure_flag"] = out["phase16_site_leakage_pressure"].fillna(False).astype(bool)
        out = out.drop(columns=["phase16_site_leakage_pressure"])

    laterality_flags = _optional_pair_flags(laterality)
    if not laterality_flags.empty:
        keep_columns = [
            column
            for column in ["pair_join_key", "phase16_pair_side_relation", "side_direction_compatibility"]
            if column in laterality_flags.columns
        ]
        out = out.merge(laterality_flags[keep_columns], on="pair_join_key", how="left")
        if "phase16_pair_side_relation" in out.columns:
            out["laterality_relation"] = out["phase16_pair_side_relation"].fillna("unknown").astype(str)
            out = out.drop(columns=["phase16_pair_side_relation"])
        if "side_direction_compatibility" in out.columns:
            out["side_compatibility"] = out["side_direction_compatibility"].fillna("unknown").astype(str)
            out = out.drop(columns=["side_direction_compatibility"])

    return out.drop(columns=["pair_join_key"]).reset_index(drop=True)


def write_run_report(summary: dict[str, object], output_dir: Path) -> None:
    lines = [
        "# Phase16G CzechLynx Real Pair Table Run",
        "",
        "This run bridges Phase16F CzechLynx selected images to Phase15 descriptor candidate pairs.",
        "It creates an audited pair-level evidence table for later Phase16H modeling.",
        "",
        "## Summary",
        "",
        f"- Selected image rows: {summary['selected_rows']:,}",
        f"- Descriptor candidate rows scanned: {summary['routing_rows']:,}",
        f"- Pair rows written: {summary['pair_rows']:,}",
        f"- Audit status: {summary['audit_status']}",
        "",
        "## Claim Boundary",
        "",
        "This output is not final model training, not automatic identity assignment, and not Bobcat identity validation.",
        "",
    ]
    (output_dir / "phase16g_czechlynx_run_report.md").write_text("\n".join(lines))


def run_real_czechlynx_pair_table(
    selected_path: Path,
    routing_path: Path,
    output_dir: Path,
    leakage_path: Path | None,
    laterality_path: Path | None,
) -> dict[str, object]:
    selected_raw = pd.read_csv(selected_path, low_memory=False)
    routing = pd.read_csv(routing_path, low_memory=False)
    leakage = pd.read_csv(leakage_path, low_memory=False) if leakage_path and leakage_path.exists() else None
    laterality = pd.read_csv(laterality_path, low_memory=False) if laterality_path and laterality_path.exists() else None

    selected_images = build_selected_image_table(selected_raw)
    descriptor_pairs = build_descriptor_pairs_for_selected(
        routing,
        selected_images,
        leakage=leakage,
        laterality=laterality,
    )
    pair_table = build_pair_rows(
        selected_images,
        descriptor_pairs,
        control_regime="phase16f_selected_real_czechlynx",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_schema(output_dir / "phase16g_pair_feature_schema.json")
    audit = write_outputs(pair_table, output_dir)
    summary = {
        "status": "PASS" if audit["status"] == "PASS" and len(pair_table) > 0 else "REVIEW",
        "audit_status": audit["status"],
        "selected_rows": int(len(selected_raw)),
        "selected_unique_images": int(selected_images["image_id"].nunique()),
        "routing_rows": int(len(routing)),
        "pair_rows": int(len(pair_table)),
        "positive_pair_rows": int(pair_table["same_identity_label"].fillna(False).astype(bool).sum())
        if len(pair_table)
        else 0,
        "false_pair_rows": int((~pair_table["same_identity_label"].fillna(False).astype(bool)).sum())
        if len(pair_table)
        else 0,
        "claim_boundary": "CzechLynx known-ID pair table only; no final model training and no Bobcat identity claim",
    }
    (output_dir / "phase16g_czechlynx_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    write_run_report(summary, output_dir)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--routing", type=Path, default=DEFAULT_ROUTING)
    parser.add_argument("--leakage", type=Path, default=DEFAULT_LEAKAGE)
    parser.add_argument("--laterality", type=Path, default=DEFAULT_LATERALITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = run_real_czechlynx_pair_table(
        selected_path=args.selected,
        routing_path=args.routing,
        output_dir=args.output_dir,
        leakage_path=args.leakage,
        laterality_path=args.laterality,
    )
    print(f"Status: {summary['status']}")
    print(f"Audit status: {summary['audit_status']}")
    print(f"Pair rows: {summary['pair_rows']}")
    print(f"Wrote {args.output_dir}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
