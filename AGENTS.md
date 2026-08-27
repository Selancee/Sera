# SeraEdit — ICMC Short Paper 全流程研发总指令

你现在是本项目的首席研究工程师、符号音乐系统开发者、实验设计者和学术论文工程助手。

你的任务不是只提供建议、方案或伪代码，而是直接检查现有仓库、修改代码、创建数据、运行测试、执行实验，并生成一套可以支撑 ICMC Short Paper 投稿的完整研究资产。

项目名称暂定为：

> **SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches**

核心研究问题是：

> 与让大语言模型重新生成整份 MusicXML 相比，使用范围受限、可验证、可预览、可撤销的结构化 ScorePatch，能否提高自然语言乐谱编辑的结构有效性、任务完成率、非目标内容保护率和编辑最小性？

---

# 0. 最重要的执行规则

必须遵守以下规则：

1. 不要只生成计划，必须真正修改仓库并实现功能。
2. 首先检查现有代码，优先复用已有的：

   * ScoreDocument；
   * ScoreOperation；
   * ScorePatch；
   * MusicXML import/export；
   * patch preview/apply/reject；
   * undo/redo；
   * light/full validation；
   * batch operations；
   * LLM provider adapter；
   * renderer adapter；
   * evaluation framework。
3. 不得为了方便而重写整个 Sera 项目。
4. 不得破坏已有生成、编辑、播放、导出和前端功能。
5. 新研究功能应尽量独立放在 `sera_edit`、`benchmark`、`evaluation` 或相似命名空间中。
6. 所有实验结果必须来自真实运行，严禁编造准确率、成功率、延迟、显著性或图表数据。
7. 如果没有 API Key：

   * 仍然完成全部代码；
   * 使用 mock provider 和缓存响应跑通流程；
   * 生成待执行命令；
   * 标明哪些结果是 mock，不能写入正式论文；
   * 不得伪造正式实验结果。
8. API Key 只能从环境变量读取，不能写入代码、日志、测试数据或 Git。
9. 所有新增核心模块必须有测试。
10. 所有实验必须保存原始输出，支持重新计算指标。
11. 所有自动指标必须有明确、可检查的定义。
12. 可以确定性计算的指标，不得交给 LLM 主观判断。
13. 不要擅自声称 Sera 可以代替 MuseScore、理解音乐审美或适用于所有音乐风格。
14. 本论文只聚焦“可靠的 MusicXML 局部编辑”，不扩张为通用音乐生成论文。
15. 每完成一个阶段，更新：

```text
docs/icmc_short_paper/IMPLEMENTATION_LOG.md
```

记录：

* 已完成内容；
* 修改文件；
* 测试结果；
* 未解决问题；
* 下一阶段；
* 是否影响论文实验。

16. 如果仓库使用 Git，进行小而清晰的本地提交，但不要自动 push。
17. 不要反复询问用户已经提供过的信息。遇到非关键歧义时，采用合理默认值并在日志中说明。
18. 遇到阻塞时，不要停止整个任务。先完成所有不依赖该阻塞项的部分。

---

# 1. 最终必须交付的成果

完成后，仓库中必须存在以下成果。

## 1.1 可运行的 SeraEdit 核心系统

实现完整闭环：

```text
MusicXML
   ↓
Canonical ScoreDocument
   ↓
Selected Scope + Natural-Language Instruction
   ↓
LLM / Rule-Based Patch Generator
   ↓
Structured ScorePatch
   ↓
Schema Validation
   ↓
Musical Constraint Validation
   ↓
Protected-Scope Validation
   ↓
Repair / Reject / Apply
   ↓
Updated ScoreDocument
   ↓
MusicXML Export + Diff + Undo
```

## 1.2 MusicXML 编辑基准集

完成正式核心集：

* 约20份基础乐谱；
* 120条编辑任务；
* 每条任务有确定的目标范围；
* 每条任务有保护范围；
* 每条任务有 gold patch 或确定性目标约束；
* 每条任务有难度、类别和可执行性标签。

## 1.3 三组实验条件

必须实现：

* Condition A：Full-Score Rewrite；
* Condition B：ScorePatch Only；
* Condition C：Sera Full Pipeline。

## 1.4 自动评测系统

至少计算：

* MusicXML Validity；
* Task Success；
* Non-target Preservation；
* Edit Minimality；
* Repair Success；
* Refusal Accuracy；
* Patch Parse Rate；
* Constraint Satisfaction；
* Latency；
* Token Usage；
* Estimated API Cost。

## 1.5 真实实验运行框架

必须支持：

* smoke 实验；
* core 实验；
* full 实验；
* 中断恢复；
* 缓存；
* 重试；
* 固定随机种子；
* 并发限制；
* 成本限制；
* 原始响应保存；
* 实验配置快照。

## 1.6 论文素材

自动生成：

* 主结果表；
* 消融实验表；
* 类别细分结果；
* 失败类型统计；
* 置信区间；
* 显著性分析；
* 论文架构图；
* benchmark 构成图；
* 主要结果图；
* 失败案例图；
* 4页 Short Paper 初稿骨架；
* 匿名补充材料说明；
* reproducibility checklist。

## 1.7 演示系统

提供轻量可运行 Demo：

* 导入或选择 MusicXML；
* 选择小节、谱表和声部；
* 输入编辑指令；
* 显示生成的 ScorePatch；
* 显示修改前后差异；
* 显示验证报告；
* 支持 apply、repair、reject、undo；
* 支持离线预缓存演示。

