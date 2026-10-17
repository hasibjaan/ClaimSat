"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDashboard } from "@/lib/api";
import { EVENT_LABELS, formatDate, LEVEL_LABELS } from "@/lib/format";

const DashboardMap = dynamic(() => import("@/components/DashboardMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-ink/10" />,
});

const CONFIDENCE_SHORT = { high: "High", medium: "Medium", low: "Low" };

function Card({ label, value, tone = "text-ink" }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <p className="text-xs font-medium tracking-wide text-ink-muted uppercase">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export default function DashboardView({ onUnauthorized }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getDashboard().then(
      (d) => !cancelled && setData(d),
      (e) => {
        if (cancelled) return;
        if (e.status === 401) onUnauthorized?.();
        setError(e.message);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [onUnauthorized]);

  const byId = useMemo(() => Object.fromEntries((data?.plots ?? []).map((p) => [p.assessment_id, p])), [data]);

  if (error) {
    return (
      <div className="mx-auto mt-16 max-w-md rounded-xl border border-line bg-surface p-6 text-center">
        <p className="font-semibold text-ink">Could not load the dashboard</p>
        <p className="mt-2 text-sm text-ink-muted">{error}</p>
      </div>
    );
  }
  if (!data) return <p className="p-10 text-center text-ink-muted">Loading dashboard…</p>;

  const { summary, plots, visit_first: visitFirst } = data;
  const event = plots[0];

  return (
    <main className="mx-auto w-full max-w-7xl space-y-5 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">
            Claim<span className="text-brand">Sat</span> · Officer dashboard
          </p>
          <h1 className="text-2xl font-semibold text-ink">Crop damage across assessed plots</h1>
          {event && (
            <p className="text-sm text-ink-muted">
              {EVENT_LABELS[event.event_type]} on {formatDate(event.event_date)} · latest assessment per plot
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {data.source !== "bigquery" && (
            <span className="rounded-full bg-warn-soft px-3 py-1 text-xs font-semibold text-warn">
              {data.source === "cache" ? "Saved demo data" : "Sample data"}
            </span>
          )}
          <Link href="/officer/register" className="flex min-h-11 items-center rounded-lg border border-line bg-surface px-4 text-sm font-medium text-ink hover:bg-surface-muted">
            Register a plot
          </Link>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Card label="Plots assessed" value={summary.plots} />
        <Card label="Severe" value={summary.severe} tone="text-danger" />
        <Card label="Moderate" value={summary.moderate} tone="text-warn" />
        <Card label="Low or none" value={summary.low_or_none} tone="text-brand" />
        <Card label="Hectares affected" value={summary.hectares_affected} />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="h-[55dvh] min-h-80 overflow-hidden rounded-xl border border-line lg:h-[640px]">
          <DashboardMap plots={plots} selectedId={selectedId} onSelect={setSelectedId} />
        </div>

        <aside className="flex flex-col rounded-xl border border-line bg-surface lg:h-[640px]">
          <div className="border-b border-line p-4">
            <h2 className="font-semibold text-ink">Visit first</h2>
            <p className="text-xs text-ink-muted">Highest damage first; higher confidence first when scores tie.</p>
          </div>
          <ol className="flex-1 divide-y divide-line overflow-y-auto">
            {visitFirst.map((id, i) => {
              const plot = byId[id];
              if (!plot) return null;
              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(id)}
                    className={`flex min-h-14 w-full items-center gap-3 px-4 py-2 text-left hover:bg-surface-muted ${
                      selectedId === id ? "bg-brand-soft" : ""
                    }`}
                  >
                    <span className="w-6 text-sm font-semibold text-ink-muted">{i + 1}</span>
                    <span
                      className="size-3 shrink-0 rounded-sm"
                      style={{ background: `var(--color-level-${plot.damage_level})` }}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">
                        {plot.farmer_name || plot.village || plot.plot_id}
                        {plot.survey_number ? ` · Sy. ${plot.survey_number}` : ""}
                      </span>
                      <span className="block text-xs text-ink-muted">
                        {LEVEL_LABELS[plot.damage_level]} · {CONFIDENCE_SHORT[plot.confidence] ?? plot.confidence} confidence · {plot.area_ha} ha
                      </span>
                    </span>
                    <span className="text-lg font-semibold text-ink">{plot.damage_score}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </aside>
      </section>

      <p className="text-xs text-ink-muted">
        Village survey plots are 1-hectare grid cells assessed together in one pass for the demo; they have no individual
        report. Plots assessed by farmers open their full report from the map popup.
      </p>
    </main>
  );
}
