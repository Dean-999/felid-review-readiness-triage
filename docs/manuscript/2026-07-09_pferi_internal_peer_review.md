# Internal Peer Review: PF-ERI Manuscript Draft

Date: 2026-07-09

Manuscript reviewed:

`docs/manuscript/2026-07-09_pferi_pair_level_evidence_admission_manuscript_draft.md`

## Summary Assessment

The manuscript presents PF-ERI as a post-retrieval pair-level evidence admission layer for wildlife Re-ID candidate review. The central claim is clear and defensible: strong descriptors retrieve candidate pairs, while PF-ERI evaluates whether those pairs contain comparable evidence for review. The manuscript avoids the most dangerous overclaims about automatic identity assignment, Bobcat identity validation, and descriptor replacement.

The draft is suitable as a first manuscript assembly, but it still reads like a late-stage internal paper rather than a submission-ready journal article. The main scientific logic is strong. The manuscript needs stronger methodological reproducibility, cleaner figure/table integration, and tighter language around the small incremental model gain over descriptor plus quality.

Recommendation: major revision before external submission, minor revision for internal project use.

## Major Comments

1. The methods section does not yet provide enough detail for an outside reader to reproduce the candidate-pair construction. The draft states that MegaDescriptor and DINOv2 queues generated pairs, but it does not specify top-k depth, query selection, self-pair exclusion details, duplicate-pair handling, split discipline, or how the final 400 reviewed pairs were sampled from the broader queue. This can raise a targeted-sample-inflation objection. The manuscript should add a reproducibility paragraph that states the sampling design, the identical-row-set constraint, and the artifact paths that define the row contract.

2. The statistical description needs one more layer of specificity. The draft reports bootstrap confidence intervals but does not state the bootstrap unit or seed in the manuscript body. Because the project has repeatedly treated row/query dependence as a threat, the methods should state that uncertainty estimates used the available clustered or component-group design where applicable and should name any remaining limitations.

3. The abstract remains slightly long and includes too many internal safeguards for a journal abstract. It should keep the endpoint boundary, the main numbers, and the key limitation, but remove some explanation of why the full evidence package matters.

4. The Results section reports evidence well, but the figure/table plan remains in captions rather than integrated display items. This is acceptable for a Markdown draft, but a submission draft will need real Figure 2 and Table 2 built from the CSV outputs. The current manuscript should explicitly mark figure/table references as placeholders to avoid looking incomplete by accident.

5. The Choo et al. citation is now verified, but several author lists use "and others" rather than a consistent journal style. This is fine for a working draft, but final references should be exported from Zotero or Crossref and formatted in the target journal style.

## Minor Comments

1. The phrase "This distinction mattered" appears in the methods and sounds conversational. Replace it with a direct statement of the consequence for endpoint design.

2. The word "therefore" appears a few times in Results and Discussion. It is acceptable, but the final stop-slop pass should reduce formulaic inference markers.

3. The manuscript should italicize *Lynx lynx* only if it introduces the Latin species name. The current draft uses common names only, which is acceptable.

4. The discussion could include one sentence explaining why future stronger descriptors do not remove the pair-admission problem. The idea appears in the introduction, but the discussion should return to it.

5. The ethics and data availability sections need completion before submission. The placeholders are acceptable in this draft.

## Required Revisions Completed In Current Pass

The next revision pass should add a reproducibility paragraph for pair construction and row contracts, tighten the abstract, replace conversational wording, and label the figures/tables as planned display items rather than final display items.
