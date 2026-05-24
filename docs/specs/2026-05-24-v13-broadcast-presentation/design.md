# V13 — Broadcast And Presentation Layer (Design)

Date: 2026-05-24
Status: Shipped (2026-05-24)
Predecessors: V7 Watchable Match Proof Loop (`docs/archive/specs/2026-05-05-v7-sprint-plan.md`); V9 Living League Memory thin ship (`docs/archive/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`); Plan C Tier 1 player-facing surface (`docs/specs/2026-05-20-post-v11-redesign-brief/plan-c-tier1-surface.md`); V12 AI Program Managers (`docs/specs/2026-05-24-v12-ai-program-managers/design.md`).

## Relation to Prior Specs

- This is the milestone formerly labeled "V12 / Broadcast & Presentation" in `docs/specs/long-range-playable-roadmap.md`. Re-slotted to **V13** on 2026-05-24 so V12 could capture the re-slotted AI Program Managers loop. The roadmap section now points here.
- **V7 (Watchable Match Proof Loop)** rebuilt the replay viewer to be tactically legible. V13 builds **on top of** V7's event log and replay timeline — it never replaces them. The raw `ReplayTimeline` and per-event detail must remain reachable at one click after V13.
- **Plan C (Tier 1 player-facing surface)** introduced `voice_*` modules, `voice_register` per tier, moment events (`comeback`, `dramatic_catch`, `gassed_collapse`, `late_game_escape`, `one_v_one_finale`, `comeback_attempt`), and the `LateGameBanner` / `OneVOneBanner` / `ComebackCard` components. V13 reuses the voice-register infrastructure and the moment-event contract — no new moment kinds are introduced.
- **V9 (Living League Memory)** persists records, awards, rivalries, and player career histories. V13 reads these as the **source data** for broadcast copy and highlight selection. V13 does not extend V9's schema.
- **V12 (AI Program Managers)** persists program archetypes and trajectory rows. V13 surfaces those in broadcast framing (e.g., "Year 3 of a development rebuild visits the defending champion"). V13 is **not** blocked on V12 shipping — the broadcast copy gracefully omits archetype phrasing if the data is absent.
- Original roadmap intent: `docs/specs/long-range-playable-roadmap.md` (V13 section, formerly "Future: Broadcast and Presentation Layer").

## Problem

Today's UI is honest but flat. After Plan C the match replay shows moments and a tactical timeline, but:

- The pre-match screen has no broadcast framing. A first-week game and a playoff rematch with the league's bitterest rival are visually identical.
- Highlight selection does not exist. Players who want a 30-second recap of a 53-event match cannot get one without scrubbing the full timeline.
- Playoff and championship matches share the regular-season header. The biggest moment of the season looks like a Tuesday.
- The season-recap and Hall-of-Fame ceremonies (`StructuredOffseasonBeats`) render structured data with terse copy; they don't celebrate.
- Commentary-style flavor is missing. Match aftermath uses `voice_aftermath` for one headline; there's nothing for the build-up or the in-replay beats beyond moment cards.

The Simulation Honesty pillar bars us from inventing drama. The opportunity V13 captures: there is **plenty** of real drama in the event log, the V9 league memory, and the V12 trajectory data — it just isn't presented.

## Playable Thesis

Once the simulation is already legible, presentation can make matches and league moments feel more dramatic without changing outcomes. Every piece of broadcast copy is derived from event log, player history, or league records — and the raw proof remains one click away.

User-visible proof at ship:

1. The matchup preview for a playoff rematch reads differently from a first-week game — and the difference is grounded in `program_trajectory`, `recent_matchups`, and standings.
2. A `Highlights` view summarizes a finished match in ≤6 beats, each one a real `moment_event` or a real elimination of statistical note, none invented.
3. The championship match shows a "Title Game" frame and the season-recap ceremony renders a multi-beat narrative (`leaders`, `records_ratified`, `hof_induction`) using V9 data plus templated copy.
4. A "Show me the proof" toggle on every broadcast surface drops back to the raw event log, replay timeline, or league-record table that the copy was derived from.

## Scope

### In scope

