# API Reference: BreatheWise

Base path: `/api` · Format: JSON (UTF-8) · Interactive docs at `/docs` in development only.

## Conventions

- All request bodies are validated with Pydantic. Unknown fields are **rejected** (`extra="forbid"`).
- Coordinates are rounded to 2 decimals on the server.
- Times are ISO 8601 in the location's local timezone.
- AI-backed responses include `"source": "ai" | "rules"`.

### Error format
```json
{ "error": { "code": "upstream_unavailable", "message": "Air quality data is temporarily unavailable. Please try again shortly." } }
```

| Status | Code | When |
|---|---|---|
| 400 | `bad_request` | Malformed input |
| 422 | `validation_error` | Field validation failed (includes `details[]`) |
| 429 | `rate_limited` | Too many requests (`Retry-After` header) |
| 503 | `upstream_unavailable` | Open-Meteo unavailable and no cached data |
| 500 | `internal_error` | Unexpected error (no internal details exposed) |

## Rate limits (per IP)

| Endpoint group | Limit |
|---|---|
| `GET /api/air`, `/api/geocode` | 60 / minute |
| `POST /api/plan`, `/api/simulate` | 10 / minute |
| `POST /api/chat` | 20 / minute |

---

## `GET /api/health`
```json
{ "status": "ok", "version": "1.0.0" }
```

## `GET /api/geocode?q={query}`
`q`: 2–80 characters (letters, spaces, commas, hyphens and periods).
```json
{
  "results": [
    { "name": "New Delhi", "admin": "Delhi", "country": "India", "lat": 28.61, "lon": 77.21, "timezone": "Asia/Kolkata" }
  ]
}
```

## `GET /api/air?lat={lat}&lon={lon}`
```json
{
  "location": { "lat": 28.61, "lon": 77.21, "timezone": "Asia/Kolkata" },
  "current": {
    "time": "2026-11-26T09:00",
    "aqi": 342, "category": "very_poor", "dominant": "pm2_5",
    "pollutants": { "pm2_5": 186.0, "pm10": 298.0, "no2": 64.0, "o3": 18.0, "co": 2.1, "so2": 12.0 },
    "weather": { "temperature_c": 14.2, "humidity_pct": 78, "wind_kmh": 4.1, "precip_mm": 0 }
  },
  "forecast": [ { "time": "2026-11-26T10:00", "aqi": 318, "category": "very_poor", "advice": "avoid" } ],
  "best_window": { "start": "2026-11-26T14:00", "end": "2026-11-26T16:00", "avg_aqi": 188, "advice": "caution" },
  "fetched_at": "2026-11-26T09:04:12+05:30",
  "stale": false
}
```

## `POST /api/plan`
**Request**
```json
{
  "location": { "lat": 28.61, "lon": 77.21 },
  "members": [
    { "id": "m_1", "name": "Aarav", "age_group": "child", "conditions": ["asthma"], "outdoor_activities": ["play"] },
    { "id": "m_2", "age_group": "adult", "conditions": [], "outdoor_activities": ["jogging"] }
  ],
  "household": {
    "commute": { "mode": "petrol_car", "distance_km": 12, "days_per_week": 5, "depart_hour": 9 },
    "school": { "start_hour": 8, "end_hour": 14 },
    "home": { "has_purifier": true, "cooking_fuel": "lpg", "smoker_at_home": false }
  }
}
```
**Response**
```json
{
  "source": "ai",
  "summary": "The air is Very Poor this morning and improves a little after 2 PM.",
  "routine": [
    { "activity": "jogging", "start": "14:00", "end": "15:00", "advice": "caution", "why": "Lowest PM2.5 of the day (~95 µg/m³).", "impact": "About 47% less PM2.5 inhaled than a 7 AM run." }
  ],
  "commute": { "recommended_departure": "10:00", "why": "...", "alternative": { "mode": "metro", "impact": "Saves ~2.0 kg CO₂ per day." } },
  "school": [ { "slot": "Recess 11:00", "advice": "avoid", "alternative": "Indoor games" } ],
  "indoor_tips": [ { "tip": "Keep windows closed until 2 PM", "why": "...", "impact": "..." } ],
  "members": [
    { "member_id": "m_1", "risk_level": "high", "alerts": ["No outdoor play before 2 PM"],
      "checklist": [ { "id": "carry_inhaler", "text": "Carry inhaler", "reason": "Asthma + Very Poor AQI" } ] }
  ],
  "generated_at": "2026-11-26T09:05:00+05:30"
}
```

## `POST /api/chat`
**Request**
```json
{
  "messages": [ { "role": "user", "content": "Is it safe to go jogging now?" } ],
  "context": { "location": { "lat": 28.61, "lon": 77.21 }, "members": [ ] }
}
```
Limits: at most 20 messages, each at most 1,000 characters. Roles are `user` and `assistant` only.

**Response**
```json
{
  "source": "ai",
  "reply": "Not right now. The AQI is 342 (Very Poor). The cleanest time today is 2–4 PM...",
  "tools_used": ["get_current_conditions", "get_forecast_windows"]
}
```

## `GET /api/scenarios`
Lists the preset scenarios with their input schemas and defaults.

## `POST /api/simulate`
**Request**
```json
{ "scenario_id": "petrol_to_public", "inputs": { "distance_km": 12, "days_per_week": 5, "to_mode": "metro" } }
```
**Response**
```json
{
  "source": "ai",
  "scenario_id": "petrol_to_public",
  "result": {
    "period": "year",
    "co2_kg": -873.6,
    "pm25_g": -68.6,
    "nox_g": -374.4,
    "exposure_change_pct": null
  },
  "explanation": "Switching your 12 km commute from a petrol car to the metro avoids about 870 kg of CO₂ a year...",
  "assumptions": ["Petrol car: 0.170 kg CO₂/km (...)", "Metro: 0.030 kg CO₂/passenger-km (...)", "..."],
  "sources": ["..."],
  "disclaimer": "These are estimated emission changes. They do not predict changes in your local AQI."
}
```

| `scenario_id` | Inputs |
|---|---|
| `avoid_peak_hours` | `distance_km`, `days_per_week`, `mode` |
| `families_reduce_driving` | `families` (1–1,000,000), `km_per_day_reduced`, `days_per_week` |
| `community_trees` | `trees` (1–100,000), `years` (1–20) |
| `petrol_to_public` | `distance_km`, `days_per_week`, `to_mode` (`bus`, `metro`, `cycle`, `walk`, `ev_2w`) |
| `custom_commute_switch` | `from_mode`, `to_mode`, `distance_km`, `days_per_week` |
