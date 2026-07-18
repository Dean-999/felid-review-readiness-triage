# PF-ERI 全项目第一性原理、对抗式与横纵分析报告

> 研究时间：2026-07-10 | 所属领域：野生动物 Re-ID、生态证据治理、应用数学与风险控制 | 研究对象类型：跨学科科研项目与方法框架

## 执行结论

PF-ERI 最有价值的部分不是当前模型分数，而是它指出了一个真实而未被充分形式化的断层：强 Re-ID 描述符回答“哪些图像相似”，生态工作流还必须回答“这对图像是否包含足以进行负责任人工判断的证据”。“Similarity is not admissibility”仍然是一个有科学张力、保护价值和跨学科潜力的核心故事。

但本次对抗审查推翻了“当前 400 对结果已经确认 PF-ERI”的判断。现有证据最多支持：在一个经过 PF-ERI 极端分层抽样、审查界面存在分组泄盲、特征机制大多由常量代理构成的数据集上，少数代理信号与人工 reviewability 标签存在探索性关联。它不能确认完整 PF-ERI 机制，不能确认部署风险，不能确认预算收益，也不能支持跨物种通用性。

本报告因此给出一个明确决策：

> 保留科学问题，冻结 PF-ERI v1 为探索性原型，停止分发或填写当前 Phase18N 审查包并将其保留为只读审计证据，重建 PF-ERI v2 的真实证据特征、真盲标签、无序对数据合同、身份隔离验证和成本敏感选择性路由，然后用全新未揭盲样本做一次性确认。

在我们共同接受的“100% 信心”定义下，我对这条策略方向有充分决策信心：所有已经发现的致命问题都要求进行 v2 重建；新策略具备明确失败条件，且允许确认结果推翻模型。这个信心不等于对 PF-ERI v2 最终产生正结果有 100% 概率。

### 当前证据等级

| 主张 | 审查后等级 | 解释 |
| --- | --- | --- |
| Re-ID 检索之后仍存在人工证据准入问题 | 中高 | 生态误识别后果、Wildbook 工作流、photo-ID 文献与项目负结果共同支持 |
| reviewability 是可重复测量的构念 | 低到中 | 一套 synthetic 可靠性无效，外部审查来源待核验，主 400 的一致性仅中等 |
| PF-ERI v1 对 reviewability 有独立预测增量 | 低 | 泄盲、极端抽样、代理特征和重复计权共同降低可信度 |
| PF-ERI v1 超越了强质量与相似度控制 | 很低 | 所谓质量控制主要是整图分辨率兼容，descriptor-specific 增量为负 |
| 当前路由能节省部署审查成本 | 很低 | 旧代路由、同样本模拟、基线污染、没有人工时间数据 |
| Bobcat 或其他物种上的身份有效性 | 无证据 | 身份标签合同不存在；当前只能做 pipeline stress |

## 一句话定义

PF-ERI 应被定义为一个位于候选检索之后、身份决策之前的 pair-level evidence-admission 框架：它估计候选图像对是否具有可比、可审查、可追溯的个体层证据，并在有限人工预算和显式错误成本下执行 admit、review 或 defer。

## 第一性原理重建：项目究竟要解决什么

### 1. 从下游科学决策倒推

相机陷阱个体识别不是一个孤立的分类任务。照片经由候选检索、人工个体判断、遭遇历史构建，最终可能进入捕获—再捕获、密度估计、活动范围和保护管理。错误并不会停留在一张图片上。已有雪豹实验显示，观察者个体误识别会系统性抬高种群数量估计；相机陷阱个体识别报告规范也要求明确处理不可分类照片、观察者分歧和误识别风险。

因此，PF-ERI 的根问题不是“能否得到更高 AUROC”，而是：

> 哪些候选图像对有资格进入个体证据链，哪些必须延期、补充证据或排除？

### 2. 正确的分析单位

证据准入的基本单位不是单张图像，也不是描述符得分，而是一个无序物理图像对及其工作流上下文。单张高质量图片与另一张不同体侧或无共同身体区域的图片组合后，仍可能不可比。相反，一个不同身份的图像对也可能高度可审查，因为观察者能够可靠排除它。

由此得到三个不变量：

1. reviewability 不等于 same identity；
2. pair admissibility 原则上对图像顺序对称，候选 rank 等检索上下文可以是方向性的附加变量；
3. 同一物理图像对不能因为被两个描述符或两个方向检索到，就被当成多个独立证据单元。

### 3. 正确的决策对象

设图像对为 p，真实但不可直接观察的证据准入状态为 A(p)，模型输出为 q(p)=P(A=1|x)。系统动作不是身份赋值，而是：

```text
a(p) in {admit, expert_review, defer}
```

错误准入、错误延期和专家审查时间具有不同成本。一个最小而完整的应用数学对象是：

```text
Expected loss =
  C_false_admit * P(not-ready and admit)
  + C_false_defer * P(ready and defer)
  + C_review * P(expert_review)
```

模型应在给定预算、成本比或最大可接受经验风险下选择动作。真实成本目前未知，因此论文应报告成本敏感性区域和策略反转点，而非虚构一个普遍成本函数。

### 4. 真正可证伪的核心假设

PF-ERI v2 的确认性假设应被压缩为：

> 在一个未参与特征开发、模型选择或阈值选择的代表性 CzechLynx 候选队列中，标签独立生成的 pair-evidence 特征，相对于“描述符相似度＋独立单图质量”主动对照，能够改善预先指定的概率评分指标，并在预先指定的成本/预算区域中降低错误准入或无效专家审查负担。

如果严格外部验证没有增量、效应在身份/图像组件隔离后消失、或输入特征采集成本接近直接专家审查成本，则 PF-ERI 模型主张失败。届时项目可以保留“证据准入”测量框架，但必须放弃“已验证自动路由模型”的表述。