---

# 2. 第一阶段：仓库审计

开始修改代码前，全面检查仓库。

必须检查：

* 前后端技术栈；
* Python/Node版本；
* 当前包管理方式；
* ScoreDocument 定义；
* MusicXML 解析与导出路径；
* 当前 ScorePatch 或 ScoreOperation schema；
* 唯一权威乐谱状态来源；
* 当前验证器；
* LLM provider；
* 当前 API endpoint；
* 当前测试框架；
* 当前实验目录；
* 当前渲染器；
* 当前 undo/redo；
* 当前数据库或项目保存格式。

优先寻找并复用类似接口：

```text
/score/validate_patch
/score/partial_apply_patch
/score/light_validate
/score/full_validate
/score/batch_operations
/score/revert_last_agent_patch
```

如果实际名称不同，以仓库实现为准。

生成：

```text
docs/icmc_short_paper/REPOSITORY_AUDIT.md
```

内容包括：

1. 当前架构；
2. 可直接复用模块；
3. 缺失模块；
4. 潜在技术债；
5. 与 Short Paper 相关的风险；
6. 计划新增文件；
7. 现有功能兼容策略。

审计完成后立即继续开发，不要停下来等待确认。

---

# 3. 推荐目录结构

在不破坏原仓库结构的前提下，建立或映射到以下目录：

```text
sera_edit/
├── domain/
│   ├── score_document.py
│   ├── score_scope.py
│   ├── score_patch.py
│   ├── operations.py
│   └── fingerprints.py
├── generation/
│   ├── patch_generator.py
│   ├── full_rewrite_generator.py
│   ├── prompts.py
│   ├── response_parser.py
│   └── repair_prompt.py
├── validation/
│   ├── schema_validator.py
│   ├── structural_validator.py
│   ├── duration_validator.py
│   ├── protected_scope_validator.py
│   ├── notation_relation_validator.py
│   ├── semantic_precondition_validator.py
│   └── validation_report.py
├── execution/
│   ├── patch_applier.py
│   ├── patch_repair.py
│   ├── diff_engine.py
│   ├── transaction.py
│   └── undo_manager.py
├── providers/
│   ├── base.py
│   ├── mock_provider.py
│   ├── openai_provider.py
│   ├── deepseek_provider.py
│   └── qwen_provider.py
└── api/
    └── routes.py

benchmark/
├── schemas/
├── source_scores/
├── tasks/
├── gold_patches/
├── expected_outputs/
├── fixtures/
├── splits/
├── generation/
├── validation/
└── README.md

evaluation/
├── conditions/
├── metrics/
├── runners/
├── statistics/
├── error_analysis/
├── reporting/
└── configs/

experiments/
├── smoke/
├── core/
├── full/
├── raw_outputs/
├── normalized_outputs/
├── metrics/
├── reports/
└── manifests/

paper/
├── manuscript/
├── figures/
├── tables/
├── supplementary/
├── anonymous_release/
└── submission_checklist/

demo/
├── presets/
├── cached_responses/
└── README.md

scripts/
├── validate_benchmark.py
├── run_smoke_experiment.py
├── run_core_experiment.py
├── run_full_experiment.py
├── recompute_metrics.py
├── generate_paper_assets.py
├── export_anonymous_package.py
└── verify_reproducibility.py
```

如果项目已有类似目录，优先整合，而不是重复创建。

---

# 4. Canonical ScoreDocument

确认并强化 ScoreDocument 作为唯一权威乐谱数据源。

必须满足：

1. 前端显示、MIDI播放、MusicXML导出和编辑操作均基于同一个 ScoreDocument。
2. 禁止：

   * 页面显示使用一份数据；
   * 播放器使用另一份数据；
   * 导出器再使用第三份数据。
3. 每个可编辑事件必须有稳定 ID，例如：

```text
sera-event-id
```

4. 稳定 ID 应在 MusicXML 导入、内存编辑、导出和重新导入后尽可能保持。
5. ScoreDocument 至少表达：

   * score；
   * part；
   * measure；
   * staff；
   * voice；
   * event；
   * pitch；
   * duration；
   * rest；
   * chord；
   * tie；
   * slur；
   * articulation；
   * dynamic；
   * key signature；
   * time signature；
   * tempo；
   * metadata。
6. 时间位置应使用精确的有理数或 tick，不使用不可控的浮点时间比较。
7. 所有操作前后都应可以计算 canonical fingerprint。

建立：

```text
source_score_fingerprint
pre_patch_fingerprint
post_patch_fingerprint
```

用于检测输入漂移和意外修改。

---

# 5. ScoreScope 设计

创建统一的范围表达。

至少支持：

```json
{
  "measures": [3, 4],
  "parts": ["P1"],
  "staffs": [1],
  "voices": [1],
  "event_ids": [],
  "time_range": null
}
```

必须支持：

* target scope；
* protected scope；
* explicit exclusions；
* whole score；
* part；
* measure range；
* staff；
* voice；
* event IDs。

范围匹配必须是确定性的，并有单元测试。

若一条操作尝试修改 protected scope：

* 默认拒绝；
* 记录 violation；
* 不静默应用；
* 可由显式用户确认后放行，但正式实验中关闭此放行。

---

