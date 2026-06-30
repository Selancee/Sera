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
  const measures = result?.plan?.measures || [];
  const doc = createEmptyScoreDocument(Math.max(1, measures.length || 4));
  doc.title = result?.intent?.title || "Generated Sera Score";
  doc.metadata.prompt = result?.prompt || "";
  doc.metadata.source = result ? "generated" : "edited";
  doc.global.key = result?.intent?.key || "C major";
  doc.global.meter = result?.intent?.time_signature || result?.intent?.meter || "4/4";
  doc.global.tempo = result?.intent?.tempo_bpm || result?.intent?.tempo || 90;
  doc.measures = (measures.length ? measures : doc.measures).map((measure: any, index: number) => ({
    measure_id: `m${index + 1}`,
    number: index + 1,
    section: measure.section || "A",
    harmony: measure.chord || measure.harmony || "I",
    cadence: measure.cadence || "none",
    events: (measure.notes?.length ? measure.notes : ["1", "2", "3", "5"]).map((degree: string, noteIndex: number) => ({
      event_id: `m${index + 1}_e${noteIndex + 1}`,
      type: "note" as ScoreEventType,
      pitch: degreeToPitch(degree),
      duration: noteIndex % 2 ? "eighth" : "quarter",
      offset: Math.min(3, noteIndex),
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    }))
  }));
  return doc;
}

function degreeToPitch(degree: string): string {
  const map: Record<string, string> = {
    "1": "C4",
    "2": "D4",
    "3": "E4",
    b3: "Eb4",
    "4": "F4",
    "5": "G4",
    "6": "A4",
    b6: "Ab4",
    "7": "B4"
  };
  return map[degree] || "C4";
}
