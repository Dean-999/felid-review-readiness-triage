#!/usr/bin/env python3
"""Select additional PF-ERI annotation candidates.

This script creates aggregate-safe, blinded candidate manifests for the next
annotation expansion. It uses internal identity labels only for balancing and
summary counts; public candidate rows contain neutral IDs and safe filenames.

Image-level candidates come from the unlabeled real-image manifest, so hard
visual factors such as blur and occlusion are not yet known. The script
therefore prioritizes identity expansion and available manifest proxies, then
records that hard visual strata must be confirmed during annotation. Pair-level
candidates use existing PF-ERI and descriptor signals where hard visual hints
are available.
"""

from __future__ import annotations

import csv
import hashlib
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat


SEED = 20260613
IMAGE_TARGET = 500
PAIR_TARGET = 800
DUPLICATE_IMAGE_RATE = 0.20
DUPLICATE_PAIR_MINIMUM = 200
IMAGE_QUALITY_POOL_PER_IDENTITY = 16

LABELED_IMAGE_TABLE = Path(
    "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated_v1.csv"
)
EXPANDED_INTERNAL_TABLE = Path(
    "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
)
REAL_MANIFEST = Path("data/interim/czechlynx/czechlynx_real_manifest.csv")
PHASE5_PAIR_TABLE = Path(
    "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
)

OUTPUT_DIR = Path("outputs/czechlynx/phase6/annotation_candidates")
QC_DIR = Path("outputs/czechlynx/qc")

IMAGE_CANDIDATES_OUT = OUTPUT_DIR / "phase6_additional_image_annotation_candidates.csv"
IMAGE_DUPLICATES_OUT = OUTPUT_DIR / "phase6_image_duplicate_annotation_subset.csv"
PAIR_CANDIDATES_OUT = OUTPUT_DIR / "phase6_hard_pair_annotation_candidates.csv"
PAIR_DUPLICATES_OUT = OUTPUT_DIR / "phase6_pair_duplicate_annotation_subset.csv"
SUMMARY_OUT = OUTPUT_DIR / "phase6_annotation_candidate_sampling_summary.csv"
QC_REPORT_OUT = QC_DIR / "phase6_annotation_candidate_selection_audit_report.txt"

SENSITIVE_HEADER_TERMS = {
    "unique_name",
    "working_individual_id",
    "original_id",
    "true_id",
    "path",
    "local_image_path",
    "review_image_path",
    "latitude",
    "longitude",
    "location",
    "cell_code",
    "trap_id",
    "source",
    "encounter",
}

SENSITIVE_VALUE_MARKERS = (
    "/Users/",
    "data/raw/",
    "CzechLynx/",
    "lynx_",
    "foe_",
    "snpa/",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def stable_hash(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def as_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_yes(value: str) -> bool:
    return str(value).strip().lower() in {"yes", "true", "1"}


def percentile_band(value: str) -> str:
    score = as_float(value)
    if score >= 90:
        return "very_high"
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 25:
        return "low"
    return "very_low"


def age_bucket(value: str) -> str:
    age = as_float(value, default=-1)
    if age < 0:
        return "age_unknown"
    if age <= 1:
        return "recent_or_low_age_proxy"
    if age <= 4:
        return "medium_age_proxy"
    return "older_image_proxy"


def image_proxy_stratum(row: dict[str, str], prior_labeled_count: int) -> str:
    parts = []
    if prior_labeled_count == 0:
        parts.append("new_identity")
    elif prior_labeled_count < 4:
        parts.append("underrepresented_identity")
    else:
        parts.append("existing_identity")

    split_pose = row.get("split-pose", "").strip() or "pose_split_unmarked"
    parts.append(f"pose_{split_pose}")

    coat_pattern = row.get("coat_pattern", "").strip() or "coat_pattern_unknown"
    parts.append(coat_pattern)
    parts.append(age_bucket(row.get("relative_age", "")))
    return "__".join(parts)


def quantile(values: list[float], q: float, default: float) -> float:
    if not values:
        return default
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * q)))
    return sorted_values[index]


