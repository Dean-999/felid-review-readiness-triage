# PF-ERI Expert Brief / 专家沟通双语稿

## 中文版

### 1. 一句话版本

我的项目不是要重新做一个动物 Re-ID 模型，而是想解决强 Re-ID 系统之后的一个关键问题：**当系统给出相似候选后，哪些照片对真的有足够个体识别证据，哪些应该人工复核、延后、降级为 species-level，或直接标记为不可比较？**

项目名称可以概括为：

```text
PF-ERI: patterned-felid Re-ID 的证据可靠性与风险分流系统
```

### 2. 为什么要做这个

现在很多 wildlife Re-ID 工具已经能给出很强的相似候选，尤其是 MegaDescriptor、Wildbook/IBEIS 这类系统。但在真实 camera-trap 数据里，候选相似不等于证据可靠。

常见问题是：

- 动物太小、模糊、遮挡、只露局部；
- 一个是侧面、一个是正面或背面，根本不可比较；
- descriptor similarity 很高，但侧腹、花纹、身体区域不支持这个比较；
- 低质量照片如果直接进入训练或检索，会污染候选队列和人工复核；
- 城市/半城市环境中的 bobcat 和野外 CzechLynx 可能产生不同的证据结构。

所以我的核心问题不是：

```text
Can I make another Re-ID descriptor?
```

而是：

```text
Can I estimate whether a candidate pair contains admissible individual-ID evidence?
```

### 3. 核心想法

我把 Re-ID 过程拆成三层证据传播：

```text
image-level evidence shift
-> pair-level comparability shift
-> retrieval/review contamination pressure
```

对应中文解释：

1. **图像层证据**：单张图有没有可用于个体识别的证据，例如花纹、侧腹、身体可见度、清晰度、遮挡、动物大小。
2. **pair 层可比性**：两张图放在一起时，是否真的可比。例如两张都清楚但角度不一致，仍然可能不可比。
3. **检索/复核污染**：不可比 pair 如果进入 top-k，会增加 false candidate burden 和人工复核压力。

这就是 PF-ERI 的位置：它不是替代 Re-ID，而是在强 descriptor 之后增加一个证据可靠性层。

### 4. PF-ERI 输出什么

PF-ERI 最终输出不是自动身份，而是五类 review action：

```text
accept
review
defer
species-level only
non-comparable
```

解释：

- `accept`：高优先级专家复核候选，不是自动确认身份；
- `review`：有一定证据，但需要人工谨慎判断；
- `defer`：有一些信息，但暂时不应进入高优先级身份判断；
- `species-level only`：能看出是 bobcat/lynx，但个体识别证据不足；
- `non-comparable`：两张图不适合做 pair-level Re-ID 对比。

### 5. 数据设计

当前设计是 2 x 2：

| Axis | Groups |
|---|---|
| environment | wild CzechLynx vs urban/peri-urban bobcat |
| evidence | high-confidence evidence vs low-evidence stress |

四个数据块：

```text
CzechLynx high-confidence
CzechLynx low-evidence stress
bobcat high-confidence
bobcat low-evidence stress
```

每个块目前是 3,000 张，共 12,000 张图。

CzechLynx 有 known-ID，因此用于验证 false-candidate risk、positive retention 和 review-routing 是否有效。Bobcat 没有 verified individual IDs，因此只用于 transfer stress test 和人工 pair-audit，不声称 bobcat identity accuracy。

### 6. 技术路线

当前技术路线是：

1. **图像证据特征**
   - pattern visibility
   - side/flank visibility
   - body visibility
   - blur
   - occlusion
   - detector geometry
   - edge/crop risk

2. **固定 descriptor**
   - 使用 MegaDescriptor embedding；
   - 不声称训练了新 descriptor；
   - descriptor similarity 作为强 baseline。

3. **pair-level evidence model**
   - weakest-image utility；
   - side/flank comparability；
   - pattern pair score；
   - descriptor-evidence conflict；
   - pair admissibility score。

4. **calibrated ranker**
   - CzechLynx known-ID candidate pairs 上训练 HGB/logistic ranker；
   - repeated held-out query split 验证；
   - 输出 risk-coverage 和 action routing。

