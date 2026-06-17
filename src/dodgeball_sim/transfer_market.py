"""V25 The Market — offseason Transfer Period orchestration.

Retention is recruiting's mirror: the V24 motivation grades
(``motivations.club_fit``) are applied to a rostered player vs his OWN club to
decide whether he re-signs. Because a player keeps the id he carried as a
prospect, his motivation profile is identical from recruitment through his whole
career. Poaching (Phase 3) and buyouts (Phase 4) build on the same machinery.

Pure decision functions live here so they are unit-testable without a DB; the
``evaluate_*`` wrappers wire them to real save data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import DEFAULT_CONTRACTS, ContractConfig
from .models import Player


# --- motivation adapter ---------------------------------------------------------

@dataclass(frozen=True)
class _PlayerMotivationView:
    """Exposes a rostered ``Player`` through the prospect interface the V24
    motivation graders read (``player_id`` / ``public_archetype_guess`` /
    ``hometown``)."""

    player_id: str
    public_archetype_guess: str
    hometown: Optional[str]


def motivation_view(player: Player, hometown: Optional[str] = None) -> _PlayerMotivationView:
    return _PlayerMotivationView(
        player_id=player.id,
        # Same ``str(archetype)`` expression build_club_context uses to key the
        # roster archetype counts, so the Court Time grade reads real depth.
        public_archetype_guess=str(getattr(player, "archetype", "") or ""),
        hometown=hometown,
    )


# --- expiring cohort ------------------------------------------------------------

def expiring_players(conn, club_id: str) -> List[Player]:
    """Players whose contract has run out (term <= 0) — the re-sign cohort."""
    from .persistence import load_club_roster

    try:
        roster = load_club_roster(conn, club_id)
    except KeyError:
        return []
    return [p for p in roster if p.contract_term <= 0]


# --- retention (re-sign) decision ----------------------------------------------

@dataclass(frozen=True)
class ResignOutcome:
    player_id: str
    re_signed: bool
    fit: float
    veto: bool
    offer_salary_k: int
    expected_salary_k: int
    required_salary_k: int
    receipt: str


def resign_required_salary_k(
    expected_salary_k: int, fit: float, config: ContractConfig = DEFAULT_CONTRACTS
) -> int:
    """The salary the player will accept, bent by motivation fit.

    fit 1.0 -> ``expected * (1 - resign_fit_discount)`` (loyal, signs cheap);
    fit 0.0 -> ``expected * (1 + resign_low_fit_premium)`` (wants a premium).
    """
    fit = max(0.0, min(1.0, fit))
    span = config.resign_fit_discount + config.resign_low_fit_premium
    factor = 1.0 + config.resign_low_fit_premium - span * fit
    return round(expected_salary_k * factor)


def retention_decision(
    *,
    offer_salary_k: int,
    expected_salary_k: int,
    fit: float,
    veto: bool,
    dealbreaker: str = "",
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> tuple[bool, int, str]:
    """Pure re-sign decision. Returns (re_signed, required_salary_k, receipt).

    A dealbreaker veto can never re-sign regardless of money; otherwise the
    player re-signs when the offer meets the fit-adjusted salary he requires.
    """
    if veto:
        label = dealbreaker.replace("_", " ").title() if dealbreaker else "a core need"
        return False, expected_salary_k, f"Walked: {label} grade too low to re-sign at any price."
    required = resign_required_salary_k(expected_salary_k, fit, config)
    if offer_salary_k >= required:
        return True, required, f"Re-signed: ${offer_salary_k}k met his ${required}k ask (fit {fit:.0%})."
    return (
        False,
        required,
        f"Walked: ${offer_salary_k}k fell short of his ${required}k ask (fit {fit:.0%}).",
    )


def evaluate_retention(
    conn,
    club_id: str,
    player: Player,
    offer_salary_k: int,
    season_id: Optional[str] = None,
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> ResignOutcome:
    """Grade a rostered player against his own club and decide the re-sign."""
    from . import contracts
    from .motivations import build_club_context, club_fit
    from .persistence import load_division_map

    ctx = build_club_context(conn, club_id, season_id)
    fit = club_fit(ctx, motivation_view(player))
    tier = 3
    if season_id:
        seat = load_division_map(conn, season_id).get(club_id)
        tier = seat.tier if seat is not None else 3
    expected = contracts.second_contract_salary_k(player.overall_skill(), tier)
    re_signed, required, receipt = retention_decision(
        offer_salary_k=offer_salary_k,
        expected_salary_k=expected,
        fit=fit.fit,
        veto=fit.veto,
        dealbreaker=fit.dealbreaker,
        config=config,
    )
    return ResignOutcome(
        player_id=player.id,
        re_signed=re_signed,
        fit=fit.fit,
        veto=fit.veto,
        offer_salary_k=offer_salary_k,
        expected_salary_k=expected,
        required_salary_k=required,
        receipt=receipt,
    )


__all__ = [
    "motivation_view",
    "expiring_players",
    "ResignOutcome",
    "resign_required_salary_k",
    "retention_decision",
    "evaluate_retention",
]