# 6. ScorePatch Schema

建立严格版本化的 JSON Schema。

推荐结构：

```json
{
  "schema_version": "1.0.0",
  "patch_id": "uuid",
  "source_score_id": "score_001",
  "source_fingerprint": "sha256...",
  "instruction": "Transpose measures 3–4 of the upper staff up by a major second.",
  "target_scope": {
    "measures": [3, 4],
    "parts": ["P1"],
    "staffs": [1],
    "voices": [1],
    "event_ids": []
  },
  "protected_scope": {
    "measures": [],
    "parts": [],
    "staffs": [2],
    "voices": [],
    "event_ids": []
  },
  "preconditions": [],
  "operations": [],
  "expected_effects": [],
  "provenance": {
    "provider": "mock",
    "model": "mock",
    "temperature": 0,
    "seed": 42
  }
}
```

每个 operation 至少包括：

```json
{
  "operation_id": "op_001",
  "type": "transpose",
  "selector": {},
  "arguments": {},
  "preconditions": [],
  "expected_change_count": 8
}
```

第一版必须支持以下操作：

1. `transpose`
2. `set_pitch`
3. `set_duration`
4. `insert_note`
5. `insert_rest`
6. `delete_event`
7. `set_dynamic`
8. `set_articulation`
9. `set_tie`
10. `set_slur`
11. `change_key_signature`
12. `change_time_signature`
13. `move_to_voice`
14. `duplicate_motif`
15. `replace_chord`
16. `batch`

对无法可靠支持的复杂操作：

* 不要伪装支持；
* 明确标记 unsupported；
* 让系统拒绝并给出解释。

必须创建：

```text
benchmark/schemas/score_patch.schema.json
```

并为每类 operation 建立正例和反例测试。

---

# 7. Patch 事务与执行机制

Patch 应以事务方式应用：

```text
validate source fingerprint
→ validate patch schema
→ validate selectors
→ validate preconditions
→ clone score state
→ apply operations
→ run post-validation
→ compare protected scope
→ commit or rollback
```

必须支持：

* dry run；
* preview；
* partial apply；
* repair；
* reject；
* rollback；
* undo；
* redo；
* operation history；
* human-readable explanation。

任何一步失败时：

* 不得留下部分损坏状态；
* 默认回滚；
* 保存失败原因；
* 保存验证报告。

---

# 8. 验证系统

建立分层验证器。

## 8.1 Schema Validation

检查：

* JSON 是否可解析；
* schema version；
* 必填字段；
* operation 类型；
* 参数类型；
* selector 合法性；
* 未知字段策略。

## 8.2 Structural Validation

检查：

* part/staff/voice 是否存在；
* measure 是否存在；
* event ID 是否存在；
* 插入位置是否合法；
* 删除后是否留下悬挂引用；
* MusicXML 是否可重新导出并重新解析。

## 8.3 Measure Duration Validation

检查每个 measure、staff、voice 的：

* expected duration；
* actual duration；
* pickup measure；
* anacrusis；
* tuplets；
* grace notes；
* multi-voice timing。

不能简单用浮点相等判断。

## 8.4 Protected Scope Validation

比较操作前后：

* 未指定小节；
* 未指定声部；
* 未指定谱表；
* 未指定音符；
* 未指定力度；
* 未指定记谱关系。

输出：

```text
unexpected_changed_elements
protected_element_count
preservation_rate
violation_details
```

## 8.5 Notation Relation Validation

检查：

* tie start/stop；
* slur start/stop；
* beams；
* tuplets；
* chord membership；
* grace-note relations；
* voice continuity。

## 8.6 Semantic Preconditions

例如：

* “升高大二度”应存在可移调音符；
* “保留节奏”意味着 duration 不得变化；
* “只修改右手”意味着左手必须受保护；
* “保持全部时值，同时改为5/8拍”可能存在冲突。

## 8.7 Validation Report

统一输出：

```json
{
  "status": "valid|warning|invalid|unsupported",
  "errors": [],
  "warnings": [],
  "checks": {},
  "repairable": true,
  "suggested_repairs": []
}
```

---

# 9. 自动 Repair

建立有限、透明、可追踪的 repair 机制。

Repair 分两类：

## 9.1 Deterministic Repair

例如：

* JSON 包裹错误；
* 枚举大小写；
* 缺少默认 schema version；
* 字符串数值转整数；
* 明确可推断的 selector 格式。

## 9.2 LLM Repair

仅在 deterministic repair 失败后启用。

输入必须包括：

* 原始指令；
* 原始 patch；
* schema error；
* structural error；
* 允许修改的范围；
* protected scope；
* 严格输出 schema。

最多修复次数配置化，默认：

```text
max_repair_attempts = 2
```

保存：

* 原始输出；
* 每次修复输出；
* 错误变化；
* 最终状态。

不得无限修复。

---

# 10. 三个实验条件

## Condition A：Full-Score Rewrite

输入：

* 原始完整 MusicXML；
* 自然语言指令；
* 简单系统提示。

输出：

* 修改后的完整 MusicXML。

不得在该条件中偷偷使用 Sera 的 patch 验证优势。

允许进行：

* 基本 XML 提取；
* 输出编码清理。

不允许：

* 根据 gold patch 修复；
* 使用 protected scope 回滚；
* 将失败输出替换为正确答案。

## Condition B：ScorePatch Only

输入：

