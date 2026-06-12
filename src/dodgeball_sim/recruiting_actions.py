"""Pure recruiting-action effects: every action returns a visible before/after.

Codex's recurring complaint across the multi-season run was that Scout / Contact
/ Visit changed a status label but showed no payoff -- the player could not tell
whether any of them did anything. This module makes each action mutate a
*verifiable* piece of state and report the delta:

- **Scout** narrows the public OVR band (reveals information). The narrowed band
  is the one the rest of the recruiting surface reads, so the effect is real and
  durable, not cosmetic.
- **Contact / Visit** raise a persisted ``interest`` value (0-100).

CONSUMER (V16 Contested Offseason): interest is mechanical. The offseason
picker resolves prospect picks through ``recruitment.conduct_recruitment_round``
where the user's offer = ``CONTESTED_USER_OFFER_BASE + interest *
CONTESTED_USER_OFFER_INTEREST_WEIGHT`` against real AI bids — courted
prospects are measurably harder to snipe (tools/contested_offer_probe.py).
Player-facing strings here and in the term registry may (and should) say so.

The module is pure -- it takes the prospect's current action state plus its base
public band and returns a new state and a :class:`RecruitingActionResult`. No
SQLite, no I/O. Persistence and the HTTP layer live in the server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Action = Literal["scout", "contact", "visit"]

# Interest gains per relationship action. Visit is the heavier touch.
_CONTACT_GAIN = 12
_VISIT_GAIN = 20
# A single scout pulls each end of the public band this fraction toward the
# midpoint -- enough to be visibly tighter without pretending to reveal the
# true rating.
_SCOUT_NARROW = 0.4


def base_interest(*, pipeline_tier: int, credibility_score: int) -> int:
    """Starting interest before any contact, from pipeline strength + program credibility.

    Pipeline tiers run 1 (weakest) → 5 (Elite, strongest), matching the 5-star
    mental model the UI teaches (``PipelineEmblem`` tier 5 = "Elite"). A *higher*
    tier starts *warmer*. This is the exact mirror of the prior (inverted) curve:
    ``max(0, pipeline_tier - 2) * 5`` reflects ``max(0, 4 - pipeline_tier) * 5``
    around the tier midpoint, so the warmest magnitude (+15) and the population
    mean over uniform tiers are preserved — only the tier↔interest direction
    flips (WT-25). No balance re-tune.
    """
    tier_floor = max(0, int(pipeline_tier) - 2) * 5  # higher tier starts warmer
    raw = 30 + tier_floor + int(credibility_score) * 0.15
    return _clamp_int(raw, 0, 80)


def narrow_band(
    band: tuple[int, int], *, scouted: bool, quality: float = 1.0
) -> tuple[int, int]:
    """Return the public OVR band the player should see, narrowed once if scouted.

    ``quality`` (V22 Phase 4) scales the narrowing with the SCOUTING head who
    ran the assignment (staff_effects.scouting_band_quality, 0.70–1.30);
    1.0 reproduces the legacy narrowing exactly. Clamped so even a perfect
    scout never pretends to reveal the true rating.
    """
    low, high = int(band[0]), int(band[1])
    if not scouted or high <= low:
        return (low, high)
    narrow = max(0.0, min(0.9, _SCOUT_NARROW * float(quality)))
    mid = (low + high) / 2.0
    new_low = round(mid - (mid - low) * (1.0 - narrow))
    new_high = round(mid + (high - mid) * (1.0 - narrow))
    return (int(new_low), int(new_high))


def scouted_band_from_state(
    state: dict[str, Any], base_band: tuple[int, int]
) -> tuple[int, int]:
    """The band a surface should display for this prospect's action state.

    V22 Phase 4: a Scout action persists the band it produced (scaled by the
    scouting head AT SCOUT TIME) as ``scouted_band``, so every surface shows
    the same numbers even if the head changes later. Legacy states without it
    fall back to the default-quality narrowing.
    """
    stored = state.get("scouted_band")
    if (
        isinstance(stored, (list, tuple))
        and len(stored) == 2
        and all(isinstance(value, (int, float)) for value in stored)
    ):
        return (int(stored[0]), int(stored[1]))
    return narrow_band(base_band, scouted=bool(state.get("scouted")))


def current_interest(state: dict[str, Any], *, pipeline_tier: int, credibility_score: int) -> int:
    """Interest stored on the prospect's action state, or the computed base if unset."""
    stored = state.get("interest")
    if stored is None:
        return base_interest(pipeline_tier=pipeline_tier, credibility_score=credibility_score)
    return _clamp_int(stored, 0, 100)


