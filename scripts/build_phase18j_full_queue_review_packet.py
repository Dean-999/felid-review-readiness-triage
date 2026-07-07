#!/usr/bin/env python3
"""Build Phase18J full-queue stratified reviewability packets."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any

try:
    from scripts.phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, to_float, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, to_float, write_csv, write_json


DEFAULT_OUTPUT_ROOT = Path("outputs/phase18/phase18j_full_queue_review_packet")
DEFAULT_PHASE18A_MANIFEST = Path("outputs/phase18/phase18a_frozen_feature_manifest/phase18a_frozen_image_feature_manifest.csv")
RANDOM_SEED = 20260703

DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
SAMPLE_PER_DESCRIPTOR = 300

FULL_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "sample_scope",
    "stratum_id",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "same_identity_known_id",
    "candidate_rank_descriptor",
    "rank_bin",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "admissibility_tertile",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "query_split_role",
    "reviewability_decision",
    "not_ready_reason",
    "secondary_reason",
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
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
]

CODEBOOK_COLUMNS = ["field", "allowed_value", "definition"]
CODEBOOK_ROWS = [
    {
        "field": "reviewability_decision",
        "allowed_value": "review_ready",
        "definition": "Both images expose enough comparable evidence for pair-level review.",
    },
    {
        "field": "reviewability_decision",
        "allowed_value": "not_review_ready",
        "definition": "The pair should not be treated as review-ready; choose a not_ready_reason.",
    },
    {
        "field": "reviewability_decision",
        "allowed_value": "uncertain",
        "definition": "Use only when the reviewer cannot determine reviewability after considering the reason options.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "low_evidence",
        "definition": "At least one image is too weak, small, occluded, blurry, distant, or low quality for reliable pair review.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "non_comparable",
        "definition": "Images are visible but body region, viewpoint, pose, scale, or evidence type cannot be compared.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "both_low_evidence_and_non_comparable",
        "definition": "Both evidence weakness and non-comparability are substantial.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "identity_uncertain_but_reviewable",
        "definition": "The pair is review-ready, but identity itself is difficult; normally decision should be review_ready.",
    },
    {
        "field": "not_ready_reason",
        "allowed_value": "other",
        "definition": "Use only with notes when no listed reason fits.",
    },
]


def manifest_by_image_id(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    by_id = {}
    for row in rows:
        by_id[row["phase18_image_id"]] = row
    return by_id


def rank_bin(rank_text: str) -> str:
    rank = int(float(rank_text))
    if rank == 1:
        return "rank_01"
    if rank <= 5:
        return "rank_02_05"
    if rank <= 10:
        return "rank_06_10"
    return "rank_11_20"


def add_admissibility_tertiles(rows: list[dict[str, str]]) -> None:
    values = sorted(to_float(row["pf_eri_admissibility_score"]) for row in rows)
    if not values:
        return
    q1 = values[int((len(values) - 1) * 0.333333)]
    q2 = values[int((len(values) - 1) * 0.666667)]
    for row in rows:
        value = to_float(row["pf_eri_admissibility_score"])
        if value <= q1:
            row["admissibility_tertile"] = "admissibility_low"
        elif value <= q2:
            row["admissibility_tertile"] = "admissibility_mid"
        else:
            row["admissibility_tertile"] = "admissibility_high"


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


def sample_descriptor_rows(
    descriptor_name: str,
    features_csv: Path,
    phase18a_manifest: Path,
    output_dir: Path,
    sample_size: int,
    random_seed: int,
) -> dict[str, Any]:
    by_id = manifest_by_image_id(phase18a_manifest)
    rows = [row for row in read_csv(features_csv) if row["query_split_role"] == "evaluation"]
    if not rows:
        raise ValueError(f"0 evaluation rows for {descriptor_name}")
    add_admissibility_tertiles(rows)
    for row in rows:
        row["rank_bin"] = rank_bin(row["candidate_rank_descriptor"])
        row["stratum_id"] = "__".join(
            [
                row["rank_bin"],
                row["admissibility_tertile"],
                f"same_{row['same_identity']}",
            ]
        )
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["stratum_id"], []).append(row)
    allocation = allocate_counts(groups, sample_size)
    rng = random.Random(random_seed + sum(ord(ch) for ch in descriptor_name))
    selected = []
    stratum_counts = {}
    for stratum_id, count in sorted(allocation.items()):
        chosen = rng.sample(groups[stratum_id], count)
        selected.extend(chosen)
        stratum_counts[stratum_id] = count
    rng.shuffle(selected)

    output_rows = []
    for idx, row in enumerate(selected, start=1):
        query = by_id[row["query_image_id"]]
        candidate = by_id[row["candidate_image_id"]]
        query_path = resolve_project_path(query["frozen_image_path"])
        candidate_path = resolve_project_path(candidate["frozen_image_path"])
        if not query_path.exists() or not candidate_path.exists():
            raise ValueError(f"missing image for review pair {row['pair_id']}")
        output_rows.append(
            {
                "review_pair_id": f"phase18j_{descriptor_name}_blind_{idx:04d}",
                "descriptor_name": descriptor_name,
                "sample_scope": "full_queue_stratified_evaluation",
                "stratum_id": row["stratum_id"],
                "query_image_id": row["query_image_id"],
                "candidate_image_id": row["candidate_image_id"],
                "query_image_path": project_relative(query_path),
                "candidate_image_path": project_relative(candidate_path),
                "same_identity_known_id": row["same_identity"],
                "candidate_rank_descriptor": row["candidate_rank_descriptor"],
                "rank_bin": row["rank_bin"],
                "descriptor_similarity": row["descriptor_similarity"],
                "descriptor_similarity_percentile": row["descriptor_similarity_percentile"],
                "admissibility_tertile": row["admissibility_tertile"],
                "descriptor_evidence_conflict_score": row["descriptor_evidence_conflict_score"],
                "pf_eri_admissibility_score": row["pf_eri_admissibility_score"],
                "pf_eri_review_score": row["pf_eri_review_score"],
                "pf_eri_route": row["pf_eri_route"],
                "weakest_image_quality_score": row["weakest_image_quality_score"],
                "pair_geometry_score": row["pair_geometry_score"],
                "query_split_role": row["query_split_role"],
                "reviewability_decision": "",
                "not_ready_reason": "",
                "secondary_reason": "",
                "visibility_notes": "",
                "reviewer_id": "",
                "review_timestamp": "",
                "claim_boundary": "Phase18J full-queue reviewability sample; labels are not identity labels.",
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    full_csv = output_dir / "phase18j_full_queue_review_packet.csv"
    blind_csv = output_dir / "phase18j_blind_review_form.csv"
    codebook_csv = output_dir / "phase18j_reviewability_codebook.csv"
    write_csv(full_csv, output_rows, FULL_COLUMNS)
    write_csv(blind_csv, output_rows, BLIND_COLUMNS)
    write_csv(codebook_csv, CODEBOOK_ROWS, CODEBOOK_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "features_csv": project_relative(features_csv),
        "phase18a_manifest": project_relative(phase18a_manifest),
        "full_csv": project_relative(full_csv),
        "blind_csv": project_relative(blind_csv),
        "codebook_csv": project_relative(codebook_csv),
        "evaluation_input_rows": len(rows),
        "sample_rows": len(output_rows),
        "requested_sample_rows": sample_size,
        "stratum_counts": stratum_counts,
        "random_seed": random_seed,
        "status": "PASS",
        "claim_boundary": "Full-queue stratified reviewability packet; not an identity-accuracy result.",
    }
    write_json(output_dir / "phase18j_full_queue_review_packet_audit.json", audit)
    return audit


def build_phase18j_full_queue_review_packet(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    phase18a_manifest: Path = DEFAULT_PHASE18A_MANIFEST,
    sample_size: int = SAMPLE_PER_DESCRIPTOR,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    audits = {}
    for descriptor_name in DESCRIPTORS:
        features_csv = Path(f"outputs/phase18/phase18d_strong_pf_eri_pair_features/{descriptor_name}/phase18d_pf_eri_pair_features.csv")
        audits[descriptor_name] = sample_descriptor_rows(
            descriptor_name=descriptor_name,
            features_csv=features_csv,
            phase18a_manifest=phase18a_manifest,
            output_dir=output_root / descriptor_name,
            sample_size=sample_size,
            random_seed=random_seed,
        )
    combined = {
        "built_at_utc": now_utc(),
        "descriptor_names": DESCRIPTORS,
        "sample_size_per_descriptor": sample_size,
        "total_sample_rows": sum(audit["sample_rows"] for audit in audits.values()),
        "descriptor_audits": audits,
        "status": "PASS",
    }
    write_json(output_root / "phase18j_full_queue_review_packet_combined_audit.json", combined)
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--phase18a-manifest", type=Path, default=DEFAULT_PHASE18A_MANIFEST)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_PER_DESCRIPTOR)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18j_full_queue_review_packet(
        output_root=args.output_root,
        phase18a_manifest=args.phase18a_manifest,
        sample_size=args.sample_size,
        random_seed=args.random_seed,
    )
    print("PASS phase18j full-queue review packet")
    print(f"total_sample_rows={audit['total_sample_rows']}")
    print(f"WROTE {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