## 纵向分析：这个项目如何走到今天

### 阶段一：单图 review-readiness 的朴素起点

项目最初研究单张图像是否适合进入 Re-ID。200 张 CzechLynx 图片被分为 review-ready、review-limited 和 unidentifiable；30 张延迟复审得到主标签 Cohen's kappa 约 0.700。固定 ResNet-50 的 400 个配对比较只有约 0.619 AUROC。最严格的 ready-only gate 虽减少错误代理，却只保留约 3% 的 same-ID 证据。

这个负结果非常重要。它揭示了第一个第一性原理错误：单图“好不好”不能代替两图“能不能比较”。严格图像过滤还可能摧毁覆盖率。

### 阶段二：从图像质量转向 pair-level weakest evidence

随后项目开始记录 weakest image、视角、可见身体区域和共享证据。研究对象从单图 readiness 逐步转向图像对。这是核心概念第一次真正出现：证据质量由两张图的共同可比较部分决定，而不是由平均画质决定。

### 阶段三：Re-ID 性能路线连续遇阻

项目随后尝试 fixed-descriptor filtering、risk–coverage、reranking、evidence utility 和 metric learning。结果并没有稳定提高 mAP；projection-head 训练还可能损害强描述符几何，且无法稳定胜过 matched controls。项目因此将 metric learning 降为诊断或可选层。

这些失败并非项目污点。它们构成当前故事的真实历史根源：PF-ERI 不应与 MegaDescriptor、DINOv2 或 WildFusion 正面竞争身份排名，因为实验已经多次表明这不是最有证据的方向。

### 阶段四：Bobcat 反复强化了初始主张边界

Bobcat/WildTrax 从项目初始版本就被限定为 field motivation 和 field-readiness stress test，因为缺少可靠个体身份标签。后续 wild/urban 扩张没有改变该边界，而是反复验证并强化它：Bobcat 只能作为 transfer-stress 和 workflow-allocation 场景，不能支持 identity accuracy、false-match accuracy、mAP、MRR 和 top-k 主张。这一治理边界是项目做得最成熟的部分之一。

### 阶段五：概念先形成，强实证与 slogan 后完成

pair-level evidence admissibility 至少在 2026-06-17 已被形式化，06-22 出现 evidence-routed review layer，06-29 又被锁为 post-retrieval review utility。07-02 至 07-06 的强描述符、matched review、descriptor-controlled 和 identity-balanced 分析主要负责实证闭合；07-09 至 07-10 才形成“Similarity is not admissibility”的 slogan、贡献层级和论文故事包装，并组织模型比较、后验敏感性、具体预算展示、反驳矩阵、主张审计和初稿。

这个故事不是凭空编造，而是由三个真实失败收敛而来：单图 gate 丢失证据、PF-ERI 不稳定改善排名、metric learning 损害强描述符。但它仍然属于结果后形成的理论框架。现有 400 行不能被描述成对原始预注册假设的确认性检验；应诚实写成“探索迭代使研究对象从 image quality 收敛到 pair-level evidence admission”。

06-08 至 06-29 的多段 daily log 明确标注为 `reconstructed` 或 `reconstructed from artifact times`，不是同期预注册日志。工件顺序支持“负结果与转向相关”，但不能把重构叙事写成无争议的实时因果记录。风险—覆盖率和 review-budget tradeoff 从最初 Q2 就存在；后验部分是具体预算点的选择、同一 400 样本上的新路由模拟，以及这些结果在最终故事中的突出位置。

### 纵向遗留包袱

历史的好决策也带来今天的包袱：

- 为寻找机制而进行的 high/low PF-ERI 富集抽样，后来被用于校准和预算模拟；
- 多次 phase 转向留下不同代际的模型、路由和阈值，当前论文表与旧 risk-route 文件并非同一证据链；
- story hardening 在看到结果后重新组织了贡献层级、具体预算展示和敏感性，因此属于稳健性探索，不是事前设计；
- 名为 2026-07-08 且被 README 称为 authoritative 的 freeze 工作文件后来继续被修改，却仍保留旧模型数字；它与当前 manuscript-facing working Table 2 使用不同 AUROC，说明不可变冻结和版本治理同时失效。

当前权威层也尚未形成可复现 commit/tag。发生冲突时，应以 `PROJECT_RULES.md`、`docs/CURRENT_PROJECT_MAP.md`、`current_pipeline_manifest.md` 和 pair-level validation README 的绑定顺序解释项目；`paper/manuscript/main.md` 只是编辑工作稿，`paper/project_report_draft.md` 已被 supersede，`docs/archive/` 与 `scripts/legacy/` 只用于历史和复现。当前 `paper/` 和大量 story-hardening 工件仍未提交到版本控制，这是提交前必须解决的治理风险。

## 对抗式科学审查

### 致命问题 1：主 400 对不是严格盲审

Phase18M 包按 PF-ERI high/low、same/different identity 和高相似度条件构造。更严重的是，实际 Streamlit 审查界面允许按 HIGH/LOW PF-ERI 和 same/different ID 筛选，并在图片上方显示 PF-ERI/identity group 与 descriptor rank。即使 blind CSV 不含这些列，也无法证明审查者只使用 CSV 而没有使用界面。

这会造成 expectation bias 和构念循环：预测变量的分组信息直接暴露给结果标注者。现有 400 对标签与 PF-ERI 分数的关联因此不能被当作真盲确认性效应。

主 400 的原始 reviewer working files 当前也已不存在，只保留派生 label-detail 和 majority artifacts。第三方无法从原始事件日志核验审查者、时间、界面版本以及是否使用了泄盲筛选。这使标签来源链无法端到端重建。

