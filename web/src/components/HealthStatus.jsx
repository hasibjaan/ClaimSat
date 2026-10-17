"use client";

import { useCallback, useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

const SERVICE_LABELS = {
  earth_engine: "Earth Engine",
  vertex_ai: "Vertex AI (Gemini)",
  bigquery: "BigQuery",
};

export default function HealthStatus() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  // Returns a promise of the next state; callers apply it once the request settles.
  const fetchHealth = useCallback(
    () =>
      getHealth().then(
        (data) => ({ loading: false, data, error: null }),
        (error) => ({ loading: false, data: null, error: error.message }),
      ),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    fetchHealth().then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [fetchHealth]);

  const load = async () => {
    setState({ loading: true, data: null, error: null });
    setState(await fetchHealth());
  };

  const { loading, data, error } = state;

  return (
    <section className="mt-8 rounded-xl border border-line bg-surface p-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-semibold text-ink">Service status</h2>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="min-h-11 rounded-lg border border-line px-4 text-sm font-medium text-ink hover:bg-surface-muted disabled:opacity-50"
        >
          {loading ? "Checking…" : "Check again"}
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {data && (
        <>
          <ul className="mt-4 divide-y divide-line">
            {Object.entries(data.services).map(([key, service]) => (
              <li key={key} className="flex items-start gap-3 py-3">
                <span
                  className={`mt-1.5 size-2.5 shrink-0 rounded-full ${
                    service.status === "ok" ? "bg-brand" : "bg-danger"
                  }`}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span className="font-medium text-ink">
                      {SERVICE_LABELS[key] ?? key}
                    </span>
                    <span className="text-sm text-ink-muted">
                      {service.status === "ok" ? "OK" : "Error"} · {service.latency_ms} ms
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm break-words text-ink-muted">
                    {service.detail}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-ink-muted">
            Project: {data.project ?? "not set"}
            {data.demo_mode ? " · Demo mode on" : ""}
          </p>
        </>
      )}
    </section>
  );
}
