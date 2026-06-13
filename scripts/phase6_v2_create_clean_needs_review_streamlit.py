#!/usr/bin/env python3
"""Create a clean v2 needs-review Streamlit package for one range."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
DEFAULT_RANGE_ID = "range_000_049"
WORKSPACE = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}/assisted_annotation_workspace"
REVIEW_IMAGE_ROOT = PROJECT_ROOT / f"data/review_images/czechlynx/{WORKFLOW_NAME}"

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
    "lighting_condition": ["", "daylight", "low_light", "mixed", "night_ir", "overexposed", "underexposed", "unknown"],
    "night_ir_artifact": ["", "none", "mild", "moderate", "severe", "not_applicable", "unknown"],
    "contrast_level": ["", "high", "medium", "low", "unknown"],
    "primary_limiting_factor": ["", "none", "blur", "occlusion", "lighting_ir", "low_pattern_visibility", "side_not_comparable", "partial_body", "frontal_rear_view", "silhouette_only", "overexposure", "underexposure", "multiple", "unknown"],
    "uncertainty_flag": ["", "yes", "no"],
    "annotation_status": ["", "complete", "needs_review", "pending", "in_progress"],
}

RESTRICTED = [
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_app(app_path: Path, range_id: str) -> None:
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text(
        f'''#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import streamlit as st

WORKFLOW = "{WORKFLOW_NAME}"
RANGE_ID = "{range_id}"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE_ROOT / "manifests/{range_id}_needs_review_correction_template_v2_clean.csv"
MANIFEST = PACKAGE_ROOT / "manifests/{range_id}_needs_review_manifest_v2_clean.csv"
WORKING = PACKAGE_ROOT / "{range_id}_needs_review_corrections_working_v2_clean.csv"

ALLOWED_VALUES = {ALLOWED_VALUES!r}
FIELDS = {ANNOTATION_FIELDS!r}

st.set_page_config(page_title="Phase 6 v2 balanced needs-review", layout="wide")
st.title("Phase 6 v2 balanced needs-review correction tool")
st.warning("Only use needs_review when the annotation itself is uncertain. Low image quality alone is not needs_review.")

if WORKING.exists():
    data = pd.read_csv(WORKING).fillna("")
else:
    data = pd.read_csv(TEMPLATE).fillna("")
manifest = pd.read_csv(MANIFEST).fillna("")
path_by_id = dict(zip(manifest["expanded_image_id"], manifest["relative_image_path"]))

st.sidebar.write(f"workflow: {{WORKFLOW}}")
st.sidebar.write(f"range: {{RANGE_ID}}")
st.sidebar.metric("needs_review rows", len(data))
complete_count = int((data["annotation_status"] == "complete").sum())
st.sidebar.metric("marked complete", f"{{complete_count}} / {{len(data)}}")

ids = list(data["expanded_image_id"])
selected_id = st.sidebar.selectbox("expanded_image_id", ids)
idx = data.index[data["expanded_image_id"] == selected_id][0]
row = data.loc[idx].copy()

left, right = st.columns([3, 2])
with left:
    image_path = PACKAGE_ROOT / path_by_id[selected_id]
    st.image(str(image_path), caption=selected_id, use_container_width=True)

with right:
    st.write(f"workflow: {{WORKFLOW}}")
    st.write(f"range: {{RANGE_ID}}")
    st.write(f"expanded_image_id: {{selected_id}}")
    st.subheader("Current first-pass annotation")
    st.dataframe(row[FIELDS].to_frame("value"), use_container_width=True)
    with st.form("correction_form"):
        updates = {{}}
        for field in FIELDS:
            if field == "annotator_notes":
                updates[field] = st.text_area(field, value=str(row.get(field, "")), height=120)
            else:
                options = ALLOWED_VALUES[field]
                current = str(row.get(field, ""))
                index = options.index(current) if current in options else 0
                updates[field] = st.selectbox(field, options, index=index)
        submitted = st.form_submit_button("Save correction")
        if submitted:
            for field, value in updates.items():
                data.at[idx, field] = value
            data.to_csv(WORKING, index=False)
            st.success(f"Saved {{WORKING.name}}")
''',
        encoding="utf-8",
    )


def leakage_scan(package_dir: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for path in package_dir.rglob("*"):
        rel = path.relative_to(package_dir).as_posix()
        if RAW_LYNX_RE.search(rel):
            issues.append(f"filename: {rel}")
        for pattern in RESTRICTED:
            if pattern.lower() in rel.lower():
                issues.append(f"filename: {rel}")
        if path.is_file() and path.suffix.lower() in {".csv", ".md", ".py", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if RAW_LYNX_RE.search(text):
                issues.append(f"text: {rel}")
                continue
            for pattern in RESTRICTED:
                if pattern.lower() in text.lower():
                    issues.append(f"text: {rel}")
                    break
    return not issues, issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-id", default=DEFAULT_RANGE_ID)
    args = parser.parse_args()
    range_dir = WORKSPACE / "incoming_from_downloads" / args.range_id
    input_csv = range_dir / f"{args.range_id}_needs_review.csv"
    package_dir = range_dir / "needs_review_streamlit_v2_clean"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)

    rows = read_csv(input_csv)
    manifest_rows = []
    template_rows = []
    missing_images = []
    for row in rows:
        image_name = Path(row["review_image_path_local"]).name
        source_image = REVIEW_IMAGE_ROOT / image_name
        target_image = package_dir / "images" / image_name
        target_image.parent.mkdir(parents=True, exist_ok=True)
        if source_image.exists():
            shutil.copy2(source_image, target_image)
        else:
            missing_images.append(row["expanded_image_id"])
        rel_path = f"images/{image_name}"
        manifest = {
            "expanded_image_id": row["expanded_image_id"],
            "relative_image_path": rel_path,
            "candidate_reason": row.get("candidate_reason", ""),
            "selection_stratum": row.get("selection_stratum", ""),
            "quality_bucket": row.get("quality_bucket", ""),
            "batch_id": row.get("batch_id", ""),
        }
        manifest_rows.append(manifest)
        template = {key: row.get(key, "") for key in ["expanded_image_id", "relative_image_path", "candidate_reason", "selection_stratum", "quality_bucket", "batch_id", *ANNOTATION_FIELDS]}
        template_rows.append(template)

    manifest_fields = ["expanded_image_id", "relative_image_path", "candidate_reason", "selection_stratum", "quality_bucket", "batch_id"]
    template_fields = ["expanded_image_id", "relative_image_path", "candidate_reason", "selection_stratum", "quality_bucket", "batch_id", *ANNOTATION_FIELDS]
    write_csv(package_dir / "manifests" / f"{args.range_id}_needs_review_manifest_v2_clean.csv", manifest_rows, manifest_fields)
    write_csv(package_dir / "manifests" / f"{args.range_id}_needs_review_correction_template_v2_clean.csv", template_rows, template_fields)
    make_app(package_dir / "streamlit" / "streamlit_phase6_v2_needs_review_app.py", args.range_id)
    (package_dir / "README.md").write_text(
        f"""# Phase 6 v2 Balanced Needs-Review Correction Tool

