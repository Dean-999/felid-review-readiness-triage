# PF-ERI Manuscript Source Data Package

Date: 2026-07-10

This package maps each manuscript display item to generated files, source
artifacts, generation commands, and claim boundaries. It is a manifest package;
it does not duplicate the underlying CSV/JSON artifacts.

## Claim Boundary

CzechLynx human reviewability/evidential admissibility and review-routing utility only; no automated identity assignment, Bobcat identity accuracy, retrieval mAP, MRR, top-k identity improvement, or universal cross-domain risk-control guarantee.

## Files

- `display_item_source_map.csv` and `.md`: display-item to source-artifact map.
- `source_file_manifest.csv` and `.md`: file-level manifest with size, SHA-256,
  and CSV row counts where applicable.
- `source_data_package_audit.json`: build audit and regeneration commands.

## Regeneration Commands

```bash
python3 scripts/build_story_hardening_issue1_figure.py
python3 scripts/build_manuscript_figures_tables.py
python3 scripts/build_manuscript_source_data_package.py
```
