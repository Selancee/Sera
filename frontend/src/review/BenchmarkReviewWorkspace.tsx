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
  expected: "Successful edit" | "Safe refusal";
  standard: string;
  protected: string;
};

const TASK_STANDARDS: TaskStandard[] = [
  {
    prefix: "pitch",
    range: "pitch_001–015",
    name: "Pitch transposition",
    expected: "Successful edit",
    standard: "Transpose the specified events by exactly the requested number of semitones.",
    protected: "Preserve note durations, events outside the target, and protected staves."
  },
  {
    prefix: "rhythm",
    range: "rhythm_001–015",
    name: "Rhythm and duration",
    expected: "Successful edit",
    standard: "Merge the first two specified rhythmic units: extend the first event and delete the second.",
    protected: "Preserve subsequent pitches, events outside the target, and total measure duration."
  },
  {
    prefix: "key",
    range: "key_001–015",
    name: "Key signature",
    expected: "Successful edit",
    standard: "Change only the key signature to the requested key.",
    protected: "Do not transpose existing pitches with the key signature; preserve all other notation."
  },
  {
    prefix: "voice",
    range: "voice_001–015",
    name: "Voices and texture",
    expected: "Successful edit",
    standard: "Move target events in the specified measures and staff from voice 1 to voice 2.",
    protected: "Preserve pitches, rhythm, event counts, and voices outside the target."
  },
  {
    prefix: "dynamics",
    range: "dynamics_001–010",
    name: "Dynamics and articulation",
    expected: "Successful edit",
    standard: "Set only the specified notes to f or staccato, as required by this task.",
    protected: "Preserve target pitches and durations; do not add marks to other notes."
  },
  {
    prefix: "insertion",
    range: "insertion_001–010",
    name: "Replacement, insertion, and deletion",
    expected: "Successful edit",
    standard: "Delete the specified event and insert the requested F♯4 or C major chord at the same position.",
    protected: "Match the requested duration and position while preserving other events and measure structure."
  },
  {
    prefix: "ties",
    range: "ties_001–010",
    name: "Slurs",
    expected: "Successful edit",
    standard: "Add a complete slur from the first to the last target note in the specified measure.",
    protected: "Use a slur, not a tie. Preserve pitches, durations, and relations outside the target."
  },
  {
    prefix: "meter",
    range: "meter_001–010",
    name: "Meter and measure structure",
    expected: "Successful edit",
    standard: "For meter_001, change 4/4 to 3/4 and delete the last beat of each measure on each staff. For meter_002–010, change the displayed meter while preserving total duration.",
    protected: "Preserve retained pitches and durations. Do not rebar or regroup beats beyond the deletions specified in meter_001."
  },
  {
    prefix: "compound",
    range: "compound_001–010",
    name: "Compound edits",
    expected: "Successful edit",
    standard: "Raise the last two specified target notes by one semitone and set the last target note to f.",
    protected: "Complete both steps while preserving all durations, other notes, and the protected scope."
  },
  {
    prefix: "conflict",
    range: "conflict_001–010",
    name: "Conflicting or unsupported",
    expected: "Safe refusal",
    standard: "Identify mathematical conflicts or unverifiable aesthetic instructions and explicitly refuse without fabricating an edit.",
    protected: "The correct result is the unchanged source with zero differences. The expected score is a copy of the source after refusal."
  }
];

const DIMENSIONS = [
  ["instruction_clarity", "Instruction clarity"],
  ["scope_correctness", "Scope correctness"],
  ["gold_correctness", "Gold correctness"],
  ["musical_validity", "Musical validity"]
] as const;

const ISSUE_LABELS: Array<[string, string]> = [
  ["instruction_ambiguous", "Ambiguous instruction"],
  ["target_scope_wrong", "Incorrect target scope"],
  ["protected_scope_wrong", "Incorrect protected scope"],
  ["gold_patch_wrong", "Incorrect gold patch"],
  ["expected_output_wrong", "Incorrect expected output"],
  ["refusal_label_wrong", "Incorrect refusal label"],
  ["constraint_wrong", "Incorrect constraint definition"],
  ["musically_implausible", "Musically implausible"],
  ["host_render_issue", "Host rendering issue"],
  ["other", "Other"]
];

