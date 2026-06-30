import type { DragPreview } from "../score/dragEditing";

export default function DragEditOverlay({ preview }: { preview: DragPreview | null }) {
  if (!preview || (!preview.semitones && !preview.offsetDelta)) return null;
  return (
    <div className="drag-edit-overlay">
      <strong>{preview.semitones > 0 ? "+" : ""}{preview.semitones} st</strong>
      <span>offset {preview.offsetDelta > 0 ? "+" : ""}{preview.offsetDelta}</span>
      {preview.previewPitches.length > 0 && <small>{preview.previewPitches.join(", ")}</small>}
      {preview.warning && <small>{preview.warning}</small>}
    </div>
  );
}
