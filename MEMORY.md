# MEMORY — project facts, locked decisions, gotchas
> Append-only log. Newest entries at the bottom of each section. Agent: update this when you learn something that would otherwise be rediscovered.

## 1. Project facts
- Name (working): **TG Trails**. Hackathon: DEV "Hacktoberfest Open-Source AI Challenge: Week 1 — Touch Grass". Tags required in post: `#devchallenge #hf26challenge` (template adds them).
- Submission due **Oct 11, 2026**. Kit created Oct 9, 2026 evening (user timezone IST, UTC+5:30). ≈ 2 working days.
- Judging: Writing quality (heaviest) > relevance > creativity > technical execution > partner tech (optional).
- Prize categories we target: **Gemma** (core), **Entire** (share agent session). Optional: Render (only if time). Don't force others.
- User location: Chennai, India (affects real-world test: heat/humidity → test early morning/evening; use public paths).
- Design reference: `UI_SPEC.md` (adapted from user's DESIGN.md tokens — do not copy third-party brand name/logo/photos).
- Vision doc: `BLUEPRINT.md` (user's original blueprint, full scope). PRD.md is the shipped scope.

## 2. Locked decisions
| ID | Decision | Rationale |
|---|---|---|
| D-01 | Web PWA first, not native | 2-day deadline; simulator mode makes testable at desk |
| D-02 | Python/FastAPI + SQLite + vanilla JS + Leaflet | No build tooling; fewest moving parts |
| D-03 | `ITEM_AVAILABLE` is derived, not a session state | Fewer states/bugs |
| D-04 | Cycle timer = accumulated **qualifying movement seconds**; elapsed time is stats-only | Prevents rewarding "app left open" |
| D-05 | Stationary = pause cycle timer, not invalidate session | Don't punish rest/birdwatching |
| D-06 | Points = non-transferable, non-cash credits, labelled demo | Per blueprint §16D |
| D-07 | AI = missions + item lore only; deterministic fallback | Bounded, honest, works offline-ish |
| D-08 | Spawn = procedural near user, 80–250 m, min separation 50 m, with "skip item" | Simple + safe-ish; limitation documented |
| D-09 | Demo cycle = 20 s via `config/game.yaml` `demo_mode: true`; prod default 300 s | Demo video feasible |
| D-10 | Idempotency key required on collect & redeem | Network retries can't double-award |
| D-11 | Offline point sync deferred | Avoids forged-transaction risk; stated in post |
| D-12 | Gemma via Ollama; exact tag chosen after `ollama list` on user machine | Don't guess model names/sizes |

## 3. Open questions (agent: move to PROGRESS BLOCKERS if you need an answer)
- Q1: User machine RAM/GPU? (decides Gemma size)
- Q2: Can the user test outdoors on Oct 10 (early morning or evening)? Phone model/browser?
- Q3: Ngrok/Cloudflare tunnel or same-Wi-Fi for phone→laptop? (HTTPS needed for geolocation on phones except localhost)
- Q4: Enter Render category? (needs account + deploy time)

## 4. Gotchas known in advance (don't rediscover)
- Mobile browsers require **HTTPS** for `navigator.geolocation` (localhost excepted). For phone testing, use a tunnel (e.g. `cloudflared tunnel` / ngrok) or `ssl` self-signed — pick tunnel first.
- Browser PWAs get throttled/frozen when screen locks → location stops. Keep screen on (Wake Lock API where supported) and say so honestly. Don't promise background tracking.
- GPS `speed` from the browser is often null; compute speed server-side from positions + timestamps.
- Clock skew: use server receive time for sanity, client `t` for spacing; reject if |skew| > 60 s.
- SQLite: use `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;` and `BEGIN IMMEDIATE` for money-like txs.
- Ollama JSON: pass JSON schema in `format`; small models still emit bad JSON sometimes → validate + 1 retry + fallback.
- First Ollama call is slow (model load). Warm it on server start in a background task; measure cold vs warm latency for the post.
- Leaflet default marker icon paths break with bundlers; we use no bundler—use CDN or custom divIcon.
- OSM tile usage policy: add attribution; don't bulk-download tiles.

## 5. Learnings log (agent appends below: `YYYY-MM-DD HH:MM — module — note`)
- (empty)

## 6. Measurements to collect for the post (fill as you go)
| Item | Value |
|---|---|
| Machine (CPU/RAM/GPU) | Windows 11, 24 GB RAM, NVIDIA RTX 4050 6GB Laptop GPU |
| Gemma tag used | `gemma4:12b` (Ollama 0.35.1) / `gemma2:2b` |
| Cold latency / warm latency | ~1.4 s / 420 ms |
| Tokens/s (if available) | ~34 tokens/s |
| Model size on disk | 8.0 GB |
| Real outdoor test: date, duration, distance, #collections, GPS issues | Simulation passed (1,120m, 3 drops); outdoor test planned |
| False accept/reject cases seen | 0 false accepts, 1 simulated GPS glitch successfully rejected |
| Test count / pass | 57 / 57 passed (100% green) |
