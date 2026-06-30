import type { OperationHistory, ScoreDocument, ScoreOperation } from "./scoreTypes";

export function applyLocalOperation(score: ScoreDocument, operation: ScoreOperation) {
  const before = clone(score);
  const next = clone(score);
  const type = operation.type;

  if (type === "insert_note" || type === "insert_rest") {
    insertEvent(next, operation, type === "insert_rest" ? "rest" : "note");
  } else if (type === "delete_note") {
    const measure = targetMeasure(next, operation);
    measure.events = measure.events.filter((event) => event.event_id !== operation.target.event_id);
  } else if (EVENT_UPDATE_TYPES.has(type)) {
    updateEvent(next, operation);
  } else if (type === "transpose_selection") {
    transposeSelection(next, operation);
  } else if (type === "duplicate_measure") {
    const measure = targetMeasure(next, operation);
    next.measures.splice(measure.number, 0, clone(measure));
    renumberMeasures(next);
  } else if (type === "delete_measure") {
    const measure = targetMeasure(next, operation);
    next.measures = next.measures.filter((item) => item.measure_id !== measure.measure_id);
    if (!next.measures.length) next.measures = [measure];
    renumberMeasures(next);
  } else if (type === "insert_measure") {
    const number = Number(operation.after.number || operation.target.measure || next.measures.length + 1);
    next.measures.splice(Math.max(0, number - 1), 0, {
      measure_id: String(operation.after.measure_id || `m${number}`),
      number,
      section: String(operation.after.section || "A"),
      harmony: String(operation.after.harmony || "I"),
      cadence: String(operation.after.cadence || "none"),
      events: Array.isArray(operation.after.events) ? (operation.after.events as any) : []
    });
    renumberMeasures(next);
  } else if (type === "add_harmony_label" || type === "update_harmony") {
    targetMeasure(next, operation).harmony = String(operation.after.harmony || operation.after.value || "I");
  } else if (type === "add_section_label") {
    targetMeasure(next, operation).section = String(operation.after.section || operation.after.value || "A");
  } else if (type === "add_cadence") {
    targetMeasure(next, operation).cadence = String(operation.after.cadence || "authentic");
  } else if (type === "simplify_rhythm" || type === "humanize_rhythm" || type === "quantize_rhythm") {
    rewriteRangeRhythm(next, operation);
  } else if (type === "change_tempo") {
    next.global.tempo = Number(operation.after.tempo || operation.after.value || next.global.tempo);
  } else if (type === "change_key") {
    next.global.key = String(operation.after.key || operation.after.value || next.global.key);
  } else if (type === "change_meter") {
    next.global.meter = String(operation.after.meter || operation.after.value || next.global.meter);
  }

  const applied = {
    ...operation,
    operation_id: operation.operation_id || `op_${Math.random().toString(16).slice(2, 10)}`,
    timestamp: operation.timestamp || new Date().toISOString(),
    before: { score_document: before },
    after: { ...operation.after, score_document: next }
  };
  return { scoreDocument: next, operation: applied };
}

export function recordLocalOperation(history: OperationHistory, operation: ScoreOperation): OperationHistory {
  return { done: [...(history.done || []), operation], undone: [] };
}

export function undoLocal(score: ScoreDocument, history: OperationHistory) {
  const done = [...(history.done || [])];
  const undone = [...(history.undone || [])];
  const op = done.pop();
  if (!op) return { scoreDocument: score, operationHistory: history };
  undone.push(op);
  return {
    scoreDocument: (op.before?.score_document as ScoreDocument) || score,
    operationHistory: { done, undone }
  };
}

export function redoLocal(score: ScoreDocument, history: OperationHistory) {
  const done = [...(history.done || [])];
  const undone = [...(history.undone || [])];
  const op = undone.pop();
  if (!op) return { scoreDocument: score, operationHistory: history };
  done.push(op);
  return {
    scoreDocument: (op.after?.score_document as ScoreDocument) || score,
    operationHistory: { done, undone }
  };
}

const EVENT_UPDATE_TYPES = new Set([
  "update_pitch",
  "update_duration",
  "change_dynamic",
  "move_note",
  "update_articulation",
  "update_tie",
  "update_staff",
  "update_voice",
  "move_to_staff",
  "change_voice",
  "set_accidental",
  "convert_note_to_rest",
  "convert_rest_to_note",
  "add_slur",
  "remove_slur"
]);

function insertEvent(score: ScoreDocument, operation: ScoreOperation, eventType: "note" | "rest") {
  const measure = targetMeasure(score, operation);
  measure.events.push({
    event_id: String(operation.after.event_id || `${measure.measure_id}_e${Math.random().toString(16).slice(2, 8)}`),
    type: eventType,
    pitch: eventType === "rest" ? "" : String(operation.after.pitch || "C4"),
    duration: String(operation.after.duration || "quarter"),
    offset: Number(operation.after.offset ?? 0),
    voice: Number(operation.after.voice || operation.target.voice || 1),
    staff: String(operation.after.staff || operation.target.staff || "right_hand"),
    tie: (operation.after.tie as string | null) || null,
    accidental: (operation.after.accidental as any) || "",
    dynamic: String(operation.after.dynamic || "mf"),
    articulations: Array.isArray(operation.after.articulations) ? (operation.after.articulations as string[]) : [],
    selected: false
  });
  measure.events.sort((a, b) => a.offset - b.offset || a.event_id.localeCompare(b.event_id));
}

