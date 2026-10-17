"use client";

import { useMemo } from "react";
import { Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(LinearScale, LineElement, PointElement, Tooltip, Legend);

// Read a colour token from globals.css (canvas can't use CSS variables directly).
function token(name, fallback) {
  if (typeof window === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

const DEFAULT_LABELS = {
  thisYear: "This year",
  normal: "Normal (last 3 years)",
  x: "Days from the event",
  y: "Crop health (NDVI)",
};

export default function NdviChart({ series, labels = DEFAULT_LABELS }) {
  const { data, options } = useMemo(() => {
    const brand = token("--color-brand", "#1f6f43");
    const muted = token("--color-ink-muted", "#5c625e");
    const danger = token("--color-danger", "#b42318");
    const line = token("--color-line", "#e3e1da");

    return {
      data: {
        datasets: [
          {
            label: labels.thisYear,
            data: (series?.this_year ?? []).map((p) => ({ x: p.day_offset, y: p.ndvi, date: p.date })),
            borderColor: brand,
            backgroundColor: brand,
            borderWidth: 2.5,
            pointRadius: 3,
            tension: 0.25,
          },
          {
            label: labels.normal,
            data: (series?.baseline ?? []).map((p) => ({ x: p.day_offset, y: p.ndvi })),
            borderColor: muted,
            backgroundColor: muted,
            borderDash: [6, 4],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.25,
          },
          {
            label: "Event",
            data: [
              { x: 0, y: 0 },
              { x: 0, y: 1 },
            ],
            borderColor: danger,
            borderWidth: 1.5,
            borderDash: [3, 3],
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: "nearest", intersect: false },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: labels.x, color: muted },
            grid: { color: line },
            ticks: { color: muted },
          },
          y: {
            min: 0,
            max: 1,
            title: { display: true, text: labels.y, color: muted },
            grid: { color: line },
            ticks: { color: muted },
          },
        },
        plugins: {
          legend: {
            labels: { color: muted, boxWidth: 14, filter: (item) => item.text !== "Event" },
          },
          tooltip: {
            filter: (item) => item.dataset.label !== "Event",
            callbacks: {
              title: (items) => {
                const raw = items[0]?.raw;
                return raw?.date ?? `Day ${raw?.x}`;
              },
              label: (item) => `${item.dataset.label}: ${item.parsed.y.toFixed(2)}`,
            },
          },
        },
      },
    };
  }, [series, labels]);

  return (
    <div className="h-56 w-full print:h-48">
      <Line data={data} options={options} aria-label="Crop health over time compared with normal years" role="img" />
    </div>
  );
}
