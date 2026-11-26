// AI Air Quality Assistant chat.
import { api } from "../api.js";
import { h, render, uid } from "../dom.js";
import { householdPayload, membersPayload, store } from "../store.js";

const MAX_HISTORY = 20;
const MAX_CHARS = 1000;
const QUICK_QUESTIONS = [
  "Is it safe to go jogging now?",
  "Can my children play outside today?",
  "Should I open my windows?",
  "When should I leave for work?",
  "What if I take the metro instead of driving?",
];
const TOOL_LABELS = {
  get_current_conditions: "current air",
  get_forecast_windows: "24-hour forecast",
  assess_family_risk: "family profiles",
  check_ventilation: "ventilation rules",
  estimate_commute_switch: "emission factors",
};

const history = [];

export function renderAssistant(root) {
  const inputId = uid("ask");
  const hintId = uid("hint");
  const log = h("ol", { class: "chat-log", role: "log", "aria-live": "polite", "aria-label": "Conversation" });
  const status = h("p", { role: "status", class: "card__meta" });
  const input = h("textarea", { id: inputId, name: "question", maxlength: String(MAX_CHARS), required: true, "aria-describedby": hintId, rows: "3" });
  const send = h("button", { type: "submit", class: "btn btn--primary" }, "Ask");
  const form = h(
    "form",
    { class: "chat", novalidate: true },
    h("label", { for: inputId, class: "field" }, h("strong", {}, "Ask about the air")),
    input,
    h("p", { id: hintId, class: "field__hint" }, "Press Enter to send, Shift+Enter for a new line."),
    h("div", { class: "actions" }, send),
  );

  const ask = async (question) => {
    const text = question.trim().slice(0, MAX_CHARS);
    if (!text || send.disabled) return;
    history.push({ role: "user", content: text });
    log.append(message({ role: "user", content: text }));
    input.value = "";
    send.disabled = true;
    status.textContent = "Airly is checking live data…";
    try {
      const state = store.get();
      const reply = await api.chat({
        messages: trimmedHistory(),
        context: {
          location: { lat: state.location.lat, lon: state.location.lon },
          members: membersPayload(state.members),
          household: householdPayload(state.household),
        },
      });
      const entry = { role: "assistant", content: reply.reply, tools: reply.tools_used, source: reply.source };
      history.push(entry);
      log.append(message(entry));
      status.textContent = "";
    } catch (error) {
      history.pop();
      status.textContent = error.message;
    } finally {
      send.disabled = false;
      log.scrollTop = log.scrollHeight;
      input.focus();
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    ask(input.value);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask(input.value);
    }
  });

  history.forEach((entry) => log.append(message(entry)));
  render(
    root,
    h("p", {}, "Answers use live air quality, the forecast and your family profiles."),
    h("div", { class: "chips", role: "group", "aria-label": "Suggested questions" }, QUICK_QUESTIONS.map((q) => h("button", { type: "button", class: "chip", onclick: () => ask(q) }, q))),
    h("div", { class: "section chat" }, log, status, form),
  );
}

function trimmedHistory() {
  let recent = history.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content }));
  while (recent.length && recent[0].role !== "user") recent = recent.slice(1);
  return recent;
}

function message(entry) {
  const tools = (entry.tools ?? []).map((t) => TOOL_LABELS[t] ?? t);
  let meta = null;
  if (entry.role === "assistant") {
    const basis = tools.length ? `Based on: ${tools.join(", ")}` : null;
    const source = entry.source === "rules" ? "Rule-based backup answer" : null;
    const text = [basis, source].filter(Boolean).join(" · ");
    meta = text ? h("span", { class: "msg__meta" }, text) : null;
  }
  return h(
    "li",
    { class: `msg msg--${entry.role}` },
    h("span", { class: "visually-hidden" }, entry.role === "user" ? "You said: " : "Airly: "),
    entry.content,
    meta,
  );
}
