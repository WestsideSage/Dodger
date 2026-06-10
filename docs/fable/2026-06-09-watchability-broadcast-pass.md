# Match Watchability / Broadcast Director Pass — 2026-06-09

Role: match-experience director / simulation watchability / broadcast producer.
Scope: make the simulated match compelling to watch, easy to read, and
emotionally satisfying **without changing outcomes dishonestly**. All work in
the main repo working tree, on top of the (uncommitted) first-hour-onboarding
and trust-audit passes.

Tooling note: Pare MCP was bypassed for most of this pass — the work needed
raw probe-script output, custom JSON diffs, and pytest/playwright output
verbatim, so plain shell commands were used (fallback disclosed per
`AGENTS.md`).

---

## 1. Watchability verdict

**Before this pass the watched replay was not believable on the default
path.** The official (foam) engine — the ruleset every new career gets —
produced replays in which **99% of events displayed a wrong live score**
(measured: 175 of 177 throw events on a fixed-seed match). The court
saturated to "all 12 players eliminated" early in game 2 of a multi-game
match and stayed that way for the remaining ~200 events, because catch
re-entries and per-game resets never reached the replay. The "TURNING POINT"
headline was literally the first hit of the match. The set-by-set story of an
official match (persisted in `official_score_json` since Phase 4b) was never
surfaced anywhere. A deterministic V13 highlight reel existed server-side
with a dead, never-rendered UI component.

**After this pass:** the live court is exact (0 drift on the same fixture),
official matches read as a series of games with a set strip + live game
labels + per-game possession grouping, recognition moments banner during
playback at the exact play they happened on, the biggest-swing headline and
its jump button reference the same event, the highlight reel is rendered with
working jump links, and the aftermath shows how the game points accumulated.
A real falsified-outcome bug on the legacy rec path (elimination wins
recorded as draws) was found and fixed at the root.

It is now genuinely watchable: a close official match reads as sets with
swings and re-entries; a blowout reads as a run of game chips you can skim
and a court that actually shows the domination.

## 2. Match samples inspected (and how they were generated)

All samples were produced with deterministic tooling; nothing was faked.

- **Two full auto-piloted careers** (temp DBs, `initialize_curated_manager_career`
  seed 20260609 + `auto_pilot_weeks` to season complete, incl. playoffs):
  one `official_foam` career and one legacy/rec career. Audited via
  `match_replay_payload` per match: official close draw (1-1 gp, no-point
  decider), official blowout (9-2 gp over 11 games, 247 throw events),
  official playoff semifinal (1-2, two no-point games), official Playoff
  Final (1-2, neutral final), rec draw, rec playoff semifinal, rec final.
- **Fixed-seed engine fixtures** (factory teams, seed 4242 official → 8-0
  across 9 games; seeds 1-40 rec with catch-heavy policies) for per-event
  drift measurement against engine ground truth.
- **A live browser career** (`watchability-verify`, official foam) driven
  through the real UI: scout → confirm → lock → simulate → aftermath →
  full replay, at 1440×900 and 1280×720.

## 3. Biggest replay/narrative problems found (ranked)

1. **Live replay state was wrong on the default path (presentation-truth
   bug).** Catch re-entries were dropped by BOTH translators (official
   `return_on_catch` events ignored; rec `returning_player_id` discarded),
   and official per-game resets weren't represented. Measured: 99% of events
   showed a wrong living count; the court showed resurrected players as
   eliminated forever. (`official_translator.py`, `rec_adapter.py`,
   `replay_proof._score_state`.)
