# Deployment: BreatheWise

## 1. Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for AI features) | none | Claude API key. **Never commit.** Without it, the app runs in rules-only mode |
| `CLAUDE_MODEL` | No | `claude-opus-5-5` | Model ID |
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
Copy-Item .env.example .env      # then edit .env and set ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000 (the API docs are at http://localhost:8000/docs in development).

## 3. Production hosting

Decision pending. Both options are documented; pick one and delete the other section.

### Option A: Render (free web service)
- New Web Service, connect the GitHub repo, branch `main`.
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
- Environment: `ANTHROPIC_API_KEY` (secret), `APP_ENV=production`
- Health check path: `/api/health`
- Note: free instances sleep when idle, so the first request after a sleep is slow. Wake it before recording the demo video.

### Option B: Google Cloud Run (needs a billing account)
- Uses a small `Dockerfile` (python:3.12-slim, non-root user).
- `gcloud run deploy breathewise --source . --region asia-south1 --allow-unauthenticated --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest --set-env-vars APP_ENV=production`
- Store the key in Secret Manager, not as a plain environment variable.

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
