#!/usr/bin/env python3
"""Build the Phase 6 balanced unique-500 v2 annotation workflow."""

from __future__ import annotations

import csv
import hashlib
import random
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

SEED = 20260613
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
IMAGE_PREFIX = "czlx_phase6_v2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

REAL_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_real_manifest.csv"
PHASE4_EXPANDED = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"

REVIEW_IMAGE_DIR = PROJECT_ROOT / f"data/review_images/czechlynx/{WORKFLOW_NAME}"
WORKING_CSV = PROJECT_ROOT / f"data/labels/czechlynx/czechlynx_{WORKFLOW_NAME}_image_annotation_working.csv"
TEMPLATE_CSV = PROJECT_ROOT / f"data/labels/czechlynx/czechlynx_{WORKFLOW_NAME}_image_annotation_template.csv"
INTERNAL_MAPPING_CSV = PROJECT_ROOT / f"data/interim/czechlynx/czechlynx_{WORKFLOW_NAME}_review_mapping_internal.csv"
PACKAGE_ROOT = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}"
QC_SELECTION_REPORT = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_selection_qc_report.txt"
LEAKAGE_REPORT = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_leakage_scan_report.txt"

TARGET_COUNTS = {
    "high_evidence_proxy": 150,
    "medium_evidence_proxy": 175,
    "low_but_annotatable_proxy": 110,
    "extreme_hard_proxy": 65,
}

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

PUBLIC_FIELDS = [
    "expanded_image_id",
    "review_image_path_local",
    "candidate_source_id",
    "candidate_reason",
    "selection_stratum",
    "quality_bucket",
    "batch_id",
    *ANNOTATION_FIELDS,
]

MAPPING_FIELDS = [
    "expanded_image_id",
    "review_image_path_local",
    "candidate_source_id",
    "candidate_reason",
    "selection_stratum",
    "quality_bucket",
    "batch_id",
    "source",
    "date",
    "encounter",
    "unique_name",
    "path",
    "local_image_path",
    "relative_age",
    "coat_pattern",
    "split_pose",
    "mean_luminance",
    "darkness_fraction",
    "bright_fraction",
    "contrast",
    "edge_density",
    "width",
    "height",
    "near_black_flag",
    "eye_shine_only_flag",
    "almost_empty_flag",
]

RESTRICTED_PUBLIC_PATTERNS = [
    "unique_name",
    "/Users/",
    "data/raw",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "location",
    "internal_id",
    "working_id",
    "working_individual_id",
    "true_id",
    "local_image_path",
]

RAW_LYNX_RE = re.compile(r"lynx_[0-9]+", re.IGNORECASE)


def stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def is_yes(value: str) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1"}


def image_metrics(path: str) -> dict[str, object]:
    try:
        image = Image.open(path).convert("L")
        width, height = image.size
        image.thumbnail((160, 160))
        stat = ImageStat.Stat(image)
        pixels = list(image.getdata())
        dark = sum(1 for px in pixels if px < 30) / max(len(pixels), 1)
        bright = sum(1 for px in pixels if px > 225) / max(len(pixels), 1)
        edge_image = image.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edge_image)
        edge_density = float(edge_stat.mean[0])
        mean = float(stat.mean[0])
        contrast = float(stat.stddev[0])
        near_black = mean < 35 or dark > 0.88
        eye_shine_only = dark > 0.80 and 0.001 <= bright <= 0.05 and edge_density < 18
        almost_empty = dark > 0.92 and edge_density < 12
        return {
            "readable": True,
            "mean_luminance": round(mean, 4),
            "darkness_fraction": round(dark, 6),
            "bright_fraction": round(bright, 6),
            "contrast": round(contrast, 4),
            "edge_density": round(edge_density, 4),
            "width": width,
            "height": height,
            "near_black_flag": "yes" if near_black else "no",
            "eye_shine_only_flag": "yes" if eye_shine_only else "no",
            "almost_empty_flag": "yes" if almost_empty else "no",
        }
    except Exception:
        return {
            "readable": False,
            "mean_luminance": 0.0,
            "darkness_fraction": 1.0,
            "bright_fraction": 0.0,
            "contrast": 0.0,
            "edge_density": 0.0,
            "width": 0,
            "height": 0,
            "near_black_flag": "yes",
            "eye_shine_only_flag": "no",
            "almost_empty_flag": "yes",
        }


