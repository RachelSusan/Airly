// A live clock showing the date and time at the selected location (12-hour, ticking).
import { h } from "./dom.js";

let timer = null;
let element = null;
let zone = null;

function format(date, timeZone) {
  const options = {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZoneName: "short",
  };
  let parts;
  try {
    parts = new Intl.DateTimeFormat("en-IN", { ...options, timeZone: timeZone || undefined }).formatToParts(date);
  } catch {
    parts = new Intl.DateTimeFormat("en-IN", options).formatToParts(date); // unknown zone: viewer's clock
  }
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  const period = (p.dayPeriod || "").toUpperCase();
  return `${p.weekday} ${p.day} ${p.month}, ${p.hour}:${p.minute}:${p.second} ${period} ${p.timeZoneName || ""}`.trim();
}

function tick() {
  if (!element) return;
  const now = new Date();
  element.textContent = format(now, zone);
  element.dateTime = now.toISOString();
}

/** A <time> element that keeps showing the current time at ``timeZone`` (IANA name). */
export function liveClock(timeZone) {
  zone = timeZone || null;
  element = h("time", { class: "live-clock" });
  tick();
  clearInterval(timer);
  timer = setInterval(tick, 1000);
  return element;
}

/** Switch the running clock to another time zone (e.g. once live data reports it). */
export function setClockZone(timeZone) {
  zone = timeZone || null;
  tick();
}
