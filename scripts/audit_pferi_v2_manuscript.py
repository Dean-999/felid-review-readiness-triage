#!/usr/bin/env python3
"""Audit the PF-ERI v2 manuscript against frozen paper-facing displays."""
from __future__ import annotations

import csv
import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "paper/manuscript/pferi_v2_manuscript_draft.md"
OUTPUT = ROOT / "paper/manuscript/pferi_v2_manuscript_audit.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(manuscript: Path = MANUSCRIPT, output: Path | None = OUTPUT) -> dict[str, Any]:
    text = manuscript.read_text(encoding="utf-8")
    table3 = read_csv(ROOT / "paper/tables/pferi_v2/table3_pair_inventories.csv")
    table4 = read_csv(ROOT / "paper/tables/pferi_v2/table_s4_reviewer_agreement.csv")
    table5 = read_csv(ROOT / "paper/tables/pferi_v2/table5_stage_results.csv")
    failures: list[str] = []

    required_strings = {
        "development_increment": table5[0]["p3_minus_p5"],
        "confirmation_increment": table5[-1]["p3_minus_p5"],
        "confirmation_lower": "-0.224671",
        "confirmation_upper": "-0.179068",
        "supported_count": "252",
        "unsupported_count": "637",
        "development_pairs": "1,600",
        "development_kappa": table4[0]["cohen_kappa_binary"],
        "calibration_kappa": table4[1]["cohen_kappa_binary"],
        "confirmation_kappa": table4[2]["cohen_kappa_binary"],
        "major_deviation": "major protocol deviation",
        "scope_boundary": "execution-validation scope",
        "sole_author_contribution": "The sole author",
        "independent_reviewer_acknowledgement": "four independent reviewers",
        "no_external_funding": "This research received no external funding.",
        "no_competing_interests": "The author declares no competing interests.",
    }
    for name, value in required_strings.items():
        if value not in text:
            failures.append(f"missing_required:{name}:{value}")

    prohibited = {
        "internal_task17": r"\bTask17\b",
        "p5_confirmed_superior": r"P5 (?:was|is) confirmed superior",
        "identity_accuracy_improved": r"identity accuracy (?:was )?improved",
        "deployment_ready": r"(?:is|was|establish(?:es|ed)?|demonstrat(?:es|ed)?) (?:a )?deployment[- ]ready",
        "fully_clean_claim": r"(?:is|was) a fully clean preregistered confirmation",
    }
    for name, pattern in prohibited.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            failures.append(f"prohibited_claim:{name}")

    for row in table3:
        if row["stage_or_subset"] == "Task15M full queue":
            if row["descriptor_supported_n_percent"] != "252 (28.3%)" or row["descriptor_unsupported_n_percent"] != "637 (71.7%)":
                failures.append("display_inventory_drift")

    reference_dois = re.findall(r"https://doi\.org/([^\s)]+)", text.split("## References", 1)[-1], flags=re.IGNORECASE)
    if len(reference_dois) < 12:
        failures.append("insufficient_verified_references")
    if len(reference_dois) != len(set(doi.lower() for doi in reference_dois)):
        failures.append("duplicate_reference_doi")

    bracket_placeholders = re.findall(r"^\[[^\n]+\]$", text, flags=re.MULTILINE)
    if bracket_placeholders:
        failures.extend(f"unresolved_placeholder:{p}" for p in bracket_placeholders)

    try:
        manuscript_label = str(manuscript.relative_to(ROOT))
    except ValueError:
        manuscript_label = str(manuscript)
    result = {
        "audit_version": "pferi_v2_manuscript_audit_v1",
        "status": "PASS" if not failures else "FAIL",
        "manuscript": manuscript_label,
        "word_count": len(re.findall(r"\b[\w'-]+\b", text)),
        "reference_doi_count": len(reference_dois),
        "remaining_author_metadata_placeholders": bracket_placeholders,
        "models_refit": False,
        "task15l_parameters_recomputed": False,
        "checked_boundaries": list(prohibited),
        "checked_required_values": required_strings,
        "failures": failures,
    }
    if output is not None:
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manuscript", type=Path, default=MANUSCRIPT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = audit(args.manuscript.resolve(), args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
