<claude-mem-context>
# Memory Context

# [felid-review-readiness-triage] recent context, 2026-06-17 2:26pm GMT+8

No previous sessions found.
</claude-mem-context>

<!-- CODEGRAPH_START -->
## CodeGraph

In this repository, CodeGraph is a code-structure tool. Use it first when the
task is to locate scripts, understand functions, trace call paths, or inspect
implementation structure.

Project-specific guardrail:

- CodeGraph is not the source of truth for scientific phase status, CSV
  contents, photo validity, image quality, or final candidate counts.
- For Bobcat/CzechLynx data decisions, verify with actual CSV/JSON manifests,
  audit files, file inventories, and direct row counts.
- If a broad Bobcat photo-selection query returns old CzechLynx legacy scripts,
  treat that as a retrieval miss. Narrow the query or inspect the concrete
  artifact paths instead of following the irrelevant legacy path.
- Do not use CodeGraph output to override project rules, human review decisions,
  or artifact audits.

Binding rule:

```text
CodeGraph can answer "where is the code?"
It cannot answer "which photos are valid?" or "what phase is scientifically correct?"
```
<!-- CODEGRAPH_END -->
