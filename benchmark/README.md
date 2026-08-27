# SeraEdit Benchmark

本目录保存 SeraEdit 的可复现 MusicXML 局部编辑基准。`source_scores` 同时保留 canonical `ScoreDocument` 与由其导出的 MusicXML；`tasks` 保存中英文指令、目标/保护范围与确定性约束；`gold_patches` 保存严格 `ScorePatch 1.0.0`；`expected_outputs` 保存事务执行后的乐谱、MusicXML 与事件级 diff。

当前资产包括：

- `batch1`：30 条最小闭环任务；
- `batch2`：累计 60 条开发任务；
- `core`：20 份短谱例、120 条核心任务；
- `batch3`：Core 中后续增加的 60 条任务。

Core 的 120 条任务已经全部通过 schema、gold patch 事务执行、确定性约束、保护范围和 MusicXML 往返自动验证。自动验证不等于人工音乐审阅；所有任务仍保持 `pending_human_review`，对应可写复核表位于 `review/core_human_review.csv`。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_benchmark_core.py --target 120
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --split core --write-report
```

所有源谱均由仓库内确定性规则生成并按 CC0-1.0 发布，不包含版权状态不明的现代作品。
