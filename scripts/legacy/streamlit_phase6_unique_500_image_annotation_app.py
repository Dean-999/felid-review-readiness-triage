#!/usr/bin/env python3
"""Streamlit app for Phase 6 unique-500 image annotation review."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

import sys

sys.path.insert(0, str(SCRIPT_DIR))
from phase6_unique_500_annotation_schema import (  # noqa: E402
    EXPECTED_ROWS,
    STREAMLIT_ALLOWED_VALUES,
    WORKING_CSV,
)

st.set_page_config(page_title="Phase 6 Unique 500 Annotation", layout="wide")
st.title("Phase 6 Unique 500 Image Annotation")

if not WORKING_CSV.exists():
    st.error(f"Working CSV not found: {WORKING_CSV.relative_to(PROJECT_ROOT)}")
    st.stop()

data = pd.read_csv(WORKING_CSV, dtype=str, keep_default_na=False).fillna("")

RANGE_PRESETS = [
    (0, 49),
    (50, 99),
    (100, 149),
    (150, 199),
    (200, 249),
    (250, 299),
    (300, 349),
    (350, 399),
    (400, 449),
    (450, 499),
]

st.sidebar.header("Review range")
preset_labels = [f"{start}–{end}" for start, end in RANGE_PRESETS]
selected_preset = st.sidebar.selectbox("50-image preset", preset_labels, index=0)
preset_index = preset_labels.index(selected_preset)
default_start, default_end = RANGE_PRESETS[preset_index]

start_index = st.sidebar.number_input("start_index", min_value=0, max_value=EXPECTED_ROWS - 1, value=default_start)
end_index = st.sidebar.number_input("end_index", min_value=0, max_value=EXPECTED_ROWS - 1, value=default_end)
if end_index < start_index:
    st.sidebar.warning("end_index is less than start_index; swapping for display.")
    start_index, end_index = end_index, start_index

status_filter = st.sidebar.selectbox("Status filter", ["all", "pending", "needs_review", "complete"])
filtered = data.iloc[start_index : end_index + 1].copy()
if status_filter != "all":
    filtered = filtered[filtered["annotation_status"] == status_filter].reset_index(drop=True)

if filtered.empty:
    st.info("No rows in the selected range/filter.")
    st.stop()

complete_total = int((data["annotation_status"] == "complete").sum())
pending_total = int((data["annotation_status"] == "pending").sum())
needs_review_total = int((data["annotation_status"] == "needs_review").sum())
range_complete = int((filtered["annotation_status"] == "complete").sum())

st.sidebar.metric("Dataset complete", f"{complete_total} / {EXPECTED_ROWS}")
st.sidebar.metric("Pending", pending_total)
st.sidebar.metric("Needs review", needs_review_total)
st.sidebar.metric("Range complete", f"{range_complete} / {len(filtered)}")

entry_labels = [
    f"{row.expanded_image_id} [{row.annotation_status or 'pending'}]"
    for row in filtered.itertuples(index=False)
]
selected_label = st.sidebar.selectbox("Image", entry_labels)
selected_id = selected_label.split(" ")[0]
global_index = data.index[data["expanded_image_id"] == selected_id][0]
row = data.loc[global_index].copy()

image_rel = row["review_image_path_local"]
image_path = PROJECT_ROOT / image_rel

left, right = st.columns([3, 2])
with left:
    if image_path.exists():
        st.image(str(image_path), caption=row["expanded_image_id"], use_container_width=True)
    else:
        st.error(f"Image not found: {image_rel}")

with right:
    st.write(f"**Status:** {row.get('annotation_status', 'pending')}")
    st.write(f"**Selection stratum:** {row.get('selection_stratum', '')}")
    with st.form("annotation_form"):
        updates = {}
        for field, options in STREAMLIT_ALLOWED_VALUES.items():
            current = row.get(field, "")
            index = options.index(current) if current in options else 0
            updates[field] = st.selectbox(field, options, index=index)
        updates["annotator_notes"] = st.text_area(
            "annotator_notes",
            value=row.get("annotator_notes", ""),
            height=120,
        )
        submitted = st.form_submit_button("Save annotation")
        if submitted:
            for field, value in updates.items():
                data.at[global_index, field] = value
            data.to_csv(WORKING_CSV, index=False)
            st.success(f"Saved to {WORKING_CSV.name}")

st.caption(
    "Review visual evidence factors only. Poor image quality can still be labeled confidently as complete."
)
