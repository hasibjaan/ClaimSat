"use client";

import { useEffect, useState } from "react";

const COMMON_START = [
  "Finding a clear Sentinel-2 image from 1 week before",
  "Finding the latest clear image of your field",
];
const COMMON_END = [
  "Step 2: checking the weather record with AI",
  "Counting reports from farmers nearby",
  "Working out the case severity",
];
const STEPS = {
  flood: [...COMMON_START, "Comparing crop health and standing water", ...COMMON_END],
  drought: [...COMMON_START, "Comparing crop health", ...COMMON_END],
  other: [...COMMON_START, "Comparing crop health", ...COMMON_END],
};

const STEP_MS = 4000;

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
