#!/usr/bin/env python3
"""Streamlit app for online supplement reason-label review."""

from __future__ import annotations

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
    "wrong_species_or_non_target",
    "license_or_source_problem",
    "other",
)


def main() -> None:
    source = (
        PROJECT_ROOT
        / "outputs/modeling-validation/reason-label-enrichment/online-supplement/online_reason_label_review_queue.csv"
    )
    working = (
        PROJECT_ROOT
        / "outputs/modeling-validation/reason-label-enrichment/online-supplement/online_reason_label_review_working.csv"
    )
    config = PairReviewConfig(
        title="Online Supplement Reason-Label Review",
        source_csv=source,
        working_csv=working,
        id_column="online_enrichment_id",
        query_image_column="query_source_image_path",
        candidate_image_column="candidate_source_image_path",
        status_column="online_reason_label_review_status",
        decision_columns=(
            "target_primary_reason",
            "target_secondary_reason",
            "target_body_region_visible",
            "target_notes",
        ),
        decision_options=("", "complete", "defer", "reject_source"),
        reason_column="target_primary_reason",
        secondary_reason_column="target_secondary_reason",
        notes_column="target_notes",
        reason_options=REASONS,
        default_filter_columns=("online_source_slice", "reason_enrichment_target", "species", "domain_label"),
        metadata_columns=(
            "online_source_slice",
            "reason_enrichment_target",
            "species",
            "domain_label",
            "query_license",
            "candidate_license",
            "query_source_record_uri",
            "candidate_source_record_uri",
        ),
        standards=(
            "This online set is for reason-label enrichment only; do not infer identity.",
            "Mark complete when you can identify the strongest evidence-risk reason for the pair.",
            "Mark reject_source if the image is wrong species, non-animal, broken, license/source-problematic, or unusable for the intended supplement.",
            "External images can be heterogeneous; judge evidence risk, not whether the source matches CzechLynx/Bobcat final modeling perfectly.",
            "If a pair is actually review-ready, note that in target_notes and choose the least applicable reason only if the form requires one.",
        ),
    )
    run_pair_review_app(config)


if __name__ == "__main__":
    main()
