import Link from "next/link";

// Damage levels for the decorative "village" grid: a flooded band along a river.
const LEVELS = ["severe", "moderate", "low", "none"];
const GRID = Array.from({ length: 36 }, (_, i) => {
  const row = Math.floor(i / 6);
  const col = i % 6;
  return LEVELS[Math.min(Math.abs(row - col), 3)];
});
const LEVEL_CLASS = {
  severe: "bg-level-severe",
  moderate: "bg-level-moderate",
  low: "bg-level-low",
  none: "bg-level-none",
};

const STEPS = [
  {
    who: "Agriculture officer",
    title: "Registers the plot",
    text: "Outlines each farmer’s land from the land records, by survey number. Overlapping or repeated plots are refused.",
  },
  {
    who: "Farmer",
    title: "Checks the field",
    text: "After a flood or drought, enters their Farmer ID, picks their plot and the date. No drawing, no paperwork.",
  },
  {
    who: "Satellites + Gemini",
    title: "Evidence in their language",
    text: "Radar, crop health and rainfall are compared with normal years. A report in English and ಕನ್ನಡ is ready to attach to the claim.",
  },
];

const TRUST = [
  ["Plots come from land records", "Farmers can’t draw or enlarge their land; officers register it."],
  ["Gemini writes words, not numbers", "Every percentage in a report is checked against the measurements."],
  ["Evidence fingerprint", "A code on each report shows if any number was changed later."],
];

export default function Home() {
  return (
    <main className="flex-1">
      <section className="bg-brand-strong text-white">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 py-14 md:grid-cols-[1.3fr_1fr] md:py-24">
          <div>
            <p className="text-sm font-semibold tracking-widest text-white/80 uppercase">Crop insurance · Karnataka</p>
            <h1 className="mt-3 text-4xl leading-tight font-semibold md:text-6xl">Satellite evidence for crop insurance claims</h1>
            <p className="mt-3 font-kannada text-xl text-white/90 md:text-2xl">ನಿಮ್ಮ ಬೆಳೆ ವಿಮೆ ಕ್ಲೇಮ್‌ಗೆ ಉಪಗ್ರಹ ಸಾಕ್ಷ್ಯ</p>
            <p className="mt-5 max-w-xl text-lg text-white/85">
              When floods or drought destroy a crop, the evidence often disappears before an assessor arrives. ClaimSat
              measures the damage from space and gives the farmer a report to attach to their claim.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/farmer"
                className="flex min-h-14 items-center justify-center rounded-xl bg-surface px-6 text-lg font-semibold text-brand-strong shadow-sm hover:bg-brand-soft"
              >
                I’m a farmer: check my field
              </Link>
              <Link
                href="/officer"
                className="flex min-h-14 items-center justify-center rounded-xl border-2 border-white/70 px-6 text-lg font-semibold text-white hover:bg-white/10"
              >
                I’m an agriculture officer
              </Link>
            </div>
          </div>

          <figure className="mx-auto w-full max-w-sm">
            <div className="grid grid-cols-6 gap-2 rounded-2xl bg-white/10 p-4" aria-hidden="true">
              {GRID.map((level, i) => (
                <span key={i} className={`aspect-square rounded-md ${LEVEL_CLASS[level]}`} />
              ))}
            </div>
            <figcaption className="mt-3 text-center text-sm text-white/80">
              Every square is a field, coloured by damage measured from satellites.
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-semibold text-ink md:text-3xl">How it works</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-2xl border border-line bg-surface p-6">
              <p className="text-sm font-semibold text-brand">
                {i + 1} · {step.who}
              </p>
              <h3 className="mt-1 text-xl font-semibold text-ink">{step.title}</h3>
              <p className="mt-2 text-ink-muted">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto grid w-full max-w-6xl gap-4 px-4 pb-14 md:grid-cols-2">
        <div className="flex flex-col rounded-2xl border border-line bg-surface p-6">
          <h2 className="text-xl font-semibold text-ink">For farmers</h2>
          <ul className="mt-3 flex-1 list-disc space-y-1 pl-5 text-ink-muted">
            <li>Use the Farmer ID from your registration slip</li>
            <li>See your damage score and why</li>
            <li>Get a report in English or ಕನ್ನಡ, ready to print</li>
            <li>Add a photo of the field as extra evidence</li>
          </ul>
          <Link href="/farmer" className="mt-5 flex min-h-12 items-center justify-center rounded-lg bg-brand font-semibold text-white hover:bg-brand-strong">
            Open the farmer dashboard
          </Link>
        </div>
        <div className="flex flex-col rounded-2xl border border-line bg-surface p-6">
          <h2 className="text-xl font-semibold text-ink">For agriculture officers</h2>
          <ul className="mt-3 flex-1 list-disc space-y-1 pl-5 text-ink-muted">
            <li>Register plots from the land records</li>
            <li>See damage across the whole village on one map</li>
            <li>Visit the worst-hit fields first</li>
            <li>Export to Looker Studio for insurers</li>
          </ul>
          <Link href="/officer" className="mt-5 flex min-h-12 items-center justify-center rounded-lg border-2 border-brand font-semibold text-brand hover:bg-brand-soft">
            Open the officer dashboard
          </Link>
        </div>
      </section>

      <section className="border-t border-line bg-surface">
        <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-10 md:grid-cols-3">
          {TRUST.map(([title, text]) => (
            <div key={title}>
              <h3 className="font-semibold text-ink">{title}</h3>
              <p className="mt-1 text-sm text-ink-muted">{text}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
