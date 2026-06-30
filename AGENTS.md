你现在继续开发我的音乐生成项目 Sera，进入 V0.8。

当前 Sera 已经完成 V0.7：

1. 前端已有 Workbench tab。
2. 已支持 ScoreDocument、ScoreOperation、undo/redo。
3. 已支持 MusicXML 导入/导出、MIDI/PDF 导出。
4. 已支持 rendererMode：auto / osmd / vexflow / fallback。
5. 已支持 ScorePatch preview / apply / reject / partial apply。
6. 已支持 mock/openai/deepseek/qwen LLM score editing provider。
7. 已支持 Agent explain selected passage。
8. 已支持 score editing evaluation。
9. 后端 pytest、前端 build、前端测试和 smoke evaluation 均通过。

V0.8 的目标是：把 Sera Workbench 从“研究型可编辑工作台”升级为“接近 MuseScore 操作体验的可落地 App 核心版”。

本轮不是继续堆 Agent 功能，而是重点实现真正可用的乐谱编辑体验，包括：

1. 精确 note-level hit mapping。
2. 鼠标点击、拖拽、键盘快捷键输入。
3. MuseScore-like 音符输入模式。
4. 拖拽改音高。
5. 时值、休止符、升降号、连音、力度、 articulation 基础编辑。
6. 多声部和钢琴双手基础编辑。
7. 播放 scrubber 与乐谱定位联动。
8. 局部重排版、自动补齐小节、错误提示。
9. Agent 与手动编辑深度融合：用户选中任何音符/小节/声部后，Agent 可局部修改并生成可回滚 patch。
10. 将这些能力真正落地到 App UI，而不只是后端 API 或实验脚本。

请严格遵守：不要推翻 V0.7 架构，不要删除已有功能，所有新增功能必须 fallback-safe。没有 OSMD、没有 MuseScore CLI、没有 API key 时，App 仍能启动和完成基本编辑。

一、V0.8 开发前检查

请先执行：

