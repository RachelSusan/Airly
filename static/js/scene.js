// Photo hero: a real photo of the user's city with the live AQI on top, a smog tint whose
// strength follows today's AQI category, and a slow drifting-mist layer.
// Photos are from Unsplash (Unsplash License) and stored locally in /img/cities.
import { h } from "./dom.js";
import { categoryBadge } from "./format.js";

const PHOTOS = [
  { match: ["delhi"], file: "delhi", alt: "India Gate, New Delhi, at sunset", author: "shalender", page: "india-gate-war-memorial-in-new-delhi-XjKaPInYVCM" },
  { match: ["mumbai", "bombay"], file: "mumbai", alt: "Gateway of India and the Mumbai waterfront", author: "renzods", page: "gateway-of-india-and-taj-mahal-MxabbMSLr_M" },
  { match: ["kolkata", "calcutta", "howrah"], file: "kolkata", alt: "Howrah Bridge over the Hooghly river, Kolkata", author: "suprabhatmondal", page: "a-large-bridge-spanning-over-a-large-body-of-water-5-eNnQ4fEvk" },
  { match: ["hyderabad", "secunderabad"], file: "hyderabad", alt: "Charminar and the old city market, Hyderabad", author: "neesh774", page: "charminar-in-hyderabad-india-stands-tall-pWH7AigRk18" },
  { match: ["bengaluru", "bangalore"], file: "bengaluru", alt: "Bengaluru skyline above a green tree canopy", author: "ittina", page: "a-view-of-a-city-with-tall-buildings-sEDewKyq6YM" },
  { match: ["chennai", "madras"], file: "chennai", alt: "Chennai Central railway station", author: "angelphotos", page: "a-red-and-white-building-with-a-clock-tower-iUnmvZB5SCk" },
];
const DEFAULT_PHOTO = { file: "default", alt: "A green, tree-lined city seen from a hill", author: "bendp", page: "a-view-of-a-city-from-a-hill-HlGEM72pd1g" };
const UNSPLASH = "https://unsplash.com";

let parts = null;
let currentFile = null;

/** Build the hero once inside ``host``. */
export function mountScene(host) {
  parts = {
    img: h("img", { class: "hero__img", alt: "", decoding: "async" }),
    haze: h("div", { class: "hero__haze", "aria-hidden": "true" }),
    mist: h("div", { class: "hero__mist", "aria-hidden": "true" }),
    city: h("p", { class: "hero__city" }, "Breathe easier, every day"),
    aqi: h("p", { class: "hero__aqi" }, "Choose your city to see live air quality."),
    credit: h("p", { class: "hero__credit" }),
  };
  host.replaceChildren(
    h(
      "div",
      { class: "hero" },
      parts.img,
      parts.haze,
      parts.mist,
      h("div", { class: "hero__shade", "aria-hidden": "true" }),
      h(
        "div",
        { class: "hero__content container" },
        h("p", { class: "hero__eyebrow" }, "Live air quality"),
        parts.city,
        parts.aqi,
      ),
      parts.credit,
    ),
  );
  setPhoto(DEFAULT_PHOTO);
}

/** Show the city's photo, name and (when known) live AQI with a matching smog tint. */
export function updateScene({ city, category, label, aqi }) {
  if (!parts) return;
  const name = (city || "").split(",")[0].trim();
  const key = (city || "").toLowerCase();
  setPhoto(PHOTOS.find((p) => p.match.some((m) => key.includes(m))) ?? DEFAULT_PHOTO);
  if (name) parts.city.textContent = name;
  if (category) {
    parts.haze.dataset.category = category;
    parts.aqi.replaceChildren(h("span", { class: "hero__number" }, `AQI ${aqi}`), " ", categoryBadge(category, label));
    const caption = document.getElementById("scene-caption");
    if (caption) {
      caption.textContent = `The haze over the photo follows today's air: ${label} in ${name}.`;
      caption.hidden = false;
    }
  }
}

function setPhoto(photo) {
  if (photo.file === currentFile) return;
  currentFile = photo.file;
  parts.img.src = `/img/cities/${photo.file}.webp`;
  parts.img.alt = photo.alt;
  parts.credit.replaceChildren(
    "Photo: ",
    h("a", { href: `${UNSPLASH}/@${photo.author}`, rel: "noopener", target: "_blank" }, `@${photo.author}`),
    " on ",
    h("a", { href: `${UNSPLASH}/photos/${photo.page}`, rel: "noopener", target: "_blank" }, "Unsplash"),
  );
}
