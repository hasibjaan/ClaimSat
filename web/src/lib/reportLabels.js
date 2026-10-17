// Fixed labels on the report page, in English and Kannada.
// The report body itself is written by Gemini in both languages.

export const LABELS = {
  en: {
    title: "Crop damage evidence report",
    assessmentId: "Assessment ID",
    generated: "Generated",
    print: "Print / Save as PDF",
    back: "Back to map",
    regenerate: "Rewrite report",
    summary: "Summary",
    damageScore: "Damage score",
    outOf: "out of 100",
    confidence: "Confidence",
    plotDetails: "Plot details",
    farmer: "Farmer",
    village: "Village",
    crop: "Crop (as reported)",
    survey: "Survey no.",
    area: "Area",
    location: "Location (centre)",
    event: "Event",
    keyMeasurements: "Key measurements",
    cropHealthLost: "Crop health lost",
    cropHealthLostHint: "vs. 1 week before the event",
    fieldFlooded: "Newly under water",
    fieldFloodedHint: "dry 1 week before",
    rainShortfall: "Rain shortfall",
    rainShortfallHint: "vs. 20-year normal",
    cropland: "Cropland",
    croplandHint: "share of the plot",
    findings: "What the satellites show",
    images: "Satellite images: 1 week before vs now",
    before: "1 week before",
    after: "Now",
    ndviAfter: "Crop health now (green = healthy)",
    floodMask: "New water since the week before (blue)",
    imagesNote: "The plot is outlined in yellow. Grey areas were hidden by cloud.",
    chart: "Crop health over time",
    chartThisYear: "This year",
    chartNormal: "Normal",
    chartX: "Days from the event",
    chartY: "Crop health (NDVI)",
    limitations: "Limitations",
    nextSteps: "What to do next",
    sources: "Data sources and image dates",
    s2Before: "Sentinel-2 image, 1 week before",
    s2After: "Sentinel-2 image, now",
    fingerprint: "Evidence fingerprint",
    fingerprintNote:
      "A code calculated from the measurements in this report. If any number is changed later, the code will no longer match.",
    writtenBy: "Report text written by Gemini (Vertex AI) from the measurements above.",
    disclaimer: "This is supporting evidence for a crop insurance claim, not an official loss assessment.",
    loading: "Loading assessment…",
    writing: "Writing your report in English and Kannada…",
    writingHint: "Gemini is writing the report from the satellite measurements. This takes about 10–20 seconds.",
    tryAgain: "Try again",
    numberWarning:
      "Some percentages in the text could not be matched to the measurements. Check the report text against the figures before using it.",
  },
  kn: {
    title: "ಬೆಳೆ ಹಾನಿ ಸಾಕ್ಷ್ಯ ವರದಿ",
    assessmentId: "ಮೌಲ್ಯಮಾಪನ ಸಂಖ್ಯೆ",
    generated: "ರಚಿಸಿದ ದಿನಾಂಕ",
    print: "ಮುದ್ರಿಸಿ / PDF ಆಗಿ ಉಳಿಸಿ",
    back: "ನಕ್ಷೆಗೆ ಹಿಂತಿರುಗಿ",
    regenerate: "ವರದಿಯನ್ನು ಮತ್ತೆ ಬರೆಯಿರಿ",
    summary: "ಸಾರಾಂಶ",
    damageScore: "ಹಾನಿ ಅಂಕ",
    outOf: "100 ರಲ್ಲಿ",
    confidence: "ವಿಶ್ವಾಸಾರ್ಹತೆ",
    plotDetails: "ಜಮೀನಿನ ವಿವರಗಳು",
    farmer: "ರೈತರು",
    village: "ಗ್ರಾಮ",
    crop: "ಬೆಳೆ (ತಿಳಿಸಿದಂತೆ)",
    survey: "ಸರ್ವೆ ನಂ.",
    area: "ವಿಸ್ತೀರ್ಣ",
    location: "ಸ್ಥಳ (ಮಧ್ಯಭಾಗ)",
    event: "ಘಟನೆ",
    keyMeasurements: "ಮುಖ್ಯ ಅಳತೆಗಳು",
    cropHealthLost: "ಬೆಳೆ ಆರೋಗ್ಯ ನಷ್ಟ",
    cropHealthLostHint: "ಘಟನೆಗೆ 1 ವಾರ ಮೊದಲಿಗೆ ಹೋಲಿಸಿದರೆ",
    fieldFlooded: "ಹೊಸದಾಗಿ ಜಲಾವೃತ",
    fieldFloodedHint: "1 ವಾರ ಮೊದಲು ಒಣಗಿತ್ತು",
    rainShortfall: "ಮಳೆ ಕೊರತೆ",
    rainShortfallHint: "20 ವರ್ಷಗಳ ಸರಾಸರಿಗೆ ಹೋಲಿಸಿದರೆ",
    cropland: "ಕೃಷಿ ಭೂಮಿ",
    croplandHint: "ಜಮೀನಿನ ಭಾಗ",
    findings: "ಉಪಗ್ರಹಗಳು ತೋರಿಸುವುದು",
    images: "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು: 1 ವಾರ ಮೊದಲು ಮತ್ತು ಈಗ",
    before: "1 ವಾರ ಮೊದಲು",
    after: "ಈಗ",
    ndviAfter: "ಈಗಿನ ಬೆಳೆ ಆರೋಗ್ಯ (ಹಸಿರು = ಆರೋಗ್ಯಕರ)",
    floodMask: "ಕಳೆದ ವಾರದಿಂದ ಹೊಸ ನೀರು (ನೀಲಿ)",
    imagesNote: "ಜಮೀನನ್ನು ಹಳದಿ ಗೆರೆಯಿಂದ ಗುರುತಿಸಲಾಗಿದೆ. ಬೂದು ಭಾಗಗಳು ಮೋಡದಿಂದ ಮರೆಯಾಗಿವೆ.",
    chart: "ಕಾಲಾನುಕ್ರಮದಲ್ಲಿ ಬೆಳೆಯ ಆರೋಗ್ಯ",
    chartThisYear: "ಈ ವರ್ಷ",
    chartNormal: "ಸಾಮಾನ್ಯ",
    chartX: "ಘಟನೆಯಿಂದ ದಿನಗಳು",
    chartY: "ಬೆಳೆಯ ಆರೋಗ್ಯ (NDVI)",
    limitations: "ಮಿತಿಗಳು",
    nextSteps: "ಮುಂದೆ ಏನು ಮಾಡಬೇಕು",
    sources: "ದತ್ತಾಂಶ ಮೂಲಗಳು ಮತ್ತು ಚಿತ್ರಗಳ ದಿನಾಂಕಗಳು",
    s2Before: "Sentinel-2 ಚಿತ್ರ, 1 ವಾರ ಮೊದಲು",
    s2After: "Sentinel-2 ಚಿತ್ರ, ಈಗ",
    fingerprint: "ಸಾಕ್ಷ್ಯದ ಬೆರಳಚ್ಚು",
    fingerprintNote:
      "ಈ ವರದಿಯ ಅಳತೆಗಳಿಂದ ಲೆಕ್ಕ ಹಾಕಿದ ಸಂಕೇತ. ನಂತರ ಯಾವುದೇ ಸಂಖ್ಯೆಯನ್ನು ಬದಲಾಯಿಸಿದರೆ, ಈ ಸಂಕೇತ ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ.",
    writtenBy: "ಮೇಲಿನ ಅಳತೆಗಳ ಆಧಾರದ ಮೇಲೆ ವರದಿಯ ಪಠ್ಯವನ್ನು Gemini (Vertex AI) ಬರೆದಿದೆ.",
    disclaimer: "ಇದು ಬೆಳೆ ವಿಮೆ ಕ್ಲೇಮ್‌ಗೆ ಪೂರಕ ಸಾಕ್ಷ್ಯ ಮಾತ್ರ, ಅಧಿಕೃತ ನಷ್ಟ ಮೌಲ್ಯಮಾಪನವಲ್ಲ.",
    loading: "ಮೌಲ್ಯಮಾಪನವನ್ನು ತೆರೆಯಲಾಗುತ್ತಿದೆ…",
    writing: "ನಿಮ್ಮ ವರದಿಯನ್ನು ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡದಲ್ಲಿ ಬರೆಯಲಾಗುತ್ತಿದೆ…",
    writingHint: "ಉಪಗ್ರಹ ಅಳತೆಗಳಿಂದ Gemini ವರದಿಯನ್ನು ಬರೆಯುತ್ತಿದೆ. ಸುಮಾರು 10–20 ಸೆಕೆಂಡುಗಳು ಬೇಕಾಗುತ್ತವೆ.",
    tryAgain: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
    numberWarning:
      "ಪಠ್ಯದಲ್ಲಿನ ಕೆಲವು ಶೇಕಡಾವಾರು ಸಂಖ್ಯೆಗಳು ಅಳತೆಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ. ಬಳಸುವ ಮೊದಲು ಪಠ್ಯವನ್ನು ಅಂಕಿಗಳೊಂದಿಗೆ ಹೋಲಿಸಿ ನೋಡಿ.",
  },
};

