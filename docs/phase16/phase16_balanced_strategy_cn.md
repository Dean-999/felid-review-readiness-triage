# Phase 16 平衡战略：竞赛、论文与工具价值

Date: 2026-06-23

## 核心定位

Phase 16 不把项目改成单纯的 urban vs wild 对比，也不把 PF-ERI 说成新的 Re-ID 模型。

核心问题是：

```text
当强 Re-ID 模型给出相似候选后，这个 candidate pair 是否仍然具备可采纳的个体识别证据？
```

## 三目标权重

```text
竞赛/展示价值：40%
科研论文严谨性：35%
真实工具应用价值：25%
```

## 主线

```text
MegaDescriptor/WildFusion-style retrieval
-> PF-ERI pair-level admissibility
-> descriptor-evidence conflict
-> calibrated review action routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

## 数据治理保护层

这些内容提高项目可信度，但不是主线替代品：

```text
laterality-aware sampling/pair audit
background/site leakage-pressure audit
strong-model benchmark contract
```

后续可选扩展：

```text
ecological/spatiotemporal plausibility prior
augmentation/generative robustness stress
captive imagery calibration ceiling
```

## 不能越界的结论

- 不声称 bobcat identity accuracy。
- 不声称 urbanization causes Re-ID failure。
- 不声称 PF-ERI 是新 descriptor。
- 不声称生成式增强产生真实身份样本。
- 不把圈养数据变成当前主轴。
- 不把 laterality balance 说成核心算法贡献。

## 最强贡献表述

```text
PF-ERI 2.0 在强 Re-ID 候选产生之后，判断 candidate pair 是否具备可采纳的个体识别证据，并在跨环境证据变化、图像退化、左右侧可比性、潜在背景/地点泄漏压力和 review budget 约束下输出可执行的 review action。
```

## 实施优先级

1. 保持 PF-ERI 建模主线：pair-level evidence utility、descriptor-evidence conflict、calibrated review routing、risk-controlled evaluation。
2. 先做 laterality-aware sampling/pair audit，防止 pair-level 对比被左右侧不平衡污染。
3. 再做 background/site leakage-pressure audit，只报告风险压力，不做因果证明。
4. 准备 strong-model benchmark package，确保 PF-ERI 是围绕强模型补足 evidence/risk decision layer，而不是只打弱 baseline。
5. 暂不启动 generative augmentation、captive imagery 或完整生态先验，除非 Phase 16A 的数据治理门槛通过。