1. 阅读 AGENTS.md。
2. 阅读 README.md。
3. 阅读 frontend/src/workbench/*。
4. 阅读 frontend/src/score/*。
5. 阅读 frontend/src/score/renderers/*。
6. 阅读 backend/services/score_document_service.py。
7. 阅读 backend/services/score_patch_service.py。
8. 阅读 backend/services/score_patch_validation_service.py。
9. 阅读 backend/agents/score_editing_agent.py。
10. 运行：

* python -m pytest -q
* npm run build
* npm test
* python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
* python -m evaluation.score_editing.summarize_edit_results

如果 V0.7 基线失败，请先修复，不要继续开发新功能。

二、核心目标：实现 MuseScore-like 编辑闭环

请将 Workbench 升级为以下核心编辑闭环：

Import / Generate Score
↓
Render with OSMD/VexFlow/Fallback
↓
Click Note / Measure / Staff / Voice
↓
Edit by Mouse / Keyboard / Inspector / Palette
↓
Update ScoreDocument
↓
Regenerate MusicXML Preview
↓
Lightweight Validation
↓
Playback Preview
↓
Export MusicXML / MIDI / PDF
↓
Optional Agent Patch
↓
Accept / Reject / Undo / Redo

要求：

1. 所有编辑都必须走 ScoreOperation。
2. 不允许 UI 组件直接随意修改 ScoreDocument。
3. 所有编辑后必须保证 ScoreDocument 可序列化。
4. 所有导出前必须经过 validation。
5. 所有 Agent 修改必须生成 ScorePatch。
6. 所有手动修改和 Agent 修改都要进入 OperationHistory。
7. 用户能通过 undo/redo 回退手动和 Agent 修改。

三、OSMD note-event 精确映射

当前 V0.7 仍未实现精确 OSMD note-level hit mapping。V0.8 必须重点解决。

请完善：

frontend/src/score/renderers/OSMDRenderer.ts
frontend/src/score/renderers/hitTesting.ts
frontend/src/score/renderers/layoutMapping.ts
frontend/src/score/selection.ts

目标：

1. 渲染 ScoreDocument 时，为每个 note event 建立 event_id。
2. ScoreDocument → MusicXML 时，将 event_id 写入可追踪 metadata。
3. OSMD 渲染后，建立 visual element → event_id 映射。
4. 鼠标点击 SVG notehead / stem / rest / measure 区域时，尽量映射回 event_id。
5. 如果 note-level 映射失败，fallback 到 measure-level。
6. 支持点击音符选中。
7. 支持点击休止符选中。
8. 支持点击小节空白区域选中 measure。
9. 支持 shift-click 多选。
10. 支持 drag selection 框选区域内音符。
11. 支持选中结果在 Inspector 中显示。
12. 支持选中结果被 AgentEditPanel 使用。

如果 OSMD 内部结构难以稳定映射，请实现 overlay hit map：

1. 渲染后读取每个 note 的 bounding box。
2. 将 bounding box 与 ScoreDocument event_id 建立索引。
3. 鼠标点击时根据坐标查找最近 note/rest。
4. 保存 mapping debug 信息。
5. 在开发模式下可以显示 hit boxes overlay。

新增调试面板：

1. 当前 renderer。
2. 当前选中 event_id。
3. 当前选中 measure_id。
4. hit-test mode。
5. mapping confidence。
6. fallback reason。

四、MuseScore-like Note Input Mode

请实现真正的音符输入模式。

新增或完善：

frontend/src/workbench/NoteInputMode.tsx
frontend/src/score/noteInput.ts
frontend/src/score/keyboardShortcuts.ts
frontend/src/workbench/KeyboardShortcutsHelp.tsx

支持两种模式：

1. Select Mode
   用户点击选择和编辑已有元素。

2. Note Input Mode
   用户选择时值后，在光标位置输入音符或休止符。

Note Input Mode 要求：

1. 有明显光标。
2. 光标绑定 measure、staff、voice、offset。
3. 用户选择 duration 后点击谱表位置可插入音符。
4. 用户按键盘 A-G 输入音名。
5. 用户按 R 输入休止符。
6. 用户按数字键选择时值：

   * 1 whole
   * 2 half
   * 4 quarter
   * 8 eighth
   * 6 sixteenth
7. 用户按 . 增加附点。
8. 用户按 ↑ / ↓ 半音移动选中音。
9. 用户按 Shift + ↑ / ↓ 八度移动选中音。
10. 用户按 Delete 删除选中元素。
11. 用户按 Ctrl/Cmd + Z 撤销。
12. 用户按 Ctrl/Cmd + Y 重做。
13. 用户按 Space 播放/停止。
14. 用户按 Esc 退出 note input mode。
15. 输入后光标自动前进。
16. 小节时值溢出时阻止输入或提示。
17. 小节不足时可自动补休止符。
18. 支持插入 chord tone：按住 Shift 点击或键盘输入叠加音。
19. 支持选择 right hand / left hand staff。
20. 支持选择 voice 1 / voice 2。

五、拖拽改音高与基础图形编辑

请实现基础拖拽编辑。

新增或完善：

frontend/src/score/dragEditing.ts
frontend/src/workbench/DragEditOverlay.tsx

要求：

1. 用户拖拽选中音符上下移动。
2. 垂直拖拽映射为半音或音阶级进移动。
3. 拖拽时实时显示 preview pitch。
4. 松开鼠标后生成 update_pitch operation。
5. 支持拖拽多个选中音符整体移高/移低。
6. 支持 Alt + drag 复制音符到新位置。
7. 支持横向拖拽调整 offset 的基础版本。
8. 横向拖拽必须量化到当前 meter 的网格。
9. 如果拖拽造成小节时值错误，显示 warning 并可自动 quantize。
10. 拖拽后自动刷新 MusicXML preview。
11. 拖拽后 OperationHistory 可 undo/redo。

如果精确拖拽难度过高，请优先实现稳定的上下拖拽改音高。

六、时值、休止符、连线、升降号编辑

请完善 Palette 与 Inspector。

DurationPalette 支持：

1. whole
2. half
3. quarter
4. eighth
5. sixteenth
6. dotted half
7. dotted quarter
8. dotted eighth
9. triplet eighth 简化版

AccidentalPalette 支持：

1. sharp
2. flat
3. natural
4. double sharp 后续 TODO
5. double flat 后续 TODO

Tie/Slur 基础支持：

1. tie selected notes
2. untie selected notes
3. slur selected passage 简化显示
4. remove slur

Rest editing：

1. 将选中 note 转换为 rest。
2. 将选中 rest 转换为 note。
3. 自动补齐空拍为 rest。
4. 删除 note 后可选择保留 rest 或压缩时值。

要求：

1. 所有操作有 ScoreOperation。
2. 所有操作可 undo/redo。
3. 所有操作后 lightweight validation。
4. 如果 MusicXML 导出不支持某些高级记号，显示 TODO warning。

七、多声部与钢琴双手编辑

请增强 piano score editing。

目标：

1. 支持 right_hand / left_hand staff 清晰切换。
2. 支持 voice 1 / voice 2 切换。
3. 支持将选中音符移动到另一 staff。
4. 支持将旋律复制到右手。
5. 支持从和声自动生成左手伴奏。
6. 支持简单 block chord accompaniment。
7. 支持简单 arpeggiated accompaniment。
8. 支持 bass + chord texture。
9. 支持选中小节后“一键生成左手伴奏”。
10. 支持 Agent 生成左手伴奏 patch。

新增 Agent tool：

1. Generate left-hand accompaniment for selected measures。
2. Simplify left hand。
3. Make left hand more flowing。
4. Preserve melody, rewrite accompaniment。
5. Move selected notes to left hand。
6. Split melody and accompaniment。

八、真实播放 scrubber 与乐谱联动

请升级 MIDI playback。

新增或完善：

frontend/src/workbench/PlaybackScrubber.tsx
frontend/src/score/playbackMap.ts
frontend/src/score/midiPlayback.ts

要求：

1. 播放当前 ScoreDocument。
2. 播放时高亮当前音符。
3. 播放时高亮当前小节。
4. 用户可以拖动 scrubber 跳到指定小节。
5. 用户可以点击小节后从该处播放。
6. 用户可以只播放选区。
7. 支持循环播放选区。
8. 支持 tempo 修改后即时更新。
9. 编辑后自动刷新 playback map。
10. MIDI 渲染失败时 fallback 到 measure-level fake playback。
11. 播放状态显示在 StatusBar。
12. 播放和编辑不能互相阻塞。
13. 播放中编辑时自动停止或提示用户。

九、局部重排版与增量渲染

当前每次编辑可能触发全量重渲染。V0.8 需要改善性能体验。

请实现：

1. ScoreDocument dirty range 标记。
2. 编辑后标记受影响 measure。
3. 轻量 validation 只检查受影响小节。
4. MusicXML export debounce。
5. OSMD render debounce。
6. 大谱子显示 loading。
7. 只改 Inspector 字段时不要全量刷新。
8. 支持 manual refresh。
9. StatusBar 显示 render time。
10. Workbench health 显示 renderer 状态。

如果 OSMD 不能可靠局部渲染，可以仍全量渲染，但必须有 debounce、loading 和性能 warning。

十、Notation Editing Toolbar 升级

请将 Toolbar 升级为更像 MuseScore 的编辑工具栏。

顶部工具栏包含：

1. Select Mode。
2. Note Input Mode。
3. Duration buttons。
4. Rest button。
5. Dot button。
6. Accidental buttons。
7. Tie。
8. Slur。
9. Dynamics。
10. Articulation。
11. Voice selector。
12. Staff selector。
13. Undo。
14. Redo。
15. Play。
16. Stop。
17. Loop selection。
18. Zoom in。
19. Zoom out。
20. Fit width。
21. Renderer selector。
22. Export buttons。

左侧 Palette 包含：

1. Notes。
2. Durations。
3. Rests。
4. Dynamics。
5. Articulations。
6. Lines。
7. Measures。
8. Agent Tools。

右侧 Inspector 包含：

1. Selection details。
2. Note properties。
3. Measure properties。
4. Staff / voice properties。
5. Agent suggestions。
6. Validation warnings。

十一、Agent 与手动编辑深度融合

请升级 Agent editing，使其能理解用户的手动编辑上下文。

AgentEditRequest 增加：

1. current_selection。
2. recent_operations。
3. dirty_measures。
4. validation_warnings。
5. playback_position。
6. selected_notes_summary。
7. user_edit_intent_inferred。
8. preserve_user_edits_since_timestamp。

Agent 行为要求：

1. 不得覆盖用户最近手动编辑，除非用户明确要求。
2. 应优先修改选区。
3. 应解释是否保留了用户编辑。
4. 应支持“基于我刚才的修改继续发展”。
5. 应支持“撤销 AI 上次改动但保留我的手动改动”。
6. 应支持“只修复错误，不改变音乐风格”。
7. Patch preview 要标明哪些内容来自 Agent，哪些内容保留用户编辑。

新增 Agent commands：

1. Continue from my last edit。
2. Fix only validation issues。
3. Preserve my manual edits。
4. Revert last AI edit。
5. Make selected notes more expressive。
6. Add variation based on selected motif。
7. Harmonize selected melody。
8. Generate accompaniment under selected melody。

十二、App 落地体验：项目文件、自动保存、崩溃恢复

请增强 .sera.json 项目文件和 autosave。

要求：

1. 每隔 30 秒自动保存到 localStorage 或工作区缓存。
2. 用户刷新页面后提示恢复未保存项目。
3. Save Project 下载 .sera.json。
4. Open Project 载入 .sera.json。
5. Export MusicXML / MIDI / PDF。
6. Export Edit History。
7. Export Agent Patch History。
8. Export Screenshot-ready project summary。
9. 如果项目文件版本低于 0.8，自动迁移。
10. 如果迁移失败，提示用户并保留原文件。

十三、后端 API 升级

新增或完善：

POST /score/operation
POST /score/batch_operations
POST /score/light_validate
POST /score/full_validate
POST /score/render_preview_musicxml
POST /score/generate_accompaniment
POST /score/export_project_package
POST /score/migrate_project
POST /score/revert_last_agent_patch
POST /score/continue_from_last_edit

要求：

1. 所有接口 Pydantic schema 完整。
2. Swagger 可读。
3. 错误信息对前端友好。
4. 所有写操作有 operation log。
5. 所有 Agent 写操作有 patch history。
6. 所有导出操作有 validation report。
7. mock 模式可用。
8. 没有 MuseScore CLI 时 PDF export graceful fallback。

十四、前端测试升级

V0.8 必须加强前端测试，防止 Workbench 变复杂后崩溃。

新增或完善：

frontend/src/score/**tests**/
noteInput.test.ts
keyboardShortcuts.test.ts
dragEditing.test.ts
playbackMap.test.ts
autosave.test.ts
projectMigration.test.ts
multiVoice.test.ts
accompanimentGeneration.test.ts

