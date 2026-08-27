import { describe, expect, it } from "vitest";
import { buildClickToNotatePreview, createClickToNotateOperation } from "../clickToNotate";
import { DEFAULT_SCORE_CURSOR } from "../scoreCursor";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("clickToNotate", () => {
  it("creates a dotted note operation from a staff click", () => {
    const score = createEmptyScoreDocument(1);
    const preview = buildClickToNotatePreview({
      score,
      cursor: DEFAULT_SCORE_CURSOR,
      hitTarget: null,
      point: { x: 96, y: 92 },
      inputMode: "note_input",
      duration: "quarter",
      dotted: true
    });
    const operation = preview && createClickToNotateOperation(preview);

    expect(preview?.action).toBe("insert_note");
    expect(operation?.type).toBe("insert_note");
    expect(operation?.after.duration).toBe("dotted_quarter");
    expect(operation?.target.offset).toBeTypeOf("number");
  });

  it("creates a rest operation in rest input mode", () => {
    const score = createEmptyScoreDocument(1);
    const preview = buildClickToNotatePreview({
      score,
      cursor: DEFAULT_SCORE_CURSOR,
      hitTarget: null,
      point: { x: 96, y: 152 },
      inputMode: "rest_input",
      duration: "eighth"
    });
    const operation = preview && createClickToNotateOperation(preview);

    expect(preview?.staff).toBe("left_hand");
    expect(operation?.type).toBe("insert_rest");
    expect(operation?.after.duration).toBe("eighth");
  });
});