* ScoreDocument 的必要上下文；
* target scope；
* 指令；
* patch schema。

输出结构化 patch。

允许：

* schema parse；
* 基础 patch apply。

不允许：

* protected-scope validation；
* post-apply musical validation；
* LLM repair；
* deterministic semantic repair；
* 自动拒绝冲突操作。

## Condition C：Sera Full Pipeline

启用：

* structured patch；
* schema validation；
* target scope；
* protected scope；
* source fingerprint；
* structural validation；
* musical constraint validation；
* repair；
* reject；
* transaction；
* undo；
* final MusicXML round-trip validation。

三组条件必须使用：

* 同一原始乐谱；
* 同一编辑指令；
* 同一模型；
* 尽可能相同的温度和 seed；
* 相同运行次数；
* 相同超时和重试规则。

---

# 11. LLM Provider 抽象

统一接口：

```python
class LLMProvider:
    def generate(
        self,
        messages,
        response_schema=None,
        temperature=0.0,
        seed=None,
        max_tokens=None,
        metadata=None
    ) -> ProviderResponse:
        ...
```

ProviderResponse 至少包含：

```text
raw_text
parsed_output
provider
model
latency_ms
input_tokens
output_tokens
estimated_cost
request_id
finish_reason
error
```

优先兼容：

* mock；
* OpenAI；
* DeepSeek；
* Qwen。

模型名称、价格和上下文限制不得硬编码到核心逻辑中，应通过配置文件管理。

创建：

```text
evaluation/configs/providers.example.yaml
```

实验中记录实际模型版本和运行日期。

---

# 12. Benchmark 设计

建立120条正式核心任务。

建议分布：

| 类别                         |  数量 |
| -------------------------- | --: |
| pitch_transposition        |  15 |
| rhythm_duration            |  15 |
| key_harmony                |  15 |
| voice_texture              |  15 |
| dynamics_articulation      |  10 |
| insertion_deletion         |  10 |
| ties_slurs_ornaments       |  10 |
| meter_measure_structure    |  10 |
| compound_multi_step        |  10 |
| conflicting_or_unsupported |  10 |
| 总计                         | 120 |

基础乐谱约20份，每份约6条任务。

乐谱类型至少覆盖：

* 单旋律；
* 钢琴双谱表；
* 双声部；
* 三至四声部；
* 大调；
* 小调；
* 2/4；
* 3/4；
* 4/4；
* 6/8；
* 弱起；
* 延音线；
* 连音线；
* 力度；
* 演奏法；
* 和弦；
* 休止符；
* 装饰音或不规则节奏样例。

优先使用：

* 自建短片段；
* 明确属于公共领域的素材；
* Sera 生成并由规则验证的合成片段。

不得直接把版权状态不明的完整现代作品加入公开数据集。

---

# 13. Benchmark Task Schema

每条任务保存为独立 JSON/YAML。

推荐结构：

```json
{
  "task_id": "pitch_001",
  "score_id": "score_001",
  "category": "pitch_transposition",
  "difficulty": "easy",
  "instruction_en": "Transpose measures 3–4 of staff 1 up by a major second while preserving rhythm.",
  "instruction_zh": "将第3至4小节第一谱表升高大二度，并保持节奏不变。",
  "target_scope": {},
  "protected_scope": {},
  "gold_patch_path": "gold_patches/pitch_001.json",
  "expected_constraints": [
    {
      "type": "pitch_delta",
      "value": 2
    },
    {
      "type": "preserve_duration"
    }
  ],
  "expected_status": "success",
  "unsupported_reason": null,
  "tags": [],
  "created_by": "rule_template",
  "review_status": "verified"
}
```

冲突任务示例：

```json
{
  "expected_status": "refuse",
  "conflict_type": "meter_duration_conflict"
}
```

每条任务必须通过：

* schema validation；
* source score existence；
* gold patch apply；
* expected output generation；
* deterministic metric verification；
* round-trip MusicXML validation。

---

# 14. Benchmark 生成策略

不要一次盲目写120条。

按以下顺序：

## Batch 1：30条

覆盖主要操作类型，先验证全链路。

## Batch 2：60条

补充中等难度、多声部和保护范围。

## Batch 3：120条

加入复杂操作、复合指令、冲突指令和失败案例。

为减少人工错误，建立模板化任务生成器，但每条正式任务都必须经过：

* 自动验证；
* 人工可读摘要；
* 可视化或事件级 diff；
* review_status 标记。

生成：

```text
benchmark/BENCHMARK_CARD.md
```

内容包括：

* 任务目的；
* 数据来源；
* 数据结构；
* 类别；
* 限制；
* 许可证；
* 潜在偏差；
* 不适用场景。

---

# 15. 自动指标

## 15.1 MusicXML Validity

定义：

```text
validity = valid_roundtrip_outputs / all_outputs
```

判定要求：

1. XML well-formed；
2. MusicXML parser 可读取；
3. 转换到 ScoreDocument 成功；
4. 重新导出成功；
5. 重新解析成功。

## 15.2 Patch Parse Rate

```text
parsed_patches / patch_outputs
```

## 15.3 Task Success

优先使用确定性 constraint evaluator。

例如：

* pitch delta；
* duration equality；
* dynamic value；
* event existence；
* event deletion；
* meter change；
* key signature；
* voice assignment；
* relation integrity。

