import { useRef, useState } from "react";

const DEGREE_TO_HZ = {
  "1": 261.63,
  "2": 293.66,
  "3": 329.63,
  b3: 311.13,
  "4": 349.23,
  "5": 392.0,
  "6": 440.0,
  b6: 415.3,
  "7": 493.88
};

export default function MidiPlayer({ measures, tempo }) {
  const [playing, setPlaying] = useState(false);
  const timersRef = useRef([]);

  function stopPlayback() {
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current = [];
    setPlaying(false);
  }

  function playPreview() {
    stopPlayback();
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext || measures.length === 0) return;
    const context = new AudioContext();
    const beatMs = 60000 / tempo;
    setPlaying(true);
    let cursor = 0;
    measures.forEach((measure) => {
      const notes = measure.notes?.length ? measure.notes : ["1", "2", "3", "5"];
      notes.forEach((degree) => {
        const timer = setTimeout(() => {
          const oscillator = context.createOscillator();
          const gain = context.createGain();
          oscillator.type = "sine";
          oscillator.frequency.value = DEGREE_TO_HZ[degree] || 261.63;
          gain.gain.setValueAtTime(0.0001, context.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
          gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.35);
          oscillator.connect(gain).connect(context.destination);
          oscillator.start();
          oscillator.stop(context.currentTime + 0.38);
        }, cursor);
        timersRef.current.push(timer);
        cursor += beatMs;
      });
    });
    const endTimer = setTimeout(() => {
      setPlaying(false);
      context.close();
    }, cursor + 120);
    timersRef.current.push(endTimer);
  }

  return (
    <section className="transport">
      <button className="transport-button" disabled={!measures.length} onClick={playing ? stopPlayback : playPreview} type="button">
        {playing ? "Stop" : "Play"}
      </button>
      <div className={playing ? "transport-line active" : "transport-line"}>
        <span />
      </div>
      <strong>MIDI</strong>
      <span>{tempo} bpm</span>
    </section>
  );
}
