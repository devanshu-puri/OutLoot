# PROGRESS — single source of truth for what's done / next / blocked
> Agent: update after EVERY task. Keep this file short. Tick format: `- [x] T0.1 … — result (YYYY-MM-DD HH:MM)`.
> Deadline: **Oct 11, 2026** (post published). Today when kit created: Oct 9, 2026 evening IST.

## STATUS SNAPSHOT
- Current phase: **P0 not started**
- Last green test run: —  (N passed)
- Next task: **T0.1**
- Open blockers needing user: **B-01, B-02** (see below)
- Time check: update "hours used" here → 0 / ~30

## TIME PLAN (≈30 working hours across 2 days; reorder only via MEMORY decision)
| Block | Target | Content |
|---|---|---|
| Fri Oct 9 night | 4–5 h | P0 Foundation, P1 Session+Movement domain, tests green |
| Sat Oct 10 morning | 5 h | P2 Items/Ledger/Market, P3 AI |
| Sat Oct 10 afternoon | 4 h | P4 Frontend + sim mode |
| Sat Oct 10 evening | 1.5 h | **Real outdoor test (user)**, record measurements |
| Sun Oct 11 morning | 4 h | P5 hardening/README/demo video, **post writing** |
| Sun Oct 11 midday | buffer | publish ≥ 3 h before the deadline (timezone of cutoff unknown → treat as early) |

## BLOCKERS (needs user input) — agent adds; user answers inline
- [x] **B-01** What are your machine RAM / GPU, OS? (to pick the Gemma size). → *user:* Windows 11, 24 GB RAM, NVIDIA RTX 4050 6GB Laptop GPU, Python 3.14, Ollama 0.35.1 installed.
- [x] **B-02** Phone model + browser for outdoor test; same Wi-Fi/hotspot or tunnel OK? → *user:* Cloudflare tunnel / ngrok for HTTPS mobile testing.
- [x] **B-03** Enter Render category? (y/n) → *user:* No (focus on local/PWA + Gemma AI first; Render only as stretch).

## ATTEMPT LOG (anti-loop; one row per problem)
| Problem | Att.1 (what/result) | Att.2 | Att.3 → BLOCKER? |
|---|---|---|---|
| — | | | |

## PHASE P0 — Foundation (M0, M1)
- [ ] T0.1 Create repo skeleton per ARCHITECTURE §3, `requirements.txt`, `.env.example`, `.gitignore` (est 20m)
- [ ] T0.2 `settings.py`, `config/game.yaml` + Pydantic loader w/ validation + test (30m)
- [ ] T0.3 `db.py` (WAL, FK, `tx()` ctx using BEGIN IMMEDIATE) + `001_init.sql` from ARCHITECTURE §13 + migration runner + test (45m)
- [ ] T0.4 `GET /api/health` (db, ollama reachable?, model tag) (15m)
- [ ] T0.5 M1 anon auth + token dependency + rate limiter + tests (45m)
- [ ] T0.6 `git init`, first commit, run `pytest -q` green

## PHASE P1 — Session & Movement (M2, M3)
- [ ] T1.1 `domain/states.py` + table-driven tests (legal/illegal) (30m)
- [ ] T1.2 session service + routes: start/pause/resume/end; one ACTIVE per user (60m)
- [ ] T1.3 `domain/geo.py` haversine/destination + tests (20m)
- [ ] T1.4 `domain/movement.py` pure evaluator + **table-driven tests for every reason code** (90m)
- [ ] T1.5 `POST /session/{id}/samples` persists events (TTL fields), updates `cycle_progress_s`, `distance_m` (45m)
- [ ] T1.6 `scripts/sample_walk.json` (realistic walk with noise, stationary stretch, one jump) + `simulate_walk.py` posting to API (30m)

## PHASE P2 — Ledger, Items, Marketplace (M5, M4, M6)
- [ ] T2.1 points ledger service + balance + test (balance==sum property test) (40m)
- [ ] T2.2 item definitions seed + weighted rarity + spawner w/ min separation + tests (60m)
- [ ] T2.3 cycle unlock logic (cycle_progress ≥ required & displacement ≥ min → AVAILABLE) + tests (45m)
- [ ] T2.4 collect tx w/ idempotency, proximity, limits, cooldown + tests: out-of-range, replay, double-spawn, concurrent threads (90m)
- [ ] T2.5 rewards seed + list + redeem tx + tests: insufficient, stock race, expired, replay (75m)
- [ ] T2.6 admin: seed script, adjust-points (audited, ADMIN_TOKEN) (30m)

