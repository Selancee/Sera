import { useCallback, useEffect, useMemo, useState } from "react";
import {
  evaluateRun,
  generateScore,
  generateSymbolicModelSample,
  getBackendCapabilities,
  getRendererStatus,
  getSymbolicModelRegistry,
  getSymbolicModelStatus,
  listExperiments,
  reviseScore,
  selectSymbolicModel,
  submitRating
} from "./api.js";
import AgentPlanPanel from "./components/AgentPlanPanel.jsx";
import CandidateMetadataPanel from "./components/CandidateMetadataPanel.jsx";
import ConsistencyReportPanel from "./components/ConsistencyReportPanel.jsx";
import ExperimentLogPanel from "./components/ExperimentLogPanel.jsx";
import ExportPanel from "./components/ExportPanel.jsx";
import HarmonyProfilePanel from "./components/HarmonyProfilePanel.jsx";
import HumanEvaluationPanel from "./components/HumanEvaluationPanel.jsx";
import KeyConsistencyPanel from "./components/KeyConsistencyPanel.jsx";
import MelodyExpectationReportPanel from "./components/MelodyExpectationReportPanel.jsx";
import MelodyLineReportPanel from "./components/MelodyLineReportPanel.jsx";
import MidiPlayer from "./components/MidiPlayer.jsx";
import PromptInput from "./components/PromptInput.jsx";
import PromptConflictPanel from "./components/PromptConflictPanel.jsx";
import ResolvedGenerationRequestPanel from "./components/ResolvedGenerationRequestPanel.jsx";
import RuntimeErrorBoundary from "./components/RuntimeErrorBoundary.jsx";
import ScoreMetadataPanel from "./components/ScoreMetadataPanel.jsx";
import ScoreViewer from "./components/ScoreViewer.jsx";
import SymbolicModelPanel from "./components/SymbolicModelPanel.jsx";
import TrackPlanPanel from "./components/TrackPlanPanel.jsx";
import ValidationReportPanel from "./components/ValidationReportPanel.jsx";
import { resolveBackendBaseUrl } from "./desktop/desktopRuntime";
import SeraAgentConsole from "./agent/SeraAgentConsole";
import BenchmarkReviewWorkspace from "./review/BenchmarkReviewWorkspace";
import { researchReviewEnabled } from "./review/researchReviewMode";
import LanguageSelector from "./i18n/LanguageSelector";
import { formatMusicTerm } from "./i18n/musicTerms";
import { useI18n } from "./i18n/useI18n";
import ScoreWorkbench from "./workbench/ScoreWorkbench";

const DEFAULT_PARAMS = {
  style: "romantic",
  instrument: "piano",
  key: "A minor",
  meter: "4/4",
  tempo: 84,
  length: 16,
  difficulty: "intermediate",
  rhythmic_density: "medium",
  texture: "melody_accompaniment",
  accompaniment_style: "bass_chord",
  cadence_strength: "clear",
  generator_mode: "hybrid_v05",
  model_task_type: "melody_fragment"
};

const DEFAULT_PARAM_SOURCES = Object.fromEntries(Object.keys(DEFAULT_PARAMS).map((key) => [key, "default"]));

const LEGACY_GENERATION_ENABLED = import.meta.env.VITE_SERA_ENABLE_LEGACY_GENERATION === "true";
const RESEARCH_REVIEW_ENABLED = researchReviewEnabled(import.meta.env.VITE_SERA_ENABLE_RESEARCH_REVIEW);

const LEGACY_TABS = [
  ["Score", "mode.score"],
  ["Workbench", "mode.workbench"],
  ["Plan", "mode.plan"],
  ["Validation", "mode.validation"],
  ["Evaluation", "mode.evaluation"],
  ["Model", "mode.model"]
];

const MAIN_TABS = LEGACY_GENERATION_ENABLED ? LEGACY_TABS : [["Workbench", "mode.workbench"]];

function makeVariationSeed() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `sera-${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`;
}

