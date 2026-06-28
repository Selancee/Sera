import { useCallback, useEffect, useMemo, useState } from "react";
import {
  evaluateRun,
  generateScore,
  generateSymbolicModelSample,
  getSymbolicModelStatus,
  listExperiments,
  reviseScore,
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

const DEFAULT_PROMPT =
  "Compose a 16 measure romantic piano nocturne with a clear melody and flowing left hand.";

const DEFAULT_PARAMS = {
  style: "romantic",
  instrument: "piano",
  key: "A minor",
  meter: "4/4",
  tempo: 84,
  length: 16,
  difficulty: "intermediate"
};

const MAIN_TABS = ["Score", "Plan", "Validation", "Evaluation", "Model"];

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
  const [feedback, setFeedback] = useState("更忧郁，左手更流动。");
  const [modelPrompt, setModelPrompt] = useState(DEFAULT_PROMPT);
  const [modelStatus, setModelStatus] = useState(null);
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
      const payload = await getSymbolicModelStatus();
      setModelStatus(payload);
    } catch (err) {
      setModelStatus({
        available: false,
        mode: "unavailable",
        warnings: [err.message]
      });
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
      const payload = await generateScore(promptWithParams(prompt, params));
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
      modelSample={modelSample}
      modelStatus={modelStatus}
      onGenerateSample={handleModelSample}
      prompt={modelPrompt}
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
            <p>Research workbench V0.2</p>
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
          {activeTab === "Score" && (
            <>
              <ScoreViewer measures={measures} result={result} />
              <MidiPlayer measures={measures} tempo={result?.intent?.tempo_bpm || 96} />
              <ValidationReportPanel result={result} />
            </>
          )}
          {activeTab === "Validation" && <ValidationReportPanel detailed result={result} />}
          {activeTab === "Evaluation" && (
            <div className="evaluation-grid">
              {Object.entries(evaluation).map(([key, value]) => (
                <div className="metric-tile" key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{Array.isArray(value) ? value.length : String(value)}</strong>
                </div>
              ))}
            </div>
          )}
          {activeTab === "Model" && modelPanel}
          {!result && activeTab !== "Model" && (
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
