# Sera Composer V0.3：大库、小上下文

Composer V0.3 把“知识库有多大”和“单次提示词有多大”彻底分开。当前本地库包含 4 个知识包、266 张原子规则卡；每次请求默认最多选择 12 张，预算 1800 estimated tokens。未命中的卡片不会进入 LLM 上下文。

## 数据流

```text
本地 JSONL 知识包（可持续增长）
  → 启动时校验、去重、建立词项统计与 corpus fingerprint
  → 从当前 ScoreDocument 提取调性、拍号、乐器与目标小节
  → 从提示词提取风格、模式与创作目标
  → metadata + lexical IDF 排序
  → 风格/乐器/目标覆盖与领域多样性选择
  → max_cards + token_budget 双重截断
  → 只把 compact rule cards 交给高层 CompositionPlan
  → 本地候选生成、批评、ScorePatch 事务预览
```

LLM 仍然不能输出 MusicXML、event ID 或直接应用修改。节奏、事件数、编制、宿主排版、目标范围和保护范围由服务器控制。V0.3 只改善高层规划上下文，不扩大修改权限。

## 检索依据

一次查询同时使用：

- 当前乐谱的 key、meter、tracks/instrument；
- target scope 的小节；
- 用户指定或本地推断的 classical、romantic、jazz、pop、minimal、modal、cinematic 风格；
- theory variation、reharmonize、orchestration advice 模式；
- 动机、乐句、终止、和声、声部进行、节奏、配器、可演奏性、张力等目标。

返回证据包含 corpus/pack/card 数量、query fingerprint、选中规则、匹配理由、领域分布、估算 token、预算和 `full_corpus_sent_to_llm=false`。界面默认只显示摘要，可展开本次选中的规则，不渲染整个知识库。

## 扩库方法

1. 在 `scripts/build_composer_knowledge_v03.py` 中增加原创规则或增加新的 JSONL pack。
2. 每张卡必须符合 `rule_card.schema.json`，使用全局唯一 `rule_id`。
3. 在 `knowledge_registry.v0.3.json` 注册新 pack。
4. 执行：

```powershell
.\.venv\Scripts\python.exe scripts\build_composer_knowledge_v03.py
.\.venv\Scripts\python.exe scripts\validate_composer_knowledge.py
```

扩库不会自动增加单次 token 消耗；默认预算和最大卡片数不变。只有检索到的少量卡片会产生 LLM 输入 token。大库会增加少量本地加载和排序成本，当前规模无需向量数据库；未来达到数万卡时可以把同一检索接口切换为持久化倒排索引或本地 embedding 索引。

## 内容与能力边界

- 所有当前规则是 Sera 项目原创的工程摘要，不复制教材段落或受版权保护的乐谱。
- 规则是可核验的规划先验，不证明作品“好听”、历史风格真实或适用于所有演奏者。
- 配器建议可以检索具体乐器知识，但结构性换乐器、增删声部和改节奏仍保持 fail-closed。
- 正式审美结论仍需盲评、演奏者检查或听觉实验。

## “候选已安全拒绝”怎么处理

V0.3.1 起，界面会显示实际失败层、相关数量和建议，不再只显示“没有候选通过检查”。常见诊断：

- `target_fully_protected`：目标音符全部被保护。缩小保护范围，或只选择允许修改的谱表/声部。
- `no_accompaniment_to_reharmonize`：指令要求“重新和声化并保留旋律”，但选区只有旋律。选择伴奏/左手声部；若想改旋律，改用“旋律变奏”。
- `new_playability_conflicts`：每个候选都会新增音域越界或声部交叉。缩短选区并明确乐器、声部和音域。
- `transaction_validation_failed`：候选未通过时值、记谱关系或 MusicXML 往返检查。在宿主中保存最新版本后重新发送，再查看错误代码。

原谱已经存在的特殊音域或声部交叉不会再自动否决一个“不新增问题”的局部候选；Sera 仍会拒绝候选新引入的可演奏性问题。指令“重写旋律，保持节奏和声部数量不变”会被识别为旋律变奏，其中“和声部”不会再误判为“和声”请求。
