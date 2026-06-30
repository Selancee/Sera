import { playbackPositionAt, quarterFromMeasure, type PlaybackMap } from "../score/playbackMap";
import type { PlaybackState } from "../score/midiPlayback";

type Props = {
  playbackMap: PlaybackMap;
  playbackState: PlaybackState;
  selectedStartMeasure: number;
  selectedEndMeasure: number;
  onSeek: (quarter: number) => void;
  onPlay: () => void;
  onStop: () => void;
  onLoop: (loop: boolean) => void;
};

export default function PlaybackScrubber({ playbackMap, playbackState, selectedStartMeasure, selectedEndMeasure, onSeek, onPlay, onStop, onLoop }: Props) {
  const position = playbackPositionAt(playbackMap, playbackState.currentQuarter);
  const loopStart = quarterFromMeasure(playbackMap, selectedStartMeasure);
  const loopEnd = quarterFromMeasure(playbackMap, selectedEndMeasure + 1) || playbackMap.totalQuarters;
  return (
    <section className="playback-scrubber">
      <button onClick={playbackState.playing ? onStop : onPlay} type="button">{playbackState.playing ? "Stop" : "Play"}</button>
      <label className="inline-check">
        <input checked={playbackState.loop} onChange={(event) => onLoop(event.target.checked)} type="checkbox" />
        loop selection
      </label>
      <input
        aria-label="Playback position"
        max={Math.max(1, playbackMap.totalQuarters)}
        min="0"
        onChange={(event) => onSeek(Number(event.target.value))}
        step="0.25"
        type="range"
        value={Math.min(playbackState.currentQuarter, playbackMap.totalQuarters)}
      />
      <span>M{position.measureNumber || 1}</span>
      {playbackState.loop && <small>loop {loopStart}-{loopEnd}</small>}
    </section>
  );
}
