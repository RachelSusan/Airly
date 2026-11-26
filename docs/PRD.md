# Product Requirements Document: BreatheWise

| | |
|---|---|
| **Product** | BreatheWise: Urban Air Quality Assistant |
| **Challenge** | PromptWars Virtual, Challenge 6 |
| **Deadline** | 29 Nov 2026, 11:59 PM IST |
| **Status** | Draft v1 |

## 1. Problem statement

> Create a GenAI-powered assistant that helps families and communities navigate severe winter smog and urban air pollution. The application should suggest low-emission daily routines, indoor air quality hacks, and sustainable alternatives tailored to their location and lifestyle, while clearly explaining the direct impact of their choices.

## 2. Goals

1. **Protect:** help families cut their exposure to harmful air, especially children, elderly people and people with respiratory conditions.
2. **Plan:** turn hourly AQI forecasts into concrete, time-based daily decisions.
3. **Reduce:** encourage low-emission choices and show their measurable impact.
4. **Explain:** every recommendation states *why* and *what it changes*, in simple language.

## 3. Non-goals

- Medical diagnosis or treatment advice.
- Predicting changes in local AQI from individual actions.
- Running our own sensors or a historical data warehouse.
- User accounts and server-side profile storage.

## 4. Target users (personas)

| Persona | Need |
|---|---|
| **Priya, a parent of two (ages 6 and 10)** | "Can the kids play outside after school? When is the safest time?" |
| **Arjun, 28, runs every morning** | "When can I jog without breathing in smog?" |
| **Meena, 67, has asthma** | "What precautions do I need today? Should I open the windows?" |
| **A community or RWA volunteer** | "What difference would it make if our society drove less or planted trees?" |
| **A school coordinator** | "Which periods are safe for outdoor sports this week?" |

## 5. Features and requirements

### Core: location and live dashboard
| ID | Requirement | Priority |
|---|---|---|
| C1 | City search (geocoding) and browser geolocation | Must |
| C2 | Current AQI (Indian NAQI) with category, dominant pollutant, PM2.5, PM10, NO₂, O₃, CO, SO₂ | Must |
| C3 | Current weather: temperature, humidity, wind speed, precipitation | Must |
| C4 | 24-hour AQI forecast timeline | Must |
| C5 | Indoor air tips and sustainable alternatives, each with its impact | Must |

### Module 1: AI Air Quality Assistant
| ID | Requirement | Priority |
|---|---|---|
| A1 | Natural-language chat about air safety and activities | Must |
| A2 | Answers use live AQI, weather, forecast and family profiles (through tool calls) | Must |
| A3 | Handles "Is it safe to jog now?", "Can my children play outside?", "Should I open my windows?" | Must |
| A4 | Simple language with a short reason, no jargon | Must |
| A5 | Suggested quick-question chips | Should |
| A6 | Rule-based fallback answer when the AI is unavailable | Must |

### Module 2: Smart Daily Routine Planner
| ID | Requirement | Priority |
|---|---|---|
| P1 | Best time windows for walking, jogging and outdoor exercise | Must |
| P2 | Safer commuting hours | Must |
| P3 | Indoor alternatives when no outdoor window is safe | Must |
| P4 | School activity planner (school hours in, safe recess and sports slots out) | Should |
| P5 | Plan refreshes when new forecast data arrives and highlights changes | Should |

### Module 3: Family Protection Profiles
| ID | Requirement | Priority |
|---|---|---|
| F1 | Create, edit and delete family members (name or nickname, age group, conditions) | Must |
| F2 | Risk level and activity limits per member | Must |
| F3 | Extra precautions for asthma, COPD, heart conditions, pregnancy and elderly people | Must |
| F4 | Children's outdoor activity alerts | Must |
| F5 | Personal daily protection checklist that can be ticked off | Must |
| F6 | Profiles stored only in the browser | Must |

### Module 4: AI What-If Pollution Simulator
| ID | Requirement | Priority |
|---|---|---|
| W1 | Preset scenarios: avoid peak traffic, 1,000 families drive less, community tree planting, petrol to public transport | Must |
| W2 | Adjustable inputs (distance, days per week, number of families, number of trees) | Must |
| W3 | Shows estimated changes in CO₂, PM2.5 and NOₓ emissions, and in personal exposure | Must |
| W4 | Lists the assumptions and sources behind every result | Must |
| W5 | Never claims a change in local AQI | Must |
| W6 | Claude writes a plain-language explanation of the computed result | Must |

## 6. User stories

- As a **parent**, I want to know if my children can play outside today, so I can plan their afternoon safely.
- As a **runner**, I want the cleanest hour to jog, so I don't breathe heavy smog.
- As a **person with asthma**, I want a checklist of precautions, so I don't forget my inhaler or mask.
- As a **commuter**, I want to know when traffic-related pollution is lowest, so I can shift my travel time.
- As a **community member**, I want to see how much a group action cuts emissions, so I can persuade neighbours.

## 7. Success criteria

| Criterion | Target |
|---|---|
| Problem alignment | All 4 modules plus core working end to end |
| Response time | Dashboard under 1.5 s (cached); AI answer under 8 s |
| Reliability | Every AI feature has a working fallback |
| Accessibility | WCAG 2.2 AA; full keyboard use; screen-reader tested |
| Testing | Engine coverage ≥ 90%; overall ≥ 80% |
| Security | No secrets in repo; all inputs validated; rate limiting on |
| Repo | Under 10 MB; single `main` branch; public |

## 8. Constraints

- At most 3 submissions, a public GitHub repo under 10 MB, a single branch.
- GenAI is mandatory, using the Anthropic Claude API.
- A demo video is mandatory (unlisted YouTube or shared Drive link).
- No GCP credits are provided.

## 9. Open items

- Deployment target (Render or Cloud Run): see `deployment.md`
- Extra options to be planned later