5. **wild-to-urban transfer**
   - 用 CzechLynx-calibrated policy 应用到 bobcat；
   - 分析 bobcat 的 accept/review/defer/species-level/non-comparable 分布；
   - 不报告 bobcat identity accuracy。

### 7. 当前结果怎么讲

目前最重要的结果有三点。

第一，CzechLynx known-ID 上，PF-ERI/quality/conflict 特征确实有稳定信号：

```text
descriptor-only ROC-AUC: 0.722
HGB ranker ROC-AUC: 0.851
descriptor-only AP: 0.334
HGB ranker AP: 0.599
```

但 top-k 命中提升不大，所以我不会声称“PF-ERI 大幅提升 Re-ID accuracy”。更合理的 claim 是：

```text
PF-ERI provides a reliable evidence-risk layer after strong descriptor retrieval.
```

第二，Phase 15D 已经把 CzechLynx candidate pairs 分成五类 action：

| Action | Pairs | Positive pair rate |
|---|---:|---:|
| accept | 8,543 | 0.824 |
| review | 29,783 | 0.232 |
| defer | 101,809 | 0.048 |
| species-level only | 58,425 | 0.099 |
| non-comparable | 101,440 | 0.073 |

第三，转移到 bobcat 后，最有意思的发现不是“urban 全面更差”，而是：

```text
bobcat shifts strongly into the defer / ambiguity band.
```

| Dataset | accept | review | defer | species-level | non-comparable |
|---|---:|---:|---:|---:|---:|
| CzechLynx | 0.028 | 0.099 | 0.339 | 0.195 | 0.338 |
| Bobcat | 0.008 | 0.064 | 0.676 | 0.029 | 0.224 |

这说明 bobcat 的主要问题可能不是简单低质量，而是大量候选 pair 处于“有一点证据但不足以直接判断”的中间风险区。

### 8. 目前最大限制

我会主动告诉专家这些限制：

1. Bobcat 没有 verified individual IDs，因此不能报告 bobcat false-match accuracy、hit@k、mAP。
2. Phase 15D action table 是 operational routing export，不是新的 held-out validation。
3. Bobcat high/low evidence labels 有 AI/detector-first 成分，需要人工 pair audit 校准。
4. 当前不能声称 urbanization causes Re-ID failure，因为还没有显式 urban covariates。

这些不是失败点，而是下一步研究设计的一部分。

### 9. 专家现在可以帮我什么

我现在准备了 250 个 bobcat pair-audit 样本，每个 action 50 个 pair：

```text
accept: 50
review: 50
defer: 50
species-level only: 50
non-comparable: 50
```

我希望专家帮助判断：

- 这些 pair 是否真的可比较？
- 系统给的 action 是否合理？
- `defer` 是否真的代表中间风险，还是系统对 bobcat 过于保守？
- 哪些 pair 只能当 species-level 证据？
- 哪些 pair 根本 non-comparable？

人工审核后，我会做 agreement analysis：

```text
system action vs manual action agreement
accept confirmation rate
review confirmation rate
defer redistribution
species-level-only confirmation rate
non-comparable confirmation rate
```

### 10. 最终贡献怎么讲

我想提出的贡献不是一个新 Re-ID 模型，而是：

```text
A reliability-aware pairwise evidence routing layer for patterned-felid Re-ID.
```

中文可以说：

```text
一个面向 patterned-felid Re-ID 的 pair-level 证据可靠性建模与风险分流框架。
```

它的价值在于：

- 让 Re-ID 不再只输出“谁最像”，而是输出“这个比较是否有证据支撑”；
- 把低证据图像从训练/检索污染中分流出来；
- 解释 descriptor-evidence conflict；
- 支持 known-ID wild lynx 的定量验证；
- 支持 urban bobcat 的 field-readiness stress test；
- 给专家复核提供更清楚的优先级和拒绝理由。

### 11. 30 秒口头版本

我的项目不是重新训练一个动物 Re-ID 模型，而是在强 Re-ID descriptor 之后加一个 evidence reliability layer。真实 camera-trap 图像里，系统给出的相似候选不一定有足够个体识别证据，尤其是侧面不可比、花纹不可见、模糊遮挡、动物太小的时候。我用 CzechLynx known-ID 数据验证这个 pair-level evidence model，再把 calibrated policy 转到 urban/peri-urban bobcat 做 stress test。当前结果显示，PF-ERI 特征能稳定预测 candidate reliability，但 top-k accuracy 提升不大，所以我把核心贡献定位为 evidence-routed review：把候选分成 accept、review、defer、species-level-only 和 non-comparable。下一步我用 250 个 bobcat pair 做人工审核，验证系统分流是否和专家判断一致。

