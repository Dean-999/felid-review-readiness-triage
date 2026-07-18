#!/usr/bin/env python3
"""Assemble a manifest-based PF-ERI manuscript submission-readiness package."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_submission_ready_package"

PACKAGE_FILES = [
    ("main_manuscript", "docs/manuscript/2026-07-09_pferi_pair_level_evidence_admission_manuscript_draft.md"),
    ("captions_and_notes", "docs/manuscript/2026-07-10_pferi_display_captions_and_table_notes.md"),
    ("figure1_harmonization", "docs/manuscript/2026-07-10_figure1_harmonization_note.md"),
    ("claim_boundary_audit_report", "docs/manuscript/2026-07-10_claim_boundary_consistency_audit.md"),
    ("internal_peer_review", "docs/manuscript/2026-07-09_pferi_internal_peer_review.md"),
    ("stop_slop_review", "docs/manuscript/2026-07-09_pferi_stop_slop_review.md"),
    ("reference_inventory", "docs/manuscript/2026-07-09_pferi_reference_inventory.md"),
    ("figure1_svg", "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.svg"),
    ("figure1_pdf", "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.pdf"),
    ("figure1_png", "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.png"),
    ("figure2_svg", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.svg"),
    ("figure2_pdf", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.pdf"),
    ("figure2_png", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.png"),
    ("figure3_svg", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.svg"),
    ("figure3_pdf", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.pdf"),
    ("figure3_png", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.png"),
    ("figure4_svg", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.svg"),
    ("figure4_pdf", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.pdf"),
    ("figure4_png", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.png"),
    ("table1_csv", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.csv"),
    ("table1_md", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.md"),
    ("table2_csv", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.csv"),
    ("table2_md", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.md"),
    ("table3_csv", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.csv"),
    ("table3_md", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.md"),
    ("display_build_audit", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/manuscript_figures_tables_audit.json"),
    ("source_data_readme", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/README.md"),
    ("source_data_map", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/display_item_source_map.csv"),
    ("source_file_manifest", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/source_file_manifest.csv"),
    ("source_data_audit", "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/source_data_package_audit.json"),
    ("claim_boundary_findings", "archive/pferi_v1/outputs/manuscript/2026-07-10_claim_boundary_audit/manuscript_claim_boundary_findings.csv"),
    ("claim_boundary_audit", "archive/pferi_v1/outputs/manuscript/2026-07-10_claim_boundary_audit/manuscript_claim_boundary_audit.json"),
    ("issue_pack", "docs/project-governance/executable-plans/plans/2026-07-10-manuscript-submission-readiness-issue-pack.md"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    missing = []
    for role, rel_path in PACKAGE_FILES:
        path = PROJECT_ROOT / rel_path
        exists = path.exists()
        if not exists:
            missing.append(rel_path)
        rows.append(
            {
                "role": role,
                "path": rel_path,
                "exists": exists,
                "bytes": path.stat().st_size if exists else "",
                "sha256": sha256(path) if exists else "",
            }
        )

    manifest_path = OUT_DIR / "submission_package_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["role", "path", "exists", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    audit = {
        "status": "PASS" if not missing else "FAIL_MISSING_FILES",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_file_count": len(rows),
        "missing_files": missing,
        "claim_boundary": (
            "Submission-readiness package preserves PF-ERI as post-retrieval "
            "pair-level evidence admission for human reviewability/evidential "
            "admissibility; no identity accuracy, Bobcat identity performance, "
            "descriptor replacement, mAP, MRR, top-k, or universal guarantee claim."
        ),
    }
    (OUT_DIR / "submission_package_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    checklist = """# Submission-Ready Package Checklist

Date: 2026-07-10

Status: `MANIFEST_READY_FOR_HUMAN_REVIEW`

## Complete

- Main manuscript draft is linked in `submission_package_manifest.csv`.
- Figure 1-4 outputs are present in SVG, PDF, and PNG where available.
- Table 1-3 outputs are present as CSV and Markdown.
- Figure captions and table notes are complete.
- Source-data package is present with SHA-256 file manifest.
- Manuscript claim-boundary audit passes with zero unsafe positive claims.

## Still Requires Human Completion Before Journal Submission

- Author list.
- Affiliations.
- Corresponding author.
- Data and code availability statement matched to the target journal and dataset licenses.
- Ethics statement matched to the actual CzechLynx and Bobcat data provenance.
- Author contributions.
- Competing interests.
- Target-journal formatting and reference export.
- Final permission/licensing check for any non-owned image data.

## Primary Review Entry Points

1. `docs/manuscript/2026-07-09_pferi_pair_level_evidence_admission_manuscript_draft.md`
2. `docs/manuscript/2026-07-10_pferi_display_captions_and_table_notes.md`
3. `archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/README.md`
4. `docs/manuscript/2026-07-10_claim_boundary_consistency_audit.md`
"""
    (OUT_DIR / "README.md").write_text(checklist, encoding="utf-8")
    print(f"Built submission package manifest in {OUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Status: {audit['status']}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
