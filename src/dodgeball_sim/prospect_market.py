"""V24 The Board Phase 5 — visible rival suitors + the in-season interest race.

For each focused prospect the recruiting board shows the AI clubs courting him
and how the user's tracked interest stacks against the strongest rival's derived
pursuit. Pursuit is a DETERMINISTIC, receipts-backed proxy: the talent a club
can see (the public ceiling band) + how hard its division tier chases upside
(reusing the V24 tier-ceiling preference) + a stable per-(prospect, club) jitter.
A club the prospect would veto on his hidden dealbreaker is not counted a real
suitor (willingness gate). No hidden dials (ADR 0002): every rival's interest is
derivable from data and carries a plain-language receipt.

Leading the race is defensible. While the user's interest leads the strongest
rival, courtship lands with a momentum bonus that compounds with the weeks left
in the season, so an early lead beats a late entry at equal effort (Phase 5
momentum gate). The pure helpers here are DB-free; the orchestration that reads
clubs/divisions and persists signals lives in ``recruiting_office``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import (
    AI_TIER_CEILING_BASELINE,
    AI_TIER_CEILING_PREFERENCE,
    RIVAL_MOMENTUM_MAX,
    RIVAL_MOMENTUM_PER_WEEK,
    RIVAL_PURSUIT_JITTER_SPAN,
    RIVAL_PURSUIT_TALENT_WEIGHT,
)


@dataclass(frozen=True)
class RivalSuitor:
    club_id: str
    club_name: str
    tier: Optional[int]
    interest: int
    receipt: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "club_id": self.club_id,
            "club_name": self.club_name,
            "tier": self.tier,
            "interest": self.interest,
            "receipt": self.receipt,
        }


@dataclass(frozen=True)
class MarketSignal:
    rivals: Tuple[RivalSuitor, ...]
    leader: str          # "user" or a rival club_id
    user_interest: int
    top_rival_interest: int
    user_lead: int       # signed: user_interest - top_rival_interest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rivals": [r.to_dict() for r in self.rivals],
            "leader": self.leader,
            "user_interest": self.user_interest,
            "top_rival_interest": self.top_rival_interest,
            "user_lead": self.user_lead,
        }


def derive_club_pursuit(*, public_high_band: float, tier: Optional[int], jitter: float) -> int:
    """A deterministic 0-100 proxy for how hard an AI club courts a prospect.

    Clubs see talent (the public ceiling band); higher-tier clubs weight upside
    above the baseline harder (the V24 tier-ceiling preference); ``jitter`` is a
    stable per-(prospect, club) value in [0, 1] giving each club a personality
    spread. Pure and bounded — the receipt cites these same factors.
    """
    high = float(public_high_band)
    base = high * RIVAL_PURSUIT_TALENT_WEIGHT
    upside = max(0.0, high - AI_TIER_CEILING_BASELINE)
    tier_pref = AI_TIER_CEILING_PREFERENCE.get(int(tier or 0), 0.0)
    spread = (float(jitter) - 0.5) * RIVAL_PURSUIT_JITTER_SPAN
    score = base + upside * tier_pref + spread
    return int(max(0, min(100, round(score))))


def build_market_signal(*, user_interest: int, rivals: Sequence[RivalSuitor]) -> MarketSignal:
    """Combine the user's tracked interest with rival pursuits into the race
    signal: who leads and by how much. Ties go to the user (you hold serve)."""
    ranked = sorted(rivals, key=lambda r: (-r.interest, r.club_id))
    top = ranked[0].interest if ranked else 0
    leader = "user" if int(user_interest) >= top else ranked[0].club_id
    return MarketSignal(
        rivals=tuple(ranked),
        leader=leader,
        user_interest=int(user_interest),
        top_rival_interest=int(top),
        user_lead=int(user_interest) - int(top),
    )


def leading_momentum_bonus(*, weeks_remaining: int, leading: bool) -> int:
    """Extra interest a courtship action lands while the user LEADS the race.

    Scales with the weeks left in the season (an early lead compounds over more
    weeks), capped so it is a modest defensible edge, never a runaway. Zero when
    trailing — momentum rewards holding a lead, it does not manufacture one."""
    if not leading or int(weeks_remaining) <= 0:
        return 0
    return int(min(RIVAL_MOMENTUM_MAX, round(int(weeks_remaining) * RIVAL_MOMENTUM_PER_WEEK)))


__all__ = [
    "RivalSuitor",
    "MarketSignal",
    "derive_club_pursuit",
    "build_market_signal",
    "leading_momentum_bonus",
]