frontend/src/workbench/**tests**/
NoteInputMode.test.tsx
ScoreCanvasHitTesting.test.tsx
DragEditOverlay.test.tsx
PlaybackScrubber.test.tsx
NotationToolbar.test.tsx
AgentManualEditIntegration.test.tsx

测试要求：

1. npm test 通过。
2. npm run build 通过。
3. 不依赖真实 OSMD DOM。
4. OSMD hit-test 用 mock mapping 测试。
5. note input cursor 可测试。
6. keyboard shortcuts 可测试。
7. drag pitch update 可测试。
8. undo/redo 可测试。
9. autosave/recovery 可测试。
10. Agent 不覆盖 recent manual edits 可测试。

十五、后端测试升级

新增或完善：

tests/test_score_batch_operations.py
tests/test_light_validate.py
tests/test_full_validate.py
tests/test_project_migration.py
tests/test_generate_accompaniment.py
tests/test_revert_last_agent_patch.py
tests/test_continue_from_last_edit.py
tests/test_agent_preserve_manual_edits.py
tests/test_export_project_package.py

要求：

1. python -m pytest -q 通过。
2. 不依赖真实 API key。
3. 不依赖 GPU。
4. 不依赖 MuseScore CLI。
5. mock fallback 可运行。
6. MusicXML import/export roundtrip 不破坏基本结构。

