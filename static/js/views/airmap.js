// Neighbourhood air map: modelled AQI grid around the user's location (Leaflet + OpenStreetMap).
import { api } from "../api.js";
import { h, render } from "../dom.js";
import { CATEGORY_LABELS, categoryBadge } from "../format.js";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const KM_PER_DEG = 111;
const LEGEND = ["good", "satisfactory", "moderate", "poor", "very_poor", "severe"];

let activeMap = null;

/** Section with the map, an accessible legend and a text summary. */
export function airMapSection(state) {
  const mapEl = h("div", {
    class: "air-map",
    role: "region",
    tabindex: "0",
    "aria-label": `Map of modelled air quality around ${state.location.name}. Use arrow keys to pan and plus or minus to zoom.`,
  });
  const summary = h("div", { "aria-live": "polite" }, h("p", { class: "card__meta" }, "Loading the map…"));
  const section = h(
    "section",
    { class: "section card", "aria-labelledby": "map-title" },
    h("h2", { id: "map-title", class: "card__title" }, "Air around you"),
    mapEl,
    h(
      "ul",
      { class: "map-legend", "aria-label": "Map legend" },
      LEGEND.map((cat) => h("li", {}, h("span", { class: `map-legend__swatch bar--${cat}`, "aria-hidden": "true" }), CATEGORY_LABELS[cat])),
      h("li", {}, h("span", { class: "map-legend__you", "aria-hidden": "true" }), "You are here"),
    ),
    summary,
  );
  loadMap(mapEl, summary, state.location);
  return section;
}

async function loadMap(mapEl, summary, location) {
  if (activeMap) {
    activeMap.remove();
    activeMap = null;
  }
  let data;
  try {
    data = await api.grid(location);
  } catch (error) {
    render(summary, h("p", { class: "alert alert--error", role: "alert" }, error.message));
    mapEl.hidden = true;
    return;
  }
  renderSummary(summary, data, location);
  if (!window.L) {
    mapEl.hidden = true;
    return; // map library unavailable (offline); the text summary still works
  }
  const L = window.L;
  const map = L.map(mapEl, { scrollWheelZoom: false, zoomControl: true, attributionControl: true });
  activeMap = map;
  L.tileLayer(TILE_URL, { maxZoom: 15, attribution: "© OpenStreetMap contributors" }).addTo(map);

  const styles = getComputedStyle(document.documentElement);
  const half = data.step_deg / 2;
  const bounds = [];
  for (const cell of data.cells) {
    const box = [
      [cell.lat - half, cell.lon - half],
      [cell.lat + half, cell.lon + half],
    ];
    bounds.push(...box);
    const color = styles.getPropertyValue(`--aqi-${cell.category.replace("_", "-")}`).trim() || "#888";
    L.rectangle(box, { color, weight: 1, fillColor: color, fillOpacity: 0.42 })
      .bindPopup(cellPopup(cell))
      .addTo(map);
  }
  L.circleMarker([location.lat, location.lon], {
    radius: 9,
    color: "#1f2d24",
    weight: 3,
    fillColor: "#ffffff",
    fillOpacity: 1,
  })
    .bindTooltip(h("span", {}, "You are here"), { permanent: false, direction: "top" })
    .addTo(map);
  map.fitBounds(bounds, { padding: [8, 8] });
}

function cellPopup(cell) {
  return h(
    "div",
    { class: "map-popup" },
    h("strong", {}, `AQI ${cell.aqi}`),
    " ",
    categoryBadge(cell.category, cell.label),
    cell.pm2_5 !== null ? h("div", {}, `PM2.5: ${Math.round(cell.pm2_5)} µg/m³`) : null,
  );
}

function renderSummary(summary, data, location) {
  const sorted = [...data.cells].sort((a, b) => a.aqi - b.aqi);
  const cleanest = sorted[0];
  const worst = sorted[sorted.length - 1];
  render(
    summary,
    h(
      "p",
      {},
      `Nearby, the cleanest air is ${describe(cleanest, location)} (AQI ${cleanest.aqi}, ${cleanest.label}) and the most polluted is ${describe(worst, location)} (AQI ${worst.aqi}, ${worst.label}).`,
    ),
    h("p", { class: "card__meta" }, data.note),
    data.stale ? h("p", { class: "card__meta" }, "Showing recently saved data.") : null,
  );
}

function describe(cell, origin) {
  const dLat = cell.lat - origin.lat;
  const dLon = (cell.lon - origin.lon) * Math.cos((origin.lat * Math.PI) / 180);
  const km = Math.round(Math.hypot(dLat, dLon) * KM_PER_DEG);
  if (km < 3) return "right where you are";
  const ns = dLat > 0.02 ? "north" : dLat < -0.02 ? "south" : "";
  const ew = dLon > 0.02 ? "east" : dLon < -0.02 ? "west" : "";
  return `about ${km} km ${[ns, ew].filter(Boolean).join("-")} of you`;
}
