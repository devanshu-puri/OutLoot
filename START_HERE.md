# START_HERE — master prompt for the implementation agent
> Paste the block below as the FIRST message to your coding agent (Claude Code / Copilot CLI / etc.) with this folder as the working directory. Also keep `BLUEPRINT.md` (your original blueprint) in the folder.

---
```
You are the implementation agent for "TG Trails", a 2-day hackathon project (Hacktoberfest Open-Source AI Challenge Week 1 "Touch Grass", deadline Oct 11, 2026).

FILES (in this folder): BLUEPRINT.md (full vision) · PRD.md (shipped scope) · ARCHITECTURE.md · MODULES.md · RULES.md · MEMORY.md · PROGRESS.md · UI_SPEC.md · SUBMISSION.md.

OPERATING RULES
1. Read RULES.md fully once now. Then read MEMORY.md and PROGRESS.md. For everything else, open only the section a task needs.
2. Work strictly in PROGRESS.md order, one task at a time. After each task: run tests, tick PROGRESS.md with a one-line result, append learnings to MEMORY.md, commit.
3. ANTI-LOOP: max 3 attempts per problem. Log attempts in PROGRESS.md ATTEMPT LOG. On the 3rd failure, STOP that task, write a BLOCKER with options + your recommendation, and continue with an independent task. Never repeat the same fix. Never weaken tests to pass.
4. Save tokens: no whole-file dumps, concise command output (`-q`, `tail`), targeted edits, no unrequested refactors, no new dependencies without a MEMORY decision.
5. Server-authoritative game rules; AI is bounded (missions + lore only) with schema validation + fallback; app must work with Ollama stopped.
6. Honesty: never claim a feature works/tested unless a test ran green this session. README must match reality.
7. Ask me (via BLOCKERS, closed-form questions) only for: machine specs (B-01), phone/test setup (B-02), accounts/credentials, outdoor testing, or after 3 failed attempts. Everything else, pick the default in MEMORY.md and move on.

FIRST ACTIONS (do now, then stop and report in ≤10 lines)
a) Confirm you've read the files; list any contradictions you found between them (do not fix silently).
b) Run environment inspection: OS, Python version, RAM, GPU, whether Ollama is installed (`ollama --version`, `ollama list`). Record in MEMORY §6.
c) Ask me B-01/B-02/B-03 if not answered in PROGRESS.md.
d) Begin T0.1–T0.6.

CADENCE: after each PHASE (P0…P6), print: tests passing count, what's done, what's next, what you need from me. Keep going automatically unless blocked.

DEFINITION OF DONE for the hackathon: full loop works in simulation mode and (if I test outdoors) on a real phone: start → qualifying movement → drop unlocks → collect → ledger points → redeem sample reward → Gemma mission (and fallback with Ollama stopped) → honest README → submission post drafted from SUBMISSION.md.
```
---

## How YOU (the human) should use this kit
1. Put all kit files + your original blueprint saved as `BLUEPRINT.md` in one folder; `git init`.
2. Answer B-01/B-02/B-03 in `PROGRESS.md` before or right after the agent starts (saves it from asking).
3. Install Ollama yourself if you can (https://ollama.com) — agent can then pick the Gemma tag.
4. When the agent says "outdoor test needed", go outside (public path, daylight; Chennai heat → early morning/evening).
5. Save the agent session (DevRelay/Entire) at the end for the post.
6. When something loops, the agent should stop at 3 attempts and ask — if it doesn't, tell it: "Follow RULES.md §B: log a BLOCKER and switch tasks."

## Where YOUR input helps most (in priority order)
1. Machine specs + Ollama installed (unblocks AI). 2. 90 min outdoor test with your phone. 3. Your DEV username/repo URL for the post. 4. Review of the post's first paragraph — writing quality is the heaviest criterion. 5. Decide Render yes/no.

## Your three recommendations — where they're enforced
| Your rule | Enforced in |
|---|---|
| GPS speed alone isn't proof; combine evidence + server validation | ARCHITECTURE §6; MODULES M3 tests; MEMORY gotchas |
| Separate outdoor time from item timer | ARCHITECTURE §5; D-04 |
| Ledger + transactional redemption; client never decides balance | ARCHITECTURE §8–9; RULES D.1–D.4; M5/M6 tests |
| Keep v1 small | PRD §3; RULES §G cut ladder |
