import type { NoteDuration } from "./noteInput";
import { durationFromKey } from "./noteInput";

export type WorkbenchEditMode = "select" | "note_input";

export type WorkbenchShortcutAction =
  | { type: "set_duration"; duration: NoteDuration }
  | { type: "toggle_dotted" }
  | { type: "toggle_note_input" }
  | { type: "input_pitch"; step: string; chordTone: boolean }
  | { type: "input_rest" }
  | { type: "transpose"; semitones: number }
  | { type: "cursor_step"; steps: number }
  | { type: "cursor_measure"; delta: number }
  | { type: "cursor_boundary"; boundary: "start" | "end" }
  | { type: "cursor_pitch"; semitones: number }
  | { type: "switch_staff"; reverse: boolean }
  | { type: "switch_voice" }
  | { type: "set_accidental"; accidental: "sharp" | "flat" }
  | { type: "delete_selection" }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "toggle_playback" }
  | { type: "clear_or_select_mode" }
  | { type: "select_all" };

export type KeyboardEventLike = {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  target?: EventTarget | null;
};

export function mapWorkbenchShortcut(event: KeyboardEventLike, editMode: WorkbenchEditMode): WorkbenchShortcutAction | null {
  if (isTextInput(event.target)) return null;
  const key = event.key;
  const lower = key.toLowerCase();
  const command = Boolean(event.ctrlKey || event.metaKey);

  if (command && lower === "a") return { type: "select_all" };
  if (command && lower === "z") return { type: "undo" };
  if (command && (lower === "y" || (lower === "z" && event.shiftKey))) return { type: "redo" };
  if (command && key === "ArrowLeft") return { type: "cursor_measure", delta: -1 };
  if (command && key === "ArrowRight") return { type: "cursor_measure", delta: 1 };
  if (command && key === "ArrowUp") return { type: "transpose", semitones: 12 };
  if (command && key === "ArrowDown") return { type: "transpose", semitones: -12 };
  if (key === " ") return { type: "toggle_playback" };
  if (key === "Tab") return { type: "switch_staff", reverse: Boolean(event.shiftKey) };
  if (lower === "v") return { type: "switch_voice" };
  if (lower === "n") return { type: "toggle_note_input" };
  if (key === "Escape") return { type: "clear_or_select_mode" };
  if (key === "Delete" || key === "Backspace") return { type: "delete_selection" };
  if (key === "ArrowLeft") return { type: "cursor_step", steps: -1 };
  if (key === "ArrowRight") return { type: "cursor_step", steps: 1 };
  if (key === "ArrowUp") return { type: "cursor_pitch", semitones: event.shiftKey ? 12 : 1 };
  if (key === "ArrowDown") return { type: "cursor_pitch", semitones: event.shiftKey ? -12 : -1 };
  if (key === "Home") return { type: "cursor_boundary", boundary: "start" };
  if (key === "End") return { type: "cursor_boundary", boundary: "end" };
  if (key === ".") return { type: "toggle_dotted" };
  if (key === "+" || key === "=") return { type: "set_accidental", accidental: "sharp" };
  if (key === "-") return { type: "set_accidental", accidental: "flat" };

  const duration = durationFromKey(key);
  if (duration) return { type: "set_duration", duration };

  if (editMode === "note_input") {
    if (/^[a-g]$/i.test(key)) return { type: "input_pitch", step: key.toUpperCase(), chordTone: Boolean(event.shiftKey) };
    if (lower === "r") return { type: "input_rest" };
  }
  return null;
}

export function shortcutLabel(action: WorkbenchShortcutAction["type"]) {
  return {
    set_duration: "1/2/4/8/6",
    toggle_dotted: ".",
    toggle_note_input: "N",
    input_pitch: "A-G",
    input_rest: "R",
    transpose: "Arrow Up/Down",
    cursor_step: "Left/Right",
    cursor_measure: "Ctrl+Left/Right",
    cursor_boundary: "Home/End",
    cursor_pitch: "Up/Down",
    switch_staff: "Tab",
    switch_voice: "V",
    set_accidental: "+/-",
    delete_selection: "Delete",
    undo: "Ctrl+Z",
    redo: "Ctrl+Y",
    toggle_playback: "Space",
    clear_or_select_mode: "Esc",
    select_all: "Ctrl+A"
  }[action];
}

function isTextInput(target: EventTarget | null | undefined) {
  const element = target as HTMLElement | null;
  if (!element) return false;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName) || element.isContentEditable;
}
