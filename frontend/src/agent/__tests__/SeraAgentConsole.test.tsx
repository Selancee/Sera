import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import SeraAgentConsole from "../SeraAgentConsole";

const api = vi.hoisted(() => ({
  applyStrictScorePatch: vi.fn(),
  chatWithSera: vi.fn(),
  createNotationBridgeSession: vi.fn(),
  exportNotationBridgeRevision: vi.fn(),
  generateStrictScorePatchPreview: vi.fn(),
  getCompositionRefinement: vi.fn(),
  getSeraEditProviderStatus: vi.fn(),
  getNotationBridgeWorkspace: vi.fn(),
  getNotationHosts: vi.fn(),
  previewCompositionCandidates: vi.fn(),
  submitCompositionPreference: vi.fn(),
  saveSeraEditProviderConfiguration: vi.fn(),
  clearSeraEditProviderConfiguration: vi.fn()
}));

const desktop = vi.hoisted(() => ({
  readPendingDesktopSession: vi.fn(() => ({ session_id: "" })),
  subscribeDesktopOpenSession: vi.fn(() => () => undefined)
}));

vi.mock("../../api.js", () => api);
vi.mock("../../desktop/desktopRuntime", () => desktop);

const validation = {
  status: "valid" as const,
  errors: [],
  warnings: [],
  checks: {},
  repairable: false,
  suggested_repairs: []
};

