const STYLES = {
  high: { label: "High confidence", className: "bg-brand-soft text-brand-strong" },
  medium: { label: "Medium confidence", className: "bg-warn-soft text-warn" },
  low: { label: "Low confidence", className: "bg-danger-soft text-danger" },
};

export default function ConfidenceBadge({ confidence }) {
  const style = STYLES[confidence?.level] ?? STYLES.low;
  return (
    <details className="rounded-lg border border-line bg-surface">
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-3 text-sm">
        <span className={`rounded-full px-3 py-1 font-semibold ${style.className}`}>{style.label}</span>
        <span className="text-ink-muted">Why?</span>
      </summary>
      <ul className="list-disc space-y-1 px-8 pb-3 text-sm text-ink-muted">
        {confidence?.reasons?.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </details>
  );
}
