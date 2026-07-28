#!/usr/bin/env python3
"""Prepare the non-reviewer browser-audit handoff for Task15I packages."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "artifacts/transfers/pferi_v2/review/task15i_reviewer_packages"
OUTPUT = ROOT / "artifacts/transfers/pferi_v2/review/task15i_browser_audit"
CHECKLIST_COLUMNS = [
    "check_id", "required_check", "status", "prohibited_exposure_observed",
    "exposed_records_or_na", "leak_source_or_na", "remediation_or_na",
    "retest_evidence_or_na", "final_disposition", "auditor_id", "auditor_role",
    "audited_at_utc", "notes",
]
PACKAGE_COLUMNS = ["reviewer_alias", "zip_filename", "zip_sha256", "first_pass_task_count"]
REQUIRED_CHECKS = [
    "rendered_dom", "url_and_browser_state", "asset_tokens_and_filenames",
    "export_columns", "sort_filter_search_controls", "network_or_hidden_fields",
    "peer_response_isolation", "leak_disposition_log",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def blank_checklist_rows() -> list[dict[str, str]]:
    return [
        {
            "check_id": f"check_{index:02d}", "required_check": check,
            "status": "not_started", "prohibited_exposure_observed": "not_recorded",
            "exposed_records_or_na": "", "leak_source_or_na": "",
            "remediation_or_na": "", "retest_evidence_or_na": "",
            "final_disposition": "pending", "auditor_id": "", "auditor_role": "",
            "audited_at_utc": "", "notes": "",
        }
        for index, check in enumerate(REQUIRED_CHECKS, start=1)
    ]


def package_rows(candidate_audit: dict[str, Any], candidate_root: Path) -> list[dict[str, Any]]:
    if candidate_audit.get("status") != "PASS_CANDIDATE_NOT_RELEASED":
        raise ValueError("candidate package build is not eligible for browser-audit handoff")
    if not candidate_audit.get("conflict_attestations_complete"):
        raise ValueError("reviewer conflict attestations are incomplete")
    packages = candidate_audit.get("reviewer_packages", {})
    if set(packages) != {"reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D"}:
        raise ValueError("candidate audit does not contain four expected reviewer packages")
    rows = []
    for alias in sorted(packages):
        package = packages[alias]
        zip_path = candidate_root / "candidate_reviewer_packages" / f"PAIR_REVIEW_{alias}.zip"
        if not zip_path.is_file() or sha256(zip_path) != package["zip_sha256"]:
            raise ValueError(f"candidate package hash mismatch: {alias}")
        if package.get("static_status") != "PASS" or package.get("first_pass_task_count") != 800:
            raise ValueError(f"candidate package static validation failed: {alias}")
        rows.append({
            "reviewer_alias": alias,
            "zip_filename": zip_path.name,
            "zip_sha256": package["zip_sha256"],
            "first_pass_task_count": package["first_pass_task_count"],
        })
    return rows


def build(output: Path = OUTPUT, candidate_root: Path = CANDIDATE) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    candidate_audit_path = candidate_root / "candidate_build_audit.json"
    candidate_audit = json.loads(candidate_audit_path.read_text(encoding="utf-8"))
    packages = package_rows(candidate_audit, candidate_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_csv(stage / "candidate_package_manifest.csv", PACKAGE_COLUMNS, packages)
        write_csv(stage / "human_browser_leakage_checklist.csv", CHECKLIST_COLUMNS, blank_checklist_rows())
        (stage / "INDEPENDENT_AUDITOR_GUIDE_zh.md").write_text(
            "# Task15I 独立浏览器泄漏审计\n\n"
            "本审计必须由一名不会担任本轮 first-pass reviewer 或 adjudicator 的独立人员执行。"
            "审计者必须逐个解压 `candidate_package_manifest.csv` 所列的四个 ZIP，运行其中的 Streamlit 界面，并在真实浏览器中完成检查；不得仅检查 CSV 或源代码。\n\n"
            "对每个检查项，审计页面、URL 和浏览器历史、图片文件名和 alt text、下载内容、搜索/排序/筛选控件、开发者工具 DOM 与网络请求，以及一次保存操作后的回应隔离。"
            "如出现 descriptor、分数、rank、route、feature、身份、相机、来源、既往回应、majority、adjudication 或其他可推断信息，标记 `fail` 并记录包、来源、修复和复测证据。\n\n"
            "只有所有行均为 `pass`、`prohibited_exposure_observed=no`、`final_disposition=no_leak_confirmed`，并由同一人以 `independent_interface_auditor` 身份和带时区时间戳签署，才可进入正式发放。"
            "本审计通过只证明界面盲法准备就绪；不产生结果标签，也不证明 pair 正确性或项目通过。\n",
            encoding="utf-8",
        )
        audit = {
            "status": "PASS_AUDIT_DELIVERY_PREPARED_NOT_COMPLETED",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "candidate_build_audit_sha256": sha256(candidate_audit_path),
            "candidate_package_count": len(packages),
            "first_pass_task_count": sum(int(row["first_pass_task_count"]) for row in packages),
            "independent_auditor_required": True,
            "packet_release_authorized": False,
            "outcome_collection_authorized": False,
            "next_required_gate": "completed_independent_real_browser_leakage_audit",
            "claim_boundary": "Audit delivery only. No reviewer package is released, no outcome is collected, and no pair correctness is established.",
        }
        (stage / "audit_delivery_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = sorted(path for path in stage.iterdir() if path.is_file())
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
