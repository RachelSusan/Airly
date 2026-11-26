// Family Protection Profiles: each member has their own relationship, health, activities,
// travel and school routine. Stored only in this browser.
import { confirmAction, h, render, uid } from "../dom.js";
import {
  AGE_LABELS,
  CONDITION_LABELS,
  MODE_LABELS,
  RELATIONSHIP_LABELS,
  roleLabel,
} from "../format.js";
import { store } from "../store.js";

const MAX_MEMBERS = 10;
const ACTIVITIES = { walking: "Walking", jogging: "Jogging", cycling: "Cycling", play: "Outdoor play", sports: "Sports" };
const FUELS = { lpg: "LPG", png: "Piped gas", electric: "Electric", biomass: "Wood / dung", kerosene: "Kerosene" };

let editingId = null;

export function renderFamily(root, state) {
  render(
    root,
    h("p", { class: "lead" }, "Add each person in your family with how they travel and their school or college hours. The day planner then gives everyone their own advice. Profiles stay on this device."),
    membersSection(root, state),
    memberForm(root, state.members.find((m) => m.id === editingId) ?? null),
    homeForm(state),
    h(
      "section",
      { class: "section", "aria-labelledby": "privacy-title" },
      h("h2", { id: "privacy-title" }, "Your data"),
      h("p", { class: "muted" }, "Profiles are never stored on our server."),
      h(
        "button",
        {
          type: "button",
          class: "btn btn--outline",
          onclick: async () => {
            if (await confirmAction("This removes your city, family profiles and checklist from this device.", "Clear my data")) {
              editingId = null;
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

// ---------------------------------------------------------------- member list

function membersSection(root, state) {
  return h(
    "section",
    { "aria-labelledby": "members-list-title" },
    h("p", { class: "eyebrow" }, "Your family"),
    h("h2", { id: "members-list-title" }, `${state.members.length} ${state.members.length === 1 ? "member" : "members"}`),
    state.members.length
      ? h("ul", { class: "grid grid--3 plain-list" }, state.members.map((m) => memberCard(root, m)))
      : h("p", { class: "empty-state" }, "No family members yet. Add the first one below."),
  );
}

function memberCard(root, m) {
  const label = m.name || RELATIONSHIP_LABELS[m.relationship] || "Family member";
  return h(
    "li",
    { class: "card member-card" },
    h(
      "div",
      { class: "member-card__head" },
      h("span", { class: "avatar", "aria-hidden": "true" }, initials(label)),
      h("div", {}, h("h3", { class: "card__title" }, label), h("p", { class: "muted small" }, roleLabel(m))),
    ),
    h(
      "dl",
      { class: "facts" },
      fact("Health", m.conditions?.length ? m.conditions.map((c) => CONDITION_LABELS[c]).join(", ") : "No conditions listed"),
      fact("Outdoors", m.outdoor_activities?.length ? m.outdoor_activities.map((a) => ACTIVITIES[a] ?? a).join(", ") : "Not set"),
      fact("Travel", m.commute ? `${MODE_LABELS[m.commute.mode]}, ${m.commute.distance_km} km each way, ${m.commute.days_per_week} days/week, leaves ${pad(m.commute.depart_hour)}:00` : "No regular trip"),
      fact("School / college", m.school ? `${pad(m.school.start_hour)}:00–${pad(m.school.end_hour)}:00` : "—"),
    ),
    h(
      "div",
      { class: "actions" },
      h(
        "button",
        {
          type: "button",
          class: "btn btn--outline btn--small",
          "aria-label": `Edit ${label}`,
          onclick: () => {
            editingId = m.id;
            renderFamily(root, store.get());
            document.getElementById("member-form-title")?.scrollIntoView({ behavior: "smooth", block: "start" });
            document.querySelector("#member-form input")?.focus();
          },
        },
        "Edit",
      ),
      h(
        "button",
        {
          type: "button",
          class: "btn btn--ghost btn--small",
          "aria-label": `Remove ${label}`,
          onclick: async () => {
            if (await confirmAction(`Remove ${label} from your family?`, "Remove")) {
              if (editingId === m.id) editingId = null;
              store.update({ members: store.get().members.filter((x) => x.id !== m.id) });
              renderFamily(root, store.get());
            }
          },
        },
        "Remove",
      ),
    ),
  );
}

function fact(term, value) {
  return h("div", {}, h("dt", {}, term), h("dd", {}, value));
}

// ---------------------------------------------------------------- add / edit form

function memberForm(root, member) {
  const ids = {
    name: uid("name"), rel: uid("rel"), age: uid("age"),
    mode: uid("mode"), km: uid("km"), days: uid("days"), dep: uid("dep"),
    ss: uid("ss"), se: uid("se"),
  };
  const error = h("p", { class: "field__error", role: "alert" });
  const c = member?.commute;
  const sc = member?.school;
  const form = h(
    "form",
    { id: "member-form", class: "card card--panel section", "aria-labelledby": "member-form-title", novalidate: true },
    h("p", { class: "eyebrow" }, member ? "Edit member" : "Add a member"),
    h("h2", { id: "member-form-title" }, member ? `Edit ${member.name || "family member"}` : "Add a family member"),

    h("h3", { class: "form-section" }, "About"),
    h(
      "div",
      { class: "form-grid" },
      field(ids.name, "Name or nickname (optional)", h("input", { id: ids.name, name: "name", maxlength: "40", autocomplete: "off", value: member?.name ?? "" })),
      field(ids.rel, "Relationship to you", select(ids.rel, "relationship", RELATIONSHIP_LABELS, member?.relationship ?? (store.get().members.length ? "spouse" : "self"))),
      field(ids.age, "Age group", select(ids.age, "age_group", AGE_LABELS, member?.age_group ?? "adult")),
    ),
    checkboxGroup("Health conditions", "conditions", CONDITION_LABELS, member?.conditions),
    checkboxGroup("Usual outdoor activities", "activities", ACTIVITIES, member?.outdoor_activities),

    h("h3", { class: "form-section" }, "Travel to work or college"),
    h(
      "div",
      { class: "form-grid" },
      field(ids.mode, "How they travel", h("select", { id: ids.mode, name: "mode" }, h("option", { value: "" }, "No regular trip"), Object.entries(MODE_LABELS).filter(([v]) => v !== "wfh").map(([v, l]) => h("option", { value: v, selected: c?.mode === v }, l)))),
      field(ids.km, "Distance one way (km)", h("input", { id: ids.km, name: "distance_km", type: "number", min: "0.5", max: "200", step: "0.5", value: c?.distance_km ?? "" })),
      field(ids.days, "Days per week", h("input", { id: ids.days, name: "days_per_week", type: "number", min: "1", max: "7", value: c?.days_per_week ?? 5 })),
      field(ids.dep, "Usually leaves at (hour, 0–23)", h("input", { id: ids.dep, name: "depart_hour", type: "number", min: "0", max: "23", value: c?.depart_hour ?? 9 })),
    ),

    h("h3", { class: "form-section" }, "School or college hours"),
    h(
      "div",
      { class: "form-grid" },
      field(ids.ss, "Starts at (hour)", h("input", { id: ids.ss, name: "school_start", type: "number", min: "5", max: "12", value: sc?.start_hour ?? "" })),
      field(ids.se, "Ends at (hour)", h("input", { id: ids.se, name: "school_end", type: "number", min: "10", max: "20", value: sc?.end_hour ?? "" })),
    ),

    error,
    h(
      "div",
      { class: "actions" },
      h("button", { type: "submit", class: "btn btn--primary" }, member ? "Save changes" : "Add member"),
      member
        ? h("button", { type: "button", class: "btn btn--ghost", onclick: () => { editingId = null; renderFamily(root, store.get()); } }, "Cancel")
        : null,
    ),
  );

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const members = store.get().members;
    if (!member && members.length >= MAX_MEMBERS) {
      error.textContent = `You can add up to ${MAX_MEMBERS} family members.`;
      return;
    }
    const d = new FormData(form);
    const num = (k) => (d.get(k) === "" || d.get(k) === null ? null : Number(d.get(k)));
    const mode = String(d.get("mode") || "");
    const km = num("distance_km");
    if (mode && !(km > 0 && km <= 200)) {
      error.textContent = "Enter a travel distance between 0.5 and 200 km, or choose “No regular trip”.";
      document.getElementById(ids.km).focus();
      return;
    }
    const start = num("school_start");
    const end = num("school_end");
    if ((start === null) !== (end === null) || (start !== null && end <= start)) {
      error.textContent = "Enter both school hours, with the end after the start, or leave both empty.";
      document.getElementById(ids.ss).focus();
      return;
    }
    const updated = {
      id: member?.id ?? `m_${Date.now().toString(36)}`,
      name: String(d.get("name") || "").trim().slice(0, 40),
      relationship: String(d.get("relationship")),
      age_group: String(d.get("age_group")),
      conditions: d.getAll("conditions").map(String),
      outdoor_activities: d.getAll("activities").map(String),
      commute: mode
        ? { mode, distance_km: km, days_per_week: clamp(num("days_per_week") ?? 5, 1, 7), depart_hour: clamp(num("depart_hour") ?? 9, 0, 23) }
        : null,
      school: start !== null ? { start_hour: clamp(start, 5, 12), end_hour: clamp(end, 10, 20) } : null,
    };
    store.update({ members: member ? members.map((m) => (m.id === member.id ? updated : m)) : [...members, updated] });
    editingId = null;
    renderFamily(root, store.get());
    document.getElementById("members-list-title")?.scrollIntoView({ behavior: "smooth" });
    document.getElementById("main").focus({ preventScroll: true });
  });
  return form;
}

// ---------------------------------------------------------------- shared home

function homeForm(state) {
  const home = state.household.home;
  const fuelId = uid("fuel");
  const status = h("p", { role: "status", class: "muted small" });
  const form = h(
    "form",
    { class: "card card--panel section", "aria-labelledby": "home-title", novalidate: true },
    h("p", { class: "eyebrow" }, "Shared by everyone"),
    h("h2", { id: "home-title" }, "Your home"),
    h("label", { class: "choice" }, h("input", { type: "checkbox", name: "has_purifier", checked: home.has_purifier }), "We have an air purifier"),
    field(fuelId, "Cooking fuel", select(fuelId, "cooking_fuel", FUELS, home.cooking_fuel)),
    status,
    h("div", { class: "actions" }, h("button", { type: "submit", class: "btn btn--primary" }, "Save home")),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const d = new FormData(form);
    store.update({
      household: {
        ...store.get().household,
        home: { has_purifier: d.get("has_purifier") !== null, cooking_fuel: String(d.get("cooking_fuel")), smoker_at_home: false },
      },
    });
    status.textContent = "Saved.";
  });
  return form;
}

// ---------------------------------------------------------------- helpers

function field(id, label, control) {
  return h("div", { class: "field" }, h("label", { for: id }, label), control);
}

function select(id, name, options, selected) {
  return h("select", { id, name }, Object.entries(options).map(([v, l]) => h("option", { value: v, selected: v === selected }, l)));
}

function checkboxGroup(legend, name, options, selected = []) {
  return h(
    "fieldset",
    { class: "field" },
    h("legend", {}, legend),
    h(
      "div",
      { class: "choices" },
      Object.entries(options).map(([value, label]) =>
        h("label", { class: "choice" }, h("input", { type: "checkbox", name, value, checked: (selected ?? []).includes(value) }), label),
      ),
    ),
  );
}

function initials(text) {
  return text.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Math.round(value)));
}
