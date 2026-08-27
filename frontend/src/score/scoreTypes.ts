export type ScoreEventType = "note" | "rest" | "chord";

export type ScoreEvent = {
  event_id: string;
  type: ScoreEventType;
  pitch: string;
  duration: string;
  offset: number;
  voice: number;
  staff: string;
  tie: null | string;
  slur?: null | string;
  accidental?: "" | "sharp" | "flat" | "natural";
  dynamic: string;
  articulations: string[];
  selected: boolean;
  part_id?: string;
  grace?: boolean;
  is_chord_tone?: boolean;
  chord_group_id?: null | string;
};

export type ScoreMeasure = {
  measure_id: string;
  number: number;
  section: string;
  harmony: string;
  cadence: string;
  events: ScoreEvent[];
};

export type ScoreDocument = {
  schema_version: "0.6";
  score_id: string;
  title: string;
  composer: string;
  metadata: Record<string, unknown>;
  global: {
    key: string;
    meter: string;
    tempo: number;
    pickup: boolean;
  };
  parts: Array<Record<string, unknown>>;
  tracks?: Array<{
    track_id: string;
    role: string;
    instrument: string;
    part_id: string;
    staff: string;
    voice: number;
  }>;
  measures: ScoreMeasure[];
  annotations: Array<Record<string, unknown>>;
};

export type ScoreOperation = {
  operation_id?: string;
  timestamp?: string;
  source: "user" | "agent" | "validator" | "system";
  type: string;
  target: Record<string, unknown>;
  before?: Record<string, unknown>;
  after: Record<string, unknown>;
  description: string;
};

export type OperationHistory = {
  done: ScoreOperation[];
  undone: ScoreOperation[];
};

export type WorkbenchProject = {
  project_version: "0.8";
  score_document: ScoreDocument;
  operation_history: OperationHistory;
  agent_patch_history: ScorePatch[];
  original_prompt: string;
  composition_plan: Record<string, unknown>;
  validation_reports: Array<Record<string, unknown>>;
  export_metadata: Record<string, unknown>;
  experiment_metadata: Record<string, unknown>;
  autosaved_at?: string;
};

export type ScorePatch = {
  patch_id: string;
  patch_type: string;
  target_range: { start_measure: number; end_measure: number };
  operations: ScoreOperation[];
  rationale: string;
  expected_effect: string;
  prompt_alignment: {
    instruction: string;
    matched_aspects: string[];
    risk_aspects: string[];
  };
  validation_expectations: Record<string, unknown>;
};

export type StrictScoreScope = {
  measures?: number[];
  parts?: string[];
  staffs?: Array<number | string>;
  voices?: number[];
  event_ids?: string[];
  exclude_measures?: number[];
  exclude_event_ids?: string[];
  time_range?: null | { start: string; end: string };
  whole_score?: boolean;
};

export type StrictPatchOperation = {
  operation_id: string;
  type: string;
  selector: StrictScoreScope & Record<string, unknown>;
  arguments: Record<string, unknown>;
  preconditions: Array<Record<string, unknown>>;
  expected_change_count: null | number;
};

export type StrictScorePatch = {
  schema_version: "1.0.0";
  patch_id: string;
  source_score_id: string;
  source_fingerprint: string;
  instruction: string;
  target_scope: StrictScoreScope;
  protected_scope: StrictScoreScope;
  preconditions: Array<Record<string, unknown>>;
  operations: StrictPatchOperation[];
  expected_effects: Array<Record<string, unknown>>;
  provenance: Record<string, unknown>;
};

export type StrictValidationIssue = {
  code: string;
  message: string;
  stage: string;
  repairable: boolean;
  details: Record<string, unknown>;
};

export type StrictValidationReport = {
  status: "valid" | "warning" | "invalid" | "unsupported";
  errors: StrictValidationIssue[];
  warnings: StrictValidationIssue[];
  checks: Record<string, unknown>;
  repairable: boolean;
  suggested_repairs: Array<Record<string, unknown>>;
};

export type StrictScoreDiff = {
  added: Array<Record<string, unknown>>;
  deleted: Array<Record<string, unknown>>;
  changed: Array<Record<string, unknown>>;
  global_changes: Record<string, unknown>;
  changed_element_count: number;
};

export type StrictTransactionResult = {
  committed: boolean;
  score_document: ScoreDocument;
  proposed_score_document: null | ScoreDocument;
  validation_report: StrictValidationReport;
  diff: StrictScoreDiff;
  audit: Array<Record<string, unknown>>;
  source_fingerprint: string;
  post_fingerprint: string;
  musicxml: null | string;
  rollback_reason: null | string;
};

export type CompositionFailureAnalysis = {
  code: string;
  summary: string;
  suggestions: string[];
  counts: Record<string, number>;
  failed_check_counts: Record<string, number>;
  error_code_counts: Record<string, number>;
  rejected_examples: Array<{
    candidate_id: string;
    transaction_status: string;
    rollback_reason?: null | string;
    error_codes: string[];
    failed_checks: string[];
  }>;
};

