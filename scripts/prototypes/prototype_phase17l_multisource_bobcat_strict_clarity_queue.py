#!/usr/bin/env python3
"""PROTOTYPE: build a strict multi-source Bobcat clarity review queue.

Question:
Can we combine multiple open image sources and rank them aggressively for
clear, high-contrast, visually comparable Bobcat photos before human review?

This is throwaway source-discovery and visual-proxy logic. It does not certify
final algorithm eligibility. Final eligibility still requires manual
`phase17l_clarity_gate_decision=clear`.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17l_multisource_strict_clarity_queue"
INAT_SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17e_external_source_probe/prototype_phase17e_inat_research_grade_bobcat_organism_candidates.csv"
)
PHASE17K_WORKING_CSV = (
    PROJECT_ROOT / "outputs/phase17/phase17k_bobcat_clarity_review/phase17k_bobcat_clarity_gate_working.csv"
)
BOBCAT_TAXON_KEY_GBIF = 2435246
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "felid-review-readiness-phase17l-prototype/0.1"

BAD_TEXT_RE = re.compile(
    r"track|tracks|footprint|scat|feces|faeces|poop|skull|skeleton|taxiderm|pelt|fur|dead|roadkill|zoo|captive",
    re.IGNORECASE,
)

OUTPUT_FIELDS = [
    "candidate_id",
    "phase17l_source",
    "phase17l_source_detail",
    "source_record_id",
    "photo_id",
    "image_uri",
    "thumbnail_uri",
    "source_uri",
    "license",
    "attribution",
    "observed_on",
    "place_guess",
    "scientific_name",
    "basis_of_record",
    "prior_human_label",
    "prior_human_source",
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
    "phase17l_clarity_gate_decision",
    "phase17l_clarity_reject_reason",
    "phase17l_clarity_notes",
    "phase17l_clarity_audited_at_utc",
    "phase17l_claim_boundary",
]


def fetch_json(url: str, timeout: int = 30, attempts: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # Prototype: retry transient API/network failures.
            last_error = error
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"failed to fetch after {attempts} attempts: {url}") from last_error


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalized_image_url(url: str) -> str:
    return (
        url.replace("/original.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/small.", "/large.")
        .replace("/square.", "/large.")
        .split("?")[0]
    )


def collect_prior_labels() -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for path in [
        PHASE17K_WORKING_CSV,
        PROJECT_ROOT / "outputs/phase17/phase17j_inat_human_calibrated_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
        PROJECT_ROOT / "outputs/phase17/phase17h_inat_auto_selected_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
        PROJECT_ROOT / "outputs/phase17/phase17f_inat_organism_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
    ]:
        for row in read_csv(path):
            candidate_id = row.get("candidate_id", "")
            image_uri = normalized_image_url(row.get("image_uri", ""))
            decision = row.get("phase17k_clarity_gate_decision") or row.get("human_quality_yes_no", "")
            if decision in {"clear", "yes"}:
                label = "clear"
            elif decision in {"not_clear", "no"}:
                label = "not_clear"
            else:
                continue
            for key in {candidate_id, image_uri}:
                if key:
                    labels[key] = {"label": label, "source": str(path)}
    return labels


def source_row_base(**kwargs: str) -> dict[str, Any]:
    row = {field: "" for field in OUTPUT_FIELDS}
    row.update(kwargs)
    row["phase17l_claim_boundary"] = (
        "strict visual-proxy review queue only; final algorithm entry requires manual clear label"
    )
    return row


def collect_inat_candidates(limit: int, prior: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(INAT_SOURCE_CSV):
        text = " ".join([row.get("annotation_pairs", ""), row.get("alive_dead", ""), row.get("place_guess", "")])
        if row.get("evidence_organism") == "no" or row.get("evidence_scat") == "yes" or row.get("evidence_track") == "yes":
            continue
        if row.get("alive_dead") == "dead" or row.get("captive") == "true" or BAD_TEXT_RE.search(text):
            continue
        image_uri = normalized_image_url(row.get("image_uri", ""))
        prior_match = prior.get(row.get("candidate_id", "")) or prior.get(image_uri)
        if prior_match and prior_match["label"] == "not_clear":
            continue
        rows.append(
            source_row_base(
                candidate_id=f"phase17l_inat_{row.get('observation_id')}_{row.get('photo_id') or row.get('photo_index')}",
                phase17l_source="iNaturalist",
                phase17l_source_detail=row.get("external_source_filter", "research_grade_organism"),
                source_record_id=row.get("observation_id", ""),
                photo_id=row.get("photo_id", ""),
                image_uri=image_uri,
                thumbnail_uri=row.get("thumbnail_uri", ""),
                source_uri=row.get("observation_uri", ""),
                license=row.get("photo_license_code", ""),
                attribution=row.get("photo_attribution", ""),
                observed_on=row.get("observed_on", ""),
                place_guess=row.get("place_guess", ""),
                scientific_name=row.get("taxon_name", "Lynx rufus"),
                basis_of_record="HUMAN_OBSERVATION",
                prior_human_label=prior_match["label"] if prior_match else "",
                prior_human_source=prior_match["source"] if prior_match else "",
            )
        )
        if len(rows) >= limit:
            break
    return rows


def gbif_media_rows(result: dict[str, Any], prior: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    media_items = ((result.get("extensions") or {}).get("http://rs.gbif.org/terms/1.0/Multimedia") or [])
    rows: list[dict[str, Any]] = []
    title_text = " ".join(
        str(result.get(key, ""))
        for key in ["eventRemarks", "occurrenceRemarks", "verbatimEventDate", "locality", "datasetName", "institutionCode"]
    )
    if BAD_TEXT_RE.search(title_text):
        return rows
    for idx, media in enumerate(media_items, start=1):
        image_uri = normalized_image_url(str(media.get("http://purl.org/dc/terms/identifier") or ""))
        if not image_uri.lower().startswith("http"):
            continue
        media_text = " ".join(str(value) for value in media.values())
        if BAD_TEXT_RE.search(media_text):
            continue
        prior_match = prior.get(image_uri)
        if prior_match and prior_match["label"] == "not_clear":
            continue
        rows.append(
            source_row_base(
                candidate_id=f"phase17l_gbif_{result.get('key')}_{idx}",
                phase17l_source="GBIF",
                phase17l_source_detail=str(result.get("datasetKey", "")),
                source_record_id=str(result.get("key", "")),
                photo_id=str(media.get("http://rs.tdwg.org/dwc/terms/catalogNumber") or idx),
                image_uri=image_uri,
                thumbnail_uri=image_uri,
                source_uri=str(media.get("http://purl.org/dc/terms/references") or f"https://www.gbif.org/occurrence/{result.get('key')}"),
                license=str(media.get("http://purl.org/dc/terms/license") or result.get("license") or ""),
                attribution=str(media.get("http://purl.org/dc/terms/creator") or media.get("http://purl.org/dc/terms/rightsHolder") or ""),
                observed_on=str(result.get("eventDate") or result.get("year") or ""),
                place_guess=", ".join(str(result.get(key, "")) for key in ["locality", "stateProvince", "country"] if result.get(key)),
                scientific_name=str(result.get("scientificName") or "Lynx rufus"),
                basis_of_record=str(result.get("basisOfRecord") or ""),
                prior_human_label=prior_match["label"] if prior_match else "",
                prior_human_source=prior_match["source"] if prior_match else "",
            )
        )
    return rows


def collect_gbif_candidates(max_occurrences: int, page_size: int, prior: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while offset < max_occurrences:
        params = {
            "taxonKey": BOBCAT_TAXON_KEY_GBIF,
            "mediaType": "StillImage",
            "occurrenceStatus": "PRESENT",
            "limit": min(page_size, max_occurrences - offset),
            "offset": offset,
        }
        url = f"{GBIF_OCCURRENCE_URL}?{urllib.parse.urlencode(params)}"
        data = fetch_json(url)
        results = data.get("results") or []
        for result in results:
            rows.extend(gbif_media_rows(result, prior))
        print(f"GBIF offset={offset} occurrences={len(results)} media_rows={len(rows)}")
        if not results or data.get("endOfRecords"):
            break
        offset += len(results)
    return rows


def collect_commons_candidates(limit: int, prior: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while len(rows) < limit:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": 'Lynx rufus OR bobcat -track -tracks -skull -taxidermy -zoo',
            "gsrnamespace": 6,
            "gsrlimit": min(50, limit - len(rows)),
            "gsroffset": offset,
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
        }
        url = f"{COMMONS_API_URL}?{urllib.parse.urlencode(params)}"
        data = fetch_json(url)
        pages = (data.get("query") or {}).get("pages") or {}
        if not pages:
            break
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            categories = str((meta.get("Categories") or {}).get("value") or "")
            title = str(page.get("title") or "")
            if BAD_TEXT_RE.search(f"{title} {categories}"):
                continue
            image_uri = str(info.get("url") or "")
            if not image_uri:
                continue
            prior_match = prior.get(normalized_image_url(image_uri))
            if prior_match and prior_match["label"] == "not_clear":
                continue
            rows.append(
                source_row_base(
                    candidate_id=f"phase17l_commons_{page.get('pageid')}",
                    phase17l_source="Wikimedia Commons",
                    phase17l_source_detail=title,
                    source_record_id=str(page.get("pageid", "")),
                    photo_id=str(page.get("pageid", "")),
                    image_uri=image_uri,
                    thumbnail_uri=image_uri,
                    source_uri=str(info.get("descriptionurl") or ""),
                    license=str((meta.get("LicenseShortName") or {}).get("value") or ""),
                    attribution=str((meta.get("Artist") or {}).get("value") or ""),
                    observed_on=str((meta.get("DateTimeOriginal") or meta.get("DateTime") or {}).get("value") or ""),
                    place_guess=categories,
                    scientific_name="Lynx rufus",
                    basis_of_record="MEDIA",
                    prior_human_label=prior_match["label"] if prior_match else "",
                    prior_human_source=prior_match["source"] if prior_match else "",
                )
            )
            if len(rows) >= limit:
                break
        offset = int((data.get("continue") or {}).get("gsroffset") or 0)
        if not offset:
            break
    return rows


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_images: set[str] = set()
    seen_records: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        image_key = normalized_image_url(str(row.get("image_uri", ""))).lower()
        record_key = (str(row.get("phase17l_source", "")), str(row.get("source_record_id", "")))
        if not image_key or image_key in seen_images or record_key in seen_records:
            continue
        seen_images.add(image_key)
        seen_records.add(record_key)
        output.append(row)
    return output


def image_url_fallbacks(url: str) -> list[str]:
    candidates = [url]
    if "/large." in url:
        candidates.extend([url.replace("/large.", "/original."), url.replace("/large.", "/medium.")])
    if "/original." in url:
        candidates.extend([url.replace("/original.", "/large."), url.replace("/original.", "/medium.")])
    if "/medium." in url:
        candidates.extend([url.replace("/medium.", "/large."), url.replace("/medium.", "/original.")])
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def download_image_bytes(url: str, timeout: int) -> bytes:
    last_error: Exception | None = None
    for candidate in image_url_fallbacks(url):
        request = urllib.request.Request(url=candidate, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:
            last_error = error
    raise RuntimeError(f"all image URL fallbacks failed for {url}: {last_error}")


def laplacian_variance(gray: np.ndarray) -> float:
    center = gray[1:-1, 1:-1] * -4.0
    lap = center + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(np.var(lap))


def image_metrics(image_bytes: bytes) -> dict[str, float | int | str]:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        width, height = image.size
        resized = image.copy()
        resized.thumbnail((768, 768))
        gray_image = resized.convert("L")
        gray = np.asarray(gray_image, dtype=np.float32)
        contrast_std = float(np.std(gray))
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
        hist = gray_image.histogram()
        total = sum(hist) or 1
        entropy = -sum((count / total) * math.log2(count / total) for count in hist if count)
        stat = ImageStat.Stat(resized)
        r, g, b = [np.asarray(channel, dtype=np.float32) for channel in resized.split()]
        rg = np.abs(r - g)
        yb = np.abs(0.5 * (r + g) - b)
        return {
            "image_width": width,
            "image_height": height,
            "image_megapixels": round((width * height) / 1_000_000, 4),
            "download_bytes": len(image_bytes),
            "contrast_std": round(contrast_std, 4),
            "gradient_mean": round(float(np.mean(gradient)), 4),
            "gradient_p90": round(float(np.percentile(gradient, 90)), 4),
            "laplacian_var": round(laplacian_variance(gray), 4),
            "entropy": round(float(entropy), 4),
            "dark_clip_fraction": round(sum(hist[:8]) / total, 6),
            "bright_clip_fraction": round(sum(hist[248:]) / total, 6),
            "colorfulness_proxy": round(float(np.std(rg) + np.std(yb) + 0.3 * np.mean(rg + yb)), 4),
        }


def strict_score(metrics: dict[str, Any], row: dict[str, Any]) -> tuple[float, str, str]:
    reject: list[str] = []
    min_dim = min(float(metrics["image_width"]), float(metrics["image_height"]))
    megapixels = float(metrics["image_megapixels"])
    contrast = float(metrics["contrast_std"])
    gradient_p90 = float(metrics["gradient_p90"])
    lap_var = float(metrics["laplacian_var"])
    entropy = float(metrics["entropy"])
    clipping = float(metrics["dark_clip_fraction"]) + float(metrics["bright_clip_fraction"])

    if min_dim < 900:
        reject.append("min_dimension_lt_900")
    if megapixels < 1.2:
        reject.append("megapixels_lt_1_2")
    if int(metrics["download_bytes"]) < 120_000:
        reject.append("small_file")
    if contrast < 42:
        reject.append("low_contrast")
    if gradient_p90 < 18:
        reject.append("weak_edges")
    if lap_var < 80:
        reject.append("low_sharpness_proxy")
    if entropy < 5.0:
        reject.append("low_entropy")
    if clipping > 0.35:
        reject.append("heavy_shadow_highlight_clipping")

    score = 0.0
    score += min(18.0, megapixels * 3.0)
    score += min(22.0, contrast / 3.0)
    score += min(18.0, gradient_p90 / 2.0)
    score += min(22.0, lap_var / 16.0)
    score += min(8.0, entropy)
    score += max(0.0, 8.0 - clipping * 18.0)
    if row.get("prior_human_label") == "clear":
        score += 18.0
    if row.get("phase17l_source") == "Wikimedia Commons":
        score += 4.0
    if row.get("phase17l_source") == "GBIF" and "inaturalist" not in row.get("image_uri", "").lower():
        score += 2.0

    if not reject and score >= 72:
        tier = "strict_pass"
    elif len(reject) <= 2 and score >= 62:
        tier = "near_strict"
    else:
        tier = "review_only"
    return round(score, 4), tier, ";".join(reject)


def score_one(row: dict[str, Any], timeout: int) -> dict[str, Any]:
    try:
        metrics = image_metrics(download_image_bytes(str(row["image_uri"]), timeout=timeout))
        score, tier, reject = strict_score(metrics, row)
        row.update(metrics)
        row["phase17l_strict_clarity_proxy_score"] = score
        row["phase17l_strict_proxy_tier"] = tier
        row["phase17l_proxy_reject_reasons"] = reject
        row["phase17l_clarity_gate_decision"] = "clear" if row.get("prior_human_label") == "clear" else ""
    except Exception as error:
        row["phase17l_strict_clarity_proxy_score"] = -1
        row["phase17l_strict_proxy_tier"] = "download_or_decode_failed"
        row["phase17l_proxy_reject_reasons"] = f"{type(error).__name__}: {str(error)[:120]}"
    return row


def score_rows(rows: list[dict[str, Any]], score_limit: int, workers: int, timeout: int) -> list[dict[str, Any]]:
    rows = rows[:score_limit]
    scored: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(score_one, dict(row), timeout) for row in rows]
        for index, future in enumerate(as_completed(futures), start=1):
            scored.append(future.result())
            if index % 100 == 0:
                print(f"scored_images={index}/{len(futures)}")
    return scored


def row_sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
    score = float(row.get("phase17l_strict_clarity_proxy_score") or -1)
    prior = 1.0 if row.get("prior_human_label") == "clear" else 0.0
    return (-prior, -score, str(row.get("candidate_id", "")))


def write_gallery(rows: list[dict[str, Any]], output_path: Path) -> None:
    cards = []
    for row in rows:
        image_uri = html.escape(str(row.get("image_uri", "")), quote=True)
        source_uri = html.escape(str(row.get("source_uri", "")), quote=True)
        title = html.escape(
            f"{row.get('candidate_id')} | {row.get('phase17l_source')} | score={row.get('phase17l_strict_clarity_proxy_score')} | {row.get('phase17l_strict_proxy_tier')}",
            quote=False,
        )
        cards.append(
            f"""
            <a class="card" href="{source_uri or image_uri}" target="_blank" rel="noreferrer">
              <img src="{image_uri}" loading="lazy" />
              <div>{title}</div>
            </a>
            """
        )
    output_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Phase17L strict clarity queue gallery</title>
  <style>
    body {{ margin: 24px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f6f3; color: #202124; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }}
    .card {{ display: block; color: inherit; text-decoration: none; background: #fff; border: 1px solid #d6d9d2; border-radius: 6px; overflow: hidden; }}
    img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: contain; display: block; background: #eceee8; }}
    .card div {{ padding: 8px; font-size: 12px; line-height: 1.35; }}
  </style>
</head>
<body>
  <h1>Phase17L strict clarity queue gallery</h1>
  <p>Top {len(rows)} candidates. This is a visual-proxy review queue, not final eligibility.</p>
  <div class="grid">{''.join(cards)}</div>
</body>
</html>
""",
        encoding="utf-8",
    )


