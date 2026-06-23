# Phase 15 Calibrated Ranker Result Analysis

Date: 2026-06-22

## 这一步在做什么

Phase 15 的目标是把 PF-ERI 从手写 gate 升级成 evidence-routed review layer。

这次 Colab/Kaggle 返回的是一个 held-out query split 的 calibrated ranker 训练结果。它使用 CzechLynx known-ID top-50 candidate routing table，训练两个 tabular ranker：

- `logistic_calibrated_ranker`
- `hist_gradient_boosting_ranker`

边界：

```text
这是 CzechLynx known-ID held-out query validation。
不是 bobcat identity validation。
不是新 descriptor。
不是 full deployment claim。
```

## 模型层面结果

| Model | Test ROC-AUC | Test average precision | Train queries | Test queries |
|---|---:|---:|---:|---:|
| logistic calibrated ranker | 0.782 | 0.393 | 4,200 | 1,800 |
| hist gradient boosting ranker | 0.849 | 0.594 | 4,200 | 1,800 |

解释：

模型确实学到了 descriptor-only 之外的区分信号。尤其 HGB 的 ROC-AUC 和 AP 明显高于 logistic，说明关系不是简单线性，PF-ERI/quality/conflict 特征可能存在非线性组合价值。

但模型 AUC/AP 不是最终科学结论。Re-ID 审查真正关心的是 top-k candidate queue 是否更干净。

## Top-k 结果

### Descriptor-only baseline

| k | hit rate | mean false/query | mean positive/query |
|---:|---:|---:|---:|
| 1 | 0.501 | 0.499 | 0.501 |
| 5 | 0.623 | 3.504 | 1.496 |
| 10 | 0.677 | 7.775 | 2.225 |
| 20 | 0.734 | 16.719 | 3.281 |
| 50 | 0.813 | 44.728 | 5.272 |

### Best trained ranker deltas

| k | Best model | hit-rate change | false/query change | positive/query change |
|---:|---|---:|---:|---:|
| 1 | descriptor-only remains best | -0.004 | +0.004 | -0.004 |
| 5 | logistic | +0.003 | -0.024 | +0.024 |
| 10 | HGB | +0.011 | -0.059 | +0.059 |
| 20 | HGB | +0.009 | -0.114 | +0.114 |
| 50 | tie | 0.000 | 0.000 | 0.000 |

## 这是好结果还是坏结果？

这是一个 **正向但不够强的结果**。

正向在于：

1. HGB ranker 在 held-out query split 上有明显模型判别能力；
2. top-10 和 top-20 出现了同时提高 hit rate、降低 false/query 的方向；
3. 训练模型比手写 gate/rerank 更合理，验证了“手写规则不足，需要 calibrated ranker”的诊断；
4. 结果没有破坏项目边界：它仍然是 fixed descriptor 后的 review/reranking layer。

不够强在于：

1. top-1 变差，说明证据特征不能直接覆盖 descriptor 的最强排序信号；
2. top-k 改善幅度目前较小，不能声称 breakthrough；
3. top-50 没变化，因为所有模型都只在同一个 top-50 candidate pool 内重排；
4. 当前评估还没有 bootstrap confidence interval、identity-stratified split、low-evidence query 专项分析。

## 当前能支持的说法

可以说：

```text
PF-ERI/quality/conflict features provide additional held-out signal beyond raw descriptor similarity, and a calibrated nonlinear ranker modestly improves mid-k candidate review queues.
```

不应该说：

```text
PF-ERI 已经显著提升 Re-ID。
PF-ERI ranker 已经解决 false candidate。
PF-ERI 可以替代 MegaDescriptor。
这个结果可以推广到 bobcat identity validation。
```

## 影响置信度的漏洞

1. **没有置信区间**
   现在只有一次 held-out query split。需要 repeated group split 或 bootstrap by query。

2. **没有分 evidence block 分析**
   需要分别看 high-confidence query、low-evidence query、high descriptor but low comparability、high-low evidence-axis mismatch。

3. **没有 calibrated probability 检查**
   AUC/AP 高不代表概率可校准。后续要看 reliability curve / Brier score。

4. **没有 risk-coverage frontier**
   目前是 fixed top-k，不是同 risk 或同 review budget 下的 frontier。

5. **HGB 解释性不足**
   后续需要 permutation importance 或 SHAP，同时保留 logistic/constrained model 作为可解释参照。

## 下一步推荐

下一步不是继续盲目换模型，而是做 Phase 15C：

```text
Repeated split + subgroup + risk-coverage validation
```

具体任务：

1. 对 query 做 repeated GroupShuffleSplit，至少 20 次。
2. 报告 descriptor-only、logistic、HGB 的 mean plus confidence interval。
3. 分析 high-confidence query、low-evidence query、high descriptor low comparability、high-low evidence-axis mismatch。
4. 输出 risk-coverage frontier。
5. 加入 permutation importance，判断 PF-ERI 特征是否真的贡献，而不是全靠 descriptor。

## 当前结论

Phase 15 训练结果是正向发现，但不是最终主张。

最稳妥的项目升级表述是：

```text
Hand-written PF-ERI gates are insufficient against a strong MegaDescriptor baseline.
However, PF-ERI/quality/conflict variables contain held-out complementary signal.
The project should therefore move from fixed evidence thresholds to calibrated,
query-split risk-aware reranking and review routing.
```

这符合我们的主线：PF-ERI 不是替代 Re-ID descriptor，而是作为强 descriptor 后面的 evidence-routed review layer。
