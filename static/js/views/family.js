// Family Protection Profiles + household lifestyle. Stored only in this browser.
import { confirmAction, h, render, uid } from "../dom.js";
import { AGE_LABELS, CONDITION_LABELS, MODE_LABELS } from "../format.js";
import { store } from "../store.js";

const MAX_MEMBERS = 10;
const ACTIVITIES = { walking: "Walking", jogging: "Jogging", cycling: "Cycling", play: "Outdoor play", sports: "Sports" };
const FUELS = { lpg: "LPG", png: "Piped gas", electric: "Electric", biomass: "Wood / dung", kerosene: "Kerosene" };

export function renderFamily(root, state) {
  render(
    root,
    h("p", {}, "Profiles stay on this device. They are only sent when you ask for a plan or an answer, and never stored on our server."),
    membersSection(root, state),
    memberForm(root),
    householdForm(state),
    h(
      "section",
      { class: "section", "aria-labelledby": "privacy-title" },
      h("h2", { id: "privacy-title" }, "Your data"),
      h(
        "button",
        {
          type: "button",
          class: "btn btn--danger",
          onclick: async () => {
            if (await confirmAction("This removes your city, family profiles and checklist from this device.", "Clear my data")) {
              store.clear();
              renderFamily(root, store.get());
            }
          },
        },
        "Clear my data",
      ),
    ),
  );
}

function membersSection(root, state) {
  return h(
    "section",
    { "aria-labelledby": "members-list-title" },
    h("h2", { id: "members-list-title" }, `Family members (${state.members.length})`),
    state.members.length
      ? h(
          "ul",
          { class: "grid grid--2 plain-list" },
          state.members.map((m) =>
            h(
              "li",
              { class: "card" },
              h("h3", { class: "card__title" }, m.name || "Family member"),
              h("p", {}, AGE_LABELS[m.age_group]),
              h("p", { class: "card__meta" }, m.conditions.length ? m.conditions.map((c) => CONDITION_LABELS[c]).join(", ") : "No conditions listed"),
              h(
                "button",
                {
                  type: "button",
                  class: "btn btn--secondary btn--small",
                  "aria-label": `Remove ${m.name || "family member"}`,
                  onclick: async () => {
                    if (await confirmAction(`Remove ${m.name || "this family member"}?`, "Remove")) {
                      store.update({ members: store.get().members.filter((x) => x.id !== m.id) });
                      renderFamily(root, store.get());
                    }
                  },
                },
                "Remove",
              ),
            ),
          ),
        )
      : h("p", { class: "empty-state" }, "No family members yet. Add the first one below."),
  );
}

function memberForm(root) {
  const nameId = uid("name");
  const ageId = uid("age");
  const errorId = uid("err");
  const error = h("p", { id: errorId, class: "field__error", role: "alert" });
  const form = h(
    "form",
    { class: "card section", "aria-labelledby": "add-title", novalidate: true },
    h("h2", { id: "add-title", class: "card__title" }, "Add a family member"),
    h(
      "div",
      { class: "form-grid" },
      h("div", { class: "field" }, h("label", { for: nameId }, "Name or nickname (optional)"), h("input", { id: nameId, name: "name", maxlength: "40", autocomplete: "off" })),
      h(
        "div",
        { class: "field" },
        h("label", { for: ageId }, "Age group"),
        h("select", { id: ageId, name: "age_group", required: true }, Object.entries(AGE_LABELS).map(([v, l]) => h("option", { value: v, selected: v === "adult" }, l))),
      ),
    ),
    checkboxGroup("Health conditions", "conditions", CONDITION_LABELS),
    checkboxGroup("Usual outdoor activities", "activities", ACTIVITIES),
    error,
    h("div", { class: "actions" }, h("button", { type: "submit", class: "btn btn--primary" }, "Add member")),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const members = store.get().members;
    if (members.length >= MAX_MEMBERS) {
      error.textContent = `You can add up to ${MAX_MEMBERS} family members.`;
      return;
    }
    const data = new FormData(form);
    const name = String(data.get("name") || "").trim().slice(0, 40);
    store.update({
      members: [
        ...members,
        {
          id: `m_${Date.now().toString(36)}`,
          name,
          age_group: String(data.get("age_group")),
          conditions: data.getAll("conditions").map(String),
          outdoor_activities: data.getAll("activities").map(String),
        },
      ],
    });
    renderFamily(root, store.get());
    document.getElementById("main").focus();
  });
  return form;
}

