import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyStrictScorePatch,
  chatWithSera,
  createNotationBridgeSession,
  exportNotationBridgeRevision,
  generateStrictScorePatchPreview,
  getCompositionRefinement,
  getSeraEditProviderStatus,
  getNotationBridgeWorkspace,
  getNotationHosts,
  previewCompositionCandidates,
  submitCompositionPreference
} from "../api.js";
import LLMProviderSettingsDialog, { type ProviderStatus } from "./LLMProviderSettingsDialog";
import { readPendingDesktopSession, subscribeDesktopOpenSession } from "../desktop/desktopRuntime";
import LanguageSelector from "../i18n/LanguageSelector";
import { englishSystemText } from "../i18n/systemText";
import { bridgeSessionIdFromSearch, safeBridgeSessionId } from "../score/notationBridge";
import {
  buildStrictScoreScopes,
  EMPTY_STRICT_PATCH_HISTORY,
  recordStrictPatch,
  undoStrictPatch,
  type StrictPatchHistory
} from "../score/seraEditResearch";
import type {
  CompositionCandidate,
  CompositionFailureAnalysis,
  CompositionPreferenceReason,
  CompositionPreviewResponse,
  CompositionRefinementResponse,
  ScoreDocument,
  SeraConversationResponse,
  StrictGenerationPreview,
  StrictScorePatch,
  StrictValidationIssue
} from "../score/scoreTypes";

type HostCapability = {
  host_id: string;
  display_name: string;
  bridge_status?: string;
};

type AgentMessage = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

type ComposerMode = "chat" | "edit" | "compose";

const FALLBACK_HOSTS: HostCapability[] = [
  { host_id: "musescore", display_name: "MuseScore Studio" },
  { host_id: "sibelius", display_name: "Avid Sibelius Ultimate" },
  { host_id: "musicxml", display_name: "Generic MusicXML" }
];

const INITIAL_MESSAGES: AgentMessage[] = [
  {
    id: 1,
    role: "assistant",
    text: "Ask me a question to get started. Chat leaves your score unchanged. To edit, connect your notation host and switch to Edit proposal to generate a validated ScorePatch."
  }
];

