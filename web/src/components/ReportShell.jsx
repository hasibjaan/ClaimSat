"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";

// Browser-only, like the map app: the report fetches data and draws a canvas chart.
const ReportView = dynamic(() => import("@/components/ReportView"), {
  ssr: false,
  loading: () => <div className="p-10 text-center text-ink-muted">Loading report…</div>,
});

export default function ReportShell() {
  const { id } = useParams();
  return <ReportView id={id} />;
}
