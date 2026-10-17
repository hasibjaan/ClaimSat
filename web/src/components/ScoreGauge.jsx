import { LEVEL_LABELS } from "@/lib/format";

const LEVEL_COLOURS = {
  none: "text-brand",
  low: "text-brand",
  moderate: "text-warn",
  severe: "text-danger",
  unknown: "text-ink-muted",
};

// Half-circle gauge for the 0-100 damage score.
// `label` and `outOfLabel` let the report show Kannada text.
export default function ScoreGauge({ score, level, label, outOfLabel = "out of 100" }) {
  const radius = 80;
  const arc = Math.PI * radius;
  const filled = score == null ? 0 : (Math.max(0, Math.min(100, score)) / 100) * arc;
  const colour = LEVEL_COLOURS[level] ?? LEVEL_COLOURS.unknown;

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 112" className="w-48" role="img" aria-label={`Damage score ${score ?? "unknown"} out of 100`}>
        <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="currentColor" strokeWidth="16" strokeLinecap="round" className="text-line" />
        <path
          d="M20 100 A80 80 0 0 1 180 100"
          fill="none"
          stroke="currentColor"
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${arc}`}
          className={colour}
        />
        <text x="100" y="92" textAnchor="middle" className="fill-ink text-[40px] font-semibold">
          {score ?? "—"}
        </text>
        <text x="100" y="110" textAnchor="middle" className="fill-ink-muted text-[11px]">
          {outOfLabel}
        </text>
      </svg>
      <p className={`mt-1 text-lg font-semibold ${colour}`}>{label ?? LEVEL_LABELS[level] ?? level}</p>
    </div>
  );
}
