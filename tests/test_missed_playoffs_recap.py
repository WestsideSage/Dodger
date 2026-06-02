"""Work item #3 — post-hoc "you missed the playoffs" beat on the recap.

A player who fast-forwards past the regular season (or simply finishes outside
the cut) must be told, at the season-complete -> offseason transition, that
their season ended without a playoff berth. These tests pin the truthfulness
fence on the ``recap`` beat payload (``offseason_presentation.build_beat_payload``
via the ``server._build_beat_payload`` re-export):

* a club below the cut -> ``missed_playoffs`` block with the correct
  finish / cutoff / total;
* a club inside the cut -> NO block;
* "missed the cut" is distinct from "lost in the playoffs": a club that is in
  the persisted bracket seeds (it played the playoffs) never gets the block,
  even if it would rank at/under the cutoff by standings alone;
* ``made`` and ``finish <= cutoff`` always agree (the seeding-key invariant);
* a league no larger than the cut has no race to miss.
"""
from __future__ import annotations

import dataclasses
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState
from dodgeball_sim.offseason_presentation import build_beat_response
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_career_state_cursor,
    load_clubs,
    load_standings,
    save_playoff_bracket,
    save_standings,
    set_state,
)
from dodgeball_sim.playoffs import PLAYOFF_FIELD_SIZE, PlayoffBracket, top_four_seeds
from dodgeball_sim.season import Season, StandingsRow
from dodgeball_sim.server import _build_beat_payload


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()
    return conn


def _row(club_id: str, points: int, *, diff: int = 0) -> StandingsRow:
    # wins/losses are cosmetic for the cut; points + elimination_differential are
    # the seeding key the playoffs actually use.
    return StandingsRow(
        club_id=club_id,
        wins=points // 3,
        losses=0,
        draws=0,
        elimination_differential=diff,
        points=points,
    )


def _six_club_standings() -> list[StandingsRow]:
    # Strictly descending points so the seeding order is unambiguous:
    # c1(18) c2(15) c3(12) c4(9) | c5(6) c6(3). Cut = top 4.
    return [
        _row("c1", 18),
        _row("c2", 15),
        _row("c3", 12),
        _row("c4", 9),
        _row("c5", 6),
        _row("c6", 3),
    ]


def _season(season_id: str = "S1") -> Season:
    return Season(
        season_id=season_id,
        year=2026,
        league_id="L1",
        config_version="official:foam",
        ruleset_version="v1",
        scheduled_matches=(),
    )


def _recap(conn, standings, player_club_id, season=None) -> dict:
    return _build_beat_payload(
        "recap",
        awards=[],
        clubs={},
        rosters={},
        standings=standings,
        ret_rows=[],
        season=season,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        player_club_id=player_club_id,
        conn=conn,
    )


def test_recap_surfaces_missed_playoffs_with_correct_numbers():
    """Club finishing below the cut -> truthful missed-playoffs block."""
    conn = _conn()
    standings = _six_club_standings()
    # c5 is 5th of 6 — outside the top-4 cut.
    result = _recap(conn, standings, "c5")

    assert "missed_playoffs" in result
    block = result["missed_playoffs"]
    assert block == {"finish": 5, "cutoff": PLAYOFF_FIELD_SIZE, "total": 6}
    # The finish position the banner shows must be the player's row in the table.
    player_rank = next(r["rank"] for r in result["standings"] if r["is_player_club"])
    assert player_rank == block["finish"]


def test_recap_last_place_reports_full_field_finish():
    conn = _conn()
    standings = _six_club_standings()
    result = _recap(conn, standings, "c6")  # dead last
    assert result["missed_playoffs"] == {"finish": 6, "cutoff": PLAYOFF_FIELD_SIZE, "total": 6}


def test_recap_omits_block_when_club_made_the_cut():
    """Club inside the top-4 -> no missed-playoffs block at all."""
    conn = _conn()
    standings = _six_club_standings()
    for made_club in ("c1", "c2", "c3", "c4"):
        result = _recap(conn, standings, made_club)
        assert "missed_playoffs" not in result, made_club


