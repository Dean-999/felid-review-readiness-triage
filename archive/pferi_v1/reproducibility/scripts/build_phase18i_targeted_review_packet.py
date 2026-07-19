#!/usr/bin/env python3
"""Build Phase18I targeted pair-review packets from Phase18H samples."""

from __future__ import annotations

import argparse
import html
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from scripts.phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, resolve_project_path, write_csv, write_json


DEFAULT_OUTPUT_ROOT = Path("outputs/phase18/phase18i_targeted_review_packet")
RANDOM_SEED = 20260702
CONTACT_SHEET_COLUMNS = 4
THUMB_SIZE = (220, 220)
CELL_WIDTH = 520
CELL_HEIGHT = 340

REVIEW_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "sample_group",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "same_identity_known_id",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "phase18h_interpretation",
    "reviewability_label",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
    "claim_boundary",
]

BLIND_COLUMNS = [
    "review_pair_id",
    "query_image_path",
    "candidate_image_path",
    "reviewability_label",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
]

CODEBOOK_ROWS = [
    {
        "field": "reviewability_label",
        "allowed_value": "review_ready",
        "definition": "Both images expose enough comparable animal evidence for a reviewer to assess the pair.",
    },
    {
        "field": "reviewability_label",
        "allowed_value": "low_evidence",
        "definition": "One or both images are too low quality, occluded, distant, or visually weak for reliable pair review.",
    },
    {
        "field": "reviewability_label",
        "allowed_value": "non_comparable",
        "definition": "The two images do not show comparable body regions, pose, scale, or view for the intended evidence comparison.",
    },
    {
        "field": "reviewability_label",
        "allowed_value": "uncertain",
        "definition": "Reviewer cannot choose a stronger label without additional context.",
    },
]


