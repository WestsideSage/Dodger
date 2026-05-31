# Player-Archetype Naming Unification — Design (2026-05-31)

Follow-up to the V15 gap review (`docs/specs/2026-05-30-v15-systems-legibility/gap-review-2026-05-31.md`),
which surfaced that the same `PlayerArchetype` displayed under two different names depending on screen
(recruitment flavor names like "Sharpshooter" on the Recruit Board vs. plain names like "Thrower" in
Season Preview), because the backend had two divergent display-name maps.

## Decisions (owner: Maurice)
- **Canonical name set:** recruitment **flavor names** — Sharpshooter, Net Specialist, Ball Hawk,
  Iron Anchor, Two-Way Threat, Skirmisher, Possession Specialist, Hit-and-Run.
- **Scope:** **global** — one source of truth, flavor names on every surface.

## Design — single source of truth
`PlayerArchetype.display_name` becomes the ONE archetype display source; `.value` (raw enum) stays the
data/persistence/`archetype_key` join. Display-only change → zero engine/RNG/sim impact (probe unchanged).

### Backend
1. `models._ARCHETYPE_DISPLAY_NAMES`: values → flavor names (THROWER→"Sharpshooter",
   CATCHER→"Net Specialist", DODGER_ANCHOR→"Iron Anchor", THROWER_CATCHER→"Two-Way Threat",
   THROWER_DODGER→"Skirmisher", CATCHER_HAWK→"Possession Specialist", HAWK_DODGER→"Hit-and-Run";
   BALL_HAWK stays "Ball Hawk").
2. `recruitment.py`: delete `_RECRUITMENT_DISPLAY_NAMES`; `_display_name_for_archetype` returns
   `archetype.display_name`. (Output identical to today → Recruit Board / Roster / Player Detail
   unchanged; they key off `archetype_for_player()`.)
3. `identity.py`: `title=` uses `player.archetype.display_name`; delete the third map `_ARCHETYPE_TITLES`.

Net effect: `.display_name` / `archetype_display_name(raw_key)` consumers (Season Preview,
next-best-improvement, identity title, matchup details, offseason ceremony, CLI) flip plain→flavor —
the intended unification. The flavor-string-keyed screens are untouched.

### Frontend
4. `legibility/archetypeMap.PLAYER_ARCHETYPE_TERM`: map enum key → **flavor** terms
   (`thrower→archetype.sharpshooter`, …; `ball_hawk→archetype.ball_hawk`). SeasonPreview already
   consumes this shared map and already receives `archetype_key`; visible text now comes from the
   backend `archetype` field (now the flavor name) → trigger label and tooltip match.
5. `legibility/terms.ts`: delete the 7 now-orphaned plain terms (`archetype.thrower/catcher/
   dodger_anchor/thrower_catcher/thrower_dodger/catcher_hawk/hawk_dodger`). Keep `archetype.ball_hawk`
   (shared by both naming systems). tsc `as const satisfies` gate confirms no dangling `TermTip` refs.

### Tests
- `test_archetype_enum.py` — display_name expectations → flavor names.
- `test_identity.py` — `classify_archetype`/`title` expectations → flavor.
- `test_next_best_improvement.py` — raw-key prettify assertion → "Hit-and-Run".
- `test_season_preview.py` — raw-key→display assertions → flavor names.
- e2e `v15-legibility-surfaces` already accepts flavor names (regex includes Net Specialist/Skirmisher).

## Verification
`python -m pytest -q` · `npm run build` (tsc orphan gate) · `npm run lint` · engine-health probe
identical before/after (display-only).