export default function SeraAgentConsole({
  backendCapabilities,
  onOpenResearchReview
}: {
  backendCapabilities?: any;
  onOpenResearchReview?: () => void;
}) {
  const [hosts, setHosts] = useState<HostCapability[]>(FALLBACK_HOSTS);
  const [selectedHost, setSelectedHost] = useState("musescore");
  const [bridgeSession, setBridgeSession] = useState<any>(null);
  const [scoreDocument, setScoreDocument] = useState<ScoreDocument | null>(null);
  const [composerMode, setComposerMode] = useState<ComposerMode>("chat");
  const [chatInput, setChatInput] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [compositionBrief, setCompositionBrief] = useState("");
  const [messages, setMessages] = useState<AgentMessage[]>(INITIAL_MESSAGES);
  const [generation, setGeneration] = useState<StrictGenerationPreview | null>(null);
  const [generationSessionId, setGenerationSessionId] = useState("");
  const [composition, setComposition] = useState<CompositionPreviewResponse | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [providerSettingsOpen, setProviderSettingsOpen] = useState(false);
  const [history, setHistory] = useState<StrictPatchHistory>(EMPTY_STRICT_PATCH_HISTORY);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Waiting for a host connection");
  const [deliveryNotice, setDeliveryNotice] = useState("");
  const [compositionRunning, setCompositionRunning] = useState(false);
  const [compositionElapsedSeconds, setCompositionElapsedSeconds] = useState(0);
  const [compositionError, setCompositionError] = useState("");
  const [compositionRefinementJobId, setCompositionRefinementJobId] = useState("");
  const [compositionRefinementNotice, setCompositionRefinementNotice] = useState("");
  const [preferenceNotice, setPreferenceNotice] = useState("");
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window === "undefined") return "";
    return bridgeSessionIdFromSearch(window.location.search)
      || safeBridgeSessionId(readPendingDesktopSession().session_id);
  });
  const activeSessionIdRef = useRef(sessionId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageIdRef = useRef(1);

  const connected = Boolean(bridgeSession?.session_id && scoreDocument);
  const selectedRange = useMemo(
    () => hostSelectedRange(scoreDocument, bridgeSession),
    [bridgeSession, scoreDocument]
  );
  const scopes = useMemo(
    () => buildStrictScoreScopes(selectedRange, [], {}),
    [selectedRange]
  );
  const hostName = hostDisplayName(hosts, bridgeSession?.host_id || selectedHost);
  const report = generation?.preview?.validation_report;
  const canApply = Boolean(
    connected
    && generation?.patch
    && generationSessionId === bridgeSession?.session_id
    && generation.preview?.proposed_score_document
    && report
    && report.status !== "invalid"
    && report.status !== "unsupported"
    && report.errors.length === 0
  );

  useEffect(() => {
    if (!compositionRunning) {
      setCompositionElapsedSeconds(0);
      return undefined;
    }
    const startedAt = Date.now();
    setCompositionElapsedSeconds(0);
    const timer = window.setInterval(() => {
      setCompositionElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [compositionRunning]);

  useEffect(() => {
    if (!compositionRefinementJobId) return undefined;
    let cancelled = false;
    let timer: number | undefined;
    let transientFailures = 0;
    const poll = async () => {
      try {
        const payload = await getCompositionRefinement(compositionRefinementJobId) as CompositionRefinementResponse;
        if (cancelled) return;
        transientFailures = 0;
        if (payload.status === "ready" && payload.result) {
          setComposition({
            ...payload.result,
            refinement: {
              job_id: payload.job_id,
              status: "ready",
              created_at: payload.created_at,
              completed_at: payload.completed_at,
              error: ""
            }
          });
          const hasCandidates = payload.result.candidates.length > 0;
          setCompositionRefinementNotice(hasCandidates
            ? "Live LLM planning is complete and candidates have been updated. Select a candidate for final review."
            : "Live LLM planning is complete, but the resulting candidates failed safety checks. Diagnostics below describe the search based on that plan.");
          setStatus(hasCandidates
            ? `LLM refinement complete · Generated ${payload.result.candidates.length} candidates`
            : "LLM responded · Candidates failed safety checks");
          setCompositionRefinementJobId("");
          return;
        }
        if (payload.status === "failed") {
          setComposition((current) => current ? {
            ...current,
            refinement: { ...current.refinement!, status: "failed", error: payload.error || "The model did not return a valid plan" }
          } : current);
          setCompositionRefinementNotice(`Background LLM refinement did not complete: ${payload.error || "The model did not return a valid plan"}. Local candidates remain available.`);
          setStatus("LLM refinement failed · Safe local candidates retained");
          setCompositionRefinementJobId("");
          return;
        }
        timer = window.setTimeout(poll, 1200);
      } catch (error: any) {
        if (cancelled) return;
        transientFailures += 1;
        if (transientFailures <= 5) {
          setCompositionRefinementNotice(
            `Connection interrupted while checking LLM progress. Retrying (${transientFailures}/5). Local results remain available.`
          );
          timer = window.setTimeout(poll, 2000);
          return;
        }
        setCompositionRefinementNotice(`Unable to check LLM progress after 5 attempts: ${error?.message || "Unknown error"}. Local results remain available.`);
        setCompositionRefinementJobId("");
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [compositionRefinementJobId]);

  useEffect(() => {
    getNotationHosts()
      .then((payload) => setHosts(payload.hosts?.length ? payload.hosts : FALLBACK_HOSTS))
      .catch(() => setHosts(FALLBACK_HOSTS));
    getSeraEditProviderStatus()
      .then((payload) => setProviderStatus(payload as ProviderStatus))
      .catch(() => setProviderStatus(null));
  }, []);

  useEffect(() => subscribeDesktopOpenSession((payload) => {
    const nextSessionId = safeBridgeSessionId(payload.session_id);
    if (!nextSessionId || nextSessionId === activeSessionIdRef.current) return;
    activeSessionIdRef.current = nextSessionId;
    setBusy(true);
    setGeneration(null);
    setGenerationSessionId("");
    setComposition(null);
    setCompositionRunning(false);
    setCompositionRefinementJobId("");
    setHistory(EMPTY_STRICT_PATCH_HISTORY);
    setDeliveryNotice("");
    setStatus("Switching to the latest host session");
    const url = new URL(window.location.href);
    url.searchParams.set("bridge_session", nextSessionId);
    url.searchParams.set("desktop", "1");
    window.history.replaceState({}, "", url);
    setSessionId(nextSessionId);
  }), []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    setBusy(true);
    setStatus("Receiving host context");
    getNotationBridgeWorkspace(sessionId)
      .then((payload) => {
        if (cancelled) return;
        loadBridgeWorkspace(payload);
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setStatus(`Host session failed to load: ${error.message}`);
        appendMessage("assistant", `Unable to read the host session: ${error.message}`);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  function appendMessage(role: AgentMessage["role"], text: string) {
    messageIdRef.current += 1;
    const message = { id: messageIdRef.current, role, text };
    setMessages((current) => [...current, message]);
  }

  function loadBridgeWorkspace(payload: any) {
    const nextScore = payload.score_document as ScoreDocument;
    const nextSession = payload.session;
    activeSessionIdRef.current = safeBridgeSessionId(nextSession?.session_id);
    setScoreDocument(nextScore);
    setBridgeSession(nextSession);
    setSelectedHost(nextSession?.host_id || "musescore");
    setGeneration(null);
    setGenerationSessionId("");
    setComposition(null);
    setCompositionRefinementJobId("");
    setCompositionRefinementNotice("");
    setPreferenceNotice("");
    setHistory(EMPTY_STRICT_PATCH_HISTORY);
    setDeliveryNotice("");
    const range = hostSelectedRange(nextScore, nextSession);
    setMessages([
      {
        id: ++messageIdRef.current,
        role: "assistant",
        text: `Received from ${hostDisplayName(hosts, nextSession?.host_id)}: “${nextScore.title || "Untitled score"}”, host selection M${range.start_measure}–M${range.end_measure}. You can continue chatting. Switch to Edit proposal to edit the score.`
      }
    ]);
    setStatus(`Connected to ${hostDisplayName(hosts, nextSession?.host_id)}`);
  }

  async function handleMusicXmlImport(file: File) {
    setBusy(true);
    setStatus("Importing MusicXML from the host");
    try {
      const payload = await createNotationBridgeSession(
        selectedHost,
        await file.text(),
        file.name,
        "Imported into the Sera Agent host bridge"
      );
      const nextSessionId = safeBridgeSessionId(payload.session?.session_id);
      if (nextSessionId) {
        const url = new URL(window.location.href);
        url.searchParams.set("bridge_session", nextSessionId);
        window.history.replaceState({}, "", url);
        setSessionId(nextSessionId);
      }
      loadBridgeWorkspace(payload);
    } catch (error: any) {
      setStatus(`MusicXML import failed: ${error.message}`);
      appendMessage("assistant", `Host file import failed: ${error.message}`);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleChat() {
    const requestText = chatInput.trim();
    if (!requestText) return;
    const conversationHistory = messages.slice(-12).map((message) => ({
      role: message.role,
      content: message.text
    }));
    setBusy(true);
    setStatus("Chatting · Score remains unchanged");
    appendMessage("user", requestText);
    setChatInput("");
    try {
      const payload = await chatWithSera(
        requestText,
        conversationHistory,
        scoreDocument,
        connected ? scopes.targetScope : {}
      ) as SeraConversationResponse;
      if (payload.provider_status) setProviderStatus(payload.provider_status as unknown as ProviderStatus);
      appendMessage("assistant", payload.answer);
      setStatus(payload.status === "answered"
        ? "Chat complete · Score unchanged"
        : `Chat unavailable · ${payload.reason || "Check the model settings"}`);
    } catch (error: any) {
      appendMessage("assistant", `Chat request failed: ${error.message}. The score is unchanged.`);
      setStatus(`Chat request failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerate() {
    if (!scoreDocument || !bridgeSession || !editInstruction.trim()) return;
    const requestSessionId = safeBridgeSessionId(bridgeSession.session_id);
    const requestText = editInstruction.trim();
    setBusy(true);
    setGeneration(null);
    setGenerationSessionId("");
    setComposition(null);
    setCompositionRefinementJobId("");
    setCompositionRefinementNotice("");
    setPreferenceNotice("");
    setDeliveryNotice("");
    setStatus("Generating and validating ScorePatch");
    try {
      const payload = await generateStrictScorePatchPreview(
        scoreDocument,
        requestText,
        scopes.targetScope,
        scopes.protectedScope
      ) as StrictGenerationPreview;
      if (activeSessionIdRef.current !== requestSessionId) return;
      setGeneration(payload);
      setGenerationSessionId(requestSessionId);
      if (payload.provider_status) setProviderStatus(payload.provider_status as unknown as ProviderStatus);
      if (payload.status === "generated") {
        const validationStatus = payload.preview?.validation_report.status || "unknown";
        const engine = payload.generator.composition_route
          ? `Composer / ${payload.generator.provider} / ${payload.generator.model}`
          : payload.generator.live
            ? `${payload.generator.provider} / ${payload.generator.model}`
            : "Local deterministic editor";
        const repair = !payload.generator.composition_route && payload.generator.repair_strategy && payload.generator.repair_strategy !== "none"
          ? ` · ${payload.generator.repair_strategy} repair`
          : "";
        setStatus(`Generated with ${engine} · Proposal ${validationStatus}${repair}`);
        setEditInstruction("");
      } else {
        setStatus(`${payload.reason || payload.status} · Score unchanged`);
      }
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      setStatus(`Proposal generation failed: ${error.message}`);
    } finally {
      if (activeSessionIdRef.current === requestSessionId) setBusy(false);
    }
  }

  async function handleCompose() {
    if (!scoreDocument || !bridgeSession || !compositionBrief.trim()) return;
    const requestSessionId = safeBridgeSessionId(bridgeSession.session_id);
    const requestText = compositionBrief.trim();
    setBusy(true);
    setGeneration(null);
    setGenerationSessionId("");
    setComposition(null);
    setCompositionError("");
    setCompositionRefinementJobId("");
    setCompositionRefinementNotice("");
    setPreferenceNotice("");
    setDeliveryNotice("");
    setStatus("Planning and validating composition candidates");
    setCompositionRunning(true);
    try {
      const payload = await previewCompositionCandidates(
        scoreDocument,
        requestText,
        scopes.targetScope,
        scopes.protectedScope,
        3,
        42
      ) as CompositionPreviewResponse;
      if (activeSessionIdRef.current !== requestSessionId) return;
      setComposition(payload);
      if (payload.refinement?.status === "running") {
        setCompositionRefinementJobId(payload.refinement.job_id);
        const waitSeconds = Math.round(Number(
          (payload.provider_status as Record<string, unknown> | undefined)?.composer_timeout_seconds || 180
        ));
        setCompositionRefinementNotice(payload.candidates.length > 0
          ? `Safe local candidates are ready. Live LLM refinement continues in the background (up to ${waitSeconds} seconds). You can review local candidates now.`
          : `These 16 candidates are local drafts. Live LLM planning continues in the background (up to ${waitSeconds} seconds). Candidates and diagnostics will update when it finishes.`);
      } else if (payload.refinement?.status === "failed") {
        setCompositionRefinementNotice(`Background LLM refinement failed: ${payload.refinement.error || "The model did not return a valid plan"}. Local candidates remain available.`);
      }
      if (payload.provider_status) setProviderStatus(payload.provider_status as unknown as ProviderStatus);
      if (payload.status === "generated") {
        setCompositionBrief("");
        setStatus(`Generated ${payload.candidates.length} candidates · Host rhythm and layout preserved`);
      } else if (payload.refinement?.status === "running") {
        setStatus("Local candidates failed checks · Waiting for the live LLM");
      } else {
        setStatus(payload.reason || "No safe candidates could be generated from this brief");
      }
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      const message = error?.message || "Unknown error";
      setCompositionError(message);
      setStatus(`Composition candidate generation failed: ${message}`);
    } finally {
      if (activeSessionIdRef.current === requestSessionId) {
        setCompositionRunning(false);
        setBusy(false);
      }
    }
  }

  function handleSelectCandidate(candidate: CompositionCandidate) {
    if (!composition) return;
    setCompositionRefinementJobId("");
    setGeneration({
      status: "generated",
      patch: candidate.patch,
      reason: null,
      matched_intents: ["theory_guided_composition"],
      generator: {
        provider: composition.planner.provider || "local_rule",
        model: composition.planner.model || "sera_composer_rules_v1",
        formal_experiment_eligible: false,
        live: composition.planner.planner === "live_llm",
        prompt_version: composition.planner.prompt_version || "sera_composition_plan_v4.0",
        latency_ms: composition.planner.latency_ms
      },
      provider_status: composition.provider_status,
      preview: candidate.preview
    });
    setGenerationSessionId(safeBridgeSessionId(bridgeSession?.session_id));
    setStatus(`${englishSystemText(candidate.label)} is ready for final proposal review. The host score is unchanged`);
  }

  async function handlePreferCandidate(candidate: CompositionCandidate, reasons: CompositionPreferenceReason[]) {
    if (!composition?.comparison_id || !composition.plan) return;
    setBusy(true);
    setPreferenceNotice("Saving your preference locally…");
    try {
      const payload = await submitCompositionPreference({
        comparison_id: composition.comparison_id,
        plan_id: composition.plan.plan_id,
        style_family: composition.plan.style_family,
        selected_candidate_id: candidate.candidate_id,
        rejected_candidate_ids: composition.candidates
          .filter((item) => item.candidate_id !== candidate.candidate_id)
          .map((item) => item.candidate_id),
        selected_review: {
          motif_score: candidate.review.motif_score,
          phrase_score: candidate.review.phrase_score,
          style_score: candidate.review.style_score,
          theory_score: candidate.review.theory_score,
          playability_score: candidate.review.playability_score
        },
        reasons
      });
      setComposition((current) => current ? { ...current, preference_profile: payload.preference_profile } : current);
      setPreferenceNotice(payload.recorded
        ? `Recorded ${englishSystemText(candidate.label)}; Total ${payload.preference_profile.feedback_count} local preferences.`
        : `${englishSystemText(candidate.label)} preference was already recorded.`);
      setStatus("Composer preferences saved locally. The aggregated profile will inform the next candidate ranking");
    } catch (error: any) {
      setPreferenceNotice(`Preference could not be saved: ${error?.message || "Unknown error"}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleApplyAndExport() {
    const patch = generation?.patch;
    if (!patch || !scoreDocument || !bridgeSession?.session_id) return;
    const requestSessionId = safeBridgeSessionId(bridgeSession.session_id);
    if (!requestSessionId || generationSessionId !== requestSessionId) return;
    setBusy(true);
    setStatus("Applying the transaction and preparing a host revision");
    try {
      const beforeScore = scoreDocument;
      const applied = await applyStrictScorePatch(beforeScore, patch);
      if (activeSessionIdRef.current !== requestSessionId) return;
      if (!applied.committed) {
        setGeneration((current) => current ? { ...current, preview: applied } : current);
        setStatus(applied.rollback_reason || "Transaction rolled back; the score is unchanged");
        return;
      }
      const afterScore = applied.score_document as ScoreDocument;
      const exported = await exportNotationBridgeRevision(
        requestSessionId,
        afterScore,
        Number(bridgeSession.revision || 0)
      );
      setScoreDocument(afterScore);
      setBridgeSession(exported.session);
      setHistory((current) => recordStrictPatch(current, {
        patch,
        beforeScore,
        afterScore,
        validationReport: applied.validation_report
      }));
      setGeneration(null);
      setGenerationSessionId("");
      const notice = `Revision ${exported.revision} is ready. Return to ${hostName} and click “Refresh and open applied revision”.`;
      setDeliveryNotice(notice);
      setStatus(`Host revision ${exported.revision} is ready`);
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      setStatus(`Host revision generation failed: ${error.message}`);
    } finally {
      if (activeSessionIdRef.current === requestSessionId) setBusy(false);
    }
  }

  async function handleUndoAndExport() {
    if (!scoreDocument || !bridgeSession?.session_id) return;
    const undone = undoStrictPatch(history, scoreDocument);
    if (!undone) return;
    setBusy(true);
    setStatus("Preparing an undo revision");
    try {
      const exported = await exportNotationBridgeRevision(
        bridgeSession.session_id,
        undone.scoreDocument,
        Number(bridgeSession.revision || 0)
      );
      setScoreDocument(undone.scoreDocument);
      setHistory(undone.history);
      setBridgeSession(exported.session);
      const notice = `Undo revision ${exported.revision} is ready. In ${hostName}, open the latest revision.`;
      setDeliveryNotice(notice);
      setStatus(`Undo revision ${exported.revision} is ready`);
    } catch (error: any) {
      setStatus(`Undo revision failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  function handleReject() {
    setGeneration(null);
    setGenerationSessionId("");
    setStatus("Proposal rejected · Score unchanged");
  }

  return (
    <div className="agent-app-shell">
      <header className="agent-topbar">
        <div className="agent-brand">
          <div className="agent-brand-mark" aria-hidden="true">S</div>
          <div>
            <strong>Sera</strong>
            <span>Intelligent score editing agent</span>
          </div>
        </div>
        <div className="agent-topbar-actions">
          {onOpenResearchReview && (
            <button className="agent-research-review-button" onClick={onOpenResearchReview} type="button">
              Research review
            </button>
          )}
          <span className={`agent-backend-state ${backendCapabilities?.api_contract ? "ready" : "waiting"}`}>
            <i aria-hidden="true" />
            {backendCapabilities?.api_contract ? "Backend ready" : "Check backend"}
          </span>
          <span
            aria-label="Agent provider status"
            className={`agent-provider-state ${providerStatus?.available ? "live" : "local"}`}
            title={providerStatus?.reason || "Checking agent provider status"}
          >
            <i aria-hidden="true" />
            {providerStatus?.available
              ? `${providerStatus.provider} · ${providerStatus.model}`
              : "Local rules"}
          </span>
          <button
            className="agent-provider-settings-button"
            onClick={() => setProviderSettingsOpen(true)}
            type="button"
          >
            Model settings
          </button>
          <LanguageSelector />
        </div>
      </header>

      <main className="agent-console-grid">
        <aside className="agent-connection-rail">
          <div>
            <h1>Connect a notation host</h1>
            <p>View and manually edit your score in your notation software.</p>
          </div>

          <section className="agent-rail-section">
            <h2>Select a host</h2>
            <div className="agent-host-list" role="radiogroup" aria-label="Select a notation host">
              {hosts.map((host) => (
                <button
                  aria-checked={selectedHost === host.host_id}
                  className={selectedHost === host.host_id ? "selected" : ""}
                  disabled={connected || busy}
                  key={host.host_id}
                  onClick={() => setSelectedHost(host.host_id)}
                  role="radio"
                  type="button"
                >
                  <span className="agent-host-monogram" aria-hidden="true">{hostMonogram(host.host_id)}</span>
                  <span>{host.display_name}</span>
                  <i aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <section className="agent-rail-section agent-steps">
            <h2>Connection steps</h2>
            <ol>
              <li><span>1</span><p>Open your score in the notation host</p></li>
              <li><span>2</span><p>Select the region you want the agent to edit</p></li>
              <li><span>3</span><p>Run Sera Bridge and return to this window</p></li>
            </ol>
          </section>

          <section className="agent-rail-section agent-session-summary">
            <h2>Connection status</h2>
            <p className={connected ? "connected" : "disconnected"}>
              <i aria-hidden="true" />
              {connected ? `Connected to ${hostName}` : "Waiting for a score from the host"}
            </p>
            {connected && scoreDocument && (
              <dl>
                <div><dt>Current score</dt><dd>{scoreDocument.title || "Untitled score"}</dd></div>
                <div><dt>Host selection</dt><dd>M{selectedRange.start_measure}–M{selectedRange.end_measure}</dd></div>
                <div><dt>Revision</dt><dd>{bridgeSession.revision ?? 0}</dd></div>
              </dl>
            )}
          </section>

          <div className="agent-import-action">
            <input
              accept=".musicxml,.xml"
              aria-label="Import a MusicXML file from the host"
              className="agent-visually-hidden"
              onChange={(event) => event.target.files?.[0] && handleMusicXmlImport(event.target.files[0])}
              ref={fileInputRef}
              type="file"
            />
            <button disabled={busy} onClick={() => fileInputRef.current?.click()} type="button">
              Import host MusicXML
            </button>
            <small>Import a copy when MuseScore Bridge is unavailable</small>
          </div>
        </aside>

        <section className="agent-conversation" aria-label="Chat with Sera">
          <header>
            <h1>Chat with Sera</h1>
            <p>Ask questions in Chat. Use Edit proposal to generate and review validated score changes.</p>
          </header>
          <div className="agent-message-list" aria-live="polite">
            {messages.map((message) => (
              <article className={`agent-message ${message.role}`} key={message.id}>
                <span className="agent-avatar" aria-hidden="true">{message.role === "assistant" ? "S" : "You"}</span>
                <div>
                  <strong>{message.role === "assistant" ? "Sera" : "You"}</strong>
                  <p>{message.text}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="agent-composer">
            <div className="agent-composer-mode" role="tablist" aria-label="Choose Chat, Edit proposal, or Compose">
              <button
                aria-selected={composerMode === "chat"}
                className={composerMode === "chat" ? "selected" : ""}
                onClick={() => setComposerMode("chat")}
                role="tab"
                type="button"
              >
                Chat
                <small>Answers without score changes</small>
              </button>
              <button
                aria-selected={composerMode === "edit"}
                className={composerMode === "edit" ? "selected" : ""}
                onClick={() => setComposerMode("edit")}
                role="tab"
                type="button"
              >
                Edit proposal
                <small>Generate and validate ScorePatch</small>
              </button>
              <button
                aria-selected={composerMode === "compose"}
                className={composerMode === "compose" ? "selected" : ""}
                onClick={() => setComposerMode("compose")}
                role="tab"
                type="button"
              >
                Compose
                <small>Plan, compare, and review</small>
              </button>
            </div>
            {composerMode === "chat" ? (
              <>
                <textarea
                  aria-label="Ask Sera a question"
                  disabled={busy}
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleChat();
                  }}
                  placeholder="Ask about music theory, using Sera, or describing your intended edit…"
                  rows={5}
                  value={chatInput}
                />
                <div className="agent-composer-footer">
                  <span>Chat does not generate, apply, or export score edits</span>
                  <button disabled={busy || !chatInput.trim()} onClick={handleChat} type="button">
                    {busy ? "Working…" : "Send message"}
                  </button>
                </div>
              </>
            ) : composerMode === "edit" ? (
              <>
                <textarea
                  aria-label="Describe your score edit"
                  disabled={!connected || busy}
                  onChange={(event) => setEditInstruction(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleGenerate();
                  }}
                  placeholder={connected ? "For example: transpose the selection up a major second while preserving rhythm…" : "Connect a notation host before generating an edit proposal…"}
                  rows={5}
                  value={editInstruction}
                />
                <div className="agent-composer-footer">
                  <span>{connected ? `Host target range: M${selectedRange.start_measure}–M${selectedRange.end_measure}` : "Edit proposals require a host score and selection"}</span>
                  <button disabled={!connected || busy || !editInstruction.trim()} onClick={handleGenerate} type="button">
                    {busy ? "Generating and validating…" : "Generate edit proposal"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <textarea
                  aria-label="Describe your composition goal"
                  disabled={!connected || busy}
                  onChange={(event) => setCompositionBrief(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleCompose();
                  }}
                  placeholder={connected
                    ? "For example: rewrite the selection as a Romantic piano passage with a clear cadence, preserving rhythm and instrumentation…"
                    : "Connect a notation host and select 1–8 measures first…"}
                  rows={5}
                  value={compositionBrief}
                />
                <div className="agent-composer-footer">
                  <span>{connected
                    ? `Based on host rhythm: M${selectedRange.start_measure}–M${selectedRange.end_measure}`
                    : "Composition requires a host score and selection"}</span>
                  <button disabled={!connected || busy || !compositionBrief.trim()} onClick={handleCompose} type="button">
                    {compositionRunning ? `Planning ${compositionElapsedSeconds}s` : "Generate candidates"}
                  </button>
                </div>
              </>
            )}
          </div>
        </section>

        <aside className="agent-proposal-rail">
          <header>
            <h1>{composition && !generation ? "Composition candidates" : "Edit proposal"}</h1>
            <p>{composition && !generation
              ? "Candidates share a theory plan and undergo individual theory and host safety checks."
              : "Review, apply, or reject validated agent edits here."}</p>
          </header>
          {!generation && !composition && !deliveryNotice && !compositionRunning && !compositionError && (
            <div className="agent-proposal-empty">
              <strong>{connected ? "Waiting for an edit instruction" : "No host connected"}</strong>
              <p>{connected ? "Generated proposals will show operation summaries, validation results, and protected scope checks here." : "Send a score from your host to get started."}</p>
            </div>
          )}
          {compositionRunning && !generation && !composition && (
            <section className="agent-composition-progress" role="status" aria-live="polite">
              <div>
                <span className="agent-progress-spinner" aria-hidden="true" />
                <strong>{compositionProgressMessage(compositionElapsedSeconds)}</strong>
              </div>
              <progress max={20} value={Math.min(compositionElapsedSeconds, 20)} />
              <p>Elapsed: {compositionElapsedSeconds} seconds. Sera is preparing safe local drafts while the LLM works in the background.</p>
              <small>Review drafts as soon as they appear. Live LLM refinement will update candidates automatically.</small>
            </section>
          )}
          {compositionError && !compositionRunning && !generation && !composition && (
            <section className="agent-composition-error" role="alert">
              <strong>No composition candidates generated</strong>
              <p>{compositionError}</p>
              <small>Check that the model API is available, or select Local rules in Model settings and try again.</small>
            </section>
          )}
          {composition && !generation && (
            <CompositionCandidateReview
              composition={composition}
              busy={busy}
              refinementNotice={compositionRefinementNotice}
              preferenceNotice={preferenceNotice}
              onPrefer={handlePreferCandidate}
              onSelect={handleSelectCandidate}
            />
          )}
          {generation && (
            <ProposalReview
              canApply={canApply}
              generation={generation}
              onApply={handleApplyAndExport}
              onReject={handleReject}
              busy={busy}
            />
          )}
          {deliveryNotice && (
            <div className="agent-delivery-success">
              <strong>Host revision generated</strong>
              <p>{deliveryNotice}</p>
            </div>
          )}
          {history.done.length > 0 && !generation && (
            <button className="agent-undo-revision" disabled={busy} onClick={handleUndoAndExport} type="button">
              Undo last agent revision
            </button>
          )}
          <footer>{englishSystemText(status)}</footer>
        </aside>
      </main>
      {providerSettingsOpen && (
        <LLMProviderSettingsDialog
          currentStatus={providerStatus}
          onClose={() => setProviderSettingsOpen(false)}
          onSaved={(nextStatus) => {
            setProviderStatus(nextStatus);
            setStatus(nextStatus.available
              ? `Enabled ${nextStatus.provider} · ${nextStatus.model}`
              : "Switched to local rules");
          }}
        />
      )}
    </div>
  );
}

function compositionProgressMessage(elapsedSeconds: number) {
  if (elapsedSeconds < 4) return "Reading the host selection and theory constraints";
  if (elapsedSeconds < 16) return "Generating local drafts and running safety checks";
  return "Finalizing local candidates; LLM refinement continues in the background";
}

function CompositionCandidateReview({
  composition,
  busy,
  preferenceNotice,
  refinementNotice,
  onPrefer,
  onSelect
}: {
  composition: CompositionPreviewResponse;
  busy: boolean;
  preferenceNotice: string;
  refinementNotice: string;
  onPrefer: (candidate: CompositionCandidate, reasons: CompositionPreferenceReason[]) => void;
  onSelect: (candidate: CompositionCandidate) => void;
}) {
  const plan = composition.plan;
  const [preferenceReasons, setPreferenceReasons] = useState<CompositionPreferenceReason[]>([]);
  const reasonOptions: Array<{ value: CompositionPreferenceReason; label: string }> = [
    { value: "motif", label: "Clearer motif" },
    { value: "phrase", label: "More natural phrasing" },
    { value: "harmony", label: "Better harmony" },
    { value: "style", label: "Closer style match" },
    { value: "playability", label: "Easier to play" }
  ];
  return (
    <div className="agent-composition-review">
      {plan && (
        <section className="agent-composition-plan">
          <div>
            <span>{plan.style_family}</span>
            <span>{plan.texture}</span>
            <span>{plan.key}</span>
          </div>
          <h2>CompositionPlan</h2>
          <p className="agent-harmony-path">{plan.harmonic_progression.join(" – ")}</p>
          <p>Motif: {plan.motif_strategy} · Tension curve: {plan.tension_curve.map((value) => Math.round(value * 100)).join(" / ")}</p>
        </section>
      )}

      <section className={`agent-planner-source ${composition.planner.planner === "live_llm" ? "live" : "local"}`} aria-label="Planning source">
        <div>
          <strong>{composition.planner.planner === "live_llm"
            ? "Plan source: live LLM"
            : composition.refinement?.status === "running"
              ? "Plan source: immediate local draft"
              : "Plan source: local theory fallback"}</strong>
          <span>{composition.planner.provider || "local_rule"} · {composition.planner.model || "sera_composer_rules_v1"}</span>
        </div>
        <p>
          {typeof composition.planner.latency_ms === "number" ? `${Math.round(composition.planner.latency_ms)} ms` : "Timing unavailable"}
          {composition.planner.request_id ? ` · request ${composition.planner.request_id}` : ""}
          {composition.run_trace?.persisted ? ` · Trace ${composition.run_trace.trace_id}` : ""}
        </p>
        {composition.planner.planner !== "live_llm" && composition.planner.fallback_reason && (
          <small>{englishSystemText(composition.planner.fallback_reason)}</small>
        )}
      </section>

      {refinementNotice && (
        <section className={`agent-refinement-notice ${composition.refinement?.status || "ready"}`} role="status" aria-live="polite">
          <strong>{composition.refinement?.status === "running" ? "LLM refinement in progress" : "Background LLM status"}</strong>
          <p>{refinementNotice}</p>
        </section>
      )}

      {composition.style_knowledge && (
        <section className="agent-style-knowledge" aria-label="Style knowledge evidence">
          <div>
            <strong>Composer V0.4 knowledge retrieval · {composition.style_knowledge.style_id.replaceAll("_", " ")}</strong>
            <span>v{composition.style_knowledge.schema_version}</span>
          </div>
          <p>
            Local library: {composition.style_knowledge.retrieval.total_cards} rule cards / {composition.style_knowledge.retrieval.pack_count} knowledge packs;
            selected for this run: {composition.style_knowledge.retrieval.selected_cards} cards, approximately {composition.style_knowledge.retrieval.estimated_tokens}/{composition.style_knowledge.retrieval.token_budget} tokens.
          </p>
          <p>
            Instruments {composition.style_knowledge.query.instruments.join(", ") || "General"} ·
            Target {composition.style_knowledge.query.goals.join(", ") || "General"} ·
            Internally reviewed {composition.search_summary.evaluated}/{composition.search_summary.search_width} candidates; showing {composition.search_summary.returned}.
          </p>
          {composition.texture_analysis && (
            <p>
              Source texture {composition.texture_analysis.texture} ({Math.round(composition.texture_analysis.confidence * 100)}%) ·
              {" "}{composition.texture_analysis.voice_count} active voices · Planned target {plan?.texture || "Not specified"}
            </p>
          )}
          <details className="agent-knowledge-rules">
            <summary>Retrieved rules ({composition.style_knowledge.matched_rules.length})</summary>
            <ol>
              {composition.style_knowledge.matched_rules.map((rule) => (
                <li key={rule.rule_id}>
                  <div><strong>{rule.rule_id}</strong><span>{rule.domain.replaceAll("_", " ")}</span></div>
                  <details><summary>Original knowledge text</summary><strong lang="zh-CN">{rule.title_zh}</strong><p lang="zh-CN">{rule.action_zh}</p></details>
                  <small>{rule.rule_id} · {rule.match_reason}</small>
                </li>
              ))}
            </ol>
          </details>
          {composition.phrase_analysis && (
            <small>
              Source melody {composition.phrase_analysis.primary_voice_id || "Not identified"} ·
              Contour {composition.phrase_analysis.source_motif.contour} ·
              Motif intervals {composition.phrase_analysis.source_motif.intervals.join(" / ") || "Insufficient data"}
            </small>
          )}
        </section>
      )}

      {composition.candidates.length > 0 && (
        <fieldset className="agent-preference-reasons">
          <legend>What matters most when comparing candidates? (Optional)</legend>
          {reasonOptions.map((option) => (
            <label key={option.value}>
              <input
                checked={preferenceReasons.includes(option.value)}
                onChange={(event) => setPreferenceReasons((current) => event.target.checked
                  ? [...current, option.value]
                  : current.filter((value) => value !== option.value))}
                type="checkbox"
              />
              {option.label}
            </label>
          ))}
          <small>Only candidate ratings and choices are saved locally. Notes and personal identity are not stored.</small>
        </fieldset>
      )}

      {preferenceNotice && <p className="agent-preference-notice" role="status">{preferenceNotice}</p>}

      {composition.status === "plan_only" && (
        <section className="agent-composition-plan-only">
          <strong>Plan only; no changes applied</strong>
          <p>{englishSystemText(composition.reason)}</p>
          {plan?.orchestration_notes?.map((note, index) => <p key={index}>• {englishSystemText(note)}</p>)}
        </section>
      )}

      {composition.status === "unsupported" && (
        <CompositionFailurePanel
          analysis={composition.failure_analysis}
          fallbackReason={englishSystemText(composition.reason)}
          refinementStatus={composition.refinement?.status}
          composerTimeoutSeconds={Number(
            (composition.provider_status as Record<string, unknown> | undefined)?.composer_timeout_seconds || 180
          )}
        />
      )}

      {composition.candidates.map((candidate) => (
        <article className="agent-candidate-card" key={candidate.candidate_id}>
          <header>
            <div>
              <strong>{englishSystemText(candidate.label)}</strong>
              <small>{candidate.review.status === "valid" ? "Safety checks passed" : "Safety checks failed"}</small>
            </div>
            <span>{Math.round(candidate.review.overall_score * 100)}</span>
          </header>
          <p>{englishSystemText(candidate.explanation)}</p>
          <dl>
            <div><dt>Theory</dt><dd>{Math.round(candidate.review.theory_score * 100)}</dd></div>
            <div><dt>Motif</dt><dd>{Math.round(candidate.review.motif_score * 100)}</dd></div>
            <div><dt>Phrase</dt><dd>{Math.round(candidate.review.phrase_score * 100)}</dd></div>
            <div><dt>Style</dt><dd>{Math.round(candidate.review.style_score * 100)}</dd></div>
            <div><dt>Playability</dt><dd>{Math.round(candidate.review.playability_score * 100)}</dd></div>
            <div><dt>Expectation</dt><dd>{Math.round((candidate.review.melody_expectation_score ?? 0) * 100)}</dd></div>
            <div><dt>Preference</dt><dd>{Math.round(candidate.review.preference_score * 100)}</dd></div>
          </dl>
          <ul>
            {candidate.review.findings.map((finding) => (
              <li className={finding.passed ? "passed" : "failed"} key={finding.check}>
                <span aria-hidden="true">{finding.passed ? "✓" : "!"}</span>
                {compositionFindingLabel(finding.check)}
                <small>{finding.claim_id}</small>
              </li>
            ))}
          </ul>
          <div className="agent-candidate-actions">
            <button
              disabled={candidate.review.status !== "valid" || busy}
              onClick={() => onSelect(candidate)}
              type="button"
            >
              Select and review candidate
            </button>
            <button
              disabled={candidate.review.status !== "valid" || busy || !composition.comparison_id}
              onClick={() => onPrefer(candidate, preferenceReasons)}
              type="button"
            >
              Prefer this version
            </button>
          </div>
        </article>
      ))}

      {composition.theory_context.length > 0 && (
        <details className="agent-theory-trace">
          <summary>Theory references ({composition.theory_context.length})</summary>
          {composition.theory_context.map((item) => (
            <p key={item.claim_id}><strong>{item.claim_id} · {item.title}</strong><br />{item.rule}</p>
          ))}
        </details>
      )}
    </div>
  );
}

function CompositionFailurePanel({
  analysis,
  fallbackReason,
  refinementStatus,
  composerTimeoutSeconds
}: {
  analysis?: CompositionFailureAnalysis | null;
  fallbackReason: string;
  refinementStatus?: "running" | "ready" | "failed";
  composerTimeoutSeconds: number;
}) {
  const counts = analysis?.counts || {};
  const failedChecks = Object.entries(analysis?.failed_check_counts || {}).filter(([, value]) => value > 0);
  return (
    <section className="agent-composition-failure" role="alert">
      <div>
        <span aria-hidden="true">!</span>
        <div>
          <strong>{refinementStatus === "running" ? "Local candidates rejected; LLM planning continues" : "Candidates safely rejected"}</strong>
          <p>{englishSystemText(analysis?.summary || fallbackReason)}</p>
          {refinementStatus === "running" && (
            <p>
              LLM planning is still in progress. Sera will wait up to {Math.round(composerTimeoutSeconds)} seconds, then repeat the search and update diagnostics when the LLM responds.
            </p>
          )}
        </div>
      </div>
      {analysis && (
        <>
          <dl>
            <div><dt>Target notes</dt><dd>{counts.target_notes ?? 0}</dd></div>
            <div><dt>Protected</dt><dd>{counts.protected_target_notes ?? 0}</dd></div>
            <div><dt>Reviewed</dt><dd>{counts.evaluated ?? 0}</dd></div>
            <div><dt>Rejected</dt><dd>{counts.rejected ?? 0}</dd></div>
          </dl>
          {failedChecks.length > 0 && (
            <p className="agent-failure-checks">
              Failed checks: {failedChecks.map(([name, count]) => `${compositionFailureLabel(name)} ${count}`).join(" · ")}
            </p>
          )}
          <ol>
            {analysis.suggestions.map((suggestion, index) => <li key={index}>{englishSystemText(suggestion)}</li>)}
          </ol>
          {analysis.rejected_examples.length > 0 && (
            <details>
              <summary>Technical diagnostics ({analysis.code})</summary>
              {analysis.rejected_examples.map((example) => (
                <p key={example.candidate_id}>
                  {example.candidate_id} · {example.failed_checks.map(compositionFailureLabel).join(", ") || example.transaction_status}
                  {example.error_codes.length ? ` · ${example.error_codes.join(", ")}` : ""}
                </p>
              ))}
            </details>
          )}
        </>
      )}
    </section>
  );
}

function ProposalReview({
  generation,
  canApply,
  busy,
  onApply,
  onReject
}: {
  generation: StrictGenerationPreview;
  canApply: boolean;
  busy: boolean;
  onApply: () => void;
  onReject: () => void;
}) {
  const preview = generation.preview;
  const report = preview?.validation_report;
  const patch = generation.patch;
  const issues = [...(report?.errors || []), ...(report?.warnings || [])];
  const validated = canApply && report?.status !== "invalid";

  return (
    <div className="agent-proposal-content">
      <section className="agent-generator-evidence" aria-label="Patch generator evidence">
        <span>{generation.generator.composition_route ? "Composer automatic routing" : generation.generator.live ? "LLM API" : "Local rules"}</span>
        <strong>{generation.generator.provider} · {generation.generator.model}</strong>
        {typeof generation.generator.latency_ms === "number" && (
          <small>{Math.round(generation.generator.latency_ms)} ms</small>
        )}
        {generation.generator.composition_route && (
          <small>
            Reviewed {generation.generator.candidate_count || 0} candidates
            {generation.generator.evaluated_candidate_count
              ? `(internal search ${generation.generator.evaluated_candidate_count})`
              : ""}
            {typeof generation.generator.selected_candidate_score === "number"
              ? ` · Best score ${Math.round(generation.generator.selected_candidate_score * 100)}`
              : ""}
            {generation.generator.style_knowledge_version
              ? ` · Style library v${generation.generator.style_knowledge_version}`
              : ""}
          </small>
        )}
        {!generation.generator.composition_route && generation.generator.repair_strategy && generation.generator.repair_strategy !== "none" && (
          <small>
            Model output format repaired safely
            {generation.generator.generation_attempts && generation.generator.generation_attempts > 1
              ? ` · ${generation.generator.generation_attempts} requests`
              : ""}
          </small>
        )}
        {generation.generator.fallback_reason && (
          <small title={generation.generator.fallback_reason}>Safe fallback enabled</small>
        )}
        {patch?.target_scope.whole_score && generation.generator.scope_resolution === "promoted_to_whole_score_for_global_key_signature" && (
          <small>Key signature is a score-wide property. The selection was expanded to the whole score while note preservation constraints remain active.</small>
        )}
      </section>
      <div className={`agent-validation-state ${validated ? "valid" : "invalid"}`}>
        <span aria-hidden="true">{validated ? "✓" : "!"}</span>
        <div>
          <strong>{validated ? "Validation passed" : generation.status === "unsupported" ? "Unsupported edit" : "Cannot apply safely"}</strong>
          <p>{validated ? "The proposal is structurally valid and can be applied as a transaction." : englishSystemText(generation.reason) || "Review the validation details below."}</p>
        </div>
      </div>

      {!validated && generation.composition_evidence?.failure_analysis && (
        <CompositionFailurePanel
          analysis={generation.composition_evidence.failure_analysis}
          fallbackReason={generation.reason || "Composer candidates failed safety checks."}
        />
      )}

      {patch && (
        <section className="agent-operation-summary">
          <h2>Edit summary</h2>
          <ol>
            {patch.operations.map((operation, index) => (
              <li key={operation.operation_id || index}>
                <span>{index + 1}</span>
                <div>
                  <strong>{operationTitle(operation.type)}</strong>
                  <p>{operationDescription(operation)}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {preview && (
        <section className="agent-diff-summary">
          <h2>Element changes</h2>
          <dl>
            <div><dt>Changed</dt><dd>{preview.diff.changed?.length || 0}</dd></div>
            <div><dt>Added</dt><dd>{preview.diff.added?.length || 0}</dd></div>
            <div><dt>Deleted</dt><dd>{preview.diff.deleted?.length || 0}</dd></div>
            <div><dt>Global</dt><dd>{Object.keys(preview.diff.global_changes || {}).length}</dd></div>
          </dl>
        </section>
      )}

      <section className="agent-protected-state">
        <h2>Protected scope</h2>
        <p className={report?.errors.some((issue) => issue.code === "E11") ? "failed" : "passed"}>
          <span aria-hidden="true">{report?.errors.some((issue) => issue.code === "E11") ? "!" : "✓"}</span>
          {report?.errors.some((issue) => issue.code === "E11") ? "Protected scope violation detected" : "No unexpected changes outside the selection detected"}
        </p>
      </section>

      {issues.length > 0 && (
        <details className="agent-validation-details">
          <summary>Validation details ({issues.length})</summary>
          {issues.map((issue, index) => <ValidationIssue key={`${issue.code}-${index}`} issue={issue} />)}
        </details>
      )}

      <div className="agent-proposal-actions">
        <button disabled={!canApply || busy} onClick={onApply} type="button">Apply and create host revision</button>
        <button disabled={busy} onClick={onReject} type="button">Reject</button>
      </div>

      {patch && (
        <details className="agent-json-details">
          <summary>Proposal details (ScorePatch JSON)</summary>
          <pre>{JSON.stringify(patch, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

function ValidationIssue({ issue }: { issue: StrictValidationIssue }) {
  return <p><strong>{issue.code}</strong> · {englishSystemText(issue.message)}</p>;
}

function hostSelectedRange(score: ScoreDocument | null, session: any) {
  const selection = session?.host_context?.selection || {};
  const start = Number(selection.start_measure);
  const end = Number(selection.end_measure);
  if (selection.is_range && Number.isFinite(start) && Number.isFinite(end)) {
    return {
      start_measure: Math.max(1, Math.min(start, end)),
      end_measure: Math.max(1, Math.max(start, end))
    };
  }
  const firstMeasure = score?.measures?.[0]?.number || 1;
  return { start_measure: firstMeasure, end_measure: firstMeasure };
}

function hostDisplayName(hosts: HostCapability[], hostId = "") {
  return hosts.find((host) => host.host_id === hostId)?.display_name
    || FALLBACK_HOSTS.find((host) => host.host_id === hostId)?.display_name
    || hostId
    || "Notation host";
}

function hostMonogram(hostId: string) {
  if (hostId === "musescore") return "M";
  if (hostId === "sibelius") return "S";
  return "XML";
}

function operationTitle(type: string) {
  const titles: Record<string, string> = {
    transpose: "Transpose",
    set_pitch: "Set pitch",
    set_duration: "Set duration",
    insert_note: "Insert note",
    insert_rest: "Insert rest",
    delete_event: "Delete event",
    set_dynamic: "Set dynamic",
    set_articulation: "Set articulation",
    set_tie: "Set tie",
    set_slur: "Set slur",
    change_key_signature: "Change key signature",
    change_time_signature: "Change time signature",
    move_to_voice: "Move to voice",
    duplicate_motif: "Duplicate motif",
    replace_chord: "Replace chord",
    batch: "Batch edit"
  };
  return titles[type] || type.replaceAll("_", " ");
}

function operationDescription(operation: StrictScorePatch["operations"][number]) {
  const selector = operation.selector || {};
  const target = ["change_key_signature", "change_time_signature"].includes(operation.type)
    ? "Whole score"
    : selector.event_ids?.length
    ? `${selector.event_ids.length} events`
    : selector.measures?.length
      ? `Measures ${selector.measures.join(", ")}`
      : "Host selection";
  const argumentsText = Object.entries(operation.arguments || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join("; ");
  return `${target}${argumentsText ? ` · ${argumentsText}` : ""}`;
}

function compositionFindingLabel(check: string) {
  const labels: Record<string, string> = {
    host_scaffold_preserved: "Host structure preserved",
    chord_tone_anchoring: "Chord tone anchoring",
    cadence_resolution: "Cadence resolution",
    register_playability: "Register and playability",
    voice_leading: "Voice leading",
    motif_coherence: "Motif coherence",
    phrase_direction: "Phrase and tension direction",
    style_profile_match: "Style knowledge match",
    melodic_expectation: "Melodic expectation proxy",
    texture_structure_preserved: "Texture structure preserved"
  };
  return labels[check] || check.replaceAll("_", " ");
}

function compositionFailureLabel(check: string) {
  const labels: Record<string, string> = {
    transaction_validation: "Transaction validation",
    protected_scope: "Protected scope",
    rhythm_or_structure: "Rhythm and structure preserved",
    new_playability_conflict: "New playability conflict"
  };
  return labels[check] || check;
}
