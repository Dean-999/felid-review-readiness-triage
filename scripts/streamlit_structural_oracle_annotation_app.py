"""Streamlit UI for a fixed independent structural-oracle annotator."""
from __future__ import annotations
import os
from pathlib import Path
import streamlit as st
from scripts import structural_oracle_annotation_core as core

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = Path(os.environ.get("STRUCTURAL_ORACLE_PACKAGE_ROOT", ROOT / "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package"))
OUTPUT_ROOT = Path(os.environ.get("STRUCTURAL_ORACLE_OUTPUT_ROOT", ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_responses"))
GRID = [f"{index / 20:.2f}" for index in range(21)]

def main(annotator_id: str) -> None:
    st.set_page_config(page_title="Structural annotation", layout="wide")
    packets = core.load_packet(PACKAGE_ROOT); responses = core.load_responses(OUTPUT_ROOT, annotator_id, set(packets.annotation_packet_id))
    done = set(responses.annotation_packet_id); pending = packets[~packets.annotation_packet_id.isin(done)]
    st.title("Structural evidence annotation"); st.caption("Record visible structure only. Do not judge identity or reviewability.")
    st.sidebar.metric("Completed", f"{len(done)} / {len(packets)}")
    row = pending.iloc[0] if not pending.empty else packets.iloc[0]
    packet_id = row.annotation_packet_id
    st.caption(packet_id)
    left, right = st.columns(2)
    with left: st.image(str(core.resolve_asset(PACKAGE_ROOT, row.left_asset_token)), caption="Image A")
    with right: st.image(str(core.resolve_asset(PACKAGE_ROOT, row.right_asset_token)), caption="Image B")
    technical = st.checkbox("Technical display problem", value=False)
    with st.form("structural_form"):
        a,b,c = st.columns(3)
        with a:
            left_pattern=st.selectbox("Image A visible pattern fraction", GRID); left_occ=st.selectbox("Image A occlusion fraction", GRID)
        with b:
            right_pattern=st.selectbox("Image B visible pattern fraction", GRID); right_occ=st.selectbox("Image B occlusion fraction", GRID)
        with c:
            shared=st.selectbox("Shared body-region fraction", GRID); view=st.selectbox("Viewpoint compatibility", core.VIEWPOINTS)
        submitted=st.form_submit_button("Save and next", type="primary")
    if submitted:
        values=core.empty_response(packet_id); values.update({"technical_problem_flag":"yes" if technical else "no", "left_visible_pattern_area_fraction":left_pattern if not technical else "", "right_visible_pattern_area_fraction":right_pattern if not technical else "", "left_occlusion_fraction":left_occ if not technical else "", "right_occlusion_fraction":right_occ if not technical else "", "shared_body_region_fraction":shared if not technical else "", "viewpoint_compatibility_class":view if not technical else ""})
        try:
            core.save_response(OUTPUT_ROOT, annotator_id, responses, values); st.rerun()
        except ValueError as error: st.error(str(error))
