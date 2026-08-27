import { describe, expect, it } from "vitest";
import { scoreDocumentToNoteEvents } from "../scoreDocumentToNoteEvents";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreDocumentToNoteEvents", () => {
  it("derives playback events from ScoreDocument notes", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({
      event_id: "n1",
      type: "note",
      pitch: "C4",
      duration: "quarter",
      offset: 0,
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    });

    const events = scoreDocumentToNoteEvents(score);

    expect(events).toHaveLength(1);
    expect(events[0].event_id).toBe("n1");
    expect(events[0].midi).toBe(60);
  });
});
