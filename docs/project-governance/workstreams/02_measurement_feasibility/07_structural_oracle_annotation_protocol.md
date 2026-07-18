# Task 04: Structural Oracle Annotation Protocol

Status: protocol locked; packet generation and two independent annotations pending.

This task measures whether human feature annotators can consistently describe visible structure. It is not the PF-ERI reviewability outcome task and does not ask whether two animals are the same individual, whether comparison is responsible, or whether a pair should be routed. The two annotators receive opaque assets, a neutral packet identifier, and only the feature form declared in the contract.

For every pilot pair, each annotator independently records two image-level pattern-area fractions, two image-level occlusion fractions, one pair-level shared-body-region fraction, and one viewpoint-compatibility class. Fractions use 0.05 increments. A value of zero is permitted only as an observed structural value, never as missingness. Technical display failures receive no structural values and are recorded separately.

The pre-registered gate requires the lower 95% confidence bound of two-annotator ICC to reach 0.60 for every continuous field and the lower 95% confidence bound of weighted kappa to reach 0.50 for viewpoint compatibility. Failure means the relevant measurement is not ready; it cannot be rescued by adjudication, outcome labels, or a more favourable definition after inspection. The oracle fields remain permanently excluded from the primary automatic model.

Before recruiting annotators, generate an opaque-asset packet from the restricted pilot manifest and perform a non-annotator leakage audit of filenames, displayed text, URL, DOM, and any downloaded export. The annotation task may proceed independently of the GPU quality measurement, but its results must not be used to retune automatic extractors.