判定：现有 400 对整体降级为 exploratory。修复方式不是统计调整，而是由未接触原分组的新审查者，在完全隔离 full packet 的界面中重新盲审。

### 致命问题 2：两套可靠性证据中一套是 synthetic

论文突出报告 κ=0.859 和 κ=0.785。实际审计显示，κ=0.859 的第一套 280 行审查者为 `synthetic_calibration_reviewer_1`，备注明确写着“not independent blind evidence”。它不能用于证明人类构念可靠性。

κ=0.785 的第二套文件被后补文档声明为独立外部审查，但 CSV 仍保留 synthetic 备注，且所有行时间戳相同。这个结果可能是真实外部审查，但当前来源链不足以让第三方独立核验。更重要的是，该 280 对是 145 lynx、123 bobcat 和 12 other 的混合集，并非主 400 CzechLynx 的直接三人复核。

主 400 的实际 reviewer-pair binary kappa 约为 0.423–0.613，明显低于论文重点展示的两个数值。论文应删除 κ=0.859；在获得审查者签署确认和原始日志前，将 κ=0.785 标为 provenance-pending。v2 确认集应直接计算双审/三审一致性、分物种一致性和裁决敏感性。

### 严重问题 1：名义六特征，实际四个常量

正式 400 行验证表中：

| PF-ERI 特征 | 唯一值数量 | 实际含义 |
| --- | ---: | --- |
| visible_pattern_area_score | 1 | CzechLynx 固定 0.74 |
| viewpoint_side_compatibility | 1 | CzechLynx 固定 0.70 |
| body_part_overlap_score | 315 | 主要为 0.78 × 两张整图分辨率面积兼容度 |
| night_or_motion_blur_risk | 1 | CzechLynx 固定 0.18 |
| cross_descriptor_agreement_score | 319 | MegaDescriptor 与 DINOv2 相似度一致性 |
| source_domain_shift_score | 1 | 同域 CzechLynx 固定 0.10 |

因此，当前 PF-ERI evidence-only 模型实际主要依赖整图尺寸兼容和两个描述符的一致性。它没有验证论文所描述的真实花纹面积、体侧/视角兼容、身体区域重叠和夜间/运动模糊机制。

### 严重问题 2：质量主动对照不是真正的质量控制

quality-only 由 visible pattern、body overlap 和 blur risk 组成，但前后两个是常量，body overlap 又主要是分辨率比。严格的“descriptor + quality”对照实际上只控制了描述符相似度和粗糙整图尺寸兼容。

正式 pooled 结果从 descriptor+quality AUROC 0.772 增至 full 0.786，AUPRC 从 0.882 增至 0.885；增量分别只有 0.014 和 0.003。两个 descriptor-specific 严格增量均为负。这个结果不能支持“PF-ERI 超越了独立图像质量和描述符相似度”的强表述，只能支持少数代理信号在富集样本中的探索性关联。

### 严重问题 3：400 行只有 319 个唯一无序图像对

直接重算得到：

- 400 行；
- 319 个唯一 unordered physical pairs；
- 75 个重复图像对组，共产生 81 条额外行；
- 11 个重复组的 reviewability 标签相互冲突；
- 相同图像对可因方向或描述符来源被重复计权。

pair-level evidence admission 的物理单位原则上是无序对。方向、rank 和 descriptor membership 可以作为上下文列，但不能把同一证据单元当作独立样本。确认集必须在抽样前建立 canonical unordered_pair_id，跨描述符去重，冲突对进入裁决。

### 严重问题 4：拆分避免图像泄漏，但没有实现身份外推

当前图像连通分量拆分成功避免同一图片跨 fold，这是一个优点。但 79 个 identity 中约 42 个跨 fold，因此结果不能解释为对 unseen identities 的泛化。代码还把 `component_group_id` 写成 `fold_component_{fold}`，丢失约 90 个真实图连接组件；后续所谓 component bootstrap 实际只在 5 个 fold 上重采样。

v2 至少需要两套互补验证：

1. unordered-pair/image-component-disjoint，用于防止同图泄漏；
2. identity-disjoint 或 identity-graph-disjoint，用于评估对新个体的泛化。

当前主文 AUROC/AUPRC 的 95% 区间还是 row-level bootstrap，忽略 query、candidate、identity 和重复无序对依赖，因此不能用于确认性推断。后续所谓 component bootstrap 又把 5 个 fold 当作组件。v2 必须预先指定真实 network component 或 multiway cluster bootstrap 的重采样单位，并同时报告 identity-cluster sensitivity。

### 严重问题 5：抽样是 predictor-enriched case-control，不是部署队列

主 400 对按 PF-ERI high/low、same/different 和高相似度富集。这样的设计适合寻找机制，但 ready prevalence、Brier、ECE、coverage 和预算收益不再对应真实候选队列。AUPRC 也受人为 prevalence 影响。

未来应维护两个不同数据集：

- mechanism stress sample：跨质量、相似度和证据状态富集，用于验证构念与失败机制；
- deployment-representative queue sample：从冻结 top-k 队列按已知概率抽样，用于校准、风险—覆盖率和预算效用。

如果使用分层抽样，部署估计必须报告 inclusion probabilities 并进行适当加权。

现有 Issue4 的 quality/similarity sensitivity 也不能修复这个问题。quality proxy 和 PF-ERI signal 共享 `body_part_overlap`，而该字段主要是整图分辨率兼容；median split、0.82/0.90 bins 和多个 strata 都是在看到数据后建立，缺乏聚类区间和多重性控制。“所有可估计 pooled strata 方向为正”只能是探索性描述，不能替代独立主动对照。

### 严重问题 6：模型、路由与预算结果不是同一代工件