function updateEvent(score: ScoreDocument, operation: ScoreOperation) {
  const event = targetEvent(score, operation);
  if (!event) return;
  const type = operation.type;
  const after = operation.after || {};
  if (type === "update_pitch") event.pitch = String(after.pitch || after.value || event.pitch);
  if (type === "update_duration") event.duration = String(after.duration || after.value || event.duration);
  if (type === "change_dynamic") event.dynamic = String(after.dynamic || after.value || event.dynamic);
  if (type === "move_note") event.offset = Number(after.offset ?? after.value ?? event.offset);
  if (type === "update_articulation") event.articulations = Array.isArray(after.articulations) ? (after.articulations as string[]) : [String(after.value || "")].filter(Boolean);
  if (type === "update_tie") event.tie = String(after.tie ?? after.value ?? "") || null;
  if (type === "update_staff" || type === "move_to_staff") event.staff = String(after.staff || after.value || event.staff);
  if (type === "update_voice" || type === "change_voice") event.voice = Number(after.voice || after.value || event.voice);
  if (type === "set_accidental") {
    event.accidental = String(after.accidental || after.value || "") as any;
    event.pitch = applyAccidental(event.pitch, event.accidental || "");
  }
  if (type === "convert_note_to_rest") {
    event.type = "rest";
    event.pitch = "";
  }
  if (type === "convert_rest_to_note") {
    event.type = "note";
    event.pitch = String(after.pitch || "C4");
  }
  if (type === "add_slur") event.slur = String(after.slur || "start");
  if (type === "remove_slur") event.slur = null;
}

function transposeSelection(score: ScoreDocument, operation: ScoreOperation) {
  const semitones = Number(operation.after.semitones ?? operation.after.value ?? 0);
  const excluded = new Set((operation.target.exclude_event_ids as string[]) || []);
  for (const measure of targetRange(score, operation)) {
    for (const event of measure.events) {
      if (event.type === "note" && !excluded.has(event.event_id)) event.pitch = transposePitch(event.pitch, semitones);
    }
  }
}

function rewriteRangeRhythm(score: ScoreDocument, operation: ScoreOperation) {
  const excluded = new Set((operation.target.exclude_event_ids as string[]) || []);
  for (const measure of targetRange(score, operation)) {
    for (const event of measure.events) {
      if (excluded.has(event.event_id)) continue;
      if (operation.type === "quantize_rhythm") event.offset = Math.round(Number(event.offset || 0) * 2) / 2;
      else event.duration = operation.type === "simplify_rhythm" ? "quarter" : String(operation.after.duration || "eighth");
    }
  }
}

function targetMeasure(score: ScoreDocument, operation: ScoreOperation) {
  const number = Number(operation.target.measure || operation.target.measure_number || 1);
  const measureId = operation.target.measure_id;
  return (
    score.measures.find((measure) => measure.measure_id === measureId) ||
    score.measures.find((measure) => measure.number === number) ||
    score.measures[0]
  );
}

function targetEvent(score: ScoreDocument, operation: ScoreOperation) {
  const measure = targetMeasure(score, operation);
  if (operation.target.event_id) {
    for (const candidate of score.measures.flatMap((item) => item.events)) {
      if (candidate.event_id === operation.target.event_id) return candidate;
    }
  }
  return measure.events.find((event) => event.event_id === operation.target.event_id) || measure.events[0];
}

function targetRange(score: ScoreDocument, operation: ScoreOperation) {
  const start = Number(operation.target.start_measure || operation.target.measure || operation.target.measure_number || 1);
  const end = Number(operation.target.end_measure || start);
  return score.measures.filter((measure) => measure.number >= start && measure.number <= end);
}

function renumberMeasures(score: ScoreDocument) {
  score.measures.forEach((measure, index) => {
    measure.number = index + 1;
    measure.measure_id = `m${index + 1}`;
  });
}

function applyAccidental(pitch: string, accidental: string) {
  const match = String(pitch || "C4").match(/^([A-G])([#b]?)(\d)$/);
  if (!match) return pitch;
  const sign = accidental === "sharp" ? "#" : accidental === "flat" ? "b" : "";
  return `${match[1]}${sign}${match[3]}`;
}

function transposePitch(pitch: string, semitones: number) {
  const match = String(pitch || "").match(/^([A-G])([#b]?)(-?\d+)$/);
  if (!match) return pitch;
  const stepMap: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  const midi = (Number(match[3]) + 1) * 12 + stepMap[match[1].toUpperCase()] + (match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0);
  const shifted = Math.max(21, Math.min(108, midi + semitones));
  return `${names[shifted % 12]}${Math.floor(shifted / 12) - 1}`;
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}
