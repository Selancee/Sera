import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  exportBenchmarkReviews,
  getBenchmarkReviewSummary,
  getBenchmarkReviewTask,
  listBenchmarkReviewTasks,
  prepareBenchmarkReviewArtifact,
  submitBenchmarkReview
} from "../api.js";
import { isDesktopRuntime, openDesktopLocalFile } from "../desktop/desktopRuntime";

type Decision = "compliant" | "needs_revision" | "exclude";
type ReviewerRole = "primary" | "secondary";

type ReviewRecord = {
  decision: Decision;
  reviewer_id: string;
  reviewer_role: ReviewerRole;
  dimensions: Record<string, number>;
  issue_codes: string[];
  notes: string;
  reviewed_at: string;
};

type TaskListItem = {
  task_id: string;
  score_id: string;
  category: string;
  difficulty: string;
  instruction: { en: string; zh: string };
  expected_status: string;
  review_status: Decision | "pending";
  automatic_valid?: boolean;
  runtime_acceptance?: RuntimeAcceptance;
  primary_review?: ReviewRecord;
  secondary_review?: ReviewRecord;
};

type RuntimeAcceptance = {
  status: "passed" | "failed" | "unverified";
  runs: number;
  passed: number;
  failed: number;
  languages: string[];
  repetitions?: number;
  host_outputs?: Record<string, boolean>;
  paper_model_result_eligible?: boolean;
};

type ReviewSummary = {
  total: number;
  primary_reviewed: number;
  secondary_reviewed: number;
  secondary_target: number;
  stale_records: number;
  remaining: number;
  completion_rate: number;
  decisions: Record<string, number>;
  noncompliance_rate: number;
  runtime_acceptance?: {
    available: boolean;
    experiment_id?: string;
    tasks_passed: number;
    tasks_failed: number;
    runs: number;
    reproducibility?: { rate?: number };
  };
  calibration_gate: {
    status: "not_enough_reviews" | "monitoring" | "benchmark_repair_required" | "aesthetic_calibration_required";
    minimum_reviewed: number;
    threshold: number;
    benchmark_repair_required: boolean;
    aesthetic_calibration_required: boolean;
    musical_problem_count: number;
    musical_problem_rate: number;
    target_pairwise_reviews: number;
    dimensions: string[];
    boundary: string;
  };
};

type TaskDetail = {
  task: Record<string, any> & { instruction: { en: string; zh: string } };
  score_summary: Record<string, any>;
  expected_score_summary: Record<string, any>;
  gold_patch: Record<string, any>;
  diff: Record<string, any>;
  diff_rows: Array<Record<string, any>>;
  host_notation_guidance?: {
    kind: "isolated_dynamic_with_restore" | "dynamic_change";
    changed_event_ids: string[];
    dynamic_marks_added: Array<Record<string, any>>;
    dynamic_marks_removed: Array<Record<string, any>>;
    restoration_marks: Array<Record<string, any>>;
    explanation_zh: string;
    explanation_en: string;
  } | null;
  automatic_validation?: Record<string, any>;
  runtime_acceptance?: RuntimeAcceptance;
  primary_review?: ReviewRecord;
  secondary_review?: ReviewRecord;
  task_fingerprint: string;
};

type TaskStandard = {
  prefix: string;
  range: string;
  name: string;
  expected: "成功执行" | "安全拒绝";
  standard: string;
  protected: string;
};

