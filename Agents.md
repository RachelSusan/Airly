# Agents.md: rules for AI coding assistants

Instructions for any AI coding agent (Claude Code or others) working in this repository.

## Read first

1. `docs/PRD.md`: what we are building and why
2. `docs/architecture.md`: structure and data flow
3. `docs/code_style.md`: conventions
4. `docs/tasks.md`: what is done and what comes next

Read the specific doc before touching that area: `api.md`, `security.md`, `testing.md`, `ai_prompts.md`, `impact_methodology.md`, `design_system.md`, `accessibility.md`.

## Hard rules (hackathon constraints)

- **One branch only: `main`.** Never create, push or merge other branches.
- **Repo size under 10 MB.** No binaries, datasets, videos, `node_modules`, `.venv` or large images. Use SVG or CSS for visuals.
- **The repo is public:** never commit secrets. The API key lives only in `.env`, which is git-ignored.
- **GenAI is mandatory:** the AI features go through the Google Gemini API (`gemini-3.8-flash`, free tier).

## Core design principle

**Code does the numbers, Gemini does the language.**
- AQI values, risk levels, time windows and emission figures are calculated in `app/engine/` with plain, deterministic functions.
- Gemini only explains, personalises and phrases. It must never invent a number. In chat it gets numbers by calling tools.
- Every AI feature needs a rule-based fallback in `app/ai/fallback.py`.

## Working rules

- Keep modules small and focused. Put business logic in `engine/` and `services/`, never in route handlers.
- Validate every input with Pydantic models at the API boundary.
- Add or update tests for every engine function and endpoint you change. Mock all external HTTP and Gemini calls.
- Run `ruff check .` and `pytest` before committing.
- Update `docs/tasks.md` when a task is finished, and the matching doc when a contract changes.
- Commit small, frequent changes with Conventional Commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- Do not add a dependency without a clear reason. Prefer the standard library and what is already in `requirements.txt`.
- Frontend: semantic HTML, no frameworks, no build step. Follow `docs/accessibility.md`.

## Commands

```bash
pip install -r requirements.txt      # install
uvicorn app.main:app --reload        # run (http://localhost:8000)
pytest                               # test
pytest --cov=app                     # coverage
ruff check . && ruff format --check .  # lint
```

## Do not

- Do not hard-code API keys, coordinates of real people, or personal data.
- Do not claim local AQI improvements in the simulator. Report emission and exposure changes only.
- Do not call Gemini from tests.
- Do not store family profiles on the server.