def image_quality_metrics(row: dict[str, str]) -> dict[str, object]:
    """Return lightweight quality proxies without writing paths or pixels."""
    path = row.get("local_image_path", "")
    try:
        image = Image.open(path).convert("L")
        image.thumbnail((160, 160))
        stat = ImageStat.Stat(image)
        edge_stat = ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES))
        width, height = image.size
        aspect = width / height if height else 0
        return {
            "ok": True,
            "brightness": float(stat.mean[0]),
            "contrast": float(stat.stddev[0]),
            "edge_std": float(edge_stat.stddev[0]),
            "aspect": float(aspect),
        }
    except Exception:
        return {
            "ok": False,
            "brightness": 0.0,
            "contrast": 0.0,
            "edge_std": 0.0,
            "aspect": 0.0,
        }


def quality_proxy_label(
    metrics: dict[str, object],
    edge_cutoff: float,
    contrast_cutoff: float,
    dark_cutoff: float,
    bright_cutoff: float,
) -> str:
    if not metrics.get("ok"):
        return "quality_proxy_unreadable"
    labels = []
    edge_std = float(metrics["edge_std"])
    contrast = float(metrics["contrast"])
    brightness = float(metrics["brightness"])
    aspect = float(metrics["aspect"])
    if edge_std <= edge_cutoff:
        labels.append("low_edge_blur_proxy")
    if contrast <= contrast_cutoff:
        labels.append("low_contrast_proxy")
    if brightness <= dark_cutoff:
        labels.append("underexposure_proxy")
    if brightness >= bright_cutoff:
        labels.append("overexposure_proxy")
    if aspect <= 0.65 or aspect >= 1.55:
        labels.append("framing_or_partial_body_proxy")
    return ";".join(labels) if labels else "medium_or_easy_quality_proxy"


def descriptor_agreement(row: dict[str, str]) -> str:
    mega = as_float(row.get("megadescriptor_percentile", "0"))
    resnet = as_float(row.get("resnet50_percentile", "0"))
    gap = abs(mega - resnet)
    if gap >= 50:
        return "very_discordant"
    if gap >= 30:
        return "discordant"
    return "broadly_aligned"


def combined_similarity_percentile(row: dict[str, str]) -> float:
    return max(
        as_float(row.get("megadescriptor_percentile", "0")),
        as_float(row.get("resnet50_percentile", "0")),
    )


def min_similarity_percentile(row: dict[str, str]) -> float:
    return min(
        as_float(row.get("megadescriptor_percentile", "0")),
        as_float(row.get("resnet50_percentile", "0")),
    )


