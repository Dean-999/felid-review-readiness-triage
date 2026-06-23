# Phase 15D Evidence-Routed Review Policy 分析

## 结论

Phase 15D 已经把 Phase 15C 的 repeated validation 转成一个可操作的 review-routing 层。它不再只回答“哪个候选最像”，而是给每个 CzechLynx candidate pair 输出五类动作：

```text
accept
review
defer
species_level_only
non_comparable
```

这里的 `accept` 必须理解为：

```text
high-priority candidate pair for expert review
```

不是自动身份确认，不是自动 individual assignment。

## 输入和输出

输入：

```text
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
outputs/phase15/repeated_ranker_validation/phase15c_risk_coverage_curve.csv
```

核心脚本：

```text
scripts/build_phase15d_evidence_routed_review_policy.py
```

输出目录：

```text
outputs/phase15/evidence_routed_review_policy/
```

核心输出：

```text
phase15d_evidence_routed_review_table.csv
phase15d_review_action_summary.csv
phase15d_query_review_summary.csv
phase15d_operating_points_from_phase15c.csv
phase15d_evidence_routed_review_policy_report.md
phase15d_evidence_routed_review_policy_audit.json
```

## 设计逻辑

Phase 15D 分两层，不混淆验证和导出：

1. **验证层**：来自 Phase 15C repeated held-out query splits。
2. **导出层**：在全部 CzechLynx known-ID candidate pairs 上 fit 一个 final HGB ranker，用于给全体 pair 输出 operational scores 和 review actions。

这意味着：

```text
Phase 15D routing table 是 operational export。
Phase 15C repeated split 才是 validation evidence。
```

这个边界非常重要。否则会把 all-data fit 的 action positive rate 误读成新的 held-out validation，这会被 reviewer 抓住。

## 动作分布

当前 300,000 个 CzechLynx candidate pairs 的动作分布：

| Action | Pairs | Pair fraction | Positive pair rate | Mean HGB score |
|---|---:|---:|---:|---:|
| accept | 8,543 | 0.028 | 0.824 | 0.739 |
| review | 29,783 | 0.099 | 0.232 | 0.226 |
| defer | 101,809 | 0.339 | 0.048 | 0.056 |
| species_level_only | 58,425 | 0.195 | 0.099 | 0.099 |
| non_comparable | 101,440 | 0.338 | 0.073 | 0.073 |

这个分布基本符合 evidence-routing 逻辑：

- `accept` 是小而高精度的候选层；
- `review` 是中等证据但仍需人工判断的候选层；
- `defer` 是模型分数较低但不一定完全不可比较的候选层；
- `species_level_only` 保留低个体证据图像的生态/物种记录价值；
- `non_comparable` 明确阻止无可比性的 pair 进入身份判断。

## Phase 15C 支持的 operating point

Phase 15C repeated split 的关键证据：

| Policy | Pair coverage | Hit rate | Query coverage | False/query |
|---|---:|---:|---:|---:|
| descriptor-only | 0.05 | 0.382 | 0.451 | 1.356 |
| HGB ranker | 0.05 | 0.431 | 0.547 | 0.527 |
| descriptor-only | 0.20 | 0.569 | 0.760 | 7.368 |
| HGB ranker | 0.20 | 0.638 | 0.936 | 6.365 |

这说明 calibrated evidence ranker 在 low-coverage review policy 上更有价值：它可以在更低 false burden 下保留更多 query coverage。

这比简单 top-k gain 更适合作为项目贡献，因为它对应的是实际 reviewer 的工作流：

```text
在有限 review budget 下，哪些候选值得优先看？
哪些候选应该延后、降级或标记不可比较？
```

## 强点

1. **把数学建模落到工作流动作**
   不再只是 score 或 reranking，而是明确输出五类 review action。

2. **不和强 descriptor 硬抢主线**
   MegaDescriptor 负责相似候选召回；PF-ERI 负责 evidence admissibility 和 risk routing。

3. **保留低证据样本的科学价值**
   low-evidence 不被简单删除，而是被分到 stress、species-level、defer 或 non-comparable。

4. **适合 wild vs urban 迁移**
   CzechLynx 可以验证 action 与 true same/different 的关系；bobcat 可以测试 action distribution、non-comparable pressure 和 review burden shift。

## 仍然存在的问题

### 1. Phase 15D action table 不是 held-out validation

这是最大边界。routing table 的 HGB score 是 all-data fit，用于 operational export。不能把 action positive rate 当成最终验证准确率。

解决方案：

- 论文主结果引用 Phase 15C repeated split；
- Phase 15D action table 作为 policy instantiation；
- 后续如果需要更强，可以做 repeated-split action assignment，把每个 test query 的 action 都来自 held-out model。

### 2. `accept` 仍可能包含 false candidates

当前 accept 层 positive pair rate 是 0.824，不是 1.0。它适合做 expert-priority，不适合自动身份确认。

解决方案：

- 在文本中统一称为 `accept_for_expert_review` 或解释 `accept` 的含义；
- 不输出 automatic identity label；
- 保留 reviewer confirmation requirement。

### 3. Bobcat 仍不能做 identity accuracy claim

Phase 15D 的 action logic 可以 transfer 到 bobcat，但 bobcat 没有 verified individual IDs 时，只能比较：

- action distribution；
- non-comparable rate；
- species-level-only pressure；
- descriptor-evidence conflict frequency；
- manual pair-audit agreement。

不能比较 false-match accuracy。

## 下一步

Phase 15E 应该做 wild-to-urban transfer stress test：

1. 把 Phase 15D action policy 应用到 bobcat candidate pairs；
2. 输出 CzechLynx vs bobcat 的 action distribution；
3. 比较 high-confidence vs low-evidence stress 的 routing shift；
4. 抽样每类 action 做人工 pair audit；
5. 如果 bobcat 没有 identity label，只报告 review-readiness 和 contamination pressure，不报告 identity accuracy。

这一步会把主线完整连起来：

```text
image-level evidence shift
-> pair-level comparability shift
-> review-routing contamination pressure
```
