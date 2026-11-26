// Air quality trend: daily AQI for the past week or month, with a summary and table.
import { api } from "../api.js";
import { h, render } from "../dom.js";
import { CATEGORY_LABELS, categoryBadge, dateLabel } from "../format.js";

const MAX_AQI = 500;
const PERIODS = [
  { days: 7, label: "Past week" },
  { days: 30, label: "Past month" },
];

let selected = 7;

/** Section with a week/month toggle, a daily bar chart, a summary and a data table. */
export function trendsSection(location) {
  const body = h("div", { "aria-live": "polite" });
  const buttons = PERIODS.map((p) =>
    h(
      "button",
      {
        type: "button",
        class: "chip",
        "aria-pressed": String(p.days === selected),
        onclick: () => {
          selected = p.days;
          buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(PERIODS[i].days === selected)));
          load(body, location);
        },
      },
      p.label,
    ),
  );
  load(body, location);
  return h(
    "section",
    { class: "section card", "aria-labelledby": "trend-title" },
    h(
      "div",
      { class: "item-row map-head" },
      h("div", {}, h("p", { class: "eyebrow" }, "Track over time"), h("h2", { id: "trend-title", class: "card__title" }, "Air quality trend")),
      h("div", { class: "chips", role: "group", "aria-label": "Choose period" }, buttons),
    ),
    body,
  );
}

async function load(body, location) {
  render(body, h("div", { class: "skeleton", "aria-busy": "true", "aria-label": "Loading trend" }));
  try {
    const data = await api.history(location, selected);
    render(body, view(data));
  } catch (error) {
    render(body, h("p", { class: "alert alert--error", role: "alert" }, error.message));
  }
}

function view(data) {
  const { days, summary } = data;
  const first = days[0];
  const last = days[days.length - 1];
  return [
    h("p", { class: "muted small" }, `${dateLabel(first.date)} – ${dateLabel(last.date)} · daily average AQI`),
    chart(days),
    summaryText(summary),
    categoryCounts(summary),
    h(
      "details",
      {},
      h("summary", {}, "Show every day as a table"),
      h(
        "div",
        { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "Daily AQI table" },
        h(
          "table",
          {},
          h("caption", {}, `Daily AQI, last ${data.period_days} days`),
          h("thead", {}, h("tr", {}, ["Date", "AQI", "Category", "PM2.5 (µg/m³)"].map((t) => h("th", { scope: "col" }, t)))),
          h(
            "tbody",
            {},
            [...days].reverse().map((d) =>
              h(
                "tr",
                {},
                h("th", { scope: "row" }, d.is_today ? `Today (${dateLabel(d.date)})` : dateLabel(d.date)),
                h("td", {}, d.aqi),
                h("td", {}, categoryBadge(d.category, d.category_label)),
                h("td", {}, d.pm2_5 ?? "–"),
              ),
            ),
          ),
        ),
      ),
    ),
    h("p", { class: "card__meta" }, data.note),
  ];
}

function chart(days) {
  const every = days.length > 10 ? 5 : 1; // label every day for a week, every 5th for a month
  const bars = h("div", { class: "trend-bars", "aria-hidden": "true" });
  const labels = h("div", { class: "trend-labels", "aria-hidden": "true" });
  days.forEach((d, i) => {
    const bar = h("div", {
      class: `trend-bars__bar bar--${d.category}${d.is_today ? " trend-bars__bar--today" : ""}`,
      title: `${dateLabel(d.date)}: AQI ${d.aqi} (${d.category_label})`,
    });
    bar.style.height = `${Math.max(4, Math.round((d.aqi / MAX_AQI) * 100))}%`;
    bars.append(bar);
    const show = i % every === 0 || i === days.length - 1;
    labels.append(h("span", {}, show ? (d.is_today ? "Today" : shortDate(d.date, days.length)) : ""));
  });
  return h("div", { class: "trend-chart" }, bars, labels);
}

function shortDate(iso, count) {
  const [, m, d] = iso.split("-").map(Number);
  return count > 10 ? `${d}/${m}` : dateLabel(iso).split(" ")[0];
}

function summaryText(s) {
  if (!s.best || !s.worst) return null;
  return h(
    "p",
    {},
    `Average AQI ${s.average_aqi} over ${s.days} full days. Cleanest: ${dateLabel(s.best.date)} (AQI ${s.best.aqi}, ${s.best.category_label}). Most polluted: ${dateLabel(s.worst.date)} (AQI ${s.worst.aqi}, ${s.worst.category_label}).`,
  );
}

function categoryCounts(s) {
  const entries = Object.entries(s.by_category).filter(([, n]) => n > 0);
  if (!entries.length) return null;
  return h(
    "ul",
    { class: "trend-counts", "aria-label": "Days in each category" },
    entries.map(([cat, n]) => h("li", {}, categoryBadge(cat, CATEGORY_LABELS[cat]), ` ${n} ${n === 1 ? "day" : "days"}`)),
  );
}
