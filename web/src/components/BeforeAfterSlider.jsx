"use client";

import { useState } from "react";

// Drag the handle to compare the "before" and "after" satellite images.
export default function BeforeAfterSlider({ before, after, beforeLabel, afterLabel }) {
  const [position, setPosition] = useState(50);

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-surface-muted select-none">
      {/* eslint-disable-next-line @next/next/no-img-element -- satellite PNGs served by our API */}
      <img src={after} alt={afterLabel} className="absolute inset-0 h-full w-full object-cover" draggable={false} />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={before}
        alt={beforeLabel}
        className="absolute inset-0 h-full w-full object-cover"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
        draggable={false}
      />
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow" style={{ left: `${position}%` }}>
        <div className="absolute top-1/2 left-1/2 flex size-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-sm text-ink shadow-md">
          ↔
        </div>
      </div>
      <span className="absolute top-2 left-2 rounded bg-ink/75 px-2 py-1 text-xs font-medium text-white">{beforeLabel}</span>
      <span className="absolute top-2 right-2 rounded bg-ink/75 px-2 py-1 text-xs font-medium text-white">{afterLabel}</span>
      <input
        type="range"
        min="0"
        max="100"
        value={position}
        onChange={(e) => setPosition(Number(e.target.value))}
        aria-label="Compare before and after"
        className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
      />
    </div>
  );
}