def select_image_candidates(
    real_manifest: list[dict[str, str]],
    expanded_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    current_by_identity = Counter(row["working_individual_id"] for row in expanded_rows)
    expanded_paths = {row.get("path", "") for row in expanded_rows}

    available_by_identity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in real_manifest:
        if not is_yes(row.get("image_exists", "")):
            continue
        if row.get("path", "") in expanded_paths:
            continue
        identity = row.get("unique_name", "").strip()
        if not identity:
            continue
        available_by_identity[identity].append(row)

    quality_by_path: dict[str, dict[str, object]] = {}
    quality_rows: list[tuple[dict[str, str], str, int, int, dict[str, object]]] = []
    quality_pool: list[tuple[dict[str, str], str, int, int]] = []
    for identity, rows in available_by_identity.items():
        prior = current_by_identity.get(identity, 0)
        available_count = len(rows)
        rows_for_quality = sorted(
            rows,
            key=lambda r: (
                r.get("encounter", ""),
                stable_hash(r.get("path", "")),
            ),
        )[:IMAGE_QUALITY_POOL_PER_IDENTITY]
        quality_pool.extend((row, identity, prior, available_count) for row in rows_for_quality)

    for row, identity, prior, available_count in quality_pool:
        metrics = image_quality_metrics(row)
        quality_by_path[row.get("path", "")] = metrics
        quality_rows.append((row, identity, prior, available_count, metrics))

    edge_values = [float(m["edge_std"]) for _, _, _, _, m in quality_rows if m.get("ok")]
    contrast_values = [float(m["contrast"]) for _, _, _, _, m in quality_rows if m.get("ok")]
    brightness_values = [float(m["brightness"]) for _, _, _, _, m in quality_rows if m.get("ok")]
    edge_cutoff = quantile(edge_values, 0.20, 8.0)
    contrast_cutoff = quantile(contrast_values, 0.20, 35.0)
    dark_cutoff = quantile(brightness_values, 0.08, 50.0)
    bright_cutoff = quantile(brightness_values, 0.92, 205.0)

    def identity_priority(item: tuple[str, list[dict[str, str]]]) -> tuple[int, int, int]:
        identity, rows = item
        prior = current_by_identity.get(identity, 0)
        enough_views = 1 if len(rows) >= 4 else 0
        return (prior, -enough_views, -len(rows), stable_hash(identity))

    selected_raw: list[tuple[dict[str, str], str, int, int]] = []
    used_paths: set[str] = set()
    selected_by_identity: Counter[str] = Counter()

    def try_add(row: dict[str, str], identity: str, prior: int, available_count: int) -> bool:
        path = row.get("path", "")
        if path in used_paths:
            return False
        if selected_by_identity[identity] >= 4:
            return False
        selected_raw.append((row, identity, prior, available_count))
        selected_by_identity[identity] += 1
        used_paths.add(path)
        return True

    def quality_sort_key(item: tuple[dict[str, str], str, int, int, dict[str, object]]) -> tuple:
        row, identity, prior, available_count, metrics = item
        return (
            prior,
            selected_by_identity[identity],
            float(metrics.get("edge_std", 0.0)),
            float(metrics.get("contrast", 0.0)),
            stable_hash(row.get("path", "")),
        )

    def add_quality_bucket(
        bucket_name: str,
        items: list[tuple[dict[str, str], str, int, int, dict[str, object]]],
        limit: int,
    ) -> None:
        added = 0
        for row, identity, prior, available_count, _ in sorted(items, key=quality_sort_key):
            if len(selected_raw) >= IMAGE_TARGET or added >= limit:
                break
            if try_add(row, identity, prior, available_count):
                row["_selection_bucket_override"] = bucket_name
                added += 1

    low_edge_items = [
        item for item in quality_rows if item[4].get("ok") and float(item[4]["edge_std"]) <= edge_cutoff
    ]
    low_contrast_items = [
        item
        for item in quality_rows
        if item[4].get("ok") and float(item[4]["contrast"]) <= contrast_cutoff
    ]
    exposure_items = [
        item
        for item in quality_rows
        if item[4].get("ok")
        and (
            float(item[4]["brightness"]) <= dark_cutoff
            or float(item[4]["brightness"]) >= bright_cutoff
        )
    ]
    framing_or_pose_items = [
        item
        for item in quality_rows
        if (
            item[4].get("ok")
            and (float(item[4]["aspect"]) <= 0.65 or float(item[4]["aspect"]) >= 1.55)
        )
        or item[0].get("split-pose", "").strip() in {"test", "train"}
    ]

    add_quality_bucket("quality_proxy_low_edge_blur", low_edge_items, 140)
    add_quality_bucket("quality_proxy_low_contrast", low_contrast_items, 100)
    add_quality_bucket("quality_proxy_exposure_extreme", exposure_items, 100)
    add_quality_bucket("quality_proxy_framing_or_pose", framing_or_pose_items, 80)

    for identity, rows in sorted(available_by_identity.items(), key=identity_priority):
        if len(selected_raw) >= IMAGE_TARGET:
            break
        prior = current_by_identity.get(identity, 0)
        per_identity_limit = 4 if prior == 0 else max(1, 4 - min(prior, 4))
        if prior > 0 and len(selected_raw) < IMAGE_TARGET * 0.80:
            continue
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r.get("encounter", ""),
                r.get("date", ""),
                stable_hash(r.get("path", "")),
            ),
        )
        seen_encounters: set[str] = set()
        picked_for_identity = 0
        for row in rows_sorted:
            if picked_for_identity >= per_identity_limit:
                break
            path = row.get("path", "")
            encounter_key = row.get("encounter", "") or path
            if encounter_key in seen_encounters and len(rows_sorted) > per_identity_limit:
                continue
            if try_add(row, identity, prior, len(rows)):
                seen_encounters.add(encounter_key)
                picked_for_identity += 1

    if len(selected_raw) < IMAGE_TARGET:
        for identity, rows in sorted(available_by_identity.items(), key=identity_priority):
            if len(selected_raw) >= IMAGE_TARGET:
                break
            prior = current_by_identity.get(identity, 0)
            for row in sorted(rows, key=lambda r: stable_hash(r.get("path", ""))):
                if len(selected_raw) >= IMAGE_TARGET:
                    break
                try_add(row, identity, prior, len(rows))

    selected_raw = selected_raw[:IMAGE_TARGET]

    rows_out: list[dict[str, object]] = []
    selected_identity_counts = Counter(identity for _, identity, _, _ in selected_raw)
    for idx, (row, identity, prior, available_count) in enumerate(selected_raw, start=1):
        proxy_stratum = image_proxy_stratum(row, prior)
        quality_metrics = quality_by_path.get(row.get("path", ""), {})
        quality_proxy = quality_proxy_label(
            quality_metrics,
            edge_cutoff=edge_cutoff,
            contrast_cutoff=contrast_cutoff,
            dark_cutoff=dark_cutoff,
            bright_cutoff=bright_cutoff,
        )
        bucket_override = row.get("_selection_bucket_override", "")
        if bucket_override:
            bucket = bucket_override
            reason = (
                "unlabeled image selected by lightweight quality proxy for possible "
                "hard visual evidence; final PF-ERI factors to be confirmed by annotation"
            )
        elif prior == 0:
            bucket = "new_identity_balanced_views"
            reason = (
                "identity not represented in current labeled set; selected for "
                "identity-diverse PF-ERI expansion; hard visual evidence to be "
                "confirmed during annotation"
            )
        elif prior < 4:
            bucket = "identity_underrepresented_views"
            reason = (
                "identity has fewer than four current labeled views; selected to "
                "improve within-identity view coverage"
            )
        else:
            bucket = "existing_identity_additional_views"
            reason = (
                "existing identity selected as fill after new-identity coverage; "
                "visual difficulty to be labeled"
            )

        rows_out.append(
            {
                "candidate_image_id": f"phase6_img_{idx:04d}",
                "proposed_review_image_filename": f"phase6_img_{idx:04d}.jpg",
                "annotation_task": "image_visual_factor_annotation",
                "selection_bucket": bucket,
                "selection_reason": reason,
                "prior_labeled_images_for_identity_count": prior,
                "available_unlabeled_images_for_identity_count": available_count,
                "selected_images_for_same_identity_count": selected_identity_counts[identity],
                "manifest_proxy_stratum": proxy_stratum,
                "image_quality_proxy_stratum": quality_proxy,
                "hard_visual_factor_status": "proxy_only_until_annotation",
                "visual_factor_status": "unlabeled_to_be_annotated",
                "annotation_round": "phase6_additional",
                "duplicate_annotation_candidate": "eligible",
                "candidate_order": idx,
                "_source_local_image_path": row.get("local_image_path", ""),
                "_source_manifest_path": row.get("path", ""),
            }
        )

    diagnostics = {
        "available_unlabeled_images": sum(len(v) for v in available_by_identity.values()),
        "available_unlabeled_identities": len(available_by_identity),
        "image_quality_proxy_pool_size": len(quality_rows),
        "image_quality_proxy_pool_per_identity_limit": IMAGE_QUALITY_POOL_PER_IDENTITY,
        "selected_internal_identity_count": len(selected_identity_counts),
        "selected_new_identity_rows": sum(
            1 for _, identity, _, _ in selected_raw if current_by_identity.get(identity, 0) == 0
        ),
        "selected_existing_identity_rows": sum(
            1 for _, identity, _, _ in selected_raw if current_by_identity.get(identity, 0) > 0
        ),
        "max_selected_images_for_one_identity": max(selected_identity_counts.values() or [0]),
        "image_selection_visual_factor_limitation": (
            "new image-level PF-ERI visual factors unavailable before annotation; "
            "selection uses identity balance, manifest proxies, and lightweight "
            "image-quality proxies"
        ),
        "image_quality_proxy_edge_std_20th_percentile": round(edge_cutoff, 4),
        "image_quality_proxy_contrast_20th_percentile": round(contrast_cutoff, 4),
        "image_quality_proxy_brightness_8th_percentile": round(dark_cutoff, 4),
        "image_quality_proxy_brightness_92nd_percentile": round(bright_cutoff, 4),
    }
    diagnostics.update(
        {
            f"image_bucket_{bucket}": count
            for bucket, count in Counter(row["selection_bucket"] for row in rows_out).items()
        }
    )
    diagnostics.update(
        {
            f"image_manifest_proxy_{stratum}": count
            for stratum, count in Counter(row["manifest_proxy_stratum"] for row in rows_out)
            .most_common(20)
        }
    )
    diagnostics.update(
        {
            f"image_quality_proxy_{stratum}": count
            for stratum, count in Counter(row["image_quality_proxy_stratum"] for row in rows_out)
            .most_common(20)
        }
    )
    return rows_out, diagnostics


