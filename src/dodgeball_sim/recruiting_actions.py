"""Pure recruiting-action effects: every action returns a visible before/after.

Codex's recurring complaint across the multi-season run was that Scout / Contact
/ Visit changed a status label but showed no payoff -- the player could not tell
whether any of them did anything. This module makes each action mutate a
*verifiable* piece of state and report the delta:

- **Scout** narrows the public OVR band (reveals information). The narrowed band
  is the one the rest of the recruiting surface reads, so the effect is real and
  durable, not cosmetic.
- **Contact / Visit** raise a persisted ``interest`` value (0-100). Interest is
  not a hidden boost: it feeds the user's offer strength at signing (see
  ``recruitment.conduct_recruitment_round``), so building interest genuinely
  improves the chance of landing the recruit.

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


def narrow_band(band: tuple[int, int], *, scouted: bool) -> tuple[int, int]:
    """Return the public OVR band the player should see, narrowed once if scouted."""
    low, high = int(band[0]), int(band[1])
    if not scouted or high <= low:
        return (low, high)
    mid = (low + high) / 2.0
    new_low = round(mid - (mid - low) * (1.0 - _SCOUT_NARROW))
    new_high = round(mid + (high - mid) * (1.0 - _SCOUT_NARROW))
    return (int(new_low), int(new_high))


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
) -> tuple[dict[str, Any], RecruitingActionResult]:
    """Apply one action to a prospect's action state, returning new state + the delta.

    ``state`` is the per-prospect dict from ``prospect_recruitment_actions_json``.
    The returned state is a new dict (the input is not mutated).
    """
    new_state = dict(state)

    interest_before = current_interest(
        state, pipeline_tier=pipeline_tier, credibility_score=credibility_score
    )
    scouted_before = bool(state.get("scouted"))
    band_before = narrow_band(base_band, scouted=scouted_before)

    interest_after = interest_before
    if action == "scout":
        new_state["scouted"] = True
    elif action == "contact":
        new_state["contacted"] = True
        interest_after = _clamp_int(interest_before + _CONTACT_GAIN, 0, 100)
    elif action == "visit":
        new_state["visited"] = True
        interest_after = _clamp_int(interest_before + _VISIT_GAIN, 0, 100)
    else:  # pragma: no cover - guarded by the Literal type at call sites
        raise ValueError(f"Unknown recruiting action: {action}")

    new_state["interest"] = interest_after
    band_after = narrow_band(base_band, scouted=bool(new_state.get("scouted")))

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
    if not state.get("scouted"):
        return "Scout to tighten the OVR read before you commit a visit slot."
    if interest < 50:
        return "Interest is lukewarm — a contact call or visit builds your standing."
    if not state.get("visited"):
        return "Strong interest. A campus visit makes your Signing Day offer hard to beat."
    return "You've done the work — slot this prospect as a Signing Day target."


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
