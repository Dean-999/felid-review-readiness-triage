#!/usr/bin/env python3
"""Rebuild unified Phase 6 unique-500 image review set and annotation CSVs."""

from __future__ import annotations

import csv
import shutil
import sys
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
from phase6_unique_500_annotation_schema import (  # noqa: E402
    EXPECTED_ROWS,
    ID_PREFIX,
    INTERNAL_MAPPING_CSV,
    PUBLIC_COLUMNS,
    REVIEW_IMAGE_DIR,
    REVIEW_IMAGE_DIR_REL,
    TEMPLATE_CSV,
    WORKING_CSV,
    find_leakage_issues,
    path_is_safe_public_path,
)

CANDIDATE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_candidates/phase6_additional_image_annotation_candidates.csv"
)
QC_REPORT = PROJECT_ROOT / "outputs/czechlynx/qc/phase6_unique_500_review_set_build_qc_report.txt"

PLAN_DOC = PROJECT_ROOT / "docs/phase6/phase6_unique_500_review_set_rebuild_plan.md"
RESULTS_DOC = PROJECT_ROOT / "docs/phase6/phase6_unique_500_review_set_rebuild_results.md"
WORKFLOW_DOC = PROJECT_ROOT / "docs/phase6/phase6_unique_500_annotation_workflow_protocol.md"
AUDIT_RULES_DOC = PROJECT_ROOT / "docs/phase6/phase6_unique_500_annotation_audit_rules.md"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def source_lookup_from_selection() -> dict[str, dict[str, str]]:
    expanded_rows = read_csv(PROJECT_ROOT / EXPANDED_INTERNAL_TABLE)
    real_manifest = read_csv(PROJECT_ROOT / REAL_MANIFEST)
    _ = read_csv(PROJECT_ROOT / LABELED_IMAGE_TABLE)
    selected_rows, _ = select_image_candidates(real_manifest, expanded_rows)
    lookup: dict[str, dict[str, str]] = {}
    for row in selected_rows:
        candidate_id = str(row["candidate_image_id"])
        lookup[candidate_id] = {
            "source_local_image_path": str(row.get("_source_local_image_path", "")),
            "source_manifest_path": str(row.get("_source_manifest_path", "")),
            "manifest_proxy_stratum": str(row.get("manifest_proxy_stratum", "")),
            "image_quality_proxy_stratum": str(row.get("image_quality_proxy_stratum", "")),
        }
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


def blank_public_row(
    expanded_image_id: str,
    review_image_path_local: str,
    candidate_source_id: str,
    candidate_reason: str,
    selection_stratum: str,
) -> dict[str, str]:
    row = {col: "" for col in PUBLIC_COLUMNS}
    row.update(
        {
            "expanded_image_id": expanded_image_id,
            "review_image_path_local": review_image_path_local,
            "candidate_source_id": candidate_source_id,
            "candidate_reason": candidate_reason,
            "selection_stratum": selection_stratum,
            "annotation_status": "pending",
        }
    )
    return row


