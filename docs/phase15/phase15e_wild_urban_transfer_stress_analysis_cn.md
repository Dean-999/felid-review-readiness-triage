# Phase 15E Wild-to-Urban Transfer Stress Test 分析

## 核心结论

Phase 15E 已经把 CzechLynx 上验证过的 evidence-routed review policy 转移到 bobcat candidate pairs 上，完成了当前项目主线最关键的一步：

```text
image-level evidence shift
-> pair-level comparability shift
-> retrieval/review contamination pressure
```

但结果不是简单的“urban bobcat 更差”。更准确的发现是：

```text
urban/peri-urban bobcat 在 CzechLynx-calibrated policy 下产生更大的 defer / ambiguity pressure。
```

也就是说，bobcat candidate pairs 很多并不是彻底 non-comparable 或 species-level-only，而是落入一个更大的中间风险区：有一些证据，但不足以直接 accept 或进入高置信 review。

这比“城市照片质量差”更有研究价值，因为它指向的是 review-routing 和 threshold transfer 的问题。

## 方法

输入：

```text
outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv
outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv
```

脚本：

```text
scripts/build_phase15e_wild_urban_transfer_stress.py
```

流程：

1. 使用 6,000 张 bobcat working-final images；
2. 用 MegaDescriptor embedding 为每张 bobcat image 生成 top-50 candidate pairs；
3. 得到 300,000 个 bobcat candidate pairs；
4. 在 CzechLynx known-ID candidate pairs 上训练 HGB routing score；
5. 使用 Czech-calibrated top 5% / top 20% threshold；
6. 对 bobcat 输出五类 action：

```text
accept
review
defer
species_level_only
non_comparable
```

## Claim Boundary

Bobcat 没有 verified individual IDs，所以 Phase 15E 不能报告：

```text
bobcat false-match accuracy
bobcat hit@k
bobcat identity validation
bobcat Re-ID improvement
```

Phase 15E 可以报告：

```text
review-readiness distribution
non-comparable pressure
species-level-only pressure
defer / ambiguity pressure
descriptor-evidence conflict pressure
wild-to-urban routing shift
```

## Bobcat Action Distribution

| Action | Pairs | Pair fraction | Query fraction | Mean comparability | Mean conflict |
|---|---:|---:|---:|---:|---:|
| accept | 2,269 | 0.008 | 0.231 | 0.746 | 0.250 |
| review | 19,152 | 0.064 | 0.514 | 0.724 | 0.220 |
| defer | 202,671 | 0.676 | 0.860 | 0.562 | 0.214 |
| species_level_only | 8,722 | 0.029 | 0.400 | 0.158 | 0.428 |
| non_comparable | 67,186 | 0.224 | 0.781 | 0.236 | 0.381 |

最重要的数值是：

```text
bobcat defer pair fraction = 0.676
```

这说明在 Czech-calibrated policy 下，大量 bobcat candidate pairs 不是直接拒绝，而是进入“需要延后/不应直接身份判断”的中间层。

## Wild vs Urban 对比

| Dataset | accept | review | defer | species-level-only | non-comparable |
|---|---:|---:|---:|---:|---:|
| CzechLynx known-ID | 0.028 | 0.099 | 0.339 | 0.195 | 0.338 |
| urban bobcat identity-unknown | 0.008 | 0.064 | 0.676 | 0.029 | 0.224 |

这个结果有三个重点：

1. Bobcat `accept` 明显更低：0.008 vs 0.028。
2. Bobcat `defer` 明显更高：0.676 vs 0.339。
3. Bobcat `species_level_only` 和 `non_comparable` 反而更低。

所以不能写成：

```text
urban bobcat data are simply lower quality.
```

更好的写法是：

```text
Under a CzechLynx-calibrated evidence-routing policy, urban/peri-urban bobcat candidates shift from confident accept/review routes toward a large defer band, suggesting cross-context ambiguity pressure rather than simple low-quality collapse.
```

## Evidence-Axis 细分

High-confidence query:

| Dataset | accept | review | defer | species-level-only | non-comparable |
|---|---:|---:|---:|---:|---:|
| CzechLynx high | 0.057 | 0.196 | 0.629 | 0.014 | 0.104 |
| Bobcat high | 0.015 | 0.118 | 0.802 | 0.007 | 0.058 |

Low-evidence query:

| Dataset | accept | review | defer | species-level-only | non-comparable |
|---|---:|---:|---:|---:|---:|
| CzechLynx low | 0.000 | 0.002 | 0.050 | 0.375 | 0.573 |
| Bobcat low | 0.000 | 0.010 | 0.549 | 0.051 | 0.390 |

这说明 bobcat low-evidence stress 不是和 CzechLynx low-evidence stress 一样被大量推到 species-level-only/non-comparable，而是更多落入 defer。

这可能有两种解释：

1. **真实机制解释**：bobcat 数据中有很多“部分可比但不够强”的候选 pair，因此需要 review-routing 而不是 hard rejection。
2. **测量层风险**：bobcat 的部分 high/low labels 来自 detector-first 和 AI working labels，视觉证据特征可能比 CzechLynx 更压缩，导致 score 分布集中在中间区。

第二点必须继续检查，不能藏。

## 对项目的意义

Phase 15E 让项目主线变得更完整：

```text
CzechLynx known-ID:
验证 PF-ERI 能建模 candidate reliability 和 review-routing signal。

Bobcat urban/peri-urban:
测试这个 reliability policy 转移后会产生怎样的 review burden / ambiguity pressure。
```

这比“筛掉低质量照片让 Re-ID 稍微好一点”更强，因为它回答的是真实使用者会遇到的问题：

```text
强 Re-ID 系统给出候选之后，哪些 pair 值得看，哪些应该延后，哪些只能当 species-level 证据，哪些根本不可比较？
```

## 当前漏洞

### 1. Bobcat 不能做 identity validation

没有 verified individual IDs，所以任何 bobcat false candidate、hit@k、mAP、identity accuracy 都不能说。

解决方式：

- 做小规模 bobcat pair audit；
- 标签不是 individual ID，而是：

```text
same / different / uncertain / non-comparable / species-level-only
```

### 2. Bobcat label 来源可能压缩证据特征

Bobcat high-confidence 中有一部分是 detector-first working labels，不是同等强度的人类身份证据标签。它可能导致 action distribution 更像阈值/特征校准问题。

解决方式：

- 抽样检查每个 action 的 bobcat pairs；
- 对 accept/review/defer/non-comparable 各抽样人工 audit；
- 如果 bobcat defer 大量其实应为 review 或 non-comparable，需要做 bobcat-specific calibration。

### 3. 当前 transfer 是 policy stress，不是 causal urbanization test

FCF bobcat 是 urban/peri-urban stress context，但目前没有显式 urbanization covariates，因此不能说 urbanization causes Re-ID degradation。

## 下一步

Phase 15F 应该做人工 pair-audit package：

```text
bobcat accept: 50 pairs
bobcat review: 50 pairs
bobcat defer: 50 pairs
bobcat species_level_only: 50 pairs
bobcat non_comparable: 50 pairs
```

人工判断：

```text
manual_pair_action
manual_pair_comparability
manual_identity_evidence
manual_review_confidence
manual_notes
```

这会直接支持 RQ4：

```text
In a small human-audited urban bobcat pair set, can PF-ERI identify pairs that should be accepted, reviewed, deferred, or downgraded to species-level evidence?
```