2. **Recorded rec outcomes could be false (outcome-truth bug).**
   `rec_adapter._derive_box_score` marked every ever-eliminated player as
   out (returns ignored) → recorded survivors undercounted on **40/40**
   probed seeds — and `franchise.simulate_match` *derives the recorded
   winner from those survivor totals* (overriding the engine's own winner).
   Live repro: a rec match whose event log ends `winner: aurora` (opponent
   wiped 2-0) was recorded and displayed as a **0-0 Draw**. The event log is
   canon; the record lied.
3. **"TURNING POINT" was the first hit of the match** — fake causality,
   shown in both the replay header block and the aftermath TACTICAL READ.
   The jump button targeted a possibly different event than the text.
4. **No game/set structure in official replays.** One undifferentiated
   stream of up to ~250 throws; no live set score; the persisted per-game
   results (`official_score_json`) surfaced nowhere.
5. **Moments were invisible while watching** (aftermath-only), and official
   moment ticks are per-game engine ticks that could not be mapped onto the
   translated stream — the V13 highlight tick-mapping was silently wrong for
   officials, and `MatchHighlights.tsx` was dead code (never imported).
6. **Official play-by-play was context-empty** ("No decision context was
   saved for this throw" on 100% of official events) while persisted truth
   (catches list, rule refs, returns) went unused in labels/details.
7. **Pacing:** fixed 1200 ms × 247 events ≈ 5 minutes of monotone autoplay;
   `ReplaySpeedControl` existed but was never wired.

## 4. Implemented changes

### Replay (truth carriers + readability)
- `official_translator.py`: stamps `state_diff["player_return"]` on the
  catching sequence's throw (joined on **(game_id, sequence_id)** — sequence
  ids restart per game; the first implementation keyed globally and was
  caught by probe + pinned by regression test), plus
  `context.official = {game_number, engine_tick}` on every throw.
- `sequence.py`: `sequence_final` payload carries `release_time_ms` (replay
  metadata only) so per-game engine ticks are recoverable.
- `rec_adapter.py`: `catch_return` raw events thread
  `returning_player_id` → `state_diff["player_return"]`.
- `replay_proof.py`: score state now processes `player_return`, resets
  eliminated sets at official game boundaries, and proof events carry
  `game_number` / `engine_tick` / `returned_player_id|name` + a `RETURN`
  proof tag. `event_label`/`event_detail` narrate the re-entry ("X
  re-enters." / "...re-enters from the catch queue.") and cite USAD rule
  refs from the persisted outcome. Legacy event streams (old saves) keep
  their old behavior — no inference is applied to streams that lack the
  metadata.
- `replay_service.py`: new `game_segments` payload (per-game winner, points,
  running totals, final actives, result type, first/last proof indices)
  built from the persisted `official_score_json`; honest
  `turning_point` = biggest in-game swing (lead flips weighted highest,
  never compared across a game reset) with `turning_point_index` so the jump
  lands on the same event.
- `server.py`: `MatchReplayResponse.game_segments` declared (FastAPI
  strip-guard, WT-2/3 bug family).
- `MatchReplay.tsx`: court eliminations now read the **current event's**
  score state (the old union-of-all-events re-broke per-game resets);
  SETS strip with per-game chips (click = jump to that game) and running
  game-point total; possession bar gains game-divider tiles and amber
  moment pips; NOW SHOWING and the Current Event card show `GAME n`; the
  game-boundary score delta reads "Game n — fresh court" instead of a fake
  ±6 swing; "BIGGEST SWING" block jumps via `turning_point_index`;
  `ReplaySpeedControl` wired (1x/2x/4x; instant = skip to final play);
  autoplay holds vary by resolution (catches/outs linger, misses move).
- `index.css`: append-only "BROADCAST LAYER" section for the new pieces.

### Moments
- `moment_events.py`: all six moment dataclasses gain optional
  `game_number` (backward compatible with old payloads).
- `official_engine.run_autonomous_match`: tags each game's moments with its
  game number (presentation metadata; engine RNG untouched).
- `replay_service`: every enriched moment carries `anchor_index` — its
  server-resolved spot in the proof timeline (game+tick exact match,
  catch-preferring; end-of-game moments anchor to the game's last play; rec
  anchors by shared tick). `MatchReplay` banners anchored moments during
  playback (DRAMATIC CATCH / LAST STAND / ONE-V-ONE FINALE / COMEBACK...)
  and marks them on the possession strip.
- `highlights.py`: moment→event mapping is now game-aware for officials
  (was: wrong-tick mapping); swing scoring no longer crosses game
  boundaries. The V13 highlight reel is finally **rendered**: `MatchReplay`
  fetches `/api/matches/{id}/highlights` and shows "HIGHLIGHT REEL — The
  Story in N Plays" with working Show-in-timeline jumps (events-index →
  proof-index translation).

### Aftermath
- `use_cases.py`: official `match_card` carries `games` (per-game winner,
  points, result type, in order). `MatchScoreHero` renders the set story as
  chips under the Final scoreline (◂ home set / ▸ away set / — no-point), so
  a 9-2 rout and a seesaw 9-2 stop reading identically.
- TACTICAL READ now receives the honest biggest-swing text (same field,
  truthful value).
- **Outcome-truth fix (rec):** `rec_adapter._derive_box_score` computes
  final on-court status from the full diff stream (out → out, return →
  back). Recorded survivors now equal the engine's `final_active` counts
  (verified 20 seeds in-test, 40 seeds by probe), so the
  `franchise.simulate_match` survivor-derived winner now **agrees with the
  event log** instead of falsifying it.
- `replay_proof.derive_narrative_beats`: deficit/lead-change walk honors
  returns (start counts = living + outs − returns; walk applies both).

### Tests
- New `tests/test_replay_watchability.py` (16 tests): translator return/game
  stamping + per-game-key regression; rec adapter return threading; per-event
  score-state vs engine ground truth (the 99%-drift fixture, now exact);
  per-game reset; turning-point honesty (biggest swing, never across a
  reset); `_game_segments` home/away mapping + legacy fallback; moment
  anchoring (official game+tick, rec tick, end-of-game); official moments
  carry game numbers; full payload end-to-end (segments, turning index,
  anchors, serialization guard); rec box-living == driver actives across
  seeds + winner agreement; narrative-beats return walk; **frozen outcome
  pin** (seed-4242 official: alpha 8-0 over 9 games — measured before the
  changes, asserted after).
- `tests/e2e/official-rules-replay.spec.ts` extended: set strip visible with
  enabled jump chips + running game-point label; BIGGEST SWING jump lands on
  the exact headline event.

## 5. Evidence outcomes were not dishonestly changed

- **Official engine/career: byte-identical.** The full-season probe (seed
  20260609, auto-pilot to offseason) was run before and after all changes:
  identical week-by-week winners and scorelines (W1 draw 1-1 w/ 1 no-point;
  W2 9-2; semifinal 1-2; final 1-2 — all unchanged), and the fixed-seed
  engine fixture is pinned in-suite (8-0 / 9 games / same winner). The only
  engine-adjacent edits (moment game tags, sequence payload metadata) touch
  no RNG and no resolution path.
- **Rec (legacy) recorded outcomes changed — intentionally, separately
  justified, and only forward.** The box-score fix makes recorded survivors
  equal the engine's actual final actives; recorded winners now match the
  engine's own `match_end` event (previously a 2-0 elimination win could be
  recorded as a 0-0 draw — live repro in §3.2). This is the *removal* of a
  dishonest outcome rewrite, not the addition of one: the event log is canon
  (`AGENTS.md`). Old saves are untouched (their records are already
  persisted); only newly simulated legacy matches record truthfully.
  Standings in a freshly probed legacy season shift accordingly (the W1
  "draw" is now the win the event log always showed).
