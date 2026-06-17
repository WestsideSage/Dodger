"""V26 The Crowd — fan-gain + fan-income formulas and the offseason rollup.

Pure formulas (the ``contracts.py`` single-formula-home pattern) plus the
season rollup that grows the club fan ledger from real logged events AND ports
prestige growth to the web (it was CLI-only, so V24 Contender/credibility never
grew on web saves). Fans are a user-program feature (user club only); prestige
grows for every club so the world's V24 grades stay honest.
"""
from __future__ import annotations

from typing import Any

from .config import DEFAULT_FANS, FanConfig

_PRESTIGE_GUARD = "prestige_awarded_for"
_FANS_GUARD = "v26_fans_awarded_for"


def club_fans_for_event(event_type: str, config: FanConfig = DEFAULT_FANS) -> int:
    table = {
        "win": config.fans_per_win,
        "promotion": config.fans_promotion,
        "title": config.fans_title,
        "cup": config.fans_cup,
        "worlds_final": config.fans_worlds_final,
        "worlds_win": config.fans_worlds_win,
    }
    return int(table.get(event_type, 0))


def grow_prestige_for_season(conn, season_id: str) -> None:
    """Port of the dormant CLI prestige award: wins+draws + placement, all clubs.

    Idempotent on the shared ``prestige_awarded_for`` guard so the web and CLI
    paths never double-grant.
    """
    from .persistence import (
        get_state, load_club_prestige, load_standings, save_club_prestige, set_state,
    )

    if get_state(conn, _PRESTIGE_GUARD) == season_id:
        return
    for index, row in enumerate(load_standings(conn, season_id)):
        bonus = row.wins + row.draws + (5 if index == 0 else 2 if index < 4 else 0)
        save_club_prestige(conn, row.club_id, load_club_prestige(conn, row.club_id) + bonus)
    set_state(conn, _PRESTIGE_GUARD, season_id)


def award_season_fans(conn, season_id: str, config: FanConfig = DEFAULT_FANS) -> dict[str, Any]:
    """Grow the USER club's fan ledger from this season's logged events, each a
    receipt. Idempotent on ``v26_fans_awarded_for``."""
    from . import fan_ledger
    from .persistence import get_state, load_club_trophies, load_standings, set_state
    from .pyramid_postseason import load_postseason_ledger

    summary = {"events": 0, "fans_gained": 0}
    if get_state(conn, _FANS_GUARD) == season_id:
        return summary
    user = get_state(conn, "player_club_id")
    if not user:
        set_state(conn, _FANS_GUARD, season_id)
        return summary

    def grant(delta: int, event_type: str, receipt: str) -> None:
        if delta <= 0:
            return
        fan_ledger.add_fans(conn, user, delta, season_id, event_type, receipt)
        summary["events"] += 1
        summary["fans_gained"] += delta

    me = next((r for r in load_standings(conn, season_id) if r.club_id == user), None)
    if me is not None and me.wins:
        gain = me.wins * config.fans_per_win
        grant(gain, "win", f"+{gain} from {me.wins} wins this season")

    for trophy in load_club_trophies(conn):
        if trophy.get("club_id") != user or trophy.get("season_id") != season_id:
            continue
        kind = "title" if trophy.get("trophy_type") == "championship" else "cup"
        grant(club_fans_for_event(kind, config), kind,
              f"+{club_fans_for_event(kind, config)} for winning the {kind}")

    ledger = load_postseason_ledger(conn, season_id) or {}
    promoted = ledger.get("promoted") or {}
    if any(user in clubs for clubs in promoted.values()):
        grant(config.fans_promotion, "promotion",
              f"+{config.fans_promotion} after the promotion final")
    worlds = ledger.get("worlds") or {}
    if worlds.get("champion_club_id") == user:
        grant(config.fans_worlds_win, "worlds_win", f"+{config.fans_worlds_win} — World Champions")
    elif worlds.get("runner_up_club_id") == user:
        grant(config.fans_worlds_final, "worlds_final", f"+{config.fans_worlds_final} — a Worlds final run")

    set_state(conn, _FANS_GUARD, season_id)
    return summary


def award_season_fans_and_prestige(conn, season_id: str, config: FanConfig = DEFAULT_FANS) -> dict[str, Any]:
    """The offseason rollup: grow prestige (all clubs) AND the user's fan ledger."""
    grow_prestige_for_season(conn, season_id)
    summary = award_season_fans(conn, season_id, config)
    conn.commit()
    return summary


__all__ = [
    "club_fans_for_event",
    "grow_prestige_for_season",
    "award_season_fans",
    "award_season_fans_and_prestige",
]