对不能完全自动判定的和声或音乐语义任务：

* 建立明确的规则代理指标；
* 或标记为 `human_review_required`；
* 不得直接让同一个生成模型自我评分。

## 15.4 Non-target Preservation

定义：

```text
preservation_rate
=
1 - unexpected_changed_protected_elements
    / max(1, protected_element_count)
```

同时报告：

* 任务级完全保护成功率；
* 元素级平均保护率；
* 意外变化总数；
* 意外变化类型。

## 15.5 Edit Minimality

至少提供两种指标：

### Operation Minimality

```text
gold_required_operations / max(actual_operations, gold_required_operations)
```

需要合理处理等价 patch。

### Element Change Precision

```text
necessary_changed_elements
/
all_changed_elements
```

如果 gold 不是唯一答案，使用 expected constraints 与允许变化集合，而不是逐字比较 JSON。

## 15.6 Repair Success

```text
successful_repairs / repair_attempts
```

同时报告 repair 是否引入新错误。

## 15.7 Refusal Accuracy

对 expected_status = refuse 的任务：

* 正确拒绝；
* 错误执行；
* 错误拒绝；
* 模糊警告。

计算：

* refusal precision；
* refusal recall；
* refusal F1；
* unsafe execution rate。

## 15.8 Constraint Satisfaction

```text
satisfied_constraints / all_expected_constraints
```

## 15.9 Latency

报告：

* median；
* mean；
* p90；
* p95。

拆分：

* provider latency；
* parse；
* validation；
* repair；
* apply；
* round-trip。

## 15.10 Cost

保存：

* input tokens；
* output tokens；
* estimated cost；
* cost per successful edit；
* repair added cost。

模型价格来自配置，不得假装永久准确。

---

# 16. 实验矩阵

建立三档配置。

## Smoke

用于开发验证：

```text
30 tasks
× 3 conditions
× 1 provider/model
× 1 run
```

## Core

用于 Short Paper 最低正式实验：

```text
120 tasks
× 3 conditions
× 1 provider/model
× 1 run
```

## Full

用于增强版：

```text
120 tasks
× 3 conditions
× 2 provider/models
× 3 repeated runs
```

重复运行仅在模型存在随机性时使用。温度为0且 provider 支持确定性 seed 时，也应保留至少一次复现检查。

实验配置应为 YAML，例如：

```yaml
experiment_id: core_v1
tasks: benchmark/splits/core.json
conditions:
  - full_rewrite
  - patch_only
  - sera_full
providers:
  - provider: qwen
    model: model-name
repetitions: 1
temperature: 0
seed: 42
max_concurrency: 2
max_retries: 2
budget_limit_usd: 20
cache: true
```

---

# 17. 实验运行器

实现稳健的实验 runner。

必须支持：

* task-level resume；
* 请求缓存；
* 唯一 run ID；
* timeout；
* retry with backoff；
* provider rate limit；
* max concurrency；
* cost budget；
* Ctrl+C 安全停止；
* 原始响应保存；
* error serialization；
* manifest；
* config snapshot；
* environment metadata；
* Git commit hash；
* Python/Node版本；
* dependency lock hash。

每次运行生成：

```text
experiments/<experiment_id>/manifest.json
experiments/<experiment_id>/runs.jsonl
experiments/<experiment_id>/raw_outputs/
experiments/<experiment_id>/normalized_outputs/
experiments/<experiment_id>/metrics.csv
experiments/<experiment_id>/summary.json
experiments/<experiment_id>/errors.csv
```

不得覆盖旧实验。

---

# 18. 统计分析

对三种条件进行配对分析，因为它们作用于同一任务。

至少生成：

* raw counts；
* percentage；
* bootstrap 95% CI；
* task-level paired differences；
* category breakdown。

对二元成功指标，优先使用：

* McNemar test；
* paired bootstrap。

对连续或比例型任务指标，优先使用：

* Wilcoxon signed-rank；
* bootstrap CI；
* Cliff’s delta 或适当的效应量。

必须：

* 报告效应量；
* 报告置信区间；
* 不只报告 p-value；
* 对多重比较进行 Holm 校正；
* 不进行选择性汇报；
* 明确样本量；
* 明确缺失输出处理方式。

生成：

```text
experiments/<id>/statistics.md
experiments/<id>/statistics.json
```

---

# 19. 错误分类体系

建立明确 taxonomy。

至少包括：

```text
E01 malformed_xml
E02 musicxml_parse_failure
E03 malformed_patch_json
E04 patch_schema_failure
E05 invalid_selector
E06 missing_event
E07 duration_mismatch
E08 voice_collision
E09 broken_tie
E10 broken_slur
E11 protected_scope_violation
E12 unintended_pitch_change
E13 unintended_duration_change
E14 unintended_notation_change
E15 incomplete_instruction_execution
E16 over_editing
E17 hallucinated_measure_or_voice
E18 conflicting_instruction_not_refused
E19 unsupported_operation
E20 timeout_or_provider_error
```

每个失败输出：

* 可以有多个 error code；
* 有 primary error；
* 有详细 message；
* 有发生阶段；
* 有是否可修复；
* 有 repair outcome。

生成：

```text
paper/tables/error_taxonomy.csv
paper/figures/error_distribution.*
```

---

# 20. Prompt 设计

为三种条件分别创建版本化 prompt。

## Full Rewrite Prompt

要求：

