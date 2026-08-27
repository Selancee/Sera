export default function TrackPlanPanel({ metadata, scoreDocument }) {
  const tracks = metadata?.track_plan || metadata?.generation_metadata?.track_plan || scoreDocument?.tracks || [];
  const coverage = metadata?.role_coverage_report || metadata?.generation_metadata?.role_coverage_report || {};
  if (!Array.isArray(tracks) || tracks.length === 0) return null;
  return (
    <details className="panel compact-report">
      <summary>Track plan</summary>
      <div className="research-grid">
        {Object.entries(coverage).map(([key, value]) => (
          <div className="intent-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{value ? "yes" : "no"}</strong>
          </div>
        ))}
      </div>
      <ul className="compact-list">
        {tracks.map((track) => (
          <li key={track.track_id || `${track.staff}-${track.voice}`}>
            {track.role}: {track.instrument} {track.staff} v{track.voice}
          </li>
        ))}
      </ul>
    </details>
  );
}
