# Testing Strategy: BreatheWise

Goal: **prove the logic is correct and the app is safe**, quickly and repeatably, with no network access and no AI costs during tests.

## 1. Test pyramid

| Layer | What | Tools | Target |
|---|---|---|---|
| **Unit: engine** | AQI, risk, windows, checklist, ventilation, impact | `pytest`, parametrised cases | ≥ 95% coverage |
| **Unit: services** | Open-Meteo parsing, cache TTL and stale behaviour, geocoding | `pytest`, `respx` (httpx mocking) | ≥ 85% |
| **Unit: AI layer** | Tool dispatch, tool input validation, schema validation, fallback selection, refusal handling | `pytest`, fake Anthropic client | ≥ 85% |
| **API** | Every endpoint: happy path, validation errors, rate limit, upstream failure, AI failure leading to fallback | FastAPI `TestClient` | All endpoints |
| **Security** | Headers present, unknown fields rejected, oversized body rejected, no secrets in responses | `TestClient` | Must pass |
| **Accessibility (static)** | `index.html`: `lang`, landmarks, labels, alt or `aria-hidden` on SVGs, skip link | Python HTML parser | Must pass |
| **Manual** | Keyboard, screen reader, mobile layout, end-to-end demo script | Checklist in `accessibility.md` | Before submissions |

**Overall coverage target: ≥ 80%** (`pytest --cov=app --cov-fail-under=80`).

## 2. Rules

- **No real network calls.** HTTP is mocked with `respx`; Claude is replaced by a fake client fixture.
- **No real API key needed:** tests set `ANTHROPIC_API_KEY=test-key`.
- Tests are deterministic: fixed clock (`freezegun` or injected `now`) and fixed fixtures.
- Fixtures live in `tests/fixtures/` (sample Open-Meteo JSON, at most a few KB each).

## 3. Key test cases

### Engine: AQI (`test_aqi.py`)
- Each pollutant's breakpoint edges: 30 → 50, 60 → 100, 90 → 200, 120 → 300, 250 → 400, ≥ 380 → 500 for PM2.5 (continuous interpolation between breakpoints)
- Values above the top breakpoint are capped at 500
- Overall AQI = maximum sub-index; the dominant pollutant is identified correctly
- Missing pollutant values are handled (index from the available ones; at least PM2.5 or PM10 required)
- Category mapping: 0–50 Good … 401+ Severe

### Engine: risk (`test_risk.py`)
- Same AQI gives a higher risk for child, senior and asthma than for a healthy adult
- Multiple conditions take the highest sensitivity
- Children's alert fires at Moderate and above for sensitive children, and at Poor and above for others

### Engine: windows (`test_windows.py`)
- Finds the lowest-AQI contiguous window of the requested length
- Respects constraints (daylight hours for play, school hours)
- Returns `avoid` with an indoor alternative when no hour is acceptable

### Engine: ventilation (`test_ventilation.py`)
- Outdoor AQI ≥ Poor means keep windows closed
- Outdoor Good or Satisfactory with wind means ventilate
- Cooking with biomass or kerosene means extra ventilation or exhaust advice even on bad days (with mask and purifier caveats)

### Engine: impact (`test_impact.py`)
- Petrol car to metro over 12 km × 5 days gives the expected kg CO₂ per year (hand-calculated)
- 1,000 families scenario scales linearly
- Trees scenario uses the per-tree absorption factor × years
- Every result includes assumptions and sources and never contains an `aqi_change` field
- Input bounds enforced

### API
- `GET /api/air` with valid coordinates returns 200 with the right shape; invalid latitude returns 422; upstream down with no cache returns 503; upstream down with stale cache returns 200 and `stale: true`
- `POST /api/plan` with AI success returns `source: "ai"`; AI exception returns `source: "rules"` with a valid shape
- `POST /api/chat` with the tool loop returns the tools used; a loop over 4 iterations stops safely; refusal goes to the fallback
- `POST /api/simulate` with an unknown scenario returns 422; out-of-range input returns 422
- Rate limit: request N+1 returns 429 with `Retry-After`
- Security headers present on `/` and `/api/*`

## 4. Running tests

```bash
pytest                         # all tests
pytest tests/unit -q           # fast unit only
pytest --cov=app --cov-report=term-missing
```

## 5. Continuous integration

`.github/workflows/ci.yml` runs on every push to `main`:
1. Set up Python 3.12
2. `pip install -r requirements.txt -r requirements-dev.txt`
3. `ruff check .` and `ruff format --check .`
4. `pytest --cov=app --cov-fail-under=80`
5. `pip-audit`

## 6. Manual demo test script (before each submission)

1. Search "Delhi", and the dashboard loads with AQI, category and forecast.
2. Add a child with asthma and an adult runner, and their risk badges differ.
3. Generate today's plan, and see routine windows, a school plan and checklists.
4. Ask "Can my children play outside today?", and get a grounded answer with tool chips.
5. Ask "Should I open my windows?", and get ventilation advice with a reason.
6. Run "petrol to public transport", and see numbers, assumptions and the disclaimer.
7. Turn off the network or the API key, and the fallback answers still work.
8. Keyboard-only run through steps 1–6.
