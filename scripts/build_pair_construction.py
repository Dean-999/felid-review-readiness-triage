#!/usr/bin/env python3
"""Build pair-level construction tables from the final modeling image index."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/final-modeling-bootstrap"
IMAGE_INDEX_CSV = INPUT_DIR / "final_modeling_image_index.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/pair-construction"
CZECHLYNX_PAIRS_CSV = OUTPUT_DIR / "czechlynx_known_id_pairs.csv"
BOBCAT_PAIRS_CSV = OUTPUT_DIR / "bobcat_transfer_stress_pairs.csv"
UNIFIED_PAIRS_CSV = OUTPUT_DIR / "pair_construction_index.csv"
AUDIT_JSON = OUTPUT_DIR / "pair_construction_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

CZECHLYNX_SAME_PER_QUERY = 3
CZECHLYNX_DIFFERENT_PER_QUERY = 3
BOBCAT_WITHIN_SCOPE_PER_QUERY = 3
BOBCAT_CROSS_SCOPE_PER_QUERY = 3

PAIR_COLUMNS = [
    "pair_id",
    "pair_family",
    "pair_scope",
    "construction_rule",
    "query_image_id",
    "candidate_image_id",
    "query_scope",
    "candidate_scope",
    "query_species",
    "candidate_species",
    "query_domain_label",
    "candidate_domain_label",
    "query_source_row_number",
    "candidate_source_row_number",
    "split_id",
    "split_role",
    "split_group_key",
    "identity_relation",
    "same_identity_label",
    "query_identity_label",
    "candidate_identity_label",
    "claim_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_id_for_key(key: str, split_count: int = 5) -> int:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % split_count


def split_role(split_id: int) -> str:
    if split_id in {0, 1}:
        return "calibration"
    return "evaluation"


def row_int(row: dict[str, str], key: str) -> int:
    try:
        return int(str(row.get(key, "")).strip())
    except ValueError:
        return 0


def pair_id(prefix: str, query_image_id: str, candidate_image_id: str, rule: str) -> str:
    return f"{prefix}_{rule}__{query_image_id}__{candidate_image_id}"


def base_pair(
    *,
    pair_id_value: str,
    pair_family: str,
    pair_scope: str,
    construction_rule: str,
    query: dict[str, str],
    candidate: dict[str, str],
    split_group_key: str,
    identity_relation: str,
    same_identity_label: str,
    query_identity_label: str,
    candidate_identity_label: str,
    claim_boundary: str,
) -> dict[str, Any]:
    split_id = split_id_for_key(split_group_key)
    return {
        "pair_id": pair_id_value,
        "pair_family": pair_family,
        "pair_scope": pair_scope,
        "construction_rule": construction_rule,
        "query_image_id": query["image_id"],
        "candidate_image_id": candidate["image_id"],
        "query_scope": query["scope"],
        "candidate_scope": candidate["scope"],
        "query_species": query["species"],
        "candidate_species": candidate["species"],
        "query_domain_label": query["domain_label"],
        "candidate_domain_label": candidate["domain_label"],
        "query_source_row_number": query["source_row_number"],
        "candidate_source_row_number": candidate["source_row_number"],
        "split_id": split_id,
        "split_role": split_role(split_id),
        "split_group_key": split_group_key,
        "identity_relation": identity_relation,
        "same_identity_label": same_identity_label,
        "query_identity_label": query_identity_label,
        "candidate_identity_label": candidate_identity_label,
        "claim_boundary": claim_boundary,
    }


def circular_candidates(
    rows: list[dict[str, str]],
    start_index: int,
    count: int,
    *,
    skip_image_id: str = "",
) -> list[dict[str, str]]:
    if not rows or count <= 0:
        return []
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for offset in range(1, len(rows) + 1):
        candidate = rows[(start_index + offset) % len(rows)]
        image_id = candidate["image_id"]
        if image_id == skip_image_id or image_id in seen:
            continue
        selected.append(candidate)
        seen.add(image_id)
        if len(selected) >= count:
            break
    return selected


def build_czechlynx_pairs(image_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    lynx_rows = sorted(
        [row for row in image_rows if row["scope"] == "lynx-wild"],
        key=lambda row: row["image_id"],
    )
    by_identity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in lynx_rows:
        by_identity[row["identity_label"]].append(row)

    identity_labels = sorted(by_identity)
    identity_index = {identity: idx for idx, identity in enumerate(identity_labels)}
    rows: list[dict[str, Any]] = []

    for query in lynx_rows:
        query_identity = query["identity_label"]
        group = sorted(by_identity[query_identity], key=lambda row: row["image_id"])
        query_pos = [row["image_id"] for row in group].index(query["image_id"])
        same_candidates = circular_candidates(
            group,
            query_pos,
            min(CZECHLYNX_SAME_PER_QUERY, max(0, len(group) - 1)),
            skip_image_id=query["image_id"],
        )
        for candidate in same_candidates:
            rows.append(
                base_pair(
                    pair_id_value=pair_id("pferi_lynx", query["image_id"], candidate["image_id"], "same_known_id"),
                    pair_family="known_id_validation",
                    pair_scope="lynx-wild",
                    construction_rule="same_known_id",
                    query=query,
                    candidate=candidate,
                    split_group_key=f"identity:{query_identity}",
                    identity_relation="known",
                    same_identity_label="yes",
                    query_identity_label=query_identity,
                    candidate_identity_label=candidate["identity_label"],
                    claim_boundary="CzechLynx known-ID pair; may support same/different evidence-sufficiency validation.",
                )
            )

        start_identity_idx = identity_index[query_identity]
        different_identity_labels: list[str] = []
        for offset in range(1, len(identity_labels) + 1):
            identity = identity_labels[(start_identity_idx + offset * 37) % len(identity_labels)]
            if identity != query_identity and identity not in different_identity_labels:
                different_identity_labels.append(identity)
            if len(different_identity_labels) >= CZECHLYNX_DIFFERENT_PER_QUERY:
                break
        for offset, candidate_identity in enumerate(different_identity_labels):
            candidates = sorted(by_identity[candidate_identity], key=lambda row: row["image_id"])
            candidate = candidates[(row_int(query, "source_row_number") + offset) % len(candidates)]
            rows.append(
                base_pair(
                    pair_id_value=pair_id("pferi_lynx", query["image_id"], candidate["image_id"], "different_known_id"),
                    pair_family="known_id_validation",
                    pair_scope="lynx-wild",
                    construction_rule="different_known_id",
                    query=query,
                    candidate=candidate,
                    split_group_key=f"identity:{query_identity}",
                    identity_relation="known",
                    same_identity_label="no",
                    query_identity_label=query_identity,
                    candidate_identity_label=candidate_identity,
                    claim_boundary="CzechLynx known-ID pair; may support same/different evidence-sufficiency validation.",
                )
            )

    return rows


def build_bobcat_pairs(image_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_scope: dict[str, list[dict[str, str]]] = {
        scope: sorted([row for row in image_rows if row["scope"] == scope], key=lambda row: row["image_id"])
        for scope in ["bobcat-wild", "bobcat-urban"]
    }
    rows: list[dict[str, Any]] = []
    for scope, scoped_rows in by_scope.items():
        for query_pos, query in enumerate(scoped_rows):
            within_candidates = circular_candidates(
                scoped_rows,
                query_pos,
                BOBCAT_WITHIN_SCOPE_PER_QUERY,
                skip_image_id=query["image_id"],
            )
            for candidate in within_candidates:
                rows.append(
                    base_pair(
                        pair_id_value=pair_id("pferi_bobcat", query["image_id"], candidate["image_id"], "within_scope_unlabeled"),
                        pair_family="transfer_stress",
                        pair_scope=scope,
                        construction_rule="within_scope_unlabeled",
                        query=query,
                        candidate=candidate,
                        split_group_key=f"{scope}:{query['image_id']}",
                        identity_relation="unlabeled",
                        same_identity_label="",
                        query_identity_label="",
                        candidate_identity_label="",
                        claim_boundary="Bobcat transfer/evidence-stress pair only; same/different identity is not labeled or inferred.",
                    )
                )

            opposite_scope = "bobcat-urban" if scope == "bobcat-wild" else "bobcat-wild"
            opposite_rows = by_scope[opposite_scope]
            if not opposite_rows:
                continue
            base_index = row_int(query, "source_row_number") % len(opposite_rows)
            cross_candidates = [
                opposite_rows[(base_index + offset * 17) % len(opposite_rows)]
                for offset in range(BOBCAT_CROSS_SCOPE_PER_QUERY)
            ]
            for candidate in cross_candidates:
                rows.append(
                    base_pair(
                        pair_id_value=pair_id("pferi_bobcat", query["image_id"], candidate["image_id"], "cross_scope_unlabeled"),
                        pair_family="transfer_stress",
                        pair_scope=f"{scope}_to_{opposite_scope}",
                        construction_rule="cross_scope_unlabeled",
                        query=query,
                        candidate=candidate,
                        split_group_key=f"{scope}:{query['image_id']}",
                        identity_relation="unlabeled",
                        same_identity_label="",
                        query_identity_label="",
                        candidate_identity_label="",
                        claim_boundary="Bobcat wild/urban transfer-stress pair only; same/different identity is not labeled or inferred.",
                    )
                )
    return rows


def audit_pairs(czechlynx_pairs: list[dict[str, Any]], bobcat_pairs: list[dict[str, Any]]) -> dict[str, Any]:
    all_pairs = czechlynx_pairs + bobcat_pairs
    pair_ids = [row["pair_id"] for row in all_pairs]
    duplicate_pair_id_count = len(pair_ids) - len(set(pair_ids))
    self_pair_count = sum(row["query_image_id"] == row["candidate_image_id"] for row in all_pairs)
    bobcat_identity_violations = sum(
        row["pair_family"] == "transfer_stress"
        and (
            row["identity_relation"] != "unlabeled"
            or row["same_identity_label"] != ""
            or row["query_identity_label"] != ""
            or row["candidate_identity_label"] != ""
        )
        for row in bobcat_pairs
    )
    czech_same_count = sum(row["same_identity_label"] == "yes" for row in czechlynx_pairs)
    czech_different_count = sum(row["same_identity_label"] == "no" for row in czechlynx_pairs)
    failures = []
    if duplicate_pair_id_count:
        failures.append("duplicate_pair_ids")
    if self_pair_count:
        failures.append("self_pairs")
    if bobcat_identity_violations:
        failures.append("bobcat_identity_boundary_violations")
    if not czech_same_count or not czech_different_count:
        failures.append("czechlynx_missing_same_or_different_pairs")

    return {
        "built_at_utc": utc_now(),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "input_image_index_csv": project_relative(IMAGE_INDEX_CSV),
        "outputs": {
            "czechlynx_pairs_csv": project_relative(CZECHLYNX_PAIRS_CSV),
            "bobcat_pairs_csv": project_relative(BOBCAT_PAIRS_CSV),
            "unified_pairs_csv": project_relative(UNIFIED_PAIRS_CSV),
            "audit_json": project_relative(AUDIT_JSON),
            "report_md": project_relative(REPORT_MD),
        },
        "pair_rows": len(all_pairs),
        "czechlynx_pair_rows": len(czechlynx_pairs),
        "bobcat_pair_rows": len(bobcat_pairs),
        "czechlynx_same_identity_pairs": czech_same_count,
        "czechlynx_different_identity_pairs": czech_different_count,
        "duplicate_pair_id_count": duplicate_pair_id_count,
        "self_pair_count": self_pair_count,
        "bobcat_identity_boundary_violations": bobcat_identity_violations,
        "pair_family_counts": dict(sorted(Counter(row["pair_family"] for row in all_pairs).items())),
        "pair_scope_counts": dict(sorted(Counter(row["pair_scope"] for row in all_pairs).items())),
        "construction_rule_counts": dict(sorted(Counter(row["construction_rule"] for row in all_pairs).items())),
        "split_role_counts": dict(sorted(Counter(row["split_role"] for row in all_pairs).items())),
        "claim_boundary": (
            "CzechLynx pairs carry known same/different labels. Bobcat pairs are unlabeled "
            "transfer-stress/comparability pairs only and cannot support identity-accuracy claims."
        ),
    }


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Pair Construction",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module builds the first pair-level tables for the PF-ERI Selective",
        "Evidence Sufficiency Model from the final modeling image index.",
        "",
        "## Outputs",
        "",
        f"- CzechLynx known-ID pairs: `{audit['outputs']['czechlynx_pairs_csv']}`",
        f"- Bobcat unlabeled transfer-stress pairs: `{audit['outputs']['bobcat_pairs_csv']}`",
        f"- Unified pair index: `{audit['outputs']['unified_pairs_csv']}`",
        "",
        "## Counts",
        "",
        f"- Total pair rows: {audit['pair_rows']}",
        f"- CzechLynx pair rows: {audit['czechlynx_pair_rows']}",
        f"- Bobcat pair rows: {audit['bobcat_pair_rows']}",
        f"- CzechLynx same-ID pairs: {audit['czechlynx_same_identity_pairs']}",
        f"- CzechLynx different-ID pairs: {audit['czechlynx_different_identity_pairs']}",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    image_rows = read_csv(IMAGE_INDEX_CSV)
    czechlynx_pairs = build_czechlynx_pairs(image_rows)
    bobcat_pairs = build_bobcat_pairs(image_rows)
    all_pairs = czechlynx_pairs + bobcat_pairs
    audit = audit_pairs(czechlynx_pairs, bobcat_pairs)

    write_csv(CZECHLYNX_PAIRS_CSV, czechlynx_pairs, PAIR_COLUMNS)
    write_csv(BOBCAT_PAIRS_CSV, bobcat_pairs, PAIR_COLUMNS)
    write_csv(UNIFIED_PAIRS_CSV, all_pairs, PAIR_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
