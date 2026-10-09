# MODULES — responsibilities, contracts, dependencies
Each module = a vertical slice: `domain/` (pure) + `services/` (DB) + `routers/` (HTTP) + tests. Build in the order shown (M0 → M9).

| # | Module | Owns | Depends on | Est. | Done-when (tests) |
|---|---|---|---|---|---|
| M0 | **Foundation** | repo skeleton, settings, `db.py`, migrations runner, health route, `game.yaml` loader | — | 1 h | `GET /api/health` 200; migration creates all tables; config loads & validates |
| M1 | **Auth/Identity** | anon user + installation token, token dependency, rate limiter | M0 | 0.75 h | token required; bad token 401; rate limit returns 429 |
| M2 | **Session + State machine** | `domain/states.py`, session service, start/pause/resume/end | M1 | 1.5 h | legal transitions pass; illegal raise; end keeps points; one ACTIVE session per user |
| M3 | **Movement** | `domain/geo.py` (haversine), `domain/movement.py`, samples endpoint, movement_events | M2 | 2.5 h | table-driven cases: walking ✔, stationary pause, vehicle speed ✘, teleport ✘, bad accuracy ✘, gap ✘, out-of-order ✘, jitter-in-place doesn't unlock |
| M4 | **Items/Spawn/Collect** | item defs seed, spawner, availability, collect w/ proximity + idempotency | M2, M3, M5 | 2.5 h | out-of-range → no points + clear message; double-collect same key → replay; two different keys same spawn → 2nd rejected; cycle resets |
| M5 | **Points Ledger** | append-only ledger, balance, history | M1 | 1 h | balance == sum; concurrent collect (threads) no dupes |
| M6 | **Marketplace** | rewards seed, list, redeem tx, redemptions list | M5 | 1.5 h | insufficient points ✘ no deduction; stock 1 + two concurrent redeems → exactly one wins; expired ✘; unique codes |
| M7 | **AI (Gemma/Ollama)** | client, prompt, schema, safety filter, retry, fallback, warm-up, metrics | M0 | 2 h | valid JSON ✔; malformed → retry → fallback; unsafe text rejected; timeout → fallback; works with Ollama stopped |
| M8 | **Frontend PWA** | map, HUD, cues, sim, marketplace screen, mission card, summary | M2–M7 APIs | 4 h | manual checklist in PROGRESS; can play full loop in sim mode |
| M9 | **Hardening, README, demo** | rate limits, TTL purge, privacy text, README truthful, demo script, real outdoor test | all | 3 h | README "what works/doesn't" matches reality; demo recorded |
| M10 | **Submission** | blog post, screenshots, video, DevRelay session, tags | M9 | 3 h | post published before deadline |

## Module contracts (signatures the agent should keep stable)
```python
# domain/geo.py
haversine_m(lat1, lon1, lat2, lon2) -> float
destination_point(lat, lon, bearing_deg, dist_m) -> (lat, lon)

# domain/movement.py  (pure)
evaluate_samples(prev_state: MovementState, samples: list[Sample], cfg: MovementCfg)
    -> MovementResult(accepted, rejected: list[(idx, reason_code)],
                      qualifying_s: float, distance_m: float, new_state: MovementState,
                      flags: list[str])

# domain/states.py
transition(current: SessionState, event: SessionEvent) -> SessionState  # raises InvalidTransition

# services/items.py
spawn_next(session_id, origin_lat, origin_lon) -> SpawnedItem
collect(session_id, user_id, spawn_id, lat, lon, accuracy_m, idempotency_key) -> CollectResult

# services/points.py
add_tx(conn, user_id, delta, kind, ref_type, ref_id, note) -> int   # must be called inside caller's tx
balance(conn, user_id) -> int

# services/market.py
redeem(user_id, reward_id, idempotency_key) -> Redemption

# services/ai.py
generate_mission(req: MissionReq) -> MissionResp   # never raises to caller; returns fallback instead
```

## Reason codes (use exactly; tests assert these)
Movement: `LOW_ACCURACY, STALE_SAMPLE, CLOCK_SKEW, GAP_TOO_LARGE, IMPLAUSIBLE_SPEED, VEHICLE_SPEED, STATIONARY, JITTER, OK`
Collect: `OK, REPLAY, NOT_ACTIVE, ITEM_NOT_AVAILABLE, ALREADY_COLLECTED, OUT_OF_RANGE, LOW_ACCURACY, SESSION_LIMIT, RETRY_COOLDOWN`
Redeem: `OK, REPLAY, INSUFFICIENT_POINTS, OUT_OF_STOCK, NOT_ACTIVE, EXPIRED`
AI: `OK, SCHEMA_INVALID, UNSAFE_CONTENT, TIMEOUT, MODEL_DOWN`

## Seed data (config/game.yaml + seed.py)
Items: Common 10 (w 50) · Uncommon 25 (w 28) · Rare 60 (w 14) · Epic 120 (w 6) · Special 200 (event only, w 0 by default).
Rewards (demo, labelled): 5% café discount 100 · Free beverage 350 · Branded sticker pack 600 (stock 3) · Outdoor activity voucher 1500 (stock 1). Starter test user gets 0 points; test helper can grant points via admin adjust (audited).
Limits: max 12 collections/session, 600 pts/session, 1500 pts/day, 5 s retry cooldown, session max 3 h.
