# SUBMISSION — DEV post skeleton (fill AFTER building; every number must come from MEMORY §6)
> Writing quality is weighted most. Rules: first-person, specific, honest about failures, short paragraphs, no hype, no claims we didn't test. Aim ~900–1400 words + 3–5 images + 1 video.

## Writing checklist
- [ ] Opens with a concrete moment (e.g. "My phone buzzed at minute 5 of a walk and I hadn't looked at it once.")
- [ ] One clear thesis: *open-weight AI + deterministic game rules = a screen-light game*
- [ ] A real outdoor test with real numbers (duration, distance, drops, battery, GPS issues)
- [ ] One genuine failure + what you changed (e.g. GPS drift near buildings counted as walking → added jitter rule)
- [ ] "Why open" with at least 3 concrete points (below)
- [ ] Limitations section (browser background GPS, tiles need internet, not anti-cheat-proof)
- [ ] Don't claim partner usage you didn't do

## Post (copy into DEV editor; keep the template's first line)
```markdown
*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built
TG Trails is a walk-to-collect game. You start a session, put the phone away, and drops only unlock after you've really moved — measured by the server from GPS evidence, not by a countdown. Collect, earn points, redeem a (demo) sponsor reward. A local Gemma model writes your mission and item lore. Built for people who want a reason to take a 15-minute break. {{ONE LINE: who tested it and where}}

## Demo
{{VIDEO or deployed link}}  — {{what the video shows in 1 line}}

## Code
{% embed https://github.com/{{user}}/{{repo}} %}

## How I Built It
- **Open model:** Gemma ({{exact tag}}) served by Ollama on {{machine}}. Cold {{x}} s / warm {{y}} s per mission.
- **What the model does:** mission + item lore only, as JSON validated against a schema, filtered for unsafe suggestions, 8 s timeout, fallback pack of {{n}} missions. Turn Ollama off and the game still plays.
- **What the model never does:** points, eligibility, redemption, fraud calls. Those are deterministic, in an append-only ledger with idempotency keys.
- **Movement:** timer counts *qualifying movement seconds*, not elapsed time. Rules: accuracy ≤30 m, 0.5–3.5 m/s, gap ≤30 s, min displacement 75 m.
- **Stack:** FastAPI + SQLite + Leaflet/OSM, no build step. {{n}} tests.
{{DIAGRAM image of architecture}}

### The outdoor test
{{Date, place type, 15+ min, distance, drops, battery, screenshot}}. {{What went wrong, e.g. drift}}. {{What I changed}}.

## Why Does Open Innovation Matter?
1. **Privacy:** location-adjacent prompts never leave the machine; the model runs where the data is.
2. **Swap & tune:** one config line changes the model; I tried {{models}} and measured {{difference}}.
3. **Cost & reliability:** zero per-call cost; works with no API key and degrades to fallback instead of failing.
4. {{one honest trade-off: smaller models gave blander lore / needed schema retries {{n}}% of the time}}

## Limitations
Browser GPS stops when the screen locks (wake lock mitigates); map tiles need internet unless cached; GPS can't prove identity — this estimates a break; rewards are demo.

## My Agent Session
{% agent_session {{ID}} %}

## Prize Categories
- Best Use of Gemma — core of the mission engine.
- Best Use of Entire — {{only if session shared}}
{{Remove any not truly used.}}
```

## Assets to capture while building
1. Architecture diagram (export the Mermaid from ARCHITECTURE §2) 2. HUD screenshot 3. Collect sheet 4. Marketplace 5. Outdoor photo (no faces) 6. Terminal showing `ollama list` + latency log 7. pytest summary
## Video script (≤ 90 s)
0–10 s hook outdoors · 10–30 s start & phone away · 30–45 s buzz + collect · 45–60 s points + redeem · 60–75 s kill Ollama → fallback · 75–90 s "why open" line.
