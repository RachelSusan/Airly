// Labels and formatting shared by views.
import { h } from "./dom.js";

export const CATEGORY_ICONS = {
  good: "●",
  satisfactory: "◐",
  moderate: "▲",
  poor: "◆",
  very_poor: "■",
  severe: "✖",
};

export const CATEGORY_LABELS = {
  good: "Good",
  satisfactory: "Satisfactory",
  moderate: "Moderate",
  poor: "Poor",
  very_poor: "Very Poor",
  severe: "Severe",
};

export const ADVICE_LABELS = { safe: "Safe", caution: "Caution", avoid: "Avoid" };
const ADVICE_ICONS = { safe: "✓", caution: "!", avoid: "✕" };

export const RISK_LABELS = {
  low: "Low risk",
  moderate: "Moderate risk",
  high: "High risk",
  very_high: "Very high risk",
};

export const ACTIVITY_LABELS = {
  walk: "Walk",
  jog: "Jog or run",
  cycle: "Cycle",
  play: "Children's outdoor play",
  commute: "Commute",
};

export const MODE_LABELS = {
  walk: "Walking",
  cycle: "Cycling",
  petrol_car: "Petrol car",
  diesel_car: "Diesel car",
  cng_car: "CNG car",
  ev_car: "Electric car",
  petrol_2w: "Petrol two-wheeler",
  ev_2w: "Electric scooter",
  auto_cng: "Auto-rickshaw (CNG)",
  bus: "Bus",
  metro: "Metro",
  wfh: "Work from home",
};

export const AGE_LABELS = {
  infant: "Infant (0–1)",
  child: "Child (2–12)",
  teen: "Teen (13–17)",
  adult: "Adult (18–64)",
  senior: "Senior (65+)",
};

export const CONDITION_LABELS = {
  asthma: "Asthma",
  copd: "COPD",
  heart: "Heart condition",
  pregnancy: "Pregnancy",
  allergy: "Allergies",
};

export const POLLUTANT_LABELS = {
  pm2_5: "PM2.5 (fine particles)",
  pm10: "PM10 (coarse particles)",
  no2: "NO₂ (nitrogen dioxide)",
  o3: "O₃ (ozone)",
  co: "CO (carbon monoxide)",
  so2: "SO₂ (sulphur dioxide)",
};

export function categoryBadge(category, label) {
  return h(
    "span",
    { class: `badge badge--${category}` },
    h("span", { class: "badge__icon", "aria-hidden": "true" }, CATEGORY_ICONS[category] ?? "●"),
    label ?? CATEGORY_LABELS[category] ?? category,
  );
}

export function adviceBadge(advice) {
  return h(
    "span",
    { class: `badge badge--${advice}` },
    h("span", { class: "badge__icon", "aria-hidden": "true" }, ADVICE_ICONS[advice] ?? ""),
    ADVICE_LABELS[advice] ?? advice,
  );
}

export function riskBadge(risk) {
  return h("span", { class: `badge badge--${risk}` }, RISK_LABELS[risk] ?? risk);
}

export function sourceBadge(source) {
  return h(
    "span",
    { class: "badge badge--neutral" },
    source === "ai" ? "Written by Claude from live data" : "Rule-based backup (AI unavailable)",
  );
}

/** "14:00" from an ISO local time like 2026-11-26T14:00:00. */
export function hhmm(iso) {
  return typeof iso === "string" && iso.length >= 16 ? iso.slice(11, 16) : iso;
}

export function number(value, digits = 0) {
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits });
}
