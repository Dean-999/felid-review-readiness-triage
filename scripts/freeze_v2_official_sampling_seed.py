#!/usr/bin/env python3
"""Freeze one official PF-ERI v2 sampling seed after all pre-seed gates pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
SEED_RECORD_VERSION = "pferi_v2_official_sampling_seed_record_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_passed_audit(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(path)
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS":
        raise RuntimeError(f"pre-seed audit is not PASS: {path}")
    if audit.get("official_seed") not in (None, ""):
        raise RuntimeError(f"pre-seed audit unexpectedly contains an official seed: {path}")
    return audit


def freeze_seed(output_json: Path, prerequisite_audits: Sequence[Path]) -> dict[str, object]:
    if output_json.exists():
        raise FileExistsError(f"official seed record already exists; reroll prohibited: {output_json}")
    if len(prerequisite_audits) != 3:
        raise ValueError("exactly three pre-seed audit files are required")
    prerequisites = []
    for path in prerequisite_audits:
        audit = load_passed_audit(path)
        prerequisites.append(
            {
                "path": str(path.resolve().relative_to(ROOT)),
                "sha256": sha256_file(path),
                "audit_version": audit.get("audit_version", ""),
                "status": audit["status"],
            }
        )
    record = {
        "seed_record_version": SEED_RECORD_VERSION,
        "status": "FROZEN",
        "frozen_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "official_seed": secrets.token_hex(32),
        "generation_method": "Python secrets.token_hex(32) backed by the operating-system cryptographic random source",
        "reroll_policy": "PROHIBITED",
        "prerequisite_audits": prerequisites,
        "authorization_boundary": (
            "The frozen seed authorizes deterministic image-role allocation only. "
            "Pair sampling and outcome-packet creation remain blocked by post-allocation audits."
        ),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-audit", type=Path, required=True)
    parser.add_argument("--exclusion-audit", type=Path, required=True)
    parser.add_argument("--strata-preflight-audit", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)
    record = freeze_seed(
        args.output_json,
        [args.quality_audit, args.exclusion_audit, args.strata_preflight_audit],
    )
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
