"""Shared pytest markers for tests that need the local evidence boundary."""

from __future__ import annotations

import pytest


LOCAL_EVIDENCE_TEST_MODULES = frozenset(
    {
        "test_advanced_claim_gates_methods_report.py",
        "test_advanced_modeling_contract.py",
        "test_analyze_task15i_conditional_90pct_feasibility.py",
        "test_analyze_task17_confirmation_outcomes.py",
        "test_audit_ws04_power_cost_inputs.py",
        "test_build_pferi_v2_manuscript_displays.py",
        "test_build_pferi_v2_manuscript_source_manifest.py",
        "test_descriptor_stratified_calibration.py",
        "test_design_task15i_independent_redevelopment.py",
        "test_freeze_pferi_v2_feature_preprocessing.py",
        "test_freeze_pferi_v2_final_project_closure.py",
        "test_freeze_task15g_exploratory_performance_bound_contract.py",
        "test_freeze_task15g_exploratory_performance_bound_results.py",
        "test_freeze_task15h_development_model.py",
        "test_freeze_task15i_human_review_development_results.py",
        "test_freeze_task15j_independent_development_model.py",
        "test_freeze_task15k_independent_calibration_design.py",
        "test_freeze_task15l_calibration_collection.py",
        "test_freeze_task15n_confirmation_execution_results.py",
        "test_freeze_task16_final_claim_matrix.py",
        "test_reason_label_enrichment_packet.py",
        "test_reconcile_task15g_external_results.py",
    }
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.name in LOCAL_EVIDENCE_TEST_MODULES:
            item.add_marker(pytest.mark.local_evidence)
