export default function KeyboardShortcutsHelp() {
  const rows = [
    ["Left / Right", "Move cursor by snap grid"],
    ["Ctrl+Left / Ctrl+Right", "Previous / next measure"],
    ["Up / Down", "Move pitch or selected notes"],
    ["Ctrl+Up / Ctrl+Down", "Octave movement"],
    ["Tab / Shift+Tab", "Switch staff"],
    ["V", "Switch voice"],
    ["N", "Toggle Note Input"],
    ["1 2 4 8 6", "Duration"],
    ["A-G / R", "Input note or rest"],
    [".", "Toggle dotted duration"],
    ["+ / -", "Sharp / flat"],
    ["Delete", "Delete selection"],
    ["Space", "Play / stop"],
    ["Ctrl+Z / Ctrl+Y", "Undo / redo"]
  ];
  return (
    <details className="shortcut-help">
      <summary>Shortcuts</summary>
      <div className="shortcut-grid">
        {rows.map(([keys, action]) => (
          <span key={keys}>
            <strong>{keys}</strong>
            {action}
          </span>
        ))}
      </div>
    </details>
  );
}
