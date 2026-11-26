# Accessibility: BreatheWise

Target: **WCAG 2.2 Level AA.** Air-quality advice is health information, so everyone must be able to perceive and act on it, including people using screen readers, keyboards, magnification or slow phones.

## 1. Commitments

| Area | Commitment |
|---|---|
| **Structure** | Semantic HTML landmarks (`header`, `nav`, `main`, `footer`), one `h1` per view, logical heading order |
| **Keyboard** | Everything works with the keyboard alone; visible focus ring; no keyboard traps; a "Skip to main content" link |
| **Colour** | Text contrast ≥ 4.5:1 (large text ≥ 3:1); UI components ≥ 3:1; **AQI is never shown by colour alone** (text label plus icon shape) |
| **Screen readers** | Labelled controls; meaningful alt text or `aria-hidden` for decorative SVGs; live regions for dynamic updates |
| **Forms** | Every input has a visible `<label>`; errors are linked with `aria-describedby` and announced; required fields are marked in text |
| **Motion** | `prefers-reduced-motion` respected; nothing flashes more than 3 times a second; no auto-playing animation |
| **Zoom and reflow** | Works at 200% zoom and 320 px width with no horizontal scroll |
| **Touch targets** | At least 44×44 px |
| **Language** | `<html lang="en">`; plain language around a Grade 6–8 reading level |
| **Timing** | No time limits; auto-refresh never moves focus or interrupts typing |

## 2. Component patterns

### AQI hero
```html
<section aria-labelledby="aqi-title">
  <h2 id="aqi-title">Air quality now in New Delhi</h2>
  <p class="aqi-value"><span class="aqi-number">342</span>
     <span class="badge badge--very-poor"><svg aria-hidden="true">…</svg>Very Poor</span></p>
  <p>Main pollutant: PM2.5. Updated 9:04 AM.</p>
</section>
```
Screen reader output: "Air quality now in New Delhi, heading. 342 Very Poor. Main pollutant PM2.5…"

### Forecast timeline
- Visual: coloured hourly bars.
- Accessible: a real `<table>` with a caption ("24-hour AQI forecast"), columns for time, AQI, category and advice. It's visually hidden on wide screens only if the bars carry the same info as text.
- Scroll container: `tabindex="0"`, `role="region"`, `aria-label`.

### Chat assistant
- The message list has `role="log"` and `aria-live="polite"`, so new replies are announced.
- A "BreatheWise is thinking…" status message uses `role="status"`.
- The input has a visible label "Ask about the air". Enter sends; Shift+Enter adds a new line.
- Quick-question chips are real `<button>`s.

### Checklist
- Native `<input type="checkbox">` with `<label>`.
- Progress text such as "3 of 6 done" in a `role="status"` region.

### Family profile form
- `<fieldset>` and `<legend>` for groups (conditions, activities).
- Delete needs confirmation, using an accessible `<dialog>` with focus trapped and returned afterwards.

### Simulator
- Results as text with units ("1,123 kg CO₂ per year avoided"), not only charts.
- Assumptions in a `<details>`/`<summary>` element.

### Alerts
- Children's outdoor alerts and data warnings use `role="status"`. `role="alert"` is reserved for errors that block a task.

## 3. Content guidelines

- Write numbers with units and context: "PM2.5 is 186 µg/m³, about 12 times the WHO 24-hour guideline."
- Expand abbreviations on first use: "PM2.5 (fine particles)".
- Avoid fear language; say what to do.
- Links and buttons describe their action ("Add family member", not "Click here").

## 4. Testing checklist

| Check | Tool or method |
|---|---|
| Automated audit | Lighthouse Accessibility ≥ 95; axe DevTools shows 0 serious or critical issues |
| Keyboard-only walkthrough | Tab through every view and do each task |
| Screen reader | NVDA (Windows) on the dashboard, chat, family form and simulator |
| Contrast | Check all tokens in light and dark mode |
| Zoom | 200% browser zoom; 320 px viewport |
| Reduced motion | OS setting on; confirm animations stop |
| Automated tests | `tests/api/test_static_a11y.py` checks `lang`, landmarks, labels and image alt attributes in `index.html` |
