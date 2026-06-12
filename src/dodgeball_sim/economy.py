"""V22 Phase 2 — the club treasury and season finances.

Owner (2026-06-11): a deliberately LIGHT financial layer (Teamfight Manager
cited): one treasury number, league payouts by finish, annual staff payroll.
USER club only — AI club finances stay abstracted, and the rules copy says
so. Amounts are integer thousands; surfaces render "$340k".

Money flow:
- Creation (V22 Phase 3): the wizard's staff hires commit season-1 payroll
  against the starting budget; what's left opens the treasury.
- Every offseason (`apply_season_finances`, called once per season from
  `initialize_manager_offseason`): league payout for the finish + playoff
  bonus comes in, next season's staff payroll goes out, the net moves the
  treasury, and the full ledger is persisted for the recap beat.
- The treasury MAY go negative (a basement finish is a real squeeze), but
  hiring freezes while it is — pressure, never a bankruptcy death spiral.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Mapping, Optional

from .config import DEFAULT_ECONOMY, EconomyConfig
from .persistence import (
    get_state,
    load_department_heads,
    load_playoff_bracket,
    load_season_outcome,
    set_state,
)

TREASURY_STATE_KEY = "club_treasury_k"
FINANCES_APPLIED_KEY = "finances_applied_for"
SEASON_FINANCES_KEY = "season_finances_json"

# V23: league payouts scale with the tier you played in. The DISTRICT league
# is the 1.0× anchor — the V22 payout/payroll squeeze was tuned at exactly
# this scale for the founding path, and "squeeze, never a spiral" must keep
# holding where new clubs are born (a 0.35× D3 was measured to spiral a
# journeyman-staffed founder to -217k by season 3). Climbing PAYS: Premier
# money is the pull up the pyramid. V25's wage bills are what stop the top
# from un-squeezing (vision doc: "promotion inflates payroll as it raises
# prize money"). Disclosed in the finances ledger every season.
TIER_PAYOUT_MULTIPLIERS: dict[int, float] = {1: 1.8, 2: 1.35, 3: 1.0}


def format_k(amount_k: int) -> str:
    """Render integer thousands the way every surface shows money."""
    sign = "-" if amount_k < 0 else ""
    value = abs(int(amount_k))
    if value >= 1000:
        millions = value / 1000.0
        text = f"{millions:.2f}".rstrip("0").rstrip(".")
        return f"{sign}${text}M"
    return f"{sign}${value}k"


def treasury_k(conn: sqlite3.Connection, config: EconomyConfig = DEFAULT_ECONOMY) -> int:
    """Current treasury. Saves created before V22 lazily seed the takeover
    default — an established program with a season behind it, not a founder's
    war chest."""
    raw = get_state(conn, TREASURY_STATE_KEY)
    if raw is None:
        return int(config.takeover_treasury_k)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(config.takeover_treasury_k)


def set_treasury_k(conn: sqlite3.Connection, amount_k: int) -> None:
    set_state(conn, TREASURY_STATE_KEY, str(int(amount_k)))


def staff_salary_k(
    rating_primary: float,
    rating_secondary: float,
    config: EconomyConfig = DEFAULT_ECONOMY,
) -> int:
    """Quality-priced annual salary for one department head."""
    quality = 0.75 * float(rating_primary) + 0.25 * float(rating_secondary)
    return max(config.salary_floor_k, round(quality) - config.salary_rating_offset_k)


def staff_payroll_k(
    conn: sqlite3.Connection, config: EconomyConfig = DEFAULT_ECONOMY
) -> int:
    """Annual payroll for the user's current six department heads."""
    return sum(
        staff_salary_k(head["rating_primary"], head["rating_secondary"], config)
        for head in load_department_heads(conn)
    )


def season_income_k(
    *,
    rank: int,
    total_clubs: int,
    playoff_result: Optional[str],
    config: EconomyConfig = DEFAULT_ECONOMY,
) -> dict[str, int]:
    """League payout for a finish + ONE playoff bonus for the furthest stage.

    ``playoff_result``: "champion" | "runner_up" | "semifinalist" | None.
    """
    payout = config.base_payout_k + max(0, total_clubs - rank) * config.per_rank_step_k
    bonus = {
        "champion": config.champion_bonus_k,
        "runner_up": config.runner_up_bonus_k,
        "semifinalist": config.semifinalist_bonus_k,
    }.get(playoff_result or "", 0)
    return {"league_payout_k": payout, "playoff_bonus_k": bonus}


def playoff_result_for_club(
    conn: sqlite3.Connection, season_id: str, club_id: str
) -> Optional[str]:
    """The furthest playoff stage the club reached this season, if any."""
    outcome = load_season_outcome(conn, season_id)
    if outcome is not None:
        if outcome.champion_club_id == club_id:
            return "champion"
        if outcome.runner_up_club_id == club_id:
            return "runner_up"
    bracket = load_playoff_bracket(conn, season_id)
    if bracket is not None and club_id in getattr(bracket, "seeds", ()):
        return "semifinalist"
    return None


