// Client-side state. Family profiles never leave this device except in the requests that need them.

const KEY = "airly:v1";
const LEGACY_KEY = "breathewise:v1"; // the app was called BreatheWise before it became Airly
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
    let raw = localStorage.getItem(KEY);
    if (!raw) {
      // Carry over profiles saved under the old app name, once.
      raw = localStorage.getItem(LEGACY_KEY);
      if (raw) {
        localStorage.setItem(KEY, raw);
        localStorage.removeItem(LEGACY_KEY);
      }
    }
    if (!raw) return defaults();
    const parsed = JSON.parse(raw);
    if (parsed?.version !== VERSION) return defaults();
    const state = migrate({ ...defaults(), ...parsed });
    if (state.checklist?.date !== today()) state.checklist = { date: today(), done: {} };
    return state;
  } catch {
    return defaults();
  }
}

/**
 * Older versions stored one commute and one school timetable for the whole household.
 * Move them onto members: the commute to "self" (or the first adult), school to children.
 */
function migrate(state) {
  const { commute, school } = state.household ?? {};
  if (!commute && !school) return state;
  const members = state.members.map((m) => ({ ...m }));
  if (commute) {
    // Only someone old enough to commute; never an infant or child.
    const owner =
      members.find((m) => m.relationship === "self") ??
      members.find((m) => m.age_group === "adult") ??
      members.find((m) => ["teen", "senior"].includes(m.age_group));
    if (owner && !owner.commute) owner.commute = commute;
  }
  if (school) {
    members
      .filter((m) => ["child", "teen"].includes(m.age_group) && !m.school)
      .forEach((m) => {
        m.school = school;
      });
  }
  return { ...state, members, household: { ...state.household, commute: null, school: null } };
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
      localStorage.removeItem(LEGACY_KEY);
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
  return members.map((m) => ({
    id: m.id,
    name: m.name || null,
    relationship: m.relationship || "other",
    age_group: m.age_group,
    conditions: m.conditions ?? [],
    outdoor_activities: m.outdoor_activities ?? [],
    commute: m.commute ?? null,
    school: m.school ?? null,
  }));
}
