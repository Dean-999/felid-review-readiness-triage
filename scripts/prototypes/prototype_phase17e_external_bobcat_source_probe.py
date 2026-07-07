#!/usr/bin/env python3
"""PROTOTYPE: probe externally pre-filtered Bobcat image sources.

Question:
Can an externally curated source, starting with iNaturalist research-grade
Lynx rufus observations, provide a better high-quality candidate pool than the
current Phase16E Bobcat camera-trap batch?

This is throwaway logic. It fetches public iNaturalist observation metadata,
extracts photo URLs and licenses, and writes a scratch candidate CSV/report for
human review. It does not make identity or algorithm-entry claims.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import time
import urllib.parse
import urllib.request
from urllib.error import URLError
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17e_external_source_probe"
INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
BOBCAT_TAXON_ID = 41976
EVIDENCE_FILTERS = {
    "all": {},
    "organism": {"term_id": 22, "term_value_id": 24},
    "scat": {"term_id": 22, "term_value_id": 25},
    "track": {"term_id": 22, "term_value_id": 26},
    "without_scat_track": {"term_id": 22, "without_term_value_id": "25,26"},
}


def fetch_json(url: str, timeout: int = 30, attempts: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "felid-review-readiness-prototype/0.1"})
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, URLError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"failed to fetch after {attempts} attempts: {url}") from last_error


def photo_large_url(url: str) -> str:
    return (
        url.replace("/square.", "/large.")
        .replace("/small.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/thumb.", "/large.")
    )


def source_score(row: dict[str, Any]) -> float:
    score = 0.0
    if row["quality_grade"] == "research":
        score += 0.45
    if row["photo_license_code"]:
        score += 0.20
    if row["observed_on"]:
        score += 0.05
    if row["place_guess"]:
        score += 0.05
    if row["community_taxon_id"] == str(BOBCAT_TAXON_ID):
        score += 0.20
    if row.get("inat_evidence_filter") == "organism":
        score += 0.10
    if row["captive"] == "true":
        score -= 0.25
    return round(score, 4)


def observation_rows(observation: dict[str, Any], evidence_filter: str) -> list[dict[str, Any]]:
    taxon = observation.get("taxon") or {}
    community_taxon = observation.get("community_taxon") or {}
    annotation_pairs = {
        f"{annotation.get('controlled_attribute_id')}|{annotation.get('controlled_value_id')}"
        for annotation in observation.get("annotations") or []
    }
    alive_dead = (
        "alive"
        if "17|18" in annotation_pairs
        else "dead"
        if "17|19" in annotation_pairs
        else "cannot_determine"
        if "17|20" in annotation_pairs
        else "missing"
    )
    rows: list[dict[str, Any]] = []
    for photo_index, photo in enumerate(observation.get("photos") or [], start=1):
        raw_url = str(photo.get("url") or "")
        if not raw_url:
            continue
        row = {
            "candidate_id": f"inat_bobcat_{observation.get('id')}_{photo_index}",
            "external_source": "iNaturalist",
            "external_source_filter": f"research_grade_bobcat_photos_{evidence_filter}",
            "inat_evidence_filter": evidence_filter,
            "observation_id": str(observation.get("id") or ""),
            "photo_id": str(photo.get("id") or ""),
            "photo_index": photo_index,
            "image_uri": photo_large_url(raw_url),
            "thumbnail_uri": raw_url,
            "observation_uri": str(observation.get("uri") or ""),
            "quality_grade": str(observation.get("quality_grade") or ""),
            "captive": str(observation.get("captive") or "").lower(),
            "observed_on": str(observation.get("observed_on") or ""),
            "place_guess": str(observation.get("place_guess") or ""),
            "taxon_id": str(taxon.get("id") or ""),
            "taxon_name": str(taxon.get("name") or ""),
            "taxon_preferred_common_name": str(taxon.get("preferred_common_name") or ""),
            "community_taxon_id": str(community_taxon.get("id") or ""),
            "photo_license_code": str(photo.get("license_code") or ""),
            "photo_attribution": str(photo.get("attribution") or ""),
            "annotation_pairs": ";".join(sorted(annotation_pairs)),
            "alive_dead": alive_dead,
            "evidence_organism": "yes" if "22|24" in annotation_pairs else "no",
            "evidence_scat": "yes" if "22|25" in annotation_pairs else "no",
            "evidence_track": "yes" if "22|26" in annotation_pairs else "no",
            "phase17e_source_status": "external_prefilter_probe",
            "phase17e_claim_boundary": "source discovery only; requires manual review-readiness audit",
        }
        row["phase17e_source_score"] = source_score(row)
        rows.append(row)
    return rows


def fetch_inat_research_grade_bobcats(
    pages: int,
    per_page: int,
    sleep_seconds: float,
    evidence_filter: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total_results = None
    if evidence_filter not in EVIDENCE_FILTERS:
        raise ValueError(f"unknown evidence filter: {evidence_filter}")
    for page in range(1, pages + 1):
        params = {
            "taxon_id": BOBCAT_TAXON_ID,
            "quality_grade": "research",
            "photos": "true",
            "per_page": per_page,
            "page": page,
            "order_by": "observed_on",
            "order": "desc",
        }
        params.update(EVIDENCE_FILTERS[evidence_filter])
        url = f"{INAT_OBSERVATIONS_URL}?{urllib.parse.urlencode(params)}"
        data = fetch_json(url)
        total_results = data.get("total_results", total_results)
        observations = data.get("results") or []
        for observation in observations:
            rows.extend(observation_rows(observation, evidence_filter=evidence_filter))
        print(
            f"fetched page={page} observations={len(observations)} photo_rows={len(rows)} "
            f"total_results={total_results}"
        )
        if len(observations) < per_page:
            break
        if sleep_seconds:
            time.sleep(sleep_seconds)
    audit = {
        "source": "iNaturalist observations API",
        "taxon_id": BOBCAT_TAXON_ID,
        "quality_grade": "research",
        "evidence_filter": evidence_filter,
        "evidence_query_params": EVIDENCE_FILTERS[evidence_filter],
        "pages_requested": pages,
        "per_page": per_page,
        "total_results_reported": total_results,
        "photo_rows": len(rows),
    }
    return rows, audit


def write_outputs(rows: list[dict[str, Any]], audit: dict[str, Any], top_count: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda row: (-float(row["phase17e_source_score"]), row["candidate_id"]))
    suffix = str(audit.get("evidence_filter") or "all")
    csv_path = OUTPUT_DIR / f"prototype_phase17e_inat_research_grade_bobcat_{suffix}_candidates.csv"
    top_csv_path = OUTPUT_DIR / f"prototype_phase17e_inat_research_grade_bobcat_{suffix}_top{top_count}.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        with top_csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows[:top_count])
    else:
        csv_path.write_text("", encoding="utf-8")
        top_csv_path.write_text("", encoding="utf-8")

    license_counts = Counter(row["photo_license_code"] or "none" for row in rows)
    captive_counts = Counter(row["captive"] or "unknown" for row in rows)
    audit = {
        **audit,
        "output_csv": str(csv_path),
        "top_csv": str(top_csv_path),
        "top_count": min(top_count, len(rows)),
        "license_counts": dict(license_counts),
        "captive_counts": dict(captive_counts),
        "unique_observations": len({row["observation_id"] for row in rows}),
        "unique_photos": len({row["photo_id"] for row in rows if row["photo_id"]}),
        "claim_boundary": "Prototype source discovery only; manual quality audit still required.",
    }
    (OUTPUT_DIR / f"prototype_phase17e_inat_{suffix}_source_probe_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    gallery_path = OUTPUT_DIR / f"prototype_phase17e_inat_{suffix}_gallery.html"
    write_gallery(rows[:120], gallery_path)

    lines = [
        "# Prototype Phase17E External Bobcat Source Probe",
        "",
        "Question: can externally pre-filtered Bobcat images provide a better candidate pool?",
        "",
        "## Result",
        "",
        f"- Source: iNaturalist research-grade Lynx rufus observations.",
        f"- Evidence filter: `{suffix}`.",
        f"- Reported observations available: {audit['total_results_reported']}.",
        f"- Probe photo rows fetched: {audit['photo_rows']}.",
        f"- Top candidate rows written: {audit['top_count']}.",
        f"- Unique observations in probe: {audit['unique_observations']}.",
        f"- Unique photos in probe: {audit['unique_photos']}.",
        f"- License counts: {dict(license_counts)}.",
        f"- Captive counts: {dict(captive_counts)}.",
        "",
        "## Interpretation",
        "",
        "This source is promising because observations are already community screened to research grade,",
        "but it is not automatically algorithm-ready. Phase17E still needs a manual review-readiness gate",
        "focused on side/body visibility, occlusion, individual markings, and license usability.",
        "",
        "## One Command",
        "",
        "```bash",
        "python3 scripts/prototypes/prototype_phase17e_external_bobcat_source_probe.py --evidence organism --pages 8 --per-page 200",
        "```",
        "",
        "## Files",
        "",
        f"- `{csv_path}`",
        f"- `{top_csv_path}`",
        f"- `{OUTPUT_DIR / f'prototype_phase17e_inat_{suffix}_source_probe_audit.json'}`",
        f"- `{gallery_path}`",
    ]
    (OUTPUT_DIR / f"NOTES_{suffix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gallery(rows: list[dict[str, Any]], output_path: Path) -> None:
    cards = []
    for row in rows:
        image_uri = html.escape(row["image_uri"], quote=True)
        obs_uri = html.escape(row["observation_uri"], quote=True)
        label = html.escape(
            f"{row['candidate_id']} | {row['photo_license_code'] or 'no-license'} | {row['place_guess']}",
        )
        cards.append(
            f"""
            <a class="card" href="{obs_uri}" target="_blank" rel="noreferrer">
              <img src="{image_uri}" loading="lazy" />
              <div>{label}</div>
            </a>
            """
        )
    output_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Prototype Phase17E iNat Bobcat Gallery</title>
  <style>
    body {{ margin: 24px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f7f7f5; color: #1d1d1f; }}
    h1 {{ font-size: 24px; margin-bottom: 6px; }}
    p {{ color: #555; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }}
    .card {{ display: block; color: inherit; text-decoration: none; background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
    img {{ width: 100%; height: 180px; object-fit: cover; display: block; background: #eee; }}
    .card div {{ padding: 8px; font-size: 12px; line-height: 1.35; }}
  </style>
</head>
<body>
  <h1>Prototype Phase17E iNaturalist Bobcat Gallery</h1>
  <p>First {len(rows)} research-grade Bobcat photo candidates. Click a card to open the source observation.</p>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
""",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--per-page", type=int, default=200)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--evidence", choices=sorted(EVIDENCE_FILTERS), default="all")
    parser.add_argument("--top-count", type=int, default=3000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, audit = fetch_inat_research_grade_bobcats(
        pages=args.pages,
        per_page=args.per_page,
        sleep_seconds=args.sleep_seconds,
        evidence_filter=args.evidence,
    )
    write_outputs(rows, audit, top_count=args.top_count)
    print(f"Wrote prototype source probe to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
