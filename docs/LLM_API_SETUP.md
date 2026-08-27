# Sera LLM API 配置与安全边界

Sera Desktop 可以调用 LLM API 理解自然语言编辑指令，但模型不直接读写 MusicXML，也不能绕过 ScorePatch 验证、保护范围检查或宿主源文件保真导出。

## 数据链路

```text
宿主 MusicXML + 宿主选区 + 用户指令
  -> 紧凑目标上下文（目标小节及必要邻域）
  -> LLM 严格结构化提案
  -> 服务器重建 source-bound ScorePatch
  -> schema / 结构 / 时值 / protected-scope 验证
  -> dry-run 预览
  -> 用户确认
  -> 事务应用
  -> 原始 MusicXML 上的局部 XML 补丁
  -> MuseScore 新修订窗口
```

LLM 不会收到完整无关乐谱，也不会获得文件路径、文件写入工具或 MuseScore 控制权。

## 在 Sera 软件内配置（推荐）

1. 启动 Sera Desktop；
2. 点击顶部的“模型设置”；
3. 选择 OpenAI、DeepSeek、Qwen 或 OpenAI 兼容接口；
4. 填写模型名称、API 地址和 API Key；
5. 点击“保存并启用”。

保存成功后顶部状态会立即显示 provider 和模型，无需重启。API Key 使用 Windows DPAPI 绑定到当前 Windows 用户后加密保存；配置文件中只有密文，前端、状态接口、日志和 ScorePatch 均不会回显密钥。再次打开设置时，密钥框保持为空；留空保存会保留已有密钥。

点击“使用本地规则”会删除已保存的加密凭据并立即停用外部 API。

## 对话与修改提案是两条独立通道

- “对话”：可在未连接宿主时使用，用于普通问答、乐理解释、Sera 使用帮助和编辑意图澄清。该接口只返回文本，不创建 ScorePatch，也没有 apply/export 路径。
- “修改提案”：必须先连接宿主乐谱与选区。模型只负责提出白名单内的结构化操作，服务器负责绑定 event ID、目标范围、源指纹和保护范围，再执行完整 dry-run 验证。

如果在“对话”中输入编辑命令，Sera 只会提示切换到“修改提案”，不会声称已经修改乐谱。右侧“修改提案”栏不显示普通聊天回答。

## PowerShell 兼容配置

旧版外部配置方式仍可用。在 `D:\Sera` 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_llm.ps1
```

脚本会隐藏 API Key 输入，并把兼容配置写入：

```text
%LOCALAPPDATA%\Sera\llm.env
```

Key 不会写入仓库、前端、ScorePatch、实验输出或日志。使用脚本配置后需要完全退出并重新启动 Sera Desktop。首次在软件内重新保存时，Sera 会迁移为 Windows 用户加密存储。

默认示例模型为 `gpt-5.6-terra`，但模型名是配置项，不在核心代码中固定。可以显式选择其他模型：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_llm.ps1 -Provider openai -Model gpt-5.6-sol
```

也支持 OpenAI-compatible、DeepSeek 和 Qwen 配置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_llm.ps1 -Provider deepseek -Model deepseek-chat
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_llm.ps1 -Provider qwen -Model qwen-plus
```

OpenAI 使用 Responses API 的严格 JSON Schema 输出；其他兼容提供商使用 Chat Completions 与服务器端 JSON/schema 校验。只有确认目标兼容端点支持严格 `json_schema` 时，才应手动设置 `SERA_LLM_STRUCTURED_OUTPUTS=true`。

## 检查状态

启动 Sera 后访问本地 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/sera-edit/provider-status
```

返回内容包含：

- `mode`：`live_llm` 或 `local_rule`；
- `provider` 和 `model`；
- `transport`：`responses`、`chat_completions` 或 `local`；
- `available`；
- `api_key_configured`；
- `credential_storage`：`windows_dpapi`、`environment` 或 `none`；
- `config_file`；
- `reason`。

该接口不会返回 API Key。桌面顶部也会显示当前 provider；每个提案会显示实际 provider、model、延迟和是否发生本地回退。

## 当前允许模型规划的操作

- `transpose`；
- `set_pitch`；
- `set_dynamic`；
- `set_articulation`，限 `staccato`、`accent`、`tenuto`。

模型只能引用宿主当前选区内、由 Sera 提供的稳定 event ID。以下操作当前必须拒绝：

- 插入或删除音符、小节；
- 改变时值、节奏、拍号或调号；
- 延音线、连音线和跨谱表关系重构；
- 排版修改；
- 整谱重写；
- 选区外编辑；
- 无法确定执行语义的模糊指令。

这些限制与当前源文件保真导出能力一致。后续只有在相应 MusicXML 局部补丁和宿主回归测试完成后才会开放更多操作。

## 故障与回退

默认 `SERA_LLM_FALLBACK_LOCAL=true`。Key 缺失、网络错误、限流、超时或模型返回非法 event ID 时，Sera 会：

1. 不修改乐谱；
2. 在界面显示本地规则或安全拒绝；
3. 仅对本地规则已支持的简单指令生成回退提案；
4. 仍然执行完整 ScorePatch 验证和用户确认。

对模型输出的容错仅限可证明无歧义的格式修复，例如把单个 operation 对象包成数组；其他格式错误最多触发一次受限 LLM 修复。修复提示仍携带原目标范围、保护范围、允许的 event ID 和操作白名单。模型一旦引用选区外 ID、产生不支持操作或无法确定意图，提案仍会被拒绝。

如需禁止回退，在用户配置中设置：

```text
SERA_LLM_FALLBACK_LOCAL=false
```

## 隐私与费用

- 只有指令、目标范围、目标小节及必要邻域的结构化事件会发送给 provider；
- 默认 `SERA_LLM_STORE=false`；
- Sera 不在代码中固定价格，费用字段必须由用户按 provider 当前价格配置；
- provider 可能仍根据其服务条款处理请求数据，使用前应检查账户的数据保留设置；
- 软件内保存的 Key 采用 Windows 当前用户加密；换到其他 Windows 账户或电脑不能解密；
- 即使配置文件中是密文，也不要把 `%LOCALAPPDATA%\Sera\llm.env` 上传、提交到 Git 或发送给他人。
