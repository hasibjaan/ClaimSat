import sampleResult from "./sampleResult.json";
import sampleResults from "./sampleResults.json";
import { polygonAreaHa } from "./geo";

// Mock data for NEXT_PUBLIC_MOCK_API=1. The three demo plots and their results
// come from ./sampleResults.json, built by api/scripts/build_samples.py with the
// real scoring code (the backend serves the same samples in DEMO_MODE):
//   112/3 verified + severe, 118/1 single report (moderate), 124/2 not supported.

const mockRegistry = sampleResults.plots.map((p) => ({ ...p }));
// Results of plots an officer registered in this session (mock only).
const extraResults = {};

export function mockPlots() {
  return mockRegistry;
}

export function mockFarmerPlots(farmerId) {
  return mockRegistry.filter((p) => p.farmer_id === String(farmerId).trim().toUpperCase());
}

export function mockRegister(body) {
  const plot = {
    ...body,
    plot_id: `plt_mock${Date.now().toString(36)}`,
    farmer_id: String(body.farmer_id).trim().toUpperCase(),
    area_ha: Number(polygonAreaHa(body.geometry).toFixed(2)),
    source: "officer",
    default_event: null,
  };
  mockRegistry.push(plot);
  return plot;
}

const clone = (value) => JSON.parse(JSON.stringify(value));

// The sample result for a demo plot; a newly registered plot borrows the
// first sample's numbers on its own outline (clearly labelled sample data).
export function mockResult(body) {
  const sample = sampleResults.results[body.plot_id];
  if (sample) {
    const result = clone(sample);
    if (body.crop) result.plot.crop = body.crop;
    return result;
  }
  const plot = mockRegistry.find((p) => p.plot_id === body.plot_id) ?? mockRegistry[0];
  const result = clone(sampleResults.results.plt_seed_1);
  result.assessment_id = `asm_mock${Date.now().toString(36)}`;
  result.plot = { ...result.plot, ...plot, crop: body.crop || plot.crop, geometry: plot.geometry, area_ha: plot.area_ha };
  extraResults[result.assessment_id] = result;
  return result;
}

export function mockAssessment(id) {
  const found = Object.values(sampleResults.results).find((r) => r.assessment_id === id) ?? extraResults[id];
  return clone(found ?? { ...sampleResults.results.plt_seed_1, assessment_id: id });
}

// --- Dashboard mock: a village grid with a flooded band along a "river" line ---

const LEVEL_THRESHOLDS = [
  [15, "none"],
  [35, "low"],
  [60, "moderate"],
];
const levelFor = (score) => LEVEL_THRESHOLDS.find(([t]) => score < t)?.[1] ?? "severe";
const CONFIDENCE_RANK = { high: 0, medium: 1, low: 2 };

// Same logic as api/app/warehouse.py summarise().
export function summarise(plots) {
  const affected = plots.filter((p) => ["moderate", "severe"].includes(p.damage_level));
  const visitFirst = plots
    .filter((p) => p.damage_score != null)
    .sort((a, b) => b.damage_score - a.damage_score || CONFIDENCE_RANK[a.confidence] - CONFIDENCE_RANK[b.confidence]);
  return {
    summary: {
      plots: plots.length,
      severe: plots.filter((p) => p.damage_level === "severe").length,
      moderate: plots.filter((p) => p.damage_level === "moderate").length,
      low_or_none: plots.filter((p) => ["low", "none"].includes(p.damage_level)).length,
      unknown: plots.filter((p) => p.damage_level === "unknown").length,
      hectares_affected: Number(affected.reduce((sum, p) => sum + (p.area_ha ?? 0), 0).toFixed(2)),
    },
    visit_first: visitFirst.slice(0, 15).map((p) => p.assessment_id),
  };
}

export function mockDashboard() {
  const [cLng, cLat] = [sampleResult.plot.centroid.lng, sampleResult.plot.centroid.lat];
  const latStep = 150 / 111320;
  const lngStep = 150 / (111320 * Math.cos((cLat * Math.PI) / 180));
  const half = 50 / 111320;
  let seed = 7;
  const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

  const plots = [];
  for (let i = -6; i <= 6; i++) {
    for (let j = -6; j <= 6; j++) {
      if (random() < 0.3) continue; // not every cell is cropland
      const lng = cLng + i * lngStep;
      const lat = cLat + j * latStep;
      const riverDistance = Math.abs(i * 0.8 - j + 1.5); // a diagonal river line
      const flood = Math.max(0, Math.min(1, 1 - riverDistance / 4 + (random() - 0.5) * 0.3));
      const loss = Math.max(0, Math.min(1, flood * 0.8 + (random() - 0.5) * 0.2));
      const score = Math.round(100 * (0.5 * flood + 0.5 * loss));
      const hl = half / Math.cos((lat * Math.PI) / 180);
      plots.push({
        assessment_id: `asm_mock${String(plots.length).padStart(3, "0")}`,
        plot_id: `plt_mock${plots.length}`,
        farmer_name: null,
        village: "Sample village",
        crop: null,
        area_ha: 1.0,
        event_type: "flood",
        event_date: sampleResult.event.date,
        damage_score: score,
        damage_level: levelFor(score),
        confidence: random() < 0.8 ? "high" : "medium",
        ndvi_loss: Number(loss.toFixed(3)),
        flood_fraction: Number(flood.toFixed(3)),
        source: "batch",
        assessed_at: new Date().toISOString(),
        geometry: {
          type: "Polygon",
          coordinates: [[[lng - hl, lat - half], [lng + hl, lat - half], [lng + hl, lat + half], [lng - hl, lat + half], [lng - hl, lat - half]]],
        },
      });
    }
  }
  return { source: "sample", plots, ...summarise(plots) };
}