@dataclass(frozen=True)
class RecruitingActionResult:
    """The visible payoff of a single recruiting action."""

    action: Action
    headline: str
    interest_before: int
    interest_after: int
    ovr_band_before: tuple[int, int]
    ovr_band_after: tuple[int, int]
    next_step: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "headline": self.headline,
            "interest_before": self.interest_before,
            "interest_after": self.interest_after,
            "ovr_band_before": list(self.ovr_band_before),
            "ovr_band_after": list(self.ovr_band_after),
            "next_step": self.next_step,
        }


def apply_action(
    state: dict[str, Any],
    action: Action,
    *,
    base_band: tuple[int, int],
    pipeline_tier: int,
    credibility_score: int,
    gain_multiplier: float = 1.0,
    scout_quality: float = 1.0,
) -> tuple[dict[str, Any], RecruitingActionResult]:
    """Apply one action to a prospect's action state, returning new state + the delta.

    ``state`` is the per-prospect dict from ``prospect_recruitment_actions_json``.
    The returned state is a new dict (the input is not mutated).
    ``gain_multiplier`` scales the interest gains (V19b: a "culture" staff
    focus week makes contact/visits land warmer).
    ``scout_quality`` (V22 Phase 4) scales how tightly THIS scout narrows the
    band; the produced band persists on the state so every surface agrees.
    """
    new_state = dict(state)

    interest_before = current_interest(
        state, pipeline_tier=pipeline_tier, credibility_score=credibility_score
    )
    band_before = scouted_band_from_state(state, base_band)

    interest_after = interest_before
    if action == "scout":
        new_state["scouted"] = True
        new_state["scouted_band"] = list(
            narrow_band(base_band, scouted=True, quality=scout_quality)
        )
    elif action == "contact":
        new_state["contacted"] = True
        interest_after = _clamp_int(
            interest_before + int(round(_CONTACT_GAIN * gain_multiplier)), 0, 100
        )
    elif action == "visit":
        new_state["visited"] = True
        interest_after = _clamp_int(
            interest_before + int(round(_VISIT_GAIN * gain_multiplier)), 0, 100
        )
    else:  # pragma: no cover - guarded by the Literal type at call sites
        raise ValueError(f"Unknown recruiting action: {action}")

    new_state["interest"] = interest_after
    band_after = scouted_band_from_state(new_state, base_band)

    return new_state, RecruitingActionResult(
        action=action,
        headline=_headline(action, interest_before, interest_after, band_before, band_after),
        interest_before=interest_before,
        interest_after=interest_after,
        ovr_band_before=band_before,
        ovr_band_after=band_after,
        next_step=_next_step(new_state, interest_after),
    )


def _headline(
    action: Action,
    interest_before: int,
    interest_after: int,
    band_before: tuple[int, int],
    band_after: tuple[int, int],
) -> str:
    if action == "scout":
        if band_after != band_before:
            return (
                f"Scout report tightened the OVR read: "
                f"{band_before[0]}-{band_before[1]} → {band_after[0]}-{band_after[1]}."
            )
        return "Scout report filed — the OVR read is already as tight as it gets."
    verb = "Contact call" if action == "contact" else "Campus visit"
    return f"{verb} landed: interest {interest_before}% → {interest_after}%."


def _next_step(state: dict[str, Any], interest: int) -> str:
    # Interest feeds the contested Signing Day offer (see module docstring),
    # so the copy may honestly promise signing odds.
    if not state.get("scouted"):
        return "Scout to tighten the OVR read before you commit a visit slot."
    if interest < 50:
        return (
            "Interest is lukewarm — a contact call or visit strengthens your "
            "Signing Day offer."
        )
    if not state.get("visited"):
        return "Strong interest. A campus visit makes your Signing Day offer hard to beat."
    return (
        "You've done the work — this prospect is near-safe from Signing Day "
        "snipes. Keep them atop your shortlist."
    )


def _clamp_int(value: float, low: int, high: int) -> int:
    return int(max(low, min(high, round(value))))


__all__ = [
    "Action",
    "RecruitingActionResult",
    "apply_action",
    "base_interest",
    "current_interest",
    "narrow_band",
]
