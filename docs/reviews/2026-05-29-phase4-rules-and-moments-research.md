# Phase 4 Rules and Moments Research

## Part A: Foam Set-Win Semantics (Rulebook-Grounded)

**How a Foam Set is Won and Scored:**
Per the USA Dodgeball 2026.1 Rulebook, a Foam/No-Sting game (set) is won strictly through the total elimination of the opposing team. Time-expiry does not award a win or partial points in Foam.

* **Winning a Game:** "To win a game and earn a point, a team must eliminate the entire opposing team." (Section 6.b.ii.2)
* **Mid-Match Time Expiry:** "If a game has not concluded within the time limit [3 minutes], it will enter No Blocking... Balls do not reset." (Section 6.b.ii.3) The game continues untimed until an elimination win occurs.
* **Match End Time Expiry:** "At the end of the 24-minute timer, the game is briefly stopped. It then resumes as a No Blocking game... played for a maximum of 3 minutes. No points are awarded if there is no clear winner within the 3-minute time limit." (Section 6.b.ii.4)
* **Match Standings:** Round Robin matches award 3 points for a match win, 1 for a tie, and 0 for a loss (Section 7.a.i.1).

**Validation of Plan's Assumption:**
The plan's assumption ("foam = set point on full elimination only; time-expiry = 0") is **confirmed**. Foam awards no points on a player-count majority at time expiry; it only awards points on full elimination. 

**`official_scoring.py` Assessment:**
There is **no mismatch**. `foam_game_points` correctly returns `(1, 0)` or `(0, 1)` only when a `winner_team_id` is explicitly passed (representing a full elimination). If the game is unresolved (e.g., the final 3-minute match-end No Blocking timer expires with survivors on both sides), it correctly returns `(0, 0)`.

---

## Part B: Moment-Event Mapping for OfficialDriver

### 1. Current Rec Engine Moment Kinds
The rec driver (`rec_engine.py`) currently emits six moment kinds:

| Moment Kind | Trigger Condition |
| :--- | :--- |
| `DRAMATIC_CATCH` | Emitted in `_resolve_throw` when a player catches a throw, the thrower is eliminated, and a queued teammate successfully re-enters the game. |
| `LATE_GAME_ESCAPE` | Emitted in `_tick` when one team reaches exactly 1 active player while the opposing team has 3 or more active players. |
| `ONE_V_ONE_FINALE` | Emitted in `_tick` when exactly 1 active player remains on each team. |
| `GASSED_COLLAPSE` | Emitted in `_mark_out` when a player is eliminated (moved to queue) and their fatigue state is evaluated as "gassed" (`fatigue_pct` > threshold). |
| `FLOOD_THROW` | Emitted in `_tick` via `flood_tracker` when a team releases 3 or more throws in the exact same tick. |
| `COMEBACK` | Emitted in `_tick` when a team reaches a deficit of >= 2 players (relative to opponent starters), then rebuilds their active count via catches to be >= the opponent's active count minus 3. |

### 2. Mapping onto the Official Match Loop
Assessing how these moments fit into the `run_autonomous_game` / `run_autonomous_match` loop in `official_engine.py`:

* **`DRAMATIC_CATCH` (Natural):** The official engine resolves throws in `resolve_throw` and handles catch queue returns within the sequence ledger. This can be cleanly emitted when a valid catch successfully returns a player.
* **`LATE_GAME_ESCAPE` (Natural):** The official loop tracks `active_a` and `active_b` each tick. Can be evaluated cleanly at the end of each tick or sequence resolution.
* **`ONE_V_ONE_FINALE` (Natural):** Evaluated cleanly via active player counts at the end of a tick.
* **`COMEBACK` (Natural):** Low-water marks and catch-counters can be tracked at the game loop level just as they are in the rec engine.
* **`GASSED_COLLAPSE` (Awkward / Doesn't Apply):** The official engine does not currently model player fatigue. It relies strictly on official state machines (burden, queues). Emitting this would require porting the entire fatigue subsystem into the official engine. ⚠ *verify: do we want fatigue in the official engine?*
* **`FLOOD_THROW` (Awkward):** The official engine currently processes a single throw action per loop iteration via `ActionSelector`, resolving sequences sequentially. It lacks the rec engine's simultaneous `PendingThrow` tracker. Implementing this would require restructuring the official action selector to batch throws. ⚠ *verify: Section 17.a.iii allows multi-throws, but the engine architecture doesn't natively batch them yet.*

### 3. Recommendations for OfficialDriver

**Minimum Set for Tier-1 Presentation:**
To keep the presentation layer populated without polluting the official engine with un-ported systems, `OfficialDriver` should emit:
* `DRAMATIC_CATCH`
* `LATE_GAME_ESCAPE`
* `ONE_V_ONE_FINALE`
* `COMEBACK`

These four rely entirely on domain facts that the official engine already tracks (player status, queue returns, and active counts). `GASSED_COLLAPSE` and `FLOOD_THROW` should be deferred.

**New Official-Only Moments:**
Given the shift to set-based scoring and official rules, new moments should be added to enrich the presentation layer:
* **`GAME_DECIDED` / `SET_WIN`:** Emitted when a game concludes and a game point is officially awarded. Essential for rendering per-set replay banners.
* **`MATCH_COMEBACK`:** Emitted at the match level (rather than the game level) if a team comes back from a multi-game deficit (e.g., down 0-2 and tying or winning).
* **`BURDEN_VIOLATION`:** Emitted when a team forfeits all balls (Foam) or loses players (Cloth) due to the Throw Clock expiring (Section 14). This replaces "stalling" with a high-drama, rules-accurate event.