def test_made_playoffs_but_lost_in_bracket_shows_no_missed_block():
    """A club that PLAYED the playoffs (in bracket.seeds) and lost is not 'missed'.

    Membership comes from the persisted bracket — the literal set of clubs that
    competed — so "missed the cut" can never be confused with "lost a playoff
    game". We seed the bracket with the bottom four clubs to prove the bracket
    overrides a standings-only heuristic.
    """
    conn = _conn()
    season = _season()
    standings = _six_club_standings()
    # Deliberately seed clubs c3,c4,c5,c6 (NOT the standings top four) to prove
    # the persisted bracket is authoritative for "who played".
    bracket = PlayoffBracket(
        season_id=season.season_id,
        format="top4_single_elimination",
        seeds=("c3", "c4", "c5", "c6"),
        rounds=(),
        status="final_scheduled",
    )
    save_playoff_bracket(conn, bracket)
    conn.commit()

    # c5 lost in the bracket but it PLAYED — no missed banner.
    assert "missed_playoffs" not in _recap(conn, standings, "c5", season=season)
    # c1 finished 1st by points but was NOT in the seeded bracket -> missed.
    missed = _recap(conn, standings, "c1", season=season).get("missed_playoffs")
    assert missed is not None
    assert missed["finish"] == 1 and missed["cutoff"] == PLAYOFF_FIELD_SIZE


def test_finish_and_membership_agree_on_official_tiebreak():
    """``made`` ⇔ ``finish <= cutoff`` even when display order would diverge.

    For official seasons ``load_standings`` breaks ties on game points, while the
    playoff seeding (and this block's ``finish``) breaks ties on elimination
    differential. Two clubs tied on points where the 4th/5th boundary is decided
    by elimination differential must NOT produce a self-contradicting banner
    (e.g. "finished 4th, top 4 qualify, you missed").
    """
    conn = _conn()
    # c4a and c4b are tied on points (9). Elimination differential is the playoff
    # tiebreak: c4a (+5) seeds ahead of c4b (-5). So c4a is 4th (in), c4b is 5th
    # (out). top_four_seeds must agree.
    standings = [
        _row("c1", 18, diff=10),
        _row("c2", 15, diff=8),
        _row("c3", 12, diff=6),
        _row("c4a", 9, diff=5),
        _row("c4b", 9, diff=-5),
        _row("c6", 3, diff=-20),
    ]
    field = set(top_four_seeds(standings))

    for row in standings:
        result = _recap(conn, standings, row.club_id)
        made = row.club_id in field
        block = result.get("missed_playoffs")
        if made:
            assert block is None, f"{row.club_id} made the cut but got a missed block"
        else:
            assert block is not None, f"{row.club_id} missed the cut but got no block"
            # The invariant: finish strictly beyond the cutoff on every miss.
            assert block["finish"] > block["cutoff"], (row.club_id, block)

    # Concretely: the elim-diff loser is 5th (out), the winner is 4th (in).
    assert "c4b" not in field
    assert _recap(conn, standings, "c4b")["missed_playoffs"]["finish"] == 5
    assert "c4a" in field
    assert "missed_playoffs" not in _recap(conn, standings, "c4a")


def test_recap_table_reseeds_by_playoff_key_not_handed_order():
    """The recap table ranks by the playoff-seeding key, not the order it is handed.

    For official seasons load_standings can order a points tie on game points while
    the playoff seeding (and the missed-playoffs finish) order it on elimination
    differential. If the recap table kept the handed (load_standings) order it could
    show the player INSIDE the top-cut line while the banner says they missed — one
    fact, two ways, on one screen (ADR 0002). Here c4b (-5 elim) is handed 4th, ahead
    of c4a (+5), but it must seed 5th so the displayed rank equals the banner finish.
    """
    conn = _conn()
    standings = [
        _row("c1", 18, diff=10),
        _row("c2", 15, diff=8),
        _row("c3", 12, diff=6),
        _row("c4b", 9, diff=-5),  # handed 4th, but seeds BELOW c4a on elim diff
        _row("c4a", 9, diff=5),
        _row("c6", 3, diff=-20),
    ]
    result = _recap(conn, standings, "c4b")
    block = result["missed_playoffs"]
    player_rank = next(r["rank"] for r in result["standings"] if r["is_player_club"])
    # Re-seeded to 5th (out), matching the banner finish — NOT the 4th it was handed.
    assert block["finish"] == 5
    assert player_rank == 5, "recap table must re-seed by the playoff key, not keep handed order"


