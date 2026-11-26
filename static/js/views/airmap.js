// Air map: a smooth, colour-graded pollution layer around the user (interpolated from the
// modelled grid), plus an optional layer of other Indian cities coloured by live AQI.
import { api } from "../api.js";
import { CITIES } from "../cities.js";
import { h, render } from "../dom.js";
import { CATEGORY_LABELS, categoryBadge } from "../format.js";

const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services";
const BASEMAPS = {
  satellite: {
    url: `${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
    labels: `${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`,
    attribution: "Imagery © Esri, Maxar, Earthstar Geographics · Labels © Esri",
  },
  streets: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "© OpenStreetMap contributors",
  },
};
const KM_PER_DEG = 111;
const LEGEND = ["good", "satisfactory", "moderate", "poor", "very_poor", "severe"];
const INDIA_BOUNDS = [
  [6.5, 68.0],
  [35.7, 97.5],
];

// AQI -> colour stops (same hues as the AQI badges), blended smoothly between stops.
const COLOUR_STOPS = [
  [0, [46, 158, 91]],
  [50, [46, 158, 91]],
  [100, [139, 195, 74]],
  [200, [242, 194, 0]],
  [300, [240, 140, 0]],
  [400, [217, 48, 37]],
  [500, [126, 31, 59]],
];
const OVERLAY_PX = 220;
const OVERLAY_ALPHA = 0.5;

let activeMap = null;

/** Section with the map, controls, an accessible legend and a text summary. */
export function airMapSection(state) {
  const mapEl = h("div", {
    class: "air-map",
    role: "region",
    tabindex: "0",
    "aria-label": `Map of modelled air quality around ${state.location.name}. Use arrow keys to pan and plus or minus to zoom.`,
  });
  const summary = h("div", { "aria-live": "polite" }, h("p", { class: "card__meta" }, "Loading the map…"));
  const cityPanel = h("div", { "aria-live": "polite" });
  const toggle = h(
    "button",
    { type: "button", class: "btn btn--outline btn--small", "aria-pressed": "false", disabled: true },
    "Show other cities",
  );
  const section = h(
    "section",
    { class: "section card", "aria-labelledby": "map-title" },
    h(
      "div",
      { class: "item-row map-head" },
      h("div", {}, h("p", { class: "eyebrow" }, "Live map"), h("h2", { id: "map-title", class: "card__title" }, "Air around you")),
      toggle,
    ),
    mapEl,
    legend(),
    summary,
    cityPanel,
  );
  loadMap({ mapEl, summary, cityPanel, toggle, location: state.location });
  return section;
}

function legend() {
  return h(
    "div",
    { class: "map-legend" },
    h("div", { class: "map-legend__scale", "aria-hidden": "true" }),
    h(
      "ul",
      { class: "map-legend__labels", "aria-label": "Map colour key" },
      LEGEND.map((cat) => h("li", {}, CATEGORY_LABELS[cat])),
    ),
  );
}

async function loadMap({ mapEl, summary, cityPanel, toggle, location }) {
  if (activeMap) {
    activeMap.remove();
    activeMap = null;
  }
  let grid;
  try {
    grid = await api.grid(location);
  } catch (error) {
    render(summary, h("p", { class: "alert alert--error", role: "alert" }, error.message));
    mapEl.hidden = true;
    return;
  }
  renderSummary(summary, grid, location);
  if (!window.L) {
    mapEl.hidden = true; // map library unavailable (offline); the text summary still works
    return;
  }
  const L = window.L;
  const map = L.map(mapEl, { scrollWheelZoom: false, zoomControl: true, attributionControl: true });
  activeMap = map;
  // Place names sit above the colour layer so they stay readable.
  const labelPane = map.createPane("labels");
  labelPane.style.zIndex = "450";
  labelPane.style.pointerEvents = "none";
  const satellite = L.layerGroup([
    L.tileLayer(BASEMAPS.satellite.url, { maxZoom: 17, attribution: BASEMAPS.satellite.attribution }),
    L.tileLayer(BASEMAPS.satellite.labels, { maxZoom: 17, pane: "labels" }),
  ]);
  const streets = L.tileLayer(BASEMAPS.streets.url, { maxZoom: 17, attribution: BASEMAPS.streets.attribution });
  satellite.addTo(map);
  L.control.layers({ Satellite: satellite, Streets: streets }, null, { position: "topright" }).addTo(map);

  const half = grid.step_deg / 2;
  const lats = grid.cells.map((c) => c.lat);
  const lons = grid.cells.map((c) => c.lon);
  const bounds = [
    [Math.min(...lats) - half, Math.min(...lons) - half],
    [Math.max(...lats) + half, Math.max(...lons) + half],
  ];
  L.imageOverlay(heatImage(grid.cells, bounds, grid.step_deg), bounds, { opacity: 1, interactive: false, className: "air-heat" }).addTo(map);

  L.circleMarker([location.lat, location.lon], {
    radius: 9,
    color: "#181818",
    weight: 3,
    fillColor: "#ffffff",
    fillOpacity: 1,
  })
    .bindPopup(youPopup(grid.cells, location))
    .addTo(map);
  const local = bounds;
  map.fitBounds(local, { padding: [12, 12] });

  // Tap anywhere on the shaded area to read the nearest modelled value.
  map.on("click", (event) => {
    const cell = nearestCell(grid.cells, event.latlng.lat, event.latlng.lng);
    if (cell && withinBounds(local, event.latlng)) {
      L.popup().setLatLng(event.latlng).setContent(cellPopup(cell, "Modelled air here")).openOn(map);
    }
  });

  let cityLayer = null;
  toggle.disabled = false;
  toggle.addEventListener("click", async () => {
    const showing = toggle.getAttribute("aria-pressed") === "true";
    if (showing) {
      cityLayer?.remove();
      toggle.setAttribute("aria-pressed", "false");
      toggle.textContent = "Show other cities";
      render(cityPanel);
      map.fitBounds(local, { padding: [12, 12] });
      return;
    }
    toggle.disabled = true;
    toggle.textContent = "Loading cities…";
    try {
      cityLayer = cityLayer ?? (await buildCityLayer(L, cityPanel));
      cityLayer.addTo(map);
      map.fitBounds(INDIA_BOUNDS);
      toggle.setAttribute("aria-pressed", "true");
      toggle.textContent = "Hide other cities";
    } catch (error) {
      render(cityPanel, h("p", { class: "alert alert--error", role: "alert" }, error.message));
      toggle.textContent = "Show other cities";
    } finally {
      toggle.disabled = false;
    }
  });
}

// ---------------------------------------------------------------- smooth overlay

/** Paint a smooth AQI surface onto a canvas, fading out at the edges. */
function heatImage(cells, bounds, step) {
  const sigma = step * 0.9;
  const [[south, west], [north, east]] = bounds;
  const canvas = document.createElement("canvas");
  canvas.width = OVERLAY_PX;
  canvas.height = OVERLAY_PX;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(OVERLAY_PX, OVERLAY_PX);
  for (let y = 0; y < OVERLAY_PX; y += 1) {
    const lat = north - ((y + 0.5) / OVERLAY_PX) * (north - south);
    for (let x = 0; x < OVERLAY_PX; x += 1) {
      const lon = west + ((x + 0.5) / OVERLAY_PX) * (east - west);
      const aqi = interpolateAqi(cells, lat, lon, sigma);
      const [r, g, b] = colourFor(aqi);
      // Soft round fade so the layer blends into the map with no visible box.
      const dx = (x + 0.5) / OVERLAY_PX - 0.5;
      const dy = (y + 0.5) / OVERLAY_PX - 0.5;
      const fade = Math.min(1, Math.max(0, (0.5 - Math.hypot(dx, dy)) / 0.22));
      const alpha = OVERLAY_ALPHA * smoothstep(fade);
      const i = (y * OVERLAY_PX + x) * 4;
      img.data[i] = r;
      img.data[i + 1] = g;
      img.data[i + 2] = b;
      img.data[i + 3] = Math.round(alpha * 255);
    }
  }
  ctx.putImageData(img, 0, 0);
  return canvas.toDataURL("image/png");
}

/** Gaussian-weighted average of nearby cells: a smooth surface with no hard edges. */
function interpolateAqi(cells, lat, lon, sigma) {
  let weighted = 0;
  let total = 0;
  const k = 1 / (2 * sigma * sigma);
  for (const c of cells) {
    const w = Math.exp(-((c.lat - lat) ** 2 + (c.lon - lon) ** 2) * k);
    weighted += w * c.aqi;
    total += w;
  }
  return total > 0 ? weighted / total : cells[0].aqi;
}

function colourFor(aqi) {
  const value = Math.max(0, Math.min(500, aqi));
  for (let i = 1; i < COLOUR_STOPS.length; i += 1) {
    const [hi, cHi] = COLOUR_STOPS[i];
    const [lo, cLo] = COLOUR_STOPS[i - 1];
    if (value <= hi) {
      const t = hi === lo ? 0 : (value - lo) / (hi - lo);
      return cLo.map((v, k) => Math.round(v + (cHi[k] - v) * t));
    }
  }
  return COLOUR_STOPS[COLOUR_STOPS.length - 1][1];
}

function colourCss(aqi) {
  const [r, g, b] = colourFor(aqi);
  return `rgb(${r} ${g} ${b})`;
}

function smoothstep(t) {
  return t * t * (3 - 2 * t);
}

function nearestCell(cells, lat, lon) {
  let best = null;
  let bestD = Infinity;
  for (const c of cells) {
    const d = (c.lat - lat) ** 2 + (c.lon - lon) ** 2;
    if (d < bestD) {
      bestD = d;
      best = c;
    }
  }
  return best;
}

function withinBounds([[s, w], [n, e]], latlng) {
  return latlng.lat >= s && latlng.lat <= n && latlng.lng >= w && latlng.lng <= e;
}

// ---------------------------------------------------------------- other cities

async function buildCityLayer(L, cityPanel) {
  const { cells } = await api.points(CITIES.map((c) => ({ lat: c.lat, lon: c.lon })));
  const rows = CITIES.map((city, i) => ({ city, cell: cells[i] })).filter((r) => r.cell);
  const layer = L.layerGroup();
  for (const { city, cell } of rows) {
    L.circleMarker([city.lat, city.lon], {
      radius: 8,
      color: "#ffffff",
      weight: 2,
      fillColor: colourCss(cell.aqi),
      fillOpacity: 0.95,
    })
      .bindTooltip(h("span", {}, `${city.city}: AQI ${cell.aqi}`), { direction: "top" })
      .bindPopup(cellPopup(cell, `${city.city}, ${city.state}`))
      .addTo(layer);
  }
  renderCityTable(cityPanel, rows);
  return layer;
}

function renderCityTable(panel, rows) {
  const sorted = [...rows].sort((a, b) => a.cell.aqi - b.cell.aqi);
  const cleanest = sorted.slice(0, 3).map((r) => r.city.city).join(", ");
  const worst = sorted.slice(-3).reverse().map((r) => r.city.city).join(", ");
  render(
    panel,
    h("p", {}, `Across ${rows.length} Indian cities right now, the cleanest air is in ${cleanest}; the most polluted is in ${worst}.`),
    h(
      "details",
      {},
      h("summary", {}, "Show all cities as a table"),
      h(
        "div",
        { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "City air quality table" },
        h(
          "table",
          {},
          h("caption", {}, "Current AQI by city (modelled)"),
          h("thead", {}, h("tr", {}, ["City", "State", "AQI", "Category"].map((t) => h("th", { scope: "col" }, t)))),
          h(
            "tbody",
            {},
            sorted.map(({ city, cell }) =>
              h("tr", {}, h("th", { scope: "row" }, city.city), h("td", {}, city.state), h("td", {}, cell.aqi), h("td", {}, categoryBadge(cell.category, cell.label))),
            ),
          ),
        ),
      ),
    ),
  );
}

// ---------------------------------------------------------------- popups and summary

function cellPopup(cell, title) {
  return h(
    "div",
    { class: "map-popup" },
    h("strong", {}, title),
    h("span", {}, `AQI ${cell.aqi} `, categoryBadge(cell.category, cell.label)),
    cell.pm2_5 !== null ? h("span", { class: "muted small" }, `PM2.5: ${Math.round(cell.pm2_5)} µg/m³`) : null,
  );
}

function youPopup(cells, location) {
  const cell = nearestCell(cells, location.lat, location.lon);
  return cell ? cellPopup(cell, "You are here") : h("strong", {}, "You are here");
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
    h("p", { class: "card__meta" }, `${data.note} Tap the map to read a value.`),
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
