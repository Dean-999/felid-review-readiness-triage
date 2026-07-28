#!/usr/bin/env python3
"""Check the PF-ERI manuscript rewrite for common AI prose patterns."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "paper/manuscript/pferi_v2_manuscript_rewrite.md"
OUTPUT = ROOT / "paper/manuscript/pferi_v2_manuscript_rewrite_style_audit.json"


PATTERNS = {
    "em_dash": r"—",
    "throat_clearing": r"\b(?:here's (?:the thing|what|why)|it turns out|let me be clear|the truth is)\b",
    "emphasis_crutch": r"\b(?:this matters because|make no mistake|let that sink in|full stop)\b",
    "business_jargon": r"\b(?:lean into|deep dive|moving forward|circle back|navigate the landscape|unpack)\b",
    "meta_commentary": r"\b(?:the rest of this|let me walk you through|as we(?:'ll| will) see|in this section)\b",
    "rhetorical_prompt": r"\b(?:think about it|what if I told you|here's what I mean)\b",
    "binary_reversal": r"\bnot because\b[^.]+\bbecause\b|\b(?:the question|the answer) isn't\b[^.]+\bit's\b",
    "filler_adverb": r"\b(?:really|just|literally|genuinely|honestly|simply|actually|deeply|truly|fundamentally|inevitably|interestingly|importantly|crucially)\b",
    "promotional_closure": r"\b(?:rigorous foundation|clear route|complete path|decisive result|principal contribution)\b",
    "vague_value_claim": r"\b(?:demonstrat(?:e|es|ed) the value|scientific task itself)\b",
    "wh_sentence_start": r"(?:^|[.!?]\s+)(?:What|When|Where|Which|Who|Why|How)\b",
}


def audit(manuscript: Path = MANUSCRIPT, output: Path | None = OUTPUT) -> dict[str, Any]:
    text = manuscript.read_text(encoding="utf-8")
    prose = text.split("## References", 1)[0]
    matches = {
        name: [m.group(0) for m in re.finditer(pattern, prose, flags=re.IGNORECASE | re.MULTILINE)]
        for name, pattern in PATTERNS.items()
    }
    failures = [name for name, values in matches.items() if values]
    passive_candidates = re.findall(r"\b(?:was|were|is|are|be|been|being)\s+[a-zA-Z-]+(?:ed|en)\b", prose)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if len(s.split()) >= 3]
    lengths = [len(s.split()) for s in sentences]
    mean_length = sum(lengths) / len(lengths) if lengths else 0.0
    short_fraction = sum(n <= 10 for n in lengths) / len(lengths) if lengths else 0.0
    long_fraction = sum(n >= 25 for n in lengths) / len(lengths) if lengths else 0.0
    scores = {
        "directness": 10 if not failures else max(1, 10 - len(failures)),
        "rhythm": 10 if short_fraction >= 0.10 and long_fraction >= 0.10 else 8,
        "trust": 10 if not matches["rhetorical_prompt"] and not matches["emphasis_crutch"] else 7,
        "authenticity": 10 if not matches["binary_reversal"] and not matches["meta_commentary"] else 7,
        "density": 10 if not matches["filler_adverb"] and not matches["throat_clearing"] else 7,
    }
    result = {
        "audit_version": "pferi_v2_manuscript_stop_slop_audit_v1",
        "status": "PASS" if not failures else "FAIL",
        "manuscript": str(manuscript),
        "pattern_matches": matches,
        "passive_voice_candidates": passive_candidates,
        "sentence_count": len(sentences),
        "mean_sentence_words": round(mean_length, 2),
        "short_sentence_fraction": round(short_fraction, 3),
        "long_sentence_fraction": round(long_fraction, 3),
        "scores": scores,
        "total_score": sum(scores.values()),
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
