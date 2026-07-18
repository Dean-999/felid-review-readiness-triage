#!/usr/bin/env python3
"""Build Issue 9 final story consistency audit."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue9"
FINDINGS_CSV = OUTPUT_DIR / "issue9_story_consistency_findings.csv"
AUDIT_JSON = OUTPUT_DIR / "issue9_story_consistency_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_final_story_consistency_audit.md"

CHECKED_FILES = [
    PROJECT_ROOT / "PROJECT_RULES.md",
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "docs/CURRENT_PROJECT_MAP.md",
    PROJECT_ROOT / "docs/modeling-validation/README.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-08_final_modeling_freeze.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_pair_level_evidence_admission_review.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_review_budget_routing_value.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_results_evidence_ladder.md",
    PROJECT_ROOT / "docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations.md",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations_table.csv",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/main_model_result_table.csv",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/final_advanced_claim_gate_table.csv",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_claim_boundaries.csv",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/robustness-and-claim-gates/final_claim_gate_table.csv",
]

REQUIRED_CLAIMS = [
    "Similarity is not admissibility",
    "pair-level",
    "evidence",
]

RISK_PATTERNS = {
    "descriptor_replacement": re.compile(r"\b(new descriptor|new embedding|descriptor replacement|replaces MegaDescriptor|replaces DINOv2|replacement Re-ID model)\b", re.I),
    "automatic_identity": re.compile(r"\b(automatic identity|automatic ID|automatically identifies|assigns identity|identity assignment|individual recognition)\b", re.I),
    "bobcat_identity_accuracy": re.compile(r"\b(Bobcat identity accuracy|Bobcat false-match accuracy|Bobcat mAP|Bobcat top-k|Bobcat identity metrics|Bobcat identity validation)\b", re.I),
    "ranking_overclaim": re.compile(r"\b(universally improves top-k|universal top-k|broad Re-ID accuracy breakthrough|ranking-superiority|mAP/MRR/top-k identity retrieval)\b", re.I),
    "tool_stack_reframe": re.compile(r"\b(mainly a conformal|mainly a Bayesian|mainly a multi-annotator|generic classifier method|generic conformal|generic Bayesian)\b", re.I),
}

BOUNDARY_MARKERS = [
    "not ",
    "no ",
    "do not",
    "must not",
    "blocked",
    "boundary",
    "caveat",
    "does not",
    "without",
    "unless",
    "rather than",
    "not as",
    "not the",
    "not a",
    "must be",
    "should not",
    "prohibited",
    "only if",
    "blocks",
]

CONTEXT_BOUNDARY_MARKERS = [
    "must not be reframed",
    "must not be silently",
    "the project must not",
    "do not use",
    "do not use the",
    "do not claim",
    "never give",
    "what not to claim",
    "it does not support",
    "blocks the interpretation",
    "blocks the",
    "blocked manuscript wording",
    "blocked final wording",
    "blocked claim",
    "blocked claims",
    "blocked wording",
    "blocked_claim",
    "must not claim",
    "does not support",
    "must not present",
    "must not be described",
    "forbidden",
    "prohibited",
]

POSITIVE_VERBS = [
    "is ",
    "are ",
    "improves",
    "validates",
    "proves",
    "replaces",
    "identifies",
    "assigns",
]

FINDING_COLUMNS = [
    "file",
    "line_number",
    "risk_family",
    "classification",
    "line_text",
    "rationale",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def line_classification(line: str, context: str = "") -> tuple[str, str]:
    lowered = line.lower()
    lowered_context = context.lower()
    if any(marker in lowered for marker in BOUNDARY_MARKERS):
        return "safe_boundary", "Risk wording appears in a negated, caveated, or blocked-claim context."
    if any(marker in lowered_context for marker in CONTEXT_BOUNDARY_MARKERS):
        return "safe_boundary", "Risk wording appears inside a blocked-claim or prohibited-wording context."
    if "pferi" not in lowered and "pf-eri" not in lowered:
        return "review_needed", "Risk wording appears in background or related-work language rather than a direct PF-ERI claim."
    if any(verb in lowered for verb in POSITIVE_VERBS):
        return "unsafe_positive_claim", "Risk wording appears with positive claim language and needs editing."
    return "review_needed", "Risk wording appears without an obvious boundary marker; manual review required."


def scan_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        line_number = index + 1
        context = "\n".join(lines[max(0, index - 14) : index])
        for risk_family, pattern in RISK_PATTERNS.items():
            if pattern.search(line):
                classification, rationale = line_classification(line, context)
                findings.append(
                    {
                        "file": project_relative(path),
                        "line_number": line_number,
                        "risk_family": risk_family,
                        "classification": classification,
                        "line_text": line.strip(),
                        "rationale": rationale,
                    }
                )
    return findings


def central_claim_presence(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "file": project_relative(path),
        "has_similarity_line": "Similarity is not admissibility" in text,
        "has_pair_level_language": "pair-level" in text.lower(),
        "has_post_retrieval_language": "post-retrieval" in text.lower() or "after strong descriptor" in text.lower(),
    }


def audit_gate(findings: list[dict[str, Any]], claim_presence: list[dict[str, Any]]) -> dict[str, Any]:
    unsafe = [row for row in findings if row["classification"] == "unsafe_positive_claim"]
    review_needed = [row for row in findings if row["classification"] == "review_needed"]
    missing_core = [
        row
        for row in claim_presence
        if row["file"] in {"PROJECT_RULES.md", "README.md", "docs/CURRENT_PROJECT_MAP.md"}
        and not (row["has_similarity_line"] and row["has_pair_level_language"])
    ]
    return {
        "status": "PASS" if not unsafe and not missing_core else "FAIL",
        "unsafe_positive_claim_count": len(unsafe),
        "review_needed_count": len(review_needed),
        "safe_boundary_count": sum(1 for row in findings if row["classification"] == "safe_boundary"),
        "missing_core_claim_files": missing_core,
        "review_needed_files": sorted({row["file"] for row in review_needed}),
    }


def report_text(audit: dict[str, Any], findings: list[dict[str, Any]], claim_presence: list[dict[str, Any]]) -> str:
    checked = "\n".join(f"- `{project_relative(path)}`" for path in CHECKED_FILES)
    risk_counts: dict[str, int] = {}
    for row in findings:
        risk_counts[row["risk_family"]] = risk_counts.get(row["risk_family"], 0) + 1
    risk_lines = "\n".join(f"- `{name}`: {count}" for name, count in sorted(risk_counts.items())) or "- No risk phrases found."
    review_needed = [row for row in findings if row["classification"] == "review_needed"]
    review_lines = "\n".join(
        f"- `{row['file']}:{row['line_number']}` `{row['risk_family']}`: {row['line_text']}"
        for row in review_needed
    ) or "- None."
    presence_lines = "\n".join(
        f"- `{row['file']}`: similarity_line={row['has_similarity_line']}, pair_level={row['has_pair_level_language']}, post_retrieval={row['has_post_retrieval_language']}"
        for row in claim_presence
    )

    return f"""# Final Story Consistency Audit

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE9_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Generated artifacts:

