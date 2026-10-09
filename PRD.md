# PRD — TG Trails (working title)

> Hackathon: Hacktoberfest Open-Source AI Challenge Week 1 — "Touch Grass". Deadline: **Oct 11, 2026**.
> Source of truth for vision: `BLUEPRINT.md` (the user's original blueprint). This PRD is the **scoped-down, shippable** version.

## 1. One-line pitch
Walk outside, collect virtual items that only appear when you've really moved, earn points, redeem a sample sponsor reward. A local open-weight model (Gemma via Ollama) writes your walk's missions and item lore. The screen is the shortest part of the experience.

## 2. Judging fit (what we optimise for)
| Criterion | Our answer |
|---|---|
| Writing quality (most weight) | Honest, specific post: what worked, what failed, a real outdoor test with numbers |
| Relevance to theme | Whole loop is about leaving the screen; audio/haptic cues; short summary screen |
| Creativity | Movement-earned drops + sponsor marketplace + local-AI missions |
| Technical execution | Server-authoritative ledger, idempotency, tested state machine, AI fallback |
| Partner tech | **Gemma** (core). **Entire/DevRelay** session shared. Render = optional stretch only |

## 3. Locked MVP (v0.1) — "deliberately small"
MUST (demo-critical):
1. Prototype user (no signup; device installation id + token).
2. Map (Leaflet + OpenStreetMap) with user dot and item markers.
3. Session start / pause / end.
4. Movement qualification **server-side** from timestamped GPS samples.
5. Collection-cycle timer based on **accumulated qualifying movement seconds** (not wall-clock).
6. 5 item rarities in config (`config/game.yaml`), procedural spawn near user.
7. Collect endpoint: proximity + eligibility + idempotency key → ledger entry.
8. Points balance derived from ledger.
9. Marketplace with 3–4 seeded sample rewards; one atomic redemption → unique code.
10. **One real AI feature:** mission + item-lore generator (Gemma/Ollama), JSON-schema validated, deterministic fallback.
11. Simulation mode (replay a GPX/JSON walk) so it can be demoed and tested at a desk.
12. Tests for: state machine, movement qualification, double-collect, double-redeem, AI invalid output.

SHOULD (only if MUST all done + tested): session history, daily cap, admin seed script UI.
WON'T (v0.1): sponsor dashboard, friends, leaderboards, real payments, native app, offline sync of point awards, background location.

## 4. Users
- **Player** (primary): student/office worker who wants a reason to go for a 15–30 min walk.
- **Admin** (script/CLI only in MVP): seeds rewards and item values.
- **Sponsor**: represented by seeded sample rewards only. No real sponsors implied.

## 5. Key product rules (resolved defaults — see MEMORY.md for rationale)
- Points are **non-transferable, non-cash gameplay credits**. No monetary value implied. Sample rewards are labelled "demo".
- Walking-focused MVP. Stationary time **pauses the cycle timer**; it never invalidates the session.
- Backend decides eligibility, points, redemption. Client never sends a balance or a "success".
- AI never decides points, ownership, eligibility, fraud, or location truth.
- App fully playable with Ollama off (fallback missions).
- Never ask users to look at the phone while moving: cues are audio/vibration; screen shows a one-glance state.

## 6. Success demo (what the video must show)
1. Start session (≤2 taps). 2. Phone in pocket / real outdoor walk. 3. Buzz: "item ready". 4. Collect near marker. 5. Points go up. 6. Redeem sample reward, see code. 7. Kill Ollama → app still works with fallback mission. 8. Short summary: "you spent 14 min outside, 3 min on screen".

## 7. Honest limitations to publish
- GPS can't prove identity; this is an evidence estimate.
- Browser PWA: location only works while the page is foregrounded/screen on (no reliable background GPS). State this plainly.
- Map tiles need internet unless pre-cached; AI + game logic run locally.
- Reward codes are demo, not redeemable.
