# Pre-Inference Evidence Hygiene Simulation

Date: 2026-07-09

Status: `PASS`

This simulation applies the PF-ERI review route as a pre-inference evidence gate on the CzechLynx reviewed candidate-pair table. The simulated workflow begins with a descriptor-retrieved candidate queue, assigns each pair to an admitted or deferred evidence state, and then audits the consequences using human reviewability and known-ID same/different labels. The simulation is deliberately placed before expert review or ecological inference; it is not a population estimate, a validated ecological outcome, or an automatic identity assignment.

In the pooled queue, 234 pairs were admitted before inference and 166 were deferred. The admitted set had review-ready rate 0.859 and not-ready/uncertain rate 0.141, whereas the deferred set had review-ready rate 0.446 and not-ready/uncertain rate 0.554. Same-ID candidate retention in the admitted set was 0.655. These values show how PF-ERI changes what evidence is allowed to proceed, not whether the system can identify individuals by itself.

The deferred set concentrated 92 not-ready or uncertain pairs, compared with 33 in the admitted set. This is the central applied value of the simulation: pairs with weaker, conflicted, or lower-readiness evidence are moved out of the immediate evidence-use path. Different-ID pairs are reported as review burden rather than errors, because many different-ID pairs can still be review-ready when the reviewer can confidently reject them.

The result should be interpreted as a CzechLynx known-ID evidence-hygiene demonstration. It supports the claim that PF-ERI can structure the candidate queue before inference, preserving a more review-ready admitted set and concentrating lower-readiness pairs into deferral. It does not support Bobcat identity accuracy, population-level ecological inference, top-k identity improvement, mAP, MRR, or automatic individual recognition.

## Artifact Links

The pair-level simulation table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_pairs.csv`. The summary table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_summary.csv`. The audit file is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_audit.json`.
