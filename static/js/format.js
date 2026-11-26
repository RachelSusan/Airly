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

export const RELATIONSHIP_LABELS = {
  self: "Me",
  spouse: "Spouse / partner",
  child: "Child",
  parent: "Parent",
  grandparent: "Grandparent",
  sibling: "Sibling",
  other: "Other family",
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
    source === "ai" ? "Written by Gemini AI from live data" : "Rule-based backup (AI unavailable)",
  );
}

// ---- Dates and times -------------------------------------------------------------
// API times are the location's local time without a zone ("2026-11-26T16:00"), so they are
// read as plain parts, never shifted into the viewer's time zone.

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function parts(iso) {
  const [datePart, timePart = "00:00"] = String(iso).split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = timePart.split(":").map(Number);
  return { y, m, d, hh: hh || 0, mm: mm || 0 };
}

function weekday({ y, m, d }) {
  return DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

/** "4:00 PM" */
export function timeLabel(iso) {
  const { hh, mm } = parts(iso);
  return `${hh % 12 || 12}:${String(mm).padStart(2, "0")} ${hh < 12 ? "AM" : "PM"}`;
}

/** "4 PM" (compact, for chart axes) */
export function hourLabel(iso) {
  const { hh } = parts(iso);
  return `${hh % 12 || 12} ${hh < 12 ? "AM" : "PM"}`;
}

/** "Thu 26 Nov" */
export function dateLabel(iso) {
  const p = parts(iso);
  return `${weekday(p)} ${p.d} ${MONTHS[p.m - 1]}`;
}

/** "Today", "Tomorrow" or "Sat 28 Nov", relative to the reference date (ISO). */
export function dayWord(iso, referenceIso) {
  const a = parts(iso);
  const b = parts(referenceIso);
  const diff = Math.round((Date.UTC(a.y, a.m - 1, a.d) - Date.UTC(b.y, b.m - 1, b.d)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return dateLabel(iso);
}

/** Viewer's own clock, e.g. "4:05 PM" (for "sent at" / "generated at" stamps). */
export function nowLabel(date = new Date()) {
  return date.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: true }).toUpperCase();
}

export function number(value, digits = 0) {
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits });
}

/** "Me · Adult (18–64)"; avoids "Child · Child (2–12)". */
export function roleLabel(person) {
  if (!person) return "";
  const age = AGE_LABELS[person.age_group] ?? "";
  if (person.relationship === "child" || !person.relationship) return age;
  return `${RELATIONSHIP_LABELS[person.relationship] ?? "Family"} · ${age}`;
}