def classify_quality(metrics: dict[str, object]) -> tuple[str, str]:
    mean = float(metrics["mean_luminance"])
    dark = float(metrics["darkness_fraction"])
    bright = float(metrics["bright_fraction"])
    contrast = float(metrics["contrast"])
    edge = float(metrics["edge_density"])
    near_black = metrics["near_black_flag"] == "yes"
    eye = metrics["eye_shine_only_flag"] == "yes"
    empty = metrics["almost_empty_flag"] == "yes"

    if near_black or eye or empty or bright > 0.55 or (contrast < 12 and edge < 10):
        return (
            "extreme_hard_proxy",
            "extreme visual condition proxy; retained under strict cap for defer/exclude modeling",
        )
    if dark > 0.65 or mean < 55 or mean > 205 or contrast < 24 or edge < 13:
        return (
            "low_but_annotatable_proxy",
            "low-quality but likely annotatable evidence proxy for degradation modeling",
        )
    if dark < 0.25 and 65 <= mean <= 180 and contrast >= 42 and edge >= 20 and bright < 0.25:
        return (
            "high_evidence_proxy",
            "clearer image-quality proxy for normal evidence behavior",
        )
    return (
        "medium_evidence_proxy",
        "medium-quality evidence proxy with moderate degradation or ordinary variation",
    )


def build_candidate_pool() -> list[dict[str, object]]:
    manifest = read_csv(REAL_MANIFEST)
    phase4_paths = {row.get("path", "") for row in read_csv(PHASE4_EXPANDED)}
    by_identity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in manifest:
        if not is_yes(row.get("image_exists", "")):
            continue
        if row.get("path", "") in phase4_paths:
            continue
        identity = row.get("unique_name", "").strip()
        if not identity:
            continue
        by_identity[identity].append(row)

    sampled_rows: list[dict[str, str]] = []
    for identity, rows in by_identity.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r.get("encounter", ""),
                r.get("date", ""),
                stable_hash(r.get("path", "")),
            ),
        )
        sampled_rows.extend(rows_sorted[:36])

    pool: list[dict[str, object]] = []
    for row in sampled_rows:
        metrics = image_metrics(row.get("local_image_path", ""))
        if not metrics["readable"]:
            continue
        bucket, reason = classify_quality(metrics)
        out: dict[str, object] = dict(row)
        out.update(metrics)
        out["quality_bucket"] = bucket
        out["candidate_reason"] = reason
        out["selection_stratum"] = f"{bucket}__{row.get('coat_pattern') or 'coat_unknown'}__pose_{row.get('split-pose') or 'unmarked'}"
        out["identity_key_internal"] = row.get("unique_name", "")
        out["encounter_key_internal"] = row.get("encounter", "")
        pool.append(out)
    return pool


def select_balanced(pool: list[dict[str, object]]) -> list[dict[str, object]]:
    rng = random.Random(SEED)
    selected: list[dict[str, object]] = []
    selected_paths: set[str] = set()
    identity_counts: Counter[str] = Counter()
    encounter_counts: Counter[str] = Counter()

    def add_from_bucket(bucket: str, target: int) -> None:
        candidates = [row for row in pool if row["quality_bucket"] == bucket]
        candidates.sort(
            key=lambda r: (
                identity_counts[str(r["identity_key_internal"])],
                encounter_counts[str(r["encounter_key_internal"])],
                stable_hash(str(r.get("path", ""))),
            )
        )
        for row in candidates:
            if len([item for item in selected if item["quality_bucket"] == bucket]) >= target:
                break
            if str(row.get("path", "")) in selected_paths:
                continue
            identity = str(row["identity_key_internal"])
            encounter = str(row["encounter_key_internal"])
            if identity_counts[identity] >= 4:
                continue
            if encounter and encounter_counts[encounter] >= 2:
                continue
            selected.append(row)
            selected_paths.add(str(row.get("path", "")))
            identity_counts[identity] += 1
            encounter_counts[encounter] += 1

        if len([item for item in selected if item["quality_bucket"] == bucket]) < target:
            remaining = [row for row in candidates if str(row.get("path", "")) not in selected_paths]
            rng.shuffle(remaining)
            for row in remaining:
                if len([item for item in selected if item["quality_bucket"] == bucket]) >= target:
                    break
                identity = str(row["identity_key_internal"])
                if identity_counts[identity] >= 5:
                    continue
                selected.append(row)
                selected_paths.add(str(row.get("path", "")))
                identity_counts[identity] += 1
                encounter_counts[str(row["encounter_key_internal"])] += 1

    for bucket, target in TARGET_COUNTS.items():
        add_from_bucket(bucket, target)

    if len(selected) != 500:
        counts = Counter(str(row["quality_bucket"]) for row in selected)
        raise RuntimeError(f"Unable to select 500 balanced images; got {len(selected)} {counts}")
    return selected


