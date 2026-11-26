# Tasks and Progress: BreatheWise

Deadline: **29 Nov 2026, 11:59 PM IST** · Submissions: at most 3 · Video mandatory

Legend: `[ ]` to do · `[x]` done · `[~]` in progress

## Day 1: 26 Nov: Foundations
- [x] Project docs (README, Agents, CLAUDE, PRD, design system, architecture, database, API, security, accessibility, code style, testing, AI prompts, impact methodology, deployment, tasks)
- [ ] Plan the extra options (to be discussed)
- [ ] Repo scaffolding: `.gitignore`, `.env.example`, `requirements*.txt`, `pyproject.toml`, `LICENSE`
- [ ] First commit and push to `main`
- [ ] `app/config.py`, `app/main.py` with security headers and a health endpoint
- [ ] Services: Open-Meteo air quality, weather, geocoding, TTL cache
- [ ] Engine: `aqi.py`, `risk.py`, `windows.py`, `ventilation.py`, `checklist.py`, `impact.py`
- [ ] Unit tests for the engine and services
- [ ] CI workflow

## Day 2: 27 Nov: AI and UI
- [ ] `app/ai`: client, prompts, schemas, tools, fallback
- [ ] Endpoints: `/api/air`, `/api/geocode`, `/api/plan`, `/api/chat`, `/api/scenarios`, `/api/simulate`
- [ ] Rate limiting
- [ ] API tests (AI mocked)
- [ ] Frontend: tokens and base CSS, dashboard, planner, family profiles, checklist, chat, simulator
- [ ] Accessibility pass (keyboard, labels, live regions, contrast)
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
