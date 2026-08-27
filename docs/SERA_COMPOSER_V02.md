# Sera Composer V0.2：风格知识与偏好闭环

Sera Composer V0.2 在 V0.1 的安全 ScorePatch 基线上增加“风格检索—乐句分析—宽候选搜索—多维批评—本地偏好反馈”闭环。它仍然不是整谱生成器，也不让 LLM 直接输出 MusicXML 或 event ID。

## 闭环

```text
宿主 MusicXML / ScoreDocument
  → 目标与保护范围
  → LLM 或本地 CompositionPlan
  → 版本化风格知识检索
  → 原谱乐句与动机分析
  → 16 个确定性内部候选
  → 事务、风格、动机、乐句、和声、演奏性批评
  → 兼顾评分与音高差异的 3 个候选
  → 用户 A/B 偏好（本机）
  → 下一次候选排序
  → 最终 ScorePatch 预览、确认与宿主修订
```

## 风格知识库

知识库位于：

- `sera_edit/composer/style_kb/style_knowledge.v0.2.json`
- `sera_edit/composer/style_kb/style_knowledge.schema.json`

当前包含古典、浪漫主义、爵士、流行、极简、调式和电影配乐七个透明基线。每个 profile 包含：

- 中英文别名；
- 和声进行家族；
- 织体、动机、轮廓、张力与力度先验；
- 级进率、半音率、重复率和跳进范围；
- 声部进行偏好；
- 七维批评权重；
- 稳定 rule ID、匹配原因和来源策略。

知识文本是项目原创工程摘要，不复制理论书籍段落，也不包含版权乐谱。未来加入公共领域或授权乐谱统计时，必须保存来源、许可和提取脚本，不能把来源不明作品混入知识库。

验证命令：

```powershell
.\.venv\Scripts\python.exe scripts\validate_style_knowledge.py
```

## 乐句与动机分析

`phrase_analysis.py` 在目标范围内提取：

- 主旋律声部；
- 音程与方向签名；
- 轮廓类型；
- 级进比例；
- 重复比例；
- 分小节音区；
- 可复算 fingerprint。

分析只读取 canonical ScoreDocument，不修改乐谱。

## 候选搜索与批评

界面默认展示 3 个候选，服务器内部默认搜索 16 个不同音高实现。所有候选必须先通过原有 ScorePatch 事务、保护范围和 MusicXML 往返检查。

V0.2 排序维度：

- safety：源指纹、范围、节奏、事件数量和版面保持；
- theory：和弦骨干、终止与声部进行；
- playability：音域、跳进和声部交叉；
- motif：源动机或允许变形的一致性；
- phrase：音区方向与计划张力曲线；
- style：profile 指定的级进、半音、跳进和轮廓范围；
- preference：与用户此前选中候选的聚合特征接近度。

规则分数是工程代理指标，不等于普遍审美质量。硬安全检查失败的候选不会因为偏好分数而被放行。

## 本地偏好

用户可在候选卡片选择“我更喜欢这个版本”，并可标记动机、乐句、和声、风格或可演奏性原因。系统只保存：

- plan / comparison / candidate ID；
- 被选候选的聚合分数；
- 用户选择的原因标签；
- 风格和时间。

系统不保存乐谱音符、MusicXML、用户姓名或账户信息。默认文件位于 `%LOCALAPPDATA%\Sera\composer_feedback.v0.2.jsonl`，可通过 `SERA_COMPOSER_FEEDBACK_FILE` 改写测试路径。

反馈是幂等的：同一比较和同一候选不会重复累计。偏好只能调整软排序权重，不能绕过 schema、protected scope、事务回滚或 MusicXML 验证。

## API

- `POST /sera-edit/composer/preview`：返回 style knowledge、phrase analysis、search summary、候选和 preference profile。
- `POST /sera-edit/composer/feedback`：记录一次显式本地偏好。
- `GET /sera-edit/composer/preference-profile`：读取聚合画像。
- `GET /sera-edit/composer/style-knowledge`：读取知识库版本、fingerprint 和风格列表。

## 仍然保留的边界

- 直接应用仍只重写选区内现有音高；
- 不自动增删音符、改变节奏、换乐器或新增声部；
- 不声称已经学会作曲家个人风格；
- 不把自动评分当成人类盲评；
- 不上传用户乐谱或偏好；
- 不使用偏好结果修改保护范围。

后续 V0.3 应优先建立合法来源的风格 benchmark、宿主试听 A/B 和专业音乐人员盲评，而不是直接训练大型音乐生成模型。
