"use client";

import Link from "next/link";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import NdviChart from "@/components/NdviChart";
import PhotoUpload from "@/components/PhotoUpload";
import ScoreGauge from "@/components/ScoreGauge";
import VerificationCard from "@/components/VerificationCard";
import { EVENT_LABELS, formatArea, formatDate, LEVEL_LABELS, pct } from "@/lib/format";
import { VERIFY_LABELS } from "@/lib/reportLabels";

const t = VERIFY_LABELS.en;

function Metric({ label, value, hint }) {
  return (
    <div className="rounded-lg bg-surface-muted p-3">
      <p className="text-xs font-medium tracking-wide text-ink-muted uppercase">{label}</p>
      <p className="mt-1 text-xl font-semibold text-ink">{value}</p>
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {children}
    </section>
  );
}

export default function ResultsPanel({ result, onReset }) {
  const { metrics, event, images = {}, plot, severity, area, score } = result;
  const isFlood = event.type === "flood";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">Result for your field</h2>
          <p className="text-sm text-ink-muted">
            {EVENT_LABELS[event.type]} on {formatDate(event.date)} · {formatArea(plot.area_ha)}
          </p>
        </div>
        {result.source !== "live" && (
          <span className="shrink-0 rounded-full bg-warn-soft px-3 py-1 text-xs font-semibold text-warn">
            {result.source === "cache" ? "Saved demo result" : "Sample data"}
          </span>
        )}
      </div>

      {/* Case severity: this plot's damage + nearby reports */}
      <section className="space-y-2">
        <h3 className="text-center text-sm font-semibold text-ink">{t.severity}</h3>
        <ScoreGauge
          score={severity?.score ?? score.damage_score}
          level={severity?.level ?? score.damage_level}
          label={t.severityLevel[severity?.level ?? score.damage_level]}
        />
        <p className="text-center text-xs text-ink-muted">{t.severityHint}</p>
        {severity?.reasons?.length > 0 && (
          <ul className="list-disc space-y-0.5 rounded-lg bg-surface-muted px-8 py-2 text-xs text-ink-muted">
            {severity.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </section>

      <VerificationCard verification={result.verification} damageLevel={score.damage_level} />

      <div className="grid grid-cols-2 gap-2">
        <Metric label={t.plotDamage} value={score.damage_score ?? "—"} hint={LEVEL_LABELS[score.damage_level]} />
        {area && (
          <Metric label={t.nearby} value={area.nearby_farmers} hint={t.areaLevel[area.level] ?? area.level} />
        )}
        <Metric label="Crop health lost" value={pct(metrics.ndvi_loss)} hint="vs. 1 week before" />
        {isFlood && <Metric label="Newly under water" value={pct(metrics.flood_fraction)} hint="dry 1 week before" />}
      </div>
      {area && <p className="-mt-3 text-xs text-ink-muted">{t.nearbyText(area.nearby_farmers, area.radius_km, area.window_days)}</p>}

      <ConfidenceBadge confidence={result.confidence} />

      {images.true_colour_before && images.true_colour_now ? (
        <Section title="1 week before vs now">
          <BeforeAfterSlider
            before={images.true_colour_before}
            after={images.true_colour_now}
            beforeLabel={`Before · ${formatDate(metrics.before_image_date)}`}
            afterLabel={`Now · ${formatDate(metrics.now_image_date)}`}
          />
          <p className="text-xs text-ink-muted">
            Both images are from Sentinel-2. Your plot is outlined in yellow; grey areas were hidden by cloud.
          </p>
        </Section>
      ) : (
        <p className="rounded-lg bg-surface-muted p-3 text-sm text-ink-muted">Satellite images couldn&apos;t be generated for this plot.</p>
      )}

      {(images.ndvi_now || images.flood_mask) && (
        <div className="grid grid-cols-2 gap-2">
          {images.ndvi_now && (
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element -- satellite PNG from our API */}
              <img src={images.ndvi_now} alt="Crop health now" className="aspect-square w-full rounded-lg object-cover" />
              <figcaption className="mt-1 text-xs text-ink-muted">Crop health now (green = healthy)</figcaption>
            </figure>
          )}
          {images.flood_mask && (
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={images.flood_mask} alt="Land that became water since the week before" className="aspect-square w-full rounded-lg object-cover" />
              <figcaption className="mt-1 text-xs text-ink-muted">New water since the week before (blue)</figcaption>
            </figure>
          )}
        </div>
      )}

      <Section title="Crop health over time">
        <NdviChart series={result.ndvi_series} />
      </Section>

      <PhotoUpload key={result.assessment_id} assessmentId={result.assessment_id} initialCheck={result.photo_check} />

      <div className="-mx-4 space-y-2 border-t border-line bg-surface px-4 pt-3 pb-4 md:sticky md:bottom-0">
        <Link
          href={`/report/${result.assessment_id}`}
          className="flex min-h-12 w-full items-center justify-center rounded-lg bg-brand px-4 text-base font-semibold text-white hover:bg-brand-strong"
        >
          Generate report
        </Link>
        <button
          type="button"
          onClick={onReset}
          className="min-h-11 w-full rounded-lg border border-line px-4 text-sm font-medium text-ink hover:bg-surface-muted"
        >
          Check another field
        </button>
      </div>
    </div>
  );
}