export const EVENT_NAMES = {
  en: { flood: "Flood", drought: "Drought", other: "Other damage" },
  kn: { flood: "ಪ್ರವಾಹ", drought: "ಬರ", other: "ಇತರ ಹಾನಿ" },
};

export const LEVEL_NAMES = {
  en: {
    none: "No clear damage",
    low: "Low damage",
    moderate: "Moderate damage",
    severe: "Severe damage",
    unknown: "Not enough data",
  },
  kn: {
    none: "ಸ್ಪಷ್ಟ ಹಾನಿ ಇಲ್ಲ",
    low: "ಕಡಿಮೆ ಹಾನಿ",
    moderate: "ಮಧ್ಯಮ ಹಾನಿ",
    severe: "ತೀವ್ರ ಹಾನಿ",
    unknown: "ಸಾಕಷ್ಟು ದತ್ತಾಂಶ ಇಲ್ಲ",
  },
};

export const CONFIDENCE_NAMES = {
  en: { high: "High confidence", medium: "Medium confidence", low: "Low confidence" },
  kn: { high: "ಹೆಚ್ಚು ವಿಶ್ವಾಸಾರ್ಹತೆ", medium: "ಮಧ್ಯಮ ವಿಶ್ವಾಸಾರ್ಹತೆ", low: "ಕಡಿಮೆ ವಿಶ್ವಾಸಾರ್ಹತೆ" },
};

