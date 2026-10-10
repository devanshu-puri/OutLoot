*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

Most fitness or location-based apps commit one of two fundamental mistakes:
1. **They demand screen addiction:** They force you to stare directly at your glass display while navigating busy sidewalks and nature paths, turning an outdoor walk into another session of visual fatigue.
2. **They are trivially spoofed:** They rely on easily faked client timers or step counts that can be simulated by shaking a phone from a desk chair or riding in a subway car.

**OutLoot (TG Trails)** flips this entirely. It is a screen-light, server-authoritative exploration game designed for developers, students, and knowledge workers who spend 8+ hours a day staring at code editors and need a genuine, rewarding reason to step away, disconnect, and touch grass.

### Key Highlights:
* **Server-Authoritative Anti-Spoofing Movement Engine:** The client collects raw GPS breadcrumbs, but never validates its own progress. The server evaluates coordinates against physics constraints (speed between 0.5–3.5 m/s, GPS horizontal accuracy ≤ 30m, sample interval ≤ 30s, and a minimum displacement threshold of 75m) to ensure only genuine outdoor foot travel earns rewards.
* **Local Gemma AI Storytelling & Quests:** A local open-weight **Gemma model** (`gemma2:2b` via Ollama) serves as the game master. It generates dynamic outdoor scavenger quests, walking tips, and mythic relic lore (like *Clover Sprouts*, *Dewdrop Crystals*, and *Ancient Acorns*) without sending any location data to third-party cloud APIs.
* **Active Screen Time Heartbeats & Grass Debt:** A background engagement tracker monitors active mouse, keyboard, and touch interactions. When you exceed your threshold (e.g., 30 minutes of continuous screen time), a frosted-glass **Touch Grass Alert** modal nudges you to take a walk. You can also import daily screen hours from **Google Digital Wellbeing** to calculate your *Grass Debt* (15 outdoor minutes required per hour of screen time).
* **Social Leaderboard, Follow System & Trail Inspector:** Compete on a global leaderboard ranked by Grass Score (`points + outdoor_mins * 2`). Follow teammates, send tactile `🌱 Nudge` alerts to get friends outside, and click **`🗺️ Trail`** on any player to inspect their verified outdoor walking path directly on the retro dark-mode map!
* **Double-Entry Points Ledger & Real Perks:** All points are recorded in an append-only ledger with cryptographic idempotency keys. Redeem points for promotional partner vouchers with unique redemption codes.
* **Zero Commercial API Keys & 100% Open Data:** Built with OpenStreetMap (OSM) and Leaflet using custom CSS dark styling. No Mapbox/Google Maps billing, no watermarks, and no third-party telemetry.

---

## Demo

