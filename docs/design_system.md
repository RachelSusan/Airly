# Design System: BreatheWise

A calm, trustworthy, readable interface. Health information must be clear at a glance, and colour is **never** the only signal.

## 1. Principles

1. **Clarity over decoration:** the AQI number, its category and the action to take come first.
2. **Never colour alone:** every AQI colour comes with a text label and an icon or shape.
3. **Calm, not alarming:** serious information in a steady tone. No flashing or aggressive red screens.
4. **Mobile first:** most users will check on a phone. Design for 360 px wide, then scale up.

## 2. Colour tokens

Defined as CSS custom properties on `:root`. The theme is **light only**: a calm, natural look with soft sage backgrounds, forest-green accents and a light leaf motif in the header.

### Brand and surface
| Token | Value | Use |
|---|---|---|
| `--color-bg` | `#F3F7F0` | Page background (soft sage, with faint sky and leaf gradients) |
| `--color-surface` | `#FFFFFF` | Cards |
| `--color-surface-2` | `#EAF2E6` | Tinted panels, chips |
| `--color-sky` | `#E4F1F5` | Location bar |
| `--color-text` | `#1F2D24` | Body text (deep forest ink) |
| `--color-text-muted` | `#4B5D50` | Secondary text (still ≥ 4.5:1) |
| `--color-primary` | `#2F6B4F` | Buttons, links, active tab (forest green) |
| `--color-accent` | `#7FB069` | Positive bars, decoration (fresh leaf) |
| `--color-border` | `#CFDCCA` | Dividers |
| `--color-focus` | `#1F6F8B` | Focus ring (3 px calm teal, distinct from the greens) |

### AQI scale (Indian NAQI categories)
Badges use a **tinted background with dark text** so contrast stays at AA or better.

| Category | AQI | Token | Swatch | Badge text | Icon |
|---|---|---|---|---|---|
| Good | 0–50 | `--aqi-good` | `#2E9E5B` | `#0B3D21` on `#D7F2E1` | ● filled circle |
| Satisfactory | 51–100 | `--aqi-satisfactory` | `#8BC34A` | `#2E4A0E` on `#ECF6DC` | ◐ half circle |
| Moderate | 101–200 | `--aqi-moderate` | `#F2C200` | `#4D3B00` on `#FFF4C7` | ▲ triangle |
| Poor | 201–300 | `--aqi-poor` | `#F08C00` | `#5A2E00` on `#FFE5C2` | ◆ diamond |
| Very Poor | 301–400 | `--aqi-very-poor` | `#D93025` | `#5C0B06` on `#FBD9D6` | ■ square |
| Severe | 401–500 | `--aqi-severe` | `#7E1F3B` | `#FFFFFF` on `#7E1F3B` | ✖ cross |

### Advice states
| State | Meaning | Label |
|---|---|---|
| `safe` | Go ahead | "Safe" |
| `caution` | Limit duration or intensity | "Caution" |
| `avoid` | Stay indoors or use an alternative | "Avoid" |

## 3. Typography

- **Font:** system stack, `system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif`. No web-font download (faster, and Indic scripts render well).
- **Base size:** 16 px (1rem), line height 1.5. Users can scale to 200% without breaking the layout.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--fs-display` | 3rem | 700 | Big AQI number |
| `--fs-h1` | 1.75rem | 700 | Page title |
| `--fs-h2` | 1.375rem | 600 | Section title |
| `--fs-h3` | 1.125rem | 600 | Card title |
| `--fs-body` | 1rem | 400 | Body |
| `--fs-small` | 0.875rem | 400 | Captions, sources |

## 4. Spacing, radius, elevation

- Spacing scale (4 px base): `--space-1: 4px`, `-2: 8px`, `-3: 12px`, `-4: 16px`, `-6: 24px`, `-8: 32px`, `-12: 48px`
- Radius: `--radius-sm: 6px`, `--radius-md: 12px`, `--radius-pill: 999px`
- Shadow: `--shadow-card: 0 1px 3px rgb(0 0 0 / 0.08)`
- Page gutter: 16 px on mobile, max content width 1100 px

## 5. Layout

- **Mobile:** single column with bottom tab navigation (Dashboard · Planner · Family · Assistant · Simulator).
- **Desktop (≥ 900 px):** top navigation and a two-column grid (main area plus side panel).
- No horizontal scroll at any width from 320 px up.

## 6. Components

| Component | Description | Key a11y notes |
|---|---|---|
| **AQI Hero Card** | Big AQI number, category badge, dominant pollutant, one-line advice, last-updated time | Number and category in one text string for screen readers |
| **Pollutant Chips** | PM2.5, PM10, NO₂, O₃, CO, SO₂ with units | `<dl>` term and value pairs |
| **City Scene** | Animated SVG banner: a colourful skyline generated from the city name, a landmark for Delhi, Mumbai, Kolkata, Hyderabad and Agra, trees swaying in the breeze, drifting clouds and birds. The sky colour and smog haze follow the live AQI category | Decorative (`aria-hidden`), with a text caption describing the haze; "Pause animation" button (WCAG 2.2.2); starts paused when the user prefers reduced motion |
| **Air Map** | OpenStreetMap (Leaflet) with a 5×5 grid of modelled AQI cells (~11 km each) around the user, a "You are here" marker, a legend and popups | Focusable region with keyboard pan and zoom; a text summary names the cleanest and most polluted nearby areas; the legend is a real list |
| **Location chip** | "📍 Using live data for …" with a "Change location" button on every view that uses location | Button moves focus to the city search |
| **Before/After chart** | Simulator CO₂ bars (before in clay, after in leaf green) | Values printed as text next to each bar |
| **Forecast Timeline** | 24 hourly blocks coloured by category, with safe windows highlighted | Also rendered as a table; scrollable with the keyboard |
| **Time Window Card** | "Best time to jog: 2–4 PM (Moderate)" | Uses advice-state label plus icon |
| **Family Member Card** | Avatar initial, name, age group, conditions, today's risk badge | Edit and delete buttons with explicit labels |
| **Checklist** | Per-member tick list | Native checkboxes; progress announced |
| **Chat Panel** | Message list, input, quick-question chips | `aria-live="polite"` for new replies; Enter sends, Shift+Enter adds a new line |
| **Scenario Card** | Preset what-if with inputs and a result panel | Results in text with units; assumptions shown expandably |
| **Alert Banner** | Children's outdoor alert, data warnings | `role="status"` (not `alert`, unless urgent) |
| **Button** | Primary, secondary, ghost | Minimum 44×44 px target; visible focus ring |
| **Skeleton loader** | Placeholder while loading | `aria-busy="true"` on the container |

## 7. Icons and imagery

- Inline SVG icons only (no icon font, no images), with `aria-hidden="true"` when decorative.
- No stock photos, which keeps the repo small.

## 8. Motion

- Transitions of 150–200 ms on opacity and transform only.
- Respect `prefers-reduced-motion: reduce`, which turns off all non-essential animation.

## 9. Voice and tone

- Simple words and short sentences, at about a Grade 6–8 reading level.
- Action first: "Jog between 2 and 4 PM today. The air is cleanest then."
- Always give a reason, and a number when it helps.
- Never use fear language. Be honest about uncertainty ("estimate", "forecast").