const DECISION_LABELS: Array<[Decision, string, string]> = [
  ["compliant", "Compliant", "Task, scope, gold patch, and result are acceptable"],
  ["needs_revision", "Needs revision", "Retain the task, but fix annotation or musical issues"],
  ["exclude", "Exclude", "Exclude this task from the formal core set"]
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
  if (!scope || !Object.keys(scope).length) return "Not specified";
  const labels: string[] = [];
  if (scope.measures?.length) labels.push(`Measures ${scope.measures.join(", ")}`);
  if (scope.parts?.length) labels.push(`Parts ${scope.parts.join(", ")}`);
  if (scope.staffs?.length) labels.push(`Staff ${scope.staffs.join(", ")}`);
  if (scope.voices?.length) labels.push(`Voice ${scope.voices.join(", ")}`);
  if (scope.event_ids?.length) labels.push(`${scope.event_ids.length} events`);
  return labels.join(" · ") || "Whole score / determined by constraints";
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
    meter_duration_conflict: "The meter conflicts with the fixed total duration",
    unsupported_ornament_semantics: "The aesthetic request cannot be mapped to a unique, verifiable notation operation"
  };
  return reasons[reason || ""] || reason || "Refusal required by the task";
}

function describeConstraint(constraint: Record<string, any>) {
  const event = constraint.event_id ? `Event ${constraint.event_id}` : "Specified events";
  const events = constraint.event_ids?.length ? `${constraint.event_ids.length} specified events` : "Specified events";
  switch (constraint.type) {
    case "pitch_delta": return `${events} pitches must be transposed ${constraint.value >= 0 ? "up" : "down"} ${Math.abs(constraint.value)} semitones`;
    case "preserve_duration": return "All retained event durations must match the source";
    case "preserve_pitch": return "Preserve pitches of retained events unless explicitly targeted";
    case "duration_equals": return `${event} duration must equal ${constraint.value}`;
    case "dynamic_equals": return `${event} dynamic must equal ${constraint.value}`;
    case "articulation_equals": return `${event} articulation must equal ${(constraint.value || []).join(", ")}`;
    case "event_deleted": return `${event} must be deleted`;
    case "event_inserted": return `Insert event ${constraint.event_id}${constraint.pitch ? `, pitch ${constraint.pitch}` : ""}`;
    case "chord_pitches": return `Create chord ${(constraint.value || []).join("–")}`;
    case "key_equals": return `Score key signature must equal ${constraint.value}`;
    case "meter_equals": return `Target meter must equal ${constraint.value}`;
    case "slur_equals": return `${event} slur state must equal ${constraint.value}`;
    case "voice_equals": return `${event} must be in voice ${constraint.value}`;
    case "refuse": return `Must safely refuse: ${translateReason(constraint.reason)}`;
    default: return `${constraint.type || "Unknown constraint"} must pass`;
  }
}

