# Sources Cache Map

This directory preserves literature search outputs and research synthesis notes. It is not runtime code.

## File Types

| Type | Meaning | Cleanup rule |
|---|---|---|
| `*.md` | Human-readable literature synthesis or gap analysis. | Keep visible. |
| `*openalex.json` | Raw OpenAlex search results. | Keep for reproducibility unless clearly obsolete and summarized. |
| `*crossref.json` | Raw Crossref metadata. | Keep for citation traceability. |
| `*ncbi*` / `*taxonomy*` | Taxonomy/species-scope evidence. | Keep. |
| other `*.json` | Search or model/tool discovery cache. | Review before deletion. |

## Current Human-Readable Research Notes

- `2026-06-17_patterned_felid_reid_evidence_utility_literature_scan.md`
- `2026-06-17_pferi_gap_model_map.md`
- `2026-06-17_pferi_research_gap_workflow_assessment.md`
- `phase8_reid_tool_dataset_search_summary.md`

## Cleanup Rule

Do not delete raw JSON just because it is large. These files document exactly what was searched and are useful for citation traceability and context recovery.

Safe cleanup requires:

1. a synthesis markdown file that cites or summarizes the raw file;
2. confirmation that the query is no longer needed;
3. no active doc references to the raw file.
