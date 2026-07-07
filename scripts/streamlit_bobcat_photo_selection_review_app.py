#!/usr/bin/env python3
"""Streamlit review app for unified Bobcat photo selection."""

from __future__ import annotations

import io
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = PROJECT_ROOT / "outputs/bobcat_photo_selection/bobcat_photo_selection_subject40_review_queue.csv"
SOURCE_CSV = Path(os.environ.get("BOBCAT_PHOTO_SELECTION_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(os.environ.get("BOBCAT_PHOTO_SELECTION_OUTPUT_DIR", PROJECT_ROOT / "outputs/bobcat_photo_selection"))
WORKING_CSV = OUTPUT_DIR / "bobcat_photo_selection_review_working.csv"

AUDIT_COLUMNS = [
    "human_subject40_clear_decision",
    "human_reject_reason",
    "human_review_notes",
    "human_reviewed_at_utc",
]

REJECT_REASONS = [
    "",
    "animal_under_40_percent",
    "blur_or_motion",
    "mosaic_or_compression",
    "low_contrast",
    "bad_angle_non_comparable",
    "occlusion",
    "not_bobcat_or_not_visible",
    "dead_sign_scat_track",
    "duplicate",
    "other",
]


def ensure_working_csv() -> None:
    if WORKING_CSV.exists():
        return
    if not SOURCE_CSV.exists():
        st.error(f"Source CSV not found: {SOURCE_CSV}")
        st.stop()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_CSV, WORKING_CSV)
    frame = pd.read_csv(WORKING_CSV, dtype=str, keep_default_na=False).fillna("")
    for column in AUDIT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame.to_csv(WORKING_CSV, index=False)


@st.cache_data(show_spinner=False)
def load_data(path_text: str) -> pd.DataFrame:
    frame = pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")
    for column in AUDIT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def save_data(frame: pd.DataFrame) -> None:
    frame.to_csv(WORKING_CSV, index=False)
    load_data.clear()


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["human_subject40_clear_decision"].isin(["clear", "not_clear"])


def next_pending_candidate(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "candidate_id"])
    if not pending:
        return ""
    if current_id in pending:
        index = pending.index(current_id)
        if index + 1 < len(pending):
            return str(pending[index + 1])
    return str(pending[0])


def save_decision(frame: pd.DataFrame, candidate_id: str, decision: str, reason: str, notes: str) -> str:
    row_index = frame.index[frame["candidate_id"].eq(candidate_id)][0]
    frame.at[row_index, "human_subject40_clear_decision"] = decision
    frame.at[row_index, "human_reject_reason"] = reason if decision == "not_clear" else ""
    frame.at[row_index, "human_review_notes"] = notes
    frame.at[row_index, "human_reviewed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)
    return next_pending_candidate(frame, candidate_id)


def safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@st.cache_data(show_spinner=False, max_entries=128)
def crop_preview(image_uri: str, x1: float, y1: float, x2: float, y2: float) -> Image.Image | None:
    response = requests.get(image_uri, timeout=(4, 8), headers={"User-Agent": "bobcat-photo-selection-review/0.1"})
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    width, height = image.size
    if x2 <= x1 or y2 <= y1:
        return None
    pad_x = (x2 - x1) * 0.25
    pad_y = (y2 - y1) * 0.25
    box = (
        max(0, int(x1 - pad_x)),
        max(0, int(y1 - pad_y)),
        min(width, int(x2 + pad_x)),
        min(height, int(y2 + pad_y)),
    )
    return image.crop(box)


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "clear", "not_clear", "completed"])
    detected_class = st.sidebar.selectbox("detected class", ["all", *sorted(v for v in out["detected_class"].unique() if v)])
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in {"clear", "not_clear"}:
        out = out[out["human_subject40_clear_decision"].eq(status)]
    if detected_class != "all":
        out = out[out["detected_class"].eq(detected_class)]
    return out


