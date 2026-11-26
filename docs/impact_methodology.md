# Impact Methodology: Airly

How Airly calculates AQI, risk, exposure and emission impacts. All of these are **deterministic code** in `app/engine/`. Gemini only explains the results.

> **Honesty rule:** the simulator reports **estimated emission changes** and **personal exposure changes**. It never predicts a change in local AQI, which depends on regional weather, transport of pollution and thousands of sources.

> **Status:** the factor values below are working defaults for the build. Each one **must be checked against its source** before final submission, and `docs/tasks.md` tracks this. If a value changes, update the table, the code constant and the tests together.

## 1. AQI: Indian National Air Quality Index (CPCB)

Sub-index for each pollutant by linear interpolation:

```
I = ((I_hi − I_lo) / (C_hi − C_lo)) × (C − C_lo) + I_lo
AQI = max(sub-indices)          dominant pollutant = argmax
```

| Category | AQI | PM2.5 (µg/m³) | PM10 (µg/m³) | NO₂ (µg/m³) | O₃ (µg/m³) | CO (mg/m³) | SO₂ (µg/m³) |
|---|---|---|---|---|---|---|---|
| Good | 0–50 | 0–30 | 0–50 | 0–40 | 0–50 | 0–1.0 | 0–40 |
| Satisfactory | 51–100 | 31–60 | 51–100 | 41–80 | 51–100 | 1.1–2.0 | 41–80 |
| Moderate | 101–200 | 61–90 | 101–250 | 81–180 | 101–168 | 2.1–10 | 81–380 |
| Poor | 201–300 | 91–120 | 251–350 | 181–280 | 169–208 | 10.1–17 | 381–800 |
| Very Poor | 301–400 | 121–250 | 351–430 | 281–400 | 209–748 | 17.1–34 | 801–1600 |
| Severe | 401–500 | 250+ | 430+ | 400+ | 748+ | 34+ | 1600+ |

Source: CPCB, *National Air Quality Index* (2014).
**Interpolation:** like the CPCB calculator, we interpolate continuously between the upper bounds of each band (for example, PM2.5 30 → 50 and 60 → 100). The Severe band is extended by the width of the Very Poor band, so PM2.5 ≥ 380 µg/m³ gives the maximum of 500. Implemented in `app/engine/aqi.py`.
**Our simplification:** the official index uses 24-hour averages (8-hour for O₃ and CO). We apply the breakpoints to **hourly modelled values** from Open-Meteo to get a near-real-time estimate. This is labelled as an estimate in the UI. Open-Meteo gives CO in µg/m³, which we divide by 1,000 to get mg/m³.

## 2. Sensitivity and risk

| Sensitivity tier | Who |
|---|---|
| **High** | Infants, children with asthma, anyone with asthma, COPD or a heart condition, pregnancy, seniors with any condition |
| **Elevated** | Children, seniors, people with allergies |
| **Standard** | Healthy teens and adults |

| AQI category | Standard | Elevated | High |
|---|---|---|---|
| Good | Safe | Safe | Safe |
| Satisfactory | Safe | Safe | Caution (prolonged exertion) |
| Moderate | Caution (prolonged exertion) | Caution | Avoid strenuous; short, light only |
| Poor | Caution (light only) | Avoid prolonged | Avoid outdoor activity |
| Very Poor | Avoid strenuous | Avoid outdoor activity | Stay indoors |
| Severe | Avoid outdoor activity | Stay indoors | Stay indoors |

Based on CPCB health statements for each category, simplified into the advice states safe, caution and avoid.

## 3. Best time windows

1. Take the hourly forecast for the next 24 hours.
2. Filter by activity constraints: daylight hours for play and walking, school hours for school slots, a commute window around the departure hour ±2 h.
3. Slide a window of `duration_hours` (contiguous hours only) and score it by the **mean AQI**.
4. Pick the lowest-scoring window (the earliest wins ties). Its advice comes from the risk table for the most sensitive participant. **Light** activities (walking, commuting) are assessed one category less severe than **strenuous** ones (jogging, cycling, play).
5. If even the best window is `avoid`, return an indoor alternative.

## 4. Inhaled dose and exposure change

```
dose (µg) = C_PM2.5 (µg/m³) × breathing_rate (m³/h) × duration (h) × (1 − protection)
exposure_change_% = (dose_new − dose_old) / dose_old × 100
```