function checkboxGroup(legend, name, options, selected = []) {
  return h(
    "fieldset",
    { class: "field" },
    h("legend", {}, legend),
    Object.entries(options).map(([value, label]) =>
      h("label", { class: "choice" }, h("input", { type: "checkbox", name, value, checked: selected.includes(value) }), label),
    ),
  );
}

function householdForm(state) {
  const hh = state.household;
  const ids = { mode: uid("mode"), km: uid("km"), days: uid("days"), dep: uid("dep"), ss: uid("ss"), se: uid("se"), fuel: uid("fuel") };
  const status = h("p", { role: "status", class: "card__meta" });
  const form = h(
    "form",
    { class: "card section", "aria-labelledby": "hh-title", novalidate: true },
    h("h2", { id: "hh-title", class: "card__title" }, "Home and travel"),
    h("p", { class: "field__hint" }, "Optional. Used for commute timing, school planning and lower-emission suggestions."),
    h(
      "fieldset",
      { class: "field" },
      h("legend", {}, "Daily commute"),
      h(
        "div",
        { class: "form-grid" },
        field(ids.mode, "Mode", h("select", { id: ids.mode, name: "mode" }, h("option", { value: "" }, "No regular commute"), Object.entries(MODE_LABELS).map(([v, l]) => h("option", { value: v, selected: hh.commute?.mode === v }, l)))),
        field(ids.km, "Distance one way (km)", h("input", { id: ids.km, name: "distance_km", type: "number", min: "0.5", max: "200", step: "0.5", value: hh.commute?.distance_km ?? "" })),
        field(ids.days, "Days per week", h("input", { id: ids.days, name: "days_per_week", type: "number", min: "1", max: "7", value: hh.commute?.days_per_week ?? 5 })),
        field(ids.dep, "Usual departure hour (0–23)", h("input", { id: ids.dep, name: "depart_hour", type: "number", min: "0", max: "23", value: hh.commute?.depart_hour ?? 9 })),
      ),
    ),
    h(
      "fieldset",
      { class: "field" },
      h("legend", {}, "School hours (if children attend school)"),
      h(
        "div",
        { class: "form-grid" },
        field(ids.ss, "Starts at hour", h("input", { id: ids.ss, name: "school_start", type: "number", min: "5", max: "12", value: hh.school?.start_hour ?? "" })),
        field(ids.se, "Ends at hour", h("input", { id: ids.se, name: "school_end", type: "number", min: "10", max: "20", value: hh.school?.end_hour ?? "" })),
      ),
    ),
    h(
      "fieldset",
      { class: "field" },
      h("legend", {}, "Home"),
      h("label", { class: "choice" }, h("input", { type: "checkbox", name: "has_purifier", checked: hh.home.has_purifier }), "We have an air purifier"),
      field(ids.fuel, "Cooking fuel", h("select", { id: ids.fuel, name: "cooking_fuel" }, Object.entries(FUELS).map(([v, l]) => h("option", { value: v, selected: hh.home.cooking_fuel === v }, l)))),
    ),
    status,
    h("div", { class: "actions" }, h("button", { type: "submit", class: "btn btn--primary" }, "Save home and travel")),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const d = new FormData(form);
    const num = (k) => (d.get(k) === "" || d.get(k) === null ? null : Number(d.get(k)));
    const mode = String(d.get("mode") || "");
    const km = num("distance_km");
    if (mode && mode !== "wfh" && !(km > 0 && km <= 200)) {
      status.textContent = "Enter a commute distance between 0.5 and 200 km.";
      return;
    }
    const start = num("school_start");
    const end = num("school_end");
    store.update({
      household: {
        commute: mode && mode !== "wfh" ? { mode, distance_km: km, days_per_week: clamp(num("days_per_week") ?? 5, 1, 7), depart_hour: clamp(num("depart_hour") ?? 9, 0, 23) } : null,
        school: start !== null && end !== null && end > start ? { start_hour: clamp(start, 5, 12), end_hour: clamp(end, 10, 20) } : null,
        home: { has_purifier: d.get("has_purifier") !== null, cooking_fuel: String(d.get("cooking_fuel")), smoker_at_home: false },
      },
    });
    status.textContent = "Saved.";
  });
  return form;
}

function field(id, label, control) {
  return h("div", { class: "field" }, h("label", { for: id }, label), control);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Math.round(value)));
}
