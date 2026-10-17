"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import { checkOfficerCode, isMock } from "@/lib/api";
import { clearOfficerCode, getOfficerCode, setOfficerCode } from "@/lib/officer";

const DashboardView = dynamic(() => import("@/components/DashboardView"), {
  ssr: false,
  loading: () => <p className="p-10 text-center text-ink-muted">Loading dashboard…</p>,
});
const RegisterPlotView = dynamic(() => import("@/components/RegisterPlotView"), {
  ssr: false,
  loading: () => <p className="p-10 text-center text-ink-muted">Loading map…</p>,
});

const NAV = [
  { view: "home", href: "/officer", label: "Home" },
  { view: "dashboard", href: "/officer/dashboard", label: "Village dashboard" },
  { view: "register", href: "/officer/register", label: "Register a plot" },
];

function CodeGate({ onAuthed }) {
  const [code, setCode] = useState("");
  const [state, setState] = useState({ busy: false, error: null });

  const submit = async (e) => {
    e.preventDefault();
    if (!code.trim()) return setState({ busy: false, error: "Enter the officer access code." });
    setState({ busy: true, error: null });
    try {
      await checkOfficerCode(code.trim());
      setOfficerCode(code.trim());
      onAuthed();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };

  return (
    <main className="mx-auto w-full max-w-md px-4 py-16">
      <form onSubmit={submit} noValidate className="space-y-4 rounded-2xl border border-line bg-surface p-6">
        <p className="text-sm font-semibold text-ink">
          Claim<span className="text-brand">Sat</span> · Agriculture officers
        </p>
        <h1 className="text-2xl font-semibold text-ink">Officer sign-in</h1>
        <p className="text-sm text-ink-muted">Officers register farmers’ plots and see damage across villages.</p>
        <div>
          <label htmlFor="officer_code" className="block text-sm font-medium text-ink">
            Access code
          </label>
          <input
            id="officer_code"
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoComplete="current-password"
            className="mt-1 block min-h-12 w-full rounded-lg border border-line bg-surface px-3 text-base text-ink focus:border-brand focus:ring-2 focus:ring-brand/30 focus:outline-none"
          />
          {isMock && <p className="mt-1 text-xs text-warn">Mock mode: any code works.</p>}
        </div>
        {state.error && (
          <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
            {state.error}
          </p>
        )}
        <button
          type="submit"
          disabled={state.busy}
          className="min-h-12 w-full rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
        >
          {state.busy ? "Checking…" : "Sign in"}
        </button>
        <Link href="/" className="block text-center text-sm text-brand hover:underline">
          ← Back to ClaimSat home
        </Link>
      </form>
    </main>
  );
}

function OfficerHome() {
  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-semibold text-ink">Agriculture officer</h1>
        <p className="mt-2 text-ink-muted">Register farmers’ plots from the land records, then follow damage across your villages.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Link href="/officer/dashboard" className="group rounded-2xl border border-line bg-surface p-6 hover:border-brand">
          <p className="text-xs font-semibold tracking-wide text-brand uppercase">Monitor</p>
          <h2 className="mt-1 text-xl font-semibold text-ink">Village dashboard →</h2>
          <p className="mt-2 text-sm text-ink-muted">Damage on every assessed plot, and which fields to visit first.</p>
        </Link>
        <Link href="/officer/register" className="group rounded-2xl border border-line bg-surface p-6 hover:border-brand">
          <p className="text-xs font-semibold tracking-wide text-brand uppercase">Register</p>
          <h2 className="mt-1 text-xl font-semibold text-ink">Register a plot →</h2>
          <p className="mt-2 text-sm text-ink-muted">
            Outline a farmer’s plot from the land records. Overlapping or duplicate survey numbers are refused.
          </p>
        </Link>
      </div>
    </main>
  );
}

// Officer pages: sign-in with the access code, then a small nav bar and the chosen view.
export default function OfficerArea({ view }) {
  const [authed, setAuthed] = useState(() => Boolean(getOfficerCode()));

  const signOut = () => {
    clearOfficerCode();
    setAuthed(false);
  };

  if (!authed) return <CodeGate onAuthed={() => setAuthed(true)} />;

  return (
    <div className="flex flex-1 flex-col">
      <nav className="flex h-14 shrink-0 items-center gap-1 overflow-x-auto border-b border-line bg-surface px-4">
        <Link href="/" className="mr-3 font-semibold whitespace-nowrap text-ink">
          Claim<span className="text-brand">Sat</span>
        </Link>
        {NAV.map((item) => (
          <Link
            key={item.view}
            href={item.href}
            className={`flex min-h-11 items-center rounded-lg px-3 text-sm font-medium whitespace-nowrap ${
              item.view === view ? "bg-brand-soft text-brand-strong" : "text-ink hover:bg-surface-muted"
            }`}
          >
            {item.label}
          </Link>
        ))}
        <button type="button" onClick={signOut} className="ml-auto min-h-11 px-3 text-sm whitespace-nowrap text-ink-muted hover:text-ink">
          Sign out
        </button>
      </nav>
      {view === "home" && <OfficerHome />}
      {view === "dashboard" && <DashboardView onUnauthorized={signOut} />}
      {view === "register" && <RegisterPlotView onUnauthorized={signOut} />}
    </div>
  );
}