export const DATA_SOURCES = {
  en: [
    "Sentinel-2 satellite images (European Space Agency, Copernicus programme): one image about 1 week before the event and the latest one. Crop health (NDVI) and standing water (water index) are read from the same two images.",
    "ERA5-Land daily weather (ECMWF / Copernicus), used only for step 2 of verification",
    "Processed with Google Earth Engine; weather check and report text by Gemini (Vertex AI)",
  ],
  kn: [
    "Sentinel-2 ಉಪಗ್ರಹ ಚಿತ್ರಗಳು (ಯುರೋಪಿಯನ್ ಬಾಹ್ಯಾಕಾಶ ಸಂಸ್ಥೆ, Copernicus ಕಾರ್ಯಕ್ರಮ): ಘಟನೆಗೆ ಸುಮಾರು 1 ವಾರ ಮೊದಲಿನ ಒಂದು ಚಿತ್ರ ಮತ್ತು ಇತ್ತೀಚಿನ ಚಿತ್ರ. ಬೆಳೆಯ ಆರೋಗ್ಯ (NDVI) ಮತ್ತು ನಿಂತ ನೀರು (ನೀರಿನ ಸೂಚ್ಯಂಕ) ಇದೇ ಎರಡು ಚಿತ್ರಗಳಿಂದ ಅಳೆಯಲಾಗುತ್ತದೆ.",
    "ERA5-Land ದೈನಂದಿನ ಹವಾಮಾನ ದತ್ತಾಂಶ (ECMWF / Copernicus), ಪರಿಶೀಲನೆಯ 2ನೇ ಹಂತಕ್ಕೆ ಮಾತ್ರ",
    "Google Earth Engine ನಲ್ಲಿ ಸಂಸ್ಕರಿಸಲಾಗಿದೆ; ಹವಾಮಾನ ಪರಿಶೀಲನೆ ಮತ್ತು ವರದಿಯ ಪಠ್ಯ Gemini (Vertex AI) ಮೂಲಕ",
  ],
};

