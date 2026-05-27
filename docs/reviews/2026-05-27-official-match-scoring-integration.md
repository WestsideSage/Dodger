Implementation Plan: Official Match Scoring Integration
Goal

Replace the current “single match = final survivor count” model with:

Match
└── many Games
    ├── game result
    ├── game points
    ├── survivor/active-player state
    └── replay events

Survivors stay visible, but they become state/context, not the scoreboard.

Phase 1 — Create canonical scoring domain types

Add a new module:

src/dodgeball_sim/official_scoring.py

Core types:

@dataclass(frozen=True)
class OfficialGameScore:
    game_number: int
    winner_team_id: str | None
    team_a_points: int
    team_b_points: int
    result_type: Literal[
        "elimination",
        "cloth_active_count",
        "tie",
        "no_point",
        "forfeit",
        "overtime",
        "sudden_death",
    ]
    final_active_a: int
    final_active_b: int
    mode: str
    elapsed_seconds: int

@dataclass(frozen=True)
class OfficialMatchScore:
    team_a_id: str
    team_b_id: str
    team_a_game_points: int
    team_b_game_points: int
    team_a_games_won: int
    team_b_games_won: int
    tied_games: int
    no_point_games: int
    games: tuple[OfficialGameScore, ...]
    winner_team_id: str | None

Rules:

Foam/no-sting game win: full elimination only = 1 point.
Foam/no-sting timed/no-blocking no winner: 0 points.
Cloth game win: 2 points.
Cloth game tie: 1 point each.
Match winner: higher total game/match score after match clock.
Round-robin standings: match win = 3 standings points, match tie = 1, loss = 0.
Tiebreakers: total game points, game point differential, head-to-head, coin flip.
Phase 2 — Stop deriving official winners from survivors

Patch franchise.py and game_loop.py.

Current bad invariant:

# The survivors-on-court tally is the source of truth for who won.

Replace with:

if is_official_ruleset(result.config_version):
    winner_club_id = result.official_match_score.winner_team_id
else:
    winner_club_id = legacy_survivor_fallback(...)

Important: keep legacy behavior for generic/old saves so existing careers do not explode.

Phase 3 — Make the official engine run a full match, not one game

Right now the official engine is effectively producing a single-game outcome that gets stuffed into the generic MatchResult.

Add:

run_autonomous_match(...)

It should:

Initialize a 24-minute round-robin match clock by default.
Loop games until match clock expires.
For each game:
Run 3-minute game loop.
Resolve full elimination / time expiry.
Apply foam/no-sting No Blocking when needed.
Apply cloth active-count scoring when needed.
Produce OfficialMatchScore.
Attach it to replay metadata and persistence payload.

Do not fake a 5-3 match by simming one long survivor contest. That would be sim cosplay. The replay needs to know: “Game 1, Game 2, Game 3…”

Phase 4 — Persistence migration

Add official score fields without deleting survivor fields:

ALTER TABLE match_records ADD COLUMN scoring_model TEXT DEFAULT 'legacy_survivor';
ALTER TABLE match_records ADD COLUMN home_game_points INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN away_game_points INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN home_games_won INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN away_games_won INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN tied_games INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN no_point_games INTEGER DEFAULT 0;
ALTER TABLE match_records ADD COLUMN official_score_json TEXT;

Keep:

home_survivors
away_survivors

But treat them as final replay state, not official score.

Phase 5 — Update standings

Current standings:

elimination_differential = survivors accumulated - survivors conceded

For official rules, add:

game_points_for
game_points_against
game_point_differential
total_game_points_scored

Sort official standings by:

Match points: 3 win / 1 tie / 0 loss.
Total game points scored.
Game point differential.
Head-to-head.
Deterministic coin flip / seeded tiebreak.

Keep survivor differential only as a secondary “legacy/generic” stat or replay flavor.

Phase 6 — Replay and UI changes

Change the main final display from:

Final: 4 survivors - 2 survivors

To:

Final: 7–5
Games: 4–2
Format: Foam · 24-minute match
Survivors at final whistle: 3–1

For cloth:

Final: 10–8
Game points: W=2, T=1, L=0
Final game decided by active players: 4–2

In MatchReplay, add a game timeline:

G1  Team A +1  Full elimination
G2  No point   No Blocking expired
G3  Team B +1  Full elimination
G4  Team A +1  Match-end No Blocking

This will make replays way more believable because the user can see how the match score happened, not just who had bodies left at the end.

Phase 7 — Copy updates

Replace League Wire copy like:

Week 4: X beat Y with 4-2 survivors.

With:

Week 4: X beat Y 6–4 on game points. Final survivor state: 4–2.

The current wire copy explicitly says “beat … with survivors,” so it will keep teaching the player the wrong scoring model until updated.

Phase 8 — Tests

Add tests for:

tests/test_official_scoring.py
tests/test_official_match_series.py
tests/test_official_standings.py
tests/test_official_replay_scoreboard.py

Minimum test cases:

Foam game only awards point on full elimination.
Foam 3-minute unresolved game enters No Blocking.
Foam match-end No Blocking can create no-point game.
Cloth time-expired game awards 2 points to higher active-player count.
Cloth equal active-player count awards 1–1 tie.
Round-robin match win gives 3 standings points.
Standings tiebreak uses total game points before differential.
Survivor advantage does not override official score.
Replay final score displays official game/match score first, survivor count second.
Concrete implementation order
Backend scoring model first — official_scoring.py.
Official match runner second — full match series, not single game.
Persistence migration third — store score JSON + summary columns.
Standings fourth — official tiebreaks.
Replay payload fifth — expose game-by-game score timeline.
Frontend sixth — scoreboard and replay copy.
Golden tests last — lock behavior so future agents do not regress back to “survivors = winner.”