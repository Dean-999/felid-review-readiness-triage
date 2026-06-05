# Expanded CzechLynx Pilot Feasibility Decision

## Purpose

The current 200-image CzechLynx pilot is complete and supports the core pilot workflow: Phase 1 manual triage passed, ResNet-50 and MegaDescriptor-S-224 baselines were completed, and Phase 3/3B risk-coverage analyses were completed.

MegaDescriptor-S-224 strengthened Q1 to moderate pilot-level support, but the remaining weakness is evidence sparsity in the strict ready-ready subset. The strict filter retains only 3 same-individual pairs, so the expanded pilot question is whether more same-pair evidence can be planned without compromising blinding or project boundaries.

This document is a feasibility and design decision only. It is not a final sampling file, not a labeling file, and not a scientific claim.

## Why Expansion Is Needed

The 200-image pilot has enough evidence to show a pilot-level review-readiness signal, but it remains limited for strict ready-ready interpretation. Larger pair sampling from the same 200 images cannot solve this because the number of same-individual pairs is constrained by how many images per known working ID are already present and how many of those images were labeled review-ready.

Expanded image sampling is therefore the appropriate next planning direction. The goal is to increase the number of within-ID image combinations before any future pair construction or model measurement step.

## Feasibility Results

The planning script `scripts/plan_czechlynx_expanded_pilot_sampling.py` read the CzechLynx real manifest, the current pilot internal map, and the finalized 200-image triage labels. It excluded the current pilot images by manifest path and verified that local path exclusion produced the same row count.

Aggregate additional availability:

| Additional images per working ID | Working IDs available |
|---:|---:|
| 2 or more | 319 |
| 3 or more | 318 |
| 4 or more | 316 |
| 5 or more | 312 |
| 6 or more | 306 |

Current pilot triage distribution:

| Triage label | Count |
|---|---:|
| review-ready | 34 |
| review-limited | 107 |
| unidentifiable | 59 |

The rough review-ready rate used for planning estimates is 17%. These readiness estimates are simple feasibility assumptions only, not predictions or final claims.

Candidate designs:

| Design | Candidate IDs available | Manual workload | Same pairs per ID | Maximum same pairs | Estimated ready-ready same pairs | Feasible |
|---|---:|---:|---:|---:|---:|---|
| 100 IDs x 4 images | 316 | 400 images | 6 | 600 | 17.34 | yes |
| 125 IDs x 4 images | 316 | 500 images | 6 | 750 | 21.68 | yes |
| 150 IDs x 3 images | 318 | 450 images | 3 | 450 | 13.01 | yes |
| 250 IDs x 2 images | 319 | 500 images | 1 | 250 | 7.23 | yes |

## Recommendation

Use `125 IDs x 4 images` as the recommended expanded-pilot planning default if the next implementation slice is approved.

Rationale:

- It is feasible by aggregate image availability.
- It gives the highest same-pair ceiling among the candidate designs: 750 same-individual pairs.
- It keeps the manual workload at 500 images, comparable to the other high-workload options.
- Under the simple 17% readiness-rate assumption, it yields the highest expected ready-ready same-pair count among the tested designs.

This recommendation is a design default for the next sampling slice. It does not create final labels, does not copy images, and does not establish a final scientific result.

## Risks And Stop Conditions

Main risks:

- The current pilot review-ready rate may not hold in the expanded sample.
- More images per working ID may include near-duplicate encounter structure unless future sampling controls are added.
- Manual review workload increases substantially from 200 to 500 images.
- Strict ready-ready evidence may still remain smaller than expected after manual labeling.

Stop conditions for the next slice:

- Required blinding cannot be preserved.
- Expanded review files would expose internal IDs, original identity paths, latitude, longitude, exact location, cell code, or trap ID.
- Any second-review file would be needed.
- The expanded sample cannot be generated without modifying raw data or existing final labels.
- The expanded sample cannot provide a meaningful increase in same-pair evidence after feasibility checks.

## Next Implementation Slice

If approved, the next slice should create a deterministic expanded-pilot sampling script for the recommended `125 IDs x 4 images` design.

That future script should:

- sample eligible working IDs and image rows deterministically with fixed seeds;
- preserve internal mapping separately from blinded review files;
- copy review images only after explicit approval;
- create blinded manual-label templates without sensitive metadata;
- avoid second-review files entirely;
- write generated artifacts only under approved `data/interim/` and `outputs/` locations;
- keep generated data and outputs uncommitted.

Generated feasibility outputs from this slice:

- `outputs/czechlynx/planning/expanded_pilot_feasibility_summary.csv`
- `outputs/czechlynx/qc/expanded_pilot_feasibility_report.txt`
