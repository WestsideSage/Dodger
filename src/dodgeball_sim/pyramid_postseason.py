"""V23 Phase 3 — pyramid postseason orchestration.

Once every division's regular season is complete, the world's postseason
runs in strict stages:

  1. **Division titles** — every division plays a top-4 single-elim title
     bracket. The USER'S division rides the legacy machinery untouched
     (``_advance_playoffs_if_needed``: legacy ``_p_r1_m1`` ids, persisted
     bracket, season outcome) so every existing surface keeps reading the
     user's title run; the three AI divisions run their brackets here under
     ``_p_div_{division}_...`` ids.
  2. **Promotion playoffs** (Challenger + District) — the four best
     non-champion clubs by regular-season rank fight for the second
     promotion slot.
  3. **WORLDS** — Premier champion + runner-up vs Circuit champion +
     runner-up, semis cross-paired, every season from Season 1.
  4. **Completion** — the postseason ledger (champions, movement, Worlds)
     and the worlds-history line are persisted.

The player plays every match they are in: stage matches are scheduled
matches, so the weekly loop surfaces a user fixture interactively and this
module only auto-sims AI-vs-AI fixtures. Everything derives from
``match_records`` (derivation from truth — re-runs can never double-count),
and ties resolve through the same ``playoff_resolution`` path the legacy
bracket uses.

Spec: docs/specs/2026-06-12-v23-the-world-spec.md.
"""
from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from .game_loop import recompute_regular_season_standings, simulate_scheduled_match
from .league import Club, DivisionMembership
from .persistence import (
    get_state,
    load_all_rosters,
    load_completed_match_ids,
    load_division_map,
    load_season,
    load_season_outcome,
    load_standings,
    save_scheduled_matches,
    set_state,
)
from .playoffs import is_playoff_match_id
from .scheduler import ScheduledMatch
from .season import Season, StandingsRow
from .view_models import normalize_root_seed
from .world import CHALLENGER, CIRCUIT, DISTRICT, PREMIER, pyramid_world_active

WORLDS_HISTORY_KEY = "worlds_history_json"

# Stage scheduling offsets past the last regular-season week. AI division
# title brackets run the same two weeks as the user's (a parallel postseason),
# then the promotion playoffs, then Worlds caps the season.
_TITLE_SEMI_OFFSET = 1
_TITLE_FINAL_OFFSET = 2
_PROMO_SEMI_OFFSET = 3
_PROMO_FINAL_OFFSET = 4
_WORLDS_SEMI_OFFSET = 5
_WORLDS_FINAL_OFFSET = 6

_PROMO_DIVISIONS = (CHALLENGER.division_id, DISTRICT.division_id)
_RELEGATION_DIVISIONS = (PREMIER.division_id, CHALLENGER.division_id)


def postseason_ledger_key(season_id: str) -> str:
    return f"pyramid_postseason_{season_id}"


