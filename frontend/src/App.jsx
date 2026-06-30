import { useCallback, useEffect, useMemo, useState } from "react";
import {
  evaluateRun,
  generateScore,
  generateSymbolicModelSample,
  getSymbolicModelRegistry,
  getSymbolicModelStatus,
  listExperiments,
  reviseScore,
  selectSymbolicModel,
  submitRating
} from "./api.js";
import AgentPlanPanel from "./components/AgentPlanPanel.jsx";
import ExperimentLogPanel from "./components/ExperimentLogPanel.jsx";
import ExportPanel from "./components/ExportPanel.jsx";
import HumanEvaluationPanel from "./components/HumanEvaluationPanel.jsx";
import MidiPlayer from "./components/MidiPlayer.jsx";
import PromptInput from "./components/PromptInput.jsx";
import ScoreViewer from "./components/ScoreViewer.jsx";
import SymbolicModelPanel from "./components/SymbolicModelPanel.jsx";
import ValidationReportPanel from "./components/ValidationReportPanel.jsx";
import ScoreWorkbench from "./workbench/ScoreWorkbench";

const DEFAULT_PROMPT =
  "Compose a 16 measure romantic piano nocturne with a clear melody and flowing left hand.";

const DEFAULT_PARAMS = {
  style: "romantic",
  instrument: "piano",
  key: "A minor",
  meter: "4/4",
  tempo: 84,
  length: 16,
  difficulty: "intermediate",
  generator_mode: "hybrid_v05",
  model_task_type: "melody_fragment"
};

const MAIN_TABS = ["Score", "Workbench", "Plan", "Validation", "Evaluation", "Model"];

function promptWithParams(prompt, params) {
  return [
    prompt.trim(),
    `Parameters: ${params.style} style, ${params.instrument}, ${params.key}, ${params.meter}, ${params.tempo} bpm, ${params.length} measures, ${params.difficulty} difficulty.`
  ].join("\n");
}

