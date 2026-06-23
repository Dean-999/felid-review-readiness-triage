# Phase 14 统计分析解释

## 当前结论

Phase 14 现在可以进入正式模型分析。完整的 2x2 数据、MegaDescriptor embedding、pair comparability、descriptor-evidence conflict 表都已经打通。

当前最强的结果不是“PF-ERI 直接判断身份”，而是：

```text
image-level evidence shift -> pair-level comparability shift -> descriptor/review risk shift
```

这条机制链已经有数据支持。

## 1. Image-Level Evidence Shift

High-confidence 和 low-evidence stress 的分层非常清楚。

- Bobcat high vs low image utility mean difference = 0.430, 95% CI [0.426, 0.433]
- CzechLynx high vs low image utility mean difference = 0.549, 95% CI [0.546, 0.553]
- Cliff's delta 接近 1，说明 high/low 分层几乎完全分离

解释：

这说明 detector-first + strict evidence rule 真的建立了高证据和低证据两类样本，而不是随机分组。

注意：

Bobcat low-evidence 的平均 utility 高于 CzechLynx low-evidence，说明两个 low-evidence stress set 的严重程度不完全对称。后续解释 wild vs urban 时不能简单说“urban 更差”。当前数据更像是：

```text
high-confidence 两组相近；
CzechLynx low-evidence stress 更极端；
urban bobcat low-evidence 更像 field stress / review-burden stress。
```

## 2. Pair-Level Evidence Propagation

pair comparability 结果支持“图像证据会传播成 pair-level 风险”。

- high-confidence within-context pair comparability:
  - bobcat - CzechLynx mean difference = 0.031
  - Cliff's delta = 0.300
- low-evidence within-context pair comparability:
  - bobcat - CzechLynx mean difference = 0.151
  - Cliff's delta = 0.804

解释：

low-evidence 图像进入 pair 后，会明显变成 non-comparable / low-comparability pair。这个结果是项目的关键机制基础。

## 3. CzechLynx Known-ID Validation

CzechLynx known-ID pair 给我们验证 descriptor 是否正常工作。

High-confidence CzechLynx:

- positive descriptor similarity mean = 0.276
- negative descriptor similarity mean = 0.116
- descriptor AUC for true positive = 0.731

Low-evidence CzechLynx:

- descriptor AUC for true positive = 0.691
- conflict score AUC for true positive = 0.678

解释：

MegaDescriptor 是有效的，positive/negative 有可分性。但 low-evidence 下，true positive pair 也会出现高 conflict，因为 descriptor 支持存在，但视觉证据不可充分审查。

这点非常重要：descriptor-evidence conflict 不能写成 false-positive detector。

## 4. 关键负面/边界发现

原来我们可能希望：

```text
high descriptor similarity + low evidence = false candidate enrichment
```

但当前 CzechLynx known-ID 结果不支持这个简单说法。

在 CzechLynx high-low cross 中：

- conflict-rule flagged false rate = 0.279
- unflagged false rate = 0.522
- risk difference = -0.242

在 CzechLynx low-evidence within 中：

- conflict-rule flagged false rate = 0.076
- unflagged false rate = 0.546
- risk difference = -0.469

这说明 high descriptor similarity 本身强烈偏向 true positive，导致 conflict group 中有很多真实 same-identity pair。

正确解释不是“conflict 找到更多假匹配”，而是：

```text
conflict 找到的是 descriptor 支持强、但视觉证据不足以自动接受的 pair。
```

也就是说，它是 review/defer/risk-control 信号，不是身份判错信号。

## 5. 这对项目是好是坏？

这是一个好的边界发现，不是项目失败。

原因：

1. 它阻止我们做过度声称。
2. 它把项目从“筛掉坏图”升级成“控制不可审查的高相似 pair”。
3. 它更符合真实 Re-ID 工作流：很多危险 pair 并不是 descriptor 不像，而是 descriptor 很像但证据不能被人可靠确认。

最稳的贡献表述应该改成：

```text
PF-ERI does not replace descriptor retrieval.
PF-ERI estimates whether high-similarity retrieved pairs contain admissible visual evidence for review, acceptance, defer, or species-level downgrade.
```

## 6. 下一步

下一步不要直接做“false-positive classifier”。更合理的是做 risk-controlled retrieval/review policy：

1. 在 CzechLynx known-ID 上建立 high descriptor pair 的 risk-coverage curve。
2. 比较 raw descriptor top candidates vs PF-ERI review policy。
3. 指标使用：
   - positive retention
   - false candidate retained
   - review burden
   - defer rate
   - species-level/non-comparable rate
4. Bobcat 只做 transfer stress：
   - conflict pressure
   - review burden
   - non-comparable rate
   - policy assignment distribution

这会让项目保持强数学建模方向，并且避开“bobcat 没有 identity label”的硬伤。

## 主要输出

- `outputs/phase14/phase14_statistical_analysis/phase14_statistical_analysis_report.md`
- `outputs/phase14/phase14_statistical_analysis/phase14_image_level_2x2_comparisons.csv`
- `outputs/phase14/phase14_statistical_analysis/phase14_pair_level_block_comparisons.csv`
- `outputs/phase14/phase14_statistical_analysis/phase14_czechlynx_known_id_validation_statistics.csv`
- `outputs/phase14/phase14_statistical_analysis/phase14_czechlynx_decision_validation_statistics.csv`
- `outputs/phase14/phase14_statistical_analysis/phase14_czechlynx_high_descriptor_risk_coverage_statistics.csv`
