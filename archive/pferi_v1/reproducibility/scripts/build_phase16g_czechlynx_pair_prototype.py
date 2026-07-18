#!/usr/bin/env python3
"""Build a Phase16G CzechLynx known-ID pair prototype table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_phase16g_pair_table import audit_pair_table


DEFAULT_OUTPUT_DIR = Path("outputs/phase16/phase16g_czechlynx_pair_prototype")


def _image_lookup(selected: pd.DataFrame) -> dict[str, dict[str, object]]:
    selected = selected.copy()
    selected["image_id"] = selected["image_id"].astype(str)
    return selected.set_index("image_id").to_dict(orient="index")


def _evidence_band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _float_value(record: dict[str, object], key: str, default: float = 0.0) -> float:
    value = record.get(key, default)
    if pd.isna(value):
        return default
    return float(value)


def build_pair_rows(
    selected: pd.DataFrame,
    descriptor_pairs: pd.DataFrame,
    control_regime: str,
) -> pd.DataFrame:
    lookup = _image_lookup(selected)
    rows: list[dict[str, object]] = []

    for row in descriptor_pairs.to_dict(orient="records"):
        query_id = str(row["query_image_id"])
        candidate_id = str(row["candidate_image_id"])
        if query_id not in lookup or candidate_id not in lookup:
            continue

        query = lookup[query_id]
        candidate = lookup[candidate_id]
        query_iqa = _float_value(query, "iqa_score")
        candidate_iqa = _float_value(candidate, "iqa_score")
        weakest_iqa = min(query_iqa, candidate_iqa)
        query_pose = _float_value(query, "pose_completeness")
        candidate_pose = _float_value(candidate, "pose_completeness")
        descriptor_similarity = float(row.get("descriptor_similarity", 0.0))
        same_identity = query.get("identity_id") == candidate.get("identity_id")

        rows.append(
            {
                "pair_id": f"czechlynx::{query_id}::{candidate_id}",
                "dataset_role": "czechlynx_known_id",
                "species_context": "czechlynx",
                "query_image_id": query_id,
                "candidate_image_id": candidate_id,
                "query_source_tier": "czechlynx_known_id",
                "candidate_source_tier": "czechlynx_known_id",
                "query_phase16f_tier": query.get("phase16f_tier", ""),
                "candidate_phase16f_tier": candidate.get("phase16f_tier", ""),
                "query_evidence_band": _evidence_band(query_iqa),
                "candidate_evidence_band": _evidence_band(candidate_iqa),
                "pair_evidence_band": _evidence_band(weakest_iqa),
                "query_load_success": True,
                "candidate_load_success": True,
                "query_iqa_score": query_iqa,
                "candidate_iqa_score": candidate_iqa,
                "weakest_iqa_score": weakest_iqa,
                "query_side_probability": _float_value(query, "side_probability"),
                "candidate_side_probability": _float_value(candidate, "side_probability"),
                "side_compatibility": row.get("side_compatibility", "unknown"),
                "laterality_relation": row.get("laterality_relation", "unknown"),
                "query_pose_completeness": query_pose,
                "candidate_pose_completeness": candidate_pose,
                "weakest_pose_completeness": min(query_pose, candidate_pose),
                "descriptor_similarity": descriptor_similarity,
                "descriptor_rank": int(row.get("descriptor_rank", 0)),
                "descriptor_margin": float(row.get("descriptor_margin", 0.0)),
                "reciprocal_rank_flag": bool(row.get("reciprocal_rank_flag", False)),
                "descriptor_support_band": "high" if descriptor_similarity >= 0.8 else "medium_or_low",
                "visual_support_band": _evidence_band(weakest_iqa),
                "descriptor_evidence_conflict_flag": bool(descriptor_similarity >= 0.8 and weakest_iqa < 0.6),
                "control_regime": control_regime,
                "duplicate_or_near_duplicate_flag": bool(row.get("duplicate_or_near_duplicate_flag", False)),
                "source_leakage_pressure_flag": bool(row.get("source_leakage_pressure_flag", False)),
                "manual_audit_status": "not_audited",
                "review_action_label": "",
                "same_identity_label": bool(same_identity),
                "label_source": "czechlynx_known_id",
                "label_allowed_for_modeling": True,
                "split_group": str(row.get("split_group", "unassigned")),
            }
        )

    return pd.DataFrame(rows)


def write_outputs(pair_table: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    audit = audit_pair_table(pair_table)

    output_dir.mkdir(parents=True, exist_ok=True)
    pair_table.to_csv(output_dir / "phase16g_czechlynx_pair_table.csv", index=False)
    (output_dir / "phase16g_czechlynx_pair_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n"
    )
    pair_table.groupby("control_regime").size().rename("pair_count").reset_index().to_csv(
        output_dir / "phase16g_czechlynx_control_summary.csv",
        index=False,
    )
    pair_table.groupby("split_group").size().rename("pair_count").reset_index().to_csv(
        output_dir / "phase16g_czechlynx_split_summary.csv",
        index=False,
    )
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--descriptor-pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--control-regime", default="phase16f_selected")
    args = parser.parse_args()

    selected = pd.read_csv(args.selected)
    descriptor_pairs = pd.read_csv(args.descriptor_pairs)
    pair_table = build_pair_rows(selected, descriptor_pairs, args.control_regime)
    audit = write_outputs(pair_table, args.output_dir)

    print(f"Audit status: {audit['status']}")
    print(f"Wrote {args.output_dir}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
