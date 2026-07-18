# Task 04: Automatic Pair-Evidence Extraction Contract

Status: complete. Contract version: `pferi_v2_automatic_pair_evidence_contract_v1`.

## Purpose

PF-ERI v2 can claim an increment beyond descriptor similarity only if its pair-evidence field is not simply another representation of descriptor similarity. This task therefore takes a deliberately restrictive position. The sole provisional primary automatic pair-evidence candidate is local-match coverage. Descriptor disagreement is retained for diagnostic or secondary sensitivity work, but is barred from the primary PF-ERI evidence set because it is calculated from descriptor outputs and could otherwise turn descriptor ensembling into an apparently independent evidence gain.

## Primary Candidate Definition

Local-match coverage is computed from the two decoded images using a registered automatic local-correspondence procedure and automatically detected subject regions. It is the fraction of the smaller detected subject region supported by mutual, geometrically consistent local correspondences. Its output must be invariant to reversing the endpoints of the canonical unordered pair. The extractor records the canonical pair identifier, value status, failure code, extractor version, runtime, and an endpoint-order check. No local support, unavailable subject region, and extractor failure are separate states; none may be silently represented as the same score.

The extractor may consume decoded pixels and registered local-correspondence and automatic-subject-region outputs. It may not consume descriptor similarity, candidate rank, review outcomes, identity truth, manual oracle annotations, historical v1 proxies or constants, or the columns of the independent-quality active control. This is a strict construct-validity boundary: the primary comparison must separate descriptor similarity, basic image quality, and local visual support rather than permit the same information to move among names.

## Consequence and Feasibility Gate

The primary model may consequently have only one automatic pair-evidence field after feasibility. That is an acceptable scientific outcome. Adding a second descriptor-derived score would improve apparent flexibility but weaken the stated incremental claim. A new automatic structural feature can be considered only through a versioned dictionary amendment, an outcome-blind registered extractor, and the same feasibility gate.

Workstream 02 must still establish automatic operation without manual rescue, nonconstant valid values, explicit failure and runtime logs, outcome-blind execution, and reproducible order invariance. Passing this contract does not establish successful matching, valid measurement, useful prediction, or routing benefit.

## Validation

`scripts/validate_v2_automatic_pair_evidence_contract.py` validates the contract at `schemas/pferi_v2/automatic_pair_evidence_contract_v1.json` against the v2 feature dictionary. It rejects descriptor-like, outcome, identity, manual, historical, and active-control inputs; it rejects direction-dependent output; and it prevents descriptor disagreement from entering the primary evidence set.

```bash
python3 scripts/validate_v2_automatic_pair_evidence_contract.py \
  --contract schemas/pferi_v2/automatic_pair_evidence_contract_v1.json \
  --dictionary schemas/pferi_v2/evidence_measurement_dictionary_v1.json \
  --audit-json path/to/automatic_pair_evidence_audit.json
```