当前正式模型 full AUROC 约 0.786；高级建模和 risk router 仍引用约 0.799 的旧代模型。Issue5 又把旧 `risk_calibrated_pair_routes.csv` 合并到新的 validation table。Bobcat 使用的阈值也来自旧代路由。

因此，预算 100/200 的结果不是当前论文模型的完整端到端结果。所有下游表格必须携带 input SHA256、代码 commit、model_version、label_version 和 feature_version；上游哈希变化应使下游工件自动失效。

### 严重问题 7：预算收益不是独立前瞻验证

PF-ERI queue 使用同一 400 行标签训练得到的 OOF 分数排序，并在同一设计样本上审核预算收益。不同 fold 的 OOF 概率来自不同模型，未统一外部校准。descriptor baseline 在相似度相同时还使用 evidence score 作为 tie-breaker，污染了纯描述符基线。七个预算中突出 100 和 200 也存在结果后选择风险。

当前“4/7 budgets 改善”只能视为探索性模拟。v2 需要一个从未参与训练和阈值选择的 test queue，固定单一模型；descriptor baseline 的排序不能引用任何 PF-ERI 字段；主要预算或成本区域必须事前指定，并使用配对、聚类感知的不确定性分析。

当前 5 folds 的行数为 30、42、65、111 和 152，标签分布也严重不均；固定的 L2、学习率和训练轮数没有 nested selection。由这些 OOF 概率直接比较 Brier/ECE 或跨 fold 排序并不稳健。v2 应在 development 内完成模型选择，再用单一冻结模型分别校准和测试。

### 严重问题 8：risk-calibrated 目前只有经验阈值

现有路由在 calibration rows 中搜索经验风险小于 alpha 且覆盖率最大的阈值，没有使用有限样本上界或严格 conformal correction。校准折只有 141 行且类别/组件不平衡。它只能称 empirical selective routing，不能称风险保证。

如果未来使用 conformal risk control，必须明确交换性/校准假设、独立校准集、损失定义和有限样本上界；如果条件不满足，就保留成本敏感 reject option，而不要追求听起来更高级的保证语言。

### Phase18N 当前包为什么必须停用

当前 Phase18N 已生成 1200 行、三审查者空白表，标签尚未污染，这是好消息。但包本身有结构性问题：

- 1200 行只有 1108 个唯一无序图像对，存在 92 条重复行；
- 49 个图像对跨 descriptor 重复；
- 所有 1200 行都进入 `quality_low`，质量分层完全塌缩；
- 大量输入图像依赖 fallback path，DINO 候选总体又因图像缺失发生大规模排除；
- 包仍基于 v1 代理特征和旧 PF-ERI strata。

因此，Phase18N 的 `PASS` 只表示脚本成功生成文件，不表示科学设计通过。结果标签表格尚为空，所以现在停止仍能避免浪费最珍贵的独立标签资源。

### Bobcat 54,000 对不是外部验证队列

当前 Bobcat 54,000 对来自确定性 circular pair scaffold，不是两个强描述符真正返回的候选队列；转移脚本还将 descriptor similarity percentile 固定为 0.5。最终 54,000 对中 53,936 对被 defer、只有 64 对 accept，主要反映输入合同失配和外推压力。这个结果甚至不能证明迁移可用性，只能称 pipeline smoke test，不能用“54,000”这个数字制造外部效度印象。

## 横向分析：PF-ERI 在当前技术版图中的位置

### 1. 强描述符与 benchmark

WildlifeDatasets/MegaDescriptor 建立了多数据集训练、工具链和强描述符基线；WildlifeReID-10k 覆盖超过 10,000 个体、约 33 个物种和超过 140,000 张图像，并特别设计时间与相似度感知拆分以减少训练—测试泄漏。DINOv2 则提供强通用视觉表示。

PF-ERI 在规模、身份排名和表征学习上不应与这些工作竞争。它的机会在于：在本报告核查的这些方法官方目标与报告指标中，未见 human pair reviewability 被作为独立终点。WildlifeReID-10k 本身也没有 reviewability 标签，只能成为 candidate pool 或上游 benchmark，重新标注后才能验证 PF-ERI。

### 2. WildFusion 与局部匹配

WildFusion 融合全局深度相似度和局部匹配相似度，并通过 dataset-specific similarity-score calibration 提高个体识别准确率；这种校准服务于身份相似度融合，不是 P(review-ready) 的概率校准。它已经占据“强身份排名＋全局/局部融合”的位置。PF-ERI 若把 cross-descriptor agreement 或局部几何简单包装成新融合算法，会被 WildFusion 直接压制。

PF-ERI 的差异必须落在终点上：WildFusion 问谁更可能是同一个体；PF-ERI 问这对图像有没有足够证据让人承担身份判断。

### 3. Wildbook/WBIA/Flukebook 等平台

Wildbook 的官方流程已经包含检测、annotation、一个或多个 ID 算法、候选列表和人工确认；官方明确表示系统辅助 photo-ID，而不是代替用户作最终决定。平台还处理 viewpoint、手工 annotation、候选 rank 和 matched-feature 可视化。

PF-ERI 不能声称发明了“人机协作 Re-ID”。它真正可能增加的是一个可测量、可校准、可审计的 pair-admission 状态，以及在有限审查预算下的路由规则。这是一项平台内决策标准，而不是替代平台。

### 4. 生物识别质量评估

biometric sample quality 领域早已将“质量”定义为对识别效用的预测，而不只是人眼画质；常用 error-versus-discard 或 utility-based 评价检验丢弃低质量样本后错误如何变化。这与 PF-ERI 很接近。

PF-ERI 的潜在新增点不是把 single-sample utility 首次扩展到 pair，而是将既有 pairwise biometric utility 操作化为 wildlife-specific、human-examiner evidence utility：体侧、共同身体区域、花纹可见性和最弱图像共同决定专家是否有资格作判断。论文必须主动承认这条理论祖先，并用真正独立的 quality baseline 证明 wildlife pair-specific 信息有增量。