export type StrictGenerationPreview = {
  status: "generated" | "unsupported" | "refused";
  patch: null | StrictScorePatch;
  reason: null | string;
  matched_intents: string[];
  generator: {
    provider: string;
    model: string;
    formal_experiment_eligible: boolean;
    transport?: string;
    live?: boolean;
    prompt_version?: string;
    latency_ms?: null | number;
    input_tokens?: null | number;
    output_tokens?: null | number;
    estimated_cost?: null | number;
    request_id?: null | string;
    requested_provider?: string;
    fallback_reason?: string;
    generation_attempts?: number;
    repair_strategy?: string;
    deterministic_repairs?: string[];
    scope_resolution?: string;
    composition_route?: boolean;
    candidate_count?: number;
    evaluated_candidate_count?: number;
    search_width?: number;
    style_knowledge_version?: string;
    preference_feedback_count?: number;
    selected_candidate_id?: string;
    selected_candidate_score?: number;
  };
  provider_status?: Record<string, unknown>;
  preview: null | StrictTransactionResult;
  composition_evidence?: {
    plan: CompositionPlan | null;
    theory_context: Array<Record<string, unknown>>;
    style_knowledge?: Record<string, unknown> | null;
    phrase_analysis?: Record<string, unknown> | null;
    search_summary?: Record<string, unknown>;
    preference_profile?: Record<string, unknown>;
    comparison_id?: string | null;
    candidate_count: number;
    selected_candidate_id: string | null;
    selected_review: null | CompositionCandidate["review"];
    failure_analysis?: CompositionFailureAnalysis | null;
    baseline_guarantees: Record<string, boolean>;
  };
};

export type SeraConversationResponse = {
  status: "answered" | "unavailable";
  answer: string;
  reason: null | string;
  generator: {
    provider: string;
    model: string;
    transport: string;
    live: boolean;
    prompt_version: string;
    latency_ms?: null | number;
    input_tokens?: null | number;
    output_tokens?: null | number;
    request_id?: null | string;
  };
  provider_status?: Record<string, unknown>;
};

export type CompositionPlan = {
  schema_version: "1.0.0";
  plan_id: string;
  brief: string;
  mode: "theory_variation" | "reharmonize" | "orchestration_advice";
  style_family: "classical" | "romantic" | "jazz" | "pop" | "minimal" | "modal" | "cinematic";
  key: string;
  meter: string;
  measures: number[];
  harmonic_progression: string[];
  texture: string;
  motif_strategy: string;
  tension_curve: number[];
  dynamics_curve: string[];
  preserve_rhythm: boolean;
  preserve_event_count: boolean;
  preserve_instrumentation: boolean;
  preserve_melody: boolean;
  theory_claim_ids: string[];
  style_rule_ids: string[];
  style_knowledge_version: string;
  knowledge_context_fingerprint: string;
  knowledge_token_estimate: number;
  orchestration_notes: string[];
};

export type CompositionPreferenceReason = "motif" | "phrase" | "style" | "harmony" | "playability";

export type CompositionPreferenceProfile = {
  schema_version: "0.2.0";
  feedback_count: number;
  dimension_targets: Partial<Record<CompositionPreferenceReason, number>>;
  reason_counts: Record<CompositionPreferenceReason, number>;
  preferred_styles: Record<string, number>;
  active: boolean;
  privacy: {
    local_only: boolean;
    stores_score_content: boolean;
    stores_user_identity: boolean;
  };
};

export type CompositionCandidate = {
  candidate_id: string;
  rank: number;
  label: string;
  patch: StrictScorePatch;
  preview: StrictTransactionResult;
  explanation: string;
  review: {
    status: "valid" | "rejected";
    overall_score: number;
    safety_score: number;
    theory_score: number;
    playability_score: number;
    motif_score: number;
    phrase_score: number;
    style_score: number;
    preference_score: number;
    critic_weights: Record<string, number>;
    changed_event_count: number;
    chord_tone_ratio: number;
    large_leap_count: number;
    melody_expectation_score?: number;
    source_melody_expectation_score?: number;
    melody_expectation_delta?: number;
    melody_expectation_preservation?: number;
    texture_structure_preserved?: boolean;
    range_violation_count: number;
    voice_crossing_count: number;
    baseline_range_violation_count?: number;
    baseline_voice_crossing_count?: number;
    introduced_range_violation_count?: number;
    introduced_voice_crossing_count?: number;
    cadence_resolved: boolean;
    findings: Array<{ check: string; passed: boolean; claim_id: string; value?: number }>;
    reviewer?: string;
  };
};

