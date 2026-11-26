# Security: BreatheWise

Security goal: **safe and responsible implementation.** Protect secrets, protect users' health data, resist abuse, and keep the AI grounded.

## 1. Threat model (summary)

| Asset | Threat | Control |
|---|---|---|
| Anthropic API key | Leak via repo, logs or the frontend | Server-side only, `.env` git-ignored, secret scanning |
| API budget | Abuse, scripted flooding | Per-IP rate limits, input size caps, AI loop caps |
| User health data | Exposure on the server or in logs | No server storage; redacted logging; minimal data to the AI |
| AI behaviour | Prompt injection, made-up figures | Tool-grounded numbers, separate instructions, output schema validation |
| Frontend | XSS from AI or user text | No `innerHTML` for dynamic text, strict CSP |
| Upstream APIs | Slow or failing responses | Timeouts, cache, stale fallback |

## 2. Secrets management

- `ANTHROPIC_API_KEY` is read **only** from the environment (`app/config.py`, pydantic-settings, `SecretStr`).
- `.env` is in `.gitignore`. `.env.example` holds placeholder values only.
- The key never goes to the browser. All Claude calls are server-side.
- The key is never logged. `SecretStr` hides it in reprs.
- Before each push: `git diff --cached` review, and GitHub secret scanning is on (public repo).
- If a key leaks: revoke it in the Anthropic Console immediately, then rotate.

## 3. Input validation

- Every endpoint uses Pydantic models with `extra="forbid"`, strict types and bounded ranges:
  - `lat` −90..90, `lon` −180..180 (rounded to 2 decimals)
  - Geocode `q`: 2–80 characters, pattern `^[\w\s,.\-']+$` (Unicode letters allowed)
  - Members: at most 10; names at most 40 characters; enums for age group, conditions and modes
  - Chat: at most 20 messages, each at most 1,000 characters, roles limited to `user` and `assistant`
  - Simulator numbers: each field has documented min and max values (`api.md`)
- Request body size is capped at 32 KB.
- Path or query values are never put into shell commands, file paths or SQL. There is no database.

## 4. Rate limiting and abuse prevention

- In-memory sliding-window limiter per client IP (limits in `api.md`). Returns `429` with `Retry-After`.
- The AI tool loop is capped at **4 iterations** per chat request; `max_tokens` is bounded.
- Timeouts: Open-Meteo 8 s; Anthropic 30 s; overall request 45 s.

## 5. HTTP security headers

Set by `app/security/headers.py` on every response:

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://unpkg.com;
                         style-src 'self' https://unpkg.com https://fonts.googleapis.com;
                         font-src 'self' https://fonts.gstatic.com;
                         img-src 'self' data: https://tile.openstreetmap.org https://server.arcgisonline.com https://unpkg.com;
                         connect-src 'self'; object-src 'none'; base-uri 'self';
                         frame-ancestors 'none'; form-action 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(self), camera=(), microphone=()
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains   (production, HTTPS only)
```

- **No inline scripts or styles**, so the CSP can stay strict.
- The map library (Leaflet 1.9.4) loads from unpkg **pinned to one version with Subresource Integrity hashes**, so a changed file is refused by the browser. Map tiles come from OpenStreetMap (streets) and Esri World Imagery (satellite), with attribution shown. If the library can't load, the map hides and the text summary still works.
- Map popups and tooltips are built as DOM nodes, never HTML strings.
- CORS: same-origin only. No wildcard origins.
- `/docs` and `/openapi.json` are turned off in production.

## 6. Frontend safety (XSS)

- Dynamic text (AI replies, names, city names) is rendered with `textContent` or created DOM nodes. **Never `innerHTML`** with untrusted data.
- AI replies are plain text. If light formatting is needed, a tiny allowlist renderer handles **bold** and line breaks only.
- No third-party scripts or analytics. The only external resources are Leaflet (SRI-pinned), map tiles (OpenStreetMap streets, Esri satellite imagery and labels) and Google Fonts (Manrope, Nunito Sans). Fonts fall back to system fonts if blocked.

## 7. AI safety and prompt-injection defence

- **Separation:** system prompts hold the instructions. User text only goes into `user` messages, never into the system prompt.
- **Grounding:** Claude gets numbers only through tools that run the deterministic engine. The system prompt tells it never to state figures it didn't get from a tool or the facts object.
- **Tool safety:** tool inputs are validated against strict JSON schemas (`strict: true`) and then validated again in Python before the engine runs. Tools are **read-only and side-effect free**.
- **Output validation:** structured outputs (plan, simulator) are parsed and validated with Pydantic. On failure, the rules fallback is used.
- **Scope guard:** the assistant stays on air quality, health precautions and emissions, and politely redirects anything off-topic.
- **Medical boundary:** general guidance only; it refers people to doctors for symptoms or medication changes.
- **Refusals:** a `stop_reason == "refusal"` is handled gracefully, with a fallback and a friendly message.

## 8. Privacy

- No accounts, no cookies, no tracking.
- Profiles live in `localStorage`; the user can clear them with one button.
- Only the minimum data goes to Claude: rounded coordinates, age groups, conditions and an optional nickname.
- Logs record method, path, status and latency. **No bodies, coordinates or chat text.**

## 9. Dependencies and supply chain

- Pinned versions in `requirements.txt`.
- `pip-audit` runs in CI. Dependabot alerts are on in GitHub.
- Minimal dependency set: FastAPI, Uvicorn, Pydantic, pydantic-settings, httpx and anthropic.

## 10. Error handling

- Generic error messages for clients. Stack traces only in server logs, and never in production responses.
- Upstream errors map to `503` with a friendly message.

## 11. Security checklist (before each submission)

- [ ] No secrets in the git history (`git log -p | findstr /i "sk-ant"` returns nothing)
- [ ] `.env` not tracked
- [ ] CSP header present and the app works with no console CSP errors
- [ ] All endpoints reject unknown fields and out-of-range values (tests pass)
- [ ] Rate limiting works (test passes)
- [ ] `pip-audit` clean
- [ ] `/docs` turned off in production