def assign_batches(selected: list[dict[str, object]]) -> list[dict[str, object]]:
    by_bucket: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in selected:
        by_bucket[str(row["quality_bucket"])].append(row)
    for rows in by_bucket.values():
        rows.sort(key=lambda r: stable_hash(str(r.get("path", ""))))

    batch_plan = []
    for batch_index in range(10):
        batch_plan.append(
            {
                "high_evidence_proxy": 15,
                "medium_evidence_proxy": 18 if batch_index < 5 else 17,
                "low_but_annotatable_proxy": 11,
                "extreme_hard_proxy": 6 if batch_index < 5 else 7,
            }
        )

    ordered: list[dict[str, object]] = []
    for batch_index, plan in enumerate(batch_plan, start=1):
        batch_id = f"batch_{batch_index:03d}"
        batch_rows: list[dict[str, object]] = []
        for bucket, count in plan.items():
            chunk = by_bucket[bucket][:count]
            by_bucket[bucket] = by_bucket[bucket][count:]
            batch_rows.extend(chunk)
        batch_rows.sort(key=lambda r: (str(r["quality_bucket"]), stable_hash(str(r.get("path", "")))))
        for row in batch_rows:
            row["batch_id"] = batch_id
            ordered.append(row)
    return ordered


def prepare_dirs() -> None:
    for path in [REVIEW_IMAGE_DIR, PACKAGE_ROOT]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    for path in [
        WORKING_CSV.parent,
        TEMPLATE_CSV.parent,
        INTERNAL_MAPPING_CSV.parent,
        QC_SELECTION_REPORT.parent,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def copy_review_image(source: str, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    image.save(target, format="JPEG", quality=95)


def make_rows(selected: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    public_rows: list[dict[str, object]] = []
    mapping_rows: list[dict[str, object]] = []
    for index, row in enumerate(selected):
        image_id = f"{IMAGE_PREFIX}_{index:04d}"
        filename = f"{image_id}.jpg"
        review_rel = f"data/review_images/czechlynx/{WORKFLOW_NAME}/{filename}"
        copy_review_image(str(row["local_image_path"]), PROJECT_ROOT / review_rel)
        public = {
            "expanded_image_id": image_id,
            "review_image_path_local": review_rel,
            "candidate_source_id": image_id,
            "candidate_reason": row["candidate_reason"],
            "selection_stratum": row["selection_stratum"],
            "quality_bucket": row["quality_bucket"],
            "batch_id": row["batch_id"],
            "annotation_status": "pending",
        }
        for field in ANNOTATION_FIELDS:
            public.setdefault(field, "")
        public["annotation_status"] = "pending"
        public_rows.append(public)

        mapping = dict(public)
        mapping.update(
            {
                "source": row.get("source", ""),
                "date": row.get("date", ""),
                "encounter": row.get("encounter", ""),
                "unique_name": row.get("unique_name", ""),
                "path": row.get("path", ""),
                "local_image_path": row.get("local_image_path", ""),
                "relative_age": row.get("relative_age", ""),
                "coat_pattern": row.get("coat_pattern", ""),
                "split_pose": row.get("split-pose", ""),
                "mean_luminance": row.get("mean_luminance", ""),
                "darkness_fraction": row.get("darkness_fraction", ""),
                "bright_fraction": row.get("bright_fraction", ""),
                "contrast": row.get("contrast", ""),
                "edge_density": row.get("edge_density", ""),
                "width": row.get("width", ""),
                "height": row.get("height", ""),
                "near_black_flag": row.get("near_black_flag", ""),
                "eye_shine_only_flag": row.get("eye_shine_only_flag", ""),
                "almost_empty_flag": row.get("almost_empty_flag", ""),
            }
        )
        mapping_rows.append(mapping)
    return public_rows, mapping_rows


def write_batch_protocol(path: Path, range_id: str) -> None:
    path.write_text(
        f"""# Phase 6 Unique-500 v2 Batch Review Protocol

Expected range ID:

```text
{range_id}
```

Expected returned files:

```text
{range_id}_annotated.csv
{range_id}_needs_review.csv
{range_id}_needs_review_streamlit.zip
{range_id}_annotation_results.zip
```

Review each image for visual evidence quality only. Do not try to identify the individual animal.

Use `complete` when you have approximately 75 percent confidence in the visual-factor labels, even if the image is poor.

Use `needs_review` only when the annotation itself is unstable or ambiguous. Low image quality alone is not `needs_review`.

Save the completed `batch_annotation_template.csv` using the expected range name before returning it.
""",
        encoding="utf-8",
    )


def make_batches(public_rows: list[dict[str, object]]) -> None:
    batches_root = PACKAGE_ROOT / "batches"
    zips_root = PACKAGE_ROOT / "batch_zips"
    batches_root.mkdir(parents=True, exist_ok=True)
    zips_root.mkdir(parents=True, exist_ok=True)
    for batch_id, rows in sorted(group_by(public_rows, "batch_id").items()):
        batch_dir = batches_root / batch_id
        image_dir = batch_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            src = PROJECT_ROOT / str(row["review_image_path_local"])
            dst = image_dir / Path(str(row["review_image_path_local"])).name
            shutil.copy2(src, dst)
        batch_number = int(batch_id.split("_")[1])
        start = (batch_number - 1) * 50
        end = start + 49
        range_id = f"range_{start:03d}_{end:03d}"
        write_csv(batch_dir / "batch_manifest.csv", rows, PUBLIC_FIELDS[:7])
        write_csv(batch_dir / "batch_annotation_template.csv", rows, PUBLIC_FIELDS)
        write_batch_protocol(batch_dir / "batch_review_protocol.md", range_id)
        qc_lines = [
            f"batch_id: {batch_id}",
            f"range_id: {range_id}",
            f"image_count: {len(rows)}",
            f"quality_distribution: {dict(Counter(str(r['quality_bucket']) for r in rows))}",
            f"extreme_hard_count: {sum(1 for r in rows if r['quality_bucket'] == 'extreme_hard_proxy')}",
            "sensitive_fields_in_public_files: no",
        ]
        (batch_dir / "qc_report.txt").write_text("\n".join(qc_lines) + "\n", encoding="utf-8")
        zip_path = zips_root / f"{batch_id}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in sorted(batch_dir.rglob("*")):
                if file.is_file():
                    zf.write(file, file.relative_to(batch_dir))


def group_by(rows: list[dict[str, object]], key: str) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return grouped


def setup_assisted_workspace(public_rows: list[dict[str, object]]) -> None:
    root = PACKAGE_ROOT / "assisted_annotation_workspace"
    for subdir in [
        "assisted_working",
        "incoming_from_downloads",
        "corrections_from_streamlit",
        "imported_ranges",
        "needs_review_index",
        "qc",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    assisted = root / "assisted_working" / f"czechlynx_{WORKFLOW_NAME}_assisted_working.csv"
    summary = root / "assisted_working" / f"czechlynx_{WORKFLOW_NAME}_working_summary.csv"
    rows = []
    for row in public_rows:
        out = dict(row)
        out["imported_range_id"] = ""
        out["correction_applied"] = "no"
        rows.append(out)
    write_csv(assisted, rows, [*PUBLIC_FIELDS, "imported_range_id", "correction_applied"])
    write_csv(summary, rows, [*PUBLIC_FIELDS, "imported_range_id", "correction_applied"])


def leakage_scan(paths: list[Path]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for path in paths:
        if path.is_dir():
            files = [item for item in path.rglob("*") if item.is_file()]
        else:
            files = [path]
        for file in files:
            rel = file.relative_to(PROJECT_ROOT).as_posix()
            if RAW_LYNX_RE.search(rel):
                issues.append(f"filename: {rel}")
            for pattern in RESTRICTED_PUBLIC_PATTERNS:
                if pattern.lower() in rel.lower():
                    issues.append(f"filename: {rel}")
            if file.suffix.lower() in {".csv", ".md", ".txt"}:
                text = file.read_text(encoding="utf-8", errors="ignore")
                if RAW_LYNX_RE.search(text):
                    issues.append(f"text: {rel}")
                    continue
                for pattern in RESTRICTED_PUBLIC_PATTERNS:
                    if pattern.lower() in text.lower():
                        issues.append(f"text: {rel}")
                        break
    return not issues, issues


def write_reports(public_rows: list[dict[str, object]], mapping_rows: list[dict[str, object]], pool: list[dict[str, object]]) -> None:
    overall = Counter(str(row["quality_bucket"]) for row in public_rows)
    batch_lines = []
    for batch_id, rows in sorted(group_by(public_rows, "batch_id").items()):
        counts = Counter(str(row["quality_bucket"]) for row in rows)
        batch_lines.append(f"- {batch_id}: {dict(counts)}")
    near_black_by_batch = {}
    mapping_by_id = {row["expanded_image_id"]: row for row in mapping_rows}
    for batch_id, rows in sorted(group_by(public_rows, "batch_id").items()):
        near_black_by_batch[batch_id] = sum(
            1
            for row in rows
            if mapping_by_id[row["expanded_image_id"]]["near_black_flag"] == "yes"
            or mapping_by_id[row["expanded_image_id"]]["eye_shine_only_flag"] == "yes"
            or mapping_by_id[row["expanded_image_id"]]["almost_empty_flag"] == "yes"
        )

    public_scan_paths = [
        WORKING_CSV,
        TEMPLATE_CSV,
        REVIEW_IMAGE_DIR,
        PACKAGE_ROOT / "batches",
        PACKAGE_ROOT / "batch_zips",
        PACKAGE_ROOT / "assisted_annotation_workspace",
    ]
    passed, issues = leakage_scan(public_scan_paths)
    LEAKAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LEAKAGE_REPORT.write_text(
        "\n".join(
            [
                "Phase 6 unique-500 v2 balanced leakage scan",
                "",
                f"result: {'PASS' if passed else 'FAIL'}",
                *(["issues:"] + [f"- {issue}" for issue in issues] if issues else ["No restricted patterns found in public v2 outputs."]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    QC_SELECTION_REPORT.write_text(
        "\n".join(
            [
                "Phase 6 unique-500 v2 balanced selection QC report",
                "",
                f"candidate_pool_size: {len(pool)}",
                f"selected_rows: {len(public_rows)}",
                f"copied_images: {len(list(REVIEW_IMAGE_DIR.glob('*.jpg')))}",
                f"batch_count: {len(group_by(public_rows, 'batch_id'))}",
                f"overall_quality_distribution: {dict(overall)}",
                f"near_black_or_empty_overall: {sum(near_black_by_batch.values())}",
                f"near_black_or_empty_by_batch: {near_black_by_batch}",
                "batch_quality_distribution:",
                *batch_lines,
                f"leakage_scan_passed: {'yes' if passed else 'no'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if not passed:
        raise RuntimeError("Leakage scan failed; see report")


def main() -> None:
    random.seed(SEED)
    prepare_dirs()
    pool = build_candidate_pool()
    selected = select_balanced(pool)
    ordered = assign_batches(selected)
    public_rows, mapping_rows = make_rows(ordered)
    write_csv(WORKING_CSV, public_rows, PUBLIC_FIELDS)
    write_csv(TEMPLATE_CSV, public_rows, PUBLIC_FIELDS)
    write_csv(INTERNAL_MAPPING_CSV, mapping_rows, MAPPING_FIELDS)
    make_batches(public_rows)
    setup_assisted_workspace(public_rows)
    write_reports(public_rows, mapping_rows, pool)
    print("Phase 6 unique-500 v2 balanced workflow built")
    print(f"selected_rows: {len(public_rows)}")
    print(f"overall_quality_distribution: {dict(Counter(str(row['quality_bucket']) for row in public_rows))}")
    for batch_id, rows in sorted(group_by(public_rows, "batch_id").items()):
        print(batch_id, dict(Counter(str(row["quality_bucket"]) for row in rows)))


if __name__ == "__main__":
    main()