def load_postseason_ledger(
    conn: sqlite3.Connection, season_id: str
) -> dict[str, Any] | None:
    raw = get_state(conn, postseason_ledger_key(season_id))
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def load_worlds_history(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    raw = get_state(conn, WORLDS_HISTORY_KEY)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def pyramid_postseason_complete(conn: sqlite3.Connection, season_id: str) -> bool:
    ledger = load_postseason_ledger(conn, season_id)
    return bool(ledger and ledger.get("complete"))


def user_division_standings_filter(
    conn: sqlite3.Connection,
    season_id: str,
    standings: list[StandingsRow],
    player_club_id: str,
) -> list[StandingsRow]:
    """Restrict title-bracket seeding to the user's division on pyramid saves.

    Identity on legacy saves. Without this the legacy bracket builder seeds a
    'top 4' from all 28 clubs of the world.
    """
    if not pyramid_world_active(conn):
        return standings
    division_map = load_division_map(conn, season_id)
    seat = division_map.get(player_club_id)
    if seat is None:
        return standings
    return [
        row
        for row in standings
        if division_map.get(row.club_id)
        and division_map[row.club_id].division_id == seat.division_id
    ]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _regular_weeks(season: Season) -> int:
    return max(
        (
            match.week
            for match in season.scheduled_matches
            if not is_playoff_match_id(season.season_id, match.match_id)
        ),
        default=0,
    )


def _regular_season_complete(conn: sqlite3.Connection, season: Season) -> bool:
    completed = load_completed_match_ids(conn, season.season_id)
    return all(
        match.match_id in completed
        for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    )


def division_rank_order(
    standings: Sequence[StandingsRow],
    division_map: Mapping[str, DivisionMembership],
    division_id: str,
) -> list[str]:
    """Final regular-season order for one division (official-aware composite).

    Mirrors the recap/economy ranking key. New V23 rules (promotion playoff
    field, relegation) rank on this; the legacy title bracket keeps its
    pinned ``top_four_seeds`` ordering for the user's division — a known,
    disclosed wrinkle for the balance re-derivation pass.
    """
    rows = [
        row
        for row in standings
        if division_map.get(row.club_id)
        and division_map[row.club_id].division_id == division_id
    ]
    rows.sort(
        key=lambda r: (
            -r.points,
            -getattr(r, "total_game_points_scored", 0),
            -getattr(r, "game_point_differential", 0),
            -r.elimination_differential,
            r.club_id,
        )
    )
    return [row.club_id for row in rows]


def _sim_ai_matches(
    conn: sqlite3.Connection,
    matches: list[ScheduledMatch],
    clubs: Mapping[str, Club],
    player_club_id: str,
    season: Season,
) -> None:
    if not matches:
        return
    from .offseason_ceremony import ensure_ai_rosters_playable

    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season.season_id, player_club_id):
        rosters = load_all_rosters(conn)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"
    for match in matches:
        simulate_scheduled_match(
            conn,
            scheduled=match,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
    recompute_regular_season_standings(conn, season)
    conn.commit()


def _resolve_winners(
    conn: sqlite3.Connection,
    seeds: Sequence[str],
    match_ids: tuple[str, ...],
    participants: Mapping[str, tuple[str, str]],
) -> dict[str, str]:
    """Resolved winners for completed matches (ties decided + persisted)."""
    from .match_orchestration import resolve_playoff_winners

    return resolve_playoff_winners(
        conn,
        bracket=SimpleNamespace(seeds=tuple(seeds)),
        match_ids=match_ids,
        participants_by_match_id=dict(participants),
    )


class _Bracket:
    """A four-club single-elim stage driven entirely from persisted state.

    ``seeds`` are the four participants in seed order (1-4); semis pair
    1v4 / 2v3 with the better seed at home. Each ``advance`` call performs at
    most one batch of work and reports whether anything moved; ``champion``
    and ``runner_up`` are only non-None once the final is resolved.
    """

    def __init__(
        self,
        season: Season,
        *,
        sf1_id: str,
        sf2_id: str,
        final_id: str,
        seeds: Sequence[str],
        semi_week: int,
        final_week: int,
    ) -> None:
        self.season = season
        self.sf1_id = sf1_id
        self.sf2_id = sf2_id
        self.final_id = final_id
        self.seeds = list(seeds)
        self.semi_week = semi_week
        self.final_week = final_week

    def advance(
        self,
        conn: sqlite3.Connection,
        clubs: Mapping[str, Club],
        player_club_id: str,
    ) -> tuple[bool, str | None, str | None]:
        """Returns (progressed, champion_club_id, runner_up_club_id)."""
        scheduled = {m.match_id: m for m in self.season.scheduled_matches}
        completed = load_completed_match_ids(conn, self.season.season_id)

        if self.sf1_id not in scheduled:
            semis = [
                ScheduledMatch(
                    match_id=self.sf1_id,
                    season_id=self.season.season_id,
                    week=self.semi_week,
                    home_club_id=self.seeds[0],
                    away_club_id=self.seeds[3],
                ),
                ScheduledMatch(
                    match_id=self.sf2_id,
                    season_id=self.season.season_id,
                    week=self.semi_week,
                    home_club_id=self.seeds[1],
                    away_club_id=self.seeds[2],
                ),
            ]
            save_scheduled_matches(conn, semis)
            conn.commit()
            return True, None, None

        semi_matches = [scheduled[self.sf1_id], scheduled[self.sf2_id]]
        pending = [m for m in semi_matches if m.match_id not in completed]
        ai_pending = [
            m for m in pending
            if player_club_id not in (m.home_club_id, m.away_club_id)
        ]
        if ai_pending:
            _sim_ai_matches(conn, ai_pending, clubs, player_club_id, self.season)
            return True, None, None
        if pending:
            return False, None, None  # blocked on the player's own match

        winners = _resolve_winners(
            conn,
            self.seeds,
            (self.sf1_id, self.sf2_id),
            {m.match_id: (m.home_club_id, m.away_club_id) for m in semi_matches},
        )
        seed_rank = {club_id: index for index, club_id in enumerate(self.seeds)}
        finalists = sorted(
            (winners[self.sf1_id], winners[self.sf2_id]),
            key=lambda club_id: seed_rank.get(club_id, 99),
        )

        if self.final_id not in scheduled:
            final = ScheduledMatch(
                match_id=self.final_id,
                season_id=self.season.season_id,
                week=self.final_week,
                home_club_id=finalists[0],
                away_club_id=finalists[1],
            )
            save_scheduled_matches(conn, [final])
            conn.commit()
            return True, None, None

        final = scheduled[self.final_id]
        if self.final_id not in completed:
            if player_club_id in (final.home_club_id, final.away_club_id):
                return False, None, None
            _sim_ai_matches(conn, [final], clubs, player_club_id, self.season)
            return True, None, None

        final_winners = _resolve_winners(
            conn,
            self.seeds,
            (self.final_id,),
            {self.final_id: (final.home_club_id, final.away_club_id)},
        )
        champion = final_winners[self.final_id]
        runner_up = (
            final.away_club_id if champion == final.home_club_id else final.home_club_id
        )
        return False, champion, runner_up


def _user_division_title_result(
    conn: sqlite3.Connection, season: Season
) -> tuple[str | None, str | None]:
    """Champion + runner-up of the user's division (the legacy bracket)."""
    outcome = load_season_outcome(conn, season.season_id)
    if outcome is None:
        return None, None
    return outcome.champion_club_id, outcome.runner_up_club_id


def _ai_title_bracket(
    season: Season,
    division_id: str,
    standings: Sequence[StandingsRow],
    division_map: Mapping[str, DivisionMembership],
) -> _Bracket:
    regular_weeks = _regular_weeks(season)
    seeds = division_rank_order(standings, division_map, division_id)[:4]
    prefix = f"{season.season_id}_p_div_{division_id}"
    return _Bracket(
        season,
        sf1_id=f"{prefix}_r1_m1",
        sf2_id=f"{prefix}_r1_m2",
        final_id=f"{prefix}_final",
        seeds=seeds,
        semi_week=regular_weeks + _TITLE_SEMI_OFFSET,
        final_week=regular_weeks + _TITLE_FINAL_OFFSET,
    )


def _promo_bracket(
    season: Season,
    division_id: str,
    champion: str,
    standings: Sequence[StandingsRow],
    division_map: Mapping[str, DivisionMembership],
) -> _Bracket:
    regular_weeks = _regular_weeks(season)
    field = [
        club_id
        for club_id in division_rank_order(standings, division_map, division_id)
        if club_id != champion
    ][:4]
    prefix = f"{season.season_id}_p_promo_{division_id}"
    return _Bracket(
        season,
        sf1_id=f"{prefix}_sf1",
        sf2_id=f"{prefix}_sf2",
        final_id=f"{prefix}_final",
        seeds=field,
        semi_week=regular_weeks + _PROMO_SEMI_OFFSET,
        final_week=regular_weeks + _PROMO_FINAL_OFFSET,
    )


def _worlds_bracket(
    season: Season,
    premier_champion: str,
    premier_runner_up: str,
    circuit_champion: str,
    circuit_runner_up: str,
) -> _Bracket:
    regular_weeks = _regular_weeks(season)
    prefix = f"{season.season_id}_p_worlds"
    bracket = _Bracket(
        season,
        sf1_id=f"{prefix}_sf1",
        sf2_id=f"{prefix}_sf2",
        final_id=f"{prefix}_final",
        # Seed order for tie resolution: champions over runners-up.
        seeds=[premier_champion, circuit_champion, premier_runner_up, circuit_runner_up],
        semi_week=regular_weeks + _WORLDS_SEMI_OFFSET,
        final_week=regular_weeks + _WORLDS_FINAL_OFFSET,
    )
    return bracket


def advance_pyramid_postseason(
    conn: sqlite3.Connection,
    season: Season,
    clubs: Mapping[str, Club],
    player_club_id: str,
) -> Season:
    """Advance the world's postseason as far as it can go without the player.

    No-op on legacy saves, before the regular season completes, and once the
    postseason ledger is written. Returns the (possibly re-loaded) season.
    """
    if not pyramid_world_active(conn):
        return season
    if pyramid_postseason_complete(conn, season.season_id):
        return season
    if not _regular_season_complete(conn, season):
        return season
    division_map = load_division_map(conn, season.season_id)
    user_seat = division_map.get(player_club_id)
    if not division_map or user_seat is None:
        return season

    while True:
        season = load_season(conn, season.season_id)
        standings = load_standings(conn, season.season_id)
        progressed = False

        champions: dict[str, str | None] = {}
        runners_up: dict[str, str | None] = {}

        # Stage 1 — division titles. The user's division belongs to the
        # legacy flow (already advanced before this hook runs).
        user_champ, user_ru = _user_division_title_result(conn, season)
        champions[user_seat.division_id] = user_champ
        runners_up[user_seat.division_id] = user_ru
        for division in (PREMIER, CHALLENGER, DISTRICT, CIRCUIT):
            if division.division_id == user_seat.division_id:
                continue
            bracket = _ai_title_bracket(season, division.division_id, standings, division_map)
            moved, champion, runner_up = bracket.advance(conn, clubs, player_club_id)
            champions[division.division_id] = champion
            runners_up[division.division_id] = runner_up
            progressed = progressed or moved
        if progressed:
            continue

        # Stage 2 — promotion playoffs, per division, as soon as that
        # division's champion is known.
        promo_winners: dict[str, str | None] = {}
        promo_fields: dict[str, list[str]] = {}
        for division_id in _PROMO_DIVISIONS:
            champion = champions.get(division_id)
            if champion is None:
                promo_winners[division_id] = None
                continue
            bracket = _promo_bracket(season, division_id, champion, standings, division_map)
            promo_fields[division_id] = list(bracket.seeds)
            moved, winner, _ = bracket.advance(conn, clubs, player_club_id)
            promo_winners[division_id] = winner
            progressed = progressed or moved
        if progressed:
            continue

        # Stage 3 — WORLDS, once both feeder finals are decided.
        premier_champ = champions.get(PREMIER.division_id)
        premier_ru = runners_up.get(PREMIER.division_id)
        circuit_champ = champions.get(CIRCUIT.division_id)
        circuit_ru = runners_up.get(CIRCUIT.division_id)
        worlds_champion: str | None = None
        worlds_runner_up: str | None = None
        if all((premier_champ, premier_ru, circuit_champ, circuit_ru)):
            worlds = _worlds_bracket(
                season, premier_champ, premier_ru, circuit_champ, circuit_ru
            )
            moved, worlds_champion, worlds_runner_up = worlds.advance(
                conn, clubs, player_club_id
            )
            progressed = progressed or moved
        if progressed:
            continue

        # Stage 4 — completion. Champions for every division, both promotion
        # playoffs, and Worlds must all be decided; otherwise we are blocked
        # on a user match and the weekly loop takes over.
        if (
            worlds_champion
            and all(champions.get(d.division_id) for d in (PREMIER, CHALLENGER, DISTRICT, CIRCUIT))
            and all(promo_winners.get(d) for d in _PROMO_DIVISIONS)
        ):
            _write_postseason_ledger(
                conn,
                season=season,
                clubs=clubs,
                standings=standings,
                division_map=division_map,
                champions={k: v for k, v in champions.items() if v},
                runners_up={k: v for k, v in runners_up.items() if v},
                promo_winners={k: v for k, v in promo_winners.items() if v},
                promo_fields=promo_fields,
                worlds_champion=worlds_champion,
                worlds_runner_up=worlds_runner_up,
            )
        return load_season(conn, season.season_id)


def _write_postseason_ledger(
    conn: sqlite3.Connection,
    *,
    season: Season,
    clubs: Mapping[str, Club],
    standings: Sequence[StandingsRow],
    division_map: Mapping[str, DivisionMembership],
    champions: Mapping[str, str],
    runners_up: Mapping[str, str],
    promo_winners: Mapping[str, str],
    promo_fields: Mapping[str, list[str]],
    worlds_champion: str,
    worlds_runner_up: str | None,
) -> None:
    """Persist the season's movement + Worlds ledger (idempotent)."""
    if pyramid_postseason_complete(conn, season.season_id):
        return

    def _name(club_id: str | None) -> str:
        club = clubs.get(club_id or "")
        return club.name if club else str(club_id or "")

    relegated: dict[str, list[str]] = {}
    for division_id in _RELEGATION_DIVISIONS:
        order = division_rank_order(standings, division_map, division_id)
        relegated[division_id] = order[-2:] if len(order) >= 2 else []

    promoted = {
        division_id: [champions[division_id], promo_winners[division_id]]
        for division_id in _PROMO_DIVISIONS
        if division_id in champions and division_id in promo_winners
    }

    ledger: dict[str, Any] = {
        "season_id": season.season_id,
        "complete": True,
        "champions": dict(champions),
        "runners_up": dict(runners_up),
        "champion_names": {k: _name(v) for k, v in champions.items()},
        "promotion_playoff": {
            division_id: {
                "participants": promo_fields.get(division_id, []),
                "winner": promo_winners.get(division_id),
                "winner_name": _name(promo_winners.get(division_id)),
            }
            for division_id in _PROMO_DIVISIONS
        },
        "promoted": promoted,
        "relegated": relegated,
        "worlds": {
            "champion_club_id": worlds_champion,
            "champion_name": _name(worlds_champion),
            "runner_up_club_id": worlds_runner_up,
            "runner_up_name": _name(worlds_runner_up),
            "final_match_id": f"{season.season_id}_p_worlds_final",
        },
    }
    set_state(conn, postseason_ledger_key(season.season_id), json.dumps(ledger))

    history = load_worlds_history(conn)
    if not any(entry.get("season_id") == season.season_id for entry in history):
        history.append(
            {
                "season_id": season.season_id,
                "champion_club_id": worlds_champion,
                "champion_name": _name(worlds_champion),
                "runner_up_club_id": worlds_runner_up,
                "runner_up_name": _name(worlds_runner_up),
                "final_match_id": f"{season.season_id}_p_worlds_final",
            }
        )
        set_state(conn, WORLDS_HISTORY_KEY, json.dumps(history))
    conn.commit()


def next_season_assignment(
    conn: sqlite3.Connection, prior_season_id: str
) -> dict[str, list[str]] | None:
    """The next season's division → clubs map, with movement applied.

    Champion + promotion-playoff winner go up from D3 and D2; the bottom two
    of D1 and D2 come down; the Circuit is closed. Returns ``None`` on legacy
    saves. If the prior postseason ledger is missing (it shouldn't be by the
    time the next season begins), the world carries over unchanged rather
    than inventing movement.
    """
    from .persistence import load_division_memberships

    memberships = load_division_memberships(conn, prior_season_id)
    if not memberships:
        return None
    current: dict[str, list[str]] = {}
    for membership in memberships:
        current.setdefault(membership.division_id, []).append(membership.club_id)

    ledger = load_postseason_ledger(conn, prior_season_id)
    if not (ledger and ledger.get("complete")):
        return {division_id: sorted(club_ids) for division_id, club_ids in current.items()}

    promoted: Mapping[str, list[str]] = ledger.get("promoted", {})
    relegated: Mapping[str, list[str]] = ledger.get("relegated", {})
    up_from_challenger = list(promoted.get(CHALLENGER.division_id, []))
    up_from_district = list(promoted.get(DISTRICT.division_id, []))
    down_from_premier = list(relegated.get(PREMIER.division_id, []))
    down_from_challenger = list(relegated.get(CHALLENGER.division_id, []))

    def _moved(division_id: str, leaving: list[str], arriving: list[str]) -> list[str]:
        kept = [c for c in current.get(division_id, []) if c not in set(leaving)]
        return sorted(kept + arriving)

    assignment = {
        PREMIER.division_id: _moved(
            PREMIER.division_id, down_from_premier, up_from_challenger
        ),
        CHALLENGER.division_id: _moved(
            CHALLENGER.division_id,
            up_from_challenger + down_from_challenger,
            down_from_premier + up_from_district,
        ),
        DISTRICT.division_id: _moved(
            DISTRICT.division_id, up_from_district, down_from_challenger
        ),
        CIRCUIT.division_id: sorted(current.get(CIRCUIT.division_id, [])),
    }
    return assignment


__all__ = [
    "WORLDS_HISTORY_KEY",
    "advance_pyramid_postseason",
    "division_rank_order",
    "load_postseason_ledger",
    "load_worlds_history",
    "next_season_assignment",
    "postseason_ledger_key",
    "pyramid_postseason_complete",
    "user_division_standings_filter",
]
