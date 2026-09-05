import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BenchmarkReviewWorkspace from "../BenchmarkReviewWorkspace";

const api = vi.hoisted(() => ({
  exportBenchmarkReviews: vi.fn(),
  getBenchmarkReviewSummary: vi.fn(),
  getBenchmarkReviewTask: vi.fn(),
  listBenchmarkReviewTasks: vi.fn(),
  prepareBenchmarkReviewArtifact: vi.fn(),
  submitBenchmarkReview: vi.fn()
}));

const desktop = vi.hoisted(() => ({
  isDesktopRuntime: vi.fn(() => true),
  openDesktopLocalFile: vi.fn()
}));

vi.mock("../../api.js", () => api);
vi.mock("../../desktop/desktopRuntime", () => desktop);

const summary = {
  total: 120,
  primary_reviewed: 20,
  secondary_reviewed: 3,
  secondary_target: 30,
  stale_records: 0,
  remaining: 100,
  completion_rate: 1 / 6,
  decisions: { compliant: 16, needs_revision: 4 },
  noncompliance_rate: 0.2,
  runtime_acceptance: {
    available: true,
    experiment_id: "runtime_acceptance_core_bilingual_r3_v1_20260824",
    tasks_passed: 120,
    tasks_failed: 0,
    runs: 720,
    reproducibility: { rate: 1 }
  },
  calibration_gate: {
    status: "aesthetic_calibration_required",
    minimum_reviewed: 20,
    threshold: 0.2,
    benchmark_repair_required: true,
    aesthetic_calibration_required: true,
    musical_problem_count: 4,
    musical_problem_rate: 0.2,
    target_pairwise_reviews: 24,
    dimensions: ["melodic_coherence"],
    boundary: "Human preferences only calibrate ranking."
  }
};

const task = {
  task_id: "pitch_001",
  score_id: "score_001",
  category: "pitch_transposition",
  difficulty: "easy",
  instruction: { zh: "将第1小节升高大二度。", en: "Transpose measure 1 up a major second." },
  expected_status: "success",
  review_status: "pending",
  automatic_valid: true,
  runtime_acceptance: { status: "passed", runs: 6, passed: 6, failed: 0, languages: ["en", "zh"], repetitions: 3 }
};

const detail = {
  task: {
    ...task,
    target_scope: { measures: [1], staffs: [1] },
    protected_scope: { staffs: [2] },
    expected_constraints: [{ type: "pitch_delta", value: 2 }]
  },
  score_summary: {
    title: "Synthetic fixture",
    key: "C major",
    meter: "4/4",
    measure_count: 2,
    event_count: 16
  },
  expected_score_summary: {
    key: "C major",
    meter: "4/4",
    measure_count: 2,
    event_count: 16
  },
  gold_patch: {
    operations: [{ operation_id: "op_1", type: "transpose", selector: { event_ids: ["m1_rh_1"] }, arguments: { semitones: 2 } }]
  },
  diff: { changed_element_count: 1 },
  diff_rows: [{ kind: "changed", event_id: "m1_rh_1", measure: 1, fields: ["pitch"], before: { pitch: "C4", duration: "quarter" }, after: { pitch: "D4", duration: "quarter" } }],
  automatic_validation: { valid: true },
  runtime_acceptance: { status: "passed", runs: 6, passed: 6, failed: 0, languages: ["en", "zh"], repetitions: 3, host_outputs: { en: true, zh: true } },
  task_fingerprint: "sha256:test"
};

const conflictTask = {
  ...task,
  task_id: "conflict_001",
  category: "conflicting_or_unsupported",
  instruction: {
    zh: "把第1小节改成5/8拍，同时保持所有音符时值且不允许休止符。",
    en: "Change measure 1 to 5/8 while preserving every note duration and leaving no rests."
  },
  expected_status: "refuse"
};

const conflictDetail = {
  ...detail,
  task: {
    ...conflictTask,
    target_scope: { measures: [1], staffs: [1] },
    protected_scope: { staffs: [2] },
    expected_constraints: [{ type: "refuse", reason: "meter_duration_conflict" }]
  },
  gold_patch: { operations: [] },
  diff: { changed_element_count: 0 },
  diff_rows: [],
  task_fingerprint: "sha256:conflict"
};

const dynamicsDetail = {
  ...detail,
  task: {
    ...detail.task,
    task_id: "dynamics_009",
    category: "dynamics_articulation",
    instruction: {
      zh: "只将所选音符改为强奏，并保持音高和时值。",
      en: "Set only the selected note to forte while preserving pitch and duration."
    },
    expected_constraints: [{ type: "dynamic_equals", event_id: "s013_m2_rh_3", value: "f" }]
  },
  host_notation_guidance: {
    kind: "isolated_dynamic_with_restore",
    changed_event_ids: ["s013_m2_rh_3"],
    dynamic_marks_added: [
      { event_id: "s013_m2_rh_3", value: "f" },
      { event_id: "s013_m2_rh_4", value: "mf" }
    ],
    dynamic_marks_removed: [],
    restoration_marks: [{ event_id: "s013_m2_rh_4", value: "mf" }],
    explanation_zh: "MusicXML 力度记号是持续状态。恢复记号不是额外的事件级修改。",
    explanation_en: "MusicXML dynamics are persistent; the reset is not an additional ScoreDocument edit."
  }
};

