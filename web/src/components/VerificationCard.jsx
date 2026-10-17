import { VERIFY_LABELS } from "@/lib/reportLabels";

const STATUS_STYLE = {
  verified: "bg-brand-soft text-brand-strong",
  needs_review: "bg-warn-soft text-warn",
  not_supported: "bg-danger-soft text-danger",
};
const STEP_MARK = {
  true: { icon: "✓", className: "bg-brand text-white", word: "passed" },
  false: { icon: "✕", className: "bg-danger text-white", word: "failed" },
  null: { icon: "?", className: "bg-line text-ink", word: "unclear" },
};
const WEATHER_PASSED = { supported: true, not_supported: false, uncertain: null };
const LEVEL_WORD = {
  en: { low: "low", moderate: "moderate", severe: "severe" },
  kn: { low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", severe: "ತೀವ್ರ" },
};

function Step({ title, passed, children }) {
  const mark = STEP_MARK[String(passed)];
  return (
    <li className="flex gap-3">
      <span
        className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${mark.className}`}
        aria-label={mark.word}
      >
        {mark.icon}
      </span>
      <div className="min-w-0 space-y-1">
        <p className="text-sm font-semibold text-ink">{title}</p>
        {children}
      </div>
    </li>
  );
}

// Step 1 (satellite) + step 2 (weather, checked by Gemini), in English or Kannada.
export default function VerificationCard({ verification, damageLevel, lang = "en" }) {
  if (!verification) return null;
  const t = VERIFY_LABELS[lang];
  const { status, satellite, weather = {} } = verification;
  const facts = weather.facts ?? {};
  const satelliteText =
    satellite?.passed === true
      ? t.satellite.pass(LEVEL_WORD[lang][damageLevel] ?? damageLevel)
      : satellite?.passed === false
        ? t.satellite.fail
        : t.satellite.unknown;
  const explanation = (lang === "kn" && weather.explanation_kn) || weather.explanation_en;

  const factLines = [
    facts.rain_week_region_mm != null && t.facts.week(facts.rain_week_region_mm, facts.normal_week_region_mm ?? "—"),
    facts.max_daily_rain_local_mm != null && t.facts.daily(facts.max_daily_rain_local_mm),
    facts.rain_month_local_mm != null && t.facts.month(facts.rain_month_local_mm, facts.normal_month_local_mm ?? "—"),
    facts.max_temp_c != null && t.facts.heat(facts.max_temp_c),
  ].filter(Boolean);

  return (
    <section className="space-y-3 rounded-lg border border-line p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">{t.title}</h3>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${STATUS_STYLE[status] ?? STATUS_STYLE.needs_review}`}>
          {t.status[status] ?? status}
        </span>
      </div>
      <p className="text-xs text-ink-muted">{t.statusHint[status]}</p>
      <ol className="space-y-3">
        <Step title={t.step1} passed={satellite?.passed ?? null}>
          <p className="text-sm text-ink">{satelliteText}</p>
        </Step>
        <Step title={t.step2} passed={WEATHER_PASSED[weather.verdict] ?? null}>
          <p className="text-sm font-medium text-ink">{t.verdict[weather.verdict] ?? weather.verdict}</p>
          {explanation && <p className="text-sm leading-relaxed text-ink-muted">{explanation}</p>}
          {factLines.length > 0 && (
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-ink-muted">
              {factLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
          <p className="text-xs text-ink-muted">{t.weatherSource}</p>
        </Step>
      </ol>
    </section>
  );
}