## PHASE P3 — Open-weight AI (M7)  ⟵ needs B-01
- [ ] T3.1 Install Ollama; `ollama list`; pull smallest suitable Gemma; record tag in MEMORY (30m)
- [ ] T3.2 `services/ai.py` client w/ JSON-schema `format`, timeout 8 s, Pydantic validation (45m)
- [ ] T3.3 safety filter + 1 retry with error feedback + fallback missions JSON (≥12 entries) (40m)
- [ ] T3.4 tests with mocked Ollama: valid, malformed, unsafe, timeout, down (45m)
- [ ] T3.5 warm-up on startup; log cold/warm latency into MEMORY §6 (15m)
- [ ] T3.6 Mission bonus: backend-checked simple criterion (e.g. "walk ≥ X m") awards fixed config bonus — **only if time**, else mission is flavor-only

## PHASE P4 — Frontend PWA (M8)  (follow UI_SPEC.md)
- [ ] T4.1 static serving, `index.html`, tokens in `style.css`, manifest (30m)
- [ ] T4.2 Leaflet map, user dot, item markers (visible when AVAILABLE; ghost optional) (45m)
- [ ] T4.3 Geolocation watcher → batches to `/samples` every 5–10 s; Wake Lock; permission explainer screen (60m)
- [ ] T4.4 HUD one-glance: big state + progress ring + Pause/End; cues (vibrate + short beep) on "item ready"/"collected" (45m)
- [ ] T4.5 `sim.js` simulation mode (replays sample_walk.json via same code path as GPS) (30m)
- [ ] T4.6 Collect flow + error messages ("48 m away") (30m)
- [ ] T4.7 Marketplace screen + redeem + code view (45m)
- [ ] T4.8 Mission card (AI source badge: "Gemma · local" / "Fallback") + session summary ("outside 14 min, screen 3 min") (45m)
- [ ] T4.9 Manual E2E checklist below passes in sim mode

## PHASE P5 — Hardening & Demo (M9)
- [ ] T5.1 TTL purge job for raw samples; privacy text in-app (30m)
- [ ] T5.2 README: setup/run/test, **truthful** what-works / not-working / offline table (45m)
- [ ] T5.3 Real outdoor test by USER (see checklist) → fill MEMORY §6 (≈1.5 h)
- [ ] T5.4 Record demo video (screen + outdoor clip) (60m)
- [ ] T5.5 Final full `pytest -q`; paste count into MEMORY §6

## PHASE P6 — Submission (M10) — see SUBMISSION.md
- [ ] T6.1 Fill post using SUBMISSION.md skeleton; every claim backed by MEMORY §6
- [ ] T6.2 Export agent session (DevRelay/Entire) and embed with `{% agent_session ID %}`
- [ ] T6.3 Add code repo link + video link; double-check tags `#devchallenge #hf26challenge`
- [ ] T6.4 Publish (target: before Oct 11 midday IST)

## MANUAL E2E CHECKLIST (sim mode)
- [ ] Start session → HUD shows ACTIVE · [ ] sim walk advances progress ring · [ ] stationary stretch pauses ring
- [ ] "Item ready" cue fires · [ ] collect far away → "out of range" message, 0 pts · [ ] collect near → +pts once
- [ ] refresh mid-collect (replay key) → no double points · [ ] end session → summary, points kept
- [ ] redeem sample reward → code shown, balance reduced · [ ] redeem again w/ low balance → clear error
- [ ] stop Ollama → new mission shows "Fallback" badge, nothing breaks

## REAL OUTDOOR TEST CHECKLIST (user)
- [ ] Public path/park, daylight, phone on HTTPS tunnel, screen kept on, earphone optional for cues
- [ ] Walk ≥ 15 min incl. 1 stop of ~1 min · [ ] note GPS jumps/drift near buildings · [ ] note battery % start/end
- [ ] Photo/screenshot for the post (no faces/private info)
- [ ] Record: distance, #collections, any wrongly rejected/accepted segments

## DONE LOG (agent appends one line per completed task)
- (empty)
