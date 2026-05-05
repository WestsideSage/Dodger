# Manager Mode — Design Spec

**Date:** 2026-04-26
**Status:** Design approved, ready for implementation planning
**Scope:** Convert the GUI from a single-match sandbox into a season-and-dynasty manager-sim experience that surfaces the existing engine's full breadth (franchise, season, awards, identity, news, records, rivalries, career, scouting, recruitment, development).

---

## 0. Context

The Tkinter GUI has just had its Phase 3 visual pass (`docs/retrospectives/2026-04-26-ui-ux-retrospective.md`). It now reads like a clean sandbox. Its remaining problem is structural, not cosmetic: **the GUI is a single-match sandbox**. Dynasty, seasons, franchises, awards, hall of fame, league wire, identity/nicknames, records, career stats, scouting, recruitment, and development all exist as tested engine modules but are reachable only through `dynasty_cli.py`. The user can run a match. They cannot play the game.

This spec describes the milestone that closes that gap — Manager Mode — built entirely on top of existing engine modules. The intent is to make the GUI **feel like playing a sport** ("MY team, scoring MY hits") inside a **season-and-dynasty arc** ("the players I scouted, the players I developed, the records they broke").

---

## 1. Goals

1. **Game-feel.** Watching a match should feel like watching a sport, not data viz: team identity, scoreboard, hit punctuation, MVP moment, end-of-match beat.
2. **Season arc.** Pick a club, play a full season (length determined by `scheduler.py` — illustrated below as 14 weeks), watch standings move, read headlines, end with awards and a champion.
3. **Dynasty arc.** Seasons accumulate. Players develop. Veterans retire. Records persist. Rookie classes arrive. Scouted prospects become signed players.
4. **Two ownership paths.** *Take Over a Club* (mid-tier or contender, win-now framing) and *Build a Club* (custom expansion franchise, hidden-gem scouting framing).
5. **Friendly mode preserved.** The current "any-team-vs-any-team" sandbox remains as a side door for engine testing.
6. **Integrity contract intact.** Every visual derives from `MatchEvent` or another engine source. The renderer never decides anything.

## Non-goals

- Audio (sound effects, music).
- Real portrait art for players or coaches.
- Camera motion or zoom in replay.
- Mid-match agency (timeouts, substitutions, real-time tactic pivots).
- Trades during the season.
- Salary cap, contracts, financial systems.
- Coaching staff hires, coordinator changes, coach contracts.
- Multi-save slots, multi-career profiles.
- Multi-season league archive viewer (Wire holds the linear history for now).
- Highlight reel export, clip sharing, social-share surfaces.
- Press conferences, morale events, fake-source narrative.
- Procedural league or team backstory.
- Custom league size, mid-career rule changes, custom rookie class size.
- Inter-club scouting visibility, scout hiring/firing/leveling.
- Heat maps, shot maps, spatial stats.
- Power rankings rendered as opinion.

---

## 2. Design Contracts

The integrity contract from `docs/specs/AGENTS.md` applies to every screen. In addition:

- **Event Log Is Canon.** Every visual on every screen is a derived view of a `MatchEvent` or an existing engine source (`stats.py`, `awards.py`, `news.py`, `records.py`, `career.py`, `scouting.py`, `recruitment.py`, `development.py`, `identity.py`). The UI does not invent state.
- **Renderer Never Decides.** The match resolves in one shot in the engine; the replay reads the log and animates feasible visuals. If log and visual disagree, visual is wrong.
- **No Win-Probability Numeric.** Pre-match shows style clash and matchup framing, never "you have a 67% chance to win." That commits to a number we'd have to defend if it lies.
- **Your Color Is The Highlight, Never The Background.** The cream/paper canvas remains neutral; the user's club color is used as accent, row tint, and side framing. Otherwise the "world outside your locker room" framing collapses.
- **One Player Profile Component, Four States.** Prospect (fuzzy ratings via `UncertaintyBar`) → signed (crisp) → veteran (crisp + career depth) → HoF inductee (crisp + retirement framing). One canonical card.
- **Manual screenshot review is part of the implementation contract.** Every implementation milestone ends with a screenshot capture in `output/ui-review-<phase>/` before the milestone is called done.

---

## 2.5 Engine Dependencies — Must Precede UI Implementation

The first draft of this spec assumed several engine modules were richer than they are. Direct source inspection shows otherwise. **Each item below is a first-class engine/design dependency, not an "API gap."** UI work that depends on these surfaces cannot start before the engine work lands.

### 2.5.1 `Club` model — data extension (small)

**Current:** `Club` has `club_id`, `name`, `colors: str` (single string like `"red/black"`), `home_region`, `founded_year`.

**Needed for UI:** primary color (hex), secondary color (hex), venue name, identity tagline.

**Action:** extend `Club` model with optional fields, persist via existing migration infra, populate the curated cast in `sample_data.py`. Keep `colors: str` as legacy field or remove via migration. Small, well-contained change.

### 2.5.2 `CoachPolicy` — control-set decision

**Current:** `target_stars`, `risk_tolerance`, `sync_throws`, `tempo`, `rush_frequency`. That's it.

**Spec earlier listed:** Target Ball-Holder, Catch Bias, Rush Proximity (none exist).

**Action — pick one:**
- **(A) v1 ships only the 5 existing controls.** Tactics screen shows 5 sliders, not 8. Defer expanded tendencies to a later balance-pass milestone with its own integrity tests.
- **(B) Engine work first: extend `CoachPolicy` with the missing fields**, wire each into the engine so changing the slider measurably shifts behavior (per AGENTS.md §4 legibility test), update golden logs with documented "why outcomes changed" notes, then UI surfaces them.

**Decision for v1:** **(A).** Eight sliders that don't all do anything would breach the integrity contract. Add new tendencies only via deliberate engine extensions with their own tests.

### 2.5.3 Lineup persistence — schema needed

**Current:** `Team.players: Tuple[Player, ...]` — flat roster ordered tuple. No starters/bench distinction. Match snapshots use the tuple order. No persisted "default lineup" or "per-match override."

