# Deployment: Airly

## 1. Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes (for AI features) | none | Gemini API key (free from Google AI Studio). **Never commit.** Without it, the app runs in rules-only mode |
| `GEMINI_MODEL` | No | `gemini-3.5-flash-lite` | Main model ID |
| `GEMINI_FALLBACK_MODELS` | No | `gemini-3.1-flash-lite,gemini-3.8-flash` | Comma-separated backups tried when the main model is busy |
| `APP_ENV` | No | `development` | `development` or `production` (production turns off `/docs` and turns on HSTS) |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `AIR_CACHE_TTL_SECONDS` | No | `900` | Air-data cache TTL |
| `RATE_LIMIT_ENABLED` | No | `true` | Turn the rate limiter on or off |
| `PORT` | No | `8000` | Port used by hosting platforms |

`.env.example` has the same keys with placeholder values.

## 2. Run locally (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env      # then edit .env and set GEMINI_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000 (the API docs are at http://localhost:8000/docs in development).

## 3. Production hosting

**Chosen: Render (free web service)**, defined in `render.yaml` (a Render Blueprint) at the repo root.

### Deploy with the Blueprint
1. Sign in at https://dashboard.render.com with GitHub.
2. **New → Blueprint**, pick the `Airly` repository (branch `main`), then **Apply**.
3. When asked for `GEMINI_API_KEY`, paste the key, or leave it empty to run in rules-only mode. It can be added later under **Environment**.
4. Wait for the build, then open the `https://airly-xxxx.onrender.com` URL and check `/api/health`.

What `render.yaml` sets:
- Python version from `.python-version` (3.13); build `pip install -r requirements.txt`
- Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`, with `FORWARDED_ALLOW_IPS=*` so rate limits see the visitor's IP behind Render's proxy
- `APP_ENV=production` (API docs off, HSTS on), health check `/api/health`, auto-deploy on every push to `main`
- Region Singapore (closest free region to India)

**Free-tier note:** the service sleeps after about 15 minutes idle; the first visit after that takes 30–60 seconds. Open the site a minute before judging or recording the video.

## 4. Production checklist

- [ ] `APP_ENV=production` (docs off, HSTS on)
- [ ] API key set as a platform **secret**
- [ ] HTTPS URL works; `/api/health` returns `ok`
- [ ] Security headers present (check in browser dev tools)
- [ ] Dashboard, plan, chat and simulator all work on the live URL
- [ ] Rules-only fallback works (test by temporarily removing the key)

## 5. Repository limits (hackathon rules)

- **Size under 10 MB.** Check with `git count-objects -vH` (look at `size-pack`).
- **Single branch `main`.** `git branch -a` should list only `main` and `origin/main`.
- **Public** repository.
- Never commit `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`, or videos and screenshots larger than about 200 KB.
