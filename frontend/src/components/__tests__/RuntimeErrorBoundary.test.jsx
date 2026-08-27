import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RuntimeErrorBoundary from "../RuntimeErrorBoundary.jsx";

function MaybeThrow({ shouldThrow }) {
  if (shouldThrow) throw new Error("generated result render failed");
  return <div>Recovered view</div>;
}

describe("RuntimeErrorBoundary", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a visible fallback instead of letting a render error blank the page", () => {
    render(
      <RuntimeErrorBoundary resetKey="run-1" scope="score-tab" title="Generated score view could not be rendered">
        <MaybeThrow shouldThrow />
      </RuntimeErrorBoundary>
    );

    expect(screen.getByTestId("runtime-error-boundary")).toBeTruthy();
    expect(screen.getByText("Generated score view could not be rendered")).toBeTruthy();
    expect(screen.getByText("generated result render failed")).toBeTruthy();
  });

  it("recovers when the reset key changes", () => {
    const { rerender } = render(
      <RuntimeErrorBoundary resetKey="run-1" scope="score-tab">
        <MaybeThrow shouldThrow />
      </RuntimeErrorBoundary>
    );

    rerender(
      <RuntimeErrorBoundary resetKey="run-2" scope="score-tab">
        <MaybeThrow shouldThrow={false} />
      </RuntimeErrorBoundary>
    );

    expect(screen.getByText("Recovered view")).toBeTruthy();
  });
});