这里还有一个更直接的理论先例。NIST 早在 2011 年就用“quality comes in pairs”说明生物识别质量不总是单图内在属性：同一张高质量人脸图像与不同参考图配对时，匹配难度可以完全不同。因此，PF-ERI 不能把“质量是成对关系”写成原创发现。ISO/IEC 29794-1:2024 主要讨论样本对自动识别的 utility，并排除了 human examiner utility；PF-ERI 更干净的空白恰恰是面向人类审查者的 wildlife pair-evidence utility。

### 5. 已有 wildlife suitability 与人工路由先例

非洲野狗 photo-ID 已使用自动裁剪、不适合图像过滤、站立姿态识别、左右体侧分类和背景去除；海豚 photo-ID 已使用分级图像质量、个体 distinctiveness、双人确认和困难案例裁决；蝾螈 photo-ID 也已用相似度阈值把有限人工检查分配给低分候选。这些工作直接否定以下潜在原创性表述：首次筛选适合 Re-ID 的图像、首次引入人工复核、首次使用相似度阈值分配有限人工审查。显式成本函数、成本优势区域和证据准入风险仍可能构成 PF-ERI 的领域化增量。

PF-ERI 仍可能占据的窄空白是：在强 wildlife Re-ID 检索器之后，以独立盲审标签预测“这对图是否足以供专家作证据判断”，并将 pair-relational evidence、成本敏感动作和审查可靠性绑定为同一验证合同。即便系统综述没有发现完全相同工作，论文也应使用“we operationalize”而不是未经系统检索的“we are the first”。

### 6. selective prediction、reject option 与 conformal risk control

SelectiveNet 等方法已经系统研究覆盖率与拒绝风险；conformal risk control 提供在明确假设下控制一般损失的形式工具。因此，“有拒绝选项”或“风险—覆盖率”本身不是 PF-ERI 的方法学新颖性。

PF-ERI 的创新只能是领域对象和测量合同：为 wildlife Re-ID 候选对定义证据准入终点、特征接口、人工标签协议和保护工作流成本。数学工具负责使这个对象可操作，而不是成为故事主角。

### 7. 更强上游会压缩 PF-ERI 的价值空间

除了 MegaDescriptor 和 DINOv2，MIEW-ID preprint 报告其已在 Wildbook 中用于 60 多个物种；WildFusion 的局部匹配覆盖和全局/局部分歧又可能吸收当前 PF-ERI 的主要信号。CARE 等语义特征对齐方法也在直接缓解 pose、occlusion 与部分可见问题。

因此，v2 主动对照至少应包含：强全局相似度、rank/margin、学习式单图 utility 的 min/mean、左右体侧与 pose 兼容、WildFusion global/local/fused score、局部匹配覆盖和 ensemble disagreement。PF-ERI 必须证明自己不是这些已有信号的重命名。

### 8. 横向定位矩阵

| 技术线 | 主要输入 | 主要终点 | 已有强项 | PF-ERI 应占的位置 |
| --- | --- | --- | --- | --- |
| MegaDescriptor | wildlife-specialized 单图表示 | 候选相似度、身份排名 | 多数据集训练与跨数据集迁移 | 上游候选生成 |
| DINOv2 | 通用自监督单图表示 | 通用视觉特征 | 强通用表示 | 上游通用 backbone 对照 |
| WildlifeReID-10k | 多物种身份数据 | 公平 Re-ID benchmark | 规模、泄漏控制 | candidate pool/评估规范；需新标 reviewability |
| WildFusion | 全局与局部相似度 | 身份准确率 | 融合与校准 | 主动身份排名对照，不是同一终点 |
| Wildbook/WBIA | annotation、算法候选、人工操作 | 最终人工 ID 工作流 | 成熟平台与审查界面 | PF-ERI 的潜在集成环境 |
| biometric quality | 单样本或比较效用 | recognition utility、discard curves | 质量—效用形式化 | 独立质量主动对照与理论邻居 |
| wildlife suitability/photo-ID QC | 单图、体侧、姿态、人工规则 | 是否进入 photo-ID 或匹配成功 | 已有质量分级、体侧过滤和人工裁决 | PF-ERI 必须区分 pair human-evidence endpoint |
| reject/selective prediction | 预测概率与拒绝动作 | risk–coverage | 通用风险理论 | PF-ERI 的数学工具箱 |
| PF-ERI v2 | pair evidence＋检索上下文 | 人工 evidence admission | 尚待确认 | 领域化 pair-evidence measurement 与 routing |

## 保护实例横向选择：Mainland Clouded Leopard 与 Marbled Cat

### Mainland Clouded Leopard

Mainland Clouded Leopard 已有直接的相机陷阱个体识别与空间捕获—再捕获实践。研究者利用独特云状皮毛区分个体，有些研究只使用照片更多的一侧；其他研究明确区分双侧完整个体和仅单侧记录。这与 PF-ERI 的体侧、共同区域和不可比证据问题高度一致。

它适合作为首选保护实例，因为“图像是否足以进入个体识别”已经直接影响密度和捕获历史，而且现有文献能给出真实工作流约束。缺点是公开、带身份与许可的原始图像未必容易获得。

### Marbled Cat

Marbled Cat 的密度研究同样依赖天然花纹个体识别，并明确记录了一部分独立照片“无法识别到个体”而被排除。这为 evidence admission 提供了非常直接的保护动机。关键证据来自 Sabah, Malaysian Borneo；它证明该场景可行，但 Borneo/Sumatra/Indochina 之间的 pelage 与潜在分类域差异意味着 Sabah adapter 不能无校准外推到 mainland population。它体型更小、影像更稀少，可能更能展示低数据和低可见性压力，但也更难获得足够确认样本。

