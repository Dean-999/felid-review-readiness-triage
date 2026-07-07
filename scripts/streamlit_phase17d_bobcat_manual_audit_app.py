#!/usr/bin/env python3
"""Streamlit app for Phase17D Bobcat manual image audit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT_SHEET = (
    PROJECT_ROOT
    / "outputs/phase17/phase17c_bobcat_provisional_3000/phase17c_bobcat_manual_audit_expansion_sheet.csv"
)
WORKING_AUDIT_SHEET = (
    PROJECT_ROOT
    / "outputs/phase17/phase17d_bobcat_manual_audit_gate/phase17d_bobcat_manual_audit_working.csv"
)

YES_NO = ["", "yes", "no"]
VIEWPOINT_LABELS = ["", "left_side", "right_side", "frontal", "rear", "partial_or_occluded", "unclear"]
OCCLUSION_LABELS = ["", "none", "mild", "moderate", "severe", "unclear"]

AUDIT_FIELDS = [
    "is_bobcat_visible",
    "is_individual_review_usable",
    "viewpoint_manual_label",
    "occlusion_manual_label",
    "selection_role_agreement",
    "algorithm_entry_allowed",
    "audit_notes",
]


def ensure_working_sheet() -> None:
    if WORKING_AUDIT_SHEET.exists():
        return
    if not SOURCE_AUDIT_SHEET.exists():
        st.error(f"Source audit sheet not found: {SOURCE_AUDIT_SHEET}")
        st.stop()
    WORKING_AUDIT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_AUDIT_SHEET, WORKING_AUDIT_SHEET)


@st.cache_data(show_spinner=False)
def load_data(path_text: str) -> pd.DataFrame:
    return pd.read_csv(Path(path_text), dtype=str, keep_default_na=False).fillna("")


def save_data(frame: pd.DataFrame) -> None:
    frame.to_csv(WORKING_AUDIT_SHEET, index=False)
    load_data.clear()


def option_index(options: list[str], current: object) -> int:
    value = str(current or "")
    return options.index(value) if value in options else 0


def completed_mask(frame: pd.DataFrame) -> pd.Series:
    required = [
        "is_bobcat_visible",
        "is_individual_review_usable",
        "selection_role_agreement",
        "algorithm_entry_allowed",
    ]
    return frame[required].fillna("").ne("").all(axis=1)


def system_decision_help(row: pd.Series) -> str:
    role = row.get("phase17c_selection_role", "")
    route = row.get("phase17b_route", "")
    bucket = row.get("phase17c_selection_bucket", "")
    if role == "clean_backbone":
        return (
            "System thinks this is part of the clean Tier 1 backbone. Mark agreement=yes only if the image "
            "really looks suitable as clean algorithm-entry evidence."
        )
    if role == "transfer_sentinel":
        return (
            "System thinks this is a Tier 2 transfer-stress sentinel. Mark agreement=yes if it is still useful "
            "as a transfer/stress-review example, even if it is not as clean as Tier 1."
        )
    if route in {"non_comparable_or_defer", "manual_low_evidence_check"}:
        return "System routed this toward defer/low-evidence review. Agreement=yes if you also think it should not enter main algorithm evidence."
    return f"Judge whether the system role/bucket is reasonable: role={role}, bucket={bucket}, route={route}."


def queue_badge(row: pd.Series) -> tuple[str, str]:
    role = row.get("phase17c_selection_role", "")
    reason = row.get("phase17c_manual_audit_reason", "")
    route = row.get("phase17b_route", "")
    if role == "clean_backbone":
        return "success", "Selected candidate: clean Tier 1 backbone for the provisional 3000."
    if role == "transfer_sentinel":
        return "info", "Selected candidate: Tier 2 transfer sentinel for stress testing, not a clean Tier 1 example."
    if reason in {"defer_or_low_score", "rejected_tier1_borderline", "rejected_tier2_borderline"}:
        return "warning", "Audit control / rejected-borderline row: use it to check whether the gate rejects weak evidence."
    if route in {"non_comparable_or_defer", "manual_low_evidence_check"}:
        return "warning", "Low-evidence review row: not a final high-confidence algorithm-entry image."
    return "info", "Review row: judge whether the system route is reasonable."


def filtered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    role_filter = st.sidebar.selectbox(
        "selection role",
        ["all", *sorted(v for v in out["phase17c_selection_role"].unique() if v)],
    )
    reason_filter = st.sidebar.selectbox(
        "audit reason",
        ["all", *sorted(v for v in out["phase17c_manual_audit_reason"].unique() if v)],
    )
    status_filter = st.sidebar.selectbox("status", ["all", "pending", "complete"])
    route_filter = st.sidebar.selectbox(
        "phase17b route",
        ["all", *sorted(v for v in out["phase17b_route"].unique() if v)],
    )
    if role_filter != "all":
        out = out[out["phase17c_selection_role"].eq(role_filter)]
    if reason_filter != "all":
        out = out[out["phase17c_manual_audit_reason"].eq(reason_filter)]
    if route_filter != "all":
        out = out[out["phase17b_route"].eq(route_filter)]
    if status_filter == "pending":
        out = out[~completed_mask(out)]
    elif status_filter == "complete":
        out = out[completed_mask(out)]
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


def main() -> None:
    st.set_page_config(page_title="Phase17D Bobcat Manual Audit", layout="wide")
    st.title("Phase17D Bobcat Manual Audit")
    st.caption(
        "Fill human review-readiness fields only. This does not assign Bobcat identity or validate identity accuracy."
    )

    ensure_working_sheet()
    data = load_data(str(WORKING_AUDIT_SHEET))
    complete = completed_mask(data)

    st.sidebar.header("Progress")
    st.sidebar.metric("completed", f"{int(complete.sum())} / {len(data)}")
    st.sidebar.metric("pending", int((~complete).sum()))
    st.sidebar.caption(f"working CSV: {WORKING_AUDIT_SHEET}")

    view = filtered_frame(data)
    if view.empty:
        st.info("No rows match the selected filters.")
        st.stop()

    query_candidate = st.query_params.get("candidate_id", "")
    candidate_ids = list(view["candidate_id"])
    if "nav_candidate_id" not in st.session_state:
        st.session_state.nav_candidate_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]
    if st.session_state.nav_candidate_id not in candidate_ids:
        st.session_state.nav_candidate_id = query_candidate if query_candidate in candidate_ids else candidate_ids[0]
    selected_id = st.sidebar.selectbox(
        "candidate_id",
        candidate_ids,
        index=candidate_ids.index(st.session_state.nav_candidate_id),
        key=f"candidate_id_selectbox_{st.session_state.nav_candidate_id}",
    )
    st.session_state.nav_candidate_id = selected_id
    set_query_row(selected_id)

    row_index = data.index[data["candidate_id"].eq(selected_id)][0]
    row = data.loc[row_index].copy()

    left, right = st.columns([3, 2])
    with left:
        st.subheader(selected_id)
        image_uri = row.get("image_uri", "")
        if image_uri:
            st.image(image_uri, caption=image_uri, width="stretch")
            st.link_button("Open image in browser", image_uri)
        else:
            st.error("No image_uri for this row.")

        st.markdown("### Selection context")
        context_cols = [
            "phase17c_selection_role",
            "phase17c_manual_audit_reason",
            "phase17c_selection_bucket",
            "phase17b_route",
            "source_tier",
            "source_role",
            "final_candidate_score",
            "iqa_quality_proxy_score",
            "clip_side_view_score",
            "clip_viewpoint_label",
            "clip_viewpoint_prob_partial_or_occluded",
            "clip_viewpoint_prob_unclear",
            "md_geometry_score",
        ]
        shown = {col: row.get(col, "") for col in context_cols if col in row.index}
        st.dataframe(pd.DataFrame(shown.items(), columns=["field", "value"]), width="stretch")

    with right:
        st.markdown("### System decision to judge")
        badge_level, badge_text = queue_badge(row)
        if badge_level == "success":
            st.success(badge_text)
        elif badge_level == "warning":
            st.warning(badge_text)
        else:
            st.info(badge_text)
        st.write(f"**selection_role:** `{row.get('phase17c_selection_role', '')}`")
        st.write(f"**selection_bucket:** `{row.get('phase17c_selection_bucket', '')}`")
        st.write(f"**phase17b_route:** `{row.get('phase17b_route', '')}`")
        st.write(f"**audit_reason:** `{row.get('phase17c_manual_audit_reason', '')}`")
        st.caption(system_decision_help(row))

        st.markdown("### Human audit")
        st.info(
            "algorithm_entry_allowed = yes only when the animal is visible as bobcat and the image is usable for individual review."
        )
        with st.form("phase17d_audit_form"):
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
                "occlusion_manual_label": st.selectbox(
                    "occlusion_manual_label",
                    OCCLUSION_LABELS,
                    index=option_index(OCCLUSION_LABELS, row.get("occlusion_manual_label", "")),
                ),
                "selection_role_agreement": st.radio(
                    "selection_role_agreement",
                    YES_NO,
                    index=option_index(YES_NO, row.get("selection_role_agreement", "")),
                    horizontal=True,
                ),
                "algorithm_entry_allowed": st.radio(
                    "algorithm_entry_allowed",
                    YES_NO,
                    index=option_index(YES_NO, row.get("algorithm_entry_allowed", "")),
                    horizontal=True,
                ),
                "audit_notes": st.text_area("audit_notes", value=row.get("audit_notes", ""), height=120),
            }
            save_col, next_col = st.columns(2)
            with save_col:
                submitted = st.form_submit_button("Save row")
            with next_col:
                submitted_next = st.form_submit_button("Save and next pending")
            if submitted or submitted_next:
                for field, value in updates.items():
                    data.at[row_index, field] = value
                save_data(data)
                if submitted_next:
                    next_id = next_pending_candidate(data, selected_id)
                    if next_id:
                        st.session_state.nav_candidate_id = next_id
                        set_query_row(next_id)
                        st.success(f"Saved. Moving to {next_id}.")
                    else:
                        st.success("Saved. All rows complete.")
                else:
                    st.success("Saved.")
                st.rerun()

        st.markdown("### Quick standards")
        st.write("- `is_bobcat_visible=yes`: bobcat is visible enough to confirm species-level presence.")
        st.write("- `is_individual_review_usable=yes`: enough visible body/marking/view quality for individual review.")
        st.write("- `selection_role_agreement=yes`: your visual judgment agrees with the system role shown above.")
        st.write("- `algorithm_entry_allowed=yes`: both above are yes and no severe blur/occlusion/non-comparable issue.")
        st.caption(
            "Important: source labels such as urban_bobcat_high_confidence come from the input pool; they are not "
            "the Phase17 final quality/readiness decision."
        )

        if st.button("Go to next pending row"):
            refreshed = load_data(str(WORKING_AUDIT_SHEET))
            next_id = next_pending_candidate(refreshed, selected_id)
            if next_id:
                st.session_state.nav_candidate_id = next_id
                set_query_row(next_id)
                st.rerun()
            st.success("All rows complete.")

    st.divider()
    st.markdown("### After filling enough rows")
    st.code(
        "python3 scripts/build_phase17d_bobcat_manual_audit_gate.py "
        "--audit-sheet outputs/phase17/phase17d_bobcat_manual_audit_gate/phase17d_bobcat_manual_audit_working.csv",
        language="bash",
    )


if __name__ == "__main__":
    main()
