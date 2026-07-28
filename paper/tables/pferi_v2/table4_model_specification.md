# Table 4. Nested P3 and P5 model specification

P5 equals P3 plus the frozen local pair-evidence block; both use the same model family and lambda.

| feature_family | feature_or_block | unit | p3_active_control | p5_full_model | availability_timing | transformation | missingness_handling | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Descriptor | MegaDescriptor and DINOv2 within-role percentiles | Directed rank percentile | Included | Included | Before human outcomes | Training-fold median imputation and z-score | Explicit missing indicator | Retrieval strength |
| Descriptor | descriptor_support_category | Pair | Included | Included | Before human outcomes | Frozen one-hot encoding | Missing and unknown states | Gate-1 relation type |
| Independent quality | Minimum endpoint pixel, sharpness, and exposure percentiles | Pair endpoint minimum | Included | Included | Before human outcomes | Training-fold median imputation and z-score | Explicit missing indicators | Weakest endpoint quality |
| Quality state | measurement failure and frozen quality stress | Pair | Included | Included | Before human outcomes | Frozen categorical encoding | Explicit states | Technical stress |
| Pair evidence | local_match_coverage_fraction and failure states | Pair | Excluded | Included | Before human outcomes | Training-fold z-score plus categorical indicators | Failure is not encoded as zero evidence | Strict P5 incremental block |
| Model | Ridge logistic regression | Pair | lambda=100 | lambda=100 | Frozen at Task15J | Logit link; unpenalized intercept | Per frozen preprocessing | Probability of not_ready_or_uncertain |
