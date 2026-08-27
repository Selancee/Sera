export default function HarmonyProfilePanel({ metadata }) {
  const profile = metadata?.harmony_profile || metadata?.generation_metadata?.harmony_profile || {};
  const voiceLeading = metadata?.voice_leading_report || metadata?.generation_metadata?.voice_leading_report || {};
  const actual = metadata?.actual_harmony_style_report || metadata?.generation_metadata?.actual_harmony_style_report || {};
  if (!profile?.style) return null;
  return (
    <details className="panel compact-report">
      <summary>Harmony profile</summary>
      <div className="research-grid">
        <div className="intent-item">
          <span>style</span>
          <strong>{profile.style}</strong>
        </div>
        <div className="intent-item">
          <span>voicing</span>
          <strong>{profile.voicing_style || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>match</span>
          <strong>{actual.style_harmony_match_score ?? voiceLeading.style_harmony_match_score ?? metadata?.harmony_style_score ?? "-"}</strong>
        </div>
        <div className="intent-item">
          <span>actual style</span>
          <strong>{actual.style || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>voicing source</span>
          <strong>{metadata?.voicing_source || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>plain triads only</span>
          <strong>{actual.plain_triad_only ? "yes" : "no"}</strong>
        </div>
        <div className="intent-item">
          <span>sevenths/extensions</span>
          <strong>{actual.contains_sevenths || actual.contains_extensions ? "yes" : "no"}</strong>
        </div>
        <div className="intent-item">
          <span>parallel fifths</span>
          <strong>{voiceLeading.parallel_fifths_count ?? 0}</strong>
        </div>
      </div>
      {Array.isArray(actual.warnings) && actual.warnings.length > 0 && (
        <ul className="compact-list warning-list">
          {actual.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      <p className="muted-note">{(profile.vocabulary || []).slice(0, 10).join(", ")}</p>
    </details>
  );
}
