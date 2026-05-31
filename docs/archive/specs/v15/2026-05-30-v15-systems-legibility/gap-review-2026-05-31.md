# V15 Gap Review — 2026-05-31

Independent verification pass over Gemini's V15 implementation, anchored on the
implementation-index **cross-plan normalization decisions** (the places parallel
drafting was most likely to drift) plus the locked toolkit API contract. No
browser testing this pass (per request); verification = source read + `npm run
build` (tsc orphan-term gate) + `npm run lint` + `python -m pytest` + engine
probe diff.

## Ground-truth gates (all green)
- `npm run build` — passes (tsc `as const satisfies` orphan-term gate green).
- `npm run lint` — clean.
- `python -m pytest -q` — full suite passes, incl. new `test_history_server.py`
  and `test_v15_honesty.py`.
- Engine-health probe `probe-baseline-v15-start.txt` == `probe-snapshot-v15-end.txt`
  (zero engine/sim/RNG drift — the hard invariant holds).

## Normalization decisions — verified
- **#1 terms pre-seeded:** the 8 canonical `archetype.<enum>` terms exist in
  `terms.ts`. (Labels use the models.py plain names, not recruitment names — see
  soft issue below.)
- **#2 shared archetype map:** FIXED this pass — see "Gaps fixed".
- **#6 ProgramModal a11y:** `role="dialog"` + `aria-label` + Esc-to-close present
  (matches the *detailed* phase-4a plan acceptance). Focus-trap is named only in
  index #6's parenthetical, not in the plan — left as optional polish.
- **#7 credibility ticks:** `CredibilityStrip` ticks at 0/40/55/70/85 exactly
  match backend `recruiting_office._grade()` (A85/B70/C55/D40/F). Grade read from
  payload, never re-derived.
- **#8 no dev-only e2e routes:** all 3 specs hit `127.0.0.1:8000`, create real
  saves via `/api/saves/new`, target real shipping routes (`?tab=...`).
- **#9 staff honesty:** only `training` department carries a mechanical hook
  (`training_modifier_pct`); others advisory; explicit `rules.honesty` string.

## Gaps fixed this pass
1. **Decision #2 was violated** — the shared `archetypeMap.ts` was dead code
   (imported only by the barrel) while screens defined local reverse-maps.
   - `LeagueContext` local `CLUB_ARCHETYPE_TERM` (byte-identical to shared) →
     now imports shared. Zero behavior change.
   - `SeasonPreview` local enum-key map → now imports shared
     `PLAYER_ARCHETYPE_TERM`.
   - `PLAYER_ARCHETYPE_TERM` had drifted to the **wrong-guess flavor term set**
     (`archetype.sharpshooter`...) that decision #1 explicitly says the
     enum-key seed was meant to replace; realigned to the canonical
     `archetype.<enum>` terms (matches SeasonPreview's prior local targets →
     zero behavior change).
2. Finished + committed the in-progress Phase 4a / Phase 5 work Gemini left
   uncommitted (history award `holder_name`/`proof_stat`, honest EmptyStates,
   `prospect-card` testid required by the e2e spec, honesty pytest suite, 3 e2e
   specs, probe snapshots).

## Soft issue surfaced (needs a Maurice decision — NOT fixed)
**Cross-screen player-archetype naming divergence.** The same `PlayerArchetype`
shows two different names depending on screen, because the **backend** uses two
display-name functions:
- `recruitment.py` → flavor names ("Sharpshooter", "Net Specialist", "Iron
  Anchor", "Two-Way Threat", "Skirmisher", "Possession Specialist",
  "Hit-and-Run"). Used by ProspectCard / Roster / PlayerDetailModal.
- `models.archetype_display_name()` → plain names ("Thrower", "Catcher", "Dodger
  Anchor", ...). Used by Season Preview's roster strength/weakness.

So a THROWER reads as "Sharpshooter" on the recruit board but "Thrower" in the
season preview. Each screen is **internally consistent** (visible text == its
tooltip label), so this is a real-but-soft legibility issue, not a break.

Why not auto-fixed: the recruitment-display screens receive only the display
string in their payload (no enum key), so unifying names requires either a
backend payload change (add `archetype_key`) or a string→enum reverse-map — the
exact pattern decision #2 warns against. And recruitment display names are used
in recruitment logic/tests, so changing them touches more than legibility.

**Options for Maurice:**
- (a) Accept the dual naming as intentional flavor (recruit board = scouting
  flavor; preview = mechanical plain) — close as wontfix.
- (b) Unify to one name set. Cleanest: add `archetype_key` to the prospect/roster
  payloads, point all four screens at the shared `PLAYER_ARCHETYPE_TERM`, and
  pick one label per term. This is a small follow-up spec, not a V15 blocker.
