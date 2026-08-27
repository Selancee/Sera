export type ScoreLayoutMode = "fit_width" | "page" | "continuous" | "compact" | "large_print";

export type ScoreLayoutConfig = {
  defaultLayoutMode: ScoreLayoutMode;
  measuresPerSystem: number;
  minMeasuresPerSystem: number;
  minMeasureWidth: number;
  maxMeasureWidth: number;
  maxMeasuresPerSystem: number;
  staffSpacing: number;
  grandStaffSpacing: number;
  systemSpacing: number;
  pagePadding: number;
  defaultZoom: number;
  autoFitWidth: boolean;
  showMeasureNumbers: boolean;
  showSectionLabels: boolean;
  showHarmonyLabels: boolean;
  autoScrollToFirstSystem: boolean;
  minPageWidth: number;
};

export const DEFAULT_LAYOUT_CONFIG: ScoreLayoutConfig = {
  defaultLayoutMode: "fit_width",
  measuresPerSystem: 4,
  minMeasuresPerSystem: 3,
  minMeasureWidth: 160,
  maxMeasureWidth: 240,
  maxMeasuresPerSystem: 4,
  staffSpacing: 72,
  grandStaffSpacing: 96,
  systemSpacing: 120,
  pagePadding: 32,
  defaultZoom: 1,
  autoFitWidth: true,
  showMeasureNumbers: true,
  showSectionLabels: true,
  showHarmonyLabels: true,
  autoScrollToFirstSystem: true,
  minPageWidth: 920
};

export function layoutConfigForMode(mode: ScoreLayoutMode): ScoreLayoutConfig {
  if (mode === "compact") {
    return { ...DEFAULT_LAYOUT_CONFIG, minMeasureWidth: 136, maxMeasureWidth: 184, maxMeasuresPerSystem: 5, measuresPerSystem: 5, staffSpacing: 64, grandStaffSpacing: 84, systemSpacing: 96, defaultZoom: 0.9 };
  }
  if (mode === "large_print") {
    return { ...DEFAULT_LAYOUT_CONFIG, minMeasureWidth: 184, maxMeasureWidth: 260, maxMeasuresPerSystem: 3, measuresPerSystem: 3, staffSpacing: 86, grandStaffSpacing: 116, systemSpacing: 144, defaultZoom: 1.25, minPageWidth: 1040 };
  }
  if (mode === "page") {
    return { ...DEFAULT_LAYOUT_CONFIG, maxMeasuresPerSystem: 4, autoFitWidth: false, minPageWidth: 980 };
  }
  if (mode === "continuous") {
    return { ...DEFAULT_LAYOUT_CONFIG, maxMeasuresPerSystem: 4, measuresPerSystem: 4, autoFitWidth: false, minPageWidth: 980 };
  }
  return DEFAULT_LAYOUT_CONFIG;
}

export function readableScoreWidth(measureCount: number, mode: ScoreLayoutMode): number {
  const config = layoutConfigForMode(mode);
  const perSystem = Math.max(1, Math.min(config.maxMeasuresPerSystem, config.measuresPerSystem, Math.max(1, measureCount)));
  const contentWidth = perSystem * config.minMeasureWidth + config.pagePadding * 2;
  return Math.max(config.minPageWidth, contentWidth);
}

export function zoomPresetValue(preset: string, containerWidth = 920, scoreWidth = 920): number {
  if (preset === "fit_width") return clamp(containerWidth / Math.max(1, scoreWidth), 0.2, 1.5);
  if (preset === "fit_page") return clamp((containerWidth - 32) / Math.max(1, scoreWidth), 0.2, 1.2);
  const numeric = Number(String(preset).replace("%", ""));
  return Number.isFinite(numeric) ? clamp(numeric / 100, 0.5, 2) : 1;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
