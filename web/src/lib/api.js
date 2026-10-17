// All browser calls to the backend go through the Next.js /api proxy.
// Set NEXT_PUBLIC_MOCK_API=1 to use the sample result instead (for building
// the UI before the backend has Google Cloud access).

import sampleResult from "./sampleResult.json";
import { mockAssessment, mockDashboard, mockFarmerPlots, mockPlots, mockRegister, mockResult } from "./mockData";
import { getOfficerCode } from "./officer";

const MOCK = process.env.NEXT_PUBLIC_MOCK_API === "1";

async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, { cache: "no-store", ...options });
  let body = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON response; handled below.
  }
  if (!response.ok) {
    const message = body?.error || body?.detail || `Request failed (${response.status})`;
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = response.status; // 401 on officer pages = ask for the code again
    throw error;
  }
  return body;
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const isMock = MOCK;

export function getHealth() {
  return request("/health");
}

export async function assess(body) {
  if (MOCK) {
    await wait(6000);
    return mockResult(body);
  }
  return request("/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// --- Farmers: only plots an officer registered to their Farmer ID ---

export async function getFarmerPlots(farmerId) {
  if (MOCK) {
    await wait(500);
    const plots = mockFarmerPlots(farmerId);
    if (!plots.length) {
      throw new Error("No land is registered to this Farmer ID yet. Ask your agriculture office to register your plot.");
    }
    return { plots };
  }
  return request(`/farmers/${encodeURIComponent(farmerId.trim())}/plots`);
}

// --- Officers: every call carries the access code from this browser session ---

function officerHeaders(code = getOfficerCode()) {
  return { "X-Officer-Code": code ?? "" };
}

export async function checkOfficerCode(code) {
  if (MOCK) {
    await wait(300);
    return { ok: true };
  }
  return request("/officer/check", { headers: officerHeaders(code) });
}

export async function listPlots() {
  if (MOCK) return { plots: mockPlots() };
  return request("/plots", { headers: officerHeaders() });
}

export async function registerPlot(body) {
  if (MOCK) {
    await wait(800);
    return { plot: mockRegister(body) };
  }
  return request("/plots", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...officerHeaders() },
    body: JSON.stringify(body),
  });
}

export async function getAssessment(id) {
  if (MOCK) return mockAssessment(id);
  return request(`/assessments/${encodeURIComponent(id)}`);
}

// Ask Gemini to write the report (the backend reuses an existing one unless refresh).
export async function generateReport(id, { refresh = false } = {}) {
  if (MOCK) {
    await wait(2500);
    return mockAssessment(id);
  }
  return request(`/report/${encodeURIComponent(id)}${refresh ? "?refresh=true" : ""}`, { method: "POST" });
}

export async function getDashboard() {
  if (MOCK) {
    await wait(600);
    return mockDashboard();
  }
  return request("/dashboard", { headers: officerHeaders() });
}

// Upload a field photo; the backend compares it with the assessment.
export async function checkPhoto(assessmentId, file) {
  if (MOCK) {
    await wait(3000);
    return {
      photo_check: {
        photo_id: "ph_mock",
        photo_url: URL.createObjectURL(file),
        checked_at: new Date().toISOString(),
        model: "sample (mock mode)",
        gps: { lat: sampleResult.plot.centroid.lat, lng: sampleResult.plot.centroid.lng },
        taken_at: "2019-08-10T09:30:00",
        distance_m: 0,
        inside_plot: true,
        days_from_event: 3,
        flags: [],
        flag_messages: [],
        what_photo_shows: "standing_water",
        consistent: true,
        observations_en: "Sample text: the photo shows standing water across the field, which agrees with the satellite finding that most of the field was newly under water.",
        observations_kn: "ಮಾದರಿ ಪಠ್ಯ: ಫೋಟೋದಲ್ಲಿ ಹೊಲದ ತುಂಬಾ ನಿಂತ ನೀರು ಕಾಣುತ್ತದೆ. ಇದು ಹೊಲದ ಹೆಚ್ಚಿನ ಭಾಗ ಹೊಸದಾಗಿ ನೀರಿನಲ್ಲಿ ಮುಳುಗಿತ್ತು ಎಂಬ ಉಪಗ್ರಹ ಫಲಿತಾಂಶಕ್ಕೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ.",
      },
    };
  }
  const form = new FormData();
  form.append("assessment_id", assessmentId);
  form.append("photo", file);
  return request("/photo-check", { method: "POST", body: form });
}
