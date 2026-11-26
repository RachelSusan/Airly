# Code Style: BreatheWise

Goal: code that a judge can read in five minutes and understand. **Readable, consistent, small.**

## 1. General

- **Clarity over cleverness.** Prefer simple, explicit code.
- **Small units:** functions under about 40 lines; modules focused on one job.
- **No dead code** or commented-out blocks. No `print` debugging left behind.
- **No magic numbers:** name them as constants (for example `CACHE_TTL_SECONDS = 900`) or put them in a documented table (emission factors, AQI breakpoints).
- Comments explain **why**, not what.

## 2. Python

| Rule | Detail |
|---|---|
| Version | Python 3.12+ |
| Formatter and linter | `ruff format` + `ruff check` (config in `pyproject.toml`) |
| Line length | 100 |
| Typing | Type hints on all public functions; `from __future__ import annotations` |
| Docstrings | Google style on public modules, classes and functions |
| Naming | `snake_case` functions and variables, `PascalCase` classes, `UPPER_SNAKE` constants, `_private` helpers |
| Imports | Standard library, then third-party, then local (ruff `I` rules); absolute imports from `app.` |
| Errors | Raise specific exceptions; catch narrowly; never use bare `except:` |
| Async | Async for I/O (httpx, Anthropic); engine functions are **sync and pure** |
| Models | Pydantic v2 with `model_config = ConfigDict(extra="forbid", frozen=True)` where it makes sense |
| Logging | `logging` module, structured key=value; no personal data |

Ruff rule sets: `E, F, W, I, N, UP, B, S, SIM, RUF` (with `S101` allowed in tests).

### Example
```python
def naqi_sub_index(pollutant: Pollutant, concentration: float) -> int:
    """Return the CPCB NAQI sub-index for one pollutant.

    Args:
        pollutant: Pollutant code, e.g. ``Pollutant.PM2_5``.
        concentration: Concentration in µg/m³ (mg/m³ for CO).

    Returns:
        Sub-index from 0 to 500.
    """
```

## 3. JavaScript (frontend)

| Rule | Detail |
|---|---|
| Modules | Native ES modules (`<script type="module">`), no bundler |
| Style | `const` and `let` (no `var`), strict equality, semicolons, 2-space indent |
| Naming | `camelCase` variables and functions, `PascalCase` classes, `UPPER_SNAKE` constants |
| DOM | Build nodes with `document.createElement` and set `textContent`; **never `innerHTML` with dynamic data** |
| Structure | `api.js` (fetch wrapper), `store.js` (localStorage), `views/*.js` (one per screen), `app.js` (router) |
| Errors | Every `fetch` handles failure and shows a friendly message |

## 4. CSS

- Design tokens only (`tokens.css`); no raw hex values in components.
- BEM-style class names: `.card`, `.card__title`, `.badge--very-poor`.
- Mobile-first media queries.
- No inline styles (the CSP blocks them).

## 5. Tests

- File naming: `tests/unit/test_<module>.py`, `tests/api/test_<endpoint>.py`.
- Test naming: `test_<function>_<scenario>_<expected>`. For example, `test_naqi_pm25_boundary_returns_satisfactory`.
- Arrange, act, assert, with one behaviour per test.

## 6. Git

- **Single branch: `main`.** Never create or push other branches.
- **Conventional Commits:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `style:`, `ci:`
  - For example, `feat(engine): add NAQI sub-index calculation`
- Small, frequent commits; push regularly (the commit history shows our process).
- Never commit `.env`, `.venv/`, `__pycache__/`, or large or binary files.

## 7. Pre-commit checklist

```bash
ruff format .
ruff check .
pytest
```
