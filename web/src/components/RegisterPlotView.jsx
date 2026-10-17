"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { listPlots, registerPlot } from "@/lib/api";
import { formatArea } from "@/lib/format";
import { plotError, polygonAreaHa } from "@/lib/geo";

const PlotMap = dynamic(() => import("@/components/PlotMap"), {
  ssr: false,
  loading: () => <div className="absolute inset-0 animate-pulse bg-ink/10" />,
});

const EMPTY = { farmer_id: "", farmer_name: "", village: "", survey_number: "", crop: "" };
const inputClass =
  "mt-1 block min-h-11 w-full rounded-lg border border-line bg-surface px-3 text-base text-ink focus:border-brand focus:ring-2 focus:ring-brand/30 focus:outline-none";

function Field({ id, label, value, onChange, hint, ...rest }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <input id={id} value={value} onChange={onChange} maxLength={80} className={inputClass} {...rest} />
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

// Officers outline a farmer's plot from the land records. The backend refuses
// outlines that overlap a registered plot and repeated survey numbers.
export default function RegisterPlotView({ onUnauthorized }) {
  const [geometry, setGeometry] = useState(null);
  const [values, setValues] = useState(EMPTY);
  const [registered, setRegistered] = useState([]);
  const [state, setState] = useState({ busy: false, error: null, done: null, submitted: false });
  const [mapKey, setMapKey] = useState(0);

  const handleError = useCallback(
    (err) => {
      if (err.status === 401) onUnauthorized?.();
      return err.message;
    },
    [onUnauthorized],
  );

  useEffect(() => {
    let cancelled = false;
    listPlots().then(
      (data) => !cancelled && setRegistered(data.plots ?? []),
      (err) => !cancelled && setState((s) => ({ ...s, error: handleError(err) })),
    );
    return () => {
      cancelled = true;
    };
  }, [handleError]);

  const set = (field) => (e) => setValues((v) => ({ ...v, [field]: e.target.value }));
  const missing = ["farmer_id", "farmer_name", "village", "survey_number"].filter((k) => !values[k].trim());
  const outlineError = plotError(geometry);

  const submit = async (e) => {
    e.preventDefault();
    setState((s) => ({ ...s, submitted: true, error: null }));
    if (outlineError || missing.length) return;
    setState((s) => ({ ...s, busy: true }));
    try {
      const { plot } = await registerPlot({ ...values, geometry });
      setRegistered((list) => [...list, plot]);
      setState({ busy: false, error: null, done: plot, submitted: false });
    } catch (err) {
      setState((s) => ({ ...s, busy: false, error: handleError(err) }));
    }
  };

  const another = () => {
    setGeometry(null);
    setValues(EMPTY);
    setState({ busy: false, error: null, done: null, submitted: false });
    setMapKey((k) => k + 1); // fresh map without the old outline
  };

  const label = geometry ? formatArea(polygonAreaHa(geometry)) : "Outline the plot from the land records";

  return (
    <div className="relative h-[calc(100dvh-2.75rem-3.5rem)] w-full overflow-hidden">
      <PlotMap key={mapKey} onChange={setGeometry} geometry={geometry} areaLabel={label} registeredPlots={registered} locked={state.busy} />

      <aside className="absolute inset-x-0 bottom-0 z-[1100] flex max-h-[60dvh] flex-col rounded-t-2xl bg-surface shadow-[0_-8px_30px_rgba(0,0,0,0.18)] md:inset-y-3 md:right-3 md:left-auto md:max-h-none md:w-[400px] md:rounded-2xl">
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {state.done ? (
            <div className="space-y-4">
              <p className="rounded-full bg-brand-soft px-3 py-1 text-sm font-semibold text-brand-strong">Plot registered</p>
              <dl className="space-y-1 text-sm">
                {[
                  ["Farmer ID", state.done.farmer_id],
                  ["Farmer", state.done.farmer_name],
                  ["Survey no.", state.done.survey_number],
                  ["Village", state.done.village],
                  ["Area", formatArea(state.done.area_ha)],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3 border-b border-line py-1">
                    <dt className="text-ink-muted">{k}</dt>
                    <dd className="font-medium text-ink">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-sm text-ink-muted">
                The farmer can now enter Farmer ID <b className="text-ink">{state.done.farmer_id}</b> to check this plot.
              </p>
              <button type="button" onClick={another} className="min-h-12 w-full rounded-lg bg-brand font-semibold text-white hover:bg-brand-strong">
                Register another plot
              </button>
            </div>
          ) : (
            <form onSubmit={submit} noValidate className="space-y-4">
              <div>
                <h1 className="text-lg font-semibold text-ink">Register a plot</h1>
                <p className="text-sm text-ink-muted">
                  Use the polygon tool to outline the plot exactly as in the land records. Registered plots are shown dashed.
                </p>
              </div>
              {state.submitted && outlineError && <p className="text-sm font-medium text-danger">{outlineError}</p>}
              <Field id="farmer_id" label="Farmer ID" value={values.farmer_id} onChange={set("farmer_id")} autoCapitalize="characters" hint="From the farmer’s registration (e.g. FRUITS ID)." />
              <Field id="farmer_name" label="Farmer name" value={values.farmer_name} onChange={set("farmer_name")} />
              <div className="grid grid-cols-2 gap-3">
                <Field id="survey_number" label="Survey no." value={values.survey_number} onChange={set("survey_number")} />
                <Field id="crop" label="Main crop" value={values.crop} onChange={set("crop")} />
              </div>
              <Field id="village" label="Village" value={values.village} onChange={set("village")} />
              {state.submitted && missing.length > 0 && (
                <p className="text-sm text-danger">Fill in the farmer ID, name, survey number and village.</p>
              )}
              {state.error && (
                <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
                  {state.error}
                </p>
              )}
              <button
                type="submit"
                disabled={state.busy}
                className="min-h-12 w-full rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
              >
                {state.busy ? "Registering…" : "Register plot"}
              </button>
            </form>
          )}
        </div>
      </aside>
    </div>
  );
}
