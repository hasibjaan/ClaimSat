// Mock data for NEXT_PUBLIC_MOCK_API=1. Values come from shared/sample_result.json
// (copied to ./sampleResult.json) and are illustrative, not real measurements.

import sampleResult from "./sampleResult.json";
import { polygonAreaHa } from "./geo";

const MOCK_IMAGES = {
  true_colour_before: "/mock/true_colour_before.svg",
  true_colour_after: "/mock/true_colour_after.svg",
  ndvi_after: "/mock/ndvi_after.svg",
  flood_mask: "/mock/flood_mask.svg",
};

// Mirrors api/app/seed_plots.json: plots an officer has registered.
const mockRegistry = [
  {
    plot_id: "plt_seed_1",
    farmer_id: "KA-DEMO-001",
    farmer_name: "Ramesh",
    village: "Athani taluk",
    survey_number: "112/3",
    crop: "sugarcane",
    geometry: sampleResult.plot.geometry,
    default_event: { event_type: "flood", event_date: sampleResult.event.date },
    source: "seed",
  },
  {
    plot_id: "plt_seed_2",
    farmer_id: "KA-DEMO-001",
    farmer_name: "Ramesh",
    village: "Athani taluk",
    survey_number: "118/1",
    crop: "maize",
    geometry: {
      type: "Polygon",
      coordinates: [[[75.0625, 16.7315], [75.0637, 16.7315], [75.0637, 16.7324], [75.0625, 16.7324], [75.0625, 16.7315]]],
    },
    default_event: { event_type: "flood", event_date: sampleResult.event.date },
    source: "seed",
  },
].map((p) => ({ ...p, area_ha: Number(polygonAreaHa(p.geometry).toFixed(2)) }));

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

export function mockResult(body) {
  const plot = mockRegistry.find((p) => p.plot_id === body.plot_id) ?? mockRegistry[0];
  return {
    ...sampleResult,
    assessment_id: `asm_mock${Date.now().toString(36)}`,
    source: "sample",
    created_at: new Date().toISOString(),
    plot: {
      ...sampleResult.plot,
      plot_id: plot.plot_id,
      farmer_id: plot.farmer_id,
      survey_number: plot.survey_number,
      farmer_name: plot.farmer_name,
      village: plot.village,
      crop: body.crop || plot.crop,
      geometry: plot.geometry,
      area_ha: plot.area_ha,
    },
    images: MOCK_IMAGES,
  };
}

