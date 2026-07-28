#!/usr/bin/env python3
"""Remove explicitly superseded artifacts after writing a SHA-256 manifest.

The command is a dry run unless ``--apply`` is supplied. Final scientific results,
audits, final freezes, response logs, human annotation history, and current extracted
execution packages are outside this allowlist and are never deleted implicitly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/project-governance/structure/2026-07-17_output_cleanup_manifest.csv"


@dataclass(frozen=True)
class CleanupTarget:
    path: str
    reason: str
    retained_path: str
    expected_sha256: str | None = None
    retained_must_match: bool = False


TARGETS = (
    CleanupTarget(
        ".venv",
        "incomplete local virtual environment without a Python executable; it cannot reproduce an execution environment",
        "README.md",
    ),
    CleanupTarget(
        "tmp/pdfs/original_plan",
        "temporary PDF page renders and extraction report",
        "docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase11/phase11_pair_level_pf_eri_table.csv",
        "rebuildable historical Phase11 training intermediate; summaries and audits are retained",
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase11/phase11_pair_level_pf_eri_score_summary.csv",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase12/phase12_pair_candidate_analysis_table.csv",
        "rebuildable historical Phase12 candidate intermediate; summaries and audits are retained",
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase12/phase12_pair_candidate_analysis_summary.csv",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase13/learned_candidate_utility/phase13_candidate_utility_training_table.csv",
        "rebuildable historical Phase13 model-training intermediate; model results, summaries, and audits are retained",
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase13/learned_candidate_utility/phase13_calibrated_utility_model_results.csv",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase13/rq4_training_control_manifest/phase13c_rq4_pair_training_control_manifest.csv",
        "rebuildable historical Phase13 RQ4 training-control intermediate; role, comparison, summary, and audit files are retained",
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase13/rq4_training_control_manifest/phase13c_rq4_training_control_manifest_summary.md",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/current_structural_oracle_reliability_audit.json",
        "superseded reliability audit from the removed current analyzer",
        "work/pferi_v2/gpu/measurement_feasibility/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/kaggle_legacy-code18_strong_baseline_input_20260702.zip",
        "superseded v1 transfer package; returned baseline results and audits are retained",
        "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/returned_strong_baselines",
    ),
    CleanupTarget(
        "archive/pferi_v2/task_runs/PF_ERI_V2_KAGGLE_RAW_ARCHIVES/v2_czechlynx_fresh_descriptor_images.zip.bin",
        "byte-identical transport suffix copy",
        "work/pferi_v2/descriptor_execution_package",
    ),
    CleanupTarget(
        "archive/pferi_v2/task_runs/PF_ERI_V2_KAGGLE_RAW_ARCHIVES/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip.bin",
        "byte-identical transport suffix copy",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
    ),
    CleanupTarget(
        "archive/pferi_v2/task_runs/v2_czechlynx_fresh_descriptor_images.zip",
        "compressed execution copy; extracted current package is retained",
        "work/pferi_v2/descriptor_execution_package",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package 2",
        "Finder-style duplicate directory",
        "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package.zip",
        "compressed copy of retained annotation package",
        "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/v2_czechlynx_pilot_local_match_images.zip",
        "compressed copy of retained local-match execution package",
        "work/pferi_v2/measurement_feasibility/local_match_execution_package",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/v2_czechlynx_pilot_quality_images.zip",
        "compressed copy of retained quality execution package",
        "work/pferi_v2/measurement_feasibility/quality_execution_package",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v1",
        "superseded by completed v3 dry run",
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v2",
        "superseded by completed v3 dry run",
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/local_match/PF_ERI_FINAL_RESULTS_GPU.zip",
        "compressed copy of retained returned result directory",
        "work/pferi_v2/gpu/measurement_feasibility/local_match/PF_ERI_FINAL_RESULTS_GPU",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2.zip",
        "compressed copy of retained final matcher package",
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/v2_local_match_kaggle_package.zip",
        "superseded matcher-v1 transfer package",
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
    ),
    CleanupTarget(
        "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2/PF_ERI_V2_TIMED_OPERATIONAL_REHEARSAL_DELIVERY.zip",
        "compressed copy of retained v2 rehearsal directory",
        "work/pferi_v2/workbook04/timed_operational_rehearsal_v2/reviewer_view",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/reviewer_view",
        "unpacked original reviewer view duplicated by the completed returned package and retained original delivery ZIP",
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/independent_browser_audit/returned_audits/2026-07-14_a001_completed/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY/reviewer_view",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/machine_static_audit_recheck.json",
        "byte-identical rerun of the retained machine static audit",
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/machine_static_audit.json",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/structural_oracle_reliability_audit.json",
        "superseded initial structural-oracle reliability calculation recorded in the iteration lineage",
        "work/pferi_v2/gpu/measurement_feasibility/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/structural_oracle_reliability_audit_v2.json",
        "superseded intermediate structural-oracle reliability calculation recorded in the iteration lineage",
        "work/pferi_v2/gpu/measurement_feasibility/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/v2_local_match_package_audit.json",
        "audit for a removed initial local-match package; hash and disposition are retained in the iteration lineage",
        "work/pferi_v2/gpu/measurement_feasibility/final_local_match_package_v2.audit.json",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/measurement_feasibility/v2_local_match_kaggle_package_audit.json",
        "audit for the superseded matcher-v1 Kaggle package; hash and disposition are retained in the iteration lineage",
        "work/pferi_v2/gpu/measurement_feasibility/final_local_match_package_v2.audit.json",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
        "superseded extracted runner package missing the current CSV robustness fix and full-frame wrapper",
        "gpu/kaggle_v2_local_matcher_v2",
    ),
    CleanupTarget(
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL_COLAB.zip",
        "parallel Colab package superseded by the platform-neutral canonical package",
        "scripts/build_v2_full_frame_local_match_control_package.py",
        "5e4b649e43738d850de4710d61ecb0bdc57891317bcb4905e5be184ead8118c7",
    ),
    CleanupTarget(
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL_COLAB.audit.json",
        "audit coupled to the removed parallel Colab package",
        "docs/project-governance/workstreams/04_dual_sample_confirmation/05_colab_full_frame_execution_engineering_audit.md",
        "f3a69547d3ba0810a087237bfd5cbf0f14e6b93337b2683f8e072b88564f3f1d",
    ),
    CleanupTarget(
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL_COLAB_CONTINUE_AFTER_KAGGLE.zip",
        "abandoned cross-platform continuation package",
        "docs/project-governance/workstreams/04_dual_sample_confirmation/05_colab_full_frame_execution_engineering_audit.md",
        "53b6592c060b3b60193d62faa352f99fb4e38316b9ba1facd3d8d995110e3b19",
    ),
    CleanupTarget(
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL_COLAB_CONTINUE_AFTER_KAGGLE.audit.json",
        "audit coupled to the abandoned cross-platform continuation package",
        "docs/project-governance/workstreams/04_dual_sample_confirmation/05_colab_full_frame_execution_engineering_audit.md",
        "b8eec5b3b5cd97a9f77a300be2340d20f7e5e748de97d178af19d6d009773e46",
    ),
    CleanupTarget(
        "work/pferi_v2/gpu/descriptor_runs/megadescriptor_l_384/embedding_manifest.csv",
        "legacy two-column manifest whose ordered image IDs are a strict subset of the retained v2 manifest schema",
        "work/pferi_v2/gpu/descriptor_runs/megadescriptor_l_384/embedding_manifest_v2.csv",
        "d9dace67216d85430026bc4dcc3df80ccb9b25b5e9c01416ccfb3303403c3bc1",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/local_match_return/2026-07-14_gpu_t4_protocol_v2/input/v2_local_match_execution_package/pair_execution_manifest.csv",
        "byte-identical returned-input copy of the retained pilot execution manifest",
        "work/pferi_v2/measurement_feasibility/local_match_execution_package/pair_execution_manifest.csv",
        "534f8a055076b2bae301d132d1c97dc6d9d5a4410998a979dcfed2581b84e2c7",
        True,
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/local_match_return/2026-07-14_gpu_t4_protocol_v2/smoke_input/v2_local_match_execution_package/pair_execution_manifest.csv",
        "byte-identical smoke-input copy of the retained pilot execution manifest",
        "work/pferi_v2/measurement_feasibility/local_match_execution_package/pair_execution_manifest.csv",
        "534f8a055076b2bae301d132d1c97dc6d9d5a4410998a979dcfed2581b84e2c7",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/czechlynx-high-topup-colab-package/legacy-code14_colab_megadetector_packaged_manifest.csv",
        "byte-identical packaged-manifest alias",
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/czechlynx-high-topup-colab-package/legacy-code14_colab_megadetector_manifest.csv",
        "924fe7bd61830022e4198833a2a600813848179bfe14c50b403dcdcc29726a76",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/low-evidence-topup-colab-package/legacy-code14_colab_megadetector_packaged_manifest.csv",
        "byte-identical packaged-manifest alias",
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/low-evidence-topup-colab-package/legacy-code14_colab_megadetector_manifest.csv",
        "94f840920fb65d45cd25240ed18ffa2cfadd8d5fcda7fcb07d8d123beafc3a51",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/review-routing/evidence-routed-review-layer/hybrid_routing_policy/legacy-code15_czechlynx_candidate_routing_input.csv",
        "byte-identical 194 MB ranker input copied into two historical packages",
        "archive/pferi_v1/outputs/review-routing/evidence-routed-review-layer/colab_ranker_package/legacy-code15_czechlynx_candidate_routing_input.csv",
        "a9d47d7446d55f931174d9a5a5baa098be54cc532f317fdd123947043c152191",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/czechlynx-high-topup-colab-package/run_legacy-code14_megadetector_colab.py",
        "byte-identical copy of the retained Phase14 MegaDetector package runner",
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/megadetector-low-evidence-package/run_legacy-code14_megadetector_colab.py",
        "0119845e6496a19853ecf224343d33799f060dfe1a2981b27eae126bfc8d9d59",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/low-evidence-topup-colab-package/run_legacy-code14_megadetector_colab.py",
        "byte-identical copy of the retained Phase14 MegaDetector package runner",
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/megadetector-low-evidence-package/run_legacy-code14_megadetector_colab.py",
        "0119845e6496a19853ecf224343d33799f060dfe1a2981b27eae126bfc8d9d59",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/descriptor-embedding-cloud-package/scripts/extract_legacy-code14_megadescriptor_embeddings.py",
        "byte-identical package copy of the retained archived Phase14 extractor",
        "archive/pferi_v1/reproducibility/scripts/extract_phase14_megadescriptor_embeddings.py",
        "19eed59c5926421780fa8a50132521a6b27440d4aecce7b01775ab4949accf17",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/descriptor-embedding-package/retry_failed_5_cloud_package/scripts/extract_legacy-code14_megadescriptor_embeddings.py",
        "byte-identical retry-package copy of the retained archived Phase14 extractor",
        "archive/pferi_v1/reproducibility/scripts/extract_phase14_megadescriptor_embeddings.py",
        "19eed59c5926421780fa8a50132521a6b27440d4aecce7b01775ab4949accf17",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/data-foundation/wild-urban-evidence-foundation/descriptor-embedding-package/retry_replacement_5_cloud_package/scripts/extract_legacy-code14_megadescriptor_embeddings.py",
        "byte-identical retry-package copy of the retained archived Phase14 extractor",
        "archive/pferi_v1/reproducibility/scripts/extract_phase14_megadescriptor_embeddings.py",
        "19eed59c5926421780fa8a50132521a6b27440d4aecce7b01775ab4949accf17",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/project-governance/safeguards-candidate-scoring/bobcat-20k-candidate-pool/run_legacy-code16e_candidate_model_filter_colab.py",
        "byte-identical Phase16E runner copied into a batch-specific package",
        "archive/pferi_v1/outputs/project-governance/safeguards-candidate-scoring/candidate-model-filter-colab-package/run_legacy-code16e_candidate_model_filter_colab.py",
        "2425df643c6ca720161fd4679c264fe323ca2245651d55dc7723a5dcf1c39370",
        True,
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/project-governance/safeguards-candidate-scoring/bobcat-remaining-local-package/run_legacy-code16e_candidate_model_filter_colab.py",
        "byte-identical Phase16E runner copied into a batch-specific package",
        "archive/pferi_v1/outputs/project-governance/safeguards-candidate-scoring/candidate-model-filter-colab-package/run_legacy-code16e_candidate_model_filter_colab.py",
        "2425df643c6ca720161fd4679c264fe323ca2245651d55dc7723a5dcf1c39370",
        True,
    ),
    CleanupTarget(
        "paper/review_packets/confirmatory_phase18n",
        "active-tree copy of the historical PF-ERI v1 Phase18N packet",
        "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/confirmatory-review-packet",
        retained_must_match=True,
    ),
    CleanupTarget(
        "paper/supplement/source_data/source_data_package_audit.json",
        "active-paper copy of the historical PF-ERI v1 source-data audit",
        "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_source_data_package/source_data_package_audit.json",
        "e9fdd40d4a1913db734028ef12110da894e89adbfcd9d8d5fa53fbf493a896a9",
        True,
    ),
)


def exact_package_duplicate_targets() -> tuple[CleanupTarget, ...]:
    """Return explicit filename-pattern duplicates from historical package families."""
    phase4_root = "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase4"
    phase4_tables = (
        "phase4e_table1_overall_qc_metrics.csv",
        "phase4e_table2_rq1_top_visual_factors.csv",
        "phase4e_table3_rq2_model_divergence.csv",
        "phase4e_table4_rq3_policy_tradeoffs.csv",
        "phase4e_sparse_strata_filtered_rq1.csv",
        "phase4e_sparse_strata_filtered_rq2.csv",
    )
    targets: list[CleanupTarget] = []
    for name in phase4_tables:
        retained = f"{phase4_root}/final_review_pack/tables/{name}"
        for package in ("result_pack", "manuscript_pack", "review_pack"):
            targets.append(CleanupTarget(
                f"{phase4_root}/{package}/tables/{name}",
                "byte-identical Phase4 table copied across result/manuscript/review/final-review packages",
                retained,
                retained_must_match=True,
            ))
    for target, retained in (
        ("manuscript_pack/docs/phase4g_integrated_manuscript_v1.md", "review_pack/docs/phase4g_integrated_manuscript_v1.md"),
        ("manuscript_pack/docs/phase4g_extended_methods_reproducibility.md", "review_pack/docs/phase4g_extended_methods_reproducibility.md"),
        ("review_pack/docs/phase4h_final_claim_boundary_check.md", "final_review_pack/docs/phase4h_final_claim_boundary_check.md"),
        ("review_pack/docs/phase4h_oral_defense_qa.md", "final_review_pack/docs/phase4h_oral_defense_qa.md"),
    ):
        targets.append(CleanupTarget(
            f"{phase4_root}/{target}",
            "byte-identical Phase4 document copied into a later review package",
            f"{phase4_root}/{retained}",
            retained_must_match=True,
        ))

    phase6_root = (
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase6/"
        "annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace"
    )
    imported_names = {
        "000_049": "range_000_049_annotated.csv",
        "050_099": "range_050_099_annotated(1).csv",
        "100_149": "range_100_149_annotated(1).csv",
        "150_199": "range_150_199_annotated.csv",
        "200_249": "range_200_249_annotated.csv",
        "250_299": "range_250_299_annotated.csv",
        "300_349": "range_300_349_annotated.csv",
        "350_399": "range_350_399_annotated.csv",
        "400_449": "range_400_449_annotated.csv",
        "450_499": "range_450_499_annotated.csv",
    }
    incoming_names = {
        **{key: f"range_{key}_annotated.csv" for key in imported_names},
        "100_149": "range_100_149_annotated(1).csv",
    }
    for range_id, imported_name in imported_names.items():
        targets.append(CleanupTarget(
            f"{phase6_root}/incoming_from_downloads/range_{range_id}/{incoming_names[range_id]}",
            "byte-identical downloaded annotation return already retained in imported_ranges",
            f"{phase6_root}/imported_ranges/range_{range_id}/{imported_name}",
            retained_must_match=True,
        ))
    for range_id in imported_names:
        manifest_root = (
            f"{phase6_root}/incoming_from_downloads/range_{range_id}/"
            f"range_{range_id}_needs_review_streamlit_v2_clean/manifests"
        )
        targets.append(CleanupTarget(
            f"{manifest_root}/range_{range_id}_needs_review_correction_template_v2_clean.csv",
            "byte-identical blank correction-template alias of the retained needs-review manifest",
            f"{manifest_root}/range_{range_id}_needs_review_manifest_v2_clean.csv",
            retained_must_match=True,
        ))
    stale_phase6 = (
        "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/phase6/"
        "archive/stale_v1_assisted_annotation_artifacts_20260613"
    )
    retained_range0 = f"{phase6_root}/imported_ranges/range_000_049/range_000_049_annotated.csv"
    for stale in (
        "imported_ranges/range_000_049/range_000_049_annotated(1).csv",
        "incoming_from_downloads/range_000_049/range_000_049_annotated(1).csv",
    ):
        targets.append(CleanupTarget(
            f"{stale_phase6}/{stale}",
            "byte-identical stale Phase6 annotation copy retained in the accepted imported workspace",
            retained_range0,
            retained_must_match=True,
        ))
    stale_manifest_root = (
        f"{stale_phase6}/incoming_from_downloads/range_000_049/"
        "range_000_049_needs_review_streamlit/manifests"
    )
    targets.append(CleanupTarget(
        f"{stale_manifest_root}/range_000_049_needs_review_correction_template.csv",
        "byte-identical stale correction-template alias",
        f"{stale_manifest_root}/range_000_049_needs_review_manifest.csv",
        retained_must_match=True,
    ))
    return tuple(targets)


TARGETS = (*TARGETS, *exact_package_duplicate_targets())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_for(path: Path) -> list[Path]:
    if path.is_file() or path.is_symlink():
        return [path]
    return sorted(item for item in path.rglob("*") if item.is_file() or item.is_symlink())


def inventory() -> tuple[list[dict[str, str | int]], list[CleanupTarget]]:
    rows: list[dict[str, str | int]] = []
    present: list[CleanupTarget] = []
    targets = list(TARGETS)
    excluded_roots = {".git", ".codegraph", ".repowise"}
    for junk in sorted(ROOT.rglob(".DS_Store")):
        if excluded_roots.isdisjoint(junk.relative_to(ROOT).parts):
            targets.append(CleanupTarget(str(junk.relative_to(ROOT)), "macOS metadata", ".gitignore"))
    for cache in sorted(ROOT.rglob("__pycache__")):
        if excluded_roots.isdisjoint(cache.relative_to(ROOT).parts):
            targets.append(CleanupTarget(str(cache.relative_to(ROOT)), "rebuildable Python bytecode cache", ".gitignore"))
    for target in targets:
        path = ROOT / target.path
        retained = ROOT / target.retained_path
        if not path.exists() and not path.is_symlink():
            continue
        if not retained.exists():
            raise FileNotFoundError(f"Refusing cleanup because retained counterpart is absent: {retained}")
        if target.expected_sha256 is not None:
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"Hash-guarded cleanup target is not a regular file: {path}")
            observed = sha256(path)
            if observed != target.expected_sha256:
                raise ValueError(
                    f"Refusing cleanup because target hash changed: {path} "
                    f"expected={target.expected_sha256} observed={observed}"
                )
        if target.retained_must_match:
            if path.is_dir() and not path.is_symlink():
                if not retained.is_dir() or retained.is_symlink():
                    raise ValueError(f"Retained duplicate is not a directory: {retained}")
                source_files = {
                    item.relative_to(path): sha256(item)
                    for item in path.rglob("*")
                    if item.is_file() and not item.is_symlink()
                }
                retained_files = {
                    item.relative_to(retained): sha256(item)
                    for item in retained.rglob("*")
                    if item.is_file() and not item.is_symlink()
                }
                if source_files != retained_files:
                    raise ValueError(
                        f"Refusing cleanup because retained directory differs: {path} != {retained}"
                    )
            else:
                if not retained.is_file() or retained.is_symlink():
                    raise ValueError(f"Retained duplicate is not a regular file: {retained}")
                if sha256(path) != sha256(retained):
                    raise ValueError(f"Refusing cleanup because retained duplicate differs: {path} != {retained}")
        present.append(target)
        for item in files_for(path):
            rows.append({
                "removed_path": str(item.relative_to(ROOT)),
                "size_bytes": item.lstat().st_size,
                "sha256": sha256(item) if item.is_file() else "symlink",
                "reason": target.reason,
                "retained_path": target.retained_path,
            })
    return rows, present


def write_manifest(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    append = path.exists() and path.stat().st_size > 0
    with path.open("a" if append else "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["removed_path", "size_bytes", "sha256", "reason", "retained_path"],
            lineterminator="\n",
        )
        if not append:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the manifest and delete allowlisted paths")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    rows, targets = inventory()
    total = sum(int(row["size_bytes"]) for row in rows)
    print(f"mode={'apply' if args.apply else 'dry-run'} targets={len(targets)} files={len(rows)} bytes={total}")
    for target in targets:
        print(f"- {target.path}: {target.reason}")
    if not args.apply:
        return
    write_manifest(args.manifest.resolve(), rows)
    for target in targets:
        path = ROOT / target.path
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    print(f"manifest={args.manifest.resolve()} cleaned_utc={datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
