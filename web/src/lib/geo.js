// Plot geometry helpers. Mirrors api/app/validation.py for quick feedback;
// the backend still validates everything.

const EARTH_RADIUS_M = 6378137;
export const MIN_AREA_HA = 0.05;
export const MAX_AREA_HA = 20;
export const MIN_DAYS_AGO = 7;
export const EARLIEST_EVENT = "2016-01-01";
const INDIA_BBOX = [68.0, 6.0, 98.0, 37.5];

const toRad = (deg) => (deg * Math.PI) / 180;

// Area of a [lng, lat] ring on a sphere, in square metres.
export function ringAreaM2(ring) {
  let total = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [lng1, lat1] = ring[i];
    const [lng2, lat2] = ring[i + 1];
    total += toRad(lng2 - lng1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)));
  }
  return (Math.abs(total) * EARTH_RADIUS_M ** 2) / 2;
}

export function polygonAreaHa(geometry) {
  if (!geometry?.coordinates?.[0]) return 0;
  return ringAreaM2(geometry.coordinates[0]) / 10000;
}

// Returns an error message, or null if the plot looks fine.
export function plotError(geometry) {
  if (!geometry) return "Draw your plot on the map first.";
  const ring = geometry.coordinates[0];
  const [minLng, minLat, maxLng, maxLat] = INDIA_BBOX;
  if (!ring.every(([lng, lat]) => lng >= minLng && lng <= maxLng && lat >= minLat && lat <= maxLat)) {
    return "The plot must be in India.";
  }
  const area = polygonAreaHa(geometry);
  if (area < MIN_AREA_HA) {
    return `The plot is too small (${area.toFixed(2)} ha). Draw at least ${MIN_AREA_HA} ha.`;
  }
  if (area > MAX_AREA_HA) {
    return `The plot is too large (${area.toFixed(1)} ha). Draw a single field of up to ${MAX_AREA_HA} ha.`;
  }
  return null;
}

// Latest allowed event date (YYYY-MM-DD), in the browser's time zone.
export function latestEventDate(now = new Date()) {
  const d = new Date(now);
  d.setDate(d.getDate() - MIN_DAYS_AGO);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function dateError(value, now = new Date()) {
  if (!value) return "Choose the date of the flood, drought or damage.";
  if (value < EARLIEST_EVENT) return "Satellite data for ClaimSat starts in 2016. Choose a later date.";
  if (value > latestEventDate(now)) {
    return `The date must be at least ${MIN_DAYS_AGO} days ago, so satellite images are available.`;
  }
  return null;
}
