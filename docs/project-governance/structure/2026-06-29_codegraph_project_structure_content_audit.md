# CodeGraph Project Structure And Content Audit

Date: 2026-06-29

Follow-up status: Priority 1 documentation fixes were implemented after this
audit. The original findings are preserved because they explain why the changes
were needed.

Implemented follow-up files:

- `docs/legacy-code17/README.md`
- `docs/structure/current_pipeline_manifest.md`
- `docs/logs/daily_work_log.md`
- updates to `PROJECT_RULES.md`, `docs/README.md`,
  `docs/CURRENT_PROJECT_MAP.md`, `docs/legacy-code16/README.md`,
  `docs/structure/csv_and_artifact_inventory.md`, and `scripts/README.md`

Scope: whole repository structure, documentation logic, naming discipline, and
current scientific-claim alignment.

Method:

- CodeGraph was used for the indexed project code surface.
- Current CodeGraph index covers Python/YAML only: 329 files, 6,438 nodes, and
  15,814 edges.
- Markdown, raw data, generated outputs, and manuscript text were audited by
  file inventory, headings, targeted content search, and line-level inspection.
- Generated outputs and local data were not content-audited as primary source
  files except where their tracked/ignored status affects project structure.

## First-Principles Standard

The repository should make five things immediately clear:

1. What the project is currently trying to prove.
2. What it is explicitly not allowed to claim.
3. Which scripts reproduce the current evidence chain.
4. Which files are historical context rather than active workflow.
5. Which artifacts are source evidence, generated outputs, local data, or
   publication-facing narrative.

By this standard, the scientific claim boundary is strong. The main weakness is
not the research direction; it is the discoverability of the active execution
chain inside a large historical repository.

## High-Level Finding

The project direction is coherent:

PF-ERI is now framed as a post-retrieval pair-level evidence reliability and
review-routing layer, not a descriptor replacement, not a new Re-ID model, and
not an automatic identity-assignment system.

This is consistently enforced in:

- `README.md`
- `PROJECT_RULES.md`
- `docs/CURRENT_PROJECT_MAP.md`
- `docs/legacy-code16/legacy-code16i_gap_rationale.md`
- `docs/legacy-code16/README.md`
- `docs/superpowers/plans/2026-06-29-legacy-code17a-czechlynx-review-utility.md`

The biggest structural risk is that the active pipeline is surrounded by many
historical scripts and plans. CodeGraph search itself exposed this: broad
architecture queries can surface Phase12/legacy-code14 historical utilities before
the legacy-code16/legacy-code17 scripts, because many old scripts share similar names,
function shapes, and scientific vocabulary.

That is a repository-navigation risk, not a scientific failure.

## Folder-By-Folder Audit

### Root

Current role: project entrypoint and binding rules.

Strengths:

- `README.md` gives the current title, contribution, claim boundary, dataset
  status, and legacy-code17a result interpretation.
- `PROJECT_RULES.md` is strong and unusually explicit about blocked claims,
  escalation rules, descriptor-only controls, and Bobcat identity-label limits.
- `.gitignore` correctly excludes local data, outputs, virtual environments,
  CodeGraph indexes, and OS/editor noise.
- `AGENTS.md` now includes the CodeGraph usage rule.

Risks:

- `AGENTS.md` still contains a stale memory-context block saying no previous
  sessions were found. This is harmless for execution but weak as a project
  memory artifact.
- `.DS_Store` files exist locally in the repository tree. They appear ignored,
  but their presence adds noise to local audits.
- `data/` is ignored, but one data CSV is tracked:
  `data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv`.
  That may be intentional, but it should be documented as a deliberate tracked
  exception.

Verdict: root framing is strong. Cleanliness/documentation exceptions remain.

### docs/

Current role: canonical project map, phase history, locked claim boundary, and
execution plans.

Strengths:

- `docs/README.md` defines a read order.
- `docs/CURRENT_PROJECT_MAP.md` correctly identifies the active core and
  separates historical layers from current legacy-code16/17 review utility.
- `docs/legacy-code16/legacy-code16i_gap_rationale.md` is the strongest claim-boundary
  document in the repository. It directly anticipates reviewer objections.
- `docs/archive/` separates superseded plans/specs from active framing.
- `docs/structure/` already contains inventory and cleanup history.

Risks:

- At audit time there was no `docs/legacy-code17/README.md`, even though legacy-code17a was
  active and had executable code/tests. legacy-code17 lived inside
  `docs/legacy-code16/README.md` and `docs/superpowers/plans/`, which made it feel
  like an appendix rather than the current validation layer. This was fixed in
  the follow-up documentation pass.
- `docs/legacy-code16/README.md` still has a `Next Step` section that starts with
  legacy-code16e scoring and manual-audit flow, even though later sections already
  document legacy-code16g/H/I and legacy-code17a. This creates chronological ambiguity.
- `docs/superpowers/plans/` contains very long execution plans. They are useful
  as audit trails, but they should not be the primary way to understand current
  project state.
