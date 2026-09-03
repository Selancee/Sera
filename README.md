# Sera

[![Research CI](https://github.com/Selancee/Sera/actions/workflows/research-ci.yml/badge.svg)](https://github.com/Selancee/Sera/actions/workflows/research-ci.yml)

## SoftwareX release track

SeraEdit is the research-software core of Sera: a local-first, structured-patch
pipeline for reliable language-guided MusicXML editing. The notation host remains the
visual authority; SeraEdit binds a proposal to a source fingerprint and explicit
target/protected scopes, validates it transactionally, and returns a separate reviewed
revision or a rejection.

- SoftwareX manuscript and submission assets: `paper/softwarex/`
- Installation and user documentation: `docs/softwarex/`
- Offline verification: `docs/softwarex/REPRODUCIBILITY.md`
- Draft readiness check: `.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile draft`
- Final readiness check: `.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile submission`
- Deterministic source/manuscript archives: `.\.venv\Scripts\python.exe scripts\export_softwarex_package.py`
- Ten-minute offline reviewer demo: `.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py`
- Reviewer evidence map: `docs/softwarex/REVIEWER_GUIDE.md`

The source is prepared under the MIT License; the synthetic benchmark is CC0-1.0.
Mock-fixture experiments verify software plumbing only and must not be reported as
language-model performance. Author metadata, the public tagged release, and the
immutable Zenodo software deposit are complete. Version DOI
`10.5281/zenodo.22128976` is publicly registered and resolves to the archived
SeraEdit 1.0.0 source release.

The accompanying manuscript was submitted to SoftwareX on 28 August 2026 as
`SOFTX-D-26-01135`. Elsevier reported the manuscript as **Under Review** on
3 September 2026; this dated status is informational and does not change the
immutable software release or its DOI.

> Sera 是建立在专业记谱环境之上的智能音乐编辑与协作层。

当前主流程已经从“提示词生成整首乐谱”切换为：在 MuseScore Studio、Sibelius Ultimate 或其他专业记谱软件中打开乐谱并确定选区，由 Sera 读取宿主上下文、接受自然语言编辑要求、审查结构化 `ScorePatch`，通过校验后生成不覆盖原文件的新修订。

- 默认界面直接进入 `Agent Console`，只保留宿主连接、Agent 对话和修改提案审查。
- 默认产品不再提供内置乐谱画布、音符输入、播放时间线、Score Inspector、手动操作历史或记谱属性面板；手动记谱统一在宿主软件中完成。
- `run_app.bat` 默认启动 Electron 本地应用，不打开外部浏览器；原 Web 开发模式保留为 `run_web_app.bat`。
- 当前桌面壳使用 Electron 内嵌渲染运行 Agent Console；它不是系统浏览器标签页，也不是纯原生 Qt 控件界面。
- `VITE_SERA_ENABLE_LEGACY_GENERATION=true` 仅保留给内部兼容和回归维护，不属于默认产品流程。
- 当前已在 MuseScore Studio 4.5.2 实机验证“保存文件 + 本地 MuseScore CLI + QML 选区上下文”的桥接输入闭环；不再依赖该版本未实现的 QML `writeScore()` / `readScore()`。Sibelius ManuScript 尚未开始。
- 完整开发路线图见 [`docs/sera_notation_agent_roadmap.md`](docs/sera_notation_agent_roadmap.md)。
- 架构图见 [`docs/architecture/sera_notation_editing_layer.png`](docs/architecture/sera_notation_editing_layer.png)，源文件为 [`sera_notation_editing_layer.mmd`](docs/architecture/sera_notation_editing_layer.mmd)。

## 当前编辑闭环

1. 在 MuseScore/Sibelius 中打开并保存乐谱，再选中需要修改的小节、谱表或声部。
2. MuseScore 4.5.2 用户在插件中选择当前已保存的乐谱，由本地 CLI 转换并创建会话；若宿主桥接不可用，也可将宿主导出的 MusicXML 导入 Agent Console。
3. 在对话区输入编辑要求，Sera 使用宿主提供的选区作为目标范围。
4. 审查 Agent 提案中的操作摘要、校验结果、变化数量和保护范围；可以应用、拒绝或重新生成。
5. 点击“应用并生成宿主修订”，再回到宿主打开最新 revision；原始乐谱文件不会被覆盖。

严格工作流默认启用。点击“生成受验证修改”后，提案区会显示人类可读的操作、target/protected 范围、指纹、变化数量和意外保护区变化计数；原始 `ScorePatch` JSON 收纳在折叠详情中。只有没有验证错误的 valid/warning 提案可以应用。撤销也会产生新的宿主修订，不会在 Sera 内部模拟手工改谱。

MuseScore v0.3 插件与安装说明见 [`integrations/musescore/README.md`](integrations/musescore/README.md)。发送前必须先保存乐谱；当前回传会在 MuseScore 中打开新乐谱，原位 patch 和单步宿主撤销尚未实现，不应当描述为已验证能力。

Windows 本地应用启动：

```powershell
.\run_app.bat
```

首次启动会准备 Electron 运行时和本地后端。应用窗口会先显示“正在启动 Sera 本地引擎”，持续检查本机后端的 `/health`；健康检查通过后才加载 Agent Console。当前打包版使用 onedir 后端，直接从应用目录加载，不会再把大型 `_MEI*` 运行时解压到 `%TEMP%`。真正超时或后端提前退出时，错误会直接显示在启动窗口内。MuseScore 创建桥接会话后，Sera 窗口会自动置前并读取对应乐谱/选区上下文。只有需要 Vite 热更新时才使用 `.\run_web_app.bat`。

已构建且完成可见冒烟的 unpacked 本地包位于：

```powershell
.\dist_desktop\release\win-unpacked\Sera.exe
```

当前验收覆盖：本地启动、宿主桥接会话读取、自然语言生成 C4→D4 严格提案、保护范围 0 意外变化、生成 revision，以及退出后的后端进程树和端口释放。portable 单文件安装器仍未完成稳定验收，因此优先使用上述 unpacked 目录版。

请使用上述 `release\win-unpacked\Sera.exe` 或根目录 `run_app.bat`。`dist_desktop\Sera.exe` 是兼容性打包冒烟所需的旧启动器，不是当前推荐的桌面入口；不要同时启动两个入口。

重新构建主本地包：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\windows\build_windows_app.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\windows\smoke_test_packaged_app.ps1
```

默认构建只生成已验证的 unpacked 应用；如确实需要单文件 portable，可在 `electron` 目录显式执行 `npm run dist:portable`，该可选目标目前未完成稳定验收。

SeraEdit 研究资产入口：

- 仓库审计：`docs/icmc_short_paper/REPOSITORY_AUDIT.md`
- Benchmark 卡：`benchmark/BENCHMARK_CARD.md`
- 实验说明：`evaluation/SERAEDIT_EXPERIMENTS.md`
- 实施日志：`docs/icmc_short_paper/IMPLEMENTATION_LOG.md`
- Short Paper 源稿：`paper/manuscript/seraedit_icmc_short_paper.md`
- 可复现检查表：`paper/supplementary/REPRODUCIBILITY_CHECKLIST.md`

120 条 Core benchmark 已全部自动验证，但仍全部标记为待人工音乐复核；`core_mock_120_v5` 仅验证实验管线，不能当作正式模型性能。MuseScore 4.5.2 的宿主到 Sera 输入闭环已实机验证；修订回传的真实宿主可见验收及 Sibelius 往返仍待完成。

旧版生成研究文档保留在下文，作为兼容维护与历史记录。

Sera is an agent-assisted prompt-to-score music generation prototype. V0.5 keeps the V0.4/V0.2 runnable path, but fixes the "small model generates monotonous quarter-note MusicXML" problem by moving the model to local musical tasks: melody fragments, motif variation, cadence generation, and rhythm rewrite. The Agent plans structure, the rule-based generator preserves MusicXML legality, and postprocess/metrics check musicality collapse modes.

## Pipeline

User Prompt -> Prompt Understanding Agent -> Structured Music Intent -> Composition Planning Agent -> Measure-level Music Plan JSON -> Symbolic Music Generator -> Draft MusicXML / MIDI / ABC -> Music Rule Validator -> Revision Agent -> Final Score -> App Preview / Playback / Export.

## Project Layout

- `backend/`: FastAPI app, mock/LLM-ready agents, symbolic generator, validators, exporters, experiment logging.
- `frontend/`: React + Vite research workbench.
- `evaluation/`: batch prompt evaluation, metrics, and human evaluation form.
- `training/`: cloud-GPU-friendly symbolic dataset, tokenizer, trainer stub, and model evaluator.
- `papers/`: paper outline, experiment plan, system description, figure plan, and figures.
- `examples/`: seed prompts and compatibility exports.
- `experiments/`: one independent folder per generation run.

## Quick Start

Recommended on Windows:

```powershell
D:\Sera\run_app.bat
```

This one-click launcher builds the local Workbench, starts the source backend on the notation bridge port, and opens the Electron desktop window. It does not open an external browser. Use `D:\Sera\run_web_app.bat` only when Vite hot reload is explicitly needed.

Optional desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\create_desktop_shortcut.ps1
```

Stop Sera processes started by the launcher:

```powershell
D:\Sera\stop_app.bat
```

Advanced manual startup:

```powershell
cd D:\Sera
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
cd D:\Sera\frontend
npm install
npm run dev
```

Open:

- Frontend app: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/docs`

## API

- `POST /generate`: prompt to plan, score, validation, evaluation, and artifacts.
- `POST /revise`: revise an existing run with user feedback.
- `POST /rate`: save local human evaluation ratings for a run.
- `GET /model/status`: inspect the optional trained symbolic model and latest AutoDL run metrics.
- `GET /model/registry`: list local `models/<model_name>` folders selectable by the app.
- `POST /model/select`: switch the active symbolic model for subsequent main-page generation.
- `POST /model/sample`: generate or replay token-level symbolic model samples for the frontend Model Lab.
- `GET /export/{run_id}/{format}`: download `musicxml`, `midi`, `abc`, `pdf`, `plan`, `validation_report`, or `experiment_log`.
- `POST /evaluate`: return saved metrics for one run.
- `GET /experiments`: list recent experiment logs.
- `POST /score/render_preview_svg`: try to render a real SVG preview from ScoreDocument-derived MusicXML.
- `POST /score/render_preview_png`: try to render a real PNG preview from ScoreDocument-derived MusicXML.
- `POST /score/render_preview_pdf`: try to render a real PDF preview from ScoreDocument-derived MusicXML.

## V0.93 Real Score Rendering And Notation Grammar

V0.93 is a corrective release focused on removing fake score preview and fake playback paths. `plan.measures` is now only an Agent Plan artifact. The final score preview must come from a real backend preview artifact, canonical `ScoreDocument`, real MusicXML text, or an explicit unavailable state. `ScoreViewer.jsx` no longer uses `plan.measures` to draw final notation, and `MidiPlayer.jsx` no longer uses `plan.measures` to synthesize final playback.

The rendering priority is:

1. Backend-rendered SVG from real MusicXML.
2. Backend-rendered PNG from real MusicXML.
3. ScoreDocument rendered through the Workbench renderer.
4. Real MusicXML text fallback.
5. Clear unavailable state.

Backend preview rendering is optional and honest. If MuseScore CLI or Verovio is not installed, `/score/render_preview_svg|png|pdf` returns `success=false`, `renderer=unavailable`, and a readable error. The frontend then shows ScoreDocument or MusicXML text rather than drawing fake notation.

V0.93 also adds `backend/notation/`:

- `duration_math.py`: rational duration math with dotted durations.
- `meter_rules.py`: 4/4, 3/4, and 6/8 capacity and grouping rules.
- `notation_normalizer.py`: fills gaps with rests, prevents overflow, and splits overlong notes with ties.
- `notation_validator.py`: checks measure duration, dotted duration, ties, voice, staff, and grouping.

The generation pipeline is now:

```text
generation -> ScoreDocument -> notation normalizer -> notation validator -> MusicXML export -> MIDI export -> preview render report
```

The validation panel exposes notation validity, duration grouping, dotted duration, tie status, and normalizer fix counts. The generated response also includes `preview_render`, `generation_metadata.notation_normalization_report`, `generation_metadata.notation_validation_report`, and `generation_metadata.musicality_validation_report`.

Musicality hardening in V0.93 adds a proxy validator for non-monophonic piano output, left-hand activity, rhythmic variety, quarter-note dominance, cadence presence, and motif presence. Default intermediate piano generation is expected to include right-hand melody, left-hand accompaniment, eighth or dotted movement, and a final cadence.

Run the V0.93 evaluation:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m evaluation.v093_real_score_and_notation.run_v093_eval --max-prompts 3
```

## V0.94 Priority A: Seeded Style Melody And MusicXML Beaming

V0.94 Priority A addresses the repeated-melody and unreadable-beaming failures before any larger symbolic model training. The main fixes are backend automatic seeds, style-aware right-hand melody material, melodic grammar repair, and real MusicXML `<beam>` output.

### Why repeated melody happened

Previous generation paths could reach the musicality engines with an empty `variation_seed`. Empty seeds produced a stable zero offset, and motif generation used a small shared major/minor degree set. This made repeated generations, and even different style prompts, sound too similar.

### Backend auto seed

Every `/generate` call now receives a run-level seed. If the request does not provide one, the backend creates it and stores it in:

- `generation_metadata.generation_profile.run_seed`
- `generation_metadata.generation_profile.variation_seed`
- experiment `metadata.run_seed`
- `ScoreDocument.metadata.run_seed`
- `intent.run_seed`

To reproduce a generation, send either `run_seed` on the request or `musicality_controls.variation_seed`:

```json
{
  "raw_prompt": "anime style bright lyrical piano theme, 8 measures",
  "generator_mode": "rule_based",
  "run_seed": 123456789
}
```

The same explicit seed is reproducible; repeated calls without an explicit seed receive different backend-generated seeds.

### Style-aware melodic engine

`backend/generation/musicality/melodic_style_engine.py` maps style intent to actual pitch material:

- Cyberpunk: minor/modal short cells, repeated ostinato-like fragments, controlled tension.
- Anime: brighter lyrical arch contours with expressive leaps.
- Chinese: pentatonic pitch vocabulary with modal wave motion and open-fifth tendency.
- Romantic: longer arch-shaped lines with neighbor-tone motion.
- Default: safe tonal melodic material.

The RuleBased generator now uses this style profile for right-hand melody before pitch realization. Generation metadata records `melodic_style_profile`, `pitch_vocabulary`, `contour_policy`, `interval_policy`, and `motif_source`.

### Melodic grammar repair

`backend/generation/musicality/melodic_grammar.py` validates and repairs generated melodies. It detects tritone-like leaps, unresolved large leaps, excessive same-direction step runs, and beginner-unfriendly leaps. Chinese generation is snapped back to pentatonic pitch classes after repair. Results are written to `generation_metadata.melodic_grammar_report`.

### MusicXML beaming

`backend/notation/beaming.py` assigns meter-aware beam metadata before export:

- 4/4 and 3/4 beam eighth/sixteenth notes within quarter-beat groups.
- 6/8 beams as 3+3 eighth-note groups.
- Rests, dotted-quarter, quarter, half, and whole notes do not receive beams.
- Single short notes do not get orphan beam tags.

`score_document_to_musicxml()` now writes `<beam number="1">begin|continue|end</beam>` under the correct note. This improves generated notation in ScoreViewer, Workbench export, and downloaded MusicXML.

### Verification

Run the backend V0.94 Priority A tests:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q tests/test_seed_service.py tests/test_backend_auto_variation_seed.py tests/test_melodic_style_engine.py tests/test_melodic_grammar.py tests/test_melodic_grammar_integration.py tests/test_beaming_engine.py tests/test_musicxml_beaming.py tests/test_musicxml_beaming_6_8.py
```

Run the full baseline:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
npm test
```

Remaining limitations: V0.94 Priority A does not yet implement full candidate ranking, recent fingerprint memory, tuplets, advanced engraving exceptions, or a real style-conditioned neural melody model. The next recommended batch is candidate generation plus novelty ranking.

Outputs:

- `evaluation/results/v093_real_score_results.csv`
- `evaluation/results/v093_notation_results.csv`
- `evaluation/results/v093_musicality_results.csv`
- `evaluation/results/v093_layout_results.csv`
- `evaluation/results/v093_summary.json`
- `evaluation/results/v093_table.tex`
- `evaluation/results/v093_failure_cases.json`

Remaining limitations: fallback SVG/ScoreDocument rendering is still not a complete professional engraver, backend real preview depends on optional MuseScore CLI or Verovio, 6/8 notation support is basic, and musicality metrics remain proxies rather than human aesthetic judgment. V0.94 should prioritize stronger engraving integration, better OSMD note mapping, and stricter phrase-level notation grammar before larger model training.

## V0.95 Metadata Synchronization And Melody-Line Diagnostics

V0.95 fixes two correctness issues before broader V1.0 polish: stale generated titles after final key resolution, and melodic diagnostics that could accidentally inspect mixed playback events instead of the right-hand melody line.

Metadata synchronization now runs after prompt/UI control resolution and before final MusicXML export. If the prompt says `C major` but the UI explicitly selects `A minor`, the final intent key, ScoreDocument key, MusicXML key signature, `score_document.title`, `score_document.metadata.title`, and MusicXML `<work-title>` are synchronized. A generated title that still contains the stale prompt key is rewritten or neutralized, for example to `Sera Piano Sketch`. The response includes `generation_metadata.metadata_sync_report` and top-level `key_consistency_report`.

Title and composer are editable in the Workbench Inspector. Edits create normal `ScoreOperation` entries:

```text
change_title
change_composer
```

They support undo/redo, project save, Workbench export, and MusicXML export. `score_document_to_musicxml()` writes `<work-title>` from `score_document.title` and `<creator type="composer">` from `score_document.composer`; empty values export as `Untitled Sera Score` and `Sera`.

The Score tab includes `ScoreMetadataPanel`, `KeyConsistencyPanel`, and `MelodyLineReportPanel`. Use the metadata panel to edit title/composer before opening the Workbench or downloading MusicXML. The key panel shows prompt key, UI key, resolved key, ScoreDocument key, title key, and MusicXML key. The melody panel shows the extracted primary staff/voice, excluded accompaniment lines, cross-measure tritone/large-leap counts, and repairs.

Playback events are now explicitly labeled as `playback_event_stream` with `melody_diagnostic_eligible=false`. Melody diagnostics use `backend/generation/musicality/melody_line_extractor.py`, which prefers `right_hand` voice 1 and excludes `left_hand` accompaniment. Cross-measure melodic grammar checks the transition from the last primary melody note of measure N to the first primary melody note of measure N+1, detects unresolved tritone-like jumps and large leaps, and applies conservative repairs to the next measure opening note when possible.

Run V0.95 evaluation:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m evaluation.v095_metadata_melody_line.run_v095_eval --max-prompts 3
.\.venv\Scripts\python.exe -m evaluation.v095_metadata_melody_line.summarize_v095_results
```

Outputs:

- `evaluation/results/v095_metadata_results.csv`
- `evaluation/results/v095_melody_line_results.csv`
- `evaluation/results/v095_summary.json`
- `evaluation/results/v095_table.tex`
- `evaluation/results/v095_failure_cases.json`

Recommended V0.95 verification:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
npm.cmd test
cd ..
.\.venv\Scripts\python.exe -m evaluation.v095_metadata_melody_line.run_v095_eval --max-prompts 3
```

Remaining limitations: metadata synchronization cannot infer a deeply custom human title unless it contains a recognizable key token, cross-measure repair is intentionally conservative, melody-line extraction is staff/voice based rather than full voice-leading analysis, and playback remains a lightweight preview rather than real audio rendering. The next recommended batch is V1.0 polish: stronger candidate ranking, voice-leading validation, MIDI keyboard input, exact engraving-engine note mapping, and user-confirmed regeneration that preserves manual edits by default.

## V0.96 Candidate Generation, Melody Expectation, And Style Harmony

V0.96 removes the long default prompt from the Generate page. The prompt box now starts empty and only shows placeholder text; placeholder examples are never submitted to the backend. If the prompt is empty but UI controls are selected, `/generate` accepts the request as `control_only_intent` and records `intent_source`, `control_only_intent`, and `source_control_terms` in metadata.

Seed handling now creates a candidate set before the final score is chosen. A run seed deterministically derives 3-8 candidate seeds, defaulting to 4. Each candidate is generated, canonicalized into `ScoreDocument`, validated, scored, and ranked. The response returns the best score only, while `generation_metadata.candidate_generation` records the run seed, selected candidate index, selected score, rejected candidates, and rank metrics.

The new melody expectation layer computes practical Huron/Narmour-inspired proxy metrics:

- Leap reversal: leaps larger than a fourth should usually reverse by step or small third.
- Mean regression: notes far above or below the tessitura should tend back toward center.
- Gap fill: large leaps should be followed by contrary motion that fills part of the gap.
- Tonal anchoring and closure: strong beats and phrase endings should land on stable tones.
- Dissonance handling: unresolved tritones and strong-beat unstable tones are counted.

Style harmony now follows `style -> harmony_profile -> progression -> voicing -> voice_leading_validation`. Jazz profiles include extensions, ii-V-I, tritone substitution, and rootless voicings. Chinese profiles favor pentatonic verticalization, open fifths, quartal shapes, and pedal tones. Classical profiles enforce functional progressions and penalize parallel fifths/octaves. Pop profiles prefer I-V-vi-IV style loops with sus/add9/slash colors. Romantic profiles allow secondary dominants and chromatic cadential approach. Electronic/cyberpunk profiles use modal minor cells, pedal point, ostinato bass, and sus/quartal clusters.

`ScoreDocument` now supports optional `tracks` for future multi-instrument generation:

```json
{
  "track_id": "piano_right_hand_v1",
  "role": "lead_melody",
  "instrument": "piano",
  "part_id": "piano",
  "staff": "right_hand",
  "voice": 1
}
```

Older piano scores without `tracks` remain valid; Sera infers right-hand melody and left-hand bass/accompaniment tracks during normalization. MusicXML and MIDI export remain backward compatible.

Run V0.96 evaluation:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m evaluation.v096_expectation_harmony_orchestration.run_v096_eval --max-prompts 3
.\.venv\Scripts\python.exe -m evaluation.v096_expectation_harmony_orchestration.summarize_v096_results
```

Outputs:

- `evaluation/results/v096_melody_expectation_results.csv`
- `evaluation/results/v096_harmony_style_results.csv`
- `evaluation/results/v096_multitrack_results.csv`
- `evaluation/results/v096_summary.json`
- `evaluation/results/v096_table.tex`
- `evaluation/results/v096_failure_cases.json`

Recommended V0.96 verification:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
npm.cmd test
cd ..
.\.venv\Scripts\python.exe -m evaluation.v096_expectation_harmony_orchestration.run_v096_eval --max-prompts 3
```

Remaining limitations: the expectation and harmony scores are proxy metrics, not human aesthetic judgment; candidate ranking is still rule-based; optional tracks prepare orchestration but do not yet provide a full multi-instrument UI; larger style-conditioned model training remains deferred. The next batch should add user-facing candidate comparison, stronger orchestration planning, and human-rated V0.96 musicality studies.

## V0.96.1 Final Score Musicality Hotfix

V0.96.1 fixes a gap in V0.96: style and expectation modules must change the final `ScoreDocument`, MusicXML, and MIDI events, not only metadata. The right-hand melody now routes through the expectation melody candidate generator/ranker before MusicXML is written. Metadata records `melody_generation_source`, selected melody candidate, candidate count, expectation report, and fallback reason.

Jazz, pop, and classical now have explicit melodic style families instead of falling back to the generic diatonic profile. Jazz targets chord tones, 7ths, extensions, and chromatic approach notes; pop uses short hook cells with repetition; classical uses functional diatonic periodic phrases with leading-tone resolution.

Harmony profile is now the real progression source. `variation_seed` selects among style-appropriate profile progressions instead of replacing jazz or romantic harmony with generic loops. Voicing engine output is used as actual left-hand notes; static triads remain fallback only. The final metadata includes `actual_harmony_style_report`, `voicing_source`, and `actual_voicing_pitches_by_measure`, so the UI can warn when metadata and final notes disagree.

Candidate diversity is measured on final score fingerprints for melody, rhythm, and harmony/voicing. Run V0.96.1 final-score evaluation:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m evaluation.v0961_final_score_style_integration.run_v0961_eval --max-prompts 3
.\.venv\Scripts\python.exe -m evaluation.v0961_final_score_style_integration.summarize_v0961_results
```

Outputs:

- `evaluation/results/v0961_final_score_style_results.csv`
- `evaluation/results/v0961_candidate_diversity_results.csv`
- `evaluation/results/v0961_melody_integration_results.csv`
- `evaluation/results/v0961_harmony_voicing_results.csv`
- `evaluation/results/v0961_summary.json`
- `evaluation/results/v0961_table.tex`
- `evaluation/results/v0961_failure_cases.json`

Remaining limitations: these are still rule-based proxy checks, not a human preference model. Jazz voicings are simplified rootless/extended piano shapes, cyberpunk ostinato is symbolic rather than audio-production aware, and candidate audition UI is intentionally deferred.

## V0.96.2 Phrase-Level Melody Generation

V0.96.2 addresses the remaining mechanical-melody problem in the rule layer. The old expectation melody engine is still available as fallback, but normal rule-based generation now builds a phrase plan before right-hand notes are written:

```text
phrase plan -> motif memory -> phrase contour -> target tones
  -> tension/release -> call-and-response -> cadence preparation
  -> final right-hand ScoreDocument events
```

The new phrase melody path lives under `backend/generation/musicality/`:

- `phrase_melody_engine.py`: creates 4-measure phrases and 8-measure periods.
- `motif_memory.py`: remembers a primary motif and develops it through repeat, sequence, answer, color, and cadential variants.
- `phrase_contour.py`: plans arch, long-line, pop-hook, jazz-guided, pentatonic, and cyberpunk contours.
- `target_tone_planner.py`: makes strong beats and phrase endings hit style-aware target tones.
- `tension_release.py`: scores phrase tension and cadential release.
- `accompaniment_interaction.py`: records how the left hand supports cadence, pedal tension, hook clarity, or inner motion.

`RuleBasedGenerator` now generates `phrase_melody` before the measure loop and `_right_hand_events()` consumes the per-measure phrase MIDI plan. `generation_metadata.melody_generation_source` is `phrase_melody_engine`, `hardcoded_shape_fallback_used` is `false`, and final `ScoreDocument` right-hand pitches match the phrase melody output. The older `_style_shapes` path is fallback only.

Style strategies:

- Jazz uses guide tones, chromatic approach color, and ii-V-I-directed target tones.
- Pop uses a short hook cell, repetition with variation, and singable range.
- Classical uses antecedent/final period behavior and cadence preparation.
- Romantic uses a broader long-line contour and delayed-resolution/neighbor color.
- Chinese keeps pentatonic material and open-space contour.
- Cyberpunk uses short modal cells, ostinato tension, and controlled mutation.

Run V0.96.2 evaluation:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m evaluation.v0962_phrase_level_melody.run_v0962_eval --max-prompts 3
.\.venv\Scripts\python.exe -m evaluation.v0962_phrase_level_melody.summarize_v0962_results
```

Outputs:

- `evaluation/results/v0962_phrase_melody_results.csv`
- `evaluation/results/v0962_ab_comparison_results.csv`
- `evaluation/results/v0962_summary.json`
- `evaluation/results/v0962_table.tex`
- `evaluation/results/v0962_failure_cases.json`

Model training remains deferred. V0.96.2 is a stronger non-neural baseline so later symbolic-model training has a clearer rule-layer target and better failure diagnostics.

## Experiment Outputs

Each generation writes:

```text
experiments/<timestamp_prompt_hash>/
  prompt.txt
  plan.json
  generated.musicxml
  generated.mid
  generated.pdf
  validation_report.json
  revision_history.json
  human_rating.json
  metadata.json
  experiment_log.json
```

The validator checks XML parsing, `music21` parsing when available, plan/measure count match, per-staff/per-voice bar completeness, instrument pitch range, empty measures, MIDI export, and PDF export.

## LLM Provider

Sera runs in mock mode by default. A live OpenAI-compatible provider can be enabled without hardcoding credentials:

```powershell
$env:SERA_LLM_PROVIDER = "openai"
$env:SERA_LLM_MODEL = "gpt-4.1-mini"
$env:SERA_LLM_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY = "<set outside source control>"
```

See `.env.example` for local environment variables.

## V0.5 Diagnostics

```powershell
python -m evaluation.analysis.dataset_diagnostics --input_dir data --output_dir evaluation/results
python -m evaluation.analysis.generated_music_diagnostics --input_dir examples/scores --output_dir evaluation/results
```

Outputs include `dataset_diagnostics.json`, `generated_music_diagnostics.json`, `rhythm_distribution.csv`, and `pitch_interval_distribution.csv`.

## V0.5 Data And Training

Build augmented data without overwriting originals:

```powershell
python -m training.augmentation.build_augmented_dataset --input_dir examples/scores --output_dir data/augmented --fragment
python -m training.tasks.build_multitask_dataset --input_dirs data/fragments data/augmented examples/scores --output data/tokenized_v05/multitask_dataset.jsonl
```

Smoke-check V0.5 training:

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_smoke.yaml --dry-run
```

Full small config:

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_small.yaml --out models/sera_v05_small
```

## V0.5 Hybrid Generation

The frontend now exposes `generator_mode` with `rule_based`, `model_based`, `hybrid_v04`, and `hybrid_v05`. The API can also select it directly:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/generate `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt":"Compose an 8 bar C major melody with varied rhythm.","generator_mode":"hybrid_v05"}'
```

`hybrid_v05` records `model_task_type`, `generated_fragment`, `decoding`, `postprocess_report`, `fallback_reason`, `final_validation_report`, and musicality metrics in the experiment log.

## V0.4 Vs V0.5 Experiment

```powershell
python evaluation/run_v05_musicality_eval.py --max-prompts 3
```

Full run writes `evaluation/results/v05_musicality_results.csv`, `v05_musicality_summary.json`, `v05_ablation_table.tex`, and plots under `evaluation/results/v05_musicality_plots/`.

## Evaluation

```powershell
python evaluation/run_evaluation.py --prompts examples/prompts/seed_prompts.jsonl
```

Outputs:

- `evaluation/evaluation_results.csv`
- `evaluation/evaluation_summary.json`

Metrics: `musicxml_validity_rate`, `midi_export_success_rate`, `pdf_export_success_rate`, `bar_completeness_score`, `pitch_range_validity_rate`, `empty_measure_rate`, `prompt_adherence_rule_score`, `revision_success_rate`, `human_rating_present`, `human_average_score`, `rhythmic_diversity_score`, `quarter_note_dominance_score`, `melodic_interval_variety_score`, `cadence_presence_score`, and `overall_musicality_proxy_score`.

## Training Pipeline

```powershell
python training/build_dataset.py --sources examples/scores
python training/tokenize_musicxml.py
python training/train_symbolic_model.py --dry-run
python training/evaluate_model.py
```

Cloud training on AutoDL:

```bash
bash training/autodl_train.sh
```

By default the AutoDL script trains a compact native PyTorch decoder-only Transformer on Sera generated examples plus the ASAP GitHub MusicXML dataset. It keeps third-party data and checkpoints under `/root/autodl-tmp` instead of committing them.

Budget-capped 50 RMB verification:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\run_autodl_50rmb_training.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -MaxRunHours 20 `
  -MaxExamples 1200 `
  -Epochs 6
```

That script saves the checkpoint in both `/root/autodl-tmp/sera_runs/<run_id>` and `/root/autodl-tmp/sera_models/<run_id>`, writes `sha256_manifest.txt`, and creates `/root/autodl-tmp/sera_models/<run_id>.tar.gz`.

The training scripts are ready for local MusicXML/PDMX/MetaScore-derived folders and future POP909/Lakh MIDI Dataset conversions. They do not download large datasets locally.

## Symbolic Model Lab

The frontend has a `Model` tab for qualitative testing of the trained symbolic model. By default it reads lightweight
AutoDL evidence from `docs/training_runs/<run_id>/samples.json` and `training_metrics.json`.

For live checkpoint inference, copy the AutoDL checkpoint artifacts outside Git into the default local model folder:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\fetch_autodl_model.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -RemoteRunDir /root/autodl-tmp/sera_models/<run_id> `
  -ModelName sera_v05_50rmb

powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\verify_model_artifacts.ps1 `
  -ModelDir D:\Sera\models\sera_v05_50rmb
```

The script downloads `model.pt`, `vocab.json`, audit files, and `sha256_manifest.txt`, verifies hashes when the manifest exists, updates local `.env`, and leaves the large files ignored by Git.

Manual equivalent:

```powershell
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_small"
$env:SERA_GENERATOR_BACKEND = "model"
# Expected files:
# D:\Sera\models\sera_symbolic_small\model.pt
# D:\Sera\models\sera_symbolic_small\vocab.json
```

Then start the backend and frontend. The `Model` tab will switch from `recorded_sample` to `checkpoint` mode when
`model.pt` is found and PyTorch is installed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
D:\Sera\stop_app.bat
D:\Sera\run_app.bat
Invoke-RestMethod http://127.0.0.1:8000/model/status
```

The backend now uses `SERA_GENERATOR_BACKEND=model` by default in the launcher. The main `/generate` route is
model-conditioned: it calls the active checkpoint first, extracts pitch/duration hints from the model tokens, and then
uses Sera's safe MusicXML assembler to produce valid MusicXML, MIDI, and PDF. The experiment log records this as
`generator_mode: model_conditioned` with `metadata.symbolic_model.loaded: true`.

The `Model` tab also exposes the local model registry. Put future checkpoints under `models/<model_name>/model.pt`,
refresh the backend, and select that model from the UI to use it for later main-page generation. UI selection persists
the active model to `.env` while preserving unrelated keys such as `OPENAI_API_KEY`. The same switch is available through
the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/model/registry
Invoke-RestMethod http://127.0.0.1:8000/model/select `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model_name":"sera_symbolic_small","persist":true}'
```

Future larger checkpoints can also be called without code changes by setting environment variables directly:

```powershell
$env:SERA_ACTIVE_SYMBOLIC_MODEL = "sera_symbolic_large"
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_large"
$env:SERA_GENERATOR_BACKEND = "model"
D:\Sera\stop_app.bat
D:\Sera\run_app.bat
```

V0.5 deliberately does not ask the small model to generate complete MusicXML from scratch. The current dataset is too small and token frequencies collapse toward common XML and quarter-note patterns. Local tasks give the model a narrower objective while Sera's rules keep notation valid.

## V0.6 Score Workbench

V0.6 adds an independent Score Workbench beside the existing Generate flow. The workbench edits a canonical `ScoreDocument` JSON model instead of editing raw MusicXML text directly. MusicXML is now an import/export format for the workbench, while all user and Agent edits are represented as `ScoreOperation` objects with undo/redo snapshots.

Run the app as usual and open the `Workbench` tab:

```powershell
D:\Sera\run_app.bat
```

Workbench capabilities now include:

- Import generated or external MusicXML into `ScoreDocument`.
- Click measures and notes in the SVG workbench canvas.
- Edit pitch, duration, dynamic, staff, key, meter, tempo, harmony, section, and cadence labels.
- Insert notes/rests from palettes.
- Undo and redo operation history.
- Ask the mock-safe Score Editing Agent for a local `ScorePatch`.
- Preview, accept, reject, or regenerate patches.
- Export edited scores to MusicXML, MIDI, and PDF.
- Save/open `.sera.json` workbench project files.

Backend workbench APIs are available in Swagger:

```text
POST /score/import_musicxml
POST /score/export_musicxml
POST /score/export_midi
POST /score/export_pdf
POST /score/validate
POST /score/apply_operation
POST /score/undo
POST /score/redo
POST /score/agent_edit
POST /score/preview_patch
POST /score/apply_patch
POST /score/reject_patch
POST /score/save_project
POST /score/load_project
```

Score editing evaluation:

```powershell
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

Outputs are written to `evaluation/results/score_editing_results.csv`, `score_editing_summary.json`, and `score_editing_table.tex`.

## V0.7 Score Workbench

V0.7 keeps the V0.6 canonical `ScoreDocument` and operation model, then adds renderer adapters, stricter patch validation, partial patch application, explain-only Agent analysis, and frontend automated tests.

Workbench renderer modes:

- `auto`: try OpenSheetMusicDisplay first, then fall back to SVG.
- `osmd`: request OpenSheetMusicDisplay explicitly; failures are shown in the status bar and editing falls back to SVG.
- `vexflow`: reserved adapter placeholder; currently falls back to SVG.
- `fallback`: always use the built-in SVG renderer.

Use the renderer selector in the Score Workbench toolbar. Backend-visible capability checks are available at:

```text
GET /score/render_capabilities
GET /score/workbench_health
```

LLM score editing is mock-safe by default:

```powershell
$env:SERA_LLM_PROVIDER = "mock"
```

Live OpenAI-compatible providers can be enabled without changing code:

```powershell
$env:SERA_LLM_PROVIDER = "openai"   # or deepseek, qwen
$env:SERA_LLM_MODEL = "gpt-4.1-mini"
$env:SERA_LLM_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY = "<set outside source control>"
```

If the provider is missing, the key is absent, JSON is invalid, schema validation fails, or repair fails, Sera falls back to the deterministic mock patch planner.

New workbench APIs:

```text
POST /score/validate_patch
POST /score/partial_apply_patch
POST /score/explain_selection
GET /score/render_capabilities
GET /score/workbench_health
```

Patch workflow:

1. Select one or more measures in Workbench.
2. Choose preserve constraints, target difficulty, patch size, staff, and voice in Agent Tools.
3. Click `Preview Agent Patch`.
4. Review diff counts, prompt-alignment scores, validation recommendation, and over-editing risk.
5. Use `Accept all`, `Reject`, `Regenerate patch`, or operation-level partial apply.

Explain selected passage:

1. Select a measure range.
2. Click `Explain` or the `Explain selected passage` Agent tool.
3. Sera returns harmony, melodic, rhythmic, difficulty, and suggested-edit notes without modifying the score.

V0.7 score editing evaluation:

```powershell
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

Outputs are written to `evaluation/results/score_editing_v07_results.csv`, `score_editing_v07_summary.json`, `score_editing_v07_table.tex`, and `score_editing_v07_failure_cases.json`.

Current non-goals remain MuseScore-level engraving and full notation editing: precise drag-to-pitch editing, advanced slurs, pedal marks, lyrics, fingering, complex tuplets, and real-time collaboration are still V0.8+ work.

## Tests

```powershell
python -m pytest
cd frontend
npm run build
npm test
```

Recommended full V0.7 verification:

```powershell
python -m pytest -q
cd frontend
npm run build
npm test
cd ..
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

## V0.8 Score Workbench

V0.8 turns the Workbench into a MuseScore-like editing core while keeping the V0.7 fallback path. The Workbench now supports Select Mode, Note Input Mode, duration and accidental controls, tie/slur actions, staff and voice selection, note-level overlay hit testing, vertical drag pitch editing, fake playback scrubber, autosave recovery, `.sera.json` project migration, left-hand accompaniment generation, and Agent edits that receive recent manual-edit context.

Renderer modes remain fallback-safe:

- `auto`: try OSMD and fall back to SVG.
- `osmd`: force OpenSheetMusicDisplay and report fallback reason on failure.
- `vexflow`: reserved adapter path with safe fallback.
- `fallback`: deterministic SVG renderer and overlay hit map.

Manual editing basics:

- Click notes/rests/measures in Select Mode; Shift-click or marquee-select for larger selections.
- Use Note Input Mode plus `A-G`, `R`, `1/2/4/8/6`, `.`, arrows, `Delete`, `Ctrl+Z`, `Ctrl+Y`, `Space`, `Esc`, and `Ctrl+A`.
- Drag selected notes vertically to change pitch; horizontal movement is quantized in the fallback editor.
- Generate simple left-hand accompaniment from the selected range.

Agent editing now sends `current_selection`, `recent_operations`, `dirty_measures`, validation warnings, playback position, selected-note summary, inferred user edit intent, and a preserve timestamp. Mock and LLM modes can protect recent manual notes through `exclude_event_ids`.

New V0.8 APIs:

- `POST /score/operation`
- `POST /score/batch_operations`
- `POST /score/light_validate`
- `POST /score/full_validate`
- `POST /score/render_preview_musicxml`
- `POST /score/generate_accompaniment`
- `POST /score/migrate_project`
- `POST /score/export_project_package`
- `POST /score/revert_last_agent_patch`
- `POST /score/continue_from_last_edit`

V0.8 verification:

```powershell
python -m pytest -q
cd D:\Sera\frontend
npm.cmd run build
npm.cmd test
cd D:\Sera
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
python -m evaluation.workbench_editing.run_workbench_edit_eval --max-prompts 3
python -m evaluation.workbench_editing.summarize_workbench_edit_results
```

V0.8 benchmark outputs are `evaluation/results/workbench_editing_v08_results.csv`, `workbench_editing_v08_summary.json`, `workbench_editing_v08_table.tex`, and `workbench_editing_v08_failure_cases.json`.

Still out of scope: full MuseScore-grade engraving, advanced tuplets/ornaments/pedal/lyrics/fingering, exact OSMD internal notehead binding in all browsers, real audio-synchronized MIDI playback, full layout reflow, and multi-user collaboration.

## TODO

1. Add OpenSheetMusicDisplay or Verovio for full browser engraving.
2. Add MuseScore CLI detection UX and production PDF rendering.
3. Replace heuristic prompt parsing with a provider registry and stricter schema-constrained LLM calls.
4. Train and evaluate a real V0.5 checkpoint on larger structured-event fragments.
5. Add multi-rater participant/session support for formal human-subject studies.
6. Improve postprocess so it preserves richer two-staff accompaniment after structured-event repair.
7. Improve OSMD note-level hit mapping beyond stable measure-level overlay selection.
8. Add precise drag-to-pitch editing, advanced articulations, slurs, pedal marks, lyrics, and collaboration support.
9. Compare mock, OpenAI, DeepSeek, and Qwen score-editing patches on the V0.7 benchmark.
10. Build V0.8 real-time playback scrubbing and richer MuseScore-like notation editing.

## V0.9 Precise Editing And Musicality Generation

V0.9 adds a MuseScore-like localization layer and a stronger rule-based musicality layer without removing the V0.8 fallback workbench. The app still runs without OSMD, MuseScore CLI, or a real LLM API key.

Workbench editing additions:

- Score Cursor: always-visible insertion cursor with measure, beat, staff, voice, pitch, duration, mode, snap, and validation state.
- Beat Grid: empty space inside a measure maps to the nearest beat, eighth, sixteenth, or triplet snap point.
- Staff Lanes: right hand and left hand regions are explicit; `Tab` and `Shift+Tab` switch staff.
- Enlarged Hit Areas: note/rest hit targets are larger than the rendered notehead; missed note hits fall back to the beat grid.
- LocationBar: always shows Measure, Beat, Staff, Voice, Pitch, Duration, Mode, Snap, Selection, and Validation.
- MusicalityControlPanel: controls rhythmic density, texture, accompaniment style, difficulty, phrase length, cadence strength, dotted rhythm amount, syncopation, left-hand complexity, and dynamic contrast for local Agent tools.

Precise input basics:

```text
Left / Right              Move Score Cursor by current snap
Ctrl+Left / Ctrl+Right    Previous / next measure
Up / Down                 Change cursor pitch, or transpose selected notes
Ctrl+Up / Ctrl+Down       Octave movement
Tab / Shift+Tab           Switch right hand / left hand
V                         Switch voice 1 / voice 2
N                         Toggle Note Input Mode
1 2 4 8 6                 Whole, half, quarter, eighth, sixteenth
A-G                       Insert note at cursor
R                         Insert rest at cursor
.                         Toggle dotted duration
+ / -                     Sharp / flat
Delete / Backspace        Delete selected events
Space                     Play / stop
Ctrl+Z / Ctrl+Y           Undo / redo
```

To enter a dotted note, choose a duration, press `.`, then press `A-G` in Note Input Mode. After insertion, the cursor advances automatically. To solve missed note hits, turn on `show hit boxes` or `show beat grid`; clicks that do not resolve to a note/rest still update the Score Cursor through the Beat Grid.

Generation additions:

- `backend/generation/musicality/` contains rhythm, motif, phrase, harmony, accompaniment, texture, cadence, dynamics, ornament, profile, and postprocessor modules.
- Default piano generation uses right-hand melody plus left-hand accompaniment.
- Rhythm patterns include dotted rhythms, eighth-note motion, simple syncopation, rests, and advanced sixteenth-note patterns.
- Cadence metadata is planned every phrase and at the final ending.
- Generation metadata includes `generation_profile`, `rhythm_patterns`, `motifs`, `harmony_plan`, `texture`, `cadence`, `accompaniment`, `dynamics`, and `postprocess_report`.

Generate Mode now passes musicality controls through `/generate`. Use rhythmic density `high` for more eighth/sixteenth motion, texture `arpeggiated` or `waltz` for flowing left hand, and accompaniment style `arpeggiated_chords`, `bass_chord`, `alberti_bass`, or `waltz_bass` for piano writing.

V0.9 evaluation:

```powershell
python -m evaluation.v09_precision_and_musicality.run_v09_eval --max-prompts 3
python -m evaluation.v09_precision_and_musicality.summarize_v09_results
```

Outputs:

- `evaluation/results/v09_precision_results.csv`
- `evaluation/results/v09_musicality_results.csv`
- `evaluation/results/v09_summary.json`
- `evaluation/results/v09_table.tex`
- `evaluation/results/v09_failure_cases.json`

Recommended V0.9 verification:

```powershell
python -m pytest -q
cd D:\Sera\frontend
npm.cmd run build
npm.cmd test
cd D:\Sera
python -m evaluation.workbench_editing.run_workbench_edit_eval --max-prompts 3
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.v09_precision_and_musicality.run_v09_eval --max-prompts 3
```

Remaining MuseScore-level limitations:

- Sera is not a full MuseScore replacement.
- Engraving, layout reflow, tuplets, ornaments, pedal, lyrics, fingering, MIDI keyboard input, and real audio-synchronized playback are still limited.
- Musicality metrics are proxy metrics for structure and surface variety; they are not a substitute for human aesthetic judgment.
- Automatic accompaniment can change a piece's style and should remain previewable and user-confirmed.

V1.0 recommendations:

1. Add a true notation layout engine binding for exact notehead geometry.
2. Add MIDI keyboard input and real playback synchronization.
3. Add user-confirmed local regeneration that preserves manually edited events by default.
4. Extend evaluation with human ratings for musicality, editability, and style preservation.

## V0.91 Stabilization And Usability

V0.91 keeps the V0.9 architecture and focuses on day-to-day usability: direct click-to-notate input, readable score layout, multilingual UI infrastructure, and a Windows desktop packaging route.

Click-to-notate:

- Switch to `Note Input` mode in the Workbench.
- Choose duration, dotted state, accidental, staff, and voice from the toolbar or Note Input panel.
- Click any staff location to insert a note at the nearest beat-grid offset.
- Vertical staff position maps to pitch; right hand uses treble mapping and left hand uses bass mapping.
- If the `rest` tool is active, clicking inserts a rest instead of a note.
- If a covering rest already exists, click input prefers converting that rest to a note.
- Invalid clicks show warning feedback in the LocationBar and ghost preview.
- Inserted notes/rests are normal `ScoreOperation` actions, so undo/redo still works.

Dotted input:

- Press `.` or use `Dot`, then select a duration such as quarter or eighth.
- Click the staff or press `A-G`; the stored event duration becomes `dotted_quarter`, `dotted_eighth`, or `dotted_half`.
- MusicXML export writes the corresponding `<dot/>`.

Readable layout:

- Workbench defaults to `fit_width`.
- Long scores keep readable measure width and scroll horizontally instead of being squeezed into an unreadable strip.
- Layout modes: `fit_width`, `page`, `continuous`, `compact`, and `large_print`.
- Zoom presets: 75%, 100%, 125%, and 150%.
- `Reset View` returns to fit-width, default zoom, and the first system.
- `Re-render Score` forces renderer refresh.
- `MusicXML Text` opens a fallback text preview when rendering is blank or suspect.
- StatusBar shows renderer mode, render state, render time, layout mode, zoom, and fallback message.

Language switching:

- Use the top-bar language selector to switch between English and Simplified Chinese.
- The preference is saved in `localStorage` under `sera.language`.
- Translation files live in `frontend/src/i18n/locales/en.json` and `frontend/src/i18n/locales/zh-CN.json`.
- Add a new visible UI string by adding the same key to both locale files and calling `t("key")`.
- Check translation parity with:

```powershell
cd D:\Sera\frontend
npm.cmd run i18n:check
```

Windows executable packaging route:

- Backend packaging files are under `packaging/backend`.
- Desktop launcher packaging files are under `packaging/desktop`.
- Windows build scripts are under `packaging/windows`.
- Electron shell files are under `electron`.
- The packaged backend selects port `8000` by default and automatically chooses a nearby free port when needed.
- The selected backend port is written to `backend_port.json` in the runtime directory.
- `dist_desktop\Sera.exe` is the legacy PyInstaller local-server compatibility artifact. It does not open a browser by default, but it is not the default UI shell.
- The Electron desktop exe waits for the runtime port file before loading the frontend, so the UI does not connect to a stale backend port.
- Electron packaging is required for a releasable no-browser desktop build; the packaging script fails clearly if the Electron artifact is missing.
- No real API key is bundled; keep credentials external in `.env`.

Run the source baseline before cutting a desktop build:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
npm.cmd test
cd ..
.\.venv\Scripts\python.exe -m evaluation.v093_real_score_and_notation.run_v093_eval --max-prompts 3
```

Build the Windows desktop exe:

```powershell
cd D:\Sera
packaging\windows\build_windows_app.bat
```

Build outputs:

- `dist_desktop\Sera.exe`: legacy local-server compatibility launcher.
- `dist_desktop\backend\SeraBackend.exe`: PyInstaller backend runtime.
- `dist_desktop\frontend\dist\index.html`: Vite frontend bundle.
- `dist_desktop\release\win-unpacked\Sera.exe`: primary unpacked Electron desktop exe.
- `dist_desktop\release\Sera-<version>-x64.exe`: primary portable Electron desktop exe.
- `dist_desktop\release_manifest.json`: manifest with the exact generated paths.

Run the packaging smoke test after building. It starts the staged backend, checks `/health`, verifies the legacy compatibility launcher, and smokes the required Electron desktop artifact:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\smoke_test_packaged_app.ps1
```

Troubleshooting packaged backend startup:

- Check whether `dist_desktop\backend\SeraBackend.exe` exists.
- Check whether `dist_desktop\Sera.exe` exists.
- Check the runtime `backend_port.json` for the actual selected port.
- Run `Invoke-RestMethod http://127.0.0.1:<port>/health`.
- If PyInstaller is missing, install it into `.venv` and rerun the build script.
- If Electron packaging fails, rerun `npm.cmd install --no-audit --no-fund` in `D:\Sera\electron`, confirm `node_modules\electron\dist\electron.exe` exists, then rerun `packaging\windows\build_windows_app.bat`.

V0.91 evaluation:

```powershell
python -m evaluation.v091_usability.run_v091_usability_eval --max-prompts 3
python -m evaluation.v091_usability.summarize_v091_results
```

Outputs:

- `evaluation/results/v091_usability_results.csv`
- `evaluation/results/v091_usability_summary.json`
- `evaluation/results/v091_table.tex`
- `evaluation/results/v091_failure_cases.json`

Remaining limitations:

- Sera is still not a complete MuseScore replacement.
- Professional engraving, wrapped multi-system layout, tuplets, ornaments, pedal, lyrics, fingering, MIDI keyboard input, real audio playback, and collaboration remain limited.
- Pitch mapping is a deterministic staff-position approximation, not a full engraving-engine semantic map.
- The desktop packaging route now produces a local portable exe; code signing, auto-update, and a polished installer remain future work.

V0.92 recommendations:

1. Add wrapped multi-system fallback layout instead of horizontal-only long-score scrolling.
2. Add an installer/signing pipeline for the Windows desktop build.
3. Add full translation coverage scanning for remaining legacy panels.
4. Improve pitch mapping with key-signature-aware accidentals and ledger-line preview.
5. Add replacement/compression UX for measure-overflow edits.

## V0.92 Unified Score Source, Custom Style, And Readable Layout

V0.92 fixes three root causes before larger model training: generated preview now uses the authoritative `ScoreDocument` or real MusicXML, playback no longer synthesizes from `plan.measures`, and custom prompts such as `cyberpunk piano passage` are preserved as executable style profiles instead of falling back to pure classical.

Authoritative score flow:

```text
Prompt -> Plan -> Generator -> MusicXML -> ScoreDocument -> Preview / Playback / Export / Workbench
```

`plan.measures` remains visible in the Agent Plan panel, but it is not the rendered score and is not a playback source. The Score tab shows:

- Rendered Score from `score_document` when present.
- Fallback MusicXML text rendering only when `score_document` is unavailable.
- Score Source and Playback Source badges.
- Consistency Report with MusicXML event count, ScoreDocument event count, MIDI event count, mismatches, warnings, and errors.
- Open in Workbench, Download MusicXML, and Play generated MIDI actions.

Playback source order:

1. Backend generated MIDI export from the same canonical score.
2. ScoreDocument note events if the MIDI file is unavailable.
3. Unavailable state if neither source exists.

Custom styles:

- Cyberpunk maps to `base_style: electronic`, tags `cyberpunk`, `futuristic`, `dark`, texture `ostinato`, accompaniment `repeating_bass`, harmony `minor_modal`, and high dynamic contrast.
- Anime maps to pop/lyrical melody with arpeggiated accompaniment.
- Cinematic maps to dramatic chordal/arpeggiated piano with stronger cadence.
- New age maps to soft ambient arpeggiation.
- Game soundtrack maps to loopable ostinato/theme controls.

Readable layout:

- ScoreViewer and Workbench share system layout defaults.
- 16-measure scores default to 4 measures per system.
- Fit Width fits the current wrapped system/page instead of shrinking the whole score into one line.
- Fallback hit areas, Beat Grid, Score Cursor, and LocationBar coordinates use the same wrapped layout.
- Reset View, Fit Width, and Re-render remain available in the Workbench toolbar.

Run V0.92 evaluation:

```powershell
python -m evaluation.v092_unified_score_and_style.run_v092_eval --max-prompts 3
python -m evaluation.v092_unified_score_and_style.summarize_v092_results
```

Outputs:

- `evaluation/results/v092_score_consistency_results.csv`
- `evaluation/results/v092_style_profile_results.csv`
- `evaluation/results/v092_layout_results.csv`
- `evaluation/results/v092_summary.json`
- `evaluation/results/v092_table.tex`
- `evaluation/results/v092_failure_cases.json`

Remaining limitations:

- Browser MIDI support varies; when MIDI playback cannot be opened inline, Sera exposes the generated MIDI export and falls back to ScoreDocument event preview only when no MIDI URL exists.
- OSMD notehead geometry can still be unavailable; Sera uses deterministic wrapped fallback hit boxes in that case.
- Custom style profiles are rule-based mappings, not a trained style-conditioned symbolic model.

V0.93 recommendations:

1. Add a robust browser MIDI playback library or server-rendered audio preview.
2. Extend custom style mappings with user-editable profile presets.
3. Add visual consistency diffing between OSMD and fallback renderer.
4. Add larger model training only after style profile and score-source contracts remain stable across evaluations.

## V0.94 Prompt Integrity, Style Grounding, And Real Preview Guard

V0.94 fixes the prompt-to-plan chain before any larger model training. The Generate page now sends the raw user prompt unchanged and sends UI controls separately as `ui_controls`. Default UI values such as `romantic`, `A minor`, or `bass_chord` are no longer appended to the prompt text.

`/generate` accepts:

```json
{
  "raw_prompt": "赛博朋克钢琴，机械感，冷色，切分节奏，重复低音，8小节",
  "ui_controls": {
    "style": "romantic",
    "key": "A minor",
    "meter": "4/4",
    "texture": "melody_accompaniment",
    "length_measures": 16
  },
  "control_policy": {
    "prompt_priority": true,
    "show_conflicts": true,
    "allow_ui_defaults": true
  }
}
```

If the raw prompt conflicts with UI controls, prompt values win by default. The response includes `prompt_control_resolution`, `prompt_terms`, `source_prompt_terms`, `unparsed_prompt_terms`, `prompt_ui_conflicts`, `resolved_generation_request`, `plan_grounding`, and `prompt_plan_alignment_score`.

Chinese custom style parsing now recognizes examples such as `赛博朋克`, `机械感`, `冷色`, `切分节奏`, `重复低音`, `动画风`, `游戏配乐`, `电影感`, `新世纪`, `中国风`, and `五声`. A Chinese cyberpunk piano prompt maps to a custom/electronic profile with `ostinato`, `repeating_bass`, `minor_modal`, medium-high syncopation, and high dynamic contrast. The CompositionPlanningAgent uses that profile when creating the measure plan, so style affects rhythm vocabulary, texture, accompaniment, harmony flavor, and plan grounding instead of appearing only in metadata.

The generated score preview no longer shows handwritten ellipse-note SVG as normal notation. The main preview states are now real backend SVG/PNG from MuseScore or Verovio, OSMD rendering of real MusicXML, MusicXML text preview with a visible renderer warning, or an explicit unavailable state. Renderer availability is exposed at:

```bash
GET /score/renderer_status
```

Run the V0.94 hotfix checks:

```bash
python -m pytest -q
cd frontend
npm run build
npm test
```
## LLM API 控制

Sera Agent Console 现在支持通过可配置 LLM API 把自然语言指令转换为受限 ScorePatch。模型不能直接重写 MusicXML；所有提案仍须经过 schema、结构、时值、保护范围、事务和源文件保真导出检查。

推荐直接在 Sera Desktop 顶部点击“模型设置”，选择服务商、模型并输入 API Key。密钥使用 Windows 当前用户加密保存，保存后立即启用，无需重启。

PowerShell 兼容配置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_llm.ps1
```

脚本配置写入 `%LOCALAPPDATA%\Sera\llm.env`，完成后重启 Sera。详细的软件内配置、安全边界、其他 provider 和状态检查见 [LLM API 配置说明](docs/LLM_API_SETUP.md)。

## Sera Composer V0.2

Composer 是建立在现有安全编辑闭环上的理论驱动创作层。它不让 LLM 直接重写 MusicXML：LLM 只规划风格、织体、和声功能、动机和张力；本地规则据此生成多个精确音高候选，并逐个检查和弦骨干、终止、音域、跳进、声部进行、保护范围和宿主结构。选择候选后仍须进入原有 ScorePatch 审查，用户确认前不会修改宿主乐谱。

桌面端使用方法：

1. 在 MuseScore 中打开乐谱并通过 Sera Bridge 发送选区，或在 Sera 中导入 MusicXML。
2. 切换到“创作草案”，描述风格、和声和旋律目标。
3. 生成候选，比较理论、安全和演奏评分及理论依据编号。
4. 选择一个候选进入最终提案审查；确认保护范围无违规后再生成宿主修订。

V0.2 在原有安全创作层上增加七类版本化风格知识、原谱乐句/动机分析、16 候选内部搜索、动机/乐句/风格批评和本地 A/B 偏好画像。界面仍只展示 3 个通过事务检查的差异候选；偏好只能影响后续软排序，不能绕过保护范围、回滚或 MusicXML 往返验证。

用户在候选卡片点击“我更喜欢这个版本”即可形成闭环。反馈默认只保存在 `%LOCALAPPDATA%\Sera\composer_feedback.v0.2.jsonl`，不保存音符、MusicXML 或个人身份。换乐器、增删声部和改节奏等结构性配器仍只生成计划，不直接应用。完整说明见 [Sera Composer V0.2](docs/SERA_COMPOSER_V02.md)；V0.1 基线说明仍保留在 [SERA_COMPOSER_V01.md](docs/SERA_COMPOSER_V01.md)。

## Sera Composer V0.3

V0.3 建立“大库、小上下文”检索层：本地知识库现有 4 个包、266 张原子规则卡，每次按当前 ScoreDocument、风格、乐器、拍号、目标小节与创作目标，只选择默认最多 12 张并受 1800 estimated-token 预算限制。完整知识库不会发送给 LLM，因此以后扩充本地规则不会线性增加单次 token 消耗。

Composer 界面会显示本地总卡数、本次选中数、token 估算/预算和选中规则。高层规划之后仍走 V0.2 候选搜索与既有 ScorePatch 事务审核；LLM 不能直接改 MusicXML、事件 ID、节奏、编制或保护范围。验证命令与扩库方法见 [Sera Composer V0.3](docs/SERA_COMPOSER_V03.md)。

点击“生成创作候选”后，右侧会立即显示当前阶段和等待秒数。实时模型最多等待30秒；如果模型超时，Composer 会自动切换到本地确定性理论计划继续生成候选，而不是一直停在加载状态。网络或后端错误会在同一区域明确显示，且任何等待、超时或回退都不会修改宿主原谱。

在“修改提案”中输入明确的创作指令，例如“重写当前选区旋律并保持节奏”或“重新和声化这两小节”，Sera 会自动将其路由到 Composer，而不会交给只支持原子编辑的普通 LLM 提案器。Composer 生成并评审三个候选，只把评分最高且事务有效的候选编译为现有音符上的 `set_pitch` ScorePatch；界面会显示“Composer 自动路由”、候选数量和最佳评分。模糊的“更好听”“像海浪”仍会拒绝，除非用户明确授权要改写的音乐对象。