// Farmer photo check (Phase 5).
export const PHOTO_LABELS = {
  en: {
    title: "Farmer's field photo",
    matches: "Photo agrees with the satellite evidence",
    matchesWithWarnings: "Photo looks consistent, but see the warnings below",
    differs: "Photo does not agree with the satellite evidence",
    shows: "What the photo shows",
    taken: "Taken",
    daysAfter: (n) => (n === 0 ? "on the event day" : n > 0 ? `${n} days after the event` : `${-n} days before the event`),
    location: "Location",
    inside: "Inside the plot",
    away: (m) => (m >= 1000 ? `${Math.round(m / 1000)} km from the plot` : `${m} m from the plot`),
    unknown: "Unknown",
    note: "Location and date come from the photo file. The stored copy has its location data removed.",
  },
  kn: {
    title: "ರೈತರು ತೆಗೆದ ಹೊಲದ ಫೋಟೋ",
    matches: "ಫೋಟೋ ಉಪಗ್ರಹ ಸಾಕ್ಷ್ಯಕ್ಕೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ",
    matchesWithWarnings: "ಫೋಟೋ ಹೊಂದಿಕೆಯಾಗುವಂತೆ ಕಾಣುತ್ತದೆ, ಆದರೆ ಕೆಳಗಿನ ಎಚ್ಚರಿಕೆಗಳನ್ನು ನೋಡಿ",
    differs: "ಫೋಟೋ ಉಪಗ್ರಹ ಸಾಕ್ಷ್ಯಕ್ಕೆ ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ",
    shows: "ಫೋಟೋದಲ್ಲಿ ಕಾಣುವುದು",
    taken: "ತೆಗೆದ ದಿನಾಂಕ",
    daysAfter: (n) => (n === 0 ? "ಘಟನೆಯ ದಿನ" : n > 0 ? `ಘಟನೆಯ ${n} ದಿನಗಳ ನಂತರ` : `ಘಟನೆಗೆ ${-n} ದಿನಗಳ ಮೊದಲು`),
    location: "ಸ್ಥಳ",
    inside: "ಜಮೀನಿನ ಒಳಗೆ",
    away: (m) => (m >= 1000 ? `ಜಮೀನಿನಿಂದ ${Math.round(m / 1000)} ಕಿ.ಮೀ ದೂರ` : `ಜಮೀನಿನಿಂದ ${m} ಮೀ ದೂರ`),
    unknown: "ತಿಳಿದಿಲ್ಲ",
    note: "ಸ್ಥಳ ಮತ್ತು ದಿನಾಂಕವನ್ನು ಫೋಟೋ ಫೈಲ್‌ನಿಂದ ಪಡೆಯಲಾಗಿದೆ. ಉಳಿಸಿದ ಪ್ರತಿಯಿಂದ ಸ್ಥಳದ ಮಾಹಿತಿಯನ್ನು ತೆಗೆದುಹಾಕಲಾಗಿದೆ.",
  },
};

export const PHOTO_FLAGS = {
  en: {
    no_gps: "The photo has no location data, so it can't be tied to this plot.",
    far_from_plot: "The photo was taken more than 200 m from the plot.",
    no_timestamp: "The photo has no date, so it can't be tied to the event.",
    taken_before_event: "The photo was taken before the event date.",
    taken_long_after_event: "The photo was taken more than 60 days after the event.",
  },
  kn: {
    no_gps: "ಫೋಟೋದಲ್ಲಿ ಸ್ಥಳದ ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಇದನ್ನು ಈ ಜಮೀನಿಗೆ ಜೋಡಿಸಲು ಆಗುವುದಿಲ್ಲ.",
    far_from_plot: "ಫೋಟೋವನ್ನು ಜಮೀನಿನಿಂದ 200 ಮೀಟರ್‌ಗಿಂತ ಹೆಚ್ಚು ದೂರದಲ್ಲಿ ತೆಗೆಯಲಾಗಿದೆ.",
    no_timestamp: "ಫೋಟೋದಲ್ಲಿ ದಿನಾಂಕ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಇದನ್ನು ಘಟನೆಗೆ ಜೋಡಿಸಲು ಆಗುವುದಿಲ್ಲ.",
    taken_before_event: "ಫೋಟೋವನ್ನು ಘಟನೆಯ ದಿನಾಂಕಕ್ಕಿಂತ ಮೊದಲು ತೆಗೆಯಲಾಗಿದೆ.",
    taken_long_after_event: "ಫೋಟೋವನ್ನು ಘಟನೆಯ 60 ದಿನಗಳಿಗಿಂತ ಹೆಚ್ಚು ನಂತರ ತೆಗೆಯಲಾಗಿದೆ.",
  },
};