* 修改给定 MusicXML；
* 只输出 MusicXML；
* 不加入解释；
* 尽量保持未指定内容。

但不要加入 Sera 专属 patch 验证机制。

## Patch Only Prompt

要求：

* 输出符合 schema 的 ScorePatch；
* 使用 event ID 和 scope；
* 不输出完整乐谱；
* 不输出 Markdown code fence。

## Sera Full Prompt

包含：

* instruction；
* selected context；
* allowed operation schema；
* target scope；
* protected scope；
* source fingerprint；
* relevant score summary；
* explicit constraints；
* unsupported/refusal rules。

Prompt 必须版本化，例如：

```text
prompt_version: sera_patch_v1.0
```

实验记录每次使用的 prompt hash。

不要把完整、过大的 MusicXML 全部塞给 patch 模型。建立 compact score context，包含目标区域和必要邻域。

---

# 21. 前端与 Demo

在现有 Workbench 中增加或强化研究演示模式。

页面至少包括：

## 左侧

* score selector；
* task selector；
* target scope；
* instruction。

## 中央

* authoritative score rendering；
* before/after overlay；
* changed event highlight；
* protected region highlight。

## 右侧

* generated patch；
* human-readable operations；
* validation report；
* errors/warnings；
* repair suggestion；
* apply；
* reject；
* undo。

## 底部

* condition selector；
* latency；
* token usage；
* run ID；
* source/post fingerprint。

提供 Demo presets：

1. 升高大二度并保持节奏；
2. 修改力度但保护音符；
3. 左手保持不变；
4. 拍号与总时值冲突；
5. 连音线破坏检测；
6. 复合编辑；
7. 无法支持的模糊指令。

建立离线模式：

* 使用缓存 patch；
* 使用本地 fixture；
* 不依赖 API；
* 一键重置；
* 可连续运行。

---

# 22. 测试要求

使用仓库现有测试框架。

至少覆盖：

## Unit Tests

* ScoreScope matching；
* protected scope；
* patch schema；
* operation parsing；
* transpose；
* duration；
* insert/delete；
* dynamics；
* ties/slurs；
* fingerprint；
* diff；
* rollback；
* repair；
* metrics。

## Integration Tests

* MusicXML → ScoreDocument → Patch → MusicXML；
* invalid patch rollback；
* protected violation rollback；
* undo/redo；
* full rewrite evaluation；
* patch-only evaluation；
* full pipeline evaluation；
* benchmark task validation。

## Regression Tests

为已经发现的重要问题建立回归测试，例如：

* A minor / C major 显示不一致；
* preview 与播放使用不同数据源；
* fallback renderer 与 authoritative score 不一致；
* 无关声部被修改；
* repeated import/export event ID 丢失；
* measure duration 浮点误差。

新增核心模块目标：

* 关键验证器和 patch applier 分支覆盖率至少85%；
* 整体项目覆盖率不得因为新增代码明显下降。

---

# 23. CLI 与一键命令

提供统一命令。

示例：

```bash
python scripts/validate_benchmark.py
python scripts/run_smoke_experiment.py
python scripts/run_core_experiment.py --config evaluation/configs/core.yaml
python scripts/recompute_metrics.py --experiment core_v1
python scripts/generate_paper_assets.py --experiment core_v1
python scripts/verify_reproducibility.py --experiment core_v1
python scripts/export_anonymous_package.py --experiment core_v1
```

如果项目使用 Makefile、Taskfile 或 npm scripts，增加：

```bash
make benchmark-validate
make experiment-smoke
make experiment-core
make metrics
make paper-assets
make anonymous-package
make reproducibility-check
```

每条命令必须：

* 有 `--help`；
* 错误码正确；
* 报错可读；
* 不吞掉异常；
* 支持 Windows 环境。

---

# 24. 自动生成论文表格

从真实实验结果自动生成：

## 主表

```text
Method
XML Validity
Patch Parse Rate
Task Success
Preservation
Minimality
Constraint Satisfaction
Latency
Cost
```

## 消融表

比较：

```text
Full Rewrite
Patch Only
Patch + Schema Validation
Patch + Structural Validation
Patch + Protected Scope
Sera Full
```

如果时间有限，正式论文至少保留：

* Full Rewrite；
* Patch Only；
* Sera Full。

## 分类表

按任务类别报告：

* pitch；
* rhythm；
* harmony；
* voice；
* notation；
* structure；
* compound；
* conflict。

输出格式：

* CSV；
* Markdown；
* LaTeX。

不得手工复制数字到论文而不保留来源。

---

# 25. 自动生成论文图

禁止使用装饰性、无信息价值的图。

至少生成：

1. 系统架构图；
2. benchmark 类别分布图；
3. 三条件主要指标图；
4. preservation 对比图；
5. error taxonomy 图；
6. repair flow 图；
7. 一个真实乐谱编辑前后案例图。

所有图必须：

* 有高分辨率版本；
* 有矢量版本，优先 PDF/SVG；
* 字体可读；
* 黑白打印仍可区分；
* 不依赖固定颜色表达唯一信息；
* caption 草稿；
* 记录生成脚本。

统计图不能伪造结果，必须从实验文件读取。

---

# 26. Short Paper 初稿

创建：

```text
paper/manuscript/seraedit_icmc_short_paper.md
paper/manuscript/seraedit_icmc_short_paper.tex
```

