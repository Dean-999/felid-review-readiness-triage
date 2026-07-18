#!/usr/bin/env bash
# Verify that every Workstream 00 v1 source artifact still matches its SHA-256 anchor.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
inventory="$repo_root/docs/project-governance/workstreams/00_v1_evidence_isolation/v1_evidence_inventory.csv"

if ! command -v shasum >/dev/null 2>&1; then
  echo "FAIL: shasum is required to verify the v1 evidence inventory." >&2
  exit 2
fi

checked=0
while IFS=, read -r artifact_id artifact_class artifact_path observed_scope expected_sha v2_role v2_status rationale; do
  if [[ "$artifact_id" == "artifact_id" ]]; then
    continue
  fi
  full_path="$repo_root/$artifact_path"
  if [[ ! -f "$full_path" ]]; then
    echo "FAIL: missing $artifact_id at $artifact_path" >&2
    exit 1
  fi
  actual_sha="$(shasum -a 256 "$full_path" | awk '{print $1}')"
  if [[ "$actual_sha" != "$expected_sha" ]]; then
    echo "FAIL: hash mismatch for $artifact_id" >&2
    echo "expected=$expected_sha" >&2
    echo "actual=$actual_sha" >&2
    exit 1
  fi
  checked=$((checked + 1))
done < "$inventory"

echo "PASS: verified $checked v1 evidence artifacts against Workstream 00 SHA-256 anchors."
