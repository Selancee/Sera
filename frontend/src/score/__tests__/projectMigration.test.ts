import { describe, expect, it } from "vitest";
import { migrateWorkbenchProject, projectNeedsMigration } from "../projectMigration";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("projectMigration", () => {
  it("migrates older project shapes to V0.8", () => {
    const migrated = migrateWorkbenchProject({ ScoreDocument: createEmptyScoreDocument(1), OperationHistory: { done: [], undone: [] } });
    expect(migrated.project_version).toBe("0.8");
    expect(projectNeedsMigration({ project_version: "0.7" })).toBe(true);
  });
});