**Needed:**
- A **lineup contract**: roster size N, starters count S (S ≤ N), bench is the rest. Engine documents how starters vs bench are used (today's match snapshot uses all players; this needs an explicit rule or stays as full-roster with "lineup" being purely a UI ordering hint).
- Persistence schema: `lineup_default(club_id, ordered_player_ids)` and `match_lineup_override(match_id, club_id, ordered_player_ids)` as new tables, or columns on existing tables. Migration follows existing infra.
- **Validation rules:** what happens when a default-lineup player retires, gets injured, or is released. Default rule: **invalid players are dropped silently from the default; the default is back-filled from highest-OVR remaining roster on match-time read.** UI flags the gap so the user knows their default needs attention.

**Action:** define the contract, add the schema, ship a `LineupResolver` that takes (club, default, override?) → ordered list of players for the snapshot. Engine match builder consumes the resolver instead of using raw roster order.

### 2.5.4 Post-match win-probability analyzer

**Current:** No engine-owned probability analyzer. Match Report's "Turning Points" and "UPSET tag" need one. Absent it, the UI would invent the numbers — which directly violates the integrity contract.

**Needed:** an engine module (`win_probability.py` or part of `stats.py`) that, given a resolved match's `MatchEvent` log, computes:
- **per-event WP delta** (post-hoc retrospective leverage; not a live prediction).
- **pre-match expected outcome** (used post-match only, to flag UPSET when the actual result deviates beyond a documented threshold).

**Critically: these are retrospective leverage estimates, not live predictions.** Wording on the Report screen and in module docstrings must call this out. The pre-match Match Preview screen does not show these numbers — that constraint stays in force.

**Action:** ship the analyzer with its own tests (monotonicity: better team has higher pre-match expected outcome; symmetry: swapping teams flips the numbers; deterministic from the log). UI consumes the analyzer; never computes its own estimate.

### 2.5.5 Scouting model — major engine extension

**Current:** stateless `generate_scout_report(player, budget_level, rng) -> ScoutingReport`. The report is one-shot — given a budget tier ("low"/"medium"/"high") it returns archetype + rating ranges (medium = 15-wide, high = 3-wide) or exact ratings (high). **There are no scout entities, no assignments, no confidence percentages, no prospect-board state, no persistence between scouting actions, no narrowing-over-time, no carry-forward across seasons.**

**Spec earlier described:** scouts as named entities with strengths, multi-week assignments, confidence narrowing, hidden-gem reveal deltas, season-to-season confidence persistence.

**Reframing:** the Scouting Center as described in Section 8 is the **target system**, but it depends on a substantial engine extension that does not exist. The UI cannot ship in the form described until the engine model exists.

**Action — two-track:**
- **v1 (this milestone):** **defer the full Scouting Center.** Either (a) no scouting surface in the GUI, or (b) a minimal "Scouting Reports" panel in Off-season that wraps the existing budget-tier function — pick a budget level, see one rookie's report, no persistence, no narrowing. This is honest about what exists.
- **v2 (later milestone, depends on engine work):** design and build the stateful scouting model — `Scout` entity with strengths, `ScoutingAssignment` with weeks-remaining and intermediate updates, per-prospect `ScoutingConfidence` that persists in SQLite and carries across seasons, `assign_scout(scout_id, player_id, weeks)` action, week-tick advances confidence. Then the full Section 8 UI ships on top of it.

The Section 8 design content stays in this spec as the **target vision** for the v2 milestone, clearly marked.

### 2.5.6 Recruitment competition — domain model needed

**Current:** `recruitment.py` has `generate_rookie_class()` and `build_transaction_event()`. No AI club ranking of prospects, no public-vs-private scouting information asymmetry, no roster caps, no sign rounds, no sniping logic, no parallel-clubs-signing-in-real-time.

**Spec earlier described:** the Recruitment phase as a real-time room with AI clubs signing in parallel, scouting confidence carry-forward giving the user an edge, hidden-gem signings sometimes lost to competitors.

**Reframing:** the Recruitment phase is the heart of the dynasty fantasy and the explicit payoff for scouting. **It is a substantial engine domain model**, not a UI wrapper. It depends on the scouting model (2.5.5) for the public-vs-private information asymmetry to mean anything.

**Action — two-track:**
- **v1:** **defer the full Recruitment phase. Ship a simple Draft beat instead** — lists the rookie class from `generate_rookie_class`, lets the user click-to-sign one or more rookies into open roster slots, no AI competition, no sniping, no public-vs-private info. Clearly labeled in copy that scouting + competing clubs come in v2.
- **v2 (after scouting v2):** design and build the recruitment domain model — AI club preferences (each club has a tendency profile influencing what kind of prospects they target), public ratings vs the user's private scouting view, sign-round mechanics, sniping likelihood, transaction event ticker source. Then the full Section 9 Beat 9 UI ships on top of it.

### 2.5.7 Match-MVP function

**Status (M0 verified):** No `compute_match_mvp` existed in `awards.py`; only `compute_season_awards`. Added in M0: `awards.compute_match_mvp(player_match_stats: Dict[str, PlayerMatchStats]) -> Optional[str]` reuses the existing `_mvp_score` formula with a deterministic player_id tiebreak. Empty input returns `None`.

### 2.5.8 Playoff support in `scheduler.py`

**Status (M0 verified):** No playoff support. `scheduler.py` exposes only `generate_round_robin`. v1 ships regular-season-by-record champion. The module docstring documents this status, and `season_format_summary()` returns a UI-consumable dict (`{"format": "round_robin", "playoffs": False, "champion_rule": "best_regular_season_record"}`) so Schedule and Standings labels stay accurate when playoffs eventually land.

### 2.5.9 Summary table

| Dependency | Size | v1 status | v2+ status |
|---|---|---|---|
| `Club` color/venue/tagline fields | Small | Landed (M0) | — |
| `CoachPolicy` expanded fields | Medium | Deferred (v1 uses existing 5) | Optional |
| Lineup persistence + resolver | Medium | Landed (M0) | — |
| Win-probability analyzer | Medium | Landed (M0) | — |
| Scouting model (stateful) | Large | Deferred (full Center is v2) | Required |
| Recruitment domain model | Large | Deferred (v1 ships simple Draft only) | Required |
| Match-MVP function | Small | Landed (M0) | — |
| Playoff support | Medium | Verified absent (M0); v1 ships regular-season-by-record | Optional |

---

## 3. Section 1 — Onboarding & Career Path

### 3.1 First-launch flow

1. **Splash.** Wordmark, brief tagline, two CTAs: **New Career** (primary) and **Friendly Match** (secondary). Small "Continue Career" appears once a save exists.
2. **Career Path Picker.** Two tiles, each filling roughly half the window:
   - **Take Over a Club.** *(v1, active.)* Inherits roster, history, expectations from one of the curated 6–8 fictional clubs. Mid-tier or contender start. Framing: *"Win now."*
   - **Build a Club.** *(v2 — disabled tile in v1.)* Renders greyed-out with a "Coming Soon" badge and the copy *"Expansion franchises arrive once scouting and recruitment systems are in place."* Click is a no-op in v1. **Implementers: do not build the club editor flow in v1.** Tile activates in v2 once the scouting + recruitment domain models land.
3. **If Take Over →** club picker grid. Each card shows: team name, primary/secondary color block, venue, one-line identity tagline ("Aurora Pilots — Power-arm aggression, deep scouting tradition"). Click selects, "Confirm Coach" commits.
4. **Build a Club branch (v2 only).** Club editor (text fields and color pickers for name, colors, venue, tagline) → confirm. **Not implemented in v1.**
5. **Welcome beat.** Brief transition: *"Welcome to the [Aurora Pilots], Coach. Week 1 begins now."* → drops into Hub.
6. **Subsequent launches.** Splash shows: **Continue Career** (primary), **New Career** (with overwrite warning), **Friendly Match** (secondary).

### 3.2 Curated cast vs procedural

The 6–8 fictional clubs are a **fixed curated cast**, hand-tuned with identity (name, colors, venue, vibe, signature style). They reuse what exists in `sample_data.py` / `league.py`. **The `Club` model needs extension first** (per §2.5.1): add primary color (hex), secondary color (hex), venue name, identity tagline. Today's `colors: str` ("red/black") is insufficient. `sample_data.py` repopulates with the full identity per club. Curated cast trades flexibility for memorability — the same teams every career, becoming *known*.

### 3.2.1 Build a Club is a v2 milestone, not v1

Per §2.5.5 and §2.5.6, the "Build a Club" expansion path's emotional payoff depends on the stateful scouting model and recruitment domain model — neither of which exists today. **v1 ships with Take Over a Club only.** The Career Path Picker still exists in v1, but the Build a Club tile is shown as **Coming Soon** (greyed, not clickable, with a brief copy line: *"Expansion franchises arrive once scouting and recruitment systems are in place."*). When v2 ships, the tile activates.

### 3.3 Persistence

- **Single save slot for this milestone.** Multi-save deferred.
- SQLite via existing `persistence.py`.
- Auto-save after each match and after each off-season ceremony beat.
- New Career on top of an existing save requires confirm.
- Friendly matches never touch the save.

---

## 4. Section 2 — Season Hub

The room the user keeps coming back to. Answers: *"Where am I in the season, and what's my next move?"*

### 4.1 Layout (top to bottom)

1. **Identity Bar.** Always visible across Career screens. Shows: club's primary color band, club name, current record, season number + week (`Aurora Pilots · 4-2 · Season 1 · Week 7 of 14`). Persistent "you" indicator.
2. **Next Match card.** Dominant element. Team-colored framing, opponent name + their color block, opponent record, brief context line (recent form), key matchup callout, primary CTA: **Go to Match Day →**.
3. **Three-column row below:**
   - **Standings glance** — top 5 of league table, your row highlighted in your color. "View full standings →" link.
   - **League Wire** — 3–4 latest headlines tagged by type (UPSET / RECORD / RIVALRY / MILESTONE / RESULT). Click → full Wire page.
   - **Spotlight** — one player from your roster. **v1 rotations:** Player of the Week (post-match, by stats), Development Watch (between matches, biggest recent OVR delta from `development.py`), Returning Headliner (week 1 of a season — your highest-OVR returning player). **v2 adds:** Hidden Gem (after a scouting reveal). Click → Player Profile.
4. **Reminder strip** (only when relevant). **v1 inline alerts:** *"Roster fatigue: 2 starters at risk"*, *"Lineup default has invalid players — needs attention"*, *"Match Report unread from Week N"* (driven by the career state machine). **v2 adds:** scouting-related alerts (*"3 unassigned scouts"*, *"New prospect tier unlocked"*). Click jumps to the relevant destination.

### 4.2 Design choices

- **Hub replaces "Home."** The current Home tab's Quick Match / Edit Teams / Randomize cards relocate to Friendly mode.
- **Your color is everywhere.** Identity Bar, standings highlight, Next Match team-side framing — your color is the persistent visual anchor.
- **Empty states still have copy.** Week 1 hub: standings show all 0-0 with you highlighted, Wire shows a "Season opens this week" headline, Spotlight shows your top returning player or top rookie.

---

## 5. Section 3 — Roster & Player Profile

### 5.1 Roster screen

- **Identity Bar persists.**
- **Roster summary strip:** club Overall, average age, top 3 rotation, fatigue/injury risk count, projected league finish band.
- **Sortable table:** Player | Role | OVR | core ratings (POW/ACC/DOD/CAT/AWR/STM) | Age | Form | **Devel** | Status.
  - **Devel column** — `↑↑ / ↑ / → / ↓` arrow per player, driven by `development.py` rolling delta over the last N matches/seasons.
  - **Status column** — small badges (ROOKIE, VETERAN, INJURED, FATIGUED, IN-FORM, SLUMP, CAPTAIN, etc.). Multiple stack horizontally.
- **Right panel / drawer:** selected player quick view. "Open Profile →" opens the full card.
- **Filters:** rotation only / full roster / by role / by archetype / by development trend.
- **Compare two players** via shift-click — designed for, deferred in v1.

### 5.2 Player Profile (trading-card view)

The screen that makes a fictional player matter. Full-window or modal.

- **Header band** in player's club color. Name, nickname (`Marlon "Laser" Reed`), jersey, archetype (POWER ARM), role (Sniper), age, tenure with club.
- **Portrait slot** — geometric avatar v1 (initials in a colored circle, scaled-up version of the court token). Slot exists for real art later.
- **Ratings panel** — every rating with `RatingBar`, numeric value, faint role-relevance indicator. POW first, then ACC, DOD, CAT, AWR, STM.
- **Traits & badges** — `IRONWALL`, `CLUTCH`, `LOW STAMINA`, etc. From `identity.py`.
- **Career stats table** — season-by-season rows from `career.py`: GP, hits, catches, dodges, MVP votes, championships.
- **Signature Moments** — short list of records broken / clutch plays from `records.py`.
- **Development history** — small line chart or stepped diff showing how each rating has moved across seasons (`development.py`).
- **Awards row** — MVP, Best Thrower, Best Catcher, Best Newcomer (the v1 award set per `awards.py`). v2 adds Defensive POY / All-League if `awards.py` is extended.

### 5.3 Profile in fuzzy mode (Scouting) — v2 only

> **v2 target vision; not in v1 scope.** Depends on `scouting_confidence` (state that doesn't exist in `scouting.py` today, per §2.5.5) and the `UncertaintyBar` component (also v2). v1 Player Profile ships with crisp ratings only.

For prospects whose `scouting_confidence < threshold`, ratings render as `UncertaintyBar` (min/max range). Archetype and traits show as "scouts believe…" until confidence narrows. A **WORTH ANOTHER LOOK** badge surfaces when confidence is low *and* the best estimate is meaningfully above the floor — never definitive, just a hint.

### 5.4 Click-through is universal

Any player name in the app — match report, league leaders, headline byline, lineup card, scouting board — opens the Player Profile. No edits live on the Profile or Roster screen; lineup edits live in Tactics / Match Preview.

---

## 6. Section 4 — Tactics & Match Preview

### 6.1 Tactics (between matches)

- **Identity Bar persists.**
- **Preset row** — five preset playstyle cards (Power-Arm Aggro, Catch-Heavy Attrition, Sniper Control, Swarm & Overload, Balanced Spreadsheet Enjoyer). Each card: name, one-line description, strengths, risks, best-fit archetype tag. Click selects; sliders snap to preset values.
- **Tendency sliders — v1 ships the 5 actual `CoachPolicy` fields** (per §2.5.2): Target Stars, Risk Tolerance, Sync Throws, Tempo, Rush Frequency. Each slider has: label, current value, plain-language effect string, and a roster-fit warning if the setting fights your players. The UI guide's wider list (Target Ball-Holder, Catch Bias, Rush Proximity) does not ship until those fields are added to `CoachPolicy` with engine behavior + tests in a later balance-pass milestone.
- **Lineup panel** on the right — drag-to-reorder, fatigue/form chips. Click name → Profile. **Lineup model per §2.5.3:** the lineup is an ordered list of player IDs; the first S are starters (S configurable, defaults to engine value), the rest are bench. The panel shows a clear starters/bench divider. Invalid players (retired, released) are auto-dropped on read with a UI flag.
- Tactics persist per-club, saved with the career. Lineup defaults persist alongside.

### 6.2 Match Preview (entered from "Go to Match Day")

The pre-match scouting screen. Where the match earns drama before it starts.

1. **Versus header** — your color band on the left, opponent color band on the right, names + records, week. Visual fight-card framing.
2. **Style clash callout** — engine-derived prediction from comparing tactics + roster ratings on both sides. Diagnostic, not flavor: *"Your Catch-Heavy Attrition vs. their Power-Arm Aggro — survival depends on opening-volley catchers."*
3. **Key matchups row** — 3 cards, each a 1-vs-1 (their best thrower vs your best catcher; their best dodger vs your best thrower; rivalry callout if `rivalries.py` flags one). Click → side-by-side comparison.
4. **Stat strip** — team rating comparison (offense, defense, depth, fatigue going in) as bars. No hidden numbers.
5. **Pre-match coaching panel** — slim Tactics override: tweak sliders or lineup just for this match. *Apply for this match only* vs *Save as new default*.
6. **Bottom CTA bar** — **Start Match →** (primary, your color), **Go Back** (secondary).

### 6.3 Lineup model

Lineup lives in two places, same data: Tactics is the persistent default; Match Preview is the per-match override. Preview shows a small badge when the lineup differs from default (*"Adjusted for this match"*).

### 6.4 No win-probability number

The integrity contract forbids it. Style clash and matchup framing carry the same weight without committing to a number we'd have to defend.

### 6.5 Friendly mode reuses Match Preview

Both sides editable in Friendly. Same cinematic pre-match buildup.

---

## 7. Section 5 — Match Replay (Game-Feel Theater)

The screen that converts "watching dots" into "watching MY team score hits." Most of the perceived game-feel lives here.

### 7.1 Frame layout

Full-window takeover. No tabs visible. Top to bottom:

1. **Scoreboard HUD** (slim, full-width). Left: your team — color block, name, **survivors count (large numeric)**, hits scored. Right: opponent — same. Center: phase indicator (`Volley 3 · Tick 0:42`) and a momentum bar (subtle, derived from recent log events).
2. **Court canvas** — dominant, ~60% of vertical space. Wider than current Replay Arena. Your side faintly tinted in your color, theirs in theirs.
3. **Active Event Banner** — between court and log. Single line, large type, punch-in/punch-out per event. Examples: `MARLON "LASER" REED — HIT on Theo Park` / `THEO PARK — CATCH! Eliminates Marcus Vale.`. Player names clickable to Profile (during pause).
4. **Event log strip** — collapsed by default (last 3 events). Click expands to full Inspector with probability/RNG/ratings.
5. **Bottom control bar** — Speed (¼× ½× 1× 2× 4×), Pause, Step back, Step forward, Jump to next highlight, Skip to end.

### 7.2 Pre-match buildup beat

Before the first event fires (after Match Preview's Start Match), a ~2-second beat:
- Your side wipes in from left, theirs from right. Big text: `AURORA PILOTS vs. NORTHWOOD WRECKERS` centered. Resolves into the Scoreboard HUD.
- Skippable with a single click.
- Doesn't gate anything. Replays at the start of every period boundary if/when the engine adds periods.

### 7.3 Game-feel devices (UI-only, engine untouched)

- **Pacing.** Default playback is slow enough to *read*: ~1.2s base per event, 1.8–2.5s for big events (catch, elimination, comeback). Speed control multiplies uniformly.
- **Hit punctuation.** Brief red pulse on target token. Score increments with snap-in animation. Banner hits with stronger weight. ~200ms total. No screen shake.
- **Catch punctuation.** Golden ring pulse on catcher token. Banner reads dramatically. 400ms hold before next event. Thrower token grays out (eliminated).
- **Possession marker.** Held ball renders next to the holder's token with faint pulsing outline.
- **Ball trajectory line.** Brief flat line traces ball path on resolved throws. Charcoal for HIT, gold-rimmed for CAUGHT, sage for DODGED, fading dotted for missed/wide. ~600ms then fades.
- **Selected-thrower / target focus.** Thrower has subtle team-color spotlight outline; target gets a reticle. Both fade after resolution.
- **Out-zone bench.** Eliminated players slide to a bench area on their team's side, dimmed and grayscale-tinted with initials still readable.
- **Player tokens with identity.** Jersey number visible at default zoom; full name in tooltip on hover (during pause). Star players (each team's top 3 by OVR) get a subtle ring accent.
- **Crowd murmur chyron.** Optional bottom-edge chyron with templated narrative beats: *"Pilots crowd on their feet — that's three straight hits."* Toggleable. Never announces an outcome before the engine resolves it.
- **End-of-match moment.** Final event lands → screen darken → winning team color band wipes across → big stamp `FINAL — Aurora Pilots 8, Wreckers 3 (3 survivors)` → 1.5s hold → MVP card pop → **Continue → Match Report** CTA.

### 7.4 Integrity contract on the replay screen

Every visual derives from a `MatchEvent`. Pause / step / jump are pure log-position operations. Inspector at any pause shows probability/RNG/ratings for the current event. No outcomes invented, no animations that contradict the log.

---

## 8. Section 6 — Match Report

The cooldown room. Where a result becomes a story you can argue with.

### 8.1 Layout (top to bottom)

1. **Result band** (~120px tall, full-width). Winning team color dominates the band. Massive score, survivors in parens, label: `FINAL · Week 7 · Aurora Pilots 8, Wreckers 3 (3 survivors)`. Tags: **UPSET** (engine-flagged via post-hoc win-probability differential), **RIVALRY** (per `rivalries.py`).
2. **MVP card** — bigger than profile thumbnail, smaller than full card. Portrait slot, name + nickname, line score (`4 hits · 1 catch · 0 outs`), one-sentence "why MVP" derived from stats. Click → full Profile.
3. **Box score table** — both teams, side-by-side or stacked. Per-player: hits, catches, dodges, throws attempted, accuracy %, time-on-court, +/− (survivors differential while on court). Sortable. Names clickable.
4. **Turning Points panel** — 3–5 events the engine flags as decisive (biggest swing in win probability, longest run, comeback moment, biggest upset roll). Each is a clickable event card showing tick/actor/target/outcome and *"This swung the match X% toward [team]."* Click → opens replay scrubbed to that event.
5. **Probability outliers** — events where the RNG roll fought the expectation (>20% surprise). *"Theo Park caught a 0.71 throw on a 0.18 roll. That's the match."* Closes the integrity contract: weird outcomes get a math reason on screen.
6. **Headlines for this match** — 2–3 templated `news.py` entries shown inline so the narrative beat lands before the user even visits the Wire.
7. **Records & Milestones strip** — career highs, season highs, club records broken or approached (`records.py`).
8. **Standings update preview** — your row before/after with a movement arrow.
9. **Bottom CTA bar.** **Back to Hub →** (primary), **Watch Replay** (replays match with scoreboard intact), **Open League Wire**.

### 8.2 Design choices

- **Result band carries the emotional payoff.** Win = your color dominates, MVP from your roster. Loss = their color dominates, but the rest of the report is framed from your seat (your box score first, your turning points emphasized).
- **Two click depths only.** Box score → Profile is one click. Turning Point → Replay is one click. No deeper drill-downs needed in this view.
- **Same Report for friendlies.** Friendly mode hides standings and records (friendlies don't count toward records — engine concern, design assumes).

### 8.3 Engine touchpoint — formalized

The Turning Points and UPSET tag depend on a **post-hoc win-probability analyzer** that **does not currently exist** (verified — no engine module owns this; only UI/CLI references). Per §2.5.4, this is a v1-required engine module:

- **`win_probability.py`** (or part of `stats.py`) consumes a resolved match's `MatchEvent` log and emits per-event WP delta + pre-match expected outcome.
- **Wording on the Match Report screen and in module docstrings must call these out as retrospective leverage estimates, not live predictions.** *"Theo Park's catch swung the leverage 32% toward Northwood (post-hoc estimate)."*
- The analyzer ships with monotonicity + symmetry + determinism tests, per AGENTS.md §1.
- The Match Preview (§7) **does not** consume this analyzer at all. Pre-match shows style clash and matchup framing, never an expected outcome number. The constraint stands.

**The WP analyzer is a Milestone 0 gate, not optional v1 scope.** If it slips, Milestone 0 has not finished; UI work does not proceed. This avoids the half-built Match Report that would result from making it skippable.

---

## 9. Section 7 — Standings, Schedule, League Wire

A single top-level **League** destination with three sub-views switched by a segmented control: **Standings · Schedule · Wire**. Keeps the top-level nav lean.

### 9.1 Standings sub-view

- Full league table — Team, Record (W-L-D), Win %, Hits Scored, Hits Allowed, Diff, Streak, Last 5 (mini-bar of W/L pips). Your row highlighted in your color. Sortable.
- **Click a team row** → opponent dossier modal: record, top 3 players (clickable), recent form, head-to-head with you, when you next play them.
- **League leaders strip** — three compact cards (Top Hits / Top Catches / Top Awards Vote-Getters), each with 3 ranked players. Your players highlighted. Click → Profile.

### 9.2 Schedule sub-view

- **Your season at a glance** — horizontal week strip spanning the full season (engine-determined length, e.g. Weeks 1–14). Played weeks show result tinted W=your color / L=opponent color. Future weeks show opponent name. Current week marked **NEXT**.
- **Click a week cell:**
  - Past → that match's Report (replay reachable from there).
  - Future → Match Preview-light (opponent dossier, predicted style clash, no Start button until the week comes).
- **Below the strip:** full league schedule grid, filterable.

### 9.3 League Wire sub-view

- Chronological feed of headlines, latest first. Each card: tag (UPSET / RECORD / RIVALRY / MILESTONE / RESULT), one-line headline, 2–3-sentence body, byline tick (*"Week 6 · Wire"*), tappable player/team names linking to Profile or dossier.
- **Filter chips:** All / About Your Team / Records / Upsets / Around the League. Default All.
- Wire entries persist across the save. End-of-season generates summary entries (champion, awards). Season transitions generate rookie-class entries.

### 9.4 Design choices

- **Schedule strip is calendar AND memory device.** Past = replay history at a glance. Future = runway. Same widget answers both.
- **Click-through to Profile and to past matches is a hard rule everywhere on this screen.** Without it the surface is dead.
- **No invented narrative beyond `news.py`.** No fake tweets, no fake fan reactions, no generated coach quotes.

### 9.5 Engine touchpoints

`league.py` (standings), `scheduler.py` (schedule), `news.py` (Wire), `awards.py` + `stats.py` (leaders). **No engine extension needed.**

---

## 10. Section 8 — Scouting Center

> **v1 status: deferred to v2.** The stateful scouting model described below (scouts as entities, multi-week assignments, confidence narrowing, season-to-season carry-forward, hidden-gem reveal deltas) does not exist in `scouting.py` today (per §2.5.5). The Section 8 design content is the **v2 target vision** — it ships once the engine model lands.
>
> **v1 fallback options (pick at plan-writing):**
> - **(A) No scouting surface in v1.** Cleanest. Off-season generates rookie classes and recruitment auto-assigns or uses the simple draft order from §11. Wait for the full feature in v2.
> - **(B) "Scouting Reports" panel inside the v1 Draft beat only.** Wraps the existing `generate_scout_report(player, budget_level, rng)` function — pick a budget tier, see one rookie's report, no persistence between seasons, no narrowing over time. Honest minimum that exposes the existing helper. The v1 Draft can render rookies with crisp ratings or with this optional report panel; pick at plan-writing.
>
> **v1 does NOT show "Scouting" as a top-level nav destination.** That tab activates in v2 when the model exists. The full Section 8 layout below is the v2 target.

The screen that pays off "I found this guy when no one else would." Multi-season attachment compounds here.

### 10.1 Layout

- **Scout Status strip** at the top — scouts as small cards: name, current assignment, days remaining, "available" if idle. Reminder badge if any unassigned. Click → assignment dialog.
- **Prospect Board** (dominant) — grid/table hybrid. Columns:
  - Player (name + age)
  - Position / archetype (best-guess if low confidence)
  - **Confidence bar** (0–100%)
  - **Estimated OVR** with uncertainty range (`63 ± 12` or fuzzy bar via `UncertaintyBar`)
  - Best guess on hidden trait (`?` if confidence too low)
  - Hometown / origin context
  - Last scouted
- **Filters & sort:** archetype / age band / confidence tier (Unknown / Glimpsed / Known / Verified) / assigned-vs-not. **Sorting by *low* confidence with *high* estimated OVR is the explicit way to find gems.**
- **Prospect detail panel** (click a row) — same Player Profile layout, but in fuzzy mode with the WORTH ANOTHER LOOK badge when applicable.
- **Scout Assignment dialog** — pick prospect from a list, see scout strengths, confirm. Assignment lasts N weeks. Intermediate updates if `scouting.py` supports them; otherwise full reveal at end.

### 10.2 The on-screen dopamine loop

- Week N: Prospect "Dax Marrow, age 18, OVR 58 ± 18, conf 22%." Assign Scout Vera. Vera moves Available → Assigned.
- Week N+3: Vera files report. Hub banner notification. Confidence 68%, band tightens, OVR estimate is now 71 ± 6. WORTH ANOTHER LOOK badge.
- Week N+6: Reassign Vera. Confidence 91%, OVR 74 verified, IRONWALL trait surfaced. **Hidden gem.** Wait for the off-season to sign him before someone else notices.

This loop is the explicit emotional target.

### 10.3 Design choices

- **Confidence is the primary axis.** Sorting by *low* confidence with *high* estimated OVR is a first-class sort, not a strange filter combo.
- **Uncertainty bars are honest.** When confidence is 22%, the bar is *wide*. The UI does not pretend the prospect is exactly OVR 58.
- **Reveals are visible.** When a scout report lands, the UI shows the *change* (old band → new band) for one cycle so the narrowing registers.
- **Same Profile component reused.** Once a prospect signs, the same card crisps from fuzzy to verified — visible reward.
- **No "scout star ratings."** The UI never tells the user this prospect is a 5-star, because that would mean lying when scouting was wrong. Confidence + uncertainty band carries the load.

### 10.4 Engine touchpoints — v2 model requirements

The current `scouting.py` is a stateless one-shot helper (per §2.5.5). The Section 8 UI is **v2 only** and depends on a new engine model that **must be designed and built before this UI ships**. The v2 engine model must expose:

- a prospect pool with hidden true ratings,
- per-prospect confidence + estimate with bounds (persisted in SQLite),
- scout entities with strengths (persisted),
- an `assign_scout(scout_id, player_id, weeks)` action that mutates persisted state,
- a week-tick that advances scouting confidence and emits intermediate updates,
- season-transition logic that carries confidence forward.

These are **engine design requirements** for v2-A, not assumptions about today's module. v2-A is its own milestone with its own design + plan + tests before the Section 8 UI is built.

---

## 11. Section 9 — Off-season: Recruitment, Development, Season Transition

> **v1 vs v2 split:**
> - **v1 ships beats:** Champion Crowning · Season Recap · Awards Ceremony · Development Summary · Retirements & Aging · Schedule Reveal · transition to next season. **6 beats.** All driven by existing engine modules (`awards.py`, `development.py`, `season.py`, `franchise.py`, `scheduler.py`, `news.py`).
> - **v1 skips:** Records Ratified beat (depends on `records.py` integration depth — verify in plan-writing; if cheap, include), HoF Induction beat (depends on whether HoF threshold logic is in place — verify), Rookie Class & Free Agents Drop full preview, **the interactive Recruitment / Signing Phase**.
> - **v1 rookie/recruitment slot: a simple Draft beat.** Lists the rookie class generated by `generate_rookie_class()`, shows each rookie's crisp ratings (no fuzzy mode in v1), and lets the user click-to-sign one or more rookies into open roster slots up to the cap. **No AI competition.** Clearly labeled in copy: *"v1 Draft — competing clubs and scouting come in v2."* Unsigned rookies roll into a free-pool list available next off-season (simple list, no scouting). This gives the off-season a small agency beat without faking the v2 system.
> - **v2 ships:** the full 10-beat ceremony as written below, including the interactive Recruitment phase with AI club competition, sniping, real-time ticker — built on top of the **recruitment domain model from §2.5.6**.
>
> The full 10-beat content stays in this section as the v2 target vision.

A guided ceremony, not a menu. Each beat is a moment the user has earned. Each has Continue → and Skip Section. Auto-saves between beats.

### 11.1 The 10-beat flow

1. **Champion Crowning.** Final standings lock. Winner color sweep, champion banner. If you won — your color dominates, MVP card, ticker-tape moment. If not — still a beat the league closes on.
2. **Season Recap (your team).** Record, finish, biggest win, worst loss, season headliners, season grade derived from preseason expectation vs actual finish.
3. **Awards Ceremony.** Reveal one at a time (~1s each). **v1 award set matches actual `awards.py` output** (verified — `compute_season_awards` returns MVP, Best Thrower, Best Catcher, Best Newcomer): **MVP → Best Thrower → Best Catcher → Best Newcomer**. Each card: trophy, recipient (color-banded by club, clickable to Profile), brief justification from stats. Your winners highlighted. **v2 expansion:** Defensive POY, All-League First Team, All-League Second Team — added once `awards.py` is extended with new award types and tests.
4. **Records Ratified.** Records broken / set. Cards per record: club records, league records, career milestones. Your players highlighted. Source: `records.py`.
5. **Hall of Fame Induction.** If a retiring veteran clears the HoF threshold, induction beat with career stats summary, signature moments, awards roll. Skipped if nobody qualifies this year.
6. **Development Summary.** Your full roster, year-over-year deltas. Each row: name, age, OVR before → after, per-rating deltas (POW +3, etc.), icon for major archetype evolution. Sorted by biggest gainers first. Source: `development.py`.
7. **Retirements & Aging.** Players who retired (your roster + league notable). Aging veterans whose ratings declined. Honest framing.
8. **Rookie Class & Free Agents Drop.** "The new prospect pool is in." Top 10 rookies briefly previewed (mostly fuzzy — scouting hasn't started). Free agents from retirements / contract ends flagged.
9. **Recruitment / Signing Phase.** *(THE INTERACTIVE BEAT.)* Full-window, two panels:
   - **Left:** prospect & free-agent pool. Sortable, filterable. Last season's scouting confidence carries forward — your hidden gems still look like hidden gems to you.
   - **Right:** your roster slots (open highlighted, filled showing current player). Roster cap from engine.
   - **Sign action.** Click prospect → Sign. **Other clubs sign in parallel.** Each round, competing clubs may snipe a target (more likely if your confidence-based ranking matched theirs publicly). Right-edge ticker shows it happening (*"Northwood signed Dax Marrow."*). Hidden gems — players you scouted but who look mediocre publicly — usually still arrive at your door.
   - **Confirm Signings →** ends phase.
10. **Schedule Reveal.** Next season's schedule generates. Identity Bar updates (`Season 2 · Week 1 of N`, where N is engine-driven). Brief overview: opening match, biggest rivalry game's week, byes if any. CTA: **Begin Season 2 →** → Hub.

### 11.2 Design choices

- **Sequenced ceremony beats every menu.** Each screen is a moment, not a panel.
- **Recruitment is the only interactive beat.** Everything else is read-confirm-continue.
- **Scouting confidence carries forward.** This is the dynasty math. Last season's scouting work makes this off-season's signings smarter.
- **AI clubs sign on-screen, in real-time ticker.** Recruitment phase feels like a *room* you're competing in, not a draft form.
- **Same Profile component reused.** Prospect → signed → veteran → HoF, one card across four states.
- **Auto-saves between beats.** Quit after Awards, return next session, resume at Records.

### 11.3 Engine touchpoints — v1 vs v2

**v1 ceremony beats use existing modules:** `awards.py` (verified: returns MVP, Best Thrower, Best Catcher, Best Newcomer), `development.py` (year-over-year deltas), `season.py` + `franchise.py` (transition orchestration), `scheduler.py` (next-season schedule), `news.py` (Wire entries for transitions), `career.py` (career stats roll-forward), `recruitment.py` `generate_rookie_class()` for the v1 Draft beat.

**v2 ceremony additions depend on:**
- The v2-A scouting model (per-prospect confidence persisting across season transition).
- The v2-B recruitment domain model (AI club preferences, sign rounds, sniping). Built as separate milestones with their own designs and plans.
- Possible `awards.py` extension for Defensive POY / All-League awards (own milestone, own tests).

### 11.4 Risks called out — split by milestone

**v1 risks:**
- **v1 Off-season thin slice should be Champion → Recap → Awards → Development → Retirements → v1 Draft → Schedule Reveal.** Ship that end-to-end before adding optional beats (Records Ratified, HoF Induction).
- **v1 Draft tuning.** Even without AI competition, the Draft beat needs sensible defaults: how many rookies are presented, how many a club can sign, what happens to unsigned rookies (released to next season's free pool? deleted?). Decide in plan-writing.
- **Award copy — "Best Newcomer" not "Rookie of the Year."** UI copy must match engine vocabulary unless `awards.py` is extended.
- **Playoff support in `scheduler.py`** — verify in plan-writing. v1 ships regular-season-by-record champion if absent. Playoffs are a separate milestone.

**v2 risks (deferred, captured here for completeness):**
- v2 Recruitment competition needs tuning — too aggressive and user never gets their gems; too soft and scouting feels pointless. Manual playtesting required when the v2 milestone is built.
- v2 Scouting model is large — own design, own plan, own tests before any UI work.

---

## 12. Section 10 — Persistence, Navigation Shell, Friendly Mode

### 12.1 Persistence

- Single save slot. SQLite via `persistence.py`. Multi-save deferred.
- Auto-save triggers: after each match, after each off-season beat, on clean app close.
- Manual "Save" entry in nav exists only as reassurance — auto-save runs regardless.
- **v1 save scope:** career identity, full league state, all match histories (event logs included so any past match is replayable), current season + week, persisted tactics & lineup defaults, career-state-machine cursor, v1 Draft state (signed-this-offseason rookies + unsigned-rookie free pool).
- **v2 save scope additions:** scouting confidence per prospect, scout entities + assignments, recruitment-phase state (sign rounds, AI club preferences in flight). These persist alongside v1 fields once v2-A / v2-B land.
- Load on launch: existing save → splash shows **Continue Career** (primary). **New Career** requires confirm. **Friendly Match** never touches the save.

### 12.2 Navigation shell

- **Identity Bar always-on in Career mode** except in full-window flows (Match Day, Off-season ceremony) which take over completely. Friendly mode shows a small "Friendly Match" banner instead of the Identity Bar.
- **Primary nav: top tab bar.** Restyled via `ui_style.py` — not default `ttk.Notebook` chrome.
  - **v1: 5 destinations** — **Hub · Roster · Tactics · League · Save**. (No Scouting tab in v1; see §10 and §2.5.5.)
  - **v2: 6 destinations** — Scouting tab activates between Tactics and League once the stateful scouting model lands.
- **Match Day and Off-season are flows, not tabs.**

### 12.3 Friendly mode

- Entry from Splash. Bypasses career persistence entirely.
- Setup screen = Match Preview with both sides editable (teams, lineups, tactics, randomize).
- Replay and Report reused unchanged — they accept (teams, event log) and render.
- After Report: **Play Another / Back to Splash**.
- Net effect: today's "test any matchup" workflow preserved as a curated side door, with the new visuals.

### 12.4 What survives from current sandbox

**Modules kept and extended:** `ui_style.py`, `ui_components.py`, `ui_formatters.py`, `court_renderer.py`. Codex's Phase 3 work is the foundation.

**Reworked:**
- Home → Splash + Hub.
- Roster Lab → Roster + Player Profile.
- Coach Board → Tactics (your-club-only in Career; both clubs in Friendly).
- Replay Arena → in-flow Match Replay.
- League Wire → League → Wire sub-view (joined by Standings, Schedule).

**New screens (v1):** Splash, Career Path Picker (Build a Club shown as Coming Soon), Identity Bar, Hub, Match Preview, in-flow Match Replay (HUD + buildup + end-of-match moment), Match Report, Player Profile (full + compact), v1 Off-season beat sequence (Champion · Recap · Awards · Development · Retirements · v1 Draft · Schedule Reveal).

**New screens (v2):** Custom Club Builder, Scouting Center, full 10-beat Off-season ceremony with interactive Recruitment, fuzzy-mode Profile.

### 12.5 New shared components

Extend `ui_components.py` with: `IdentityBar`, `TeamColorBlock`, `VersusHeader`, `ScoreboardHUD`, `EventBanner`, `PlayerCard`, `PlayerCardCompact`, `UncertaintyBar`, `DevelopmentArrow`, `HeadlineCard`, `AwardCard`, `CelebrationBeat` (sweep/pop animations).

---

## 12.6 Career State Machine — explicit

To prevent save/resume edge cases from leaking into every screen, the career has an explicit state machine. The save persists `(state, payload)` and every screen reads from it.

**States:**

| State | Meaning | UI shell shows |
|---|---|---|
| `splash` | No save loaded yet, or user backed out to splash | Splash screen |
| `season_active_pre_match` | A season is in progress, current week's match is not yet played | Hub (default) or any nav destination |
| `season_active_in_match` | User has entered Match Day flow but not finished | Match Preview / Replay (resume mid-flow) |
| `season_active_match_report_pending` | Match resolved, user has not yet acknowledged the Report | Match Report (forced surface on launch — *"You have an unread match report from Week 7."*) |
| `season_complete_offseason_beat` | Regular season ended, currently on off-season beat N | The corresponding beat (resume at the same beat on relaunch) |
| `season_complete_recruitment_pending` | All non-recruitment beats done; awaiting recruitment phase | Recruitment Phase (or v1 stub) |
| `next_season_ready` | Off-season complete, schedule generated, awaiting "Begin Season N" click | Schedule Reveal / Hub-with-Begin-Season-CTA |

**Transitions (all auto-save on transition):**
- `splash → season_active_pre_match` (after onboarding or Continue Career)
- `season_active_pre_match → season_active_in_match` (Start Match in Match Preview)
- `season_active_in_match → season_active_match_report_pending` (engine resolves match, log persisted)
- `season_active_match_report_pending → season_active_pre_match` (user clicks Back to Hub from Report) — **also advances current week**
- `season_active_pre_match → season_complete_offseason_beat[1]` (final week's report acknowledged AND no more weeks)
- `season_complete_offseason_beat[N] → season_complete_offseason_beat[N+1]` (Continue → on each beat)
- `season_complete_offseason_beat[last_pre_recruitment] → season_complete_recruitment_pending`
- `season_complete_recruitment_pending → next_season_ready` (v1 Draft confirmed; v2 Confirm Signings)
- `next_season_ready → season_active_pre_match` (Begin Season N → click)

**Resume behavior:** every state has an explicit "where am I" surface. Quitting and relaunching mid-anything drops the user back at the right surface, with the right copy ("Continue from Week 7 Match Report" / "Continue Off-season — Awards Ceremony"). The state machine lives in a dedicated module (`career_state.py` or in `franchise.py`) with tests for each transition.

**Why this is in the spec:** the reviewer flagged that without an explicit state machine, save/resume edge cases will leak into every screen as conditional rendering. Centralizing the state and forcing every screen to read from it eliminates that drift.

---

## 13. Cross-cutting Risks

- **Pacing tuning is feel, not spec.** Replay timing values (per-event ms, big-event holds, end-of-match beat) need a screenshot+timing review pass during implementation. Cannot be code-reviewed alone.
- **Tkinter animation has limits.** Design leans on punctuated state changes, not continuous motion. Validate early with a small prototype event in the implementation plan.
- **v1 engine items to verify when plan-writing Milestone 0:**
  - Match-MVP function (may exist in `awards.py`; verify, add if absent).
  - Playoff support in `scheduler.py` (verify; if absent, v1 ships regular-season-by-record champion).
  - The WP analyzer (§2.5.4) and lineup resolver (§2.5.3) are not "gaps to verify" — they are explicit Milestone 0 deliverables.
- **v2 engine items (deferred, captured for v2 planning):**
  - Step-able recruitment phase for the Off-season Recruitment ticker (v2-B).
  - Scout confidence persistence across season transition (v2-A).
  - Possible `awards.py` extension for Defensive POY / All-League awards.
- **Off-season ceremony scope risk.** v1 ships the 7-beat sequence (Champion · Recap · Awards · Development · Retirements · v1 Draft · Schedule Reveal). Records Ratified and HoF Induction are optional v1 add-ons; full 10-beat ceremony is v2.

---

## 14. Implementation Slicing Hint

**Not the implementation plan** — that's the writing-plans skill's job. The slicing rationale is recorded here so the planner doesn't lead with Tkinter screens before engine/state contracts exist. **Order matters.**

### Milestone 0 — Engine & State Contracts (NO UI work)

Land everything in §2.5 + §12.6 that v1 depends on, with tests and golden-log preservation:

1. `Club` model extension (primary color, secondary color, venue, tagline) + `sample_data.py` repopulation + migration.
2. Lineup persistence schema + `LineupResolver` + match builder integration + tests.
3. Win-probability analyzer module + tests (monotonicity, symmetry, determinism).
4. Match-MVP function (verify, add if missing).
5. Career state machine module + transition tests + persistence integration.
6. Verify playoff support; document v1 as regular-season-by-record if not present.

**Definition of done:** tests green, golden logs unchanged (or change-noted per AGENTS.md), no UI yet. This milestone is invisible to the user but unblocks every UI milestone.

### Milestone 1 — Career Vertical Slice (UI starts)

Splash → Onboarding (Take Over only; Build a Club shown as Coming Soon) → Hub → Match Preview (5 actual `CoachPolicy` controls + lineup panel) → in-flow Replay (HUD + buildup beat; minimal hit/catch punctuation; pacing not yet tuned) → Match Report (box score + headlines + records + Turning Points + UPSET tag, all consuming the M0 WP analyzer) → Back to Hub → next week's match.

**Acceptance:** user can play through one full season in the GUI, end with a champion and a Season Recap screen. State machine drives every transition. Save/resume works at any point.

### Milestone 2 — Game-Feel Pass on Match Replay

Full punctuation devices from §7.3, end-of-match moment, MVP card pop, ball trajectory lines, possession marker, pacing tuning. Screenshot+timing review pass. No new screens.

### Milestone 3 — League Surface

Standings + Schedule + Wire as the unified League destination with click-through to past Reports and Profiles.

### Milestone 4 — Player Profile

Full trading-card view (without UncertaintyBar — that's v2). Click-through everywhere a player name appears.

### Milestone 5 — Off-season Ceremony (v1 scope)

Champion · Season Recap · Awards · Development Summary · Retirements & Aging · v1 Draft (rookie pick, no AI competition) · Schedule Reveal · transition. 7 beats. State machine carries beat index across save/resume.

### Milestone 6 — Polish & Friendly Mode Rework

Final polish, accessibility pass, Friendly mode rebuilt on the new component set.

---

### v2 Roadmap (out of this milestone)

These build on top of v1 and require their own engine domain models first:

- **v2-A — Stateful Scouting Model** (§2.5.5). Scout entities, assignments, confidence persistence + carry-forward, narrowing-over-time. Engine first, then Section 8 UI.
- **v2-B — Recruitment Domain Model** (§2.5.6). AI club preferences, public-vs-private info, sign rounds, sniping. Depends on v2-A. Engine first, then full §11 Beat 9 UI.
- **v2-C — Build a Club Path.** Activates the second tile in the Career Path Picker. Depends on v2-A and v2-B (the expansion fantasy is meaningless without scouting/recruiting depth).
- **v2-D — Expanded `CoachPolicy` Tendencies.** Adds Target Ball-Holder, Catch Bias, Rush Proximity, etc., with engine behavior + AI legibility tests + golden-log change-notes.
- **v2-E — Records Ratified, HoF Induction, Rookie Class Preview** beats, completing the 10-beat ceremony.
- **v2-F — Playoffs** (if not in v1).
- **v2-G — UncertaintyBar component + fuzzy Profile mode** (depends on v2-A scouting model).

Each milestone (v1 and v2) ends with a `output/ui-review-<phase>/` capture step before being called done.

---

## 15. Acceptance Criteria

### v1 acceptance (this milestone)

1. A new user can launch the app, pick a curated club, and play through a full season — match by match — without leaving the GUI.
2. Each match feels like a sport: identity bar, scoreboard, hit/catch punctuation, MVP moment, end-of-match beat. Pacing reviewed and tuned via screenshot+timing pass.
3. Match Report shows box score, headlines, records, standings update, Turning Points, and UPSET tag — all consuming the M0 win-probability analyzer (§2.5.4).
4. Standings, schedule, and Wire are reachable as a unified League destination with click-through to past matches and player profiles.
5. The Player Profile is the most-clickable thing in the app, accessible from every player name.
6. Off-season runs end-to-end as a guided ceremony with the v1 beat set (§11). Rookie slot is filled via the v1 Draft beat (user pick, no AI competition).
7. Friendly mode preserves the current "test any matchup" workflow with the new visuals.
8. Career state machine drives every transition. Save/resume works at any state, including mid-flow.
9. The integrity contract holds across every screen — no displayed value lacks an engine source; the renderer never decides anything. Win-probability numbers, where shown, are explicitly retrospective.
10. All existing tests pass. Engine extensions in §2.5 ship with their own tests. Golden logs unchanged unless explicitly authorized with documented change-notes.
11. The app no longer reads as a sandbox or utility. It reads as a manager-sim.

### v2 acceptance (later milestones)

12. Build a Club path produces a viable expansion-tier career with weak starting roster.
13. Scouting Center supports the full hidden-gem loop: assign scout → confidence narrows → reveal → confidence persists across season.
14. Off-season Recruitment phase shows AI clubs signing in real time, with sniping and public-vs-private information asymmetry.
15. Match Replay supports the full punctuation device set including any v2 polish items.