1. **Broadcast framing module (`broadcast.py`).** Pure server-side function: given `(match, season_state, league_memory, program_trajectory?)` → a structured `BroadcastFrame` (rivalry tag, stakes tag, archetype tag, optional historical hook, voice-register slot). Frame is consumed by the matchup preview and the replay header.
2. **Highlight package generator.** Given a finished match's event log + moment events, return a deterministic 4–6-beat sequence: opening shot of significance (first elimination, opening rush outcome), 1–2 mid-match swing eliminations, every moment event up to a cap, the winning play. **No invented context.** Each beat carries its source event id so the proof toggle works.
3. **Playoff and championship presentation.** A flag on the match (already present via `playoffs.py` round info) drives a `PlayoffFrame` that overlays the regular `BroadcastFrame`: round name, bracket position, series context if rounds become multi-game later (V13 ships single-elim parity; bracket schema unchanged).
4. **Commentary flavor in the replay timeline.** Extend `ReplayTimeline` to interleave 1–3 lightweight commentary inserts derived from event log + V9 records (e.g., "Garza's 18th elimination of the season ties the program single-season mark."). Inserts are gated by event id and source — if the record isn't real, the insert doesn't render.
5. **Season recap and Hall-of-Fame ceremony upgrades.** `StructuredOffseasonBeats` gets a presentation pass: leaders beat surfaces the top-5 with stat lines; `records_ratified` reads the actual record entries and renders cards with the prior holder; `hof_induction` renders a per-inductee card with career-line data from V9. The structured-data contract is unchanged; the rendering is richer.
6. **Voice register reuse.** All new copy templates route through `voice_register` for the active tier (`tier1` from Plan C). No new register is added in V13. If `tier2_official` voice templates are needed for a future tier, the structure must support it without code changes.
7. **Proof-toggle invariant.** Every broadcast surface ships with a visible affordance that reveals the underlying source row (event id, record id, trajectory row, matchup-history row). The toggle is a Playwright-assertable selector.

### Out of scope

- **Mid-match coaching, mid-match user control.** Roadmap calls this out as separately designed. V13 is presentation-only.
- **Camera-heavy visuals, animation, 3-D court rendering, audio.** This is a UI/copy layer, not a media-asset pipeline.
- **Commentary that invents unsupported causes.** Forbidden. Every insert must point at a real event or record.
- **New moment-event kinds.** V13 uses Plan C's six kinds. If a presentation use case demands a seventh, file a follow-up against Plan C, not V13.
- **Schema changes to V9 records, V12 trajectory, or the event log.** V13 reads them. If a field is missing for presentation, the copy degrades gracefully — it never blocks ship on a schema extension.
- **OfficialDriver-only or rec-driver-only behavior.** Both drivers must produce matches that V13 can present. The moment-event contract is the only interface V13 requires.
- **Localization.** English only. Copy is templated via `voice_register` so a future localization pass is mechanical.
- **Per-match commentary AI / LLM.** All copy is templated. Honesty constraint: a template + source row is auditable; a generative call is not.

## Approach (three phases)

### Phase 1 — `broadcast.py` and the matchup preview

Smallest visible change. Lands the structured frame and one consumer.

**Work:**

1. New module `src/dodgeball_sim/broadcast.py`. Pure functions over already-loaded data. Returns `BroadcastFrame` dataclass: `rivalry_tag`, `stakes_tag`, `archetype_tag`, `historical_hook` (optional), `voice_slot` (which `voice_register` slot to render through).
2. Inputs read from existing modules only: `matchup_details.build_matchup_details`, `dynasty_office.recent_matchups`, V9 record lookups, V12 `program_trajectory` (optional). If V12 hasn't shipped yet, the `archetype_tag` is `None` and templates skip that slot.
3. Wire `BroadcastFrame` into `/api/matchup-details` response (existing endpoint). Frontend `MatchupPreview` reads the new field and renders the tag chips + historical-hook line.
4. Tests: `tests/test_broadcast.py` covers (a) playoff vs regular-season tagging, (b) rivalry threshold from `recent_matchups`, (c) graceful degradation when V12 data is absent, (d) determinism (same inputs → same frame).
5. Playwright: extend an existing matchup-preview spec to assert chip presence for a playoff match.

**Exit criterion:** matchup preview visibly differs between a first-week game and a playoff rematch on a progressed save; pytest + frontend build green.

### Phase 2 — Highlight package + proof toggle

The new presentation surface. Highest user-value beat for the ship.

**Work:**

1. New module `src/dodgeball_sim/highlights.py`. `build_highlight_package(match_id, conn) → list[HighlightBeat]`. Selection rule (deterministic, fully event-id-keyed):
   - First scored elimination of the match.
   - Every `moment_event`, up to 3, in chronological order.
   - The two highest-impact swing eliminations between moments, scored by "lead change magnitude" (already derivable from the event log).
   - The terminal elimination.
   - Cap: 6 beats. Dedup by event id.
2. New endpoint `GET /api/matches/{match_id}/highlights` returning the package + per-beat source event ids.
3. New frontend component `MatchHighlights.tsx` in `frontend/src/features/replay/`. Renders the beats as compact cards, each with a "Show in timeline" button that scrolls/highlights the source event in the existing `ReplayTimeline`. This **is** the proof toggle.
4. Voice copy per beat goes through `voice_register.tier1` slots. No commentary is allowed to claim context beyond the source event's payload.
5. Tests: `tests/test_highlights.py` covers selection rules on fixture matches, asserts dedup, asserts deterministic ordering, asserts every beat has a valid `source_event_id`.
6. Playwright: a finished match → highlights view renders ≥4 beats, each beat's "Show in timeline" reveals the source event.

