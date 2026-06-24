# Phase 16D 扩展高置信候选池

Date: 2026-06-24

## 目标

为了保证最终 high-confidence 照片的清晰度、动物完整度、可对比度和角度平衡，不能只从当前 3000 张里修补。Phase 16D 建立更大的同域候选池，再交给云端模型做：

```text
detector / pose
-> no-reference image quality
-> animal crop quality
-> viewpoint / laterality
-> PF-ERI evidence gate
-> constrained final selection
```

最终目标仍然是：

```text
urban_bobcat_high_confidence: 3000
wild_czechlynx_high_confidence: 3000
```

但这 3000 张必须从更大的候选池中筛出，而不是硬凑。

## 当前已找到的同域候选池

脚本：

```text
scripts/package_phase16_expanded_high_confidence_candidate_pool.py
```

输出：

```text
outputs/phase16/expanded_high_confidence_candidate_pool/
```

核心文件：

```text
phase16_high_confidence_source_registry.csv
phase16_expanded_high_confidence_candidate_manifest.csv
phase16_expanded_high_confidence_candidate_pool_audit.json
```

当前候选数量：

| target quadrant | source | candidate count | current use |
| --- | --- | ---: | --- |
| urban_bobcat_high_confidence | FCF bobcat rows passing LILA MegaDetector high-geometry prefilter | 6412 | final candidate source |
| wild_czechlynx_high_confidence | CzechLynx real local image pool | 39760 | final candidate source |

## 为什么这两个来源优先

### Bobcat

FCF 是当前最相关的 bobcat 来源：同物种、San Francisco Bay Area/urban-edge context、LILA 可公开访问，并且已有 MegaDetector 预筛结果。当前我们只选择已经通过高几何质量预筛的 6412 张作为 high-confidence 候选，不把所有 bobcat 图直接送入最终筛选。

### CzechLynx

CzechLynx 是最强 wild lynx 来源：同属同目标物种，且包含 identity、pose、segmentation 等信息。当前候选池使用真实图像，不使用 synthetic images，也不在 cloud manifest 中暴露 sensitive location 或 individual identifier 字段。

## 外部清理数据集的角色

ATRW、LeopardID2022、HyenaID2022、WildlifeReID-10k 等清理数据集仍然有价值，但它们不能直接进入 final wild-vs-urban 3000 张主数据。

它们的正确用途是：

```text
quality/viewpoint/flank selector training
strong-model benchmark context
methodological sanity check
```

不是：

```text
replace target-domain bobcat/lynx evidence
```

## 下一步云端模型要求

Bobcat:

```text
download_url -> crop by existing MD bbox -> IQA -> viewpoint/laterality -> final score
```

CzechLynx:

```text
local/uploaded image -> detector or pose model -> crop -> IQA -> viewpoint/laterality -> final score
```

云端返回后，最终选择不能简单 top-3000。必须使用 constrained selection：

```text
maximize quality + PF-ERI evidence utility
subject to:
  animal completeness high
  side/flank/pattern comparable
  frontal/rear/partial limited
  left/right balanced where possible
  duplicate/near-duplicate controlled
  source/provenance recorded
```

## Claim Boundary

这些 46172 张不是最终数据集。它们只是高置信候选池。最终 high-confidence Dataset v1 只有在质量模型、角度模型、PF-ERI gate 和人工抽样复核都通过后才能冻结。
