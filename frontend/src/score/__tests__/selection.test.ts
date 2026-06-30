import { describe, expect, it } from "vitest";
import { EMPTY_SELECTION, selectAllMeasures, selectEvent, selectMeasure, selectMeasureRange, selectionToRange } from "../selection";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("selection", () => {
  it("selects measures, ranges, events, and all measures", () => {
    const score = createEmptyScoreDocument(4);
    const selected = selectMeasure(EMPTY_SELECTION, "m2");
    expect(selected.measureIds).toEqual(["m2"]);
    const range = selectMeasureRange(score, "m2", "m4");
    expect(range.measureIds).toEqual(["m2", "m3", "m4"]);
    const eventSelection = selectEvent(selected, "n1", "m2");
    expect(eventSelection.eventIds).toEqual(["n1"]);
    expect(selectionToRange(score, range)).toEqual({ start_measure: 2, end_measure: 4, part_id: "piano", staff: "right_hand" });
    expect(selectAllMeasures(score).measureIds).toHaveLength(4);
  });
});