export const PHOTO_SHOWS = {
  en: {
    standing_water: "Standing water",
    flattened_or_damaged_crop: "Flattened or damaged crop",
    dried_crop: "Dried crop",
    healthy_crop: "Healthy crop",
    bare_soil: "Bare soil",
    not_a_field: "Not a farm field",
    unclear: "Unclear",
  },
  kn: {
    standing_water: "ನಿಂತ ನೀರು",
    flattened_or_damaged_crop: "ನೆಲಕ್ಕುರುಳಿದ ಅಥವಾ ಹಾನಿಗೊಳಗಾದ ಬೆಳೆ",
    dried_crop: "ಒಣಗಿದ ಬೆಳೆ",
    healthy_crop: "ಆರೋಗ್ಯಕರ ಬೆಳೆ",
    bare_soil: "ಬರಿಯ ಮಣ್ಣು",
    not_a_field: "ಹೊಲದ ಚಿತ್ರವಲ್ಲ",
    unclear: "ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ",
  },
};

// Two-step verification, nearby reports and case severity.
export const VERIFY_LABELS = {
  en: {
    title: "Two-step verification",
    status: { verified: "Verified", needs_review: "Needs review", not_supported: "Not supported" },
    statusHint: {
      verified: "The satellite images and the weather record both support this claim.",
      needs_review: "One check couldn’t confirm the claim. An officer should look at it.",
      not_supported: "Neither the satellite images nor the weather record support this claim.",
    },
    step1: "Step 1 · Satellite images",
    step2: "Step 2 · Weather record (checked by AI)",
    verdict: { supported: "Supports the claim", not_supported: "Doesn’t support the claim", uncertain: "Can’t confirm either way" },
    satellite: {
      pass: (level) => `The satellite images show ${level} damage on this plot.`,
      fail: "The satellite images show no clear damage on this plot.",
      unknown: "Not enough clear satellite images to judge the damage.",
    },
    facts: {
      week: (v, n) => `Rain across the region in the week before: ${v} mm (normal ${n} mm)`,
      daily: (v) => `Most rain in one day: ${v} mm`,
      month: (v, n) => `Rain in the last 30 days: ${v} mm (normal ${n} mm)`,
      heat: (v) => `Highest temperature that week: ${v} °C`,
    },
    weatherSource: "ERA5-Land daily weather",
    severity: "Case severity",
    severityLevel: { none: "Minimal", low: "Low", moderate: "Moderate", severe: "Severe", unknown: "Unknown" },
    severityHint: "This plot’s damage, together with how many farmers nearby reported the same event.",
    plotDamage: "Damage on this plot",
    nearby: "Nearby reports",
    nearbyText: (n, km, days) =>
      n === 0
        ? `No other farmers within ${km} km have reported this yet.`
        : `${n} other farmer${n === 1 ? "" : "s"} within ${km} km reported the same event within ${days} days.`,
    areaLevel: { isolated: "Single report", some: "Some reports nearby", widespread: "Widespread" },
  },
  kn: {
    title: "ಎರಡು ಹಂತದ ಪರಿಶೀಲನೆ",
    status: { verified: "ದೃಢೀಕರಿಸಲಾಗಿದೆ", needs_review: "ಪರಿಶೀಲನೆ ಅಗತ್ಯ", not_supported: "ಬೆಂಬಲವಿಲ್ಲ" },
    statusHint: {
      verified: "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಮತ್ತು ಹವಾಮಾನ ದಾಖಲೆಗಳು ಎರಡೂ ಈ ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುತ್ತವೆ.",
      needs_review: "ಒಂದು ಪರಿಶೀಲನೆ ಕ್ಲೇಮ್ ಅನ್ನು ದೃಢಪಡಿಸಲಿಲ್ಲ. ಅಧಿಕಾರಿಗಳು ಇದನ್ನು ನೋಡಬೇಕು.",
      not_supported: "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಅಥವಾ ಹವಾಮಾನ ದಾಖಲೆಗಳು ಈ ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ.",
    },
    step1: "ಹಂತ 1 · ಉಪಗ್ರಹ ಚಿತ್ರಗಳು",
    step2: "ಹಂತ 2 · ಹವಾಮಾನ ದಾಖಲೆ (AI ಪರಿಶೀಲನೆ)",
    verdict: { supported: "ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ", not_supported: "ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ", uncertain: "ಖಚಿತವಾಗಿ ಹೇಳಲಾಗುವುದಿಲ್ಲ" },
    satellite: {
      pass: (level) => `ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಈ ಜಮೀನಿನಲ್ಲಿ ${level} ಹಾನಿಯನ್ನು ತೋರಿಸುತ್ತವೆ.`,
      fail: "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಈ ಜಮೀನಿನಲ್ಲಿ ಸ್ಪಷ್ಟ ಹಾನಿಯನ್ನು ತೋರಿಸುವುದಿಲ್ಲ.",
      unknown: "ಹಾನಿಯನ್ನು ನಿರ್ಧರಿಸಲು ಸಾಕಷ್ಟು ಸ್ಪಷ್ಟ ಉಪಗ್ರಹ ಚಿತ್ರಗಳಿಲ್ಲ.",
    },
    facts: {
      week: (v, n) => `ಹಿಂದಿನ ವಾರ ಪ್ರದೇಶದಾದ್ಯಂತ ಮಳೆ: ${v} ಮಿ.ಮೀ (ಸಾಮಾನ್ಯ ${n} ಮಿ.ಮೀ)`,
      daily: (v) => `ಒಂದೇ ದಿನದ ಗರಿಷ್ಠ ಮಳೆ: ${v} ಮಿ.ಮೀ`,
      month: (v, n) => `ಕಳೆದ 30 ದಿನಗಳ ಮಳೆ: ${v} ಮಿ.ಮೀ (ಸಾಮಾನ್ಯ ${n} ಮಿ.ಮೀ)`,
      heat: (v) => `ಆ ವಾರದ ಗರಿಷ್ಠ ತಾಪಮಾನ: ${v} °C`,
    },
    weatherSource: "ERA5-Land ದೈನಂದಿನ ಹವಾಮಾನ ದತ್ತಾಂಶ",
    severity: "ಪ್ರಕರಣದ ತೀವ್ರತೆ",
    severityLevel: { none: "ಕನಿಷ್ಠ", low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", severe: "ತೀವ್ರ", unknown: "ತಿಳಿದಿಲ್ಲ" },
    severityHint: "ಈ ಜಮೀನಿನ ಹಾನಿ ಮತ್ತು ಹತ್ತಿರದ ಎಷ್ಟು ರೈತರು ಇದೇ ಘಟನೆಯನ್ನು ವರದಿ ಮಾಡಿದ್ದಾರೆ ಎಂಬುದರ ಆಧಾರದ ಮೇಲೆ.",
    plotDamage: "ಈ ಜಮೀನಿನ ಹಾನಿ",
    nearby: "ಹತ್ತಿರದ ವರದಿಗಳು",
    nearbyText: (n, km, days) =>
      n === 0
        ? `${km} ಕಿ.ಮೀ ಒಳಗೆ ಬೇರೆ ಯಾವ ರೈತರೂ ಇದನ್ನು ಇನ್ನೂ ವರದಿ ಮಾಡಿಲ್ಲ.`
        : `${km} ಕಿ.ಮೀ ಒಳಗಿನ ಇನ್ನೂ ${n} ರೈತರು ${days} ದಿನಗಳ ಒಳಗೆ ಇದೇ ಘಟನೆಯನ್ನು ವರದಿ ಮಾಡಿದ್ದಾರೆ.`,
    areaLevel: { isolated: "ಒಂದೇ ವರದಿ", some: "ಹತ್ತಿರ ಕೆಲವು ವರದಿಗಳು", widespread: "ವ್ಯಾಪಕ" },
  },
};
