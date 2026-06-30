import { describe, expect, it } from "vitest";
import { buildPlaybackMap, playbackPositionAt } from "../playbackMap";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("playbackMap", () => {
  it("maps events and measure positions", () => {
    const score = createEmptyScoreDocument(2);
    score.measures[0].events.push({ event_id: "n1", type: "note", pitch: "C4", duration: "quarter", offset: 0, voice: 1, staff: "right_hand", tie: null, dynamic: "mf", articulations: [], selected: false });
    const map = buildPlaybackMap(score);
    expect(map.points).toHaveLength(1);
    expect(playbackPositionAt(map, 4).measureNumber).toBe(2);
  });
});
