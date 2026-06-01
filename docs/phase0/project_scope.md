# Project Scope

## Working Title

Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

## One-Sentence Definition

This project evaluates whether felid camera-trap images should pass through a review-readiness gate before individual-level Re-ID review, and quantifies how that gate affects Re-ID reliability, pairwise false-match risk proxy, and retained matching evidence.

## Project Positioning

This project is a conservation computer vision reliability study.

It is not designed to build a new animal Re-ID model. It is not a general all-animal identification system. It is not a claim that AI can identify true individual animals from uncontrolled field images. Instead, it studies a narrower and more defensible question:

Before a camera-trap image is used for individual-level Re-ID review, is it reliable enough to enter that review process at all?

The project uses Re-ID embeddings as an auxiliary measurement signal, not as the final product. The core contribution is a review-readiness triage policy and a validation framework for testing whether that policy improves Re-ID reliability while measuring how much matching evidence is lost when low-readiness images are filtered out.

## Scientific Motivation

Conservation camera-trap workflows often produce images that are species-identifiable but not necessarily suitable for individual-level identification. A bobcat or lynx may be visible enough to tag at the species level, but the image may still be too blurred, occluded, partial, poorly angled, or distorted by night infrared illumination to support safe individual-level Re-ID review.

The field already has strong animal Re-ID tools, datasets, and benchmarks, including WildlifeDatasets, MegaDescriptor, WildlifeReID-10k, CzechLynx, and WildFusion. Therefore, the project should not claim novelty in animal Re-ID itself.

The research gap addressed here is earlier in the workflow:

Which images should be allowed into Re-ID review in the first place?

## Personal Field Motivation

The field motivation comes from UWIN-Atlanta camera-trap tagging work. In that workflow, many images are useful for species-level tagging but are not clearly suitable for individual-level evidence. Common field problems include blur, night IR artifacts, partial body views, occlusion, angle instability, repeated detections of what may be the same animal, and species-level uncertainty.

This project converts that field observation into a testable research question. Instead of claiming that field images can be used for true individual identification, it asks whether a review-readiness gate can reduce unreliable identity evidence before Re-ID review.

## Main Research Questions

### Q1: Reliability

Do images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images?

Technical version:

Does the review-ready label correspond to stronger same-individual versus different-individual similarity separation in known-ID felid Re-ID data?

### Q2: Trade-off

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much potential known matching evidence is lost?

Technical version:

How much safety is gained, and how much matching coverage is lost, when low-readiness images are removed from candidate Re-ID review?

## Data Roles

### CzechLynx / Eurasian Lynx

Role: quantitative known-ID validation carrier.

CzechLynx is used because it provides known individual IDs and camera-trap images suitable for constructing same-individual and different-individual pairs. It supports the strict validation of Q1 and Q2.

CzechLynx is not the biological identity of the project. The project is not a Eurasian lynx Re-ID project. CzechLynx is the validation carrier for a broader felid review-readiness question.

### UWIN / WildTrax Bobcat and Canada Lynx

Role: field motivation and field-readiness stress test.

UWIN/WildTrax images are used to show the real field problem: species-level detections can be blurred, occluded, partial, night-distorted, or unstable in angle. These images can support field triage distribution and failure-mode analysis.

They cannot support strict identity validation unless verified individual IDs are available.

### Marbled Cat

Role: future Asian conservation application scenario.

Marbled Cat is included only as a future application case for Asian forest felid monitoring. It is not part of the current quantitative validation. The project does not validate Marbled Cat Re-ID.

## What the Project Is

This project is:

- a review-readiness gate study;
- a conservation workflow reliability study;
- a known-ID validation study using CzechLynx;
- a field motivation and stress-test study using UWIN/WildTrax images;
- a risk–coverage trade-off analysis;
- a future application framework for Asian felid monitoring.

## What the Project Is Not

This project is not:

- a new animal Re-ID model;
- a state-of-the-art Re-ID benchmark submission;
- a universal wildlife identification system;
- a claim that AI identifies true individuals in WildTrax;
- a population size estimation study;
- a full human review website;
- a RUDI system;
- a broad all-animal Re-ID workflow;
- a validation study for Marbled Cat Re-ID;
- a claim that thresholds transfer directly across species.

## Primary Contribution

The primary contribution is a validated review-readiness triage strategy for felid conservation camera-trap images.

The project tests whether human-defined review-readiness categories correspond to measurable Re-ID reliability in known-ID data, and it quantifies the trade-off between reduced pairwise false-match risk proxy and retained matching evidence.

## Intended Audience

The immediate audience is a professor or mentor in conservation computer vision, animal Re-ID, or ecological AI.

The secondary audience may include science fair reviewers, conservation researchers, and future paper readers.

The writing should therefore be technically accurate, conservative in its claims, and clear about what is validated versus what is only motivated or proposed.

## Final Abstract Draft

Animal re-identification from camera-trap images is increasingly used to support wildlife monitoring, but not every species-level detection is suitable for individual-level review. Blurred, occluded, partial, night-distorted, or poorly angled images may introduce unsafe identity evidence if they are passed directly into a Re-ID workflow. This project evaluates a review-readiness gate for felid camera-trap images before individual-level Re-ID review. Using known-ID CzechLynx data as a quantitative validation carrier, the study tests whether images labeled as review-ready show stronger same-individual versus different-individual similarity separation than review-limited or unidentifiable images. It also measures the risk–coverage trade-off created by filtering low-readiness images, reporting pairwise false-match risk proxy, retained image rate, retained identity count, retained same-pair coverage, and known-match loss. UWIN/WildTrax Bobcat and Canada Lynx images are used only as field motivation and triage stress-test examples, while Marbled Cat is discussed as a future Asian conservation application requiring separate authorized known-ID validation. The project does not propose a new Re-ID model or claim true individual identification in field data without verified IDs. Its contribution is a conservation-safe pre-Re-ID triage protocol for deciding which felid camera-trap images are reliable enough to enter individual-level review.

## Mentor-Facing Short Explanation

I am narrowing the project so it does not duplicate mature animal Re-ID work. Instead of building a new Re-ID model, I want to study a review-readiness gate for felid camera-trap images before individual-level Re-ID review. The main questions are whether review-ready images actually show stronger same-individual versus different-individual Re-ID similarity separation, and whether filtering low-readiness images lowers pairwise false-match risk proxy while losing some known matching evidence. CzechLynx would be used for quantitative known-ID validation, UWIN/WildTrax Bobcat and Canada Lynx images would provide field motivation and triage stress-test examples, and Marbled Cat would be discussed only as a future Asian conservation application case requiring separate data audit and calibration.

## Phase 0 Pass Standard

Phase 0 is complete only if:

- the project is clearly not framed as a new Re-ID model;
- only Q1 and Q2 remain as core research questions;
- each dataset has a distinct role;
- all forbidden claims are documented;
- the evidence chain is clear;
- the mentor-facing explanation can be understood in under one minute;
- every future claim is assigned to one of three evidence levels:
  - quantitative validation;
  - field stress test;
  - future application.