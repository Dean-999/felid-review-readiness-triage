# PF-ERI v2 manuscript source-data manifest

This directory is the paper-facing evidence map for the new PF-ERI v2 manuscript. It is separate from the historical v1 source-data package in the parent directory.

`evidence_source_manifest.csv` and `.md` bind each manuscript evidence source to its path, SHA-256, file size, row count where applicable, scientific role, stage, and access class. `claim_evidence_map.csv` and `.md` map every planned manuscript claim to its supporting evidence and interpretation boundary. `source_manifest_audit.json` records fail-closed validation of hashes, declared row counts, and the principal cross-stage scientific invariants. `CHECKSUMS.sha256` covers the generated package.

Regenerate with `python3 scripts/build_pferi_v2_manuscript_source_manifest.py`. The command refuses to write a passing package when a frozen source is missing, changed, row-count inconsistent, or semantically inconsistent with the declared Task15I-through-closure evidence chain.