// Sample report text matching the sample measurements (what Gemini would write).
export const MOCK_REPORT = {
  generated_at: "2026-10-17T10:31:00Z",
  model: "sample (mock mode)",
  summary_en:
    "Satellite images show severe damage to this sugarcane field after the flood on 7 August 2019. Radar images found that 83% of the field was under water, and crop health afterwards was 65% below what is normal for these weeks. The damage score is 74 out of 100, with high confidence. This report is supporting evidence for your insurance claim, not an official loss assessment.",
  summary_kn:
    "2019ರ ಆಗಸ್ಟ್ 7ರ ಪ್ರವಾಹದ ನಂತರ ಈ ಕಬ್ಬಿನ ಹೊಲಕ್ಕೆ ತೀವ್ರ ಹಾನಿಯಾಗಿರುವುದನ್ನು ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ತೋರಿಸುತ್ತವೆ. ರಾಡಾರ್ ಚಿತ್ರಗಳ ಪ್ರಕಾರ ಹೊಲದ 83% ಭಾಗ ನೀರಿನಲ್ಲಿ ಮುಳುಗಿತ್ತು. ಪ್ರವಾಹದ ನಂತರ ಬೆಳೆಯ ಆರೋಗ್ಯ ಈ ವಾರಗಳಲ್ಲಿ ಸಾಮಾನ್ಯವಾಗಿ ಇರುವುದಕ್ಕಿಂತ 65% ಕಡಿಮೆಯಾಗಿದೆ. ಹಾನಿ ಅಂಕ 100ರಲ್ಲಿ 74, ವಿಶ್ವಾಸಾರ್ಹತೆ ಹೆಚ್ಚು. ಈ ವರದಿ ನಿಮ್ಮ ವಿಮೆ ಕ್ಲೇಮ್‌ಗೆ ಪೂರಕ ಸಾಕ್ಷ್ಯ ಮಾತ್ರ, ಅಧಿಕೃತ ನಷ್ಟ ಮೌಲ್ಯಮಾಪನವಲ್ಲ.",
  findings: [
    {
      title_en: "Most of the field was flooded",
      title_kn: "ಹೊಲದ ಹೆಚ್ಚಿನ ಭಾಗ ಜಲಾವೃತವಾಗಿತ್ತು",
      detail_en:
        "Radar satellites, which see through clouds, show standing water on 83% of the field in the days after 7 August 2019.",
      detail_kn:
        "ಮೋಡಗಳ ಮೂಲಕವೂ ನೋಡಬಲ್ಲ ರಾಡಾರ್ ಉಪಗ್ರಹಗಳು, 2019ರ ಆಗಸ್ಟ್ 7ರ ನಂತರದ ದಿನಗಳಲ್ಲಿ ಹೊಲದ 83% ಭಾಗದಲ್ಲಿ ನೀರು ನಿಂತಿರುವುದನ್ನು ತೋರಿಸುತ್ತವೆ.",
    },
    {
      title_en: "Crop health fell sharply",
      title_kn: "ಬೆಳೆಯ ಆರೋಗ್ಯ ತೀವ್ರವಾಗಿ ಕುಸಿದಿದೆ",
      detail_en:
        "After the flood, crop health measured from satellite images was 65% below the normal level for the same weeks in 2016–2018.",
      detail_kn:
        "ಪ್ರವಾಹದ ನಂತರ, ಉಪಗ್ರಹ ಚಿತ್ರಗಳಿಂದ ಅಳೆದ ಬೆಳೆಯ ಆರೋಗ್ಯ 2016–2018ರ ಇದೇ ವಾರಗಳ ಸಾಮಾನ್ಯ ಮಟ್ಟಕ್ಕಿಂತ 65% ಕಡಿಮೆ ಇತ್ತು.",
    },
    {
      title_en: "The crop was healthy before the flood",
      title_kn: "ಪ್ರವಾಹಕ್ಕೂ ಮೊದಲು ಬೆಳೆ ಆರೋಗ್ಯವಾಗಿತ್ತು",
      detail_en:
        "In the month before the flood, crop health was at or above normal, so the drop matches the flood rather than a normal harvest.",
      detail_kn:
        "ಪ್ರವಾಹಕ್ಕೂ ಹಿಂದಿನ ತಿಂಗಳಲ್ಲಿ ಬೆಳೆಯ ಆರೋಗ್ಯ ಸಾಮಾನ್ಯ ಮಟ್ಟದಲ್ಲಿ ಅಥವಾ ಅದಕ್ಕಿಂತ ಹೆಚ್ಚಾಗಿತ್ತು. ಆದ್ದರಿಂದ ಈ ಕುಸಿತ ಸಾಮಾನ್ಯ ಕಟಾವಿನಿಂದಲ್ಲ, ಪ್ರವಾಹದಿಂದ ಆಗಿದೆ.",
    },
  ],
  confidence_reasons_kn: [
    "ಘಟನೆಯ ಮೊದಲು ಮತ್ತು ನಂತರ 3 ಅಥವಾ ಹೆಚ್ಚು ಮೋಡರಹಿತ Sentinel-2 ಚಿತ್ರಗಳು ಲಭ್ಯವಿವೆ",
    "ಘಟನೆಯ ಮೊದಲು ಮತ್ತು ನಂತರ ರಾಡಾರ್ ಚಿತ್ರಗಳು ಲಭ್ಯವಿವೆ",
    "ಜಮೀನಿನ ಹೆಚ್ಚಿನ ಭಾಗ ಕೃಷಿ ಭೂಮಿ (78%)",
    "ಜಮೀನು 102 ಉಪಗ್ರಹ ಪಿಕ್ಸೆಲ್‌ಗಳನ್ನು ಒಳಗೊಂಡಿದೆ",
  ],
  limitations_en:
    "Clouds can hide parts of the field in optical images; radar was used to measure the flood. Each satellite pixel is 10 metres wide, so the edges of the field are less precise. The crop type is as reported by the user and was not checked from space.",
  limitations_kn:
    "ಮೋಡಗಳು ಕೆಲವೊಮ್ಮೆ ಹೊಲದ ಭಾಗಗಳನ್ನು ಮರೆಮಾಡಬಹುದು; ಪ್ರವಾಹವನ್ನು ಅಳೆಯಲು ರಾಡಾರ್ ಬಳಸಲಾಗಿದೆ. ಪ್ರತಿ ಉಪಗ್ರಹ ಪಿಕ್ಸೆಲ್ 10 ಮೀಟರ್ ಅಗಲವಿರುವುದರಿಂದ ಹೊಲದ ಅಂಚುಗಳ ಅಳತೆ ಕಡಿಮೆ ನಿಖರವಾಗಿರುತ್ತದೆ. ಬೆಳೆಯ ಪ್ರಕಾರವನ್ನು ಬಳಕೆದಾರರು ತಿಳಿಸಿದಂತೆ ಬರೆಯಲಾಗಿದೆ; ಅದನ್ನು ಉಪಗ್ರಹದಿಂದ ಪರಿಶೀಲಿಸಿಲ್ಲ.",
  recommended_next_steps_en:
    "Report the crop loss to your insurance company, bank or agriculture office within 72 hours of the event, as PMFBY requires, or as soon as possible if that time has passed. Attach this report and ask for a field inspection.",
  recommended_next_steps_kn:
    "PMFBY ನಿಯಮದಂತೆ ಘಟನೆ ನಡೆದ 72 ಗಂಟೆಗಳೊಳಗೆ ನಿಮ್ಮ ವಿಮಾ ಕಂಪನಿ, ಬ್ಯಾಂಕ್ ಅಥವಾ ಕೃಷಿ ಕಚೇರಿಗೆ ಬೆಳೆ ನಷ್ಟವನ್ನು ತಿಳಿಸಿ. ಆ ಸಮಯ ಕಳೆದಿದ್ದರೆ ಸಾಧ್ಯವಾದಷ್ಟು ಬೇಗ ತಿಳಿಸಿ. ಈ ವರದಿಯನ್ನು ಲಗತ್ತಿಸಿ ಮತ್ತು ಹೊಲ ಪರಿಶೀಲನೆಗೆ ಮನವಿ ಮಾಡಿ.",
  number_check: { ok: true, unexpected_percentages: [] },
};

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
        rain_deficit: null,
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
