import { afterEach, describe, expect, it, vi } from "vitest";
import { generateScore } from "../../api";

describe("control-only generation request", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits an empty raw prompt with explicit controls and control-only mode", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true })
    });

    await generateScore({
      raw_prompt: "",
      prompt: "",
      ui_controls: { style: "cyberpunk", key: "A minor", meter: "4/4" },
      generation_mode: "control_only_intent",
      candidate_count: 4
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.raw_prompt).toBe("");
    expect(body.generation_mode).toBe("control_only_intent");
    expect(body.ui_controls.style).toBe("cyberpunk");
    expect(body.candidate_count).toBe(4);
  });
});
