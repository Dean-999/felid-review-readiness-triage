#!/usr/bin/env python3
"""Streamlit app for Phase18L descriptor-controlled pair reviewability labeling."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_ROOT = PROJECT_ROOT / "outputs/phase18/phase18l_descriptor_controlled_review_packet"
PACKET_ROOT = Path(os.environ.get("PHASE18L_PACKET_ROOT", DEFAULT_PACKET_ROOT))
OUTPUT_ROOT = Path(os.environ.get("PHASE18L_REVIEW_OUTPUT_ROOT", PROJECT_ROOT / "outputs/phase18/phase18l_streamlit_review"))
DEFAULT_REVIEWER_ID = os.environ.get("PHASE18L_REVIEWER_ID", "reviewer1")

DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
REVIEWERS = ["reviewer1", "reviewer2", "reviewer3"]
ADMISSIBILITY_GROUPS = ["all", "high_admissibility", "low_admissibility"]
DECISIONS = ["", "review_ready", "not_review_ready", "uncertain"]
NOT_READY_REASONS = [
    "",
    "low_evidence",
    "non_comparable",
    "both_low_evidence_and_non_comparable",
    "identity_uncertain_but_reviewable",
    "other",
]

WORKING_COLUMNS = [
    "review_pair_id",
    "query_image_path",
    "candidate_image_path",
    "reviewability_decision",
    "not_ready_reason",
    "secondary_reason",
    "visibility_notes",
    "reviewer_id",
    "review_timestamp",
    "descriptor_name",
]


def packet_paths(descriptor_name: str, reviewer_id: str) -> dict[str, Path]:
    packet_dir = PACKET_ROOT / descriptor_name
    working_dir = OUTPUT_ROOT / reviewer_id / descriptor_name
    return {
        "blind": packet_dir / "phase18l_blind_review_form.csv",
        "full": packet_dir / "phase18l_descriptor_controlled_review_packet.csv",
        "codebook": packet_dir / "phase18l_reviewability_codebook.csv",
        "working": working_dir / "phase18l_descriptor_controlled_review_working.csv",
        "analysis_ready": working_dir / "phase18l_descriptor_controlled_review_analysis_ready.csv",
    }


@st.cache_data(show_spinner=False)
def load_csv(path_text: str) -> pd.DataFrame:
    return pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")


def ensure_working_csv(descriptor_name: str, reviewer_id: str) -> Path:
    paths = packet_paths(descriptor_name, reviewer_id)
    if paths["working"].exists():
        return paths["working"]
    if not paths["blind"].exists():
        st.error(f"Blind review form not found: {paths['blind']}")
        st.stop()
    paths["working"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths["blind"], paths["working"])
    frame = pd.read_csv(paths["working"], dtype=str, keep_default_na=False).fillna("")
    frame["descriptor_name"] = descriptor_name
    frame["reviewer_id"] = reviewer_id
    for column in WORKING_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame[WORKING_COLUMNS].to_csv(paths["working"], index=False)
    return paths["working"]


def load_working(descriptor_name: str, reviewer_id: str) -> pd.DataFrame:
    working = ensure_working_csv(descriptor_name, reviewer_id)
    frame = load_csv(str(working))
    for column in WORKING_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def save_working(descriptor_name: str, reviewer_id: str, frame: pd.DataFrame) -> None:
    path = packet_paths(descriptor_name, reviewer_id)["working"]
    frame[WORKING_COLUMNS].to_csv(path, index=False)
    load_csv.clear()


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    valid_decision = frame["reviewability_decision"].isin(["review_ready", "not_review_ready", "uncertain"])
    reason_ok = ~frame["reviewability_decision"].eq("not_review_ready") | frame["not_ready_reason"].isin(NOT_READY_REASONS[1:])
    return valid_decision & reason_ok


def pending_count(descriptor_name: str, reviewer_id: str) -> int:
    working = packet_paths(descriptor_name, reviewer_id)["working"]
    blind = packet_paths(descriptor_name, reviewer_id)["blind"]
    if working.exists():
        frame = load_csv(str(working))
    elif blind.exists():
        frame = load_csv(str(blind))
    else:
        return 0
    return int((~completed_mask(frame)).sum()) if "reviewability_decision" in frame.columns else len(frame)


def default_descriptor_index(reviewer_id: str) -> int:
    for idx, descriptor_name in enumerate(DESCRIPTORS):
        if pending_count(descriptor_name, reviewer_id) > 0:
            return idx
    return 0


def descriptor_label(descriptor_name: str, admissibility_group: str) -> str:
    suffix = {
        "all": "all admissibility",
        "high_admissibility": "HIGH PF-ERI admissibility",
        "low_admissibility": "LOW PF-ERI admissibility",
    }[admissibility_group]
    return f"{descriptor_name} | {suffix}"


def option_index(options: list[str], value: object) -> int:
    text = str(value or "")
    return options.index(text) if text in options else 0


def resolve_image_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def filtered_frame(frame: pd.DataFrame, descriptor_name: str, reviewer_id: str, admissibility_group: str) -> pd.DataFrame:
    out = frame.copy()
    if admissibility_group != "all":
        full = load_csv(str(packet_paths(descriptor_name, reviewer_id)["full"]))
        keep_ids = set(full.loc[full["evidence_group"].eq(admissibility_group), "review_pair_id"])
        out = out[out["review_pair_id"].isin(keep_ids)]
    status = st.sidebar.selectbox("status", ["pending", "all", "completed", *DECISIONS[1:]])
    if status == "pending":
        out = out[~completed_mask(out)]
    elif status == "completed":
        out = out[completed_mask(out)]
    elif status in DECISIONS[1:]:
        out = out[out["reviewability_decision"].eq(status)]
    return out


def next_pending_id(frame: pd.DataFrame, current_id: str) -> str:
    pending = list(frame.loc[~completed_mask(frame), "review_pair_id"])
    if not pending:
        return ""
    if current_id in pending:
        idx = pending.index(current_id)
        if idx + 1 < len(pending):
            return str(pending[idx + 1])
    return str(pending[0])


def save_row(
    descriptor_name: str,
    reviewer_id: str,
    frame: pd.DataFrame,
    review_pair_id: str,
    decision: str,
    reason: str,
    secondary_reason: str,
    notes: str,
) -> tuple[bool, str]:
    if decision == "not_review_ready" and reason == "":
        return False, "Choose not_ready_reason before saving a not_review_ready pair."
    row_index = frame.index[frame["review_pair_id"].eq(review_pair_id)][0]
    frame.at[row_index, "reviewability_decision"] = decision
    frame.at[row_index, "not_ready_reason"] = reason if decision == "not_review_ready" else ""
    frame.at[row_index, "secondary_reason"] = secondary_reason
    frame.at[row_index, "visibility_notes"] = notes
    frame.at[row_index, "reviewer_id"] = reviewer_id
    frame.at[row_index, "review_timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds") if decision else ""
    save_working(descriptor_name, reviewer_id, frame)
    return True, next_pending_id(frame, review_pair_id)


def export_analysis_ready(descriptor_name: str, reviewer_id: str, working: pd.DataFrame) -> Path:
    paths = packet_paths(descriptor_name, reviewer_id)
    full = load_csv(str(paths["full"]))
    context_cols = [
        "review_pair_id",
        "sample_scope",
        "match_group_id",
        "evidence_group",
        "same_identity_known_id",
        "candidate_rank_descriptor",
        "rank_bin",
        "descriptor_similarity",
        "descriptor_similarity_percentile",
        "similarity_match_delta",
        "descriptor_evidence_conflict_score",
        "pf_eri_admissibility_score",
        "pf_eri_review_score",
        "pf_eri_route",
        "weakest_image_quality_score",
        "pair_geometry_score",
        "query_image_id",
        "candidate_image_id",
    ]
    merged = working.merge(full[context_cols], on="review_pair_id", how="left")
    paths["analysis_ready"].parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(paths["analysis_ready"], index=False)
    return paths["analysis_ready"]


def evidence_group_label(descriptor_name: str, reviewer_id: str, review_pair_id: str) -> str:
    full = load_csv(str(packet_paths(descriptor_name, reviewer_id)["full"]))
    matches = full[full["review_pair_id"].eq(review_pair_id)]
    if matches.empty:
        return ""
    value = str(matches.iloc[0].get("evidence_group", ""))
    if value == "high_admissibility":
        return "HIGH PF-ERI admissibility"
    if value == "low_admissibility":
        return "LOW PF-ERI admissibility"
    return value


def main() -> None:
    st.set_page_config(page_title="Phase18L Descriptor-Controlled Review", layout="wide")

    reviewer_index = REVIEWERS.index(DEFAULT_REVIEWER_ID) if DEFAULT_REVIEWER_ID in REVIEWERS else 0
    reviewer_id = st.sidebar.selectbox("reviewer_id", REVIEWERS, index=reviewer_index)
    descriptor_options = [(descriptor, group) for descriptor in DESCRIPTORS for group in ADMISSIBILITY_GROUPS]
    default_descriptor = DESCRIPTORS[default_descriptor_index(reviewer_id)]
    default_index = descriptor_options.index((default_descriptor, "all"))
    descriptor_group = st.sidebar.selectbox(
        "descriptor / admissibility group",
        descriptor_options,
        index=default_index,
        format_func=lambda value: descriptor_label(value[0], value[1]),
    )
    descriptor_name, admissibility_group = descriptor_group
    working = load_working(descriptor_name, reviewer_id)
    complete = completed_mask(working)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(working)}")
    st.sidebar.metric("pending", int((~complete).sum()))
    for decision in DECISIONS[1:]:
        st.sidebar.metric(decision, int(working["reviewability_decision"].eq(decision).sum()))
    st.sidebar.caption(f"working CSV: {packet_paths(descriptor_name, reviewer_id)['working']}")

    view = filtered_frame(working, descriptor_name, reviewer_id, admissibility_group)
    if view.empty:
        st.info("No pairs match the current filters. Switch status to `all` or choose another descriptor.")
        st.stop()

    pair_ids = list(view["review_pair_id"])
    query_pair = st.query_params.get("review_pair_id", "")
    state_key = f"phase18l_current_pair_id_{reviewer_id}_{descriptor_name}"
    if state_key not in st.session_state or st.session_state[state_key] not in pair_ids:
        st.session_state[state_key] = query_pair if query_pair in pair_ids else pair_ids[0]
    selected_id = st.sidebar.selectbox(
        "review_pair_id",
        pair_ids,
        index=pair_ids.index(st.session_state[state_key]),
        key=f"phase18l_pair_select_{reviewer_id}_{descriptor_name}_{st.session_state[state_key]}",
    )
    st.session_state[state_key] = selected_id
    st.query_params["review_pair_id"] = selected_id

    row = working.loc[working.index[working["review_pair_id"].eq(selected_id)][0]].copy()
    group_label = evidence_group_label(descriptor_name, reviewer_id, selected_id)

    img_a, img_b = st.columns(2)
    with img_a:
        query_path = resolve_image_path(row["query_image_path"])
        st.image(str(query_path), width="stretch")
    with img_b:
        candidate_path = resolve_image_path(row["candidate_image_path"])
        st.image(str(candidate_path), width="stretch")

    decision = st.radio(
        "reviewability_decision",
        DECISIONS,
        index=option_index(DECISIONS, row.get("reviewability_decision", "")),
        horizontal=True,
    )
    reason_col, secondary_col = st.columns(2)
    with reason_col:
        reason = st.selectbox(
            "not_ready_reason",
            NOT_READY_REASONS,
            index=option_index(NOT_READY_REASONS, row.get("not_ready_reason", "")),
            disabled=decision != "not_review_ready",
        )
    with secondary_col:
        secondary_reason = st.selectbox(
            "secondary_reason",
            NOT_READY_REASONS,
            index=option_index(NOT_READY_REASONS, row.get("secondary_reason", "")),
        )
    notes = st.text_area("visibility_notes", value=row.get("visibility_notes", ""), height=80)
    save_col, skip_col, export_col = st.columns(3)
    with save_col:
        if st.button("Save and next", type="primary", use_container_width=True):
            ok, next_id = save_row(descriptor_name, reviewer_id, working, selected_id, decision, reason, secondary_reason, notes)
            if not ok:
                st.error(next_id)
            else:
                if next_id:
                    st.session_state[state_key] = next_id
                    st.query_params["review_pair_id"] = next_id
                st.rerun()
    with skip_col:
        if st.button("Skip", use_container_width=True):
            next_id = next_pending_id(working, selected_id)
            if next_id:
                st.session_state[state_key] = next_id
                st.query_params["review_pair_id"] = next_id
            st.rerun()
    with export_col:
        if st.button("Export", use_container_width=True):
            export_analysis_ready(descriptor_name, reviewer_id, working)


if __name__ == "__main__":
    main()
