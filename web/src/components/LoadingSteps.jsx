"use client";

import { useEffect, useState } from "react";

const STEPS = {
  flood: [
    "Finding Sentinel-2 images of your field",
    "Fetching radar images (they see through clouds)",
    "Mapping water on your field after the flood",
    "Comparing with the same weeks in the last 3 years",
    "Scoring the damage",
  ],
  drought: [
    "Finding Sentinel-2 images of your field",
    "Measuring crop health through the season",
    "Adding up rainfall against the 20-year normal",
    "Comparing with the same season in the last 3 years",
    "Scoring the damage",
  ],
  other: [
    "Finding Sentinel-2 images of your field",
    "Measuring crop health before and after",
    "Comparing with the same weeks in the last 3 years",
    "Scoring the damage",
  ],
};

const STEP_MS = 5000;

export default function LoadingSteps({ eventType }) {
  const steps = STEPS[eventType] ?? STEPS.other;
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => Math.min(i + 1, steps.length - 1));
    }, STEP_MS);
    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <div aria-live="polite">
      <h2 className="text-lg font-semibold text-ink">Checking your field…</h2>
      <p className="mt-1 text-sm text-ink-muted">This usually takes 20 to 30 seconds.</p>
      <ol className="mt-5 space-y-3">
        {steps.map((step, i) => (
          <li key={step} className="flex items-center gap-3 text-sm">
            <span
              className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                i < index
                  ? "bg-brand text-white"
                  : i === index
                    ? "animate-pulse bg-brand-soft text-brand-strong ring-2 ring-brand"
                    : "bg-surface-muted text-ink-muted"
              }`}
            >
              {i < index ? "✓" : i + 1}
            </span>
            <span className={i <= index ? "text-ink" : "text-ink-muted"}>{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