def _final_rank(
    standings: Iterable[Any], club_id: str
) -> tuple[Optional[int], int]:
    """(rank, total_clubs) using the same composite key the recap table uses."""
    rows = sorted(
        standings,
        key=lambda r: (
            -r.points,
            -getattr(r, "total_game_points_scored", 0),
            -getattr(r, "game_point_differential", 0),
            -r.elimination_differential,
            r.club_id,
        ),
    )
    for index, row in enumerate(rows, start=1):
        if row.club_id == club_id:
            return index, len(rows)
    return None, len(rows)


def apply_season_finances(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    club_id: str,
    standings: Iterable[Any],
    config: EconomyConfig = DEFAULT_ECONOMY,
) -> Optional[dict[str, Any]]:
    """Apply one season's income and payroll to the treasury, once.

    Idempotent per season (the caller, ``initialize_manager_offseason``, is
    itself guarded, but finances guard independently so a partial older save
    can never double-pay). Returns the persisted ledger, or the existing one
    when already applied.
    """
    if get_state(conn, FINANCES_APPLIED_KEY) == season_id:
        return load_season_finances(conn)

    # V23: on pyramid saves you are paid by your DIVISION — rank within its
    # seven clubs, scaled by the tier's payout multiplier.
    from .world import pyramid_world_active

    standings = list(standings)
    tier_multiplier = 1.0
    division_name: Optional[str] = None
    tier: Optional[int] = None
    if pyramid_world_active(conn):
        from .persistence import load_division_map

        division_map = load_division_map(conn, season_id)
        seat = division_map.get(club_id)
        if seat is not None:
            standings = [
                row
                for row in standings
                if division_map.get(row.club_id)
                and division_map[row.club_id].division_id == seat.division_id
            ]
            tier_multiplier = TIER_PAYOUT_MULTIPLIERS.get(seat.tier, 1.0)
            division_name = seat.division_name
            tier = seat.tier

    rank, total_clubs = _final_rank(standings, club_id)
    if rank is None:
        return None
    playoff_result = playoff_result_for_club(conn, season_id, club_id)
    income = season_income_k(
        rank=rank,
        total_clubs=total_clubs,
        playoff_result=playoff_result,
        config=config,
    )
    league_payout_k = round(income["league_payout_k"] * tier_multiplier)
    playoff_bonus_k = round(income["playoff_bonus_k"] * tier_multiplier)
    payroll = staff_payroll_k(conn, config)
    opening = treasury_k(conn, config)
    net = league_payout_k + playoff_bonus_k - payroll
    closing = opening + net

    rules_line = (
        "Club finances cover the user program only — league payouts in, staff "
        "payroll out. AI club budgets stay abstracted."
    )
    if division_name is not None:
        rules_line = (
            f"League payouts scale with tier: the {division_name} pays "
            f"{tier_multiplier:.2f}× the District League base. " + rules_line
        )

    ledger: dict[str, Any] = {
        "season_id": season_id,
        "rank": rank,
        "total_clubs": total_clubs,
        "playoff_result": playoff_result,
        "league_payout_k": league_payout_k,
        "playoff_bonus_k": playoff_bonus_k,
        "staff_payroll_k": payroll,
        "net_k": net,
        "opening_treasury_k": opening,
        "closing_treasury_k": closing,
        # V23: which rung of the pyramid paid this (None on legacy saves).
        "division_name": division_name,
        "tier": tier,
        "tier_multiplier": tier_multiplier,
        # Honest scope line, rendered verbatim by the finances block.
        "rules": rules_line,
    }
    set_treasury_k(conn, closing)
    set_state(conn, SEASON_FINANCES_KEY, json.dumps(ledger))
    set_state(conn, FINANCES_APPLIED_KEY, season_id)
    return ledger


def load_season_finances(conn: sqlite3.Connection) -> Optional[dict[str, Any]]:
    raw = get_state(conn, SEASON_FINANCES_KEY)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, Mapping) else None


def hiring_frozen(conn: sqlite3.Connection, config: EconomyConfig = DEFAULT_ECONOMY) -> bool:
    """Hiring freezes while the treasury is negative (the no-spiral rule)."""
    return treasury_k(conn, config) < 0


__all__ = [
    "FINANCES_APPLIED_KEY",
    "SEASON_FINANCES_KEY",
    "TREASURY_STATE_KEY",
    "apply_season_finances",
    "format_k",
    "hiring_frozen",
    "load_season_finances",
    "playoff_result_for_club",
    "season_income_k",
    "set_treasury_k",
    "staff_payroll_k",
    "staff_salary_k",
    "treasury_k",
]
