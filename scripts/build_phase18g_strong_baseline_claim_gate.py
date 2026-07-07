#!/usr/bin/env python3
"""Build Phase18G strong-baseline handoff and claim gate.

This phase is deliberately strict. It does not pretend the Phase18B local
descriptor-control baseline is a strong Re-ID baseline. If torch/timm or returned
strong-model embeddings are absent, the script still writes the handoff package
and exits successfully, but the scientific claim gate remains blocked.
"""

from __future__ import annotations

import argparse
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PHASE18B_DIR,
        PHASE18E_DIR,
        PHASE18G_DIR,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PHASE18B_DIR,
        PHASE18E_DIR,
        PHASE18G_DIR,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )


HANDOFF_COLUMNS = [
    "phase18_image_id",
    "species",
    "modeling_role",
    "train_eval_eligible",
    "has_known_identity",
    "identity_label",
    "frozen_image_path",
    "sha256",
    "recommended_strong_baseline_role",
    "required_return_key",
    "claim_boundary",
]

GATE_COLUMNS = [
    "gate_id",
    "gate_status",
    "evidence",
    "required_repair",
]


def dependency_status() -> dict[str, bool]:
    return {
        "torch": importlib.util.find_spec("torch") is not None,
        "timm": importlib.util.find_spec("timm") is not None,
        "wildlife_tools": importlib.util.find_spec("wildlife_tools") is not None,
        "sklearn": importlib.util.find_spec("sklearn") is not None,
    }


def handoff_role(row: dict[str, str]) -> str:
    if row["species"] == "czechlynx":
        return "known_id_retrieval_baseline"
    if row["species"] == "bobcat":
        return "unlabeled_transfer_embedding_only"
    return "unknown"


def build_handoff_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                "phase18_image_id": row["phase18_image_id"],
                "species": row["species"],
                "modeling_role": row["modeling_role"],
                "train_eval_eligible": row["train_eval_eligible"],
                "has_known_identity": row["has_known_identity"],
                "identity_label": row["identity_label"],
                "frozen_image_path": row["frozen_image_path"],
                "sha256": row["sha256"],
                "recommended_strong_baseline_role": handoff_role(row),
                "required_return_key": row["phase18_image_id"],
                "claim_boundary": (
                    "Strong baseline extraction input only. Return embeddings or "
                    "pair scores keyed by phase18_image_id; do not create Bobcat "
                    "identity labels."
                ),
            }
        )
    return output


def build_gate_rows(
    deps: dict[str, bool],
    strong_embedding_manifest: Path | None,
    strong_pair_scores: Path | None,
) -> list[dict[str, str]]:
    strong_manifest_present = bool(strong_embedding_manifest and strong_embedding_manifest.exists())
    strong_scores_present = bool(strong_pair_scores and strong_pair_scores.exists())
    strong_runtime_ready = bool(deps["torch"] and deps["timm"])
    return [
        {
            "gate_id": "strong_descriptor_runtime",
            "gate_status": "PASS" if strong_runtime_ready else "BLOCKED",
            "evidence": f"torch={deps['torch']} timm={deps['timm']} wildlife_tools={deps['wildlife_tools']}",
            "required_repair": "Install torch+timm and run MegaDescriptor/WildlifeTools, or return strong embeddings from GPU/Colab.",
        },
        {
            "gate_id": "strong_embedding_artifact",
            "gate_status": "PASS" if strong_manifest_present else "BLOCKED",
            "evidence": str(strong_embedding_manifest) if strong_embedding_manifest else "not provided",
            "required_repair": "Provide a strong embedding manifest keyed by phase18_image_id.",
        },
        {
            "gate_id": "strong_pair_or_retrieval_scores",
            "gate_status": "PASS" if strong_scores_present else "BLOCKED",
            "evidence": str(strong_pair_scores) if strong_pair_scores else "not provided",
            "required_repair": "Provide strong baseline retrieval/pair scores for CzechLynx known-ID evaluation.",
        },
        {
            "gate_id": "local_control_not_final_claim",
            "gate_status": "BLOCKED",
            "evidence": str(PHASE18B_DIR / "phase18b_local_descriptor_control_audit.json"),
            "required_repair": "Do not use Phase18B local-control metrics as final descriptor comparison claims.",
        },
    ]