def leakage_scan_paths(paths: list[Path]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for path in paths:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if path.suffix.lower() in {".csv", ".md", ".txt"}:
            if path.suffix.lower() == ".csv":
                with path.open(newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_id = row.get("expanded_image_id", "?")
                        for col, value in row.items():
                            if col == "review_image_path_local" and path_is_safe_public_path(value):
                                continue
                            issues.extend(
                                find_leakage_issues(value, context=f"{rel}:{row_id}:{col}")
                            )
            else:
                issues.extend(find_leakage_issues(path.read_text(encoding="utf-8"), context=rel))
    return not issues, issues


def write_plan_doc() -> None:
    PLAN_DOC.parent.mkdir(parents=True, exist_ok=True)
    PLAN_DOC.write_text(
        f"""# Phase 6 Unique 500 Review Set Rebuild Plan

## Purpose

Reset the Phase 6 additional image annotation workflow to the earlier unified Czech dataset annotation pattern:

1. copy source images into one anonymized review folder;
2. assign stable `expanded_image_id` values;
3. maintain one 500-row public annotation CSV;
4. review in 50-image ranges via Streamlit;
5. audit and freeze a v1 CSV after completion.

## Why Reset

The fragmented 10-ZIP batch workflow created operational overhead. A single working CSV bound to stable `czlx_phase6_expanded_####` IDs matches the proven expanded 125x4 workflow.

## Scope

- Input: `{CANDIDATE_CSV.relative_to(PROJECT_ROOT)}` (500 unique candidates only)
- Exclude duplicate-review reliability entries for now
- No model training, descriptor computation, or PF-ERI score changes

## Outputs

| Artifact | Path |
|---|---|
| Review images | `{REVIEW_IMAGE_DIR_REL}/` |
| Working CSV | `{WORKING_CSV.relative_to(PROJECT_ROOT)}` |
| Template CSV | `{TEMPLATE_CSV.relative_to(PROJECT_ROOT)}` |
| Internal mapping | `{INTERNAL_MAPPING_CSV.relative_to(PROJECT_ROOT)}` |
| Streamlit app | `scripts/streamlit_phase6_unique_500_image_annotation_app.py` |
| Audit script | `scripts/audit_phase6_unique_500_image_annotations.py` |

## Build Command

```bash
python3 scripts/phase6_rebuild_unique_500_image_review_set.py
```
""",
        encoding="utf-8",
    )


def write_workflow_doc() -> None:
    WORKFLOW_DOC.write_text(
        f"""# Phase 6 Unique 500 Annotation Workflow Protocol

## Workflow Reset

This protocol replaces fragmented per-batch ZIP annotation with one unified 500-row CSV and one anonymized image folder, following the same pattern as the earlier expanded visual-factor annotation workflow.

## Why One Unified CSV

- One stable row per image via `expanded_image_id`
- Resume anywhere without merging batch CSVs
- Same audit/freeze pattern as expanded 125x4 triage
- Streamlit range review supports 50-image sessions without separate files

## ID Binding

Each row uses:

- `expanded_image_id`: `czlx_phase6_expanded_0000` … `czlx_phase6_expanded_0499`
- `review_image_path_local`: relative path under `{REVIEW_IMAGE_DIR_REL}/`

The internal mapping in `data/interim/czechlynx/` links these public IDs to candidate/source metadata for reproducibility only.

## Review in 50-Image Ranges

Use Streamlit with default ranges:

- 0–49, 50–99, …, 450–499

Filter to `pending` or `needs_review` as needed. Save progress directly to the working CSV.

## Annotation Status Definitions

### `pending`

Unannotated row.

### `complete`

Use when the annotator has approximately ≥75% confidence in the visual-factor labels, even if the image itself is poor quality.

Poor Re-ID evidence is not the same as annotation uncertainty. A low-quality image can still be confidently labeled (for example severe blur, low pattern visibility, partial body) and marked `complete`.

### `needs_review`

Use only when the annotation itself is unstable or ambiguous, such as:

- object/animal identity unclear;
- body region unclear;
- side visibility genuinely ambiguous;
- severe blur prevents stable factor labeling;
- severe occlusion prevents stable factor labeling;
- cannot distinguish silhouette/frontal/partial-body state;
- multiple fields would be guesses.

When using `needs_review`, set `uncertainty_flag = yes`.

## Commands

Build review set:

```bash
python3 scripts/phase6_rebuild_unique_500_image_review_set.py
```

Annotate:

```bash
streamlit run scripts/streamlit_phase6_unique_500_image_annotation_app.py
```

Audit:

```bash
python3 scripts/audit_phase6_unique_500_image_annotations.py
```

Freeze v1 after audit pass:

```bash
python3 scripts/audit_phase6_unique_500_image_annotations.py --freeze-if-pass
```
""",
        encoding="utf-8",
    )


def write_audit_rules_doc() -> None:
    AUDIT_RULES_DOC.write_text(
        """# Phase 6 Unique 500 Annotation Audit Rules

## Row and File Checks

- exactly 500 CSV rows;
- exactly 500 review images;
- every `review_image_path_local` resolves to an existing file.

## Required Fields

- `annotation_status = complete` requires all annotation fields except `annotator_notes`;
- `annotation_status = needs_review` requires `uncertainty_flag = yes`;
- `pending` rows are allowed during annotation but not in final freeze.

## Allowed Values

All categorical fields must match the schema in `scripts/phase6_unique_500_annotation_schema.py`.

## Logic Consistency (Warnings)

- `uncertainty_flag = yes` should correspond to `annotation_status = needs_review`;
- low `body_fraction_visible` (`0_25`, `26_50`) should usually imply `partial_body = yes`;
- `silhouette_only = yes` should usually imply low/none pattern visibility;
- `frontal_or_rear_view = yes` should usually imply `side_visibility = unknown`;
- `pattern_visibility = none` should not usually pair with high side evidence quality;
- `primary_limiting_factor = none` should not coexist with major quality problems;
- `complete` rows should avoid unexplained `unknown` values.

## Leakage

Public CSVs, docs, and review filenames must not expose raw IDs, GPS, trap metadata, or absolute raw paths.

## Freeze Criteria

Freeze to v1 only when audit passes with:

- 500 rows;
- no pending rows;
- no failures;
- no leakage failures;
- warnings reviewed and acceptable.
""",
        encoding="utf-8",
    )


def write_results_doc(
    images_copied: int,
    leakage_passed: bool,
) -> None:
    RESULTS_DOC.write_text(
        f"""# Phase 6 Unique 500 Review Set Rebuild Results

## Summary

Unified Phase 6 image review set rebuilt for 500 unique additional annotation candidates.

## Outputs

| Artifact | Path |
|---|---|
| Review images | `{REVIEW_IMAGE_DIR_REL}/` |
| Working CSV | `{WORKING_CSV.relative_to(PROJECT_ROOT)}` |
| Template CSV | `{TEMPLATE_CSV.relative_to(PROJECT_ROOT)}` |
| Internal mapping | `{INTERNAL_MAPPING_CSV.relative_to(PROJECT_ROOT)}` |
| Build QC | `{QC_REPORT.relative_to(PROJECT_ROOT)}` |

## Counts

- review images copied: {images_copied}
- CSV rows: {EXPECTED_ROWS}
- duplicate-review entries included: 0

## Leakage Scan

{'PASS' if leakage_passed else 'FAIL'}

## Ready for Annotation

{'Yes — use Streamlit with 50-image ranges on the working CSV.' if leakage_passed and images_copied == EXPECTED_ROWS else 'No — inspect build QC report.'}

## Next Steps

1. Annotate via Streamlit in 50-image ranges.
2. Run audit script.
3. Freeze v1 only after audit pass.
""",
        encoding="utf-8",
    )


def write_qc_report(
    candidate_count: int,
    images_copied: int,
    leakage_passed: bool,
    leakage_issues: list[str],
) -> None:
    lines = [
        "Phase 6 unique-500 review set build QC report",
        "",
        f"candidate CSV rows: {candidate_count}",
        f"review images copied: {images_copied}",
        f"expected rows/images: {EXPECTED_ROWS}",
        f"working CSV rows written: {EXPECTED_ROWS}",
        f"template CSV rows written: {EXPECTED_ROWS}",
        f"internal mapping rows written: {EXPECTED_ROWS}",
        f"duplicate-review rows included: 0",
        f"leakage scan passed: {'yes' if leakage_passed else 'no'}",
    ]
    if leakage_issues:
        lines.append("leakage issues:")
        lines.extend(f"- {issue}" for issue in leakage_issues)
    QC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    QC_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_plan_doc()
    write_workflow_doc()
    write_audit_rules_doc()

    candidate_rows = read_csv(CANDIDATE_CSV)
    if len(candidate_rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} candidates, found {len(candidate_rows)}")

    candidate_ids = [row["candidate_image_id"] for row in candidate_rows]
    if len(set(candidate_ids)) != EXPECTED_ROWS:
        raise RuntimeError("Candidate CSV does not contain 500 unique candidate_image_id values")

    source_lookup = source_lookup_from_selection()
    ordered = sorted(candidate_rows, key=lambda r: int(r["candidate_order"]))

    if REVIEW_IMAGE_DIR.exists():
        shutil.rmtree(REVIEW_IMAGE_DIR)
    REVIEW_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    public_rows: list[dict[str, str]] = []
    internal_rows: list[dict[str, str]] = []
    missing: list[str] = []

    for idx, candidate in enumerate(ordered):
        expanded_image_id = f"{ID_PREFIX}_{idx:04d}"
        review_filename = f"{expanded_image_id}.jpg"
        review_image_path_local = f"{REVIEW_IMAGE_DIR_REL}/{review_filename}"
        candidate_source_id = candidate["candidate_image_id"]
        source_meta = source_lookup.get(candidate_source_id, {})
        source_path = source_meta.get("source_local_image_path", "")
        target_path = REVIEW_IMAGE_DIR / review_filename

        if not source_path:
            missing.append(candidate_source_id)
            continue
        try:
            copy_or_convert_image(source_path, target_path)
        except FileNotFoundError:
            missing.append(candidate_source_id)

        public_rows.append(
            blank_public_row(
                expanded_image_id=expanded_image_id,
                review_image_path_local=review_image_path_local,
                candidate_source_id=candidate_source_id,
                candidate_reason=candidate["selection_reason"],
                selection_stratum=candidate["selection_bucket"],
            )
        )
        internal_rows.append(
            {
                "expanded_image_id": expanded_image_id,
                "review_image_filename": review_filename,
                "review_image_path_local": review_image_path_local,
                "candidate_source_id": candidate_source_id,
                "candidate_order": candidate["candidate_order"],
                "selection_bucket": candidate["selection_bucket"],
                "selection_reason": candidate["selection_reason"],
                "manifest_proxy_stratum": candidate.get("manifest_proxy_stratum", ""),
                "image_quality_proxy_stratum": candidate.get("image_quality_proxy_stratum", ""),
                "source_local_image_path": source_path,
                "source_manifest_path": source_meta.get("source_manifest_path", ""),
            }
        )

    if missing:
        raise RuntimeError(
            f"{len(missing)} source images missing for candidates: {', '.join(missing[:10])}"
        )
    if len(public_rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} public rows, found {len(public_rows)}")

    write_csv(WORKING_CSV, public_rows, PUBLIC_COLUMNS)
    write_csv(TEMPLATE_CSV, public_rows, PUBLIC_COLUMNS)
    write_csv(
        INTERNAL_MAPPING_CSV,
        internal_rows,
        list(internal_rows[0].keys()),
    )

    public_scan_paths = [WORKING_CSV, TEMPLATE_CSV, WORKFLOW_DOC, AUDIT_RULES_DOC]
    image_names = list(REVIEW_IMAGE_DIR.glob("*.jpg"))
    leakage_passed, leakage_issues = leakage_scan_paths(public_scan_paths)

    write_qc_report(len(candidate_rows), len(image_names), leakage_passed, leakage_issues)
    write_results_doc(len(image_names), leakage_passed)

    if len(image_names) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} review images, found {len(image_names)}")
    if not leakage_passed:
        raise RuntimeError("Leakage scan failed during review set build")

    print("Phase 6 unique-500 review set rebuild: PASS")
    print(f"review images: {REVIEW_IMAGE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"working CSV: {WORKING_CSV.relative_to(PROJECT_ROOT)}")
    print(f"template CSV: {TEMPLATE_CSV.relative_to(PROJECT_ROOT)}")
    print(f"internal mapping: {INTERNAL_MAPPING_CSV.relative_to(PROJECT_ROOT)}")
    print(f"QC report: {QC_REPORT.relative_to(PROJECT_ROOT)}")
    print(f"images copied: {len(image_names)}")


if __name__ == "__main__":
    main()
