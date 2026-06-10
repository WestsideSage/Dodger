"""Watchability pass (2026-06-09): replay presentation-truth guards.

Pins the fixes from the broadcast/watchability audit:

* Catch re-entries reach the persisted event stream (``state_diff["player_return"]``)
  on BOTH engines, so the replay's live survivor state can stay truthful.
  Pre-fix evidence: 99% (175/177) of an official match's replay events showed
  a wrong live count — the court saturated to 12 crossed-out players while
  the real games were 6v6.
* Official multi-game structure reaches the replay: per-event ``game_number``
  / ``engine_tick`` metadata, per-game elimination resets in the proof score
  state, and a ``game_segments`` payload from the persisted official score.
* The report "turning point" is the biggest actual swing, not the first hit
  of the match, and carries the index of the same event it describes.
* Moment events are tagged with their game and anchored into the proof
  timeline.
* Outcomes are NOT changed by any of this — pinned for a fixed seed.
"""
from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.official_adapter import OfficialEngineAdapter
from dodgeball_sim.persistence import create_schema, save_club, save_match_result
from dodgeball_sim.rec_adapter import _translate_throw_event
from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.replay_proof import build_replay_proof
from dodgeball_sim.replay_service import (
    _anchor_proof_index,
    _game_segments,
    _turning_point_selection,
    match_replay_payload,
)
from dodgeball_sim.rulesets import RulesetSelection

from .factories import make_match_setup, make_player, make_team


def _six(prefix: str, **kw):
    return [make_player(f"{prefix}{i}", **kw) for i in range(1, 7)]


def _official_fixture(seed: int = 4242):
    team_a = make_team("alpha", _six("a", accuracy=70, catch=68, dodge=62), name="Alpha")
    team_b = make_team("beta", _six("b", accuracy=58, catch=52, dodge=50), name="Beta")
    setup = make_match_setup(team_a, team_b)
    adapter = OfficialEngineAdapter(RulesetSelection("official_foam"))
    raw = adapter.run(setup, seed=seed, match_id="probe_official")
    generic = adapter.run_generic(setup, seed=seed, match_id="probe_official")
    return team_a, team_b, raw, generic


def _snapshots(team_a, team_b):
    return {
        team_a.id: [
            {"id": p.id, "name": p.name, "match_role": "active", "archetype": p.archetype.value}
            for p in team_a.players
        ],
        team_b.id: [
            {"id": p.id, "name": p.name, "match_role": "active", "archetype": p.archetype.value}
            for p in team_b.players
        ],
    }


def _proof_for(team_a, team_b, generic):
    events = [e.to_dict() for e in generic.events]
    name_map = {p.id: p.name for p in (*team_a.players, *team_b.players)}
    return events, build_replay_proof(
        events,
        name_map=name_map,
        roster_snapshots=_snapshots(team_a, team_b),
        home_club_id=team_a.id,
        away_club_id=team_b.id,
    )


# ---------------------------------------------------------------------------
# Translator truth carriers
# ---------------------------------------------------------------------------


def test_official_translator_stamps_player_returns_and_game_metadata():
    team_a, team_b, raw, generic = _official_fixture()
    throws = [e for e in generic.events if e.event_type == "throw"]
    assert throws, "official fixture produced no throw events"

    all_ids = {p.id for p in (*team_a.players, *team_b.players)}
    returns = [e for e in throws if "player_return" in e.state_diff]
    catches = [e for e in throws if e.outcome.get("resolution") == "catch"]
    # The official engine returns a queued teammate on most valid catches —
    # a multi-game foam match reliably produces several.
    assert returns, "no player_return reached the translated stream"
    for event in returns:
        # Returns only happen on catches, and the returned player is real.
        assert event.outcome.get("resolution") == "catch"
        ret = event.state_diff["player_return"]
        assert ret["player_id"] in all_ids
        assert ret["team"] in {team_a.id, team_b.id}
        # The thrower is out on the same catch; the returned player belongs to
        # the CATCHING side, never the thrower's side.
        out = event.state_diff.get("player_out")
        assert out is not None and out["team"] != ret["team"]
    assert len(returns) <= len(catches)

    # Every throw carries the game it belongs to plus the per-game engine tick.
    games_seen = set()
    for event in throws:
        official = event.context.get("official") or {}
        assert isinstance(official.get("game_number"), int)
        assert isinstance(official.get("engine_tick"), int)
        games_seen.add(official["game_number"])
    meta = raw.official_metadata
    assert games_seen == {g["game_number"] for g in meta["games"]}


