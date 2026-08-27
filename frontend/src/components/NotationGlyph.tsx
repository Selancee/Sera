import { formatDuration, type Translate } from "../i18n/musicTerms";

type Props = {
  duration: string;
  kind?: "note" | "rest";
  label?: string;
  size?: number;
};

export function NotationGlyph({ duration, kind = "note", size = 34 }: Props) {
  const baseDuration = duration.replace(/^dotted_/, "");
  const dotted = duration.startsWith("dotted_");
  const isRest = kind === "rest" || duration === "rest";
  const filled = !["whole", "half"].includes(baseDuration);
  const hasStem = !isRest && baseDuration !== "whole";
  const hasFlag = ["eighth", "sixteenth", "triplet_eighth"].includes(baseDuration);
  const hasSecondFlag = baseDuration === "sixteenth";
  return (
    <svg aria-hidden="true" className={`notation-glyph ${isRest ? "rest" : "note"} duration-${baseDuration}`} focusable="false" height={size} viewBox="0 0 44 44" width={size}>
      {isRest ? (
        <>
          <path className="rest-mark" d="M13 16h18v5H13zM18 21h13v5H18z" />
          <path className="rest-hook" d="M25 25c-7 3-7 7 0 10" />
        </>
      ) : (
        <>
          <ellipse className={filled ? "note-head filled" : "note-head open"} cx="18" cy="29" rx="9" ry="6" transform="rotate(-18 18 29)" />
          {hasStem && <path className="note-stem" d="M26 27V7" />}
          {hasFlag && <path className="note-flag" d="M26 7c10 3 10 10 0 13" />}
          {hasSecondFlag && <path className="note-flag second" d="M26 13c9 3 9 10 0 13" />}
        </>
      )}
      {dotted && <circle className="duration-dot" cx="35" cy="27" r="2.2" />}
      {baseDuration === "triplet_eighth" && <text className="tuplet-mark" x="7" y="10">3</text>}
    </svg>
  );
}

export function DurationGlyphLabel({ duration, t }: { duration: string; t: Translate }) {
  return (
    <>
      <NotationGlyph duration={duration} label={formatDuration(duration, t)} />
      <span className="sr-only">{formatDuration(duration, t)}</span>
    </>
  );
}
