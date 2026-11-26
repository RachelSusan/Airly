// Smart Daily Routine Planner + per-member protection checklists.
import { api } from "../api.js";
import { h, render } from "../dom.js";
import { householdPayload, membersPayload, store } from "../store.js";
import { adviceBadge, categoryBadge, MODE_LABELS, riskBadge, sourceBadge } from "../format.js";

const REFRESH_MS = 30 * 60 * 1000;
let lastPlan = null;
let refreshTimer = null;

export function renderPlanner(root, state) {
  clearInterval(refreshTimer);
  if (!state.members.length) {
    render(
      root,
      h(
        "div",
        { class: "empty-state" },
        h("p", {}, "Add your family first so the plan fits everyone."),
        h("a", { class: "btn btn--primary", href: "#family" }, "Add family members"),
      ),
    );
    return;
  }
  const output = h("div", { "aria-live": "polite" });
  const button = h("button", { type: "button", class: "btn btn--primary", onclick: () => load(output, button) }, "Make today's plan");
  render(
    root,
    h("p", {}, "BreatheWise reads the live forecast and your family profiles, then plans the cleanest times for each activity."),
    h("div", { class: "actions" }, button),
    output,
  );
  if (lastPlan) render(output, planView(lastPlan, null));
  refreshTimer = setInterval(() => {
    if (document.visibilityState === "visible" && location.hash === "#planner") load(output, button);
  }, REFRESH_MS);
}

async function load(output, button) {
  const state = store.get();
  button.disabled = true;
  button.textContent = "Planning…";
  output.setAttribute("aria-busy", "true");
  try {
    const plan = await api.plan({
      location: { lat: state.location.lat, lon: state.location.lon },
      members: membersPayload(state.members),
      household: householdPayload(state.household),
    });
    const previous = lastPlan;
    lastPlan = plan;
    render(output, planView(plan, previous));
  } catch (error) {
    render(output, h("p", { class: "alert alert--error", role: "alert" }, error.message));
  } finally {
    button.disabled = false;
    button.textContent = "Refresh plan";
    output.removeAttribute("aria-busy");
  }
}

function planView(plan, previous) {
  const before = new Map((previous?.routine ?? []).map((r) => [r.activity, `${r.start}-${r.end}`]));
  const names = new Map(store.get().members.map((m) => [m.id, m.name || "Family member"]));
  return [
    h(
      "div",
      { class: "card section" },
      h("p", { class: "item-row" }, sourceBadge(plan.source), h("span", { class: "card__meta" }, `Updated ${new Date(plan.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`)),
      h("p", { class: "aqi-value" }, h("strong", {}, `AQI ${plan.current.aqi}`), categoryBadge(categoryKey(plan.current.category), plan.current.category)),
      h("p", {}, plan.summary),
    ),
    section(
      "Your routine",
      plan.routine.map((r) => {
        const changed = previous && before.get(r.activity) !== `${r.start}-${r.end}`;
        return h(
          "li",
          { class: "card" },
          h("div", { class: "item-row" }, h("h3", { class: "card__title" }, `${r.activity}: ${r.start}–${r.end}`), adviceBadge(r.advice)),
          changed ? h("p", { class: "tag-updated" }, "Updated: the forecast changed") : null,
          h("p", { class: "why" }, r.why),
          r.impact ? h("p", { class: "impact" }, r.impact) : null,
        );
      }),
    ),
    plan.commute ? commuteCard(plan.commute) : null,
    plan.school.length
      ? section(
          "School activities",
          plan.school.map((s) =>
            h("li", { class: "card" }, h("div", { class: "item-row" }, h("strong", {}, s.slot), adviceBadge(s.advice)), s.alternative ? h("p", {}, `Instead: ${s.alternative}`) : null),
          ),
        )
      : null,
    section("Indoor air", plan.indoor_tips.map(tipItem)),
    section("Lower-emission choices", plan.sustainable_choices.map(tipItem)),
    h(
      "section",
      { class: "section", "aria-labelledby": "members-title" },
      h("h2", { id: "members-title" }, "Family protection checklists"),
      h("div", { class: "grid grid--2" }, plan.members.map((m) => memberCard(m, names.get(m.member_id)))),
    ),
  ];
}

function categoryKey(label) {
  return String(label).toLowerCase().replace(" ", "_");
}

function section(title, items) {
  if (!items.length) return null;
  const id = `sec-${title.replace(/\W+/g, "-").toLowerCase()}`;
  return h("section", { class: "section", "aria-labelledby": id }, h("h2", { id }, title), h("ul", { class: "plain-list" }, items));
}

function tipItem(t) {
  return h("li", { class: "card" }, h("h3", { class: "card__title" }, t.tip), t.why ? h("p", { class: "why" }, t.why) : null, t.impact ? h("p", { class: "impact" }, t.impact) : null);
}

function commuteCard(c) {
  return h(
    "section",
    { class: "section card", "aria-labelledby": "commute-title" },
    h("h2", { id: "commute-title", class: "card__title" }, `Commute: leave around ${c.recommended_departure}`),
    h("p", { class: "why" }, c.why),
    c.alternative_mode ? h("p", {}, h("strong", {}, "Try: "), MODE_LABELS[c.alternative_mode] ?? c.alternative_mode) : null,
    c.alternative_impact ? h("p", { class: "impact" }, c.alternative_impact) : null,
  );
}

function memberCard(m, name) {
  const progress = h("p", { class: "progress", role: "status" });
  const update = () => {
    const done = m.checklist.filter((item) => store.isChecked(m.member_id, item.id)).length;
    progress.textContent = `${done} of ${m.checklist.length} done`;
  };
  const card = h(
    "article",
    { class: "card", "aria-label": `${name} checklist` },
    h("div", { class: "item-row" }, h("h3", { class: "card__title" }, name), riskBadge(m.risk_level)),
    m.alerts.map((a) => h("p", { class: "alert", role: "status" }, a)),
    h(
      "ul",
      { class: "checklist" },
      m.checklist.map((item) => {
        const box = h("input", {
          type: "checkbox",
          checked: store.isChecked(m.member_id, item.id),
          onchange: (e) => {
            store.toggleChecklist(m.member_id, item.id, e.target.checked);
            update();
          },
        });
        return h("li", {}, h("label", {}, box, h("span", {}, item.text, h("span", { class: "checklist__reason" }, item.reason))));
      }),
    ),
    progress,
  );
  update();
  return card;
}
