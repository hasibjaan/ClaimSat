import HealthStatus from "@/components/HealthStatus";

export const metadata = { title: "System status · ClaimSat" };

// Checks that the web app can reach the API and the API can reach Google Cloud.
export default function StatusPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-10">
      <p className="text-sm font-semibold tracking-wide text-brand uppercase">ClaimSat</p>
      <h1 className="mt-2 text-3xl font-semibold text-ink">System status</h1>
      <p className="mt-3 text-ink-muted">Each Google Cloud service the app depends on.</p>
      <HealthStatus />
    </main>
  );
}
