#!/usr/bin/env python3
"""Build Phase18N confirmatory blinded review packets.

Phase18N is the pre-specified confirmatory expansion for PF-ERI pair-level
evidence admission. It samples from strong-descriptor CzechLynx candidate-pair
features and writes both a hidden full packet and reviewer-facing blind forms.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

try:
    from phase18_pipeline_utils import (
        now_utc,
        project_relative,
        read_csv,
        resolve_project_path,
        to_float,
        write_csv,
        write_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
    from phase18_pipeline_utils import (
        now_utc,
        project_relative,
        read_csv,
        resolve_project_path,
        to_float,
        write_csv,
        write_json,
    )


DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
RANDOM_SEED = 20260710
SAMPLE_PER_DESCRIPTOR = 600
REVIEWER_COUNT = 3
DEFAULT_OUTPUT_ROOT = Path("archive/pferi_v1/outputs/modeling-validation/pair-level-validation/confirmatory-review-packet")
DEFAULT_PHASE18A_MANIFEST = Path(
    "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/frozen-feature-manifest/"
    "legacy-code18a_frozen_image_feature_manifest.csv"
)
DEFAULT_FEATURE_ROOT = Path("archive/pferi_v1/outputs/modeling-validation/pair-level-validation/strong-pf-eri-pair-features")
IMAGE_FALLBACK_DIRS = [
    Path("data/frozen/pferi_v2/lynx-wild/images"),
    Path("data/frozen/pferi_v2/lynx-urban/images"),
    Path("data/frozen/pferi_v2/bobcat-wild/images"),
    Path("data/frozen/pferi_v2/bobcat-urban/images"),
]

FULL_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "sample_scope",
    "stratum_id",
    "rank_bin",
    "similarity_stratum",
    "quality_stratum",
    "identity_stratum",
    "admission_stratum",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "same_identity_known_id",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "query_image_quality_score",
    "candidate_image_quality_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "query_split_role",
    "reviewability_decision",
    "not_ready_reason",
    "secondary_reason",
    "review_confidence",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
    "claim_boundary",
]

BLIND_COLUMNS = [
    "review_pair_id",
    "query_image_path",
    "candidate_image_path",
    "reviewability_decision",
    "not_ready_reason",
    "secondary_reason",
    "review_confidence",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
]

CODEBOOK_COLUMNS = ["field", "allowed_value", "definition"]
CODEBOOK_ROWS = [
    {
        "field": "reviewability_decision",
        "allowed_value": "review_ready",
        "definition": "The pair contains enough comparable visual evidence for responsible individual-level review, including confident rejection.",
    },
    {
        "field": "reviewability_decision",
        "allowed_value": "not_review_ready",
        "definition": "The pair should not enter immediate evidence use because comparable pair evidence is inadequate.",
    },
    {
        "field": "reviewability_decision",
        "allowed_value": "uncertain",
        "definition": "The reviewer cannot determine reviewability from the pair after considering the reason fields.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "low_evidence",
        "definition": "At least one image is too weak, small, occluded, blurred, distant, overexposed, or otherwise low-evidence.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "non_comparable",
        "definition": "Images are visible but body region, side, pose, scale, viewpoint, or pattern evidence cannot be compared.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "both_low_evidence_and_non_comparable",
        "definition": "Both evidence weakness and non-comparability affect the pair.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "identity_uncertain_but_reviewable",
        "definition": "The pair is reviewable, but identity itself is hard; normally pair decision should be review_ready.",
    },
    {"field": "not_ready_reason", "allowed_value": "other", "definition": "Use only with notes."},
    {"field": "review_confidence", "allowed_value": "high", "definition": "Reviewer is confident in the reviewability decision."},
    {"field": "review_confidence", "allowed_value": "medium", "definition": "Reviewer has moderate confidence."},
    {"field": "review_confidence", "allowed_value": "low", "definition": "Reviewer has low confidence."},
]


def rank_bin(rank_text: str) -> str:
    rank = int(float(rank_text))
    if rank == 1:
        return "rank_01"
    if rank <= 5:
        return "rank_02_05"
    if rank <= 10:
        return "rank_06_10"
    return "rank_11_20"


def quantile_cutoffs(rows: list[dict[str, str]], column: str) -> tuple[float, float]:
    values = sorted(to_float(row[column]) for row in rows)
    if not values:
        return 0.0, 0.0
    low_idx = int((len(values) - 1) * 0.333333)
    high_idx = int((len(values) - 1) * 0.666667)
    return float(values[low_idx]), float(values[high_idx])


def tertile(value: float, low_cutoff: float, high_cutoff: float, prefix: str) -> str:
    if value <= low_cutoff:
        return f"{prefix}_low"
    if value <= high_cutoff:
        return f"{prefix}_mid"
    return f"{prefix}_high"


def manifest_by_image_id(path: Path) -> dict[str, dict[str, str]]:
    return {row["phase18_image_id"]: row for row in read_csv(path)}


def resolve_existing_image_path(value: str) -> tuple[Path | None, bool]:
    direct = resolve_project_path(value)
    if direct.exists():
        return direct, False
    name = Path(value).name
    for base in IMAGE_FALLBACK_DIRS:
        candidate = resolve_project_path(str(base / name))
        if candidate.exists():
            return candidate, True
    return None, False


def allocate_counts(groups: dict[str, list[dict[str, str]]], total: int) -> dict[str, int]:
    nonempty = {key: rows for key, rows in groups.items() if rows}
    if not nonempty:
        return {}
    base = total // len(nonempty)
    allocation = {key: min(base, len(rows)) for key, rows in nonempty.items()}
    remaining = total - sum(allocation.values())
    ordered = sorted(nonempty, key=lambda key: len(nonempty[key]) - allocation[key], reverse=True)
    while remaining > 0:
        progressed = False
        for key in ordered:
            if allocation[key] < len(nonempty[key]):
                allocation[key] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break
    return allocation


def add_strata(rows: list[dict[str, str]]) -> dict[str, Any]:
    sim_low, sim_high = quantile_cutoffs(rows, "descriptor_similarity_percentile")
    quality_low, quality_high = quantile_cutoffs(rows, "weakest_image_quality_score")
    admission_low, admission_high = quantile_cutoffs(rows, "pf_eri_admissibility_score")
    for row in rows:
        row["rank_bin"] = rank_bin(row["candidate_rank_descriptor"])
        row["similarity_stratum"] = tertile(
            to_float(row["descriptor_similarity_percentile"]), sim_low, sim_high, "similarity"
        )
        row["quality_stratum"] = tertile(
            to_float(row["weakest_image_quality_score"]), quality_low, quality_high, "quality"
        )
        row["identity_stratum"] = "same_identity" if row["same_identity"] == "yes" else "different_identity"
        row["admission_stratum"] = tertile(
            to_float(row["pf_eri_admissibility_score"]), admission_low, admission_high, "admission"
        )
        row["stratum_id"] = "__".join(
            [
                row["rank_bin"],
                row["similarity_stratum"],
                row["quality_stratum"],
                row["identity_stratum"],
                row["admission_stratum"],
            ]
        )
    return {
        "similarity_cutoffs": {"low_mid": sim_low, "mid_high": sim_high},
        "quality_cutoffs": {"low_mid": quality_low, "mid_high": quality_high},
        "admission_cutoffs": {"low_mid": admission_low, "mid_high": admission_high},
    }


def hidden_to_blind(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column, "") for column in BLIND_COLUMNS}


def row_to_output(
    descriptor_name: str,
    source: dict[str, str],
    by_id: dict[str, dict[str, str]],
    idx: int,
) -> dict[str, Any]:
    query = by_id[source["query_image_id"]]
    candidate = by_id[source["candidate_image_id"]]
    query_path, _query_fallback = resolve_existing_image_path(query["frozen_image_path"])
    candidate_path, _candidate_fallback = resolve_existing_image_path(candidate["frozen_image_path"])
    if query_path is None or candidate_path is None:
        raise ValueError(f"missing image for pair {source['pair_id']}")
    return {
        "review_pair_id": f"phase18n_{descriptor_name}_blind_{idx:04d}",
        "descriptor_name": descriptor_name,
        "sample_scope": "confirmatory_stratified_blind_review",
        "stratum_id": source["stratum_id"],
        "rank_bin": source["rank_bin"],
        "similarity_stratum": source["similarity_stratum"],
        "quality_stratum": source["quality_stratum"],
        "identity_stratum": source["identity_stratum"],
        "admission_stratum": source["admission_stratum"],
        "query_image_id": source["query_image_id"],
        "candidate_image_id": source["candidate_image_id"],
        "query_image_path": project_relative(query_path),
        "candidate_image_path": project_relative(candidate_path),
        "same_identity_known_id": source["same_identity"],
        "candidate_rank_descriptor": source["candidate_rank_descriptor"],
        "descriptor_similarity": source["descriptor_similarity"],
        "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
        "query_image_quality_score": source["query_image_quality_score"],
        "candidate_image_quality_score": source["candidate_image_quality_score"],
        "weakest_image_quality_score": source["weakest_image_quality_score"],
        "pair_geometry_score": source["pair_geometry_score"],
        "descriptor_evidence_conflict_score": source["descriptor_evidence_conflict_score"],
        "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
        "pf_eri_review_score": source["pf_eri_review_score"],
        "pf_eri_route": source["pf_eri_route"],
        "query_split_role": source["query_split_role"],
        "reviewability_decision": "",
        "not_ready_reason": "",
        "secondary_reason": "",
        "review_confidence": "",
        "visibility_notes": "",
        "reviewer_id": "",
        "review_timestamp": "",
        "claim_boundary": "Phase18N confirmatory reviewability packet; labels are not identity labels.",
    }


def build_descriptor_confirmatory_packet(
    descriptor_name: str,
    features_csv: Path,
    phase18a_manifest: Path,
    output_dir: Path,
    sample_size: int = SAMPLE_PER_DESCRIPTOR,
    reviewer_count: int = REVIEWER_COUNT,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    by_id = manifest_by_image_id(phase18a_manifest)
    candidate_rows = [row for row in read_csv(features_csv) if row["query_split_role"] == "evaluation"]
    rows = []
    missing_image_rows = 0
    missing_manifest_rows = 0
    fallback_image_reference_count = 0
    for row in candidate_rows:
        query = by_id.get(row["query_image_id"])
        candidate = by_id.get(row["candidate_image_id"])
        if query is None or candidate is None:
            missing_manifest_rows += 1
            continue
        query_path, query_fallback = resolve_existing_image_path(query["frozen_image_path"])
        candidate_path, candidate_fallback = resolve_existing_image_path(candidate["frozen_image_path"])
        if query_path is None or candidate_path is None:
            missing_image_rows += 1
            continue
        fallback_image_reference_count += int(query_fallback) + int(candidate_fallback)
        rows.append(row)
    if len(rows) < sample_size:
        raise ValueError(
            f"{descriptor_name} has {len(rows)} image-available evaluation rows, below requested {sample_size}; "
            f"missing_manifest_rows={missing_manifest_rows} missing_image_rows={missing_image_rows}"
        )
    cutoffs = add_strata(rows)
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["stratum_id"], []).append(row)
    allocation = allocate_counts(groups, sample_size)
    if sum(allocation.values()) != sample_size:
        raise ValueError(f"could allocate {sum(allocation.values())} rows, requested {sample_size}")

    rng = random.Random(random_seed + sum(ord(ch) for ch in descriptor_name))
    selected = []
    stratum_counts = {}
    stratum_input_counts = {}
    for stratum_id, count in sorted(allocation.items()):
        chosen = rng.sample(groups[stratum_id], count)
        selected.extend(chosen)
        stratum_counts[stratum_id] = count
        stratum_input_counts[stratum_id] = len(groups[stratum_id])
    rng.shuffle(selected)

    output_rows = [row_to_output(descriptor_name, row, by_id, idx) for idx, row in enumerate(selected, start=1)]
    blind_rows = [hidden_to_blind(row) for row in output_rows]

    output_dir.mkdir(parents=True, exist_ok=True)
    full_csv = output_dir / "phase18n_confirmatory_review_packet.csv"
    blind_csv = output_dir / "phase18n_blind_review_form.csv"
    codebook_csv = output_dir / "phase18n_reviewability_codebook.csv"
    write_csv(full_csv, output_rows, FULL_COLUMNS)
    write_csv(blind_csv, blind_rows, BLIND_COLUMNS)
    write_csv(codebook_csv, CODEBOOK_ROWS, CODEBOOK_COLUMNS)
    for reviewer_idx in range(1, reviewer_count + 1):
        reviewer_rows = [dict(row, reviewer_id=f"reviewer_{reviewer_idx}") for row in blind_rows]
        write_csv(output_dir / f"reviewer_{reviewer_idx}_blind_review_form.csv", reviewer_rows, BLIND_COLUMNS)

    selected_queries = {row["query_image_id"] for row in output_rows}
    selected_pairs = {tuple(sorted([row["query_image_id"], row["candidate_image_id"]])) for row in output_rows}
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "features_csv": project_relative(features_csv),
        "phase18a_manifest": project_relative(phase18a_manifest),
        "full_csv": project_relative(full_csv),
        "blind_csv": project_relative(blind_csv),
        "codebook_csv": project_relative(codebook_csv),
        "reviewer_count": reviewer_count,
        "reviewer_form_paths": [
            project_relative(output_dir / f"reviewer_{idx}_blind_review_form.csv")
            for idx in range(1, reviewer_count + 1)
        ],
        "evaluation_input_rows": len(rows),
        "raw_evaluation_input_rows": len(candidate_rows),
        "missing_manifest_rows_excluded": missing_manifest_rows,
        "missing_image_rows_excluded": missing_image_rows,
        "fallback_image_reference_count": fallback_image_reference_count,
        "image_fallback_dirs": [project_relative(resolve_project_path(str(path))) for path in IMAGE_FALLBACK_DIRS],
        "requested_sample_rows": sample_size,
        "sample_rows": len(output_rows),
        "unique_query_image_count": len(selected_queries),
        "unordered_pair_count": len(selected_pairs),
        "duplicate_unordered_pair_count": len(output_rows) - len(selected_pairs),
        "stratum_count": len(stratum_counts),
        "stratum_counts": stratum_counts,
        "stratum_input_counts": stratum_input_counts,
        "cutoffs": cutoffs,
        "blind_columns": BLIND_COLUMNS,
        "hidden_columns_excluded_from_blind": [
            "descriptor_name",
            "same_identity_known_id",
            "identity_stratum",
            "descriptor_similarity",
            "descriptor_similarity_percentile",
            "pf_eri_admissibility_score",
            "pf_eri_review_score",
            "pf_eri_route",
            "admission_stratum",
            "quality_stratum",
            "similarity_stratum",
        ],
        "random_seed": random_seed,
        "status": "PASS",
        "claim_boundary": "Confirmatory blind packet for reviewability/admissibility; not identity accuracy.",
    }
    write_json(output_dir / "phase18n_confirmatory_review_packet_audit.json", audit)
    return audit


def build_phase18n_confirmatory_review_packet(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    phase18a_manifest: Path = DEFAULT_PHASE18A_MANIFEST,
    feature_root: Path = DEFAULT_FEATURE_ROOT,
    sample_size_per_descriptor: int = SAMPLE_PER_DESCRIPTOR,
    reviewer_count: int = REVIEWER_COUNT,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    audits = {}
    for descriptor_name in DESCRIPTORS:
        features_csv = feature_root / descriptor_name / "legacy-code18d_pf_eri_pair_features.csv"
        audits[descriptor_name] = build_descriptor_confirmatory_packet(
            descriptor_name=descriptor_name,
            features_csv=features_csv,
            phase18a_manifest=phase18a_manifest,
            output_dir=output_root / descriptor_name,
            sample_size=sample_size_per_descriptor,
            reviewer_count=reviewer_count,
            random_seed=random_seed,
        )
    combined = {
        "built_at_utc": now_utc(),
        "descriptor_names": DESCRIPTORS,
        "sample_size_per_descriptor": sample_size_per_descriptor,
        "reviewer_count": reviewer_count,
        "total_sample_rows": sum(audit["sample_rows"] for audit in audits.values()),
        "descriptor_audits": audits,
        "status": "PASS",
        "claim_boundary": "Phase18N confirmatory expansion packet; review labels are not identity labels.",
    }
    write_json(output_root / "phase18n_confirmatory_review_packet_combined_audit.json", combined)
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--phase18a-manifest", type=Path, default=DEFAULT_PHASE18A_MANIFEST)
    parser.add_argument("--feature-root", type=Path, default=DEFAULT_FEATURE_ROOT)
    parser.add_argument("--sample-size-per-descriptor", type=int, default=SAMPLE_PER_DESCRIPTOR)
    parser.add_argument("--reviewer-count", type=int, default=REVIEWER_COUNT)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18n_confirmatory_review_packet(
        output_root=args.output_root,
        phase18a_manifest=args.phase18a_manifest,
        feature_root=args.feature_root,
        sample_size_per_descriptor=args.sample_size_per_descriptor,
        reviewer_count=args.reviewer_count,
        random_seed=args.random_seed,
    )
    print(
        "PASS Phase18N confirmatory review packet "
        f"total_sample_rows={audit['total_sample_rows']} output_root={args.output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
