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
  { host_id: "musicxml", display_name: "通用 MusicXML" }
];

const INITIAL_MESSAGES: AgentMessage[] = [
  {
    id: 1,
    role: "assistant",
    text: "你可以直接向我提问；普通对话不会修改乐谱。需要编辑时，请切换到“修改提案”，连接宿主后生成可验证的 ScorePatch。"
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
  const [status, setStatus] = useState("等待宿主连接");
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
            ? "实时 LLM 规划已完成，候选已自动更新；仍需选择后进入最终审查。"
            : "实时 LLM 高层规划已返回，但其实现候选仍未通过安全检查；下方诊断来自 LLM 计划后的实际搜索。");
          setStatus(hasCandidates
            ? `LLM 优化完成 · 已生成 ${payload.result.candidates.length} 个候选`
            : "LLM 已反馈 · 实现候选未通过安全检查");
          setCompositionRefinementJobId("");
          return;
        }
        if (payload.status === "failed") {
          setComposition((current) => current ? {
            ...current,
            refinement: { ...current.refinement!, status: "failed", error: payload.error || "模型未返回合法计划" }
          } : current);
          setCompositionRefinementNotice(`LLM 后台优化未完成：${payload.error || "模型未返回合法计划"}。当前本地候选仍可正常使用。`);
          setStatus("LLM 优化失败 · 已保留本地安全候选");
          setCompositionRefinementJobId("");
          return;
        }
        timer = window.setTimeout(poll, 1200);
      } catch (error: any) {
        if (cancelled) return;
        transientFailures += 1;
        if (transientFailures <= 5) {
          setCompositionRefinementNotice(
            `读取 LLM 后台状态时出现连接波动，正在重试（${transientFailures}/5）；当前本地结果不受影响。`
          );
          timer = window.setTimeout(poll, 2000);
          return;
        }
        setCompositionRefinementNotice(`连续 5 次无法读取 LLM 后台状态：${error?.message || "未知错误"}。当前本地结果仍可使用。`);
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
    setStatus("正在切换到最新宿主会话");
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
    setStatus("正在接收宿主上下文");
    getNotationBridgeWorkspace(sessionId)
      .then((payload) => {
        if (cancelled) return;
        loadBridgeWorkspace(payload);
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setStatus(`宿主会话加载失败：${error.message}`);
        appendMessage("assistant", `无法读取宿主会话：${error.message}`);
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
        text: `已从 ${hostDisplayName(hosts, nextSession?.host_id)} 接收《${nextScore.title || "未命名乐谱"}》和宿主选区 M${range.start_measure}–M${range.end_measure}。你可以继续对话；要编辑乐谱，请切换到“修改提案”。`
      }
    ]);
    setStatus(`已连接 ${hostDisplayName(hosts, nextSession?.host_id)}`);
  }

  async function handleMusicXmlImport(file: File) {
    setBusy(true);
    setStatus("正在导入宿主 MusicXML");
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
      setStatus(`MusicXML 导入失败：${error.message}`);
      appendMessage("assistant", `宿主文件没有成功导入：${error.message}`);
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
    setStatus("正在进行普通对话 · 不会修改乐谱");
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
        ? "对话完成 · 乐谱未修改"
        : `对话不可用 · ${payload.reason || "请检查模型设置"}`);
    } catch (error: any) {
      appendMessage("assistant", `对话请求失败：${error.message}。乐谱未修改。`);
      setStatus(`对话请求失败：${error.message}`);
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
    setStatus("正在生成并验证 ScorePatch");
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
            : "本地确定性编辑器";
        const repair = !payload.generator.composition_route && payload.generator.repair_strategy && payload.generator.repair_strategy !== "none"
          ? ` · ${payload.generator.repair_strategy} 修复`
          : "";
        setStatus(`已通过 ${engine} 生成提案 · ${validationStatus}${repair}`);
        setEditInstruction("");
      } else {
        setStatus(`${payload.reason || payload.status} · 乐谱未修改`);
      }
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      setStatus(`提案生成失败：${error.message}`);
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
    setStatus("正在规划和验证创作候选");
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
          ? `本地安全候选已就绪；实时 LLM 正在后台优化（最多等待 ${waitSeconds} 秒），你现在就可以先审查本地候选。`
          : `这 16 个只是本地初稿候选；实时 LLM 仍在后台规划（最多等待 ${waitSeconds} 秒），返回后会自动重新实现并更新诊断。`);
      } else if (payload.refinement?.status === "failed") {
        setCompositionRefinementNotice(`LLM 后台优化失败：${payload.refinement.error || "模型未返回合法计划"}。当前本地候选仍可使用。`);
      }
      if (payload.provider_status) setProviderStatus(payload.provider_status as unknown as ProviderStatus);
      if (payload.status === "generated") {
        setCompositionBrief("");
        setStatus(`已生成 ${payload.candidates.length} 个候选 · 全部保留宿主节奏与排版`);
      } else if (payload.refinement?.status === "running") {
        setStatus("本地候选未通过 · 正在等待实时 LLM 反馈");
      } else {
        setStatus(payload.reason || "当前创作简述不能安全生成候选");
      }
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      const message = error?.message || "未知错误";
      setCompositionError(message);
      setStatus(`创作候选生成失败：${message}`);
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
    setStatus(`${candidate.label} 已进入最终提案审查；尚未修改宿主乐谱`);
  }

  async function handlePreferCandidate(candidate: CompositionCandidate, reasons: CompositionPreferenceReason[]) {
    if (!composition?.comparison_id || !composition.plan) return;
    setBusy(true);
    setPreferenceNotice("正在记录本机偏好…");
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
        ? `已记录 ${candidate.label}；累计 ${payload.preference_profile.feedback_count} 次本机偏好。`
        : `${candidate.label} 的偏好已经记录过。`);
      setStatus("Composer 偏好已保存在本机；下一次候选排序会使用聚合画像");
    } catch (error: any) {
      setPreferenceNotice(`偏好未保存：${error?.message || "未知错误"}`);
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
    setStatus("正在应用事务并生成宿主修订");
    try {
      const beforeScore = scoreDocument;
      const applied = await applyStrictScorePatch(beforeScore, patch);
      if (activeSessionIdRef.current !== requestSessionId) return;
      if (!applied.committed) {
        setGeneration((current) => current ? { ...current, preview: applied } : current);
        setStatus(applied.rollback_reason || "事务已回滚，乐谱未修改");
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
      const notice = `修订 ${exported.revision} 已就绪。请返回 ${hostName}，点击“Refresh and open applied revision”。`;
      setDeliveryNotice(notice);
      setStatus(`宿主修订 ${exported.revision} 已就绪`);
    } catch (error: any) {
      if (activeSessionIdRef.current !== requestSessionId) return;
      setStatus(`宿主修订生成失败：${error.message}`);
    } finally {
      if (activeSessionIdRef.current === requestSessionId) setBusy(false);
    }
  }

  async function handleUndoAndExport() {
    if (!scoreDocument || !bridgeSession?.session_id) return;
    const undone = undoStrictPatch(history, scoreDocument);
    if (!undone) return;
    setBusy(true);
    setStatus("正在生成撤销修订");
    try {
      const exported = await exportNotationBridgeRevision(
        bridgeSession.session_id,
        undone.scoreDocument,
        Number(bridgeSession.revision || 0)
      );
      setScoreDocument(undone.scoreDocument);
      setHistory(undone.history);
      setBridgeSession(exported.session);
      const notice = `撤销修订 ${exported.revision} 已就绪。请在 ${hostName} 中打开最新修订。`;
      setDeliveryNotice(notice);
      setStatus(`撤销修订 ${exported.revision} 已就绪`);
    } catch (error: any) {
      setStatus(`撤销修订失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  function handleReject() {
    setGeneration(null);
    setGenerationSessionId("");
    setStatus("提案已拒绝 · 乐谱未修改");
  }

  return (
    <div className="agent-app-shell">
      <header className="agent-topbar">
        <div className="agent-brand">
          <div className="agent-brand-mark" aria-hidden="true">S</div>
          <div>
            <strong>Sera</strong>
            <span>智能乐谱编辑 Agent</span>
          </div>
        </div>
        <div className="agent-topbar-actions">
          {onOpenResearchReview && (
            <button className="agent-research-review-button" onClick={onOpenResearchReview} type="button">
              研究复核
            </button>
          )}
          <span className={`agent-backend-state ${backendCapabilities?.api_contract ? "ready" : "waiting"}`}>
            <i aria-hidden="true" />
            {backendCapabilities?.api_contract ? "后端已就绪" : "检查后端"}
          </span>
          <span
            aria-label="Agent provider status"
            className={`agent-provider-state ${providerStatus?.available ? "live" : "local"}`}
            title={providerStatus?.reason || "正在读取 Agent provider 状态"}
          >
            <i aria-hidden="true" />
            {providerStatus?.available
              ? `${providerStatus.provider} · ${providerStatus.model}`
              : "本地规则"}
          </span>
          <button
            className="agent-provider-settings-button"
            onClick={() => setProviderSettingsOpen(true)}
            type="button"
          >
            模型设置
          </button>
          <LanguageSelector />
        </div>
      </header>

      <main className="agent-console-grid">
        <aside className="agent-connection-rail">
          <div>
            <h1>连接记谱宿主</h1>
            <p>乐谱显示与手工记谱始终留在专业宿主软件中。</p>
          </div>

          <section className="agent-rail-section">
            <h2>选择宿主</h2>
            <div className="agent-host-list" role="radiogroup" aria-label="选择记谱宿主">
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
            <h2>连接步骤</h2>
            <ol>
              <li><span>1</span><p>在宿主中打开目标乐谱</p></li>
              <li><span>2</span><p>选择需要 Agent 修改的范围</p></li>
              <li><span>3</span><p>运行 Sera Bridge 并返回此窗口</p></li>
            </ol>
          </section>

          <section className="agent-rail-section agent-session-summary">
            <h2>连接状态</h2>
            <p className={connected ? "connected" : "disconnected"}>
              <i aria-hidden="true" />
              {connected ? `已连接到 ${hostName}` : "等待宿主发送乐谱"}
            </p>
            {connected && scoreDocument && (
              <dl>
                <div><dt>当前乐谱</dt><dd>{scoreDocument.title || "未命名乐谱"}</dd></div>
                <div><dt>宿主选区</dt><dd>M{selectedRange.start_measure}–M{selectedRange.end_measure}</dd></div>
                <div><dt>修订</dt><dd>{bridgeSession.revision ?? 0}</dd></div>
              </dl>
            )}
          </section>

          <div className="agent-import-action">
            <input
              accept=".musicxml,.xml"
              aria-label="导入宿主 MusicXML 文件"
              className="agent-visually-hidden"
              onChange={(event) => event.target.files?.[0] && handleMusicXmlImport(event.target.files[0])}
              ref={fileInputRef}
              type="file"
            />
            <button disabled={busy} onClick={() => fileInputRef.current?.click()} type="button">
              导入宿主 MusicXML
            </button>
            <small>MuseScore Bridge 不可用时的非破坏式后备路径</small>
          </div>
        </aside>

        <section className="agent-conversation" aria-label="与 Sera 对话">
          <header>
            <h1>与 Sera 对话</h1>
            <p>普通问答不会触碰乐谱；编辑指令通过独立的受验证提案通道处理。</p>
          </header>
          <div className="agent-message-list" aria-live="polite">
            {messages.map((message) => (
              <article className={`agent-message ${message.role}`} key={message.id}>
                <span className="agent-avatar" aria-hidden="true">{message.role === "assistant" ? "S" : "你"}</span>
                <div>
                  <strong>{message.role === "assistant" ? "Sera" : "你"}</strong>
                  <p>{message.text}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="agent-composer">
            <div className="agent-composer-mode" role="tablist" aria-label="选择对话、修改提案或创作草案">
              <button
                aria-selected={composerMode === "chat"}
                className={composerMode === "chat" ? "selected" : ""}
                onClick={() => setComposerMode("chat")}
                role="tab"
                type="button"
              >
                对话
                <small>只回答，不改乐谱</small>
              </button>
              <button
                aria-selected={composerMode === "edit"}
                className={composerMode === "edit" ? "selected" : ""}
                onClick={() => setComposerMode("edit")}
                role="tab"
                type="button"
              >
                修改提案
                <small>生成并验证 ScorePatch</small>
              </button>
              <button
                aria-selected={composerMode === "compose"}
                className={composerMode === "compose" ? "selected" : ""}
                onClick={() => setComposerMode("compose")}
                role="tab"
                type="button"
              >
                创作草案
                <small>理论规划 · 多候选 · 再审查</small>
              </button>
            </div>
            {composerMode === "chat" ? (
              <>
                <textarea
                  aria-label="向 Sera 提问"
                  disabled={busy}
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleChat();
                  }}
                  placeholder="询问乐理、Sera 用法，或让 Sera 帮你把编辑意图说清楚…"
                  rows={5}
                  value={chatInput}
                />
                <div className="agent-composer-footer">
                  <span>对话回答不会生成、应用或导出乐谱修改</span>
                  <button disabled={busy || !chatInput.trim()} onClick={handleChat} type="button">
                    {busy ? "处理中…" : "发送消息"}
                  </button>
                </div>
              </>
            ) : composerMode === "edit" ? (
              <>
                <textarea
                  aria-label="描述乐谱修改"
                  disabled={!connected || busy}
                  onChange={(event) => setEditInstruction(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleGenerate();
                  }}
                  placeholder={connected ? "例如：将当前选区升高大二度，并保持节奏不变…" : "请先连接记谱宿主，再生成修改提案…"}
                  rows={5}
                  value={editInstruction}
                />
                <div className="agent-composer-footer">
                  <span>{connected ? `绑定宿主目标范围：M${selectedRange.start_measure}–M${selectedRange.end_measure}` : "修改提案需要宿主乐谱与选区"}</span>
                  <button disabled={!connected || busy || !editInstruction.trim()} onClick={handleGenerate} type="button">
                    {busy ? "生成并验证中…" : "生成修改提案"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <textarea
                  aria-label="描述创作目标"
                  disabled={!connected || busy}
                  onChange={(event) => setCompositionBrief(event.target.value)}
                  onKeyDown={(event) => {
                    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") handleCompose();
                  }}
                  placeholder={connected
                    ? "例如：把当前选区改写成有清晰终止的浪漫主义钢琴段落，保留节奏和配器…"
                    : "请先连接记谱宿主并选择 1–8 个小节…"}
                  rows={5}
                  value={compositionBrief}
                />
                <div className="agent-composer-footer">
                  <span>{connected
                    ? `基于宿主节奏骨架：M${selectedRange.start_measure}–M${selectedRange.end_measure}`
                    : "创作草案需要宿主乐谱与选区"}</span>
                  <button disabled={!connected || busy || !compositionBrief.trim()} onClick={handleCompose} type="button">
                    {compositionRunning ? `规划中 ${compositionElapsedSeconds}s` : "生成创作候选"}
                  </button>
                </div>
              </>
            )}
          </div>
        </section>

        <aside className="agent-proposal-rail">
          <header>
            <h1>{composition && !generation ? "创作候选" : "修改提案"}</h1>
            <p>{composition && !generation
              ? "候选共享同一个理论计划，并分别通过确定性乐理与宿主安全检查。"
              : "与普通对话分离；这里只审查、应用或拒绝受验证的 Agent 修改。"}</p>
          </header>
          {!generation && !composition && !deliveryNotice && !compositionRunning && !compositionError && (
            <div className="agent-proposal-empty">
              <strong>{connected ? "等待编辑指令" : "尚未连接宿主"}</strong>
              <p>{connected ? "生成后将在此显示操作摘要、验证结果和保护范围检查。" : "从宿主发送乐谱后即可开始。"}</p>
            </div>
          )}
          {compositionRunning && !generation && !composition && (
            <section className="agent-composition-progress" role="status" aria-live="polite">
              <div>
                <span className="agent-progress-spinner" aria-hidden="true" />
                <strong>{compositionProgressMessage(compositionElapsedSeconds)}</strong>
              </div>
              <progress max={20} value={Math.min(compositionElapsedSeconds, 20)} />
              <p>已运行 {compositionElapsedSeconds} 秒。Sera 正在先生成本地安全初稿，LLM 不再阻塞这个步骤。</p>
              <small>初稿出现后即可使用；实时 LLM 会在后台继续优化并自动更新候选。</small>
            </section>
          )}
          {compositionError && !compositionRunning && !generation && !composition && (
            <section className="agent-composition-error" role="alert">
              <strong>创作候选没有生成</strong>
              <p>{compositionError}</p>
              <small>请确认模型 API 可用，或在“模型设置”中切换为本地规则后重试。</small>
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
              <strong>宿主修订已生成</strong>
              <p>{deliveryNotice}</p>
            </div>
          )}
          {history.done.length > 0 && !generation && (
            <button className="agent-undo-revision" disabled={busy} onClick={handleUndoAndExport} type="button">
              撤销上次 Agent 修订
            </button>
          )}
          <footer>{status}</footer>
        </aside>
      </main>
      {providerSettingsOpen && (
        <LLMProviderSettingsDialog
          currentStatus={providerStatus}
          onClose={() => setProviderSettingsOpen(false)}
          onSaved={(nextStatus) => {
            setProviderStatus(nextStatus);
            setStatus(nextStatus.available
              ? `已启用 ${nextStatus.provider} · ${nextStatus.model}`
              : "已切换为本地规则");
          }}
        />
      )}
    </div>
  );
}

function compositionProgressMessage(elapsedSeconds: number) {
  if (elapsedSeconds < 4) return "正在读取宿主选区与理论约束";
  if (elapsedSeconds < 16) return "正在生成本地初稿并执行安全评审";
  return "正在完成本地候选；LLM 已转入后台优化";
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
    { value: "motif", label: "动机更清楚" },
    { value: "phrase", label: "乐句更自然" },
    { value: "harmony", label: "和声更合适" },
    { value: "style", label: "风格更准确" },
    { value: "playability", label: "更易演奏" }
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
          <p>动机：{plan.motif_strategy} · 张力曲线：{plan.tension_curve.map((value) => Math.round(value * 100)).join(" / ")}</p>
        </section>
      )}

      <section className={`agent-planner-source ${composition.planner.planner === "live_llm" ? "live" : "local"}`} aria-label="本次规划来源">
        <div>
          <strong>{composition.planner.planner === "live_llm"
            ? "本次高层计划：实时 LLM"
            : composition.refinement?.status === "running"
              ? "本次高层计划：本地即时初稿"
              : "本次高层计划：本地理论回退"}</strong>
          <span>{composition.planner.provider || "local_rule"} · {composition.planner.model || "sera_composer_rules_v1"}</span>
        </div>
        <p>
          {typeof composition.planner.latency_ms === "number" ? `${Math.round(composition.planner.latency_ms)} ms` : "耗时未知"}
          {composition.planner.request_id ? ` · request ${composition.planner.request_id}` : ""}
          {composition.run_trace?.persisted ? ` · 审计 ${composition.run_trace.trace_id}` : ""}
        </p>
        {composition.planner.planner !== "live_llm" && composition.planner.fallback_reason && (
          <small>{composition.planner.fallback_reason}</small>
        )}
      </section>

      {refinementNotice && (
        <section className={`agent-refinement-notice ${composition.refinement?.status || "ready"}`} role="status" aria-live="polite">
          <strong>{composition.refinement?.status === "running" ? "LLM 正在后台优化" : "LLM 后台状态"}</strong>
          <p>{refinementNotice}</p>
        </section>
      )}

      {composition.style_knowledge && (
        <section className="agent-style-knowledge" aria-label="风格知识库证据">
          <div>
            <strong>Composer V0.4 知识检索 · {composition.style_knowledge.display_name_zh}</strong>
            <span>v{composition.style_knowledge.schema_version}</span>
          </div>
          <p>
            本地大库 {composition.style_knowledge.retrieval.total_cards} 张规则卡 / {composition.style_knowledge.retrieval.pack_count} 个知识包；
            本次只选 {composition.style_knowledge.retrieval.selected_cards} 张，约 {composition.style_knowledge.retrieval.estimated_tokens}/{composition.style_knowledge.retrieval.token_budget} tokens。
          </p>
          <p>
            乐器 {composition.style_knowledge.query.instruments.join("、") || "通用"} ·
            目标 {composition.style_knowledge.query.goals.join("、") || "通用"} ·
            内部评审 {composition.search_summary.evaluated}/{composition.search_summary.search_width} 个候选，展示 {composition.search_summary.returned} 个。
          </p>
          {composition.texture_analysis && (
            <p>
              原谱织体 {composition.texture_analysis.texture}（{Math.round(composition.texture_analysis.confidence * 100)}%） ·
              {" "}{composition.texture_analysis.voice_count} 个活动声部 · 计划目标 {plan?.texture || "未指定"}
            </p>
          )}
          <details className="agent-knowledge-rules">
            <summary>查看本次检索规则（{composition.style_knowledge.matched_rules.length}）</summary>
            <ol>
              {composition.style_knowledge.matched_rules.map((rule) => (
                <li key={rule.rule_id}>
                  <div><strong>{rule.title_zh}</strong><span>{rule.domain}</span></div>
                  <p>{rule.action_zh}</p>
                  <small>{rule.rule_id} · {rule.match_reason}</small>
                </li>
              ))}
            </ol>
          </details>
          {composition.phrase_analysis && (
            <small>
              原谱主线 {composition.phrase_analysis.primary_voice_id || "未识别"} ·
              轮廓 {composition.phrase_analysis.source_motif.contour} ·
              动机间隔 {composition.phrase_analysis.source_motif.intervals.join(" / ") || "不足"}
            </small>
          )}
        </section>
      )}

      {composition.candidates.length > 0 && (
        <fieldset className="agent-preference-reasons">
          <legend>比较候选时，你更看重什么？（可选）</legend>
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
          <small>只在本机保存候选评分与选择，不保存乐谱音符或个人身份。</small>
        </fieldset>
      )}

      {preferenceNotice && <p className="agent-preference-notice" role="status">{preferenceNotice}</p>}

      {composition.status === "plan_only" && (
        <section className="agent-composition-plan-only">
          <strong>仅生成方案，不直接应用</strong>
          <p>{composition.reason}</p>
          {plan?.orchestration_notes?.map((note, index) => <p key={index}>• {note}</p>)}
        </section>
      )}

      {composition.status === "unsupported" && (
        <CompositionFailurePanel
          analysis={composition.failure_analysis}
          fallbackReason={composition.reason}
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
              <strong>{candidate.label}</strong>
              <small>{candidate.review.status === "valid" ? "通过安全检查" : "未通过安全检查"}</small>
            </div>
            <span>{Math.round(candidate.review.overall_score * 100)}</span>
          </header>
          <p>{candidate.explanation}</p>
          <dl>
            <div><dt>理论</dt><dd>{Math.round(candidate.review.theory_score * 100)}</dd></div>
            <div><dt>动机</dt><dd>{Math.round(candidate.review.motif_score * 100)}</dd></div>
            <div><dt>乐句</dt><dd>{Math.round(candidate.review.phrase_score * 100)}</dd></div>
            <div><dt>风格</dt><dd>{Math.round(candidate.review.style_score * 100)}</dd></div>
            <div><dt>演奏</dt><dd>{Math.round(candidate.review.playability_score * 100)}</dd></div>
            <div><dt>期待</dt><dd>{Math.round((candidate.review.melody_expectation_score ?? 0) * 100)}</dd></div>
            <div><dt>偏好</dt><dd>{Math.round(candidate.review.preference_score * 100)}</dd></div>
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
              选择此候选并审查
            </button>
            <button
              disabled={candidate.review.status !== "valid" || busy || !composition.comparison_id}
              onClick={() => onPrefer(candidate, preferenceReasons)}
              type="button"
            >
              我更喜欢这个版本
            </button>
          </div>
        </article>
      ))}

      {composition.theory_context.length > 0 && (
        <details className="agent-theory-trace">
          <summary>理论依据（{composition.theory_context.length}）</summary>
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
          <strong>{refinementStatus === "running" ? "本地候选已拒绝，LLM 仍在后台规划" : "候选已安全拒绝"}</strong>
          <p>{analysis?.summary || fallbackReason}</p>
          {refinementStatus === "running" && (
            <p>
              这不是 LLM 最终反馈。Sera 最多等待 {Math.round(composerTimeoutSeconds)} 秒；LLM 返回后会自动重新搜索并替换本诊断。
            </p>
          )}
        </div>
      </div>
      {analysis && (
        <>
          <dl>
            <div><dt>目标音符</dt><dd>{counts.target_notes ?? 0}</dd></div>
            <div><dt>受保护</dt><dd>{counts.protected_target_notes ?? 0}</dd></div>
            <div><dt>已评审</dt><dd>{counts.evaluated ?? 0}</dd></div>
            <div><dt>已拒绝</dt><dd>{counts.rejected ?? 0}</dd></div>
          </dl>
          {failedChecks.length > 0 && (
            <p className="agent-failure-checks">
              失败层：{failedChecks.map(([name, count]) => `${compositionFailureLabel(name)} ${count}`).join(" · ")}
            </p>
          )}
          <ol>
            {analysis.suggestions.map((suggestion, index) => <li key={index}>{suggestion}</li>)}
          </ol>
          {analysis.rejected_examples.length > 0 && (
            <details>
              <summary>技术诊断（{analysis.code}）</summary>
              {analysis.rejected_examples.map((example) => (
                <p key={example.candidate_id}>
                  {example.candidate_id} · {example.failed_checks.map(compositionFailureLabel).join("、") || example.transaction_status}
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
        <span>{generation.generator.composition_route ? "Composer 自动路由" : generation.generator.live ? "LLM API" : "本地规则"}</span>
        <strong>{generation.generator.provider} · {generation.generator.model}</strong>
        {typeof generation.generator.latency_ms === "number" && (
          <small>{Math.round(generation.generator.latency_ms)} ms</small>
        )}
        {generation.generator.composition_route && (
          <small>
            已评审 {generation.generator.candidate_count || 0} 个候选
            {generation.generator.evaluated_candidate_count
              ? `（内部搜索 ${generation.generator.evaluated_candidate_count}）`
              : ""}
            {typeof generation.generator.selected_candidate_score === "number"
              ? ` · 最佳评分 ${Math.round(generation.generator.selected_candidate_score * 100)}`
              : ""}
            {generation.generator.style_knowledge_version
              ? ` · 风格库 v${generation.generator.style_knowledge_version}`
              : ""}
          </small>
        )}
        {!generation.generator.composition_route && generation.generator.repair_strategy && generation.generator.repair_strategy !== "none" && (
          <small>
            已安全修正模型输出格式
            {generation.generator.generation_attempts && generation.generator.generation_attempts > 1
              ? ` · ${generation.generator.generation_attempts} 次请求`
              : ""}
          </small>
        )}
        {generation.generator.fallback_reason && (
          <small title={generation.generator.fallback_reason}>已启用安全回退</small>
        )}
        {patch?.target_scope.whole_score && generation.generator.scope_resolution === "promoted_to_whole_score_for_global_key_signature" && (
          <small>调号是全谱属性；已将宿主选区安全提升为全谱范围，音符仍受保持约束。</small>
        )}
      </section>
      <div className={`agent-validation-state ${validated ? "valid" : "invalid"}`}>
        <span aria-hidden="true">{validated ? "✓" : "!"}</span>
        <div>
          <strong>{validated ? "验证通过" : generation.status === "unsupported" ? "不支持此修改" : "不可安全应用"}</strong>
          <p>{validated ? "提案结构有效，可按事务方式应用。" : generation.reason || "请检查下方验证信息。"}</p>
        </div>
      </div>

      {!validated && generation.composition_evidence?.failure_analysis && (
        <CompositionFailurePanel
          analysis={generation.composition_evidence.failure_analysis}
          fallbackReason={generation.reason || "Composer 候选未通过安全检查。"}
        />
      )}

      {patch && (
        <section className="agent-operation-summary">
          <h2>修改摘要</h2>
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
          <h2>元素变化</h2>
          <dl>
            <div><dt>修改</dt><dd>{preview.diff.changed?.length || 0}</dd></div>
            <div><dt>新增</dt><dd>{preview.diff.added?.length || 0}</dd></div>
            <div><dt>删除</dt><dd>{preview.diff.deleted?.length || 0}</dd></div>
            <div><dt>全局</dt><dd>{Object.keys(preview.diff.global_changes || {}).length}</dd></div>
          </dl>
        </section>
      )}

      <section className="agent-protected-state">
        <h2>保护范围</h2>
        <p className={report?.errors.some((issue) => issue.code === "E11") ? "failed" : "passed"}>
          <span aria-hidden="true">{report?.errors.some((issue) => issue.code === "E11") ? "!" : "✓"}</span>
          {report?.errors.some((issue) => issue.code === "E11") ? "发现保护范围违规" : "未发现选区外意外修改"}
        </p>
      </section>

      {issues.length > 0 && (
        <details className="agent-validation-details">
          <summary>验证信息（{issues.length}）</summary>
          {issues.map((issue, index) => <ValidationIssue key={`${issue.code}-${index}`} issue={issue} />)}
        </details>
      )}

      <div className="agent-proposal-actions">
        <button disabled={!canApply || busy} onClick={onApply} type="button">应用并生成宿主修订</button>
        <button disabled={busy} onClick={onReject} type="button">拒绝</button>
      </div>

      {patch && (
        <details className="agent-json-details">
          <summary>提案详情（ScorePatch JSON）</summary>
          <pre>{JSON.stringify(patch, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

function ValidationIssue({ issue }: { issue: StrictValidationIssue }) {
  return <p><strong>{issue.code}</strong> · {issue.message}</p>;
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
    || "记谱宿主";
}

function hostMonogram(hostId: string) {
  if (hostId === "musescore") return "M";
  if (hostId === "sibelius") return "S";
  return "XML";
}

function operationTitle(type: string) {
  const titles: Record<string, string> = {
    transpose: "移调",
    set_pitch: "修改音高",
    set_duration: "修改时值",
    insert_note: "插入音符",
    insert_rest: "插入休止符",
    delete_event: "删除记谱事件",
    set_dynamic: "修改力度",
    set_articulation: "修改演奏法",
    set_tie: "修改延音线",
    set_slur: "修改连音线",
    change_key_signature: "修改调号",
    change_time_signature: "修改拍号",
    move_to_voice: "移动到声部",
    duplicate_motif: "复制动机",
    replace_chord: "替换和弦",
    batch: "批量修改"
  };
  return titles[type] || type.replaceAll("_", " ");
}

function operationDescription(operation: StrictScorePatch["operations"][number]) {
  const selector = operation.selector || {};
  const target = ["change_key_signature", "change_time_signature"].includes(operation.type)
    ? "全谱"
    : selector.event_ids?.length
    ? `${selector.event_ids.length} 个事件`
    : selector.measures?.length
      ? `小节 ${selector.measures.join("、")}`
      : "宿主选区";
  const argumentsText = Object.entries(operation.arguments || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join("；");
  return `${target}${argumentsText ? ` · ${argumentsText}` : ""}`;
}

function compositionFindingLabel(check: string) {
  const labels: Record<string, string> = {
    host_scaffold_preserved: "宿主骨架保持",
    chord_tone_anchoring: "和弦骨干音",
    cadence_resolution: "终止解决",
    register_playability: "音域与可演奏性",
    voice_leading: "声部进行",
    motif_coherence: "动机一致性",
    phrase_direction: "乐句与张力方向",
    style_profile_match: "风格知识匹配",
    melodic_expectation: "旋律期待代理",
    texture_structure_preserved: "织体骨架保持"
  };
  return labels[check] || check.replaceAll("_", " ");
}

function compositionFailureLabel(check: string) {
  const labels: Record<string, string> = {
    transaction_validation: "事务验证",
    protected_scope: "保护范围",
    rhythm_or_structure: "节奏/结构保持",
    new_playability_conflict: "新增可演奏性冲突"
  };
  return labels[check] || check;
}
