"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import LanguageToggle from "@/components/LanguageToggle";
import NdviChart from "@/components/NdviChart";
import PhotoCheckResult from "@/components/PhotoCheckResult";
import ScoreGauge from "@/components/ScoreGauge";
import { generateReport, getAssessment, isMock } from "@/lib/api";
import { formatArea, formatDate, formatDateList, pct } from "@/lib/format";
import { CONFIDENCE_NAMES, DATA_SOURCES, EVENT_NAMES, LABELS, LEVEL_NAMES, PHOTO_LABELS } from "@/lib/reportLabels";

const LOCALES = { en: "en-IN", kn: "kn-IN" };
const CONFIDENCE_STYLES = {
  high: "bg-brand-soft text-brand-strong",
  medium: "bg-warn-soft text-warn",
  low: "bg-danger-soft text-danger",
};

function Section({ title, children, className = "" }) {
  return (
    <section className={`break-inside-avoid border-t border-line pt-5 ${className}`}>
      <h2 className="mb-3 text-base font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}

function Metric({ label, value, hint }) {
  return (
    <div className="rounded-lg bg-surface-muted p-3 print:border print:border-line print:bg-surface">
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
      <p className="text-xs text-ink-muted">{hint}</p>
    </div>
  );
}

function Figure({ src, caption }) {
  if (!src) return null;
  return (
    <figure className="break-inside-avoid">
      {/* eslint-disable-next-line @next/next/no-img-element -- satellite PNG from our API */}
      <img src={src} alt={caption} className="aspect-square w-full rounded-lg border border-line object-cover" />
      <figcaption className="mt-1 text-xs text-ink-muted">{caption}</figcaption>
    </figure>
  );
}

function StatusCard({ title, hint, action }) {
  return (
    <div className="mx-auto mt-16 max-w-md rounded-xl border border-line bg-surface p-6 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {hint && <p className="mt-2 text-sm text-ink-muted">{hint}</p>}
      {action}
    </div>
  );
}

export default function ReportView({ id }) {
  const [lang, setLang] = useState("en");
  const [assessment, setAssessment] = useState(null);
  const [phase, setPhase] = useState("loading"); // loading | writing | ready | error
  const [error, setError] = useState(null);

  // Load the assessment; if it has no report yet, ask Gemini to write one.
  // State is only set in promise callbacks, so this is safe to start from an effect.
  const load = useCallback(
    (refresh, isCancelled = () => false) => {
      const fail = (e) => {
        if (isCancelled()) return;
        setError(e.message);
        setPhase("error");
      };
      const write = () =>
        generateReport(id, { refresh }).then((data) => {
          if (isCancelled()) return;
          setAssessment(data);
          setPhase("ready");
        }, fail);

      if (refresh) return write();
      return getAssessment(id).then((data) => {
        if (isCancelled()) return;
        setAssessment(data);
        if (data.report) {
          setPhase("ready");
        } else {
          setPhase("writing");
          return write();
        }
      }, fail);
    },
    [id],
  );

  useEffect(() => {
    let cancelled = false;
    load(false, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load]);

  const retry = (refresh = false) => {
    setPhase(refresh ? "writing" : "loading");
    setError(null);
    load(refresh);
  };

  const t = LABELS[lang];
  const locale = LOCALES[lang];

  if (phase === "loading") return <StatusCard title={t.loading} />;
  if (phase === "error") {
    return (
      <StatusCard
        title={error}
        action={
          <div className="mt-4 flex justify-center gap-2">
            <button type="button" onClick={() => retry()} className="min-h-11 rounded-lg bg-brand px-4 font-medium text-white">
              {t.tryAgain}
            </button>
            <Link href="/farmer" className="flex min-h-11 items-center rounded-lg border border-line px-4 font-medium text-ink">
              {t.back}
            </Link>
          </div>
        }
      />
    );
  }
  if (phase === "writing") {
    return (
      <StatusCard
        title={t.writing}
        hint={t.writingHint}
        action={<div className="mx-auto mt-5 h-1.5 w-40 animate-pulse rounded-full bg-brand" />}
      />
    );
  }

  const { plot, event, metrics, score, confidence, images = {}, acquisitions = {}, report } = assessment;
  const text = (field) => report[`${field}_${lang}`];
  const reasons = lang === "kn" && report.confidence_reasons_kn?.length ? report.confidence_reasons_kn : confidence.reasons;
  const isFlood = event.type === "flood";
  const isDrought = event.type === "drought";

  return (
    <main className={`mx-auto w-full max-w-[210mm] px-4 py-6 print:max-w-none print:p-0 ${lang === "kn" ? "font-kannada" : ""}`} lang={lang}>
      {/* Screen-only toolbar */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Link href="/farmer" className="flex min-h-11 items-center rounded-lg px-2 text-sm font-medium text-brand hover:underline">
          ← {t.back}
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <LanguageToggle value={lang} onChange={setLang} />
          <button type="button" onClick={() => window.print()} className="min-h-11 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong">
            {t.print}
          </button>
        </div>
      </div>

      {(isMock || assessment.source !== "live") && (
        <p className="mb-4 rounded-lg bg-warn-soft p-3 text-sm text-warn print:hidden">
          {assessment.source === "cache" ? "Saved demo result." : "Sample data: these are not real satellite measurements."}
        </p>
      )}
      {report.number_check && !report.number_check.ok && (
        <p className="mb-4 rounded-lg bg-danger-soft p-3 text-sm text-danger">{t.numberWarning}</p>
      )}

      <article className="space-y-6 rounded-2xl bg-surface p-5 shadow-sm sm:p-8 print:rounded-none print:p-0 print:shadow-none">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-lg font-semibold text-ink">
              Claim<span className="text-brand">Sat</span>
            </p>
            <h1 className="text-2xl font-semibold text-ink">{t.title}</h1>
          </div>
          <dl className="text-right text-xs text-ink-muted">
            <div>
              <dt className="inline">{t.assessmentId}: </dt>
              <dd className="inline font-mono text-ink">{assessment.assessment_id}</dd>
            </div>
            <div>
              <dt className="inline">{t.generated}: </dt>
              <dd className="inline text-ink">{formatDate(report.generated_at?.slice(0, 10), locale)}</dd>
            </div>
          </dl>
        </header>

        <p className="rounded-lg border border-warn/40 bg-warn-soft p-3 text-sm font-medium text-warn">{t.disclaimer}</p>

        <section className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-start">
          <div>
            <h2 className="mb-2 text-base font-semibold text-ink">{t.summary}</h2>
            <p className="leading-relaxed text-ink">{text("summary")}</p>
          </div>
          <div className="flex flex-col items-center gap-2">
            <ScoreGauge score={score.damage_score} level={score.damage_level} label={LEVEL_NAMES[lang][score.damage_level]} outOfLabel={t.outOf} />
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${CONFIDENCE_STYLES[confidence.level] ?? CONFIDENCE_STYLES.low}`}>
              {CONFIDENCE_NAMES[lang][confidence.level]}
            </span>
          </div>
        </section>

        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>

        <Section title={t.plotDetails}>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            {[
              [t.farmer, plot.farmer_name || "—"],
              [t.village, plot.village || "—"],
              [t.crop, plot.crop || "—"],
              [t.area, formatArea(plot.area_ha)],
              [t.location, plot.centroid ? `${plot.centroid.lat.toFixed(5)}° N, ${plot.centroid.lng.toFixed(5)}° E` : "—"],
              [t.event, `${EVENT_NAMES[lang][event.type]} · ${formatDate(event.date, locale)}`],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3 border-b border-line py-1">
                <dt className="text-ink-muted">{label}</dt>
                <dd className="text-right font-medium text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section title={t.keyMeasurements}>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Metric label={t.cropHealthLost} value={pct(metrics.ndvi_loss)} hint={t.cropHealthLostHint} />
            {isFlood && <Metric label={t.fieldFlooded} value={pct(metrics.flood_fraction)} hint={t.fieldFloodedHint} />}
            {isDrought && <Metric label={t.rainShortfall} value={pct(metrics.rain_deficit)} hint={t.rainShortfallHint} />}
            <Metric label={t.cropland} value={pct(metrics.crop_fraction)} hint={t.croplandHint} />
            <Metric label={t.damageScore} value={score.damage_score ?? "—"} hint={t.outOf} />
          </div>
        </Section>

        <Section title={t.findings}>
          <ol className="space-y-3">
            {report.findings.map((finding, i) => (
              <li key={i} className="break-inside-avoid">
                <p className="font-semibold text-ink">{finding[`title_${lang}`]}</p>
                <p className="text-sm leading-relaxed text-ink">{finding[`detail_${lang}`]}</p>
              </li>
            ))}
          </ol>
        </Section>

        {Object.keys(images).length > 0 && (
          <Section title={t.images}>
            <div className="grid grid-cols-2 gap-3 print:grid-cols-4">
              <Figure src={images.true_colour_before} caption={t.before} />
              <Figure src={images.true_colour_after} caption={t.after} />
              <Figure src={images.ndvi_after} caption={t.ndviAfter} />
              <Figure src={images.flood_mask} caption={t.floodMask} />
            </div>
            <p className="mt-2 text-xs text-ink-muted">{t.imagesNote}</p>
          </Section>
        )}

        {assessment.photo_check && (
          <Section title={PHOTO_LABELS[lang].title}>
            <PhotoCheckResult check={assessment.photo_check} lang={lang} />
          </Section>
        )}

        <Section title={t.chart}>
          <NdviChart series={assessment.ndvi_series} labels={{ thisYear: t.chartThisYear, normal: t.chartNormal, x: t.chartX, y: t.chartY }} />
        </Section>

        <div className="grid gap-6 sm:grid-cols-2">
          <Section title={t.limitations}>
            <p className="text-sm leading-relaxed text-ink">{text("limitations")}</p>
          </Section>
          <Section title={t.nextSteps}>
            <p className="text-sm leading-relaxed text-ink">{text("recommended_next_steps")}</p>
          </Section>
        </div>

        <Section title={t.sources}>
          <ul className="list-disc space-y-0.5 pl-5 text-xs text-ink-muted">
            {DATA_SOURCES[lang].map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
          <dl className="mt-3 space-y-0.5 text-xs text-ink-muted">
            {[
              [t.s2Before, acquisitions.s2_before],
              [t.s2After, acquisitions.s2_after],
              ...(isFlood ? [[t.s1Before, acquisitions.s1_pre], [t.s1After, acquisitions.s1_post]] : []),
            ].map(([label, dates]) => (
              <div key={label}>
                <dt className="inline font-medium text-ink">{label}: </dt>
                <dd className="inline">{formatDateList(dates, locale, "—")}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section title={t.fingerprint}>
          <p className="font-mono text-xs break-all text-ink">{assessment.evidence_hash}</p>
          <p className="mt-1 text-xs text-ink-muted">{t.fingerprintNote}</p>
          <p className="mt-3 text-xs text-ink-muted">{t.writtenBy}</p>
        </Section>
      </article>

      <div className="mt-4 text-center print:hidden">
        <button type="button" onClick={() => retry(true)} className="min-h-11 rounded-lg px-3 text-sm text-ink-muted underline hover:text-ink">
          {t.regenerate}
        </button>
      </div>
    </main>
  );
}
