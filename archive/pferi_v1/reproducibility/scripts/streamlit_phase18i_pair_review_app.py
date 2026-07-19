#!/usr/bin/env python3
"""Streamlit app for Phase18I targeted pair reviewability audit."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_ROOT = PROJECT_ROOT / "outputs/phase18/phase18i_targeted_review_packet"
PACKET_ROOT = Path(os.environ.get("PHASE18I_PACKET_ROOT", DEFAULT_PACKET_ROOT))
OUTPUT_DIR = Path(os.environ.get("PHASE18I_REVIEW_OUTPUT_DIR", PROJECT_ROOT / "outputs/phase18/phase18i_streamlit_review"))

DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
REVIEWABILITY_LABELS = ["", "review_ready", "low_evidence", "non_comparable", "uncertain"]

WORKING_COLUMNS = [
    "review_pair_id",
    "query_image_path",
    "candidate_image_path",
    "reviewability_label",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
    "descriptor_name",
]


def packet_paths(descriptor_name: str) -> dict[str, Path]:
    descriptor_dir = PACKET_ROOT / descriptor_name
    return {
        "blind": descriptor_dir / "phase18i_blind_review_form.csv",
        "full": descriptor_dir / "phase18i_targeted_pair_review_packet.csv",
        "contact_sheet": descriptor_dir / "phase18i_contact_sheet.jpg",
        "html": descriptor_dir / "phase18i_review_packet.html",
        "codebook": descriptor_dir / "phase18i_reviewability_codebook.csv",
        "working": OUTPUT_DIR / descriptor_name / "phase18i_pair_review_working.csv",
    }


def ensure_working_csv(descriptor_name: str) -> Path:
    paths = packet_paths(descriptor_name)
    working = paths["working"]
    if working.exists():
        return working
    if not paths["blind"].exists():
        st.error(f"Blind review form not found: {paths['blind']}")
        st.stop()
    working.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths["blind"], working)
    frame = pd.read_csv(working, dtype=str, keep_default_na=False).fillna("")
    frame["descriptor_name"] = descriptor_name
    for column in WORKING_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame[WORKING_COLUMNS].to_csv(working, index=False)
    return working


@st.cache_data(show_spinner=False)
def load_csv(path_text: str) -> pd.DataFrame:
    return pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")


def load_working(descriptor_name: str) -> pd.DataFrame:
    path = ensure_working_csv(descriptor_name)
    frame = load_csv(str(path))
    for column in WORKING_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def save_working(descriptor_name: str, frame: pd.DataFrame) -> None:
    path = packet_paths(descriptor_name)["working"]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame[WORKING_COLUMNS].to_csv(path, index=False)
    load_csv.clear()


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["reviewability_label"].isin(REVIEWABILITY_LABELS[1:])


def option_index(options: list[str], current: object) -> int:
    value = str(current or "")
    return options.index(value) if value in options else 0


def resolve_image_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_full_packet(descriptor_name: str) -> pd.DataFrame:
    full_path = packet_paths(descriptor_name)["full"]
    if not full_path.exists():
        return pd.DataFrame()
    return load_csv(str(full_path))


def merged_analysis_view(descriptor_name: str, working: pd.DataFrame) -> pd.DataFrame:
    full = load_full_packet(descriptor_name)
    if full.empty:
        return working.copy()
    hidden_columns = [
        "review_pair_id",
        "sample_group",
        "same_identity_known_id",
        "candidate_rank_descriptor",
        "descriptor_similarity",
        "descriptor_similarity_percentile",
        "descriptor_evidence_conflict_score",
        "pf_eri_admissibility_score",
        "pf_eri_review_score",
        "pf_eri_route",
        "weakest_image_quality_score",
        "pair_geometry_score",
    ]
    return working.merge(full[hidden_columns], on="review_pair_id", how="left")


def next_pending_id(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "review_pair_id"])
    if not pending:
        return ""
    if current_id in pending:
        current_index = pending.index(current_id)
        if current_index + 1 < len(pending):
            return str(pending[current_index + 1])
    return str(pending[0])


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status = st.sidebar.selectbox("status", ["pending", "all", "completed", *REVIEWABILITY_LABELS[1:]])
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in REVIEWABILITY_LABELS[1:]:
        out = out[out["reviewability_label"].eq(status)]
    return out


def save_row(
    descriptor_name: str,
    frame: pd.DataFrame,
    review_pair_id: str,
    label: str,
    notes: str,
    reviewer_id: str,
) -> str:
    row_index = frame.index[frame["review_pair_id"].eq(review_pair_id)][0]
    frame.at[row_index, "reviewability_label"] = label
    frame.at[row_index, "visibility_notes"] = notes
    frame.at[row_index, "reviewer_id"] = reviewer_id
    frame.at[row_index, "review_timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds") if label else ""
    save_working(descriptor_name, frame)
    return next_pending_id(frame, review_pair_id)


def export_summary(descriptor_name: str, working: pd.DataFrame) -> Path:
    export_path = OUTPUT_DIR / descriptor_name / "phase18i_pair_review_analysis_ready.csv"
    merged = merged_analysis_view(descriptor_name, working)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(export_path, index=False)
    return export_path


def show_codebook(descriptor_name: str) -> None:
    codebook = packet_paths(descriptor_name)["codebook"]
    if codebook.exists():
        st.sidebar.dataframe(load_csv(str(codebook)), width="stretch", hide_index=True)


def pending_count_for_descriptor(descriptor_name: str) -> int:
    working = packet_paths(descriptor_name)["working"]
    if not working.exists():
        blind = packet_paths(descriptor_name)["blind"]
        if not blind.exists():
            return 0
        frame = load_csv(str(blind))
    else:
        frame = load_csv(str(working))
    if "reviewability_label" not in frame.columns:
        return len(frame)
    return int((~frame["reviewability_label"].isin(REVIEWABILITY_LABELS[1:])).sum())


def default_descriptor_index() -> int:
    for idx, descriptor_name in enumerate(DESCRIPTORS):
        if pending_count_for_descriptor(descriptor_name) > 0:
            return idx
    return 0


def main() -> None:
    st.set_page_config(page_title="Phase18I Pair Review", layout="wide")
    st.title("Phase18I Pair Reviewability")
    st.caption("Review pair evidence only. Do not assign identity labels in this app.")

    descriptor_name = st.sidebar.selectbox("descriptor", DESCRIPTORS, index=default_descriptor_index())
    working = load_working(descriptor_name)
    complete = completed_mask(working)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(working)}")
    st.sidebar.metric("pending", int((~complete).sum()))
    for label in REVIEWABILITY_LABELS[1:]:
        st.sidebar.metric(label, int(working["reviewability_label"].eq(label).sum()))
    st.sidebar.caption(f"working CSV: {packet_paths(descriptor_name)['working']}")
    show_codebook(descriptor_name)

    view = filtered_frame(working)
    if view.empty:
        st.info("No pairs match the current filters. If this descriptor is complete, switch status to `all` or choose another descriptor.")
        st.stop()

    pair_ids = list(view["review_pair_id"])
    query_pair = st.query_params.get("review_pair_id", "")
    if "phase18i_current_pair_id" not in st.session_state:
        st.session_state.phase18i_current_pair_id = query_pair if query_pair in pair_ids else pair_ids[0]
    if st.session_state.phase18i_current_pair_id not in pair_ids:
        st.session_state.phase18i_current_pair_id = query_pair if query_pair in pair_ids else pair_ids[0]

    selected_id = st.sidebar.selectbox(
        "review_pair_id",
        pair_ids,
        index=pair_ids.index(st.session_state.phase18i_current_pair_id),
        key=f"phase18i_pair_select_{descriptor_name}_{st.session_state.phase18i_current_pair_id}",
    )
    st.session_state.phase18i_current_pair_id = selected_id
    st.query_params["review_pair_id"] = selected_id

    row_index = working.index[working["review_pair_id"].eq(selected_id)][0]
    row = working.loc[row_index].copy()
    full = load_full_packet(descriptor_name)
    full_row = pd.Series(dtype=str)
    if not full.empty and selected_id in set(full["review_pair_id"]):
        full_row = full.loc[full["review_pair_id"].eq(selected_id)].iloc[0]

    left, right = st.columns([3.2, 1.2])
    with left:
        st.subheader(selected_id)
        query_path = resolve_image_path(row["query_image_path"])
        candidate_path = resolve_image_path(row["candidate_image_path"])
        img_a, img_b = st.columns(2)
        with img_a:
            st.image(str(query_path), caption=f"query: {row['query_image_path']}", width="stretch")
            st.link_button("Open query image", str(query_path))
        with img_b:
            st.image(str(candidate_path), caption=f"candidate: {row['candidate_image_path']}", width="stretch")
            st.link_button("Open candidate image", str(candidate_path))

        with st.expander("Pair context for later analysis", expanded=False):
            if full_row.empty:
                st.info("Full packet context not available.")
            else:
                context_cols = [
                    "sample_group",
                    "candidate_rank_descriptor",
                    "descriptor_similarity_percentile",
                    "descriptor_evidence_conflict_score",
                    "pf_eri_admissibility_score",
                    "pf_eri_review_score",
                    "pf_eri_route",
                    "weakest_image_quality_score",
                    "pair_geometry_score",
                ]
                shown = {col: full_row.get(col, "") for col in context_cols}
                st.dataframe(pd.DataFrame(shown.items(), columns=["field", "value"]), width="stretch", hide_index=True)
                st.caption("Known same/different truth remains hidden during review and is only used after labels are exported.")

    with right:
        current = row.get("reviewability_label", "")
        if current:
            st.success(f"Current: {current}")
        else:
            st.warning("Pending")

        st.markdown("### Label Standard")
        st.markdown("- `review_ready`: enough comparable evidence in both images.")
        st.markdown("- `low_evidence`: image quality, occlusion, distance, or visibility is too weak.")
        st.markdown("- `non_comparable`: body region, view, pose, or scale cannot be compared.")
        st.markdown("- `uncertain`: use sparingly when the distinction is unclear.")

        reviewer_id = st.text_input("reviewer_id", value=row.get("reviewer_id", "") or "dshen")
        label = st.radio(
            "reviewability_label",
            REVIEWABILITY_LABELS,
            index=option_index(REVIEWABILITY_LABELS, row.get("reviewability_label", "")),
        )
        notes = st.text_area("visibility_notes", value=row.get("visibility_notes", ""), height=100)

        save_col, skip_col = st.columns(2)
        with save_col:
            if st.button("Save and next", type="primary", use_container_width=True):
                next_id = save_row(descriptor_name, working, selected_id, label, notes, reviewer_id)
                if next_id:
                    st.session_state.phase18i_current_pair_id = next_id
                    st.query_params["review_pair_id"] = next_id
                st.rerun()
        with skip_col:
            if st.button("Skip", use_container_width=True):
                next_id = next_pending_id(working, selected_id)
                if next_id:
                    st.session_state.phase18i_current_pair_id = next_id
                    st.query_params["review_pair_id"] = next_id
                st.rerun()

        if st.button("Export analysis-ready CSV", use_container_width=True):
            export_path = export_summary(descriptor_name, working)
            st.success(f"Wrote {export_path}")

        contact_sheet = packet_paths(descriptor_name)["contact_sheet"]
        if contact_sheet.exists():
            st.link_button("Open contact sheet", str(contact_sheet))


if __name__ == "__main__":
    main()
