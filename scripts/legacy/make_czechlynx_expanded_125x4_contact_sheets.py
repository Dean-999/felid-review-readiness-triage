#!/usr/bin/env python3
"""Build blinded contact sheets for the expanded CzechLynx 125x4 review."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLINDED_CSV = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "czechlynx"
    / "czechlynx_expanded_125x4_triage_blinded.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "expanded_125x4_contact_sheets"

EXPECTED_ROWS = 500
IMAGES_PER_SHEET = 25
GRID_COLS = 5
GRID_ROWS = 5
THUMB_SIZE = 180
LABEL_HEIGHT = 28
PADDING = 16
TITLE_HEIGHT = 40


def resolve_image_path(image_path: str) -> Path:
    path = Path(image_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_thumbnail(image_path: Path, size: int) -> Image.Image:
    with Image.open(image_path) as img:
        thumb = img.convert("RGB")
        thumb.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (size, size), "white")
        offset = ((size - thumb.width) // 2, (size - thumb.height) // 2)
        canvas.paste(thumb, offset)
        return canvas


def build_contact_sheet(
    rows: pd.DataFrame,
    sheet_number: int,
    title_font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
) -> Image.Image:
    cell_width = THUMB_SIZE + PADDING
    cell_height = THUMB_SIZE + LABEL_HEIGHT + PADDING
    width = GRID_COLS * cell_width + PADDING
    height = GRID_ROWS * cell_height + PADDING + TITLE_HEIGHT

    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (PADDING, 8),
        f"CzechLynx expanded 125x4 contact sheet {sheet_number:02d}",
        fill="black",
        font=title_font,
    )

    for index, row in enumerate(rows.itertuples(index=False)):
        col = index % GRID_COLS
        row_idx = index // GRID_COLS
        x0 = PADDING + col * cell_width
        y0 = TITLE_HEIGHT + PADDING + row_idx * cell_height

        image_path = resolve_image_path(row.image_path)
        thumb = make_thumbnail(image_path, THUMB_SIZE)
        sheet.paste(thumb, (x0, y0))

        label_y = y0 + THUMB_SIZE + 4
        draw.text((x0, label_y), str(row.expanded_image_id), fill="black", font=label_font)

    return sheet


def main() -> int:
    if not BLINDED_CSV.exists():
        print(f"FAIL: blinded CSV not found: {BLINDED_CSV}")
        return 1

    df = pd.read_csv(BLINDED_CSV, dtype=str, keep_default_na=False)
    required_columns = {"expanded_image_id", "image_path"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        print("FAIL: missing required column(s): " + ", ".join(missing_columns))
        return 1

    df = df.sort_values("expanded_image_id").reset_index(drop=True)
    if len(df) != EXPECTED_ROWS:
        print(f"FAIL: expected {EXPECTED_ROWS} expanded rows, found {len(df)}")
        return 1

    expected_sheets = EXPECTED_ROWS // IMAGES_PER_SHEET
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    title_font = load_font(18)
    label_font = load_font(14)

    written: list[Path] = []
    for sheet_idx in range(expected_sheets):
        start = sheet_idx * IMAGES_PER_SHEET
        end = start + IMAGES_PER_SHEET
        batch = df.iloc[start:end]
        sheet = build_contact_sheet(batch, sheet_idx + 1, title_font, label_font)
        output_path = (
            OUTPUT_DIR
            / f"czechlynx_expanded_125x4_contact_sheet_{sheet_idx + 1:02d}.jpg"
        )
        sheet.save(output_path, quality=90)
        written.append(output_path)

    print(f"Read {len(df)} expanded rows from: {BLINDED_CSV}")
    print(f"Wrote {len(written)} contact sheets to: {OUTPUT_DIR}")
    for path in written:
        print(f"  {path.name}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