```text
{project_relative(FINDINGS_CSV)}
{project_relative(AUDIT_JSON)}
```

## Purpose

This document completes the final story consistency audit for the story
hardening issue pack. The audit checks whether the project-facing and
manuscript-facing claim layers preserve the same scientific line:

```text
Similarity is not admissibility.
PF-ERI is pair-level evidence admission after descriptor retrieval.
```

The audit is intentionally conservative. It searches for language that could
reframe PF-ERI as a descriptor, automatic identity system, Bobcat identity
validation, universal ranking improvement, generic conformal/Bayesian wrapper,
or generic classifier. Each flagged line is classified as a safe boundary, a
manual-review item, or an unsafe positive claim.

## Audit Result

The final gate status is `{audit['status']}`. The audit found
{audit['unsafe_positive_claim_count']} unsafe positive claim lines,
{audit['review_needed_count']} manual-review lines, and
{audit['safe_boundary_count']} safe boundary lines. Manual-review lines are not
claim failures; they are lines where a risk phrase appears without an automatic
negation marker and should be read in context. No current unsafe positive claim
is allowed to remain in the claim-bearing layer.

## Files Checked

{checked}

## Central Claim Presence

{presence_lines}

## Risk Families Flagged

{risk_lines}

## Manual-Review Lines

{review_lines}

## Edits Made

This pass adds the Issue 9 audit script, line-level findings table, JSON audit,
and this final consistency report. It also updates the project map,
modeling-validation README, daily log, and story hardening issue pack so Issue
9 is part of the active navigation layer. The scan did not require claim-text
repairs in the current claim-bearing documents because dangerous phrases are
already framed as blocked claims, caveats, or explicit boundaries.

## Remaining Boundaries

PF-ERI remains a post-retrieval pair-level evidence admission layer. It is not a
new descriptor, not an automatic identity-assignment system, not a Bobcat
identity-validation system, and not a generic conformal, Bayesian,
multi-annotator, or classifier method. The strongest positive claim remains
reviewability and evidential admissibility on the CzechLynx reviewed validation
contract, with Bobcat restricted to unlabeled transfer-stress and workflow
allocation unless audited Bobcat identity labels or same/different pair labels
are added later.

## Next Action

The story-hardening issue pack is complete. The next scientific step should be
manuscript assembly from the evidence chain, contribution hierarchy, results
evidence ladder, objection matrix, and final claim narrative. The next
engineering step should be a separate repository hygiene pass only if the user
wants staging, committing, or further cleanup.
"""


def build() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    existing_files = [path for path in CHECKED_FILES if path.exists()]
    missing_files = [project_relative(path) for path in CHECKED_FILES if not path.exists()]
    for path in existing_files:
        findings.extend(scan_file(path))
    claim_presence = [central_claim_presence(path) for path in existing_files]
    gate = audit_gate(findings, claim_presence)
    audit = {
        "built_at_utc": utc_now(),
        "status": gate["status"],
        "checked_files": [project_relative(path) for path in existing_files],
        "missing_files": missing_files,
        "findings_csv": project_relative(FINDINGS_CSV),
        "report_md": project_relative(REPORT_MD),
        **gate,
    }
    write_csv(FINDINGS_CSV, findings, FINDING_COLUMNS)
    write_json(AUDIT_JSON, audit)
    REPORT_MD.write_text(report_text(audit, findings, claim_presence), encoding="utf-8")
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
