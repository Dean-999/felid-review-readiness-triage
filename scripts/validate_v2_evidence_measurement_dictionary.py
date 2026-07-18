#!/usr/bin/env python3
"""Validate the PF-ERI v2 evidence-measurement dictionary.

The dictionary records what a measurement means, how it may be obtained, and
why it may be unavailable.  It is deliberately not an implementation of old
PF-ERI proxy scores: no v1 values, labels, review routes, or decision
thresholds are valid inputs to this v2 contract.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


DICTIONARY_VERSION = "pferi_v2_evidence_measurement_dictionary_v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY_PATH = ROOT / "schemas" / "pferi_v2" / "evidence_measurement_dictionary_v1.json"

VALID_ROLES = {"automatic_core_candidate", "oracle_measurement", "metadata_stratification_only"}
VALID_ENTITY_LEVELS = {"image", "pair", "pair_membership"}
VALID_DATA_TYPES = {"continuous", "integer", "categorical", "identifier"}
VALID_AVAILABILITY = {"automatic", "manual_only", "metadata_only"}
VALID_PRIMARY_ELIGIBILITY = {"pending_workstream_02", "never_oracle", "never_metadata"}
VALUE_STATUSES = {
    "not_missing",
    "not_attempted",
    "upstream_input_absent",
    "image_decode_failure",
    "detector_no_subject",
    "detector_low_confidence",
    "model_inference_failure",
    "model_output_invalid",
    "not_applicable",
    "restricted_metadata",
    "ambiguous_human_annotation",
}
FAILURE_CODES = {
    "none",
    "input_manifest_missing",
    "file_unavailable",
    "image_decode_failure",
    "subject_not_detected",
    "detector_low_confidence",
    "model_runtime_error",
    "model_output_invalid",
    "manual_annotation_unavailable",
    "manual_annotation_ambiguous",
    "not_applicable",
    "restricted_metadata",
}
FORBIDDEN_FEATURE_TOKENS = ("review", "decision", "route", "pferi", "outcome", "label", "identity")
REQUIRED_FEATURE_FIELDS = {
    "feature_name",
    "entity_level",
    "role",
    "data_type",
    "unit_or_categories",
    "value_direction",
    "inference_time_availability",
    "primary_model_eligibility",
    "outcome_independence",
    "operational_definition",
    "prohibited_inputs",
    "allowed_value_statuses",
    "allowed_failure_codes",
    "version",
}


def _feature(
    name: str,
    entity_level: str,
    role: str,
    data_type: str,
    unit_or_categories: str,
    value_direction: str,
    availability: str,
    eligibility: str,
    definition: str,
    prohibited_inputs: list[str],
) -> dict[str, Any]:
    return {
        "feature_name": name,
        "entity_level": entity_level,
        "role": role,
        "data_type": data_type,
        "unit_or_categories": unit_or_categories,
        "value_direction": value_direction,
        "inference_time_availability": availability,
        "primary_model_eligibility": eligibility,
        "outcome_independence": "must be measured without v2 outcome reviewer decisions, routes, or identity truth",
        "operational_definition": definition,
        "prohibited_inputs": prohibited_inputs,
        "allowed_value_statuses": sorted(VALUE_STATUSES),
        "allowed_failure_codes": sorted(FAILURE_CODES),
        "version": "v1",
    }


def build_default_dictionary() -> dict[str, Any]:
    """Return the checked-in versioned dictionary; candidate does not mean admitted."""
    if DEFAULT_DICTIONARY_PATH.exists():
        return load_dictionary(DEFAULT_DICTIONARY_PATH)
    return _build_initial_dictionary()


def _build_initial_dictionary() -> dict[str, Any]:
    """Provide the source definition for initial artifact creation only."""
    automatic_quality = ("automatic_core_candidate", "automatic", "pending_workstream_02")
    automatic_pair = ("automatic_core_candidate", "automatic", "pending_workstream_02")
    oracle = ("oracle_measurement", "manual_only", "never_oracle")
    metadata = ("metadata_stratification_only", "metadata_only", "never_metadata")
    blocked = ["v2_outcome_review", "review_route", "identity_truth", "historical_v1_proxy_or_constant"]
    return {
        "dictionary_version": DICTIONARY_VERSION,
        "construct": "pair-level evidential admissibility for responsible individual-level review",
        "scope": "CzechLynx v2 only; cross-species use requires a new adapter and calibration",
        "record_contract": {
            "required_columns": [
                "entity_id", "feature_name", "value_numeric", "value_categorical", "value_status",
                "failure_code", "source_mode", "extractor_or_annotation_version", "runtime_ms",
                "manual_correction_minutes",
            ],
            "zero_rule": "A numeric zero is a measured value only when value_status is not_missing; it cannot encode missingness or failure.",
            "blank_rule": "Blank measurement values require a non-not_missing value_status and a declared failure_code.",
        },
        "taxonomy": {"value_statuses": sorted(VALUE_STATUSES), "failure_codes": sorted(FAILURE_CODES)},
        "features": [
            _feature("animal_coverage_fraction", "image", *automatic_quality, "continuous", "fraction from 0 to 1", "higher indicates more visible subject coverage", "estimated subject pixels divided by image pixels", blocked),
            _feature("native_pixel_count", "image", *automatic_quality, "integer", "native image pixels", "higher indicates greater available spatial detail", "decoded native width multiplied by decoded native height", blocked),
            _feature("sharpness_measure", "image", *automatic_quality, "continuous", "extractor-specific nonnegative scale", "higher indicates sharper local structure", "pre-registered automatic sharpness extractor output", blocked),
            _feature("exposure_clipping_fraction", "image", *automatic_quality, "continuous", "fraction from 0 to 1", "lower indicates less clipped exposure", "fraction of pixels classified as clipped by the registered extractor", blocked),
            _feature("infrared_likelihood", "image", *automatic_quality, "continuous", "probability-like score from 0 to 1", "direction is descriptive, not intrinsically favorable", "registered automatic classifier estimate of infrared illumination likelihood", blocked),
            _feature("local_match_coverage_fraction", "pair", *automatic_pair, "continuous", "fraction from 0 to 1", "higher indicates more locally supported correspondence", "registered local matcher coverage over valid comparable regions", blocked),
            _feature("descriptor_disagreement", "pair", *automatic_pair, "continuous", "registered disagreement scale", "higher indicates less descriptor concordance", "difference among registered descriptor outputs after their inputs are frozen", blocked),
            _feature("visible_pattern_area_fraction", "image", *oracle, "continuous", "fraction from 0 to 1", "higher indicates more visible individual-pattern evidence", "structural annotation using the feature-only guide; not a reviewer outcome", blocked),
            _feature("viewpoint_compatibility_class", "pair", *oracle, "categorical", "compatible, partial, incompatible, or unknown", "compatible is more comparable; unknown is not a numeric value", "feature-annotator classification of view compatibility using neutral instructions", blocked),
            _feature("shared_body_region_fraction", "pair", *oracle, "continuous", "fraction from 0 to 1", "higher indicates more shared visible anatomical region", "feature-annotator estimate using the structural overlap guide", blocked),
            _feature("occlusion_fraction", "image", *oracle, "continuous", "fraction from 0 to 1", "lower indicates less occlusion", "feature-annotator estimate of subject area obscured by non-subject material", blocked),
            _feature("descriptor_name", "pair_membership", *metadata, "identifier", "frozen descriptor identifier", "not a quality or evidence direction", "identifier from the directed membership manifest", ["v2_outcome_review", "identity_truth", "model_input"]),
            _feature("queue_snapshot_id", "pair_membership", *metadata, "identifier", "frozen queue snapshot identifier", "not a quality or evidence direction", "identifier from the directed membership manifest", ["v2_outcome_review", "identity_truth", "model_input"]),
            _feature("source_dataset", "image", *metadata, "categorical", "audited source domain category", "not a quality or evidence direction", "provenance category from the frozen image manifest", ["v2_outcome_review", "identity_truth", "model_input"]),
        ],
        "admission_rule": "automatic_core_candidate fields are candidates only. Workstreams 02 and 04 must demonstrate feasibility and nonconstant valid outputs before any field can enter a primary model.",
        "boundary": "Oracle and metadata fields are retained for measurement evaluation, stratification, and audit; they are never primary automatic-model inputs.",
    }


def load_dictionary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def validate_dictionary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic audit. This validates contracts, not feasibility."""
    issues: list[dict[str, str]] = []
    if payload.get("dictionary_version") != DICTIONARY_VERSION:
        _issue(issues, "invalid_dictionary_version", "unexpected dictionary version")
    taxonomy = payload.get("taxonomy", {})
    if set(taxonomy.get("value_statuses", [])) != VALUE_STATUSES:
        _issue(issues, "invalid_value_status_taxonomy", "value-status taxonomy must be complete and exact")
    if set(taxonomy.get("failure_codes", [])) != FAILURE_CODES:
        _issue(issues, "invalid_failure_code_taxonomy", "failure-code taxonomy must be complete and exact")
    record_columns = set(payload.get("record_contract", {}).get("required_columns", []))
    required_record_columns = {"entity_id", "feature_name", "value_status", "failure_code", "source_mode"}
    if not required_record_columns.issubset(record_columns):
        _issue(issues, "record_contract_missing_required_columns", "measurement records need entity, feature, status, failure, and source fields")

    features = payload.get("features", [])
    if not isinstance(features, list) or not features:
        _issue(issues, "features_empty", "dictionary requires at least one feature")
        features = []
    names: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    for feature in features:
        if not isinstance(feature, Mapping):
            _issue(issues, "feature_not_object", "each feature must be an object")
            continue
        name = str(feature.get("feature_name", ""))
        names[name] += 1
        roles[str(feature.get("role", ""))] += 1
        missing = sorted(REQUIRED_FEATURE_FIELDS.difference(feature))
        if missing:
            _issue(issues, f"feature_missing_fields:{name}", ", ".join(missing))
            continue
        if not name:
            _issue(issues, "feature_name_empty", "feature name cannot be empty")
        if any(token in name.lower() for token in FORBIDDEN_FEATURE_TOKENS):
            _issue(issues, f"forbidden_feature_name_token:{name}", "feature name encodes a prohibited outcome or truth concept")
        if feature["entity_level"] not in VALID_ENTITY_LEVELS:
            _issue(issues, f"invalid_entity_level:{name}", "invalid entity level")
        role = feature["role"]
        if role not in VALID_ROLES:
            _issue(issues, f"invalid_role:{name}", "invalid role")
        if feature["data_type"] not in VALID_DATA_TYPES:
            _issue(issues, f"invalid_data_type:{name}", "invalid data type")
        if feature["inference_time_availability"] not in VALID_AVAILABILITY:
            _issue(issues, f"invalid_availability:{name}", "invalid availability")
        if feature["primary_model_eligibility"] not in VALID_PRIMARY_ELIGIBILITY:
            _issue(issues, f"invalid_primary_eligibility:{name}", "invalid primary-model eligibility")
        if "not_missing" not in feature["allowed_value_statuses"] or not set(feature["allowed_value_statuses"]).issubset(VALUE_STATUSES):
            _issue(issues, f"invalid_value_statuses:{name}", "feature must declare valid value statuses including not_missing")
        if "none" not in feature["allowed_failure_codes"] or not set(feature["allowed_failure_codes"]).issubset(FAILURE_CODES):
            _issue(issues, f"invalid_failure_codes:{name}", "feature must declare valid failure codes including none")
        if role == "automatic_core_candidate" and feature["inference_time_availability"] != "automatic":
            _issue(issues, f"automatic_candidate_not_automatic:{name}", "automatic candidate must be available automatically")
        if role == "automatic_core_candidate" and feature["primary_model_eligibility"] != "pending_workstream_02":
            _issue(issues, f"automatic_candidate_wrong_primary_status:{name}", "automatic candidate remains pending feasibility")
        if role == "oracle_measurement" and feature["primary_model_eligibility"] != "never_oracle":
            _issue(issues, f"oracle_feature_not_blocked_from_primary_model:{name}", "oracle feature cannot enter primary automatic model")
        if role == "metadata_stratification_only" and feature["primary_model_eligibility"] != "never_metadata":
            _issue(issues, f"metadata_feature_not_blocked_from_primary_model:{name}", "metadata cannot enter primary model")
        prohibited = {str(item) for item in feature["prohibited_inputs"]}
        if "v2_outcome_review" not in prohibited or "identity_truth" not in prohibited:
            _issue(issues, f"feature_missing_leakage_boundary:{name}", "feature must prohibit outcomes and identity truth")
    for name, count in names.items():
        if name and count > 1:
            _issue(issues, f"duplicate_feature_name:{name}", "feature names must be unique")
    return {
        "dictionary_version": payload.get("dictionary_version"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "error_codes": [issue["code"] for issue in issues],
        "feature_count": len(features),
        "feature_role_counts": dict(sorted(roles.items())),
        "outcome_leakage_feature_count": sum(any(token in str(item.get("feature_name", "")).lower() for token in FORBIDDEN_FEATURE_TOKENS) for item in features if isinstance(item, Mapping)),
        "claim_boundary": "This audit validates dictionary completeness and leakage boundaries. It does not establish extractor feasibility, measurement reliability, model benefit, or a deployment threshold.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY_PATH)
    parser.add_argument("--audit-json", type=Path)
    parser.add_argument("--write-schema", type=Path)
    args = parser.parse_args(argv)
    payload = load_dictionary(args.dictionary)
    audit = validate_dictionary(payload)
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_schema:
        args.write_schema.parent.mkdir(parents=True, exist_ok=True)
        args.write_schema.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
