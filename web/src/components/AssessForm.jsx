"use client";

import { useState } from "react";
import { dateError, latestEventDate, EARLIEST_EVENT } from "@/lib/geo";
import { EVENT_LABELS } from "@/lib/format";

const CROPS = ["Paddy", "Sugarcane", "Maize", "Cotton", "Groundnut", "Ragi", "Jowar", "Tur dal", "Other"];

const inputClass =
  "mt-1 block min-h-11 w-full rounded-lg border border-line bg-surface px-3 text-base text-ink focus:border-brand focus:ring-2 focus:ring-brand/30 focus:outline-none";
const labelClass = "block text-sm font-medium text-ink";

// What happened to the selected (registered) plot. The plot outline itself
// can't be changed here.
export default function AssessForm({ values, onValuesChange, onSubmit, serverError }) {
  const [submitted, setSubmitted] = useState(false);

  const set = (field) => (e) => onValuesChange({ ...values, [field]: e.target.value });
  const errors = { date: dateError(values.event_date) };
  const hasErrors = Object.values(errors).some(Boolean);

  const submit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    if (!hasErrors) onSubmit();
  };

  const show = (key) => submitted && errors[key];

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <fieldset>
        <legend className={labelClass}>What happened?</legend>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {Object.entries(EVENT_LABELS).map(([value, label]) => (
            <label
              key={value}
              className={`flex min-h-11 cursor-pointer items-center justify-center rounded-lg border px-2 text-center text-sm font-medium ${
                values.event_type === value
                  ? "border-brand bg-brand-soft text-brand-strong"
                  : "border-line bg-surface text-ink hover:bg-surface-muted"
              }`}
            >
              <input
                type="radio"
                name="event_type"
                value={value}
                checked={values.event_type === value}
                onChange={set("event_type")}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="event_date" className={labelClass}>
          {values.event_type === "drought" ? "Date in the dry season" : "Date it happened"}
        </label>
        <input
          id="event_date"
          type="date"
          min={EARLIEST_EVENT}
          max={latestEventDate()}
          value={values.event_date}
          onChange={set("event_date")}
          className={inputClass}
        />
        {show("date") && <p className="mt-1 text-sm text-danger">{errors.date}</p>}
      </div>

      <p className="text-xs text-ink-muted">
        We compare a satellite image from about 1 week before this date with the latest image of your field.
      </p>

      <div>
        <label htmlFor="crop" className={labelClass}>Crop this season</label>
        <select id="crop" value={values.crop} onChange={set("crop")} className={inputClass}>
          <option value="">Select a crop</option>
          {CROPS.map((crop) => (
            <option key={crop} value={crop.toLowerCase()}>
              {crop}
            </option>
          ))}
        </select>
      </div>

      {serverError && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {serverError}
        </p>
      )}

      <button
        type="submit"
        className="min-h-12 w-full rounded-lg bg-brand px-4 text-base font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
      >
        Check my field
      </button>
    </form>
  );
}
