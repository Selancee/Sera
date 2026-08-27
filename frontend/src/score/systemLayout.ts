import { layoutConfigForMode, readableScoreWidth, type ScoreLayoutMode } from "./layoutConfig";

export type SystemMeasureLayout = {
  measureIndex: number;
  measureNumber: number;
  systemIndex: number;
  x: number;
  y: number;
  width: number;
  rightStaffTop: number;
  leftStaffTop: number;
};

export type SystemLayoutResult = {
  width: number;
  height: number;
  measuresPerSystem: number;
  systems: Array<{ index: number; y: number; measureIndexes: number[] }>;
  measures: SystemMeasureLayout[];
};

export const SYSTEM_MEASURE_TOP = 42;
export const SYSTEM_RIGHT_STAFF_TOP = 74;
export const SYSTEM_LEFT_STAFF_TOP = 170;
export const SYSTEM_MEASURE_HEIGHT = 176;

export function buildSystemLayout(measureCount: number, mode: ScoreLayoutMode = "fit_width"): SystemLayoutResult {
  const config = layoutConfigForMode(mode);
  const count = Math.max(1, measureCount);
  const measuresPerSystem = Math.max(1, Math.min(config.maxMeasuresPerSystem, config.measuresPerSystem, count));
  const width = readableScoreWidth(count, mode);
  const measureWidth = Math.max(
    config.minMeasureWidth,
    Math.min(config.maxMeasureWidth, (width - config.pagePadding * 2) / measuresPerSystem)
  );
  const systems: SystemLayoutResult["systems"] = [];
  const measures: SystemMeasureLayout[] = [];

  for (let index = 0; index < count; index += 1) {
    const systemIndex = Math.floor(index / measuresPerSystem);
    const positionInSystem = index % measuresPerSystem;
    const systemY = config.pagePadding + systemIndex * (SYSTEM_MEASURE_HEIGHT + config.systemSpacing);
    if (!systems[systemIndex]) {
      systems[systemIndex] = { index: systemIndex, y: systemY, measureIndexes: [] };
    }
    systems[systemIndex].measureIndexes.push(index);
    measures.push({
      measureIndex: index,
      measureNumber: index + 1,
      systemIndex,
      x: config.pagePadding + positionInSystem * measureWidth,
      y: systemY,
      width: measureWidth,
      rightStaffTop: systemY + SYSTEM_RIGHT_STAFF_TOP,
      leftStaffTop: systemY + SYSTEM_LEFT_STAFF_TOP
    });
  }

  const height = config.pagePadding * 2 + systems.length * SYSTEM_MEASURE_HEIGHT + Math.max(0, systems.length - 1) * config.systemSpacing;
  return { width, height, measuresPerSystem, systems, measures };
}

export function measureLayoutAt(layout: SystemLayoutResult, measureIndex: number): SystemMeasureLayout {
  return layout.measures[Math.max(0, Math.min(layout.measures.length - 1, measureIndex))];
}
