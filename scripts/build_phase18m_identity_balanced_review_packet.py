#!/usr/bin/env python3
"""Build Phase18M identity-balanced descriptor-controlled review packets."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, to_float, write_csv, write_json
except ModuleNotFoundError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, to_float, write_csv, write_json


DEFAULT_OUTPUT_ROOT = Path("outputs/phase18/phase18m_identity_balanced_review_packet")
DEFAULT_PHASE18A_MANIFEST = Path("outputs/phase18/phase18a_frozen_feature_manifest/phase18a_frozen_image_feature_manifest.csv")
DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
RANDOM_SEED = 20260704
PAIRS_PER_IDENTITY_CELL = 50
SIMILARITY_CUTOFF_PERCENTILES = [0.75, 0.70, 0.65, 0.60, 0.55, 0.50]

FULL_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "sample_scope",
    "identity_stratum",
    "evidence_group",
    "match_group_id",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "same_identity_known_id",
    "candidate_rank_descriptor",
    "rank_bin",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "similarity_match_delta",
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
    {"field": "reviewability_decision", "allowed_value": "review_ready", "definition": "Both images expose enough comparable evidence for pair-level review."},
    {"field": "reviewability_decision", "allowed_value": "not_review_ready", "definition": "The pair should not be treated as review-ready; choose a not_ready_reason."},
    {"field": "reviewability_decision", "allowed_value": "uncertain", "definition": "Use only when reviewability cannot be determined after considering the reason options."},
    {"field": "not_ready_reason", "allowed_value": "low_evidence", "definition": "At least one image is too weak, small, occluded, blurry, distant, or low quality for reliable pair review."},
    {"field": "not_ready_reason", "allowed_value": "non_comparable", "definition": "Images are visible but body region, viewpoint, pose, scale, or evidence type cannot be compared."},
    {"field": "not_ready_reason", "allowed_value": "both_low_evidence_and_non_comparable", "definition": "Both evidence weakness and non-comparability are substantial."},
    {"field": "not_ready_reason", "allowed_value": "identity_uncertain_but_reviewable", "definition": "The pair is review-ready, but identity itself is difficult; normally decision should be review_ready."},
    {"field": "not_ready_reason", "allowed_value": "other", "definition": "Use only with notes when no listed reason fits."},
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


def manifest_by_image_id(path: Path) -> dict[str, dict[str, str]]:
    return {row["phase18_image_id"]: row for row in read_csv(path)}


def quantile(rows: list[dict[str, str]], column: str, pct: float) -> float:
    values = sorted(to_float(row[column]) for row in rows)
    if not values:
        return 0.0
    return float(values[int((len(values) - 1) * pct)])


def greedy_similarity_matches(
    high_rows: list[dict[str, str]],
    low_rows: list[dict[str, str]],
    pair_count: int,
) -> list[tuple[dict[str, str], dict[str, str], float]]:
    high = sorted(high_rows, key=lambda row: to_float(row["descriptor_similarity_percentile"]))
    low = sorted(low_rows, key=lambda row: to_float(row["descriptor_similarity_percentile"]))
    matches = []
    if len(high) <= len(low):
        anchors = [("high", row) for row in high]
        available = low
    else:
        anchors = [("low", row) for row in low]
        available = high
    for anchor_kind, anchor_row in anchors:
        if not available or len(matches) >= pair_count:
            break
        anchor_similarity = to_float(anchor_row["descriptor_similarity_percentile"])
        best_idx = min(
            range(len(available)),
            key=lambda idx: abs(to_float(available[idx]["descriptor_similarity_percentile"]) - anchor_similarity),
        )
        matched_row = available.pop(best_idx)
        delta = abs(to_float(matched_row["descriptor_similarity_percentile"]) - anchor_similarity)
        high_row = anchor_row if anchor_kind == "high" else matched_row
        low_row = matched_row if anchor_kind == "high" else anchor_row
        matches.append((high_row, low_row, delta))
    return matches


def row_to_output(
    descriptor_name: str,
    source: dict[str, str],
    by_id: dict[str, dict[str, str]],
    idx: int,
    identity_stratum: str,
    evidence_group: str,
    match_group_id: str,
    similarity_match_delta: float,
) -> dict[str, Any]:
    query = by_id[source["query_image_id"]]
    candidate = by_id[source["candidate_image_id"]]
    query_path = resolve_project_path(query["frozen_image_path"])
    candidate_path = resolve_project_path(candidate["frozen_image_path"])
    if not query_path.exists() or not candidate_path.exists():
        raise ValueError(f"missing image for pair {source['pair_id']}")
    return {
        "review_pair_id": f"phase18m_{descriptor_name}_blind_{idx:04d}",
        "descriptor_name": descriptor_name,
        "sample_scope": "identity_balanced_descriptor_controlled_admissibility_contrast",
        "identity_stratum": identity_stratum,
        "evidence_group": evidence_group,
        "match_group_id": match_group_id,
        "query_image_id": source["query_image_id"],
        "candidate_image_id": source["candidate_image_id"],
        "query_image_path": project_relative(query_path),
        "candidate_image_path": project_relative(candidate_path),
        "same_identity_known_id": source["same_identity"],
        "candidate_rank_descriptor": source["candidate_rank_descriptor"],
        "rank_bin": rank_bin(source["candidate_rank_descriptor"]),
        "descriptor_similarity": source["descriptor_similarity"],
        "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
        "similarity_match_delta": round(similarity_match_delta, 8),
        "descriptor_evidence_conflict_score": source["descriptor_evidence_conflict_score"],
        "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
        "pf_eri_review_score": source["pf_eri_review_score"],
        "pf_eri_route": source["pf_eri_route"],
        "weakest_image_quality_score": source["weakest_image_quality_score"],
        "pair_geometry_score": source["pair_geometry_score"],
        "query_split_role": source["query_split_role"],
        "reviewability_decision": "",
        "not_ready_reason": "",
        "secondary_reason": "",
        "visibility_notes": "",
        "reviewer_id": "",
        "review_timestamp": "",
        "claim_boundary": "Identity-balanced reviewability packet; review labels are not identity labels.",
    }


def build_descriptor_identity_balanced_packet(
    descriptor_name: str,
    features_csv: Path,
    phase18a_manifest: Path,
    output_dir: Path,
    pairs_per_identity_cell: int = PAIRS_PER_IDENTITY_CELL,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    by_id = manifest_by_image_id(phase18a_manifest)
    rows = [row for row in read_csv(features_csv) if row["query_split_role"] == "evaluation"]
    if not rows:
        raise ValueError(f"0 evaluation rows for {descriptor_name}")
    adm_low = quantile(rows, "pf_eri_admissibility_score", 0.333333)
    adm_high = quantile(rows, "pf_eri_admissibility_score", 0.666667)
    rng = random.Random(random_seed + sum(ord(ch) for ch in descriptor_name))
    selected_pct = 0.0
    sim_cutoff = 0.0
    high_similarity: list[dict[str, str]] = []
    selected_cells: list[tuple[str, str, list[dict[str, str]], list[dict[str, str]], list[tuple[dict[str, str], dict[str, str], float]]]] = []
    for cutoff_pct in SIMILARITY_CUTOFF_PERCENTILES:
        candidate_cutoff = quantile(rows, "descriptor_similarity_percentile", cutoff_pct)
        candidate_high_similarity = [
            row for row in rows if to_float(row["descriptor_similarity_percentile"]) >= candidate_cutoff
        ]
        candidate_cells = []
        complete = True
        for identity_value, identity_stratum in [("yes", "same_identity"), ("no", "different_identity")]:
            identity_rows = [row for row in candidate_high_similarity if row["same_identity"] == identity_value]
            high_evidence = [row for row in identity_rows if to_float(row["pf_eri_admissibility_score"]) >= adm_high]
            low_evidence = [row for row in identity_rows if to_float(row["pf_eri_admissibility_score"]) <= adm_low]
            rng.shuffle(high_evidence)
            rng.shuffle(low_evidence)
            matches = greedy_similarity_matches(high_evidence, low_evidence, pairs_per_identity_cell)
            candidate_cells.append((identity_stratum, identity_value, high_evidence, low_evidence, matches))
            if len(matches) < pairs_per_identity_cell:
                complete = False
        if complete:
            selected_pct = cutoff_pct
            sim_cutoff = candidate_cutoff
            high_similarity = candidate_high_similarity
            selected_cells = candidate_cells
            break
    if not selected_cells:
        raise ValueError(
            f"insufficient Phase18M matches for {descriptor_name}: requested "
            f"{pairs_per_identity_cell} high/low matches in both identity strata"
        )

    output_rows = []
    cell_audits = []
    idx = 1
    for identity_stratum, identity_value, high_evidence, low_evidence, matches in selected_cells:
        deltas = []
        for match_idx, (high_row, low_row, delta) in enumerate(matches, start=1):
            deltas.append(delta)
            group = f"phase18m_{descriptor_name}_{identity_stratum}_match_{match_idx:04d}"
            output_rows.append(
                row_to_output(descriptor_name, high_row, by_id, idx, identity_stratum, "high_admissibility", group, delta)
            )
            idx += 1
            output_rows.append(
                row_to_output(descriptor_name, low_row, by_id, idx, identity_stratum, "low_admissibility", group, delta)
            )
            idx += 1
        cell_audits.append(
            {
                "identity_stratum": identity_stratum,
                "identity_input_rows": len([row for row in high_similarity if row["same_identity"] == identity_value]),
                "high_evidence_rows": len(high_evidence),
                "low_evidence_rows": len(low_evidence),
                "matched_pair_count": len(matches),
                "mean_similarity_match_delta": float(np.mean(deltas)) if deltas else 0.0,
            }
        )
    rng.shuffle(output_rows)
    for new_idx, row in enumerate(output_rows, start=1):
        row["review_pair_id"] = f"phase18m_{descriptor_name}_blind_{new_idx:04d}"

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "phase18m_identity_balanced_review_packet.csv", output_rows, FULL_COLUMNS)
    write_csv(output_dir / "phase18m_blind_review_form.csv", output_rows, BLIND_COLUMNS)
    write_csv(output_dir / "phase18m_reviewability_codebook.csv", CODEBOOK_ROWS, CODEBOOK_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "features_csv": project_relative(features_csv),
        "phase18a_manifest": project_relative(phase18a_manifest),
        "output_dir": project_relative(output_dir),
        "evaluation_input_rows": len(rows),
        "high_similarity_rows": len(high_similarity),
        "pairs_per_identity_cell": pairs_per_identity_cell,
        "sample_rows": len(output_rows),
        "matched_pair_count": sum(cell["matched_pair_count"] for cell in cell_audits),
        "selected_similarity_cutoff_percentile": selected_pct,
        "similarity_percentile_cutoff": sim_cutoff,
        "admissibility_low_cutoff": adm_low,
        "admissibility_high_cutoff": adm_high,
        "cell_audits": cell_audits,
        "mean_similarity_match_delta": float(np.mean([cell["mean_similarity_match_delta"] for cell in cell_audits])),
        "status": "PASS",
        "claim_boundary": "Identity-balanced high-similarity PF-ERI admissibility contrast; reviewability labels are not identity labels.",
    }
    write_json(output_dir / "phase18m_identity_balanced_review_packet_audit.json", audit)
    return audit


def build_phase18m_identity_balanced_review_packet(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    phase18a_manifest: Path = DEFAULT_PHASE18A_MANIFEST,
    pairs_per_identity_cell: int = PAIRS_PER_IDENTITY_CELL,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    audits = {}
    for descriptor_name in DESCRIPTORS:
        features_csv = Path(f"outputs/phase18/phase18d_strong_pf_eri_pair_features/{descriptor_name}/phase18d_pf_eri_pair_features.csv")
        audits[descriptor_name] = build_descriptor_identity_balanced_packet(
            descriptor_name=descriptor_name,
            features_csv=features_csv,
            phase18a_manifest=phase18a_manifest,
            output_dir=output_root / descriptor_name,
            pairs_per_identity_cell=pairs_per_identity_cell,
            random_seed=random_seed,
        )
    combined = {
        "built_at_utc": now_utc(),
        "descriptor_names": DESCRIPTORS,
        "pairs_per_identity_cell": pairs_per_identity_cell,
        "total_sample_rows": sum(audit["sample_rows"] for audit in audits.values()),
        "descriptor_audits": audits,
        "status": "PASS",
    }
    write_json(output_root / "phase18m_identity_balanced_review_packet_combined_audit.json", combined)
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--phase18a-manifest", type=Path, default=DEFAULT_PHASE18A_MANIFEST)
    parser.add_argument("--pairs-per-identity-cell", type=int, default=PAIRS_PER_IDENTITY_CELL)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18m_identity_balanced_review_packet(
        output_root=args.output_root,
        phase18a_manifest=args.phase18a_manifest,
        pairs_per_identity_cell=args.pairs_per_identity_cell,
        random_seed=args.random_seed,
    )
    print("PASS phase18m identity-balanced review packet")
    print(f"total_sample_rows={audit['total_sample_rows']}")
    print(f"WROTE {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
