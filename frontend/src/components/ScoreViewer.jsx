const NOTE_X = 38;
const MEASURE_WIDTH = 104;
const STAFF_TOP = 68;
const STAFF_GAP = 10;
const PITCH_Y = {
  C: 110,
  D: 105,
  E: 100,
  F: 95,
  G: 90,
  A: 85,
  B: 80
};

function noteY(note) {
  const step = String(note || "C").charAt(0).toUpperCase();
  return PITCH_Y[step] || 94;
}

function collectNotes(measures) {
  return measures.flatMap((measure, measureIndex) => {
    const source = measure.notes?.length ? measure.notes : ["1", "2", "3", "5"];
    return source.map((degree, noteIndex) => ({
      id: `${measure.index}-${noteIndex}`,
      x: measureIndex * MEASURE_WIDTH + NOTE_X + noteIndex * 18,
      y: noteY(degreeToNote(degree)),
      measure: measure.index
    }));
  });
}

function degreeToNote(degree) {
  const map = { "1": "C", "2": "D", "3": "E", b3: "E", "4": "F", "5": "G", "6": "A", b6: "A", "7": "B" };
  return map[degree] || "C";
}

export default function ScoreViewer({ measures, result }) {
  const width = Math.max(880, measures.length * MEASURE_WIDTH + 40);
  const notes = collectNotes(measures);
  const musicxmlPreview = result?.musicxml ? result.musicxml.slice(0, 3000) : "";
  const generation = result?.generation || {};
  const symbolicModel = result?.metadata?.symbolic_model || {};

  return (
    <section className="panel score-panel">
      <div className="panel-heading">
        <h2>Score</h2>
        <span>{result?.intent?.instrumentation?.join(", ") || result?.intent?.instruments?.join(", ") || "MusicXML"}</span>
      </div>
      <div className="score-scroll">
        <svg className="score-svg" viewBox={`0 0 ${width} 180`} role="img" aria-label="Generated score preview">
          <rect x="0" y="0" width={width} height="180" rx="6" />
          {[0, 1, 2, 3, 4].map((line) => (
            <line
              key={line}
              x1="24"
              x2={width - 24}
              y1={STAFF_TOP + line * STAFF_GAP}
              y2={STAFF_TOP + line * STAFF_GAP}
            />
          ))}
          {measures.map((measure, index) => (
            <g key={measure.index}>
              <line
                className="barline"
                x1={index * MEASURE_WIDTH + 24}
                x2={index * MEASURE_WIDTH + 24}
                y1={STAFF_TOP}
                y2={STAFF_TOP + STAFF_GAP * 4}
              />
              <text x={index * MEASURE_WIDTH + 32} y="42">{measure.section}</text>
              <text className="chord" x={index * MEASURE_WIDTH + 32} y="150">{measure.chord}</text>
            </g>
          ))}
          <line
            className="barline"
            x1={measures.length * MEASURE_WIDTH + 24}
            x2={measures.length * MEASURE_WIDTH + 24}
            y1={STAFF_TOP}
            y2={STAFF_TOP + STAFF_GAP * 4}
          />
          {notes.map((note) => (
            <g className="note" key={note.id}>
              <ellipse cx={note.x} cy={note.y} rx="6.5" ry="4.5" transform={`rotate(-18 ${note.x} ${note.y})`} />
              <line x1={note.x + 6} x2={note.x + 6} y1={note.y} y2={note.y - 28} />
            </g>
          ))}
        </svg>
      </div>
      <div className="musicxml-strip">
        <span>MusicXML</span>
        <code>{result?.artifacts?.musicxml_path || "pending"}</code>
      </div>
      {result && (
        <div className="musicxml-strip generation-strip">
          <span>{generation.generator_mode || result?.metadata?.generator_mode || "generator"}</span>
          <code>
            {symbolicModel.loaded
              ? `${symbolicModel.name || "symbolic model"} checkpoint`
              : "rule-based fallback"}
          </code>
        </div>
      )}
      <details className="json-details musicxml-preview">
        <summary>MusicXML text preview</summary>
        <pre>{musicxmlPreview || "Generate a score to inspect MusicXML. TODO: add OpenSheetMusicDisplay or Verovio engraving."}</pre>
      </details>
    </section>
  );
}
