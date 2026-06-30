import type { ScoreDocument, ScoreOperation } from "./scoreTypes";

export type AccompanimentTexture = "block_chord" | "arpeggiated" | "bass_chord";

const ROOTS: Record<string, string> = {
  I: "C3",
  i: "C3",
  ii: "D3",
  IV: "F3",
  V: "G2",
  vi: "A2"
};

export function generateLeftHandAccompanimentOperations(
  score: ScoreDocument,
  startMeasure: number,
  endMeasure: number,
  texture: AccompanimentTexture = "arpeggiated"
): ScoreOperation[] {
  const operations: ScoreOperation[] = [];
  for (const measure of score.measures.filter((item) => item.number >= startMeasure && item.number <= endMeasure)) {
    const root = ROOTS[String(measure.harmony || "I")] || "C3";
    const pitches = accompanimentPitches(root, texture);
    const offsets = texture === "block_chord" ? [0, 0, 0] : texture === "bass_chord" ? [0, 1, 1] : [0, 0.5, 1, 1.5];
    pitches.forEach((pitch, index) => {
      operations.push({
        source: "user",
        type: "insert_note",
        target: { measure_id: measure.measure_id, measure: measure.number, staff: "left_hand", voice: 1 },
        after: {
          event_id: `${measure.measure_id}_lh_${texture}_${index}`,
          pitch,
          duration: texture === "block_chord" ? "half" : "eighth",
          offset: offsets[index] ?? index * 0.5,
          staff: "left_hand",
          voice: 1,
          dynamic: "mp"
        },
        description: `Generate ${texture} left-hand accompaniment`
      });
    });
  }
  return operations;
}

export function accompanimentPatch(score: ScoreDocument, startMeasure: number, endMeasure: number, texture: AccompanimentTexture = "arpeggiated") {
  return {
    patch_id: `patch_lh_${Date.now().toString(36)}`,
    patch_type: "update_texture",
    target_range: { start_measure: startMeasure, end_measure: endMeasure },
    operations: generateLeftHandAccompanimentOperations(score, startMeasure, endMeasure, texture),
    rationale: "Generate a simple left-hand pattern from the current harmony labels.",
    expected_effect: "The passage gains a playable piano accompaniment while preserving right-hand melody.",
    prompt_alignment: { instruction: "Generate left-hand accompaniment", matched_aspects: ["accompaniment", "selected range"], risk_aspects: ["harmony labels are heuristic"] },
    validation_expectations: { should_preserve_measure_count: true, should_preserve_meter: true, should_preserve_harmony: true }
  };
}

function accompanimentPitches(root: string, texture: AccompanimentTexture) {
  const third = root.replace(/^C/, "E").replace(/^D/, "F").replace(/^F/, "A").replace(/^G/, "B").replace(/^A/, "C");
  const fifth = root.replace(/^C/, "G").replace(/^D/, "A").replace(/^F/, "C").replace(/^G/, "D").replace(/^A/, "E");
  if (texture === "block_chord") return [root, third, fifth];
  if (texture === "bass_chord") return [root, third, fifth];
  return [root, fifth, third, fifth];
}
