import { durationToQuarters } from "./noteInput";
import type { ScoreDocument } from "./scoreTypes";

export type PlaybackPoint = {
  eventId: string;
  measureId: string;
  measureNumber: number;
  startQuarter: number;
  durationQuarter: number;
  label: string;
};

export type PlaybackMap = {
  tempo: number;
  totalQuarters: number;
  points: PlaybackPoint[];
  measures: Array<{ measureId: string; measureNumber: number; startQuarter: number; endQuarter: number }>;
};

export function buildPlaybackMap(score: ScoreDocument): PlaybackMap {
  const measureLength = measureQuarters(score);
  const points: PlaybackPoint[] = [];
  const measures = score.measures.map((measure, index) => {
    const startQuarter = index * measureLength;
    for (const event of measure.events) {
      points.push({
        eventId: event.event_id,
        measureId: measure.measure_id,
        measureNumber: measure.number,
        startQuarter: startQuarter + Number(event.offset || 0),
        durationQuarter: durationToQuarters(event.duration),
        label: event.type === "rest" ? "rest" : event.pitch
      });
    }
    return { measureId: measure.measure_id, measureNumber: measure.number, startQuarter, endQuarter: startQuarter + measureLength };
  });
  points.sort((a, b) => a.startQuarter - b.startQuarter || a.eventId.localeCompare(b.eventId));
  return { tempo: Number(score.global.tempo || 90), totalQuarters: score.measures.length * measureLength, points, measures };
}

export function playbackPositionAt(map: PlaybackMap, quarter: number) {
  const measure = [...map.measures].reverse().find((item) => quarter >= item.startQuarter) || map.measures[0];
  const event = [...map.points].reverse().find((point) => quarter >= point.startQuarter) || map.points[0];
  return {
    measureId: measure?.measureId || "",
    measureNumber: measure?.measureNumber || 0,
    eventId: event?.eventId || "",
    progress: map.totalQuarters ? Math.max(0, Math.min(1, quarter / map.totalQuarters)) : 0
  };
}

export function quarterFromMeasure(map: PlaybackMap, measureNumber: number) {
  return map.measures.find((measure) => measure.measureNumber === measureNumber)?.startQuarter || 0;
}

export function quarterToMilliseconds(quarter: number, tempo: number) {
  return quarter * (60_000 / Math.max(1, tempo));
}

export function millisecondsToQuarter(ms: number, tempo: number) {
  return ms / (60_000 / Math.max(1, tempo));
}

function measureQuarters(score: ScoreDocument) {
  const [beats, beatType] = String(score.global.meter || "4/4").split("/").map((value) => Number(value) || 4);
  return beats * (4 / beatType);
}