export default function App() {
  const { t } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [paramSources, setParamSources] = useState(DEFAULT_PARAM_SOURCES);
  const [result, setResult] = useState(null);
  const [experiments, setExperiments] = useState([]);
  const [feedback, setFeedback] = useState("Make the cadence clearer and add more rhythmic contrast.");
  const [modelPrompt, setModelPrompt] = useState("");
  const [modelStatus, setModelStatus] = useState(null);
  const [modelRegistry, setModelRegistry] = useState({ models: [] });
  const [modelSample, setModelSample] = useState(null);
  const [rendererStatus, setRendererStatus] = useState(null);
  const [backendCapabilities, setBackendCapabilities] = useState(null);
  const [status, setStatus] = useState("ready");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(LEGACY_GENERATION_ENABLED ? "Score" : "Workbench");
  const [researchReviewOpen, setResearchReviewOpen] = useState(false);

  const runId = result?.run_id || "";
  const evaluation = useMemo(() => result?.evaluation || {}, [result]);
  const midiUrl = result?.midi_url || result?.exports?.midi || "";

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
    if (LEGACY_GENERATION_ENABLED) {
      refreshExperiments();
      refreshModelStatus();
    }
    getBackendCapabilities().then(setBackendCapabilities).catch(() => setBackendCapabilities(null));
    if (LEGACY_GENERATION_ENABLED) {
      getRendererStatus().then(setRendererStatus).catch(() => setRendererStatus(null));
    }
  }, [refreshExperiments, refreshModelStatus]);

  const handleParamChange = useCallback((key, value) => {
    setParams((current) => ({ ...current, [key]: value }));
    setParamSources((current) => ({ ...current, [key]: "explicit" }));
  }, []);

  const handleGenerate = useCallback(async () => {
    setStatus("generating");
    setError("");
    try {
      const variationSeed = makeVariationSeed();
      const trimmedPrompt = prompt.trim();
      const controlOnly = !trimmedPrompt;
      const uiControls = {
        style: params.style,
        instrument: params.instrument,
        key: params.key,
        meter: params.meter,
        tempo: params.tempo,
        length_measures: params.length,
        difficulty: params.difficulty,
        rhythmic_density: params.rhythmic_density,
        texture: params.texture,
        accompaniment_style: params.accompaniment_style,
        cadence_strength: params.cadence_strength
      };
      const payload = await generateScore({
        raw_prompt: trimmedPrompt,
        prompt: trimmedPrompt,
        ui_controls: uiControls,
        ui_control_sources: {
          ...paramSources,
          length_measures: paramSources.length,
          instrument: paramSources.instrument
        },
        control_policy: {
          prompt_priority: true,
          show_conflicts: true,
          allow_ui_defaults: true
        },
        prompt_context: {
          source: "generate_page",
          intent_source: controlOnly ? "control_only_intent" : "prompt_plus_controls",
          language: navigator.language || "unknown"
        },
        generator_mode: params.generator_mode,
        generation_mode: controlOnly ? "control_only_intent" : "prompt_plus_controls",
        candidate_count: 4,
        model_task_type: params.model_task_type,
        musicality_controls: {
          variation_seed: variationSeed
        }
      });
      setResult(payload);
      setActiveTab("Score");
      await refreshExperiments();
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, [paramSources, params, prompt, refreshExperiments]);

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

  const handlePlayMidi = useCallback(() => {
    if (!midiUrl) return;
    const url = /^https?:\/\//i.test(midiUrl) ? midiUrl : `${resolveBackendBaseUrl()}${midiUrl.startsWith("/") ? "" : "/"}${midiUrl}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }, [midiUrl]);

  const handleScoreMetadataChange = useCallback((field, value) => {
    if (!["title", "composer"].includes(field)) return;
    setResult((current) => updateResultMetadata(current, field, value));
  }, []);

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
const renderResetKey = `${activeTab}:${runId || "no-run"}:${status}`;

  if (!LEGACY_GENERATION_ENABLED) {
    return researchReviewOpen
      ? <BenchmarkReviewWorkspace onClose={() => setResearchReviewOpen(false)} />
      : <SeraAgentConsole
          backendCapabilities={backendCapabilities}
          onOpenResearchReview={RESEARCH_REVIEW_ENABLED ? () => setResearchReviewOpen(true) : undefined}
        />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            S
          </div>
          <div>
            <h1>{t("app.title")}</h1>
            <p>{t("app.subtitle")}</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Main views">
          {MAIN_TABS.map(([tab, labelKey]) => (
            <button
              className={activeTab === tab ? "tab active" : "tab"}
              key={tab}
              onClick={() => setActiveTab(tab)}
              type="button"
            >
              {t(labelKey)}
            </button>
          ))}
        </nav>
        <LanguageSelector />
        <div
          className={`runtime-chip ${backendCapabilities?.api_contract ? "ok" : "warning"}`}
          title={backendCapabilities?.api_contract ? `Backend contract: ${backendCapabilities.api_contract}` : "Backend contract unavailable"}
        >
          Backend {backendCapabilities?.api_contract || "unknown"}
        </div>
        <div className={`status-chip ${status}`}>{formatMusicTerm(status, t)}</div>
      </header>

      <main className="workspace">
        <aside className="left-rail">
          {LEGACY_GENERATION_ENABLED ? (
            <>
              <PromptInput
                disabled={status === "generating"}
                onGenerate={handleGenerate}
                onParamChange={handleParamChange}
                params={params}
                prompt={prompt}
                controlOnly={!prompt.trim()}
                setParams={setParams}
                setPrompt={setPrompt}
              />
              <ExperimentLogPanel experiments={experiments} selectedRunId={runId} />
            </>
          ) : (
            <div className="panel editing-layer-intro">
              <strong>{t("editingLayer.primaryWorkflow")}</strong>
              <ol>
                <li>{t("editingLayer.step1")}</li>
                <li>{t("editingLayer.step2")}</li>
                <li>{t("editingLayer.step3")}</li>
                <li>{t("editingLayer.step4")}</li>
              </ol>
              <small>{t("editingLayer.legacyHint")}</small>
            </div>
          )}
        </aside>

        <section className="score-stage" aria-label="Score workspace">
          {activeTab === "Plan" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="plan-tab" title="Agent Plan could not be rendered">
              <AgentPlanPanel result={result} />
            </RuntimeErrorBoundary>
          )}
          {activeTab === "Workbench" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="workbench-tab" title="Workbench could not be rendered">
              <ScoreWorkbench result={result} />
            </RuntimeErrorBoundary>
          )}
          {activeTab === "Score" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="score-tab" title="Generated score view could not be rendered">
              <PromptConflictPanel resolution={result?.prompt_control_resolution} />
              <ScoreMetadataPanel onMetadataChange={handleScoreMetadataChange} result={result} />
              <KeyConsistencyPanel report={result?.key_consistency_report || result?.generation_metadata?.key_consistency_report} />
              <MelodyLineReportPanel
                crossMeasureReport={result?.generation_metadata?.cross_measure_melodic_grammar_report || result?.metadata?.cross_measure_melodic_grammar_report}
                report={result?.generation_metadata?.melody_line_report || result?.metadata?.melody_line_report}
              />
              <CandidateMetadataPanel metadata={result?.generation_metadata || result?.metadata} />
              <MelodyExpectationReportPanel
                report={result?.generation_metadata?.melody_expectation_report || result?.metadata?.melody_expectation_report}
                metadata={result?.generation_metadata || result?.metadata}
              />
              <HarmonyProfilePanel metadata={result?.generation_metadata || result?.metadata} />
              <TrackPlanPanel metadata={result?.generation_metadata || result?.metadata} scoreDocument={result?.score_document} />
              <ScoreViewer onOpenWorkbench={() => setActiveTab("Workbench")} onPlayMidi={handlePlayMidi} rendererStatus={rendererStatus} result={result} />
              <MidiPlayer result={result} />
              <ResolvedGenerationRequestPanel resolution={result?.prompt_control_resolution} />
              <ConsistencyReportPanel report={result?.consistency_report} />
              <ValidationReportPanel result={result} />
            </RuntimeErrorBoundary>
          )}
          {activeTab === "Validation" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="validation-tab" title="Validation view could not be rendered">
              <ValidationReportPanel detailed result={result} />
            </RuntimeErrorBoundary>
          )}
          {activeTab === "Evaluation" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="evaluation-tab" title="Evaluation view could not be rendered">
              <ResearchModePanel result={result} />
              <div className="evaluation-grid">
                {Object.entries(evaluation).map(([key, value]) => (
                  <div className="metric-tile" key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>{Array.isArray(value) ? value.length : String(value)}</strong>
                  </div>
                ))}
              </div>
            </RuntimeErrorBoundary>
          )}
          {activeTab === "Model" && (
            <RuntimeErrorBoundary resetKey={renderResetKey} scope="model-tab" title="Model view could not be rendered">
              {modelPanel}
            </RuntimeErrorBoundary>
          )}
          {!result && activeTab !== "Model" && activeTab !== "Workbench" && (
            <div className="empty-state">
              <strong>{t("app.empty.title")}</strong>
              <span>{t("app.empty.body")}</span>
            </div>
          )}
          {error && <div className="error-banner">{error}</div>}
        </section>

        <aside className="right-inspector">
          {LEGACY_GENERATION_ENABLED ? (
            <>
              <RuntimeErrorBoundary resetKey={renderResetKey} scope="right-plan" title="Plan summary could not be rendered">
                <AgentPlanPanel compact result={result} />
              </RuntimeErrorBoundary>
              <RuntimeErrorBoundary resetKey={renderResetKey} scope="export-panel" title="Export panel could not be rendered">
                <ExportPanel onEvaluate={handleEvaluate} result={result} />
              </RuntimeErrorBoundary>
              <RuntimeErrorBoundary resetKey={renderResetKey} scope="rating-panel" title="Rating panel could not be rendered">
                <HumanEvaluationPanel
                  disabled={status === "generating" || status === "revising"}
                  onSubmit={handleRating}
                  result={result}
                />
              </RuntimeErrorBoundary>
              <div className="panel">
                <label htmlFor="feedback">{t("revision.label")}</label>
                <textarea
                  id="feedback"
                  rows="4"
                  value={feedback}
                  onChange={(event) => setFeedback(event.target.value)}
                />
                <button className="secondary-action" disabled={!runId} onClick={handleRevise} type="button">
                  {t("revision.button")}
                </button>
              </div>
            </>
          ) : (
            <div className="panel editing-layer-principles">
              <strong>{t("editingLayer.guardrails")}</strong>
              <ul>
                <li>{t("editingLayer.guardrail1")}</li>
                <li>{t("editingLayer.guardrail2")}</li>
                <li>{t("editingLayer.guardrail3")}</li>
              </ul>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

function updateResultMetadata(current, field, value) {
  if (!current) return current;
  const scoreDocument = current.score_document?.schema_version === "0.6"
    ? {
        ...current.score_document,
        metadata: { ...(current.score_document.metadata || {}) }
      }
    : null;
  if (scoreDocument) {
    scoreDocument[field] = value;
    scoreDocument.metadata[field] = value;
  }
  const title = field === "title" ? value : scoreDocument?.title || current.intent?.title || "Untitled Sera Score";
  const composer = field === "composer" ? value : scoreDocument?.composer || "Sera";
  const generationMetadata = {
    ...(current.generation_metadata || {}),
    metadata_sync_report: {
      ...(current.generation_metadata?.metadata_sync_report || {}),
      title_after: title,
      composer_after: composer
    }
  };
  return {
    ...current,
    intent: { ...(current.intent || {}), ...(field === "title" ? { title } : {}) },
    score_document: scoreDocument || current.score_document,
    musicxml: patchMusicXmlMetadata(current.musicxml || "", title, composer),
    generation_metadata: generationMetadata
  };
}

function patchMusicXmlMetadata(musicxml, title, composer) {
  if (!musicxml) return musicxml;
  let updated = String(musicxml).replace(/<work-title>.*?<\/work-title>/s, `<work-title>${escapeXml(title || "Untitled Sera Score")}</work-title>`);
  if (updated === musicxml && /<score-partwise\b[^>]*>/i.test(updated)) {
    updated = updated.replace(/(<score-partwise\b[^>]*>)/i, `$1\n  <work>\n    <work-title>${escapeXml(title || "Untitled Sera Score")}</work-title>\n  </work>`);
  }
  if (/<creator\s+type=["']composer["']>.*?<\/creator>/s.test(updated)) {
    updated = updated.replace(/<creator\s+type=["']composer["']>.*?<\/creator>/s, `<creator type="composer">${escapeXml(composer || "Sera")}</creator>`);
  } else if (updated.includes("</identification>")) {
    updated = updated.replace("</identification>", `    <creator type="composer">${escapeXml(composer || "Sera")}</creator>\n  </identification>`);
  }
  return updated;
}

function escapeXml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function ResearchModePanel({ result }) {
  const { t } = useI18n();
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
        <h2>{t("research.title")}</h2>
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