由于下一届 ICMC 模板和页数可能尚未确定：

* 先创建 conference-neutral 紧凑双栏稿；
* 页数目标按4页正文含参考文献准备；
* 将模板适配封装，避免正文与格式强耦合；
* 在 `SUBMISSION_NOTES.md` 中标记待根据新 CFP 更新的字段。

推荐标题：

> **SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches**

备选：

> **Structured Patches for Reliable Language-Guided MusicXML Score Editing**

论文结构：

## Abstract

约120–170词，包括：

* 问题；
* 方法；
* benchmark；
* 三条件；
* 主要真实结果；
* 限制。

在实验完成前，用明确占位符：

```text
[RESULT TO BE INSERTED FROM EXPERIMENT]
```

不得编造数字。

## 1. Introduction

包括：

* 自然语言乐谱编辑的价值；
* 全谱重写风险；
* 局部、受保护、可验证编辑的缺口；
* 三项贡献。

贡献限制为：

1. structured ScorePatch；
2. validation and protected-scope pipeline；
3. benchmark evaluation。

## 2. Method

介绍：

* ScoreDocument；
* Scope；
* ScorePatch；
* validation；
* repair/reject/apply；
* transaction。

## 3. Evaluation

介绍：

* 120 tasks；
* 20 source scores；
* three conditions；
* provider/model；
* metrics；
* statistics。

## 4. Results and Analysis

从自动生成表格引用真实结果。

重点分析：

* validity；
* preservation；
* task success；
* refusal；
* repair；
* failures。

## 5. Limitations and Conclusion

明确限制：

* benchmark 规模有限；
* 主要是短符号乐谱片段；
* 语义复杂任务仍有限；
* 不能代表完整作曲质量；
* 不能代表所有 MusicXML 软件兼容性；
* LLM 模型结果可能随版本变化。

---

# 27. 文献与 Related Work

建立：

```text
paper/manuscript/references.bib
paper/manuscript/RELATED_WORK_NOTES.md
```

文献类别至少覆盖：

* symbolic music representation；
* MusicXML；
* computer-assisted composition；
* music notation systems；
* LLM agents；
* structured generation；
* constrained decoding；
* program repair；
* human-in-the-loop editing；
* MIR evaluation；
* music editing interfaces。

不得伪造文献、DOI、页码或作者。

对于未核实的引用：

```text
verification_status: pending
```

正式稿中只使用已核实文献。

---

# 28. 匿名评审包

创建：

```text
paper/anonymous_release/
```

必须移除：

* 作者姓名；
* 学校；
* 本地路径；
* 用户名；
* API request ID 中的敏感信息；
* GitHub 私有地址；
* commit author 信息；
* 元数据中的个人信息。

包含：

* benchmark 子集或完整匿名集；
* 核心代码；
* 安装说明；
* 一键复现实验；
* 缓存示例；
* figure/table generation；
* system requirements；
* limitations。

生成：

```text
paper/submission_checklist/ANONYMITY_CHECK.md
```

自动扫描：

* 用户名；
* Windows 用户目录；
* 邮箱；
* 学校名；
* 作者名；
* access token；
* API key；
* repository remote。

---

# 29. Reproducibility

创建：

```text
paper/supplementary/REPRODUCIBILITY.md
```

至少说明：

* OS；
* Python/Node版本；
* dependency install；
* provider config；
* benchmark validation；
* smoke run；
* full run；
* metric recomputation；
* figure generation；
* expected runtime；
* expected API cost；
* deterministic components；
* nondeterministic components；
* cache policy。

创建环境锁定文件：

* Python lock；
* Node lock；
* Dockerfile 或可替代环境定义；
* `.env.example`。

不得把真实 key 放入 `.env.example`。

---

# 30. 数据与软件许可证

分别评估：

* 项目代码许可证；
* benchmark 数据许可证；
* 公共领域乐谱来源；
* 合成数据；
* 模型输出使用限制。

生成：

```text
benchmark/LICENSE
benchmark/SOURCE_ATTRIBUTION.md
docs/icmc_short_paper/LICENSING_NOTES.md
```

不要擅自给来源不明的音乐文件添加开放许可证。

---

# 31. 人工核验工具

建立一个轻量审核界面或 CLI，用于音乐专业人员检查任务。

每条任务显示：

* 原始乐谱；
* 指令；
* 目标范围；
* 修改后乐谱；
* before/after diff；
* 自动指标；
* reviewer 选择。

Reviewer 标签：

```text
task_success: yes/no/uncertain
unintended_change: yes/no
notation_valid: yes/no/uncertain
severity: none/minor/major
comment: text
```

即使第一篇不进行正式用户研究，也应支持2–3名音乐专业人员做输出核验。

不要把少量核验描述成大规模用户实验。

---

# 32. 研究边界

本项目当前不处理或暂缓：

* 高质量音频生成；
* 大规模音乐模型训练；
* 脑机接口；
* 完整作曲审美评价；
* 取代 MuseScore；
* 所有 MusicXML 记谱语义；
* 完整管弦乐大总谱；
* 实时多人协作；
* 移动端；
* 云端商业账户系统。

如果现有项目已有这些功能，不删除，但不要让它们干扰论文核心。

---

# 33. 推荐实施顺序

严格按以下阶段执行。

## Phase 1：审计与冻结范围

输出：