**Exit criterion:** every finished match has a highlight package; proof toggle works on every beat; pytest + frontend green.

### Phase 3 — Playoff frame, commentary inserts, ceremony upgrades

Polish + ceremony. Highest visual impact, smallest engine risk.

**Work:**

1. **Playoff frame.** `broadcast.PlayoffFrame` overlays `BroadcastFrame` when `playoffs.is_playoff_match_id(match_id)` is true. Round name and bracket context surfaced. Championship match gets a distinct visual treatment in the replay header (frontend CSS only — no new layout primitives).
2. **Commentary inserts in `ReplayTimeline`.** Extend the timeline payload (server-rendered, like Plan C's `display_text`) with optional `commentary_insert` entries pinned to event ids. Generator lives in `broadcast.py` and reads V9 record lookups (`league_records`, `player_career_stats`). Cap: 3 inserts per match. If a record can't be confirmed at render time, the insert is dropped.
3. **Ceremony upgrades.** `StructuredOffseasonBeats.tsx` consumers (`leaders`, `records_ratified`, `hof_induction`) get richer card layouts. Backend `offseason_ceremony.py` already exposes the needed structured rows; this phase is mostly frontend.
4. Voice templates added to `voice_register.tier1` for: rivalry framing, playoff stakes, record-tying / record-breaking, HoF citation. No new register; templates only.
5. Playwright `tests/e2e/v13_broadcast_layer.spec.ts`: walks a season into the playoffs, asserts the championship match shows the title frame; opens the season recap and asserts each beat renders the richer layout.

**Exit criterion:** all four user-visible proofs from the Playable Thesis section are reachable in the browser on a fresh save; pytest + frontend build + Playwright green.

## Out of Scope (reiterated)

See "Out of scope" under Scope. The integrity-critical line: **no LLM-generated commentary, no invented context, no schema changes to V9/V12/event log, no engine math touched.**

## Risks

- **Commentary inserts make false claims.** A record-tying insert that's actually wrong is a worse failure than no insert. Mitigation: every insert carries a `source_record_id`; render-time validation drops inserts whose source row no longer matches; a unit test seeds a fake record-tying scenario and asserts the insert appears, then mutates the underlying data and asserts the insert is dropped.
- **Highlight selection lies about importance.** A "swing elimination" computed wrong reads as fake drama. Mitigation: the lead-change-magnitude metric is derived directly from event log eliminations and the current alive-count; test against synthetic matches with known peaks.
- **V12 absence breaks templates.** If V12 ships after V13, every `archetype_tag` slot is `None`. Mitigation: templates are slot-aware; the matchup preview tested with V12 trajectory absent in Phase 1.
- **Frontend bundle bloat.** Three new components in `frontend/src/features/`. Mitigation: reuse existing card primitives; do not introduce a new design-system dependency.
- **Proof toggle becomes a maintenance burden.** Every new presentation surface needs a proof affordance, which is easy to skip in future PRs. Mitigation: ship a Playwright helper that asserts every broadcast surface exposes a `data-broadcast-proof-source` attribute; the helper is invoked by `v13_broadcast_layer.spec.ts`.
- **Ceremony copy reads as filler.** A richer card with templated text can feel emptier than terse honesty. Mitigation: every ceremony card surfaces at least one concrete numeric stat or named entity — no card is allowed to render with only template strings.

## Acceptance Criteria

1. `python -m pytest -q` is green, including new test files: `test_broadcast.py`, `test_highlights.py`, plus the commentary-insert validation test in `test_broadcast.py`.
2. `npm run build` and `npm run lint` in `frontend/` are clean.
3. Playwright spec `tests/e2e/v13_broadcast_layer.spec.ts` passes against the local dev server.
4. Every broadcast surface (matchup preview, highlight beat, commentary insert, ceremony card) exposes a `data-broadcast-proof-source` attribute identifying its source event id, record id, or trajectory row id. A Playwright helper enforces this across the suite.
5. A side-by-side replay of the same `match_id` with V13 disabled (feature flag for the duration of QA — removed before ship) and enabled produces **byte-identical** event logs and `MatchResult`. Outcomes are unchanged.
6. `docs/STATUS.md` moves V13 into "Shipped And Verified" with the spec link; `docs/specs/MILESTONES.md` updates V13's status to `Shipped (YYYY-MM-DD)`.
7. The integrity contract holds: no new randomness in `engine.py` / `rec_engine.py`; no comeback code; the diff against engine code is empty.