| Activity | Breathing rate (adult, m³/h) |
|---|---|
| Rest / indoors | 0.5 |
| Walking | 1.2 |
| Cycling | 2.0 |
| Jogging | 3.0 |

Source: US EPA *Exposure Factors Handbook* (2011), ch. 6 (rounded mid-range values).

| Protection | Reduction factor (default) | Note |
|---|---|---|
| None | 0 | |
| Cloth or surgical mask | 0.2 | Loose fit; low filtration |
| N95 / FFP2, well fitted | 0.8 | Lab filtration ≥ 95%; real-world fit lowers it |
| Indoors, windows closed | 0.4 | Indoor/outdoor ratio varies widely |
| Indoors with HEPA purifier (right size for the room) | 0.65 | Range 50–80% in studies |

**Example:** jog at 7 AM (PM2.5 = 180) compared with 2 PM (PM2.5 = 95), 1 h each:
`(95×3 − 180×3) / (180×3) = −47%`. That gives "about 47% less PM2.5 inhaled."

## 5. Emission factors (per km)

`distance_km` in the API is **one-way**. Commutes are counted as a round trip (×2). One year = 52 weeks.

| Mode | CO₂ (kg/km) | PM2.5 (g/km)* | NOₓ (g/km) | Basis |
|---|---|---|---|---|
| Petrol car | 0.170 | 0.012 | 0.060 | Per vehicle-km, single occupant |
| Diesel car | 0.170 | 0.015 | 0.080 | Per vehicle-km |
| CNG car | 0.130 | 0.010 | 0.050 | Per vehicle-km |
| Electric car | 0.110 | 0.008 | 0.000 | Grid electricity (about 0.71 kg CO₂/kWh × 0.15 kWh/km); PM is non-exhaust only |
| Petrol two-wheeler | 0.045 | 0.006 | 0.060 | Per vehicle-km |
| Electric two-wheeler | 0.021 | 0.003 | 0.000 | Grid (0.71 × 0.03 kWh/km) |
| CNG auto-rickshaw | 0.070 | 0.008 | 0.050 | Per vehicle-km, shared → ÷ 1.5 passengers |
| Bus | 0.030 | 0.002 | 0.050 | Per passenger-km |
| Metro | 0.030 | 0.001 | 0.000 | Per passenger-km (grid) |
| Walk / cycle | 0 | 0 | 0 | |

\* PM2.5 includes non-exhaust (brake, tyre and road dust) estimates, which are a large share of traffic PM in Indian cities.

**Sources to verify:** India GHG Program, *India Specific Road Transport Emission Factors* (2015); CEA, *CO₂ Baseline Database for the Indian Power Sector* (grid factor); ICCT India briefs; BS-VI type-approval limits; DMRC sustainability reports.

## 6. Scenario formulas

### `petrol_to_public` / `custom_commute_switch`
```
annual_km = distance_km × 2 × days_per_week × 52
Δ = (EF_to − EF_from) × annual_km          (per pollutant)
```
Example: 12 km, 5 days a week, petrol car to metro. annual_km = 6,240.
CO₂ Δ = (0.030 − 0.170) × 6,240 = **−873.6 kg/year**; PM2.5 Δ = (0.001 − 0.012) × 6,240 = **−68.6 g**; NOₓ Δ = −374.4 g.

### `families_reduce_driving`
```
Δ = families × km_per_day_reduced × days_per_week × 52 × EF_petrol_car (substitute: walk/cycle/public as chosen)
```
Reported as tonnes CO₂ and kg PM2.5 or NOₓ per year. A **comparison** line (for example, "about the yearly CO₂ of N average Indian households' electricity use") is added only when the factor is sourced.

### `avoid_peak_hours`
- Emissions: congestion raises fuel use. Default assumption: **15% lower fuel use off-peak** (a sourced range is to be confirmed).
  `Δ = −0.15 × EF_mode × annual_km`
- Exposure: calculated from the **actual forecast**. In-transit PM2.5 at the peak hour compared with the chosen off-peak hour (section 4), so it's grounded in live data.

### `community_trees`
```
CO₂ absorbed = trees × 21 kg/year × years      (mature tree average; young trees absorb much less)
```
PM2.5 removal by urban trees varies a lot with species, leaf area and placement. We **describe it qualitatively** and give no number.

## 7. What we never output

- "This will reduce your city's AQI by X."
- Health outcome predictions ("you will avoid an asthma attack").
- Any number not produced by these formulas or the live data.

Every simulator result includes `assumptions[]`, `sources[]` and the standard disclaimer.