export type CompositionPreviewResponse = {
  status: "generated" | "plan_only" | "unsupported";
  reason: string;
  apply_supported: boolean;
  plan: CompositionPlan | null;
  theory_context: Array<{
    claim_id: string;
    title: string;
    rule: string;
    provenance: string;
    match_reason: string;
  }>;
  planner: {
    planner: "live_llm" | "deterministic_theory" | "none";
    provider?: string;
    model?: string;
    latency_ms?: number;
    fallback_reason?: string;
    prompt_version?: string;
    input_tokens?: number | null;
    output_tokens?: number | null;
    request_id?: string | null;
    source_texture?: string;
    source_texture_confidence?: number;
  };
  candidates: CompositionCandidate[];
  selected_candidate_id: string | null;
  comparison_id: string | null;
  style_knowledge: null | {
    knowledge_base_id: string;
    schema_version: string;
    fingerprint: string;
    style_id: string;
    display_name_zh: string;
    matched_rules: Array<{
      rule_id: string;
      domain: string;
      title_zh: string;
      action_zh: string;
      avoid_zh: string;
      hard_constraint: boolean;
      relevance_score: number;
      match_reason: string;
      provenance: string;
    }>;
    query: {
      style_id: string;
      mode: string;
      key: string;
      meter: string;
      instruments: string[];
      goals: string[];
      target_measures: number[];
      source_texture?: string;
    };
    query_fingerprint: string;
    retrieval: {
      strategy: string;
      total_cards: number;
      pack_count: number;
      eligible_cards: number;
      selected_cards: number;
      dropped_cards: number;
      estimated_tokens: number;
      token_budget: number;
      max_cards: number;
      selected_domains: Record<string, number>;
      full_corpus_sent_to_llm: boolean;
    };
    profile_schema_version: string;
    provenance: Record<string, string>;
  };
  phrase_analysis: null | {
    analysis_version: string;
    selected_note_count: number;
    measure_count: number;
    primary_voice_id: string | null;
    source_motif: { intervals: number[]; interval_signs: number[]; signature: number[]; contour: string };
    fingerprint: string;
  };
  texture_analysis?: null | {
    analysis_version: string;
    classifier: string;
    texture: string;
    confidence: number;
    evidence: string[];
    voice_count: number;
    primary_voice_id: string | null;
    attack_alignment_ratio: number;
    homorhythmic_similarity: number;
    rhythmic_independence: number;
    register_separation_semitones: number;
    fingerprint: string;
  };
  search_summary: {
    search_width: number;
    evaluated: number;
    valid: number;
    rejected?: number;
    valid_not_returned?: number;
    returned: number;
    selection?: string;
  };
  failure_analysis?: CompositionFailureAnalysis | null;
  preference_profile: CompositionPreferenceProfile;
  baseline_guarantees: Record<string, boolean>;
  provider_status?: Record<string, unknown>;
  run_trace?: {
    trace_id: string | null;
    created_at?: string;
    persisted: boolean;
    error?: string;
  };
  refinement?: {
    job_id: string;
    status: "running" | "ready" | "failed";
    created_at?: number;
    completed_at?: number | null;
    error?: string;
  };
};

export type CompositionRefinementResponse = {
  job_id: string;
  status: "running" | "ready" | "failed";
  created_at?: number;
  completed_at?: number | null;
  error?: string;
  result?: CompositionPreviewResponse;
};

export function createEmptyScoreDocument(measureCount = 4): ScoreDocument {
  const now = new Date().toISOString();
  return {
    schema_version: "0.6",
    score_id: `score_${Math.random().toString(16).slice(2, 10)}`,
    title: "Sera Workbench Score",
    composer: "Sera",
    metadata: { created_at: now, updated_at: now, source: "edited", prompt: "", agent_plan_id: "" },
    global: { key: "C major", meter: "4/4", tempo: 90, pickup: false },
    parts: [
      {
        part_id: "piano",
        name: "Piano",
        instrument: "piano",
        staves: [
          { staff_id: "right_hand", clef: "treble", measures: [] },
          { staff_id: "left_hand", clef: "bass", measures: [] }
        ]
      }
    ],
    tracks: [
      {
        track_id: "piano_right_hand_v1",
        role: "lead_melody",
        instrument: "piano",
        part_id: "piano",
        staff: "right_hand",
        voice: 1
      },
      {
        track_id: "piano_left_hand_v1",
        role: "bass",
        instrument: "piano",
        part_id: "piano",
        staff: "left_hand",
        voice: 1
      }
    ],
    measures: Array.from({ length: measureCount }, (_, index) => ({
      measure_id: `m${index + 1}`,
      number: index + 1,
      section: "A",
      harmony: "I",
      cadence: "none",
      events: []
    })),
    annotations: []
  };
}

export function scoreDocumentFromResult(result: any): ScoreDocument {
  if (result?.score_document?.schema_version === "0.6") {
    return result.score_document as ScoreDocument;
  }
  const doc = createEmptyScoreDocument(4);
  doc.title = result?.intent?.title || (result ? "Generated Sera Score" : "Untitled Sera Score");
  doc.metadata.prompt = result?.prompt || "";
  doc.metadata.source = result ? "missing_authoritative_score" : "edited";
  doc.metadata.warning = result ? "No authoritative ScoreDocument was provided; plan data is not converted into final notation." : "";
  doc.global.key = result?.intent?.key || "C major";
  doc.global.meter = result?.intent?.time_signature || result?.intent?.meter || "4/4";
  doc.global.tempo = result?.intent?.tempo_bpm || result?.intent?.tempo || 90;
  return doc;
}
