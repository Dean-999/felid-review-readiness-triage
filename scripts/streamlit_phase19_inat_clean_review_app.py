#!/usr/bin/env python3
"""Minimal review app for Phase19 iNaturalist clean Bobcat queue."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_daylight_clean_queue/phase19_bobcat_inat_daylight_nonblur_review_queue.csv"
)
SOURCE_CSV = Path(os.environ.get("PHASE19_INAT_REVIEW_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(
    os.environ.get(
        "PHASE19_INAT_REVIEW_OUTPUT_DIR",
        PROJECT_ROOT / "outputs/phase19/phase19_bobcat_inat_daylight_clean_review",
    )
)
WORKING_CSV = OUTPUT_DIR / "phase19_bobcat_inat_daylight_clean_review_working.csv"

AUDIT_COLUMNS = [
    "phase19_manual_decision",
    "phase19_manual_reject_reason",
    "phase19_manual_notes",
    "phase19_manual_audited_at_utc",
]

REJECT_REASONS = [
    "",
    "blur_or_motion_smear",
    "tiny_or_far_subject",
    "partial_body_or_occlusion",
    "low_resolution_or_compression",
    "low_contrast_or_night_like",
    "not_bobcat_visible",
    "dead_sign_track_scat_or_nonliving",
    "captive_or_zoo_not_target",
    "duplicate_or_near_duplicate",
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
    tier = st.sidebar.selectbox(
        "tier",
        ["all", *sorted(v for v in out["phase19_daylight_nonblur_tier"].unique() if v)],
    )
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in {"clear", "reject", "defer"}:
        out = out[out["phase19_manual_decision"].eq(status)]
    if tier != "all":
        out = out[out["phase19_daylight_nonblur_tier"].eq(tier)]
    return out


def next_pending_id(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "phase19_review_id"])
    if not pending:
        return ""
    if current_id in pending:
        index = pending.index(current_id)
        if index + 1 < len(pending):
            return str(pending[index + 1])
    return str(pending[0])


def save_decision(frame: pd.DataFrame, review_id: str, decision: str, reject_reason: str, notes: str) -> str:
    row_index = frame.index[frame["phase19_review_id"].eq(review_id)][0]
    frame.at[row_index, "phase19_manual_decision"] = decision
    frame.at[row_index, "phase19_manual_reject_reason"] = reject_reason if decision == "reject" else ""
    frame.at[row_index, "phase19_manual_notes"] = notes
    frame.at[row_index, "phase19_manual_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)
    return next_pending_id(frame, review_id)


def main() -> None:
    st.set_page_config(page_title="Phase19 iNat Bobcat Review", layout="wide")
    st.title("Phase19 iNat Bobcat Review")
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
    query_id = st.query_params.get("review_id", "")
    if "phase19_inat_current_id" not in st.session_state:
        st.session_state.phase19_inat_current_id = query_id if query_id in review_ids else review_ids[0]
    if st.session_state.phase19_inat_current_id not in review_ids:
        st.session_state.phase19_inat_current_id = query_id if query_id in review_ids else review_ids[0]

    selected_id = st.sidebar.selectbox(
        "phase19_review_id",
        review_ids,
        index=review_ids.index(st.session_state.phase19_inat_current_id),
        key="phase19_inat_selectbox",
    )
    st.session_state.phase19_inat_current_id = selected_id
    st.query_params["review_id"] = selected_id
    row = data.loc[data["phase19_review_id"].eq(selected_id)].iloc[0].copy()

    left, right = st.columns([3.5, 1.1])
    with left:
        st.subheader(selected_id)
        st.image(row["source_image_uri"], width="stretch")
        link_cols = st.columns(2)
        with link_cols[0]:
            st.link_button("Open image", row.get("source_image_uri", ""))
        with link_cols[1]:
            if row.get("source_record_uri", ""):
                st.link_button("Open record", row.get("source_record_uri", ""))

    with right:
        current = row.get("phase19_manual_decision", "")
        if current == "clear":
            st.success("CLEAR")
        elif current == "reject":
            st.error("REJECT")
        elif current == "defer":
            st.warning("DEFER")
        else:
            st.info("Pending")

        with st.expander("Details", expanded=False):
            for key in [
                "phase19_daylight_nonblur_tier",
                "phase19_daylight_nonblur_score",
                "phase19_daylight_nonblur_reasons",
                "phase19_area10_gate_decision",
                "phase19_area10_area_fraction",
                "phase19_area10_area_bin",
                "phase19_area10_confidence",
                "phase19_area10_bbox_width_fraction",
                "phase19_area10_bbox_height_fraction",
                "phase17m_seed_tier",
                "phase17m_seed_score",
                "phase17m_seed_reject_reasons",
                "image_width",
                "image_height",
                "colorfulness_proxy",
                "dark_clip_fraction",
                "contrast_std",
                "gradient_p90",
                "laplacian_var",
                "place_guess",
                "license",
            ]:
                st.write(f"{key}: `{row.get(key, '')}`")

        reject_reason = st.selectbox(
            "reject reason",
            REJECT_REASONS,
            index=REJECT_REASONS.index(row.get("phase19_manual_reject_reason", ""))
            if row.get("phase19_manual_reject_reason", "") in REJECT_REASONS
            else 0,
        )
        notes = st.text_area("notes", value=row.get("phase19_manual_notes", ""), height=80)

        clear_col, reject_col = st.columns(2)
        with clear_col:
            if st.button("CLEAR", type="primary", use_container_width=True):
                next_id = save_decision(data, selected_id, "clear", "", notes)
                if next_id:
                    st.session_state.phase19_inat_current_id = next_id
                    st.query_params["review_id"] = next_id
                st.rerun()
        with reject_col:
            if st.button("REJECT", use_container_width=True):
                next_id = save_decision(data, selected_id, "reject", reject_reason, notes)
                if next_id:
                    st.session_state.phase19_inat_current_id = next_id
                    st.query_params["review_id"] = next_id
                st.rerun()
        if st.button("DEFER", use_container_width=True):
            next_id = save_decision(data, selected_id, "defer", "", notes)
            if next_id:
                st.session_state.phase19_inat_current_id = next_id
                st.query_params["review_id"] = next_id
            st.rerun()
        if st.button("Next pending", use_container_width=True):
            next_id = next_pending_id(data, selected_id)
            if next_id:
                st.session_state.phase19_inat_current_id = next_id
                st.query_params["review_id"] = next_id
            st.rerun()


if __name__ == "__main__":
    main()