def stratified_duplicate_rows(
    rows: list[dict[str, object]],
    bucket_field: str,
    duplicate_count: int,
    id_field: str,
    duplicate_id_field: str,
    duplicate_of_field: str,
    prefix: str,
) -> list[dict[str, object]]:
    rng = random.Random(SEED)
    by_bucket: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_bucket[str(row[bucket_field])].append(row)

    selected: list[dict[str, object]] = []
    for bucket_rows in by_bucket.values():
        if not bucket_rows:
            continue
        target = max(1, round(len(bucket_rows) * duplicate_count / max(len(rows), 1)))
        shuffled = list(bucket_rows)
        rng.shuffle(shuffled)
        selected.extend(shuffled[:target])

    if len(selected) < duplicate_count:
        already = {row[id_field] for row in selected}
        remaining = [row for row in rows if row[id_field] not in already]
        rng.shuffle(remaining)
        selected.extend(remaining[: duplicate_count - len(selected)])

    selected = selected[:duplicate_count]
    duplicate_rows: list[dict[str, object]] = []
    for idx, row in enumerate(selected, start=1):
        out = dict(row)
        out[duplicate_id_field] = f"{prefix}_{idx:04d}"
        out[duplicate_of_field] = row[id_field]
        out["duplicate_annotation_round"] = "phase6_duplicate_reliability"
        duplicate_rows.append(out)
    return duplicate_rows


