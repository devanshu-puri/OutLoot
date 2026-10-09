# TG Trails (OutLoot) 🌿✦

> **Hacktoberfest Open-Source AI Challenge (Week 1: "Touch Grass")**  
> An outdoor walking PWA where genuine physical movement unlocks virtual drops and sponsor vouchers, accompanied by private local Gemma AI missions.

---

## 🌟 What is TG Trails?

Most apps optimize for screen time. **TG Trails** is built to minimize it.
1. **Walk outside:** Put your phone in your pocket. The app uses server-authoritative physics checks to qualify genuine pedestrian movement (not GPS jumps or vehicle speeds).
2. **Audio & Haptic Discovery:** When your accumulated movement unlocks a nearby drop, your phone rings with a dual-tone chime and vibration cue.
3. **Collect & Earn:** Step within proximity of the drop to collect items across 5 rarities, backed by an append-only points ledger.
4. **Local AI Missions & Lore:** A locally-hosted open-weight model (**Google Gemma via Ollama**) generates tailored outdoor walking missions and immersive trail lore with strict JSON schema validation, safety filters, and offline fallback.
5. **Redeem Sponsor Rewards:** Spend your non-monetary demo credits in the marketplace to claim sample café discounts and outdoor activity passes.
6. **Screen Time vs Outdoors Proof:** Each completed walk generates an honest summary contrasting your actual outdoors time against active screen interaction.

---

## 🏗 System Architecture & Design

```
Client (Static PWA)          FastAPI Server               Local AI & DB
┌──────────────────┐        ┌────────────────────────┐   ┌───────────────────────┐
│ Leaflet Dark Map │  HTTP  │ • Session State Machine │   │ SQLite (WAL mode)     │
│ One-Glance HUD   │───────>│ • Movement Evaluator   │──>│ • Append-only Ledger  │
│ WebAudio Cues    │ (JSON) │ • Item Spawner & Tx    │   │ • Idempotent Col/Red  │
│ Desk Simulator   │        │ • AI Schema & Filter   │   └───────────────────────┘
└──────────────────┘        └────────────────────────┘               │
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
| **Desk Simulation Mode** | ✅ Yes | Replay realistic GPS walks via the `SIM MODE` header button |
| **Offline game logic & ledger** | ✅ Yes | Operates on local Wi-Fi / localhost without external internet |
| **Map Tiles** | ⚠️ Online | Requires internet connection unless tiles are cached in browser |
| **Background Location Tracking** | ❌ No | Standard web browsers throttle background geolocation; screen is dimmed instead |
| **Monetary Reward Cashout** | ❌ No | Points and vouchers are non-monetary demo collectibles |

---

## 🚀 Quickstart & Setup

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

### 3. Run the TG Trails Server
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```
Open your browser at [http://localhost:8000](http://localhost:8000).

### 4. Run the Test Suite
```bash
python -m pytest -q
```

---

## 🧪 Simulation Mode

Test the complete walking, unlocking, and collecting loop directly from your desk:
1. Open the web app at `http://localhost:8000`.
2. Click **Allow Location & Start Walk**.
3. Toggle the **SIM MODE** button in the header.
4. Watch the progress ring advance, trigger audio cues, unearth drops, and earn points!

---

## 📄 License & Hackathon Tags
* License: MIT
* Tags: `#devchallenge` `#hf26challenge` `#touchgrass` `#gemma`