十六、V0.8 Evaluation：MuseScore-like Editing Benchmark

新增：

evaluation/workbench_editing/
workbench_edit_prompt_sets_v08.json
run_workbench_edit_eval.py
workbench_edit_metrics.py
summarize_workbench_edit_results.py

设计 60 条测试，覆盖：

1. 手动插入音符。
2. 手动删除音符。
3. 手动改音高。
4. 手动改时值。
5. 插入休止符。
6. 多选转调。
7. 拖拽改音高。
8. 左右手 staff 切换。
9. 生成左手伴奏。
10. Agent 保留旋律改伴奏。
11. Agent 保留和声改旋律。
12. Agent 修复 validation warning。
13. Agent 不覆盖用户最近编辑。
14. undo/redo。
15. partial apply。
16. 保存/打开 .sera.json。
17. MusicXML 导出。
18. MIDI 导出。
19. PDF 导出 fallback。
20. playback scrubber。

指标：

1. note_input_success_rate。
2. hit_test_success_rate。
3. drag_edit_success_rate。
4. operation_reversibility_rate。
5. undo_redo_success_rate。
6. musicxml_valid_after_manual_edit_rate。
7. musicxml_valid_after_agent_edit_rate。
8. playback_sync_success_rate。
9. autosave_recovery_success_rate。
10. project_roundtrip_success_rate。
11. agent_preserve_manual_edits_score。
12. average_edit_latency_ms。
13. render_fallback_rate。
14. overall_workbench_usability_proxy_score。

输出：

evaluation/results/workbench_v08_results.csv
evaluation/results/workbench_v08_summary.json
evaluation/results/workbench_v08_table.tex
evaluation/results/workbench_v08_failure_cases.json

十七、论文材料更新

请更新 papers/：

1. system_description.md
   增加 V0.8 MuseScore-like Workbench 架构。

