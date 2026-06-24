# Phase 16B 高置信照片质量与角度重评分计划

Date: 2026-06-24

## 目标

Phase 16A 发现两个 high-confidence quadrant 没有达到 90% 数据根基门槛。Phase 16B 的目标不是放松规则，而是引入现成预训练模型重新评分 high-confidence 候选照片：

```text
detector geometry
-> no-reference image quality assessment
-> viewpoint / laterality preclassification
-> PF-ERI evidence gate
-> manual calibration
-> balanced high-confidence Dataset v1
```

## 为什么不能只用一个“清晰度模型”

这里必须直接指出一个风险：通用图像质量模型只能判断照片是否清晰、曝光是否自然、失真是否少。它不能保证 patterned-felid Re-ID 证据足够，因为 Re-ID 还需要：

- 动物足够大；
- 侧面或 flank 可比较；
- 花纹区域可见；
- 非前后视角；
- 非严重裁切；
- 左右侧分布不要严重倾斜。

因此 high-confidence 选择必须是多门控系统，而不是单一 quality score 排序。

## 可用现成模型

### 1. No-reference image quality assessment

推荐工具：`pyiqa` / IQA-PyTorch。

原因：

- 它集成了多种 FR/NR IQA 指标和现代深度模型，包括 MUSIQ、TOPIQ、NIMA、BRISQUE、NIQE 等。
- 可以直接在 Colab/Kaggle GPU 上跑，不需要我们本地训练。
- 适合给动物 crop 生成质量分数，避免背景质量掩盖动物本体质量。

候选模型：

- `musiq`: 适合不同分辨率和长宽比的多尺度 IQA。
- `topiq_nr`: top-down semantic-to-distortion IQA，适合关注语义区域的失真。
- `maniqa`: CVPRW/NTIRE 系列 NR-IQA 模型，可作为备选。
- `brisque` / `niqe`: 传统无参考质量基线，速度快，可作为 sanity check。

### 2. Viewpoint / laterality preclassification

推荐起步：CLIP/OpenCLIP zero-shot prompts。

用途：

- 先粗分 `left_side`, `right_side`, `frontal`, `rear`, `partial_or_occluded`, `unclear`。
- 作为人工复核优先级和 laterality balance 的预筛，不作为最终标签。

更强后续方案：

- SuperAnimal / DeepLabCut Model Zoo 做 quadruped pose/keypoint inference。
- 如果 pose 关键点稳定，再用左右关键点、头尾方向、躯干可见性推断 flank/viewpoint。

边界：

```text
CLIP viewpoint is a prefilter, not final laterality truth.
SuperAnimal pose is stronger but heavier, and may still require domain calibration on camera-trap felids.
```

## 当前执行包

脚本：

```text
scripts/package_phase16_high_confidence_quality_viewpoint_rescore.py
```

输出：

```text
outputs/phase16/high_confidence_quality_viewpoint_rescore/
```

主要文件：

```text
phase16_high_confidence_quality_viewpoint_manifest.csv
run_phase16_quality_viewpoint_colab.py
README.md
phase16_high_confidence_quality_viewpoint_package_audit.json
```

Colab/Kaggle 命令：

```bash
pip install -q pyiqa open_clip_torch pandas pillow tqdm
python run_phase16_quality_viewpoint_colab.py \
  --manifest phase16_high_confidence_quality_viewpoint_manifest.csv \
  --output phase16_high_confidence_quality_viewpoint_scores.csv
```

## 返回结果怎么用

返回分数后，不直接用最高分 3000 张。正确做法是：

1. 先剔除明显低质量、unclear、partial、frontal/rear-only、edge crop 风险样本。
2. 按 `left_side/right_side/both/frontal/rear/unknown` 分层。
3. 对 high-confidence set 做 laterality-balanced selection。
4. 每个 quadrant 抽样人工复核，目标 precision >= 90%。
5. 只有通过这一步的数据才能冻结为 Dataset v1 high-confidence clean set。

## 与 PF-ERI 主线关系

这一步不改变主线。它是 PF-ERI 前的数据根基升级：

```text
High-quality image != Re-ID evidence.
High-quality + correct viewpoint + flank/pattern visibility = candidate Re-ID evidence.
PF-ERI then evaluates whether pair-level evidence is admissible.
```

## 文献与工具依据

- IQA-PyTorch / `pyiqa` provides a PyTorch toolbox for IQA and includes many FR/NR metrics including MUSIQ, TOPIQ, NIMA, BRISQUE, and NIQE.
- MUSIQ was designed for multi-scale image quality assessment on native-resolution images with varying sizes and aspect ratios.
- TOPIQ proposes a top-down approach from semantics to distortions for IQA and supports no-reference IQA.
- HyperIQA separates content understanding, perception rule learning, and quality prediction for blind image quality assessment in the wild.
- SuperAnimal provides pretrained pose estimation models usable across more than 45 species and supports fine-tuning/video adaptation when needed.

## Claim Boundary

Do not claim that IQA or CLIP alone identifies usable individual evidence. The defensible claim is that Phase 16B adds pretrained quality and viewpoint gates before PF-ERI pair-level modeling, reducing the risk that high-confidence sets are polluted by small, cropped, blurry, frontal/rear, or laterality-imbalanced images.