- The replay/aftermath layers render persisted data only; the renderer never
  decides outcomes; no unseeded randomness was added anywhere (display-text
  template choice still uses the existing deterministic hash-seeded RNG).

## 6. Tests/checks run — exact status

- `python -m pytest -q` (full suite, 1,294 tests incl. the 16 new): **green,
  exit 0** — run twice after the changes. (One unrelated flake,
  `test_server_save_boundary.py::test_load_save_accepts_managed_save_and_swaps_active_path`,
  failed in a single earlier full run, passes in isolation/module, and did
  **not** reproduce in either subsequent full run — order-dependent,
  pre-existing; flagged below.)
- Focused: replay-family files + conformance matrix + golden-log regression
  + use-cases/aftermath: green throughout.
- `npm run build` + `npm run lint` (frontend): **clean**.
- Playwright (chromium, fresh uvicorn server): `official-rules-replay`
  (incl. the new set-strip/swing assertions), `replay-score-parity`,
  `wt22-decision-proof`, `command-center-aftermath` (2), `v13_broadcast_layer`
  (2), `tier1_recognition` — **8/8 passed**.
- Live browser walk (preview, uvicorn, real career `watchability-verify`):
  full week loop through the UI, aftermath set chips render, replay set
  strip + game dividers + moment banner + highlight reel + speed control all
  live; set-chip jump → "GAME 2"; highlight jump → exact event; biggest-swing
  text == jumped event; Current Event card shows "G1 · T4 · CATCH ·
  HOME -1 / AWAY +1" with "...re-enters from the catch queue. (USA Dodgeball
  rule 22.)". **Zero console errors; zero horizontal overflow at 1440×900
  and 1280×720.**
- Outcome-invariance probes: §5.

## 7. Remaining gaps / owner-decision calls

1. **Old saves keep the old replay limitations.** Persisted event streams
   that predate this pass carry no return/game metadata; their replays keep
   cumulative-elimination courts (status quo) while still gaining the set
   strip (game results are read from `official_score_json`, which old
   official saves do have) — chips just aren't clickable. Re-deriving
   returns for legacy streams via FIFO queue simulation would be possible
   but is inference; deliberately not done.
2. **Rec recorded-outcome correction is forward-only** (old records are not
   migrated). If the owner wants historical legacy records reconciled to
   their event logs, that's a separate, explicitly-scoped migration.
3. **Official survivors column** (`match_records.home/away_survivors`) for
   officials still stores the box-score "never out across all games" count —
   a meaningless metric that is no longer displayed anywhere (officials are
   scored in game points everywhere post-WT-2/3). Cosmetic cleanup only.
4. **Official decision context** (why a thrower/target was chosen, catch
   posture reads) is still not persisted by the official engine — the
   Current Event card for officials now shows outcome truth (catch/out/
   return/rule ref) but not intent. That is the V16A "intent frames" slice
   in `docs/specs/2026-06-09-watchable-match-replay-research.md`; engine
   work, deliberately out of scope here.
5. **`test_server_save_boundary` order-dependent flake** (pre-existing):
   failed once in a full-suite run, passes everywhere else, including two
   subsequent full runs. Worth a look at shared `server._active_save_path`
   state between tests.
6. **States not browser-exercised this pass:** cloth-division ties (`tie`
   result-type chip renders "—" + tooltip; covered by unit test only),
   overtime/`narrative_note` playoff tiebreak copy (renders only on
   contested playoff results — unchanged from the §4 verification pass), and
   bye weeks (no replay; unchanged). Draw/no-point official states WERE
   exercised (W1 1-1 draw with no-point decider; probe + payload assertions).
7. **`stats.extract_player_stats` ignores returns** for `minutes_played` /
   plus-minus (a returned player stops accruing after their first out) and
   `revivals_caused` is hardcoded 0. Doesn't affect any scoreline; noted for
   a stats-truth follow-up.
8. `.claude/launch.json` gained an "E2E Uvicorn" config (tokenless server,
   matching the Playwright environment) used for preview verification.
