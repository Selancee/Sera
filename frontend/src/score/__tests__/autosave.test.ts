import { describe, expect, it } from "vitest";
import { clearAutosave, loadAutosave, makeAutosavePayload, saveAutosave } from "../autosave";
import { EMPTY_OPERATION_HISTORY } from "../operationHistory";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("autosave", () => {
  it("saves and loads a V0.8 project payload", () => {
    const storage = window.localStorage;
    clearAutosave(storage);
    const payload = makeAutosavePayload({ scoreDocument: createEmptyScoreDocument(1), operationHistory: EMPTY_OPERATION_HISTORY });
    expect(saveAutosave(payload, storage)).toBe(true);
    expect(loadAutosave(storage)?.project_version).toBe("0.8");
    clearAutosave(storage);
  });
});