describe("SeraAgentConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/");
    window.localStorage.setItem("sera.language", "zh-CN");
    api.getNotationHosts.mockResolvedValue({
      hosts: [
        { host_id: "musescore", display_name: "MuseScore Studio" },
        { host_id: "sibelius", display_name: "Avid Sibelius Ultimate" }
      ]
    });
    api.getSeraEditProviderStatus.mockResolvedValue({
      mode: "local_rule",
      provider: "local_rule",
      model: "seraedit_rule_v1",
      available: false,
      transport: "local",
      api_key_configured: false,
      in_app_configuration: true,
      reason: "Local fallback"
    });
    api.submitCompositionPreference.mockResolvedValue({
      recorded: true,
      feedback_id: "pref_test",
      preference_profile: {
        schema_version: "0.2.0",
        feedback_count: 1,
        dimension_targets: { motif: 0.88 },
        reason_counts: { motif: 1, phrase: 0, style: 0, harmony: 0, playability: 0 },
        preferred_styles: { classical: 1 },
        active: true,
        privacy: { local_only: true, stores_score_content: false, stores_user_identity: false }
      }
    });
    desktop.readPendingDesktopSession.mockReturnValue({ session_id: "" });
    desktop.subscribeDesktopOpenSession.mockReturnValue(() => undefined);
  });

  it("keeps the default product focused on host connection, conversation, and proposal review", async () => {
    renderConsole();

    await waitFor(() => expect(api.getNotationHosts).toHaveBeenCalledOnce());
    await waitFor(() => expect(api.getSeraEditProviderStatus).toHaveBeenCalledOnce());

    expect(screen.getByLabelText("Agent provider status").textContent).toContain("本地规则");
    expect(screen.getByText("连接记谱宿主")).toBeTruthy();
    expect(screen.getByText("与 Sera 对话")).toBeTruthy();
    expect(screen.getAllByText("修改提案").length).toBeGreaterThanOrEqual(2);
    expect((screen.getByRole("button", { name: "发送消息" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("tab", { name: /修改提案/ }));
    expect((screen.getByRole("button", { name: "生成修改提案" }) as HTMLButtonElement).disabled).toBe(true);

    expect(screen.queryByText("音符输入")).toBeNull();
    expect(screen.queryByText("Score Inspector")).toBeNull();
    expect(screen.queryByText("Operation History")).toBeNull();
    expect(screen.queryByText("Play")).toBeNull();
  });

  it("answers ordinary conversation without a host and never starts patch generation", async () => {
    api.chatWithSera.mockResolvedValue({
      status: "answered",
      answer: "大二度通常等于两个半音。这个回答不会修改乐谱。",
      reason: null,
      generator: {
        provider: "openai",
        model: "test-chat-model",
        transport: "responses",
        live: true,
        prompt_version: "sera_conversation_v1.0"
      }
    });
    renderConsole();
    await waitFor(() => expect(api.getSeraEditProviderStatus).toHaveBeenCalledOnce());

    fireEvent.change(screen.getByLabelText("向 Sera 提问"), { target: { value: "大二度是多少个半音？" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

    await screen.findByText(/大二度通常等于两个半音/);
    expect(api.chatWithSera).toHaveBeenCalledWith(
      "大二度是多少个半音？",
      expect.any(Array),
      null,
      {}
    );
    expect(api.generateStrictScorePatchPreview).not.toHaveBeenCalled();
    expect(screen.queryByText("验证通过")).toBeNull();
  });

  it("configures a live provider inside Sera without retaining the key in the rendered UI", async () => {
    api.saveSeraEditProviderConfiguration.mockResolvedValue({
      saved: true,
      status: {
        mode: "live_llm",
        provider: "openai",
        model: "gpt-5.6-terra",
        base_url: "https://api.openai.com/v1",
        available: true,
        configured: true,
        api_key_configured: true,
        credential_storage: "windows_dpapi",
        in_app_configuration: true,
        transport: "responses",
        fallback_local: true,
        reasoning_effort: "low",
        composer_timeout_seconds: 180,
        reason: "Live LLM provider is ready."
      }
    });
    renderConsole();
    await waitFor(() => expect(api.getSeraEditProviderStatus).toHaveBeenCalledOnce());

    fireEvent.click(screen.getByRole("button", { name: "模型设置" }));
    expect(screen.getByRole("dialog", { name: "模型与 API 设置" })).toBeTruthy();
    const keyInput = screen.getByLabelText("API Key") as HTMLInputElement;
    expect(keyInput.type).toBe("password");
    fireEvent.change(keyInput, { target: { value: "secret-only-in-request" } });
    fireEvent.click(screen.getByRole("button", { name: "保存并启用" }));

    await waitFor(() => expect(api.saveSeraEditProviderConfiguration).toHaveBeenCalledWith({
      provider: "openai",
      model: "gpt-5.6-terra",
      base_url: "https://api.openai.com/v1",
      api_key: "secret-only-in-request",
      fallback_local: true,
      reasoning_effort: "low",
      composer_timeout_seconds: 180
    }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "模型与 API 设置" })).toBeNull());
    expect(screen.getByLabelText("Agent provider status").textContent).toContain("openai · gpt-5.6-terra");
    expect(document.body.textContent).not.toContain("secret-only-in-request");
    const storedValues = Array.from(
      { length: window.localStorage.length },
      (_, index) => window.localStorage.getItem(window.localStorage.key(index) || "")
    );
    expect(storedValues).not.toContain("secret-only-in-request");
  });

  it("can remove the saved provider and return to local rules", async () => {
    api.clearSeraEditProviderConfiguration.mockResolvedValue({
      saved: true,
      status: {
        mode: "local_rule",
        provider: "local_rule",
        model: "seraedit_rule_v1",
        available: false,
        transport: "local",
        api_key_configured: false,
        credential_storage: "none",
        in_app_configuration: true,
        reason: "Using local rules."
      }
    });
    renderConsole();
    await waitFor(() => expect(api.getSeraEditProviderStatus).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole("button", { name: "模型设置" }));
    fireEvent.click(screen.getByRole("button", { name: "使用本地规则" }));

    await waitFor(() => expect(api.clearSeraEditProviderConfiguration).toHaveBeenCalledOnce());
    expect(screen.getByLabelText("Agent provider status").textContent).toContain("本地规则");
  });

  it("loads a host session, generates a validated patch, and exports a new host revision", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Host Score";
    const session = {
      session_id: "bridge_test_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_test_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    api.generateStrictScorePatchPreview.mockResolvedValue({
      status: "generated",
      reason: null,
      matched_intents: ["transpose"],
      generator: { provider: "local_rule", model: "seraedit_rule_v1", formal_experiment_eligible: false },
      patch: {
        schema_version: "1.0.0",
        patch_id: "patch_1",
        source_score_id: score.score_id,
        source_fingerprint: "sha256:source",
        instruction: "升高大二度",
        target_scope: { measures: [1, 2] },
        protected_scope: {},
        preconditions: [],
        operations: [{
          operation_id: "op_1",
          type: "transpose",
          selector: { measures: [1, 2] },
          arguments: { semitones: 2 },
          preconditions: [],
          expected_change_count: 2
        }],
        expected_effects: [],
        provenance: {}
      },
      preview: {
        committed: false,
        score_document: score,
        proposed_score_document: score,
        validation_report: validation,
        diff: { added: [], deleted: [], changed: [{ id: "e1" }], global_changes: {}, changed_element_count: 1 },
        audit: [],
        source_fingerprint: "sha256:source",
        post_fingerprint: "sha256:after",
        musicxml: null,
        rollback_reason: null
      }
    });
    api.applyStrictScorePatch.mockResolvedValue({
      committed: true,
      score_document: score,
      proposed_score_document: score,
      validation_report: validation,
      diff: { added: [], deleted: [], changed: [{ id: "e1" }], global_changes: {}, changed_element_count: 1 },
      audit: [],
      source_fingerprint: "sha256:source",
      post_fingerprint: "sha256:after",
      musicxml: null,
      rollback_reason: null
    });
    api.exportNotationBridgeRevision.mockResolvedValue({
      revision: 1,
      session: { ...session, revision: 1 }
    });

    renderConsole();

    await screen.findByText(/已从 MuseScore Studio 接收《Host Score》/);
    expect(screen.getByText("M1–M2")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: /修改提案/ }));
    fireEvent.change(screen.getByLabelText("描述乐谱修改"), { target: { value: "将选区升高大二度" } });
    fireEvent.click(screen.getByRole("button", { name: "生成修改提案" }));

    await screen.findByText("验证通过");
    expect(screen.getByText("移调")).toBeTruthy();
    expect(api.generateStrictScorePatchPreview).toHaveBeenCalledWith(
      score,
      "将选区升高大二度",
      { measures: [1, 2] },
      {}
    );

    fireEvent.click(screen.getByRole("button", { name: "应用并生成宿主修订" }));
    await waitFor(() => expect(screen.getAllByText(/修订 1 已就绪/).length).toBeGreaterThan(0));
    expect(api.applyStrictScorePatch).toHaveBeenCalledOnce();
    expect(api.exportNotationBridgeRevision).toHaveBeenCalledWith(session.session_id, score, 0);
  });

  it("invalidates an old proposal immediately when a newer host session arrives", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Old Host Score";
    const oldSession = {
      session_id: "bridge_old_12345678",
      host_id: "musescore",
      revision: 3,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    let notifyDesktopSession: (payload: { sequence: number; session_id: string }) => void = () => undefined;
    desktop.subscribeDesktopOpenSession.mockImplementation((callback) => {
      notifyDesktopSession = callback;
      return () => undefined;
    });
    window.history.replaceState({}, "", "/?bridge_session=bridge_old_12345678");
    api.getNotationBridgeWorkspace.mockImplementation((sessionId: string) => {
      if (sessionId === oldSession.session_id) return Promise.resolve({ score_document: score, session: oldSession });
      return new Promise(() => undefined);
    });
    api.generateStrictScorePatchPreview.mockResolvedValue({
      status: "generated",
      reason: null,
      matched_intents: ["transpose"],
      generator: { provider: "local_rule", model: "seraedit_rule_v1", formal_experiment_eligible: false },
      patch: {
        schema_version: "1.0.0",
        patch_id: "patch_old",
        source_score_id: score.score_id,
        source_fingerprint: "sha256:source",
        instruction: "升高大二度",
        target_scope: { measures: [1, 2] },
        protected_scope: {},
        preconditions: [],
        operations: [{
          operation_id: "op_1",
          type: "transpose",
          selector: { measures: [1, 2] },
          arguments: { semitones: 2 },
          preconditions: [],
          expected_change_count: 2
        }],
        expected_effects: [],
        provenance: {}
      },
      preview: {
        committed: false,
        score_document: score,
        proposed_score_document: score,
        validation_report: validation,
        diff: { added: [], deleted: [], changed: [{ id: "e1" }], global_changes: {}, changed_element_count: 1 },
        audit: [],
        source_fingerprint: "sha256:source",
        post_fingerprint: "sha256:after",
        musicxml: null,
        rollback_reason: null
      }
    });

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Old Host Score》/);
    fireEvent.click(screen.getByRole("tab", { name: /修改提案/ }));
    fireEvent.change(screen.getByLabelText("描述乐谱修改"), { target: { value: "将选区升高大二度" } });
    fireEvent.click(screen.getByRole("button", { name: "生成修改提案" }));
    await screen.findByText("验证通过");

    act(() => notifyDesktopSession({ sequence: 4, session_id: "bridge_new_12345678" }));

    expect(screen.queryByRole("button", { name: "应用并生成宿主修订" })).toBeNull();
    expect(screen.getByText("正在接收宿主上下文")).toBeTruthy();
    expect(api.applyStrictScorePatch).not.toHaveBeenCalled();
    expect(api.exportNotationBridgeRevision).not.toHaveBeenCalled();
    await waitFor(() => expect(api.getNotationBridgeWorkspace).toHaveBeenCalledWith("bridge_new_12345678"));
  });

  it("shows a promoted whole-score key edit and counts the global change", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Key Signature Host";
    score.global.key = "C major";
    const proposed = structuredClone(score);
    proposed.global.key = "G major";
    const session = {
      session_id: "bridge_key_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_key_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    api.generateStrictScorePatchPreview.mockResolvedValue({
      status: "generated",
      reason: null,
      matched_intents: ["change_key_signature"],
      generator: {
        provider: "local_rule",
        model: "seraedit_rule_v1",
        formal_experiment_eligible: false,
        routing: "local_first",
        scope_resolution: "promoted_to_whole_score_for_global_key_signature"
      },
      patch: {
        schema_version: "1.0.0",
        patch_id: "key_patch_1",
        source_score_id: score.score_id,
        source_fingerprint: "sha256:source",
        instruction: "将调号改为G major，但不要移调音符。",
        target_scope: { whole_score: true },
        protected_scope: {},
        preconditions: [],
        operations: [{
          operation_id: "op_001",
          type: "change_key_signature",
          selector: {},
          arguments: { key: "G major" },
          preconditions: [],
          expected_change_count: null
        }],
        expected_effects: [{ type: "preserve_pitch" }],
        provenance: {}
      },
      preview: {
        committed: false,
        score_document: score,
        proposed_score_document: proposed,
        validation_report: validation,
        diff: {
          added: [],
          deleted: [],
          changed: [],
          global_changes: { key: { before: "C major", after: "G major" } },
          changed_element_count: 1
        },
        audit: [],
        source_fingerprint: "sha256:source",
        post_fingerprint: "sha256:after",
        musicxml: null,
        rollback_reason: null
      }
    });

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Key Signature Host》/);
    fireEvent.click(screen.getByRole("tab", { name: /修改提案/ }));
    fireEvent.change(screen.getByLabelText("描述乐谱修改"), { target: { value: "将调号改为G major，但不要移调音符。" } });
    fireEvent.click(screen.getByRole("button", { name: "生成修改提案" }));

    await screen.findByText("验证通过");
    expect(screen.getByText("修改调号")).toBeTruthy();
    expect(screen.getByText(/全谱 · key: G major/)).toBeTruthy();
    expect(screen.getByText(/调号是全谱属性；已将宿主选区安全提升为全谱范围/)).toBeTruthy();
    expect(screen.getByText("全局").parentElement?.textContent).toContain("1");
    expect(screen.queryByText("不支持此修改")).toBeNull();
  });

  it("creates ranked theory candidates before reusing the proposal review", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Composer Host Score";
    const session = {
      session_id: "bridge_composer_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_composer_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    const patch = {
      schema_version: "1.0.0",
      patch_id: "composer_patch_1",
      source_score_id: score.score_id,
      source_fingerprint: "sha256:source",
      instruction: "创作古典变化",
      target_scope: { measures: [1, 2] },
      protected_scope: {},
      preconditions: [],
      operations: [{
        operation_id: "composer_op_1",
        type: "set_pitch",
        selector: { event_ids: ["e1"] },
        arguments: { pitch: "D4" },
        preconditions: [],
        expected_change_count: 1
      }],
      expected_effects: [{ type: "preserve_duration" }],
      provenance: {}
    };
    const preview = {
      committed: false,
      score_document: score,
      proposed_score_document: score,
      validation_report: validation,
      diff: { added: [], deleted: [], changed: [{ id: "e1", changed_fields: ["pitch"] }], global_changes: {}, changed_element_count: 1 },
      audit: [],
      source_fingerprint: "sha256:source",
      post_fingerprint: "sha256:after",
      musicxml: null,
      rollback_reason: null
    };
    let resolveRefinement: (payload: any) => void = () => undefined;
    api.getCompositionRefinement.mockReturnValue(new Promise((resolve) => {
      resolveRefinement = resolve;
    }));
    api.previewCompositionCandidates.mockResolvedValue({
      status: "generated",
      reason: "",
      apply_supported: true,
      plan: {
        schema_version: "1.0.0",
        plan_id: "plan_1",
        brief: "创作古典变化",
        mode: "theory_variation",
        style_family: "classical",
        key: "C major",
        meter: "4/4",
        measures: [1, 2],
        harmonic_progression: ["I", "V"],
        texture: "melody_accompaniment",
        motif_strategy: "preserve_contour",
        tension_curve: [0.3, 0.2],
        dynamics_curve: ["mp", "mf"],
        preserve_rhythm: true,
        preserve_event_count: true,
        preserve_instrumentation: true,
        preserve_melody: false,
        theory_claim_ids: ["TH-SAFE-001"],
        style_rule_ids: ["KB-STYLE-CLASSICAL-01"],
        style_knowledge_version: "0.4.0",
        knowledge_context_fingerprint: "sha256:query",
        knowledge_token_estimate: 260,
        orchestration_notes: []
      },
      theory_context: [{
        claim_id: "TH-SAFE-001",
        title: "Preserve the host scaffold",
        rule: "Preserve rhythm and layout.",
        provenance: "sera_curated_theory_summary",
        match_reason: "core"
      }],
      planner: {
        planner: "deterministic_theory",
        provider: "local_rule",
        model: "sera_composer_rules_v1",
        latency_ms: 0,
        prompt_version: "sera_composition_plan_v4.0",
        fallback_reason: "LLM planner not configured",
        run_trace: { trace_id: "composer_trace_1", recorded_at: "2026-08-22T01:30:00Z" }
      },
      candidates: [{
        candidate_id: "candidate_1",
        rank: 1,
        label: "候选 1",
        patch,
        preview,
        explanation: "古典和声候选，保留节奏与宿主排版。",
        review: {
          status: "valid",
          overall_score: 0.96,
          safety_score: 1,
          theory_score: 0.9,
          playability_score: 1,
          motif_score: 0.88,
          phrase_score: 0.82,
          style_score: 0.91,
          preference_score: 0.5,
          critic_weights: { safety: 0.28, theory: 0.17, playability: 0.1, motif: 0.15, phrase: 0.14, style: 0.11, preference: 0.05 },
          changed_event_count: 1,
          chord_tone_ratio: 0.8,
          large_leap_count: 0,
          range_violation_count: 0,
          voice_crossing_count: 0,
          cadence_resolved: true,
          melody_expectation_score: 0.91,
          source_melody_expectation_score: 0.88,
          melody_expectation_delta: 0.03,
          texture_structure_preserved: true,
          findings: [
            { check: "host_scaffold_preserved", passed: true, claim_id: "TH-SAFE-001" },
            { check: "melodic_expectation", passed: true, claim_id: "KB-EXPECT-001" },
            { check: "texture_structure_preserved", passed: true, claim_id: "KB-TEXTURE-001" }
          ]
        }
      }],
      selected_candidate_id: "candidate_1",
      comparison_id: "comparison_1",
      style_knowledge: {
        knowledge_base_id: "sera_composer_atomic_kb_v04",
        schema_version: "0.4.0",
        fingerprint: "sha256:kb",
        style_id: "classical",
        display_name_zh: "古典",
        matched_rules: [{ rule_id: "KB-STYLE-CLASSICAL-01", domain: "motif", title_zh: "古典·动机", action_zh: "使用短动机和清晰终止。", avoid_zh: "避免丢失动机身份。", hard_constraint: false, relevance_score: 9.2, match_reason: "style:classical", provenance: "sera_original_engineering_summary_v03" }],
        query: { style_id: "classical", mode: "theory_variation", key: "C major", meter: "4/4", instruments: ["piano"], goals: ["composition_craft", "melodic_expectation", "motif", "texture"], source_texture: "melody_accompaniment", target_measures: [1, 2] },
        query_fingerprint: "sha256:query",
        retrieval: { strategy: "metadata_lexical_idf_domain_diversity_cap4_v2", total_cards: 358, pack_count: 7, eligible_cards: 310, selected_cards: 4, dropped_cards: 306, estimated_tokens: 640, token_budget: 1800, max_cards: 12, selected_domains: { composition_craft: 1, melodic_expectation: 1, motif: 1, texture: 1 }, full_corpus_sent_to_llm: false },
        profile_schema_version: "0.2.0",
        provenance: { content_policy: "original" }
      },
      phrase_analysis: {
        analysis_version: "0.2.0",
        selected_note_count: 8,
        measure_count: 2,
        primary_voice_id: "right_hand:v1",
        source_motif: { intervals: [2, 2, 1], interval_signs: [1, 1, 1], signature: [2, 2, 1], contour: "ascending" },
        fingerprint: "sha256:phrase"
      },
      texture_analysis: {
        analysis_version: "0.4.0",
        texture: "melody_accompaniment",
        confidence: 0.89,
        voice_count: 2,
        primary_voice_id: "right_hand:v1"
      },
      search_summary: { search_width: 16, evaluated: 16, valid: 14, rejected: 13, returned: 1, selection: "overall_score_plus_pitch_diversity" },
      preference_profile: {
        schema_version: "0.2.0",
        feedback_count: 0,
        dimension_targets: {},
        reason_counts: { motif: 0, phrase: 0, style: 0, harmony: 0, playability: 0 },
        preferred_styles: {},
        active: false,
        privacy: { local_only: true, stores_score_content: false, stores_user_identity: false }
      },
      baseline_guarantees: { preserve_host_layout: true },
      refinement: { job_id: "composer_refine_test", status: "running", created_at: 1, error: "" }
    });

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Composer Host Score》/);
    fireEvent.click(screen.getByRole("tab", { name: /创作草案/ }));
    fireEvent.change(screen.getByLabelText("描述创作目标"), { target: { value: "创作古典变化" } });
    fireEvent.click(screen.getByRole("button", { name: "生成创作候选" }));

    await screen.findByText("CompositionPlan");
    expect(screen.getByText("I – V")).toBeTruthy();
    expect(screen.getByText("TH-SAFE-001")).toBeTruthy();
    expect(screen.getByText(/Composer V0.4 知识检索/)).toBeTruthy();
    expect(screen.getByText(/本地大库 358 张规则卡/)).toBeTruthy();
    expect(screen.getByText(/本次高层计划：本地即时初稿/)).toBeTruthy();
    expect(screen.getByText(/本地安全候选已就绪；实时 LLM 正在后台优化/)).toBeTruthy();
    expect(screen.getAllByText(/melody_accompaniment/).length).toBeGreaterThan(0);
    expect(screen.getByText(/内部评审 16\/16 个候选/)).toBeTruthy();
    expect(api.previewCompositionCandidates).toHaveBeenCalledWith(
      score,
      "创作古典变化",
      { measures: [1, 2] },
      {},
      3,
      42
    );
    expect(api.getCompositionRefinement).toHaveBeenCalledWith("composer_refine_test");

    resolveRefinement({
      job_id: "composer_refine_test",
      status: "failed",
      created_at: 1,
      completed_at: 2,
      error: "模型超时"
    });
    await screen.findByText(/LLM 后台优化未完成：模型超时/);
    expect(screen.getByText(/当前本地候选仍可正常使用/)).toBeTruthy();

    fireEvent.click(screen.getByLabelText("动机更清楚"));
    fireEvent.click(screen.getByRole("button", { name: "我更喜欢这个版本" }));
    await screen.findByText(/累计 1 次本机偏好/);
    expect(api.submitCompositionPreference).toHaveBeenCalledWith(expect.objectContaining({
      comparison_id: "comparison_1",
      selected_candidate_id: "candidate_1",
      reasons: ["motif"]
    }));

    fireEvent.click(screen.getByRole("button", { name: "选择此候选并审查" }));
    await screen.findByText("验证通过");
    expect(screen.getByText("修改音高")).toBeTruthy();
    expect(api.applyStrictScorePatch).not.toHaveBeenCalled();
  });

  it("shows an automatically routed Composer melody rewrite as a valid proposal", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Melody Rewrite Host";
    const session = {
      session_id: "bridge_melody_rewrite_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_melody_rewrite_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    api.generateStrictScorePatchPreview.mockResolvedValue({
      status: "generated",
      reason: null,
      matched_intents: ["theory_guided_composition", "theory_variation"],
      generator: {
        provider: "deepseek",
        model: "test-composer-model",
        transport: "composer_pipeline",
        live: true,
        formal_experiment_eligible: false,
        prompt_version: "sera_composition_plan_v2.0",
        latency_ms: 1200,
        composition_route: true,
        candidate_count: 3,
        selected_candidate_id: "candidate_1",
        selected_candidate_score: 0.94,
        repair_strategy: "composer_candidate_selection"
      },
      patch: {
        schema_version: "1.0.0",
        patch_id: "composer_routed_patch_1",
        source_score_id: score.score_id,
        source_fingerprint: "sha256:source",
        instruction: "重写旋律",
        target_scope: { measures: [1, 2] },
        protected_scope: {},
        preconditions: [],
        operations: [{
          operation_id: "op_001",
          type: "set_pitch",
          selector: { event_ids: ["e1"] },
          arguments: { pitch: "E4" },
          preconditions: [],
          expected_change_count: 1
        }],
        expected_effects: [{ type: "preserve_duration" }],
        provenance: {}
      },
      preview: {
        committed: false,
        score_document: score,
        proposed_score_document: score,
        validation_report: validation,
        diff: { added: [], deleted: [], changed: [{ id: "e1", changed_fields: ["pitch"] }], global_changes: {}, changed_element_count: 1 },
        audit: [],
        source_fingerprint: "sha256:source",
        post_fingerprint: "sha256:after",
        musicxml: null,
        rollback_reason: null
      }
    });

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Melody Rewrite Host》/);
    fireEvent.click(screen.getByRole("tab", { name: /修改提案/ }));
    fireEvent.change(screen.getByLabelText("描述乐谱修改"), { target: { value: "重写当前选区旋律并保持节奏" } });
    fireEvent.click(screen.getByRole("button", { name: "生成修改提案" }));

    await screen.findByText("验证通过");
    expect(screen.getByText("Composer 自动路由")).toBeTruthy();
    expect(screen.getByText(/已评审 3 个候选 · 最佳评分 94/)).toBeTruthy();
    expect(screen.getByText("修改音高")).toBeTruthy();
    expect(screen.queryByText("不支持此修改")).toBeNull();
  });

  it("shows immediate Composer progress and a visible failure instead of appearing idle", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Slow Composer Score";
    const session = {
      session_id: "bridge_slow_composer_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_slow_composer_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    let rejectPreview: (error: Error) => void = () => undefined;
    api.previewCompositionCandidates.mockReturnValue(new Promise((_, reject) => {
      rejectPreview = reject;
    }));

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Slow Composer Score》/);
    fireEvent.click(screen.getByRole("tab", { name: /创作草案/ }));
    fireEvent.change(screen.getByLabelText("描述创作目标"), { target: { value: "创作浪漫主义变化" } });
    fireEvent.click(screen.getByRole("button", { name: "生成创作候选" }));

    const progress = await screen.findByRole("status");
    expect(progress.textContent).toContain("正在读取宿主选区与理论约束");
    expect(progress.textContent).toContain("实时 LLM 会在后台继续优化并自动更新候选");
    expect(screen.getByRole("button", { name: /规划中 0s/ })).toBeTruthy();

    rejectPreview(new Error("模型服务暂时不可用"));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("创作候选没有生成");
    expect(alert.textContent).toContain("模型服务暂时不可用");
  });

  it("shows actionable Composer rejection diagnostics instead of a generic unsupported message", async () => {
    const score = createEmptyScoreDocument(2);
    score.title = "Protected Melody";
    const session = {
      session_id: "bridge_protected_melody_12345678",
      host_id: "musescore",
      revision: 0,
      host_context: { selection: { is_range: true, start_measure: 1, end_measure: 2 } }
    };
    window.history.replaceState({}, "", "/?bridge_session=bridge_protected_melody_12345678");
    api.getNotationBridgeWorkspace.mockResolvedValue({ score_document: score, session });
    api.previewCompositionCandidates.mockResolvedValue({
      status: "unsupported",
      reason: "目标选区中的 8 个音符全部位于保护范围内；Sera 未越过保护边界。",
      apply_supported: false,
      plan: null,
      theory_context: [],
      planner: { planner: "deterministic_theory", model: "sera_composer_rules_v1" },
      candidates: [],
      selected_candidate_id: null,
      comparison_id: null,
      style_knowledge: null,
      phrase_analysis: null,
      search_summary: { search_width: 16, evaluated: 0, valid: 0, rejected: 0, returned: 0 },
      failure_analysis: {
        code: "target_fully_protected",
        summary: "目标选区中的 8 个音符全部位于保护范围内；Sera 未越过保护边界。",
        suggestions: ["缩小保护范围，或只选择允许改写的谱表/声部。"],
        counts: { target_notes: 8, protected_target_notes: 8, evaluated: 0, rejected: 0 },
        failed_check_counts: {},
        error_code_counts: {},
        rejected_examples: []
      },
      preference_profile: {
        schema_version: "0.2.0",
        feedback_count: 0,
        dimension_targets: {},
        reason_counts: { motif: 0, phrase: 0, style: 0, harmony: 0, playability: 0 },
        preferred_styles: {},
        active: false,
        privacy: { local_only: true, stores_score_content: false, stores_user_identity: false }
      },
      baseline_guarantees: { protected_scope_enforced: true }
    });

    renderConsole();
    await screen.findByText(/已从 MuseScore Studio 接收《Protected Melody》/);
    fireEvent.click(screen.getByRole("tab", { name: /创作草案/ }));
    fireEvent.change(screen.getByLabelText("描述创作目标"), { target: { value: "重新和声化并保留旋律" } });
    fireEvent.click(screen.getByRole("button", { name: "生成创作候选" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("候选已安全拒绝");
    expect(alert.textContent).toContain("目标选区中的 8 个音符全部位于保护范围内");
    expect(alert.textContent).toContain("目标音符8");
    expect(alert.textContent).toContain("受保护8");
    expect(alert.textContent).toContain("缩小保护范围");
  });
});

function renderConsole() {
  return render(
    <I18nProvider>
      <SeraAgentConsole backendCapabilities={{ api_contract: "v1_notation_editing_layer" }} />
    </I18nProvider>
  );
}
