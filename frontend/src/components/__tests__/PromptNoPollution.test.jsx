import { afterEach, describe, expect, it, vi } from "vitest";
import { generateScore } from "../../api";

describe("prompt request integrity", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends raw prompt and UI controls separately", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true })
    });

    await generateScore({
      raw_prompt: "cyberpunk piano",
      ui_controls: { style: "romantic", key: "A minor" },
      control_policy: { prompt_priority: true }
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.raw_prompt).toBe("cyberpunk piano");
    expect(body.ui_controls.style).toBe("romantic");
    expect(body.raw_prompt).not.toContain("romantic");
    expect(body.raw_prompt).not.toContain("A minor");
  });
});
