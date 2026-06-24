# Phase 16C 外部高质量数据源策略

Date: 2026-06-24

## 结论

使用别人已经清理过、用于训练的动物 Re-ID 数据集是合理的，但它们不能无条件混入最终 wild-vs-urban 主数据集。

正确角色分三类：

```text
final candidate source
model/selector training support
reference-only / not suitable
```

原因很简单：如果我们把 zoo tiger、African leopard、hyena、bear、sea turtle 等高质量清理数据直接混入最终比较，模型可能学到的是数据集来源、拍摄方式、圈养环境或物种差异，而不是我们关心的 Lynx wild-vs-urban evidence shift。

## 核心原则

```text
Final 3000 high-confidence images must still come from the target comparison domain whenever possible.
External clean Re-ID datasets should train or calibrate quality/viewpoint/evidence selectors, not replace target-domain evidence.
```

## 可用数据源分级

| source | relevance | recommended role | use in final 3000? | reason |
| --- | --- | --- | --- | --- |
| CzechLynx | highest for wild lynx | final candidate source + pose/view calibration | yes, for wild CzechLynx | same species, identity labels, pose/skeleton/segmentation, target domain |
| AnimalCLEF 2025/2026 lynx subsets | high for lynx Re-ID | benchmark/selector calibration | maybe, only if provenance does not duplicate or leak | contains lynx Re-ID challenge data, useful for method validation |
| FCF bobcat | highest current bobcat source | final candidate source | yes, for urban/periurban bobcat | same species and current source family, but quality varies |
| Snapshot USA / Caltech / NACTI bobcat-like camera trap sources | medium-high | bobcat high-candidate top-up after source tagging | maybe, if metadata/license and urban/periurban definition are controlled | same species possible, but identity labels and cleaned Re-ID evidence usually absent |
| ATRW Amur tiger | medium | viewpoint/pose/flank selector training | no | felid body plan, bounding boxes, pose, identity labels; but zoo tiger, not lynx/bobcat |
| LeopardID2022 | medium | spotted-felid evidence/viewpoint support | no | felid pattern Re-ID with boxes/IDs; different species/context |
| HyenaID2022 | medium | viewpoint classifier calibration | no | has left/right viewpoint labels and boxes; useful for side classifier, not target species |
| WildlifeReID-10k | medium | strong Re-ID benchmark/pretraining/reference splits | no | curated multi-species benchmark, useful for model support but too heterogeneous for final comparison |
| BelugaID / SeaTurtleID / cattle/cow datasets | low for final, useful methodologically | quality/viewpoint method reference only | no | often cleaner, but morphology and Re-ID evidence are too different |

## 对 Bobcat 的现实判断

Bobcat 是当前最难的一格。公开、已清理、个体级 bobcat Re-ID 数据集并不明显存在。很多 bobcat 图片来自 species-level camera-trap datasets，不是 individual Re-ID benchmark。

因此 Bobcat high-confidence 的可靠路径不是寻找一个“完美 bobcat Re-ID 数据集”，而是：

```text
扩大同物种候选池
-> 使用 MegaDetector/LILA MD results 预筛
-> 使用 NR-IQA 清晰度评分
-> 使用 viewpoint/laterality 预筛
-> PF-ERI evidence gate
-> 人工抽样校准
-> 如果仍不足，再引入新 bobcat camera-trap source，并把 source 作为协变量/分层变量
```

## 对 CzechLynx 的现实判断

CzechLynx 本身就是最强数据源，不应该优先引入其他物种替代。更合理的是从未用 CzechLynx pool 中继续扩大 high-candidate manifest，并利用已有 pose/skeleton/segmentation 信息改进角度和可见性判断。

```text
CzechLynx top-up should be same-dataset-first.
```

## 外部清理数据集真正有用的地方

### 1. 训练/校准角度分类器

HyenaID2022、LeopardID2022、ATRW 这类带 viewpoint、bbox、pose 或 ID 的数据可以训练：

```text
left / right / frontal / rear / partial / unknown
```

但迁移到 lynx/bobcat 前必须人工校准。

### 2. 训练质量与证据选择器

外部数据可以帮助学习：

```text
animal crop quality
body completeness
flank visibility
edge crop risk
small animal risk
pose comparability
```

但不能让模型仅学习“漂亮图片”。

### 3. 强模型 benchmark

WildlifeReID-10k、AnimalCLEF、CzechLynx baseline with WildFusion 可以作为比较对象，帮助我们说明 PF-ERI 不是在和弱 baseline 比，而是在强 Re-ID pipeline 之后做 evidence/risk routing。

## 更新后的 Phase 16C 执行路线

```text
1. Build expanded same-domain candidate pools
   - Bobcat: FCF first, then Snapshot/Caltech/NACTI only if shortage remains
   - CzechLynx: unused CzechLynx pool first

2. Build external clean support set
   - ATRW, LeopardID, HyenaID, WildlifeReID-10k, AnimalCLEF/CzechLynx
   - Use for selector training/calibration, not final comparison

3. Run cloud quality + viewpoint scoring
   - NR-IQA on animal crop
   - CLIP / pose / viewpoint classifier
   - detector geometry and edge-crop risk

4. Constrained final selection
   - target n = 3000 per high-confidence quadrant
   - left/right balanced when possible
   - frontal/rear/unknown limited or routed to review/stress
   - source stratification recorded

5. Manual audit
   - 150-300 images per high quadrant
   - target precision >= 90%
```

## Claim Boundary

External clean datasets can strengthen the selector and benchmark story, but final claims must not imply that performance on tiger/leopard/hyena transfers automatically to bobcat/lynx. The paper should phrase this as:

```text
We used external curated animal Re-ID datasets to calibrate quality/viewpoint selection modules, while final wild-to-urban evidence comparisons were performed on target-domain Lynx images with source-stratified controls.
```