2. interface_design.md
   增加 Note Input Mode、拖拽编辑、播放 scrubber、autosave。

3. human_ai_collaboration.md
   增加“手动编辑上下文感知 Agent”的描述。

4. experiment_plan.md
   增加 Workbench editing benchmark。

5. results_template.md
   增加 V0.8 app usability metrics。

6. limitations_and_ethics.md
   增加：

   * App 编辑能力仍不是完整 MuseScore 替代品。
   * Agent 应尊重用户手动编辑。
   * 自动改谱需要用户确认。
   * 编辑历史可用于追踪人机共同创作过程。
   * 真实 LLM 输出仍可能破坏音乐结构，因此必须 patch preview 与 validation。

新增：

papers/v08_workbench_app_design.md
papers/v08_workbench_evaluation.md

十八、README 更新

请更新 README.md：

1. V0.8 新功能。
2. 如何进入 Workbench。
3. 如何切换 Select Mode / Note Input Mode。
4. 如何用键盘输入音符。
5. 如何拖拽改音高。
6. 如何修改时值、升降号、休止符、力度。
7. 如何编辑左右手与声部。
8. 如何使用 playback scrubber。
9. 如何让 Agent 基于选区改谱。
10. 如何保护用户手动编辑。
11. 如何保存/恢复 .sera.json。
12. 如何导出 MusicXML/MIDI/PDF。
13. 如何运行 V0.8 workbench evaluation。
14. 当前仍未实现的 MuseScore 级高级能力。
15. V0.9 建议。

十九、开发优先级

如果时间有限，请按以下顺序完成。

Priority A：必须完成

1. OSMD note/measure hit mapping 或稳定 overlay hit map。
2. Note Input Mode。
3. 键盘快捷键输入。
4. 拖拽上下改音高。
5. 时值修改。
6. 休止符插入。
7. Staff / voice 基础切换。
8. 播放 scrubber 小节级联动。
9. Agent preserve manual edits。
10. autosave / recovery。
11. Workbench V0.8 tests。
12. README 更新。

Priority B：强烈建议完成

1. 多选拖拽。
2. chord tone 输入。
3. tie/slur 基础支持。
4. 左手伴奏生成。
5. partial apply 更细粒度。
6. playback note-level highlight。
7. project migration。
8. workbench editing benchmark。

Priority C：后续扩展

1. 完整 MuseScore 级排版。
2. 复杂多声部冲突解决。
3. 踏板、歌词、指法。
4. 装饰音。
5. 高级连音线。
6. 实时协同编辑。
7. MIDI 键盘实时输入。
8. 音频渲染与虚拟乐器。

二十、完成标准

V0.8 完成后应达到：

1. Workbench 已不只是预览器，而是可实际编辑乐谱。
2. 用户能进入 Note Input Mode 输入音符和休止符。
3. 用户能通过键盘快捷键改时值、音高、删除、撤销、播放。
4. 用户能点击或框选小节/音符。
5. 用户能拖拽音符上下改音高。
6. 用户能修改 duration、dynamic、accidental、staff、voice。
7. 用户能保存并恢复 .sera.json 项目。
8. 用户能导出 MusicXML、MIDI、PDF。
9. 播放 scrubber 能与小节或音符联动。
10. Agent 能读取用户最近手动编辑上下文。
11. Agent patch 不应默认覆盖用户最近手动编辑。
12. 所有编辑可 undo/redo。
13. 所有编辑后能通过 lightweight validation。
14. 导出前能通过 full validation 或给出明确 warning。
15. npm run build 通过。
16. npm test 通过。
17. python -m pytest -q 通过。
18. V0.8 workbench evaluation 可运行。
19. README 和 papers 已更新。

二十一、完成后总结

完成后请输出：

1. 新增和修改文件列表。
2. 如何启动前端和后端。
3. 如何进入 Workbench。
4. 如何使用 Note Input Mode。
5. 如何使用键盘快捷键。
6. 如何拖拽改音高。
7. 如何编辑左右手和声部。
8. 如何使用 playback scrubber。
9. 如何让 Agent 基于选区改谱。
10. 如何确认 Agent 没有覆盖用户手动编辑。
11. 如何保存和恢复 .sera.json。
12. 如何导出 MusicXML/MIDI/PDF。
13. 如何运行前端测试。
14. 如何运行后端测试。
15. 如何运行 V0.8 workbench evaluation。
16. 当前仍未实现的 MuseScore 级高级功能。
17. V0.9 建议。

请现在开始执行 Sera V0.8。先检查现有代码状态，再制定实施计划，然后逐步修改代码。