* **Live Deployed App (Render):** [https://outloot-tgtrails.onrender.com](https://outloot-tgtrails.onrender.com)
* **Local Run:** Run `uvicorn server.main:app --reload` and visit `http://127.0.0.1:8000/`.
* **Zero-Setup PWA:** Fully responsive across mobile browsers and desktops with a retro cyber/pixel aesthetic.

---

## Code

{% github devanshu-puri/OutLoot %}

* **GitHub Repository:** [https://github.com/devanshu-puri/OutLoot](https://github.com/devanshu-puri/OutLoot)
* **License:** MIT Open Source
* **Test Suite:** 61 automated unit and integration tests passing (`python -m pytest`) covering physics filters, ledger accounting, authentication, trail rendering, and local Gemma fallbacks.

---

## How I Built It

OutLoot is built with a focus on simplicity, offline resilience, and zero cloud API dependencies:

### 1. Architecture Overview
```
┌────────────────────────────────────────────────────────┐
│  Frontend (Vanilla HTML5 / CSS3 / Leaflet 1.9.4 OSM)   │
│  • PWA Shell  • Audio Chimes  • Trail Inspector Map    │
└──────────────────────────┬─────────────────────────────┘
                           │ Raw GPS Batches / Heartbeats
┌──────────────────────────▼─────────────────────────────┐
│  Backend (FastAPI / Python 3.12 / Pydantic v2)         │
│  • Movement Evaluator (Haversine & Physics Gates)      │
│  • Double-Entry Points Ledger (Idempotent tx)          │
│  • Social System (Follows, Leaderboard, GPS Tracks)    │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
┌──────────────▼────────────┐ ┌────────────▼─────────────┐
│ SQLite (WAL Mode, ACID)   │ │ Local Gemma AI Engine    │
│ • Users, Drops, Tracks    │ │ (Ollama gemma2:2b +      │
│ • Ledger Transactions     │ │ 12-Mission Fallback Pack)│
└───────────────────────────┘ └──────────────────────────┘
```

### 2. Technologies Used:
* **AI Engine:** Google's **Gemma** open-weight model (`gemma2:2b` / `gemma:7b`) running locally via **Ollama**. Responses are strictly constrained to JSON schemas with prompt sanitization, an 8-second circuit breaker, and an offline fallback pack of 12 hand-crafted missions ensuring 100% uptime even on remote trails without internet.
* **Server & Logic:** Python 3.12, FastAPI, and Pydantic v2 schemas. SQLite in WAL mode with strict foreign key constraints and ACID transaction managers.
* **Mapping:** Leaflet 1.9.4 and OpenStreetMap standard tiles enhanced with CSS inversion filters (`filter: invert(100%) hue-rotate(180deg) brightness(82%) contrast(108%)`), delivering a clean dark cyber aesthetic without commercial API keys or tile watermarks.
* **Screen-Light UX:** Screen Wake Lock API and audio/haptic chimes allow players to keep the app active in their pocket at minimum screen brightness.

---

## Why Does Open Innovation Matter?

1. **Absolute Location Privacy:** Geolocation breadcrumbs and daily movement patterns are deeply personal. Sending real-time coordinates to proprietary cloud AI providers risks leaking sensitive physical routines. By running open-weight Gemma models locally on the device or self-hosted server, your physical whereabouts never leave your custody.
2. **Separation of Determinism and Creativity:** Core game economics (points, anti-spoofing verification, vouchers) must remain 100% deterministic and auditable. Open-source architecture ensures open-weight AI is dedicated solely to creative tasks (quests, lore, and wellbeing coaching), while deterministic code guarantees fairness.
3. **No Hidden Costs, Rate Limits, or Paywalls:** Proprietary APIs inevitably deprecate endpoints, introduce per-token costs, or enforce usage caps. Open-source AI and community OpenStreetMap data make OutLoot completely free to self-host, fork, and operate forever.
4. **Resilience in Nature:** True outdoor exploration often happens in dead zones with zero cellular connectivity. Open-weight models and offline fallback systems ensure the game keeps working whether you are in a downtown park or a secluded mountain ridge.

---

## My Agent Session

OutLoot was designed, implemented, tested, and deployed end-to-end with the assistance of **Antigravity** (Google DeepMind's agentic AI coding assistant). The session coordinated:
- Drafting Pydantic schemas, database migrations, and geodesic haversine algorithms.
- Developing the 61-test verification suite (`pytest`).
- Integrating the local Gemma Ollama interface and fallback pipelines.
- Automating the deployment to Render via infrastructure-as-code (`render.yaml`).
- Interactive trail inspection and social follow mechanics.

You can view the full source code and commit history directly on GitHub:
👉 **[https://github.com/devanshu-puri/OutLoot](https://github.com/devanshu-puri/OutLoot)**

---

## Prize Categories

* **Open-Source AI Challenge Week 1: Touch Grass** (Primary Track)
* **Best Use of Gemma** (Local open-weight Gemma model generating structured JSON quests, seasonal walking tips, and biome relic lore with offline fallback guarantees)
* **Best Use of Render** (Automated infrastructure-as-code deployment on Render serving FastAPI backend and PWA frontend with zero external dependencies)
