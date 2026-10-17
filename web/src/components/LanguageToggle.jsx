"use client";

const OPTIONS = [
  { value: "en", label: "English" },
  { value: "kn", label: "ಕನ್ನಡ", className: "font-kannada" },
];

export default function LanguageToggle({ value, onChange }) {
  return (
    <div role="radiogroup" aria-label="Report language" className="inline-flex rounded-lg border border-line bg-surface p-1">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
          className={`min-h-9 rounded-md px-3 text-sm font-medium ${option.className ?? ""} ${
            value === option.value ? "bg-brand text-white" : "text-ink hover:bg-surface-muted"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