def test_recap_no_block_for_small_league():
    """A league no larger than the cut has no playoff race to miss."""
    conn = _conn()
    standings = [_row("c1", 9), _row("c2", 6), _row("c3", 3)]  # 3 clubs, cut = 4
    assert "missed_playoffs" not in _recap(conn, standings, "c3")


def test_recap_no_block_when_player_absent_from_standings():
    conn = _conn()
    standings = _six_club_standings()
    assert "missed_playoffs" not in _recap(conn, standings, "not_a_club")
    assert "missed_playoffs" not in _recap(conn, standings, "")


# ---------------------------------------------------------------------------
# Wired-path test: prove the missed-playoffs facts reach the actual recap BEAT
# assembled by build_beat_response (which derives player_club_id / standings /
# season from DB state), not just the helper in isolation. This is the surface
# the player hits at the season-complete -> offseason transition. The brief
# explicitly warns a prior agent mis-closed this by pointing at the wrong
# surface, so the beat path is exercised end-to-end here.
# ---------------------------------------------------------------------------


def _curated_offseason_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    # Land in the first offseason beat (recap is OFFSEASON_CEREMONY_BEATS[0]).
    cursor = load_career_state_cursor(conn)
    cursor = dataclasses.replace(
        cursor, state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, offseason_beat_index=0
    )
    from dodgeball_sim.persistence import save_career_state_cursor

    save_career_state_cursor(conn, cursor)
    # Restrict the active beats to just the recap so build_beat_response renders
    # it regardless of which conditional beats have content this season.
    set_state(conn, "offseason_active_beats_json", '["recap"]')
    conn.commit()
    return conn, cursor


def _force_standings_rank(conn, season_id: str, player_club_id: str, *, rank: int) -> int:
    """Rewrite season standings so ``player_club_id`` lands at ``rank`` (1-based).

    Assigns strictly descending points by desired finishing order so the seeding
    key is unambiguous. Returns the total club count.
    """
    club_ids = sorted(load_clubs(conn).keys())
    # Put the player's club at the requested 1-based rank, the rest around it.
    others = [c for c in club_ids if c != player_club_id]
    order = others[: rank - 1] + [player_club_id] + others[rank - 1 :]
    rows = [
        StandingsRow(
            club_id=club_id,
            wins=0,
            losses=0,
            draws=0,
            elimination_differential=len(order) - position,
            points=(len(order) - position) * 3,
        )
        for position, club_id in enumerate(order)
    ]
    save_standings(conn, season_id, rows)
    conn.commit()
    return len(order)


def test_build_beat_response_recap_carries_missed_block_for_below_cut_club():
    conn, cursor = _curated_offseason_conn()
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    assert player_club_id, "curated career must assign a player club"

    total = _force_standings_rank(conn, season_id, player_club_id, rank=PLAYOFF_FIELD_SIZE + 1)

    beat = build_beat_response(conn, cursor)
    assert beat["key"] == "recap"
    missed = beat["payload"].get("missed_playoffs")
    assert missed is not None, "below-cut club must surface a missed-playoffs beat"
    assert missed == {"finish": PLAYOFF_FIELD_SIZE + 1, "cutoff": PLAYOFF_FIELD_SIZE, "total": total}
    # The banner finish must equal the player's highlighted row in the same beat.
    player_rank = next(r["rank"] for r in beat["payload"]["standings"] if r["is_player_club"])
    assert player_rank == missed["finish"]


def test_build_beat_response_recap_omits_missed_block_for_in_cut_club():
    conn, cursor = _curated_offseason_conn()
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")

    _force_standings_rank(conn, season_id, player_club_id, rank=1)  # top seed

    beat = build_beat_response(conn, cursor)
    assert beat["key"] == "recap"
    assert "missed_playoffs" not in beat["payload"]
