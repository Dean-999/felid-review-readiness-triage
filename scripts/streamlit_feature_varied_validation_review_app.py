#!/usr/bin/env python3
"""Streamlit app for feature-varied pair validation review."""

from __future__ import annotations

from pathlib import Path

from streamlit_pair_review_common import PROJECT_ROOT, PairReviewConfig, run_pair_review_app


REASONS = (
    "",
    "low_image_evidence",
    "motion_or_blur",
    "night_or_low_light",
    "subject_too_small",
    "partial_body",
    "occlusion",
    "non_comparable_viewpoint",
    "non_overlapping_body_region",
    "descriptor_evidence_conflict",
    "source_domain_stress",
    "other",
)


def main() -> None:
    source = PROJECT_ROOT / "outputs/modeling-validation/feature-varied-validation-packet/feature_varied_validation_review_form.csv"
    working = (
        PROJECT_ROOT
        / "outputs/modeling-validation/feature-varied-validation-packet/feature_varied_validation_review_working.csv"
    )
    config = PairReviewConfig(
        title="Feature-Varied Pair Validation",
        source_csv=source,
        working_csv=working,
        id_column="feature_varied_id",
        query_image_column="query_image_path",
        candidate_image_column="candidate_image_path",
        status_column="target_review_ready",
        decision_columns=("target_not_ready_reason", "target_secondary_reason", "target_notes"),
        decision_options=("", "yes", "no", "uncertain"),
        reason_column="target_not_ready_reason",
        secondary_reason_column="target_secondary_reason",
        notes_column="target_notes",
        reason_options=REASONS,
        default_filter_columns=("selection_feature", "selection_bin"),
        metadata_columns=(
            "selection_feature",
            "selection_bin",
            "visible_pattern_area_score",
            "viewpoint_side_compatibility",
            "body_part_overlap_score",
            "night_or_motion_blur_risk",
            "cross_descriptor_agreement_score",
            "source_domain_shift_score",
        ),
        standards=(
            "YES: both images provide enough comparable individual evidence for a reviewer to judge the pair.",
            "NO: evidence is not admissible because the animal is blurred, too small, partial, occluded, or the two images do not show comparable body regions.",
            "UNCERTAIN: possible evidence exists, but a careful reviewer could not confidently decide without more context.",
            "Do not mark YES just because each single image is visually clear; the pair must be comparable.",
            "For Bobcat transfer rows, do not infer same/different identity. Only judge evidence readiness.",
        ),
    )
    run_pair_review_app(config)


if __name__ == "__main__":
    main()
