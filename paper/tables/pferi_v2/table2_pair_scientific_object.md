# Table 2. The pair as the scientific object: two gates and adjacent concepts

The descriptor-support gate, human reviewability endpoint, and identity truth are distinct constructs.

| concept | unit | information_used | decision_question | positive_state | negative_state | role_in_pferi | not_equivalent_to |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Single-image technical quality | Image | Decode status, pixels, sharpness, exposure | Can the image be decoded and measured? | Technical measurements are available | Measurement failure or stress | Predictor/input audit | Pair reviewability |
| Descriptor similarity | Directed retrieval | Descriptor ranks/scores | Does one image retrieve the other highly? | High within-role retrieval rank | Weak or absent retrieval | Candidate generation/predictor | Same identity or reviewability |
| Gate 1: descriptor-relation support | Unordered image pair | MegaDescriptor and DINOv2 directed top-20 ranks | Is the frozen same-direction dual-descriptor relation present? | both_reciprocal or both_agreement | no_same_direction_dual_descriptor_top20_consensus | Scoring eligibility gate | Human rejection |
| Gate 2: visual reviewability | Unordered image pair | Blinded human visual evidence | Is there comparable evidence for responsible review? | review_ready | not_review_ready or uncertain | Primary human endpoint | Identity match |
| Identity truth | Known-identity relation | Trusted individual identity linkage | Do the images depict the same individual? | Same individual | Different individual | Outside primary endpoint | Review-ready; a different-identity pair may be review-ready |