### 推荐顺序

在数据访问和许可条件相当时，主保护案例优先 Mainland Clouded Leopard，Marbled Cat 作为第二案例或稀缺数据压力测试。但当前没有核实到任何可直接使用的公开、带身份且可授权的原始 pair-image corpus；实际选择必须由书面数据意向、raw-image audit、identity provenance 和四个门槛决定：合法许可、可审计图像、pair-level reviewability 标签、清楚的保护工作流问题。如果没有身份标签，只做 evidence admission，不做 identity accuracy。

## 横纵交汇：历史如何决定今天的生态位

PF-ERI 今天最强的优势，来自它曾经失败过。单图 gate 的失败迫使项目承认 comparability 是 pair-level；mAP 和 metric learning 的失败迫使项目退出描述符竞赛；Bobcat 标签缺失迫使项目建立严格主张边界。这些历史节点把项目推到一个更窄但更真实的位置。

今天最弱的部分也来自同一历史。为了快速验证转向，项目用常量和代理构造了证据特征；为了寻找信号，富集 high/low PF-ERI；为了把故事组织成论文，后验增加了预算与敏感性分析。早期作为原型合理的选择，在论文阶段变成了机制错位、抽样偏倚和 HARK 风险。

真正的升级不是换一个更复杂模型，而是把历史上混在一起的三件事拆开：

1. 证据构念如何测量；
2. 模型如何预测构念；
3. 工作流如何根据成本采取动作。

当这三层被独立验证，PF-ERI 才会从“一个好故事包裹的代理分数”变成“一个可被其他研究者复用的证据准入标准”。

## 新策略：PF-ERI v2

### 总体架构

```text
强描述符候选队列
  -> canonical unordered pair contract
  -> 物种适配器：检测、身体部位、体侧/姿态、花纹区域、模糊/遮挡
  -> 标签独立的 pair-evidence features
  -> calibrated P(reviewable evidence | pair)
  -> cost-sensitive {admit, expert review, defer}
  -> 风险、覆盖率、时间成本和审计日志
```

通用性放在稳定接口、动作空间、损失定义、校准和审计协议上；物种差异由 adapter 处理。不要声称一个模型无校准跨所有物种通用。

### Workstream 0：立即隔离 v1

- 将现有 400 行、Figures 2–4 和预算结果标为 exploratory/provisional；
- 删除 κ=0.859 的人类可靠性表述；
- 将 κ=0.785 标为 provenance-pending，直到取得签署确认与原始记录；
- 禁止分发现有 Phase18N review forms；
- 建立 v1/v2 版本边界，不覆盖历史负结果。
- 保存不可变 raw review logs、界面版本 hash、审查者 attestation、时间戳和事件审计；派生 majority labels 不能替代原始记录。

### Workstream 1：重建证据测量合同

特征标注组只回答可观察事实，不回答 reviewability：

- 动物框与有效像素面积；
- 左/右/正/后/不确定体侧；
- 可见身体区域及共享区域；
- 可见花纹区域比例；
- 运动模糊、夜间红外、过曝、遮挡、距离；
- 局部匹配覆盖与跨描述符冲突；
- 特征缺失与不确定性。

结果审查组只判断 pair 是否 review-ready、defer 或 non-comparable，看不到特征、PF-ERI、descriptor、rank 和 identity。两组人员与界面必须隔离。

### Workstream 2：先验证测量，再训练模型

用一个小而覆盖困难情形的 measurement sample 检验：

- 每个特征是否有足够变异；
- inter-rater reliability；
- 自动特征与人工特征的一致性；
- 缺失率、失败模式和物种/昼夜分层；
- 单项特征是否真的比简单分辨率或 detector box 更有信息。

如果花纹面积、体侧和身体区域无法可靠测量，应删掉或改写定义，而不是用常量补齐。

人工结构化特征只作为 measurement truth 和 oracle upper bound。任何“节省工作流成本”的正式结果必须来自推理时自动可得的特征，并把 detector、pose、body-part 推理时间、失败率和人工修正时间计入成本。

### Workstream 3：开发、校准、确认三分离

建议按信息角色而非简单比例拆分：

- development：特征工程、模型族比较、误差分析；
- calibration：阈值、概率校准、成本策略；
- confirmation：一次性揭盲，任何修改都进入下一版本。

所有拆分按 identity graph 和 image-pair graph 进行。共享图像、共享无序对和需要评估的新 identity 不得跨越相应边界。

### Workstream 4：双样本确认设计

不要让一个富集样本同时承担机制与部署两种任务：

1. mechanism confirmation sample：平衡质量、相似度、体侧和证据状态，检验 pair features 是否真实工作；
2. deployment queue sample：从真实冻结 top-k 队列概率抽样，估计校准、coverage、预算和时间收益。

总目标可以维持 800–1200 个唯一无序对，但数量应由最小实用效应、组件聚类和审查成本的模拟决定。每对至少双盲审，分歧由第三人裁决。若一对同时来自两个描述符，只审一次，同时记录两个 queue-membership。

两个样本不能无权重合并。主要 proper score、校准、风险和预算估计只能来自代表性 queue sample，或按预先记录的 inclusion probability 加权；mechanism sample 仅用于预注册条件效应和失败机制。

### Workstream 5：应用数学主线

主模型不需要炫技。推荐使用可解释的正则化概率模型作为确认主模型，非线性模型作为预注册次要对照。数学贡献集中于：

- pair-level latent evidence state；
- 非对称错误成本；
- reject option；
- proper scoring rules；
- risk–coverage 与 cost–coverage；
- 聚类/网络依赖不确定性；
- 成本比变化下的策略优势区域。

