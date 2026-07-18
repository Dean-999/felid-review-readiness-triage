#!/usr/bin/env python3
"""Build Issue 8 reviewer objection matrix and claim gate."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8"
MATRIX_CSV = OUTPUT_DIR / "issue8_reviewer_objection_matrix.csv"
CLAIM_GATE_JSON = OUTPUT_DIR / "issue8_claim_gate.json"
AUDIT_JSON = OUTPUT_DIR / "issue8_objection_matrix_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md"
FINAL_CLAIM_NARRATIVE = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md"
)

REQUIRED_OBJECTIONS = [
    "reviewability_subjectivity",
    "quality_proxy",
    "descriptor_similarity_proxy",
    "targeted_sample_or_full_queue_representativeness",
    "human_label_reliability",
    "bobcat_identity_label_absence",
    "partial_feature_sensitivity_non_estimable_features",
]

MATRIX_COLUMNS = [
    "objection_id",
    "reviewer_objection",
    "answer_type",
    "answer_summary",
    "primary_artifact",
    "appendix_or_sensitivity_artifact",
    "safe_wording",
    "blocked_wording",
    "remaining_boundary",
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


def objection_rows() -> list[dict[str, str]]:
    return [
        {
            "objection_id": "reviewability_subjectivity",
            "reviewer_objection": "Reviewability may be a subjective human preference rather than a defensible scientific endpoint.",
            "answer_type": "answered_by_main_evidence",
            "answer_summary": "The manuscript defines reviewability as the pair-level evidential-admissibility endpoint and places construct validity first in the results ladder.",
            "primary_artifact": "docs/modeling-validation/2026-07-09_results_evidence_ladder.md",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_analysis_audit.json",
            "safe_wording": "PF-ERI is evaluated against blind reliability-supported reviewability and evidential-admissibility labels.",
            "blocked_wording": "Human reviewability labels prove animal identity truth or complete causal mechanisms.",
            "remaining_boundary": "Reviewability is a reference construct for evidence admission, not objective identity truth.",
        },
        {
            "objection_id": "quality_proxy",
            "reviewer_objection": "PF-ERI may only be an image-quality filter.",
            "answer_type": "answered_by_appendix_sensitivity",
            "answer_summary": "Issue 4 tests quality-matched and high-quality subsets; pooled contrasts remain positive, while non-estimable quality fields are explicitly bounded.",
            "primary_artifact": "docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv; archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv",
            "safe_wording": "PF-ERI is not reducible to the estimable image-quality controls in the current CzechLynx reviewed pairs.",
            "blocked_wording": "PF-ERI proves universal superiority over every image-quality feature or every descriptor-specific quality stratum.",
            "remaining_boundary": "Several nominal quality fields are constant or sparse in the 400-row reviewed table.",
        },
        {
            "objection_id": "descriptor_similarity_proxy",
            "reviewer_objection": "PF-ERI may only restate descriptor similarity.",
            "answer_type": "answered_by_main_evidence_and_appendix_sensitivity",
            "answer_summary": "Issue 3 compares descriptor-only and PF-ERI models; Issue 4 adds high-similarity and rank/similarity-stratified checks.",
            "primary_artifact": "docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv; archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv",
            "safe_wording": "Similarity and quality do not fully exhaust the human reviewability construct.",
            "blocked_wording": "PF-ERI always improves descriptor ranking, mAP, MRR, or top-k identity performance.",
            "remaining_boundary": "The active-control AUROC/AUPRC increment over descriptor plus quality is small and descriptor-specific increments are not uniformly positive.",
        },
        {
            "objection_id": "targeted_sample_or_full_queue_representativeness",
            "reviewer_objection": "Targeted reviewed samples could inflate the apparent PF-ERI effect.",
            "answer_type": "answered_by_claim_boundary",
            "answer_summary": "The final results ladder uses CzechLynx reviewed candidate pairs for evidence admission and treats targeted mechanism samples as mechanism support, not population estimates.",
            "primary_artifact": "docs/modeling-validation/2026-07-09_results_evidence_ladder.md",
            "appendix_or_sensitivity_artifact": "docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md",
            "safe_wording": "Targeted and stratified reviewed samples support pair-level reviewability and mechanism checks within the reviewed validation contract.",
            "blocked_wording": "The reviewed sample estimates the full retrieval-queue population effect or deployment population performance.",
            "remaining_boundary": "Full-population queue estimates require a separately sampled and audited full-queue validation design.",
        },
        {
            "objection_id": "human_label_reliability",
            "reviewer_objection": "Majority labels or reviewer labels may be unstable.",
            "answer_type": "answered_by_main_evidence",
            "answer_summary": "Blind reliability artifacts support the reviewability labels and final claim narrative records reviewer agreement and provenance.",
            "primary_artifact": "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_analysis_audit.json; archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis-reviewer2/blind_reliability_analysis_audit.json",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_disagreement_appendix.csv",
            "safe_wording": "The labels are blind reliability-supported reviewability labels.",
            "blocked_wording": "Blind review proves animal identity truth or removes all human-label uncertainty.",
            "remaining_boundary": "Reviewer disagreement remains a measurement limitation and should be reported, not hidden.",
        },
        {
            "objection_id": "bobcat_identity_label_absence",
            "reviewer_objection": "Bobcat transfer results cannot validate identity performance without Bobcat individual labels.",
            "answer_type": "explicitly_blocked_as_claim",
            "answer_summary": "Bobcat is restricted to transfer-stress and workflow-allocation diagnostics; identity accuracy, false-match accuracy, mAP, MRR, and top-k claims are blocked.",
            "primary_artifact": "archive/pferi_v1/outputs/modeling-validation/bobcat-wild-urban-transfer-stress/README.md",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/strong-bobcat-transfer-readiness/megadescriptor_l_384/legacy-code18f_bobcat_transfer_readiness_audit.json; archive/pferi_v1/outputs/modeling-validation/pair-level-validation/strong-bobcat-transfer-readiness/dinov2_vitl14/legacy-code18f_bobcat_transfer_readiness_audit.json",
            "safe_wording": "Bobcat is an unlabeled transfer-stress and workflow-allocation context.",
            "blocked_wording": "PF-ERI validates Bobcat identity accuracy, Bobcat false-match accuracy, Bobcat mAP, or Bobcat top-k retrieval.",
            "remaining_boundary": "Audited Bobcat individual IDs or same/different pair labels are required before any Bobcat identity claim.",
        },
        {
            "objection_id": "partial_feature_sensitivity_non_estimable_features",
            "reviewer_objection": "Some PF-ERI feature mechanisms are not fully estimable because fields are constant or sparse.",
            "answer_type": "answered_by_appendix_sensitivity_and_claim_boundary",
            "answer_summary": "Issue 4 reports the estimable sensitivity results and explicitly keeps constant or sparse fields as boundaries.",
            "primary_artifact": "docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md",
            "appendix_or_sensitivity_artifact": "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_similarity_sensitivity_audit.json",
            "safe_wording": "PF-ERI shows pair-level reviewability signal under estimable quality and similarity checks.",
            "blocked_wording": "Every PF-ERI feature family is independently validated, causal, and equally supported.",
            "remaining_boundary": "Feature-level causal and mechanism claims remain bounded where current feature variation is insufficient.",
        },
    ]


def claim_gate(rows: list[dict[str, str]]) -> dict[str, Any]:
    missing = sorted(set(REQUIRED_OBJECTIONS) - {row["objection_id"] for row in rows})
    answer_types = {row["objection_id"]: row["answer_type"] for row in rows}
    unsupported = [
        row["objection_id"]
        for row in rows
        if not row["primary_artifact"].strip() and not row["appendix_or_sensitivity_artifact"].strip()
    ]
    return {
        "status": "PASS" if not missing and not unsupported else "FAIL",
        "built_at_utc": utc_now(),
        "central_claim": "Similarity is not admissibility.",
        "required_objection_count": len(REQUIRED_OBJECTIONS),
        "matrix_row_count": len(rows),
        "missing_required_objections": missing,
        "unsupported_objections": unsupported,
        "answer_types_by_objection": answer_types,
        "allowed_claim": "PF-ERI is a post-retrieval pair-level evidence admission layer for descriptor-retrieved wildlife Re-ID candidate pairs.",
        "blocked_claims": [
            "PF-ERI is a new descriptor or embedding.",
            "PF-ERI automatically identifies individuals.",
            "PF-ERI validates Bobcat identity accuracy.",
            "PF-ERI proves universal descriptor-ranking improvement.",
            "PF-ERI proves every feature mechanism causally.",
            "PF-ERI provides distribution-free cross-domain guarantees.",
        ],
    }


def report_text(rows: list[dict[str, str]], gate: dict[str, Any]) -> str:
    table_lines = [
        "| Objection | Answer type | Evidence answer | Safe wording | Blocked wording |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        table_lines.append(
            "| {objection} | `{answer_type}` | {answer_summary} Artifacts: `{primary}`; `{appendix}`. | {safe} | {blocked} |".format(
                objection=row["reviewer_objection"],
                answer_type=row["answer_type"],
                answer_summary=row["answer_summary"],
                primary=row["primary_artifact"],
                appendix=row["appendix_or_sensitivity_artifact"],
                safe=row["safe_wording"],
                blocked=row["blocked_wording"],
            )
        )

    return f"""# Reviewer Objection Matrix And Claim Gate

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE8_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Generated artifacts:

