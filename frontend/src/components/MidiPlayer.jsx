import { useMemo, useRef, useState } from "react";
import { resolveBackendBaseUrl } from "../desktop/desktopRuntime";
import { useI18n } from "../i18n/useI18n";
import { resolvePlaybackSource } from "../score/fakeScoreGuard";
import { scoreDocumentToNoteEvents } from "../score/scoreDocumentToNoteEvents";
import PlaybackSourceBadge from "./PlaybackSourceBadge.jsx";

export default function MidiPlayer({ result }) {
  const { t } = useI18n();
  const scoreDocument = result?.score_document?.schema_version === "0.6" ? result.score_document : null;
  const midiUrl = result?.midi_url || result?.exports?.midi || "";
  const absoluteMidiUrl = midiUrl ? absoluteUrl(midiUrl) : "";
  const scoreDocumentEvents = useMemo(() => scoreDocumentToNoteEvents(scoreDocument), [scoreDocument]);
  const backendEvents = useMemo(() => backendNoteEventsToPlaybackEvents(result?.note_events || []), [result?.note_events]);
  const playbackSource = resolvePlaybackSource(result, scoreDocumentEvents.length);
  const noteEvents = playbackSource === "backend_note_events" ? backendEvents : scoreDocumentEvents;
  const [playing, setPlaying] = useState(false);
  const timersRef = useRef([]);
  const contextRef = useRef(null);

  function stopPlayback() {
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current = [];
    if (contextRef.current) {
      contextRef.current.close?.();
      contextRef.current = null;
    }
    setPlaying(false);
  }

  function playPreview() {
    if (playbackSource === "midi_export" && absoluteMidiUrl) {
      window.open(absoluteMidiUrl, "_blank", "noopener,noreferrer");
      return;
    }
    stopPlayback();
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext || noteEvents.length === 0) return;
    const context = new AudioContext();
    contextRef.current = context;
    setPlaying(true);
    const startAt = context.currentTime + 0.02;
    noteEvents.forEach((event) => {
      const timer = setTimeout(() => {
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = event.staff === "left_hand" ? "triangle" : "sine";
        oscillator.frequency.value = midiToHz(event.midi);
        gain.gain.setValueAtTime(0.0001, context.currentTime);
        gain.gain.exponentialRampToValueAtTime(velocityForDynamic(event.dynamic), context.currentTime + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + Math.max(0.08, event.duration_seconds));
        oscillator.connect(gain).connect(context.destination);
        oscillator.start();
        oscillator.stop(context.currentTime + Math.max(0.1, event.duration_seconds + 0.02));
      }, Math.max(0, Math.round(event.start_seconds * 1000)));
      timersRef.current.push(timer);
    });
    const endSeconds = Math.max(...noteEvents.map((event) => event.start_seconds + event.duration_seconds), 0);
    const endTimer = setTimeout(stopPlayback, Math.max(150, Math.round((endSeconds + startAt) * 1000)));
    timersRef.current.push(endTimer);
  }

  return (
    <section className="transport">
      <button className="transport-button" disabled={playbackSource === "unavailable"} onClick={playing ? stopPlayback : playPreview} type="button">
        {playing ? "Stop" : playbackSource === "midi_export" ? "Open MIDI" : "Play"}
      </button>
      <div className={playing ? "transport-line active" : "transport-line"}>
        <span />
      </div>
      <PlaybackSourceBadge source={playbackSource} />
      <span>Playback Event Stream</span>
      <span>{scoreDocument?.global?.tempo || result?.intent?.tempo_bpm || 96} bpm</span>
      {playbackSource === "unavailable" && <strong className="transport-warning">{t("score.noAuthoritativePlayback")}</strong>}
      {result?.consistency_report?.mismatch_count > 0 && <strong className="transport-warning">Score/playback mismatch</strong>}
    </section>
  );
}

function backendNoteEventsToPlaybackEvents(events) {
  if (!Array.isArray(events)) return [];
  return events
    .filter((event) => event && event.midi != null)
    .map((event, index) => ({
      event_id: event.event_id || `backend_note_${index + 1}`,
      measure_id: event.measure_id || `m${event.measure || 1}`,
      measure_number: Number(event.measure_number || event.measure || 1),
      staff: Number(event.staff) === 2 ? "left_hand" : event.staff || "right_hand",
      voice: Number(event.voice || 1),
      pitch: event.pitch || "",
      midi: Number(event.midi),
      duration: event.duration || "quarter",
      duration_seconds: Number(event.duration_seconds || event.duration_quarter || 1) * 0.5,
      offset_beats: Number(event.offset_beats || 0),
      start_seconds: Number(event.start_seconds || event.start_quarter || 0) * 0.5,
      dynamic: event.dynamic || "mf",
      diagnostic_stream: "playback_event_stream",
      melody_diagnostic_eligible: false
    }));
}

function midiToHz(midi) {
  return 440 * 2 ** ((Number(midi) - 69) / 12);
}

function velocityForDynamic(dynamic) {
  return { p: 0.04, mp: 0.055, mf: 0.075, f: 0.095 }[dynamic] || 0.07;
}

function absoluteUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return `${resolveBackendBaseUrl()}${url.startsWith("/") ? "" : "/"}${url}`;
}
