# Architecture: Airly

## 1. Overview

Airly is a single **FastAPI** service. It serves a static, framework-free frontend and a JSON API. The work is split into layers with one-way dependencies:

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser: static HTML / CSS / JS                                 │
│  • Family profiles + checklist state in localStorage             │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTPS / JSON
┌───────────────▼──────────────────────────────────────────────────┐
│  API layer (app/api)                                             │
│  • Routing, Pydantic validation, rate limiting, security headers │
└───────┬───────────────────────┬──────────────────────┬───────────┘
        │                       │                      │
┌───────▼────────┐   ┌──────────▼─────────┐   ┌────────▼───────────┐
│ Services       │   │ Engine (pure)      │   │ AI layer           │
│ app/services   │   │ app/engine         │   │ app/ai             │
│ • Open-Meteo   │──►│ • aqi.py  (NAQI)   │◄──│ • client.py        │
│   air + weather│   │ • risk.py          │   │ • prompts.py       │
│ • geocoding    │   │ • windows.py       │   │ • tools.py ───────►│ calls engine
│ • TTL cache    │   │ • checklist.py     │   │ • schemas.py       │
└───────┬────────┘   │ • impact.py        │   │ • fallback.py      │
        │            └────────────────────┘   └────────┬───────────┘
        ▼                                              ▼
  Open-Meteo APIs                              Google Gemini API
```

**Dependency rule:** `api → services, engine, ai`; `ai → engine, services`; `engine → models only` (pure functions, no I/O). This keeps the engine fully unit-testable.

## 2. Folder structure

```
Airly/
├── app/
│   ├── main.py              # App factory: middleware, routers, static files
│   ├── config.py            # Settings from environment (pydantic-settings)
│   ├── api/
│   │   ├── deps.py          # Shared dependencies (settings, clients)
│   │   ├── air.py           # /api/geocode, /api/air
│   │   ├── plan.py          # /api/plan
│   │   ├── chat.py          # /api/chat
│   │   ├── simulate.py      # /api/simulate, /api/scenarios
│   │   └── health.py        # /api/health
│   ├── models/              # Pydantic request/response schemas
│   ├── services/
│   │   ├── air_quality.py   # Open-Meteo air-quality + forecast client
│   │   ├── geocoding.py     # Open-Meteo geocoding client
│   │   └── cache.py         # Small async TTL cache
│   ├── engine/
│   │   ├── aqi.py           # NAQI sub-index + overall AQI + category
│   │   ├── risk.py          # Per-member sensitivity → risk + activity limits
│   │   ├── windows.py       # Best/safe time windows from hourly forecast
│   │   ├── checklist.py     # Rule-based protection checklist items
│   │   ├── ventilation.py   # "Should I open my windows?" rules
│   │   ├── exposure.py      # Inhaled PM2.5 dose + exposure change
│   │   └── impact.py        # Emission factors + what-if calculations
│   ├── ai/
│   │   ├── client.py        # Google Gen AI SDK wrapper (timeouts, errors, tool loop)
│   │   ├── prompts.py       # System prompts (stable → cacheable)
│   │   ├── tools.py         # Tool definitions + dispatch to engine
│   │   ├── schemas.py       # JSON schemas for structured outputs
│   │   └── fallback.py      # Rule-based responses when AI is unavailable
│   └── security/
│       ├── headers.py       # CSP + security headers middleware
│       └── rate_limit.py    # Per-IP rate limiting
├── static/
│   ├── index.html
│   ├── css/  (tokens.css, base.css, components.css)
│   └── js/   (app.js, api.js, store.js, views/*.js)
├── tests/
│   ├── unit/                # engine + services (mocked HTTP)
│   ├── api/                 # endpoint tests (TestClient, mocked AI)
│   └── conftest.py
├── docs/
├── .github/workflows/ci.yml
├── requirements.txt
├── pyproject.toml           # ruff + pytest config
├── .env.example
└── .gitignore
```

## 3. Request flows

### 3.1 Dashboard: `GET /api/air?lat&lon`
1. Validate coordinates (latitude −90..90, longitude −180..180), rounded to 2 decimals (about 1 km, which improves cache hits and privacy).
2. Look up the cache (TTL 15 minutes). On a miss, fetch air quality and weather from Open-Meteo **in parallel**.
3. `engine.aqi` calculates the NAQI for the current hour and each forecast hour.
4. `engine.windows` labels each hour as safe, caution or avoid for a general adult.
5. Return the combined JSON. **No AI call.** The dashboard is fast and always available.

### 3.2 Daily plan: `POST /api/plan`
1. Validate the body: location, family members, lifestyle (commute mode, distance, school hours).
2. Get air data (cached), then let the engine work out per-member risk, windows, checklist and ventilation advice. This produces a **facts object**.
3. Send the facts object to Gemini with the planner system prompt and a **structured output schema**.
4. Validate Gemini's JSON against the schema, then return it.
5. On any AI error, return `fallback.plan(facts)` with `"source": "rules"`.

### 3.3 Assistant chat: `POST /api/chat`
1. Validate the message history (max turns and length) and the context (location, members).
2. Call Gemini with the assistant system prompt and **tools**: `get_current_conditions`, `get_forecast_windows`, `assess_family_risk`, `check_ventilation`, `simulate_scenario`.
3. Run the tool loop: Gemini asks for a tool, the server runs the engine function, and the result goes back to Gemini. The loop is capped at 4 iterations.
4. Return the final text and a list of tools used (shown as "based on live data" chips).
5. On error, `fallback.chat(intent, facts)` gives keyword-based answers for the common questions.

### 3.4 Simulator: `POST /api/simulate`
1. Validate the scenario ID and its numeric inputs (with bounded ranges).
2. `engine.impact` calculates the emission changes, with an assumptions list. This is deterministic.
3. Gemini writes a short plain-language explanation of **the computed numbers only**.
4. Return the numbers, assumptions and explanation. On AI failure, return a template explanation.

## 4. Key design decisions

| Decision | Why |
|---|---|
| Engine is pure, with no I/O | Deterministic, testable, and stops the AI from making up numbers |
| Gemini reaches data only through tools | Answers are grounded in live data, and the tool calls show the reasoning |
| Structured outputs for plan and simulator | The UI renders fields directly, with no fragile text parsing |
| No server database | No personal data on the server; simpler and more secure (see `database.md`) |
| Static frontend with no build | Small repo, fast load, few dependencies |
| TTL cache, coordinates rounded to 0.01° | Fewer upstream calls, faster responses, better privacy |
| Every AI path has a fallback | The app works even without the AI service |

## 5. Configuration

All configuration comes from environment variables (see `deployment.md`). Nothing secret is in code.

## 6. Error handling

- Upstream data failure: `503` with a friendly message. If a stale cached value exists, serve it with `"stale": true`.
- AI failure (timeout, rate limit, refusal, invalid JSON): fall back to the rules and set `"source": "rules"`.
- Validation errors: `422` with field-level messages.
- All errors are logged without personal data or request bodies.
