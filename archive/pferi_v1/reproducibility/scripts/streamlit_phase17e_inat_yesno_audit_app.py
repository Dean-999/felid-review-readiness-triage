#!/usr/bin/env python3
"""Streamlit yes/no audit app for Phase17E iNaturalist Bobcat candidates."""

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
    / "outputs/phase17/phase17e_external_source_probe/prototype_phase17e_inat_research_grade_bobcat_top3000.csv"
)
SOURCE_CSV = Path(os.environ.get("PHASE17E_YESNO_SOURCE_CSV", DEFAULT_SOURCE_CSV))
OUTPUT_DIR = Path(os.environ.get("PHASE17E_YESNO_OUTPUT_DIR", PROJECT_ROOT / "outputs/phase17/phase17e_inat_yesno_audit"))
WORKING_CSV = OUTPUT_DIR / "phase17e_inat_bobcat_yesno_working.csv"

AUDIT_COLUMNS = [
    "human_quality_yes_no",
    "human_reject_reason",
    "human_audit_notes",
    "human_audited_at_utc",
]

REJECT_REASONS = [
    "",
    "animal_trace_or_sign",
    "scat_or_footprint",
    "dead_organism",
    "not_bobcat_visible",
    "low_quality_or_occluded",
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
    return frame["human_quality_yes_no"].isin(["yes", "no"])


def set_query_row(candidate_id: str) -> None:
    st.query_params["candidate_id"] = candidate_id


def next_pending_candidate(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "candidate_id"])
    if not pending:
        return ""
    if current_id in pending:
        idx = pending.index(current_id)
        if idx + 1 < len(pending):
            return str(pending[idx + 1])
    return str(pending[0])


def save_decision(frame: pd.DataFrame, candidate_id: str, decision: str, reject_reason: str, notes: str) -> str:
    idx = frame.index[frame["candidate_id"].eq(candidate_id)][0]
    frame.at[idx, "human_quality_yes_no"] = decision
    frame.at[idx, "human_reject_reason"] = reject_reason if decision == "no" else ""
    frame.at[idx, "human_audit_notes"] = notes
    frame.at[idx, "human_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(frame)
    return next_pending_candidate(frame, candidate_id)


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "yes", "no", "complete"])
    license_filter = st.sidebar.selectbox(
        "license",
        ["all", *sorted(v for v in out["photo_license_code"].unique() if v)],
    )
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "complete":
        out = out[completed_mask(out)]
    elif status in {"yes", "no"}:
        out = out[out["human_quality_yes_no"].eq(status)]
    if license_filter != "all":
        out = out[out["photo_license_code"].eq(license_filter)]
    return out


def main() -> None:
    st.set_page_config(page_title="Phase17E iNat Bobcat YES/NO", layout="wide")
    st.title("Phase17E iNat Bobcat YES/NO")
    st.caption("YES = good enough to keep for high-quality Bobcat algorithm-entry review. NO = reject.")

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    complete = completed_mask(data)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(data)}")
    st.sidebar.metric("yes", int(data["human_quality_yes_no"].eq("yes").sum()))
    st.sidebar.metric("no", int(data["human_quality_yes_no"].eq("no").sum()))
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    candidate_ids = list(view["candidate_id"])
    query_candidate = st.query_params.get("candidate_id", "")
    if "inat_nav_candidate_id" not in st.session_state:
        st.session_state.inat_nav_candidate_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]
    if st.session_state.inat_nav_candidate_id not in candidate_ids:
        st.session_state.inat_nav_candidate_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]

    selected_id = st.sidebar.selectbox(
        "candidate_id",
        candidate_ids,
        index=candidate_ids.index(st.session_state.inat_nav_candidate_id),
        key=f"inat_candidate_select_{st.session_state.inat_nav_candidate_id}",
    )
    st.session_state.inat_nav_candidate_id = selected_id
    set_query_row(selected_id)

    row_idx = data.index[data["candidate_id"].eq(selected_id)][0]
    row = data.loc[row_idx].copy()
    existing_notes = str(row.get("human_audit_notes", ""))
    existing_reject_reason = str(row.get("human_reject_reason", ""))

    left, right = st.columns([3, 1.35])
    with left:
        st.subheader(selected_id)
        st.image(row["image_uri"], caption=row["image_uri"], width="stretch")
        st.link_button("Open iNaturalist observation", row.get("observation_uri", ""))
        st.link_button("Open image", row.get("image_uri", ""))

    with right:
        current = row.get("human_quality_yes_no", "")
        if current == "yes":
            st.success("Current decision: YES")
        elif current == "no":
            st.error("Current decision: NO")
        else:
            st.warning("Pending")

        st.markdown("### Source")
        st.write(f"license: `{row.get('photo_license_code', '') or 'none'}`")
        st.write(f"observed: `{row.get('observed_on', '')}`")
        st.write(f"place: `{row.get('place_guess', '')}`")
        st.write(f"score: `{row.get('phase17e_source_score', '')}`")

        reject_reason = st.selectbox(
            "NO reason optional",
            REJECT_REASONS,
            index=REJECT_REASONS.index(existing_reject_reason) if existing_reject_reason in REJECT_REASONS else 0,
        )
        notes = st.text_area("notes optional", value=existing_notes, height=80)
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button("YES", type="primary", use_container_width=True):
                next_id = save_decision(data, selected_id, "yes", "", notes)
                if next_id:
                    st.session_state.inat_nav_candidate_id = next_id
                    set_query_row(next_id)
                st.rerun()
        with no_col:
            if st.button("NO", use_container_width=True):
                next_id = save_decision(data, selected_id, "no", reject_reason, notes)
                if next_id:
                    st.session_state.inat_nav_candidate_id = next_id
                    set_query_row(next_id)
                st.rerun()

        if st.button("Skip to next pending", use_container_width=True):
            next_id = next_pending_candidate(data, selected_id)
            if next_id:
                st.session_state.inat_nav_candidate_id = next_id
                set_query_row(next_id)
                st.rerun()


if __name__ == "__main__":
    main()
