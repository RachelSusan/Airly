// Client-side state. Family profiles never leave this device except in the requests that need them.

const KEY = "breathewise:v1";
const VERSION = 1;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function defaults() {
  return {
    version: VERSION,
    location: null,
    members: [],
    household: {
      commute: null,
      school: null,
      home: { has_purifier: false, cooking_fuel: "lpg", smoker_at_home: false },
    },
    checklist: { date: today(), done: {} },
  };
}

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaults();
    const parsed = JSON.parse(raw);
    if (parsed?.version !== VERSION) return defaults();
    const state = { ...defaults(), ...parsed };
    if (state.checklist?.date !== today()) state.checklist = { date: today(), done: {} };
    return state;
  } catch {
    return defaults();
  }
}

let state = load();
const listeners = new Set();

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // storage unavailable (private mode): the app still works for this session
  }
}

export const store = {
  get: () => state,
  update(patch) {
    state = { ...state, ...patch };
    persist();
    listeners.forEach((fn) => fn(state));
  },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
  clear() {
    try {
      localStorage.removeItem(KEY);
    } catch {
      // ignore
    }
    state = defaults();
    listeners.forEach((fn) => fn(state));
  },
  toggleChecklist(memberId, itemId, done) {
    const checklist = state.checklist.date === today() ? state.checklist : { date: today(), done: {} };
    const items = new Set(checklist.done[memberId] ?? []);
    if (done) items.add(itemId);
    else items.delete(itemId);
    state = { ...state, checklist: { ...checklist, done: { ...checklist.done, [memberId]: [...items] } } };
    persist();
  },
  isChecked(memberId, itemId) {
    return (state.checklist.done[memberId] ?? []).includes(itemId);
  },
};

/** Household payload for the API, dropping incomplete optional parts. */
export function householdPayload(household) {
  const out = { home: household.home };
  if (household.commute) out.commute = household.commute;
  if (household.school) out.school = household.school;
  return out;
}

/** Members payload for the API (only the fields the server accepts). */
export function membersPayload(members) {
  return members.map(({ id, name, age_group, conditions, outdoor_activities }) => ({
    id,
    name: name || null,
    age_group,
    conditions,
    outdoor_activities,
  }));
}
