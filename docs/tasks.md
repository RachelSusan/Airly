# Tasks and Progress: BreatheWise

Deadline: **29 Nov 2026, 11:59 PM IST** · Submissions: at most 3 · Video mandatory

Legend: `[ ]` to do · `[x]` done · `[~]` in progress

## Day 1: 26 Nov: Foundations
- [x] Project docs (README, Agents, CLAUDE, PRD, design system, architecture, database, API, security, accessibility, code style, testing, AI prompts, impact methodology, deployment, tasks)
- [ ] Plan the extra options (to be discussed)
- [x] Repo scaffolding: `.gitignore`, `.env.example`, `requirements*.txt`, `pyproject.toml`, `LICENSE`
- [x] First commit and push to `main`
- [x] `app/config.py`, `app/main.py` with security headers and a health endpoint
- [x] Services: Open-Meteo air quality, weather, geocoding, TTL cache (checked against the live API)
- [x] Engine: `aqi.py`, `risk.py`, `windows.py`, `ventilation.py`, `checklist.py`, `exposure.py`, `impact.py`
- [x] Unit tests for the engine and services (120 tests, 99% coverage)
- [x] CI workflow (lint, tests with coverage gate, `pip-audit`)

## Day 2: 27 Nov: AI and UI
- [x] `app/ai`: client, prompts, schemas, tools, fallback, planner, assistant, simulator
- [x] Endpoints: `/api/air`, `/api/geocode`, `/api/plan`, `/api/chat`, `/api/scenarios`, `/api/simulate`
- [x] Rate limiting, 32 KB body limit, consistent error format
- [x] API tests (AI mocked) and static accessibility checks (181 tests, 97% coverage)
- [x] Frontend: tokens and base CSS, dashboard, planner, family profiles, checklist, chat, simulator
- [~] Accessibility pass: labels, live regions, skip link, text + icon badges, mobile reflow done; NVDA and Lighthouse checks pending
- [x] Neighbourhood air map (OpenStreetMap + modelled AQI grid), location chip on every location-based view
- [x] Light, calm, green theme; before/after CO₂ chart in the simulator
- [ ] Test the AI path with a real `ANTHROPIC_API_KEY` (all AI paths verified with mocks only so far)
- [ ] Deploy (platform decision)
- [ ] **Submission 1** (baseline, all modules working)

## Day 3: 28 Nov: Polish and proof
- [ ] Verify every emission factor and its source (`impact_methodology.md`)
- [ ] School activity planner and auto-refresh change highlights
- [ ] Security checklist (`security.md` §11) and `pip-audit`
- [ ] Coverage ≥ 80%; Lighthouse a11y ≥ 95
- [ ] README final: screenshots (small), live link, assumptions
- [ ] Record the demo video (follow the manual demo script in `testing.md`)
- [ ] **Submission 2** with video

## Day 4: 29 Nov: Buffer
- [ ] Fix anything found in review
- [ ] **Submission 3** only if it is clearly better

## Pre-submission checklist
- [ ] Repo public, single `main` branch, under 10 MB
- [ ] README covers vertical, approach and logic, how it works, assumptions
- [ ] Live URL works; fallback works without the AI
- [ ] All tests and lint pass in CI
- [ ] Video link (unlisted YouTube or shared Drive) works in a private window
