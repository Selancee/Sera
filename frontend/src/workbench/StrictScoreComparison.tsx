import { useMemo } from "react";
import type {
  ScoreDocument,
  ScoreEvent,
  StrictGenerationPreview,
  StrictScoreScope
} from "../score/scoreTypes";

type LocatedEvent = {
  event: ScoreEvent;
  measure: number;
  part: string;
};

type ChangeRow = {
  eventId: string;
  measure: number;
  kind: "added" | "deleted" | "changed";
  before: LocatedEvent | null;
  after: LocatedEvent | null;
  scope: "target" | "protected";
};

export default function StrictScoreComparison({ generation }: { generation: StrictGenerationPreview | null }) {
  const preview = generation?.preview;
  const comparison = useMemo(() => {
    if (!preview?.proposed_score_document || !generation?.patch) return null;
    return compareDocuments(
      preview.score_document,
      preview.proposed_score_document,
      generation.patch.target_scope,
      generation.patch.protected_scope
    );
  }, [generation, preview]);

  if (!comparison || !generation?.patch || !preview) return null;

  return (
    <section aria-label="严格补丁前后乐谱对照" className="strict-score-comparison">
      <div className="strict-comparison-heading">
        <div>
          <span className="eyebrow">未应用提案 · authoritative comparison</span>
          <h2>当前谱面与 ScorePatch 提案</h2>
        </div>
        <div className="strict-comparison-counts">
          <span className="change-badge changed">修改 {comparison.counts.changed}</span>
          <span className="change-badge added">新增 {comparison.counts.added}</span>
          <span className="change-badge deleted">删除 {comparison.counts.deleted}</span>
          <span className="change-badge protected">保护区意外变化 {comparison.protectedChanges}</span>
        </div>
      </div>
      <p className="strict-comparison-note">
        左侧来自当前唯一权威 ScoreDocument；右侧来自尚未提交的事务克隆。只有点击 Apply 且全部验证通过后，右侧才会成为当前谱面。
      </p>
      <div className="strict-comparison-scope">
        <span><strong>Target</strong> {scopeSummary(generation.patch.target_scope)}</span>
        <span><strong>Protected</strong> {scopeSummary(generation.patch.protected_scope) || "目标范围之外"}</span>
        <span><strong>Fingerprint</strong> {shortFingerprint(preview.source_fingerprint)} → {shortFingerprint(preview.post_fingerprint)}</span>
      </div>
      {comparison.rows.length ? (
        <div className="strict-comparison-table-wrap">
          <table className="strict-comparison-table">
            <thead>
              <tr>
                <th>位置</th>
                <th>范围</th>
                <th>当前权威谱面</th>
                <th>未应用提案</th>
                <th>变化</th>
              </tr>
            </thead>
            <tbody>
              {comparison.rows.map((row) => (
                <tr className={`comparison-row ${row.kind} ${row.scope}`} key={`${row.kind}-${row.eventId}`}>
                  <td><strong>M{row.measure}</strong><code>{row.eventId}</code></td>
                  <td><span className={`scope-badge ${row.scope}`}>{row.scope}</span></td>
                  <td>{eventSummary(row.before)}</td>
                  <td>{eventSummary(row.after)}</td>
                  <td><span className={`change-badge ${row.kind}`}>{changeLabel(row.kind)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="strict-comparison-empty">提案未产生事件级变化；请检查全局属性变化或验证报告。</p>
      )}
    </section>
  );
}

function flatten(score: ScoreDocument) {
  const events = new Map<string, LocatedEvent>();
  for (const measure of score.measures) {
    for (const event of measure.events) {
      events.set(event.event_id, { event, measure: measure.number, part: event.part_id || "piano" });
    }
  }
  return events;
}

export function compareDocuments(
  beforeScore: ScoreDocument,
  afterScore: ScoreDocument,
  targetScope: StrictScoreScope,
  protectedScope: StrictScoreScope
) {
  const before = flatten(beforeScore);
  const after = flatten(afterScore);
  const rows: ChangeRow[] = [];
  const ids = new Set([...before.keys(), ...after.keys()]);
  for (const eventId of ids) {
    const oldEvent = before.get(eventId) || null;
    const newEvent = after.get(eventId) || null;
    const kind = !oldEvent ? "added" : !newEvent ? "deleted" : comparableEvent(oldEvent.event) !== comparableEvent(newEvent.event) ? "changed" : null;
    if (!kind) continue;
    const located = newEvent || oldEvent;
    if (!located) continue;
    const target = matchesScope(located, targetScope);
    const explicitlyProtected = matchesScope(located, protectedScope);
    rows.push({
      eventId,
      measure: located.measure,
      kind,
      before: oldEvent,
      after: newEvent,
      scope: target && !explicitlyProtected ? "target" : "protected"
    });
  }
  rows.sort((left, right) => left.measure - right.measure || left.eventId.localeCompare(right.eventId));
  const counts = {
    added: rows.filter((row) => row.kind === "added").length,
    deleted: rows.filter((row) => row.kind === "deleted").length,
    changed: rows.filter((row) => row.kind === "changed").length
  };
  return { rows, counts, protectedChanges: rows.filter((row) => row.scope === "protected").length };
}

function comparableEvent(event: ScoreEvent) {
  return JSON.stringify({
    type: event.type,
    pitch: event.pitch,
    duration: event.duration,
    offset: event.offset,
    voice: event.voice,
    staff: event.staff,
    dynamic: event.dynamic,
    articulations: event.articulations || [],
    tie: event.tie,
    slur: event.slur,
    grace: Boolean(event.grace),
    chord: Boolean(event.is_chord_tone),
    chordGroup: event.chord_group_id || null
  });
}

function matchesScope(located: LocatedEvent, scope: StrictScoreScope) {
  const event = located.event;
  if (scope.whole_score) return true;
  if (scope.exclude_measures?.includes(located.measure) || scope.exclude_event_ids?.includes(event.event_id)) return false;
  const criteria: boolean[] = [];
  if (scope.measures?.length) criteria.push(scope.measures.includes(located.measure));
  if (scope.parts?.length) criteria.push(scope.parts.includes(located.part));
  if (scope.staffs?.length) criteria.push(scope.staffs.some((staff) => String(staff) === String(event.staff)));
  if (scope.voices?.length) criteria.push(scope.voices.includes(event.voice));
  if (scope.event_ids?.length) criteria.push(scope.event_ids.includes(event.event_id));
  return criteria.length > 0 && criteria.every(Boolean);
}

function eventSummary(located: LocatedEvent | null) {
  if (!located) return <span className="missing-event">—</span>;
  const event = located.event;
  const pitch = event.type === "rest" ? "rest" : event.pitch || event.type;
  const notation = [event.dynamic, ...(event.articulations || []), event.tie, event.slur].filter(Boolean).join(" · ");
  return (
    <span className="event-summary">
      <strong>{pitch}</strong>
      <span>{event.duration} · {event.staff} · V{event.voice}</span>
      {notation && <small>{notation}</small>}
    </span>
  );
}

function scopeSummary(scope: StrictScoreScope) {
  const fields: string[] = [];
  if (scope.whole_score) fields.push("whole score");
  if (scope.measures?.length) fields.push(`M${scope.measures.join(",")}`);
  if (scope.parts?.length) fields.push(`part ${scope.parts.join(",")}`);
  if (scope.staffs?.length) fields.push(`staff ${scope.staffs.join(",")}`);
  if (scope.voices?.length) fields.push(`voice ${scope.voices.join(",")}`);
  if (scope.event_ids?.length) fields.push(`${scope.event_ids.length} events`);
  return fields.join(" · ");
}

function shortFingerprint(value: string) {
  return value ? `${value.slice(0, 15)}…${value.slice(-8)}` : "—";
}

function changeLabel(kind: ChangeRow["kind"]) {
  return kind === "added" ? "新增" : kind === "deleted" ? "删除" : "修改";
}
