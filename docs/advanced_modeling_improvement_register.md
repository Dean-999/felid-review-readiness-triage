# Advanced Modeling Improvement Register

This register records limitations or improvement paths discovered during the
advanced PF-ERI mathematical validation work. These items are not current claim
failures; they are constraints that must remain visible before stronger future
claims are made.

## Current Items

| Item | Status | Why It Matters | Future Fix |
| --- | --- | --- | --- |
| Finite-sample upper risk exceeds target alpha | Open | Hoeffding upper-risk diagnostics are conservative with current accepted calibration sample sizes, so alpha-level routing is empirical-calibration supported rather than finite-sample upper-bound guaranteed. | Increase calibration sample size or use a more suitable risk-control method with clearly stated assumptions. |
| Identity-cluster bootstrap not feasible | Open | The reviewed table has same/different identity relation but not resolved query/candidate identity clusters. | Add `query_identity_label` and `candidate_identity_label` to the validation table when available. |
| Component-group bootstrap is sparse | Open | Component/fold bootstrap has only a few clusters, so those intervals are diagnostics rather than high-precision uncertainty estimates. | Add more independent component groups or use a validation design with more cluster units. |
| Source-held-out causal domain claim blocked | Open | CzechLynx validation has constant source/domain stress in the current supervised set. | Build a source-varied held-out validation set before making source/domain generalization claims. |
| Risk decomposition reason labels sparse | Open | Current risk-family decomposition is component attribution, not fully validated human reason classification. | Add explicit human reason labels for not-ready/uncertain decisions. |
| Bobcat identity metrics blocked | Open | Bobcat rows are unlabeled transfer-stress/workflow diagnostics in this workflow. | Add audited Bobcat same/different identity labels before estimating identity accuracy, mAP, MRR, or top-k retrieval claims. |
| Descriptor-specific alpha control not guaranteed by pooled threshold | Open | The pooled alpha threshold can satisfy overall calibration risk while a descriptor family, such as DINOv2 in the current diagnostics, exceeds alpha on descriptor-specific calibration rows. | Add descriptor-family-specific calibration thresholds or hierarchical calibration if the paper needs per-descriptor risk-control claims. |
| Nonlinear sensitivity mostly limited by constant core features | Open | Four of six pre-specified core evidence features are constant in the current 400-row CzechLynx validation table, so nonlinear/spline effects are only estimable for body-part overlap and cross-descriptor agreement. | Add a source-varied and quality-varied validation packet before claiming nonlinear effects for visible pattern area, viewpoint compatibility, blur/night risk, or source/domain stress. |
| Cross-descriptor sensitivity has sparse low-tail bin | Open | Tie-aware binning avoids splitting the dominant 0.5 agreement value, but the lowest cross-descriptor agreement bin currently has only a few rows, so monotonic support should be reported with a sparse-bin caveat. | Enrich the validation sample with more low-agreement candidate pairs or use a pre-specified low-agreement oversampling design. |
| Review-budget optimization is predicted-risk constrained | Open | The budget optimizer constrains mean predicted evidence risk, while empirical risk and Wilson intervals are post-selection audits; this should not be described as a new finite-sample conformal guarantee. | If stronger guarantees are needed, design a budget-specific conformal or risk-control procedure with grouped calibration and report its assumptions separately. |