def test_official_translator_sequence_ids_restart_per_game_returns_keyed_by_game():
    """Sequence ids restart each game ("s1", "s2", ... per game); a return in
    game 3's s4 must never be stamped onto game 1's s4. Regression for the
    first (wrong) global-keyed implementation of this pass."""
    _team_a, _team_b, _raw, generic = _official_fixture()
    throws = [e for e in generic.events if e.event_type == "throw"]
    for event in throws:
        if "player_return" in event.state_diff:
            # If a miss ever carries a return, the join leaked across games.
            assert event.outcome.get("resolution") == "catch"


def test_rec_adapter_preserves_catch_return():
    raw = {
        "type": "catch_return",
        "tick": 7,
        "thrower": "b1",
        "thrower_team": "beta",
        "target": "a4",
        "target_team": "alpha",
        "returning_player_id": "a3",
        "state_diff": {"player_out": {"team": "beta", "player_id": "b1"}},
    }
    event = _translate_throw_event(raw=raw, event_id=1, seed=1, difficulty="pro")
    assert event.state_diff["player_return"] == {"team": "alpha", "player_id": "a3"}
    # The thrower-out diff is untouched.
    assert event.state_diff["player_out"] == {"team": "beta", "player_id": "b1"}


def test_rec_driver_returns_reach_translated_stream():
    catchy = CoachPolicy(
        approach="patient",
        target_focus="spread",
        catch_posture="go_for_catches",
        rush_commit="balanced",
        rush_target="center",
    )
    team_a = make_team("alpha", _six("a", accuracy=65, catch=85, catch_courage=85), name="Alpha", policy=catchy)
    team_b = make_team("beta", _six("b", accuracy=65, catch=85, catch_courage=85), name="Beta", policy=catchy)
    lookup = {p.id: p for p in (*team_a.players, *team_b.players)}
    driver = RecTier1Driver()
    out = driver.run(
        DriverMatchInput(
            match_id="probe_rec",
            team_a_id="alpha",
            team_b_id="beta",
            starters_a=tuple(p.id for p in team_a.players),
            starters_b=tuple(p.id for p in team_b.players),
            player_lookup=lookup,
            policy_a=catchy,
            policy_b=catchy,
            seed=1,
        )
    )
    raw_returns = [e for e in out.events if e.get("type") == "catch_return"]
    assert raw_returns, "seed 1 fixture is expected to produce catch returns"
    translated = [
        _translate_throw_event(raw=r, event_id=i, seed=1, difficulty="pro")
        for i, r in enumerate(raw_returns)
    ]
    for raw_event, event in zip(raw_returns, translated):
        assert event.state_diff["player_return"]["player_id"] == raw_event["returning_player_id"]


# ---------------------------------------------------------------------------
# Proof score-state truth
# ---------------------------------------------------------------------------