def overall_status(gates: list[dict[str, str]]) -> str:
    if all(row["gate_status"] == "PASS" for row in gates[:3]):
        return "READY_FOR_STRONG_BASELINE_EVALUATION"
    return "BLOCKED_STRONG_BASELINE_NOT_RUN"


def build_phase18g(
    input_manifest: Path,
    output_dir: Path,
    strong_embedding_manifest: Path | None = None,
    strong_pair_scores: Path | None = None,
) -> dict[str, Any]:
    rows = read_csv(input_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    handoff_rows = build_handoff_rows(rows)
    deps = dependency_status()
    gates = build_gate_rows(deps, strong_embedding_manifest, strong_pair_scores)
    status = overall_status(gates)

    handoff_csv = output_dir / "phase18g_strong_baseline_handoff_manifest.csv"
    gates_csv = output_dir / "phase18g_claim_gate.csv"
    requirements_json = output_dir / "phase18g_strong_baseline_requirements.json"
    write_csv(handoff_csv, handoff_rows, HANDOFF_COLUMNS)
    write_csv(gates_csv, gates, GATE_COLUMNS)
    requirements = {
        "required_models": [
            "MegaDescriptor-L-384 or current WildlifeTools MegaDescriptor equivalent",
            "DINOv2 or another strong foundation descriptor",
            "optional WildFusion/local matching scores",
        ],
        "required_return_columns": [
            "phase18_image_id",
            "descriptor_name",
            "embedding_row or embedding vector path",
            "embedding_dim",
            "sha256 or source image hash",
        ],
        "required_pair_score_columns": [
            "query_image_id",
            "candidate_image_id",
            "descriptor_name",
            "strong_descriptor_similarity",
            "strong_descriptor_rank",
        ],
        "bobcat_boundary": "Bobcat may receive embeddings/readiness scores, but no identity-accuracy claim without labels.",
    }
    write_json(requirements_json, requirements)

    audit = {
        "built_at_utc": now_utc(),
        "input_manifest": project_relative(input_manifest),
        "handoff_csv": project_relative(handoff_csv),
        "claim_gate_csv": project_relative(gates_csv),
        "requirements_json": project_relative(requirements_json),
        "image_rows": len(rows),
        "species_counts": dict(sorted(Counter(row["species"] for row in rows).items())),
        "dependency_status": deps,
        "strong_embedding_manifest_present": bool(strong_embedding_manifest and strong_embedding_manifest.exists()),
        "strong_pair_scores_present": bool(strong_pair_scores and strong_pair_scores.exists()),
        "phase18g_status": status,
        "scientific_claim_gate": status,
        "claim_boundary": (
            "Phase18G is a strong-baseline gate. It blocks final claims until "
            "strong descriptor embeddings or retrieval scores are supplied."
        ),
    }
    write_json(output_dir / "phase18g_strong_baseline_claim_gate_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18G Strong Baseline Claim Gate\n\n"
        "This phase prepares the strong-baseline handoff manifest and records why "
        "final descriptor-comparison claims are or are not allowed.\n\n"
        f"Current gate: `{status}`\n",
        encoding="utf-8",
    )
    return audit


def parse_optional_path(value: str) -> Path | None:
    return Path(value) if value else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=PHASE18A_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=PHASE18G_DIR)
    parser.add_argument("--strong-embedding-manifest", type=parse_optional_path, default=None)
    parser.add_argument("--strong-pair-scores", type=parse_optional_path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18g(
        input_manifest=args.input_manifest,
        output_dir=args.output_dir,
        strong_embedding_manifest=args.strong_embedding_manifest,
        strong_pair_scores=args.strong_pair_scores,
    )
    print("PASS phase18g strong baseline claim gate")
    print(f"image_rows={audit['image_rows']}")
    print(f"phase18g_status={audit['phase18g_status']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
