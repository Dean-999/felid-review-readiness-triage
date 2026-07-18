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
        "outputs/pferi_v2/measurement_feasibility_pilot/current_structural_oracle_reliability_audit.json",
        "superseded reliability audit from the removed current analyzer",
        "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/kaggle_legacy-code18_strong_baseline_input_20260702.zip",
        "superseded v1 transfer package; returned baseline results and audits are retained",
        "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/returned_strong_baselines",
    ),
    CleanupTarget(
        "outputs/pferi_v2/PF_ERI_V2_KAGGLE_RAW_ARCHIVES/v2_czechlynx_fresh_descriptor_images.zip.bin",
        "byte-identical transport suffix copy",
        "work/pferi_v2/descriptor_execution_package",
    ),
    CleanupTarget(
        "outputs/pferi_v2/PF_ERI_V2_KAGGLE_RAW_ARCHIVES/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip.bin",
        "byte-identical transport suffix copy",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
    ),
    CleanupTarget(
        "outputs/pferi_v2/v2_czechlynx_fresh_descriptor_images.zip",
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
        "outputs/pferi_v2/measurement_feasibility_pilot/v2_czechlynx_pilot_local_match_images.zip",
        "compressed copy of retained local-match execution package",
        "work/pferi_v2/measurement_feasibility/local_match_execution_package",
    ),
    CleanupTarget(
        "outputs/pferi_v2/measurement_feasibility_pilot/v2_czechlynx_pilot_quality_images.zip",
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
        "outputs/pferi_v2/measurement_feasibility_pilot/local_match_runs/2026-07-14_gpu_t4_protocol_v2/PF_ERI_FINAL_RESULTS_GPU.zip",
        "compressed copy of retained returned result directory",
        "outputs/pferi_v2/measurement_feasibility_pilot/local_match_runs/2026-07-14_gpu_t4_protocol_v2/PF_ERI_FINAL_RESULTS_GPU",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2.zip",
        "compressed copy of retained final matcher package",
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
    ),
    CleanupTarget(
        "outputs/pferi_v2/measurement_feasibility_pilot/v2_local_match_kaggle_package.zip",
        "superseded matcher-v1 transfer package",
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
    ),
    CleanupTarget(
        "outputs/pferi_v2/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2/PF_ERI_V2_TIMED_OPERATIONAL_REHEARSAL_DELIVERY.zip",
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
        "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_reliability_audit.json",
        "superseded initial structural-oracle reliability calculation recorded in the iteration lineage",
        "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_reliability_audit_v2.json",
        "superseded intermediate structural-oracle reliability calculation recorded in the iteration lineage",
        "outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_reliability_audit_latest.json",
    ),
    CleanupTarget(
        "outputs/pferi_v2/measurement_feasibility_pilot/v2_local_match_package_audit.json",
        "audit for a removed initial local-match package; hash and disposition are retained in the iteration lineage",
        "outputs/pferi_v2/measurement_feasibility_pilot/final_local_match_package_v2.audit.json",
    ),
    CleanupTarget(
        "outputs/pferi_v2/measurement_feasibility_pilot/v2_local_match_kaggle_package_audit.json",
        "audit for the superseded matcher-v1 Kaggle package; hash and disposition are retained in the iteration lineage",
        "outputs/pferi_v2/measurement_feasibility_pilot/final_local_match_package_v2.audit.json",
    ),
    CleanupTarget(
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
        "superseded extracted runner package missing the current CSV robustness fix and full-frame wrapper",
        "gpu/kaggle_v2_local_matcher_v2",
    ),
)


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
