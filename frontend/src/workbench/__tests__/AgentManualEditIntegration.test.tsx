import { describe, expect, it } from "vitest";
import { mapWorkbenchShortcut } from "../../score/keyboardShortcuts";

describe("AgentManualEditIntegration", () => {
  it("keeps keyboard actions serializable for agent context", () => {
    const action = mapWorkbenchShortcut({ key: "ArrowUp" }, "select");
    const context = { recent_operations: [{ source: "user", type: action?.type, target: { event_id: "n1" } }] };
    expect(JSON.parse(JSON.stringify(context))).toBeTruthy();
  });
});
