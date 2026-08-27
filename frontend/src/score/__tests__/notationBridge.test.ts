import { describe, expect, it } from "vitest";
import { bridgeSessionIdFromSearch, safeBridgeSessionId, selectionFromNotationHostContext } from "../notationBridge";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("notation bridge deep links", () => {
  it("accepts only safe bridge session ids", () => {
    expect(bridgeSessionIdFromSearch("?bridge_session=bridge_20260803_abcdef12")).toBe("bridge_20260803_abcdef12");
    expect(bridgeSessionIdFromSearch("?bridge_session=../../source.musicxml")).toBe("");
    expect(safeBridgeSessionId("bridge_20260803_12345678")).toBe("bridge_20260803_12345678");
    expect(safeBridgeSessionId("not-a-bridge-session")).toBe("");
  });

  it("restores the MuseScore range selection by measure number", () => {
    const score = createEmptyScoreDocument(4);
    const selection = selectionFromNotationHostContext(score, {
      selection: { is_range: true, start_measure: 2, end_measure: 3 }
    });

    expect(selection.measureIds).toEqual(["m2", "m3"]);
    expect(selection.anchorMeasureId).toBe("m2");
  });

  it("falls back to the first measure when MuseScore has no range selection", () => {
    const score = createEmptyScoreDocument(2);
    const selection = selectionFromNotationHostContext(score, { selection: { is_range: false } });

    expect(selection.measureIds).toEqual(["m1"]);
  });
});
