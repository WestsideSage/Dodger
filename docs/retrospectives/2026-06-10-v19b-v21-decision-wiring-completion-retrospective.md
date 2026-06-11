# V19b → V21 — Decision Wiring completion + Broadcast/Presentation truth (retrospective)

Date: 2026-06-10. One owner-directed mega-pass ("implement everything
remaining… surprise me on my first playthrough") covering V19b, the V20
truth fixes, and the V21 presentation slice. Commits: `ab8ce92` (staff
focus), `fd10825` (promises), then V19b-3/V20/V21 commits through
`31f3942`. Plans: `docs/specs/2026-06-10-v19-decision-wiring-sprint-plan.md`
(V19 a/b), sequencing plan §2 rows V20/V21.

## Shipped

**V19b — management lanes (Decision Wiring complete):**
1. *Staff focus* — the six flavor department dropdowns became ONE real
   weekly decision: tactics (+18 effective IQ next match), conditioning
   (fatigue drag halved next match), training (practice credits → offseason
   growth, cap 8 weeks), scouting (+1 Scout action), culture (courtship
   +25% this week); medical REMOVED (nothing to decide). Symmetric: AI
   clubs pick archetype-flavored focuses through the same plan tables, and
   their training weeks feed their own offseason credits.
2. *Promises revived with a real consumer* — kept/broken promises feed
   credibility (+4 kept / −6 broken, capped ±15) → prospect interest → the
   contested Signing Day offer. Dynasty Office gains a Promises panel
   (open/KEPT/BROKEN with evaluator evidence) and prospect cards gain a
   plain-language Promise action ("Early playing time", "Development
   priority", "We'll contend").
3. *Week-1 scouting yields real intel* — tape-less axes fill from the
   opponent ARCHETYPE's playbook (the same generator their weekly plan
   derives from), labelled "playbook", replaced by tape reads as games are
   recorded. Fog fence proven harder: the fence test plants a live policy
   diverging from the playbook and asserts reveals come from the generator.

**V20 — broadcast/stats truth:** catch returns finally reach player stats
(returned players' minutes/plus-minus resume; `revivals_caused` real after
being hardcoded 0 since V1); the All-Time Record sums completed seasons
only; the official replay SETS strip is live-per-event (unreached games
show ·, the current game ▶ — replays no longer spoil themselves); the
official adapter persists both clubs' locked match policies and the replay
renders a GAME PLANS row (intent context, slim slice).

**V21 — presentation:** records gain a CAREER MILESTONES middle tier
(same-holder extensions crossing a round-number boundary — "passed 100
career eliminations"); zero-floats sweep (HoF legacy line, offer prose,
ceremony prose, evidence ratings, team previews — the raw-proof drawer's
probabilities deliberately exempt).

## Verification

Full `python -m pytest -q` green (pytest exit captured directly), npm
build + lint clean, and a live prod-server first-playthrough walk: career
creation → promise made (panel + chip live) → staff focus picked (Scout
slots 3/3 → 4/4) → week-1 scout (0/5 → 5/5 playbook reads) → plan locked →
match simulated → replay verified (live strip unspoiled, GAME PLANS row,
honest catch/block narration) — zero console errors, zero failed requests;
walkthrough save purged.

## Honest remainders (recorded, not silently dropped)

- Official survivors-column cleanup (V20 §7.3): persistence-shape surgery
  with standings-consumer risk — needs its own measured pass.
- `test_server_save_boundary` flake investigation (V20 §7.5).
- V21 app-wide voice/vague-language purge, information-dedup pass, further
  Class Brief redesign (structured rows from the v2 pass remain current),
  scenario-browser coverage beyond the main-ruleset walks.
- Dynasty Office budget panel shows a stale Scout count until navigation
  refetch after changing staff focus in the modal (minor polish).

## Traps for future passes

- `pytest -q | tail` masks failures twice over (pipe exit code) — always
  capture pytest's own exit; one V20 commit briefly landed with a red
  pinned test because of this (fixed forward in `6a0ce5c`).
- Amplitude-only noise scaling cannot flip a deterministic argmax over
  equal base scores — selection-quality consumers need a channel that
  shifts VALUES, not just noise width (the rec tactics-prep lesson).
- Engines consuming new context (preps) must default to byte-identical
  behavior with the context absent, or every fixture pin churns.
