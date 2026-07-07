#!/usr/bin/env python3
"""Build a blind adjudication packet for Phase18J reviewer-disagreement pairs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, write_csv, write_json
except ModuleNotFoundError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, write_csv, write_json


DEFAULT_ANALYSIS_DIR = Path("outputs/phase18/phase18j_reviewer_agreement_analysis_100")
DEFAULT_PACKET_ROOT = Path("outputs/phase18/phase18j_full_queue_review_packet_100")
DEFAULT_OUTPUT_DIR = Path("outputs/phase18/phase18k_adjudication_packet")

ADJUDICATION_COLUMNS = [
    "adjudication_pair_id",
    "review_pair_id",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "decision_vote_summary",
    "reason_vote_summary",
    "adjudicated_reviewability_label",
    "adjudicated_reason",
    "adjudication_confidence",
    "adjudication_notes",
    "adjudicator_id",
    "adjudication_timestamp",
]

AUDIT_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "same_identity_known_id",
    "rank_bin",
    "admissibility_tertile",
    "candidate_rank_descriptor",
    "descriptor_similarity_percentile",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "pf_eri_route",
    "decision_votes",
    "reason_votes",
]


def packet_rows(packet_root: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for packet_csv in sorted(packet_root.glob("*/phase18j_full_queue_review_packet.csv")):
        for row in read_csv(packet_csv):
            rows[row["review_pair_id"]] = row
    return rows


def is_disagreement(row: dict[str, str]) -> bool:
    if row.get("unanimous_decision") == "no":
        return True
    votes = row.get("decision_votes", "")
    return ";" in votes


def build_phase18k_adjudication_packet(
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    packet_root: Path = DEFAULT_PACKET_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    majority_rows = read_csv(analysis_dir / "phase18j_pair_majority_labels.csv")
    packets = packet_rows(packet_root)
    disagreements = [row for row in majority_rows if is_disagreement(row)]
    blind_rows = []
    audit_rows = []
    for idx, row in enumerate(disagreements, start=1):
        packet = packets.get(row["review_pair_id"])
        if packet is None:
            raise ValueError(f"missing packet source row: {row['review_pair_id']}")
        blind_rows.append(
            {
                "adjudication_pair_id": f"phase18k_adjudication_{idx:04d}",
                "review_pair_id": row["review_pair_id"],
                "query_image_id": packet["query_image_id"],
                "candidate_image_id": packet["candidate_image_id"],
                "query_image_path": packet["query_image_path"],
                "candidate_image_path": packet["candidate_image_path"],
                "decision_vote_summary": row["decision_votes"],
                "reason_vote_summary": row["reason_votes"],
                "adjudicated_reviewability_label": "",
                "adjudicated_reason": "",
                "adjudication_confidence": "",
                "adjudication_notes": "",
                "adjudicator_id": "",
                "adjudication_timestamp": "",
            }
        )
        audit_rows.append({key: row.get(key, "") for key in AUDIT_COLUMNS})

    write_csv(output_dir / "phase18k_adjudication_blind_packet.csv", blind_rows, ADJUDICATION_COLUMNS)
    write_csv(output_dir / "phase18k_adjudication_hidden_audit.csv", audit_rows, AUDIT_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "analysis_dir": project_relative(analysis_dir),
        "packet_root": project_relative(packet_root),
        "output_dir": project_relative(output_dir),
        "disagreement_pair_count": len(blind_rows),
        "status": "PASS",
        "blindness_boundary": "Blind packet excludes descriptor name, identity truth, descriptor scores, PF-ERI scores, and reviewer identities.",
    }
    write_json(output_dir / "phase18k_adjudication_packet_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18k_adjudication_packet(args.analysis_dir, args.packet_root, args.output_dir)
    print("PASS phase18k adjudication packet")
    print(f"disagreement_pair_count={audit['disagreement_pair_count']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
