"""Shared schema constants for Phase 6 unique-500 image annotation workflow."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REVIEW_IMAGE_DIR = PROJECT_ROOT / "data/review_images/czechlynx/phase6_unique_500"
REVIEW_IMAGE_DIR_REL = "data/review_images/czechlynx/phase6_unique_500"
WORKING_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase6_unique_500_image_annotation_working.csv"
TEMPLATE_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase6_unique_500_image_annotation_template.csv"
INTERNAL_MAPPING_CSV = (
    PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase6_unique_500_image_review_mapping_internal.csv"
)
FREEZE_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase6_unique_500_image_annotation_v1.csv"

EXPECTED_ROWS = 500
ID_PREFIX = "czlx_phase6_expanded"

PUBLIC_COLUMNS = [
    "expanded_image_id",
    "review_image_path_local",
    "candidate_source_id",
    "candidate_reason",
    "selection_stratum",
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "annotator_notes",
]

ANNOTATION_FIELDS = [
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "annotator_notes",
]

ALLOWED_VALUES: dict[str, set[str]] = {
    "pattern_visibility": {"high", "medium", "low", "none", "unknown"},
    "side_visibility": {"left", "right", "both", "unknown"},
    "side_evidence_quality": {"high", "medium", "low", "none", "unknown"},
    "body_fraction_visible": {"0_25", "26_50", "51_75", "76_100", "unknown"},
    "partial_body": {"yes", "no", "unknown"},
    "frontal_or_rear_view": {"yes", "no", "unknown"},
    "silhouette_only": {"yes", "no", "unknown"},
    "blur_level": {"none", "mild", "moderate", "severe", "unknown"},
    "occlusion_level": {"none", "partial", "major", "unknown"},
    "lighting_condition": {"normal", "overexposed", "underexposed", "mixed", "unknown"},
    "night_ir_artifact": {"yes", "no", "unknown"},
    "contrast_level": {"good", "low", "unknown"},
    "primary_limiting_factor": {
        "none",
        "blur",
        "occlusion",
        "low_contrast",
        "overexposed",
        "underexposed",
        "night_ir_artifact",
        "pattern_not_visible",
        "side_unknown",
        "side_non_comparable",
        "partial_body",
        "frontal_or_rear_view",
        "silhouette",
        "non_target_species",
        "other",
        "unknown",
    },
    "uncertainty_flag": {"yes", "no"},
    "annotation_status": {"pending", "complete", "needs_review"},
}

PENDING_ALLOWED_BLANK = set(ANNOTATION_FIELDS) - {"annotation_status"}
COMPLETE_REQUIRED_FIELDS = [
    field
    for field in ANNOTATION_FIELDS
    if field not in {"annotator_notes", "annotation_status"}
]

RESTRICTED_PATTERNS = [
    "unique_name",
    "/Users/",
    "data/raw",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "internal_id",
    "working_id",
    "working_individual_id",
    "true_id",
    "local_image_path",
    "czlx_expanded_",
    "CzechLynx/snpa",
    "CzechLynx/foe",
]

SAFE_PATH_PREFIXES = (
    "data/review_images/czechlynx/",
    "data/labels/czechlynx/",
    "data/interim/czechlynx/",
)


def find_leakage_issues(text: str, *, context: str = "") -> list[str]:
    """Return human-readable leakage matches, avoiding safe czechlynx path false positives."""
    import re

    issues: list[str] = []
    lower = text.lower()

    for pattern in RESTRICTED_PATTERNS:
        if pattern.lower() in lower:
            issues.append(f"{context}: matched `{pattern}`")

    if re.search(r"(?<![a-z])lynx_\d", text):
        issues.append(f"{context}: matched raw individual id pattern `lynx_`")

    if "location" in lower and "selection_stratum" not in lower:
        if not any(prefix in lower for prefix in SAFE_PATH_PREFIXES):
            issues.append(f"{context}: matched `location`")

    return issues


def path_is_safe_public_path(path_str: str) -> bool:
    normalized = path_str.replace("\\", "/").lower()
    return any(normalized.startswith(prefix) for prefix in SAFE_PATH_PREFIXES)

STREAMLIT_ALLOWED_VALUES = {field: [""] + sorted(values) for field, values in ALLOWED_VALUES.items()}