---

## English Version

### 1. One-Sentence Pitch

My project is not trying to build another animal Re-ID descriptor. It addresses a downstream reliability problem: **after a strong Re-ID system retrieves visually similar candidates, which image pairs actually contain admissible individual-identification evidence, and which should be reviewed, deferred, downgraded to species-level evidence, or marked non-comparable?**

Project shorthand:

```text
PF-ERI: an evidence reliability and review-routing system for patterned-felid Re-ID.
```

### 2. Why This Matters

Modern wildlife Re-ID tools can already produce strong candidate rankings. However, camera-trap similarity is not the same as reliable identity evidence.

Common failure cases include:

- the animal is too small, blurred, occluded, or partially cropped;
- one image is lateral while another is frontal or rear-facing;
- the descriptor gives high similarity but flank/pattern/body evidence is not comparable;
- low-evidence images contaminate retrieval queues or training signals;
- urban/peri-urban bobcat data may create a different evidence-risk structure from wild CzechLynx data.

Therefore, the core question is not:

```text
Can I build another Re-ID descriptor?
```

It is:

```text
Can I estimate whether a candidate pair contains admissible individual-ID evidence?
```

### 3. Core Idea

I frame the problem as a three-layer evidence propagation chain:

```text
image-level evidence shift
-> pair-level comparability shift
-> retrieval/review contamination pressure
```

Meaning:

1. **Image-level evidence**: whether a single image contains usable identity evidence, such as pattern, flank, body visibility, sharpness, occlusion, and animal size.
2. **Pair-level comparability**: whether two images are visually comparable enough for descriptor similarity to be trusted.
3. **Retrieval/review contamination**: how unreliable or non-comparable pairs enter candidate queues and increase review burden.

PF-ERI sits after strong descriptor retrieval. It does not replace Re-ID; it estimates evidence reliability for candidate comparisons.

### 4. What PF-ERI Outputs

PF-ERI outputs five review actions:

```text
accept
review
defer
species-level only
non-comparable
```

Definitions:

- `accept`: high-priority candidate for expert review, not automatic identity assignment;
- `review`: potentially useful but requires careful human review;
- `defer`: some evidence is present, but the pair should not enter high-priority identity judgement;
- `species-level only`: the animal is visible, but individual-level evidence is insufficient;
- `non-comparable`: the two images should not be used as a pair-level Re-ID comparison.

### 5. Data Design

The current design is a 2 x 2 evidence-risk structure:

| Axis | Groups |
|---|---|
| environment | wild CzechLynx vs urban/peri-urban bobcat |
| evidence | high-confidence evidence vs low-evidence stress |

Four blocks:

```text
CzechLynx high-confidence
CzechLynx low-evidence stress
bobcat high-confidence
bobcat low-evidence stress
```

Each block currently contains 3,000 images, for 12,000 images total.

CzechLynx has known individual IDs, so it supports quantitative validation of false-candidate risk, positive retention, and review-routing behavior. Bobcat currently lacks verified individual IDs, so it is used for transfer stress testing and human pair-audit, not identity-accuracy validation.

### 6. Technical Pipeline

The current pipeline is:

1. **Image evidence features**
   - pattern visibility;
   - side/flank visibility;
   - body visibility;
   - blur;
   - occlusion;
   - detector geometry;
   - edge/crop risk.

2. **Fixed descriptor baseline**
   - MegaDescriptor embeddings;
   - no claim of a newly trained descriptor;
   - descriptor similarity is treated as a strong baseline.

3. **Pair-level evidence model**
   - weakest-image utility;
   - side/flank comparability;
   - pattern pair score;
   - descriptor-evidence conflict;
   - pair admissibility score.

4. **Calibrated ranker**
   - trained on CzechLynx known-ID candidate pairs;
   - evaluated using repeated held-out query splits;
   - used to define risk-coverage and review-routing policies.

