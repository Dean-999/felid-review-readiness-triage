#!/usr/bin/env python3
"""Audit manuscript-facing files for PF-ERI claim-boundary drift."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_claim_boundary_audit"
FINDINGS_CSV = OUTPUT_DIR / "manuscript_claim_boundary_findings.csv"
AUDIT_JSON = OUTPUT_DIR / "manuscript_claim_boundary_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/manuscript/2026-07-10_claim_boundary_consistency_audit.md"

CHECKED_FILES = [
    PROJECT_ROOT / "docs/manuscript/2026-07-09_pferi_pair_level_evidence_admission_manuscript_draft.md",
    PROJECT_ROOT / "docs/manuscript/2026-07-10_pferi_display_captions_and_table_notes.md",
    PROJECT_ROOT / "docs/manuscript/2026-07-10_figure1_harmonization_note.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables/README.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/README.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/display_item_source_map.md",
]

RISK_PATTERNS = {
    "automatic_identity": re.compile(
        r"\b(automatic identity|automated identity|automatic ID|automated ID|automatically identifies|assigns identity|identity assignment|automated recognition accuracy)\b",
        re.I,
    ),
    "bobcat_identity_accuracy": re.compile(
        r"\b(Bobcat identity accuracy|Bobcat false-match accuracy|Bobcat mAP|Bobcat top-k|Bobcat identity performance|Bobcat identity validation)\b",
        re.I,
    ),
    "ranking_overclaim": re.compile(
        r"\b(mAP|MRR|top-k|top k|retrieval improvement|ranking improvement|ranking-superiority|universal superiority)\b",
        re.I,
    ),
    "descriptor_replacement": re.compile(
        r"\b(new descriptor|replacement descriptor|descriptor replacement|replacement retrieval model|replaces MegaDescriptor|replaces DINOv2)\b",
        re.I,
    ),
    "overproof": re.compile(r"\b(proves|prove|proved|universal guarantee|guarantees)\b", re.I),
}

SAFE_MARKERS = [
    "not ",
    "no ",
    "does not",
    "do not",
    "cannot",
    "without",
    "blocked",
    "boundary",
    "outside",
    "restricted",
    "rather than",
    "not as",
    "not a",
    "not identity",
    "not automated",
    "should not",
    "must not",
    "preventing",
    "claim boundary",
]

REFERENCE_MARKERS = [
    "reference",
    "doi",
    "https://",
    "arxiv",
    "identification using camera trap",
    "animal re-identification",
]

POSITIVE_MARKERS = [
    "pf-eri improves",
    "pf-eri proves",
    "pf-eri validates",
    "pf-eri identifies",
    "pf-eri assigns",
    "pf-eri replaces",
    "we prove",
    "we validate bobcat",
]


def project_relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def classify(line: str, context: str) -> tuple[str, str]:
    lowered = line.lower()
    lowered_context = context.lower()
    if any(marker in lowered for marker in SAFE_MARKERS) or any(marker in lowered_context for marker in SAFE_MARKERS):
        return "safe_boundary", "Risk phrase appears in a negated, blocked, or claim-boundary context."
    if any(marker in lowered for marker in POSITIVE_MARKERS):
        return "unsafe_positive_claim", "Risk phrase appears in direct positive PF-ERI claim language."
    if any(marker in lowered for marker in REFERENCE_MARKERS):
        return "reference_context", "Risk phrase appears in a citation or related-work reference context."
    if "pf-eri" in lowered and any(verb in lowered for verb in ["improve", "valid", "identif", "assign", "replac", "prove"]):
        return "unsafe_positive_claim", "PF-ERI appears with a risky positive verb."
    return "manual_review", "Risk phrase lacks an explicit boundary marker and should be reviewed in context."


def scan_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        context = "\n".join(lines[max(0, index - 4) : index + 1])
        for risk_family, pattern in RISK_PATTERNS.items():
            if pattern.search(line):
                classification, rationale = classify(line, context)
                findings.append(
                    {
                        "file": project_relative(path),
                        "line_number": index + 1,
                        "risk_family": risk_family,
                        "classification": classification,
                        "line_text": line.strip(),
                        "rationale": rationale,
                    }
                )
    return findings


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = ["file", "line_number", "risk_family", "classification", "line_text", "rationale"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def report_text(audit: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    checked = "\n".join(f"- `{project_relative(path)}`" for path in CHECKED_FILES)
    unsafe = [row for row in findings if row["classification"] == "unsafe_positive_claim"]
    manual = [row for row in findings if row["classification"] == "manual_review"]
    unsafe_lines = "\n".join(
        f"- `{row['file']}:{row['line_number']}` `{row['risk_family']}`: {row['line_text']}" for row in unsafe
    ) or "- None."
    manual_lines = "\n".join(
        f"- `{row['file']}:{row['line_number']}` `{row['risk_family']}`: {row['line_text']}" for row in manual
    ) or "- None."

    return f"""# Manuscript Claim-Boundary Consistency Audit

Date: 2026-07-10

Status: `{audit['status']}`

Issue source:

```text
docs/project-governance/executable-plans/plans/2026-07-10-manuscript-submission-readiness-issue-pack.md
```

## Scope

This audit checks the manuscript-facing layer after captions, display tables,
source-data manifests, and Figure 1 harmonization were added. It searches for
phrases that could reframe PF-ERI as a descriptor, automatic identity system,
Bobcat identity-validation system, retrieval-ranking improvement, or universal
guarantee.

## Files Checked

{checked}

## Result

The audit status is `{audit['status']}`. It found {audit['unsafe_positive_claim_count']} unsafe positive claim lines, {audit['manual_review_count']} manual-review lines, {audit['safe_boundary_count']} safe-boundary lines, and {audit['reference_context_count']} reference-context lines.

## Unsafe Positive Claims

{unsafe_lines}

## Manual-Review Lines

{manual_lines}

## Interpretation

The current manuscript-facing layer preserves the positive claim as
post-retrieval pair-level evidence admission for human reviewability /
evidential admissibility. Risk phrases that remain are used as blocked claims,
limitations, references, or explicit claim boundaries.

Generated artifacts:

```text
{project_relative(FINDINGS_CSV)}
{project_relative(AUDIT_JSON)}
```
"""


def main() -> None:
    missing = [project_relative(path) for path in CHECKED_FILES if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing checked files: {missing}")

    findings: list[dict[str, Any]] = []
    for path in CHECKED_FILES:
        findings.extend(scan_file(path))

    unsafe_count = sum(row["classification"] == "unsafe_positive_claim" for row in findings)
    audit = {
        "status": "PASS" if unsafe_count == 0 else "FAIL_UNSAFE_POSITIVE_CLAIMS",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "checked_files": [project_relative(path) for path in CHECKED_FILES],
        "finding_count": len(findings),
        "unsafe_positive_claim_count": unsafe_count,
        "manual_review_count": sum(row["classification"] == "manual_review" for row in findings),
        "safe_boundary_count": sum(row["classification"] == "safe_boundary" for row in findings),
        "reference_context_count": sum(row["classification"] == "reference_context" for row in findings),
        "claim_boundary": (
            "PF-ERI remains a post-retrieval pair-level evidence admission layer for "
            "human reviewability/evidential admissibility; no identity accuracy, "
            "Bobcat identity performance, descriptor replacement, mAP, MRR, top-k, "
            "or universal guarantee claim."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(FINDINGS_CSV, findings)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(report_text(audit, findings), encoding="utf-8")
    print(f"Built manuscript claim-boundary audit: {audit['status']}")
    print(project_relative(REPORT_MD))
    if unsafe_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
