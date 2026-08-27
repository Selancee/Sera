# SeraEdit 实验运行说明

运行器支持三条件、单/多 provider、重复运行、任务级恢复、共享响应缓存、超时、有限重试与指数退避、请求频率限制、并发限制、成本预算、原始请求/响应保存、错误序列化和配置/Prompt/Benchmark 漂移阻断。

## 无 API Key 的本地闭环

```powershell
.\.venv\Scripts\python.exe scripts\run_smoke_experiment.py
.\.venv\Scripts\python.exe scripts\run_core_experiment.py
```

这两条默认使用 `BenchmarkMockProvider`。输出永久标记为 `mock_non_formal` 和 `formal_results_allowed=false`，只能验证管线，不能写成模型表现。

## 正式 Core

1. 复制 `evaluation/configs/core.example.yaml` 到未提交的本地配置；
2. 填入实际模型名、当前输入/输出价格和正预算；
3. 只在环境变量中设置 API Key；
4. 运行：

```powershell
.\.venv\Scripts\python.exe scripts\run_core_experiment.py --config path\to\core.local.yaml
```

正式配置缺价格、预算或环境密钥时会在发出请求前失败。YAML 中出现 `api_key` 字段也会直接拒绝。

## Full

复制 `evaluation/configs/full.example.yaml`，配置两个 provider/model 和三次重复后运行：

```powershell
.\.venv\Scripts\python.exe scripts\run_full_experiment.py --config path\to\full.local.yaml
```

总预算会保守地均分给 provider，避免并发请求合计突破上限。缓存文件不保存密钥；每次运行的 manifest 保存 Git 状态、Python/平台、依赖 hash、prompt hash、benchmark hash 与无密钥 provider 配置。

## Repair 边界

- `full_rewrite`：只清理允许的 XML 包裹/编码，不使用 ScorePatch repair。
- `patch_only`：只做解析和基础 apply，不启用 deterministic/LLM repair、protected-scope 或事后音乐约束回滚。
- `sera_full`：先做 deterministic repair；仍失败时最多执行配置中的 `max_repair_attempts`（默认 2）次 provider repair。每次输入、输出、错误变化、token、延迟和成本都保存为证据。

## 重算、统计、论文资产与匿名包

以下命令只从已有实验目录读取，不会发出新的模型请求：

```powershell
.\.venv\Scripts\python.exe scripts\recompute_metrics.py --experiment core_mock_120_v5
.\.venv\Scripts\python.exe scripts\generate_paper_assets.py --experiment core_mock_120_v5
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment core_mock_120_v5
.\.venv\Scripts\python.exe scripts\export_anonymous_package.py --experiment core_mock_120_v5
```

当前 `core_mock_120_v5` 是可复现的 `mock_non_formal` 管线证据，不是正式模型实验。正式论文数字必须来自授权的 live provider 配置，并在 120 条任务完成人工复核后重新生成。