预注册前必须锁定一个而不是多个可替换的 primary proper score，同时规定最小实用增量或非劣界值、cluster-aware 95% 区间、功效/模拟方案和唯一主要 cost/budget region。AUROC/AUPRC、其他 proper score 和多个预算点进入层级化 secondary，并处理 multiplicity。人工分钟数、无效审查率和错误准入上界为工作流指标。若没有严格 conformal 条件，就不要把“conformal”放入核心贡献。

另增加一个不参与训练的 consequential-validity 实验：新盲审者对已知 ID CzechLynx 做 same/different 判断并记录正确率、置信度和耗时，检验 admitted 与 deferred 是否真的改变判断可靠性或效率。它不用于生成 reviewability 标签，只负责连接构念与实际后果。

### Workstream 6：保护实例与通用工具

在 CzechLynx 确认后，再接入 Mainland Clouded Leopard 或 Marbled Cat：

- 先只验证 adapter 与 pair reviewability；
- 有可靠身份标签后才评价 identity-related utility；
- 报告当地相机设置、体侧分布、夜间比例和专家成本；
- 工具输出每个 route 的理由、缺失特征和版本哈希。

## 预注册成功、失败与停止门槛

| 层级 | 成功要求 | 失败/降级条件 |
| --- | --- | --- |
| 测量 | 核心特征有变异、有可接受可靠性、自动与人工测量一致 | 常量、低可靠性或只能由结果审查者主观生成 |
| 构念 | 真盲双审支持稳定 reviewability，分歧可解释 | 一致性接近偶然或不同 reviewer 定义不同构念 |
| 增量模型 | full 相对 descriptor+independent-quality 超过预注册最小实用增量，且 primary proper score 的聚类区间通过门槛 | 增量为零/负、低于最小实用值，或仅在富集样本中存在 |
| 泛化 | image/component 与 identity-disjoint 均保持方向和实用量级 | 去重、身份隔离或高质量/高相似度后效应消失 |
| 校准 | 独立 calibration 上锁阈值，test 上风险与覆盖率达门槛 | 经验风险反复超限或仅靠事后换阈值通过 |
| 工作流 | 在预设成本/预算区域减少无效专家分钟数或错误准入 | 特征采集成本抵消收益，或 descriptor baseline 更优 |
| 外部实例 | 新物种 adapter 重新校准后复现 reviewability utility | 直接迁移失败且无法由预设 adapter 解释 |

预设异质性报告至少覆盖 descriptor、same/different、rank、identity frequency、camera/site、day/night/IR、left/right flank、reviewer 和 feature-missingness。pooled 正效应不得掩盖预先定义的重要结构性失败。

一旦确认失败，可以构建 PF-ERI v3，但必须使用新版本、公开失败原因和新的未见确认数据。不能在同一确认集上调到成功。

## 三个未来剧本

### 最可能剧本

PF-ERI v2 在 CzechLynx 上显示中等的 reviewability 增量，严格主动对照后的效应不大，但在部分预算/成本区域能减少无效审查。论文成为一篇可信的 focused methods paper：主要贡献是 evidence-admission 构念、验证协议和风险路由，而不是全面算法领先。

### 最危险剧本

真盲、去重、身份隔离和独立质量控制后，PF-ERI 增量消失。此前信号主要来自泄盲、极端抽样、分辨率代理和重复计权。此时应把论文改写为一项负结果驱动的测量研究：展示为什么简单质量代理无法解决 pair admissibility，并发布数据合同和审查协议。

这个剧本仍然可以产生有价值的科研成果，但不能保留“PF-ERI 已验证模型”标题。

### 最乐观剧本

真实 pair-evidence 特征在 identity-disjoint CzechLynx 确认集上稳定改善 proper score，并在真实队列减少专家时间；Mainland Clouded Leopard adapter 又复现相同方向。PF-ERI 将不再只是一个学生项目模型，而可能成为 Wildbook 类平台可集成的 evidence-admission 标准和跨物种审计协议。

## 信心账本

| 判断 | 当前信心 | 理由 |
| --- | ---: | --- |
| “Similarity is not admissibility”是有价值的问题 | 高 | 生态误识别风险、平台人工审查、单图质量不足与项目负结果共同支持 |
| 现有 v1 完整机制已验证 | 很低 | 泄盲、四个常量特征、弱质量对照、富集抽样 |
| 现有 400 行可作为探索性信号 | 中等 | 有强描述符、同 row-set 比较和图像组件隔离，但依赖与偏倚明显 |
| 现有预算收益可部署 | 很低 | 旧代路由、同样本评估、基线污染、无聚类不确定性 |
| v2 重建是当前最优策略 | 充分决策信心 | 修复所有已知致命问题，保留故事并允许失败 |
| v2 一定得到漂亮正结果 | 未知 | 只有新数据能回答，不能由叙事保证 |
| 无校准跨物种通用 | 极低 | 尚无独立外部物种验证 |

## 立即行动顺序

1. 在仓库和主稿中标记 v1 exploratory，暂停 Phase18N。
2. 修复可靠性叙述、400 rows/pairs 叙述和当前 model/route 代际冲突。
3. 写 PF-ERI v2 measurement specification 与不可泄盲界面测试。
4. 构建 canonical unordered-pair universe 和 identity/image component graph。
5. 小规模验证真实特征，拒绝常量和低可靠性特征。
6. 锁定 development/calibration/confirmation 与成本敏感主要终点。
7. 重建 800–1200 个唯一 pair 的双样本确认包，再开始人工审查。
8. CzechLynx 成功后推进 Mainland Clouded Leopard 保护实例；Marbled Cat 作为第二压力场景。
9. 将工具整理为通用 core＋species adapter＋audit manifest，而不是通用免校准模型。

## 最终判断

