# Phase 15C 重复验证结果分析

## 核心结论

Phase 15C 的结果是正向的，但不能包装成“PF-ERI 已经显著提升 Re-ID 准确率”。更准确的说法是：

```text
PF-ERI + quality + descriptor-conflict 特征在 known-ID CzechLynx 候选 pair 中提供了稳定的候选可靠性信号；
该信号能支持 evidence-routed review 和风险覆盖分析；
但在强 MegaDescriptor baseline 之后，top-k 命中率提升很小，且置信区间高度重叠。
```

这对项目不是坏结果。它把主线从“做一个更强 Re-ID 排序器”推向更合理的位置：**在强 descriptor 检索之后，判断候选 pair 是否有足够 admissible identity evidence，应该 accept、review、defer、species-level only，还是 non-comparable**。

## 验证设计

输入来自 Phase 15B 的 CzechLynx top-50 candidate routing table：

```text
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
```

验证设置：

- 6,000 个 CzechLynx query images；
- 300,000 个 top-50 candidate pairs；
- 20 次 repeated held-out query split；
- 每次 70% queries 训练，30% queries 测试；
- 不把同一个 query 的 candidate set 同时放入 train/test；
- 比较 descriptor-only、logistic calibrated ranker、hist-gradient-boosting ranker；
- 额外输出 subgroup、risk-coverage curve、permutation importance。

Claim boundary：

```text
这是 CzechLynx known-ID repeated query-split validation。
它可以支持 CzechLynx candidate reranking / review burden / risk routing 分析。
它不能支持 urban bobcat identity accuracy claim。
```

## 主要结果

### 1. 模型层面信号很稳定

Repeated split 下，模型级别区分 true positive candidate 的能力明显强于 descriptor-only：

| Model | ROC-AUC mean | AP mean |
|---|---:|---:|
| descriptor-only | 0.722 | 0.334 |
| logistic calibrated ranker | 0.788 | 0.400 |
| hist-gradient-boosting ranker | 0.851 | 0.599 |

这说明 PF-ERI/quality/conflict 特征不是噪声。它们确实能提供 descriptor similarity 之外的可靠性信息。

### 2. Top-k queue 提升很小

在真正的 top-k review queue 指标上，提升明显变小：

| Policy | hit@10 | false/query@10 | hit@20 | false/query@20 |
|---|---:|---:|---:|---:|
| descriptor-only | 0.691 | 7.717 | 0.749 | 16.642 |
| logistic ranker | 0.694 | 7.690 | 0.750 | 16.578 |
| HGB ranker | 0.692 | 7.687 | 0.751 | 16.545 |

解释：

- MegaDescriptor 已经是强 baseline；
- top-1/top-k 主要被 descriptor geometry 支配；
- PF-ERI 特征更像“风险解释和 review routing 信号”，不一定会大幅改变最前面的排序；
- 如果只追求 top-k 命中率，这个结果不够强；
- 如果目标是减少不可比较候选、解释错误来源、控制 review burden，这个结果有价值。

### 3. 低证据 query 是更重要的受益区

High-confidence query 中，descriptor-only 已经很强，calibrated ranker 没有明显改进。

Low-evidence query 中，logistic/HGB 的 hit@10 和 false burden 有小幅改善。这个方向更符合项目主线，因为 PF-ERI 本来就不是为了替代强 descriptor，而是为了处理 descriptor 在低证据、不可比较、conflict pair 上的风险。

### 4. Feature importance 支持“混合 evidence-routing”而非“PF-ERI 单独万能”

HGB permutation importance 的前几项：

| Feature | AP drop |
|---|---:|
| descriptor_similarity | 0.321 |
| mean_image_utility_score | 0.282 |
| weakest_image_utility_score | 0.167 |
| detector_geometry_pair_score | 0.151 |
| pair_comparability_score | 0.113 |
| blur_pair_score | 0.112 |

这很关键：descriptor_similarity 仍然最重要，但 image utility、weakest-image evidence、detector geometry、pair comparability 也有实质贡献。

因此当前模型的正确定位不是：

```text
PF-ERI beats descriptor retrieval.
```

而是：

```text
PF-ERI supplies the evidence-risk layer that descriptor retrieval lacks.
```

## 对项目主线的影响

Phase 15C 支持继续推进，但主张需要清楚分层：

1. **强支持**：PF-ERI/quality/conflict 特征能稳定预测 candidate reliability。
2. **中等支持**：calibrated ranker 能轻微改善 review queue 的 mid-k risk/coverage。
3. **暂不支持**：PF-ERI 已经带来突破性 Re-ID top-k accuracy improvement。
4. **最合理主线**：Evidence-Routed Review Layer。

这也解释了为什么项目要做 wild vs urban：

```text
wild known-ID CzechLynx 验证 pair-level risk model；
urban bobcat 测试 evidence distribution shift 和 review-routing pressure；
low-evidence stress set 检验模型是否知道什么时候不要强行做 Re-ID。
```

## 下一步

下一步不应该继续盲目训练更复杂模型，而应该把 Phase 15C 转成可审查的 review-routing policy：

- 用 risk-coverage curve 选择几个工作点；
- 输出 accept / review / defer / species-level only / non-comparable；
- 比较 descriptor-only、quality-only、PF-ERI hybrid、calibrated ranker；
- 在 CzechLynx 上验证 true-positive retention 和 false-candidate burden；
- 在 bobcat 上只做 evidence shift、review-readiness、non-comparability pressure，不做 identity accuracy claim；
- 准备小规模人工 pair audit 来验证 review-routing labels。

## 文件

核心脚本：

```text
scripts/build_phase15c_repeated_ranker_validation.py
```

核心输出：

```text
outputs/phase15/repeated_ranker_validation/
```

主要表：

```text
phase15c_repeated_model_eval.csv
phase15c_repeated_split_summary.csv
phase15c_risk_coverage_curve.csv
phase15c_permutation_importance.csv
phase15c_repeated_ranker_validation_report.md
phase15c_repeated_ranker_validation_audit.json
```