describe("BenchmarkReviewWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    api.getBenchmarkReviewSummary.mockResolvedValue(summary);
    api.listBenchmarkReviewTasks.mockResolvedValue({ items: [task], categories: ["pitch_transposition"], summary });
    api.getBenchmarkReviewTask.mockResolvedValue(detail);
    api.submitBenchmarkReview.mockResolvedValue({ saved: true, summary });
    api.prepareBenchmarkReviewArtifact.mockResolvedValue({ path: "C:\\Sera\\research_reviews\\workspace\\pitch_001\\source.musicxml" });
    api.exportBenchmarkReviews.mockResolvedValue({ record_count: 1, csv_path: "C:\\Sera\\research_reviews\\reviews.csv" });
    desktop.openDesktopLocalFile.mockResolvedValue({ ok: true });
  });

  it("shows task evidence without rendering or manually editing notation", async () => {
    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);

    expect(await screen.findByText("Event diff")).toBeInTheDocument();
    expect(screen.getByText("Gold benchmark evidence · No LLM calls on this page")).toBeInTheDocument();
    expect(screen.getByText("None · Gold benchmark review only")).toBeInTheDocument();
    expect(screen.getByText("Agent runtime 6/6")).toBeInTheDocument();
    expect(screen.getByText("120/120")).toBeInTheDocument();
    expect(screen.getAllByText("m1_rh_1").length).toBeGreaterThan(0);
    expect(screen.queryByText("音符输入")).not.toBeInTheDocument();
    expect(screen.getByText("Preference calibration triggered")).toBeInTheDocument();
  });

  it("explains every task-code family in English", async () => {
    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);
    await screen.findByText("Event diff");

    fireEvent.click(screen.getByRole("button", { name: "Task ID standards" }));

    expect(screen.getByRole("region", { name: "Task ID standards reference" })).toBeInTheDocument();
    expect(screen.getByText("pitch_001–015")).toBeInTheDocument();
    expect(screen.getByText("meter_001–010")).toBeInTheDocument();
    expect(screen.getByText("conflict_001–010")).toBeInTheDocument();
    expect(screen.getByText(/task sequence numbers/)).toBeInTheDocument();
  });

  it("makes refusal tasks explicit and treats zero score changes as correct", async () => {
    api.listBenchmarkReviewTasks.mockResolvedValue({ items: [conflictTask], categories: ["conflicting_or_unsupported"], summary });
    api.getBenchmarkReviewTask.mockResolvedValue(conflictDetail);

    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);

    expect(await screen.findByText(/This task passes only when the edit is refused/)).toHaveTextContent("it is not a timeout, empty response, or provider failure");
    expect(screen.getByText(/Zero changes is a pass/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open refused score (unchanged)" })).toBeInTheDocument();
    expect(screen.getByText(/6 runs safely refused as required, without applying a transaction/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Sera Chinese refusal" })).toBeInTheDocument();
    expect(screen.getByText("Must safely refuse: The meter conflicts with the fixed total duration")).toBeInTheDocument();
    expect(screen.getByText("Benchmark contract validated")).toBeInTheDocument();
  });

  it("shows concrete before and after values for a global key-signature change", async () => {
    api.getBenchmarkReviewTask.mockResolvedValue({
      ...detail,
      task: {
        ...detail.task,
        task_id: "key_001",
        category: "key_harmony",
        instruction: { zh: "将调号改为 G major。", en: "Change the key signature to G major." }
      },
      score_summary: { ...detail.score_summary, key: "C major" },
      expected_score_summary: { ...detail.expected_score_summary, key: "G major" },
      diff_rows: [{
        kind: "global",
        event_id: "key",
        measure: null,
        fields: ["key"],
        before: { key: "C major" },
        after: { key: "G major" }
      }]
    });

    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);

    expect(await screen.findByText("C major", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("G major", { selector: "td" })).toBeInTheDocument();
  });

  it("explains why an isolated dynamic edit needs a visible reset mark in MuseScore", async () => {
    api.getBenchmarkReviewTask.mockResolvedValue(dynamicsDetail);

    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);

    expect(await screen.findByRole("region", { name: "Interpreting MuseScore dynamic marks" })).toHaveTextContent("Event changes 1");
    expect(screen.getByText(/New MuseScore dynamic marks 2/)).toBeInTheDocument();
    expect(screen.getByText(/the reset is not an additional ScoreDocument edit/)).toBeInTheDocument();
  });

  it("requires an issue for noncompliance and appends a traceable review", async () => {
    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);
    await screen.findByText("Event diff");

    fireEvent.click(screen.getByRole("button", { name: /Needs revision/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    expect(await screen.findByText(/Select at least one issue type/)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Musically implausible"));
    fireEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    await waitFor(() => expect(api.submitBenchmarkReview).toHaveBeenCalledWith(expect.objectContaining({
      task_id: "pitch_001",
      reviewer_id: "reviewer-01",
      decision: "needs_revision",
      issue_codes: ["musically_implausible"]
    })));
    expect(await screen.findByText(/the original benchmark files are unchanged/)).toBeInTheDocument();
  });

  it("prepares a MusicXML artifact and opens it through the desktop bridge", async () => {
    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);
    await screen.findByText("Event diff");

    fireEvent.click(screen.getByRole("button", { name: "Open source score" }));

    await waitFor(() => expect(api.prepareBenchmarkReviewArtifact).toHaveBeenCalledWith("pitch_001", "source"));
    expect(desktop.openDesktopLocalFile).toHaveBeenCalledWith(expect.stringContaining("source.musicxml"));
  });

  it("opens the actual bilingual Sera runtime output for efficient host review", async () => {
    render(<BenchmarkReviewWorkspace onClose={vi.fn()} />);
    await screen.findByText("Event diff");

    fireEvent.click(screen.getByRole("button", { name: "Open Sera Chinese output" }));

    await waitFor(() => expect(api.prepareBenchmarkReviewArtifact).toHaveBeenCalledWith("pitch_001", "runtime_zh"));
    expect(screen.getByText(/6 runs passed generation, transaction, protected scope, and MusicXML round-trip checks/)).toBeInTheDocument();
  });
});
