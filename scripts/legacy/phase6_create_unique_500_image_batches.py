#!/usr/bin/env python3
"""Create Phase 6 unique-500 image annotation batch packages (10 x 50).

Packaging/export only. Does not mix duplicate-review entries into these batches.
"""

from __future__ import annotations

import ast
import csv
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_select_additional_annotation_candidates import (  # noqa: E402
    EXPANDED_INTERNAL_TABLE,
    LABELED_IMAGE_TABLE,
    REAL_MANIFEST,
    read_csv,
    select_image_candidates,
)

PACKAGE_ROOT = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_image_batches"
)
BATCH_ZIP_DIR = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_image_batches_zips"
)
COMBINED_ZIP = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_image_batches_ALL.zip"
)

CANDIDATE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_candidates/phase6_additional_image_annotation_candidates.csv"
)
DUPLICATE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_candidates/phase6_image_duplicate_annotation_subset.csv"
)

BATCH_SIZE = 50
BATCH_COUNT = 10
EXPECTED_CANDIDATES = 500

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
    "czlx_expanded",
    "CzechLynx/",
    "foe_",
    "snpa",
]

MANIFEST_FIELDS = [
    "review_entry_id",
    "batch_id",
    "review_image_filename",
    "relative_image_path",
    "neutral_image_id",
    "candidate_reason",
    "selection_stratum",
    "annotation_status",
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

TEMPLATE_FIELDS = [
    "review_entry_id",
    "batch_id",
    "review_image_filename",
    *ANNOTATION_FIELDS,
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


def copy_or_convert_image(source_path: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"source image not found: {source}")
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        shutil.copy2(source, target_path)
    else:
        image = Image.open(source).convert("RGB")
        image.save(target_path, format="JPEG", quality=95)


def build_review_rows(candidate_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    ordered = sorted(candidate_rows, key=lambda r: int(r["candidate_order"]))
    review_rows: list[dict[str, object]] = []
    for global_idx, row in enumerate(ordered, start=1):
        batch_index = (global_idx - 1) // BATCH_SIZE + 1
        within_batch = (global_idx - 1) % BATCH_SIZE + 1
        batch_id = f"batch_{batch_index:03d}"
        review_image_filename = f"img_batch{batch_index:03d}_{within_batch:04d}.jpg"
        relative_image_path = f"images/{review_image_filename}"
        combined_relative_path = f"{batch_id}/{relative_image_path}"
        review_rows.append(
            {
                "review_entry_id": f"review_{global_idx:06d}",
                "batch_id": batch_id,
                "review_image_filename": review_image_filename,
                "relative_image_path": relative_image_path,
                "combined_relative_image_path": combined_relative_path,
                "neutral_image_id": f"phase6_img_candidate_{global_idx:06d}",
                "candidate_reason": row["selection_reason"],
                "selection_stratum": row["selection_bucket"],
                "annotation_status": "not_started",
                "_source_candidate_id": row["candidate_image_id"],
            }
        )
    return review_rows


def write_batch_outputs(review_rows: list[dict[str, object]]) -> Counter[str]:
    batch_counts: Counter[str] = Counter()
    for batch_index in range(1, BATCH_COUNT + 1):
        batch_id = f"batch_{batch_index:03d}"
        batch_rows = [row for row in review_rows if row["batch_id"] == batch_id]
        batch_counts[batch_id] = len(batch_rows)
        batch_dir = PACKAGE_ROOT / batch_id
        manifest_rows = [
            {
                "review_entry_id": row["review_entry_id"],
                "batch_id": row["batch_id"],
                "review_image_filename": row["review_image_filename"],
                "relative_image_path": row["relative_image_path"],
                "neutral_image_id": row["neutral_image_id"],
                "candidate_reason": row["candidate_reason"],
                "selection_stratum": row["selection_stratum"],
                "annotation_status": row["annotation_status"],
            }
            for row in batch_rows
        ]
        template_rows = [
            {
                "review_entry_id": row["review_entry_id"],
                "batch_id": row["batch_id"],
                "review_image_filename": row["review_image_filename"],
                "annotation_status": "not_started",
            }
            for row in batch_rows
        ]
        write_csv(batch_dir / f"{batch_id}_manifest.csv", manifest_rows, MANIFEST_FIELDS)
        write_csv(batch_dir / f"{batch_id}_annotation_template.csv", template_rows, TEMPLATE_FIELDS)
    return batch_counts


def write_combined_outputs(review_rows: list[dict[str, object]], batch_counts: Counter[str]) -> None:
    combined_dir = PACKAGE_ROOT / "combined"
    manifest_rows = [
        {
            "review_entry_id": row["review_entry_id"],
            "batch_id": row["batch_id"],
            "review_image_filename": row["review_image_filename"],
            "relative_image_path": row["combined_relative_image_path"],
            "neutral_image_id": row["neutral_image_id"],
            "candidate_reason": row["candidate_reason"],
            "selection_stratum": row["selection_stratum"],
            "annotation_status": row["annotation_status"],
        }
        for row in review_rows
    ]
    template_rows = [
        {
            "review_entry_id": row["review_entry_id"],
            "batch_id": row["batch_id"],
            "review_image_filename": row["review_image_filename"],
            "annotation_status": "not_started",
        }
        for row in review_rows
    ]
    summary_rows = [
        {"batch_id": batch_id, "image_count": batch_counts[batch_id]}
        for batch_id in sorted(batch_counts)
    ]
    write_csv(combined_dir / "unique_500_image_manifest.csv", manifest_rows, MANIFEST_FIELDS)
    write_csv(combined_dir / "unique_500_annotation_template.csv", template_rows, TEMPLATE_FIELDS)
    write_csv(combined_dir / "batch_summary.csv", summary_rows, ["batch_id", "image_count"])


def write_streamlit_app() -> None:
    app_path = PACKAGE_ROOT / "streamlit/streamlit_image_review_app.py"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text(
        '''#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import streamlit as st

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COMBINED_TEMPLATE = PACKAGE_ROOT / "combined/unique_500_annotation_template.csv"
COMBINED_MANIFEST = PACKAGE_ROOT / "combined/unique_500_image_manifest.csv"
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


def resolve_paths(batch_id: str | None) -> tuple[Path, Path, Path]:
    if batch_id:
        batch_dir = PACKAGE_ROOT / batch_id
        template_path = batch_dir / f"{batch_id}_annotation_template.csv"
        manifest_path = batch_dir / f"{batch_id}_manifest.csv"
        working_path = batch_dir / "image_annotation_working.csv"
        return template_path, manifest_path, working_path
    return COMBINED_TEMPLATE, COMBINED_MANIFEST, WORKING_PATH


st.set_page_config(page_title="Phase 6 Image Review", layout="wide")
st.title("Phase 6 Unique Image Annotation Review")

mode = st.sidebar.radio("Package mode", ["combined", "single_batch"])
selected_batch = None
if mode == "single_batch":
    batch_dirs = sorted(p.name for p in PACKAGE_ROOT.glob("batch_*") if p.is_dir())
    selected_batch = st.sidebar.selectbox("Batch folder", batch_dirs)

template_path, manifest_path, working_path = resolve_paths(selected_batch if mode == "single_batch" else None)

if working_path.exists():
    data = pd.read_csv(working_path).fillna("")
else:
    data = pd.read_csv(template_path).fillna("")

manifest = pd.read_csv(manifest_path).fillna("")
path_by_entry = dict(zip(manifest["review_entry_id"], manifest["relative_image_path"]))

batches = sorted(data["batch_id"].unique())
active_batch = st.sidebar.selectbox("Filter batch", batches)
batch_data = data[data["batch_id"] == active_batch].reset_index(drop=True)

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

if mode == "single_batch":
    image_path = PACKAGE_ROOT / selected_batch / path_by_entry[selected_entry_id]
else:
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
            data.to_csv(working_path, index=False)
            st.success(f"Saved to {working_path.name}")

st.caption("Review evidence quality only. Do not attempt individual identification.")
''',
        encoding="utf-8",
    )

    instructions_path = PACKAGE_ROOT / "streamlit/streamlit_run_instructions.md"
    instructions_path.write_text(
        """# Streamlit Run Instructions

Install locally (offline after install):

```bash
pip install streamlit pandas pillow
```

## Combined package (all 500 images)

From the unzipped package root `phase6_unique_500_image_batches/`:

```bash
streamlit run streamlit/streamlit_image_review_app.py
```

Choose **combined** mode in the sidebar. Progress saves to:

```text
image_annotation_working.csv
```

## Single batch folder

After unzipping one batch ZIP, place it inside the package root or run from the full package and choose **single_batch** mode, then select e.g. `batch_001`.

Progress for a single batch saves to:

```text
batch_001/image_annotation_working.csv
```

Return the completed working CSV to the project after review.
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

These ten batches contain 500 unique new image candidates only. Duplicate-review reliability entries are handled separately and are not included here.

Use the Streamlit app dropdowns for categorical fields and notes only when needed.

Save progress frequently. The app writes progress to `image_annotation_working.csv` (combined mode) or `batch_XXX/image_annotation_working.csv` (single-batch mode).

After review, return the completed working CSV to the project.
""",
        encoding="utf-8",
    )


def scan_text_for_leakage(text: str, rel: str, issues: list[str]) -> None:
    lower = text.lower()
    for pattern in RESTRICTED_PATTERNS:
        if pattern.lower() in lower:
            issues.append(f"text: {rel} (matched `{pattern}`)")


def leakage_scan() -> tuple[bool, list[str]]:
    issues: list[str] = []
    scan_suffixes = {".csv", ".md", ".py", ".txt"}
    public_roots = [
        PACKAGE_ROOT / "combined",
        PACKAGE_ROOT / "docs",
        PACKAGE_ROOT / "streamlit",
        PACKAGE_ROOT / "qc",
    ]
    public_roots.extend(PACKAGE_ROOT.glob("batch_*"))

    for root in public_roots:
        if not root.exists():
            continue
        if root.is_file():
            paths = [root]
        else:
            paths = [p for p in root.rglob("*") if p.is_file()]
        for path in paths:
            rel = path.relative_to(PACKAGE_ROOT).as_posix()
            for pattern in RESTRICTED_PATTERNS:
                if pattern.lower() in rel.lower():
                    issues.append(f"filename: {rel} (matched `{pattern}`)")
            if path.suffix.lower() in scan_suffixes:
                scan_text_for_leakage(path.read_text(encoding="utf-8", errors="ignore"), rel, issues)
    return not issues, issues


def write_qc_reports(
    candidate_count: int,
    unique_candidate_count: int,
    duplicate_rows_excluded: int,
    images_found: int,
    images_copied: int,
    missing_images: list[str],
    batch_counts: Counter[str],
    zip_paths: list[Path],
    streamlit_ok: bool,
    leakage_passed: bool,
    leakage_issues: list[str],
) -> None:
    qc_dir = PACKAGE_ROOT / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "Phase 6 unique-500 image batch export QC report",
        "",
        f"candidate CSV row count: {candidate_count}",
        f"unique candidate count: {unique_candidate_count}",
        f"duplicate-review rows excluded from export: {duplicate_rows_excluded}",
        f"images found: {images_found}",
        f"images copied: {images_copied}",
        f"missing images: {len(missing_images)}",
        f"number of batches: {len(batch_counts)}",
        f"images per batch: {dict(sorted(batch_counts.items()))}",
        f"batch ZIP files created: {len([p for p in zip_paths if p.name.startswith('batch_')])}",
        f"combined ZIP created: {any(p.name.endswith('_ALL.zip') for p in zip_paths)}",
        f"streamlit compile/import check passed: {'yes' if streamlit_ok else 'no'}",
        f"leakage scan passed: {'yes' if leakage_passed else 'no'}",
    ]
    if missing_images:
        lines.append("missing neutral_image_id values:")
        lines.extend(f"- {item}" for item in missing_images)
    lines.extend(["", "batch ZIP paths:"])
    lines.extend(f"- {path.relative_to(PROJECT_ROOT)}" for path in sorted(zip_paths))
    (qc_dir / "unique_500_batch_export_qc_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    scan_lines = [
        "Phase 6 unique-500 image batch export leakage scan",
        "",
        f"result: {'PASS' if leakage_passed else 'FAIL'}",
    ]
    if leakage_issues:
        scan_lines.append("issues:")
        scan_lines.extend(f"- {issue}" for issue in leakage_issues)
    else:
        scan_lines.append("No restricted patterns were found in public manifests, docs, filenames, or package CSVs.")
    (qc_dir / "leakage_scan_report.txt").write_text("\n".join(scan_lines) + "\n", encoding="utf-8")


def create_zip(source_dir: Path, zip_path: Path, arc_prefix: Path | None = None) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                if arc_prefix is None:
                    arcname = path.relative_to(source_dir.parent if source_dir.name.startswith("batch_") else source_dir)
                else:
                    arcname = arc_prefix / path.relative_to(source_dir)
                zf.write(path, arcname)


def create_batch_zips() -> list[Path]:
    zip_paths: list[Path] = []
    BATCH_ZIP_DIR.mkdir(parents=True, exist_ok=True)
    for batch_index in range(1, BATCH_COUNT + 1):
        batch_id = f"batch_{batch_index:03d}"
        batch_dir = PACKAGE_ROOT / batch_id
        zip_path = BATCH_ZIP_DIR / f"{batch_id}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(batch_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, Path(batch_id) / path.relative_to(batch_dir))
        zip_paths.append(zip_path)
    return zip_paths


def create_combined_zip() -> Path:
    if COMBINED_ZIP.exists():
        COMBINED_ZIP.unlink()
    with zipfile.ZipFile(COMBINED_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, Path("phase6_unique_500_image_batches") / path.relative_to(PACKAGE_ROOT))
    return COMBINED_ZIP


def verify_zip_integrity(zip_paths: list[Path]) -> None:
    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise RuntimeError(f"Corrupt ZIP entry in {zip_path}: {bad}")


def check_streamlit_syntax() -> bool:
    app_path = PACKAGE_ROOT / "streamlit/streamlit_image_review_app.py"
    source = app_path.read_text(encoding="utf-8")
    ast.parse(source)
    return True


def write_project_doc(
    batch_zip_paths: list[Path],
    leakage_passed: bool,
    missing_count: int,
) -> None:
    doc_path = PROJECT_ROOT / "docs/phase6/phase6_unique_500_image_batch_export_results.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        f"""# Phase 6 Unique 500 Image Batch Export Results

## Purpose

This export packages the 500 unique new Phase 6 image-level annotation candidates into ten review batches (50 images each) for external human annotation. Duplicate-review reliability entries are excluded from these batches.

## Source Candidate CSV

```text
{CANDIDATE_CSV.relative_to(PROJECT_ROOT)}
```

## Unique Images Exported

- unique image candidates: {EXPECTED_CANDIDATES}
- batches: {BATCH_COUNT}
- images per batch: {BATCH_SIZE}

## Output Directory

```text
{PACKAGE_ROOT.relative_to(PROJECT_ROOT)}
```

## Batch ZIP Paths

```text
{BATCH_ZIP_DIR.relative_to(PROJECT_ROOT)}/batch_001.zip
...
{BATCH_ZIP_DIR.relative_to(PROJECT_ROOT)}/batch_010.zip
```

## Combined ZIP Path

```text
{COMBINED_ZIP.relative_to(PROJECT_ROOT)}
```

## Streamlit Instructions

From the unzipped combined package root:

```bash
streamlit run streamlit/streamlit_image_review_app.py
```

See `streamlit/streamlit_run_instructions.md` inside the package.

## QC Result

See:

```text
qc/unique_500_batch_export_qc_report.txt
```

Missing images at export: {missing_count}.

## Leakage Result

{'PASS' if leakage_passed else 'FAIL'} — see `qc/leakage_scan_report.txt`.

## Limitations

- Packaging/export only; no model training or descriptor computation.
- Duplicate-review subset remains separate for later reliability analysis.
- Completed annotation working CSVs must be returned before PF-ERI factor labels can be finalized.
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

    candidate_ids = [row["candidate_image_id"] for row in candidate_rows]
    if len(set(candidate_ids)) != EXPECTED_CANDIDATES:
        raise RuntimeError("Candidate CSV does not contain 500 unique candidate_image_id values")

    duplicate_source_ids = {row["duplicate_of_candidate_image_id"] for row in duplicate_rows}

    source_lookup = source_lookup_from_selection()
    review_rows = build_review_rows(candidate_rows)

    missing_sources: list[str] = []
    images_found = 0
    images_copied = 0
    for row in review_rows:
        source_candidate_id = str(row["_source_candidate_id"])
        source_path = source_lookup.get(source_candidate_id, "")
        target_path = PACKAGE_ROOT / str(row["batch_id"]) / str(row["relative_image_path"])
        if not source_path:
            missing_sources.append(str(row["neutral_image_id"]))
            continue
        images_found += 1
        try:
            copy_or_convert_image(source_path, target_path)
            images_copied += 1
        except FileNotFoundError:
            missing_sources.append(str(row["neutral_image_id"]))

    if missing_sources:
        report_path = PACKAGE_ROOT / "qc/missing_images_report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(missing_sources) + "\n", encoding="utf-8")
        raise RuntimeError(
            f"{len(missing_sources)} source images missing; see {report_path.relative_to(PROJECT_ROOT)}"
        )

    batch_counts = write_batch_outputs(review_rows)
    write_combined_outputs(review_rows, batch_counts)
    write_streamlit_app()
    write_docs()

    streamlit_ok = check_streamlit_syntax()
    leakage_passed, leakage_issues = leakage_scan()

    batch_zip_paths = create_batch_zips()
    combined_zip = create_combined_zip()
    all_zip_paths = batch_zip_paths + [combined_zip]
    verify_zip_integrity(all_zip_paths)

    write_qc_reports(
        candidate_count=len(candidate_rows),
        unique_candidate_count=len(set(candidate_ids)),
        duplicate_rows_excluded=len(duplicate_rows),
        images_found=images_found,
        images_copied=images_copied,
        missing_images=missing_sources,
        batch_counts=batch_counts,
        zip_paths=all_zip_paths,
        streamlit_ok=streamlit_ok,
        leakage_passed=leakage_passed,
        leakage_issues=leakage_issues,
    )
    write_project_doc(batch_zip_paths, leakage_passed, len(missing_sources))

    if len(review_rows) != EXPECTED_CANDIDATES:
        raise RuntimeError("Unexpected review row count")
    if len(batch_counts) != BATCH_COUNT:
        raise RuntimeError("Unexpected batch count")
    if any(count != BATCH_SIZE for count in batch_counts.values()):
        raise RuntimeError(f"Unexpected batch sizes: {dict(batch_counts)}")
    if not leakage_passed:
        raise RuntimeError("Leakage scan failed")
    duplicate_only_ids = duplicate_source_ids - set(candidate_ids)
    if duplicate_only_ids:
        raise RuntimeError(
            f"Duplicate subset references candidates not in the 500 list: {sorted(duplicate_only_ids)[:5]}"
        )

    print("Phase 6 unique-500 image batch export complete")
    print(f"package directory: {PACKAGE_ROOT.relative_to(PROJECT_ROOT)}")
    print(f"review entries: {len(review_rows)}")
    print(f"batches: {len(batch_counts)}")
    print(f"images copied: {images_copied}")
    print(f"batch zips: {BATCH_ZIP_DIR.relative_to(PROJECT_ROOT)}")
    print(f"combined zip: {COMBINED_ZIP.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
