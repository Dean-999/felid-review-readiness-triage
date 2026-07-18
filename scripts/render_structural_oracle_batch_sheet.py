"""Render a compact, opaque-asset contact sheet for structural annotation."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from scripts import structural_oracle_annotation_core as core


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package"
RESPONSES = ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_responses"


def tile(path: Path, label: str, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail((width, height - 26), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "white")
    x = (width - image.width) // 2
    y = 26 + (height - 26 - image.height) // 2
    canvas.paste(image, (x, y))
    ImageDraw.Draw(canvas).text((8, 6), label, fill="black")
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packets = core.load_packet(PACKAGE)
    responses = core.load_responses(RESPONSES, "annotator_b", set(packets.annotation_packet_id))
    pending = packets[~packets.annotation_packet_id.isin(set(responses.annotation_packet_id))].head(args.count)
    width, height = 440, 330
    sheet = Image.new("RGB", (width * 2, height * len(pending)), "#d9d9d9")
    for index, row in enumerate(pending.itertuples(index=False), start=1):
        left = tile(core.resolve_asset(PACKAGE, row.left_asset_token), f"{index}A", width, height)
        right = tile(core.resolve_asset(PACKAGE, row.right_asset_token), f"{index}B", width, height)
        sheet.paste(left, (0, (index - 1) * height))
        sheet.paste(right, (width, (index - 1) * height))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)


if __name__ == "__main__":
    main()
