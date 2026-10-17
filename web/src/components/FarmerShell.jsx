"use client";

import dynamic from "next/dynamic";

// The farmer app is browser-only: it needs `window` (Leaflet) and today's date.
const FarmerApp = dynamic(() => import("@/components/FarmerApp"), {
  ssr: false,
  loading: () => <div className="flex h-[calc(100dvh-2.75rem)] items-center justify-center text-ink-muted">Loading map…</div>,
});

export default function FarmerShell() {
  return <FarmerApp />;
}