def select_pair_candidates(
    phase5_rows: list[dict[str, str]],
    expanded_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    filename_by_expanded_id = {
        row["expanded_image_id"]: row["review_image_filename"] for row in expanded_rows
    }

    selected: list[tuple[dict[str, str], str, str]] = []
    used_pair_ids: set[str] = set()

    def add_bucket(name: str, reason: str, candidates: list[dict[str, str]], limit: int) -> None:
        for row in candidates:
            if len([item for item in selected if item[1] == name]) >= limit:
                break
            pair_id = row.get("pair_id", "")
            if pair_id in used_pair_ids:
                continue
            used_pair_ids.add(pair_id)
            selected.append((row, name, reason))

    high_similarity_different = sorted(
        [
            r
            for r in phase5_rows
            if r.get("pair_type") == "different" and combined_similarity_percentile(r) >= 90
        ],
        key=combined_similarity_percentile,
        reverse=True,
    )
    low_similarity_same = sorted(
        [
            r
            for r in phase5_rows
            if r.get("pair_type") == "same" and min_similarity_percentile(r) <= 25
        ],
        key=min_similarity_percentile,
    )
    high_pferi_descriptor_risky = sorted(
        [
            r
            for r in phase5_rows
            if r.get("pair_type") == "different"
            and r.get("visual_only_eri_band") == "high"
            and combined_similarity_percentile(r) >= 80
        ],
        key=combined_similarity_percentile,
        reverse=True,
    )
    low_pferi_descriptor_high = sorted(
        [
            r
            for r in phase5_rows
            if r.get("visual_only_eri_band") in {"low", "medium"}
            and combined_similarity_percentile(r) >= 80
        ],
        key=combined_similarity_percentile,
        reverse=True,
    )
    descriptor_disagreement = sorted(
        [
            r
            for r in phase5_rows
            if abs(
                as_float(r.get("megadescriptor_percentile", "0"))
                - as_float(r.get("resnet50_percentile", "0"))
            )
            >= 40
        ],
        key=lambda r: abs(
            as_float(r.get("megadescriptor_percentile", "0"))
            - as_float(r.get("resnet50_percentile", "0"))
        ),
        reverse=True,
    )
    side_not_comparable = sorted(
        [
            r
            for r in phase5_rows
            if r.get("pair_side_comparable", "").strip().lower() != "yes"
        ],
        key=combined_similarity_percentile,
        reverse=True,
    )
    frontal_rear_or_silhouette = sorted(
        [
            r
            for r in phase5_rows
            if is_yes(r.get("pair_any_frontal_rear", ""))
            or is_yes(r.get("pair_any_silhouette", ""))
            or is_yes(r.get("pair_any_uncertain", ""))
        ],
        key=combined_similarity_percentile,
        reverse=True,
    )
    balanced_fill = sorted(
        phase5_rows,
        key=lambda r: (
            combined_similarity_percentile(r),
            as_float(r.get("visual_only_eri", "0")),
        ),
        reverse=True,
    )

    add_bucket(
        "high_similarity_different_identity",
        "different-identity candidate with very high descriptor similarity",
        high_similarity_different,
        200,
    )
    add_bucket(
        "low_similarity_same_identity",
        "same-identity candidate with low descriptor similarity",
        low_similarity_same,
        150,
    )
    add_bucket(
        "pf_eri_high_descriptor_risky",
        "high visual evidence but descriptor-risky different-identity candidate",
        high_pferi_descriptor_risky,
        150,
    )
    add_bucket(
        "pf_eri_low_descriptor_high",
        "lower PF-ERI evidence but high descriptor similarity",
        low_pferi_descriptor_high,
        150,
    )
    add_bucket(
        "descriptor_disagreement",
        "MegaDescriptor and ResNet50 percentile disagreement",
        descriptor_disagreement,
        150,
    )
    add_bucket(
        "side_not_comparable_or_ambiguous",
        "source visual factors indicate side comparability is not clearly yes",
        side_not_comparable,
        150,
    )
    add_bucket(
        "frontal_rear_silhouette_uncertainty",
        "source visual factors indicate frontal/rear, silhouette, or uncertainty risk",
        frontal_rear_or_silhouette,
        100,
    )
    add_bucket(
        "balanced_hard_candidate_fill",
        "high-information fill to keep pair annotation set broad",
        balanced_fill,
        PAIR_TARGET,
    )

    selected = selected[:PAIR_TARGET]

    rows_out: list[dict[str, object]] = []
    for idx, (row, bucket, reason) in enumerate(selected, start=1):
        mega_band = percentile_band(row.get("megadescriptor_percentile", "0"))
        resnet_band = percentile_band(row.get("resnet50_percentile", "0"))
        rows_out.append(
            {
                "candidate_pair_id": f"phase6_pair_{idx:04d}",
                "image_a_review_filename": filename_by_expanded_id.get(
                    row.get("image_a_expanded_id", ""), ""
                ),
                "image_b_review_filename": filename_by_expanded_id.get(
                    row.get("image_b_expanded_id", ""), ""
                ),
                "annotation_task": "hard_pair_evidence_annotation",
                "selection_bucket": bucket,
                "selection_reason": reason,
                "similarity_risk_stratum": f"mega_{mega_band}__resnet_{resnet_band}",
                "visual_eri_band_hint": row.get("visual_only_eri_band", ""),
                "descriptor_agreement_hint": descriptor_agreement(row),
                "input_side_comparable_hint": row.get("pair_side_comparable", ""),
                "input_visual_issue_hint": ";".join(
                    flag
                    for flag, present in [
                        ("frontal_or_rear", is_yes(row.get("pair_any_frontal_rear", ""))),
                        ("silhouette", is_yes(row.get("pair_any_silhouette", ""))),
                        ("uncertain", is_yes(row.get("pair_any_uncertain", ""))),
                    ]
                    if present
                )
                or "none_flagged",
                "pair_side_comparability": "",
                "pair_visible_pattern_overlap": "",
                "pair_viewpoint_compatibility": "",
                "pair_evidence_overlap": "",
                "pair_review_recommendation": "",
                "pair_defer_reason": "",
                "pair_uncertainty_flag": "",
                "pair_annotation_notes": "",
                "candidate_order": idx,
            }
        )

    diagnostics = {
        "selected_same_pairs_internal_count": sum(
            1 for row, _, _ in selected if row.get("pair_type") == "same"
        ),
        "selected_different_pairs_internal_count": sum(
            1 for row, _, _ in selected if row.get("pair_type") == "different"
        ),
        "high_similarity_different_candidates_selected": sum(
            1
            for row, _, _ in selected
            if row.get("pair_type") == "different" and combined_similarity_percentile(row) >= 90
        ),
        "low_similarity_same_candidates_selected": sum(
            1
            for row, _, _ in selected
            if row.get("pair_type") == "same" and min_similarity_percentile(row) <= 25
        ),
        "pf_eri_descriptor_disagreement_candidates_selected": sum(
            1 for row, _, _ in selected if descriptor_agreement(row) != "broadly_aligned"
        ),
    }
    diagnostics.update(
        {
            f"pair_bucket_{bucket}": count
            for bucket, count in Counter(row["selection_bucket"] for row in rows_out).items()
        }
    )
    return rows_out, diagnostics


def write_summary(
    image_rows: list[dict[str, object]],
    image_duplicates: list[dict[str, object]],
    pair_rows: list[dict[str, object]],
    pair_duplicates: list[dict[str, object]],
    image_diag: dict[str, object],
    pair_diag: dict[str, object],
) -> None:
    summary_rows: list[dict[str, object]] = [
        {"metric": "random_seed", "value": SEED, "notes": "fixed deterministic seed"},
        {
            "metric": "selected_image_candidate_count",
            "value": len(image_rows),
            "notes": "target approximately 500 additional image labels",
        },
        {
            "metric": "selected_pair_candidate_count",
            "value": len(pair_rows),
            "notes": "target approximately 500-1000 hard pair labels",
        },
        {
            "metric": "image_duplicate_annotation_count",
            "value": len(image_duplicates),
            "notes": "20 percent of selected image candidates",
        },
        {
            "metric": "pair_duplicate_annotation_count",
            "value": len(pair_duplicates),
            "notes": "at least 200 hard pair candidates",
        },
        {
            "metric": "image_factor_strata_coverage",
            "value": "hard_visual_factors_proxy_only_before_annotation",
            "notes": (
                "new images come from the large manifest and do not yet have "
                "PF-ERI visual factor labels; manifest and image-quality proxy strata are reported"
            ),
        },
    ]
    for key, value in sorted(image_diag.items()):
        summary_rows.append({"metric": key, "value": value, "notes": "image selection diagnostic"})
    for key, value in sorted(pair_diag.items()):
        summary_rows.append({"metric": key, "value": value, "notes": "pair selection diagnostic"})

    write_csv(SUMMARY_OUT, summary_rows, ["metric", "value", "notes"])


def audit_outputs(paths: list[Path]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for path in paths:
        rows = read_csv(path)
        if rows:
            for header in rows[0].keys():
                lowered = header.lower()
                if any(term in lowered for term in SENSITIVE_HEADER_TERMS):
                    issues.append(f"{path}: sensitive header {header}")
        text = path.read_text(encoding="utf-8")
        for marker in SENSITIVE_VALUE_MARKERS:
            if marker in text:
                issues.append(f"{path}: sensitive value marker {marker}")
    return not issues, issues


def write_qc_report(
    output_paths: list[Path],
    audit_passed: bool,
    audit_issues: list[str],
    image_diag: dict[str, object],
    pair_diag: dict[str, object],
) -> None:
    QC_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "Phase 6 annotation candidate selection audit report",
        "",
        f"seed: {SEED}",
        f"image target: {IMAGE_TARGET}",
        f"pair target: {PAIR_TARGET}",
        "",
        "Outputs:",
    ]
    lines.extend(f"- {path}" for path in output_paths)
    lines.extend(
        [
            "",
            "Image diagnostics:",
        ]
    )
    lines.extend(f"- {key}: {value}" for key, value in sorted(image_diag.items()))
    lines.extend(["", "Pair diagnostics:"])
    lines.extend(f"- {key}: {value}" for key, value in sorted(pair_diag.items()))
    lines.extend(
        [
            "",
            "Known limitations:",
            "- New image candidates do not have PF-ERI visual factor labels yet; hard visual strata must be verified during annotation.",
            "- Image selection uses identity expansion plus lightweight image-quality proxies because blur, occlusion, pattern visibility, and side evidence are not yet human-annotated.",
            "- The image candidate file intentionally excludes raw paths and identity labels, so image-copy preparation must use the internal manifest separately.",
            "- Pair candidates are selected from the existing Phase 5 pair universe, not a full gallery/query universe.",
            "- Same/different labels are used only for aggregate selection summaries and are not exposed row-by-row.",
            "",
            f"Leakage audit: {'PASS' if audit_passed else 'FAIL'}",
        ]
    )
    if audit_issues:
        lines.extend(f"- {issue}" for issue in audit_issues)
    else:
        lines.append("- no sensitive headers or value markers detected in public candidate outputs")
    QC_REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for path in [
        LABELED_IMAGE_TABLE,
        EXPANDED_INTERNAL_TABLE,
        REAL_MANIFEST,
        PHASE5_PAIR_TABLE,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)

    # Loaded for presence and row count validation. Current rows are already in
    # EXPANDED_INTERNAL_TABLE, while new candidates come from REAL_MANIFEST.
    labeled_rows = read_csv(LABELED_IMAGE_TABLE)
    expanded_rows = read_csv(EXPANDED_INTERNAL_TABLE)
    real_manifest = read_csv(REAL_MANIFEST)
    phase5_rows = read_csv(PHASE5_PAIR_TABLE)

    if len(labeled_rows) != len(expanded_rows):
        raise RuntimeError(
            "Expected labeled and expanded tables to describe the same current image set"
        )

    image_rows, image_diag = select_image_candidates(real_manifest, expanded_rows)
    image_duplicate_count = math.ceil(len(image_rows) * DUPLICATE_IMAGE_RATE)
    image_duplicates = stratified_duplicate_rows(
        image_rows,
        bucket_field="selection_bucket",
        duplicate_count=image_duplicate_count,
        id_field="candidate_image_id",
        duplicate_id_field="duplicate_annotation_id",
        duplicate_of_field="duplicate_of_candidate_image_id",
        prefix="phase6_img_dup",
    )

    pair_rows, pair_diag = select_pair_candidates(phase5_rows, expanded_rows)
    pair_duplicates = stratified_duplicate_rows(
        pair_rows,
        bucket_field="selection_bucket",
        duplicate_count=min(len(pair_rows), DUPLICATE_PAIR_MINIMUM),
        id_field="candidate_pair_id",
        duplicate_id_field="duplicate_pair_annotation_id",
        duplicate_of_field="duplicate_of_candidate_pair_id",
        prefix="phase6_pair_dup",
    )

    image_fields = [
        "candidate_image_id",
        "proposed_review_image_filename",
        "annotation_task",
        "selection_bucket",
        "selection_reason",
        "prior_labeled_images_for_identity_count",
        "available_unlabeled_images_for_identity_count",
        "selected_images_for_same_identity_count",
        "manifest_proxy_stratum",
        "image_quality_proxy_stratum",
        "hard_visual_factor_status",
        "visual_factor_status",
        "annotation_round",
        "duplicate_annotation_candidate",
        "candidate_order",
    ]
    image_duplicate_fields = [
        "duplicate_annotation_id",
        "duplicate_of_candidate_image_id",
        *image_fields,
        "duplicate_annotation_round",
    ]
    pair_fields = [
        "candidate_pair_id",
        "image_a_review_filename",
        "image_b_review_filename",
        "annotation_task",
        "selection_bucket",
        "selection_reason",
        "similarity_risk_stratum",
        "visual_eri_band_hint",
        "descriptor_agreement_hint",
        "input_side_comparable_hint",
        "input_visual_issue_hint",
        "pair_side_comparability",
        "pair_visible_pattern_overlap",
        "pair_viewpoint_compatibility",
        "pair_evidence_overlap",
        "pair_review_recommendation",
        "pair_defer_reason",
        "pair_uncertainty_flag",
        "pair_annotation_notes",
        "candidate_order",
    ]
    pair_duplicate_fields = [
        "duplicate_pair_annotation_id",
        "duplicate_of_candidate_pair_id",
        *pair_fields,
        "duplicate_annotation_round",
    ]

    write_csv(IMAGE_CANDIDATES_OUT, image_rows, image_fields)
    write_csv(IMAGE_DUPLICATES_OUT, image_duplicates, image_duplicate_fields)
    write_csv(PAIR_CANDIDATES_OUT, pair_rows, pair_fields)
    write_csv(PAIR_DUPLICATES_OUT, pair_duplicates, pair_duplicate_fields)
    write_summary(image_rows, image_duplicates, pair_rows, pair_duplicates, image_diag, pair_diag)

    output_paths = [
        IMAGE_CANDIDATES_OUT,
        IMAGE_DUPLICATES_OUT,
        PAIR_CANDIDATES_OUT,
        PAIR_DUPLICATES_OUT,
        SUMMARY_OUT,
    ]
    audit_passed, audit_issues = audit_outputs(output_paths)
    write_qc_report(output_paths, audit_passed, audit_issues, image_diag, pair_diag)

    if not audit_passed:
        raise RuntimeError("Sensitive output audit failed; see QC report")

    print("Phase 6 annotation candidate selection complete")
    print(f"image candidates: {len(image_rows)}")
    print(f"image duplicates: {len(image_duplicates)}")
    print(f"pair candidates: {len(pair_rows)}")
    print(f"pair duplicates: {len(pair_duplicates)}")
    print(f"QC report: {QC_REPORT_OUT}")


if __name__ == "__main__":
    main()
