#!/usr/bin/env python3
"""Create the Phase 6 image-level annotation review package.

The package is designed for blinded human annotation. It copies candidate
images to neutral filenames, mixes duplicate-review entries into normal
batches, and writes a small local Streamlit app for annotation.
"""

from __future__ import annotations

import csv
import random
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_select_additional_annotation_candidates import (  # noqa: E402
    EXPANDED_INTERNAL_TABLE,
    LABELED_IMAGE_TABLE,
    REAL_MANIFEST,
    SEED,
    read_csv,
    select_image_candidates,
)

PACKAGE_ROOT = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_review_packages/phase6_image_level_review_package"
)
ZIP_OUT = PACKAGE_ROOT.with_suffix(".zip")

CANDIDATE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_candidates/phase6_additional_image_annotation_candidates.csv"
)
DUPLICATE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_candidates/phase6_image_duplicate_annotation_subset.csv"
)

BATCH_SIZE = 50
EXPECTED_CANDIDATES = 500
EXPECTED_DUPLICATES = 100
EXPECTED_REVIEW_ENTRIES = 600

RESTRICTED_PATTERNS = [
    "unique_name",
    "lynx_",
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
    "review_image_path",
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

ALLOWED_VALUES = {
    "pattern_visibility": ["", "high", "medium", "low", "none", "unknown"],
    "side_visibility": ["", "left", "right", "both", "frontal", "rear", "unknown"],
    "side_evidence_quality": ["", "high", "medium", "low", "none", "unknown"],
    "body_fraction_visible": ["", "0_25", "26_50", "51_75", "76_100", "unknown"],
    "partial_body": ["", "yes", "no", "unknown"],
    "frontal_or_rear_view": ["", "yes", "no", "unknown"],
    "silhouette_only": ["", "yes", "no", "unknown"],
    "blur_level": ["", "none", "mild", "moderate", "severe", "unknown"],
    "occlusion_level": ["", "none", "mild", "moderate", "severe", "unknown"],
    "lighting_condition": [
        "",
        "daylight",
        "low_light",
        "mixed",
        "night_ir",
        "overexposed",
        "underexposed",
        "unknown",
    ],
    "night_ir_artifact": ["", "none", "mild", "moderate", "severe", "not_applicable", "unknown"],
    "contrast_level": ["", "high", "medium", "low", "unknown"],
    "primary_limiting_factor": [
        "",
        "none",
        "blur",
        "occlusion",
        "lighting_ir",
        "low_pattern_visibility",
        "side_not_comparable",
        "partial_body",
        "frontal_rear_view",
        "silhouette_only",
        "overexposure",
        "underexposure",
        "multiple",
        "unknown",
    ],
    "uncertainty_flag": ["", "yes", "no"],
    "annotation_status": ["", "not_started", "in_progress", "complete", "needs_review"],
}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def source_lookup_from_selection() -> dict[str, str]:
    expanded_rows = read_csv(PROJECT_ROOT / EXPANDED_INTERNAL_TABLE)
    real_manifest = read_csv(PROJECT_ROOT / REAL_MANIFEST)
    _ = read_csv(PROJECT_ROOT / LABELED_IMAGE_TABLE)
    selected_rows, _ = select_image_candidates(real_manifest, expanded_rows)
    lookup: dict[str, str] = {}
    for row in selected_rows:
        candidate_id = str(row["candidate_image_id"])
        source_path = str(row.get("_source_local_image_path", ""))
        if source_path:
            lookup[candidate_id] = source_path
    return lookup


def make_review_entries(
    candidate_rows: list[dict[str, str]],
    duplicate_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_candidate = {row["candidate_image_id"]: row for row in candidate_rows}
    duplicate_source_ids = [row["duplicate_of_candidate_image_id"] for row in duplicate_rows]

    originals = [
        {
            "source_candidate_id": row["candidate_image_id"],
            "entry_type": "primary",
            "candidate_reason": row["selection_reason"],
            "selection_stratum": row["selection_bucket"],
            "neutral_image_id": row["candidate_image_id"],
        }
        for row in candidate_rows
    ]
    duplicates = [
        {
            "source_candidate_id": candidate_id,
            "entry_type": "duplicate",
            "candidate_reason": by_candidate[candidate_id]["selection_reason"],
            "selection_stratum": by_candidate[candidate_id]["selection_bucket"],
            "neutral_image_id": by_candidate[candidate_id]["candidate_image_id"],
        }
        for candidate_id in duplicate_source_ids
    ]

    rng = random.Random(SEED)
    rng.shuffle(originals)
    rng.shuffle(duplicates)

    batch_count = EXPECTED_REVIEW_ENTRIES // BATCH_SIZE
    batches: list[list[dict[str, object]]] = [[] for _ in range(batch_count)]

    for idx, entry in enumerate(duplicates):
        batches[idx % batch_count].append(entry)
    for entry in originals:
        target_batch = min(range(batch_count), key=lambda i: len(batches[i]))
        batches[target_batch].append(entry)

    review_rows: list[dict[str, object]] = []
    duplicate_key_rows: list[dict[str, object]] = []
    original_entry_by_candidate: dict[str, str] = {}
    original_neutral_by_candidate: dict[str, str] = {}
    review_counter = 1

    for batch_index, batch_entries in enumerate(batches, start=1):
        rng.shuffle(batch_entries)
        batch_id = f"batch_{batch_index:03d}"
        for entry in batch_entries:
            review_entry_id = f"review_{review_counter:06d}"
            public_neutral_image_id = f"neutral_img_{review_counter:06d}"
            filename = f"img_review_{review_counter:06d}.jpg"
            relative_path = f"images/{batch_id}/{filename}"
            public_row = {
                "review_entry_id": review_entry_id,
                "batch_id": batch_id,
                "review_image_filename": filename,
                "relative_image_path": relative_path,
                "candidate_reason": entry["candidate_reason"],
                "annotation_status": "not_started",
                "neutral_image_id": public_neutral_image_id,
                "selection_stratum": entry["selection_stratum"],
                "review_notes": "",
                "_source_candidate_id": entry["source_candidate_id"],
                "_entry_type": entry["entry_type"],
            }
            review_rows.append(public_row)
            if entry["entry_type"] == "primary":
                original_entry_by_candidate[str(entry["source_candidate_id"])] = review_entry_id
                original_neutral_by_candidate[str(entry["source_candidate_id"])] = public_neutral_image_id
            review_counter += 1

    for row in review_rows:
        if row["_entry_type"] != "duplicate":
            continue
        source_candidate_id = str(row["_source_candidate_id"])
        duplicate_key_rows.append(
            {
                "notice": "INTERNAL ONLY - DO NOT USE DURING ANNOTATION.",
                "duplicate_review_entry_id": row["review_entry_id"],
                "duplicate_review_image_filename": row["review_image_filename"],
                "duplicate_batch_id": row["batch_id"],
                "original_review_entry_id": original_entry_by_candidate.get(source_candidate_id, ""),
                "duplicate_public_neutral_image_id": row["neutral_image_id"],
                "original_public_neutral_image_id": original_neutral_by_candidate.get(
                    source_candidate_id, ""
                ),
            }
        )

    return review_rows, duplicate_key_rows


def copy_or_convert_image(source_path: str, target_path: Path) -> bool:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    if not source.exists():
        return False
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        shutil.copy2(source, target_path)
    else:
        image = Image.open(source).convert("RGB")
        image.save(target_path, format="JPEG", quality=95)
    return True


def write_streamlit_app() -> None:
    app_path = PACKAGE_ROOT / "streamlit/streamlit_image_review_app.py"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text(
        '''#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import streamlit as st

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PACKAGE_ROOT / "manifests/image_annotation_template.csv"
MANIFEST_PATH = PACKAGE_ROOT / "manifests/image_review_manifest.csv"
WORKING_PATH = PACKAGE_ROOT / "image_annotation_working.csv"

ALLOWED_VALUES = {
    "pattern_visibility": ["", "high", "medium", "low", "none", "unknown"],
    "side_visibility": ["", "left", "right", "both", "frontal", "rear", "unknown"],
    "side_evidence_quality": ["", "high", "medium", "low", "none", "unknown"],
    "body_fraction_visible": ["", "0_25", "26_50", "51_75", "76_100", "unknown"],
    "partial_body": ["", "yes", "no", "unknown"],
    "frontal_or_rear_view": ["", "yes", "no", "unknown"],
    "silhouette_only": ["", "yes", "no", "unknown"],
    "blur_level": ["", "none", "mild", "moderate", "severe", "unknown"],
    "occlusion_level": ["", "none", "mild", "moderate", "severe", "unknown"],
    "lighting_condition": ["", "daylight", "low_light", "mixed", "night_ir", "overexposed", "underexposed", "unknown"],
    "night_ir_artifact": ["", "none", "mild", "moderate", "severe", "not_applicable", "unknown"],
    "contrast_level": ["", "high", "medium", "low", "unknown"],
    "primary_limiting_factor": ["", "none", "blur", "occlusion", "lighting_ir", "low_pattern_visibility", "side_not_comparable", "partial_body", "frontal_rear_view", "silhouette_only", "overexposure", "underexposure", "multiple", "unknown"],
    "uncertainty_flag": ["", "yes", "no"],
    "annotation_status": ["", "not_started", "in_progress", "complete", "needs_review"],
}

st.set_page_config(page_title="Phase 6 Image Review", layout="wide")
st.title("Phase 6 Image-Level Evidence Review")

if WORKING_PATH.exists():
    data = pd.read_csv(WORKING_PATH).fillna("")
else:
    data = pd.read_csv(TEMPLATE_PATH).fillna("")

manifest = pd.read_csv(MANIFEST_PATH).fillna("")
path_by_entry = dict(zip(manifest["review_entry_id"], manifest["relative_image_path"]))

batches = sorted(data["batch_id"].unique())
selected_batch = st.sidebar.selectbox("Batch", batches)
batch_data = data[data["batch_id"] == selected_batch].reset_index(drop=True)

complete_count = int((data["annotation_status"] == "complete").sum())
st.sidebar.metric("Completed", f"{complete_count} / {len(data)}")

entry_labels = [
    f"{row.review_entry_id} - {row.review_image_filename}"
    for row in batch_data.itertuples(index=False)
]
selected_label = st.sidebar.selectbox("Image", entry_labels)
selected_entry_id = selected_label.split(" - ")[0]
row_index = data.index[data["review_entry_id"] == selected_entry_id][0]
row = data.loc[row_index].copy()

image_path = PACKAGE_ROOT / path_by_entry[selected_entry_id]
left, right = st.columns([3, 2])
with left:
    st.image(str(image_path), caption=f"{row['review_entry_id']} | {row['batch_id']}", use_container_width=True)

with right:
    with st.form("annotation_form"):
        updates = {}
        for field, options in ALLOWED_VALUES.items():
            current = row.get(field, "")
            index = options.index(current) if current in options else 0
            updates[field] = st.selectbox(field, options, index=index)
        updates["annotator_notes"] = st.text_area("annotator_notes", value=row.get("annotator_notes", ""), height=120)
        submitted = st.form_submit_button("Save annotation")
        if submitted:
            for field, value in updates.items():
                data.at[row_index, field] = value
            data.to_csv(WORKING_PATH, index=False)
            st.success(f"Saved to {WORKING_PATH.name}")

st.caption("Duplicate review entries are intentionally blinded. Do not use internal package files during annotation.")
''',
        encoding="utf-8",
    )

    instructions_path = PACKAGE_ROOT / "streamlit/streamlit_run_instructions.md"
    instructions_path.write_text(
        """# Streamlit Run Instructions

From a terminal:

```bash
cd /path/to/phase6_image_level_review_package
streamlit run streamlit/streamlit_image_review_app.py
```

The app saves progress to:

```text
image_annotation_working.csv
```

Return the completed working CSV to the project after review. Do not open the internal duplicate key during annotation.
""",
        encoding="utf-8",
    )


def write_docs() -> None:
    docs_dir = PACKAGE_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    schema_lines = [
        "# Image Annotation Schema",
        "",
        "Use the dropdown values in the Streamlit app. Leave a value blank only when the field has not yet been reviewed.",
        "",
    ]
    definitions = {
        "pattern_visibility": "Visibility of diagnostic coat pattern.",
        "side_visibility": "Main visible body side or non-side view.",
        "side_evidence_quality": "How useful the visible side is for patterned-felid review.",
        "body_fraction_visible": "Approximate visible body fraction.",
        "partial_body": "Whether only part of the animal is visible.",
        "frontal_or_rear_view": "Whether the image is mainly frontal or rear.",
        "silhouette_only": "Whether the animal is mainly a silhouette.",
        "blur_level": "Motion or focus blur severity.",
        "occlusion_level": "Vegetation, objects, or scene occlusion severity.",
        "lighting_condition": "Primary lighting condition.",
        "night_ir_artifact": "IR artifact severity, or not applicable.",
        "contrast_level": "Overall contrast for visible pattern review.",
        "primary_limiting_factor": "Main reason evidence is limited.",
        "uncertainty_flag": "Use yes when the annotation is uncertain.",
        "annotation_status": "Progress marker for the current row.",
        "annotator_notes": "Optional short reviewer notes.",
    }
    for field in ANNOTATION_FIELDS:
        values = ", ".join(ALLOWED_VALUES.get(field, ["free_text"]))
        schema_lines.extend([f"## {field}", "", definitions[field], "", f"Allowed values: `{values}`", ""])
    (docs_dir / "image_annotation_schema.md").write_text("\n".join(schema_lines), encoding="utf-8")

    (docs_dir / "review_protocol.md").write_text(
        """# Review Protocol

Review one image at a time.

Do not try to identify the individual animal. Focus only on evidence quality factors for patterned-felid Re-ID review.

Repeat-review images are mixed into the normal batches for reliability checking. They are intentionally blinded. Do not open the internal duplicate key during annotation.

Use the Streamlit app dropdowns for categorical fields and notes only when needed.

Save progress frequently. The app writes progress to `image_annotation_working.csv`.

After review, return the completed working CSV to the project.
""",
        encoding="utf-8",
    )


def write_manifests(
    public_rows: list[dict[str, object]],
    duplicate_key_rows: list[dict[str, object]],
) -> tuple[Counter[str], int]:
    manifest_dir = PACKAGE_ROOT / "manifests"
    public_fields = [
        "review_entry_id",
        "batch_id",
        "review_image_filename",
        "relative_image_path",
        "candidate_reason",
        "annotation_status",
        "neutral_image_id",
        "selection_stratum",
        "review_notes",
    ]
    write_csv(manifest_dir / "image_review_manifest.csv", public_rows, public_fields)

    template_fields = [
        "review_entry_id",
        "batch_id",
        "review_image_filename",
        "relative_image_path",
        *ANNOTATION_FIELDS,
    ]
    template_rows = [
        {
            "review_entry_id": row["review_entry_id"],
            "batch_id": row["batch_id"],
            "review_image_filename": row["review_image_filename"],
            "relative_image_path": row["relative_image_path"],
            "annotation_status": "not_started",
        }
        for row in public_rows
    ]
    write_csv(manifest_dir / "image_annotation_template.csv", template_rows, template_fields)

    duplicate_fields = [
        "notice",
        "duplicate_review_entry_id",
        "duplicate_review_image_filename",
        "duplicate_batch_id",
        "original_review_entry_id",
        "duplicate_public_neutral_image_id",
        "original_public_neutral_image_id",
    ]
    write_csv(manifest_dir / "image_duplicate_key_internal.csv", duplicate_key_rows, duplicate_fields)

    batch_counts = Counter(str(row["batch_id"]) for row in public_rows)
    batch_summary_rows = [
        {"batch_id": batch_id, "review_entry_count": count}
        for batch_id, count in sorted(batch_counts.items())
    ]
    write_csv(manifest_dir / "image_batch_summary.csv", batch_summary_rows, ["batch_id", "review_entry_count"])
    return batch_counts, len(template_rows)


def leakage_scan() -> tuple[bool, list[str]]:
    issues: list[str] = []
    scan_suffixes = {".csv", ".md", ".py", ".txt"}
    for path in PACKAGE_ROOT.rglob("*"):
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        for pattern in RESTRICTED_PATTERNS:
            if pattern.lower() in rel.lower():
                issues.append(f"filename: {rel}")
        if path.is_file() and path.suffix.lower() in scan_suffixes:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in RESTRICTED_PATTERNS:
                if pattern.lower() in text.lower():
                    issues.append(f"text: {rel}")
                    break
    return not issues, issues


def write_qc(
    original_count: int,
    duplicate_count: int,
    review_count: int,
    batch_counts: Counter[str],
    copied_count: int,
    missing_sources: list[str],
    manifest_rows: int,
    duplicate_key_count: int,
    leakage_passed: bool,
    leakage_issues: list[str],
) -> None:
    qc_dir = PACKAGE_ROOT / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    duplicate_batches = sorted({issue["duplicate_batch_id"] for issue in read_csv(PACKAGE_ROOT / "manifests/image_duplicate_key_internal.csv")})
    lines = [
        "Phase 6 image-level review package QC report",
        "",
        f"original candidates loaded: {original_count}",
        f"duplicate candidates loaded: {duplicate_count}",
        f"review entries created: {review_count}",
        f"number of batches: {len(batch_counts)}",
        f"batch size distribution: {dict(sorted(Counter(batch_counts.values()).items()))}",
        f"images copied: {copied_count}",
        f"missing images: {len(missing_sources)}",
        f"public review manifest rows: {manifest_rows}",
        f"annotation template rows: {manifest_rows}",
        f"duplicate key rows: {duplicate_key_count}",
        f"duplicates mixed into normal batches: {'yes' if len(duplicate_batches) == len(batch_counts) else 'no'}",
        "public manifest hides duplicate flags: yes",
        f"leakage scan passed: {'yes' if leakage_passed else 'no'}",
    ]
    if missing_sources:
        lines.append("missing image neutral IDs:")
        lines.extend(f"- {item}" for item in missing_sources)
    (qc_dir / "package_qc_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    scan_lines = [
        "Phase 6 image-level review package leakage scan",
        "",
        f"result: {'PASS' if leakage_passed else 'FAIL'}",
    ]
    if leakage_issues:
        scan_lines.append("issues:")
        scan_lines.extend(f"- {issue}" for issue in leakage_issues)
    else:
        scan_lines.append("No restricted patterns were found in package text files or package filenames.")
    (qc_dir / "leakage_scan_report.txt").write_text("\n".join(scan_lines) + "\n", encoding="utf-8")


def create_zip() -> None:
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(PACKAGE_ROOT.parent))


def write_project_doc(
    review_count: int,
    batch_count: int,
    duplicate_key_count: int,
    leakage_passed: bool,
) -> None:
    doc_path = PROJECT_ROOT / "docs/phase6/phase6_image_review_package_creation_results.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        f"""# Phase 6 Image Review Package Creation Results

## Purpose

This package was created to support human image-level annotation for the 500 new CzechLynx candidates selected for PF-ERI Control data expansion. It is a packaging step only.

## Inputs Used

- `outputs/czechlynx/phase6/annotation_candidates/phase6_additional_image_annotation_candidates.csv`
- `outputs/czechlynx/phase6/annotation_candidates/phase6_image_duplicate_annotation_subset.csv`
- internal CzechLynx image tables for safe source-image lookup

## Package Paths

Package directory:

```text
{PACKAGE_ROOT.relative_to(PROJECT_ROOT)}
```

ZIP package:

```text
{ZIP_OUT.relative_to(PROJECT_ROOT)}
```

## Row Counts

- original image candidates: {EXPECTED_CANDIDATES}
- duplicate-review entries: {EXPECTED_DUPLICATES}
- total review entries: {review_count}
- batches: {batch_count}
- duplicate key rows: {duplicate_key_count}

## Duplicate Mixing Design

Duplicate-review entries were copied as separate neutral review files and mixed into the normal 50-entry batches. The public review manifest does not include a duplicate flag. The internal duplicate key is stored separately and should not be opened during annotation.

## Streamlit Use

From inside the unzipped package:

```bash
streamlit run streamlit/streamlit_image_review_app.py
```

The app saves progress to `image_annotation_working.csv`.

## QC Result

The package QC report was written to:

```text
qc/package_qc_report.txt
```

Leakage scan result: {'PASS' if leakage_passed else 'FAIL'}.

## Limitations

- This package does not train a model or change PF-ERI scores.
- Image-quality proxy strata are sampling aids only.
- The internal duplicate key must not be used during annotation.
- The completed working CSV must be returned before reliability analysis can proceed.
""",
        encoding="utf-8",
    )


def main() -> None:
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)

    candidate_rows = read_csv(CANDIDATE_CSV)
    duplicate_rows = read_csv(DUPLICATE_CSV)
    if len(candidate_rows) != EXPECTED_CANDIDATES:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATES} candidates, found {len(candidate_rows)}")
    if len(duplicate_rows) != EXPECTED_DUPLICATES:
        raise RuntimeError(f"Expected {EXPECTED_DUPLICATES} duplicates, found {len(duplicate_rows)}")

    source_lookup = source_lookup_from_selection()
    review_rows, duplicate_key_rows = make_review_entries(candidate_rows, duplicate_rows)

    copied_count = 0
    missing_sources: list[str] = []
    for row in review_rows:
        source_path = source_lookup.get(str(row["_source_candidate_id"]), "")
        target_path = PACKAGE_ROOT / str(row["relative_image_path"])
        if copy_or_convert_image(source_path, target_path):
            copied_count += 1
        else:
            missing_sources.append(str(row["neutral_image_id"]))

    if missing_sources:
        review_rows = [
            row for row in review_rows if str(row["neutral_image_id"]) not in set(missing_sources)
        ]

    public_rows = [{k: v for k, v in row.items() if not k.startswith("_")} for row in review_rows]
    batch_counts, manifest_rows = write_manifests(public_rows, duplicate_key_rows)
    write_streamlit_app()
    write_docs()

    leakage_passed, leakage_issues = leakage_scan()
    write_qc(
        original_count=len(candidate_rows),
        duplicate_count=len(duplicate_rows),
        review_count=len(public_rows),
        batch_counts=batch_counts,
        copied_count=copied_count,
        missing_sources=missing_sources,
        manifest_rows=manifest_rows,
        duplicate_key_count=len(duplicate_key_rows),
        leakage_passed=leakage_passed,
        leakage_issues=leakage_issues,
    )

    if len(public_rows) != EXPECTED_REVIEW_ENTRIES:
        raise RuntimeError(f"Expected {EXPECTED_REVIEW_ENTRIES} review entries, found {len(public_rows)}")
    if len(batch_counts) != EXPECTED_REVIEW_ENTRIES // BATCH_SIZE:
        raise RuntimeError("Unexpected batch count")
    if any(count != BATCH_SIZE for count in batch_counts.values()):
        raise RuntimeError("Unexpected batch size distribution")
    if not leakage_passed:
        raise RuntimeError("Package leakage scan failed")

    create_zip()
    write_project_doc(
        review_count=len(public_rows),
        batch_count=len(batch_counts),
        duplicate_key_count=len(duplicate_key_rows),
        leakage_passed=leakage_passed,
    )

    print("Phase 6 image-level review package created")
    print(f"package directory: {PACKAGE_ROOT.relative_to(PROJECT_ROOT)}")
    print(f"zip path: {ZIP_OUT.relative_to(PROJECT_ROOT)}")
    print(f"review entries: {len(public_rows)}")
    print(f"batches: {len(batch_counts)}")
    print(f"images copied: {copied_count}")


if __name__ == "__main__":
    main()
