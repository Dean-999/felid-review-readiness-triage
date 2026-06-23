# Phase 14 风险控制审查策略解释

## 这一步在做什么

这一步不是完整 gallery retrieval benchmark，也不是 Re-ID top-1 准确率实验。

它做的是：

```text
在 high-descriptor candidate pairs 中，
比较 raw descriptor、PF-ERI pair comparability、quality-only、random matched control
能否更好地控制 positive retention、false candidate retention、review/defer burden。
```

CzechLynx 有 known-ID pair，因此可以验证 positive/false candidate。Bobcat 当前没有 individual ID，因此只能做 transfer stress 和 review burden。

## 核心结果

### 1. Clean high-confidence block

在 `czechlynx_high_confidence_within` 中，raw descriptor top 10% 已经很好：

- retained false-candidate rate = 0.042
- PF-ERI >= 0.70 后 retained false-candidate rate = 0.048
- positive retention 从 1.000 降到 0.629

解释：

高置信图像内部，PF-ERI 严格 gate 没有必要，甚至会损失 coverage。这支持一个重要边界：

```text
PF-ERI 不应该无差别过滤所有场景。
它应该在证据混杂或低证据场景中启动。
```

### 2. High-low mixed block

在 `czechlynx_high_low_cross` 中，PF-ERI 开始有价值。

Raw descriptor top 10%：

- positive retention = 1.000
- false candidate retention = 1.000
- retained false-candidate rate = 0.262

PF-ERI pair comparability >= 0.40：

- positive retention = 0.128
- false candidate retention = 0.050
- retained false-candidate rate = 0.121

Matched random control 在同 coverage 下：

- random false-candidate retention mean = 0.108
- 95% interval = [0.084, 0.131]

解释：

PF-ERI 在 mixed evidence 场景中不是简单“保留更多”，而是更强地减少 false candidate burden。代价是 positive retention 也下降。因此它应该被建模成 risk-coverage frontier，而不是单一阈值。

### 3. Low-evidence stress within block

这是最重要的边界发现。

PF-ERI >= 0.30：

- retained pairs = 128
- positive retention = 0.069
- false candidate retention = 0.000

quality-only weakest image utility >= 0.40：

- retained pairs = 153
- positive retention = 0.083
- false candidate retention = 0.000

解释：

在 severe low-evidence block 中，quality-only 当前支配 PF-ERI 单独 gate。也就是说，如果只在极差样本里做单一 PF-ERI pair threshold，创新性不够强，容易被 reviewer 说成质量筛选。

正确升级方向是：

```text
PF-ERI + quality hybrid
```

而不是继续主张 PF-ERI 单独优于 quality-only。

## 对项目是好还是坏？

这是好结果，但不是“无条件正向”。

好在：

1. high/low evidence design 已经成立；
2. pair-level comparability 传播成立；
3. mixed evidence pair 中 PF-ERI 有风险控制价值；
4. 我们明确发现了 PF-ERI 单独不足的边界条件；
5. 下一步模型升级方向非常清楚。

风险在：

1. 不能声称 PF-ERI always beats quality filtering；
2. 不能声称它是 false-positive detector；
3. 不能声称 bobcat false-match accuracy；
4. 不能把 sampled pair policy 说成完整 retrieval benchmark。

## 推荐下一步

下一步应该做 Pareto optimization / hybrid policy：

```text
score = f(
  descriptor percentile,
  pair comparability,
  weakest image utility,
  conflict score,
  evidence-axis mismatch
)
```

目标不是单纯最大化准确率，而是：

```text
maximize positive retention
minimize false candidate retention
minimize review burden
subject to evidence risk <= tau
```

必须比较：

- raw descriptor top candidates
- quality-only gate
- PF-ERI pair-comparability gate
- PF-ERI + quality hybrid
- random matched same-coverage control

## 当前结论写法

可以写：

```text
PF-ERI provides useful risk-control signal in mixed-evidence candidate pairs,
but severe low-evidence cases require hybridization with quality-based controls.
The contribution is therefore not generic image filtering, but risk-controlled
review routing over high-descriptor candidate pairs.
```

不要写：

```text
PF-ERI always improves Re-ID.
PF-ERI detects false positives.
PF-ERI outperforms quality filtering in all settings.
Bobcat false-match risk was validated.
```

## 主要输出

- `outputs/phase14/phase14_risk_controlled_review_policy/phase14_risk_controlled_review_policy_report.md`
- `outputs/phase14/phase14_risk_controlled_review_policy/phase14_czechlynx_policy_evaluation.csv`
- `outputs/phase14/phase14_risk_controlled_review_policy/phase14_czechlynx_random_matched_policy_control.csv`
- `outputs/phase14/phase14_risk_controlled_review_policy/phase14_czechlynx_policy_pareto_diagnostics.csv`
- `outputs/phase14/phase14_risk_controlled_review_policy/phase14_bobcat_policy_transfer_stress.csv`
