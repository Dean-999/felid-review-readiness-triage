#!/usr/bin/env python3
"""Streamlit app for the Phase17K Bobcat clarity-first gate."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    PROJECT_ROOT / "outputs/phase17/phase17k_bobcat_clarity_gate/phase17k_bobcat_clarity_gate_pool.csv"
)
SOURCE_CSV = Path(os.environ.get("PHASE17K_CLARITY_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(
    os.environ.get("PHASE17K_CLARITY_OUTPUT_DIR", PROJECT_ROOT / "outputs/phase17/phase17k_bobcat_clarity_review")
)
WORKING_CSV = OUTPUT_DIR / "phase17k_bobcat_clarity_gate_working.csv"

AUDIT_COLUMNS = [
    "phase17k_clarity_gate_decision",
    "phase17k_clarity_reject_reason",
    "phase17k_clarity_notes",
    "phase17k_clarity_audited_at_utc",
]

REJECT_REASONS = [
    "",
    "tiny_or_far_subject",
    "blur_or_motion_smear",
    "low_resolution_or_compression",
    "severe_occlusion",
    "bad_angle_non_comparable",
    "dead_sign_or_non_living_evidence",
    "not_bobcat_visible",
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
    return frame["phase17k_clarity_gate_decision"].isin(["clear", "not_clear"])


def next_pending_candidate(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "candidate_id"])
    if not pending:
        return ""
    if current_id in pending:
        current_index = pending.index(current_id)
        if current_index + 1 < len(pending):
            return str(pending[current_index + 1])
    return str(pending[0])


def save_decision(frame: pd.DataFrame, candidate_id: str, decision: str, reject_reason: str, notes: str) -> str:
    row_index = frame.index[frame["candidate_id"].eq(candidate_id)][0]
    frame.at[row_index, "phase17k_clarity_gate_decision"] = decision
    frame.at[row_index, "phase17k_clarity_reject_reason"] = reject_reason if decision == "not_clear" else ""
    frame.at[row_index, "phase17k_clarity_notes"] = notes
    frame.at[row_index, "phase17k_clarity_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)
    return next_pending_candidate(frame, candidate_id)


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "clear", "not_clear", "completed"])
    prior = st.sidebar.selectbox("prior human label", ["all", "seeded_yes", "unlabeled"])
    license_filter = st.sidebar.selectbox("license", ["all", *sorted(v for v in out["photo_license_code"].unique() if v)])
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in {"clear", "not_clear"}:
        out = out[out["phase17k_clarity_gate_decision"].eq(status)]
    if prior == "seeded_yes":
        out = out[out.get("phase17k_prior_human_quality_label", "").eq("yes")]
    elif prior == "unlabeled":
        out = out[~out.get("phase17k_prior_human_quality_label", "").eq("yes")]
    if license_filter != "all":
        out = out[out["photo_license_code"].eq(license_filter)]
    return out


def main() -> None:
    st.set_page_config(page_title="Phase17K Bobcat Clarity Gate", layout="wide")
    st.title("Phase17K Bobcat Clarity Gate")
    st.caption("CLEAR = algorithm eligible. NOT CLEAR = cannot enter Bobcat 3000.")

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    complete = completed_mask(data)
    clear_count = int(data["phase17k_clarity_gate_decision"].eq("clear").sum())
    not_clear_count = int(data["phase17k_clarity_gate_decision"].eq("not_clear").sum())

    st.sidebar.header("Progress")
    st.sidebar.metric("clear", clear_count)
    st.sidebar.metric("not clear", not_clear_count)
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.metric("target clear", f"{clear_count} / 3000")
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    candidate_ids = list(view["candidate_id"])
    query_candidate = st.query_params.get("candidate_id", "")
    if "phase17k_current_id" not in st.session_state:
        st.session_state.phase17k_current_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]
    if st.session_state.phase17k_current_id not in candidate_ids:
        st.session_state.phase17k_current_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]

    selected_id = st.sidebar.selectbox(
        "candidate_id",
        candidate_ids,
        index=candidate_ids.index(st.session_state.phase17k_current_id),
        key="phase17k_candidate_selectbox",
    )
    st.session_state.phase17k_current_id = selected_id
    st.query_params["candidate_id"] = selected_id

    row_index = data.index[data["candidate_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()
    existing_reason = str(row.get("phase17k_clarity_reject_reason", ""))
    existing_notes = str(row.get("phase17k_clarity_notes", ""))

    left, right = st.columns([3.2, 1.25])
    with left:
        st.subheader(selected_id)
        st.image(row["image_uri"], caption=row["image_uri"], width="stretch")
        st.link_button("Open full image", row.get("image_uri", ""))
        st.link_button("Open iNaturalist observation", row.get("observation_uri", ""))

    with right:
        current = row.get("phase17k_clarity_gate_decision", "")
        if current == "clear":
            st.success("Current: CLEAR")
        elif current == "not_clear":
            st.error("Current: NOT CLEAR")
        else:
            st.warning("Pending")

        st.markdown("### Standard")
        st.markdown("- CLEAR only if the bobcat is sharp, visible, and visually comparable.")
        st.markdown("- Reject tiny/far subjects, blur, motion smear, severe occlusion, dead/sign-only evidence.")
        st.markdown("- When unsure, choose NOT CLEAR.")

        st.markdown("### Source")
        st.write(f"license: `{row.get('photo_license_code', '') or 'none'}`")
        st.write(f"observed: `{row.get('observed_on', '')}`")
        st.write(f"place: `{row.get('place_guess', '')}`")
        st.write(f"prior: `{row.get('phase17k_prior_human_quality_label', '') or 'none'}`")

        reject_reason = st.selectbox(
            "NOT CLEAR reason",
            REJECT_REASONS,
            index=REJECT_REASONS.index(existing_reason) if existing_reason in REJECT_REASONS else 0,
        )
        notes = st.text_area("notes", value=existing_notes, height=80)

        clear_col, reject_col = st.columns(2)
        with clear_col:
            if st.button("CLEAR", type="primary", use_container_width=True):
                next_id = save_decision(data, selected_id, "clear", "", notes)
                if next_id:
                    st.session_state.phase17k_current_id = next_id
                    st.query_params["candidate_id"] = next_id
                st.rerun()
        with reject_col:
            if st.button("NOT CLEAR", use_container_width=True):
                next_id = save_decision(data, selected_id, "not_clear", reject_reason, notes)
                if next_id:
                    st.session_state.phase17k_current_id = next_id
                    st.query_params["candidate_id"] = next_id
                st.rerun()

        if st.button("Skip to next pending", use_container_width=True):
            next_id = next_pending_candidate(data, selected_id)
            if next_id:
                st.session_state.phase17k_current_id = next_id
                st.query_params["candidate_id"] = next_id
                st.rerun()


if __name__ == "__main__":
    main()
