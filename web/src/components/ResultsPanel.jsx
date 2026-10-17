"use client";

import Link from "next/link";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import NdviChart from "@/components/NdviChart";
import PhotoUpload from "@/components/PhotoUpload";
import ScoreGauge from "@/components/ScoreGauge";
import { EVENT_LABELS, formatArea, formatDate, formatDateList, pct } from "@/lib/format";

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
  const { metrics, event, images = {}, acquisitions = {}, plot } = result;
  const isFlood = event.type === "flood";
  const isDrought = event.type === "drought";

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

      <ScoreGauge score={result.score.damage_score} level={result.score.damage_level} />
      <ConfidenceBadge confidence={result.confidence} />

      <div className="grid grid-cols-2 gap-2">
        <Metric label="Crop health lost" value={pct(metrics.ndvi_loss)} hint="vs. the last 3 years" />
        {isFlood && <Metric label="Field flooded" value={pct(metrics.flood_fraction)} hint="from radar" />}
        {isDrought && (
          <Metric
            label="Rain shortfall"
            value={pct(metrics.rain_deficit)}
            hint={metrics.season_rain_mm != null ? `${Math.round(metrics.season_rain_mm)} mm vs ${Math.round(metrics.baseline_rain_mm)} mm normal` : "vs. 20-year normal"}
          />
        )}
        <Metric label="Cropland" value={pct(metrics.crop_fraction)} hint="share of the plot" />
        {!isFlood && !isDrought && <Metric label="Clear images" value={`${metrics.clear_obs_before} / ${metrics.clear_obs_after}`} hint="before / after" />}
      </div>

      {images.true_colour_before && images.true_colour_after ? (
        <Section title="Before and after">
          <BeforeAfterSlider
            before={images.true_colour_before}
            after={images.true_colour_after}
            beforeLabel="Before"
            afterLabel="After"
          />
          <p className="text-xs text-ink-muted">Your plot is outlined in yellow. Grey areas were hidden by cloud.</p>
        </Section>
      ) : (
        <p className="rounded-lg bg-surface-muted p-3 text-sm text-ink-muted">Satellite images couldn&apos;t be generated for this plot.</p>
      )}

      {(images.ndvi_after || images.flood_mask) && (
        <div className="grid grid-cols-2 gap-2">
          {images.ndvi_after && (
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element -- satellite PNG from our API */}
              <img src={images.ndvi_after} alt="Crop health after the event" className="aspect-square w-full rounded-lg object-cover" />
              <figcaption className="mt-1 text-xs text-ink-muted">Crop health after (green = healthy)</figcaption>
            </figure>
          )}
          {images.flood_mask && (
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={images.flood_mask} alt="Flooded area detected by radar" className="aspect-square w-full rounded-lg object-cover" />
              <figcaption className="mt-1 text-xs text-ink-muted">Flooded area (blue), from radar</figcaption>
            </figure>
          )}
        </div>
      )}

      <Section title="Crop health over time">
        <NdviChart series={result.ndvi_series} />
      </Section>

      <Section title="Satellite images used">
        <dl className="space-y-1 text-xs text-ink-muted">
          <div><dt className="inline font-medium text-ink">Sentinel-2 before: </dt><dd className="inline">{formatDateList(acquisitions.s2_before)}</dd></div>
          <div><dt className="inline font-medium text-ink">Sentinel-2 after: </dt><dd className="inline">{formatDateList(acquisitions.s2_after)}</dd></div>
          {isFlood && (
            <>
              <div><dt className="inline font-medium text-ink">Radar before: </dt><dd className="inline">{formatDateList(acquisitions.s1_pre)}</dd></div>
              <div><dt className="inline font-medium text-ink">Radar after: </dt><dd className="inline">{formatDateList(acquisitions.s1_post)}</dd></div>
            </>
          )}
        </dl>
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
