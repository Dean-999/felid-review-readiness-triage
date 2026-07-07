#!/usr/bin/env python3
"""Run Phase18C-F plus review-utility confidence for one strong descriptor."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.build_phase18_review_utility_confidence import build_phase18_review_utility_confidence
    from scripts.build_phase18c_czechlynx_pair_contract import build_phase18c
    from scripts.build_phase18d_pf_eri_pair_features import build_phase18d
    from scripts.build_phase18e_review_router import build_phase18e
    from scripts.build_phase18f_bobcat_transfer_readiness import build_phase18f
    from scripts.phase18_pipeline_utils import PROJECT_ROOT, now_utc, project_relative, write_json
except ImportError:  # pragma: no cover - direct script execution
    from build_phase18_review_utility_confidence import build_phase18_review_utility_confidence
    from build_phase18c_czechlynx_pair_contract import build_phase18c
    from build_phase18d_pf_eri_pair_features import build_phase18d
    from build_phase18e_review_router import build_phase18e
    from build_phase18f_bobcat_transfer_readiness import build_phase18f
    from phase18_pipeline_utils import PROJECT_ROOT, now_utc, project_relative, write_json


STRONG_ROOT = PROJECT_ROOT / "outputs/phase18/phase18_strong_baselines"


def run_phase18_strong_descriptor_pipeline(
    descriptor_name: str,
    manifest_csv: Path,
    embeddings_npy: Path,
    output_root: Path,
    czech_top_k: int = 20,
    bobcat_top_k: int = 10,
    bootstrap_iterations: int = 5000,
) -> dict[str, Any]:
    c_dir = output_root / "phase18c_strong_pair_contract" / descriptor_name
    d_dir = output_root / "phase18d_strong_pf_eri_pair_features" / descriptor_name
    e_dir = output_root / "phase18e_strong_review_router" / descriptor_name
    f_dir = output_root / "phase18f_strong_bobcat_transfer_readiness" / descriptor_name
    confidence_dir = output_root / "phase18_review_utility_confidence" / descriptor_name

    c_audit = build_phase18c(manifest_csv, embeddings_npy, c_dir, top_k=czech_top_k)
    d_audit = build_phase18d(c_dir / "phase18c_czechlynx_known_id_pair_contract.csv", d_dir)
    e_audit = build_phase18e(d_dir / "phase18d_pf_eri_pair_features.csv", e_dir)
    f_audit = build_phase18f(manifest_csv, embeddings_npy, f_dir, top_k=bobcat_top_k)
    confidence_audit = build_phase18_review_utility_confidence(
        input_features=d_dir / "phase18d_pf_eri_pair_features.csv",
        output_dir=confidence_dir,
        iterations=bootstrap_iterations,
    )

    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "input_manifest": project_relative(manifest_csv),
        "input_embeddings": project_relative(embeddings_npy),
        "phase18c": c_audit,
        "phase18d": d_audit,
        "phase18e": e_audit,
        "phase18f": f_audit,
        "confidence": confidence_audit,
        "status": "PASS",
        "claim_boundary": (
            "Strong descriptor pipeline evaluates PF-ERI pair-level review utility "
            "after upstream candidate generation. It is not a descriptor-replacement claim."
        ),
    }
    run_dir = output_root / "phase18_strong_descriptor_pipeline" / descriptor_name
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "phase18_strong_descriptor_pipeline_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor-name", required=True)
    parser.add_argument("--strong-dir", type=Path, default=None)
    parser.add_argument("--manifest-csv", type=Path, default=None)
    parser.add_argument("--embeddings-npy", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "outputs/phase18")
    parser.add_argument("--czech-top-k", type=int, default=20)
    parser.add_argument("--bobcat-top-k", type=int, default=10)
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    strong_dir = args.strong_dir or STRONG_ROOT / args.descriptor_name
    manifest_csv = args.manifest_csv or strong_dir / "phase18_strong_embedding_manifest.csv"
    embeddings_npy = args.embeddings_npy or strong_dir / "phase18_strong_embeddings.npy"
    audit = run_phase18_strong_descriptor_pipeline(
        descriptor_name=args.descriptor_name,
        manifest_csv=manifest_csv,
        embeddings_npy=embeddings_npy,
        output_root=args.output_root,
        czech_top_k=args.czech_top_k,
        bobcat_top_k=args.bobcat_top_k,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    print("PASS phase18 strong descriptor pipeline")
    print(f"descriptor_name={audit['descriptor_name']}")
    print(f"status={audit['status']}")
    print(f"review_utility_status={audit['confidence']['pair_level_review_utility_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
