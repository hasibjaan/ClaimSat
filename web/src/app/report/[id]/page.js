import { Suspense } from "react";
import ReportShell from "@/components/ReportShell";

export const metadata = { title: "Evidence report · ClaimSat" };

// ReportShell reads the id from the URL, which Next.js requires inside <Suspense>.
export default function ReportPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-ink-muted">Loading report…</div>}>
      <ReportShell />
    </Suspense>
  );
}
