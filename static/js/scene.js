// Animated city scene: a colourful skyline generated for each city, a landmark for some
// Indian cities, trees swaying in the breeze, drifting clouds and birds, and a smog haze whose
// thickness follows the live AQI. Pure SVG built with DOM APIs (no images, no HTML strings).

const NS = "http://www.w3.org/2000/svg";
const WIDTH = 1200;
const HEIGHT = 240;
const GROUND = 205;

const BUILDING_COLOURS = ["#e8a87c", "#f2c57c", "#7fb7be", "#d98b8b", "#9fc490", "#c3a6d8", "#f0d98c", "#8fb3d9"];
const WINDOW_COLOUR = "#fff8e1";

/** Sky colours and haze per AQI category: clear blue on good days, beige smog on bad ones. */
const SKY = {
  none: { top: "#bfe3f2", bottom: "#eef7f1", haze: 0 },
  good: { top: "#8fd0ee", bottom: "#e8f7f0", haze: 0 },
  satisfactory: { top: "#a5d6ea", bottom: "#eef6ea", haze: 0.08 },
  moderate: { top: "#c3d9dd", bottom: "#f3efdc", haze: 0.2 },
  poor: { top: "#d4cfbf", bottom: "#efe3c8", haze: 0.32 },
  very_poor: { top: "#cfc3ab", bottom: "#e6d5b5", haze: 0.45 },
  severe: { top: "#b9a98e", bottom: "#d9c4a0", haze: 0.58 },
};

const LANDMARKS = [
  { match: ["delhi"], draw: indiaGate, label: "India Gate" },
  { match: ["mumbai", "bombay"], draw: gateway, label: "Gateway of India" },
  { match: ["kolkata", "calcutta", "howrah"], draw: bridge, label: "Howrah Bridge" },
  { match: ["hyderabad", "secunderabad"], draw: charminar, label: "Charminar" },
  { match: ["agra"], draw: domeMonument, label: "Taj Mahal" },
];

function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  children.flat().forEach((c) => c && el.append(c));
  return el;
}

