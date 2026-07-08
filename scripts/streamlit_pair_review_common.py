#!/usr/bin/env python3
"""Shared Streamlit pair-review app helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PairReviewConfig:
    title: str
    source_csv: Path
    working_csv: Path
    id_column: str
    query_image_column: str
    candidate_image_column: str
    status_column: str
    decision_columns: tuple[str, ...]
    decision_options: tuple[str, ...]
    reason_column: str
    secondary_reason_column: str
    notes_column: str
    standards: tuple[str, ...]
    reason_options: tuple[str, ...]
    metadata_columns: tuple[str, ...]
    default_filter_columns: tuple[str, ...] = ()


def resolve_path(path_text: str) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_working_csv(config: PairReviewConfig) -> None:
    if config.working_csv.exists():
        return
    if not config.source_csv.exists():
        st.error(f"Source CSV not found: {config.source_csv}")
        st.stop()
    config.working_csv.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config.source_csv, config.working_csv)
    frame = pd.read_csv(config.working_csv, dtype=str, keep_default_na=False).fillna("")
    for column in [config.status_column, *config.decision_columns]:
        if column not in frame.columns:
            frame[column] = ""
    frame.to_csv(config.working_csv, index=False)


@st.cache_data(show_spinner=False)
def load_data(path_text: str, required_columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")
    for column in required_columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def save_data(config: PairReviewConfig, frame: pd.DataFrame) -> None:
    frame.to_csv(config.working_csv, index=False)
    load_data.clear()


def completed_mask(config: PairReviewConfig, frame: pd.DataFrame) -> pd.Series:
    return frame[config.status_column].isin([option for option in config.decision_options if option])


def next_pending_id(config: PairReviewConfig, frame: pd.DataFrame, ordered_ids: list[str], current_id: str) -> str:
    pending_ids = set(frame.loc[~completed_mask(config, frame), config.id_column])
    pending = [row_id for row_id in ordered_ids if row_id in pending_ids]
    if not pending:
        return ""
    if current_id in pending:
        index = pending.index(current_id)
        if index + 1 < len(pending):
            return pending[index + 1]
    return pending[0]


def filtered_frame(config: PairReviewConfig, frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status_values = ["pending", "all", "completed", *[option for option in config.decision_options if option]]
    status = st.sidebar.selectbox("status", status_values)
    if status == "pending":
        out = out[~completed_mask(config, out)]
    elif status == "completed":
        out = out[completed_mask(config, out)]
    elif status not in {"all"}:
        out = out[out[config.status_column].eq(status)]

    for column in config.default_filter_columns:
        if column not in out.columns:
            continue
        values = sorted(v for v in out[column].unique() if v)
        if not values:
            continue
        selected = st.sidebar.selectbox(column, ["all", *values])
        if selected != "all":
            out = out[out[column].eq(selected)]
    return out


def save_row(
    config: PairReviewConfig,
    frame: pd.DataFrame,
    row_id: str,
    decision: str,
    reason: str,
    secondary_reason: str,
    notes: str,
    body_region: str = "",
) -> None:
    row_index = frame.index[frame[config.id_column].eq(row_id)][0]
    frame.at[row_index, config.status_column] = decision
    if config.reason_column:
        frame.at[row_index, config.reason_column] = reason
    if config.secondary_reason_column:
        frame.at[row_index, config.secondary_reason_column] = secondary_reason
    if config.notes_column:
        frame.at[row_index, config.notes_column] = notes
    if "target_body_region_visible" in frame.columns:
        frame.at[row_index, "target_body_region_visible"] = body_region
    audited_col = f"{config.status_column}_audited_at_utc"
    if audited_col not in frame.columns:
        frame[audited_col] = ""
    frame.at[row_index, audited_col] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(config, frame)


def show_image(path_text: str, label: str) -> None:
    path = resolve_path(path_text)
    if path.exists():
        st.image(str(path), caption=str(path), width="stretch")
    else:
        st.error(f"{label} image missing: {path}")


def progress_sidebar(config: PairReviewConfig, frame: pd.DataFrame) -> None:
    complete = completed_mask(config, frame)
    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(frame)}")
    for option in [option for option in config.decision_options if option]:
        st.sidebar.metric(option, int(frame[config.status_column].eq(option).sum()))
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {config.working_csv}")


def show_standards(config: PairReviewConfig) -> None:
    st.markdown("### Standards")
    for item in config.standards:
        st.markdown(f"- {item}")


def run_pair_review_app(config: PairReviewConfig) -> None:
    st.set_page_config(page_title=config.title, layout="wide")
    st.title(config.title)

    ensure_working_csv(config)
    required = (config.status_column, *config.decision_columns)
    data = load_data(str(config.working_csv), required)
    progress_sidebar(config, data)
    view = filtered_frame(config, data)
    if view.empty:
        st.info("No rows match the current filters.")
        st.stop()

    row_ids = list(view[config.id_column])
    state_key = f"{config.id_column}_selected_nav"
    if state_key not in st.session_state or st.session_state[state_key] not in row_ids:
        st.session_state[state_key] = row_ids[0]

    selected_id = st.sidebar.selectbox(
        config.id_column,
        row_ids,
        index=row_ids.index(st.session_state[state_key]),
        key=f"{config.id_column}_select_{st.session_state[state_key]}",
    )
    st.session_state[state_key] = selected_id

    row_index = data.index[data[config.id_column].eq(selected_id)][0]
    row = data.loc[row_index].copy()

    image_left, image_right, form_col = st.columns([1.55, 1.55, 1.1])
    with image_left:
        st.subheader("Query")
        show_image(str(row.get(config.query_image_column, "")), "query")
    with image_right:
        st.subheader("Candidate")
        show_image(str(row.get(config.candidate_image_column, "")), "candidate")
    with form_col:
        st.subheader(selected_id)
        current = str(row.get(config.status_column, ""))
        if current:
            st.success(f"Current: {current}")
        else:
            st.warning("Pending")

        show_standards(config)

        with st.expander("Row details", expanded=False):
            for column in config.metadata_columns:
                if column in row.index:
                    st.write(f"{column}: `{row.get(column, '')}`")

        decision = st.radio(
            "decision",
            config.decision_options,
            index=config.decision_options.index(current) if current in config.decision_options else 0,
        )
        reason = ""
        secondary_reason = ""
        body_region = str(row.get("target_body_region_visible", ""))
        if config.reason_column:
            existing_reason = str(row.get(config.reason_column, ""))
            reason = st.selectbox(
                "primary reason",
                config.reason_options,
                index=config.reason_options.index(existing_reason) if existing_reason in config.reason_options else 0,
            )
        if config.secondary_reason_column:
            existing_secondary = str(row.get(config.secondary_reason_column, ""))
            secondary_reason = st.selectbox(
                "secondary reason",
                config.reason_options,
                index=config.reason_options.index(existing_secondary)
                if existing_secondary in config.reason_options
                else 0,
            )
        if "target_body_region_visible" in data.columns:
            body_options = ("", "full_body_or_most_body", "flank_or_pattern_region", "head_only", "rear_only", "legs_only", "not_visible_or_unclear")
            body_region = st.selectbox(
                "body region visible",
                body_options,
                index=body_options.index(body_region) if body_region in body_options else 0,
            )
        notes = st.text_area("notes", value=str(row.get(config.notes_column, "")), height=90)

        save_col, next_col = st.columns(2)
        with save_col:
            if st.button("Save row", type="primary", use_container_width=True):
                save_row(config, data, selected_id, decision, reason, secondary_reason, notes, body_region)
                st.rerun()
        with next_col:
            if st.button("Next pending", use_container_width=True):
                next_id = next_pending_id(config, data, row_ids, selected_id)
                if next_id:
                    st.session_state[state_key] = next_id
                st.rerun()