const TASK_STANDARDS: TaskStandard[] = [
  {
    prefix: "pitch",
    range: "pitch_001–015",
    name: "音高移调",
    expected: "成功执行",
    standard: "指定事件按题目要求升降准确半音数。",
    protected: "音符时值、目标外事件及保护谱表不得改变。"
  },
  {
    prefix: "rhythm",
    range: "rhythm_001–015",
    name: "节奏时值",
    expected: "成功执行",
    standard: "合并指定的前两个节奏单位：首事件延长，第二事件删除。",
    protected: "后续音高、目标外事件和小节总时值不得意外改变。"
  },
  {
    prefix: "key",
    range: "key_001–015",
    name: "调号",
    expected: "成功执行",
    standard: "只把调号改成题目指定的调。",
    protected: "现有音符音高不随调号自动移调，其他记谱内容保持不变。"
  },
  {
    prefix: "voice",
    range: "voice_001–015",
    name: "声部与织体",
    expected: "成功执行",
    standard: "把指定小节、谱表中的目标事件从声部1移动到声部2。",
    protected: "音高、节奏、事件数量及目标外声部不得改变。"
  },
  {
    prefix: "dynamics",
    range: "dynamics_001–010",
    name: "力度与演奏法",
    expected: "成功执行",
    standard: "只给指定音符设置 f 或 staccato，以本题约束为准。",
    protected: "目标音的音高与时值不变，其他音符不得被批量加记号。"
  },
  {
    prefix: "insertion",
    range: "insertion_001–010",
    name: "替换、插入与删除",
    expected: "成功执行",
    standard: "删除指定旧事件，并在同一位置插入题目指定的 F♯4 或 C大三和弦。",
    protected: "替换后的时值/位置符合题目，目标外事件与小节结构不变。"
  },
  {
    prefix: "ties",
    range: "ties_001–010",
    name: "连奏线",
    expected: "成功执行",
    standard: "在指定小节第一个与最后一个目标音之间建立完整 slur 起止关系。",
    protected: "不得把 slur 误作 tie；音高、时值及目标外关系保持不变。"
  },
  {
    prefix: "meter",
    range: "meter_001–010",
    name: "拍号与小节结构",
    expected: "成功执行",
    standard: "meter_001 为 4/4→3/4 并删除各谱表每小节最后一拍；meter_002–010 只替换等总时长拍号显示。",
    protected: "保留事件的音高/时值不变；除 meter_001 明示删除外，不得重划小节或重组节拍。"
  },
  {
    prefix: "compound",
    range: "compound_001–010",
    name: "复合编辑",
    expected: "成功执行",
    standard: "指定的最后两个目标音同时升高1半音，并把最后一个目标音设为 f。",
    protected: "所有时值、目标外音符和保护范围保持不变；两步必须同时完成。"
  },
  {
    prefix: "conflict",
    range: "conflict_001–010",
    name: "矛盾或不支持",
    expected: "安全拒绝",
    standard: "识别数学冲突或不可验证的审美指令，明确拒绝，不生成伪造修改。",
    protected: "正确结果是原谱完全不变、0处差异；预期谱只是拒绝后的原谱副本。"
  }
];

const DIMENSIONS = [
  ["instruction_clarity", "指令清晰"],
  ["scope_correctness", "范围正确"],
  ["gold_correctness", "Gold 正确"],
  ["musical_validity", "音乐可用"]
] as const;

const ISSUE_LABELS: Array<[string, string]> = [
  ["instruction_ambiguous", "指令含糊"],
  ["target_scope_wrong", "目标范围错误"],
  ["protected_scope_wrong", "保护范围错误"],
  ["gold_patch_wrong", "Gold Patch 错误"],
  ["expected_output_wrong", "预期输出错误"],
  ["refusal_label_wrong", "拒绝标签错误"],
  ["constraint_wrong", "约束定义错误"],
  ["musically_implausible", "音乐性不合理"],
  ["host_render_issue", "宿主渲染异常"],
  ["other", "其他"]
];

const DECISION_LABELS: Array<[Decision, string, string]> = [
  ["compliant", "合规", "任务、范围、Gold 与结果均可接受"],
  ["needs_revision", "需修订", "保留任务，但必须修复标注或音乐问题"],
  ["exclude", "排除", "任务不应进入正式核心集"]
];

const DEFAULT_DIMENSIONS = {
  instruction_clarity: 4,
  scope_correctness: 4,
  gold_correctness: 4,
  musical_validity: 4
};

function reviewForRole(detail: TaskDetail | null, role: ReviewerRole) {
  return role === "primary" ? detail?.primary_review : detail?.secondary_review;
}

function formatScope(scope: Record<string, any> | undefined) {
  if (!scope || !Object.keys(scope).length) return "未指定";
  const labels: string[] = [];
  if (scope.measures?.length) labels.push(`小节 ${scope.measures.join("、")}`);
  if (scope.parts?.length) labels.push(`声部组 ${scope.parts.join("、")}`);
  if (scope.staffs?.length) labels.push(`谱表 ${scope.staffs.join("、")}`);
  if (scope.voices?.length) labels.push(`声部 ${scope.voices.join("、")}`);
  if (scope.event_ids?.length) labels.push(`${scope.event_ids.length} 个事件`);
  return labels.join(" · ") || "全谱/由约束确定";
}

