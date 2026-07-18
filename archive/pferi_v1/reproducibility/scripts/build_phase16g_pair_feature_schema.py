#!/usr/bin/env python3
"""Build the Phase16G pair-level feature schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUTPUT = Path("outputs/phase16/phase16g_pair_contract/phase16g_pair_feature_schema.json")


def build_schema() -> dict[str, object]:
    return {
        "phase": "Phase16G",
        "schema_version": "1.0",
        "claim_boundary": {
            "czechlynx": "known-id validation carrier",
            "bobcat": "transfer-stress unless verified labels or audited same/different pairs exist",
            "not_allowed": [
                "automatic identity assignment",
                "bobcat identity accuracy without verified labels",
                "new Re-ID descriptor claim",
            ],
        },
        "column_groups": [
            {
                "name": "identity_fields",
                "columns": [
                    "pair_id",
                    "dataset_role",
                    "species_context",
                    "query_image_id",
                    "candidate_image_id",
                ],
            },
            {
                "name": "image_evidence_features",
                "columns": [
                    "query_load_success",
                    "candidate_load_success",
                    "query_iqa_score",
                    "candidate_iqa_score",
                    "weakest_iqa_score",
                    "query_evidence_band",
                    "candidate_evidence_band",
                    "pair_evidence_band",
                ],
            },
            {
                "name": "pair_comparability_features",
                "columns": [
                    "query_side_probability",
                    "candidate_side_probability",
                    "side_compatibility",
                    "laterality_relation",
                    "query_pose_completeness",
                    "candidate_pose_completeness",
                    "weakest_pose_completeness",
                ],
            },
            {
                "name": "descriptor_features",
                "columns": [
                    "descriptor_similarity",
                    "descriptor_rank",
                    "descriptor_margin",
                    "reciprocal_rank_flag",
                    "descriptor_support_band",
                ],
            },
            {
                "name": "conflict_features",
                "columns": [
                    "visual_support_band",
                    "descriptor_evidence_conflict_flag",
                ],
            },
            {
                "name": "control_features",
                "columns": [
                    "control_regime",
                    "duplicate_or_near_duplicate_flag",
                    "source_leakage_pressure_flag",
                    "query_source_tier",
                    "candidate_source_tier",
                    "query_phase16f_tier",
                    "candidate_phase16f_tier",
                ],
            },
            {
                "name": "label_fields",
                "columns": [
                    "same_identity_label",
                    "review_action_label",
                    "label_source",
                    "label_allowed_for_modeling",
                ],
            },
            {
                "name": "audit_fields",
                "columns": ["manual_audit_status"],
            },
            {
                "name": "split_fields",
                "columns": ["split_group"],
            },
        ],
    }


def write_schema(output_path: Path = DEFAULT_OUTPUT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = write_schema(args.output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
