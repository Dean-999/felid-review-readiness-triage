#!/usr/bin/env python3
"""Streamlit app for Phase19 strict photo review."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_strict_photo_prefilter/phase19_strict_photo_review_queue.csv"
)
SOURCE_CSV = Path(os.environ.get("PHASE19_PHOTO_REVIEW_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(
    os.environ.get(
        "PHASE19_PHOTO_REVIEW_OUTPUT_DIR",
        PROJECT_ROOT / "outputs/phase19/phase19_strict_photo_review",
    )
)
WORKING_CSV = OUTPUT_DIR / "phase19_strict_photo_review_working.csv"

AUDIT_COLUMNS = [
    "phase19_manual_decision",
    "phase19_manual_reject_reason",
    "phase19_manual_notes",
    "phase19_manual_audited_at_utc",
]

DECISIONS = ["", "clear", "reject", "defer"]
REJECT_REASONS = [
    "",
    "motion_blur_or_soft_animal",
    "mosaic_or_compression",
    "subject_too_small_lt_20pct",
    "subject_20_30pct_but_not_clear_enough",
    "partial_body_or_occlusion",
    "insufficient_body_or_marking_evidence",
    "track_scat_dead_sign_label",
    "wrong_species_or_no_felid",
    "duplicate_or_near_duplicate",
    "license_or_provenance_problem",
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
    return frame["phase19_manual_decision"].isin(["clear", "reject", "defer"])


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "clear", "reject", "defer", "completed"])
    pool = st.sidebar.selectbox("pool", ["all", *sorted(v for v in out["phase19_cell"].unique() if v)])
    priority = "all"
    tier = "all"
    object_decision = "all"
    if "phase19_manual_review_priority" in out.columns:
        priority = st.sidebar.selectbox(
            "priority",
            ["high+cautious", "all", *sorted(v for v in out["phase19_manual_review_priority"].unique() if v)],
        )
    if "phase19_prefilter_tier" in out.columns:
        tier = st.sidebar.selectbox("tier", ["all", *sorted(v for v in out["phase19_prefilter_tier"].unique() if v)])
    if "object_aware_decision" in out.columns:
        object_values = sorted(v for v in out["object_aware_decision"].unique() if v)
        object_decision = st.sidebar.selectbox(
            "object-aware",
            ["all", *object_values],
        )

    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in {"clear", "reject", "defer"}:
        out = out[out["phase19_manual_decision"].eq(status)]
    if pool != "all":
        out = out[out["phase19_cell"].eq(pool)]
    if object_decision != "all":
        out = out[out["object_aware_decision"].eq(object_decision)]
    if priority == "high+cautious" and "phase19_manual_review_priority" in out.columns:
        out = out[out["phase19_manual_review_priority"].isin(["high", "cautious"])]
    elif priority != "all" and "phase19_manual_review_priority" in out.columns:
        out = out[out["phase19_manual_review_priority"].eq(priority)]
    if tier != "all" and "phase19_prefilter_tier" in out.columns:
        out = out[out["phase19_prefilter_tier"].eq(tier)]
    return out


def next_pending_id(frame: pd.DataFrame, ordered_ids: list[str], current_id: str) -> str:
    pending = [row_id for row_id in ordered_ids if row_id in set(frame.loc[~completed_mask(frame), "phase19_review_id"])]
    if not pending:
        return ""
    if current_id in pending:
        index = pending.index(current_id)
        if index + 1 < len(pending):
            return pending[index + 1]
    return pending[0]


def write_decision(frame: pd.DataFrame, review_id: str, decision: str, reject_reason: str, notes: str) -> None:
    row_index = frame.index[frame["phase19_review_id"].eq(review_id)][0]
    frame.at[row_index, "phase19_manual_decision"] = decision
    frame.at[row_index, "phase19_manual_reject_reason"] = reject_reason if decision == "reject" else ""
    frame.at[row_index, "phase19_manual_notes"] = notes
    frame.at[row_index, "phase19_manual_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)


def image_path_for(row: pd.Series) -> Path:
    path_text = str(row.get("source_image_path", ""))
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def maybe_float(value: object) -> float | None:
    try:
        if value in {"", None}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def show_image_with_optional_crop(image_path: Path, row: pd.Series) -> None:
    if not image_path.exists():
        st.error(f"Image missing: {image_path}")
        return
    bbox_values = [maybe_float(row.get(col, "")) for col in ["animal_bbox_x1", "animal_bbox_y1", "animal_bbox_x2", "animal_bbox_y2"]]
    if all(value is not None for value in bbox_values):
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            x1, y1, x2, y2 = [int(round(value or 0)) for value in bbox_values]
            x1 = max(0, min(image.width, x1))
            x2 = max(0, min(image.width, x2))
            y1 = max(0, min(image.height, y1))
            y2 = max(0, min(image.height, y2))
            crop = image.crop((x1, y1, x2, y2)) if x2 > x1 and y2 > y1 else None
            original_col, crop_col = st.columns([1.3, 1.0])
            with original_col:
                st.image(str(image_path), caption=str(image_path), width="stretch")
            with crop_col:
                if crop is not None:
                    st.image(crop, caption="animal crop used for object-aware clarity", width="stretch")
                else:
                    st.warning("Invalid animal crop box.")
    else:
        st.image(str(image_path), caption=str(image_path), width="stretch")


def main() -> None:
    st.set_page_config(page_title="Phase19 Strict Photo Review", layout="wide")
    st.title("Phase19 Strict Photo Review")

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    complete = completed_mask(data)

    st.sidebar.header("Progress")
    st.sidebar.metric("clear", int(data["phase19_manual_decision"].eq("clear").sum()))
    st.sidebar.metric("reject", int(data["phase19_manual_decision"].eq("reject").sum()))
    st.sidebar.metric("defer", int(data["phase19_manual_decision"].eq("defer").sum()))
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    review_ids = list(view["phase19_review_id"])
    jump_id = st.session_state.pop("phase19_jump_to_id", "")
    default_id = jump_id if jump_id in review_ids else review_ids[0]
    selected_id = st.sidebar.selectbox(
        "phase19_review_id",
        review_ids,
        index=review_ids.index(default_id),
        key="phase19_review_selectbox",
    )

    row_index = data.index[data["phase19_review_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()
    image_path = image_path_for(row)

    left, right = st.columns([3.2, 1.3])
    with left:
        st.subheader(selected_id)
        show_image_with_optional_crop(image_path, row)
        if row.get("source_image_uri", ""):
            st.link_button("Open source image URL", row.get("source_image_uri", ""))

    with right:
        current = row.get("phase19_manual_decision", "")
        if current == "clear":
            st.success("Current: CLEAR")
        elif current == "reject":
            st.error(f"Current: REJECT / {row.get('phase19_manual_reject_reason', '')}")
        elif current == "defer":
            st.warning("Current: DEFER")
        else:
            st.info("Pending")

        with st.expander("Details", expanded=False):
            st.write(f"pool: `{row.get('phase19_cell', '')}`")
            if row.get("bobcat_wild_rescue_tier", "") != "":
                st.write(f"rescue tier: `{row.get('bobcat_wild_rescue_tier', '')}`")
                st.write(f"rescue score: `{row.get('bobcat_wild_rescue_score', '')}`")
            if row.get("phase19_prefilter_tier", "") != "":
                st.write(f"tier: `{row.get('phase19_prefilter_tier', '')}`")
                st.write(f"score: `{row.get('phase19_strict_photo_score', '')}`")
                st.write(f"area rule: `{row.get('subject_area_rule', '')}`")
                st.write(f"technical: `{row.get('technical_quality_rule', '')}`")
            if row.get("animal_area_fraction", "") != "":
                st.write(f"class: `{row.get('yolo_class', '')}` conf: `{row.get('yolo_confidence', '')}`")
                st.write(f"area: `{row.get('animal_area_fraction', '')}`")
                st.write(f"crop sharpness: `{row.get('animal_crop_laplacian_var', '')}`")
                st.write(f"crop edges: `{row.get('animal_crop_gradient_p90', '')}`")
            st.write(f"size: `{row.get('image_width', '')} x {row.get('image_height', '')}`")

        decision = st.radio(
            "decision",
            DECISIONS,
            index=DECISIONS.index(current) if current in DECISIONS else 0,
            horizontal=True,
        )
        existing_reason = str(row.get("phase19_manual_reject_reason", ""))
        reject_reason = st.selectbox(
            "reject reason",
            REJECT_REASONS,
            index=REJECT_REASONS.index(existing_reason) if existing_reason in REJECT_REASONS else 0,
        )
        notes = st.text_area("notes", value=str(row.get("phase19_manual_notes", "")), height=80)

        save_col, next_col = st.columns(2)
        with save_col:
            if st.button("Save and next", type="primary", use_container_width=True):
                if decision == "":
                    st.warning("Choose clear, reject, or defer before saving.")
                else:
                    write_decision(data, selected_id, decision, reject_reason, notes)
                    updated = load_data(str(WORKING_CSV))
                    next_id = next_pending_id(updated, review_ids, selected_id)
                    if next_id:
                        st.session_state.phase19_jump_to_id = next_id
                    st.rerun()
        with next_col:
            if st.button("Skip", use_container_width=True):
                next_id = next_pending_id(data, review_ids, selected_id)
                if next_id:
                    st.session_state.phase19_jump_to_id = next_id
                st.rerun()


if __name__ == "__main__":
    main()
