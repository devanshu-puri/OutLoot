# TG Trails (OutLoot) 🌿✦

> **Hacktoberfest Open-Source AI Challenge (Week 1: "Touch Grass")**  
> An outdoor walking PWA where genuine physical movement unlocks virtual drops and sponsor vouchers, accompanied by private local Gemma AI missions, real-time screen time tracking, and social leaderboards.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/devanshu-puri/OutLoot)
[![OutLoot CI](https://github.com/devanshu-puri/OutLoot/actions/workflows/ci.yml/badge.svg)](https://github.com/devanshu-puri/OutLoot/actions/workflows/ci.yml)

---

## 🌟 What is TG Trails?

Most apps optimize to maximize your screen time. **TG Trails** is built to minimize it.
1. **Walk outside:** Put your phone in your pocket. The app uses server-authoritative physics checks to qualify genuine pedestrian movement (not GPS jumps or vehicle speeds).
2. **Audio & Haptic Discovery:** When your accumulated movement unlocks a nearby drop, your phone rings with a dual-tone chime and vibration cue.
3. **Collect & Earn:** Step within proximity of the drop to collect items across 5 rarities, backed by an append-only points ledger.
4. **Local AI Missions & Lore:** A locally-hosted open-weight model (**Google Gemma via Ollama**) generates tailored outdoor walking missions and immersive trail lore with strict JSON schema validation, safety filters, and offline fallback.
5. **Real-Time Screen Time & Grass Debt:** Built-in engagement heartbeats track when you are active on screens. When you exceed your chosen threshold (e.g. 30m), a "Touch Grass" alert modal prompts you to step outside. Sync your daily phone screen time from **Android Digital Wellbeing** to compute your lifestyle Grass Debt.
6. **Live Leaderboards & Friends Squad:** Compete on real-time leaderboards ranked by Grass Score (`points + (outdoor_mins * 2)`), view your squad's live walk stats, and send instant `🌱 Nudge` alerts to teammates.
7. **Redeem Sponsor Rewards:** Spend your non-monetary demo credits in the marketplace to claim sample café discounts, stickers, and outdoor activity passes.
8. **100% Free Open-Source Maps:** Powered by community OpenStreetMap (OSM) tiles with custom client-side contrast styling — zero API keys and zero commercial watermarks.

---

## 🏗 System Architecture & Design

```
Client (Static PWA)          FastAPI Server               Local AI & DB
┌──────────────────┐        ┌────────────────────────┐   ┌───────────────────────┐
│ Leaflet OSM Dark │  HTTP  │ • Session State Machine │   │ SQLite (WAL mode)     │
│ One-Glance HUD   │───────>│ • Movement Evaluator   │──>│ • Append-only Ledger  │
│ WebAudio Cues    │ (JSON) │ • Screen Time Heartbeat│   │ • Friends & Nudges    │
│ Desk Simulator   │        │ • Item Spawner & Tx    │   │ • Idempotent Col/Red  │
└──────────────────┘        │ • AI Schema & Filter   │   └───────────────────────┘
                            └────────────────────────┘               │
                                        │               ┌───────────────────────┐
                                        └──────────────>│ Ollama + Gemma Local  │
                                                        │ (http://localhost:11434)
                                                        └───────────────────────┘
```

### Key Engineering Guarantees
* **Server-Authoritative Ledger:** Client sends raw timestamped GPS evidence, never outcomes or balances. Balances equal the exact transaction sum.
* **Idempotency & Concurrency:** Double-collects and replay requests are rejected at the database level via unique constraints and `BEGIN IMMEDIATE` transactions.
* **Fault-Tolerant AI:** If Ollama is offline or generates malformed output, the system seamlessly falls back to pre-seeded nature missions without disrupting gameplay.
* **Privacy-First:** High-frequency GPS points are retained only during the active walk and pruned on session completion.

---

## 📊 Truthful Capability Table

| Feature / Capability | Supported? | Details |
|---|---|---|
| **Server-authoritative movement qualification** | ✅ Yes | Speed filters (0.5–3.5 m/s), gap detection, accuracy filters |
| **Idempotent item collection & ledger** | ✅ Yes | Append-only ledger with transactional safety |
| **Local open-weight Gemma missions** | ✅ Yes | Structured JSON output via Ollama with safety rules |
| **Deterministic AI fallback** | ✅ Yes | Works 100% when Ollama is stopped |
| **Real-time Screen Time Tracking** | ✅ Yes | 15s heartbeats, customizable streak threshold, alert modal |
| **Android Digital Wellbeing Sync** | ✅ Yes | Daily hours extractor computes lifestyle Grass Debt |
| **Live Leaderboard & Friends Squad** | ✅ Yes | Ranked by Grass Score with friend nudges |
| **Watermark-Free Maps** | ✅ Yes | 100% free OpenStreetMap standard, dark, and trail styles |
| **Desk Simulation Mode** | ✅ Yes | Replay realistic GPS walks via `SIM Walk` button |
| **Render Cloud Deployment** | ✅ Yes | Ready for 1-click deploy with `render.yaml` |
| **Background Location Tracking** | ⚠️ Screen On | Mobile web browsers throttle background geolocation; screen is kept on via Wake Lock API |
| **Monetary Reward Cashout** | ❌ No | Points and vouchers are non-monetary demo collectibles |

---

## 🚀 Live Deployment on Render

You can deploy TG Trails to Render in one click using Render's Blueprint (`render.yaml`):

1. Click the **Deploy to Render** button above or visit:
   [https://render.com/deploy?repo=https://github.com/devanshu-puri/OutLoot](https://render.com/deploy?repo=https://github.com/devanshu-puri/OutLoot)
2. Render will automatically detect `render.yaml` and configure:
   - **Service Type:** Web Service (Python 3.12)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
3. Click **Apply**. Within 2 minutes, your live URL will be active (e.g. `https://outloot-tgtrails.onrender.com`).
*(When deployed without a local GPU, OutLoot automatically uses its built-in fallback AI mission pack, keeping the game 100% functional).*

---

## 💻 Local Quickstart

### Prerequisites
* Python 3.11+
* [Ollama](https://ollama.com/) (optional, for live AI generation)

### 1. Installation
```bash
git clone https://github.com/devanshu-puri/OutLoot.git
cd OutLoot
pip install -r requirements.txt
```

### 2. (Optional) Run Ollama with Gemma
```bash
ollama run gemma4:12b # or gemma2:2b
```

### 3. Run the Server
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```
Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 4. Run the Test Suite
```bash
python -m pytest tests/
python tests/verify_mvp2.py
```

---

## 🧪 Simulation Mode

Test the complete walking, unlocking, and collecting loop directly from your desk:
1. Open the web app at `http://127.0.0.1:8000`.
2. Click **⚡ SIM Walk** on the home screen.
3. Watch the progress ring advance, trigger audio cues, unearth drops, and earn points!

---

## 📄 License & Hackathon Tags
* License: MIT
* Tags: `#devchallenge` `#hf26challenge` `#touchgrass` `#gemma` `#render`
