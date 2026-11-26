# BreatheWise — Urban Air Quality Assistant

> A GenAI-powered assistant that helps families and communities get through severe winter smog and urban air pollution. It plans safer daily routines, protects every family member, and explains what each choice changes.

**Challenge:** PromptWars Virtual, Challenge 6: Urban Air Quality Assistant
**Live demo:** _TBD_ · **Demo video:** _TBD_

---

## Chosen vertical

**Urban Air Quality Assistant.** The app suggests low-emission daily routines, indoor air-quality tips and sustainable alternatives for the user's location and lifestyle. It also explains the direct impact of each choice.

## Features

| Module | What it does |
|---|---|
| **1. AI Air Quality Assistant** | Ask in plain language: *"Is it safe to go jogging now?"*, *"Can my children play outside today?"*, *"Should I open my windows?"*. Answers use live AQI, weather and your family profile, in simple language. |
| **2. Smart Daily Routine Planner** | Finds the cleanest hours for walking, jogging, commuting and school outdoor time. Suggests indoor alternatives and updates when the AQI forecast changes. |
| **3. Family Protection Profiles** | One profile per family member (age group, asthma or other conditions). Each member gets their own risk level, children's outdoor alerts and a daily protection checklist. |
| **4. What-If Pollution Simulator** | Try scenarios such as *"What if I switch from petrol to public transport?"* or *"What if 1,000 families drive less?"*. It shows **estimated emission changes**, never promises about local AQI. |
| **Core** | Live dashboard (AQI, PM2.5, PM10, NO₂, O₃, weather), city search or GPS, indoor air tips, sustainable alternatives with their impact. |

## Approach and logic

BreatheWise follows one rule: **code does the numbers, Claude does the language.**

```
Live data (Open-Meteo) ──► Rule engine (AQI, risk, time windows) ──┐
                           Impact engine (emission factors)       ├──► Claude ──► Plain-language advice
User + family profile ─────────────────────────────────────────────┘
```

1. **Data layer:** fetches hourly air quality and weather for the user's coordinates and caches it for a short time.
2. **Rule engine** (plain code, unit-tested): calculates Indian NAQI from pollutant levels, works out per-member risk, and finds the safest time windows.
3. **Impact engine** (plain code, unit-tested): calculates emission changes from documented emission factors.
4. **Claude layer:** turns those verified facts into personalised plans, checklists and chat answers. In chat, Claude calls **tools** that run the engines, so every number comes from code, not from the model.
5. **Fallback:** if the AI service is unavailable, the rule engine still returns basic advice.

## How it works

1. The user picks a city (or shares location) and adds family members.
2. The dashboard shows the current AQI and a 24-hour forecast with safe, caution and avoid windows.
3. The planner builds a day plan and a checklist for each member.
4. The assistant answers follow-up questions using live data.
5. The simulator shows how much a habit change cuts emissions and personal exposure.

## Assumptions

- Air-quality and weather data come from the Open-Meteo APIs (modelled data, not a government monitoring station).
- AQI follows India's **NAQI (CPCB)** categories, calculated from hourly concentrations. The official index uses 24-hour or 8-hour averages, so ours is a close estimate.
- Emission factors and exposure-reduction figures are published averages. See [docs/impact_methodology.md](docs/impact_methodology.md).
- Family profiles stay **in the user's browser**. The server keeps no personal data.
- This is guidance, not medical advice.

## Tech stack

Python 3.12+ · FastAPI · Pydantic · Anthropic Claude API (`claude-opus-5-5`) · Open-Meteo · HTML, CSS and JavaScript · pytest · GitHub Actions

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then set ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000. Run the tests with `pytest`.

## Documentation

| Doc | Purpose |
|---|---|
| [PRD](docs/PRD.md) | Product requirements |
| [Architecture](docs/architecture.md) | System design and folder structure |
| [API](docs/api.md) | Endpoint contracts |
| [Database](docs/database.md) | Data model and storage |
| [AI prompts](docs/ai_prompts.md) | How Claude is used |
| [Impact methodology](docs/impact_methodology.md) | Formulas, factors, sources |
| [Design system](docs/design_system.md) | UI tokens and components |
| [Accessibility](docs/accessibility.md) | Inclusive design commitments |
| [Security](docs/security.md) | Security controls |
| [Testing](docs/testing.md) | Test strategy |
| [Code style](docs/code_style.md) | Conventions |
| [Deployment](docs/deployment.md) | Running and deploying |

## Credits

City photos are from [Unsplash](https://unsplash.com) under the [Unsplash License](https://unsplash.com/license), resized and stored in `static/img/cities/`:

| City | Photographer |
|---|---|
| Delhi (India Gate) | [@shalender](https://unsplash.com/@shalender) |
| Mumbai (Gateway of India) | [@renzods](https://unsplash.com/@renzods) |
| Kolkata (Howrah Bridge) | [@suprabhatmondal](https://unsplash.com/@suprabhatmondal) |
| Hyderabad (Charminar) | [@neesh774](https://unsplash.com/@neesh774) |
| Bengaluru (skyline) | [@ittina](https://unsplash.com/@ittina) |
| Chennai (Central station) | [@angelphotos](https://unsplash.com/@angelphotos) |
| Other cities (green city view) | [@bendp](https://unsplash.com/@bendp) |

Maps © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, drawn with [Leaflet](https://leafletjs.com).

## Disclaimer

BreatheWise gives general guidance about air pollution. It is not a substitute for medical advice. People with respiratory or heart conditions should follow their doctor's guidance.
