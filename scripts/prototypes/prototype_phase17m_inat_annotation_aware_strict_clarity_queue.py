#!/usr/bin/env python3
"""PROTOTYPE: iNaturalist annotation-aware strict Bobcat clarity queue.

Phase17L showed that GBIF expands volume but reintroduces sign/dead/non-animal
evidence because GBIF photo mirrors do not carry iNaturalist annotation gates.
Phase17M therefore prioritizes direct iNaturalist organism/alive/not-scat/not-
track annotations and allows multiple photos per observation for review.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE17L_SCRIPT = PROJECT_ROOT / "scripts/prototypes/prototype_phase17l_multisource_bobcat_strict_clarity_queue.py"
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17e_external_source_probe/prototype_phase17e_inat_research_grade_bobcat_organism_candidates.csv"
)
PHASE17L_WORKING_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17l_multisource_strict_clarity_review/phase17l_bobcat_strict_clarity_review_working.csv"
)
PHASE17L_SCORED_CSV = (
    PROJECT_ROOT / "outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_multisource_bobcat_scored_all.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue"
QUEUE_CSV = OUTPUT_DIR / "phase17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv"
SCORED_CSV = OUTPUT_DIR / "phase17m_inat_annotation_aware_scored_all.csv"


def load_phase17l_module() -> Any:
    spec = importlib.util.spec_from_file_location("phase17l", PHASE17L_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {PHASE17L_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalized_image_url(url: str) -> str:
    return (
        url.replace("/original.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/small.", "/large.")
        .replace("/square.", "/large.")
        .split("?")[0]
    )


def prior_label_maps() -> tuple[set[str], set[str]]:
    clear: set[str] = set()
    not_clear: set[str] = set()
    for row in read_csv(PHASE17L_WORKING_CSV):
        decision = row.get("phase17l_clarity_gate_decision", "")
        if decision not in {"clear", "not_clear"}:
            continue
        keys = {row.get("candidate_id", ""), normalized_image_url(row.get("image_uri", ""))}
        target = clear if decision == "clear" else not_clear
        target.update(key for key in keys if key)
    return clear, not_clear


def source_to_phase17l_row(row: dict[str, str], clear_keys: set[str]) -> dict[str, Any]:
    image_uri = normalized_image_url(row.get("image_uri", ""))
    phase17l_id = f"phase17m_inat_{row.get('observation_id')}_{row.get('photo_id') or row.get('photo_index')}"
    prior_label = "clear" if row.get("candidate_id", "") in clear_keys or image_uri in clear_keys else ""
    return {
        "candidate_id": phase17l_id,
        "phase17l_source": "iNaturalist",
        "phase17l_source_detail": "research_grade_organism_annotation_aware_all_photos",
        "source_record_id": row.get("observation_id", ""),
        "photo_id": row.get("photo_id", ""),
        "image_uri": image_uri,
        "thumbnail_uri": row.get("thumbnail_uri", ""),
        "source_uri": row.get("observation_uri", ""),
        "license": row.get("photo_license_code", ""),
        "attribution": row.get("photo_attribution", ""),
        "observed_on": row.get("observed_on", ""),
        "place_guess": row.get("place_guess", ""),
        "scientific_name": row.get("taxon_name", "Lynx rufus"),
        "basis_of_record": "HUMAN_OBSERVATION",
        "prior_human_label": prior_label,
        "prior_human_source": str(PHASE17L_WORKING_CSV) if prior_label else "",
        "phase17l_clarity_gate_decision": "clear" if prior_label == "clear" else "",
        "phase17l_clarity_reject_reason": "",
        "phase17l_clarity_notes": "seeded from prior human CLEAR" if prior_label == "clear" else "",
        "phase17l_clarity_audited_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")
        if prior_label == "clear"
        else "",
        "phase17l_claim_boundary": "annotation-aware strict review queue only; final algorithm entry requires manual clear",
    }


def valid_source_row(row: dict[str, str], not_clear_keys: set[str]) -> bool:
    image_uri = normalized_image_url(row.get("image_uri", ""))
    if row.get("candidate_id", "") in not_clear_keys or image_uri in not_clear_keys:
        return False
    if row.get("evidence_organism") != "yes":
        return False
    if row.get("evidence_scat") == "yes" or row.get("evidence_track") == "yes":
        return False
    if row.get("alive_dead") == "dead" or row.get("captive") == "true":
        return False
    return bool(image_uri)


def existing_scores_by_image(module: Any) -> dict[str, dict[str, Any]]:
    scored: dict[str, dict[str, Any]] = {}
    for row in read_csv(PHASE17L_SCORED_CSV):
        if row.get("phase17l_source") != "iNaturalist":
            continue
        key = normalized_image_url(row.get("image_uri", ""))
        if key:
            scored[key] = row
    return scored


def apply_existing_score(row: dict[str, Any], scored: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    existing = scored.get(normalized_image_url(str(row.get("image_uri", ""))))
    if not existing:
        return None
    out = dict(row)
    for key in [
        "image_width",
        "image_height",
        "image_megapixels",
        "download_bytes",
        "contrast_std",
        "gradient_mean",
        "gradient_p90",
        "laplacian_var",
        "entropy",
        "dark_clip_fraction",
        "bright_clip_fraction",
        "colorfulness_proxy",
        "phase17l_strict_clarity_proxy_score",
        "phase17l_strict_proxy_tier",
        "phase17l_proxy_reject_reasons",
    ]:
        out[key] = existing.get(key, "")
    return out


def row_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    tier_rank = {"strict_pass": 0, "near_strict": 1, "review_only": 2}.get(
        str(row.get("phase17l_strict_proxy_tier", "")),
        9,
    )
    score = float(row.get("phase17l_strict_clarity_proxy_score") or -1)
    return (tier_rank, -score, str(row.get("candidate_id", "")))


def dedupe_scored_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        keys = [
            normalized_image_url(str(row.get("image_uri", ""))).lower(),
            f"photo:{row.get('photo_id', '')}" if row.get("photo_id") else "",
        ]
        if any(key and key in seen for key in keys):
            continue
        seen.update(key for key in keys if key)
        output.append(row)
    return output


def build_queue(args: argparse.Namespace) -> dict[str, Any]:
    module = load_phase17l_module()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_keys, not_clear_keys = prior_label_maps()
    source_rows = read_csv(SOURCE_CSV)
    candidates = [
        source_to_phase17l_row(row, clear_keys)
        for row in source_rows
        if valid_source_row(row, not_clear_keys)
    ]
    scored_lookup = existing_scores_by_image(module)
    reused: list[dict[str, Any]] = []
    to_score: list[dict[str, Any]] = []
    for row in candidates:
        existing = apply_existing_score(row, scored_lookup)
        if existing is None:
            to_score.append(row)
        else:
            reused.append(existing)
    newly_scored = module.score_rows(to_score, score_limit=len(to_score), workers=args.workers, timeout=args.timeout)
    scored_all = reused + newly_scored
    module.write_csv(SCORED_CSV, scored_all, module.OUTPUT_FIELDS)
    scored_success = dedupe_scored_rows(
        [
        row
        for row in scored_all
        if float(row.get("phase17l_strict_clarity_proxy_score") or -1) >= 0
        and row.get("phase17l_strict_proxy_tier") in {"strict_pass", "near_strict"}
        ]
    )
    scored_success.sort(key=row_sort_key)
    selected = scored_success[: args.target_count]
    module.write_csv(QUEUE_CSV, selected, module.OUTPUT_FIELDS)
    module.write_gallery(selected[: args.gallery_count], OUTPUT_DIR / "phase17m_inat_annotation_aware_gallery.html")
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_csv": str(SOURCE_CSV),
        "input_rows": len(source_rows),
        "candidate_rows_after_annotation_and_prior_filters": len(candidates),
        "reused_phase17l_iNat_scores": len(reused),
        "newly_scored_rows": len(newly_scored),
        "scored_all_rows": len(scored_all),
        "strict_or_near_rows_available": len(scored_success),
        "selected_rows": len(selected),
        "selected_tier_counts": dict(Counter(row.get("phase17l_strict_proxy_tier", "") for row in selected)),
        "selected_proxy_reject_reason_counts": dict(
            Counter(row.get("phase17l_proxy_reject_reasons", "") or "none" for row in selected).most_common(30)
        ),
        "selected_photo_index_counts": dict(Counter(row.get("photo_id", "") for row in selected).most_common(5)),
        "output_csv": str(QUEUE_CSV),
        "scored_csv": str(SCORED_CSV),
        "claim_boundary": "More semantically conservative than Phase17L because all rows carry direct iNaturalist annotation gates.",
    }
    (OUTPUT_DIR / "phase17m_inat_annotation_aware_strict_clarity_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    notes = [
        "# Phase17M iNaturalist Annotation-Aware Strict Clarity Queue",
        "",
        "Question: can we reduce scat/track/dead leakage by dropping GBIF mirrors and using direct iNaturalist annotation gates?",
        "",
        "This is a prototype queue. Final Bobcat algorithm entry still requires manual CLEAR.",
    ]
    (OUTPUT_DIR / "NOTES.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-count", type=int, default=5000)
    parser.add_argument("--gallery-count", type=int, default=500)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--timeout", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    audit = build_queue(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
