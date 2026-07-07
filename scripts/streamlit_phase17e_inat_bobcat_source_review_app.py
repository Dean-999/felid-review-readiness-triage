#!/usr/bin/env python3
"""Streamlit app for Phase17E iNaturalist Bobcat source review."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17e_external_source_probe/prototype_phase17e_inat_research_grade_bobcat_top3000.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17e_external_source_probe"
WORKING_CSV = OUTPUT_DIR / "phase17e_inat_bobcat_source_review_working.csv"

YES_NO = ["", "yes", "no"]
VIEWPOINT_LABELS = ["", "left_side", "right_side", "frontal", "rear", "partial_or_occluded", "unclear"]
OCCLUSION_LABELS = ["", "none", "mild", "moderate", "severe", "unclear"]
BODY_FRACTION_LABELS = ["", "0_25", "26_50", "51_75", "76_100", "unclear"]
QUALITY_LABELS = ["", "excellent", "good", "borderline", "reject"]

AUDIT_FIELDS = [
    "is_bobcat_visible",
    "is_individual_review_usable",
    "viewpoint_manual_label",
    "body_fraction_visible",
    "markings_visible",
    "occlusion_manual_label",
    "algorithm_entry_allowed",
    "quality_bucket_manual",
    "audit_notes",
]


def ensure_working_csv() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if WORKING_CSV.exists():
        return
    if not SOURCE_CSV.exists():
        st.error(f"Source CSV not found: {SOURCE_CSV}")
        st.stop()
    shutil.copy2(SOURCE_CSV, WORKING_CSV)
    data = pd.read_csv(WORKING_CSV, dtype=str, keep_default_na=False).fillna("")
    for field in AUDIT_FIELDS:
        if field not in data.columns:
            data[field] = ""
    data["phase17e_review_status"] = "pending"
    data["phase17e_claim_boundary"] = "external-source review only; no automatic identity or algorithm-entry claim"
    data.to_csv(WORKING_CSV, index=False)


@st.cache_data(show_spinner=False)
def load_data(path_text: str) -> pd.DataFrame:
    return pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")


def save_data(frame: pd.DataFrame) -> None:
    frame.to_csv(WORKING_CSV, index=False)
    load_data.clear()


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    required = [
        "is_bobcat_visible",
        "is_individual_review_usable",
        "algorithm_entry_allowed",
        "quality_bucket_manual",
    ]
    return frame[required].fillna("").ne("").all(axis=1)


def option_index(options: list[str], current: object) -> int:
    value = str(current or "")
    return options.index(value) if value in options else 0


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    status_filter = st.sidebar.selectbox("status", ["all", "pending", "complete"])
    license_filter = st.sidebar.selectbox(
        "photo license",
        ["all", *sorted(v for v in out["photo_license_code"].unique() if v)],
    )
    quality_filter = st.sidebar.selectbox(
        "manual quality",
        ["all", *sorted(v for v in out["quality_bucket_manual"].unique() if v)],
    )
    if status_filter == "pending":
        out = out[~completed_mask(out)]
    elif status_filter == "complete":
        out = out[completed_mask(out)]
    if license_filter != "all":
        out = out[out["photo_license_code"].eq(license_filter)]
    if quality_filter != "all":
        out = out[out["quality_bucket_manual"].eq(quality_filter)]
    return out


def set_query_row(candidate_id: str) -> None:
    st.query_params["candidate_id"] = candidate_id


def next_pending_candidate(frame: pd.DataFrame, current_id: str) -> str:
    pending_ids = list(frame.loc[~completed_mask(frame), "candidate_id"])
    if not pending_ids:
        return ""
    if current_id in pending_ids:
        current_pos = pending_ids.index(current_id)
        if current_pos + 1 < len(pending_ids):
            return str(pending_ids[current_pos + 1])
    return str(pending_ids[0])


def source_help(row: pd.Series) -> str:
    return (
        "This is iNaturalist research-grade source material: species/community screening is stronger than "
        "the previous camera-trap batch, but you still decide review-readiness from the image itself."
    )


def main() -> None:
    st.set_page_config(page_title="Phase17E iNat Bobcat Source Review", layout="wide")
    st.title("Phase17E iNat Bobcat Source Review")
    st.caption("External curated-source probe. Review image usability only; do not assign individual identity here.")

    ensure_working_csv()
    data = load_data(str(WORKING_CSV))
    for field in AUDIT_FIELDS:
        if field not in data.columns:
            data[field] = ""
    complete = completed_mask(data)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(data)}")
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_CSV}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the selected filters.")
        st.stop()

    candidate_ids = list(view["candidate_id"])
    query_candidate = st.query_params.get("candidate_id", "")
    if "phase17e_nav_candidate_id" not in st.session_state:
        st.session_state.phase17e_nav_candidate_id = (
            query_candidate if query_candidate in candidate_ids else candidate_ids[0]
        )
    if st.session_state.phase17e_nav_candidate_id not in candidate_ids:
        st.session_state.phase17e_nav_candidate_id = (
            query_candidate if query_candidate in candidate_ids else candidate_ids[0]
        )

    selected_id = st.sidebar.selectbox(
        "candidate_id",
        candidate_ids,
        index=candidate_ids.index(st.session_state.phase17e_nav_candidate_id),
        key=f"phase17e_candidate_selectbox_{st.session_state.phase17e_nav_candidate_id}",
    )
    st.session_state.phase17e_nav_candidate_id = selected_id
    set_query_row(selected_id)

    row_index = data.index[data["candidate_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()

    left, right = st.columns([3, 2])
    with left:
        st.subheader(selected_id)
        image_uri = row.get("image_uri", "")
        if image_uri:
            st.image(image_uri, caption=image_uri, width="stretch")
            st.link_button("Open source observation", row.get("observation_uri", ""))
            st.link_button("Open image", image_uri)
        else:
            st.error("No image_uri for this row.")

        st.markdown("### Source context")
        context_cols = [
            "external_source",
            "quality_grade",
            "photo_license_code",
            "observed_on",
            "place_guess",
            "taxon_name",
            "taxon_preferred_common_name",
            "phase17e_source_score",
            "observation_id",
            "photo_id",
        ]
        shown = {col: row.get(col, "") for col in context_cols if col in row.index}
        st.dataframe(pd.DataFrame(shown.items(), columns=["field", "value"]), width="stretch")

    with right:
        st.markdown("### Review decision")
        st.info(source_help(row))
        with st.form("phase17e_inat_source_review_form"):
            updates = {
                "is_bobcat_visible": st.radio(
                    "is_bobcat_visible",
                    YES_NO,
                    index=option_index(YES_NO, row.get("is_bobcat_visible", "")),
                    horizontal=True,
                ),
                "is_individual_review_usable": st.radio(
                    "is_individual_review_usable",
                    YES_NO,
                    index=option_index(YES_NO, row.get("is_individual_review_usable", "")),
                    horizontal=True,
                ),
                "viewpoint_manual_label": st.selectbox(
                    "viewpoint_manual_label",
                    VIEWPOINT_LABELS,
                    index=option_index(VIEWPOINT_LABELS, row.get("viewpoint_manual_label", "")),
                ),
                "body_fraction_visible": st.selectbox(
                    "body_fraction_visible",
                    BODY_FRACTION_LABELS,
                    index=option_index(BODY_FRACTION_LABELS, row.get("body_fraction_visible", "")),
                ),
                "markings_visible": st.radio(
                    "markings_visible",
                    YES_NO,
                    index=option_index(YES_NO, row.get("markings_visible", "")),
                    horizontal=True,
                ),
                "occlusion_manual_label": st.selectbox(
                    "occlusion_manual_label",
                    OCCLUSION_LABELS,
                    index=option_index(OCCLUSION_LABELS, row.get("occlusion_manual_label", "")),
                ),
                "algorithm_entry_allowed": st.radio(
                    "algorithm_entry_allowed",
                    YES_NO,
                    index=option_index(YES_NO, row.get("algorithm_entry_allowed", "")),
                    horizontal=True,
                ),
                "quality_bucket_manual": st.selectbox(
                    "quality_bucket_manual",
                    QUALITY_LABELS,
                    index=option_index(QUALITY_LABELS, row.get("quality_bucket_manual", "")),
                ),
                "audit_notes": st.text_area("audit_notes", value=row.get("audit_notes", ""), height=100),
            }
            save_col, next_col = st.columns(2)
            submitted = save_col.form_submit_button("Save row")
            submitted_next = next_col.form_submit_button("Save and next pending")
            if submitted or submitted_next:
                for field, value in updates.items():
                    data.at[row_index, field] = value
                data.at[row_index, "phase17e_review_status"] = "complete"
                save_data(data)
                if submitted_next:
                    next_id = next_pending_candidate(data, selected_id)
                    if next_id:
                        st.session_state.phase17e_nav_candidate_id = next_id
                        set_query_row(next_id)
                st.rerun()

        st.markdown("### Quick standards")
        st.write("- `excellent`: clear body/side or distinctive markings, low occlusion, useful for algorithm-entry.")
        st.write("- `good`: usable for review, maybe not perfect.")
        st.write("- `borderline`: visible bobcat but weak for individual review.")
        st.write("- `reject`: not useful for individual-review or algorithm-entry.")
        if st.button("Go to next pending row"):
            refreshed = load_data(str(WORKING_CSV))
            next_id = next_pending_candidate(refreshed, selected_id)
            if next_id:
                st.session_state.phase17e_nav_candidate_id = next_id
                set_query_row(next_id)
                st.rerun()
            st.success("All rows complete.")


if __name__ == "__main__":
    main()