function gateCopy(summary: ReviewSummary) {
  const gate = summary.calibration_gate;
  if (gate.status === "not_enough_reviews") {
    return {
      tone: "waiting",
      title: "Collect review evidence first",
      text: `Complete at least ${gate.minimum_reviewed} primary reviews before assessing whether benchmark repair or preference calibration is needed.`
    };
  }
  if (gate.status === "aesthetic_calibration_required") {
    return {
      tone: "alert",
      title: "Preference calibration triggered",
      text: `${Math.round(gate.musical_problem_rate * 100)}% of reviewed tasks have musical issues. Next, collect ${gate.target_pairwise_reviews} blinded A/B preferences to calibrate candidate ranking weights.`
    };
  }
  if (gate.status === "benchmark_repair_required") {
    return {
      tone: "warning",
      title: "Repair the benchmark contract first",
      text: "Noncompliance exceeds the threshold, mainly due to nonmusical issues. Repair instructions, scopes, gold patches, or constraints before preference calibration."
    };
  }
  return {
    tone: "ready",
    title: "Monitoring",
    text: "Current evidence is below the threshold for benchmark repair or preference calibration."
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
      <div aria-label={`${label} rating`} role="radiogroup">
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
        if (!opened.ok) throw new Error(opened.error || "Could not open the local host inspection file.");
        const label = variant === "source" ? "Source" : variant === "expected" ? "Expected" : variant === "runtime_en" ? "Sera English replay" : "Sera Chinese replay";
        setNotice(`${label} MusicXML sent to the associated notation host.`);
      } else {
        await navigator.clipboard?.writeText(artifact.path);
        setNotice(`File prepared; path copied: ${artifact.path}`);
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
      setNotice(`Exported ${exported.record_count} records: ${exported.csv_path}`);
    } catch (caught: any) {
      setError(caught.message);
    }
  }

  async function handleSave() {
    if (!detail || !selectedTaskId || saving) return;
    if (!reviewerId.trim()) {
      setError("Enter a reviewer alias rather than a real name. ");
      return;
    }
    if (decision !== "compliant" && !issueCodes.length) {
      setError("Select at least one issue type for Needs revision or Exclude. ");
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
      setNotice(`${selectedTaskId} saved; the original benchmark files are unchanged.`);
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
          <div><strong>SeraEdit Research review</strong><small>Gold benchmark evidence · No LLM calls on this page</small></div>
        </div>
        <div className="review-topbar-actions">
          <button aria-expanded={standardsOpen} onClick={() => setStandardsOpen((current) => !current)} type="button">Task ID standards</button>
          <button onClick={handleExport} type="button">Export review records</button>
          <button className="primary" onClick={onClose} type="button">Back to Agent</button>
        </div>
      </header>

      {standardsOpen && (
        <section className="review-standards-panel" aria-label="Task ID standards reference">
          <header>
            <div><span className="review-eyebrow">How to read</span><h2>Task ID standards reference</h2></div>
            <p><strong>Numbers after the underscore are task sequence numbers</strong>. They do not represent measures, difficulty, or edit counts. Use the bilingual instructions, target scope, and deterministic constraints as the task criteria.</p>
          </header>
          <div className="review-standards-table-wrap">
            <table>
              <thead><tr><th>Task ID</th><th>Category</th><th>Expected</th><th>Required outcome</th><th>Must preserve</th></tr></thead>
              <tbody>{TASK_STANDARDS.map((item) => (
                <tr key={item.prefix}><td><code>{item.range}</code></td><td>{item.name}</td><td><span className={item.expected === "Safe refusal" ? "refuse" : "success"}>{item.expected}</span></td><td>{item.standard}</td><td>{item.protected}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      {summary && (
        <section className="review-summary-strip" aria-label="Review progress">
          <div><strong>{summary.primary_reviewed}/{summary.total}</strong><span>Primary review</span></div>
          <div><strong>{summary.secondary_reviewed}/{summary.secondary_target}</strong><span>Secondary review</span></div>
          <div><strong>{Math.round(summary.completion_rate * 100)}%</strong><span>Completion</span></div>
          <div><strong>{Math.round(summary.noncompliance_rate * 100)}%</strong><span>Noncompliance</span></div>
          <div className={summary.runtime_acceptance?.tasks_failed ? "runtime-failed" : "runtime-passed"}>
            <strong>{summary.runtime_acceptance?.tasks_passed || 0}/{summary.total}</strong>
            <span>Agent runs · {summary.runtime_acceptance?.runs || 0} runs</span>
          </div>
          <button className={`review-gate ${gate?.tone}`} onClick={() => setCalibrationOpen((current) => !current)} type="button">
            <span>{gate?.title}</span><small>{gate?.text}</small>
          </button>
        </section>
      )}

      {calibrationOpen && summary && (
        <section className="review-calibration-panel">
          <div>
            <span className="review-eyebrow">Conditional preference calibration</span>
            <h2>{summary.calibration_gate.aesthetic_calibration_required ? "Start blinded preference calibration" : "Calibration not currently needed"}</h2>
            <p>{gate?.text}</p>
          </div>
          <ol>
            <li>Sample candidates only from categories marked as musically implausible.</li>
            <li>Have reviewers complete {summary.calibration_gate.target_pairwise_reviews} A/B comparisons with generator identities hidden.</li>
            <li>Calibrate ranking weights for melody, harmony, voice leading, rhythm, texture, style, and playability.</li>
            <li>Regenerate failed categories and repeat structure, protected scope, playability, and human review checks.</li>
          </ol>
          <p className="review-boundary">Preferences calibrate Sera candidate ranking only. They do not establish universal aesthetic quality or replace validation.</p>
        </section>
      )}

      {summary && summary.stale_records > 0 && (
        <div className="review-notice error" role="status">
          Retained {summary.stale_records} audit records from older versions. Their tasks have changed, so they are excluded from current progress. Please review these tasks again.
        </div>
      )}

      {(notice || error) && <div className={`review-notice ${error ? "error" : "success"}`} role="status">{error || notice}</div>}

      <main className="review-workspace-grid">
        <aside className="review-task-rail">
          <div className="review-filter-stack">
            <label>Search<input onChange={(event) => setSearch(event.target.value)} placeholder="Task, category, or instruction" value={search} /></label>
            <div>
              <label>Category<select onChange={(event) => setCategory(event.target.value)} value={category}><option value="">All categories</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label>Status<select onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}><option value="">All statuses</option><option value="pending">Pending review</option><option value="compliant">Compliant</option><option value="needs_revision">Needs revision</option><option value="exclude">Exclude</option></select></label>
              <label>Agent runtime<select onChange={(event) => setRuntimeFilter(event.target.value)} value={runtimeFilter}><option value="">All runtime statuses</option><option value="failed">Failed only</option><option value="unverified">Unverified only</option><option value="passed">Passed only</option></select></label>
            </div>
          </div>
          <div className="review-task-count">{tasks.length} tasks</div>
          <div className="review-task-list" aria-label="Benchmark task list">
            {tasks.map((task) => (
              <button className={task.task_id === selectedTaskId ? "selected" : ""} key={task.task_id} onClick={() => setSelectedTaskId(task.task_id)} type="button">
                <span className={`review-status-dot ${task.review_status}`} aria-hidden="true" />
                <span><strong>{task.task_id}</strong><small>{task.category} · {task.difficulty}</small><em>{task.instruction.en || task.instruction.zh}</em></span>
                <span className="review-task-evidence-badges">
                  {task.runtime_acceptance?.status === "passed" && <b className="runtime-pass" title={`${task.runtime_acceptance.runs} agent runs passed`}>✓</b>}
                  {task.runtime_acceptance?.status === "failed" && <b className="runtime-fail" title="Agent runtime failed">!</b>}
                  {task.secondary_review && <b title="Secondary review complete">2</b>}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="review-evidence-panel" aria-label="Review evidence">
          {!detail ? <div className="review-empty">{loading ? "Loading task evidence…" : "No tasks match these filters."}</div> : (
            <>
              <header className="review-task-header">
                <div><span className="review-eyebrow">{detail.task.category} · {detail.task.difficulty}</span><h1>{detail.task.task_id}</h1></div>
                <div className="review-header-badges">
                  <span className={`review-auto-badge ${detail.automatic_validation?.valid ? "valid" : "unknown"}`}>{detail.automatic_validation?.valid ? "Benchmark contract validated" : "Benchmark contract needs checking"}</span>
                  <span className={`review-auto-badge runtime-${detail.runtime_acceptance?.status || "unverified"}`}>
                    {detail.runtime_acceptance?.status === "passed" ? `Agent runtime ${detail.runtime_acceptance.passed}/${detail.runtime_acceptance.runs}` : detail.runtime_acceptance?.status === "failed" ? `Agent runtime failed ${detail.runtime_acceptance.failed}` : "Agent runtime unverified"}
                  </span>
                </div>
              </header>

              <article className="review-instruction-card">
                <h2>Edit instruction</h2>
                <p>{detail.task.instruction.en || detail.task.instruction.zh}</p>
                {detail.task.instruction.en && detail.task.instruction.zh && (
                  <details><summary>Original Chinese instruction</summary><p lang="zh-CN">{detail.task.instruction.zh}</p></details>
                )}
                <div className="review-score-meta">
                  <span>{detail.score_summary.title}</span>
                  <span>Key signature {detail.score_summary.key} → {detail.expected_score_summary.key}</span>
                  <span>Meter {detail.score_summary.meter} → {detail.expected_score_summary.meter}</span>
                  <span>Event {detail.score_summary.event_count} → {detail.expected_score_summary.event_count}</span>
                </div>
              </article>

              {currentStandard && (
                <section className={`review-current-standard ${expectedRefusal ? "refuse" : "success"}`} aria-label="Task acceptance criteria">
                  <header><div><span>Task ID standard</span><strong>{currentStandard.range} · {currentStandard.name}</strong></div><b>{currentStandard.expected}</b></header>
                  <p>{currentStandard.standard} {currentStandard.protected}</p>
                  <div><strong>Deterministic acceptance criteria</strong><ul>{(detail.task.expected_constraints || []).map((constraint: Record<string, any>, index: number) => <li key={`${constraint.type}-${index}`}>{describeConstraint(constraint)}</li>)}</ul></div>
                  {expectedRefusal && <p className="review-refusal-explainer"><strong>Interpretation: </strong>This task passes only when the edit is refused, the source score is unchanged, and the event diff is zero. This is the gold expected outcome; it is not a timeout, empty response, or provider failure.</p>}
                </section>
              )}

              <section className="review-scope-grid">
                <div><span>Target scope</span><strong>{formatScope(detail.task.target_scope)}</strong></div>
                <div><span>Protected scope</span><strong>{formatScope(detail.task.protected_scope)}</strong></div>
                <div><span>Expected status</span><strong>{detail.task.expected_status === "refuse" ? "Safe refusal" : "Successful edit"}</strong></div>
                <div><span>Model calls</span><strong>None · Gold benchmark review only</strong></div>
              </section>

              {detail.host_notation_guidance && (
                <section className="review-host-notation-explainer" aria-label="Interpreting MuseScore dynamic marks">
                  <div>
                    <span>Marks visible in the host</span>
                    <strong>Event changes {detail.host_notation_guidance.changed_event_ids.length} · New MuseScore dynamic marks {detail.host_notation_guidance.dynamic_marks_added.length} marks</strong>
                  </div>
                  <p>{detail.host_notation_guidance.explanation_en}</p>
                  <details><summary>Original Chinese explanation</summary><p lang="zh-CN">{detail.host_notation_guidance.explanation_zh}</p></details>
                </section>
              )}

              <div className="review-host-actions">
                <div><strong>Inspect gold evidence in your notation host</strong><small>No model is run here. The two MusicXML files are read-only benchmark comparisons.</small></div>
                <button onClick={() => openArtifact("source")} type="button">Open source score</button>
                <button onClick={() => openArtifact("expected")} type="button">{expectedRefusal ? "Open refused score (unchanged)" : "Open expected score"}</button>
              </div>

              <div className={`review-host-actions review-runtime-actions ${detail.runtime_acceptance?.status || "unverified"}`}>
                <div>
                  <strong>Actual Sera agent output</strong>
                  <small>
                    {detail.runtime_acceptance?.status === "passed"
                      ? expectedRefusal
                        ? `${detail.runtime_acceptance.runs} runs safely refused as required, without applying a transaction or changing the score. This verifies product behavior, not LLM performance.`
                        : `${detail.runtime_acceptance.runs} runs passed generation, transaction, protected scope, and MusicXML round-trip checks. This verifies product behavior, not LLM performance.`
                      : "No passing product replay is available for inspection. Prioritize this task."}
                  </small>
                </div>
                {detail.runtime_acceptance?.status === "passed" && <button onClick={() => openArtifact("runtime_en")} type="button">{expectedRefusal ? "Open Sera English refusal" : "Open Sera English output"}</button>}
                {detail.runtime_acceptance?.status === "passed" && <button onClick={() => openArtifact("runtime_zh")} type="button">{expectedRefusal ? "Open Sera Chinese refusal" : "Open Sera Chinese output"}</button>}
              </div>

              <section className="review-diff-section">
                <header><div><h2>Event diff</h2><p>Deterministic ScoreDocument diff, without LLM scoring.</p></div><strong>{detail.diff.changed_element_count || 0} changes</strong></header>
                {detail.diff_rows.length ? (
                  <div className="review-diff-table-wrap"><table><thead><tr><th>Event</th><th>Position</th><th>Before</th><th>After</th><th>Fields</th></tr></thead><tbody>{detail.diff_rows.map((row, index) => <tr key={`${row.kind}-${row.event_id}-${index}`}><td><span className={`review-diff-kind ${row.kind}`}>{row.kind}</span>{row.event_id}</td><td>{row.measure ? `M${row.measure}` : "Global"}</td><td>{conciseEvent(row.before)}</td><td>{conciseEvent(row.after)}</td><td>{row.fields?.join(", ") || "—"}</td></tr>)}</tbody></table></div>
                ) : <p className="review-no-diff">{expectedRefusal ? "The correct outcome is refusal, so the expected and source scores are identical. Zero changes is a pass." : "This task expects no event changes."}</p>}
              </section>

              <details className="review-json-details"><summary>Gold patch and deterministic constraints</summary><div className="review-operation-list">{detail.gold_patch.operations?.map((operation: any) => <article key={operation.operation_id}><strong>{operation.type}</strong><span>{operation.operation_id}</span><code>{JSON.stringify(operation.selector)}</code><code>{JSON.stringify(operation.arguments)}</code></article>) || <p>This task expects refusal and has no gold patch operations.</p>}</div><pre>{JSON.stringify(detail.task.expected_constraints || [], null, 2)}</pre></details>
              <footer className="review-fingerprint">Task fingerprint <code>{detail.task_fingerprint}</code></footer>
            </>
          )}
        </section>

        <aside className="review-form-panel">
          <header><span className="review-eyebrow">Human assessment</span><h2>Review record</h2><p>Assess whether the defined task is satisfied, without considering the model brand.</p></header>
          <label>Reviewer alias<input onChange={(event) => setReviewerId(event.target.value)} value={reviewerId} /></label>
          <div className="review-role-switch" role="radiogroup" aria-label="Review role">
            <button aria-checked={reviewerRole === "primary"} className={reviewerRole === "primary" ? "selected" : ""} onClick={() => setReviewerRole("primary")} role="radio" type="button">Primary review</button>
            <button aria-checked={reviewerRole === "secondary"} className={reviewerRole === "secondary" ? "selected" : ""} onClick={() => setReviewerRole("secondary")} role="radio" type="button">Secondary review</button>
          </div>
          <fieldset className="review-decision-fieldset"><legend>Decision</legend>{DECISION_LABELS.map(([value, label, description]) => <button className={decision === value ? `selected ${value}` : ""} key={value} onClick={() => setDecision(value)} type="button"><span>{label}</span><small>{description}</small></button>)}</fieldset>
          <section className="review-ratings"><h3>Four review dimensions</h3>{DIMENSIONS.map(([key, label]) => <RatingRow key={key} label={label} onChange={(value) => setDimensions((current) => ({ ...current, [key]: value }))} value={dimensions[key]} />)}</section>
          <fieldset className="review-issues" disabled={decision === "compliant"}><legend>Issue types</legend>{ISSUE_LABELS.map(([code, label]) => <label key={code}><input checked={issueCodes.includes(code)} onChange={() => toggleIssue(code)} type="checkbox" />{label}</label>)}</fieldset>
          <label>Review notes<textarea onChange={(event) => setNotes(event.target.value)} placeholder="Record host inspection results, issue locations, or suggested revisions" rows={5} value={notes} /></label>
          <button className="review-save-button" disabled={!detail || saving} onClick={handleSave} type="button">{saving ? "Saving…" : "Save and continue"}</button>
          <small className="review-save-boundary">Records are appended locally. Saving does not modify the benchmark or train a model.</small>
        </aside>
      </main>
    </div>
  );
}