def main() -> None:
    st.set_page_config(page_title="Bobcat Photo Selection", layout="wide")
    st.title("Bobcat Photo Selection")
    st.caption("CLEAR only if the animal is large enough for comparison, sharp, non-mosaic, complete enough, and comparable.")

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    complete = completed_mask(data)
    st.sidebar.header("Progress")
    st.sidebar.metric("clear", int(data["human_subject40_clear_decision"].eq("clear").sum()))
    st.sidebar.metric("not clear", int(data["human_subject40_clear_decision"].eq("not_clear").sum()))
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    candidate_ids = list(view["candidate_id"])
    query_candidate = st.query_params.get("candidate_id", "")
    if "bobcat_photo_selection_current_id" not in st.session_state:
        st.session_state.bobcat_photo_selection_current_id = (
            query_candidate if query_candidate in candidate_ids else candidate_ids[0]
        )
    if st.session_state.bobcat_photo_selection_current_id not in candidate_ids:
        st.session_state.bobcat_photo_selection_current_id = (
            query_candidate if query_candidate in candidate_ids else candidate_ids[0]
        )

    selected_id = st.sidebar.selectbox(
        "candidate_id",
        candidate_ids,
        index=candidate_ids.index(st.session_state.bobcat_photo_selection_current_id),
        key="bobcat_photo_selection_candidate_select",
    )
    st.session_state.bobcat_photo_selection_current_id = selected_id
    st.query_params["candidate_id"] = selected_id

    row = data.loc[data.index[data["candidate_id"].eq(selected_id)][0]].copy()
    left, right = st.columns([3.3, 1.25])
    with left:
        st.subheader(selected_id)
        st.image(row["image_uri"], caption=row["image_uri"], width="stretch")
        x1 = safe_float(row.get("subject_bbox_x1", ""))
        y1 = safe_float(row.get("subject_bbox_y1", ""))
        x2 = safe_float(row.get("subject_bbox_x2", ""))
        y2 = safe_float(row.get("subject_bbox_y2", ""))
        if x2 > x1 and y2 > y1:
            try:
                crop = crop_preview(row["image_uri"], x1, y1, x2, y2)
                if crop is not None:
                    st.image(crop, caption="animal crop preview", width="stretch")
            except Exception as error:
                st.caption(f"crop preview unavailable: {type(error).__name__}")
        st.link_button("Open full image", row["image_uri"])
        if row.get("source_uri", ""):
            st.link_button("Open source record", row["source_uri"])

    with right:
        decision = row.get("human_subject40_clear_decision", "")
        if decision == "clear":
            st.success("Current: CLEAR")
        elif decision == "not_clear":
            st.error("Current: NOT CLEAR")
        else:
            st.warning("Pending")

        st.markdown("### Gate")
        st.write(f"class: `{row.get('detected_class', '')}`")
        st.write(f"confidence: `{row.get('detected_confidence', '')}`")
        st.write(f"area: `{row.get('subject_area_fraction', '')}`")
        st.write(f"width: `{row.get('subject_width_fraction', '')}`")
        st.write(f"height: `{row.get('subject_height_fraction', '')}`")
        st.write(f"sharpness: `{row.get('laplacian_var', '')}`")

        existing_reason = row.get("human_reject_reason", "")
        reason = st.selectbox(
            "NOT CLEAR reason",
            REJECT_REASONS,
            index=REJECT_REASONS.index(existing_reason) if existing_reason in REJECT_REASONS else 0,
        )
        notes = st.text_area("notes", value=row.get("human_review_notes", ""), height=80)
        clear_col, reject_col = st.columns(2)
        with clear_col:
            if st.button("CLEAR", type="primary", use_container_width=True):
                next_id = save_decision(data, selected_id, "clear", "", notes)
                if next_id:
                    st.session_state.bobcat_photo_selection_current_id = next_id
                    st.query_params["candidate_id"] = next_id
                st.rerun()
        with reject_col:
            if st.button("NOT CLEAR", use_container_width=True):
                next_id = save_decision(data, selected_id, "not_clear", reason, notes)
                if next_id:
                    st.session_state.bobcat_photo_selection_current_id = next_id
                    st.query_params["candidate_id"] = next_id
                st.rerun()


if __name__ == "__main__":
    main()
