# Superseded implementations and evidence retention

This register is the canonical explanation for implementation families that left
the active PF-ERI v2 tree. Exact historical source remains available in Git; the
active repository keeps current implementations, scientific results, frozen
inputs, provenance hashes, and regression tests for the failure that motivated a
replacement.

## Retention rule

- Keep final freezes, manifests, audit JSON, human-return records, scientific
  result tables, source hashes, and the current implementation.
- Remove old execution code, notebooks, implemented plans, duplicated transfer
  archives, and intermediate packages when a retained source or result exists.
- A suffix such as `*_v1` inside `schemas/pferi_v2/` is not itself evidence that
  the artifact belongs to the exploratory PF-ERI v1 project.
- `data/frozen/pferi_v2/` is an authoritative input store, not disposable build
  output, and is excluded from automated cleanup.

## Capability succession

### Timed operational rehearsal

The first interface allowed duplicate `(participant, packet)` submissions and
was retired. The accepted implementation requires restricted assignment, excludes
the retired pair ledger, and rejects duplicate or unassigned returns. The active
contract is `schemas/pferi_v2/timed_operational_rehearsal_contract_v2.json`; the
v1 contract and v1 defaults were removed. The response schema remains version 1
because it is the first response schema within PF-ERI v2, not the failed project
version.

### Local matcher

The original Kaggle runner was replaced by the robust v2 runner with frozen region
selection, defensive model-output parsing, two-direction measurement, provenance,
and result validation. The old runner, notebook, package builder, test, and
implemented plan/spec formed one superseded capability island and were removed
together. Current code lives in `gpu/kaggle_v2_local_matcher_v2/`.

### Structural-oracle reliability

The initial `current` analyzer could not evaluate the frozen reliability gate and
did not implement the corrected ordinal weighted-kappa/bootstrap calculation. The
corrected analyzer is `scripts/analyze_v2_structural_oracle_reliability.py`; the
old analyzer was removed. Historical audit hashes remain in the work log, while
the latest reliability audit/report remain under the v2 measurement-feasibility
outputs.

### Exploratory Phase 6-17 code

`scripts/legacy/` and `colab/archive/` contained early exploratory annotation,
retrieval, metric-learning, and packaging implementations. They are not imported
by the PF-ERI v2 execution chain and were removed from the active tree. On 18
July, the remaining 124 Phase 7–17 scripts and 16 directly coupled tests were
byte-preserved under `archive/pferi_v1/reproducibility/`. The archive manifest
records every original path, archive path, size, SHA-256, and source commit.
Top-level Phase18–19 files remain temporarily because the working tree contains
unfinished Phase18 changes; they are historical support code, not a v2 dependency.

### Photo-selection prototypes

The prototype scripts were implementation scaffolding for the final photo freeze.
The authoritative result is `data/frozen/pferi_v2/` with its manifests and audits;
prototype locations are not part of the scientific record and were removed.

## Workbook04 boundary

Workbook04 now reads one frozen capsule,
`schemas/pferi_v2/ws04_exploratory_context_v1.json`, instead of three legacy
Phase18 output paths. The capsule embeds the ten aggregate scenario-context rows
and records each original SHA-256. It cannot be used to set a v2 effect size,
decision threshold, calibration target, or confirmation claim.

The three Workbook04 scripts remain separate scientific stages—input audit,
sensitivity simulation, and allocation audit—because collapsing them would blur
their authorization boundaries. Their shared hashing/serialization code is small;
the repository therefore keeps the stage separation instead of introducing an
abstraction solely to reduce line count.

## Output cleanup

On 17 July 2026, `outputs/` contained roughly 29 GB across 19,162 files. About
15 GB was the authoritative final photo freeze and about 6 GB was the current v2
workspace. The cleanup deliberately targets only duplicated/superseded packaging:

- a legacy strong-baseline transfer ZIP whose returned results are retained;
- byte-identical or extracted `.zip`/`.zip.bin` execution copies;
- the Finder-style `structural_oracle_annotation_package 2` directory;
- reviewer-interface dry-run v1/v2 after completion of v3;
- compressed copies of retained matcher results and rehearsal directories;
- `.DS_Store` metadata.

`scripts/cleanup_superseded_artifacts.py` is dry-run by default. With `--apply` it
appends deleted-file size, SHA-256, rationale, and retained counterpart records to
`docs/project-governance/structure/2026-07-17_output_cleanup_manifest.csv` before
deletion. Scientific tables, audits, response logs, current extracted packages,
and all final-freeze files are outside its allowlist.

The follow-up whole-repository scan also covered model weights, NumPy arrays,
virtual environments, caches, temporary PDF renders, ZIP/TAR archives, annotation
snapshots, and large training tables. It removed four historical Phase11-13
training/candidate intermediates while retaining their generators, result tables,
summaries, and audits; one byte-identical full-frame matcher `.zip.bin`; the
incomplete `.venv` (it had no Python executable); `tmp/pdfs/original_plan/`; and
rebuildable Python/Finder caches. These are explicit cleanup targets, so the same
decisions can be reproduced with a dry run before applying them.
Four empty placeholder directories left behind by earlier packaging/cleanup work
were also removed; empty directories carry no Git or scientific provenance.

The scan deliberately retains the following objects despite archive-like names:

- the final freeze and all current v2/Workbook04 execution results;
- the unique YOLO weights and both historical strong-baseline embedding sets
  (the apparently parallel arrays have different SHA-256 values);
- 127 annotation backup files and five superseded-cleanup snapshots, because
  they record human annotation history rather than generated cache state;
- annotation batch and completed-return ZIPs, because the extracted directories
  do not contain equivalent image/return payloads;
- original and returned reviewer-delivery ZIPs, whose differing hashes document
  the handoff and completed human response;
- source-data caches under `sources/`, plus the local `.codegraph/` and
  `.repowise/` indexes.

Environment audit note: the deleted `.venv` contained partial site-packages but
no Python executable. The host system Python is 3.9 and cannot import current
code that uses `datetime.UTC`. The root README now states Python 3.11+ explicitly;
dependency locking remains a documented reproducibility gap rather than being
papered over by retaining a broken local environment.

Audit note: the first bulk run removed 403 files totalling 8,323,839,829 bytes.
A second one-file run was executed before append semantics were added and
overwrote the first run's detailed CSV. The static allowlist, retained-counterpart
guards, dry-run count, total byte count, and terminal record preserve the scope,
but the first run's individual SHA-256 rows cannot be reconstructed and are not
fabricated here. The remaining manifest row records the final 2,102-byte legacy
structural-oracle audit. All future runs append instead of overwrite.
