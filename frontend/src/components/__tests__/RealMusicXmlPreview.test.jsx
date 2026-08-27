import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../../i18n";
import RealMusicXmlPreview from "../RealMusicXmlPreview.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("RealMusicXmlPreview", () => {
  it("does not show a render error while MusicXML is absent between generations", async () => {
    renderWithI18n(<RealMusicXmlPreview musicxml="" />);

    await waitFor(() => {
      expect(screen.queryByTestId("osmd-render-error")).toBeNull();
    });
  });
});
