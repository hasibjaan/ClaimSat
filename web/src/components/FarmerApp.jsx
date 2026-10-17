"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import AssessForm from "@/components/AssessForm";
import LoadingSteps from "@/components/LoadingSteps";
import ResultsPanel from "@/components/ResultsPanel";
import { assess, getFarmerPlots, isMock } from "@/lib/api";
import { formatArea } from "@/lib/format";

const FarmerPlotMap = dynamic(() => import("@/components/FarmerPlotMap"), {
  ssr: false,
  loading: () => <div className="absolute inset-0 animate-pulse bg-ink/10" />,
});

const EMPTY_VALUES = { event_type: "flood", event_date: "", crop: "" };
const inputClass =
  "block min-h-12 w-full rounded-lg border border-line bg-surface px-3 text-lg tracking-wide text-ink uppercase focus:border-brand focus:ring-2 focus:ring-brand/30 focus:outline-none";

// Farmers pick from the plots an agriculture officer registered to their
// Farmer ID. They can't draw or change a plot outline.
export default function FarmerApp() {
  const [farmerId, setFarmerId] = useState("");
  const [plots, setPlots] = useState(null);
  const [lookup, setLookup] = useState({ busy: false, error: null });
  const [selectedId, setSelectedId] = useState(null);
  const [values, setValues] = useState(EMPTY_VALUES);
  const [status, setStatus] = useState("idle"); // idle | loading | done
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(true);

  const selected = plots?.find((p) => p.plot_id === selectedId) ?? null;

  const findPlots = async (e) => {
    e.preventDefault();
    if (!farmerId.trim()) {
      setLookup({ busy: false, error: "Enter your Farmer ID." });
      return;
    }
    setLookup({ busy: true, error: null });
    try {
      const data = await getFarmerPlots(farmerId);
      setPlots(data.plots);
      setLookup({ busy: false, error: null });
      if (data.plots.length === 1) selectPlot(data.plots[0]);
    } catch (err) {
      setLookup({ busy: false, error: err.message });
    }
  };

  const selectPlot = (plot) => {
    setSelectedId(plot.plot_id);
    setValues({
      ...EMPTY_VALUES,
      ...(plot.default_event
        ? {
            event_type: plot.default_event.event_type,
            event_date: plot.default_event.event_date,
          }
        : {}),
      crop: plot.crop ?? "",
    });
    setResult(null);
    setError(null);
    setStatus("idle");
    setSheetOpen(true);
  };

  const changeFarmer = () => {
    setPlots(null);
    setSelectedId(null);
    setResult(null);
    setStatus("idle");
    setError(null);
  };

  const submit = async () => {
    setStatus("loading");
    setError(null);
    setSheetOpen(true);
    try {
      const data = await assess({
        plot_id: selectedId,
        event_type: values.event_type,
        event_date: values.event_date,
        crop: values.crop,
      });
      setResult(data);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  };

  const mapLabel = selected
    ? `Survey no. ${selected.survey_number} · ${formatArea(selected.area_ha)}`
    : plots
      ? "Tap one of your plots"
      : "Enter your Farmer ID to see your land";

  return (
    <div className="relative h-[calc(100dvh-2.75rem)] w-full overflow-hidden">
      <FarmerPlotMap plots={plots ?? []} selectedId={selectedId} onSelect={(id) => selectPlot(plots.find((p) => p.plot_id === id))} label={mapLabel} />

      <aside
        className={`absolute inset-x-0 bottom-0 z-[1100] flex flex-col rounded-t-2xl bg-surface shadow-[0_-8px_30px_rgba(0,0,0,0.18)] transition-[max-height] duration-300 md:inset-y-3 md:right-3 md:left-auto md:w-[420px] md:max-h-none md:rounded-2xl ${
          sheetOpen ? "max-h-[65dvh]" : "max-h-16"
        }`}
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <Link href="/" className="text-base font-semibold text-ink">
              Claim<span className="text-brand">Sat</span>
            </Link>
            <p className="text-xs text-ink-muted">Farmer · check your field</p>
          </div>
          <button
            type="button"
            onClick={() => setSheetOpen((open) => !open)}
            className="min-h-11 shrink-0 rounded-lg border border-line px-3 text-sm font-medium whitespace-nowrap text-ink md:hidden"
            aria-expanded={sheetOpen}
          >
            {sheetOpen ? "Show map" : "Show panel"}
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-4">
          {isMock && (
            <p className="mb-4 rounded-lg bg-warn-soft p-2 text-xs text-warn">
              Mock mode: results are sample data, not real satellite measurements.
            </p>
          )}
          <div className="space-y-5 pb-4">
            {status === "loading" && <LoadingSteps eventType={values.event_type} />}
            {status === "done" && result && <ResultsPanel result={result} onReset={() => setStatus("idle")} />}

            {status === "idle" && !plots && (
              <form onSubmit={findPlots} className="space-y-4" noValidate>
                <div>
                  <h2 className="text-lg font-semibold text-ink">Find your registered land</h2>
                  <p className="mt-1 text-sm text-ink-muted">
                    Your agriculture office registers your plot from the land records. Enter the Farmer ID on your
                    registration slip.
                  </p>
                </div>
                <div>
                  <label htmlFor="farmer_id" className="block text-sm font-medium text-ink">
                    Farmer ID
                  </label>
                  <input
                    id="farmer_id"
                    value={farmerId}
                    onChange={(e) => setFarmerId(e.target.value)}
                    autoComplete="off"
                    autoCapitalize="characters"
                    placeholder="KA-DEMO-001"
                    className={`mt-1 ${inputClass}`}
                  />
                  <p className="mt-1 text-xs text-ink-muted">Demo: KA-DEMO-001</p>
                </div>
                {lookup.error && (
                  <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
                    {lookup.error}
                  </p>
                )}
                <button
                  type="submit"
                  disabled={lookup.busy}
                  className="min-h-12 w-full rounded-lg bg-brand px-4 text-base font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
                >
                  {lookup.busy ? "Looking up…" : "Find my land"}
                </button>
              </form>
            )}

            {status === "idle" && plots && (
              <>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">Namaskara, {plots[0].farmer_name}</h2>
                    <p className="text-sm text-ink-muted">Choose the plot that was damaged.</p>
                  </div>
                  <button type="button" onClick={changeFarmer} className="min-h-11 shrink-0 text-sm font-medium text-brand hover:underline">
                    Not you?
                  </button>
                </div>

                <ul className="space-y-2" role="radiogroup" aria-label="Your registered plots">
                  {plots.map((plot) => (
                    <li key={plot.plot_id}>
                      <button
                        type="button"
                        role="radio"
                        aria-checked={plot.plot_id === selectedId}
                        onClick={() => selectPlot(plot)}
                        className={`flex min-h-14 w-full items-center justify-between gap-3 rounded-lg border px-4 py-2 text-left ${
                          plot.plot_id === selectedId ? "border-brand bg-brand-soft" : "border-line hover:bg-surface-muted"
                        }`}
                      >
                        <span>
                          <span className="block font-medium text-ink">Survey no. {plot.survey_number}</span>
                          <span className="block text-xs text-ink-muted">
                            {plot.village} · {formatArea(plot.area_ha)}
                            {plot.crop ? ` · ${plot.crop}` : ""}
                          </span>
                        </span>
                        <span
                          className={`size-5 shrink-0 rounded-full border-2 ${plot.plot_id === selectedId ? "border-brand bg-brand" : "border-line"}`}
                          aria-hidden="true"
                        />
                      </button>
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-ink-muted">
                  Plot outlines come from the land records and can only be changed by the agriculture office.
                </p>

                {selected && <AssessForm values={values} onValuesChange={setValues} onSubmit={submit} serverError={error} />}
              </>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