function conciseEvent(event: Record<string, any> | null | undefined) {
  if (!event) return "—";
  return [event.key, event.meter, event.pitch, event.duration, event.dynamic, event.articulation, event.voice ? `V${event.voice}` : ""]
    .filter(Boolean)
    .join(" · ") || event.type || "—";
}

function taskPrefix(taskId: string | undefined) {
  return (taskId || "").split("_")[0];
}

function taskStandard(taskId: string | undefined) {
  return TASK_STANDARDS.find((item) => item.prefix === taskPrefix(taskId));
}

function translateReason(reason: string | undefined) {
  const reasons: Record<string, string> = {
    meter_duration_conflict: "拍号与固定总时值互相矛盾",
    unsupported_ornament_semantics: "审美要求不可转成唯一、可验证的记谱操作"
  };
  return reasons[reason || ""] || reason || "题目要求拒绝";
}

function describeConstraint(constraint: Record<string, any>) {
  const event = constraint.event_id ? `事件 ${constraint.event_id}` : "指定事件";
  const events = constraint.event_ids?.length ? `${constraint.event_ids.length} 个指定事件` : "指定事件";
  switch (constraint.type) {
    case "pitch_delta": return `${events} 的音高统一${constraint.value >= 0 ? "升高" : "降低"} ${Math.abs(constraint.value)} 个半音`;
    case "preserve_duration": return "所有保留事件的时值必须与原谱一致";
    case "preserve_pitch": return "所有非明确改音高的保留事件必须维持原音高";
    case "duration_equals": return `${event} 的时值必须变为 ${constraint.value}`;
    case "dynamic_equals": return `${event} 的力度必须为 ${constraint.value}`;
    case "articulation_equals": return `${event} 的演奏法必须为 ${(constraint.value || []).join("、")}`;
    case "event_deleted": return `${event} 必须被删除`;
    case "event_inserted": return `必须插入事件 ${constraint.event_id}${constraint.pitch ? `，音高为 ${constraint.pitch}` : ""}`;
    case "chord_pitches": return `必须生成和弦 ${(constraint.value || []).join("–")}`;
    case "key_equals": return `全谱调号必须变为 ${constraint.value}`;
    case "meter_equals": return `目标拍号必须变为 ${constraint.value}`;
    case "slur_equals": return `${event} 的连奏线状态必须为 ${constraint.value}`;
    case "voice_equals": return `${event} 必须位于声部 ${constraint.value}`;
    case "refuse": return `必须安全拒绝：${translateReason(constraint.reason)}`;
    default: return `${constraint.type || "未知约束"} 必须通过`;
  }
}

function gateCopy(summary: ReviewSummary) {
  const gate = summary.calibration_gate;
  if (gate.status === "not_enough_reviews") {
    return {
      tone: "waiting",
      title: "先积累合规证据",
      text: `至少完成 ${gate.minimum_reviewed} 条主复核后，系统才判断是否需要批量修复或美感拟合。`
    };
  }
  if (gate.status === "aesthetic_calibration_required") {
    return {
      tone: "alert",
      title: "已触发艺术美感校准",
      text: `${Math.round(gate.musical_problem_rate * 100)}% 的已复核任务出现音乐性问题；下一阶段采集 ${gate.target_pairwise_reviews} 组盲化 A/B 偏好，拟合候选排序权重。`
    };
  }
  if (gate.status === "benchmark_repair_required") {
    return {
      tone: "warning",
      title: "先修复基准契约",
      text: "不合规率已超过门槛，但证据主要不是音乐性问题。应先修指令、范围、Gold 或约束，不启动审美拟合。"
    };
  }
  return {
    tone: "ready",
    title: "持续监测中",
    text: "当前证据未达到批量修复或美感校准门槛。"
  };
}

