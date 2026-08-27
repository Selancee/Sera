# SeraEdit Benchmark Card

## 目的

评估自然语言驱动 MusicXML 局部编辑在结构有效性、任务完成率、非目标内容保护率和编辑最小性方面的可靠性。基准比较全谱重写、仅生成 ScorePatch 与 Sera 完整验证流水线三个条件，不评价完整作曲质量。

## 当前版本

Core v1 包含 20 份规则合成短谱和 120 条任务。任务分布为：

| 类别 | 数量 |
| --- | ---: |
| pitch_transposition | 15 |
| rhythm_duration | 15 |
| key_harmony | 15 |
| voice_texture | 15 |
| dynamics_articulation | 10 |
| insertion_deletion | 10 |
| ties_slurs_ornaments | 10 |
| meter_measure_structure | 10 |
| compound_multi_step | 10 |
| conflicting_or_unsupported | 10 |
| 总计 | 120 |

源谱覆盖 4/4、6/8、大调/小调、双谱表、独立第二声部、和弦、连音线、跨小节延音线与装饰音。当前没有把弱起、任意嵌套连音、任意 tuplets 或完整多乐器编制宣称为已覆盖。

### 编号含义与类别标准

任务号是 `类别前缀_序号`；序号只用于识别任务，不是小节号或期望修改数。

| 前缀 | 必须达到 | 必须保持/拒绝标准 |
| --- | --- | --- |
| `pitch_*` | 对指定事件执行精确半音移调 | 保持时值及范围外内容 |
| `rhythm_*` | 合并指定的两个节奏单位 | 保持后续音高、范围外内容和合法小节总时值 |
| `key_*` | 只改变调号 | 不移调现有音符 |
| `voice_*` | 把指定事件移至声部2 | 保持音高、时值、数量和范围外声部 |
| `dynamics_*` | 只设置指定力度或演奏法 | 不给其他音符批量添加记号 |
| `insertion_*` | 原位删除并插入指定音或和弦 | 保持位置/时值与范围外结构 |
| `ties_*` | 建立指定首尾音的 slur 起止关系 | 不误改为 tie，不改音高/时值 |
| `meter_*` | 按题目改变拍号；仅 `meter_001` 执行明示结构删拍 | 其余只改等总时长拍号，不冒充通用 rebar |
| `compound_*` | 同时完成移调和力度两步 | 保持时值与范围外内容 |
| `conflict_*` | 正确识别矛盾/不支持并安全拒绝 | 原谱不变，事件级差异为0 |

例如 `conflict_001` 的三个条件（改为5/8、全部原时值不变、不允许休止符）互相
冲突，所以其正确预期不是一份5/8输出谱，而是拒绝执行并保持原谱不变。
研究复核界面只检查这类任务定义和 Gold 证据，不会在翻页或打开预期谱时调用模型；
因此“安全拒绝”不能解释为模型超时、空响应或API失败。模型表现必须由三条件实验
运行记录另行判定。

## 数据来源与许可证

所有片段由 `scripts/generate_benchmark_batch1.py` 和 `scripts/generate_benchmark_core.py` 确定性生成，按 CC0-1.0 发布。没有改编或摘录版权状态不明的完整现代作品。每份源谱的 metadata 与 `source_scores/manifest.json` 保存来源、许可证和特征摘要。

## 数据结构

- `source_scores/*.score.json`：权威 canonical ScoreDocument；
- `source_scores/*.musicxml`：由同一 ScoreDocument 导出的交换文件；
- `tasks/batch1|batch2|batch3/*.json`：中英文指令、目标/保护范围与约束；
- `gold_patches/*.json`：可事务执行的 ScorePatch；
- `expected_outputs/*`：预期 ScoreDocument、MusicXML 与 diff；
- `splits/batch1.json`、`batch2.json`、`core.json`：增量与累计任务清单；
- `validation/core_report.json`：真实自动验证结果；
- `review/core_human_review.csv`：人工逐条复核表。

## 自动验证

每条成功任务必须通过：任务字段检查、源 MusicXML 解析与 canonical JSON 对照、ScorePatch schema、gold patch 事务执行、目标/保护范围验证、确定性约束、预期输出 fingerprint，以及已签入 MusicXML 的重新导入、canonical diff 和约束复算。拒绝任务必须具有明确冲突或不支持原因，且不得带有伪造 gold patch。

当前 Core 自动结果为 120 valid、0 invalid。该结果只证明数据与执行规则自洽，不是模型性能结果，也不代表人工音乐审阅完成。

## 审阅状态

120 条任务全部为 `pending_human_review`。人工复核应检查指令可读性、gold edit 的音乐常识、保护范围合理性和 diff 的可解释性；未完成前不得写成“专家验证基准”。

## 已知限制与偏差

规则模板可能高估结构明确任务的可执行性。源谱是短小的钢琴式合成片段，不能代表大型管弦乐、复杂排版、任意 MusicXML 厂商扩展或完整创作美学。当前一条事件只保存一个未编号 slur 状态，因此嵌套/并行编号 slur 被明确排除。

拍号任务分为两种明确语义：`meter_001` 是受约束的4/4到3/4结构修改，会删除每个谱表每小节最后一拍；其余任务仅替换等总时长拍号显示值，并明确禁止重新划分小节或重组节拍。基准不会把“只改拍号元数据”冒充通用自动 rebar 能力。

## 不适用场景

本基准不评价音频生成、临床用途、情绪识别、通用作曲能力、最终制谱美观度，也不证明 MuseScore、Sibelius 或其他宿主软件的全部私有元数据兼容性。

## 本地复核记录

Sera Desktop 的“研究复核”界面读取本卡所述 120 条 core 任务，但不会直接
改写任务 JSON 或 `review_status`。决定以带任务指纹的追加式 JSONL 保存在用户
本地数据目录，必要时导出 JSON/CSV 供裁决与发布归档。只有完成裁决并显式更新
正式数据资产后，任务才能从 `pending_human_review` 变为已人工复核；软件测试中
的隔离记录不得计入正式复核数量。完整流程见
`docs/softwarex/HUMAN_REVIEW_PROTOCOL.md`。
