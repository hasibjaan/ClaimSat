"use client";

import dynamic from "next/dynamic";

// Officer pages are browser-only: the access code lives in sessionStorage.
const OfficerArea = dynamic(() => import("@/components/OfficerArea"), {
  ssr: false,
  loading: () => <p className="p-10 text-center text-ink-muted">Loading…</p>,
});

export default function OfficerShell({ view }) {
  return <OfficerArea view={view} />;
}
