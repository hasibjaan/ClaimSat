export const HA_TO_ACRES = 2.47105;

const twoDp = (n) => n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatArea(ha) {
  if (ha == null) return "—";
  return `${twoDp(ha)} ha · ${twoDp(ha * HA_TO_ACRES)} acres`;
}

export function pct(value) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

export function formatDate(iso, locale = "en-IN") {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateList(dates, locale = "en-IN", none = "none") {
  return dates?.length ? dates.map((d) => formatDate(d, locale)).join(", ") : none;
}

export const EVENT_LABELS = { flood: "Flood", drought: "Drought", other: "Other damage" };

export const LEVEL_LABELS = {
  none: "No clear damage",
  low: "Low damage",
  moderate: "Moderate damage",
  severe: "Severe damage",
  unknown: "Not enough data",
};