def test_proof_score_state_matches_engine_ground_truth_per_event():
    """The replay's live survivor counts equal the engine's active counts at
    every sequence — returns honored, eliminations reset per game. Pre-fix
    this mismatched on 99% of events for this exact fixture/seed."""
    from dodgeball_sim.official_events import OfficialEventKind

    team_a, team_b, raw, generic = _official_fixture()
    events, proof = _proof_for(team_a, team_b, generic)

    # Ground truth straight from the raw official stream (enqueue/return
    # events + per-game resets), snapshotted after each sequence settles.
    ids_a = {p.id for p in team_a.players}
    active = {p.id: True for p in (*team_a.players, *team_b.players)}
    truth: dict[tuple[str | None, str | None], tuple[int, int]] = {}
    pending: tuple[str | None, str | None] | None = None
    current_game = None
    for ev in raw.events:
        if ev.game_id != current_game:
            current_game = ev.game_id
            for pid in active:
                active[pid] = True
            pending = None
        if ev.kind == OfficialEventKind.SEQUENCE and (ev.payload or {}).get("kind") == "sequence_final":
            pending = (ev.game_id, ev.sequence_id)
        if ev.kind == OfficialEventKind.CATCH_QUEUE and ev.player_ids:
            kind = (ev.payload or {}).get("kind")
            if kind == "enqueue":
                active[ev.player_ids[0]] = False
            elif kind == "return_on_catch":
                active[ev.player_ids[0]] = True
        if pending is not None:
            truth[pending] = (
                sum(1 for pid, live in active.items() if live and pid in ids_a),
                sum(1 for pid, live in active.items() if live and pid not in ids_a),
            )

    compared = 0
    for p in proof["proof_events"]:
        seq = (events[p["sequence_index"]].get("state_diff") or {}).get("sequence_id")
        key = (f"g{p['game_number']}" if p["game_number"] is not None else None, seq)
        if seq is None or key not in truth:
            continue
        compared += 1
        assert (p["score_state"]["home_living"], p["score_state"]["away_living"]) == truth[key], (
            f"live-count drift at {key}"
        )
    assert compared > 50, "fixture did not produce enough comparable events"


def test_proof_events_carry_game_metadata_and_return_names():
    team_a, team_b, _raw, generic = _official_fixture()
    _events, proof = _proof_for(team_a, team_b, generic)
    by_game: dict[int, list[dict]] = {}
    for p in proof["proof_events"]:
        assert isinstance(p["game_number"], int)
        by_game.setdefault(p["game_number"], []).append(p)
    assert len(by_game) > 1, "multi-game fixture expected"
    # The first proof event of every game after the first starts from a fresh
    # court: at most one elimination (its own diff) per side.
    for game, plays in sorted(by_game.items())[1:]:
        first = plays[0]
        state = first["score_state"]
        assert state["home_living"] >= 5
        assert state["away_living"] >= 5
    returns = [p for p in proof["proof_events"] if p["returned_player_id"]]
    assert returns
    for p in returns:
        assert p["returned_player_name"]
        assert "RETURN" in p["proof_tags"]
        assert "re-enters" in p["summary"] or "re-enters" in p["detail"]


# ---------------------------------------------------------------------------
# Turning point honesty
# ---------------------------------------------------------------------------


def test_turning_point_is_biggest_swing_not_first_hit():
    def play(idx, *, game, key, home, away):
        return {
            "is_key_play": key,
            "game_number": game,
            "tick": idx,
            "summary": f"play {idx}",
            "score_state": {"home_living": home, "away_living": away},
        }

    proof_events = [
        play(0, game=1, key=True, home=6, away=5),   # first hit (old pick)
        play(1, game=1, key=False, home=6, away=5),
        play(2, game=1, key=True, home=6, away=4),
        # Lead flip: from home up 2 to away up 1 — the real turning point.
        play(3, game=1, key=True, home=3, away=4),
    ]
    text, index = _turning_point_selection(proof_events)
    assert index == 3
    assert text == "play 3"


def test_turning_point_never_scores_across_game_boundary():
    def play(idx, *, game, key, home, away):
        return {
            "is_key_play": key,
            "game_number": game,
            "tick": idx,
            "summary": f"play {idx}",
            "score_state": {"home_living": home, "away_living": away},
        }

    # Game 1 ends 0-6; game 2 starts fresh. The 0-6 -> 6-5 transition is a
    # reset, not a swing — it must not be selected over the real in-game play.
    proof_events = [
        play(0, game=1, key=True, home=0, away=6),
        play(1, game=2, key=True, home=6, away=5),
        play(2, game=2, key=True, home=2, away=3),  # real biggest in-game swing
    ]
    _text, index = _turning_point_selection(proof_events)
    assert index == 2