```text
{project_relative(MATRIX_CSV)}
{project_relative(CLAIM_GATE_JSON)}
{project_relative(AUDIT_JSON)}
```

## Purpose

This document completes Issue 8 of the story hardening issue pack. Its purpose
is to make the manuscript rebuttal-ready without making the claims larger than
the evidence. The rule is strict: no reviewer objection is answered by
reassurance alone. Each objection must be answered by main evidence, appendix
sensitivity, or an explicit blocked-claim boundary.

The central claim remains:

```text
Similarity is not admissibility.
```

The claim gate status is `{gate["status"]}`. The allowed positive claim is that
PF-ERI is a post-retrieval pair-level evidence admission layer for
descriptor-retrieved wildlife Re-ID candidate pairs. The gate blocks descriptor
replacement, automatic identity assignment, Bobcat identity accuracy,
unqualified retrieval-ranking improvement, universal feature-causal claims, and
distribution-free cross-domain guarantees.

## Objection Matrix

{chr(10).join(table_lines)}

## Claim Gate Interpretation

The matrix protects the project in two ways. First, it prevents overclaiming by
making the blocked wording explicit next to each safe wording. This is
important because several attractive but unsafe claims are close to the current
results, especially Bobcat identity performance, top-k identity improvement,
and universal feature-mechanism validation. Second, it keeps the main
contribution focused on pair-level evidence admission rather than on the
supporting statistical tools. Reviewer reliability, quality/similarity
sensitivity, review-budget routing, and transfer-stress diagnostics are
safeguards around the evidence-admission claim.