* REPOSITORY_AUDIT；
* implementation plan；
* regression baseline；
* 当前测试结果。

## Phase 2：ScorePatch 与验证器

完成：

* schema；
* scope；
* protected scope；
* transaction；
* diff；
* validation；
* rollback；
* tests。

## Phase 3：30条 Benchmark

完成端到端：

```text
task → generation → apply → evaluate → report
```

先确认流程，再扩展。

## Phase 4：三实验条件

完成：

* Full Rewrite；
* Patch Only；
* Sera Full；
* unified runner。

## Phase 5：扩展到120条

确保：

* 类别平衡；
* gold 可执行；
* 冲突任务正确；
* benchmark validation 全通过。

## Phase 6：Smoke 与 Core 实验

先跑 smoke。

确认无系统性错误后再跑 core。

## Phase 7：统计与错误分析

生成：

* tables；
* figures；
* taxonomy；
* confidence intervals；
* paired comparisons。

## Phase 8：Demo 与论文素材

完成：

* research demo；
* paper draft；
* anonymous package；
* reproducibility。

## Phase 9：最终验收

运行全部测试和命令，生成最终报告。

---

# 34. 最终验收标准

只有满足以下条件，才能标记项目完成。

## 代码

* [ ] ScoreDocument 是权威数据源；
* [ ] ScorePatch 有版本化 schema；
* [ ] target/protected scope 可确定性执行；
* [ ] patch 事务支持 rollback；
* [ ] apply/reject/undo 可用；
* [ ] validators 可用；
* [ ] full rewrite baseline 可用；
* [ ] patch-only baseline 可用；
* [ ] full pipeline 可用。

## Benchmark

* [ ] 约20份 source scores；
* [ ] 120条正式任务；
* [ ] 每条任务通过 schema；
* [ ] 每条 gold patch 可应用；
* [ ] 每条 expected constraint 可计算或明确要求人工检查；
* [ ] 10条冲突/拒绝任务；
* [ ] benchmark card；
* [ ] license/source attribution。

## 实验

* [ ] smoke 可完整运行；
* [ ] core 可完整运行；
* [ ] 可恢复中断；
* [ ] 原始响应保存；
* [ ] 配置保存；
* [ ] 指标可重算；
* [ ] 无手工伪造结果；
* [ ] cost 与 latency 有记录。

## 分析

* [ ] 主结果表；
* [ ] 消融表；
* [ ] 分类结果；
* [ ] error taxonomy；
* [ ] 95% CI；
* [ ] 配对统计；
* [ ] 效应量；
* [ ] failure cases。

## 论文

* [ ] 标题与摘要；
* [ ] 4页短论文骨架；
* [ ] 架构图；
* [ ] 结果图；
* [ ] 参考文献库；
* [ ] limitation；
* [ ] anonymous package；
* [ ] reproducibility checklist。

## 演示

* [ ] 可导入乐谱；
* [ ] 可选择范围；
* [ ] 可输入指令；
* [ ] 可预览 patch；
* [ ] 可显示验证；
* [ ] 可 apply/reject/undo；
* [ ] 有离线预设；
* [ ] 不依赖实时网络也能展示核心闭环。

---

# 35. 最终报告

完成全部工作后，创建：

```text
docs/icmc_short_paper/FINAL_COMPLETION_REPORT.md
```

必须包括：

1. 项目概述；
2. 实际完成的功能；
3. 新增和修改文件；
4. Benchmark 统计；
5. 实验运行情况；
6. 真实结果摘要；
7. 测试结果；
8. 当前论文完成度；
9. 仍然存在的限制；
10. 投稿前必须人工处理的事项；
11. 一键运行命令；
12. 是否达到 ICMC Short Paper 最低投稿标准；
13. 是否达到增强投稿标准；
14. 不能完成的内容及准确原因。

最后在终端输出简洁摘要：

```text
SeraEdit ICMC Short Paper package completed.

Benchmark:
- Source scores:
- Tasks:
- Valid tasks:
- Conflict tasks:

Experiments:
- Smoke:
- Core:
- Full:

Tests:
- Passed:
- Failed:
- Coverage:

Paper assets:
- Tables:
- Figures:
- Draft:
- Anonymous package:

Remaining blockers:
```

---

# 36. 质量优先级

当时间或资源不足时，按以下顺序保证质量：

1. 数据正确性；
2. ScorePatch 与 protected scope；
3. 验证与 rollback；
4. 三条件公平实验；
5. 自动指标；
6. 120条 benchmark；
7. 可复现性；
8. 论文表格和图；
9. Demo UI；
10. 额外模型和更多任务。

不要为了做漂亮界面而牺牲实验正确性。

不要为了增加任务数量而加入未经验证的数据。

不要为了得到显著结果而修改指标、删除失败样本或更换实验条件。

---

# 37. 立即开始

现在立即执行以下步骤：

1. 扫描并理解整个仓库；
2. 运行当前测试；
3. 创建 `REPOSITORY_AUDIT.md`；
4. 确认现有 ScoreDocument、ScorePatch、验证器和 provider；
5. 建立本任务的实现日志；
6. 从 Phase 1 开始连续执行；
7. 不要只输出方案；
8. 不要在完成审计后停止；
9. 尽可能完成全部代码、数据、测试、实验框架和论文资产；
10. 最终用 `FINAL_COMPLETION_REPORT.md` 汇报真实完成情况。