# ---------------------------------------------------------------------------
# Game segments + moment anchoring (payload level)
# ---------------------------------------------------------------------------


def test_game_segments_map_official_score_to_home_away():
    proof_events = [
        {"game_number": 1, "tick": 1},
        {"game_number": 1, "tick": 2},
        {"game_number": 2, "tick": 3},
    ]
    score = {
        "team_a_id": "home_club",
        "games": [
            {
                "game_number": 1,
                "winner_team_id": "home_club",
                "team_a_points": 1,
                "team_b_points": 0,
                "result_type": "elimination",
                "final_active_a": 4,
                "final_active_b": 0,
            },
            {
                "game_number": 2,
                "winner_team_id": None,
                "team_a_points": 0,
                "team_b_points": 0,
                "result_type": "no_point",
                "final_active_a": 2,
                "final_active_b": 3,
            },
        ],
    }
    segments = _game_segments(json.dumps(score), proof_events, "home_club")
    assert segments is not None and len(segments) == 2
    g1, g2 = segments
    assert (g1["home_points"], g1["away_points"]) == (1, 0)
    assert (g1["first_proof_index"], g1["last_proof_index"]) == (0, 1)
    assert (g1["home_running_points"], g1["away_running_points"]) == (1, 0)
    assert g2["result_type"] == "no_point"
    assert (g2["first_proof_index"], g2["last_proof_index"]) == (2, 2)
    # Flipped mapping when team_a is the AWAY club.
    flipped = _game_segments(json.dumps(score), proof_events, "other_club")
    assert (flipped[0]["home_points"], flipped[0]["away_points"]) == (0, 1)
    # Legacy streams without per-event game metadata: segments still render,
    # jump targets honestly absent.
    legacy = _game_segments(json.dumps(score), [{"game_number": None, "tick": 1}], "home_club")
    assert legacy[0]["first_proof_index"] is None


def test_moment_anchoring_official_and_rec():
    proof_events = [
        {"game_number": 1, "engine_tick": 0, "tick": 1, "resolution": "hit"},
        {"game_number": 1, "engine_tick": 4, "tick": 2, "resolution": "catch"},
        {"game_number": 2, "engine_tick": 0, "tick": 3, "resolution": "hit"},
        {"game_number": 2, "engine_tick": 4, "tick": 4, "resolution": "hit"},
    ]
    # Official: same per-game tick in two games — game_number disambiguates.
    assert _anchor_proof_index({"tick": 4, "game_number": 1}, proof_events) == 1
    assert _anchor_proof_index({"tick": 4, "game_number": 2}, proof_events) == 3
    # End-of-game moment (comeback) past the last tick anchors to the game's last play.
    assert _anchor_proof_index({"tick": 99, "game_number": 1}, proof_events) == 1
    # Rec: no game metadata; event ticks share the coordinate.
    rec_proof = [
        {"game_number": None, "engine_tick": None, "tick": 3, "resolution": "hit"},
        {"game_number": None, "engine_tick": None, "tick": 5, "resolution": "catch"},
    ]
    assert _anchor_proof_index({"tick": 5}, rec_proof) == 1
    assert _anchor_proof_index({"tick": 4}, rec_proof) == 0


def test_official_moments_carry_game_number():
    _team_a, _team_b, raw, _generic = _official_fixture()
    assert raw.moment_events, "fixture expected to produce moments"
    games = {g["game_number"] for g in raw.official_metadata["games"]}
    for moment in raw.moment_events:
        assert moment.game_number in games


# ---------------------------------------------------------------------------
# Full payload + serialization guard
# ---------------------------------------------------------------------------


