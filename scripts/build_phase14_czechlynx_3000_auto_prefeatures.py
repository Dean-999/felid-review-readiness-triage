#!/usr/bin/env python3
"""Build automated image prefeatures for the Phase 14 CzechLynx 3000 manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_phase14_fcf_bobcat_auto_prefeatures import image_metrics  # noqa: E402

DEFAULT_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_3000_manifest.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUT = OUT_DIR / "czechlynx_phase14_3000_auto_prefeatures.csv"
DEFAULT_SUMMARY = OUT_DIR / "czechlynx_phase14_3000_auto_prefeatures_summary.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build(manifest: pd.DataFrame, max_side: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = len(manifest)
    for i, row in manifest.iterrows():
        base = row.to_dict()
        path = resolve(str(row["review_image_path_local"]))
        base["image_exists"] = "yes" if path.exists() else "no"
        try:
            if not path.exists():
                raise FileNotFoundError(path)
            base.update(image_metrics(path, max_side=max_side))
            base["auto_prefeature_status"] = "ok"
            base["auto_prefeature_error"] = ""
        except Exception as exc:  # noqa: BLE001 - record row-level failure for audit.
            base["auto_prefeature_status"] = "failed"
            base["auto_prefeature_error"] = repr(exc)
        rows.append(base)
        if (i + 1) % 250 == 0 or (i + 1) == total:
            print(f"processed {i + 1}/{total}")
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--max-side", type=int, default=1024)
    args = parser.parse_args()

    manifest_path = resolve(args.manifest)
    output_path = resolve(args.output)
    summary_path = resolve(args.summary)
    manifest = pd.read_csv(manifest_path)
    table = build(manifest, max_side=args.max_side)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)

    ok = table[table["auto_prefeature_status"].eq("ok")]
    summary = {
        "manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "row_count": int(len(table)),
        "ok_count": int(len(ok)),
        "failed_count": int(table["auto_prefeature_status"].eq("failed").sum()),
        "identity_count": int(table["identity_label"].nunique()),
        "label_status_counts": {
            str(k): int(v)
            for k, v in table["phase14_label_status"].value_counts().sort_index().items()
        },
        "auto_review_bucket_counts": {
            str(k): int(v)
            for k, v in ok["auto_review_bucket"].value_counts().sort_index().items()
        },
        "auto_night_ir_counts": {
            str(k): int(v)
            for k, v in ok["auto_night_ir"].value_counts().sort_index().items()
        },
        "claim_boundary": "machine_prefeatures_for_phase14_czechlynx_3000_not_human_ground_truth",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 CzechLynx 3000 prefeatures "
        f"rows={len(table)} failures={summary['failed_count']} output={output_path.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
