# SeraEdit benchmark human-review protocol

## Completed release snapshot

The 2026-08-27 core review completed 120/120 current primary decisions and the
stratified 30/30 repeat check with zero stale records. The immutable JSON/CSV export,
summary, and SHA-256 manifest are stored in
`experiments/softwarex_human_review_120_v1`. Both passes used the same pseudonymous
reviewer, so the result verifies task instructions, scopes, Gold outputs, and
host-visible notation but is not an independent inter-rater or aesthetic-quality study.

## What this review establishes

The review determines whether each benchmark task has a clear instruction, a correct
target/protected scope, a defensible Gold Patch or refusal label, and a musically usable
expected result. It does not measure language-model accuracy and it does not establish
universal aesthetic quality.

If the 120-task core is described as a reviewed research dataset, complete one primary
review for every task. A second reviewer should independently inspect a stratified 25%
sample (30 tasks), including every category and all tasks marked `needs_revision` or
`exclude` by the primary reviewer. Resolve disagreements explicitly; never silently
replace either record.

## Evidence layers

The interface keeps three evidence classes separate:

1. **Gold contract**: task definition, scope, deterministic constraints, Gold Patch and
   expected MusicXML. This layer does not invoke an LLM.
2. **Product runtime acceptance**: the instruction is replayed through Sera's interactive
   generation, validation, transaction and MusicXML path. The current local acceptance
   snapshot covers 120 tasks in English and Chinese over three repetitions (720 runs).
3. **Human judgment**: a reviewer checks the source, expected score and Sera output in a
   professional notation host and records an append-only decision.

An automatic `120/120` result supports review but does not mark any task human-reviewed.
The local acceptance snapshot is not remote-model accuracy or an aesthetic-quality score.

## Using the local interface

1. For a dedicated source-level review build, set
   `VITE_SERA_ENABLE_RESEARCH_REVIEW=true`, build/start Sera Desktop, and choose
   **Research review** in the Agent header. The ordinary product build hides this tool.
2. Enter a pseudonymous reviewer code and select **Primary** or **Secondary**.
3. Filter by category, review status and **Agent runtime**. Failed and unverified runtime
   cases are ordered first. Read both language versions of the instruction.
4. Inspect target scope, protected scope, deterministic constraints, Gold Patch and the
   event-level before/after diff.
5. Choose **Open source score** and **Open expected score**. Sera prepares read-only
   MusicXML copies and delegates visual inspection to MuseScore, Sibelius or the local
   MusicXML-associated host. Sera does not provide a substitute score editor here.
6. Choose **Open Sera English output** and **Open Sera Chinese output**. These are actual
   product-replay artifacts generated without supplying the Gold Patch to generation.
7. For an expected refusal, confirm that Sera refused before transaction application and
   that the opened result is the unchanged source. Zero score changes are correct here.
8. Rate instruction clarity, scope correctness, Gold correctness and musical validity
   from 1 to 5. Choose `compliant`, `needs_revision`, or `exclude`.
9. A non-compliant decision must include an issue code and a concise note identifying the
   measure/event or explaining the refusal problem. Save and continue.

The append-only store is normally:

```text
%LOCALAPPDATA%\Sera\research_reviews\benchmark_reviews.v1.jsonl
```

Use **Export review records** to create timestamped JSON and UTF-8 CSV snapshots under
the same local review root. Each record includes a task fingerprint, timestamp, reviewer
role, decision, ratings, issue codes and note. API keys and score-event content are not
written to review records.

## 编号代号与合格标准

任务号格式为“类别前缀_序号”。下划线后的 `001`、`002` 等数字只表示该类别中的
任务序号，不代表小节号、难度或应修改的元素数量。复核时以当前题目的指令、目标
范围、保护范围和确定性约束为最终依据。

| 编号范围 | 含义 | 期望 | 合格标准 | 必须保护 |
| --- | --- | --- | --- | --- |
| `pitch_001–015` | 音高移调 | 成功执行 | 指定事件准确升降题目要求的半音数 | 时值、目标外事件和保护谱表不变 |
| `rhythm_001–015` | 节奏时值 | 成功执行 | 按题目合并或改变指定节奏单位 | 后续音高、目标外事件和小节总时值不意外改变 |
| `key_001–015` | 调号 | 成功执行 | 只把全谱调号设为指定调 | 现有音符不随调号自动移调，其他内容不变 |
| `voice_001–015` | 声部/织体 | 成功执行 | 指定事件从声部 1 移到声部 2 | 音高、时值、事件数和目标外声部不变 |
| `dynamics_001–010` | 力度/演奏法 | 成功执行 | 只给指定音符设置 `f` 或 `staccato` | 音高、时值和其他音符记号不变 |
| `insertion_001–010` | 替换/插入/删除 | 成功执行 | 在原位置写入指定 F-sharp 音或 C 大三和弦 | 新事件位置和时值正确，目标外内容不变 |
| `ties_001–010` | 连奏线 | 成功执行 | 指定首尾音具有配对的 `slur start/stop` | 不得误作延音线，其他关系不变 |
| `meter_001–010` | 拍号/小节结构 | 成功执行 | 按题目改变拍号；仅明确要求时重排或删除事件 | 保留事件的音高和时值不变 |
| `compound_001–010` | 复合编辑 | 成功执行 | 两个指定目标音升高 1 半音，最后一个同时设为 `f` | 两步都完成；时值和目标外内容不变 |
| `conflict_001–010` | 冲突/不支持 | **安全拒绝** | 识别冲突或不可验证请求并拒绝，不生成伪修改 | **原谱完全不变，事件级差异为 0** |

`conflict_001` 故意同时要求“改成 5/8、保持每个音符原时值、又不允许休止符”。
当现有总时值不能同时满足这些条件时，正确结果是安全拒绝；预期谱只是拒绝后的
原谱副本。它不要求生成一份 5/8 乐谱。

## Fingerprint and stale-review handling

If a task, source score, Gold Patch or expected output changes, its fingerprint changes.
Earlier decisions remain in the append-only audit file but are marked stale, excluded
from progress/gates and shown as requiring re-review. A decision about an old expected
score therefore cannot silently validate a repaired task.

## Decision rubric

- `compliant`: instruction, scope, Gold/refusal, deterministic diff, Sera replay and host
  inspection agree; the result is musically usable for the stated narrow task.
- `needs_revision`: the task is salvageable, but an instruction, scope, constraint, Gold
  patch, expected output, runtime output or music property must be corrected.
- `exclude`: the task cannot be made unambiguous and reliable without changing its
  research purpose, or it lies outside the supported MusicXML editing contract.

## Separating benchmark repair from aesthetic calibration

The interface evaluates a gate only after 20 primary reviews:

- if at least 20% are non-compliant for any reason, it marks benchmark repair required;
- it marks aesthetic calibration required only when at least 20% are explicitly tagged
  `musically_implausible` or receive a musical-validity rating of 2 or less.

This prevents a wrong selector or Gold Patch from being treated as an aesthetic-model
failure. When the aesthetic gate activates, collect at least 24 blinded A/B musician
preferences over affected categories, calibrate candidate ranking, regenerate affected
cases, and rerun structure, protection, playability and human-review checks.

Preference calibration changes candidate ranking, not the ScorePatch safety boundary.
It is not automatic model training and must not be reported as proof that Sera writes
universally better music.
