import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import OperationHistoryPanel from "../OperationHistoryPanel";

describe("OperationHistoryPanel", () => {
  it("renders recent operations", () => {
    render(
      <OperationHistoryPanel
        history={{
          done: [{ operation_id: "op1", source: "user", type: "insert_note", target: {}, after: {}, description: "Insert note" }],
          undone: []
        }}
      />
    );
    expect(screen.getByText("Insert note")).toBeTruthy();
  });
});