5. **Wild-to-urban transfer**
   - apply the CzechLynx-calibrated policy to bobcat candidate pairs;
   - analyze action distribution and ambiguity pressure;
   - do not report bobcat identity accuracy.

### 7. Current Results

First, on CzechLynx known-ID candidate pairs, PF-ERI/quality/conflict features provide stable signal:

```text
descriptor-only ROC-AUC: 0.722
HGB ranker ROC-AUC: 0.851
descriptor-only AP: 0.334
HGB ranker AP: 0.599
```

However, top-k retrieval improvement is modest. Therefore, I do not claim that PF-ERI broadly improves Re-ID accuracy. The stronger and more honest claim is:

```text
PF-ERI provides a reliable evidence-risk layer after strong descriptor retrieval.
```

Second, Phase 15D routed 300,000 CzechLynx candidate pairs into five actions:

| Action | Pairs | Positive pair rate |
|---|---:|---:|
| accept | 8,543 | 0.824 |
| review | 29,783 | 0.232 |
| defer | 101,809 | 0.048 |
| species-level only | 58,425 | 0.099 |
| non-comparable | 101,440 | 0.073 |

Third, when transferred to bobcat, the main finding is not that urban data are simply worse. Instead:

```text
bobcat shifts strongly into the defer / ambiguity band.
```

| Dataset | accept | review | defer | species-level | non-comparable |
|---|---:|---:|---:|---:|---:|
| CzechLynx | 0.028 | 0.099 | 0.339 | 0.195 | 0.338 |
| Bobcat | 0.008 | 0.064 | 0.676 | 0.029 | 0.224 |

This suggests that urban/peri-urban bobcat candidate pairs often contain partial but insufficient evidence, creating ambiguity pressure rather than simple low-quality collapse.

### 8. Current Limitations

I would explicitly tell the expert:

1. Bobcat has no verified individual IDs, so I cannot report bobcat false-match accuracy, hit@k, or mAP.
2. Phase 15D action tables are operational exports; Phase 15C repeated query splits are the validation evidence.
3. Bobcat high/low evidence labels partly rely on detector-first and AI-assisted working labels, so human pair-audit is needed.
4. I cannot claim urbanization causes Re-ID failure because explicit urban covariates are not yet modeled.

These are not hidden weaknesses; they define the next validation step.

### 9. What I Need From the Expert

I prepared a 250-pair bobcat audit set, with 50 pairs from each action:

```text
accept: 50
review: 50
defer: 50
species-level only: 50
non-comparable: 50
```

The expert can help judge:

- whether the two images are truly comparable;
- whether the system action is reasonable;
- whether `defer` is a real intermediate-risk category or an overly conservative transfer artifact;
- which pairs should be species-level only;
- which pairs are truly non-comparable.

After manual review, I will compute:

```text
system action vs manual action agreement
accept confirmation rate
review confirmation rate
defer redistribution
species-level-only confirmation rate
non-comparable confirmation rate
```

### 10. Final Contribution Statement

The contribution is not a new Re-ID model. It is:

```text
A reliability-aware pairwise evidence routing layer for patterned-felid Re-ID.
```

Its value is that it:

- moves beyond "which candidate looks most similar";
- estimates whether the comparison has admissible identity evidence;
- routes low-evidence images away from training and high-priority identity decisions;
- identifies descriptor-evidence conflict;
- validates the model on known-ID wild CzechLynx;
- stress-tests transfer to urban/peri-urban bobcat monitoring;
- gives experts a clearer review priority and rejection rationale.

### 11. 30-Second Spoken Version

My project is not about training another animal Re-ID descriptor. It adds an evidence reliability layer after strong descriptor retrieval. In camera-trap data, visually similar candidates may not contain admissible individual-ID evidence, especially when the animal is small, occluded, blurred, or not comparable in flank or body view. I validate this pair-level evidence model on known-ID CzechLynx, then apply the calibrated review-routing policy to urban/peri-urban bobcat as a transfer stress test. The current results show that PF-ERI features provide stable candidate-reliability signal, but top-k accuracy gains are modest. Therefore, I frame the contribution as evidence-routed review: assigning candidate pairs to accept, review, defer, species-level only, or non-comparable. The next validation step is a 250-pair bobcat human audit to test whether these routing decisions agree with expert judgement.
