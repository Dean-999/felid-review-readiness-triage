# Mentor Progress Update 001

## Project Title

Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

## One-Sentence Definition

This project evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review.

## What This Project Is Not

This project does not identify individual animals, train a new Re-ID model, estimate population size, or claim that any review-readiness gate works yet. Re-ID embeddings, when used later, will be measurement signals for validation rather than the project's final product.

## Completed Work

- CzechLynx dataset downloaded and audited locally as the quantitative known-ID validation carrier.
- 200-image blinded pilot sample created with neutral review filenames.
- Manual triage completed for all 200 pilot images.
- Final consistency audit passed.
- Label distribution: 34 review-ready, 107 review-limited, 59 unidentifiable.
- 30-image second-review subset created; blinding audit passed.
- Phase 2 validation table and pair set created.
- Pair set summary: 200 validation rows, 100 unique IDs, 100 same-individual pairs, and 300 sampled different-individual pairs.

## Current Safeguards

- Manual triage was identity-blinded.
- Review images use neutral filenames.
- Raw data are not committed.
- Images and contact sheets will not be publicly displayed until license and display permissions are confirmed.
- Internal ID mappings remain separate from blinded review files.

## Current Pending Items

- Delayed 30-image intra-reviewer consistency check.
- CzechLynx license and citation verification.
- Embedding baseline selection.

## Planned Phase 2

Phase 2 will compare same-individual and different-individual similarity separation by triage group. The main validation question is whether review-ready images show stronger Re-ID reliability signals than review-limited or unidentifiable images.

This will be treated as pilot validation of the review-readiness rubric, not as proof of deployed individual identification.

## Planned Phase 3

Phase 3 will compare risk-coverage policies:

- no filter;
- balanced filter;
- strict filter.

The goal will be to assess how much false-match proxy risk may be reduced, and how much potential known matching evidence may be lost, under increasingly conservative triage policies.

## Questions for Mentor

- Is the review-readiness framing scientifically defensible?
- Are the triage categories appropriate for felid Re-ID?
- What pretrained embedding baseline would be most appropriate?
- How conservative should the strict filter be?
- What license/display cautions should be followed for CzechLynx examples?
