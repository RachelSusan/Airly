# Data and Storage: BreatheWise

## 1. Storage decision: no server-side database

BreatheWise deliberately runs **without a server database**.

| Data | Where it lives | Why |
|---|---|---|
| Family profiles, lifestyle, saved location | **Browser `localStorage`** | Personal and health-related data never leaves the device except in the request that needs it. Nothing is stored on the server |
| Checklist tick state (per day) | Browser `localStorage` | Per-device convenience; reset daily |
| Chat history | Browser memory (session only) | Not saved; sent with each request so the conversation has context |
| Air-quality and weather responses | **Server in-memory TTL cache** | Public data; cut latency and upstream calls |
| Geocoding results | Server in-memory TTL cache | Public data |

**Benefits:** a smaller attack surface, no personal data to breach, no database to run, and simpler deployment.
**Trade-off:** profiles don't sync between devices. That's acceptable for this scope; see section 6.

## 2. Client-side data model

Stored under one versioned key, `breathewise:v1`.

```jsonc
{
  "version": 1,
  "location": {
    "name": "New Delhi, Delhi, India",
    "lat": 28.61,            // rounded to 2 decimals
    "lon": 77.21
  },
  "household": {
    "commute": { "mode": "petrol_car", "distance_km": 12, "days_per_week": 5, "depart_hour": 9 },
    "school":  { "start_hour": 8, "end_hour": 14 },          // optional
    "home":    { "has_purifier": true, "cooking_fuel": "lpg", "smoker_at_home": false }
  },
  "members": [
    {
      "id": "m_7f3a",        // random client id, not personal
      "name": "Aarav",        // nickname is fine; optional
      "age_group": "child",   // infant | child | teen | adult | senior
      "conditions": ["asthma"], // asthma | copd | heart | pregnancy | allergy
      "outdoor_activities": ["play", "cycling"]
    }
  ],
  "checklist": {
    "date": "2026-11-26",
    "done": { "m_7f3a": ["carry_inhaler", "n95_outdoors"] }
  },
  "preferences": { "aqi_standard": "naqi", "theme": "system" }
}
```

### Enumerations

| Field | Values |
|---|---|
| `age_group` | `infant` (0–1), `child` (2–12), `teen` (13–17), `adult` (18–64), `senior` (65+) |
| `conditions` | `asthma`, `copd`, `heart`, `pregnancy`, `allergy` |
| `commute.mode` | `walk`, `cycle`, `petrol_car`, `diesel_car`, `cng_car`, `ev_car`, `petrol_2w`, `ev_2w`, `auto_cng`, `bus`, `metro`, `wfh` |
| `cooking_fuel` | `lpg`, `png`, `electric`, `biomass`, `kerosene` |

### Rules
- Max 10 members per household. Names are at most 40 characters. Numbers have bounded ranges (validated again on the server).
- Schema version `1`. A migration function upgrades older versions on load.
- **Clear my data:** one button removes the `breathewise:v1` key.

## 3. Server-side domain models (in memory, per request)

Defined as Pydantic models in `app/models/`.

| Model | Key fields |
|---|---|
| `Location` | `lat`, `lon`, `name?` |
| `PollutantReading` | `pm2_5`, `pm10`, `no2`, `o3`, `co`, `so2` (µg/m³; CO in mg/m³ after conversion) |
| `WeatherReading` | `temperature_c`, `humidity_pct`, `wind_kmh`, `precip_mm` |
| `HourlyPoint` | `time`, `pollutants`, `weather`, `aqi`, `category`, `dominant` |
| `AirSnapshot` | `location`, `current: HourlyPoint`, `forecast: list[HourlyPoint]`, `fetched_at`, `stale` |
| `Member` | `id`, `name?`, `age_group`, `conditions[]`, `outdoor_activities[]` |
| `MemberRisk` | `member_id`, `sensitivity`, `risk_level`, `limits`, `alerts[]` |
| `TimeWindow` | `activity`, `start`, `end`, `advice` (safe, caution or avoid), `avg_aqi` |
| `ChecklistItem` | `id`, `member_id`, `text`, `reason` |
| `ScenarioResult` | `scenario_id`, `inputs`, `co2_kg`, `pm25_g`, `nox_g`, `exposure_change_pct?`, `period`, `assumptions[]`, `sources[]` |

## 4. Cache

| Key | TTL | Size cap |
|---|---|---|
| `air:{lat2}:{lon2}` | 15 min | 500 entries (LRU) |
| `geo:{query_lower}` | 24 h | 1,000 entries (LRU) |

- An in-process async cache with a lock per key, so concurrent requests don't call upstream twice.
- If upstream fails and an expired entry exists, serve it with `stale: true` for up to 2 hours.

## 5. Data retention and privacy

- The server **persists nothing**. Logs hold no coordinates beyond 2 decimals, no names, no conditions, and no chat text.
- Data sent to the Anthropic API holds only what the answer needs: rounded location, age groups and conditions, and nicknames only if the user typed them. No email, phone or exact address.

## 6. Future (out of scope)

If accounts or multi-device sync are needed later, use a managed database (for example PostgreSQL or Firestore), encrypt health fields, and add consent and deletion flows.
