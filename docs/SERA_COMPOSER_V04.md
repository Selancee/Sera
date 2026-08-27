# Sera Composer V0.4：可追溯规划、旋律期待与织体识别

V0.4 保留 V0.3 的“大库、小上下文”边界，同时补上三类缺失能力：研究可追溯的旋律期待规则、符号织体识别和基础作曲写作规则。知识库现有 7 个 pack、358 张规则卡；每次请求仍最多选择 12 张，默认预算仍为 1800 estimated tokens，完整语料不会发送给 LLM。

## 最新任务审计

2026-08-22 对当前 MuseScore 会话 `bridge_20260822_010422_fbdd674e` 的 M1–M4 做了源谱/修订真实回放：

- 界面显示的计划 `classical / melody_accompaniment / I–IV–ii–V / preserve_contour / 20–34–48–68` 与本地古典 profile 的默认值逐项一致；旧版本只显示 provider “ready”，没有保存本次 planner 的 request ID 或 fallback，因此不能把它认定为真实 LLM 输出。
- 原谱选区包含 64 个音符、4 个活动声部；织体启发式识别为 `melody_accompaniment`，置信度 0.8955，主线为 `right_hand:v1`。
- 原谱主线的旋律期待代理分为 0.8800；已应用的修订降至 0.6717，大跳数量从 0 增至 6，跳后反向率降至 0.1667，近距离进行分降至 0.3333。它通过了 MusicXML/事务安全检查，但音乐性方案并不理想。
- 接入 V0.4 后，以同一源谱和“重写当前选区的旋律，保持节奏和声部数量不变，并形成清晰终止”做本地确定性回放，返回 3 个合法候选。第一候选的旋律期待代理分为 0.8950，相对原谱 +0.0150，织体骨架保持；检索只使用 12/358 张卡、1413/1800 estimated tokens。

这些分数是结构代理指标，不是“好听度”或人类审美分数。它们用于发现大跳未解决、音域外扩、弱收束和旋律塌缩；正式质量结论仍需盲评、试听与演奏者复核。

## 旋律期待模型的边界

V0.4 把已有 `melody_expectation_validator_v096` 接入 Composer 候选排序，并明确标识为 `huron_tessitura_expectation_proxy_v1`。它计算：

- pitch proximity；
- tessitura/mean regression；
- post-skip reversal；
- registral return 与 gap fill；
- directional inertia；
- tonal anchoring、closure 和显著不协和解决。

实现特别保留了 von Hippel 与 Huron 的重要限定：大跳后反向可能主要来自有限音域/音区约束，不能把它当成脱离语料与声部的普遍心理定律。ITPRA 也没有被压缩成一个伪精确“审美分”。候选同时报告绝对分、相对原谱变化和来源，期待层只影响软排序，不绕过 ScorePatch 硬验证。

## 织体识别

`sera_symbolic_texture_heuristic_v1` 在当前 `ScoreScope` 内按声部分析：

- 活动声部数；
- 精确攻击点对齐率；
- 成对节奏相似度与独立度；
- 主线 track role；
- 主线/支撑音区分离；
- 每小节密度。

输出 `monophonic`、`homorhythmic_chordal`、`melody_accompaniment`、`contrapuntal` 或 `layered`，同时给出置信度、证据和局限。该分类只适用于当前选区，只建模符号攻击模式，不假装拥有完整的声学音色或持续重叠分析。

规划现在明确区分：

- `source_texture`：服务器从原谱确定性识别；
- `plan.texture`：LLM 或本地 profile 建议的目标织体。

当前宿主安全合同只允许音高改写，因此可以保护和解释织体骨架，但不会伪装已经完成增删声部、改时值或换乐器的结构性重配。

## 可追溯性

每次 Composer 请求在本机 `%LOCALAPPDATA%\Sera\composer_runs.v0.4.jsonl` 追加一个隐私受限 trace，包括：

- brief、target/protected scope 与 source fingerprint；
- `live_llm` / `deterministic_theory`、provider、model、request ID、token、latency 和 fallback reason；
- CompositionPlan、检索 query、selected rule IDs、织体/乐句摘要；
- 候选聚合评分与失败诊断。

trace 不保存 API key、MusicXML、音符/事件内容或候选 patch。界面直接显示“本次高层计划：实时 LLM”或“本次高层计划：本地理论回退”，不再用 provider ready 状态冒充本次调用证据。

## 来源与内容策略

规则卡是 Sera 项目自己的短工程摘要，不复制教材段落或受版权保护的乐谱。研究来源在 registry 的 pack 级元数据中记录：

- David Huron, *Sweet Anticipation*, MIT Press, ISBN 9780262083454: <https://mitpress.mit.edu/9780262582780/sweet-anticipation/>
- Paul von Hippel & David Huron, “Why Do Skips Precede Reversals?”, *Music Perception* 18(1), DOI 10.2307/40285901: <https://online.ucpress.edu/mp/article-abstract/18/1/59/62088/>
- Mathieu Giraud et al., “Towards Modeling Texture in Symbolic Data”, ISMIR 2014: <https://archives.ismir.net/ismir2014/paper/000143.pdf>
- Open Music Theory, “Texture” and undergraduate composition/theory OER, CC BY-SA 4.0: <https://viva.pressbooks.pub/openmusictheory/chapter/texture/>

## 命令

```powershell
.\.venv\Scripts\python.exe scripts\build_composer_knowledge_v04.py
.\.venv\Scripts\python.exe scripts\validate_composer_knowledge.py
.\.venv\Scripts\python.exe scripts\audit_composer_musicxml.py source.musicxml --revision revision.musicxml --measures 1 2 3 4 --brief "重写旋律并形成清晰终止"
```

V0.4 不扩大修改权限。节奏、事件数量、编制、宿主排版、目标/保护范围、指纹、MusicXML 往返和事务回滚仍由服务器控制。
