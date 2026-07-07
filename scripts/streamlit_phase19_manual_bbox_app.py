#!/usr/bin/env python3
"""Manual bbox annotation app for Phase19 Bobcat wild area measurement."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_wild_body_gate/bobcat_wild_blur_pass_body_gate_queue.csv"
)
SOURCE_CSV = Path(os.environ.get("PHASE19_BBOX_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(
    os.environ.get(
        "PHASE19_BBOX_OUTPUT_DIR",
        PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_manual_bbox",
    )
)
WORKING_CSV = OUTPUT_DIR / "phase19_bobcat_wild_manual_bbox_working.csv"

BBOX_COLUMNS = [
    "manual_bbox_status",
    "manual_bbox_x1",
    "manual_bbox_y1",
    "manual_bbox_x2",
    "manual_bbox_y2",
    "manual_bbox_area_fraction",
    "manual_bbox_notes",
    "manual_bbox_audited_at_utc",
]


def maybe_float(value: object) -> float | None:
    try:
        text = str(value).strip()
        if text in {"", "nan", "None"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def existing_area(row: pd.Series) -> float | None:
    for column in ["animal_area_fraction", "phase14_md_area_fraction"]:
        value = maybe_float(row.get(column, ""))
        if value is not None and value > 0:
            return value
    return None


def image_path_for(row: pd.Series) -> Path:
    path = Path(str(row.get("source_image_path", "")))
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_working_csv() -> None:
    if WORKING_CSV.exists():
        return
    if not SOURCE_CSV.exists():
        st.error(f"Source CSV not found: {SOURCE_CSV}")
        st.stop()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_CSV, WORKING_CSV)
    frame = pd.read_csv(WORKING_CSV, dtype=str, keep_default_na=False).fillna("")
    for column in BBOX_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame.to_csv(WORKING_CSV, index=False)


@st.cache_data(show_spinner=False)
def load_data(path_text: str) -> pd.DataFrame:
    frame = pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")
    for column in BBOX_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def save_data(frame: pd.DataFrame) -> None:
    frame.to_csv(WORKING_CSV, index=False)
    load_data.clear()


def manual_done_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["manual_bbox_status"].isin(["boxed", "no_box", "skip"])


def needs_manual_box(frame: pd.DataFrame) -> pd.Series:
    return frame.apply(existing_area, axis=1).isna()


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["needs_box", "pending", "boxed", "no_box", "skip", "all"])
    source = st.sidebar.selectbox("source", ["all", *sorted(v for v in out["source_dataset"].unique() if v)])
    if status == "needs_box":
        out = out[needs_manual_box(out) & ~manual_done_mask(out)]
    elif status == "pending":
        out = out[~manual_done_mask(out)]
    elif status in {"boxed", "no_box", "skip"}:
        out = out[out["manual_bbox_status"].eq(status)]
    if source != "all":
        out = out[out["source_dataset"].eq(source)]
    return out


def draw_existing_rect(row: pd.Series, scale: float) -> list[dict[str, object]]:
    x1 = maybe_float(row.get("manual_bbox_x1", ""))
    y1 = maybe_float(row.get("manual_bbox_y1", ""))
    x2 = maybe_float(row.get("manual_bbox_x2", ""))
    y2 = maybe_float(row.get("manual_bbox_y2", ""))
    if None in {x1, y1, x2, y2}:
        return []
    return [
        {
            "type": "rect",
            "version": "4.4.0",
            "originX": "left",
            "originY": "top",
            "left": float(x1 or 0) * scale,
            "top": float(y1 or 0) * scale,
            "width": max(1.0, (float(x2 or 0) - float(x1 or 0)) * scale),
            "height": max(1.0, (float(y2 or 0) - float(y1 or 0)) * scale),
            "fill": "rgba(255, 0, 0, 0.15)",
            "stroke": "#ff3333",
            "strokeWidth": 3,
        }
    ]


def latest_rectangle(canvas_json: dict[str, object] | None) -> dict[str, float] | None:
    if not canvas_json:
        return None
    objects = canvas_json.get("objects", [])
    if not isinstance(objects, list):
        return None
    rects = [obj for obj in objects if isinstance(obj, dict) and obj.get("type") == "rect"]
    if not rects:
        return None
    rect = rects[-1]
    left = float(rect.get("left", 0))
    top = float(rect.get("top", 0))
    width = float(rect.get("width", 0)) * float(rect.get("scaleX", 1))
    height = float(rect.get("height", 0)) * float(rect.get("scaleY", 1))
    if width <= 0 or height <= 0:
        return None
    return {"left": left, "top": top, "width": width, "height": height}


def save_box(frame: pd.DataFrame, review_id: str, rect: dict[str, float], scale: float, image: Image.Image, notes: str) -> None:
    row_index = frame.index[frame["phase19_review_id"].eq(review_id)][0]
    x1 = max(0.0, min(float(image.width), rect["left"] / scale))
    y1 = max(0.0, min(float(image.height), rect["top"] / scale))
    x2 = max(0.0, min(float(image.width), (rect["left"] + rect["width"]) / scale))
    y2 = max(0.0, min(float(image.height), (rect["top"] + rect["height"]) / scale))
    area = max(0.0, x2 - x1) * max(0.0, y2 - y1) / max(1.0, float(image.width * image.height))
    frame.at[row_index, "manual_bbox_status"] = "boxed"
    frame.at[row_index, "manual_bbox_x1"] = f"{x1:.2f}"
    frame.at[row_index, "manual_bbox_y1"] = f"{y1:.2f}"
    frame.at[row_index, "manual_bbox_x2"] = f"{x2:.2f}"
    frame.at[row_index, "manual_bbox_y2"] = f"{y2:.2f}"
    frame.at[row_index, "manual_bbox_area_fraction"] = f"{area:.8f}"
    frame.at[row_index, "manual_bbox_notes"] = notes
    frame.at[row_index, "manual_bbox_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)


def mark_status(frame: pd.DataFrame, review_id: str, status: str, notes: str) -> None:
    row_index = frame.index[frame["phase19_review_id"].eq(review_id)][0]
    frame.at[row_index, "manual_bbox_status"] = status
    frame.at[row_index, "manual_bbox_notes"] = notes
    frame.at[row_index, "manual_bbox_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)


def main() -> None:
    st.set_page_config(page_title="Phase19 Manual BBox", layout="wide")
    st.title("Phase19 Manual BBox")
    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    needs = needs_manual_box(data)
    done = manual_done_mask(data)
    st.sidebar.metric("source rows", len(data))
    st.sidebar.metric("missing area", int(needs.sum()))
    st.sidebar.metric("manual boxed", int(data["manual_bbox_status"].eq("boxed").sum()))
    st.sidebar.metric("manual pending", int((needs & ~done).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    review_ids = list(view["phase19_review_id"])
    jump_id = st.session_state.pop("phase19_bbox_jump_to_id", "")
    default_id = jump_id if jump_id in review_ids else review_ids[0]
    selected_id = st.sidebar.selectbox(
        "phase19_review_id",
        review_ids,
        index=review_ids.index(default_id),
        key="phase19_bbox_selectbox",
    )
    row_index = data.index[data["phase19_review_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()
    image_path = image_path_for(row)
    if not image_path.exists():
        st.error(f"Image missing: {image_path}")
        st.stop()

    with Image.open(image_path) as original:
        image = original.convert("RGB")
    max_width = st.sidebar.slider("display width", 700, 1400, 1100, 50)
    scale = min(1.0, max_width / max(1, image.width))
    canvas_width = int(round(image.width * scale))
    canvas_height = int(round(image.height * scale))
    display_image = image.resize((canvas_width, canvas_height))

    left, right = st.columns([3.2, 1.0])
    with left:
        st.subheader(selected_id)
        initial = {"version": "4.4.0", "objects": draw_existing_rect(row, scale)}
        canvas = st_canvas(
            fill_color="rgba(255, 0, 0, 0.15)",
            stroke_width=3,
            stroke_color="#ff3333",
            background_image=display_image,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="rect",
            initial_drawing=initial,
            key=f"bbox_canvas_{selected_id}",
        )
    with right:
        st.write(f"image: `{image.width} x {image.height}`")
        existing = existing_area(row)
        st.write(f"existing area: `{'' if existing is None else f'{existing:.4f}'}`")
        st.write(f"manual status: `{row.get('manual_bbox_status', '')}`")
        notes = st.text_area("notes", value=str(row.get("manual_bbox_notes", "")), height=100)
        rect = latest_rectangle(canvas.json_data)
        if rect:
            area = (rect["width"] / scale) * (rect["height"] / scale) / max(1, image.width * image.height)
            st.metric("drawn area", f"{area:.2%}")
        if st.button("Save box", type="primary", disabled=rect is None):
            if rect is not None:
                save_box(data, selected_id, rect, scale, image, notes)
                st.session_state["phase19_bbox_jump_to_id"] = selected_id
                st.rerun()
        if st.button("No usable box"):
            mark_status(data, selected_id, "no_box", notes)
            st.rerun()
        if st.button("Skip"):
            mark_status(data, selected_id, "skip", notes)
            st.rerun()

        pending_ids = list(view.loc[~manual_done_mask(view), "phase19_review_id"])
        if st.button("Next pending"):
            if pending_ids:
                current_pos = pending_ids.index(selected_id) if selected_id in pending_ids else -1
                st.session_state["phase19_bbox_jump_to_id"] = pending_ids[(current_pos + 1) % len(pending_ids)]
                st.rerun()


if __name__ == "__main__":
    main()
