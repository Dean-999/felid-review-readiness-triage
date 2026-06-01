# Data Roles

## Purpose

This document defines the role of each data source in the project.

The project uses three data categories:

1. CzechLynx / Eurasian Lynx
2. UWIN/WildTrax Bobcat and Canada Lynx
3. Marbled Cat

These data sources must not be treated as interchangeable.

## Role Summary Table

| Data Source | Role | What It Can Support | What It Cannot Support |
|---|---|---|---|
| CzechLynx / Eurasian Lynx | Quantitative known-ID validation carrier | Q1 reliability test, Q2 risk–coverage trade-off, same/different pair construction, pairwise false-match risk proxy | The project should not become a Eurasian lynx-only Re-ID project |
| UWIN/WildTrax Bobcat and Canada Lynx | Field motivation and field-readiness stress test | Field image readiness distribution, real camera-trap failure modes, examples of blur/occlusion/night IR/partial body/angle instability | Strict identity validation without verified individual IDs |
| Marbled Cat | Future Asian conservation application scenario | Discussion, future readiness checklist, Asian felid conservation relevance | Current performance validation or Marbled Cat Re-ID claims |

## CzechLynx / Eurasian Lynx

### Role

CzechLynx is the quantitative known-ID validation carrier.

It is used because it provides camera-trap images with verified individual IDs. This allows construction of same-individual and different-individual pairs, which are necessary for testing whether review-readiness labels correspond to measurable Re-ID reliability.

### Why CzechLynx Is Needed

The project’s core questions require known identities:

- Q1 requires same-individual versus different-individual similarity comparison.
- Q2 requires known-match retention and false-match proxy analysis.

Without known IDs, the project cannot validate Re-ID behavior.

### What CzechLynx Supports

CzechLynx supports:

- review-ready / review-limited / unidentifiable triage validation;
- same-individual pair construction;
- different-individual pair construction;
- embedding similarity comparison;
- same/different separation analysis;
- pairwise separability metrics;
- risk–coverage trade-off analysis;
- retained identity count;
- retained same-pair coverage;
- known-match loss;
- dataset-specific operating point analysis.

### What CzechLynx Does Not Support

CzechLynx does not support:

- a claim that the project is only about Eurasian lynx;
- a claim that thresholds transfer directly to Bobcat, Canada Lynx, or Marbled Cat;
- a claim that the project validates all felids;
- a claim that the project measures real-world deployment false-match rate;
- a claim that the project estimates population size.

### Required Boundary Sentence

CzechLynx is the known-ID validation carrier, not the biological scope of the project.

## UWIN/WildTrax Bobcat and Canada Lynx

### Role

UWIN/WildTrax images are used for field motivation and field-readiness stress testing.

They represent the real camera-trap workflow that motivated the project. The user’s UWIN-Atlanta tagging work shows that many images are species-level usable but not necessarily reliable for individual-level evidence.

### Why UWIN/WildTrax Is Needed

CzechLynx provides known-ID validation, but it does not fully represent the field conditions that motivated the project.

UWIN/WildTrax can show:

- motion blur;
- night IR artifacts;
- occlusion;
- partial body views;
- angle instability;
- repeated detections;
- species-level uncertainty;
- real tagging ambiguity.

### What UWIN/WildTrax Supports

UWIN/WildTrax supports:

- field motivation;
- triage stress testing;
- review-readiness distribution;
- failure-mode taxonomy;
- examples of why species-level tagging is not the same as individual-level readiness;
- explanation of how a high school student discovered the problem through real conservation tagging work.

### What UWIN/WildTrax Does Not Support

UWIN/WildTrax does not support:

- strict Re-ID accuracy;
- true individual identification;
- true individual count;
- population estimation;
- same/different pair validation;
- false-match risk measurement;
- claims that a candidate match is a true identity.

### Required Boundary Sentence

UWIN/WildTrax field images are used to test the applicability of the review-readiness rubric in real camera-trap conditions, not to validate individual identity.

## Marbled Cat

### Role

Marbled Cat is a future Asian conservation application scenario.

It is included because it is an Asian forest felid with conservation relevance and camera-trap monitoring value. However, it is not part of the current experimental validation.

### Why Marbled Cat Is Included

The project is intended to develop a workflow logic that may later help Asian felid conservation projects.

Marbled Cat is suitable as a future application example because:

- it is a forest-dependent Asian felid;
- its status and distribution are not fully understood;
- camera traps are relevant for documenting rare or elusive felids;
- future monitoring projects may need a cautious pre-Re-ID readiness protocol.

### What Marbled Cat Supports

Marbled Cat supports:

- future application discussion;
- future data requirement checklist;
- Asian conservation relevance;
- explanation of how the readiness protocol could be transferred conceptually.

### What Marbled Cat Does Not Support

Marbled Cat does not support:

- current Re-ID validation;
- performance claims;
- similarity thresholds;
- identity prediction;
- population estimation;
- direct transfer from CzechLynx results.

### Required Boundary Sentence

Marbled Cat is not validated in the current study. It is included only as a future application scenario requiring authorized known-ID data, metadata, repeated detections, and species-specific calibration.

## Data Separation Rules

### Rule 1: Do Not Mix Validation Levels

Every project result must be assigned to one of three evidence levels:

1. Quantitative validation
2. Field stress test
3. Future application

### Rule 2: Only CzechLynx Can Validate Q1 and Q2

Only CzechLynx can support Q1 and Q2 because only CzechLynx has verified individual IDs in the current plan.

### Rule 3: WildTrax Cannot Become Identity Evidence

WildTrax can show field difficulty, but it cannot be used as identity ground truth without verified IDs.

### Rule 4: Marbled Cat Cannot Become Current Experimental Data

Marbled Cat must remain in the Discussion or Future Application section unless authorized known-ID Marbled Cat data become available.

### Rule 5: Thresholds Are Dataset-Specific

Any threshold or operating point derived from CzechLynx must be described as dataset-specific.

## Data Access Notes for Future Phase 1

Phase 1 must record:

### CzechLynx

- source;
- version;
- license;
- image count;
- individual count;
- identity label structure;
- metadata fields;
- split definitions;
- allowed use;
- citation requirement;
- whether sample images may be shown.

### WildTrax/UWIN

- source project;
- permission to view images;
- permission to show images;
- available species labels;
- available metadata;
- absence of verified individual IDs;
- privacy or location concerns;
- aggregation rules for reporting.

### Marbled Cat

- no current data;
- future application only;
- required future dataset conditions.

## Phase 0 Pass Standard

This document is accepted only if:

- CzechLynx is clearly the only quantitative validation carrier;
- WildTrax is clearly field motivation and stress test only;
- Marbled Cat is clearly future application only;
- no dataset is used to support a claim it cannot validate.