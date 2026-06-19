"""V24 The Board — receipts-backed recruiting motivations.

Each prospect cares about 2-3 of seven motivations and has one hidden
dealbreaker. A club's FIT to a prospect is the weighted blend of the club's
GRADE in the motivations he cares about — every grade computed from real save
data with a plain-language receipt (no hidden dials; ADR 0002 faithfulness).
Fit strengthens the Signing Day offer and in-season interest momentum; a club
graded below ~C in the dealbreaker can never earn a verbal.

The prospect's motivation profile is derived deterministically from his
player_id on a SEPARATE rng stream (derive_seed(0, "v24_motivation", id)), so it
is stable per save and never perturbs the prospect-generation stream.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .rng import DeterministicRNG, derive_seed

MOTIVATIONS: Tuple[str, ...] = (
    "court_time",
    "contender",
    "development",
    "legacy",
    "staff",
    "scheme_fit",
    "hometown",
)

MOTIVATION_LABELS: Dict[str, str] = {
    "court_time": "Court Time",
    "contender": "Contender",
    "development": "Development",
    "legacy": "Legacy",
    "staff": "Staff",
    "scheme_fit": "Scheme Fit",
    "hometown": "Hometown",
}

# A club graded below this (≈ below a C) in a prospect's dealbreaker can never
# earn his verbal — the offer is vetoed, not merely weakened.
DEALBREAKER_MIN_GRADE = 0.45

# Development has no measured track record until the per-signee ceiling-delivery
# ledger exists (a later pass); until then it grades as an honest neutral C,
# never a dealbreaker fail. Mirrors league-memory's limited-state convention.
_DEVELOPMENT_LIMITED_SCORE = 0.55


def grade_letter(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.70:
        return "B"
    if score >= 0.55:
        return "C"
    if score >= 0.40:
        return "D"
    return "F"


@dataclass(frozen=True)
class MotivationProfile:
    cared: Tuple[str, ...]
    dealbreaker: str
    weights: Dict[str, float]


@dataclass(frozen=True)
class ClubMotivationContext:
    club_id: str
    tier: Optional[int]
    roster_archetype_counts: Dict[str, int]
    roster_size: int
    prestige: int
    titles: int
    hof_count: int
    staff_avg: float
    program_archetype: str
    home_region: Optional[str]


@dataclass(frozen=True)
class GradedMotivation:
    motivation: str
    label: str
    score: float
    letter: str
    receipt: str
    weight: float
    cared: bool


@dataclass(frozen=True)
class Fit:
    fit: float
    veto: bool
    dealbreaker: str
    grades: Dict[str, GradedMotivation]


def prospect_motivation_profile(prospect) -> MotivationProfile:
    """Which 2-3 motivations this prospect cares about, his dealbreaker (the
    heaviest), and the normalized weights — deterministic per prospect id."""
    rng = DeterministicRNG(derive_seed(0, "v24_motivation", str(prospect.player_id)))
    pool = rng.shuffle(list(MOTIVATIONS))
    count = 2 + int(rng.roll(0, 1.999))  # 2 or 3
    cared = tuple(pool[:count])
    dealbreaker = cared[0]
    # The dealbreaker carries half the weight; the rest split the remainder.
    rest = (1.0 - 0.5) / (count - 1)
    weights = {cared[0]: 0.5}
    for m in cared[1:]:
        weights[m] = rest
    return MotivationProfile(cared=cared, dealbreaker=dealbreaker, weights=weights)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _grade_court_time(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    lane = getattr(prospect, "public_archetype_guess", None) or "their role"
    at_lane = ctx.roster_archetype_counts.get(lane, 0)
    score = _clamp(1.0 - 0.22 * at_lane, 0.1, 1.0)
    if at_lane == 0:
        return score, f"No one ahead of you at {lane} — a clear path to the court."
    return score, f"{at_lane} already at your {lane} slot."


def _grade_contender(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    # Saturating normalization — scale-robust whatever the prestige range.
    score = _clamp(ctx.prestige / (ctx.prestige + 50.0)) if ctx.prestige > 0 else 0.0
    return score, f"Program prestige {ctx.prestige}."


def _grade_development(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    return _DEVELOPMENT_LIMITED_SCORE, "No measured development track record yet (limited)."


def _grade_legacy(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    score = _clamp(ctx.titles * 0.18 + ctx.hof_count * 0.12)
    return score, f"{ctx.titles} title(s), {ctx.hof_count} Hall of Famer(s)."


def _grade_staff(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    score = _clamp(ctx.staff_avg / 100.0)
    return score, f"Department heads average {ctx.staff_avg:.0f}."


# Coarse v1 scheme preference: which player archetype families a program leans
# toward. A match is a B+; anything else is an honest neutral C+.
_PROGRAM_SCHEME_HINTS: Dict[str, Tuple[str, ...]] = {
    "Contender": ("Power Thrower", "Catch Specialist"),
    "Development Factory": ("Quick Release", "Dodge Specialist", "All-Rounder"),
    "Aging Veterans": ("Catch Specialist", "All-Rounder"),
}


def _grade_scheme_fit(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    archetype = getattr(prospect, "public_archetype_guess", "") or ""
    prefers = _PROGRAM_SCHEME_HINTS.get(ctx.program_archetype, ())
    if any(archetype == p or archetype in p or p in archetype for p in prefers):
        return 0.82, f"Your {ctx.program_archetype} scheme prizes a {archetype}."
    return 0.60, f"A {archetype} fits your {ctx.program_archetype} scheme well enough."


def _grade_hometown(ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    home = getattr(prospect, "hometown", None)
    if ctx.home_region and home == ctx.home_region:
        return 1.0, f"A local kid from {home}."
    if ctx.home_region and home and home.endswith("District") and ctx.home_region.endswith("District"):
        return 0.62, f"From {home}; you're rooted in {ctx.home_region}."
    return 0.45, f"From {home}." if home else "Hometown unknown."


_GRADERS = {
    "court_time": _grade_court_time,
    "contender": _grade_contender,
    "development": _grade_development,
    "legacy": _grade_legacy,
    "staff": _grade_staff,
    "scheme_fit": _grade_scheme_fit,
    "hometown": _grade_hometown,
}


def grade_motivation(motivation: str, ctx: ClubMotivationContext, prospect) -> Tuple[float, str]:
    """Return (score in 0-1, plain-language receipt) for one motivation."""
    grader = _GRADERS.get(motivation)
    if grader is None:
        raise ValueError(f"Unknown motivation: {motivation}")
    return grader(ctx, prospect)


def club_fit(ctx: ClubMotivationContext, prospect) -> Fit:
    """The club's fit to the prospect: graded on every motivation (for display),
    blended by the prospect's cared-about weights, with the dealbreaker veto."""
    profile = prospect_motivation_profile(prospect)
    grades: Dict[str, GradedMotivation] = {}
    for m in MOTIVATIONS:
        score, receipt = grade_motivation(m, ctx, prospect)
        grades[m] = GradedMotivation(
            motivation=m,
            label=MOTIVATION_LABELS[m],
            score=round(score, 4),
            letter=grade_letter(score),
            receipt=receipt,
            weight=profile.weights.get(m, 0.0),
            cared=m in profile.cared,
        )
    fit = sum(profile.weights[m] * grades[m].score for m in profile.cared)
    veto = grades[profile.dealbreaker].score < DEALBREAKER_MIN_GRADE
    return Fit(fit=round(fit, 4), veto=veto, dealbreaker=profile.dealbreaker, grades=grades)


