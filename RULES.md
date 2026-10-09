# RULES — read once per session, obey always

## A. Token & time economy
1. **Reading order each session (and nothing else unless needed):** `MEMORY.md` → `PROGRESS.md` → only the files named by the *current task*. Do NOT re-read PRD/ARCHITECTURE end to end each time; open the specific section.
2. Work **one task at a time** from `PROGRESS.md`. Never start task N+1 before N is tested and ticked.
3. Don't dump big outputs. Use `pytest -q -x`, `| tail -30`, `head`, `grep`. Never `cat` a whole log or DB.
4. Don't rewrite whole files for small changes; use targeted edits.
5. Don't refactor, rename, or "improve" finished modules unless a test fails or the task says so.
6. No new dependency without a MEMORY.md decision entry (reason + alternative considered).

## B. Anti-loop protocol (most important)
- Keep an **attempt counter per problem** in `PROGRESS.md → ATTEMPT LOG`.
- **Attempt 1:** read the *actual* error; form one hypothesis; make one change.
- **Attempt 2:** if same error, change approach (not the same fix with tweaks). Check docs (`--help`, official doc page) instead of guessing.
- **Attempt 3:** if still failing, STOP. Write the problem in `PROGRESS.md → BLOCKERS` with: error text (≤15 lines), what was tried, 2 options, which you recommend. Then **ask the user** and move to a different independent task.
- Never retry an identical command expecting a different result.
- Never "fix" a failing test by weakening/deleting it. Fix code, or log a BLOCKER if the test is wrong.
- If a tool/network step is blocked (e.g. can't download model), do not hammer it: log it, use the fallback, continue.
- **Time-box:** each task has an estimate in `PROGRESS.md`. At 2× estimate, stop and re-plan (cut scope, don't push on).

## C. Ask-the-user triggers (use `BLOCKERS`, keep questions closed-form)
Ask when: (a) hardware/RAM unknown and needed to pick a model, (b) a credential/account is needed (Render, DEV post, partner promo), (c) a product rule in `MEMORY.md` is missing, (d) 3rd failed attempt, (e) real-device GPS testing is needed (user must go outside), (f) anything legal/safety-adjacent.
Don't ask about: formatting, file names, internal structure, choices already listed in MEMORY.md.

## D. Engineering rules (non-negotiable)
1. Server is authoritative for eligibility, points, redemption. Client sends *evidence*, never *outcomes*.
2. All state transitions through `domain/states.py`. Illegal transition = exception + test.
3. Money-like operations (collect, redeem, adjust) = one DB transaction + idempotency key + UNIQUE constraints.
4. Balance = ledger sum. A test asserts equality after random operations.
5. AI output is untrusted input: schema-validate, filter, timeout, fallback. App works with Ollama stopped.
6. Rules live in `config/game.yaml`; no magic numbers in code.
7. No raw location history beyond the TTL defined in ARCHITECTURE §11.
8. Safety copy: never instruct entering private property/roads/unsafe terrain; audio cues over screen glances.
9. Don't claim anything is done/tested unless the test ran green in this session. README "What works" must match reality.
10. Secrets only in `.env` (gitignored).

## E. Definition of Done (per task)
- [ ] Code written · [ ] test(s) written and green (`pytest -q`) · [ ] no unrelated files touched
- [ ] `PROGRESS.md` ticked with 1-line result and date/time · [ ] commit `feat(module): msg`
- [ ] New decision/gotcha appended to `MEMORY.md` if any

## F. Session ritual
**Start:** read MEMORY → PROGRESS (find first unticked task + any open BLOCKER with user answer) → say in one sentence what you'll do.
**End (or when context gets long):** update PROGRESS (done / next / blockers), append MEMORY learnings, commit. Print ≤10 lines: done, next, what I need from you.

## G. Cut-scope ladder (when time runs short, drop from the bottom up)
Render deploy → session history → daily caps UI → locked-ghost markers → ElevenLabs/other partners → admin endpoints (keep seed script) → polish. **Never drop:** ledger tests, double-collect/redeem tests, AI fallback, simulation mode, honest README, the post.
