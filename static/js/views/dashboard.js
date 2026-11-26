// Live AQI dashboard: current conditions, best windows and 24-hour forecast.
import { api } from "../api.js";
import { h, render } from "../dom.js";
import { updateScene } from "../scene.js";
import { airMapSection } from "./airmap.js";
import {
  ACTIVITY_LABELS,
  POLLUTANT_LABELS,
  adviceBadge,
  categoryBadge,
  hhmm,
  number,
} from "../format.js";

const MAX_AQI = 500;

export async function renderDashboard(root, state) {
  render(root, h("div", { class: "skeleton", "aria-busy": "true", "aria-label": "Loading air quality" }));
  try {
    const data = await api.air(state.location);
    updateScene({
      city: state.location.name,
      category: data.current.category,
      label: data.current.label,
      aqi: data.current.aqi,
      nearYou: Boolean(state.location.gps),
    });
    render(root, view(data, state));
  } catch (error) {
    render(root, h("p", { class: "alert alert--error", role: "alert" }, error.message));
  }
}

function view(data, state) {
  const { current } = data;
  const children = state.members.filter((m) => m.age_group === "child" || m.age_group === "infant");
  return [
    data.stale
      ? h("p", { class: "alert alert--info", role: "status" }, "Showing recent saved data; the live feed is slow right now.")
      : null,
    children.length && ["poor", "very_poor", "severe"].includes(current.category)
      ? h(
          "p",
          { class: "alert", role: "status" },
          `Children's alert: the air is ${current.label}. Keep outdoor play short or move it indoors. See the Day planner for each child.`,
        )
      : null,
    h(
      "section",
      { class: "aqi-hero", "aria-labelledby": "aqi-title" },
      h(
        "div",
        { class: "card" },
        h("h2", { id: "aqi-title", class: "card__title" }, `Air quality now in ${state.location.gps && state.location.near ? `your area (near ${state.location.near})` : state.location.name}`),
        h(
          "p",
          { class: "aqi-value" },
          h("span", { class: "aqi-number" }, current.aqi),
          h("span", { class: "aqi-unit" }, "AQI (India)"),
          categoryBadge(current.category, current.label),
        ),
        h("p", {}, h("strong", {}, "Main pollutant: "), POLLUTANT_LABELS[current.dominant] ?? current.dominant),
        h("p", {}, adviceBadge(current.advice), " ", current.guidance),
        h("p", { class: "card__meta" }, `Updated ${hhmm(current.time)} local time · Estimate from modelled data`),
      ),
      h(
        "div",
        { class: "card" },
        h("h2", { class: "card__title" }, "Pollutants and weather"),
        pollutantList(current),
      ),
    ),
    airMapSection(state),
    h(
      "section",
      { class: "section", "aria-labelledby": "windows-title" },
      h("h2", { id: "windows-title" }, "Best times today"),
      h(
        "div",
        { class: "grid grid--4" },
        Object.entries(data.best_windows).map(([activity, w]) => windowCard(activity, w)),
      ),
    ),
    h(
      "section",
      { class: "section card", "aria-labelledby": "forecast-title" },
      h("h2", { id: "forecast-title", class: "card__title" }, "Next 24 hours"),
      forecastBars(data.forecast),
      forecastTable(data.forecast),
    ),
  ];
}

function pollutantList(current) {
  const p = current.pollutants;
  const w = current.weather;
  const rows = [
    ["PM2.5", p.pm2_5, "µg/m³"],
    ["PM10", p.pm10, "µg/m³"],
    ["NO₂", p.no2, "µg/m³"],
    ["O₃", p.o3, "µg/m³"],
    ["CO", p.co, "mg/m³"],
    ["SO₂", p.so2, "µg/m³"],
    ["Temperature", w.temperature_c, "°C"],
    ["Humidity", w.humidity_pct, "%"],
    ["Wind", w.wind_kmh, "km/h"],
  ];
  return h(
    "dl",
    { class: "pollutants" },
    rows
      .filter(([, value]) => value !== null && value !== undefined)
      .map(([label, value, unit]) =>
        h("div", {}, h("dt", {}, label), h("dd", {}, `${number(value, 1)} ${unit}`)),
      ),
  );
}

function windowCard(activity, w) {
  const title = ACTIVITY_LABELS[activity] ?? activity;
  if (!w) {
    return h("div", { class: "card" }, h("h3", { class: "card__title" }, title), h("p", {}, "No suitable time in the next 24 hours."));
  }
  return h(
    "div",
    { class: "card" },
    h("h3", { class: "card__title" }, title),
    h("p", { class: "item-row" }, h("strong", {}, `${hhmm(w.start)}–${hhmm(w.end)}`), adviceBadge(w.advice)),
    h("p", { class: "card__meta" }, `Average AQI ${w.avg_aqi} (${w.label})`),
    h("p", {}, w.guidance),
  );
}

function forecastBars(forecast) {
  const bars = h("div", { class: "forecast-bars", "aria-hidden": "true" });
  for (const hour of forecast) {
    const bar = h("div", { class: `forecast-bars__bar bar--${hour.category}`, title: `${hhmm(hour.time)}: AQI ${hour.aqi}` });
    bar.style.height = `${Math.max(4, Math.round((hour.aqi / MAX_AQI) * 100))}%`;
    bars.append(bar);
  }
  const first = forecast[0];
  const last = forecast[forecast.length - 1];
  return [
    bars,
    first
      ? h("div", { class: "forecast-axis", "aria-hidden": "true" }, h("span", {}, hhmm(first.time)), h("span", {}, hhmm(last.time)))
      : null,
  ];
}

function forecastTable(forecast) {
  return h(
    "details",
    {},
    h("summary", {}, "Show hourly forecast as a table"),
    h(
      "div",
      { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "Hourly forecast table" },
      h(
        "table",
        {},
        h("caption", {}, "24-hour AQI forecast"),
        h("thead", {}, h("tr", {}, ["Time", "AQI", "Category", "Outdoor exercise"].map((t) => h("th", { scope: "col" }, t)))),
        h(
          "tbody",
          {},
          forecast.map((hour) =>
            h(
              "tr",
              {},
              h("th", { scope: "row" }, hhmm(hour.time)),
              h("td", {}, hour.aqi),
              h("td", {}, categoryBadge(hour.category, hour.label)),
              h("td", {}, adviceBadge(hour.advice)),
            ),
          ),
        ),
      ),
    ),
  );
}