- Some older phase README files are intentionally short. That is fine, but only
  because `docs/CURRENT_PROJECT_MAP.md` acts as the current navigation layer.

Verdict: documentation logic is strong, but the legacy-code17 layer should become a
first-class documented phase.

### scripts/

Current role: local executable pipeline scripts.

Measured structure:

- 227 tracked script files under `scripts/`.
- 113 Python files under `scripts/legacy/`.
- 113 top-level Python scripts remain in `scripts/`.
- 14 tracked test files in `tests/`.

Strengths:

- Most scientific scripts use phase-prefixed names, which is good for audit
  traceability.
- Current legacy-code16/17 scripts have more explicit claim-boundary naming than the
  older code.
- legacy-code17a has a test and a dedicated executable script:
  `scripts/build_legacy-code17a_czechlynx_review_utility.py`.
- The current code avoids hiding the claim boundary inside a generic model
  score. It preserves descriptor-only, quality-only, evidence-only,
  conflict-penalized, and diagnostic-review-utility policies.

Risks:

- `scripts/` root is too crowded to function as "active scripts only." It
  contains many Phase11-15 historical scripts alongside current legacy-code16/17
  utilities.
- The existence of `scripts/legacy/` is good, but the split is incomplete.
  A new collaborator cannot infer that every root-level script is active.
- Test coverage is concentrated around the recent scientific contract and
  legacy-code16/17 code. That is acceptable only if older root scripts are historical.
  If root means active, the test story becomes weak.
- legacy-code17a is a single 492-line scientific script. That is acceptable for now,
  but future legacy-code17b/17C work should factor shared review-utility evaluation
  helpers rather than copy/paste the same metric blocks.

Verdict: code logic is serviceable; script organization is the most important
repository-structure weakness.

### tests/

Current role: contract and regression tests for current pipeline logic.

Strengths:

- The tests focus on recent high-risk scientific logic: legacy-code16g contracts,
  legacy-code16h controls/router behavior, and legacy-code17a review utility.
- This matches the project's real risk surface: claim-boundary mistakes matter
  more than old exploratory script behavior.

Risks:

- There is no single manifest explaining which scripts are considered current
  and therefore test-required.
- Without such a manifest, reviewers can reasonably ask why many top-level
  scripts have no direct tests.

Verdict: tests are directionally right, but they need a current-pipeline
manifest to define the expected coverage boundary.

### colab/

Current role: cloud/offline execution support.

Strengths:

- `colab/README.md` clearly separates active utilities from archived diagnostic
  metric-learning experiments.
- `archive_metric_learning/` makes the Phase9-11 metric-learning line visibly
  historical.
- `legacy-code15_calibrated_ranker_colab.py` is correctly framed as optional and
  control-bound.

Risks:

- `legacy-code14_megadetector_selection/` remains active-looking even though its main
  function is older data construction support. This is defensible, but it should
  be described as data-foundation support, not current modeling.
- The active/archive split is clearer in `colab/` than in `scripts/`, which
  creates an inconsistency in repository hygiene.

Verdict: good, but `scripts/` should learn from this folder's clearer split.

### data/

Current role: local data and one tracked label artifact.

Strengths:

- Data are generally ignored, which is correct for local image/data artifacts.

Risks:

- One CzechLynx label CSV is tracked despite the broad `data/` ignore rule.
  That can be valid, but it needs an explicit reason in the artifact inventory.
- Local data contains many `.DS_Store` files. They are ignored, but they should
  be cleaned before packaging or sharing local archives.

Verdict: acceptable if the tracked CSV exception is intentional and documented.

### outputs/

Current role: generated, ignored experiment outputs.

Strengths:

- Generated outputs are ignored, which prevents the repository from becoming an
  accidental artifact dump.
- Docs and scripts name the output paths clearly.

Risks:

- Because outputs are ignored, the repository's committed evidence depends on
  summaries in documentation and reproducible scripts/tests. This is fine, but
  key result summaries must remain committed in docs.
- If legacy-code17a becomes central to a paper claim, consider committing a tiny
  derived summary table or audit digest rather than the full generated output.

Verdict: correct policy; make sure important results are summarized in tracked
docs.

### sources/

Current role: tracked literature/source-evidence corpus.

Strengths:

- Literature evidence and source notes are versioned, which supports the
  project gap argument.

Risks:

- `sources/` is not prominent in the main read order. A reviewer can miss that
  the literature basis exists.
- If source files include downloaded metadata, the project should avoid mixing
  raw external dumps with interpreted notes without clear naming.

Verdict: valuable, but it needs a clearer place in the project map.

### paper/

Current role: historical manuscript-like draft.

Strengths:

- `paper/project_report_draft.md` opens with a clear supersession note and says
  not to treat it as the final manuscript.

Risks:

- The folder name `paper/` is stronger than the warning inside the file. A new
  reader may assume this is the current manuscript.
- The draft still contains old Phase1-8 framing and should not be the default
  publication-facing entrypoint.

Verdict: content warning is good; folder/file naming remains misleading.

## Naming Audit

Good patterns:

- Phase-prefixed files make chronology auditable.
- Current scripts are descriptive and include the dataset/task in the name.
- The current documentation consistently avoids claiming descriptor replacement
  or identity assignment.

Naming risks:

- `legacy-code16g`, `legacy-code16g`, and `legacy-code16g_` appear in different contexts. This is
  not fatal, but titles should prefer `legacy-code16g` and file names should prefer
  `legacy-code16g_`.
- legacy-code17a currently appears inside legacy-code16 documentation, which weakens the
  mental model that legacy-code17 is a validation layer after legacy-code16i.
- `paper/project_report_draft.md` sounds active despite being historical.
- `review_action_label` style fields must remain explicitly described as proxy
  review actions unless a human audit creates true expert labels.

## Content Logic Audit

The core scientific logic is now well aligned:

- Descriptor-only remains a required strong baseline.
- PF-ERI is not being positioned as a descriptor replacement.
- CzechLynx known-ID results support false-candidate and positive-retention
  analysis.
- UWIN/FCF bobcat remains field-readiness or review-readiness evidence unless
  verified identity labels or audited pair labels are available.
- legacy-code17a correctly reframes value around review utility rather than forcing a
  top-k ranking-improvement claim.

The main content issue is chronological staleness in navigation:

- `docs/legacy-code16/README.md` has an older `Next Step` block before newer legacy-code16g,
  legacy-code16h, legacy-code16i, and legacy-code17a sections.
- At audit time there was no first-class `docs/legacy-code17/README.md`; this was
  fixed in the follow-up documentation pass.
- The current pipeline is understandable after reading several docs, but it is
  not yet expressed as a single manifest.

## Adversarial Review

Reviewer attack: "Your repository says legacy-code17a is important, but there was no
legacy-code17 documentation folder at audit time. Was this an afterthought?"

Response: Create `docs/legacy-code17/README.md` and make it the current validation
entrypoint.

Reviewer attack: "The scripts folder is full of old experiments. How do I know
which scripts reproduce the current claim?"

Response: Add a current-pipeline manifest that lists active scripts in order,
their inputs, outputs, tests, and allowed claims. Later, move historical root
scripts into archive folders only after import/path impact is checked.

Reviewer attack: "You say data are ignored, but there is a tracked data CSV."

Response: Document the tracked label CSV as an intentional minimal label
artifact, or move it out of `data/` into a clearly versioned `fixtures/` or
`metadata/` path if it is meant to support tests/reproducibility.

Reviewer attack: "The legacy-code17a review actions are proxy labels, not expert
labels."

Response: Keep the word `proxy` in every output/report/claim until expert audit
labels exist. Do not use proxy review-action metrics as human-agreement claims.

Reviewer attack: "The current paper folder contains historical claims."

Response: Rename or relocate the historical draft, or add `paper/README.md`
that states there is no current manuscript yet and points to the active docs.

Reviewer attack: "Your contribution sounds weaker than descriptor-only."

Response: The project no longer competes on descriptor replacement as the main
claim. The gap is post-retrieval evidence admissibility, review routing,
false-candidate burden, positive retention, risk coverage, and expert-audit
agreement. This boundary is strong and should remain locked.

## Priority Fixes

Priority 0: no science-blocking inconsistency found.

Priority 1:

- Done: add `docs/legacy-code17/README.md`.
- Done: update the stale `Next Step` section in `docs/legacy-code16/README.md`.
- Done: add a current-pipeline manifest under `docs/structure/`.
- Done: document the tracked `data/labels/czechlynx/...csv` exception.

Priority 2:

- Add `scripts/README.md` or `scripts/ACTIVE_PIPELINE.md` that marks scripts as
  active, support, historical, or legacy.
- Plan a low-risk archive move for old top-level scripts only after checking
  imports, tests, and documentation references.
- Factor repeated legacy-code17 review-utility metric code if legacy-code17b/17C repeats
  the same evaluation patterns.

Priority 3:

- Remove local `.DS_Store` files.
- Add `paper/README.md` or rename the historical draft to make its status
  impossible to miss.
- Add `sources/README.md` or link `sources/` from `docs/CURRENT_PROJECT_MAP.md`.

## Confidence Loop

Question: do I have 100% confidence that the current strategy is structurally
safe?

Answer: not yet, because the active chain is still too distributed across
legacy-code16 docs, legacy-code17 scripts, long superpowers plans, and a crowded script root.

Vulnerabilities found:

- legacy-code17 is active but not first-class in `docs/`.
- Old scripts remain mixed with current scripts.
- One tracked data artifact conflicts with the broad `data/` ignore mental
  model.
- Historical manuscript draft lives under an active-sounding `paper/` folder.

Repair strategy:

1. Make legacy-code17 first-class in documentation.
2. Create a current-pipeline manifest before moving files.
3. Document artifact exceptions before changing data paths.
4. Preserve claim-boundary language exactly; do not broaden claims while
   cleaning structure.

After these repairs, the repository would be much closer to adversarially robust
because a reader could distinguish current claim, current pipeline, historical
experiments, and generated artifacts without relying on memory.
