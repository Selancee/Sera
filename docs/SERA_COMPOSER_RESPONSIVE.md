# Sera Composer 响应式 LLM 工作流

## 当前行为

从 dev.13 开始，自动 Composer 采用两阶段流程；dev.14 修复了真实 DeepSeek 长推理截断与多声部候选全部被拒绝的问题：

1. 服务端立即启动一个有界的后台 LLM 高层规划任务；
2. 同时用确定性理论计划搜索本地安全候选；
3. `composer/preview` 先返回本地候选和后台任务 ID；
4. 前端每 1.2 秒轮询后台状态；
5. LLM 返回合法 `CompositionPlan` 后自动替换候选；
6. LLM 超时、网络错误或非法计划不会清空已经返回的本地候选。

本地草案和 LLM 候选都必须通过来源指纹、事务、目标/保护范围、节奏、事件数、记谱关系、可演奏性和 MusicXML 往返验证。后台结果不会直接修改宿主乐谱，仍需用户审查和应用。

## 配置

可在应用内的“模型设置”配置 Composer 后台等待时间，也可使用环境变量：

```dotenv
SERA_COMPOSER_LLM_TIMEOUT_SECONDS=180
SERA_COMPOSER_LLM_MAX_OUTPUT_TOKENS=2048
```

- `SERA_COMPOSER_LLM_TIMEOUT_SECONDS`：独立的 Composer 后台等待上限，范围 30–600 秒，默认 180 秒。它不会阻塞首批本地候选。
- `SERA_COMPOSER_LLM_MAX_OUTPUT_TOKENS`：高层计划输出上限，范围 512–8192，默认 2048。
- 普通对话与修改提案继续使用通用 `SERA_LLM_TIMEOUT_SECONDS` 和 `SERA_LLM_MAX_OUTPUT_TOKENS`。

## DeepSeek V4 Pro 专用路径

Composer 只让 LLM 选择风格、和声、织体、动机、张力和力度，不让它直接生成音符。dev.14 对 DeepSeek 请求采用：

- 紧凑乐谱摘要，不发送 129 个事件的逐音符上下文；
- `response_format: {"type":"json_object"}`；
- 明确的 JSON 示例；
- `thinking: {"type":"disabled"}`，只用于这个窄结构化计划。

关闭思考不会改变普通对话的推理设置。LLM 负责高层取舍，本地 Composer 仍负责检索知识、实现音高候选并执行全部安全验证。

## 可演奏性处理

钢琴多声部候选现在从原乐谱推导每小节的左右手安全边界：

- 原谱左右手分离的小节，候选必须保留位于原间隙中的边界；
- 原谱已经声部交叉的小节，不把既有问题误报为候选新增问题；
- 新增音域越界或新增声部交叉仍然安全拒绝。

这避免了固定左右手音域同时重写五个声部时，把原本正常的小节全部变成新增交叉。

## API 合同

初始响应包含：

```json
{
  "planner": {"planner": "deterministic_theory"},
  "candidates": [],
  "refinement": {
    "job_id": "composer_refine_...",
    "status": "running",
    "created_at": 0,
    "completed_at": null,
    "error": ""
  }
}
```

前端通过只读接口获取结果：

```text
GET /sera-edit/composer/refinements/{job_id}
```

状态为 `running`、`ready` 或 `failed`。只有 `ready` 携带完整优化结果，响应不包含 API Key。

## dev.14 真实验证

在用户的 M1–M8、129 个目标音符、五个钢琴声部会话上：

- 首批本地结果 12.055 秒返回，评审 8 个、有效 8 个、返回 3 个；
- DeepSeek V4 Pro 后台规划 4.347 秒完成；
- 输入 2890 tokens，输出 174 tokens，完成状态为 `live_llm`；
- LLM 计划下评审 12 个、有效 12 个、拒绝 0 个、返回 3 个；
- 浏览器可见检查确认宿主会话 M1–M8 已载入、模型设置显示 180 秒，控制台无 error/warn。

这些是响应性、结构完整性与验证流水线证据，不是“更好听”的主观质量结论。
