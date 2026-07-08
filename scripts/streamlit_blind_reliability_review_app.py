#!/usr/bin/env python3
"""Streamlit app for external blind reliability review."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = PROJECT_ROOT / "outputs/modeling-validation/blind-reliability-packet/blind_reliability_review_template.csv"
SOURCE_CSV = Path(os.environ.get("BLIND_RELIABILITY_SOURCE_CSV", DEFAULT_TEMPLATE))
REVIEWER_ID = os.environ.get("BLIND_RELIABILITY_REVIEWER_ID", "external_reviewer_1")
OUTPUT_DIR = Path(
    os.environ.get(
        "BLIND_RELIABILITY_OUTPUT_DIR",
        PROJECT_ROOT / "outputs/modeling-validation/blind-reliability-packet/external-reviews" / REVIEWER_ID,
    )
)
WORKING_CSV = OUTPUT_DIR / "blind_reliability_review_working.csv"

DECISIONS = ["", "yes", "no", "uncertain"]
REASONS = [
    "",
    "low_image_evidence",
    "motion_or_blur",
    "night_or_low_light",
    "subject_too_small",
    "partial_body",
    "occlusion",
    "non_comparable_viewpoint",
    "non_overlapping_body_region",
    "descriptor_evidence_conflict",
    "source_domain_stress",
    "wrong_species_or_non_target",
    "other",
]
BODY_REGIONS = [
    "",
    "full_body_or_most_body",
    "flank_or_pattern_region",
    "head_only",
    "rear_only",
    "legs_only",
    "not_visible_or_unclear",
]
CONFIDENCE = ["", "high", "medium", "low"]
AUDIT_COLUMNS = ["reviewed_at_utc"]


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
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
    frame["reviewer_id"] = REVIEWER_ID
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
    return frame["review_ready"].isin(["yes", "no", "uncertain"])


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "completed", "yes", "no", "uncertain"])
    source_packet = st.sidebar.selectbox("source packet", ["all", *sorted(v for v in out["source_packet"].unique() if v)])
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in {"yes", "no", "uncertain"}:
        out = out[out["review_ready"].eq(status)]
    if source_packet != "all":
        out = out[out["source_packet"].eq(source_packet)]
    return out


def next_pending_id(frame: pd.DataFrame, ordered_ids: list[str], current_id: str) -> str:
    pending_ids = set(frame.loc[~completed_mask(frame), "blind_pair_id"])
    pending = [row_id for row_id in ordered_ids if row_id in pending_ids]
    if not pending:
        return ""
    if current_id in pending:
        idx = pending.index(current_id)
        if idx + 1 < len(pending):
            return pending[idx + 1]
    return pending[0]


def save_row(
    frame: pd.DataFrame,
    blind_pair_id: str,
    review_ready: str,
    primary_reason: str,
    secondary_reason: str,
    body_region_visible: str,
    reviewer_confidence: str,
    reviewer_notes: str,
) -> None:
    row_index = frame.index[frame["blind_pair_id"].eq(blind_pair_id)][0]
    frame.at[row_index, "reviewer_id"] = REVIEWER_ID
    frame.at[row_index, "review_ready"] = review_ready
    frame.at[row_index, "primary_reason"] = primary_reason
    frame.at[row_index, "secondary_reason"] = secondary_reason
    frame.at[row_index, "body_region_visible"] = body_region_visible
    frame.at[row_index, "reviewer_confidence"] = reviewer_confidence
    frame.at[row_index, "reviewer_notes"] = reviewer_notes
    frame.at[row_index, "reviewed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)


def show_image(path_text: str, caption: str) -> None:
    path = resolve_path(path_text)
    if path.exists():
        st.image(str(path), caption=str(path), width="stretch")
    else:
        st.error(f"{caption} image missing: {path}")


def main() -> None:
    st.set_page_config(page_title="Blind Reliability Review", layout="wide")
    st.title("Blind Reliability Review")
    st.caption(f"Reviewer: {REVIEWER_ID}")
    st.markdown(
        "- Judge whether this pair is review-ready as pair-level evidence.\n"
        "- Do not infer identity for Bobcat or external rows.\n"
        "- Use only the displayed images; original labels and model features are hidden.\n"
        "- If not yes, choose the strongest primary reason."
    )

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    complete = completed_mask(data)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(data)}")
    st.sidebar.metric("yes", int(data["review_ready"].eq("yes").sum()))
    st.sidebar.metric("no", int(data["review_ready"].eq("no").sum()))
    st.sidebar.metric("uncertain", int(data["review_ready"].eq("uncertain").sum()))
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    row_ids = list(view["blind_pair_id"])
    state_key = "blind_reliability_selected_id"
    if state_key not in st.session_state or st.session_state[state_key] not in row_ids:
        st.session_state[state_key] = row_ids[0]
    selected_id = st.sidebar.selectbox(
        "blind_pair_id",
        row_ids,
        index=row_ids.index(st.session_state[state_key]),
        key=f"blind_select_{st.session_state[state_key]}",
    )
    st.session_state[state_key] = selected_id
    row_index = data.index[data["blind_pair_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()

    left, middle, right = st.columns([1.55, 1.55, 1.05])
    with left:
        st.subheader("Query")
        show_image(row["query_image_path"], "query")
    with middle:
        st.subheader("Candidate")
        show_image(row["candidate_image_path"], "candidate")
    with right:
        st.subheader(selected_id)
        st.write(f"source packet: `{row.get('source_packet', '')}`")
        current = row.get("review_ready", "")
        if current:
            st.success(f"Current: {current}")
        else:
            st.warning("Pending")
        review_ready = st.radio(
            "review_ready",
            DECISIONS,
            index=DECISIONS.index(current) if current in DECISIONS else 0,
        )
        primary = st.selectbox(
            "primary_reason",
            REASONS,
            index=REASONS.index(row.get("primary_reason", "")) if row.get("primary_reason", "") in REASONS else 0,
        )
        secondary = st.selectbox(
            "secondary_reason",
            REASONS,
            index=REASONS.index(row.get("secondary_reason", "")) if row.get("secondary_reason", "") in REASONS else 0,
        )
        body = st.selectbox(
            "body_region_visible",
            BODY_REGIONS,
            index=BODY_REGIONS.index(row.get("body_region_visible", ""))
            if row.get("body_region_visible", "") in BODY_REGIONS
            else 0,
        )
        confidence = st.selectbox(
            "reviewer_confidence",
            CONFIDENCE,
            index=CONFIDENCE.index(row.get("reviewer_confidence", ""))
            if row.get("reviewer_confidence", "") in CONFIDENCE
            else 0,
        )
        notes = st.text_area("reviewer_notes", value=row.get("reviewer_notes", ""), height=90)
        save_col, next_col = st.columns(2)
        with save_col:
            if st.button("Save row", type="primary", use_container_width=True):
                save_row(data, selected_id, review_ready, primary, secondary, body, confidence, notes)
                st.rerun()
        with next_col:
            if st.button("Next pending", use_container_width=True):
                next_id = next_pending_id(data, row_ids, selected_id)
                if next_id:
                    st.session_state[state_key] = next_id
                st.rerun()


if __name__ == "__main__":
    main()