这个项目目前不是“已经做完、只差投稿”，也不是“故事被推翻”。它正处在一个更关键的位置：研究问题已经成熟，第一版实现暴露出足够多的问题，使第二版可以真正成为科学研究。

对一名高中生研究者而言，最能体现科研实力的不是让所有结果都看起来成功，而是能够保留一个好问题，同时亲手推翻不可靠的证据链，重新设计一个可能失败但值得相信的实验。应用数学实力也不在于工具数量，而在于把证据状态、损失、约束、校准和停止规则定义清楚。

因此，本报告的战略结论是：

> 不放弃 PF-ERI；放弃把 PF-ERI v1 当作确认成功。用 v2 将“Similarity is not admissibility”从一个好故事变成一个可测量、可拒绝、可迁移、可审计的科学对象。

## 信息来源

### 项目内部证据

- `paper/manuscript/main.md`：当前论文主稿。
- `paper/project_report_draft.md`：早期单图 review-readiness 历史稿。
- `docs/project-governance/logs/daily_work_log.md`：项目纵向演化与负结果记录。
- `scripts/streamlit_phase18m_identity_balanced_review_app.py`：Phase18M 审查界面及分组暴露。
- `scripts/build_phase18m_identity_balanced_review_packet.py`：PF-ERI/identity 富集抽样。
- `scripts/build_evidence_feature_extraction.py`：CzechLynx 常量代理与 pair features。
- `scripts/build_known_id_evidence_sufficiency_validation.py`：组件交叉验证与主模型。
- `outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv`：400 行实际验证表。
- `outputs/modeling-validation/pair-level-validation/identity-balanced-analysis/legacy-code18m_reviewer_agreement.csv`：主 400 审查者一致性。
- `outputs/modeling-validation/blind-reliability-packet/`：synthetic 与外部可靠性来源链。
- `scripts/build_risk_calibrated_evidence_admission.py`：经验阈值路由。
- `scripts/build_story_hardening_issue5_review_budget_value.py`：预算比较。
- `paper/review_packets/confirmatory_phase18n/`：当前未标注确认包与审计。

### 外部一手与学术来源

- Cermak et al. (2024), WildlifeDatasets / MegaDescriptor: https://openaccess.thecvf.com/content/WACV2024/papers/Cermak_WildlifeDatasets_An_Open-Source_Toolkit_for_Animal_Re-Identification_WACV_2024_paper.pdf
- Adam et al. (2025), WildlifeReID-10k: https://openaccess.thecvf.com/content/CVPR2025W/FGVC/html/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.html
- DINOv2: https://arxiv.org/abs/2304.07193
- Cermak et al. (2024), WildFusion preprint: https://arxiv.org/abs/2408.12934
- MIEW-ID multi-species Re-ID preprint: https://arxiv.org/abs/2412.05602
- CARE semantic feature alignment, WACV 2026: https://openaccess.thecvf.com/content/WACV2026/html/Wu_Overcoming_Fine-Grained_Visual_Challenges_in_Animal_Re-Identification_via_Semantic_Feature_WACV_2026_paper.html
- Wildbook Matching Process: https://wildbook.docs.wildme.org/data/matching-process.html
- Wildbook Image Analysis Pipeline: https://wildbook.docs.wildme.org/introduction/image-analysis-pipeline.html
- Geifman & El-Yaniv (2019), SelectiveNet: https://proceedings.mlr.press/v97/geifman19a.html
- Angelopoulos et al. (2024), Conformal Risk Control: https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf
- Choo et al. (2020), Best practices for reporting individual identification: https://doi.org/10.1016/j.gecco.2020.e01294
- Johansson et al. (2020), Identification errors and population overestimation: https://pubmed.ncbi.nlm.nih.gov/32286438/
- Henniger et al. (2024), Utility-based biometric sample quality: https://doi.org/10.1186/s13640-024-00644-1
- Schlett et al. (2023), Evaluation of biometric quality assessment: https://arxiv.org/abs/2303.13294
- NIST, When High-Quality Face Images Match Poorly: https://www.nist.gov/publications/when-high-quality-face-images-match-poorly-0
- ISO/IEC 29794-1:2024 biometric sample quality framework: https://www.iso.org/standard/79519.html
- Automated suitability screening for African wild dog photo-ID: https://pmc.ncbi.nlm.nih.gov/articles/PMC10316465/
- Dolphin photo-ID quality and independent confirmation: https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.849813/full
- Salamander fixed-workload similarity-threshold routing: https://pmc.ncbi.nlm.nih.gov/articles/PMC3605430/
- Snow leopard human expertise plus AI: https://doi.org/10.1016/j.gecco.2022.e02350
- Bhatt & Lyngdoh (2023), Clouded leopard camera-trap individual identification: https://www.cambridge.org/core/journals/oryx/article/secrets-of-the-clouded-leopard-abundance-habitat-use-and-carnivore-coexistence-in-tropical-forest-of-manas-national-park-assam-india/EC4FBDF0B91D514D34BC236E0FEF2D69
- Rasphone et al., wild felid density trends and flank workflow in northern Laos: https://link.springer.com/article/10.1007/s10531-021-02172-0
- Hearn et al. (2016), Marbled Cat density and unidentifiable captures: https://doi.org/10.1371/journal.pone.0151046
- IUCN Cat Specialist Group, Marbled Cat: https://www.catsg.org/living-species-marbledcat

## 方法论说明

本报告采用横纵分析法：纵向追踪项目从单图 readiness、检索控制和 metric learning 到 pair-level evidence admission 的演化；横向比较强描述符、身份融合、人机 photo-ID 平台、生物识别质量和选择性预测；两条轴在第一性原理的证据单元、损失函数和可证伪确认设计上交汇。科学审查同时使用构念效度、选择偏倚、测量偏倚、统计结论效度、外部效度与证据比例原则。
