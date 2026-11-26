// App shell: routing, location search and view rendering.
import { api } from "./api.js";
import { CITIES, COUNTRY, findCity, nearestCity } from "./cities.js";
import { h, render } from "./dom.js";
import { mountScene, updateScene } from "./scene.js";
import { store } from "./store.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderPlanner } from "./views/planner.js";
import { renderFamily } from "./views/family.js";
import { renderAssistant } from "./views/assistant.js";
import { renderSimulator } from "./views/simulator.js";

const VIEWS = {
  dashboard: { title: "Air now", render: renderDashboard, needsLocation: true },
  planner: { title: "Today's plan", render: renderPlanner, needsLocation: true },
  family: { title: "Family profiles", render: renderFamily, needsLocation: false },
  assistant: { title: "Ask BreatheWise", render: renderAssistant, needsLocation: true },
  simulator: { title: "What if? Pollution simulator", render: renderSimulator, needsLocation: false },
};

const viewEl = document.getElementById("view");
const titleEl = document.getElementById("view-title");
const statusEl = document.getElementById("location-status");
const resultsEl = document.getElementById("city-results");

function viewName() {
  const name = location.hash.replace("#", "");
  return name in VIEWS ? name : "dashboard";
}

function showView({ focus = false } = {}) {
  const name = viewName();
  const view = VIEWS[name];
  titleEl.textContent = view.title;
  document.title = `${view.title} · BreatheWise`;
  document.querySelectorAll(".tabs__link").forEach((link) => {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  const state = store.get();
  showLocationChip(view.needsLocation ? state.location : null);
  if (view.needsLocation && !state.location) {
    render(
      viewEl,
      h(
        "div",
        { class: "empty-state" },
        h("p", {}, "Choose your city above to see live air quality for where you are."),
      ),
    );
  } else {
    view.render(viewEl, state);
  }
  if (focus) document.getElementById("main").focus();
}

/** Show which location this view uses, with a quick way to change it. */
function showLocationChip(loc) {
  const chip = document.getElementById("view-location");
  if (!loc) {
    chip.hidden = true;
    render(chip);
    return;
  }
  render(
    chip,
    h("span", { class: "view-location__pin", "aria-hidden": "true" }, "📍"),
    h("span", {}, `Using live data for ${locationLabel(loc)}`),
    h(
      "button",
      {
        type: "button",
        class: "btn btn--ghost btn--small",
        onclick: () => document.getElementById("city-input").focus(),
      },
      "Change location",
    ),
  );
  chip.hidden = false;
}

/** Human-readable label; GPS locations are described by the nearest listed city. */
function locationLabel(loc) {
  if (!loc.gps) return loc.name;
  return loc.near ? `your location near ${loc.near}` : "your location";
}

function setLocation(loc) {
  store.update({ location: loc });
  updateScene({ city: loc.name, nearYou: Boolean(loc.gps) });
  statusEl.textContent = `Showing air quality for ${locationLabel(loc)}.`;
  const select = document.getElementById("city-select");
  select.value = CITIES.some((c) => c.name === loc.name) && !loc.gps ? loc.name : "";
  render(resultsEl);
  resultsEl.hidden = true;
  showView();
}

async function searchCity(event) {
  event.preventDefault();
  const input = document.getElementById("city-input");
  const query = input.value.trim();
  if (query.length < 2) {
    statusEl.textContent = "Type at least 2 letters of your city name.";
    input.focus();
    return;
  }
  const listed = findCity(query);
  if (listed) {
    setLocation(cityToLocation(listed));
    return;
  }
  statusEl.textContent = "Searching…";
  try {
    const { results } = await api.geocode(query, COUNTRY.code);
    if (!results.length) {
      statusEl.textContent = `No places found for "${query}". Check the spelling and try again.`;
      return;
    }
    if (results.length === 1) {
      setLocation(placeToLocation(results[0]));
      return;
    }
    statusEl.textContent = `${results.length} places found. Choose one.`;
    render(
      resultsEl,
      results.map((place) =>
        h(
          "li",
          {},
          h(
            "button",
            {
              type: "button",
              class: "btn btn--secondary",
              onclick: () => setLocation(placeToLocation(place)),
            },
            placeLabel(place),
          ),
        ),
      ),
    );
    resultsEl.hidden = false;
    resultsEl.querySelector("button")?.focus();
  } catch (error) {
    statusEl.textContent = error.message;
  }
}

function placeLabel(place) {
  return [place.name, place.admin, place.country].filter(Boolean).join(", ");
}

function placeToLocation(place) {
  return { name: placeLabel(place), lat: place.lat, lon: place.lon };
}

function cityToLocation(city) {
  return { name: city.name, lat: city.lat, lon: city.lon };
}

/** Location object for GPS coordinates, named after the nearest listed city if close. */
function gpsLocation(lat, lon) {
  const near = nearestCity(lat, lon);
  return { name: near ? near.name : "Your area", lat, lon, gps: true, near: near?.city ?? null };
}

function setupCityPicker() {
  const select = document.getElementById("city-select");
  const datalist = document.getElementById("city-suggestions");
  for (const city of CITIES) {
    select.append(h("option", { value: city.name }, `${city.city}, ${city.state}`));
    datalist.append(h("option", { value: city.name }));
  }
  select.addEventListener("change", () => {
    const city = CITIES.find((c) => c.name === select.value);
    if (city) {
      document.getElementById("city-input").value = "";
      setLocation(cityToLocation(city));
    }
  });
}

function useMyLocation() {
  if (!("geolocation" in navigator)) {
    statusEl.textContent = "Location isn't available in this browser. Search for your city instead.";
    return;
  }
  statusEl.textContent = "Finding your location…";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = Math.round(pos.coords.latitude * 100) / 100;
      const lon = Math.round(pos.coords.longitude * 100) / 100;
      setLocation(gpsLocation(lat, lon));
    },
    () => {
      statusEl.textContent = "Couldn't get your location. Search for your city instead.";
    },
    { maximumAge: 600000, timeout: 10000 },
  );
}

function init() {
  mountScene(document.getElementById("scene"));
  setupCityPicker();
  document.getElementById("location-form").addEventListener("submit", searchCity);
  document.getElementById("geo-button").addEventListener("click", useMyLocation);
  window.addEventListener("hashchange", () => showView({ focus: true }));
  let loc = store.get().location;
  if (loc && loc.name === "your location") {
    loc = gpsLocation(loc.lat, loc.lon); // upgrade locations saved by an older version
    store.update({ location: loc });
  }
  if (loc) {
    updateScene({ city: loc.name, nearYou: Boolean(loc.gps) });
    const listed = CITIES.some((c) => c.name === loc.name) && !loc.gps;
    document.getElementById("city-select").value = listed ? loc.name : "";
    document.getElementById("city-input").value = listed || loc.gps ? "" : loc.name;
    statusEl.textContent = `Showing air quality for ${locationLabel(loc)}.`;
  }
  showView();
}

init();