The strongest positive statement is therefore bounded but useful. PF-ERI
supports a pair-level reviewability and evidential-admissibility signal after
strong descriptor retrieval, and this signal is not exhausted by the estimable
descriptor-similarity and image-quality controls in the reviewed CzechLynx
validation setting. The Bobcat analyses remain valuable as transfer-stress and
workflow-allocation diagnostics, but they do not validate identity accuracy.

## Issue 8 Acceptance Check

The matrix covers reviewability subjectivity, the image-quality proxy
alternative, the descriptor-similarity proxy alternative, targeted-sample or
full-queue representativeness, human label reliability, Bobcat identity-label
absence, and partial feature sensitivity with non-estimable features. Each
objection has an evidence artifact, appendix sensitivity artifact, or explicit
blocked-claim boundary. The final claim narrative is updated to point to this
matrix and preserve the same safe and blocked wording.
"""


def update_final_claim_narrative(gate: dict[str, Any]) -> None:
    marker = "## Reviewer Objection Matrix Gate\n"
    block = f"""{marker}
Issue 8 adds a rebuttal-ready objection matrix and claim gate:

```text
{project_relative(MATRIX_CSV)}
{project_relative(CLAIM_GATE_JSON)}
```

Gate status: `{gate["status"]}`.

The matrix requires every major reviewer objection to be answered by main
evidence, appendix sensitivity, or an explicit blocked-claim boundary. It
covers reviewability subjectivity, quality-proxy and descriptor-similarity-proxy
alternatives, targeted-sample/full-queue representativeness, human label
reliability, Bobcat identity-label absence, and partial feature sensitivity.

Safe final wording remains: PF-ERI is a post-retrieval pair-level evidence
admission layer for descriptor-retrieved wildlife Re-ID candidate pairs.

Blocked final wording remains: PF-ERI is a new descriptor, automatically
identifies individuals, validates Bobcat identity accuracy, universally improves
top-k/mAP/MRR identity retrieval, proves every PF-ERI feature mechanism
causally, or provides unqualified distribution-free cross-domain guarantees.
"""
    text = FINAL_CLAIM_NARRATIVE.read_text(encoding="utf-8")
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n\n" + block
    else:
        text = text.rstrip() + "\n\n" + block
    FINAL_CLAIM_NARRATIVE.write_text(text, encoding="utf-8")


def build() -> dict[str, Any]:
    rows = objection_rows()
    gate = claim_gate(rows)
    write_csv(MATRIX_CSV, rows, MATRIX_COLUMNS)
    write_json(CLAIM_GATE_JSON, gate)
    write_json(
        AUDIT_JSON,
        {
            "built_at_utc": gate["built_at_utc"],
            "status": gate["status"],
            "matrix_csv": project_relative(MATRIX_CSV),
            "claim_gate_json": project_relative(CLAIM_GATE_JSON),
            "report_md": project_relative(REPORT_MD),
            "final_claim_narrative": project_relative(FINAL_CLAIM_NARRATIVE),
            "acceptance_criteria": {
                objection_id: objection_id in {row["objection_id"] for row in rows}
                for objection_id in REQUIRED_OBJECTIONS
            },
        },
    )
    REPORT_MD.write_text(report_text(rows, gate), encoding="utf-8")
    update_final_claim_narrative(gate)
    return gate


def main() -> int:
    gate = build()
    print(json.dumps(gate, indent=2, sort_keys=True))
    return 0 if gate["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
