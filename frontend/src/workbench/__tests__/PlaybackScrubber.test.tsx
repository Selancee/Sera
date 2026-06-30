import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EMPTY_PLAYBACK_STATE } from "../../score/midiPlayback";
import { buildPlaybackMap } from "../../score/playbackMap";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import PlaybackScrubber from "../PlaybackScrubber";

describe("PlaybackScrubber", () => {
  it("plays and seeks", () => {
    const onPlay = vi.fn();
    const onSeek = vi.fn();
    render(<PlaybackScrubber playbackMap={buildPlaybackMap(createEmptyScoreDocument(2))} playbackState={EMPTY_PLAYBACK_STATE} selectedStartMeasure={1} selectedEndMeasure={2} onLoop={vi.fn()} onPlay={onPlay} onSeek={onSeek} onStop={vi.fn()} />);
    fireEvent.click(screen.getByText("Play"));
    fireEvent.change(screen.getByLabelText("Playback position"), { target: { value: "1" } });
    expect(onPlay).toHaveBeenCalled();
    expect(onSeek).toHaveBeenCalledWith(1);
  });
});