def build_queue(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prior = collect_prior_labels()
    print(f"prior_labels={len(prior)}")
    all_rows: list[dict[str, Any]] = []
    if "inat" in args.sources:
        all_rows.extend(collect_inat_candidates(args.inat_limit, prior))
    if "gbif" in args.sources:
        all_rows.extend(collect_gbif_candidates(args.gbif_occurrence_limit, args.gbif_page_size, prior))
    if "commons" in args.sources:
        all_rows.extend(collect_commons_candidates(args.commons_limit, prior))

    deduped = dedupe_rows(all_rows)
    source_counts_before = Counter(row["phase17l_source"] for row in all_rows)
    source_counts_after = Counter(row["phase17l_source"] for row in deduped)
    pre_score_path = OUTPUT_DIR / "phase17l_multisource_bobcat_pre_score_candidates.csv"
    write_csv(pre_score_path, deduped, OUTPUT_FIELDS)

    # Put curated and prior-positive material first for scoring, then the larger API pool.
    deduped.sort(
        key=lambda row: (
            row.get("prior_human_label") != "clear",
            row.get("phase17l_source") != "Wikimedia Commons",
            row.get("phase17l_source") != "iNaturalist",
            row.get("candidate_id", ""),
        )
    )
    scored_all = score_rows(deduped, args.score_limit, args.workers, args.timeout)
    scored_all_path = OUTPUT_DIR / "phase17l_multisource_bobcat_scored_all.csv"
    write_csv(scored_all_path, scored_all, OUTPUT_FIELDS)
    scored = [row for row in scored_all if float(row.get("phase17l_strict_clarity_proxy_score") or -1) >= 0]
    scored.sort(key=row_sort_key)
    selected = scored[: args.target_count]

    output_csv = OUTPUT_DIR / "phase17l_bobcat_strict_clarity_review_queue_5000.csv"
    write_csv(output_csv, selected, OUTPUT_FIELDS)
    write_gallery(selected[: args.gallery_count], OUTPUT_DIR / "phase17l_bobcat_strict_clarity_gallery.html")

    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": "Can multi-source open image discovery create a stricter 5000-row Bobcat clarity review queue?",
        "sources_requested": args.sources,
        "candidate_rows_before_dedupe": len(all_rows),
        "candidate_rows_after_dedupe": len(deduped),
        "scored_rows": len(scored),
        "download_or_decode_failed_rows": len(scored_all) - len(scored),
        "selected_rows": len(selected),
        "target_count": args.target_count,
        "source_counts_before_dedupe": dict(source_counts_before),
        "source_counts_after_dedupe": dict(source_counts_after),
        "selected_source_counts": dict(Counter(row["phase17l_source"] for row in selected)),
        "selected_tier_counts": dict(Counter(row["phase17l_strict_proxy_tier"] for row in selected)),
        "selected_proxy_reject_reason_counts": dict(Counter(row["phase17l_proxy_reject_reasons"] or "none" for row in selected).most_common(30)),
        "output_csv": str(output_csv),
        "pre_score_csv": str(pre_score_path),
        "scored_all_csv": str(scored_all_path),
        "gallery": str(OUTPUT_DIR / "phase17l_bobcat_strict_clarity_gallery.html"),
        "claim_boundary": "The queue is stricter than source metadata but still requires human CLEAR review for 100% clarity.",
    }
    (OUTPUT_DIR / "phase17l_bobcat_strict_clarity_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    notes = [
        "# Phase17L Multisource Strict Clarity Queue Prototype",
        "",
        "Question: can multiple open image databases provide a stricter Bobcat review queue than iNaturalist alone?",
        "",
        "## Verdict Placeholder",
        "",
        "This queue is for human review. It must not be treated as final algorithm eligibility until rows are manually marked clear.",
        "",
        "## One Command",
        "",
        "```bash",
        "python3 scripts/prototypes/prototype_phase17l_multisource_bobcat_strict_clarity_queue.py --sources inat gbif commons --target-count 5000",
        "```",
        "",
        "## Outputs",
        "",
        f"- `{output_csv}`",
        f"- `{pre_score_path}`",
        f"- `{scored_all_path}`",
        f"- `{OUTPUT_DIR / 'phase17l_bobcat_strict_clarity_audit.json'}`",
        f"- `{OUTPUT_DIR / 'phase17l_bobcat_strict_clarity_gallery.html'}`",
    ]
    (OUTPUT_DIR / "NOTES.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=["inat", "gbif", "commons"], default=["inat", "gbif", "commons"])
    parser.add_argument("--target-count", type=int, default=5000)
    parser.add_argument("--inat-limit", type=int, default=12000)
    parser.add_argument("--gbif-occurrence-limit", type=int, default=12000)
    parser.add_argument("--gbif-page-size", type=int, default=300)
    parser.add_argument("--commons-limit", type=int, default=500)
    parser.add_argument("--score-limit", type=int, default=8500)
    parser.add_argument("--gallery-count", type=int, default=500)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_queue(args)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
