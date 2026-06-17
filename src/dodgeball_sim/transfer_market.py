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


# --- Phase 3: uphill poaching ---------------------------------------------------

@dataclass(frozen=True)
class PoachSuitor:
    club_id: str
    club_name: str
    tier: int
    offer_salary_k: int
    interest: int
    receipt: str


def poach_suitors(
    conn,
    season_id: str,
    player: Player,
    user_club_id: str,
    root_seed: int,
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> List[PoachSuitor]:
    """Higher-tier AI clubs with wage headroom that court a user expiring star.

    Poaching flows UPHILL: only clubs in a higher tier (lower tier number) than
    the player's club bid, and only when their tier wage budget has room for his
    estimated wage. Interest reuses the V24 ``derive_club_pursuit`` proxy on a
    fresh ``v25_poach`` stream (the player's OVR is the talent a club reads);
    the offer scales the estimated wage up by that interest. Deterministic.
    """
    from . import contracts
    from .prospect_market import derive_club_pursuit
    from .persistence import load_all_rosters, load_clubs, load_division_map
    from .rng import DeterministicRNG, derive_seed

    division_map = load_division_map(conn, season_id)
    user_seat = division_map.get(user_club_id)
    if user_seat is None:
        return []
    user_tier = user_seat.tier
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    ovr = player.overall_skill()

    suitors: List[PoachSuitor] = []
    for club_id, seat in division_map.items():
        if club_id == user_club_id or seat.tier >= user_tier:
            continue  # uphill only (lower tier number = higher rung)
        est_wage = contracts.second_contract_salary_k(ovr, seat.tier, config)
        bill = contracts.wage_bill_k(rosters.get(club_id, []), config)
        budget = contracts.wage_budget_for_tier(seat.tier, config)
        if budget - bill < est_wage:
            continue  # no wage headroom — the cap binds
        jitter = DeterministicRNG(
            derive_seed(root_seed, "v25_poach", player.id, club_id)
        ).unit()
        interest = derive_club_pursuit(public_high_band=ovr, tier=seat.tier, jitter=jitter)
        if interest <= 0:
            continue
        offer = round(est_wage * (1.0 + config.poach_offer_interest_scale * interest / 100.0))
        name = getattr(clubs.get(club_id), "name", club_id)
        suitors.append(
            PoachSuitor(
                club_id=club_id,
                club_name=name,
                tier=seat.tier,
                offer_salary_k=offer,
                interest=interest,
                receipt=f"{name} (Tier {seat.tier}) — interest {interest}, offers ${offer}k.",
            )
        )
    return sorted(suitors, key=lambda s: (-s.offer_salary_k, -s.interest, s.club_id))


@dataclass(frozen=True)
class PoachResolution:
    player_id: str
    stayed: bool
    winner_club_id: Optional[str]
    user_offer_k: int
    best_rival_offer_k: int
    fit: float
    veto: bool
    dev_compensation_k: int
    receipt: str


def resolve_poaching(
    *,
    player_id: str,
    user_offer_k: int,
    expected_salary_k: int,
    fit: float,
    veto: bool,
    dealbreaker_letter: str,
    suitors: List[PoachSuitor],
    salary_k: int,
    term_remaining: int,
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> PoachResolution:
    """Decide whether a courted expiring player stays or is poached.

    Money is the dominant pull; motivations break ties — a loyal (high-fit)
    player stays even when outbid, up to a fit-scaled loyalty buffer; a
    dealbreaker veto always leaves. A departure earns the user a modest
    development-compensation credit and carries a data-derived receipt.
    """
    best = suitors[0] if suitors else None
    rival = best.offer_salary_k if best else 0
    required = resign_required_salary_k(expected_salary_k, fit, config)
    loyalty_buffer = round(max(0.0, min(1.0, fit)) * config.poach_loyalty_money_k)

    stays = (
        not veto
        and user_offer_k >= required
        and user_offer_k + loyalty_buffer >= rival
    )
    if stays or best is None:
        # No suitor able to take him, or he chose to stay: he is retained (the
        # caller still checks retention_decision for the no-suitor walk case).
        return PoachResolution(
            player_id=player_id,
            stayed=stays,
            winner_club_id=None,
            user_offer_k=user_offer_k,
            best_rival_offer_k=rival,
            fit=fit,
            veto=veto,
            dev_compensation_k=0,
            receipt=(
                f"Re-signed: held off {best.club_name} (${rival}k) on a ${user_offer_k}k offer."
                if (stays and best is not None)
                else f"Re-signed: ${user_offer_k}k, no rival pursuit."
            ),
        )

    from . import contracts

    dev_comp = contracts.dev_compensation_k(salary_k, term_remaining, config)
    ratio = rival / max(1, user_offer_k)
    if veto:
        reason = f"his {dealbreaker_letter} dealbreaker grade left him gone at any price"
    else:
        reason = f"outbid ×{ratio:.1f} (${rival}k vs your ${user_offer_k}k)"
    return PoachResolution(
        player_id=player_id,
        stayed=False,
        winner_club_id=best.club_id,
        user_offer_k=user_offer_k,
        best_rival_offer_k=rival,
        fit=fit,
        veto=veto,
        dev_compensation_k=dev_comp,
        receipt=f"Poached by {best.club_name}: {reason}. (+${dev_comp}k development compensation.)",
    )


# --- Phase 4: buyouts (incoming refusable, outgoing bids) -----------------------

@dataclass(frozen=True)
class BuyoutOffer:
    buyer_club_id: str
    buyer_club_name: str
    buyer_tier: int
    player_id: str
    player_name: str
    fee_k: int
    receipt: str


def incoming_buyout_offers(
    conn,
    season_id: str,
    user_club_id: str,
    root_seed: int,
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> List[BuyoutOffer]:
    """Higher-tier clubs table refusable buyout bids for the user's CONTRACTED
    (non-expiring) stars whose pursuit interest clears the threshold.

    Accepting is treasury income; refusing keeps the player and his wage — the
    'couldn't let him fall into another team's hands' beat. Deterministic on the
    ``v25_transfer`` stream; only solvent (wage-headroom) higher-tier clubs bid.
    """
    from . import contracts
    from .prospect_market import derive_club_pursuit
    from .persistence import load_all_rosters, load_clubs, load_division_map
    from .rng import DeterministicRNG, derive_seed

    division_map = load_division_map(conn, season_id)
    user_seat = division_map.get(user_club_id)
    if user_seat is None:
        return []
    user_tier = user_seat.tier
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    contracted = sorted(
        (p for p in rosters.get(user_club_id, []) if p.contract_term > 0),
        key=lambda p: -p.overall_skill(),
    )

    offers: List[BuyoutOffer] = []
    for player in contracted:
        ovr = player.overall_skill()
        best = None  # (club_id, interest, tier)
        for club_id, seat in division_map.items():
            if club_id == user_club_id or seat.tier >= user_tier:
                continue
            est_wage = contracts.second_contract_salary_k(ovr, seat.tier, config)
            bill = contracts.wage_bill_k(rosters.get(club_id, []), config)
            if contracts.wage_budget_for_tier(seat.tier, config) - bill < est_wage:
                continue
            jitter = DeterministicRNG(
                derive_seed(root_seed, "v25_transfer", player.id, club_id)
            ).unit()
            interest = derive_club_pursuit(public_high_band=ovr, tier=seat.tier, jitter=jitter)
            if best is None or interest > best[1]:
                best = (club_id, interest, seat.tier)
        if best is None or best[1] < config.buyout_interest_threshold:
            continue
        club_id, interest, tier = best
        fee = contracts.buyout_fee_k(player.salary_k, player.contract_term, config)
        name = getattr(clubs.get(club_id), "name", club_id)
        offers.append(
            BuyoutOffer(
                buyer_club_id=club_id,
                buyer_club_name=name,
                buyer_tier=tier,
                player_id=player.id,
                player_name=player.name,
                fee_k=fee,
                receipt=f"{name} (Tier {tier}) bids ${fee}k for {player.name} (interest {interest}).",
            )
        )
    return offers


def accept_buyout(conn, user_club_id: str, offer: BuyoutOffer) -> int:
    """Sell the player: move him to the buyer, credit the fee. Returns the fee."""
    from dataclasses import replace as _replace

    from .economy import set_treasury_k, treasury_k
    from .persistence import load_all_rosters, load_clubs, save_club

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    user_roster = rosters.get(user_club_id, [])
    moved = next((p for p in user_roster if p.id == offer.player_id), None)
    if moved is None:
        return 0
    save_club(conn, clubs[user_club_id], [p for p in user_roster if p.id != offer.player_id])
    buyer_roster = list(rosters.get(offer.buyer_club_id, [])) + [
        _replace(moved, club_id=offer.buyer_club_id)
    ]
    save_club(conn, clubs[offer.buyer_club_id], buyer_roster)
    set_treasury_k(conn, treasury_k(conn) + offer.fee_k)
    conn.commit()
    return offer.fee_k


@dataclass(frozen=True)
class OutgoingBidResult:
    success: bool
    asking_k: int
    bid_k: int
    player_id: str
    receipt: str


def outgoing_bid(
    conn,
    user_club_id: str,
    target_club_id: str,
    target_player_id: str,
    bid_k: int,
    config: ContractConfig = DEFAULT_CONTRACTS,
) -> OutgoingBidResult:
    """Bid against an AI asking price to buy a contracted player — rich-club
    privilege: the bid must meet the asking AND the treasury must cover it AND
    the selling club may not be left below the roster floor."""
    from dataclasses import replace as _replace

    from .economy import set_treasury_k, treasury_k
    from .persistence import load_all_rosters, load_clubs, save_club

    rosters = load_all_rosters(conn)
    target = next((p for p in rosters.get(target_club_id, []) if p.id == target_player_id), None)
    if target is None:
        return OutgoingBidResult(False, 0, bid_k, target_player_id, "Target not found.")
    from . import contracts

    asking = contracts.buyout_fee_k(target.salary_k, max(1, target.contract_term), config)
    treasury = treasury_k(conn)
    if bid_k < asking:
        return OutgoingBidResult(False, asking, bid_k, target_player_id,
                                 f"Bid ${bid_k}k under the ${asking}k asking price.")
    if treasury < bid_k:
        return OutgoingBidResult(False, asking, bid_k, target_player_id,
                                 f"Treasury ${treasury}k cannot cover ${bid_k}k — rich-club privilege.")
    if len(rosters.get(target_club_id, [])) - 1 < config.min_roster_after_transfer:
        return OutgoingBidResult(False, asking, bid_k, target_player_id,
                                 f"{target_club_id} won't sell below its roster floor.")
    clubs = load_clubs(conn)
    save_club(conn, clubs[target_club_id],
              [p for p in rosters.get(target_club_id, []) if p.id != target_player_id])
    save_club(conn, clubs[user_club_id],
              list(rosters.get(user_club_id, [])) + [_replace(target, club_id=user_club_id)])
    set_treasury_k(conn, treasury - bid_k)
    conn.commit()
    return OutgoingBidResult(True, asking, bid_k, target_player_id,
                             f"Signed {target.name} for ${bid_k}k (asking ${asking}k).")


__all__ = [
    "motivation_view",
    "expiring_players",
    "ResignOutcome",
    "resign_required_salary_k",
    "retention_decision",
    "evaluate_retention",
    "PoachSuitor",
    "poach_suitors",
    "PoachResolution",
    "resolve_poaching",
    "BuyoutOffer",
    "incoming_buyout_offers",
    "accept_buyout",
    "OutgoingBidResult",
    "outgoing_bid",
]
