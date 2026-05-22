# Pre-Plan-C Knockout — Design Spec

**Date:** 2026-05-22
**Status:** Approved (Approach A — "Tight knockout")
**Predecessor audit:** `docs/qa/2026-05-21-browser-playthrough-audit.md`
**Successor plan:** `docs/superpowers/plans/2026-05-22-pre-plan-c-knockout.md`

## Goal

Close the small, well-scoped bugs and tech debt surfaced by the 2026-05-21 browser playthrough QA audit so that Plan C (Tier 1 player-facing surface) starts from a clean baseline. Out of scope: anything Plan C is going to rewrite anyway, and the O1 engine balance change (which needs its own brief with golden-log regen).

## Scope

### In scope (12 fixes)

| # | Bug | Severity | Area |
|---|---|---|---|
| 1 | 7.4 Program Credibility shows "0 wins" after a championship | High | `recruiting_office.py` — only loads current-season history |
| 2 | 7.10 Every player shows "Potential: Elite ★★★☆☆" | High | recruit-pool potential spread + `PotentialBadge.tsx` |
| 3 | 7.1 Recruit-roster OVR scale mismatch ("50-100" → "76-82") | Medium | recruit picker labels |
| 4 | 7.9 27 visible `qa-playthrough-*` orphan saves on landing | Medium | save list filter |
| 5 | 7.5 Plan Status `!` warning persists after Lock Plan | Medium | `WeeklyChecklist.tsx` |
| 6 | 7.3 Standings "Approach: Not set" for all teams | Low/Med | LeagueContext / PreSimDashboard fallback |
| 7 | 7.2 League Rank #2 at S1W1 (no games played) | Low | `PreSimDashboard.tsx` rank gate |
| 8 | 7.7 Week 5 silently missing (bye not surfaced) | Cosmetic | Command Center schedule rendering |
| 9 | 7.8 Dev language leaks ("11 throw events were derived…") | Cosmetic | `replay_proof.py` copy |
| 10 | 7.11 Elite vs High render with identical 3 stars | Low | `PotentialBadge.tsx` |
| 11 | Plan A follow-up: rec-driver comeback heuristic loose | Medium | `rec_engine.py` comeback path |
| 12 | Repo cruft: 11 playthrough `*.png` at repo root | Hygiene | `.gitignore` |

### Out of scope

- **Bug 7.6** (disabled approach buttons): Plan C rewrites `CoachPolicy` and the picker.
- **Audit P0** "make tactical lever change variance" + "narrate the why on losses": Plan C tactics v2 + voice rewrite.
- **Audit P1** "round-by-round survivor ribbon": Plan C match-replay UI.
- **O1 engine balance**: needs explicit sign-off + golden-log regen (per `AGENTS.md`). Own brief.
- **Audit P2/P3**: season length, aging curve, rookie slate, staff market depth — later milestones.

## Per-fix approach

### Fix 1 — Program Credibility (Bug 7.4)
Root cause: `dynasty_office.py:84` calls `load_command_history(conn, season_id)` which returns only the current season. At S3W1 after winning S2, that's empty. **Approach:** Add `load_command_history_all_seasons(conn)` and pass it to `build_recruiting_state`. Keep existing per-season loader for callers that need it. Update credibility evidence line to read "career command-history wins/losses" so the source is honest.

### Fix 2 — Potential spread (Bug 7.10)
The recruit pool currently assigns "Elite" tier to ~all prospects. Likely cause: `potential_tier` derivation in recruitment / scouting uses a too-permissive threshold. **Approach:** Locate the threshold (probably in `recruitment.py` or `scouting.py` — same file as Bug 7.1 since they're related), introduce a deterministic distribution (e.g., ~10% Elite, ~25% High, ~40% Mid, ~25% Low) based on the potential ceiling, and pin with a test that draws a pool of 50 and asserts the distribution.

### Fix 3 — Recruit OVR scale (Bug 7.1)
Picker shows "50-100 OVR" where "50" is current and "100" is potential ceiling, but the in-game OVR is the actual current rating after generation (76-82). **Approach:** Relabel the picker to "Current 50 / Potential 100" with an explicit divider, and add a tooltip explaining the two numbers. No model change.

### Fix 4 — Save list filter (Bug 7.9)
**Approach:** In the save-list endpoint and/or frontend filter, hide names starting with `qa-playthrough-` by default. Add a "Show debug saves" toggle on the landing screen. Server returns all; frontend filters.

### Fix 5 — Plan Status `!` warning (Bug 7.5)
The Plan Status block in `WeeklyChecklist.tsx:68` is rendered from `planConfirmed` correctly — so the warning shouldn't appear post-lock. The audit's screenshot must reflect a different `!` chip. **Approach:** Reproduce in the running app, find the truly persistent warning chip (likely on the right rail of `PreSimDashboard.tsx`), and gate it on the same lock-state signal `WeeklyChecklist` uses.

### Fix 6 — Standings "Approach: Not set" (Bug 7.3)
The `Not set` fallback fires when `policy_approach` is null on the standings row. **Approach:** When a club has no week-set policy, fall back to its default `coach_policy.approach` rather than null. Persist the last-set approach across offseason if straightforward, otherwise document the per-week semantic in a column tooltip.

### Fix 7 — League Rank at S1W1 (Bug 7.2)
`PreSimDashboard.tsx:108` computes rank from standings unconditionally. **Approach:** When `games_played == 0` across the league, render "Rank n/a" instead of `#N`.

### Fix 8 — Week 5 bye (Bug 7.7)
The schedule sequence jumps Wk 4 → Wk 6 silently for clubs with a bye in a 7-team league. **Approach:** When the player's club has no game in a week within the season window, show an explicit "Bye Week" beat in the schedule strip and the post-week advance.

### Fix 9 — Dev-language strip (Bug 7.8)
`replay_proof.py:155` emits "N throw events were derived from the saved event log." **Approach:** Rewrite to player-facing copy ("Reconstructed from N throws of game tape."). Drop "Based on Result proof" or rename it ("Match Replay Verified").

### Fix 10 — Elite vs High stars (Bug 7.11)
`PotentialBadge.tsx:2` renders `confidence` stars (scouting confidence), not potential tier — so Elite and High look identical because their confidence is the same. **Approach:** Render stars off the potential tier itself (Elite=5, High=4, Mid=3, Low=2), or render two separate visuals (tier badge + confidence pip).

### Fix 11 — Rec-driver comeback heuristic (Plan A follow-up)
STATUS.md flags the comeback heuristic firing in ~22/25 expected matches. **Approach:** Read the relevant branch in `rec_engine.py`, tighten the comeback-trigger threshold so the heuristic fires for the expected match shape, and pin with a deterministic test that runs N seeds and asserts the firing rate is at or above the target.

### Fix 12 — Repo cruft
Add the playthrough screenshots and Playwright artifact dump to `.gitignore`. Delete the files from the working tree.

## Verification baseline

Before any fix lands: `python -m pytest -q` green, `npm run build` + `npm run lint` clean. After each fix: the new regression test passes, the existing suites still pass. After the full sweep: a smoke browser load to confirm no fix regressed another fix.

## Definition of done

All 12 fixes landed, each with a regression test where the bug is observable in code (Fixes 1, 2, 6, 7, 8, 9, 10, 11) and a manual reproduction note where the bug is only browser-observable (Fixes 3, 4, 5, 12). `docs/qa/2026-05-21-browser-playthrough-audit.md` updated with a resolution table mirroring the bug-log style. STATUS.md updated.