/** Deterministic pseudo-random numbers so each city always gets the same skyline. */
function seeded(text) {
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

let svg = null;
let stops = null;
let haze = null;
let cityLayer = null;
let currentCity = null;

/** Create the scene inside ``host`` once. */
export function mountScene(host) {
  stops = [s("stop", { offset: "0%" }), s("stop", { offset: "100%" })];
  haze = s("rect", { x: 0, y: 0, width: WIDTH, height: HEIGHT, class: "scene-haze", fill: "#c9b48f", opacity: 0 });
  cityLayer = s("g");
  svg = s(
    "svg",
    {
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      preserveAspectRatio: "xMidYMax slice",
      class: "scene",
      "aria-hidden": "true",
      focusable: "false",
    },
    s("defs", {}, s("linearGradient", { id: "sky", x1: 0, y1: 0, x2: 0, y2: 1 }, stops)),
    s("rect", { width: WIDTH, height: HEIGHT, fill: "url(#sky)" }),
    s("circle", { cx: 1010, cy: 58, r: 30, class: "scene-sun" }),
    clouds(),
    hills(),
    cityLayer,
    breeze(),
    birds(),
    s("path", { d: `M0 ${GROUND} Q300 ${GROUND - 10} 600 ${GROUND} T1200 ${GROUND} V${HEIGHT} H0 Z`, fill: "#8cc084" }),
    trees(),
    haze,
  );
  host.replaceChildren(svg);
  setSky("none");
  updateScene({ city: "" });
}

/** Redraw the skyline for a city and tint the sky by AQI category. */
export function updateScene({ city, category, label }) {
  if (!svg) return;
  if (category) {
    setSky(category);
    const caption = document.getElementById("scene-caption");
    if (caption && label) {
      caption.textContent = `The haze in the sky above follows today's air: ${label} in ${city.split(",")[0]}.`;
      caption.hidden = false;
    }
  }
  const key = (city || "").toLowerCase();
  if (key === currentCity) return;
  currentCity = key;
  cityLayer.replaceChildren(skyline(key));
}

function setSky(category) {
  const sky = SKY[category] ?? SKY.none;
  stops[0].setAttribute("stop-color", sky.top);
  stops[1].setAttribute("stop-color", sky.bottom);
  haze.setAttribute("opacity", String(sky.haze));
  svg.dataset.category = category;
}

function skyline(city) {
  const rand = seeded(city || "breathewise");
  const group = s("g");
  const landmark = LANDMARKS.find((l) => l.match.some((m) => city.includes(m)));
  const landmarkX = 470;
  let x = 0;
  while (x < WIDTH) {
    const width = 34 + Math.floor(rand() * 46);
    if (landmark && x + width > landmarkX - 20 && x < landmarkX + 150) {
      x += width; // keep a gap for the landmark
      continue;
    }
    const height = 40 + Math.floor(rand() * 95);
    const colour = BUILDING_COLOURS[Math.floor(rand() * BUILDING_COLOURS.length)];
    group.append(building(x, width, height, colour, rand));
    x += width + 4 + Math.floor(rand() * 10);
  }
  if (landmark) group.append(s("g", { transform: `translate(${landmarkX} ${GROUND - 118})`, class: "scene-landmark" }, landmark.draw()));
  return group;
}

function building(x, width, height, colour, rand) {
  const top = GROUND - height;
  const g = s("g", {}, s("rect", { x, y: top, width, height, rx: 3, fill: colour }));
  if (rand() > 0.6) g.append(s("rect", { x: x + width / 2 - 2, y: top - 12, width: 4, height: 12, fill: colour }));
  for (let wy = top + 10; wy < GROUND - 14; wy += 16) {
    for (let wx = x + 7; wx < x + width - 10; wx += 13) {
      if (rand() > 0.35) g.append(s("rect", { x: wx, y: wy, width: 6, height: 8, rx: 1, fill: WINDOW_COLOUR, opacity: 0.85 }));
    }
  }
  return g;
}

// ---- Landmarks (simple silhouettes, ~140 wide x 118 tall, origin top-left) ----
const STONE = "#d98a5f";
const STONE_DARK = "#b86f48";

function indiaGate() {
  return [
    s("rect", { x: 20, y: 18, width: 100, height: 14, fill: STONE_DARK }),
    s("path", { d: "M28 118 V32 H112 V118 H86 V70 Q70 46 54 70 V118 Z", fill: STONE }),
    s("rect", { x: 54, y: 4, width: 32, height: 14, fill: STONE }),
    // Qutub Minar beside it
    s("path", { d: "M132 118 L138 20 H146 L152 118 Z", fill: STONE_DARK }),
  ];
}

function gateway() {
  return [
    s("path", { d: "M10 118 V44 H130 V118 H86 V74 Q70 54 54 74 V118 Z", fill: "#e0b77a" }),
    ...[18, 46, 94, 122].map((cx) => s("g", {}, s("rect", { x: cx - 6, y: 24, width: 12, height: 20, fill: "#e0b77a" }), s("circle", { cx, cy: 22, r: 7, fill: "#c99a5b" }))),
    s("circle", { cx: 70, cy: 40, r: 14, fill: "#c99a5b" }),
  ];
}

function bridge() {
  const truss = [];
  for (let i = 0; i <= 8; i += 1) truss.push(s("line", { x1: 10 + i * 15, y1: 70, x2: 10 + i * 15, y2: 100, stroke: "#6c7a89", "stroke-width": 2 }));
  return [
    s("rect", { x: 22, y: 20, width: 10, height: 98, fill: "#6c7a89" }),
    s("rect", { x: 108, y: 20, width: 10, height: 98, fill: "#6c7a89" }),
    s("path", { d: "M0 70 L27 22 L70 62 L113 22 L140 70", stroke: "#6c7a89", "stroke-width": 4, fill: "none" }),
    s("rect", { x: 0, y: 98, width: 140, height: 6, fill: "#556270" }),
    ...truss,
  ];
}

function charminar() {
  const minar = (x) => s("g", {}, s("rect", { x, y: 10, width: 12, height: 108, fill: "#e6c79c" }), s("circle", { cx: x + 6, cy: 10, r: 7, fill: "#cfa56f" }));
  return [
    s("path", { d: "M24 118 V46 H116 V118 H86 V84 Q70 62 54 84 V118 Z", fill: "#e6c79c" }),
    s("rect", { x: 24, y: 40, width: 92, height: 8, fill: "#cfa56f" }),
    minar(12),
    minar(116),
  ];
}

function domeMonument() {
  return [
    s("rect", { x: 20, y: 70, width: 100, height: 48, fill: "#f4efe6" }),
    s("path", { d: "M40 72 Q40 22 70 18 Q100 22 100 72 Z", fill: "#f4efe6" }),
    s("rect", { x: 68, y: 4, width: 4, height: 16, fill: "#d8cfc0" }),
    ...[6, 128].map((x) => s("rect", { x, y: 40, width: 7, height: 78, fill: "#e8e1d4" })),
  ];
}

// ---- Nature and motion ----
function clouds() {
  // Outer group positions the cloud; the inner group carries the CSS drift animation
  // (a CSS transform would otherwise replace the positioning transform).
  const cloud = (x, y, scale, cls) =>
    s(
      "g",
      { transform: `translate(${x} ${y}) scale(${scale})` },
      s(
        "g",
        { class: `scene-cloud ${cls}` },
        s("ellipse", { cx: 0, cy: 0, rx: 34, ry: 14, fill: "#ffffff", opacity: 0.9 }),
        s("ellipse", { cx: 24, cy: -8, rx: 24, ry: 14, fill: "#ffffff", opacity: 0.9 }),
        s("ellipse", { cx: -22, cy: -4, rx: 18, ry: 10, fill: "#ffffff", opacity: 0.9 }),
      ),
    );
  return s("g", {}, cloud(160, 50, 1, "scene-cloud--slow"), cloud(620, 34, 0.8, "scene-cloud--fast"), cloud(880, 70, 1.1, "scene-cloud--slow"));
}

function hills() {
  return s("path", { d: "M0 170 Q150 120 320 160 T640 150 T960 140 T1200 150 V210 H0 Z", fill: "#b8d8a8", opacity: 0.8 });
}

function breeze() {
  const lines = [
    "M60 120 q60 -14 120 0 t120 0",
    "M520 96 q50 -12 100 0 t100 0",
    "M860 128 q60 -14 120 0 t120 0",
  ];
  return s("g", { class: "scene-breeze" }, lines.map((d, i) => s("path", { d, class: `scene-breeze__line scene-breeze__line--${i}` })));
}

function birds() {
  const bird = (x, y) => s("path", { d: `M${x} ${y} q6 -6 12 0 q6 -6 12 0`, class: "scene-bird" });
  return s("g", { class: "scene-birds" }, bird(300, 60), bird(330, 50), bird(350, 66));
}

function trees() {
  const spots = [
    [40, 1.1], [130, 0.8], [250, 1.0], [400, 0.75], [700, 0.9], [820, 1.15], [960, 0.8], [1080, 1.05], [1160, 0.85],
  ];
  return s(
    "g",
    {},
    spots.map(([x, scale], i) =>
      s(
        "g",
        { transform: `translate(${x} ${GROUND + 6}) scale(${scale})` },
        s(
          "g",
          { class: `scene-tree scene-tree--${i % 3}` },
          s("rect", { x: -4, y: -34, width: 8, height: 36, rx: 2, fill: "#7a5a3a" }),
          s("circle", { cx: 0, cy: -50, r: 22, fill: i % 2 ? "#4f9a5b" : "#5fae62" }),
          s("circle", { cx: -14, cy: -38, r: 14, fill: "#6dbb6a" }),
          s("circle", { cx: 14, cy: -40, r: 15, fill: "#3f8a4f" }),
        ),
      ),
    ),
  );
}
