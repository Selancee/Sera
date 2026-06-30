import type { ScoreDocument, ScoreEvent, ScoreMeasure } from "./scoreTypes";

export function downloadTextFile(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function scoreDocumentToSimpleMusicXml(scoreDocument: ScoreDocument) {
  const [beats, beatType] = scoreDocument.global.meter.split("/").map((item) => Number(item) || 4);
  const divisions = 4;
  const expected = beats * divisions * (4 / beatType);
  const measures = scoreDocument.measures.map((measure, index) => measureToXml(measure, index === 0, divisions, expected, beats, beatType));
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<score-partwise version="3.1">',
    "  <part-list>",
    '    <score-part id="P1"><part-name>Piano</part-name></score-part>',
    "  </part-list>",
    '  <part id="P1">',
    ...measures,
    "  </part>",
    "</score-partwise>"
  ].join("\n");
}

function measureToXml(measure: ScoreMeasure, first: boolean, divisions: number, expected: number, beats: number, beatType: number) {
  const lines = [`    <measure number="${measure.number}">`];
  if (first) {
    lines.push("      <attributes>");
    lines.push(`        <divisions>${divisions}</divisions>`);
    lines.push("        <key><fifths>0</fifths></key>");
    lines.push(`        <time><beats>${beats}</beats><beat-type>${beatType}</beat-type></time>`);
    lines.push("        <staves>2</staves>");
    lines.push('        <clef number="1"><sign>G</sign><line>2</line></clef>');
    lines.push('        <clef number="2"><sign>F</sign><line>4</line></clef>');
    lines.push("      </attributes>");
  }
  lines.push(`      <direction placement="above"><direction-type><words>${escapeXml(`${measure.section} ${measure.harmony}`)}</words></direction-type></direction>`);
  const right = measure.events.filter((event) => event.staff !== "left_hand");
  const left = measure.events.filter((event) => event.staff === "left_hand");
  lines.push(...eventsToXml(right, expected, divisions, 1));
  if (left.length) {
    lines.push("      <backup>");
    lines.push(`        <duration>${expected}</duration>`);
    lines.push("      </backup>");
    lines.push(...eventsToXml(left, expected, divisions, 2));
  }
  lines.push("    </measure>");
  return lines.join("\n");
}

function eventsToXml(events: ScoreEvent[], expected: number, divisions: number, staff: number) {
  const lines: string[] = [];
  let cursor = 0;
  for (const event of [...events].sort((a, b) => a.offset - b.offset)) {
    const offset = Math.max(0, Math.round(Number(event.offset || 0) * divisions));
    if (offset > cursor) {
      lines.push(...restXml(offset - cursor, staff));
      cursor = offset;
    }
    const duration = Math.max(1, Math.min(expected - cursor, Math.round(durationToQuarters(event.duration) * divisions)));
    lines.push(`      <!-- sera-event-id:${escapeXml(event.event_id)} -->`);
    lines.push(event.type === "rest" ? restXml(duration, staff, event).join("\n") : noteXml(event.pitch || "C4", duration, staff, event));
    cursor += duration;
    if (cursor >= expected) break;
  }
  if (cursor < expected) lines.push(...restXml(expected - cursor, staff));
  return lines;
}

function noteXml(pitch: string, duration: number, staff: number, event?: ScoreEvent) {
  const match = pitch.match(/^([A-G])([#b]?)(\d)$/) || ["", "C", "", "4"];
  const alter = match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0;
  const lines = [
    "      <note>",
    "        <pitch>",
    `          <step>${match[1]}</step>`,
    alter ? `          <alter>${alter}</alter>` : "",
    `          <octave>${match[3]}</octave>`,
    "        </pitch>",
    `        <duration>${duration}</duration>`,
    `        <voice>${event?.voice || 1}</voice>`,
    `        <type>${durationType(duration)}</type>`,
    `        <staff>${staff}</staff>`,
    event ? `        <notations><technical><other-technical>sera-event-id:${escapeXml(event.event_id)}</other-technical></technical></notations>` : "",
    "      </note>"
  ].filter(Boolean);
  return lines.join("\n");
}

function restXml(duration: number, staff: number, event?: ScoreEvent) {
  return [
    "      <note>",
    "        <rest/>",
    `        <duration>${duration}</duration>`,
    `        <voice>${event?.voice || 1}</voice>`,
    `        <type>${durationType(duration)}</type>`,
    `        <staff>${staff}</staff>`,
    event ? `        <notations><technical><other-technical>sera-event-id:${escapeXml(event.event_id)}</other-technical></technical></notations>` : "",
    "      </note>"
  ].filter(Boolean);
}

function durationToQuarters(duration: string) {
  return {
    whole: 4,
    half: 2,
    quarter: 1,
    eighth: 0.5,
    sixteenth: 0.25,
    dotted_quarter: 1.5,
    dotted_eighth: 0.75
  }[duration] || 1;
}

function durationType(duration: number) {
  return {
    16: "whole",
    8: "half",
    6: "quarter",
    4: "quarter",
    3: "eighth",
    2: "eighth",
    1: "16th"
  }[duration] || "quarter";
}

function escapeXml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
