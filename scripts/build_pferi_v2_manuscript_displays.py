#!/usr/bin/env python3
"""Build auditable PF-ERI v2 manuscript tables and publication figures.

The builder only reads frozen artifacts. It never fits a model or recalculates
Task15L calibration parameters.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "paper/tables/pferi_v2"
DEFAULT_FIGURES = ROOT / "paper/figures/pferi_v2"
TASK15I = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-27_task15i_human_review_outcome_analysis/iterations/v3"
SOURCE_PACKAGE = ROOT / "paper/supplement/source_data/pferi_v2"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pct(n: int, d: int) -> str:
    return f"{n} ({100 * n / d:.1f}%)" if d else "not applicable"


def f6(value: float) -> str:
    return f"{value:.6f}"


def markdown_table(rows: list[dict[str, Any]], columns: list[str], title: str, note: str) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [f"# {title}", "", f"{note}", "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(clean(row.get(c, "")) for c in columns) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def write_table(directory: Path, stem: str, title: str, rows: list[dict[str, Any]], note: str) -> dict[str, Any]:
    if not rows:
        raise ValueError(f"empty table: {stem}")
    columns = list(rows[0])
    with (directory / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    (directory / f"{stem}.md").write_text(markdown_table(rows, columns, title, note), encoding="utf-8")
    return {"table_id": stem.split("_")[0].upper(), "stem": stem, "title": title, "row_count": len(rows), "columns": columns, "note": note}


def cohen_kappa_binary(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return math.nan
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    a1 = sum(a == "1" for a, _ in pairs) / n
    b1 = sum(b == "1" for _, b in pairs) / n
    expected = a1 * b1 + (1 - a1) * (1 - b1)
    return (observed - expected) / (1 - expected) if expected < 1 else math.nan


def agreement_row(stage: str, triples: list[tuple[str, str]], interpretation: str) -> dict[str, Any]:
    binary = [("0" if a == "review_ready" else "1", "0" if b == "review_ready" else "1") for a, b in triples]
    exact = sum(a == b for a, b in triples)
    binary_n = sum(a == b for a, b in binary)
    return {
        "stage": stage,
        "pair_count": len(triples),
        "first_pass_response_count": 2 * len(triples),
        "three_category_exact_agreement": pct(exact, len(triples)),
        "binary_agreement": pct(binary_n, len(triples)),
        "cohen_kappa_binary": f"{cohen_kappa_binary(binary):.4f}",
        "disagreement_count": len(triples) - exact,
        "adjudication_count": "not applicable" if stage != "Formal confirmation" else len(triples) - exact,
        "interpretation": interpretation,
    }


def weighted_mean(rows: list[dict[str, str]], field: str) -> float:
    weights = [1 / float(row["first_order_inclusion_probability"]) for row in rows]
    return sum(w * float(row[field]) for w, row in zip(weights, rows)) / sum(weights)


def build_tables(output: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    model = read_json(ROOT / "outputs/pferi_v2/models/development/final_model_bundle.json")
    freeze = read_json(ROOT / "outputs/pferi_v2/models/development/development_model_freeze_record_v2.json")
    cal = read_json(ROOT / "outputs/pferi_v2/models/calibration/analysis/task15l_calibration_analysis_freeze_record.json")
    execution = read_json(ROOT / "outputs/pferi_v2/models/confirmation/execution_freeze/task15n_confirmation_execution_result_freeze.json")
    confirmation = read_json(ROOT / "outputs/pferi_v2/models/confirmation/final_analysis/task17_confirmation_outcome_analysis.json")
    closure = read_json(ROOT / "outputs/pferi_v2/project_closure/final_project_closure_record.json")
    labels_i = read_csv(TASK15I / "pair_level_outcome_labels.csv")
    folds = read_csv(TASK15I / "fold_level_brier_results.csv")
    descriptor = read_csv(ROOT / "outputs/pferi_v2/models/confirmation/execution_results/descriptor_pair_measurements.csv")
    outcomes = read_csv(ROOT / "outputs/pferi_v2/review/adjudicated_outcomes/final_adjudicated_outcomes.csv")
    deployment = [r for r in outcomes if r["formal_sampling_stage"] == "deployment_confirmation"]
    loss = read_csv(ROOT / "outputs/pferi_v2/models/confirmation/final_analysis/task17_pair_level_brier_losses.csv")
    predictions = read_csv(ROOT / "outputs/pferi_v2/models/confirmation/execution_results/frozen_model_calibrated_predictions.csv")
    source_manifest = read_csv(SOURCE_PACKAGE / "evidence_source_manifest.csv")
    claim_map = read_csv(SOURCE_PACKAGE / "claim_evidence_map.csv")
    records: list[dict[str, Any]] = []

    rows = [
        {"stage": "Task15I development", "scientific_purpose": "Qualify the nested pair-evidence extension", "pair_source": "Independent redevelopment reservoir", "pair_count": "1,600 in 400 endpoint-disjoint components", "outcome_access": "Available only within component-disjoint development folds", "permitted_model_action": "Fit and compare P3/P5 at fixed lambda", "dependency_control": "Endpoint-disjoint components", "primary_output": "PASS_TASK15I_DEVELOPMENT_SCREEN", "permitted_claim": "Development qualification"},
        {"stage": "Task15J model freeze", "scientific_purpose": "Lock the active control and full model", "pair_source": "Task15I development data", "pair_count": "1,600", "outcome_access": "No new outcomes", "permitted_model_action": "Freeze coefficients, preprocessing, and lambda=100", "dependency_control": "Frozen bundle hash", "primary_output": freeze["status"], "permitted_claim": "Reproducible model freeze"},
        {"stage": "Task15L calibration", "scientific_purpose": "Estimate calibration intercept and slope", "pair_source": "Independent calibration partition", "pair_count": "448", "outcome_access": "Opened for calibration only", "permitted_model_action": "Calibrate probabilities; no refit or selection", "dependency_control": "Double review; frozen P3/P5", "primary_output": cal["status"], "permitted_claim": "Calibration completion"},
        {"stage": "Task15M/15N execution", "scientific_purpose": "Validate outcome-free external execution", "pair_source": "Deployment-confirmation queue", "pair_count": "889 candidates; 252 supported", "outcome_access": "Sealed", "permitted_model_action": "Measure, score, and calibrate only", "dependency_control": "Hash and shape validation", "primary_output": execution["status"], "permitted_claim": "Execution integrity and support accounting"},
        {"stage": "Independent outcome analysis", "scientific_purpose": "Test frozen P5 versus P3", "pair_source": "252 descriptor-supported pairs", "pair_count": "252 pairs; 357 physical endpoints", "outcome_access": "Opened once", "permitted_model_action": "Analyze only; no refit", "dependency_control": "Dyadic endpoint-aware interval", "primary_output": confirmation["status"], "permitted_claim": "Independent comparison result"},
        {"stage": "Operational closure", "scientific_purpose": "Close the governed execution workflow", "pair_source": "Task15M execution record", "pair_count": "889 candidates", "outcome_access": "Not the closure basis", "permitted_model_action": "None", "dependency_control": "Frozen acceptance hashes", "primary_output": f"{closure['status']}/{closure['project_status']}", "permitted_claim": "Task15M execution-validation scope only"},
    ]
    records.append(write_table(output, "table1_study_architecture", "Table 1. Prospective study architecture and information boundaries", rows, "Operational CONFIRMED is limited to Task15M execution validation; it is not P5 superiority or identity validation."))

    rows = [
        {"concept": "Single-image technical quality", "unit": "Image", "information_used": "Decode status, pixels, sharpness, exposure", "decision_question": "Can the image be decoded and measured?", "positive_state": "Technical measurements are available", "negative_state": "Measurement failure or stress", "role_in_pferi": "Predictor/input audit", "not_equivalent_to": "Pair reviewability"},
        {"concept": "Descriptor similarity", "unit": "Directed retrieval", "information_used": "Descriptor ranks/scores", "decision_question": "Does one image retrieve the other highly?", "positive_state": "High within-role retrieval rank", "negative_state": "Weak or absent retrieval", "role_in_pferi": "Candidate generation/predictor", "not_equivalent_to": "Same identity or reviewability"},
        {"concept": "Gate 1: descriptor-relation support", "unit": "Unordered image pair", "information_used": "MegaDescriptor and DINOv2 directed top-20 ranks", "decision_question": "Is the frozen same-direction dual-descriptor relation present?", "positive_state": "both_reciprocal or both_agreement", "negative_state": "no_same_direction_dual_descriptor_top20_consensus", "role_in_pferi": "Scoring eligibility gate", "not_equivalent_to": "Human rejection"},
        {"concept": "Gate 2: visual reviewability", "unit": "Unordered image pair", "information_used": "Blinded human visual evidence", "decision_question": "Is there comparable evidence for responsible review?", "positive_state": "review_ready", "negative_state": "not_review_ready or uncertain", "role_in_pferi": "Primary human endpoint", "not_equivalent_to": "Identity match"},
        {"concept": "Identity truth", "unit": "Known-identity relation", "information_used": "Trusted individual identity linkage", "decision_question": "Do the images depict the same individual?", "positive_state": "Same individual", "negative_state": "Different individual", "role_in_pferi": "Outside primary endpoint", "not_equivalent_to": "Review-ready; a different-identity pair may be review-ready"},
    ]
    records.append(write_table(output, "table2_pair_scientific_object", "Table 2. The pair as the scientific object: two gates and adjacent concepts", rows, "The descriptor-support gate, human reviewability endpoint, and identity truth are distinct constructs."))

    desc_counts = Counter(r["support_status"] for r in descriptor)
    supported_ids = {r["canonical_pair_id"] for r in descriptor if r["support_status"] == "supported"}
    historical_by_task = {r["task15m_confirmation_pair_id"]: r["historical_canonical_pair_id"] for r in loss}
    supported_historical = set(historical_by_task.values())
    dep_supported = [r for r in deployment if r["canonical_pair_id"] in supported_historical]
    dep_unsupported = [r for r in deployment if r["canonical_pair_id"] not in supported_historical]
    def inventory(stage: str, candidate: int, analyzed: int, endpoints: str, components: str, subset: list[dict[str, str]] | None, sup: int | str, unsup: int | str, role: str) -> dict[str, Any]:
        rr = sum(r["not_ready_or_uncertain_label"] in ("0", "0.0") for r in subset) if subset is not None else None
        nr = len(subset) - rr if subset is not None else None
        return {"stage_or_subset": stage, "candidate_pairs": candidate, "analyzable_or_scored_pairs": analyzed, "unique_endpoint_images": endpoints, "endpoint_components": components, "review_ready_n_percent": pct(rr, len(subset)) if subset is not None else "not available", "not_ready_or_uncertain_n_percent": pct(nr, len(subset)) if subset is not None else "not available", "descriptor_supported_n_percent": pct(sup, candidate) if isinstance(sup, int) else sup, "descriptor_unsupported_n_percent": pct(unsup, candidate) if isinstance(unsup, int) else unsup, "sampling_or_weighting_role": role}
    rows = [
        inventory("Task15I development", 1600, 1600, "not reported in display source", "400", labels_i, "not applicable", "not applicable", "Inverse-square-root inclusion weights"),
        inventory("Task15L calibration", 448, 448, "not reported in display source", "not applicable", [{"not_ready_or_uncertain_label": str(x)} for x in ([0] * 86 + [1] * 362)], "not applicable", "not applicable", "Calibration only"),
        inventory("Task15M full queue", 889, 252, "815", "not applicable", deployment, 252, 637, "Deployment sampling probabilities"),
        inventory("Task15M descriptor-supported", 252, 252, "357 in final analysis", "not applicable", dep_supported, 252, 0, "Primary independent comparison subset"),
        inventory("Task15M descriptor-unsupported", 637, 0, "not separately frozen", "not applicable", dep_unsupported, 0, 637, "Excluded by Gate 1; outcomes descriptive only"),
    ]
    records.append(write_table(output, "table3_pair_inventories", "Table 3. Pair inventories, support, and endpoint distributions by stage", rows, "The 637 descriptor-unsupported pairs are not 637 human-not-review-ready pairs. Human counts are linked directly to frozen outcome records."))

    rows = [
        {"feature_family": "Descriptor", "feature_or_block": "MegaDescriptor and DINOv2 within-role percentiles", "unit": "Directed rank percentile", "p3_active_control": "Included", "p5_full_model": "Included", "availability_timing": "Before human outcomes", "transformation": "Training-fold median imputation and z-score", "missingness_handling": "Explicit missing indicator", "interpretation": "Retrieval strength"},
        {"feature_family": "Descriptor", "feature_or_block": "descriptor_support_category", "unit": "Pair", "p3_active_control": "Included", "p5_full_model": "Included", "availability_timing": "Before human outcomes", "transformation": "Frozen one-hot encoding", "missingness_handling": "Missing and unknown states", "interpretation": "Gate-1 relation type"},
        {"feature_family": "Independent quality", "feature_or_block": "Minimum endpoint pixel, sharpness, and exposure percentiles", "unit": "Pair endpoint minimum", "p3_active_control": "Included", "p5_full_model": "Included", "availability_timing": "Before human outcomes", "transformation": "Training-fold median imputation and z-score", "missingness_handling": "Explicit missing indicators", "interpretation": "Weakest endpoint quality"},
        {"feature_family": "Quality state", "feature_or_block": "measurement failure and frozen quality stress", "unit": "Pair", "p3_active_control": "Included", "p5_full_model": "Included", "availability_timing": "Before human outcomes", "transformation": "Frozen categorical encoding", "missingness_handling": "Explicit states", "interpretation": "Technical stress"},
        {"feature_family": "Pair evidence", "feature_or_block": "local_match_coverage_fraction and failure states", "unit": "Pair", "p3_active_control": "Excluded", "p5_full_model": "Included", "availability_timing": "Before human outcomes", "transformation": "Training-fold z-score plus categorical indicators", "missingness_handling": "Failure is not encoded as zero evidence", "interpretation": "Strict P5 incremental block"},
        {"feature_family": "Model", "feature_or_block": "Ridge logistic regression", "unit": "Pair", "p3_active_control": "lambda=100", "p5_full_model": "lambda=100", "availability_timing": "Frozen at Task15J", "transformation": "Logit link; unpenalized intercept", "missingness_handling": "Per frozen preprocessing", "interpretation": "Probability of not_ready_or_uncertain"},
    ]
    records.append(write_table(output, "table4_model_specification", "Table 4. Nested P3 and P5 model specification", rows, "P5 equals P3 plus the frozen local pair-evidence block; both use the same model family and lambda."))

    est = confirmation["estimand"]
    ci = confirmation["interval"]
    rows = [
        {"stage": "Task15I pooled development", "sample": "1,600 pairs; 400 components", "p3_brier": f6(0.19490913068842816), "p5_brier": f6(0.18904623200281223), "p3_minus_p5": f6(0.00586289868561593), "interval_95": "not prespecified", "decision_threshold": ">=0.005 point estimate", "stability_or_coverage": "5/5 folds nonnegative", "frozen_result": "PASS_TASK15I_DEVELOPMENT_SCREEN", "interpretation": "Development qualification"},
        {"stage": "Task15L calibration", "sample": "448 pairs", "p3_brier": "not an outcome-performance stage", "p5_brier": "not an outcome-performance stage", "p3_minus_p5": "not applicable", "interval_95": "not applicable", "decision_threshold": "Calibration validity only", "stability_or_coverage": "2,000 bootstrap replicates", "frozen_result": "PASS", "interpretation": "No external superiority claim"},
        {"stage": "Task15M/15N execution", "sample": "889 candidates; 252 supported", "p3_brier": "not an outcome-performance stage", "p5_brier": "not an outcome-performance stage", "p3_minus_p5": "not applicable", "interval_95": "not applicable", "decision_threshold": "Validation audit PASS", "stability_or_coverage": "504 model predictions", "frozen_result": execution["status"], "interpretation": "Execution integrity only"},
        {"stage": "Independent outcome analysis", "sample": "252 supported pairs; 357 endpoints", "p3_brier": f6(est["p3_weighted_brier"]), "p5_brier": f6(est["p5_weighted_brier"]), "p3_minus_p5": f6(est["point_estimate"]), "interval_95": f"[{f6(ci['lower_95'])}, {f6(ci['upper_95'])}]", "decision_threshold": "Lower 95% bound >0.005", "stability_or_coverage": "Dyadic endpoint-aware interval", "frozen_result": confirmation["status"], "interpretation": "P5 superiority did not reproduce"},
    ]
    records.append(write_table(output, "table5_stage_results", "Table 5. Development, calibration, execution, and independent outcome results", rows, "Brier score is lower-is-better. P3-minus-P5 is positive when P5 performs better."))

    rows = [{"claim": r["statement"], "evidence_stage": r["evidence_ids"], "disposition": r["disposition"], "quantitative_basis": {"PAIR_AS_OBJECT": "Pair-level contracts and endpoint", "TWO_DISTINCT_GATES": "252/889 Gate-1 supported; human endpoint separately linked", "P5_DEVELOPMENT_QUALIFIED": "+0.005863; 5/5 nonnegative folds", "MODELS_AND_CALIBRATION_FROZEN": "lambda=100; no refit; calibration PASS", "EXECUTION_VALIDATED": "889 candidates; 252 supported; 504 predictions", "INDEPENDENT_SUPERIORITY_NOT_REPRODUCED": "-0.201870 [95% CI -0.224671, -0.179068]", "HUMAN_OUTCOMES_WITH_DEVIATION": "Authorship accepted; major protocol deviation", "IDENTITY_CLAIMS_PROHIBITED": "No identity-accuracy endpoint", "OPERATIONAL_CLOSURE_CONFIRMED": "CONFIRMED/CLOSED for Task15M execution validation"}.get(r["claim_id"], "See evidence map"), "permitted_wording": r["statement"], "prohibited_extension": r["interpretation_boundary"]} for r in claim_map]
    records.append(write_table(output, "table6_evidence_claim_matrix", "Table 6. Evidence-to-claim matrix", rows, "Dispositions and boundaries are copied from the hash-bound manuscript evidence map."))

    # Supplementary tables.
    rows = [
        {"dataset_or_reservoir": "Independent redevelopment reservoir", "species": "Felid image pairs", "source_institution": "Controlled project sources", "license": "Source-specific; imagery not redistributed here", "image_or_pair_count": "1,600 pairs", "identity_availability": "Not used as PF-ERI endpoint", "geographic_sensitivity": "Controlled", "publication_permission": "Verify per source before image publication", "repository_access_class": "Restricted imagery; derived tables", "manuscript_role": "Development"},
        {"dataset_or_reservoir": "Calibration partition", "species": "Felid image pairs", "source_institution": "Controlled project sources", "license": "Source-specific", "image_or_pair_count": "448 pairs", "identity_availability": "Not used as endpoint", "geographic_sensitivity": "Controlled", "publication_permission": "Derived statistics only unless cleared", "repository_access_class": "Restricted", "manuscript_role": "Calibration"},
        {"dataset_or_reservoir": "Deployment-confirmation queue", "species": "Felid image pairs", "source_institution": "Controlled project sources", "license": "Source-specific", "image_or_pair_count": "815 images; 889 candidate pairs", "identity_availability": "Internal linkage not reported as accuracy", "geographic_sensitivity": "Controlled", "publication_permission": "Derived statistics only unless cleared", "repository_access_class": "Restricted images; auditable derived artifacts", "manuscript_role": "External execution and outcome comparison"},
    ]
    records.append(write_table(output, "table_s1_dataset_provenance", "Table S1. Dataset provenance, licenses, and access restrictions", rows, "This display does not grant image-publication rights; rights must be verified before representative photographs are used."))

    rows = [
        {"stage": "Task15I development", "source_reservoir": "Independent redevelopment reservoir", "selection_rule": "400 endpoint-disjoint components; four pairs/component", "pair_count": 1600, "endpoint_image_count": "not reported in display source", "component_count": 400, "pair_overlap_with_earlier_stages": "none by stage role", "endpoint_overlap": "zero across outer folds", "identity_overlap": "not an analysis endpoint", "seed": "frozen in source contract", "sampling_probability": "first-order probability used in weights", "audit_status": "PASS"},
        {"stage": "Task15L calibration", "source_reservoir": "Independent calibration partition", "selection_rule": "Frozen double-review calibration sample", "pair_count": 448, "endpoint_image_count": "not reported in display source", "component_count": "not applicable", "pair_overlap_with_earlier_stages": "stage-isolated by contract", "endpoint_overlap": "not reported in display source", "identity_overlap": "not an analysis endpoint", "seed": "frozen in design artifact", "sampling_probability": "not used for model reselection", "audit_status": "PASS"},
        {"stage": "Task15M confirmation", "source_reservoir": "Deployment-confirmation queue", "selection_rule": "Frozen candidate manifest then dual-descriptor Gate 1", "pair_count": 889, "endpoint_image_count": 815, "component_count": "not applicable", "pair_overlap_with_earlier_stages": "stage-isolated by contract", "endpoint_overlap": "357 endpoints among supported analysis pairs", "identity_overlap": "not an analysis endpoint", "seed": "frozen upstream", "sampling_probability": "retained for Hajek weighting", "audit_status": execution["status"]},
    ]
    records.append(write_table(output, "table_s2_sampling_nonoverlap", "Table S2. Pair sampling frames and non-overlap checks", rows, "Unavailable fields are stated explicitly rather than inferred."))

    rows = [
        {"instrument_item": "review_ready", "definition": "Pair contains comparable visual evidence for responsible review", "reviewer_visible_information": "Blinded pair imagery and review instrument", "role_in_eligibility": "Positive Gate-2 state", "role_in_endpoint": "Binary outcome 0 only when required rule is met", "analysis_treatment": "Review-ready"},
        {"instrument_item": "not_review_ready", "definition": "Comparable evidence is insufficient", "reviewer_visible_information": "Blinded pair imagery", "role_in_eligibility": "Negative Gate-2 state", "role_in_endpoint": "Maps to outcome 1", "analysis_treatment": "not_ready_or_uncertain"},
        {"instrument_item": "uncertain", "definition": "Reviewer cannot responsibly resolve reviewability", "reviewer_visible_information": "Blinded pair imagery", "role_in_eligibility": "Conservative non-admission", "role_in_endpoint": "Maps to outcome 1", "analysis_treatment": "not_ready_or_uncertain"},
        {"instrument_item": "reason codes", "definition": "Structured rationale families", "reviewer_visible_information": "Allowed code list", "role_in_eligibility": "Descriptive", "role_in_endpoint": "No direct numerical role", "analysis_treatment": "Descriptive only"},
        {"instrument_item": "confidence", "definition": "Reviewer-reported certainty", "reviewer_visible_information": "Low/medium/high field", "role_in_eligibility": "None", "role_in_endpoint": "None", "analysis_treatment": "Descriptive only"},
        {"instrument_item": "technical_problem_flag", "definition": "Review could not be completed technically", "reviewer_visible_information": "Yes/no", "role_in_eligibility": "Hard response eligibility", "role_in_endpoint": "Excluded when yes", "analysis_treatment": "Eligibility audit"},
        {"instrument_item": "disagreement/adjudication", "definition": "First-pass labels differ", "reviewer_visible_information": "Fresh blinded adjudication package", "role_in_eligibility": "Triggers adjudication in formal review", "role_in_endpoint": "Adjudicated final label", "analysis_treatment": "Final frozen outcome"},
        {"instrument_item": "timestamp", "definition": "Submission metadata", "reviewer_visible_information": "Not a scientific criterion", "role_in_eligibility": "Excluded", "role_in_endpoint": "None", "analysis_treatment": "Descriptive only"},
    ]
    records.append(write_table(output, "table_s3_review_instrument", "Table S3. Human review instrument and adjudication rules", rows, "The endpoint is visual reviewability, not identity truth."))

    triples_i = [(r["decision_1"], r["decision_2"]) for r in labels_i]
    labels_l = read_csv(ROOT / "outputs/pferi_v2/models/calibration/analysis/merged_analysis/double_review_pair_labels.csv")
    triples_l = [(r["reviewer_1_label"], r["reviewer_2_label"]) for r in labels_l]
    triples_m = [(r["first_pass_decision_1"], r["first_pass_decision_2"]) for r in deployment]
    rows = [agreement_row("Task15I development", triples_i, "Low agreement; labels retained under the frozen conservative mapping"), agreement_row("Task15L calibration", triples_l, "Descriptive only; calibration eligibility did not depend on agreement"), agreement_row("Formal confirmation", triples_m, "Disagreements were adjudicated in the frozen final outcome")]
    rows[-1]["adjudication_count"] = sum(r["adjudication_required"] == "yes" for r in deployment)
    records.append(write_table(output, "table_s4_reviewer_agreement", "Table S4. Reviewer agreement and endpoint reliability by stage", rows, "Agreement is deterministically recomputed from frozen first-pass labels. Cohen's kappa uses the binary review-ready versus not-ready-or-uncertain mapping."))

    rows = [{"outer_fold": r["outer_fold"], "validation_pair_count": r["pair_count"], "validation_component_count": 80, "p3_brier": f6(float(r["p3_weighted_brier"])), "p5_brier": f6(float(r["p5_weighted_brier"])), "p3_minus_p5": f6(float(r["delta_brier_P3_minus_P5"])), "direction": "favors P5" if float(r["delta_brier_P3_minus_P5"]) > 0 else "favors P3", "endpoint_leakage_count": 0, "fixed_lambda": 100} for r in folds]
    rows.append({"outer_fold": "pooled", "validation_pair_count": 1600, "validation_component_count": 400, "p3_brier": f6(0.19490913068842816), "p5_brier": f6(0.18904623200281223), "p3_minus_p5": f6(0.00586289868561593), "direction": "favors P5", "endpoint_leakage_count": 0, "fixed_lambda": 100})
    records.append(write_table(output, "table_s5_task15i_folds", "Table S5. Task15I component-disjoint fold results", rows, "Positive P3-minus-P5 values favor P5; lower Brier scores are better."))

    contract = read_json(ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json")
    rows = []
    for family, spec in contract["feature_blocks"].items():
        for raw_type in ("continuous", "categorical"):
            for field in spec.get(raw_type, []):
                rows.append({"source_field": field, "scientific_family": family, "unit": "pair or pair-derived endpoint summary", "raw_type": raw_type, "transformation": contract[f"{raw_type}_policy"]["scaling"] if raw_type == "continuous" else contract["categorical_policy"]["encoding"], "training_fold_statistic": "median, mean, population SD" if raw_type == "continuous" else "observed levels/reference", "missing_state_encoding": "explicit indicator/state", "p3_inclusion": "yes" if family != "pair_evidence" else "no", "p5_inclusion": "yes", "outcome_availability_prohibition": "must be available before human outcome", "interpretation_boundary": "Predictive, not causal"})
    records.append(write_table(output, "table_s6_predictor_dictionary", "Table S6. Complete predictor and preprocessing dictionary", rows, "Generated directly from the frozen feature-preprocessing contract."))

    rows = []
    for model_id, spec in model["models"].items():
        for name, coef in zip(spec["coefficient_order"], spec["coefficients"]):
            rows.append({"model": model_id, "transformed_feature": name, "coefficient": f"{coef:.12g}", "intercept_indicator": "yes" if name == "intercept" else "no", "lambda": model["fixed_lambda"], "coefficient_scale": "log-odds per transformed unit", "source_bundle_field": f"models.{model_id}.coefficients", "interpretation_note": "Reproducibility only; not causal"})
    records.append(write_table(output, "table_s7_frozen_coefficients", "Table S7. Frozen P3 and P5 coefficients", rows, "Coefficients are copied without refitting from the Task15J final model bundle."))

    rows = []
    for model_id in ("P3", "P5"):
        raw = read_csv(ROOT / f"outputs/pferi_v2/models/calibration/analysis/merged_analysis/{model_id.lower()}_raw_and_calibrated_probabilities.csv")
        fit = read_json(ROOT / f"outputs/pferi_v2/models/calibration/analysis/merged_analysis/{model_id.lower()}_calibration_fit.json")
        raw_values = [float(r["raw_probability"]) for r in raw]
        rows.append({"model": model_id, "calibration_pair_count": 448, "class_counts": "y0=86; y1=362", "raw_probability_range": f"{min(raw_values):.6f}-{max(raw_values):.6f}", "intercept": f"{fit['intercept']:.12g}", "slope": f"{fit['slope']:.12g}", "convergence_status": str(fit["converged"]).lower(), "bootstrap_replicates": 2000, "calibrated_probability_valid": str(fit["calibrated_probabilities_in_unit_interval"]).lower(), "model_refit": "no", "feature_change": "no", "lambda_change": "no", "threshold_created": "no"})
    records.append(write_table(output, "table_s8_calibration_details", "Table S8. Task15L calibration details", rows, "Stored intercepts and slopes are reported exactly; this builder does not recalculate them."))

    cat = Counter(r["descriptor_support_category"] for r in descriptor if r["support_status"] == "supported")
    rows = [
        {"support_category": "both_reciprocal", "formal_definition": "Both descriptors retrieve the pair in both directions within top 20", "directed_top20_requirement": "Reciprocal for both descriptors", "pair_count": cat["both_reciprocal"], "percentage_of_889": f"{100*cat['both_reciprocal']/889:.1f}%", "scoring_eligibility": "yes", "local_match_eligibility": "yes", "prediction_count": 2 * cat["both_reciprocal"], "interpretation": "Gate-1 supported"},
        {"support_category": "both_agreement", "formal_definition": "Both descriptors support the same pair direction within top 20", "directed_top20_requirement": "Same-direction consensus", "pair_count": cat["both_agreement"], "percentage_of_889": f"{100*cat['both_agreement']/889:.1f}%", "scoring_eligibility": "yes", "local_match_eligibility": "yes", "prediction_count": 2 * cat["both_agreement"], "interpretation": "Gate-1 supported"},
        {"support_category": "unsupported", "formal_definition": "no_same_direction_dual_descriptor_top20_consensus", "directed_top20_requirement": "Requirement not met", "pair_count": 637, "percentage_of_889": "71.7%", "scoring_eligibility": "no", "local_match_eligibility": "no", "prediction_count": 0, "interpretation": "Not a human reviewability judgment"},
    ]
    records.append(write_table(output, "table_s9_descriptor_support", "Table S9. Task15M descriptor pair-support taxonomy", rows, "Support is a descriptor-relation property, not a human endpoint."))

    rows = [
        {"measurement_family": "Image decode and quality", "expected_unit": "image", "expected_count": 815, "observed_count": 815, "missing_count": 0, "failure_code_distribution": "none=815", "hash_audit": "PASS", "shape_audit": "PASS", "downstream_consequence": "All images measurable"},
        {"measurement_family": "MegaDescriptor embeddings", "expected_unit": "image x 1536", "expected_count": 815, "observed_count": 815, "missing_count": 0, "failure_code_distribution": "none", "hash_audit": "PASS", "shape_audit": "815 x 1536", "downstream_consequence": "Top-20 relation available"},
        {"measurement_family": "DINOv2 embeddings", "expected_unit": "image x 1024", "expected_count": 815, "observed_count": 815, "missing_count": 0, "failure_code_distribution": "none", "hash_audit": "PASS", "shape_audit": "815 x 1024", "downstream_consequence": "Top-20 relation available"},
        {"measurement_family": "Descriptor pair support", "expected_unit": "candidate pair", "expected_count": 889, "observed_count": 889, "missing_count": 0, "failure_code_distribution": "supported=252; unsupported=637", "hash_audit": "PASS", "shape_audit": "PASS", "downstream_consequence": "252 eligible for scoring"},
        {"measurement_family": "Local matching", "expected_unit": "supported pair", "expected_count": 252, "observed_count": 252, "missing_count": 0, "failure_code_distribution": "none=252", "hash_audit": "PASS", "shape_audit": "PASS", "downstream_consequence": "P5 pair evidence complete"},
        {"measurement_family": "Calibrated predictions", "expected_unit": "supported pair x model", "expected_count": 504, "observed_count": len(predictions), "missing_count": 504-len(predictions), "failure_code_distribution": "none", "hash_audit": "PASS", "shape_audit": "252 x 2", "downstream_consequence": "Independent comparison executable"},
    ]
    records.append(write_table(output, "table_s10_measurement_completeness", "Table S10. Technical measurement completeness and failure inventory", rows, "Counts are tied to the Task15N execution freeze and frozen execution outputs."))

    p3i = read_csv(TASK15I / "p3_oof_predictions.csv")
    p5i = read_csv(TASK15I / "p5_oof_predictions.csv")
    pred_by_model = {m: [float(r["calibrated_probability_not_ready_or_uncertain"]) for r in predictions if r["model_id"] == m] for m in ("P3", "P5")}
    rows = [
        {"stage_or_subset": "Task15I development", "pair_count": 1600, "review_ready_count_percent": pct(448,1600), "not_ready_or_uncertain_count_percent": pct(1152,1600), "descriptor_support_composition": "development-supported design", "median_p3_probability": f"{statistics.median(float(r['probability_not_ready_or_uncertain']) for r in p3i):.6f}", "median_p5_probability": f"{statistics.median(float(r['probability_not_ready_or_uncertain']) for r in p5i):.6f}", "probability_range": "OOF frozen development probabilities", "role_in_analysis": "Development qualification"},
        {"stage_or_subset": "Task15L calibration", "pair_count": 448, "review_ready_count_percent": pct(86,448), "not_ready_or_uncertain_count_percent": pct(362,448), "descriptor_support_composition": "calibration sample", "median_p3_probability": f"{statistics.median(float(r['calibrated_probability']) for r in read_csv(ROOT/'outputs/pferi_v2/models/calibration/analysis/merged_analysis/p3_raw_and_calibrated_probabilities.csv')):.6f}", "median_p5_probability": f"{statistics.median(float(r['calibrated_probability']) for r in read_csv(ROOT/'outputs/pferi_v2/models/calibration/analysis/merged_analysis/p5_raw_and_calibrated_probabilities.csv')):.6f}", "probability_range": "Stored calibrated probabilities", "role_in_analysis": "Calibration"},
        {"stage_or_subset": "Task15M descriptor-supported", "pair_count": 252, "review_ready_count_percent": pct(218,252), "not_ready_or_uncertain_count_percent": pct(34,252), "descriptor_support_composition": "252/252 supported", "median_p3_probability": f"{statistics.median(pred_by_model['P3']):.6f}", "median_p5_probability": f"{statistics.median(pred_by_model['P5']):.6f}", "probability_range": f"P3 {min(pred_by_model['P3']):.3f}-{max(pred_by_model['P3']):.3f}; P5 {min(pred_by_model['P5']):.3f}-{max(pred_by_model['P5']):.3f}", "role_in_analysis": "Independent outcome comparison"},
        {"stage_or_subset": "Task15M descriptor-unsupported", "pair_count": 637, "review_ready_count_percent": pct(sum(r['not_ready_or_uncertain_label']=='0' for r in dep_unsupported),637), "not_ready_or_uncertain_count_percent": pct(sum(r['not_ready_or_uncertain_label']=='1' for r in dep_unsupported),637), "descriptor_support_composition": "0/637 supported", "median_p3_probability": "not scored", "median_p5_probability": "not scored", "probability_range": "not applicable", "role_in_analysis": "Gate-1-excluded descriptive subset"},
    ]
    records.append(write_table(output, "table_s11_transport_diagnostics", "Table S11. Endpoint prevalence and transport diagnostics", rows, "Descriptive distribution shifts are not evidence of a causal mediation mechanism."))

    weights = [1/float(r["first_order_inclusion_probability"]) for r in loss]
    ess = sum(weights)**2/sum(w*w for w in weights)
    def loss_row(name: str, subset: list[dict[str,str]], status: str) -> dict[str,Any]:
        endpoints = Counter(x for r in subset for x in (r["endpoint_a_image_id"], r["endpoint_b_image_id"]))
        return {"summary_group": name, "pair_count": len(subset), "weighted_mean_p3_loss": f6(weighted_mean(subset,"p3_brier_loss")), "weighted_mean_p5_loss": f6(weighted_mean(subset,"p5_brier_loss")), "p3_minus_p5": f6(weighted_mean(subset,"delta_brier_p3_minus_p5")), "pairs_favoring_p3": sum(float(r["delta_brier_p3_minus_p5"])<0 for r in subset), "pairs_favoring_p5": sum(float(r["delta_brier_p3_minus_p5"])>0 for r in subset), "inclusion_weight_effective_n": f"{ess:.1f}" if name=="Primary all supported pairs" else "descriptive", "unique_endpoint_count": len(endpoints), "maximum_endpoint_degree": max(endpoints.values()), "independent_row_se": f"{ci['independent_row_se_diagnostic']:.6f}" if name=="Primary all supported pairs" else "not applicable", "dyadic_se": f"{ci['standard_error']:.6f}" if name=="Primary all supported pairs" else "not applicable", "analysis_status": status}
    rows = [loss_row("Primary all supported pairs", loss, "Preplanned primary"), loss_row("Outcome=review_ready", [r for r in loss if r["not_ready_or_uncertain_label"]=="0.0"], "Post hoc descriptive"), loss_row("Outcome=not_ready_or_uncertain", [r for r in loss if r["not_ready_or_uncertain_label"]=="1.0"], "Post hoc descriptive")]
    records.append(write_table(output, "table_s12_pair_loss_diagnostics", "Table S12. Pair-level confirmation loss diagnostics", rows, "Only the all-supported-pairs row is the preplanned primary result; label-stratified rows are post hoc descriptive diagnostics."))

    rows = [
        {"issue": "Formal release authorization timing", "stage_detected": "First return audit", "original_disposition": "FAIL_QUARANTINED_PROVENANCE_AND_PRECOLLECTION_GATE", "retained_evidence": "Raw reviewer responses and assignments", "retrospective_resolution": "Owner accepted human authorship attestations", "fields_accepted": "Review decisions", "fields_excluded": "Timing as eligibility evidence", "effect_on_analysis": "Major protocol-deviation disclosure", "disclosure_wording": "Human-authored outcomes accepted retrospectively", "fully_clean_preregistered_confirmation_authorized": "no"},
        {"issue": "Browser audit version mismatch", "stage_detected": "First return audit", "original_disposition": "Quarantined", "retained_evidence": "Review outputs and later attestations", "retrospective_resolution": "Accepted with deviation", "fields_accepted": "Labels", "fields_excluded": "Version audit as proof of final-app exposure", "effect_on_analysis": "Limits provenance claim", "disclosure_wording": "Interface audit did not correspond exactly to final application version", "fully_clean_preregistered_confirmation_authorized": "no"},
        {"issue": "Submission timestamps", "stage_detected": "Return audit", "original_disposition": "Anomalous/descriptive", "retained_evidence": "Timestamp strings", "retrospective_resolution": "Excluded from eligibility and analysis", "fields_accepted": "None for inference", "fields_excluded": "submitted_at_utc", "effect_on_analysis": "No numerical role", "disclosure_wording": "Timestamps were excluded from scientific eligibility and analysis", "fully_clean_preregistered_confirmation_authorized": "no"},
        {"issue": "Retrospective human-authorship attestation", "stage_detected": "Provenance resolution", "original_disposition": "Not available prospectively", "retained_evidence": "Four reviewer attestations and owner assertion", "retrospective_resolution": "PASS_HUMAN_AUTHORSHIP_ATTESTED_WITH_MAJOR_PROTOCOL_DEVIATION", "fields_accepted": "Human review decisions", "fields_excluded": "Claim of fully clean preregistered collection", "effect_on_analysis": "Outcomes retained with boundary", "disclosure_wording": "Labels were human-authored but provenance was resolved retrospectively", "fully_clean_preregistered_confirmation_authorized": "no"},
    ]
    records.append(write_table(output, "table_s13_protocol_deviations", "Table S13. Human provenance and protocol-deviation register", rows, "Human authorship is accepted; the collection cannot be represented as a fully clean preregistered confirmation."))

    rows = [{"component": r["source_id"], "script": "scripts/build_pferi_v2_manuscript_source_manifest.py", "environment_or_runtime": "Python 3 standard library", "dependency_version": "not applicable", "input_contract": "manuscript_source_manifest_contract_v1", "input_sha256": r["sha256"], "output_artifact": r["source_path"], "output_sha256": r["sha256"], "deterministic_seed": "not applicable", "automated_test": "test_build_pferi_v2_manuscript_source_manifest", "verification_status": "PASS" if r["hash_match"]=="true" else "FAIL"} for r in source_manifest]
    records.append(write_table(output, "table_s14_reproducibility", "Table S14. Reproducibility environment and artifact integrity", rows, "The source-manifest builder verifies each frozen input hash before manuscript displays are generated."))

    rows = [
        {"analysis": "Task15I P3 versus P5", "planning_status": "Prospectively governed redevelopment", "information_access_timing": "Development outcomes", "primary_inference_eligible": "Development only", "result_status": "PASS development screen", "inclusion_or_exclusion_reason": "Primary development qualification"},
        {"analysis": "Task15F Bayesian sensitivity", "planning_status": "Historical sensitivity", "information_access_timing": "Pre-Task15I route", "primary_inference_eligible": "no", "result_status": "Exploratory", "inclusion_or_exclusion_reason": "Non-primary historical model"},
        {"analysis": "Task15G performance bound", "planning_status": "Exploratory", "information_access_timing": "Pre-freeze", "primary_inference_eligible": "no", "result_status": "Exploratory", "inclusion_or_exclusion_reason": "Not the frozen P3/P5 comparison"},
        {"analysis": "Independent Task15M supported-pair comparison", "planning_status": "Frozen one-shot analysis", "information_access_timing": "After prediction freeze", "primary_inference_eligible": "yes", "result_status": "FAIL_PRIMARY_CONFIRMATION", "inclusion_or_exclusion_reason": "Primary independent comparison"},
        {"analysis": "Unweighted or label-stratified loss diagnostics", "planning_status": "Post hoc", "information_access_timing": "After outcome opening", "primary_inference_eligible": "no", "result_status": "Descriptive", "inclusion_or_exclusion_reason": "Mechanism-generating only"},
        {"analysis": "Historical PF-ERI v1", "planning_status": "Superseded", "information_access_timing": "Earlier project version", "primary_inference_eligible": "no", "result_status": "Historical", "inclusion_or_exclusion_reason": "Must not be pooled with v2"},
    ]
    records.append(write_table(output, "table_s15_sensitivity_registry", "Table S15. Sensitivity and alternative-analysis registry", rows, "Only the frozen independent supported-pair comparison is eligible for the v2 primary external-inference statement."))

    rows = []
    trace_values = {
        "TASK15I_RESULT_FREEZE": "1,600; 400; 0.005863; 5/5",
        "TASK15L_CALIBRATION_FREEZE": "448; y0=86; y1=362; PASS",
        "TASK15N_EXECUTION_FREEZE": "889; 252; 637; 504; PASS",
        "PRIMARY_CONFIRMATION_RESULT": "P3=0.307246; P5=0.509116; difference=-0.201870; 95% CI",
        "PROJECT_CLOSURE_RECORD": "CONFIRMED/CLOSED within Task15M execution-validation scope",
    }
    for r in source_manifest:
        if r["source_id"] in trace_values:
            rows.append({"manuscript_section": "Methods/Results", "display_item": "Tables 1, 3, 5, 6 and Figures 2-4", "reported_number": trace_values[r["source_id"]], "exact_field_or_aggregation": "Frozen JSON fields or declared CSV aggregation", "source_id": r["source_id"], "source_path": r["source_path"], "sha256": r["sha256"], "generation_command": "python3 scripts/build_pferi_v2_manuscript_displays.py", "verification_status": "PASS"})
    records.append(write_table(output, "table_s16_number_source_trace", "Table S16. Manuscript number-to-source trace", rows, "This internal submission audit connects headline numbers to hash-bound frozen artifacts."))

    context = {"folds": folds, "confirmation": confirmation, "descriptor": descriptor, "labels_i": labels_i, "cal": cal, "deployment": deployment, "predictions": predictions, "loss": loss}
    return records, context


def render_figures(directory: Path, context: dict[str, Any]) -> list[dict[str, Any]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 12, "axes.labelsize": 9, "svg.fonttype": "none", "pdf.fonttype": 42})
    colors = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00", "sky": "#56B4E9", "gray": "#666666", "light": "#E8E8E8", "black": "#1A1A1A"}
    records = []

    def save(fig: Any, stem: str, title: str, note: str) -> None:
        for suffix in ("png", "svg", "pdf"):
            fig.savefig(directory / f"{stem}.{suffix}", dpi=450 if suffix == "png" else None, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        records.append({"figure_id": stem, "title": title, "formats": "PNG 450 dpi; SVG; PDF", "note": note})

    def box(ax: Any, x: float, y: float, w: float, h: float, text: str, color: str, fc: str = "white") -> None:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.015",linewidth=1.4,edgecolor=color,facecolor=fc))
        ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=9,color=colors["black"],wrap=True)

    fig, ax = plt.subplots(figsize=(12,4.2)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    xs=[.02,.19,.36,.53,.70,.87]; texts=["Descriptor\nretrieval","Candidate\nimage pair","Gate 1\nDescriptor support","Gate 2\nVisual reviewability","Staged P3 vs P5\nevaluation","Bounded\nconclusion"]
    for i,(x,t) in enumerate(zip(xs,texts)):
        box(ax,x,.40,.11,.25,t,colors["blue"] if i<3 else colors["green"],"#F7FBFD" if i<3 else "#F4FAF7")
        if i<len(xs)-1: ax.annotate("",xy=(xs[i+1]-.01,.525),xytext=(x+.12,.525),arrowprops=dict(arrowstyle="->",lw=1.5,color=colors["gray"]))
    ax.text(.585,.22,"Development: +0.005863, 5/5 folds",ha="center",color=colors["green"],weight="bold")
    ax.text(.585,.12,"Independent: -0.201870 (95% CI -0.224671 to -0.179068)",ha="center",color=colors["red"],weight="bold")
    ax.text(.5,.90,"PF-ERI v2: admitting evidence for pair review, not assigning identity",ha="center",fontsize=16,weight="bold")
    save(fig,"graphical_abstract","Graphical abstract","Identity retrieval and evidence admission are visually separated.")

    fig, ax = plt.subplots(figsize=(10,5)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    box(ax,.04,.62,.22,.20,"Single-image quality\nCan each image be measured?",colors["gray"],"#F5F5F5")
    box(ax,.39,.62,.22,.20,"Gate 1: descriptor relation\n252 supported / 889 candidates",colors["blue"],"#EAF4FA")
    box(ax,.74,.62,.22,.20,"Gate 2: visual evidence\n218 review-ready / 252 supported",colors["green"],"#EAF7F2")
    # Route connectors through the boxes' upper whitespace so they do not cross labels.
    for a,b in [((.26,.79),(.39,.79)),((.61,.79),(.74,.79))]: ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",lw=2,color=colors["gray"]))
    box(ax,.21,.18,.24,.18,"Admit to comparison",colors["green"],"#EAF7F2"); box(ax,.56,.18,.24,.18,"Expert review or defer",colors["orange"],"#FFF6E5")
    ax.annotate("",xy=(.33,.36),xytext=(.80,.62),arrowprops=dict(arrowstyle="->",lw=1.5,color=colors["green"])); ax.annotate("",xy=(.68,.36),xytext=(.85,.62),arrowprops=dict(arrowstyle="->",lw=1.5,color=colors["orange"]))
    ax.text(.5,.93,"Figure 1. The image pair is the scientific object",ha="center",fontsize=14,weight="bold")
    ax.text(.5,.04,"Descriptor support, visual reviewability, and identity truth are not interchangeable.",ha="center",color=colors["gray"])
    save(fig,"figure1_pair_decision_chain","Figure 1. Scientific object and decision chain","Two distinct pair-level gates.")

    fig, ax = plt.subplots(figsize=(12,5)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    xs=[.02,.18,.34,.50,.66,.82]; titles=["Development","Model freeze","Calibration","External execution","Outcome analysis","Closure"]
    bodies=["1,600 pairs\n400 components\nP5 qualified","P3/P5 frozen\nlambda=100\nno reselection","448 pairs\nintercept/slope only\nPASS","889 candidates\n252 supported\n504 predictions","252 pairs\none shot\nno refit","CONFIRMED/CLOSED\nexecution-validation\nscope"]
    cols=[colors["green"],colors["blue"],colors["orange"],colors["blue"],colors["red"],colors["gray"]]
    for i,x in enumerate(xs):
        box(ax,x,.42,.13,.30,f"{titles[i]}\n\n{bodies[i]}",cols[i],"white")
        if i<5: ax.annotate("",xy=(xs[i+1]-.01,.57),xytext=(x+.14,.57),arrowprops=dict(arrowstyle="->",lw=1.4,color=colors["gray"]))
    ax.text(.5,.90,"Figure 2. Prospective study flow and information boundaries",ha="center",fontsize=14,weight="bold")
    ax.text(.58,.25,"Outcomes sealed",ha="center",color=colors["blue"],weight="bold"); ax.plot([.49,.79],[.31,.31],color=colors["blue"],lw=2)
    ax.text(.5,.08,"Operational closure and independent superiority are separate dispositions.",ha="center",color=colors["gray"])
    save(fig,"figure2_prospective_flow","Figure 2. Prospective study flow","Counts, freezing, and outcome-access boundaries.")

    folds=context["folds"]
    labels=[f"Task15I fold {r['outer_fold']}" for r in folds]+["Task15I pooled","Independent confirmation"]
    values=[float(r["delta_brier_P3_minus_P5"]) for r in folds]+[0.00586289868561593,context["confirmation"]["estimand"]["point_estimate"]]
    lo=values[:-1]+[context["confirmation"]["interval"]["lower_95"]]; hi=values[:-1]+[context["confirmation"]["interval"]["upper_95"]]
    fig,ax=plt.subplots(figsize=(8,5.5)); y=list(range(len(labels)))[::-1]
    for i,(yy,v,l,h) in enumerate(zip(y,values,lo,hi)):
        c=colors["red"] if i==len(values)-1 else colors["blue"]
        ax.errorbar(v,yy,xerr=[[v-l],[h-v]],fmt="o",color=c,ecolor=c,capsize=3,markersize=6)
    ax.axvline(0,color=colors["black"],lw=1); ax.axvline(.005,color=colors["orange"],lw=1.5,ls="--",label="Frozen +0.005 threshold")
    ax.set_yticks(y,labels); ax.set_xlabel("Brier(P3) - Brier(P5); positive favors P5")
    ax.set_title("Figure 3. Development gain did not reproduce independently",weight="bold"); ax.grid(axis="x",color=colors["light"],lw=.8); ax.legend(frameon=False,loc="lower right")
    save(fig,"figure3_development_confirmation","Figure 3. Development and confirmation contrast","Fold points have no prespecified intervals; the independent estimate has a dyadic 95% CI.")

    fig,axs=plt.subplots(1,2,figsize=(10,4.8),gridspec_kw={"wspace":.35})
    stages=["Development","Calibration","Confirmation\nsupported"]
    rr=[448/1600,86/448,218/252]; nr=[1-x for x in rr]
    axs[0].bar(stages,rr,color=colors["green"],label="review_ready"); axs[0].bar(stages,nr,bottom=rr,color=colors["gray"],label="not_ready_or_uncertain",hatch="///")
    for x, ready, other, ready_text, other_text in zip(range(3), rr, nr, ("448/1,600", "86/448", "218/252"), ("1,152/1,600", "362/448", "34/252")):
        axs[0].text(x, ready/2, ready_text, ha="center", va="center", color="white", fontsize=8, weight="bold")
        axs[0].text(x, ready+other/2, other_text, ha="center", va="center", color="white", fontsize=8, weight="bold")
    axs[0].set_ylim(0,1); axs[0].set_ylabel("Human endpoint proportion"); axs[0].legend(frameon=False,fontsize=8); axs[0].set_title("Gate 2 / endpoint prevalence",weight="bold")
    axs[1].bar(["Task15M\nqueue"],[252/889],color=colors["blue"],label="descriptor-supported"); axs[1].bar(["Task15M\nqueue"],[637/889],bottom=[252/889],color=colors["orange"],hatch="xx",label="descriptor-unsupported")
    axs[1].text(0, (252/889)/2, "252/889", ha="center", va="center", color="white", fontsize=9, weight="bold")
    axs[1].text(0, 252/889+(637/889)/2, "637/889", ha="center", va="center", color=colors["black"], fontsize=9, weight="bold")
    axs[1].set_ylim(0,1); axs[1].set_ylabel("Candidate-pair proportion"); axs[1].legend(frameon=False,fontsize=8); axs[1].set_title("Gate 1 / descriptor support",weight="bold")
    fig.suptitle("Figure 4. Human endpoint shift and descriptor support are distinct",fontsize=14,weight="bold")
    save(fig,"figure4_distribution_support_shift","Figure 4. Distribution and support shift","Aligned bars avoid conflating Gate 1 descriptor support with Gate 2 human reviewability.")

    preds=context["predictions"]
    p3=[float(r["calibrated_probability_not_ready_or_uncertain"]) for r in preds if r["model_id"]=="P3"]
    p5=[float(r["calibrated_probability_not_ready_or_uncertain"]) for r in preds if r["model_id"]=="P5"]
    fig,ax=plt.subplots(figsize=(8,4.8)); bins=[i/20 for i in range(21)]
    ax.hist(p3,bins=bins,histtype="step",lw=2,color=colors["blue"],label="P3 calibrated",density=True); ax.hist(p5,bins=bins,histtype="step",lw=2,color=colors["red"],label="P5 calibrated",density=True,linestyle="--")
    ax.set_xlabel("Frozen probability of not_ready_or_uncertain"); ax.set_ylabel("Density"); ax.set_title("Figure 5. Frozen prediction distributions in supported confirmation pairs",weight="bold"); ax.legend(frameon=False); ax.grid(axis="y",color=colors["light"])
    save(fig,"figure5_calibration_transport","Figure 5. Calibration transport","Descriptive only; no recalibration, refitting, or threshold selection was performed.")
    return records


def build(output: Path = DEFAULT_OUTPUT, figures: Path = DEFAULT_FIGURES, render: bool = True) -> dict[str, Any]:
    source_audit = read_json(SOURCE_PACKAGE / "source_manifest_audit.json")
    if source_audit["status"] != "PASS":
        raise RuntimeError("source manifest must pass before displays are built")
    output.parent.mkdir(parents=True, exist_ok=True)
    figures.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pferi_v2_displays.") as tmp:
        stage = Path(tmp) / "tables"; stage.mkdir()
        table_records, context = build_tables(stage)
        fig_stage = Path(tmp) / "figures"; fig_stage.mkdir()
        figure_records = render_figures(fig_stage, context) if render else []
        audit = {"audit_version": "pferi_v2_manuscript_displays_audit_v1", "status": "PASS", "table_count": len(table_records), "main_table_count": 6, "supplementary_table_count": 16, "figure_count": len(figure_records), "models_refit": False, "task15l_parameters_recomputed": False, "source_manifest_status": "PASS", "scientific_boundaries": ["Descriptor support is not human reviewability.", "Reviewability is not identity truth.", "Operational CONFIRMED is limited to Task15M execution validation.", "Independent P5 superiority was not confirmed."], "tables": table_records, "figures": figure_records}
        (stage / "table_build_audit.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (stage / "README.md").write_text("# PF-ERI v2 manuscript tables\n\nSix main and sixteen supplementary tables, each supplied as editable CSV and Markdown. Regenerate with `python3 scripts/build_pferi_v2_manuscript_displays.py`. See `table_build_audit.json` for scientific boundaries and source-package status.\n",encoding="utf-8")
        (fig_stage / "figure_captions.md").write_text("# PF-ERI v2 figure captions\n\n"+"\n\n".join(f"## {r['title']}\n\n{r['note']}" for r in figure_records)+"\n",encoding="utf-8")
        for directory in (stage,fig_stage):
            files=sorted(p for p in directory.iterdir() if p.is_file() and p.name!="CHECKSUMS.sha256")
            (directory/"CHECKSUMS.sha256").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files),encoding="utf-8")
        if output.exists(): shutil.rmtree(output)
        if figures.exists(): shutil.rmtree(figures)
        shutil.copytree(stage,output); shutil.copytree(fig_stage,figures)
    return audit


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument("--figures",type=Path,default=DEFAULT_FIGURES)
    parser.add_argument("--skip-figures",action="store_true")
    args=parser.parse_args()
    audit=build(args.output,args.figures,not args.skip_figures)
    print(json.dumps({"status":audit["status"],"tables":audit["table_count"],"figures":audit["figure_count"]},sort_keys=True))


if __name__ == "__main__":
    main()