Workflow: `{WORKFLOW_NAME}`

Range: `{args.range_id}`

Run:

```bash
streamlit run streamlit/streamlit_phase6_v2_needs_review_app.py
```

The app writes:

```text
{args.range_id}_needs_review_corrections_working_v2_clean.csv
```

Do not use old `streamlit_needs_review_app.py` packages for this v2 workflow.
""",
        encoding="utf-8",
    )
    passed, issues = leakage_scan(package_dir)
    qc_lines = [
        "Phase 6 v2 clean needs-review Streamlit QC",
        "",
        f"workflow: {WORKFLOW_NAME}",
        f"range_id: {args.range_id}",
        f"needs_review_rows: {len(rows)}",
        f"images_copied: {len(rows) - len(missing_images)}",
        f"missing_images: {len(missing_images)}",
        f"leakage_scan: {'PASS' if passed else 'FAIL'}",
        "app_name: streamlit_phase6_v2_needs_review_app.py",
    ]
    if missing_images:
        qc_lines.append("missing image ids:")
        qc_lines.extend(f"- {item}" for item in missing_images)
    if issues:
        qc_lines.append("leakage issues:")
        qc_lines.extend(f"- {item}" for item in issues)
    (package_dir / "qc").mkdir(parents=True, exist_ok=True)
    (package_dir / "qc" / "needs_review_streamlit_v2_clean_qc_report.txt").write_text("\n".join(qc_lines) + "\n", encoding="utf-8")
    if missing_images or not passed:
        raise SystemExit(1)
    print(f"created {package_dir}")
    print(f"needs_review_rows: {len(rows)}")


if __name__ == "__main__":
    main()
