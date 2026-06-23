# Phase 15F Bobcat Pair-Audit Package 分析

## 核心目标

Phase 15F 的目标是验证 Phase 15E 的 bobcat review-routing 是否符合人工证据判断。

它不是 bobcat identity validation。当前 bobcat 没有 verified individual IDs，所以这一步只能验证：

```text
这个 pair 是否可比较？
这个 pair 是否有 individual Re-ID evidence？
系统给出的 accept/review/defer/species-level-only/non-comparable 是否合理？
```

不能验证：

```text
bobcat false-match accuracy
bobcat hit@k
bobcat mAP
bobcat true same/different identity accuracy
```

## 已生成内容

脚本：

```text
scripts/package_phase15f_bobcat_pair_audit.py
```

输出目录：

```text
outputs/phase15/bobcat_pair_audit_package/
```

核心文件：

```text
phase15f_bobcat_pair_audit_manifest.csv
phase15f_bobcat_pair_audit_blank_template.csv
phase15f_bobcat_pair_audit_sample_summary.csv
phase15f_bobcat_pair_audit_250_pair_sheets.zip
phase15f_bobcat_pair_audit_package_report.md
phase15f_bobcat_pair_audit_package_audit.json
pair_sheets/
```

## 抽样设计

每个 Phase 15E action 抽 50 个 pair：

| Action | Pairs | High-confidence queries | Low-evidence queries |
|---|---:|---:|---:|
| accept | 50 | 50 | 0 |
| review | 50 | 25 | 25 |
| defer | 50 | 25 | 25 |
| species_level_only | 50 | 25 | 25 |
| non_comparable | 50 | 25 | 25 |

`accept` 全部来自 high-confidence query 不是错误。Phase 15E 本身几乎没有把 bobcat low-evidence query 路由到 accept，这正是需要人工验证的结果。

## 人工填写列

请在 blank template 中填写：

```text
manual_pair_action
manual_pair_comparability
manual_identity_evidence
manual_review_confidence
manual_same_individual_if_judgable
manual_notes
```

推荐取值：

```text
manual_pair_action:
accept | review | defer | species_level_only | non_comparable | exclude

manual_pair_comparability:
high | medium | low | none | uncertain

manual_identity_evidence:
strong | moderate | weak | none | uncertain

manual_review_confidence:
high | medium | low

manual_same_individual_if_judgable:
same | different | uncertain | not_judgable
```

注意：`manual_same_individual_if_judgable` 是可选判断。没有 verified ID 时，不要强行判断 same/different。很多 pair 应该填 `uncertain` 或 `not_judgable`。

## 这一步能回答什么

Phase 15F 可以支持 RQ4：

```text
In a small human-audited urban bobcat pair set, can PF-ERI identify pairs that should be accepted, reviewed, deferred, or downgraded to species-level evidence?
```

更具体地说，它能检查：

1. `accept` 是否真的具有 strong/moderate identity evidence；
2. `review` 是否确实是人工可判断但需要谨慎的 pair；
3. `defer` 是否代表中间风险，而不是被错误地过度保守；
4. `species_level_only` 是否真的缺少 individual-level evidence；
5. `non_comparable` 是否真的无法做 pair-level Re-ID comparison。

## 当前需要特别关注的问题

Phase 15E 的主要发现是 bobcat 大量进入 `defer`。Phase 15F 最关键的问题是：

```text
这些 defer pair 到底是真的中间风险，还是模型因为跨物种/跨场景校准不足而过度 defer？
```

如果人工审核发现：

- 很多 defer 应该是 review 或 accept，说明 CzechLynx threshold 对 bobcat 过严；
- 很多 defer 应该是 non_comparable，说明模型对低可比性风险不够保守；
- defer 大多确实是 weak/moderate evidence，说明 Phase 15E 的 ambiguity pressure 解释成立。

## 下一步

人工填完：

```text
outputs/phase15/bobcat_pair_audit_package/phase15f_bobcat_pair_audit_blank_template.csv
```

之后进入 Phase 15G：

```text
manual audit agreement analysis
```

要计算：

- system action vs manual action agreement；
- action-specific precision；
- defer 的人工去向；
- accept/review 是否被人工确认；
- species-level-only / non-comparable 的人工确认率；
- high-confidence vs low-evidence 的人工分歧。

这会直接决定 bobcat transfer stress 的置信度。
