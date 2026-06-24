# Phase 16A 数据根基审计解释

Date: 2026-06-24

## 为什么先做这个

当前项目的算法和模型都建立在 3000 x 4 的 2x2 数据基础上。如果这个基础存在系统性偏差，后续 PF-ERI、strong-model benchmark、wild-vs-urban 对比都会被污染。因此 Phase 16A 把数据基础本身作为一个可审计对象，而不是把选图当作一次性前处理。

这不是降级。对一个 evidence reliability 项目来说，数据证据是否可采纳本身就是方法的一部分。

## 自动审计结论

审计脚本：

```text
scripts/build_phase16_dataset_foundation_audit.py
```

输出目录：

```text
outputs/phase16/dataset_foundation_audit/
```

核心结果：

| quadrant | status | proxy pass rate | interpretation |
| --- | --- | ---: | --- |
| urban_bobcat_high_confidence | not_ready_rebuild_or_topup_required | 0.6000 | Bobcat high-confidence 当前不能直接作为 90% 干净训练基础。主要风险是动物偏小或 bbox span 不足。 |
| urban_bobcat_low_evidence_stress | pass_for_stress_testing_with_spot_audit | 0.9727 | Bobcat low-evidence stress 基本可用于压力测试。 |
| wild_czechlynx_high_confidence | not_ready_rebuild_or_topup_required | 0.5347 | CzechLynx high-confidence 当前不能直接作为 90% 干净训练基础。主要风险是 MegaDetector 置信度较低，但这可能部分来自检测器对该数据域不适配。 |
| wild_czechlynx_low_evidence_stress | pass_for_stress_testing_with_spot_audit | 0.9877 | CzechLynx low-evidence stress 基本可用于压力测试。 |

## 重要解释边界

这些数值是 conservative proxy，不是最终人工真值。尤其 CzechLynx high-confidence 的失败原因高度集中在 `low_detector_confidence`，这不一定说明图像不可用，也可能说明 MegaDetector 对 CzechLynx 场景、红外、裁切或姿态不够稳定。

因此不能直接说：

```text
CzechLynx high-confidence 只有 53.5% 是好图。
```

更准确的说法是：

```text
在当前 detector-first 代理规则下，CzechLynx high-confidence 只有 53.5% 达到自动高证据门槛，需要人工审计或更适合的动物 Re-ID/姿态/可见性模型复核。
```

## 对下一步的影响

现在不应该直接进入核心训练或强结论比较。更合理的顺序是：

```text
manual audit candidates review
-> diagnose whether failure comes from true low evidence or detector-domain mismatch
-> targeted top-up / stricter re-screen for failing high-confidence categories
-> freeze Dataset v1
-> strong-model benchmark
-> PF-ERI pair-level risk modeling
```

## 具体行动

1. 先复核 `phase16_dataset_foundation_manual_audit_candidates.csv`，每组 150 张，共 600 张。
2. 对 Bobcat high-confidence，重点看动物大小、侧面/身体可比性、边缘裁切。
3. 对 CzechLynx high-confidence，重点判断 MegaDetector 低置信是否真的对应不可用，还是检测器代理过严。
4. low-evidence 两格暂时不需要重建，只保留 spot audit。
5. 如果人工复核确认 high-confidence 真实 precision 低于 85-90%，再做 targeted top-up，不放松规则。

## 与主线关系

Phase 16A 不改变项目主线。主线仍然是：

```text
strong descriptor retrieval
-> PF-ERI pair-level evidence utility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

数据根基审计只是进入这条主线前的质量门槛。
