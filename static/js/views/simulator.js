// AI What-If Pollution Simulator.
import { api } from "../api.js";
import { h, render, uid } from "../dom.js";
import { MODE_LABELS, number, sourceBadge } from "../format.js";
import { store } from "../store.js";

const FIELD_LABELS = {
  distance_km: ["Distance one way (km)", { min: 0.5, max: 200, step: 0.5 }],
  days_per_week: ["Days per week", { min: 1, max: 7, step: 1 }],
  families: ["Number of families", { min: 1, max: 1000000, step: 1 }],
  km_per_day_reduced: ["Km less driving per family per day", { min: 0.5, max: 200, step: 0.5 }],
  trees: ["Number of trees", { min: 1, max: 100000, step: 1 }],
  years: ["Years", { min: 1, max: 20, step: 1 }],
  peak_hour: ["Usual (peak) departure hour", { min: 0, max: 23, step: 1 }],
  off_peak_hour: ["New (off-peak) departure hour", { min: 0, max: 23, step: 1 }],
};
const MODE_FIELDS = { to_mode: "New way to travel", from_mode: "Current way to travel", mode: "How you travel", substitute: "Instead, families…" };
const PUBLIC_MODES = ["metro", "bus", "cycle", "walk", "ev_2w"];

let scenarios = null;

export async function renderSimulator(root) {
  render(root, h("div", { class: "skeleton", "aria-busy": "true", "aria-label": "Loading scenarios" }));
  try {
    scenarios = scenarios ?? (await api.scenarios()).scenarios;
  } catch (error) {
    render(root, h("p", { class: "alert alert--error", role: "alert" }, error.message));
    return;
  }
  const formHost = h("div");
  const result = h("div", { "aria-live": "polite" });
  const choose = (scenario) => render(formHost, scenarioForm(scenario, result));
  render(
    root,
    h("p", {}, "Explore what changes when you, or your community, change habits. Results are estimated emission changes, not predictions of your local AQI."),
    h(
      "fieldset",
      { class: "field scenario-list" },
      h("legend", {}, "Choose a scenario"),
      scenarios.map((s, i) =>
        h(
          "label",
          { class: "scenario-option" },
          h("input", { type: "radio", name: "scenario", value: s.scenario_id, checked: i === 0, onchange: () => choose(s) }),
          h("span", {}, h("strong", {}, s.title), h("span", { class: "checklist__reason" }, s.description)),
        ),
      ),
    ),
    formHost,
    result,
  );
  choose(scenarios[0]);
}

function scenarioForm(scenario, result) {
  const controls = Object.entries(scenario.defaults).map(([name, value]) => control(scenario.scenario_id, name, value));
  const button = h("button", { type: "submit", class: "btn btn--primary" }, "Calculate impact");
  const form = h("form", { class: "card section", novalidate: true }, h("h2", { class: "card__title" }, scenario.title), h("div", { class: "form-grid" }, controls), h("div", { class: "actions" }, button));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const inputs = {};
    for (const [name, value] of new FormData(form).entries()) {
      inputs[name] = name in FIELD_LABELS ? Number(value) : String(value);
    }
    const body = { scenario_id: scenario.scenario_id, inputs };
    const loc = store.get().location;
    if (scenario.scenario_id === "avoid_peak_hours" && loc) body.location = { lat: loc.lat, lon: loc.lon };
    button.disabled = true;
    result.setAttribute("aria-busy", "true");
    try {
      render(result, resultView(await api.simulate(body)));
    } catch (error) {
      render(result, h("p", { class: "alert alert--error", role: "alert" }, error.message));
    } finally {
      button.disabled = false;
      result.removeAttribute("aria-busy");
    }
  });
  return form;
}

function control(scenarioId, name, value) {
  const id = uid(name);
  if (name in MODE_FIELDS) {
    const options = name === "to_mode" && scenarioId === "petrol_to_public" ? PUBLIC_MODES : Object.keys(MODE_LABELS).filter((m) => m !== "wfh");
    return h(
      "div",
      { class: "field" },
      h("label", { for: id }, MODE_FIELDS[name]),
      h("select", { id, name }, options.map((m) => h("option", { value: m, selected: m === value }, MODE_LABELS[m]))),
    );
  }
  const [label, limits] = FIELD_LABELS[name] ?? [name, {}];
  return h("div", { class: "field" }, h("label", { for: id }, label), h("input", { id, name, type: "number", required: true, value, ...limits }));
}

function resultView(data) {
  const r = data.result;
  const verb = (v) => (v < 0 ? "less" : "more");
  const stats = [
    ["CO₂", `${number(Math.abs(r.co2_kg))} kg ${verb(r.co2_kg)}`],
    r.pm25_g !== null ? ["PM2.5 emitted", `${number(Math.abs(r.pm25_g))} g ${verb(r.pm25_g)}`] : null,
    r.nox_g !== null ? ["NOₓ emitted", `${number(Math.abs(r.nox_g))} g ${verb(r.nox_g)}`] : null,
    r.exposure_change_pct !== null ? ["PM2.5 you breathe on the way", `${r.exposure_change_pct > 0 ? "+" : ""}${r.exposure_change_pct}%`] : null,
  ].filter(Boolean);
  return h(
    "section",
    { class: "card section", "aria-labelledby": "result-title" },
    h("h2", { id: "result-title", class: "card__title" }, `Estimated change per ${r.period}`),
    h("p", {}, sourceBadge(data.source)),
    h("dl", { class: "stats" }, stats.map(([k, v]) => h("div", {}, h("dt", {}, k), h("dd", {}, v)))),
    h("p", {}, data.explanation),
    data.next_step ? h("p", {}, h("strong", {}, "Next step: "), data.next_step) : null,
    h(
      "details",
      {},
      h("summary", {}, "How we calculated this"),
      h("ul", {}, data.assumptions.map((a) => h("li", {}, a))),
      h("p", { class: "card__meta" }, "Sources: ", data.sources.join("; ")),
    ),
    h("p", { class: "disclaimer" }, data.disclaimer),
  );
}
