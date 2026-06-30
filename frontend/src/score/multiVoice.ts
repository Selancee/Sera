import type { ScoreDocument, ScoreOperation } from "./scoreTypes";

export type StaffId = "right_hand" | "left_hand";
export type VoiceNumber = 1 | 2;

export function moveSelectionToStaff(score: ScoreDocument, eventIds: string[], staff: StaffId): ScoreOperation[] {
  return findSelected(score, eventIds).map(({ measure, event }) => ({
    source: "user",
    type: "update_staff",
    target: { measure_id: measure.measure_id, measure: measure.number, event_id: event.event_id },
    after: { staff },
    description: `Move ${event.event_id} to ${staff}`
  }));
}

export function changeSelectionVoice(score: ScoreDocument, eventIds: string[], voice: VoiceNumber): ScoreOperation[] {
  return findSelected(score, eventIds).map(({ measure, event }) => ({
    source: "user",
    type: "update_voice",
    target: { measure_id: measure.measure_id, measure: measure.number, event_id: event.event_id },
    after: { voice },
    description: `Move ${event.event_id} to voice ${voice}`
  }));
}

export function duplicateMelodyToStaff(score: ScoreDocument, sourceStaff: StaffId, targetStaff: StaffId, startMeasure: number, endMeasure: number): ScoreOperation[] {
  const operations: ScoreOperation[] = [];
  for (const measure of score.measures.filter((item) => item.number >= startMeasure && item.number <= endMeasure)) {
    for (const event of measure.events.filter((item) => item.staff === sourceStaff && item.type === "note")) {
      operations.push({
        source: "user",
        type: "insert_note",
        target: { measure_id: measure.measure_id, measure: measure.number, staff: targetStaff, voice: event.voice },
        after: { ...event, event_id: `${event.event_id}_${targetStaff}`, staff: targetStaff },
        description: `Copy melody note to ${targetStaff}`
      });
    }
  }
  return operations;
}

function findSelected(score: ScoreDocument, eventIds: string[]) {
  const wanted = new Set(eventIds);
  const selected: Array<{ measure: ScoreDocument["measures"][number]; event: ScoreDocument["measures"][number]["events"][number] }> = [];
  for (const measure of score.measures) {
    for (const event of measure.events) {
      if (wanted.has(event.event_id)) selected.push({ measure, event });
    }
  }
  return selected;
}