def _persist_official_match(conn, team_a, team_b, raw, generic):
    club_a = Club(team_a.id, team_a.name, "red/white", "North", 2020, CoachPolicy())
    club_b = Club(team_b.id, team_b.name, "blue/gold", "South", 2020, CoachPolicy())
    save_club(conn, club_a, roster=[])
    save_club(conn, club_b, roster=[])
    conn.execute(
        """
        INSERT INTO matches (id, seed, config_version, winner_team_id, team_a_id, team_b_id,
                             difficulty, setup_json, box_score_json, final_tick)
        VALUES (77, 4242, 'official:official_foam', ?, ?, ?, 'pro', '{}', ?, ?)
        """,
        (
            generic.winner_team_id,
            team_a.id,
            team_b.id,
            json.dumps(generic.box_score),
            generic.final_tick,
        ),
    )
    for index, event in enumerate(generic.events):
        conn.execute(
            "INSERT INTO match_events (match_id, event_index, event_json) VALUES (77, ?, ?)",
            (index, json.dumps(event.to_dict())),
        )
    snapshots = _snapshots(team_a, team_b)
    for club_id, players in snapshots.items():
        conn.execute(
            "INSERT INTO match_roster_snapshots (match_id, club_id, players_json) VALUES ('m77', ?, ?)",
            (club_id, json.dumps(players)),
        )
    meta = raw.official_metadata
    save_match_result(
        conn,
        match_id="m77",
        season_id="season_1",
        week=1,
        home_club_id=team_a.id,
        away_club_id=team_b.id,
        winner_club_id=generic.winner_team_id,
        home_survivors=0,
        away_survivors=0,
        home_roster_hash="h1",
        away_roster_hash="h2",
        config_version="official:official_foam",
        ruleset_version="v1.0",
        seed=4242,
        event_log_hash="event_h",
        final_state_hash="state_h",
        engine_match_id=77,
        scoring_model="foam",
        home_game_points=int(meta["team_a_game_points"]),
        away_game_points=int(meta["team_b_game_points"]),
        home_games_won=int(meta["team_a_games_won"]),
        away_games_won=int(meta["team_b_games_won"]),
        tied_games=int(meta["tied_games"]),
        no_point_games=int(meta["no_point_games"]),
        official_score_json=json.dumps(meta, default=str),
    )


def test_payload_game_segments_turning_point_and_anchors_end_to_end():
    team_a, team_b, raw, generic = _official_fixture()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    _persist_official_match(conn, team_a, team_b, raw, generic)

    payload = match_replay_payload(conn, "m77")
    segments = payload["game_segments"]
    assert segments is not None
    assert len(segments) == len(raw.official_metadata["games"])
    # Running totals end at the recorded final score.
    assert segments[-1]["home_running_points"] == payload["home_game_points"]
    assert segments[-1]["away_running_points"] == payload["away_game_points"]
    # Jump targets cover the proof timeline in order.
    n_proof = len(payload["proof_events"])
    for seg in segments:
        assert seg["first_proof_index"] is not None
        assert 0 <= seg["first_proof_index"] <= seg["last_proof_index"] < n_proof

    # Turning-point text and index describe the same event.
    index = payload["report"]["turning_point_index"]
    assert index is not None
    assert payload["report"]["turning_point"] == payload["proof_events"][index]["summary"]

    # Moments anchor inside their own game's slice of the timeline.
    assert payload["moment_events"]
    for moment in payload["moment_events"]:
        anchor = moment["anchor_index"]
        assert anchor is not None and 0 <= anchor < n_proof
        if moment.get("game_number") is not None:
            assert payload["proof_events"][anchor]["game_number"] == moment["game_number"]

    # Serialization guard: the response model must not strip the new field.
    from dodgeball_sim.server import MatchReplayResponse

    serialized = MatchReplayResponse(**payload).model_dump()
    assert serialized["game_segments"] == segments
    assert serialized["report"]["turning_point_index"] == index


def test_aftermath_match_card_games_sum_to_totals():
    """The aftermath set story must re-add to the headline game points."""
    team_a, team_b, raw, _generic = _official_fixture()
    meta = raw.official_metadata
    games = meta["games"]
    assert games
    home_total = sum(int(g["team_a_points"]) for g in games)
    away_total = sum(int(g["team_b_points"]) for g in games)
    assert home_total == int(meta["team_a_game_points"])
    assert away_total == int(meta["team_b_game_points"])


