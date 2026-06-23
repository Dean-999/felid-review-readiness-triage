#!/usr/bin/env python3
"""Package Phase 15F bobcat pair-audit samples.

The package samples bobcat candidate pairs from each Phase 15E review action and
creates side-by-side review sheets plus a blank manual-audit template. Bobcat
individual identities are unavailable, so the audit validates review-routing
judgements, not identity accuracy.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase15/bobcat_pair_audit_package"
SHEET_DIR = OUT_DIR / "pair_sheets"
MANIFEST_CSV = OUT_DIR / "phase15f_bobcat_pair_audit_manifest.csv"
BLANK_TEMPLATE_CSV = OUT_DIR / "phase15f_bobcat_pair_audit_blank_template.csv"
SUMMARY_CSV = OUT_DIR / "phase15f_bobcat_pair_audit_sample_summary.csv"
ZIP_PATH = OUT_DIR / "phase15f_bobcat_pair_audit_250_pair_sheets.zip"
AUDIT_JSON = OUT_DIR / "phase15f_bobcat_pair_audit_package_audit.json"
REPORT_MD = OUT_DIR / "phase15f_bobcat_pair_audit_package_report.md"

ACTION_ORDER = ["accept", "review", "defer", "species_level_only", "non_comparable"]
DEFAULT_PER_ACTION = 50
DEFAULT_SEED = 20260622
SHEET_SIZE = (1800, 1120)
IMAGE_PANEL_SIZE = (860, 830)
PANEL_TOP = 210
PANEL_LABEL_TOP = 174

MANUAL_COLUMNS = [
    "manual_pair_action",
    "manual_pair_comparability",
    "manual_identity_evidence",
    "manual_review_confidence",
    "manual_same_individual_if_judgable",
    "manual_notes",
]

ALLOWED_MANUAL_VALUES = {
    "manual_pair_action": "accept|review|defer|species_level_only|non_comparable|exclude",
    "manual_pair_comparability": "high|medium|low|none|uncertain",
    "manual_identity_evidence": "strong|moderate|weak|none|uncertain",
    "manual_review_confidence": "high|medium|low",
    "manual_same_individual_if_judgable": "same|different|uncertain|not_judgable",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def clear_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def choose_samples(data: pd.DataFrame, per_action: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for action in ACTION_ORDER:
        part = data[data["phase15e_review_action"].eq(action)].copy()
        if len(part) < per_action:
            raise ValueError(f"Not enough rows for {action}: {len(part)} < {per_action}")
        part["score_bin"] = pd.qcut(
            numeric(part["phase15e_transfer_hgb_score"]).rank(method="first"),
            q=min(5, len(part)),
            labels=False,
            duplicates="drop",
        )
        axis_groups = sorted(part["query_evidence_axis"].dropna().astype(str).unique())
        selected_parts = []
        base_per_axis = max(1, per_action // max(len(axis_groups), 1))
        for axis in axis_groups:
            axis_part = part[part["query_evidence_axis"].astype(str).eq(axis)].copy()
            if axis_part.empty:
                continue
            n = min(base_per_axis, len(axis_part))
            bin_samples = []
            per_bin = max(1, int(np.ceil(n / max(axis_part["score_bin"].nunique(), 1))))
            for _, bin_part in axis_part.groupby("score_bin", sort=True):
                bin_samples.append(
                    bin_part.sample(
                        n=min(len(bin_part), per_bin),
                        random_state=int(rng.integers(0, 2**31 - 1)),
                    )
                )
            sampled = pd.concat(bin_samples, ignore_index=False)
            selected_parts.append(sampled)
        selected = pd.concat(selected_parts, ignore_index=False).drop_duplicates(
            ["query_image_evidence_id", "candidate_image_evidence_id"]
        )
        if len(selected) < per_action:
            remaining = part.drop(index=selected.index, errors="ignore")
            extra = remaining.sample(
                n=per_action - len(selected),
                random_state=int(rng.integers(0, 2**31 - 1)),
            )
            selected = pd.concat([selected, extra], ignore_index=False)
        elif len(selected) > per_action:
            selected = selected.sample(n=per_action, random_state=int(rng.integers(0, 2**31 - 1)))
        selected = selected.copy()
        selected["audit_action_group"] = action
        rows.append(selected)
    sampled_all = pd.concat(rows, ignore_index=True)
    sampled_all = sampled_all.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    sampled_all.insert(0, "audit_pair_index", np.arange(1, len(sampled_all) + 1))
    sampled_all.insert(1, "audit_pair_id", sampled_all["audit_pair_index"].map(lambda i: f"p15f_bobcat_pair_{i:04d}"))
    return sampled_all


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def text_lines(row: pd.Series) -> list[str]:
    return [
        f"Pair: {row['audit_pair_id']} | Action: {row['phase15e_review_action']} | Query axis: {row['query_evidence_axis']}",
        f"Rank: {int(row['rank'])} | Descriptor: {float(row['descriptor_similarity']):.3f} | HGB: {float(row['phase15e_transfer_hgb_score']):.3f}",
        f"Pair comparability: {float(row['pair_comparability_score']):.3f} | Weakest utility: {float(row['weakest_image_utility_score']):.3f} | Conflict: {float(row['descriptor_evidence_conflict_score']):.3f}",
        f"Failure reason: {row['primary_failure_reason']}",
    ]


def draw_sheet(row: pd.Series, out_path: Path) -> None:
    q_path = Path(str(row["query_image_path"]))
    c_path = Path(str(row["candidate_image_path"]))
    if not q_path.exists() or not c_path.exists():
        missing = [str(p) for p in [q_path, c_path] if not p.exists()]
        raise FileNotFoundError(f"Missing pair image(s): {missing}")

    sheet = Image.new("RGB", SHEET_SIZE, "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("Arial.ttf", 28)
        small = ImageFont.truetype("Arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    query_panel = fit_image(q_path, IMAGE_PANEL_SIZE)
    candidate_panel = fit_image(c_path, IMAGE_PANEL_SIZE)
    sheet.paste(query_panel, (30, PANEL_TOP))
    sheet.paste(candidate_panel, (910, PANEL_TOP))
    draw.rectangle(
        (30, PANEL_TOP, 30 + IMAGE_PANEL_SIZE[0], PANEL_TOP + IMAGE_PANEL_SIZE[1]),
        outline="black",
        width=3,
    )
    draw.rectangle(
        (910, PANEL_TOP, 910 + IMAGE_PANEL_SIZE[0], PANEL_TOP + IMAGE_PANEL_SIZE[1]),
        outline="black",
        width=3,
    )
    draw.text((30, PANEL_LABEL_TOP), "QUERY", fill="black", font=font)
    draw.text((910, PANEL_LABEL_TOP), "CANDIDATE", fill="black", font=font)
    y = 16
    for line in text_lines(row):
        draw.text((30, y), line, fill="black", font=small)
        y += 28
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet = ImageOps.exif_transpose(sheet)
    sheet.save(out_path, quality=92)


def make_package(sampled: pd.DataFrame) -> pd.DataFrame:
    clear_dir(SHEET_DIR)
    rows = []
    for _, row in sampled.iterrows():
        sheet_name = f"{row['audit_pair_id']}_{row['phase15e_review_action']}.jpg"
        sheet_path = SHEET_DIR / sheet_name
        draw_sheet(row, sheet_path)
        out = row.to_dict()
        out["pair_sheet_path"] = str(sheet_path)
        out["pair_sheet_relative_path"] = rel(sheet_path)
        rows.append(out)
    return pd.DataFrame(rows)


def write_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SHEET_DIR.glob("*.jpg")):
            zf.write(path, arcname=f"pair_sheets/{path.name}")


def write_report(summary: pd.DataFrame, audit: dict[str, Any]) -> None:
    lines = [
        "# Phase 15F Bobcat Pair-Audit Package",
        "",
        "This package samples bobcat candidate pairs from the Phase 15E evidence-routed review table for manual audit.",
        "",
        "## Boundary",
        "",
        "Bobcat individual identities are unavailable. The audit validates review-routing labels and pair comparability, not bobcat identity accuracy.",
        "",
        "## Manual Label Columns",
        "",
    ]
    for column, allowed in ALLOWED_MANUAL_VALUES.items():
        lines.append(f"- `{column}`: {allowed}")
    lines.extend(
        [
            "- `manual_notes`: free text",
            "",
            "## Sample Summary",
            "",
            "| Action | Pairs | High-confidence queries | Low-evidence queries |",
            "|---|---:|---:|---:|",
        ]
    )
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['phase15e_review_action']} | {int(row['pairs'])} | "
            f"{int(row.get('high_confidence_queries', 0))} | {int(row.get('low_evidence_stress_queries', 0))} |"
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Manifest: `{audit['outputs']['manifest']}`",
            f"- Blank template: `{audit['outputs']['blank_template']}`",
            f"- Pair sheets zip: `{audit['outputs']['zip']}`",
            f"- Pair sheets directory: `{audit['outputs']['pair_sheets_dir']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(sampled: pd.DataFrame) -> pd.DataFrame:
    axis_counts = (
        sampled.groupby(["phase15e_review_action", "query_evidence_axis"]).size().unstack(fill_value=0).reset_index()
    )
    axis_counts = axis_counts.rename(
        columns={
            "high_confidence": "high_confidence_queries",
            "low_evidence_stress": "low_evidence_stress_queries",
        }
    )
    total = sampled.groupby("phase15e_review_action", as_index=False).agg(
        pairs=("audit_pair_id", "size"),
        mean_descriptor_similarity=("descriptor_similarity", "mean"),
        mean_hgb_score=("phase15e_transfer_hgb_score", "mean"),
        mean_pair_comparability=("pair_comparability_score", "mean"),
        mean_conflict=("descriptor_evidence_conflict_score", "mean"),
    )
    return total.merge(axis_counts, on="phase15e_review_action", how="left").sort_values("phase15e_review_action")


def run(args: argparse.Namespace) -> dict[str, Any]:
    data = pd.read_csv(args.input, low_memory=False)
    required = {
        "phase15e_review_action",
        "query_image_path",
        "candidate_image_path",
        "query_evidence_axis",
        "descriptor_similarity",
        "phase15e_transfer_hgb_score",
        "pair_comparability_score",
        "weakest_image_utility_score",
        "descriptor_evidence_conflict_score",
        "primary_failure_reason",
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    sampled = choose_samples(data, args.per_action, args.seed)
    packaged = make_package(sampled)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    packaged.to_csv(MANIFEST_CSV, index=False)
    blank = packaged[
        [
            "audit_pair_id",
            "audit_action_group",
            "phase15e_review_action",
            "query_evidence_axis",
            "rank",
            "descriptor_similarity",
            "phase15e_transfer_hgb_score",
            "pair_comparability_score",
            "weakest_image_utility_score",
            "descriptor_evidence_conflict_score",
            "primary_failure_reason",
            "pair_sheet_relative_path",
        ]
    ].copy()
    for column in MANUAL_COLUMNS:
        blank[column] = ""
    blank.to_csv(BLANK_TEMPLATE_CSV, index=False)
    summary = summarize(packaged)
    summary.to_csv(SUMMARY_CSV, index=False)
    write_zip()

    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "input": rel(args.input),
        "output_dir": rel(OUT_DIR),
        "seed": int(args.seed),
        "per_action": int(args.per_action),
        "sampled_pairs": int(len(packaged)),
        "action_counts": packaged["phase15e_review_action"].value_counts().to_dict(),
        "manual_columns": MANUAL_COLUMNS,
        "claim_boundary": "Bobcat manual audit package validates review-routing/comparability only, not identity accuracy.",
        "outputs": {
            "manifest": rel(MANIFEST_CSV),
            "blank_template": rel(BLANK_TEMPLATE_CSV),
            "summary": rel(SUMMARY_CSV),
            "zip": rel(ZIP_PATH),
            "pair_sheets_dir": rel(SHEET_DIR),
            "report": rel(REPORT_MD),
        },
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(summary, audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_CSV)
    parser.add_argument("--per-action", type=int, default=DEFAULT_PER_ACTION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> int:
    audit = run(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