def manifest_by_image_id(phase18a_manifest: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(phase18a_manifest)
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        image_id = row["phase18_image_id"]
        if image_id in by_id:
            raise ValueError(f"duplicate phase18_image_id in Phase18A manifest: {image_id}")
        by_id[image_id] = row
    return by_id


def resolved_existing_path(value: str) -> Path:
    path = resolve_project_path(value)
    if not path.exists():
        raise ValueError(f"missing review image file: {value}")
    return path


def review_rows(
    descriptor_name: str,
    phase18h_sample_csv: Path,
    phase18a_manifest: Path,
    random_seed: int,
) -> list[dict[str, Any]]:
    samples = read_csv(phase18h_sample_csv)
    if not samples:
        raise ValueError("0 Phase18H sample rows")
    by_id = manifest_by_image_id(phase18a_manifest)
    rows = []
    for idx, sample in enumerate(samples, start=1):
        query_id = sample["query_image_id"]
        candidate_id = sample["candidate_image_id"]
        if query_id not in by_id:
            raise ValueError(f"query image missing from Phase18A manifest: {query_id}")
        if candidate_id not in by_id:
            raise ValueError(f"candidate image missing from Phase18A manifest: {candidate_id}")
        query_path = resolved_existing_path(by_id[query_id]["frozen_image_path"])
        candidate_path = resolved_existing_path(by_id[candidate_id]["frozen_image_path"])
        rows.append(
            {
                "review_pair_id": f"phase18i_{descriptor_name}_{idx:04d}",
                "descriptor_name": descriptor_name,
                "sample_group": sample["sample_group"],
                "query_image_id": query_id,
                "candidate_image_id": candidate_id,
                "query_image_path": project_relative(query_path),
                "candidate_image_path": project_relative(candidate_path),
                "same_identity_known_id": sample["same_identity"],
                "candidate_rank_descriptor": sample["candidate_rank_descriptor"],
                "descriptor_similarity": sample["descriptor_similarity"],
                "descriptor_similarity_percentile": sample["descriptor_similarity_percentile"],
                "descriptor_evidence_conflict_score": sample["descriptor_evidence_conflict_score"],
                "pf_eri_admissibility_score": sample["pf_eri_admissibility_score"],
                "pf_eri_review_score": sample["pf_eri_review_score"],
                "pf_eri_route": sample["pf_eri_route"],
                "weakest_image_quality_score": sample["weakest_image_quality_score"],
                "pair_geometry_score": sample["pair_geometry_score"],
                "phase18h_interpretation": sample["interpretation"],
                "reviewability_label": "",
                "visibility_notes": "",
                "reviewer_id": "",
                "review_timestamp": "",
                "claim_boundary": "Human review packet labels pair reviewability only; not Bobcat identity accuracy and not automatic ID.",
            }
        )
    rng = random.Random(random_seed)
    rng.shuffle(rows)
    for idx, row in enumerate(rows, start=1):
        row["review_pair_id"] = f"phase18i_{descriptor_name}_blind_{idx:04d}"
    return rows


def fit_image(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", THUMB_SIZE, "white")
    left = (THUMB_SIZE[0] - image.width) // 2
    top = (THUMB_SIZE[1] - image.height) // 2
    canvas.paste(image, (left, top))
    return canvas


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, width: int) -> None:
    font = ImageFont.load_default()
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    y = xy[1]
    for line in lines[:5]:
        draw.text((xy[0], y), line, fill="black", font=font)
        y += 14


def build_contact_sheet(rows: list[dict[str, Any]], output_path: Path) -> None:
    page_count = len(rows)
    if page_count == 0:
        return
    cols = CONTACT_SHEET_COLUMNS
    rows_count = math.ceil(page_count / cols)
    sheet = Image.new("RGB", (cols * CELL_WIDTH, rows_count * CELL_HEIGHT), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(rows):
        col = idx % cols
        r = idx // cols
        x = col * CELL_WIDTH
        y = r * CELL_HEIGHT
        draw.rectangle((x, y, x + CELL_WIDTH - 1, y + CELL_HEIGHT - 1), outline=(210, 210, 210))
        query = fit_image(resolve_project_path(row["query_image_path"]))
        candidate = fit_image(resolve_project_path(row["candidate_image_path"]))
        sheet.paste(query, (x + 20, y + 36))
        sheet.paste(candidate, (x + 280, y + 36))
        draw.text((x + 20, y + 14), row["review_pair_id"], fill="black", font=ImageFont.load_default())
        draw.text((x + 20, y + 262), "query", fill="black", font=ImageFont.load_default())
        draw.text((x + 280, y + 262), "candidate", fill="black", font=ImageFont.load_default())
        draw_text(
            draw,
            (x + 20, y + 286),
            "Label one: review_ready / low_evidence / non_comparable / uncertain",
            CELL_WIDTH - 40,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def build_review_html(rows: list[dict[str, Any]], output_path: Path) -> None:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Phase18I Targeted Review Packet</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;color:#222}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:18px}"
        ".pair{border:1px solid #ddd;padding:12px}.imgs{display:flex;gap:12px}"
        "img{width:220px;height:220px;object-fit:contain;background:#f8f8f8}"
        ".id{font-weight:700;margin-bottom:8px}.labels{font-size:13px;color:#555;margin-top:8px}</style>",
        "</head><body><h1>Phase18I Targeted Review Packet</h1>",
        "<p>Label pair reviewability only: review_ready, low_evidence, non_comparable, or uncertain. Do not infer new identity labels from this packet.</p>",
        "<div class='grid'>",
    ]
    for row in rows:
        q = html.escape(row["query_image_path"])
        c = html.escape(row["candidate_image_path"])
        parts.extend(
            [
                "<div class='pair'>",
                f"<div class='id'>{html.escape(row['review_pair_id'])}</div>",
                "<div class='imgs'>",
                f"<div><img src='../../../../{q}'><div>query</div></div>",
                f"<div><img src='../../../../{c}'><div>candidate</div></div>",
                "</div>",
                "<div class='labels'>reviewability_label: ____________________<br>notes: ____________________</div>",
                "</div>",
            ]
        )
    parts.extend(["</div></body></html>"])
    output_path.write_text("\n".join(parts), encoding="utf-8")


def build_phase18i_targeted_review_packet(
    descriptor_name: str,
    phase18h_sample_csv: Path,
    phase18a_manifest: Path,
    output_dir: Path,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = review_rows(descriptor_name, phase18h_sample_csv, phase18a_manifest, random_seed)
    review_csv = output_dir / "phase18i_targeted_pair_review_packet.csv"
    blind_csv = output_dir / "phase18i_blind_review_form.csv"
    codebook_csv = output_dir / "phase18i_reviewability_codebook.csv"
    contact_sheet = output_dir / "phase18i_contact_sheet.jpg"
    html_path = output_dir / "phase18i_review_packet.html"
    write_csv(review_csv, rows, REVIEW_COLUMNS)
    write_csv(blind_csv, rows, BLIND_COLUMNS)
    write_csv(codebook_csv, CODEBOOK_ROWS, ["field", "allowed_value", "definition"])
    build_contact_sheet(rows, contact_sheet)
    build_review_html(rows, html_path)
    group_counts: dict[str, int] = {}
    known_id_counts: dict[str, int] = {}
    for row in rows:
        group_counts[row["sample_group"]] = group_counts.get(row["sample_group"], 0) + 1
        known_id_counts[row["same_identity_known_id"]] = known_id_counts.get(row["same_identity_known_id"], 0) + 1
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "phase18h_sample_csv": project_relative(phase18h_sample_csv),
        "phase18a_manifest": project_relative(phase18a_manifest),
        "review_csv": project_relative(review_csv),
        "blind_csv": project_relative(blind_csv),
        "codebook_csv": project_relative(codebook_csv),
        "contact_sheet": project_relative(contact_sheet),
        "html_review_packet": project_relative(html_path),
        "review_pair_rows": len(rows),
        "sample_group_counts": group_counts,
        "known_id_truth_counts_retained_for_analysis_only": known_id_counts,
        "random_seed": random_seed,
        "status": "PASS",
        "claim_boundary": "Phase18I prepares targeted reviewability audit data; it does not create identity labels or final PF-ERI claims.",
    }
    write_json(output_dir / "phase18i_targeted_review_packet_audit.json", audit)
    (output_dir / "README.md").write_text(
        f"# Phase18I Targeted Review Packet: {descriptor_name}\n\n"
        "This packet supports human review of pair-level reviewability only. "
        "Allowed labels are documented in `phase18i_reviewability_codebook.csv`.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor-name", required=True)
    parser.add_argument("--phase18h-sample-csv", type=Path, required=True)
    parser.add_argument(
        "--phase18a-manifest",
        type=Path,
        default=Path("outputs/phase18/phase18a_frozen_feature_manifest/phase18a_frozen_image_feature_manifest.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / args.descriptor_name
    audit = build_phase18i_targeted_review_packet(
        descriptor_name=args.descriptor_name,
        phase18h_sample_csv=args.phase18h_sample_csv,
        phase18a_manifest=args.phase18a_manifest,
        output_dir=output_dir,
        random_seed=args.random_seed,
    )
    print("PASS phase18i targeted review packet")
    print(f"descriptor_name={audit['descriptor_name']}")
    print(f"review_pair_rows={audit['review_pair_rows']}")
    print(f"WROTE {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