export default function App() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [result, setResult] = useState(null);
  const [experiments, setExperiments] = useState([]);
  const [feedback, setFeedback] = useState("Make the cadence clearer and add more rhythmic contrast.");
  const [modelPrompt, setModelPrompt] = useState(DEFAULT_PROMPT);
  const [modelStatus, setModelStatus] = useState(null);
  const [modelRegistry, setModelRegistry] = useState({ models: [] });
  const [modelSample, setModelSample] = useState(null);
  const [status, setStatus] = useState("ready");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("Score");

  const runId = result?.run_id || "";
  const measures = useMemo(() => result?.plan?.measures || [], [result]);
  const evaluation = useMemo(() => result?.evaluation || {}, [result]);

  const refreshExperiments = useCallback(async () => {
    try {
      const payload = await listExperiments();
      setExperiments(payload.records || []);
    } catch {
      setExperiments([]);
    }
  }, []);

  const refreshModelStatus = useCallback(async () => {
    try {
      const [statusPayload, registryPayload] = await Promise.all([
        getSymbolicModelStatus(),
        getSymbolicModelRegistry()
      ]);
      setModelStatus(statusPayload);
      setModelRegistry(registryPayload);
    } catch (err) {
      setModelStatus({
        available: false,
        mode: "unavailable",
        warnings: [err.message]
      });
      setModelRegistry({ models: [] });
    }
  }, []);

  useEffect(() => {
    refreshExperiments();
    refreshModelStatus();
  }, [refreshExperiments, refreshModelStatus]);

  const handleGenerate = useCallback(async () => {
    setStatus("generating");
    setError("");
    try {
      const payload = await generateScore(promptWithParams(prompt, params), {
        generator_mode: params.generator_mode,
        model_task_type: params.model_task_type
      });
      setResult(payload);
      setActiveTab("Score");
      await refreshExperiments();
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, [params, prompt, refreshExperiments]);

  const handleRevise = useCallback(async () => {
    if (!runId) return;
    setStatus("revising");
    setError("");
    try {
      const payload = await reviseScore(runId, feedback);
      setResult(payload);
      setActiveTab("Plan");
      await refreshExperiments();
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, [feedback, refreshExperiments, runId]);

  const handleEvaluate = useCallback(async () => {
    if (!runId) return;
    setStatus("evaluating");
    setError("");
    try {
      const metrics = await evaluateRun(runId);
      setResult((current) => (current ? { ...current, evaluation: metrics } : current));
      setActiveTab("Evaluation");
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, [runId]);

  const handleModelSample = useCallback(async () => {
    setStatus("modeling");
    setError("");
    try {
      const payload = await generateSymbolicModelSample(modelPrompt, 96);
      setModelSample(payload);
      setModelStatus(payload.status || modelStatus);
      setActiveTab("Model");
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, [modelPrompt, modelStatus]);

  const handleSelectModel = useCallback(async (modelName) => {
    if (!modelName) return;
    setStatus("modeling");
    setError("");
    try {
      const payload = await selectSymbolicModel(modelName, true);
      setModelStatus(payload);
      setModelRegistry({
        active_model: payload.active_model,
        expected_model_dir: payload.expected_model_dir,
        models: payload.known_models || []
      });
      setModelSample(null);
      setActiveTab("Model");
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, []);

  const handleRating = useCallback(
    async (rating) => {
      if (!runId) return;
      setError("");
      try {
        const payload = await submitRating(runId, rating);
        setResult(payload);
        await refreshExperiments();
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [refreshExperiments, runId]
  );

  const modelPanel = (
    <SymbolicModelPanel
      disabled={status === "modeling"}
      modelRegistry={modelRegistry}
      modelSample={modelSample}
      modelStatus={modelStatus}
      onGenerateSample={handleModelSample}
      onSelectModel={handleSelectModel}
      prompt={modelPrompt}
      selectingModel={status === "modeling"}
      setPrompt={setModelPrompt}
    />
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            S
          </div>
          <div>
            <h1>Sera - Agentic Text-to-Score Composition System</h1>
            <p>Score Workbench V0.6</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Main views">
          {MAIN_TABS.map((tab) => (
            <button
              className={activeTab === tab ? "tab active" : "tab"}
              key={tab}
              onClick={() => setActiveTab(tab)}
              type="button"
            >
              {tab}
            </button>
          ))}
        </nav>
        <div className={`status-chip ${status}`}>{status}</div>
      </header>

      <main className="workspace">
        <aside className="left-rail">
          <PromptInput
            disabled={status === "generating"}
            onGenerate={handleGenerate}
            params={params}
            prompt={prompt}
            setParams={setParams}
            setPrompt={setPrompt}
          />
          <ExperimentLogPanel experiments={experiments} selectedRunId={runId} />
        </aside>

        <section className="score-stage" aria-label="Score workspace">
          {activeTab === "Plan" && <AgentPlanPanel result={result} />}
          {activeTab === "Workbench" && <ScoreWorkbench result={result} />}
          {activeTab === "Score" && (
            <>
              <ScoreViewer measures={measures} result={result} />
              <MidiPlayer measures={measures} tempo={result?.intent?.tempo_bpm || 96} />
              <ValidationReportPanel result={result} />
            </>
          )}
          {activeTab === "Validation" && <ValidationReportPanel detailed result={result} />}
          {activeTab === "Evaluation" && (
            <>
              <ResearchModePanel result={result} />
              <div className="evaluation-grid">
                {Object.entries(evaluation).map(([key, value]) => (
                  <div className="metric-tile" key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>{Array.isArray(value) ? value.length : String(value)}</strong>
                  </div>
                ))}
              </div>
            </>
          )}
          {activeTab === "Model" && modelPanel}
          {!result && activeTab !== "Model" && activeTab !== "Workbench" && (
            <div className="empty-state">
              <strong>Ready for first generation</strong>
              <span>Run the prompt to create MusicXML, MIDI, ABC, PDF, and an experiment log.</span>
            </div>
          )}
          {error && <div className="error-banner">{error}</div>}
        </section>

        <aside className="right-inspector">
          <AgentPlanPanel compact result={result} />
          <ExportPanel onEvaluate={handleEvaluate} result={result} />
          <HumanEvaluationPanel
            disabled={status === "generating" || status === "revising"}
            onSubmit={handleRating}
            result={result}
          />
          <div className="panel">
            <label htmlFor="feedback">Revision</label>
            <textarea
              id="feedback"
              rows="4"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
            />
            <button className="secondary-action" disabled={!runId} onClick={handleRevise} type="button">
              Revise
            </button>
          </div>
        </aside>
      </main>
    </div>
  );
}

function ResearchModePanel({ result }) {
  const generation = result?.generation || {};
  const metadata = result?.metadata || {};
  const decoding = metadata.decoding || generation.decoding || {};
  const postprocess = metadata.postprocess_report || generation.postprocess_report || {};
  const evaluation = result?.evaluation || {};
  const postprocessRows = [
    ["fixed consecutive quarters", postprocess.fixed_consecutive_quarters],
    ["added leap", postprocess.added_leap],
    ["added cadence", postprocess.added_cadence],
    ["filled measure", postprocess.filled_measure],
    ["fixed pitch range", postprocess.fixed_pitch_range]
  ];
  const metricRows = [
    ["rhythmic diversity", evaluation.rhythmic_diversity_score],
    ["quarter-note dominance", evaluation.quarter_note_dominance_score],
    ["interval variety", evaluation.melodic_interval_variety_score],
    ["cadence presence", evaluation.cadence_presence_score],
    ["overall musicality proxy score", evaluation.overall_musicality_proxy_score]
  ];
  return (
    <section className="panel research-panel">
      <div className="panel-heading">
        <h2>Research Mode</h2>
        <span>{metadata.generator_mode || generation.generator_mode || "pending"}</span>
      </div>
      <div className="research-grid">
        <div className="intent-item">
          <span>generator mode</span>
          <strong>{metadata.generator_mode || generation.generator_mode || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>model task type</span>
          <strong>{metadata.model_task_type || generation.model_task_type || "melody_fragment"}</strong>
        </div>
        {["temperature", "top_p", "top_k", "repetition_penalty"].map((key) => (
          <div className="intent-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{decoding[key] ?? "-"}</strong>
          </div>
        ))}
      </div>
      <div className="research-grid">
        {postprocessRows.map(([label, value]) => (
          <div className="intent-item" key={label}>
            <span>{label}</span>
            <strong>{value ? "yes" : "no"}</strong>
          </div>
        ))}
      </div>
      <div className="research-grid">
        {metricRows.map(([label, value]) => (
          <div className="intent-item" key={label}>
            <span>{label}</span>
            <strong>{value ?? "-"}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