def build_club_context(conn, club_id: str, season_id: Optional[str] = None) -> ClubMotivationContext:
    """Assemble a club's motivation context from real save data (one pass)."""
    from .persistence import (
        load_all_rosters,
        load_club_prestige,
        load_club_trophies,
        load_clubs,
        load_department_heads,
        load_division_map,
    )

    clubs = load_clubs(conn)
    club = clubs.get(club_id)
    roster = load_all_rosters(conn).get(club_id, [])
    archetype_counts: Dict[str, int] = {}
    for player in roster:
        key = str(getattr(player, "archetype", "") or "")
        archetype_counts[key] = archetype_counts.get(key, 0) + 1

    titles = sum(1 for t in load_club_trophies(conn) if t.get("club_id") == club_id)

    tier = None
    if season_id:
        seat = load_division_map(conn, season_id).get(club_id)
        tier = seat.tier if seat is not None else None

    # Staff: only the user club has a department-head table; AI clubs use an
    # abstracted proxy by tier (matching staff_effects' AI convention) so the
    # Staff grade is symmetric in spirit, never user-only fiction.
    heads = load_department_heads(conn)
    if heads and (club is not None and getattr(club, "is_user_club", False) or _is_user_club(conn, club_id)):
        staff_avg = sum(float(h.get("rating_primary") or 0) for h in heads) / len(heads)
    else:
        staff_avg = {1: 80.0, 2: 68.0, 3: 58.0}.get(tier or 0, 65.0)

    return ClubMotivationContext(
        club_id=club_id,
        tier=tier,
        roster_archetype_counts=archetype_counts,
        roster_size=len(roster),
        prestige=load_club_prestige(conn, club_id),
        titles=titles,
        hof_count=0,  # per-club HoF attribution lands with the Development ledger pass
        staff_avg=staff_avg,
        program_archetype=str(getattr(club, "program_archetype", "") or "Balanced Rebuild"),
        home_region=getattr(club, "home_region", None),
    )


def _is_user_club(conn, club_id: str) -> bool:
    from .persistence import get_state

    return get_state(conn, "player_club_id") == club_id