# ---------------------------------------------------------------------------
# Rec recorded-outcome truth (the box-score return bug)
# ---------------------------------------------------------------------------


def test_rec_box_score_living_matches_driver_final_actives_across_seeds():
    """The recorded survivor totals must equal the engine's actual final
    actives. Pre-fix the box marked every ever-eliminated player as out
    (catch-returns ignored), undercounting survivors on 40/40 probed seeds —
    and franchise.simulate_match derives the recorded WINNER from those
    totals, so a 2-0 elimination win could be recorded as a 0-0 draw."""
    from dodgeball_sim.rec_adapter import RecEngineAdapter

    catchy = CoachPolicy(
        approach="patient",
        target_focus="spread",
        catch_posture="go_for_catches",
        rush_commit="balanced",
        rush_target="center",
    )
    team_a = make_team("alpha", _six("a", accuracy=65, catch=85, catch_courage=85), name="Alpha", policy=catchy)
    team_b = make_team("beta", _six("b", accuracy=65, catch=85, catch_courage=85), name="Beta", policy=catchy)
    setup = make_match_setup(team_a, team_b)
    adapter = RecEngineAdapter()
    saw_return = False
    for seed in range(1, 21):
        output = adapter.run(setup, seed=seed, match_id="probe")
        result = adapter.run_generic(setup, seed=seed, match_id="probe")
        box = result.box_score["teams"]
        assert box["alpha"]["totals"]["living"] == output.final_active_a, f"seed {seed}"
        assert box["beta"]["totals"]["living"] == output.final_active_b, f"seed {seed}"
        # The winner the record derives from survivors agrees with the driver.
        assert result.winner_team_id == output.winner_team_id, f"seed {seed}"
        if any(e.get("type") == "catch_return" for e in output.events):
            saw_return = True
    assert saw_return, "fixture never produced a catch return; test lost its teeth"


def test_narrative_beats_deficit_walk_honors_returns():
    """A returned player offsets an out in the deficit/lead walk."""
    from types import SimpleNamespace

    from dodgeball_sim.replay_proof import derive_narrative_beats

    def event(state_diff):
        return SimpleNamespace(state_diff=state_diff)

    # 6v6 start. Two player-side outs, one return: net -1 → final 5v6 living.
    events = [
        event({"player_out": {"team": "mine", "player_id": "m1"}}),
        event({"player_out": {"team": "mine", "player_id": "m2"}}),
        event({
            "player_out": {"team": "theirs", "player_id": "t1"},
            "player_return": {"team": "mine", "player_id": "m1"},
        }),
    ]
    result = SimpleNamespace(
        box_score={
            "teams": {
                "mine": {"totals": {"living": 5}},
                "theirs": {"totals": {"living": 5}},
            }
        },
        events=events,
    )
    beats = derive_narrative_beats(result, player_club_id="mine")
    # Worst point was after the second out: mine 4 vs theirs 6 → deficit 2.
    # Without return handling the recovered start counts drift and the walk
    # reports a deficit that never happened on court.
    assert beats.largest_deficit == 2


# ---------------------------------------------------------------------------
# Outcome invariance
# ---------------------------------------------------------------------------


def test_watchability_metadata_does_not_change_outcomes():
    """Frozen outcome pin for the fixture seed. Watchability metadata must
    never move these; only intentional engine changes may re-capture them.
    Originally measured 2026-06-09 (gp 8-0 across 9 games, alpha winner);
    RE-CAPTURED 2026-06-10 three times for owner-greenlit engine changes
    (V17 Task 1 catch retune: 11-0/12; V17 Task 2 WT-20 live rules: 8-4/12;
    V19a engine consumers (stamina/tiq/role fit): 13-0/13 — see the V17/V19
    sprint plans)."""
    _team_a, _team_b, raw, generic = _official_fixture(seed=4242)
    meta = raw.official_metadata
    assert generic.winner_team_id == "alpha"
    assert int(meta["team_a_game_points"]) == 13
    assert int(meta["team_b_game_points"]) == 0
    assert len(meta["games"]) == 13
