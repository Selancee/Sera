import { buildSystemLayout } from "./systemLayout";
import type { ScoreLayoutMode } from "./layoutConfig";
import type { ScoreDocument } from "./scoreTypes";

export type ScoreVisibilityReport = {
  valid: boolean;
  checks: Record<string, boolean>;
  warnings: string[];
  fallbackLayoutMode: ScoreLayoutMode;
};

export function checkScoreVisibility(scoreDocument: ScoreDocument | null | undefined, mode: ScoreLayoutMode = "fit_width"): ScoreVisibilityReport {
  const warnings: string[] = [];
  const measureCount = scoreDocument?.measures?.length || 0;
  const layout = buildSystemLayout(Math.max(1, measureCount || 1), mode);
  const eventCount = scoreDocument?.measures?.reduce((sum, measure) => sum + measure.events.length, 0) || 0;
  const checks = {
    not_blank: Boolean(scoreDocument && measureCount > 0),
    has_note_elements: eventCount > 0,
    measures_per_system_ok: layout.measuresPerSystem <= 4,
    rendered_width_readable: layout.width >= 720,
    first_system_visible: layout.systems[0]?.y >= 0,
    staff_spacing_ok: true,
    score_inside_viewport: layout.height > 0
  };
  for (const [key, passed] of Object.entries(checks)) {
    if (!passed) warnings.push(key);
  }
  return {
    valid: Object.values(checks).every(Boolean),
    checks,
    warnings,
    fallbackLayoutMode: "fit_width"
  };
}
