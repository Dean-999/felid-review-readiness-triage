#!/usr/bin/env python3
"""Streamlit app for internal reason-label enrichment review."""

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
    "other",
)


def main() -> None:
    source = (
        PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_review_form.csv"
    )
    working = (
        PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_review_working.csv"
    )
    config = PairReviewConfig(
        title="Internal Reason-Label Enrichment",
        source_csv=source,
        working_csv=working,
        id_column="enrichment_id",
        query_image_column="query_image_path",
        candidate_image_column="candidate_image_path",
        status_column="reason_label_review_status",
        decision_columns=(
            "target_primary_reason",
            "target_secondary_reason",
            "target_body_region_visible",
            "target_notes",
        ),
        decision_options=("", "complete", "defer"),
        reason_column="target_primary_reason",
        secondary_reason_column="target_secondary_reason",
        notes_column="target_notes",
        reason_options=REASONS,
        default_filter_columns=("majority_decision", "suggested_reason_proxy"),
        metadata_columns=("majority_decision", "suggested_reason_proxy"),
        standards=(
            "Choose the primary reason explaining why this pair is not review-ready or uncertain.",
            "Use non_comparable_viewpoint when both images may be clear but show incompatible pose/side/body region.",
            "Use low_image_evidence, motion_or_blur, night_or_low_light, subject_too_small, partial_body, or occlusion when a single image blocks evidence.",
            "Use descriptor_evidence_conflict only when visual evidence is weak/conflicting despite the pair being a descriptor candidate.",
            "If unsure between two causes, put the strongest cause as primary and the other as secondary.",
        ),
    )
    run_pair_review_app(config)


if __name__ == "__main__":
    main()
