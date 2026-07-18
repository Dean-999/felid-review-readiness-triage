#!/usr/bin/env python3
"""Build a feature-varied validation packet for PF-ERI core predictors."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/evidence-feature-extraction/pair_evidence_features.csv"
IMAGE_INDEX_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/final-modeling-bootstrap/final_modeling_image_index.csv"
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/feature-varied-validation-packet"
PACKET_CSV = OUTPUT_DIR / "feature_varied_validation_packet.csv"
REVIEW_FORM_CSV = OUTPUT_DIR / "feature_varied_validation_review_form.csv"
AUDIT_JSON = OUTPUT_DIR / "feature_varied_validation_packet_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

CORE_FEATURES = [
    "visible_pattern_area_score",
    "viewpoint_side_compatibility",
    "body_part_overlap_score",
    "night_or_motion_blur_risk",
    "cross_descriptor_agreement_score",
    "source_domain_shift_score",
]

PACKET_COLUMNS = [
    "feature_varied_id",
    "selection_role",
    "selection_feature",
    "selection_bin",
    "pair_id",
    "pair_family",
    "pair_scope",
    "construction_rule",
    "identity_relation",
    "same_identity_label",
    "validation_label_role",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "query_image_exists",
    "candidate_image_exists",
    *CORE_FEATURES,
    "visible_pattern_area_score_bin",
    "viewpoint_side_compatibility_bin",
    "body_part_overlap_score_bin",
    "night_or_motion_blur_risk_bin",
    "cross_descriptor_agreement_score_bin",
    "source_domain_shift_score_bin",
    "descriptor_score_source",
    "visible_pattern_area_source",
    "source_domain_shift_source",
    "target_review_ready",
    "target_not_ready_reason",
    "target_secondary_reason",
    "target_notes",
    "claim_boundary",
]

REVIEW_COLUMNS = [
    "feature_varied_id",
    "query_image_path",
    "candidate_image_path",
    "selection_feature",
    "selection_bin",
    *CORE_FEATURES,
    "target_review_ready",
    "target_not_ready_reason",
    "target_secondary_reason",
    "target_notes",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def bin_feature(feature: str, value: Any) -> str:
    numeric = to_float(value)
    if feature == "visible_pattern_area_score":
        if numeric < 0.20:
            return "low_visible_pattern"
        if numeric < 0.67:
            return "mid_visible_pattern"
        return "high_visible_pattern"
    if feature == "viewpoint_side_compatibility":
        if numeric <= 0.35:
            return "low_side_compatibility"
        if numeric < 0.69:
            return "mid_side_compatibility"
        return "high_side_compatibility"
    if feature == "body_part_overlap_score":
        if numeric < 0.33:
            return "low_body_overlap"
        if numeric < 0.67:
            return "mid_body_overlap"
        return "high_body_overlap"
    if feature == "night_or_motion_blur_risk":
        if numeric < 0.20:
            return "low_blur_risk"
        if numeric < 0.50:
            return "mid_blur_risk"
        return "high_blur_risk"
    if feature == "cross_descriptor_agreement_score":
        if numeric < 0.50:
            return "low_descriptor_agreement"
        if numeric <= 0.67:
            return "neutral_descriptor_agreement"
        return "high_descriptor_agreement"
    if feature == "source_domain_shift_score":
        if numeric <= 0.20:
            return "low_domain_shift"
        if numeric < 0.70:
            return "mid_domain_shift"
        return "high_domain_shift"
    raise ValueError(f"unknown feature: {feature}")


def image_path_lookup() -> dict[str, str]:
    return {row["image_id"]: row["local_image_path"] for row in read_csv(IMAGE_INDEX_CSV)}


def path_exists(path_text: str) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if path.is_absolute():
        return path.exists()
    return (PROJECT_ROOT / path).exists()


def row_bins(row: dict[str, str]) -> dict[str, str]:
    return {f"{feature}_bin": bin_feature(feature, row.get(feature, "")) for feature in CORE_FEATURES}


def stable_sort_key(row: dict[str, str]) -> tuple[Any, ...]:
    return (
        row.get("pair_family", ""),
        row.get("pair_scope", ""),
        row.get("construction_rule", ""),
        row.get("pair_id", ""),
    )


def select_evenly(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if count <= 0 or not rows:
        return []
    ordered = sorted(rows, key=stable_sort_key)
    if len(ordered) <= count:
        return ordered
    selected: list[dict[str, str]] = []
    used_indices: set[int] = set()
    for n in range(count):
        idx = round(n * (len(ordered) - 1) / max(1, count - 1))
        while idx in used_indices and idx + 1 < len(ordered):
            idx += 1
        if idx not in used_indices:
            selected.append(ordered[idx])
            used_indices.add(idx)
    return selected


def diversity_score(row: dict[str, str], global_bin_counts: Counter[str]) -> tuple[float, str]:
    rarity = 0.0
    for feature in CORE_FEATURES:
        bin_name = bin_feature(feature, row.get(feature, ""))
        rarity += 1.0 / max(1, global_bin_counts[f"{feature}:{bin_name}"])
    extremes = sum(abs(to_float(row.get(feature, 0.5)) - 0.5) for feature in CORE_FEATURES)
    return (rarity + extremes / 10.0, row["pair_id"])


def validation_label_role(row: dict[str, str]) -> str:
    if row["identity_relation"] == "known":
        return "known_id_same_different_label_available_not_predictor"
    return "unlabeled_feature_variation_only_no_identity_claim"


def packet_row(
    source: dict[str, str],
    image_paths: dict[str, str],
    feature_varied_id: str,
    selection_role: str,
    selection_feature: str,
    selection_bin: str,
) -> dict[str, Any]:
    query_path = image_paths.get(source["query_image_id"], "")
    candidate_path = image_paths.get(source["candidate_image_id"], "")
    bins = row_bins(source)
    return {
        "feature_varied_id": feature_varied_id,
        "selection_role": selection_role,
        "selection_feature": selection_feature,
        "selection_bin": selection_bin,
        "pair_id": source["pair_id"],
        "pair_family": source["pair_family"],
        "pair_scope": source["pair_scope"],
        "construction_rule": source["construction_rule"],
        "identity_relation": source["identity_relation"],
        "same_identity_label": source["same_identity_label"],
        "validation_label_role": validation_label_role(source),
        "query_image_id": source["query_image_id"],
        "candidate_image_id": source["candidate_image_id"],
        "query_image_path": query_path,
        "candidate_image_path": candidate_path,
        "query_image_exists": "yes" if path_exists(query_path) else "no",
        "candidate_image_exists": "yes" if path_exists(candidate_path) else "no",
        **{feature: source.get(feature, "") for feature in CORE_FEATURES},
        **bins,
        "descriptor_score_source": source.get("descriptor_score_source", ""),
        "visible_pattern_area_source": source.get("visible_pattern_area_source", ""),
        "source_domain_shift_source": source.get("source_domain_shift_source", ""),
        "target_review_ready": "",
        "target_not_ready_reason": "",
        "target_secondary_reason": "",
        "target_notes": "",
        "claim_boundary": (
            "Feature-varied validation packet for reviewability/evidence-risk labels. "
            "Known identity labels are targets/diagnostics only and must not be model predictors; "
            "Bobcat rows are not identity-labeled."
        ),
    }


def build_packet_rows(target_rows: int, per_feature_bin: int) -> list[dict[str, Any]]:
    feature_rows = read_csv(FEATURE_TABLE_CSV)
    image_paths = image_path_lookup()
    by_pair_id = {row["pair_id"]: row for row in feature_rows}
    selected: dict[str, tuple[dict[str, str], str, str, str]] = {}

    for feature in CORE_FEATURES:
        bins: dict[str, list[dict[str, str]]] = {}
        for row in feature_rows:
            bins.setdefault(bin_feature(feature, row.get(feature, "")), []).append(row)
        for bin_name, candidates in sorted(bins.items()):
            for row in select_evenly(candidates, per_feature_bin):
                selected.setdefault(row["pair_id"], (row, "feature_bin_stratified", feature, bin_name))

    global_bin_counts: Counter[str] = Counter()
    for row in feature_rows:
        for feature in CORE_FEATURES:
            global_bin_counts[f"{feature}:{bin_feature(feature, row.get(feature, ''))}"] += 1

    if len(selected) < target_rows:
        remaining = [row for row in by_pair_id.values() if row["pair_id"] not in selected]
        remaining.sort(key=lambda row: diversity_score(row, global_bin_counts), reverse=True)
        for row in remaining[: max(0, target_rows - len(selected))]:
            selected[row["pair_id"]] = (row, "diversity_fill", "multi_feature", "rarity_and_extreme_fill")

    ordered = sorted(selected.values(), key=lambda item: stable_sort_key(item[0]))[:target_rows]
    return [
        packet_row(
            source=row,
            image_paths=image_paths,
            feature_varied_id=f"feature_varied_{idx:04d}",
            selection_role=selection_role,
            selection_feature=selection_feature,
            selection_bin=selection_bin,
        )
        for idx, (row, selection_role, selection_feature, selection_bin) in enumerate(ordered, start=1)
    ]


def feature_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for feature in CORE_FEATURES:
        values = [to_float(row[feature]) for row in rows]
        bin_counts = Counter(row[f"{feature}_bin"] for row in rows)
        summary[feature] = {
            "unique_values": len(set(values)),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "bin_counts": dict(sorted(bin_counts.items())),
            "represented_bins": sum(1 for count in bin_counts.values() if count > 0),
        }
    return summary


def audit_packet(rows: list[dict[str, Any]], target_rows: int) -> dict[str, Any]:
    feature_stats = feature_summary(rows)
    missing_image_rows = [
        row["feature_varied_id"]
        for row in rows
        if row["query_image_exists"] != "yes" or row["candidate_image_exists"] != "yes"
    ]
    feature_failures = {
        feature: stats
        for feature, stats in feature_stats.items()
        if stats["represented_bins"] < 2 or stats["unique_values"] < 2
    }
    hard_failures = []
    if not (600 <= len(rows) <= 1000):
        hard_failures.append("packet_row_count_outside_600_1000")
    if len(rows) != min(target_rows, max(target_rows, len(rows))):
        hard_failures.append("unexpected_target_row_count")
    if missing_image_rows:
        hard_failures.append("missing_image_paths")
    if feature_failures:
        hard_failures.append("core_features_without_variation")
    bobcat_identity_violations = sum(
        row["pair_family"] == "transfer_stress"
        and (row["identity_relation"] != "unlabeled" or bool(str(row["same_identity_label"]).strip()))
        for row in rows
    )
    if bobcat_identity_violations:
        hard_failures.append("bobcat_identity_boundary_violation")
    descriptor_low_count = feature_stats["cross_descriptor_agreement_score"]["bin_counts"].get(
        "low_descriptor_agreement", 0
    )
    limitations = []
    if descriptor_low_count < 10:
        limitations.append(
            "low cross-descriptor disagreement is scarce in the current feature table; packet includes available lows but cannot balance that bin."
        )
    return {
        "built_at_utc": utc_now(),
        "status": "PASS" if not hard_failures else "FAIL",
        "failures": hard_failures,
        "limitations": limitations,
        "input_feature_table_csv": project_relative(FEATURE_TABLE_CSV),
        "input_image_index_csv": project_relative(IMAGE_INDEX_CSV),
        "packet_csv": project_relative(PACKET_CSV),
        "review_form_csv": project_relative(REVIEW_FORM_CSV),
        "packet_rows": len(rows),
        "feature_summary": feature_stats,
        "selection_role_counts": dict(sorted(Counter(row["selection_role"] for row in rows).items())),
        "pair_family_counts": dict(sorted(Counter(row["pair_family"] for row in rows).items())),
        "construction_rule_counts": dict(sorted(Counter(row["construction_rule"] for row in rows).items())),
        "identity_relation_counts": dict(sorted(Counter(row["identity_relation"] for row in rows).items())),
        "missing_image_rows": missing_image_rows[:20],
        "missing_image_row_count": len(missing_image_rows),
        "bobcat_identity_boundary_violations": bobcat_identity_violations,
        "claim_boundary": (
            "This packet solves feature variation for reviewability validation. It does not create new identity labels, "
            "does not validate reason classes by itself, and does not convert Bobcat transfer rows into identity evidence."
        ),
    }


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Feature-Varied Validation Packet",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This packet samples pair rows so all six prespecified PF-ERI core features vary across the human-review queue.",
        "",
        "## Counts",
        "",
        f"- Packet rows: {audit['packet_rows']}",
        f"- Pair families: `{audit['pair_family_counts']}`",
        f"- Identity relations: `{audit['identity_relation_counts']}`",
        "",
        "## Core Feature Coverage",
        "",
    ]
    for feature, stats in audit["feature_summary"].items():
        lines.append(
            f"- `{feature}`: unique={stats['unique_values']}, min={stats['min']}, max={stats['max']}, bins=`{stats['bin_counts']}`"
        )
    lines.extend(["", "## Limitations", ""])
    if audit["limitations"]:
        lines.extend(f"- {item}" for item in audit["limitations"])
    else:
        lines.append("- No feature-variation limitation detected.")
    lines.extend(["", "## Boundary", "", audit["claim_boundary"]])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(target_rows: int = 900, per_feature_bin: int = 35) -> dict[str, Any]:
    rows = build_packet_rows(target_rows=target_rows, per_feature_bin=per_feature_bin)
    audit = audit_packet(rows, target_rows=target_rows)
    write_csv(PACKET_CSV, rows, PACKET_COLUMNS)
    write_csv(REVIEW_FORM_CSV, rows, REVIEW_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-rows", type=int, default=900)
    parser.add_argument("--per-feature-bin", type=int, default=35)
    args = parser.parse_args()
    audit = build(target_rows=args.target_rows, per_feature_bin=args.per_feature_bin)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
