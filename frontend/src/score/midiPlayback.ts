import { buildPlaybackMap, millisecondsToQuarter, playbackPositionAt, quarterToMilliseconds, type PlaybackMap } from "./playbackMap";
import type { ScoreDocument } from "./scoreTypes";

export type PlaybackState = {
  playing: boolean;
  currentQuarter: number;
  currentMeasure: number;
  currentEventId: string;
  loop: boolean;
  fallback: boolean;
};

export const EMPTY_PLAYBACK_STATE: PlaybackState = {
  playing: false,
  currentQuarter: 0,
  currentMeasure: 0,
  currentEventId: "",
  loop: false,
  fallback: true
};

export function createPlaybackState(score: ScoreDocument, quarter = 0, loop = false): PlaybackState {
  const map = buildPlaybackMap(score);
  const position = playbackPositionAt(map, quarter);
  return {
    playing: false,
    currentQuarter: quarter,
    currentMeasure: position.measureNumber,
    currentEventId: position.eventId,
    loop,
    fallback: true
  };
}

export function advanceFakePlayback(map: PlaybackMap, state: PlaybackState, elapsedMs: number, loopStartQuarter = 0, loopEndQuarter = map.totalQuarters): PlaybackState {
  let currentQuarter = state.currentQuarter + millisecondsToQuarter(elapsedMs, map.tempo);
  if (state.loop && currentQuarter >= loopEndQuarter) currentQuarter = loopStartQuarter;
  if (!state.loop && currentQuarter >= map.totalQuarters) currentQuarter = map.totalQuarters;
  const position = playbackPositionAt(map, currentQuarter);
  return {
    ...state,
    playing: state.loop ? state.playing : state.playing && currentQuarter < map.totalQuarters,
    currentQuarter,
    currentMeasure: position.measureNumber,
    currentEventId: position.eventId
  };
}

export function seekPlayback(map: PlaybackMap, quarter: number, state: PlaybackState = EMPTY_PLAYBACK_STATE): PlaybackState {
  const bounded = Math.max(0, Math.min(map.totalQuarters, quarter));
  const position = playbackPositionAt(map, bounded);
  return { ...state, currentQuarter: bounded, currentMeasure: position.measureNumber, currentEventId: position.eventId };
}

export function estimatedPlaybackMs(map: PlaybackMap) {
  return quarterToMilliseconds(map.totalQuarters, map.tempo);
}
