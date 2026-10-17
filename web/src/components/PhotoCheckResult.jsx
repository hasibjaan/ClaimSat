import { formatDate } from "@/lib/format";
import { PHOTO_FLAGS, PHOTO_LABELS, PHOTO_SHOWS } from "@/lib/reportLabels";

const LOCALES = { en: "en-IN", kn: "kn-IN" };

// Shows a stored photo check, in English or Kannada (used on results and the report).
export default function PhotoCheckResult({ check, lang = "en", compact = false }) {
  const t = PHOTO_LABELS[lang];
  // Green only when Gemini sees agreement AND the photo's place and date check out.
  const verdict = !check.consistent ? "differs" : check.flags?.length ? "matchesWithWarnings" : "matches";
  const location =
    check.inside_plot == null ? t.unknown : check.inside_plot ? t.inside : t.away(check.distance_m);
  const taken = check.taken_at
    ? `${formatDate(check.taken_at.slice(0, 10), LOCALES[lang])} · ${t.daysAfter(check.days_from_event)}`
    : t.unknown;

  return (
    <div className={`grid gap-3 ${compact ? "" : "sm:grid-cols-[200px_1fr] print:grid-cols-[160px_1fr]"}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- user photo served by our API */}
      <img
        src={check.photo_url}
        alt={t.title}
        className={`w-full rounded-lg border border-line object-cover ${compact ? "max-h-56" : "aspect-square"}`}
      />
      <div className="space-y-2 text-sm">
        <p
          className={`inline-block rounded-full px-3 py-1 font-semibold ${
            verdict === "matches" ? "bg-brand-soft text-brand-strong" : "bg-warn-soft text-warn"
          }`}
        >
          {t[verdict]}
        </p>
        <p className="leading-relaxed text-ink">{check[`observations_${lang}`]}</p>
        <dl className="space-y-0.5 text-xs text-ink-muted">
          <div>
            <dt className="inline font-medium text-ink">{t.shows}: </dt>
            <dd className="inline">{PHOTO_SHOWS[lang][check.what_photo_shows] ?? check.what_photo_shows}</dd>
          </div>
          <div>
            <dt className="inline font-medium text-ink">{t.taken}: </dt>
            <dd className="inline">{taken}</dd>
          </div>
          <div>
            <dt className="inline font-medium text-ink">{t.location}: </dt>
            <dd className="inline">{location}</dd>
          </div>
        </dl>
        {check.flags?.length > 0 && (
          <ul className="space-y-1 rounded-lg bg-warn-soft p-2 text-xs text-warn">
            {check.flags.map((flag) => (
              <li key={flag}>⚠ {PHOTO_FLAGS[lang][flag] ?? flag}</li>
            ))}
          </ul>
        )}
        <p className="text-xs text-ink-muted">{t.note}</p>
      </div>
    </div>
  );
}