function RatingRow({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="review-rating-row">
      <span>{label}</span>
      <div aria-label={`${label}评分`} role="radiogroup">
        {[1, 2, 3, 4, 5].map((rating) => (
          <button
            aria-checked={value === rating}
            className={value === rating ? "selected" : ""}
            key={rating}
            onClick={() => onChange(rating)}
            role="radio"
            type="button"
          >
            {rating}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function BenchmarkReviewWorkspace({ onClose }: { onClose: () => void }) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [category, setCategory] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [runtimeFilter, setRuntimeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [reviewerId, setReviewerId] = useState(() => localStorage.getItem("sera.review.reviewer_id") || "reviewer-01");
  const [reviewerRole, setReviewerRole] = useState<ReviewerRole>("primary");
  const [decision, setDecision] = useState<Decision>("compliant");
  const [dimensions, setDimensions] = useState<Record<string, number>>(DEFAULT_DIMENSIONS);
  const [issueCodes, setIssueCodes] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [calibrationOpen, setCalibrationOpen] = useState(false);
  const [standardsOpen, setStandardsOpen] = useState(false);
  const filtersMountedRef = useRef(false);

  const refreshTasks = useCallback(async () => {
    const response = await listBenchmarkReviewTasks({ category, status: statusFilter, runtime_status: runtimeFilter, search });
    setTasks(response.items || []);
    setCategories(response.categories || []);
    setSummary(response.summary);
    setSelectedTaskId((current) => {
      if (current && (response.items || []).some((item: TaskListItem) => item.task_id === current)) return current;
      return response.items?.[0]?.task_id || "";
    });
  }, [category, runtimeFilter, search, statusFilter]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([getBenchmarkReviewSummary(), listBenchmarkReviewTasks()])
      .then(([summaryResponse, taskResponse]) => {
        if (!active) return;
        setSummary(summaryResponse);
        setTasks(taskResponse.items || []);
        setCategories(taskResponse.categories || []);
        setSelectedTaskId(taskResponse.items?.[0]?.task_id || "");
      })
      .catch((caught) => active && setError(caught.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!filtersMountedRef.current) {
      filtersMountedRef.current = true;
      return;
    }
    const timer = window.setTimeout(() => {
      refreshTasks().catch((caught) => setError(caught.message));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [refreshTasks]);

  useEffect(() => {
    if (!selectedTaskId) {
      setDetail(null);
      return;
    }
    let active = true;
    setLoading(true);
    getBenchmarkReviewTask(selectedTaskId)
      .then((response) => active && setDetail(response))
      .catch((caught) => active && setError(caught.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [selectedTaskId]);

  useEffect(() => {
    const existing = reviewForRole(detail, reviewerRole);
    setDecision(existing?.decision || "compliant");
    setDimensions(existing?.dimensions || DEFAULT_DIMENSIONS);
    setIssueCodes(existing?.issue_codes || []);
    setNotes(existing?.notes || "");
  }, [detail, reviewerRole]);

  const selectedIndex = useMemo(
    () => tasks.findIndex((task) => task.task_id === selectedTaskId),
    [selectedTaskId, tasks]
  );

  const gate = summary ? gateCopy(summary) : null;
  const currentStandard = taskStandard(detail?.task.task_id);
  const expectedRefusal = detail?.task.expected_status === "refuse";

  function toggleIssue(issueCode: string) {
    setIssueCodes((current) => current.includes(issueCode)
      ? current.filter((item) => item !== issueCode)
      : [...current, issueCode]);
  }

  async function openArtifact(variant: "source" | "expected" | "runtime_en" | "runtime_zh") {
    if (!selectedTaskId) return;
    setNotice("");
    setError("");
    try {
      const artifact = await prepareBenchmarkReviewArtifact(selectedTaskId, variant);
      if (isDesktopRuntime()) {
        const opened = await openDesktopLocalFile(artifact.path);
        if (!opened.ok) throw new Error(opened.error || "无法打开本地宿主检查文件。");
        const label = variant === "source" ? "原始" : variant === "expected" ? "预期" : variant === "runtime_en" ? "Sera 英文回放" : "Sera 中文回放";
        setNotice(`${label} MusicXML 已交给系统关联宿主打开。`);
      } else {
        await navigator.clipboard?.writeText(artifact.path);
        setNotice(`文件已准备，路径已复制：${artifact.path}`);
      }
    } catch (caught: any) {
      setError(caught.message);
    }
  }

  async function handleExport() {
    setError("");
    try {
      const exported = await exportBenchmarkReviews();
      if (isDesktopRuntime()) await openDesktopLocalFile(exported.csv_path);
      setNotice(`已导出 ${exported.record_count} 条记录：${exported.csv_path}`);
    } catch (caught: any) {
      setError(caught.message);
    }
  }

  async function handleSave() {
    if (!detail || !selectedTaskId || saving) return;
    if (!reviewerId.trim()) {
      setError("请填写复核人代号；不要填写真实姓名。 ");
      return;
    }
    if (decision !== "compliant" && !issueCodes.length) {
      setError("“需修订”或“排除”必须选择至少一个问题类型。 ");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    localStorage.setItem("sera.review.reviewer_id", reviewerId.trim());
    const nextTaskId = tasks[selectedIndex + 1]?.task_id || tasks.find((task) => task.review_status === "pending")?.task_id || "";
    try {
      const saved = await submitBenchmarkReview({
        task_id: selectedTaskId,
        reviewer_id: reviewerId.trim(),
        reviewer_role: reviewerRole,
        decision,
        dimensions,
        issue_codes: decision === "compliant" ? [] : issueCodes,
        notes
      });
      setSummary(saved.summary);
      setNotice(`${selectedTaskId} 已保存；基准原文件未被修改。`);
      await refreshTasks();
      if (nextTaskId) setSelectedTaskId(nextTaskId);
      else setDetail(await getBenchmarkReviewTask(selectedTaskId));
    } catch (caught: any) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="review-app-shell">
      <header className="review-topbar">
        <div className="review-brand">
          <span aria-hidden="true">S</span>
          <div><strong>SeraEdit 研究复核</strong><small>Gold 基准证据 · 本页面不调用 LLM</small></div>
        </div>
        <div className="review-topbar-actions">
          <button aria-expanded={standardsOpen} onClick={() => setStandardsOpen((current) => !current)} type="button">编号标准</button>
          <button onClick={handleExport} type="button">导出复核记录</button>
          <button className="primary" onClick={onClose} type="button">返回 Agent</button>
        </div>
      </header>

      {standardsOpen && (
        <section className="review-standards-panel" aria-label="编号标准总表">
          <header>
            <div><span className="review-eyebrow">阅读规则</span><h2>编号标准总表</h2></div>
            <p><strong>下划线后的数字只是任务序号</strong>，不是小节号、难度或期望修改数。每题仍以中英文指令、目标范围和下方确定性约束为最终标准。</p>
          </header>
          <div className="review-standards-table-wrap">
            <table>
              <thead><tr><th>编号</th><th>类别</th><th>期望</th><th>必须达到</th><th>必须保护</th></tr></thead>
              <tbody>{TASK_STANDARDS.map((item) => (
                <tr key={item.prefix}><td><code>{item.range}</code></td><td>{item.name}</td><td><span className={item.expected === "安全拒绝" ? "refuse" : "success"}>{item.expected}</span></td><td>{item.standard}</td><td>{item.protected}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      {summary && (
        <section className="review-summary-strip" aria-label="复核进度">
          <div><strong>{summary.primary_reviewed}/{summary.total}</strong><span>主复核</span></div>
          <div><strong>{summary.secondary_reviewed}/{summary.secondary_target}</strong><span>二次抽查</span></div>
          <div><strong>{Math.round(summary.completion_rate * 100)}%</strong><span>完成度</span></div>
          <div><strong>{Math.round(summary.noncompliance_rate * 100)}%</strong><span>不合规率</span></div>
          <div className={summary.runtime_acceptance?.tasks_failed ? "runtime-failed" : "runtime-passed"}>
            <strong>{summary.runtime_acceptance?.tasks_passed || 0}/{summary.total}</strong>
            <span>Agent 实跑 · {summary.runtime_acceptance?.runs || 0} 次</span>
          </div>
          <button className={`review-gate ${gate?.tone}`} onClick={() => setCalibrationOpen((current) => !current)} type="button">
            <span>{gate?.title}</span><small>{gate?.text}</small>
          </button>
        </section>
      )}

      {calibrationOpen && summary && (
        <section className="review-calibration-panel">
          <div>
            <span className="review-eyebrow">条件式艺术美感拟合</span>
            <h2>{summary.calibration_gate.aesthetic_calibration_required ? "进入盲化偏好校准" : "当前不启动拟合"}</h2>
            <p>{gate?.text}</p>
          </div>
          <ol>
            <li>只从被标记为“音乐性不合理”的类别抽取候选。</li>
            <li>由人工完成 {summary.calibration_gate.target_pairwise_reviews} 组不显示生成器身份的 A/B 比较。</li>
            <li>拟合旋律、和声、声部进行、节奏、织体、风格与可演奏性的候选排序权重。</li>
            <li>重新生成失败类别并再次走结构、保护范围、可演奏性与人工复核闭环。</li>
          </ol>
          <p className="review-boundary">边界：偏好只能校准 Sera 的候选排序，不能证明“普遍更好听”，也不能替代合规验证。</p>
        </section>
      )}

      {summary && summary.stale_records > 0 && (
        <div className="review-notice error" role="status">
          已保留 {summary.stale_records} 条旧版本审计记录，但对应任务已更新，因此不会计入当前复核进度；请重新复核这些任务。
        </div>
      )}

      {(notice || error) && <div className={`review-notice ${error ? "error" : "success"}`} role="status">{error || notice}</div>}

      <main className="review-workspace-grid">
        <aside className="review-task-rail">
          <div className="review-filter-stack">
            <label>搜索<input onChange={(event) => setSearch(event.target.value)} placeholder="任务、类别或指令" value={search} /></label>
            <div>
              <label>类别<select onChange={(event) => setCategory(event.target.value)} value={category}><option value="">全部类别</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label>状态<select onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}><option value="">全部状态</option><option value="pending">待复核</option><option value="compliant">合规</option><option value="needs_revision">需修订</option><option value="exclude">排除</option></select></label>
              <label>Agent 实跑<select onChange={(event) => setRuntimeFilter(event.target.value)} value={runtimeFilter}><option value="">全部实跑状态</option><option value="failed">只看失败</option><option value="unverified">只看未验证</option><option value="passed">只看通过</option></select></label>
            </div>
          </div>
          <div className="review-task-count">{tasks.length} 条任务</div>
          <div className="review-task-list" aria-label="基准任务列表">
            {tasks.map((task) => (
              <button className={task.task_id === selectedTaskId ? "selected" : ""} key={task.task_id} onClick={() => setSelectedTaskId(task.task_id)} type="button">
                <span className={`review-status-dot ${task.review_status}`} aria-hidden="true" />
                <span><strong>{task.task_id}</strong><small>{task.category} · {task.difficulty}</small><em>{task.instruction.zh || task.instruction.en}</em></span>
                <span className="review-task-evidence-badges">
                  {task.runtime_acceptance?.status === "passed" && <b className="runtime-pass" title={`${task.runtime_acceptance.runs} 次 Agent 实跑通过`}>✓</b>}
                  {task.runtime_acceptance?.status === "failed" && <b className="runtime-fail" title="Agent 实跑失败">!</b>}
                  {task.secondary_review && <b title="已二次复核">2</b>}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="review-evidence-panel" aria-label="复核证据">
          {!detail ? <div className="review-empty">{loading ? "正在读取任务证据…" : "没有符合筛选条件的任务。"}</div> : (
            <>
              <header className="review-task-header">
                <div><span className="review-eyebrow">{detail.task.category} · {detail.task.difficulty}</span><h1>{detail.task.task_id}</h1></div>
                <div className="review-header-badges">
                  <span className={`review-auto-badge ${detail.automatic_validation?.valid ? "valid" : "unknown"}`}>{detail.automatic_validation?.valid ? "基准契约验证通过" : "基准契约待检查"}</span>
                  <span className={`review-auto-badge runtime-${detail.runtime_acceptance?.status || "unverified"}`}>
                    {detail.runtime_acceptance?.status === "passed" ? `Agent 实跑 ${detail.runtime_acceptance.passed}/${detail.runtime_acceptance.runs}` : detail.runtime_acceptance?.status === "failed" ? `Agent 实跑失败 ${detail.runtime_acceptance.failed}` : "Agent 实跑未验证"}
                  </span>
                </div>
              </header>

              <article className="review-instruction-card">
                <h2>编辑指令</h2>
                {detail.task.instruction.zh && <p>{detail.task.instruction.zh}</p>}
                <p className={detail.task.instruction.zh ? "secondary" : ""}>{detail.task.instruction.en}</p>
                <div className="review-score-meta">
                  <span>{detail.score_summary.title}</span>
                  <span>调号 {detail.score_summary.key} → {detail.expected_score_summary.key}</span>
                  <span>拍号 {detail.score_summary.meter} → {detail.expected_score_summary.meter}</span>
                  <span>事件 {detail.score_summary.event_count} → {detail.expected_score_summary.event_count}</span>
                </div>
              </article>

              {currentStandard && (
                <section className={`review-current-standard ${expectedRefusal ? "refuse" : "success"}`} aria-label="本题合格条件">
                  <header><div><span>本编号标准</span><strong>{currentStandard.range} · {currentStandard.name}</strong></div><b>{currentStandard.expected}</b></header>
                  <p>{currentStandard.standard} {currentStandard.protected}</p>
                  <div><strong>本题确定性合格条件</strong><ul>{(detail.task.expected_constraints || []).map((constraint: Record<string, any>, index: number) => <li key={`${constraint.type}-${index}`}>{describeConstraint(constraint)}</li>)}</ul></div>
                  {expectedRefusal && <p className="review-refusal-explainer"><strong>判读：</strong>本题不是要求生成修改后的谱；拒绝执行、原谱保持不变、事件级差异为 0，才算通过。这里展示的是 Gold 预期，不是模型超时、空响应或返回失败。</p>}
                </section>
              )}

              <section className="review-scope-grid">
                <div><span>目标范围</span><strong>{formatScope(detail.task.target_scope)}</strong></div>
                <div><span>保护范围</span><strong>{formatScope(detail.task.protected_scope)}</strong></div>
                <div><span>期望状态</span><strong>{detail.task.expected_status === "refuse" ? "安全拒绝" : "成功执行"}</strong></div>
                <div><span>模型调用</span><strong>无 · 只检查 Gold 基准</strong></div>
              </section>

              {detail.host_notation_guidance && (
                <section className="review-host-notation-explainer" aria-label="MuseScore 力度记号判读">
                  <div>
                    <span>宿主可见记号</span>
                    <strong>事件级修改 {detail.host_notation_guidance.changed_event_ids.length} 处 · MuseScore 新增力度记号 {detail.host_notation_guidance.dynamic_marks_added.length} 个</strong>
                  </div>
                  <p>{detail.host_notation_guidance.explanation_zh}</p>
                  <small>{detail.host_notation_guidance.explanation_en}</small>
                </section>
              )}

              <div className="review-host-actions">
                <div><strong>在专业记谱宿主中检查 Gold 证据</strong><small>这里不运行模型；两份 MusicXML 只是基准定义的只读对照。</small></div>
                <button onClick={() => openArtifact("source")} type="button">打开原始谱</button>
                <button onClick={() => openArtifact("expected")} type="button">{expectedRefusal ? "打开拒绝后原谱（应不变）" : "打开预期谱"}</button>
              </div>

              <div className={`review-host-actions review-runtime-actions ${detail.runtime_acceptance?.status || "unverified"}`}>
                <div>
                  <strong>Sera 实际 Agent 输出</strong>
                  <small>
                    {detail.runtime_acceptance?.status === "passed"
                      ? expectedRefusal
                        ? `${detail.runtime_acceptance.runs} 次均按任务合同安全拒绝，未进入事务应用，乐谱保持原样；这是产品验收，不是 LLM 性能分数。`
                        : `${detail.runtime_acceptance.runs} 次生成、事务、保护范围和 MusicXML 回读均通过；这是产品验收，不是 LLM 性能分数。`
                      : "没有可供人工检查的已通过产品回放；请优先处理此任务。"}
                  </small>
                </div>
                {detail.runtime_acceptance?.status === "passed" && <button onClick={() => openArtifact("runtime_en")} type="button">{expectedRefusal ? "打开 Sera 英文拒绝结果" : "打开 Sera 英文输出"}</button>}
                {detail.runtime_acceptance?.status === "passed" && <button onClick={() => openArtifact("runtime_zh")} type="button">{expectedRefusal ? "打开 Sera 中文拒绝结果" : "打开 Sera 中文输出"}</button>}
              </div>

              <section className="review-diff-section">
                <header><div><h2>事件级差异</h2><p>确定性 ScoreDocument diff，不依赖 LLM 打分。</p></div><strong>{detail.diff.changed_element_count || 0} 处</strong></header>
                {detail.diff_rows.length ? (
                  <div className="review-diff-table-wrap"><table><thead><tr><th>事件</th><th>位置</th><th>修改前</th><th>修改后</th><th>字段</th></tr></thead><tbody>{detail.diff_rows.map((row, index) => <tr key={`${row.kind}-${row.event_id}-${index}`}><td><span className={`review-diff-kind ${row.kind}`}>{row.kind}</span>{row.event_id}</td><td>{row.measure ? `M${row.measure}` : "全局"}</td><td>{conciseEvent(row.before)}</td><td>{conciseEvent(row.after)}</td><td>{row.fields?.join("、") || "—"}</td></tr>)}</tbody></table></div>
                ) : <p className="review-no-diff">{expectedRefusal ? "本任务的正确结果是拒绝执行，因此预期谱与原谱相同；0 处修改即为合格。" : "该任务预期不改变事件级内容。"}</p>}
              </section>

              <details className="review-json-details"><summary>Gold Patch 与确定性约束</summary><div className="review-operation-list">{detail.gold_patch.operations?.map((operation: any) => <article key={operation.operation_id}><strong>{operation.type}</strong><span>{operation.operation_id}</span><code>{JSON.stringify(operation.selector)}</code><code>{JSON.stringify(operation.arguments)}</code></article>) || <p>该任务预期拒绝，不包含 Gold Patch 操作。</p>}</div><pre>{JSON.stringify(detail.task.expected_constraints || [], null, 2)}</pre></details>
              <footer className="review-fingerprint">任务指纹 <code>{detail.task_fingerprint}</code></footer>
            </>
          )}
        </section>

        <aside className="review-form-panel">
          <header><span className="review-eyebrow">人工判定</span><h2>复核记录</h2><p>判断“是否满足明确定义的任务”，不要评价生成模型品牌。</p></header>
          <label>复核人代号<input onChange={(event) => setReviewerId(event.target.value)} value={reviewerId} /></label>
          <div className="review-role-switch" role="radiogroup" aria-label="复核角色">
            <button aria-checked={reviewerRole === "primary"} className={reviewerRole === "primary" ? "selected" : ""} onClick={() => setReviewerRole("primary")} role="radio" type="button">主复核</button>
            <button aria-checked={reviewerRole === "secondary"} className={reviewerRole === "secondary" ? "selected" : ""} onClick={() => setReviewerRole("secondary")} role="radio" type="button">二次抽查</button>
          </div>
          <fieldset className="review-decision-fieldset"><legend>结论</legend>{DECISION_LABELS.map(([value, label, description]) => <button className={decision === value ? `selected ${value}` : ""} key={value} onClick={() => setDecision(value)} type="button"><span>{label}</span><small>{description}</small></button>)}</fieldset>
          <section className="review-ratings"><h3>四维评分</h3>{DIMENSIONS.map(([key, label]) => <RatingRow key={key} label={label} onChange={(value) => setDimensions((current) => ({ ...current, [key]: value }))} value={dimensions[key]} />)}</section>
          <fieldset className="review-issues" disabled={decision === "compliant"}><legend>问题类型</legend>{ISSUE_LABELS.map(([code, label]) => <label key={code}><input checked={issueCodes.includes(code)} onChange={() => toggleIssue(code)} type="checkbox" />{label}</label>)}</fieldset>
          <label>复核说明<textarea onChange={(event) => setNotes(event.target.value)} placeholder="记录宿主检查结果、问题位置或修订建议" rows={5} value={notes} /></label>
          <button className="review-save-button" disabled={!detail || saving} onClick={handleSave} type="button">{saving ? "正在保存…" : "保存并进入下一条"}</button>
          <small className="review-save-boundary">记录追加保存到本机，不会自动改写 benchmark，也不会自动训练模型。</small>
        </aside>
      </main>
    </div>
  );
}
